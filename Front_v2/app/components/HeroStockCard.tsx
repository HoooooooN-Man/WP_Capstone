import { memo } from 'react';
import { useNavigate } from 'react-router-dom';
import StockLogo from './StockLogo';
import ScoreBadge from './ScoreBadge';

/**
 * HeroStockCard — 추천 페이지 상단 Top-3 히어로 카드
 *
 * 리디자인(Frontend_Redesign_Plan P0-3): 50행 동일 리스트의 벽 → "오늘 꼭 볼 것" 3종목을
 * 큰 카드로 분리해 시각 위계를 만든다.
 */
interface HeroStockCardProps {
  rank: number;
  ticker: string;
  name: string;
  sector?: string;
  price: number;
  changePercent: number;
  signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  score: number;
  tier: 'A' | 'B' | 'C' | 'D';
  headline?: string;
}

const SIGNAL: Record<string, { bg: string; text: string; icon: string }> = {
  BUY:   { bg: 'var(--buy-bg)',   text: 'var(--buy-text)',   icon: '▲' },
  HOLD:  { bg: 'var(--hold-bg)',  text: 'var(--hold-text)',  icon: '◆' },
  SELL:  { bg: 'var(--sell-bg)',  text: 'var(--sell-text)',  icon: '▼' },
  WATCH: { bg: 'var(--watch-bg)', text: 'var(--watch-text)', icon: '○' },
};

function HeroStockCard({
  rank, ticker, name, sector, price, changePercent, signal, score, tier, headline,
}: HeroStockCardProps) {
  const navigate = useNavigate();
  const sg = SIGNAL[signal] ?? SIGNAL.WATCH;
  const up = (changePercent ?? 0) >= 0;

  return (
    <button
      onClick={() => navigate(`/stocks/${ticker}`)}
      className="flex-1 min-w-0 text-left rounded-2xl p-5 transition-all duration-150 cursor-pointer
        shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:shadow-[0_10px_28px_rgba(0,0,0,0.10)] hover:-translate-y-[3px]"
      style={{
        backgroundColor: 'var(--bg-elev-1)',
        border: '1px solid var(--border)',
      }}
    >
      {/* 순위 + 신호 */}
      <div className="flex items-center justify-between mb-4">
        <span
          className="flex items-center justify-center rounded-lg tabular-nums w-[26px] h-[26px] wp-t-base font-extrabold"
          style={{
            backgroundColor: rank === 1 ? 'var(--accent-blue)' : 'var(--bg-elev-2)',
            color: rank === 1 ? '#FFFFFF' : 'var(--text-secondary)',
          }}
        >
          {rank}
        </span>
        <span
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 wp-t-sm font-bold"
          style={{ backgroundColor: sg.bg, color: sg.text }}
        >
          <span className="wp-t-2xs">{sg.icon}</span>{signal}
        </span>
      </div>

      {/* 로고 + 점수 */}
      <div className="flex items-center justify-between mb-3">
        <StockLogo ticker={ticker} name={name} size={52} />
        <ScoreBadge score={score} tier={tier} size="lg" />
      </div>

      {/* 종목명 */}
      <div className="wp-t-xl font-extrabold text-[var(--text-primary)] truncate">
        {name}
      </div>
      <div className="wp-t-sm text-[var(--text-tertiary)] mt-0.5">
        {ticker}{sector ? ` · ${sector}` : ''}
      </div>

      {/* 가격 */}
      <div className="flex items-baseline gap-2 mt-3">
        <span className="tabular-nums wp-t-2xl font-extrabold text-[var(--text-primary)]">
          {Number.isFinite(price) ? price.toLocaleString('ko-KR') : '—'}
        </span>
        <span
          className="tabular-nums wp-t-base font-bold"
          style={{ color: up ? 'var(--color-up)' : 'var(--color-down)' }}
        >
          {up ? '+' : ''}{(changePercent ?? 0).toFixed(2)}%
        </span>
      </div>

      {/* 헤드라인 */}
      {headline && (
        <div
          className="mt-3 pt-3 wp-t-sm text-[var(--text-secondary)] line-clamp-2"
          style={{ borderTop: '1px solid var(--border)' }}
        >
          {headline}
        </div>
      )}
    </button>
  );
}

export default memo(HeroStockCard);
