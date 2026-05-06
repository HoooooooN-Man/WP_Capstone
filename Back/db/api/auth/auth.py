from fastapi import Header, APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from dotenv import load_dotenv
import redis
import random
import os

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

# 공통으로 사용할 세션 체크 함수
def get_current_user(session_token: str = Header(None)):
    if not session_token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    # Redis에서 토큰으로 이메일 조회
    email = rd.get(f"session:{session_token}")
    if not email:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해주세요.")
    
    return email # 이후 로직에서 이 이메일을 사용함

# --- API 엔드포인트 ---

@router.post("/check-email")
def check_email_duplicate(email: str, db: Session = Depends(get_db)):
    """이메일 중복 검사 및 인증번호 발송"""
    user = db.query(User).filter(User.email == email).first()
    if user:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")
    
    # 6자리 인증번호 생성 및 Redis 저장 (3분 만료)
    code = str(random.randint(100000, 999999))
    rd.setex(f"verify:{email}", 180, code)
    
    # 실제 서비스라면 여기서 이메일 발송 로직 호출 (생략)
    success = send_verification_email(email, code)
    if not success:
        raise HTTPException(status_code=500, detail="메일 발송에 실패했습니다.")
        
    return {"message": "인증 코드가 실제 이메일로 발송되었습니다."}

@router.post("/verify-code")
def verify_email_code(data: EmailVerification):
    """인증번호 확인"""
    saved_code = rd.get(f"verify:{data.email}")
    if not saved_code or saved_code != data.code:
        raise HTTPException(status_code=400, detail="인증번호가 틀렸거나 만료되었습니다.")
    
    # 인증 완료 표시를 Redis에 5분간 저장 (회원가입 버튼 클릭 전까지 유효)
    rd.setex(f"confirmed:{data.email}", 300, "true")
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

@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    """로그인 및 세션 생성"""
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다.")

    # Redis 세션 생성 (UUID)
    import uuid
    session_token = str(uuid.uuid4())
    rd.setex(f"session:{session_token}", 3600, user.email) # 1시간 유지

    return {"session_token": session_token, "nickname": user.nickname}

@router.post("/reset-password")
def reset_password(
    data: PasswordResetRequest, 
    db: Session = Depends(get_db),
    current_email: str = Depends(get_current_user) # 로그인 된 상태 기준
):
    user = db.query(User).filter(User.email == current_email).first()
    
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
    data: PasswordResetEmailRequest, # 이메일, 인증코드, 새비밀번호 포함
    db: Session = Depends(get_db)
):
    # 1. 이메일 인증 코드 확인 (Redis)
    is_confirmed = rd.get(f"confirmed:{data.email}")
    if not is_confirmed:
        raise HTTPException(status_code=400, detail="이메일 인증이 완료되지 않았습니다.")

    # 2. 새 비밀번호 업데이트
    user = db.query(User).filter(User.email == data.email).first()
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    
    rd.delete(f"confirmed:{data.email}")
    return {"message": "이메일 인증을 통해 비밀번호가 재설정되었습니다."}