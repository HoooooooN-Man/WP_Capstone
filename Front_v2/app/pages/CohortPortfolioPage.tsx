/**
 * CohortPortfolioPage v3 — ML 5 코호트 종목 추천 + 사용자 직접 편집 (빼기/추가).
 *
 * v3 변경 (사용자 정정):
 *   - 가상 자본·수량 계산 X — 종목 리스트만
 *   - 체크박스로 빼기 + 검색으로 추가
 *   - "저장" 클릭 시 선택된 ticker list 만 백엔드 INSERT (quantity=0 placeholder)
 */
import { useEffect, useMemo, useState } from 'react';
import { Plus, X, Search } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SignalLabelChip from '../components/SignalLabelChip';
import PageErrorState from '../components/PageErrorState';
import { useSession } from '../api/client';
import {
  useCohortPreview, useCohortPortfolio, useApplyCohort, useStockSearch,
  useCohortHistoricalTest, useCohortBacktest,
  type CohortName, type CohortPick,
} from '../api/hooks';
import { getReturnColor } from '../utils/format';

const COHORTS: { name: CohortName; label: string; desc: string }[] = [
  { name: 'balanced',     label: '균형',     desc: '점수 상위 균등 분산' },
  { name: 'conservative', label: '안정',     desc: '저변동·재무 우량' },
  { name: 'growth',       label: '성장',     desc: '매출 성장 + 점수' },
  { name: 'dividend',     label: '배당',     desc: '배당수익률 2% 이상' },
  { name: 'value',        label: '가치',     desc: 'PER<15 + PBR<1.5' },
];

export default function CohortPortfolioPage() {
  const { isLoggedIn } = useSession();
  const [selected, setSelected] = useState<CohortName>('balanced');
  /** 0 = 현재 ML 추천, N>0 = N일 전 시점 ML 추천 (백테 모드). */
  const [backtestDays, setBacktestDays] = useState<number>(0);

  const { data: preview, isLoading: pvLoading } = useCohortPreview(selected, backtestDays);
  const { data: portfolio } = useCohortPortfolio(selected);
  const apply = useApplyCohort();
  const historicalTest = useCohortHistoricalTest();
  const { data: backtest } = useCohortBacktest();

  // 사용자 편집 state — preview 받으면 default 로 모두 선택
  const [selectedTickers, setSelectedTickers] = useState<Set<string>>(new Set());
  const [extraPicks, setExtraPicks] = useState<CohortPick[]>([]);   // 외부 추가 종목
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQ, setSearchQ] = useState('');
  const { data: searchData } = useStockSearch(searchQ);

  // preview 로딩되면 default = 모든 ML 추천 선택, 또는 기존 저장된 portfolio 있으면 그걸 default
  useEffect(() => {
    if (!preview) return;
    if (portfolio && portfolio.total > 0) {
      const savedTickers = new Set(portfolio.items.map((it) => it.ticker));
      // saved 중 ML 추천에 없는 종목은 extra 로 추출
      const mlTickerSet = new Set(preview.picks.map((p) => p.ticker));
      const savedExtras: CohortPick[] = portfolio.items
        .filter((it) => !mlTickerSet.has(it.ticker))
        .map((it) => ({
          ticker: it.ticker,
          name: it.name,
          sector: it.sector,
          current_price: it.current_price,
          score: it.score ?? undefined,
          signal_label: it.signal_label ?? undefined,
        }));
      setSelectedTickers(savedTickers);
      setExtraPicks(savedExtras);
    } else {
      // 신규 — 모든 ML 추천 선택 default
      setSelectedTickers(new Set(preview.picks.map((p) => p.ticker)));
      setExtraPicks([]);
    }
  }, [preview, portfolio, selected]);

  const allPicks: CohortPick[] = useMemo(() => {
    if (!preview) return extraPicks;
    return [...preview.picks, ...extraPicks];
  }, [preview, extraPicks]);

  // 저장된 종목별 선정 후 수익률 lookup
  const portfolioReturnMap = useMemo(() => {
    const m = new Map<string, { return_pct: number | null; days: number | null; entry: number; split: boolean }>();
    portfolio?.items.forEach((it) => {
      m.set(it.ticker, {
        return_pct: it.return_pct ?? null,
        days: it.days_since_pick ?? null,
        entry: it.entry_price,
        split: it.split_event_suspected ?? false,
      });
    });
    return m;
  }, [portfolio]);

  const toggleTicker = (ticker: string) => {
    setSelectedTickers((prev) => {
      const next = new Set(prev);
      next.has(ticker) ? next.delete(ticker) : next.add(ticker);
      return next;
    });
  };

  const removeExtra = (ticker: string) => {
    setExtraPicks((prev) => prev.filter((p) => p.ticker !== ticker));
    setSelectedTickers((prev) => {
      const next = new Set(prev);
      next.delete(ticker);
      return next;
    });
  };

  const addExtra = (s: { ticker: string; name?: string; sector?: string; close: number; score?: number; signal_label?: string }) => {
    if (allPicks.some((p) => p.ticker === s.ticker)) return;
    setExtraPicks((prev) => [...prev, {
      ticker: s.ticker, name: s.name, sector: s.sector,
      current_price: s.close,
      score: s.score, signal_label: s.signal_label as CohortPick['signal_label'],
    }]);
    setSelectedTickers((prev) => new Set(prev).add(s.ticker));
    setSearchOpen(false); setSearchQ('');
  };

  const handleSave = () => {
    const tickers = Array.from(selectedTickers);
    if (tickers.length === 0) return;
    apply.mutate({ cohort: selected, tickers });
  };

  const hasChanges = useMemo(() => {
    if (!portfolio) return selectedTickers.size > 0;
    const saved = new Set(portfolio.items.map((it) => it.ticker));
    if (saved.size !== selectedTickers.size) return true;
    for (const t of selectedTickers) if (!saved.has(t)) return true;
    return false;
  }, [portfolio, selectedTickers]);

  return (
    <AppLayout maxWidth={1280}>
      <h1 className="wp-t-3xl font-bold text-[var(--text-primary)] mb-2">코호트 추천 종목</h1>
      <p className="wp-t-base text-[var(--text-secondary)] mb-6">
        ML 이 5코호트별 10종목씩 추천 · 사용자가 직접 빼거나 추가해 저장
      </p>

      {!isLoggedIn && (<div className="py-8"><PageErrorState type="auth" /></div>)}

      {isLoggedIn && (
        <>
          {/* 코호트 카드 */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            {COHORTS.map((c) => {
              const active = c.name === selected;
              return (
                <button
                  key={c.name}
                  onClick={() => setSelected(c.name)}
                  className="p-4 rounded-xl text-left transition-all"
                  style={{
                    backgroundColor: active ? 'var(--accent-blue)' : 'var(--bg-elev-1)',
                    color: active ? 'white' : 'var(--text-primary)',
                    border: `1px solid ${active ? 'var(--accent-blue)' : 'var(--border-default)'}`,
                  }}
                >
                  <div className="wp-t-lg font-bold mb-1">{c.label}</div>
                  <div className="wp-t-xs opacity-80">{c.desc}</div>
                </button>
              );
            })}
          </div>

          {/* 저장된 포트폴리오 수익률 요약 — apply 후에만 노출 */}
          {portfolio && portfolio.total > 0 && portfolio.summary?.avg_return_pct != null && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              <div className="p-4 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
                <div className="wp-t-xs text-[var(--text-tertiary)] mb-1">평균 수익률</div>
                <div className="wp-t-2xl font-bold tabular-nums" style={{ color: getReturnColor(portfolio.summary.avg_return_pct) }}>
                  {portfolio.summary.avg_return_pct >= 0 ? '+' : ''}{portfolio.summary.avg_return_pct.toFixed(2)}%
                </div>
                <div className="wp-t-xs text-[var(--text-tertiary)] mt-1">{portfolio.summary.n_valid_returns}개 종목 평균</div>
              </div>
              <div className="p-4 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
                <div className="wp-t-xs text-[var(--text-tertiary)] mb-1">승률</div>
                <div className="wp-t-2xl font-bold tabular-nums">
                  {portfolio.summary.win_rate_pct?.toFixed(0)}%
                </div>
                <div className="wp-t-xs text-[var(--text-tertiary)] mt-1">상승 종목 비율</div>
              </div>
              {portfolio.summary.best_pick && (
                <div className="p-4 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
                  <div className="wp-t-xs text-[var(--text-tertiary)] mb-1">최고 성과</div>
                  <div className="wp-t-base font-bold truncate">{portfolio.summary.best_pick.name}</div>
                  <div className="wp-t-lg font-bold tabular-nums" style={{ color: 'var(--color-up)' }}>
                    +{portfolio.summary.best_pick.return_pct.toFixed(2)}%
                  </div>
                </div>
              )}
              {portfolio.summary.worst_pick && (
                <div className="p-4 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
                  <div className="wp-t-xs text-[var(--text-tertiary)] mb-1">최저 성과</div>
                  <div className="wp-t-base font-bold truncate">{portfolio.summary.worst_pick.name}</div>
                  <div className="wp-t-lg font-bold tabular-nums" style={{ color: getReturnColor(portfolio.summary.worst_pick.return_pct) }}>
                    {portfolio.summary.worst_pick.return_pct >= 0 ? '+' : ''}{portfolio.summary.worst_pick.return_pct.toFixed(2)}%
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 액션 바 */}
          <div className="flex items-center gap-3 mb-4">
            <div className="wp-t-sm text-[var(--text-secondary)]">
              선택된 종목 <span className="font-bold text-[var(--text-primary)]">{selectedTickers.size}</span>개
              {extraPicks.length > 0 && <> · 직접 추가 {extraPicks.length}개</>}
            </div>
            <div className="ml-auto flex items-center gap-2">
              <button
                onClick={() => setSearchOpen((v) => !v)}
                className="flex items-center gap-1 px-3 py-2 rounded-lg wp-t-sm border border-[var(--border-default)] bg-[var(--bg-elev-1)]"
              >
                <Plus size={14} /> 종목 추가
              </button>
              <button
                onClick={handleSave}
                disabled={!hasChanges || apply.isPending || selectedTickers.size === 0}
                className="px-4 py-2 rounded-lg wp-t-sm font-bold text-white"
                style={{
                  backgroundColor: hasChanges ? 'var(--accent-blue)' : 'var(--text-tertiary)',
                  opacity: apply.isPending ? 0.6 : 1,
                  cursor: hasChanges && !apply.isPending ? 'pointer' : 'not-allowed',
                }}
              >
                {portfolio && portfolio.total > 0 ? '변경사항 저장' : '이 구성으로 저장'}
              </button>
            </div>
          </div>

          {/* 백테스트: 과거 시점 모델 추천 종목의 현재 수익률 */}
          <div className="flex items-center justify-between p-3 rounded-xl mb-6 border border-dashed border-[var(--border-default)] bg-[var(--bg-elev-2)]">
            <div className="wp-t-sm text-[var(--text-secondary)]">
              <span className="font-bold">{backtestDays > 0 ? `백테스트 모드 (${backtestDays}일 전)` : '백테스트'}</span>
              {' · '}과거 시점에 모델이 추천했던 종목의 현재 수익률
            </div>
            <div className="flex gap-2">
              {backtestDays === 0 ? (
                <>
                  {[30, 90, 180].map((d) => (
                    <button
                      key={d}
                      onClick={() => {
                        setBacktestDays(d);
                        historicalTest.mutate({ cohort: selected, days_ago: d });
                      }}
                      disabled={historicalTest.isPending}
                      className="px-3 py-1.5 rounded wp-t-xs font-bold border border-[var(--border-default)] bg-[var(--bg-base)]"
                      style={{ opacity: historicalTest.isPending ? 0.6 : 1 }}
                    >
                      {d === 30 ? '1개월' : d === 90 ? '3개월' : '6개월'} 전 추천
                    </button>
                  ))}
                </>
              ) : (
                <button
                  onClick={() => setBacktestDays(0)}
                  className="px-3 py-1.5 rounded wp-t-xs font-bold text-white"
                  style={{ backgroundColor: 'var(--accent-blue)' }}
                >
                  현재 추천으로 돌아가기
                </button>
              )}
            </div>
          </div>

          {/* 검색 드롭다운 */}
          {searchOpen && (
            <div className="mb-4 p-3 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
              <div className="flex items-center gap-2 mb-2">
                <Search size={16} className="text-[var(--text-tertiary)]" />
                <input
                  autoFocus
                  type="text"
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  placeholder="종목명 또는 티커 검색 (예: 삼성전자, 005930)"
                  className="flex-1 px-2 py-1 rounded bg-transparent outline-none"
                />
                <button onClick={() => { setSearchOpen(false); setSearchQ(''); }} className="text-[var(--text-tertiary)]">
                  <X size={16} />
                </button>
              </div>
              {searchQ && searchData?.items && (
                <div className="max-h-60 overflow-y-auto">
                  {searchData.items.slice(0, 8).map((s) => (
                    <button
                      key={s.ticker}
                      onClick={() => addExtra({
                        ticker: s.ticker, name: s.name, sector: s.sector,
                        close: s.close, score: s.score, signal_label: s.signal_label,
                      })}
                      disabled={allPicks.some((p) => p.ticker === s.ticker)}
                      className="w-full flex items-center gap-3 px-2 py-2 hover:bg-[var(--bg-elev-2)] rounded text-left disabled:opacity-50"
                    >
                      <div className="flex-1">
                        <div className="font-bold">{s.name}</div>
                        <div className="wp-t-xs text-[var(--text-tertiary)]">{s.ticker} · {s.sector}</div>
                      </div>
                      <div className="tabular-nums wp-t-sm">{s.close?.toLocaleString('ko-KR')}원</div>
                      {allPicks.some((p) => p.ticker === s.ticker) && <span className="wp-t-xs text-[var(--text-tertiary)]">이미 추가됨</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 종목 리스트 */}
          {pvLoading && <div className="py-8 text-center text-[var(--text-tertiary)]">로딩...</div>}
          {!pvLoading && (
            <div className="rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)] overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-default)] wp-t-xs text-[var(--text-tertiary)] font-bold">
                    <th className="text-left px-4 py-3 w-12">선택</th>
                    <th className="text-left px-4 py-3">종목</th>
                    <th className="text-right px-4 py-3">점수</th>
                    <th className="text-center px-4 py-3">신호</th>
                    <th className="text-right px-4 py-3">현재가</th>
                    <th className="text-right px-4 py-3 w-32">선정 후</th>
                    <th className="text-left px-4 py-3 w-24">유형</th>
                    <th className="text-center px-4 py-3 w-12"></th>
                  </tr>
                </thead>
                <tbody>
                  {allPicks.map((p) => {
                    const isML = preview?.picks.some((pp) => pp.ticker === p.ticker) ?? false;
                    const checked = selectedTickers.has(p.ticker);
                    return (
                      <tr key={p.ticker} className="border-b border-[var(--border-default)]" style={{ opacity: checked ? 1 : 0.5 }}>
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleTicker(p.ticker)}
                            className="w-4 h-4 cursor-pointer"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-bold">{p.name ?? p.ticker}</div>
                          <div className="wp-t-xs text-[var(--text-tertiary)]">{p.ticker}{p.sector ? ` · ${p.sector}` : ''}</div>
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">{p.score != null ? p.score.toFixed(1) : '—'}</td>
                        <td className="px-4 py-3 text-center">
                          {p.signal_label && <SignalLabelChip signal={p.signal_label} showIcon={false} />}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">{p.current_price.toLocaleString('ko-KR')}원</td>
                        <td className="px-4 py-3 text-right">
                          {(() => {
                            const r = portfolioReturnMap.get(p.ticker);
                            if (!r) {
                              return <span className="wp-t-xs text-[var(--text-tertiary)]">저장 전</span>;
                            }
                            if (r.split || r.return_pct == null) {
                              return <span className="wp-t-xs text-[var(--text-tertiary)]" title="분할 의심">분할 의심</span>;
                            }
                            return (
                              <div>
                                <div className="tabular-nums font-bold" style={{ color: getReturnColor(r.return_pct) }}>
                                  {r.return_pct >= 0 ? '+' : ''}{r.return_pct.toFixed(2)}%
                                </div>
                                {r.days != null && (
                                  <div className="wp-t-xs text-[var(--text-tertiary)]">선정 후 {r.days}일</div>
                                )}
                              </div>
                            );
                          })()}
                        </td>
                        <td className="px-4 py-3">
                          <span className="wp-t-xs px-2 py-1 rounded" style={{
                            backgroundColor: isML ? 'var(--buy-bg)' : 'var(--bg-elev-2)',
                            color: isML ? 'var(--buy-text)' : 'var(--text-secondary)',
                          }}>
                            {isML ? 'ML 추천' : '직접 추가'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {!isML && (
                            <button onClick={() => removeExtra(p.ticker)} className="text-[var(--text-tertiary)] hover:text-[var(--color-down)]">
                              <X size={16} />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* 백테 성과 — Regime-dep K10·H20 5코호트 16개월 */}
          {backtest && (
            <div className="mt-8">
              <h2 className="wp-t-xl font-bold mb-1">5-Cohort 백테 성과 (16개월)</h2>
              <p className="wp-t-xs text-[var(--text-tertiary)] mb-3">
                Regime-dep · {backtest.description} · 2025-01 ~ 2026-04
              </p>
              <div className="rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)] overflow-hidden">
                <table className="w-full wp-t-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-default)] wp-t-xs text-[var(--text-tertiary)] font-bold">
                      <th className="text-left px-4 py-2">코호트</th>
                      <th className="text-right px-4 py-2">평균 월</th>
                      <th className="text-right px-4 py-2">16개월 누적</th>
                      <th className="text-right px-4 py-2">승률</th>
                      <th className="text-right px-4 py-2">최고 월</th>
                      <th className="text-right px-4 py-2">최저 월</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(['balanced', 'conservative', 'growth', 'dividend', 'value'] as const)
                      .filter((c) => backtest.summary[c])
                      .map((c) => {
                        const s = backtest.summary[c];
                        const label = { balanced: '균형', conservative: '안정', growth: '성장', dividend: '배당', value: '가치' }[c];
                        return (
                          <tr key={c} className="border-b border-[var(--border-default)]">
                            <td className="px-4 py-2 font-bold">{label}</td>
                            <td className="px-4 py-2 text-right tabular-nums" style={{ color: getReturnColor(s.avg_return_pct) }}>
                              {s.avg_return_pct >= 0 ? '+' : ''}{s.avg_return_pct.toFixed(2)}%
                            </td>
                            <td className="px-4 py-2 text-right tabular-nums font-bold" style={{ color: getReturnColor(s.cum_return_pct) }}>
                              {s.cum_return_pct >= 0 ? '+' : ''}{s.cum_return_pct.toFixed(2)}%
                            </td>
                            <td className="px-4 py-2 text-right tabular-nums">{s.win_rate_pct.toFixed(1)}%</td>
                            <td className="px-4 py-2 text-right wp-t-xs">
                              <div className="tabular-nums" style={{ color: 'var(--color-up)' }}>
                                +{s.best_month?.return_pct.toFixed(2)}%
                              </div>
                              <div className="text-[var(--text-tertiary)]">{s.best_month?.date}</div>
                            </td>
                            <td className="px-4 py-2 text-right wp-t-xs">
                              <div className="tabular-nums" style={{ color: getReturnColor(s.worst_month?.return_pct ?? 0) }}>
                                {s.worst_month && s.worst_month.return_pct >= 0 ? '+' : ''}{s.worst_month?.return_pct.toFixed(2)}%
                              </div>
                              <div className="text-[var(--text-tertiary)]">{s.worst_month?.date}</div>
                            </td>
                          </tr>
                        );
                      })}
                    {backtest.kospi_summary && (
                      <tr className="border-t-2 border-[var(--border-default)] bg-[var(--bg-elev-2)]">
                        <td className="px-4 py-2 font-bold">KOSPI 동기간</td>
                        <td className="px-4 py-2 text-right tabular-nums">{backtest.kospi_summary.avg_return_pct.toFixed(2)}%</td>
                        <td className="px-4 py-2 text-right tabular-nums font-bold">{backtest.kospi_summary.cum_return_pct.toFixed(2)}%</td>
                        <td className="px-4 py-2 text-right tabular-nums">{backtest.kospi_summary.win_rate_pct.toFixed(1)}%</td>
                        <td colSpan={2} className="px-4 py-2 text-right wp-t-xs text-[var(--text-tertiary)]">
                          벤치마크 참조
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="mt-2 wp-t-xs text-[var(--text-tertiary)]">
                * net 수익률 (편도 0.15% × 2 = 0.30%/rebal). 균등 가중. 거래세·슬리피지 미반영.
              </div>
            </div>
          )}

          <div className="mt-4 wp-t-xs text-[var(--text-tertiary)]">
            * 본 추천은 자문이 아닙니다. 매수 금액·수량은 사용자가 직접 결정합니다.
          </div>
        </>
      )}
    </AppLayout>
  );
}
