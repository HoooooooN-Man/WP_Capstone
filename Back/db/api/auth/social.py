from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import httpx
import uuid
import os

from db.database import get_db
from db.models import User, SocialAccount
from .auth import rd  # 이전 답변에서 설정한 Redis 객체

router = APIRouter(prefix="/auth", tags=["social_auth"])

# --- 각 플랫폼별 유저 정보 취득 URL ---
USER_INFO_URLS = {
    "google": "https://www.googleapis.com/oauth2/v3/userinfo",
    "kakao": "https://kapi.kakao.com/v2/user/me",
    "naver": "https://openapi.naver.com/v1/nid/me"
}

async def get_social_user_data(provider: str, access_token: str):
    """Access Token을 이용해 각 플랫폼에서 유저 정보를 가져옴"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get(USER_INFO_URLS[provider], headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail=f"{provider} 인증 실패")
        
        data = response.json()
        
        # 플랫폼별 데이터 구조 표준화
        if provider == "google":
            return {"social_id": data["sub"], "email": data["email"], "nickname": data.get("name")}
        elif provider == "kakao":
            return {
                "social_id": str(data["id"]),
                "email": data["kakao_account"].get("email"),
                "nickname": data["properties"].get("nickname")
            }
        elif provider == "naver":
            res = data.get("response")
            return {"social_id": res["id"], "email": res["email"], "nickname": res.get("nickname")}

@router.post("/login/{provider}")
async def social_login(provider: str, access_token: str, db: Session = Depends(get_db)):
    """
    프론트엔드에서 Access Token을 받아 처리하는 엔드포인트
    (프론트에서 각 소셜 SDK를 쓰거나 Redirect를 직접 처리한 후 토큰만 넘겨주는 방식)
    """
    # 1. 소셜 플랫폼에서 유저 정보 가져오기
    user_data = await get_social_user_data(provider, access_token)
    email = user_data["email"]
    social_id = user_data["social_id"]
    
    if not email:
        raise HTTPException(status_code=400, detail="소셜 계정의 이메일 정보를 가져올 수 없습니다.")

    # 2. 소셜 연동 여부 확인
    social_account = db.query(SocialAccount).filter(
        SocialAccount.provider == provider, 
        SocialAccount.social_id == social_id
    ).first()

    target_user = None

    if social_account:
        # 이미 연동된 계정이 있는 경우
        target_user = social_account.user
    else:
        # 3. [Case A] 기존 이메일 유저가 있는지 확인
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            # 기존 이메일 유저에게 소셜 계정 새로 연동
            new_social = SocialAccount(
                user_id=existing_user.user_id,
                provider=provider,
                social_id=social_id
            )
            db.add(new_social)
            db.commit()
            target_user = existing_user
        else:
            # 4. 신규 유저 생성
            # 닉네임 중복 방지를 위해 소셜 닉네임 뒤에 랜덤 숫자 부여 등의 처리 권장
            new_user = User(
                email=email,
                nickname=f"{user_data['nickname']}_{str(uuid.uuid4())[:4]}",
                is_verified=True, # 소셜 이메일은 인증된 것으로 간주
                is_active=True
            )
            db.add(new_user)
            db.flush()
            
            new_social = SocialAccount(
                user_id=new_user.user_id,
                provider=provider,
                social_id=social_id
            )
            db.add(new_social)
            db.commit()
            target_user = new_user

    # 5. 비밀번호 설정 여부 체크 (강제 유도용)
    needs_password = target_user.hashed_password is None

    # 6. Redis 세션 생성
    session_token = str(uuid.uuid4())
    rd.setex(f"session:{session_token}", 3600, target_user.email)

    return {
        "session_token": session_token,
        "nickname": target_user.nickname,
        "needs_password": needs_password, # 프론트에서 이 값을 보고 비번 설정 모달을 띄움
        "message": "로그인 성공"
    }