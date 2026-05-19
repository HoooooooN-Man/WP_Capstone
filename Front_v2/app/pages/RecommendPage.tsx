import { useState, useMemo } from 'react';
import AppLayout from '../components/AppLayout';
import StockListRow from '../components/StockListRow';
import { RowSkeleton } from '../components/Skeleton';
import HeroStockCard from '../components/HeroStockCard';
import Dropdown from '../components/Dropdown';
import EmptyState from '../components/EmptyState';
import PageErrorState from '../components/PageErrorState';
import BottomDisclaimer from '../components/BottomDisclaimer';
import { useRecommendations, useMarketRegime, type StockItem } from '../api/hooks';

/**
 * RecommendPage — PRD §4.1 와이드 리스트 (1 칼럼 × 20행)
 *
 * StockListRow §3.17 사용. 카드 그리드 금지.
 * Cohort 옵션은 텍스트 라벨만 (이모지 금지 — PRD §3.17 아이콘 정책).
 */
export default function RecommendPage() {
  const [cohort, setCohort] = useState('balanced');
  const [diversify, setDiversify] = useState('correlation');
  const [topK, setTopK] = useState(50);
  const [signalFilter, setSignalFilter] = useState<string[]>([]);  // 빈 = 전체
  // P1-9 정렬
  const [sortBy, setSortBy] = useState<'score' | 'change_pct' | 'cumulative_return_pct'>('score');
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc');

  // 이모지 제거 — 텍스트 라벨만 (PRD 명시 금지)
  const cohortOptions = [
    { value: 'conservative', label: '보수형' },
    { value: 'balanced',     label: '균형'   },
    { value: 'growth',       label: '성장'   },
    { value: 'dividend',     label: '배당'   },
    { value: 'value',        label: '가치'   },
  ];

  const diversifyOptions = [
    { value: 'correlation', label: 'Correlation' },
    { value: 'sector',      label: 'Sector'      },
    { value: 'embedding',   label: 'Embedding'   },
    { value: 'none',        label: 'None'        },
  ];

  // 백엔드 연동
  const { data: marketRegime } = useMarketRegime();
  const { data: recommendations, isLoading, isError } = useRecommendations({
    cohort,
    diversify,
    top_k: topK,
  });

  // 필터 + 정렬 — 입력이 바뀔 때만 재계산 (memo 된 StockListRow 50행과 함께 작동)
  const stocks = useMemo(() => {
    const allStocks = recommendations?.items ?? [];
    const filtered = signalFilter.length === 0
      ? allStocks
      : allStocks.filter((s) => signalFilter.includes(s.signal_label ?? 'WATCH'));
    // 정렬 (안정성: null 은 최하위로)
    return [...filtered].sort((a, b) => {
      const va = a[sortBy] ?? -Infinity;
      const vb = b[sortBy] ?? -Infinity;
      return sortDir === 'desc' ? vb - va : va - vb;
    });
  }, [recommendations, signalFilter, sortBy, sortDir]);

  const toggleSignal = (sig: string) => {
    setSignalFilter(prev => prev.includes(sig) ? prev.filter(s => s !== sig) : [...prev, sig]);
  };
  const toggleSort = (key: typeof sortBy) => {
    if (sortBy === key) setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    else { setSortBy(key); setSortDir('desc'); }
  };

  const handleLoadMore = () => {
    setTopK((prev) => prev + 20);
  };

  return (
    <AppLayout maxWidth={1200}>
        {/* 페이지 타이틀 */}
        <div className="mb-6">
          <h1 className="wp-t-3xl font-bold text-[var(--text-primary)]">
            오늘의 추천 종목
          </h1>
          <p className="wp-t-base text-[var(--text-secondary)] mt-1">
            AI 모델이 매일 분석한 상위 종목을 와이드 리스트로 확인하세요
          </p>
        </div>

        {/* 상단 컨트롤 바 — 슬림 */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6 px-5 py-3 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border)]">
          <div className="flex items-center gap-3">
            <span className="wp-t-sm text-[var(--text-tertiary)]">시장 점수</span>
            <span className="tabular-nums wp-t-2xl font-extrabold text-[var(--text-primary)]">
              {(marketRegime?.market_score ?? 50).toFixed(1)}
            </span>
            <span className="px-2 py-0.5 rounded wp-t-xs font-bold bg-[var(--bg-elev-2)] text-[var(--text-secondary)]">
              {(marketRegime?.market_score ?? 50) >= 70 ? '과열' :
               (marketRegime?.market_score ?? 50) >= 45 ? '중립' : '침체'}
            </span>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <Dropdown label="투자 성향" options={cohortOptions} value={cohort} onChange={setCohort} />
            <Dropdown label="다양화" options={diversifyOptions} value={diversify} onChange={setDiversify} />
          </div>
        </div>

        {/* P0-4 신호 필터 칩 */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <span className="wp-t-base text-[var(--text-secondary)] mr-2">신호</span>
          {[
            { value: 'BUY',   label: '매수', icon: '▲' },
            { value: 'HOLD',  label: '보유', icon: '◆' },
            { value: 'SELL',  label: '매도', icon: '▼' },
            { value: 'WATCH', label: '관망', icon: '○' },
          ].map(s => {
            const active = signalFilter.includes(s.value);
            return (
              <button
                key={s.value}
                onClick={() => toggleSignal(s.value)}
                className={`px-3 py-1.5 rounded-md transition-colors cursor-pointer wp-t-sm ${active ? 'font-bold' : 'font-normal'}`}
                // 신호별 색은 토큰명이 동적(--buy-bg 등)이라 인라인 유지
                style={{
                  backgroundColor: active ? `var(--${s.value.toLowerCase()}-bg)` : 'transparent',
                  color:           active ? `var(--${s.value.toLowerCase()}-text)` : 'var(--text-tertiary)',
                  border: `1px solid ${active ? `var(--${s.value.toLowerCase()}-text)` : 'var(--border)'}`,
                }}
              >
                <span className="mr-1">{s.icon}</span>
                {s.label}
              </button>
            );
          })}
          {signalFilter.length > 0 && (
            <button
              onClick={() => setSignalFilter([])}
              className="wp-t-sm text-[var(--text-tertiary)] bg-transparent border-none cursor-pointer underline"
            >
              전체 해제
            </button>
          )}

          {/* P1-9 정렬 토글 */}
          <span className="ml-6 wp-t-base text-[var(--text-secondary)]">정렬</span>
          {[
            { value: 'score' as const,                 label: '점수' },
            { value: 'change_pct' as const,            label: '등락률' },
            { value: 'cumulative_return_pct' as const, label: '최근 30일' },
          ].map(opt => {
            const active = sortBy === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => toggleSort(opt.value)}
                className={`wp-t-sm px-2 py-1 bg-transparent border-none cursor-pointer ${
                  active ? 'font-bold text-[var(--accent-blue)]' : 'font-normal text-[var(--text-tertiary)]'
                }`}
              >
                {opt.label}{active ? (sortDir === 'desc' ? ' ↓' : ' ↑') : ''}
              </button>
            );
          })}
        </div>

        {/* 메인 컨텐츠 */}
        {isLoading && <RowSkeleton count={8} />}

        {isError && <PageErrorState type="error" />}

        {!isLoading && !isError && stocks.length === 0 && (
          <div className="py-16">
            <EmptyState
              title="오늘은 추천 종목이 없습니다"
              description="선택하신 투자 성향에 맞는 종목을 찾을 수 없습니다."
              actionLabel="투자 성향 변경"
              onAction={() => setCohort('balanced')}
            />
          </div>
        )}

        {!isLoading && !isError && stocks.length > 0 && (
          <>
            {/* Top-3 히어로 */}
            <div className="flex flex-col sm:flex-row gap-4 mb-8">
              {stocks.slice(0, 3).map((stock: StockItem, idx: number) => (
                <HeroStockCard
                  key={`hero-${stock.ticker}-${idx}`}
                  rank={idx + 1}
                  ticker={stock.ticker}
                  name={stock.name ?? stock.ticker}
                  sector={stock.sector ?? undefined}
                  price={stock.close ?? 0}
                  changePercent={stock.change_pct ?? 0}
                  signal={stock.signal_label ?? 'WATCH'}
                  score={stock.score ?? 0}
                  tier={stock.tier ?? 'C'}
                  headline={stock.headline}
                />
              ))}
            </div>

            {/* 4위 이하 리스트 */}
            {stocks.length > 3 && (
              <div className="mb-2 wp-t-base font-bold text-[var(--text-secondary)]">
                전체 추천 ({stocks.length})
              </div>
            )}
            <div className="rounded-xl overflow-hidden border border-[var(--border)]">
              {stocks.slice(3).map((stock: StockItem, idx: number) => (
                <StockListRow
                  key={`${stock.ticker}-${idx}`}
                  rank={idx + 4}
                  ticker={stock.ticker}
                  name={stock.name ?? stock.ticker}
                  sector={stock.sector ?? undefined}
                  marketCapLabel={stock.market_cap_label ?? undefined}
                  price={stock.close ?? 0}
                  changePercent={stock.change_pct ?? 0}
                  signal={stock.signal_label ?? 'WATCH'}
                  starRating={stock.star_rating ?? 0}
                  score={stock.score ?? 0}
                  tier={stock.tier ?? 'C'}
                  cumulativeReturn={stock.cumulative_return_pct}
                  headline={stock.headline}
                  per={stock.per}
                  pbr={stock.pbr}
                  roe={stock.roe}
                  revGrowthYoy={stock.rev_growth_yoy}
                  dividendYield={stock.dividend_yield}
                />
              ))}
            </div>

            <div className="flex justify-center mt-8">
              <button
                onClick={handleLoadMore}
                className="px-8 py-3 rounded-full transition-colors duration-150 cursor-pointer
                  bg-[var(--bg-elev-1)] hover:bg-[var(--bg-elev-2)] border border-[var(--border)]
                  text-[var(--text-primary)] wp-t-base font-bold"
              >
                더보기 — 20개 더 보기
              </button>
            </div>
          </>
        )}

        <BottomDisclaimer />
    </AppLayout>
  );
}
