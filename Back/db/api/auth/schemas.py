"""
api/auth/schemas.py
===================
인증 도메인 Pydantic 스키마 (v2).

이전 구현은 v1 의 `validator(..., allow_reuse=True)` 데코레이터를 사용했는데,
프로젝트 내 다른 라우터(`users.py`, `notes.py`)는 이미 v2 스타일
(`class Config: from_attributes = True`, `Field(..., pattern=...)`) 를 쓰고 있다.
v1/v2 혼용은 deprecation 경고와 v2.7+ pin 시 import 오류의 원인 — 본 파일을 v2 로 통일.
"""
from __future__ import annotations

import re
from pydantic import BaseModel, EmailStr, Field, field_validator

# Password 정책: 영문·숫자·특수문자 포함 8~24자
_PW_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,24}$")


def _validate_password(v: str) -> str:
    if not _PW_RE.match(v or ""):
        raise ValueError("비밀번호는 영문, 숫자, 특수문자를 포함한 8~24자여야 합니다.")
    return v


# 1. 회원가입 요청
class UserCreate(BaseModel):
    email: EmailStr
    nickname: str = Field(..., min_length=2, max_length=20)
    password: str = Field(...)

    @field_validator("password")
    @classmethod
    def _v_password(cls, v: str) -> str:
        return _validate_password(v)


# 2. 로그인 요청
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# 3. 이메일 인증번호 확인
class EmailVerification(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=10)


# 4. 현재 비밀번호로 재설정 (로그인 상태)
class PasswordResetRequest(BaseModel):
    current_password: str
    new_password: str = Field(...)

    @field_validator("new_password")
    @classmethod
    def _v_new_password(cls, v: str) -> str:
        return _validate_password(v)


# 5. 이메일 인증을 통한 재설정 (비번 까먹었을 때)
class PasswordResetEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=10)
    new_password: str = Field(...)

    @field_validator("new_password")
    @classmethod
    def _v_new_password(cls, v: str) -> str:
        return _validate_password(v)
