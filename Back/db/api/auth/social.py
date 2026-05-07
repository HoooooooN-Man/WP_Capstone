# auth/social.py — 보안 강화 버전

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
import uuid
import os

from db.database import get_db
from db.models import User, SocialAccount
from .auth import rd, redis_setex, redis_incr_with_expire, get_client_ip, SESSION_TTL

router = APIRouter(prefix="/auth", tags=["social_auth"])

# ── 허용 provider 화이트리스트 ─────────────────────────────────────────────
ALLOWED_PROVIDERS = {"google", "kakao", "naver"}

USER_INFO_URLS = {
    "google": "https://www.googleapis.com/oauth2/v3/userinfo",
    "kakao":  "https://kapi.kakao.com/v2/user/me",
    "naver":  "https://openapi.naver.com/v1/nid/me",
}

SOCIAL_LOGIN_RATE_LIMIT = 20   # IP당 분당 최대 요청
HTTPX_TIMEOUT          = 10.0  # 외부 API 타임아웃(초)

# ── 요청 바디 스키마 (토큰을 쿼리스트링 → Body로 이동) ──────────────────
class SocialLoginRequest(BaseModel):
    access_token: str

# ── 소셜 플랫폼별 유저 정보 파싱 ──────────────────────────────────────────
def _parse_google(data: dict) -> dict:
    social_id = data.get("sub")
    email     = data.get("email")
    if not social_id or not email:
        raise HTTPException(status_code=401, detail="Google 인증 응답이 올바르지 않습니다.")
    return {"social_id": str(social_id), "email": email, "nickname": data.get("name")}

def _parse_kakao(data: dict) -> dict:
    social_id = data.get("id")
    account   = data.get("kakao_account") or {}
    props     = data.get("properties") or {}
    if not social_id:
        raise HTTPException(status_code=401, detail="Kakao 인증 응답이 올바르지 않습니다.")
    return {
        "social_id": str(social_id),
        "email":     account.get("email"),
        "nickname":  props.get("nickname"),
    }

def _parse_naver(data: dict) -> dict:
    res = data.get("response") or {}
    social_id = res.get("id")
    email     = res.get("email")
    if not social_id or not email:
        raise HTTPException(status_code=401, detail="Naver 인증 응답이 올바르지 않습니다.")
    return {"social_id": str(social_id), "email": email, "nickname": res.get("nickname")}

_PARSERS = {"google": _parse_google, "kakao": _parse_kakao, "naver": _parse_naver}

async def get_social_user_data(provider: str, access_token: str) -> dict:
    """Access Token으로 소셜 플랫폼에서 유저 정보를 가져오고 표준화"""
    try:
        async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
            headers  = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(USER_INFO_URLS[provider], headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"{provider} 서버 응답 시간이 초과됐습니다.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail=f"{provider} 서버에 연결할 수 없습니다.")

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail=f"유효하지 않은 {provider} 액세스 토큰입니다.")
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail=f"{provider} 인증에 실패했습니다.")

    return _PARSERS[provider](response.json())

# ── 닉네임 생성 헬퍼 ──────────────────────────────────────────────────────
def _make_unique_nickname(base: str | None, db: Session) -> str:
    """
    소셜 닉네임을 기반으로 DB 중복 없는 닉네임을 생성.
    base가 None이면 "user"를 기본값으로 사용.
    최대 10회 재시도 후 실패 시 예외.
    """
    base = (base or "user")[:12].strip() or "user"
    # 허용 문자 정제 (한글·영문·숫자만)
    import re
    base = re.sub(r"[^가-힣a-zA-Z0-9]", "", base) or "user"

    for _ in range(10):
        candidate = f"{base}_{uuid.uuid4().hex[:6]}"  # hex 6자리 = 16^6 ≈ 1600만 가지
        if not db.query(User).filter(User.nickname == candidate).first():
            return candidate

    raise HTTPException(status_code=500, detail="닉네임 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")

# ── 엔드포인트 ────────────────────────────────────────────────────────────
@router.post("/login/{provider}")
async def social_login(
    provider: str,
    body: SocialLoginRequest,     # ✅ 토큰을 Body로 수신 (URL 노출 차단)
    request: Request,
    db: Session = Depends(get_db),
):
    # 1. provider 화이트리스트 검증
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail="지원하지 않는 소셜 로그인 제공자입니다.")

    # 2. IP Rate limiting
    ip       = get_client_ip(request)
    ip_count = redis_incr_with_expire(f"rate:social_login:{ip}", 60)
    if ip_count > SOCIAL_LOGIN_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요.")

    # 3. 소셜 플랫폼에서 유저 정보 취득
    user_data = await get_social_user_data(provider, body.access_token)
    email     = user_data["email"]
    social_id = user_data["social_id"]

    if not email:
        raise HTTPException(status_code=400, detail="소셜 계정의 이메일 정보를 가져올 수 없습니다.")

    # 4. 소셜 계정 연동 여부 확인
    social_account = (
        db.query(SocialAccount)
        .filter(SocialAccount.provider == provider, SocialAccount.social_id == social_id)
        .first()
    )

    try:
        if social_account:
            # 이미 연동된 계정
            target_user = social_account.user

        else:
            existing_user = db.query(User).filter(User.email == email).first()

            if existing_user:
                # ✅ 기존 이메일 계정에 소셜 연동 — 자동 병합 대신 플래그만 반환
                #    프론트엔드에서 "기존 계정과 연동하시겠습니까?" 확인을 받은 후
                #    /auth/link/{provider} 엔드포인트를 별도 호출하도록 유도
                return {
                    "session_token": None,
                    "requires_link_confirmation": True,
                    "link_hint_token": _issue_link_hint(email, provider, social_id),
                    "message": "이미 가입된 이메일입니다. 기존 계정과 연동하려면 확인이 필요합니다.",
                }
            else:
                # 신규 유저 생성
                nickname  = _make_unique_nickname(user_data.get("nickname"), db)
                new_user  = User(
                    email=email,
                    nickname=nickname,
                    is_verified=True,
                    is_active=True,
                )
                db.add(new_user)
                db.flush()

                new_social = SocialAccount(
                    user_id=new_user.user_id,
                    provider=provider,
                    social_id=social_id,
                )
                db.add(new_social)
                db.commit()
                target_user = new_user

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="계정 처리 중 오류가 발생했습니다.")

    # 5. 세션 발급
    session_token = str(uuid.uuid4())
    if not redis_setex(f"session:{session_token}", SESSION_TTL, target_user.email):
        raise HTTPException(status_code=503, detail="세션 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")

    return {
        "session_token":  session_token,
        "nickname":       target_user.nickname,
        "needs_password": target_user.hashed_password is None,
        "message":        "로그인 성공",
    }


# ── 계정 연동 확인 엔드포인트 ─────────────────────────────────────────────
class LinkConfirmRequest(BaseModel):
    link_hint_token: str

@router.post("/link/{provider}")
async def confirm_social_link(
    provider: str,
    body: LinkConfirmRequest,
    db: Session = Depends(get_db),
):
    """
    프론트엔드에서 "기존 계정과 연동" 사용자 동의 후 호출.
    link_hint_token으로 Redis에 저장해 둔 연동 정보를 꺼내 처리.
    """
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail="지원하지 않는 제공자입니다.")

    raw = rd.get(f"link_hint:{body.link_hint_token}")
    if not raw:
        raise HTTPException(status_code=400, detail="연동 정보가 만료됐거나 올바르지 않습니다.")

    # "email|provider|social_id" 형식
    parts = raw.split("|")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="연동 정보가 올바르지 않습니다.")
    email, saved_provider, social_id = parts

    if saved_provider != provider:
        raise HTTPException(status_code=400, detail="제공자 정보가 일치하지 않습니다.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다.")

    try:
        new_social = SocialAccount(user_id=user.user_id, provider=provider, social_id=social_id)
        db.add(new_social)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="계정 연동 중 오류가 발생했습니다.")

    rd.delete(f"link_hint:{body.link_hint_token}")

    session_token = str(uuid.uuid4())
    if not redis_setex(f"session:{session_token}", SESSION_TTL, user.email):
        raise HTTPException(status_code=503, detail="세션 생성에 실패했습니다.")

    return {"session_token": session_token, "nickname": user.nickname, "message": "계정 연동 및 로그인 성공"}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────
def _issue_link_hint(email: str, provider: str, social_id: str) -> str:
    """
    연동 의사 확인을 위한 단기 토큰 발급 (5분 유효).
    실제 연동은 /link/{provider} 호출 시에만 수행.
    """
    token = uuid.uuid4().hex
    rd.setex(f"link_hint:{token}", 300, f"{email}|{provider}|{social_id}")
    return token