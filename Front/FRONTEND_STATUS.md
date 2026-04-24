# WP_Capstone 프론트엔드 구현 현황

> 최종 업데이트: 2026-04-24  
> 빌드 상태: ✅ 정상 (vite build 통과)  
> 배포 라우트: `http://localhost:5173`

---

## 목차

1. [기술 스택](#기술-스택)
2. [라우트 및 페이지](#라우트-및-페이지)
3. [컴포넌트](#컴포넌트)
4. [Pinia 스토어](#pinia-스토어)
5. [API 클라이언트](#api-클라이언트)
6. [Composables](#composables)
7. [전역 기능](#전역-기능)
8. [미구현 / 추후 과제](#미구현--추후-과제)

---

## 기술 스택

| 분류 | 라이브러리 | 버전 |
|------|-----------|------|
| **프레임워크** | Vue 3 (Composition API, `<script setup>`) | ^3.5 |
| **빌드** | Vite | ^8.0 |
| **라우팅** | Vue Router | ^5.0 |
| **상태관리** | Pinia | ^3.0 |
| **HTTP** | Axios | ^1.15 |
| **CSS** | Tailwind CSS v4 (`@tailwindcss/vite`) | ^4.2 |
| **차트** | Chart.js + vue-chartjs | ^4.5 |
| **금융 차트** | chartjs-chart-financial (캔들) | ^0.2 |
| **트리맵** | chartjs-chart-treemap | ^3.1 |
| **날짜** | date-fns + chartjs-adapter-date-fns | ^4.1 |
| **유틸리티** | @vueuse/core | ^14.2 |
| **SWR 캐시** | @tanstack/vue-query | ^5.100 |
| **가상 스크롤** | vue-virtual-scroller | ^2.0.0-beta |
| **PWA** | vite-plugin-pwa (Workbox) | ^1.2 |
| **타입** | TypeScript + vue-tsc | ~5.9 |

---

## 라우트 및 페이지

### 인증

| 라우트 | 파일 | 상태 | 설명 |
|--------|------|------|------|
| `/login` | `page/auth/Login.vue` | ✅ 완료 | 이메일/비밀번호 로그인, authStore 연동, redirect 지원 |
| `/register` | `page/auth/Register.vue` | ✅ 완료 | 이메일 인증코드 발송→확인→회원가입 3단계 |
| `/reset-password` | `page/auth/ResetPassword.vue` | ✅ 완료 | 이메일 인증 후 비밀번호 변경 2단계 |

### 메인 분석

| 라우트 | 파일 | 상태 | 설명 |
|--------|------|------|------|
| `/` | `views/HomeView.vue` | ✅ 완료 | 시장 레짐 배너, 요약 카드, 섹터 표, 종목 미리보기 |
| `/stocks` | `views/StocksView.vue` | ✅ 완료 | ML 점수 기반 종목 추천 (필터/테이블/요약 3컬럼) |
| `/stocks/:ticker` | `views/StockDetailView.vue` | ✅ 완료 | 캔들차트, 거래량, ML점수 추이, 재무 레이더/테이블 |
| `/screener` | `views/ScreenerView.vue` | ✅ 완료 | ML+재무 복합 필터, 프리셋 저장, 결과 테이블 |
| `/compare` | `views/CompareView.vue` | ✅ 완료 | 최대 5종목 ML점수/재무 비교, URL 상태 동기화 |
| `/portfolio` | `views/PortfolioView.vue` | ✅ 완료 | 성장형/안정형 포트폴리오, 백테스트 요약·차트 |
| `/sectors` | `views/SectorsView.vue` | ✅ 완료 | 섹터 트리맵 (Chart.js), 클릭 시 /stocks 이동 |

### 커뮤니티 · 소셜

| 라우트 | 파일 | 상태 | 설명 |
|--------|------|------|------|
| `/board` | `page/board/Boardview.vue` | ✅ 완료 | 종목별 게시판 (팀원 구현, board.db 연동) |
| `/ranking` | `views/RankingView.vue` | ✅ 완료 | AI 추천 / 커뮤니티 인기 / 급상승 Top 20 |
| `/news` | `views/NewsView.vue` | ✅ 완료 | FinBERT 감성 피드, 전체/긍정/중립/부정 탭 |
| `/user/:nickname` | `views/UserProfileView.vue` | ✅ 완료 | 공개 프로필, 관심종목, 팔로우 |

### 개인화

| 라우트 | 파일 | 상태 | 설명 |
|--------|------|------|------|
| `/my` | `views/MyPageView.vue` | ✅ 완료 | 내 포트폴리오 수익률 추적기 (localStorage), 설정 |
| `/backtest` | `views/BacktestView.vue` | ✅ 완료 | 조건 커스텀 백테스트 시뮬레이터, 결과 차트 |

### 미연결 (라우터 미포함)

| 파일 | 비고 |
|------|------|
| `views/LoginView.vue` | 스텁 — `page/auth/Login.vue`로 대체됨 |
| `views/RegisterView.vue` | 스텁 — `page/auth/Register.vue`로 대체됨 |
| `views/RecommendView.vue` | `/recommend` → `/stocks` redirect 처리됨 |
| `page/main/news/NewsDetailModal.vue` | 팀원 작성, 아직 미연결 |
| `page/main/test.vue` | 팀원 테스트 파일 |

---

## 컴포넌트

### 공통 (`components/common/`)

| 파일 | 설명 |
|------|------|
| `TierBadge.vue` | A/B/C/D 등급 원형 뱃지 |
| `GlobalSearch.vue` | Cmd+K 글로벌 검색 모달 (Teleport, 키보드 탐색, 최근 검색어) |
| `OfflineBanner.vue` | 오프라인 감지 시 상단 배너 |

### 홈 (`components/home/`)

| 파일 | 설명 |
|------|------|
| `MarketRegimeBanner.vue` | 시장 레짐 상태 배너 (Bull/Bear/Neutral) |
| `SummaryCards.vue` | KOSPI/KOSDAQ/환율/공포지수 요약 카드 |
| `SectorSummaryTable.vue` | 섹터별 평균 ML점수 요약 테이블 |
| `TopStocksPreview.vue` | 오늘의 상위 종목 미리보기 |

### 종목 추천 (`components/stocks/`)

| 파일 | 설명 |
|------|------|
| `FilterPanel.vue` | 날짜/모델버전/섹터/점수/Tier 필터 |
| `StockTable.vue` | 종목 테이블 (100개↑ 가상 스크롤 자동 전환) |
| `StockRow.vue` | 테이블 행 단위 컴포넌트 |
| `SummaryPanel.vue` | Tier 도넛 차트 + 점수 히스토그램 |
| `TierDonut.vue` | Chart.js 도넛 차트 |
| `ScoreHistogram.vue` | Chart.js 막대 차트 |
| `ProbDrawer.vue` | 종목 확률 상세 드로어 |

### 종목 상세 (`components/stockDetail/`)

| 파일 | 설명 |
|------|------|
| `StockHeader.vue` | 종목 기본 정보 헤더 |
| `CandleChart.vue` | chartjs-chart-financial 캔들스틱 |
| `VolumeChart.vue` | 거래량 막대 차트 |
| `ScoreHistoryChart.vue` | ML 점수 추이 라인 차트 |
| `FinanceSummary.vue` | 재무 레이더 차트 |
| `FinanceTable.vue` | 재무 지표 상세 테이블 |

### 스크리너 (`components/screener/`)

| 파일 | 설명 |
|------|------|
| `FilterSidebar.vue` | ML/재무 복합 필터 사이드바, 프리셋 저장 |
| `ScreenerTable.vue` | 복합 점수 툴팁, 최고값 하이라이트 |

### 포트폴리오 (`components/portfolio/`)

| 파일 | 설명 |
|------|------|
| `StrategyTabs.vue` | 성장형/안정형 전략 탭 |
| `PortfolioCardGrid.vue` | 포트폴리오 종목 카드 그리드 |
| `StrategyExplanation.vue` | 전략 설명 텍스트 |
| `BacktestSummaryTable.vue` | 백테스트 요약 지표 테이블 |
| `BacktestMonthlyChart.vue` | 월별 수익률 차트 |

### 비교 (`components/compare/`)

| 파일 | 설명 |
|------|------|
| `StockSearchSelector.vue` | 종목 검색 + 선택 태그 |
| `ScoreHistoryChart.vue` | 다중 종목 ML점수 추이 비교 |
| `StockSummaryCards.vue` | 종목별 요약 카드 |
| `FinanceCompareTable.vue` | 재무 지표 비교 테이블 (최고값 강조) |

---

## Pinia 스토어

| 파일 | 주요 상태 | 설명 |
|------|----------|------|
| `auth.js` | `token`, `nickname`, `isLoggedIn` | 로그인 상태, session_token (localStorage 동기화) |
| `theme.js` | `isDark` | 다크/라이트 모드, localStorage 저장 |
| `market.js` | `versions`, `dates` | 모델 버전/날짜 목록 |
| `stocks.js` | `items`, `filters`, `tierCounts` | 종목 추천 데이터 및 필터 |
| `screener.js` | `items`, `filters`, `presets` | 스크리너 필터, localStorage 프리셋 |
| `portfolio.js` | `growthItems`, `stableItems`, `backtestSummary` | 포트폴리오 및 백테스트 데이터 |
| `watchlist.js` | `watchlist` | 관심종목 목록 |
| `notifications.js` | `unread`, `list` | 알림 상태, 5분 폴링, Notification API |

---

## API 클라이언트

| 파일 | 베이스 URL | 설명 |
|------|-----------|------|
| `axios.js` | `http://localhost:8001` | ML 분석 서버 (Axios 인스턴스, 세션 인터셉터) |
| `dbapi.js` | `http://100.67.18.188:8000` | 인증/커뮤니티 서버 |
| `stocks.js` | — | 종목 추천, 검색, 비교 API |
| `chart.js` | — | 캔들/거래량 차트 데이터 API |
| `finance.js` | — | 재무 지표 API |
| `screener.js` | — | 스크리너 필터 API |
| `portfolio.js` | — | 포트폴리오/백테스트 API |
| `auth.js` | — | 인증 관련 API (로그인/회원가입) |

---

## Composables

| 파일 | 설명 |
|------|------|
| `useStockQuery.js` | @tanstack/vue-query 기반 SWR 캐시 래퍼 |

### useStockQuery 목록

| 함수 | staleTime | 설명 |
|------|----------|------|
| `useVersions()` | 5분 | 모델 버전 목록 |
| `useSectors()` | 5분 | 섹터 요약 데이터 |
| `useRecommendations(params)` | 60초 | 종목 추천 (Redis TTL 맞춤) |
| `useStockDetail(ticker)` | 30초 | 종목 상세 |
| `useNewsFeed(params)` | 30초 | 뉴스 피드 |
| `useRanking(limit)` | 60초 | 랭킹 데이터 |

---

## 전역 기능

| 기능 | 구현 위치 | 설명 |
|------|----------|------|
| **다크 모드** | `stores/theme.js` + `style.css` | Tailwind dark: + CSS 변수 오버라이드, localStorage 저장 |
| **글로벌 검색** | `GlobalSearch.vue` + `App.vue` | Cmd+K / Ctrl+K 단축키, 최근 검색 5개 |
| **모바일 레이아웃** | `App.vue` | 하단 탭 바 + 슬라이드 사이드바 + Bottom Sheet 필터 |
| **URL 상태 동기화** | `StocksView`, `ScreenerView`, `PortfolioView` | `watchEffect` + `router.replace()` |
| **Push 알림** | `stores/notifications.js` + `App.vue` | Notification API, 5분 폴링, 벨 아이콘 배지 |
| **PWA** | `vite.config.ts` | Service Worker, manifest, 오프라인 배너 |
| **가상 스크롤** | `StockTable.vue` | 100개↑ 자동 RecycleScroller 전환 |
| **SWR 캐시** | `main.ts` + `useStockQuery.js` | QueryClient 전역 등록 |

---

## 미구현 / 추후 과제

### 프론트엔드

| 항목 | 우선순위 | 설명 |
|------|---------|------|
| 실시간 가격 연동 (WebSocket) | P1 | 증권사 OpenAPI WebSocket, 실시간 시세 깜빡임 |
| AI 종목 리포트 자동 생성 | P2 | LLM API 연동, SSE 스트리밍 타이핑 효과 |
| 개인화 추천 (사용자별 모델) | P2 | 행동 로그 기반 맞춤 추천, user_preference |
| 투자 아이디어 공유 게시판 | P2 | 태그 시스템, 종목 멘션 자동 링크 |
| `page/main/news/NewsDetailModal.vue` | — | 팀원 작성 파일, 아직 미연결 |

### 백엔드 의존

| API 엔드포인트 | 용도 | 비고 |
|--------------|------|------|
| `POST /portfolio/backtest` | 백테스트 시뮬레이터 | 미구현 시 모의 데이터 표시 |
| `GET /news/feed` | 뉴스 감성 피드 | 미구현 시 모의 데이터 표시 |
| `GET /stocks/sectors/summary` | 섹터 히트맵 | 미구현 시 모의 데이터 표시 |
| `GET /stocks/rising` | 급상승 종목 | 미구현 시 AI 랭킹으로 대체 |
| `GET /users/notifications` | Push 알림 폴링 | 미구현 시 무응답 |
| `GET /users/:nickname/public` | 유저 프로필 | 미구현 시 모의 데이터 표시 |
| `GET /stocks/:ticker/price` | 현재가 조회 | 마이페이지 수익률 계산 |

---

## 실행 방법

```bash
cd WP_Capstone-main/Front

# 의존성 설치
npm install --legacy-peer-deps

# 개발 서버
npm run dev        # http://localhost:5173

# 빌드
npm run build

# 빌드 미리보기
npm run preview
```

### 환경 변수 (`.env.local`)

```env
VITE_API_BASE_URL=http://localhost:8001   # ML 분석 FastAPI
VITE_DB_API_URL=http://localhost:8000    # 인증/커뮤니티 FastAPI
```

---

## 디렉터리 구조

```
Front/src/
├── api/              # Axios 클라이언트 모듈
│   ├── axios.js      # 공통 인스턴스 (포트 8001)
│   ├── dbapi.js      # 인증 서버 인스턴스 (포트 8000)
│   ├── stocks.js     # 종목 API
│   ├── chart.js      # 차트 데이터 API
│   ├── finance.js    # 재무 API
│   ├── screener.js   # 스크리너 API
│   ├── portfolio.js  # 포트폴리오 API
│   └── auth.js       # 인증 API
│
├── stores/           # Pinia 스토어
│   ├── auth.js       # 인증 상태
│   ├── theme.js      # 다크 모드
│   ├── market.js     # 시장 데이터
│   ├── stocks.js     # 종목 추천
│   ├── screener.js   # 스크리너
│   ├── portfolio.js  # 포트폴리오
│   ├── watchlist.js  # 관심종목
│   └── notifications.js  # 알림
│
├── composables/
│   └── useStockQuery.js  # SWR 캐시 래퍼
│
├── components/
│   ├── common/       # 공통 컴포넌트
│   ├── home/         # 홈 대시보드
│   ├── stocks/       # 종목 추천
│   ├── stockDetail/  # 종목 상세
│   ├── screener/     # 스크리너
│   ├── portfolio/    # 포트폴리오
│   └── compare/      # 종목 비교
│
├── views/            # 페이지 뷰 (신규 구현)
│   ├── HomeView.vue
│   ├── StocksView.vue
│   ├── StockDetailView.vue
│   ├── ScreenerView.vue
│   ├── PortfolioView.vue
│   ├── CompareView.vue
│   ├── SectorsView.vue
│   ├── RankingView.vue
│   ├── NewsView.vue
│   ├── BacktestView.vue
│   ├── MyPageView.vue
│   └── UserProfileView.vue
│
├── page/             # 팀원 구현 페이지
│   ├── auth/         # 로그인/회원가입/비밀번호찾기
│   ├── board/        # 커뮤니티 게시판
│   └── main/         # 기존 홈뷰 등
│
├── router/
│   └── index.ts      # Vue Router 설정
│
├── App.vue           # 루트 컴포넌트 (Nav, 다크모드, GlobalSearch)
├── main.ts           # 진입점 (Pinia, VueQuery, PWA, VirtualScroller)
└── style.css         # 전역 스타일 (CSS 변수, 다크모드 오버라이드)
```
