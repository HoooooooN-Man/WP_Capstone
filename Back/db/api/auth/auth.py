# auth/router.py — 보안 강화 버전

from fastapi import Header, APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from dotenv import load_dotenv
import redis
import random
import os
import uuid
import hmac  # 타이밍 어택 방지용

from db.database import get_db
from db.models import User
from .schemas import UserCreate, UserLogin, SetPasswordRequest, EmailVerification, PasswordResetRequest, PasswordResetEmailRequest
from .smtp import send_verification_email

load_dotenv()
router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Redis 연결 ──────────────────────────────────────────────────────────────
REDIS_HOST     = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT     = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_AUTH_PASSWORD") or os.getenv("REDIS_PASSWORD") or None
REDIS_AUTH_DB  = int(os.getenv("REDIS_AUTH_DB", "0"))

rd = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", "60")),
    socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", "10")),
    retry_on_timeout=True,
    db=REDIS_AUTH_DB,
)

# Redis 접근 불가 시 fakeredis(in-memory) 로 graceful fallback.
# 운영 Redis(Tailscale 100.67.30.5)가 닿지 않는 데모/오프라인 환경에서 인증·세션·인증코드 동작 유지.
# in-memory 라 서버 재시작 시 모두 휘발 — 데모 한정.
try:
    rd.ping()
except Exception as _e:
    try:
        import fakeredis  # type: ignore
        rd = fakeredis.FakeRedis(decode_responses=True)
        import logging
        logging.getLogger(__name__).warning(
            f"[Redis] {REDIS_HOST}:{REDIS_PORT} 접근 실패({_e!s}) — fakeredis in-memory fallback. "
            f"세션·인증코드는 서버 재시작 시 휘발됩니다."
        )
    except ImportError:
        # fakeredis 미설치면 그대로 원본 client 유지 (redis_get 등이 RedisError 잡음)
        pass

# ── 상수 ────────────────────────────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS   = 5    # 로그인 실패 잠금 기준
LOGIN_LOCKOUT_SEC    = 900  # 15분 잠금
MAX_VERIFY_ATTEMPTS  = 5    # 인증코드 실패 잠금 기준
VERIFY_CODE_TTL      = 180  # 인증코드 유효 3분
CONFIRMED_TTL        = 300  # 인증 완료 표시 유효 5분
SESSION_TTL          = 3600 # 세션 1시간
EMAIL_RATE_LIMIT_SEC = 60   # 동일 이메일 재발송 최소 간격

# ── 비밀번호 정책 ──────────────────────────────────────────────────────────
import re

PASSWORD_MIN_LEN = 8

def validate_password(password: str) -> None:
    """최소 8자, 영문+숫자 혼용 강제"""
    if len(password) < PASSWORD_MIN_LEN:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="비밀번호는 영문과 숫자를 포함해야 합니다.")

# ── Redis 안전 헬퍼 ────────────────────────────────────────────────────────
def redis_get(key: str) -> str | None:
    """Redis 장애 시 None 반환, 요청 차단 안 함"""
    try:
        return rd.get(key)
    except redis.RedisError:
        return None

def redis_setex(key: str, ttl: int, value: str) -> bool:
    try:
        rd.setex(key, ttl, value)
        return True
    except redis.RedisError:
        return False

def redis_incr_with_expire(key: str, ttl: int) -> int:
    """카운터 증가 + TTL 설정 (원자적 처리)"""
    try:
        pipe = rd.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = pipe.execute()
        return results[0]
    except redis.RedisError:
        return 0

def redis_delete(*keys: str) -> None:
    try:
        rd.delete(*keys)
    except redis.RedisError:
        pass

# ── 헬퍼 함수 ──────────────────────────────────────────────────────────────
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def secure_compare(a: str, b: str) -> bool:
    """타이밍 어택 방지용 상수 시간 문자열 비교"""
    return hmac.compare_digest(a.encode(), b.encode())

def get_client_ip(request: Request) -> str:
    """프록시 환경 대응 IP 추출"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# ── 세션 의존성 ────────────────────────────────────────────────────────────
def get_current_user(session_token: str = Header(None)) -> str:
    if not session_token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    email = redis_get(f"session:{session_token}")
    if not email:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해주세요.")
    return email

# ── 엔드포인트 ─────────────────────────────────────────────────────────────

@router.get("/session")
def get_session(session_token: str = Header(None), db: Session = Depends(get_db)):
    """현재 세션 상태 반환 — Front_v2 부트스트랩용.

    토큰 없거나 만료 시: 200 + {nickname: None, is_logged_in: False} (404 가 아님).
    유효 토큰: 200 + {nickname, email, is_logged_in: True}.
    """
    if not session_token:
        return {"nickname": None, "email": None, "is_logged_in": False}
    email = redis_get(f"session:{session_token}")
    if not email:
        return {"nickname": None, "email": None, "is_logged_in": False}
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"nickname": None, "email": None, "is_logged_in": False}
    return {
        "nickname": user.nickname,
        "email": user.email,
        "is_logged_in": True,
    }


@router.post("/check-email")
def check_email_duplicate(
    email: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """이메일 중복 검사 및 인증번호 발송"""
    # 1. 동일 이메일 재발송 Rate limit (60초 이내 재발송 차단)
    if redis_get(f"email_sent:{email}"):
        raise HTTPException(status_code=429, detail="잠시 후 다시 시도해주세요. (1분 제한)")

    # 2. IP 기반 Rate limit (분당 10회)
    ip = get_client_ip(request)
    ip_count = redis_incr_with_expire(f"rate:check_email:{ip}", 60)
    if ip_count > 10:
        raise HTTPException(status_code=429, detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요.")

    # 3. 중복 검사 — 계정 존재 노출 최소화
    #    (이미 가입된 경우에도 "발송됐습니다"처럼 보이도록 처리하되,
    #     실제 이메일은 발송하지 않음 → 사용자 열거 방지)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        code = str(random.randint(100000, 999999))
        if not redis_setex(f"verify:{email}", VERIFY_CODE_TTL, code):
            raise HTTPException(status_code=503, detail="서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        redis_setex(f"email_sent:{email}", EMAIL_RATE_LIMIT_SEC, "1")
        # 실패 카운터 초기화
        redis_delete(f"verify_fail:{email}")

        try:
            send_verification_email(email, code)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"메일 발송 실패: {str(e)}")

    # user가 있어도 없는 척 동일 응답 반환
    return {"message": "인증 코드가 이메일로 발송되었습니다."}


@router.post("/verify-code")
def verify_email_code(data: EmailVerification):
    """인증번호 확인 — 실패 횟수 초과 시 잠금"""
    # 실패 횟수 확인
    fail_key = f"verify_fail:{data.email}"
    fail_count = int(redis_get(fail_key) or "0")
    if fail_count >= MAX_VERIFY_ATTEMPTS:
        raise HTTPException(status_code=429, detail="인증 시도 횟수를 초과했습니다. 인증코드를 재발송 받아주세요.")

    saved_code = redis_get(f"verify:{data.email}")
    if not saved_code or not secure_compare(saved_code, data.code):
        redis_incr_with_expire(fail_key, VERIFY_CODE_TTL)
        raise HTTPException(status_code=400, detail="인증번호가 틀렸거나 만료되었습니다.")

    # 인증 성공: 코드 즉시 삭제(재사용 방지), 확인 상태 저장
    redis_delete(f"verify:{data.email}", fail_key)
    redis_setex(f"confirmed:{data.email}", CONFIRMED_TTL, "true")
    return {"message": "이메일 인증 성공"}


@router.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """최종 회원가입"""
    # 1. 비밀번호 정책 검증
    validate_password(user_data.password)

    # 2. 이메일 인증 여부
    if not redis_get(f"confirmed:{user_data.email}"):
        raise HTTPException(status_code=400, detail="이메일 인증이 필요합니다.")

    # 3. 닉네임 길이/형식 검증
    if not (2 <= len(user_data.nickname) <= 20):
        raise HTTPException(status_code=400, detail="닉네임은 2~20자 사이여야 합니다.")
    if not re.match(r"^[가-힣a-zA-Z0-9_]+$", user_data.nickname):
        raise HTTPException(status_code=400, detail="닉네임에 허용되지 않는 문자가 포함되어 있습니다.")

    # 4. 닉네임·이메일 중복 최종 확인
    if db.query(User).filter(User.nickname == user_data.nickname).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다.")
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")

    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        nickname=user_data.nickname,
    )
    db.add(new_user)
    db.commit()

    redis_delete(f"confirmed:{user_data.email}")
    return {"message": "회원가입이 완료되었습니다."}


@router.post("/login")
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    """로그인 — IP + 계정 이중 잠금"""
    ip = get_client_ip(request)
    ip_lock_key      = f"login_fail_ip:{ip}"
    account_lock_key = f"login_fail_account:{data.email}"

    # IP 잠금 확인
    if int(redis_get(ip_lock_key) or "0") >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="로그인 시도 횟수를 초과했습니다. 15분 후 다시 시도해주세요.")

    # 계정 잠금 확인
    if int(redis_get(account_lock_key) or "0") >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="계정이 일시적으로 잠겼습니다. 15분 후 다시 시도해주세요.")

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        redis_incr_with_expire(ip_lock_key, LOGIN_LOCKOUT_SEC)
        redis_incr_with_expire(account_lock_key, LOGIN_LOCKOUT_SEC)
        # 존재 여부를 노출하지 않는 통일된 메시지
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다.")

    # 성공 시 잠금 카운터 초기화
    redis_delete(ip_lock_key, account_lock_key)

    session_token = str(uuid.uuid4())
    if not redis_setex(f"session:{session_token}", SESSION_TTL, user.email):
        raise HTTPException(status_code=503, detail="서버 오류가 발생했습니다.")

    return {"session_token": session_token, "nickname": user.nickname, "user_id": user.user_id}


@router.post("/logout")
def logout(session_token: str = Header(None)):
    """명시적 로그아웃"""
    if session_token:
        redis_delete(f"session:{session_token}")
    return {"message": "로그아웃되었습니다."}


@router.post("/reset-password")
def reset_password(
    data: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_email: str = Depends(get_current_user),
):
    validate_password(data.new_password)

    user = db.query(User).filter(User.email == current_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=403,
            detail="현재 비밀번호가 일치하지 않습니다. 이메일 인증을 진행해주세요.",
        )

    user.hashed_password = get_password_hash(data.new_password)
    db.commit()

    # 비밀번호 변경 후 전체 세션 무효화
    _invalidate_all_sessions(current_email)
    return {"message": "비밀번호가 성공적으로 변경되었습니다. 다시 로그인해주세요."}


@router.post("/reset-password-via-email")
def reset_password_via_email(
    data: PasswordResetEmailRequest,
    db: Session = Depends(get_db),
):
    validate_password(data.new_password)

    if not redis_get(f"confirmed:{data.email}"):
        raise HTTPException(status_code=400, detail="이메일 인증이 완료되지 않았습니다.")

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # 존재하지 않는 계정이어도 동일 메시지 반환 (열거 방지)
        raise HTTPException(status_code=400, detail="이메일 인증이 완료되지 않았습니다.")

    user.hashed_password = get_password_hash(data.new_password)
    db.commit()

    redis_delete(f"confirmed:{data.email}")
    _invalidate_all_sessions(data.email)
    return {"message": "비밀번호가 재설정되었습니다. 다시 로그인해주세요."}


# ── 내부 유틸 ──────────────────────────────────────────────────────────────
def _invalidate_all_sessions(email: str) -> None:
    """해당 이메일의 모든 세션 토큰 무효화.
    
    현재 구현은 scan 기반 — 세션 수가 많아지면 성능 이슈 있음.
    프로덕션에서는 "user:{email}:sessions" 셋에 토큰을 모아두고
    일괄 삭제하는 방식을 권장.
    """
    try:
        cursor = 0
        while True:
            cursor, keys = rd.scan(cursor, match="session:*", count=100)
            for key in keys:
                if redis_get(key) == email:
                    redis_delete(key)
            if cursor == 0:
                break
    except redis.RedisError:
        pass  # 실패해도 비밀번호 변경 자체는 성공 처리

@router.post("/set-password")
def set_password(
    data: SetPasswordRequest,
    db: Session = Depends(get_db),
    current_email: str = Depends(get_current_user),
):
    """소셜 전용 계정의 최초 비밀번호 설정 (hashed_password가 None인 경우만 허용)"""
    validate_password(data.new_password)

    user = db.query(User).filter(User.email == current_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # 이미 비밀번호가 있는 계정은 이 엔드포인트 사용 불가
    # → reset-password 엔드포인트를 사용해야 함
    if user.hashed_password is not None:
        raise HTTPException(status_code=400, detail="이미 비밀번호가 설정된 계정입니다.")

    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "비밀번호가 설정되었습니다."}