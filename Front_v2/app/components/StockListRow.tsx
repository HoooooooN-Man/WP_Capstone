import { memo } from 'react';
import { useNavigate } from 'react-router-dom';
import StarRating from './StarRating';
import StockLogo from './StockLogo';
import ScoreBadge from './ScoreBadge';
import { getReturnColor } from '../utils/format';

interface StockListRowProps {
  rank: number;
  ticker: string;
  name: string;
  sector?: string;
  marketCapLabel?: string;     // 예: "시총 542조"
  price: number;
  changePercent: number;
  signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  starRating: number;
  score: number;
  tier: 'A' | 'B' | 'C' | 'D';
  cumulativeReturn?: number;
  headline?: string;
  // FE 평가 #6 — headline 부재 시 finance 한 줄 폴백 (왜 추천됐는지)
  per?: number;
  pbr?: number;
  roe?: number;
  revGrowthYoy?: number;
  dividendYield?: number;
}

/**
 * StockListRow — PRD §3.17 / §4.1 와이드 리스트
 *
 * 6 영역 가로 stack:
 *   [32px 순위] [40px 로고] [flex 종목정보] [140px 신호&점수] [120px 가격] [100px 누적수익]
 *
 * 리디자인(Frontend_Redesign_Plan P0): 종목 로고(이니셜 원형 폴백)로 시각 텍스처 추가.
 */
function StockListRow({
  rank,
  ticker,
  name,
  sector,
  marketCapLabel,
  price,
  changePercent,
  signal,
  starRating,
  score,
  tier,
  cumulativeReturn,
  headline,
  per,
  pbr,
  roe,
  revGrowthYoy,
  dividendYield,
}: StockListRowProps) {
  // FE 평가 #6 — headline 없을 때 finance 한 줄 폴백.
  // 우선순위: 1) 매출성장 우수 2) 저PER 가치 3) 고ROE 4) 고배당 5) 저PBR 자산주
  const fallbackReason: string | null = (() => {
    if (revGrowthYoy != null && revGrowthYoy >= 15)
      return `매출 성장 +${revGrowthYoy.toFixed(0)}% — 성장세 우량`;
    if (per != null && per > 0 && per < 10)
      return `PER ${per.toFixed(1)}배 — 저평가 가치주`;
    if (roe != null && roe >= 15)
      return `ROE ${roe.toFixed(1)}% — 자기자본 수익 우량`;
    if (dividendYield != null && dividendYield >= 3)
      return `배당수익률 ${dividendYield.toFixed(2)}% — 인컴 매력`;
    if (pbr != null && pbr > 0 && pbr < 0.8)
      return `PBR ${pbr.toFixed(2)}배 — 자산주`;
    return null;
  })();
  const subText = headline || fallbackReason;
  const navigate = useNavigate();

  const formatPrice = (p: number | null | undefined) => {
    if (p == null || !Number.isFinite(p)) return '—';
    return p.toLocaleString('ko-KR');
  };
  const formatPercent = (p: number | null | undefined) => {
    if (p == null || !Number.isFinite(p)) return '0.00%';
    return `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`;
  };

  const signalColors: Record<string, { bg: string; text: string; icon: string }> = {
    BUY:   { bg: 'var(--buy-bg)',   text: 'var(--buy-text)',   icon: '▲' },
    HOLD:  { bg: 'var(--hold-bg)',  text: 'var(--hold-text)',  icon: '◆' },
    SELL:  { bg: 'var(--sell-bg)',  text: 'var(--sell-text)',  icon: '▼' },
    WATCH: { bg: 'var(--watch-bg)', text: 'var(--watch-text)', icon: '○' },
  };

  const sg = signalColors[signal] || signalColors.WATCH;
  const isPositive = changePercent >= 0;
  const isReturnPositive = (cumulativeReturn ?? 0) >= 0;

  const truncatedName = name.length > 12 ? `${name.slice(0, 12)}…` : name;

  return (
    <button
      type="button"
      aria-label={`${name} 상세 보기`}
      className="w-full text-left flex items-center gap-4 px-5 py-4 transition-colors duration-150 ease-out cursor-pointer border-b relative bg-[var(--bg-base)] hover:bg-[var(--bg-elev-1)]"
      style={{
        minHeight: '100px',
        borderColor: 'var(--border)',
        // P2-11 좌측 5px 신호 색 띠
        borderLeft: `5px solid ${sg.text}`,
      }}
      onClick={() => navigate(`/stocks/${ticker}`)}
    >
      {/* 1. 순위 — 32px */}
      <div className="tabular-nums flex-shrink-0 text-center w-8 wp-t-lg font-bold text-[var(--text-tertiary)]">
        {rank}
      </div>

      {/* 2. 종목 로고 — 40px */}
      <StockLogo ticker={ticker} name={name} size={40} />

      {/* 3. 종목 정보 — flex */}
      <div className="flex-1 min-w-0 space-y-1">
        <div className="wp-t-xl font-bold text-[var(--text-primary)] truncate">
          {truncatedName}
        </div>
        <div className="wp-t-base text-[var(--text-tertiary)]">
          {ticker}
          {sector && ` · ${sector}`}
          {marketCapLabel && ` · ${marketCapLabel}`}
        </div>
        {subText && (
          <div className="wp-t-md text-[var(--text-secondary)] truncate">
            {subText}
          </div>
        )}
      </div>

      {/* 3. 신호 & 점수 — 140px */}
      <div className="flex-shrink-0 space-y-1.5 w-[140px]">
        <div className="flex items-center gap-1.5">
          <div
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 wp-t-base font-bold"
            style={{ backgroundColor: sg.bg, color: sg.text, minHeight: '24px' }}
          >
            <span className="wp-t-xs">{sg.icon}</span>
            {signal}
          </div>
          <StarRating rating={starRating} size="sm" showNumber={false} />
        </div>
        <ScoreBadge score={score} tier={tier} size="sm" />
      </div>

      {/* 4. 가격 — 120px, 우측 정렬 */}
      <div className="flex-shrink-0 text-right w-[120px]">
        <div className="tabular-nums wp-t-xl font-bold text-[var(--text-primary)]">
          {formatPrice(price)}
        </div>
        {/* B60: 변동률 0 = 거래 발생했지만 호가 변동 없음 (소형주 패턴). 회색 "변동없음" 표시. */}
        {changePercent === 0 ? (
          <div className="tabular-nums wp-t-base text-[var(--text-tertiary)]">
            변동없음
          </div>
        ) : (
          <div
            className="tabular-nums wp-t-base font-bold"
            style={{ color: isPositive ? 'var(--color-up)' : 'var(--color-down)' }}
          >
            {formatPercent(changePercent)}
          </div>
        )}
      </div>

      {/* 5. 최근 30일 수익률 — 100px, 우측 정렬 (모델 월별 rebal 가정 정합) */}
      <div className="flex-shrink-0 text-right w-[100px]">
        <div className="wp-t-xs text-[var(--text-tertiary)]">최근 30일</div>
        {cumulativeReturn != null && Number.isFinite(cumulativeReturn) ? (
          <div
            className="tabular-nums wp-t-xl font-bold"
            style={{ color: getReturnColor(cumulativeReturn) }}
          >
            {isReturnPositive ? '+' : ''}
            {cumulativeReturn.toFixed(1)}%
          </div>
        ) : (
          <div className="text-[var(--text-tertiary)]">—</div>
        )}
      </div>
    </button>
  );
}

// 와이드 리스트 50행 — 부모(RecommendPage) 리렌더 시 prop 동일 행은 재렌더 스킵
export default memo(StockListRow);
