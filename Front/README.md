# Front — Vue 3 프론트엔드

WP_Capstone 주식 추천 시스템의 프론트엔드입니다.

## 기술 스택

- **Vue 3** + Composition API (`<script setup>`)
- **TypeScript**
- **Vite** (빌드 도구)
- **Pinia** (상태 관리)
- **Vue Router** (라우팅)
- **Axios** (API 통신)

## 실행

```bash
npm install
npm run dev      # 개발 서버 (http://localhost:5173)
npm run build    # 프로덕션 빌드
npm run preview  # 빌드 결과 미리보기
```

## 페이지 구조

```
src/
├── page/
│   ├── auth/
│   │   ├── Login.vue          # 로그인
│   │   ├── Register.vue       # 회원가입 (이메일 인증 포함)
│   │   └── ResetPassword.vue  # 비밀번호 재설정
│   └── main/
│       ├── HomeView.vue       # 메인 홈 (추천 종목 + 시장 현황)
│       └── news/
│           └── NewsDetailModal.vue  # 뉴스 상세 모달
├── views/
│   ├── HomeView.vue           # 홈 뷰 (구버전 레이아웃)
│   ├── RecommendView.vue      # 종목 추천 목록
│   ├── StockDetailView.vue    # 종목 상세 (차트·재무·게시판)
│   ├── ScreenerView.vue       # 다중 조건 스크리너
│   └── CompareView.vue        # 종목 비교
├── api/
│   ├── index.ts               # FastAPI 추천 서버 연동 (포트 8001)
│   └── dbapi.js               # 인증·뉴스 서버 연동 (포트 8000)
├── stores/
│   └── auth.ts                # Pinia 인증 상태 (세션 토큰 관리)
└── router/
    └── index.ts               # Vue Router 라우트 정의
```

## API 연결

| 파일 | 연결 서버 | 포트 |
|------|-----------|------|
| `api/index.ts` | FastAPI 추천 서버 | 8001 |
| `api/dbapi.js` | 인증·뉴스 서버 | 8000 |
