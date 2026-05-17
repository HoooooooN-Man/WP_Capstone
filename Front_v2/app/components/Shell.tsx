import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import AppHeader from './AppHeader';
import BottomNav from './BottomNav';
import MarketTickerBar from './MarketTickerBar';
import CommandPalette from './CommandPalette';
import { useSessionBootstrap } from '../api/client';

/**
 * Shell — 라우터 레벨 레이아웃 라우트.
 *
 * 헤더·하단 시세띠·모바일 바텀나브·전역 CommandPalette 같은 "지속 크롬"을
 * 라우트 전환과 무관하게 한 번만 마운트한다. 페이지 본문은 <Outlet/> 으로
 * 교체되며, 전환 중 lazy 청크 로드는 내부 Suspense 가 셸 안에서 처리한다.
 */
export default function Shell() {
  // H#27: 페이지 첫 진입 시 /auth/session 으로 cookie 세션 hydrate (legacy 토큰 모드에선 noop).
  useSessionBootstrap();
  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-base)' }}>
      <div className="hidden lg:block">
        <AppHeader variant="desktop" />
      </div>
      <div className="block lg:hidden">
        <AppHeader variant="mobile" />
      </div>

      <Suspense fallback={<ShellFallback />}>
        <Outlet />
      </Suspense>

      <MarketTickerBar />

      <div className="block lg:hidden fixed bottom-0 left-0 right-0 z-50">
        <BottomNav />
      </div>

      {/* 전역 Ctrl/Cmd+K 종목 검색 */}
      <CommandPalette />
    </div>
  );
}

function ShellFallback() {
  return (
    <div className="mx-auto px-4 sm:px-6 py-8" style={{ maxWidth: 1200 }}>
      <div className="wp-skeleton rounded-xl" style={{ height: 420 }} />
    </div>
  );
}
