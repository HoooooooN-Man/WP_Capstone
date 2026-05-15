import { useState, useEffect } from 'react';
import AppLayout from '../components/AppLayout';
import RadarChart from '../components/RadarChart';
import ScoreBadge from '../components/ScoreBadge';
import StockLogo from '../components/StockLogo';
import SignalLabelChip from '../components/SignalLabelChip';
import StarRating from '../components/StarRating';
import { useRecommendations, useStockRadar, useStockFairValue, useStockDividend, type StockItem } from '../api/hooks';

interface ScoreRow {
  ticker: string;
  name: string;
  sector?: string;
  price: number;
  changePercent: number;
  signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  score: number;
  tier: 'A' | 'B' | 'C' | 'D';
  starRating: number;
  cumulativeReturn: number;
}

export default function SmartScorePage() {
  // 전 종목 점수 정렬 — API 우선, 실패 시 mock
  const { data: rec } = useRecommendations({ top_k: 0 });
  const apiList: ScoreRow[] | undefined = rec?.items?.map((it: StockItem) => ({
    ticker: it.ticker, name: it.name, sector: it.sector,
    price: it.close ?? 0, changePercent: it.change_pct ?? 0,
    signal: it.signal_label ?? 'WATCH',
    score: it.score ?? 0, tier: it.tier ?? 'C',
    starRating: it.star_rating ?? 0,
    cumulativeReturn: it.cumulative_return_pct ?? 0,
  }));
  const allStocks: ScoreRow[] = apiList ?? [];
  const [selectedTicker, setSelectedTicker] = useState<string>('');
  // API 로드 후 첫 종목 자동 선택
  useEffect(() => {
    if (!selectedTicker && allStocks.length > 0) setSelectedTicker(allStocks[0].ticker);
  }, [allStocks, selectedTicker]);
  const selectedStock = allStocks.find((s) => s.ticker === selectedTicker) ?? allStocks[0];

  // 선택된 종목의 5요인 레이더 + 적정주가 + 배당 (실데이터 sub-score)
  const { data: radar }     = useStockRadar(selectedTicker);
  const { data: fairValue } = useStockFairValue(selectedTicker);
  const { data: dividend }  = useStockDividend(selectedTicker);

  // API 로딩 전이면 allStocks 가 비어 selectedStock 이 undefined — 가드 (훅 호출 이후 early return)
  if (!selectedStock) {
    return (
      <AppLayout maxWidth={1280}>
        <h1 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '24px' }}>
          스마트스코어 분석
        </h1>
        <div style={{ fontSize: '14px', color: 'var(--text-tertiary)' }}>종목 데이터를 불러오는 중…</div>
      </AppLayout>
    );
  }

  // API radar 사용 — 데이터 없으면 모두 0
  const radarData = radar?.groups ?? { growth: 0, profitability: 0, safety: 0, monopoly: 0, cashflow: 0 };
  const sectorAvgData = radar?.sector_average;

  // 5요인 = PRD §3.3.2 진단 = backend radar API 직결
  const scoreBreakdown = {
    growth:        Math.round(radarData.growth ?? 0),
    profitability: Math.round(radarData.profitability ?? 0),
    safety:        Math.round(radarData.safety ?? 0),
    monopoly:      Math.round(radarData.moat ?? radarData.monopoly ?? 0),
    cashflow:      Math.round(radarData.cashflow ?? 0),
  };

  // sub-score: 실데이터(fairValue / dividend) 우선, 부재 시 '-'
  const fv = fairValue?.inputs;
  const scoreDetails = [
    {
      name: '성장성', key: 'growth' as const,
      description: 'SHAP 기여도 — 매출·EPS 성장 관련 피처',
      subScores: dividend?.scores ? [
        { label: 'EPS 성장률 점수', value: dividend.scores.eps_growth_score ?? 0, description: (dividend.scores.eps_growth_score ?? 0) >= 70 ? '우수' : '보통', raw: false },
      ] : [],
      hasData: !!radar,
    },
    {
      name: '수익성', key: 'profitability' as const,
      description: 'SHAP 기여도 — ROE·영업이익률 관련',
      subScores: fv ? [
        { label: 'EPS (원)', value: fv.eps, description: '주당순이익', raw: true },
        { label: 'BPS (원)', value: fv.bps, description: '주당순자산', raw: true },
      ] : [],
      hasData: !!radar,
    },
    {
      name: '안전성', key: 'safety' as const,
      description: 'SHAP 기여도 — 부채·유동비율 관련',
      subScores: [],
      hasData: !!radar,
    },
    {
      name: '독점력', key: 'monopoly' as const,
      description: 'SHAP 기여도 — 영업이익 안정성 / 시장점유',
      subScores: [],
      hasData: !!radar,
    },
    {
      name: '현금창출력', key: 'cashflow' as const,
      description: 'SHAP 기여도 — FCF·영업현금흐름 관련',
      subScores: dividend ? [
        { label: '배당수익률', value: dividend.yield_pct, description: `${dividend.yield_pct?.toFixed(2) ?? '-'}%`, raw: true },
        { label: '연속배당 년수', value: dividend.years_paid, description: `${dividend.years_paid ?? '-'}년`, raw: true },
      ] : [],
      hasData: !!radar,
    },
    ...(fairValue ? [{
      name: '밸류에이션', key: 'valuation' as const,
      description: `적정주가 ${fairValue.fair_value?.toLocaleString('ko-KR')}원 · ${fairValue.band_ko}`,
      subScores: [
        { label: '편차', value: fairValue.deviation_pct, description: `${fairValue.deviation_pct >= 0 ? '+' : ''}${fairValue.deviation_pct?.toFixed(1)}%`, raw: true },
      ],
      hasData: true,
    }] : []),
  ];

  return (
    <AppLayout maxWidth={1280}>
        <h1 className="wp-t-3xl font-bold text-[var(--text-primary)] mb-6">
          스마트스코어 분석
        </h1>

        <div className="mb-6">
          <label className="wp-t-base font-bold text-[var(--text-secondary)] block mb-2">
            종목 선택
          </label>
          <select
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value)}
            className="w-full sm:w-1/2 px-4 py-3 rounded-lg wp-t-base bg-[var(--bg-elev-1)] border border-[var(--border-default)] text-[var(--text-primary)]"
          >
            {allStocks.map((stock) => (
              <option key={stock.ticker} value={stock.ticker}>
                {stock.name} ({stock.ticker})
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <div className="flex items-center gap-4 mb-4">
              <StockLogo ticker={selectedStock.ticker} name={selectedStock.name} size={44} />
              <div>
                <h2 className="wp-t-lg font-bold text-[var(--text-primary)]">
                  {selectedStock.name}
                </h2>
                <div className="wp-t-sm text-[var(--text-tertiary)]">
                  {selectedStock.ticker}{selectedStock.sector ? ` · ${selectedStock.sector}` : ''}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4 mb-4">
              <ScoreBadge score={selectedStock.score} tier={selectedStock.tier} size="lg" />
              <div className="wp-t-sm text-[var(--text-secondary)]">
                AI 모델이 산출한<br />0–100 종합 점수
              </div>
            </div>
            <div className="p-3 rounded-lg bg-[var(--bg-elev-2)]">
              <div className="wp-t-xs text-[var(--text-tertiary)] mb-1">현재가</div>
              <div className="tabular-nums wp-t-xl font-bold text-[var(--text-primary)]">
                {selectedStock.price.toLocaleString('ko-KR')}원
              </div>
              <div
                className="tabular-nums wp-t-base"
                style={{ color: selectedStock.changePercent >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
              >
                {selectedStock.changePercent >= 0 ? '+' : ''}
                {selectedStock.changePercent.toFixed(2)}%
              </div>
            </div>

            {/* 신호 · 별점 · 누적수익 */}
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="wp-t-sm text-[var(--text-tertiary)]">매매 신호</span>
                <SignalLabelChip signal={selectedStock.signal} showIcon={true} />
              </div>
              <div className="flex items-center justify-between">
                <span className="wp-t-sm text-[var(--text-tertiary)]">별점</span>
                <StarRating rating={selectedStock.starRating} size="sm" showNumber={true} />
              </div>
              <div className="flex items-center justify-between">
                <span className="wp-t-sm text-[var(--text-tertiary)]">추천 후 누적수익</span>
                <span
                  className="tabular-nums wp-t-base font-bold"
                  style={{ color: (selectedStock.cumulativeReturn ?? 0) >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
                >
                  {selectedStock.cumulativeReturn != null && Number.isFinite(selectedStock.cumulativeReturn)
                    ? `${selectedStock.cumulativeReturn >= 0 ? '+' : ''}${selectedStock.cumulativeReturn.toFixed(1)}%`
                    : '—'}
                </span>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-xl flex justify-center bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <RadarChart
              stockData={{
                growth: radarData.growth ?? 75,
                profitability: radarData.profitability ?? 75,
                safety: radarData.safety ?? 75,
                monopoly: radarData.moat ?? radarData.monopoly ?? 75,
                cashflow: radarData.cashflow ?? 75,
              }}
              sectorAvg={sectorAvgData ? {
                growth: sectorAvgData.growth ?? 50,
                profitability: sectorAvgData.profitability ?? 50,
                safety: sectorAvgData.safety ?? 50,
                monopoly: sectorAvgData.moat ?? sectorAvgData.monopoly ?? 50,
                cashflow: sectorAvgData.cashflow ?? 50,
              } : undefined}
            />
          </div>
        </div>

        <div className="space-y-6">
          {scoreDetails.map((category) => (
            <div
              key={category.key}
              className="p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]"
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="wp-t-lg font-bold text-[var(--text-primary)] mb-1">
                    {category.name}
                  </h3>
                  <p className="wp-t-base text-[var(--text-tertiary)]">
                    {category.description}
                  </p>
                </div>
                <div className="tabular-nums font-bold text-[var(--accent-blue)]" style={{ fontSize: 32 }}>
                  {(scoreBreakdown as Record<string, number>)[category.key] ?? '—'}
                </div>
              </div>

              {category.subScores.length === 0 ? (
                <div className="wp-t-sm text-[var(--text-tertiary)] p-3 rounded-lg bg-[var(--bg-elev-2)]">
                  세부 지표 데이터 부재 — SHAP top_factors 적재 필요 (compute_shap.py)
                </div>
              ) : (
                <div className="space-y-4">
                  {category.subScores.map((sub) => (
                    <div key={sub.label}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="wp-t-base text-[var(--text-secondary)]">
                          {sub.label}
                        </span>
                        <span className="tabular-nums wp-t-base font-bold text-[var(--text-primary)]">
                          {sub.raw ? (sub.value?.toLocaleString?.('ko-KR') ?? sub.value) : sub.value}
                        </span>
                      </div>
                      {!sub.raw && (
                        <div className="relative rounded-full overflow-hidden h-2 bg-[var(--bg-elev-2)]">
                          <div
                            className="absolute top-0 left-0 h-full rounded-full bg-[var(--accent-blue)]"
                            style={{ width: `${sub.value}%`, transition: 'width 0.3s' }}
                          />
                        </div>
                      )}
                      <div className="wp-t-xs text-[var(--text-tertiary)] mt-1">
                        {sub.description}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
          <h3 className="wp-t-md font-bold text-[var(--text-primary)] mb-3">
            스마트스코어란?
          </h3>
          <div className="space-y-2">
            <p className="wp-t-base text-[var(--text-secondary)]">
              스마트스코어는 6가지 핵심 지표(가치, 모멘텀, 수익성, 성장성, 안전성, 독점력)를 종합적으로 분석하여 0~100점 사이의 점수로 표현합니다.
            </p>
            <p className="wp-t-base text-[var(--text-secondary)]">
              각 지표는 재무제표 데이터, 시장 데이터, AI 분석을 통해 산출되며, 종목의 투자 매력도를 객관적으로 평가합니다.
            </p>
            <div className="mt-4 p-3 rounded-lg bg-[var(--bg-elev-2)]">
              <div className="wp-t-xs text-[var(--text-tertiary)] mb-2">등급 기준</div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="wp-t-xs text-[var(--text-secondary)]">A+ : 90점 이상</div>
                <div className="wp-t-xs text-[var(--text-secondary)]">A : 80~89점</div>
                <div className="wp-t-xs text-[var(--text-secondary)]">B : 70~79점</div>
                <div className="wp-t-xs text-[var(--text-secondary)]">C : 70점 미만</div>
              </div>
            </div>
          </div>
        </div>
    </AppLayout>
  );
}
