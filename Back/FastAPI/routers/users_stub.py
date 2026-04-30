"""
routers/users_stub.py
=====================
사용자/알림 stub 라우터.

본 프로젝트는 **로그인 없이 운영**되는 단일 FastAPI 모드를 기본으로 한다.
이 stub은 프론트엔드의 알림 폴링·프로필 조회가 콘솔 에러를 내지 않도록
빈 응답을 안전하게 반환한다.

(전체 사용자 기능은 `Back/db/server.py`(PostgreSQL+Redis) 별도 서버 참조)
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users-stub"])


@router.get("/notifications", summary="알림 목록 stub (빈 응답)")
def list_notifications(unread: bool = False, limit: int = 10):
    return {"items": [], "total": 0, "unread_count": 0}


@router.post("/notifications/read-all", summary="알림 모두 읽음 stub")
def read_all_notifications():
    return {"ok": True, "updated": 0}


@router.get("/{nickname}/public", summary="공개 프로필 stub")
def get_public_profile(nickname: str):
    return {
        "nickname":      nickname,
        "follower_cnt":  0,
        "following_cnt": 0,
        "is_following":  False,
        "bio":           "",
        "joined_at":     None,
    }


@router.post("/{nickname}/follow", summary="팔로우 stub (로그인 필요)")
def follow(nickname: str):
    return {"ok": False, "reason": "auth-disabled"}


@router.delete("/{nickname}/follow", summary="언팔로우 stub (로그인 필요)")
def unfollow(nickname: str):
    return {"ok": False, "reason": "auth-disabled"}
