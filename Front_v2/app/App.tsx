import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Shell from './components/Shell';

// 라우트 단위 코드 스플리팅 — 페이지별 청크로 분리해 초기 번들에서 제외
const RecommendPage = lazy(() => import('./pages/RecommendPage'));
const WinnerPage = lazy(() => import('./pages/WinnerPage'));
const SignalPage = lazy(() => import('./pages/SignalPage'));
const SearchPage = lazy(() => import('./pages/SearchPage'));
const NewsPage = lazy(() => import('./pages/NewsPage'));
const ScreenerPage = lazy(() => import('./pages/ScreenerPage'));
const SmartScorePage = lazy(() => import('./pages/SmartScorePage'));
const SectorsPage = lazy(() => import('./pages/SectorsPage'));
const StockDetailPage = lazy(() => import('./pages/StockDetailPage'));
const ComparePage = lazy(() => import('./pages/ComparePage'));
const WatchlistPage = lazy(() => import('./pages/WatchlistPage'));
const MyPage = lazy(() => import('./pages/MyPage'));
const MyPortfolioPage = lazy(() => import('./pages/MyPortfolioPage'));
const CohortPortfolioPage = lazy(() => import('./pages/CohortPortfolioPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));

export default function App() {
  return (
    <Suspense fallback={<div className="min-h-screen" style={{ backgroundColor: 'var(--bg-base)' }} />}>
      <Routes>
        {/* 지속 크롬(헤더·시세띠·바텀나브) 라우트 — 페이지는 Shell 내부 Outlet 으로 교체 */}
        <Route element={<Shell />}>
          <Route path="/" element={<Navigate to="/recommend" replace />} />

          {/* 추천·신호 (메인 네비 1) */}
          <Route path="/recommend" element={<RecommendPage />} />
          <Route path="/winner" element={<WinnerPage />} />
          <Route path="/signal" element={<SignalPage />} />

          {/* 검색 (메인 네비 2) */}
          <Route path="/search" element={<SearchPage />} />

          {/* 뉴스·발굴 (메인 네비 3) */}
          <Route path="/news" element={<NewsPage />} />
          <Route path="/screener" element={<ScreenerPage />} />
          <Route path="/scores" element={<SmartScorePage />} />
          <Route path="/sectors" element={<SectorsPage />} />

          {/* 종목 상세 + 비교 */}
          <Route path="/stocks/:ticker" element={<StockDetailPage />} />
          <Route path="/compare" element={<ComparePage />} />

          {/* 관심 (메인 네비 4) */}
          <Route path="/watchlist" element={<WatchlistPage />} />

          {/* 마이 (우상단 아바타) */}
          <Route path="/my" element={<MyPage />} />
          <Route path="/my/portfolio" element={<MyPortfolioPage />} />
          <Route path="/my/cohort-portfolio" element={<CohortPortfolioPage />} />

          {/* fallback */}
          <Route path="*" element={<Navigate to="/recommend" replace />} />
        </Route>

        {/* 인증 — 전체화면 레이아웃, Shell 없음 */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Routes>
    </Suspense>
  );
}
