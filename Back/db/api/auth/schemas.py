from pydantic import BaseModel, EmailStr, Field, validator
import re

# 공통 비밀번호 검증 로직 (중복 방지를 위해 함수화 가능)
def password_validator(v):
    regex = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,24}$"
    if not re.match(regex, v):
        raise ValueError("비밀번호는 영문, 숫자, 특수문자를 포함한 8~24자여야 합니다.")
    return v

# 1. 회원가입 요청
class UserCreate(BaseModel):
    email: EmailStr
    nickname: str = Field(..., min_length=2, max_length=20)
    password: str = Field(...)
    
    _validate_password = validator("password", allow_reuse=True)(password_validator)

# 2. 로그인 요청
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# 3. 이메일 인증번호 확인
class EmailVerification(BaseModel):
    email: EmailStr
    code: str

# 4. 현재 비밀번호로 재설정 (로그인 상태)
class PasswordResetRequest(BaseModel):
    current_password: str
    new_password: str = Field(...)

    _validate_password = validator("new_password", allow_reuse=True)(password_validator)

# 5. 이메일 인증을 통한 재설정 (비번 까먹었을 때)
class PasswordResetEmailRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(...)

    _validate_password = validator("new_password", allow_reuse=True)(password_validator)