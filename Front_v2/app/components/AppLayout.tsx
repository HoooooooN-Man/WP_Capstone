import type { ReactNode } from 'react';
import ContextRail from './ContextRail';

interface AppLayoutProps {
  children: ReactNode;
  /** 본문 컨테이너 최대 폭(px). 'full' 이면 폭 제한 없음. 기본 1200 */
  maxWidth?: number | 'full';
  /** 우측 ContextRail 노출 여부(xl+ 에서만 실제 표시). 기본 true */
  rail?: boolean;
}

/**
 * AppLayout — 페이지 본문 컨테이너.
 *
 * 지속 크롬(헤더·시세띠·바텀나브·CommandPalette)은 Shell 이 책임지고,
 * 여기서는 본문 폭 제어 + 우측 ContextRail 만 담당한다.
 *
 * 레이아웃(데스크탑 xl+):
 *   [ main (maxWidth) ] [ ContextRail 320px ]   ← 가운데 정렬
 */
export default function AppLayout({ children, maxWidth = 1200, rail = true }: AppLayoutProps) {
  const mainMax = maxWidth === 'full' ? '100%' : `${maxWidth}px`;
  // rail 포함 시 바깥 컨테이너는 main + gap(24) + rail(320) 까지 허용
  const outerMax =
    rail && maxWidth !== 'full' ? `${maxWidth + 24 + 320}px` : mainMax;

  return (
    <div
      className="mx-auto flex justify-center gap-6 px-4 sm:px-6"
      style={{ maxWidth: outerMax }}
    >
      {/* 본문 — pb 는 모바일 BottomNav(56) / 데스크탑 MarketTickerBar(36) 클리어 */}
      <main
        className="flex-1 min-w-0 py-6 sm:py-8 pb-36 lg:pb-16"
        style={{ maxWidth: mainMax }}
      >
        {children}
      </main>

      {rail && (
        <aside className="hidden xl:block flex-shrink-0 py-6 sm:py-8" style={{ width: 320 }}>
          <div className="sticky" style={{ top: 16 }}>
            <ContextRail />
          </div>
        </aside>
      )}
    </div>
  );
}
