"""
seed_personas.py
================
User_Scenarios.md 4 페르소나의 가상 계정 + 데이터(코호트·관심종목·보유종목)를
8000 인증 서버 API 로 생성한다. 스크린샷 데모용.

이메일 인증은 auth Redis 에 `confirmed:{email}` 키를 직접 넣어 우회한다
(개발 환경 한정 — 운영에서는 절대 사용 금지).

실행: python Back/db/scripts/seed_personas.py
사전조건: 8000 백엔드 + auth Redis 기동.
"""
from __future__ import annotations

import sys
import requests
import redis

API = "http://localhost:8000"
PW = "Capstone1!"

AUTH_REDIS = dict(
    host="100.67.30.5", port=6379, db=0,
    password="change_this_auth_password_123!",
    socket_connect_timeout=5, socket_timeout=5, decode_responses=True,
)

# ── 페르소나 정의 ────────────────────────────────────────────────────────────
PERSONAS = [
    {
        "email": "kimjiwoo@example.com", "nickname": "김지우", "cohort": "conservative",
        "watchlist": [("035420", "default"), ("035720", "default")],
        "holdings": [],
    },
    {
        "email": "parkseojun@example.com", "nickname": "박서준", "cohort": "value",
        "watchlist": [
            ("005930", "반도체 후보"), ("000660", "반도체 후보"),
            ("005490", "가치주"), ("051910", "가치주"),
        ],
        "holdings": [],
    },
    {
        "email": "leehaeun@example.com", "nickname": "이하은", "cohort": "growth",
        "watchlist": [("035900", "관심"), ("058970", "관심")],
        "holdings": [
            # (ticker, quantity, avg_price)  — 현재가 대비 손익 섞이게 설정
            ("005930", 30, 210000),    # 삼성전자  현재 226,000 → +7.6%
            ("000660", 5, 1150000),    # SK하이닉스 현재 1,293,000 → +12.4%
            ("035420", 20, 235000),    # NAVER    현재 220,000 → -6.4%
            ("035720", 100, 42000),    # 카카오    현재 48,400 → +15.2%
            ("051910", 8, 430000),     # LG화학   현재 407,500 → -5.2%
            ("005380", 10, 560000),    # 현대차    현재 556,000 → -0.7%
        ],
    },
    {
        "email": "jeongminho@example.com", "nickname": "정민호", "cohort": None,  # balanced
        "watchlist": [("145020", "default"), ("207940", "default")],
        "holdings": [
            ("058970", 200, 22000),    # 엠로      현재 28,600 → +30%
            ("145020", 10, 240000),    # 휴젤      현재 263,000 → +9.6%
            ("035900", 50, 58000),     # JYP Ent. 현재 64,500 → +11.2%
            ("207940", 3, 1400000),    # 삼성바이오 현재 1,473,000 → +5.2%
            ("068270", 15, 215000),    # 셀트리온  현재 204,000 → -5.1%
        ],
    },
]


def seed_one(rd: redis.Redis, p: dict) -> None:
    email, nick = p["email"], p["nickname"]
    print(f"\n── {nick} ({email}) ──")

    # 1) 이메일 인증 우회
    rd.setex(f"confirmed:{email}", 600, "true")

    # 2) 회원가입 (이미 있으면 통과)
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "nickname": nick, "password": PW})
    if r.status_code == 200:
        print("  [회원가입] 완료")
    elif "이미" in r.text:
        print("  [회원가입] 기존 계정 — 건너뜀")
    else:
        print(f"  [회원가입] 실패 {r.status_code}: {r.text}")

    # 3) 로그인
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PW})
    if r.status_code != 200:
        print(f"  [로그인] 실패 {r.status_code}: {r.text}")
        return
    token = r.json()["session_token"]
    H = {"session-token": token}
    print(f"  [로그인] OK  token={token[:8]}…")

    # 4) 코호트
    r = requests.put(f"{API}/users/me/cohort", headers=H, json={"cohort": p["cohort"]})
    print(f"  [코호트] {p['cohort'] or 'balanced'} → {r.status_code}")

    # 5) 관심종목
    for ticker, group in p["watchlist"]:
        r = requests.post(f"{API}/users/me/watchlist", headers=H,
                          json={"ticker": ticker, "group_name": group})
        ok = "OK" if r.status_code in (200, 201) else f"{r.status_code} {r.text[:40]}"
        print(f"  [관심] {ticker} ({group}) → {ok}")

    # 6) 보유종목
    for ticker, qty, avg in p["holdings"]:
        r = requests.post(f"{API}/users/me/portfolio/holdings", headers=H,
                          json={"ticker": ticker, "quantity": qty, "avg_price": avg})
        ok = "OK" if r.status_code in (200, 201) else f"{r.status_code} {r.text[:40]}"
        print(f"  [보유] {ticker} x{qty} @{avg:,} → {ok}")


def main() -> int:
    try:
        rd = redis.Redis(**AUTH_REDIS)
        rd.ping()
    except Exception as e:
        print(f"[ERR] auth Redis 연결 실패: {e}")
        return 1
    try:
        requests.get(f"{API}/", timeout=3)
    except Exception as e:
        print(f"[ERR] 8000 백엔드 응답 없음: {e}")
        return 1

    for p in PERSONAS:
        seed_one(rd, p)

    print("\n[done] 4 페르소나 시딩 완료. 로그인 정보:")
    for p in PERSONAS:
        print(f"  {p['nickname']:6s} {p['email']:28s} / {PW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
