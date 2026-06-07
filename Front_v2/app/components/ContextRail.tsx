import { useNavigate } from 'react-router-dom';
import { Star, Clock } from 'lucide-react';
import Card from './Card';
import SectionHeader from './SectionHeader';
import StockLogo from './StockLogo';
import { useMarketRegime, useWatchlist, useRecommendations, type StockItem, type WatchlistItem } from '../api/hooks';
import { useSession } from '../api/client';
import { loadRecentStocks } from '../utils/recent';
import { formatPrice, formatPercent } from '../utils/format';

/**
 * ContextRail — 데스크탑(xl+) 우측 고정 사이드바.
 * 토스 레퍼런스의 우측 패널 대응: 화면을 떠나지 않고 시장·관심·최근 맥락을 유지한다.
 *   상단 = 오늘의 시장 점수
 *   중단 = 관심종목 미니리스트 (로그인 필요)
 *   하단 = 최근 본 종목 (localStorage)
 */
export default function ContextRail() {
  const navigate = useNavigate();
  const { isLoggedIn } = useSession();

  const { data: regime } = useMarketRegime();
  const { data: wlApi } = useWatchlist();
  const { data: allStocksApi } = useRecommendations({ top_k: 0 });

  // 시장 점수
  const score = regime?.market_score ?? null;
  const scoreState =
    score == null ? '—' : score >= 70 ? '과열' : score >= 45 ? '중립' : '침체';
  const scoreColor =
    score == null
      ? 'var(--text-tertiary)'
      : score >= 70
        ? 'var(--color-up)'
        : score >= 45
          ? 'var(--text-primary)'
          : 'var(--color-down)';

  // 관심종목 — watchlist ticker 를 추천 전 종목 데이터로 enrich
  const allMap = new Map<string, StockItem>(
    (allStocksApi?.items ?? []).map((s: StockItem) => [s.ticker, s]),
  );
  const watchlist: StockItem[] = (wlApi?.items ?? [])
    .map((w: WatchlistItem) => allMap.get(w.ticker))
    .filter((s): s is StockItem => Boolean(s))
    .slice(0, 5);

  // 최근 본 종목
  const recent = loadRecentStocks().slice(0, 5);

  return (
    <div className="space-y-4">
      {/* 오늘의 시장 점수 */}
      <Card>
        <SectionHeader title="오늘의 시장" />
        <div className="flex items-end gap-3 mt-3">
          <span
            className="tabular-nums"
            style={{ fontSize: '40px', fontWeight: 800, lineHeight: 1, color: scoreColor }}
          >
            {score != null ? score.toFixed(1) : '—'}
          </span>
          <span
            className="px-2 py-0.5 rounded"
            style={{
              fontSize: '12px',
              fontWeight: 700,
              backgroundColor: 'var(--bg-elev-2)',
              color: 'var(--text-secondary)',
              marginBottom: '4px',
            }}
          >
            {scoreState}
          </span>
        </div>
        {/* 0–100 mini bar */}
        <div
          className="mt-3 rounded-full overflow-hidden"
          style={{ height: '6px', backgroundColor: 'var(--bg-elev-2)' }}
        >
          <div
            style={{
              width: `${Math.max(0, Math.min(100, score ?? 0))}%`,
              height: '100%',
              backgroundColor: scoreColor,
            }}
          />
        </div>
        {regime?.message && (
          <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: 10, lineHeight: '17px' }}>
            {regime.message}
          </p>
        )}
      </Card>

      {/* 관심종목 */}
      <Card padded={false}>
        <div className="px-5 pt-5 pb-3">
          <SectionHeader
            title="관심종목"
            right={
              <button
                onClick={() => navigate('/watchlist')}
                style={{ fontSize: '12px', color: 'var(--accent-blue)', fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer' }}
              >
                전체
              </button>
            }
          />
        </div>
        {!isLoggedIn ? (
          <button
            onClick={() => navigate('/login')}
            className="w-full text-left px-5 py-4"
            style={{ fontSize: '13px', color: 'var(--text-tertiary)', background: 'none', border: 'none', borderTop: '1px solid var(--border-default)', cursor: 'pointer' }}
          >
            로그인하면 관심종목을 여기서 바로 확인할 수 있습니다.
          </button>
        ) : watchlist.length === 0 ? (
          <div
            className="px-5 py-4"
            style={{ fontSize: '13px', color: 'var(--text-tertiary)', borderTop: '1px solid var(--border-default)' }}
          >
            아직 관심종목이 없습니다.
          </div>
        ) : (
          watchlist.map((s) => (
            <button
              key={s.ticker}
              onClick={() => navigate(`/stocks/${s.ticker}`)}
              className="w-full flex items-center gap-2.5 px-5 py-2.5 text-left"
              style={{ background: 'none', border: 'none', borderTop: '1px solid var(--border-default)', cursor: 'pointer' }}
            >
              <Star size={13} style={{ color: '#FFB800', fill: '#FFB800', flexShrink: 0 }} />
              <StockLogo ticker={s.ticker} name={s.name} size={28} />
              <div className="flex-1 min-w-0">
                <div
                  style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                >
                  {s.name ?? s.ticker}
                </div>
                <div className="tabular-nums" style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                  {formatPrice(s.close)}
                </div>
              </div>
              <div
                className="tabular-nums"
                style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  color: (s.change_pct ?? 0) >= 0 ? 'var(--color-up)' : 'var(--color-down)',
                }}
              >
                {formatPercent(s.change_pct ?? 0)}
              </div>
            </button>
          ))
        )}
      </Card>

      {/* 최근 본 종목 */}
      {recent.length > 0 && (
        <Card padded={false}>
          <div className="px-5 pt-5 pb-3">
            <SectionHeader title="최근 본 종목" />
          </div>
          {recent.map((s) => (
            <button
              key={s.ticker}
              onClick={() => navigate(`/stocks/${s.ticker}`)}
              className="w-full flex items-center gap-2.5 px-5 py-2.5 text-left"
              style={{ background: 'none', border: 'none', borderTop: '1px solid var(--border-default)', cursor: 'pointer' }}
            >
              <Clock size={13} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
              <StockLogo ticker={s.ticker} name={s.name} size={28} />
              <div className="flex-1 min-w-0">
                <div
                  style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                >
                  {s.name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{s.ticker}</div>
              </div>
            </button>
          ))}
        </Card>
      )}
    </div>
  );
}
