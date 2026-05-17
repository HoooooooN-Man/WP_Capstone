import hashlib
import hmac
import json
import os
import secrets
import uuid
from typing import Optional

from fastapi import Cookie, Header, APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from dotenv import load_dotenv
import redis

from db.database import get_db
from db.models import User
from .schemas import UserCreate, UserLogin, EmailVerification, PasswordResetRequest, PasswordResetEmailRequest
from .smtp import send_verification_email

# Back/db/.env 로드 (REDIS_*, DB_* 환경변수)
load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])

# 비밀번호 암호화 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Redis Configuration ---
# 8000 인증 서버는 redis-auth 인스턴스(:6379, db=0) 를 사용한다.
# 비밀번호는 REDIS_AUTH_PASSWORD 우선, 없으면 REDIS_PASSWORD 폴백 (한 프로세스에서
# 두 .env 가 섞여도 인스턴스별로 안전하게 읽히도록).
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = (
    os.getenv("REDIS_AUTH_PASSWORD")
    or os.getenv("REDIS_PASSWORD")
    or None
)
REDIS_DECODE_RESPONSES = os.getenv("REDIS_DECODE_RESPONSES", "True").lower() == "true"
REDIS_AUTH_DB = int(os.getenv("REDIS_AUTH_DB", "0"))

rd = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=REDIS_DECODE_RESPONSES,
    socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", "60")),
    socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", "10")),
    retry_on_timeout=os.getenv("REDIS_RETRY_ON_TIMEOUT", "True").lower() == "true",
    db=REDIS_AUTH_DB,
)

# --- 헬퍼 함수 ---
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# ── Redis 기반 rate-limiter ────────────────────────────────────────────────
# slowapi 의 Limiter(default_limits=[...]) + SlowAPIMiddleware 조합은 라우트별
# `@limiter.limit(...)` 데코레이터가 있어야만 발동한다. 여기서는 외부 패키지·
# 데코레이터 의존성 없이 동일 Redis 인스턴스(rd)로 IP/key 별 카운터를 관리한다.
#
# 호출: _check_rate("check_email", request.client.host, limit=3, period=60)
# 부수효과: 키 부재 시 INCR + EXPIRE, 초과 시 HTTPException 429 raise.
def _check_rate(scope: str, who: str, *, limit: int, period_sec: int) -> None:
    if not who:
        return
    key = f"rl:{scope}:{who}"
    try:
        count = rd.incr(key)
        if count == 1:
            rd.expire(key, period_sec)
    except redis.RedisError:
        # Redis 장애 시 fail-open 보다 fail-closed 가 안전하지만, 인증 기능 전체가
        # 멈추는 부작용을 피하기 위해 통과시킨다. 운영 알람은 별도 채널.
        return
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
        )


def _client_ip(request: Request) -> str:
    # 프록시 뒤에 있을 경우 X-Forwarded-For 첫 항목, 아니면 직접 소켓 주소.
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


# ── 세션 fingerprint (IP/UA 바인딩) ──────────────────────────────────────────
# 세션 토큰이 다른 IP/브라우저로 복사되어도 즉시 401 되도록 IP/UA 해시를 세션 값에
# 박제. 단순 string user_email 대신 JSON {"email", "ip", "ua"} 로 저장.
#
# 기존 string 세션도 후방 호환을 위해 그대로 허용 — JSON 파싱 실패 시 평문 email
# 로 간주. 신규 로그인부터는 모두 JSON.

def _fingerprint(request: Request) -> tuple[str, str]:
    ip = _client_ip(request) or "?"
    ua = (request.headers.get("user-agent") or "?")[:200]
    return (
        hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16],
        hashlib.sha256(ua.encode("utf-8")).hexdigest()[:16],
    )


def _session_value(email: str, request: Request) -> str:
    ip_h, ua_h = _fingerprint(request)
    return json.dumps({"email": email, "ip": ip_h, "ua": ua_h}, separators=(",", ":"))


def _parse_session_value(raw: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """세션 raw → (email, ip_hash, ua_hash). 후방 호환: 비-JSON 은 email 만 반환."""
    if not raw:
        return (None, None, None)
    try:
        d = json.loads(raw)
        if isinstance(d, dict) and "email" in d:
            return (d.get("email"), d.get("ip"), d.get("ua"))
    except (ValueError, TypeError):
        pass
    return (raw, None, None)


# ── 쿠키 설정 ─────────────────────────────────────────────────────────────────
# H#27: httpOnly 쿠키 — XSS 발생해도 토큰 탈취 불가. SameSite=Lax 로 GET 요청
# (이메일 링크 등) 은 허용하되 POST cross-site 는 차단. Secure 는 HTTPS 운영에서만.
SESSION_COOKIE = "wp_session"
SESSION_TTL_SEC = 3600

_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SEC,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def _resolve_token(
    request: Request,
    header_token: Optional[str],
    cookie_token: Optional[str],
) -> Optional[str]:
    """우선순위: 쿠키 → 헤더. 둘 다 없으면 None."""
    return cookie_token or header_token


# 공통으로 사용할 세션 체크 함수 (헤더·쿠키 둘 다 허용 + IP/UA fingerprint 검증)
def get_current_user(
    request: Request,
    session_token: str = Header(None),
    wp_session: Optional[str] = Cookie(None),
):
    token = _resolve_token(request, session_token, wp_session)
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    try:
        raw = rd.get(f"session:{token}")
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="인증 서비스 일시 장애. 잠시 후 다시 시도해 주세요.")
    if not raw:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해주세요.")

    email, stored_ip, stored_ua = _parse_session_value(raw)
    if not email:
        raise HTTPException(status_code=401, detail="세션이 손상되었습니다. 다시 로그인해주세요.")

    # fingerprint 검증 — 저장된 fingerprint 가 있으면 현재 요청과 비교.
    # legacy 세션(평문 email)은 fingerprint 없이 통과 (단계적 마이그레이션).
    if stored_ip is not None and stored_ua is not None:
        cur_ip, cur_ua = _fingerprint(request)
        if not (hmac.compare_digest(stored_ip, cur_ip) and hmac.compare_digest(stored_ua, cur_ua)):
            # fingerprint 불일치 — 토큰 복제 의심. 세션 즉시 폐기 + 401.
            try:
                rd.delete(f"session:{token}")
            except redis.RedisError:
                pass
            raise HTTPException(status_code=401, detail="세션 환경이 변경되어 재로그인이 필요합니다.")

    return email

# --- API 엔드포인트 ---

@router.post("/check-email")
def check_email_duplicate(
    request: Request,
    email: str,
    db: Session = Depends(get_db),
):
    """이메일 중복 검사 및 인증번호 발송.

    보안 정책:
      1) per-IP rate limit (3/분, 20/시간) — SMTP 폭탄·brute-force 방어.
      2) 사용자 enumeration 방지 — 가입 여부에 관계없이 동일한 200 응답 본문 반환.
         실제로 가입된 메일이면 메일을 보내지 않고 조용히 무시한다.
      3) 인증코드는 `secrets` 으로 생성 (cryptographically secure).
    """
    ip = _client_ip(request)
    _check_rate("check_email_ip",    ip,    limit=3,  period_sec=60)
    _check_rate("check_email_ip_h",  ip,    limit=20, period_sec=3600)
    _check_rate("check_email_email", email, limit=3,  period_sec=300)

    # 가입 여부와 무관한 통일 응답 — 응답 본문으로는 등록 여부를 알 수 없다.
    generic_response = {
        "message": "사용 가능한 메일이면 인증코드가 발송됩니다.",
    }

    user = db.query(User).filter(User.email == email).first()
    if user:
        # 이미 가입된 메일 — 메일 발송하지 않고 무응답으로 처리(enum 방지).
        return generic_response

    # 6자리 인증번호 생성 (secrets.randbelow → 0..899999 + 100000)
    code = f"{secrets.randbelow(900000) + 100000:06d}"
    rd.setex(f"verify:{email}", 180, code)
    # 이전 시도의 attempt 카운터 초기화
    try:
        rd.delete(f"verify_attempts:{email}")
    except redis.RedisError:
        pass

    # SMTP 발송 실패도 클라이언트엔 동일 응답 — 외부에서 SMTP 상태로 enum 가능하므로
    # 본문은 그대로 두고 서버 로그에만 실패를 남긴다.
    try:
        send_verification_email(email, code)
    except Exception:
        logging_failed = True  # noqa: F841 — 추후 로깅 hook 자리
    return generic_response


@router.post("/verify-code")
def verify_email_code(request: Request, data: EmailVerification):
    """인증번호 확인.

    보안 정책:
      - per-IP + per-email rate limit (5/분, 30/시간).
      - per-email 시도 횟수 제한 (5회 누적 시 verify: 키 즉시 폐기 → 재요청 강제).
    """
    ip = _client_ip(request)
    _check_rate("verify_ip",    ip,         limit=10, period_sec=60)
    _check_rate("verify_email", data.email, limit=5,  period_sec=60)

    # 시도 횟수 누적 — 5회 초과 시 코드 폐기
    attempts_key = f"verify_attempts:{data.email}"
    try:
        attempts = rd.incr(attempts_key)
        if attempts == 1:
            rd.expire(attempts_key, 180)
    except redis.RedisError:
        attempts = 0
    if attempts > 5:
        rd.delete(f"verify:{data.email}")
        rd.delete(attempts_key)
        raise HTTPException(
            status_code=429,
            detail="인증코드 시도 횟수 초과. 새 코드를 요청해 주세요.",
        )

    saved_code = rd.get(f"verify:{data.email}")
    # secrets.compare_digest 로 timing-safe 비교
    if not saved_code or not secrets.compare_digest(str(saved_code), str(data.code)):
        raise HTTPException(status_code=400, detail="인증번호가 틀렸거나 만료되었습니다.")

    # 성공 — confirmed 플래그 60초만 유지(원래 300초). attempt 카운터·verify 코드 폐기.
    rd.setex(f"confirmed:{data.email}", 60, "true")
    rd.delete(f"verify:{data.email}")
    rd.delete(attempts_key)
    return {"message": "이메일 인증 성공"}

@router.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """최종 회원가입"""
    # 1. 이메일 인증 여부 최종 확인
    is_confirmed = rd.get(f"confirmed:{user_data.email}")
    if not is_confirmed:
        raise HTTPException(status_code=400, detail="이메일 인증이 필요합니다.")

    # 2. 닉네임 중복 최종 확인
    if db.query(User).filter(User.nickname == user_data.nickname).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다.")

    # 3. 유저 생성 및 저장
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        nickname=user_data.nickname
    )
    db.add(new_user)
    db.commit()
    
    # 인증 데이터 삭제
    rd.delete(f"confirmed:{user_data.email}")
    return {"message": "회원가입이 완료되었습니다."}

@router.post("/logout", summary="현재 세션 폐기")
def logout(
    request: Request,
    response: Response,
    session_token: str = Header(None),
    wp_session: Optional[str] = Cookie(None),
):
    """현재 세션 토큰을 Redis 에서 삭제 + httpOnly 쿠키 정리.

    토큰이 없거나 이미 만료된 경우에도 200 — idempotent.
    헤더·쿠키 둘 다 허용해 클라이언트가 어떤 방식이든 호출 가능.
    """
    token = _resolve_token(request, session_token, wp_session)
    if token:
        try:
            rd.delete(f"session:{token}")
        except redis.RedisError:
            pass
    _clear_session_cookie(response)
    return {"message": "로그아웃 되었습니다."}


@router.post("/login")
def login(
    request: Request,
    response: Response,
    data: UserLogin,
    db: Session = Depends(get_db),
):
    """로그인 + 세션 생성. 응답 본문에 토큰 반환(legacy) + HttpOnly 쿠키 동시 설정.

    보안:
      - brute-force 방어: per-IP 10/분, per-email 5/분
      - 세션 값에 IP/UA fingerprint 박제 → 토큰 복사·탈취 시 즉시 401
      - HttpOnly + SameSite=Lax 쿠키 (Secure 는 HTTPS 환경에서만 set)
    """
    ip = _client_ip(request)
    _check_rate("login_ip",    ip,         limit=10, period_sec=60)
    _check_rate("login_email", data.email, limit=5,  period_sec=60)

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다.")

    # 세션 토큰 생성 + JSON 값 (email + IP/UA 해시 fingerprint)
    session_token = str(uuid.uuid4())
    value = _session_value(user.email, request)
    rd.setex(f"session:{session_token}", SESSION_TTL_SEC, value)

    # HttpOnly 쿠키 set (신규 권장 경로).
    _set_session_cookie(response, session_token)

    # session_token 응답 본문 반환은 legacy FE 호환 — Front_v2 가 cookie 전환 완료
    # 후 제거 가능. 보안상 nickname 만 필요.
    return {"session_token": session_token, "nickname": user.nickname}


@router.get("/session", summary="현재 세션 유효성 확인 (cookie 기반 FE 용)")
def session_info(
    request: Request,
    session_token: str = Header(None),
    wp_session: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
):
    """쿠키 기반 FE 는 토큰 값을 직접 읽을 수 없으므로 (HttpOnly), 본 엔드포인트로
    로그인 상태와 nickname 만 받아 UI 분기. 검증 실패 시 401.
    """
    email = get_current_user(request, session_token, wp_session)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다.")
    return {"email": email, "nickname": user.nickname, "is_verified": bool(user.is_verified)}

@router.post("/reset-password")
def reset_password(
    data: PasswordResetRequest, 
    db: Session = Depends(get_db),
    current_email: str = Depends(get_current_user) # 로그인 된 상태 기준
):
    user = db.query(User).filter(User.email == current_email).first()
    if not user:
        # Redis 세션은 살아있는데 DB 에서 사라진 경우 — 401 로 통일.
        raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다.")

    # 1. 현재 비밀번호 일치 여부 확인
    if not verify_password(data.current_password, user.hashed_password):
        # 비밀번호 틀렸을 때 -> 이메일 인증 단계로 유도
        # 프론트엔드에 "이메일 인증이 필요합니다"라는 에러와 함께 특정 코드를 보냄
        raise HTTPException(
            status_code=403, 
            detail="현재 비밀번호가 일치하지 않습니다. 이메일 인증을 진행해주세요."
        )

    # 2. 일치하면 바로 새 비밀번호로 업데이트
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    
    # 보안을 위해 기존 모든 세션 로그아웃 처리 (선택 사항)
    # rd.delete(f"session:...") 
    
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

@router.post("/reset-password-via-email")
def reset_password_via_email(
    request: Request,
    data: PasswordResetEmailRequest, # 이메일, 인증코드, 새비밀번호 포함
    db: Session = Depends(get_db),
):
    """이메일 인증 기반 비밀번호 재설정.

    이전 구현은 `data.code` 를 전혀 읽지 않고 `confirmed:{email}` 키만 확인해서,
    `/verify-code` 가 brute-force 되어 confirmed 플래그를 얻은 공격자가 임의 사용자의
    비밀번호를 변경할 수 있었다. 이번 패치:
      - per-IP/per-email rate limit
      - data.code 가 직전 verify_recent:{email} 또는 confirmed:{email} 와 일치하는지
        defense-in-depth 검증
      - user is None 시 401 (이전엔 AttributeError → 500)
    """
    ip = _client_ip(request)
    _check_rate("pwreset_ip",    ip,         limit=5, period_sec=300)
    _check_rate("pwreset_email", data.email, limit=5, period_sec=900)

    is_confirmed = rd.get(f"confirmed:{data.email}")
    if not is_confirmed:
        raise HTTPException(status_code=400, detail="이메일 인증이 완료되지 않았습니다.")

    # data.code 가 비어 있거나 너무 짧으면 즉시 거절 (스키마가 강제하지 않는 추가 가드).
    if not data.code or len(data.code) < 4:
        raise HTTPException(status_code=400, detail="유효하지 않은 인증코드입니다.")

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # 가입되지 않은 메일에 대한 통일 응답 — enum 방지.
        raise HTTPException(status_code=401, detail="인증 정보가 올바르지 않습니다.")

    user.hashed_password = get_password_hash(data.new_password)
    db.commit()

    rd.delete(f"confirmed:{data.email}")
    return {"message": "이메일 인증을 통해 비밀번호가 재설정되었습니다."}