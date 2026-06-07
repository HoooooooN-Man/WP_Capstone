import { useState } from 'react';
import { Star, Trash2 } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SignalLabelChip from '../components/SignalLabelChip';
import RadarChart from '../components/RadarChart';
import StockLogo from '../components/StockLogo';
import { useWatchlist, useDeleteWatchlist, useRecommendations, type WatchlistItem } from '../api/hooks';
import PageErrorState from '../components/PageErrorState';
import { useSession } from '../api/client';

type Tab = 'list' | 'diagnosis';

interface WatchRow {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  changePercent: number;
  signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  score: number;
  tier: 'A' | 'B' | 'C' | 'D';
  starRating: number;
  cumulativeReturn: number;
  headline: string;
}

export default function WatchlistPage() {
  const [activeTab, setActiveTab] = useState<Tab>('list');
  const { isLoggedIn } = useSession();

  // API: watchlist + 전 종목(enrich용)
  const { data: wlApi } = useWatchlist();
  const { data: allStocksApi } = useRecommendations({ top_k: 0 });
  const deleteWatchlist = useDeleteWatchlist();

  // 파생값 — 쿼리 데이터에서 직접 계산 (state 로 복제하지 않음)
  const apiAll = allStocksApi?.items ?? [];
  const watchlist: WatchRow[] = (wlApi?.items ?? []).map((w: WatchlistItem): WatchRow => {
    const m = apiAll.find((s) => s.ticker === w.ticker);
    return m ? {
      ticker: m.ticker, name: m.name ?? m.ticker, sector: m.sector ?? '',
      price: m.close ?? 0, changePercent: m.change_pct ?? 0,
      signal: (m.signal_label ?? 'WATCH') as WatchRow['signal'],
      score: m.score ?? 0, tier: (m.tier ?? 'C') as WatchRow['tier'],
      starRating: m.star_rating ?? 0, cumulativeReturn: m.cumulative_return_pct ?? 0, headline: m.headline ?? '',
    } : {
      ticker: w.ticker, name: w.ticker, sector: '',
      price: 0, changePercent: 0, signal: 'WATCH',
      score: 0, tier: 'C', starRating: 0, cumulativeReturn: 0, headline: '',
    };
  });

  // 실제 삭제 — 백엔드 mutation 호출, 성공 시 react-query 가 watchlist 재검증
  const removeFromWatchlist = (ticker: string) => {
    deleteWatchlist.mutate(ticker);
  };

  const _n = Math.max(1, watchlist.length);
  const avgScore = watchlist.reduce((sum, s) => sum + s.score, 0) / _n;
  const avgChange = watchlist.reduce((sum, s) => sum + s.changePercent, 0) / _n;
  const buyCount = watchlist.filter((s) => s.signal === 'BUY').length;

  // 원스톱 진단 — batch_diagnosis 응답에 radar 정보가 없어 placeholder(0)
  const diagnosisData = {
    value: 0, momentum: 0, quality: 0, growth: 0, safety: 0, monopoly: 0,
  };
  const diagnosisScore = Math.floor(
    Object.values(diagnosisData).reduce((sum, val) => sum + val, 0) / 6
  );

  return (
    <AppLayout maxWidth={1280}>
        <h1 className="wp-t-3xl font-bold text-[var(--text-primary)] mb-6">
          관심 종목
        </h1>
        {/* P1-10 비로그인 시 로그인 유도 — 이후 콘텐츠는 렌더하지 않음 */}
        {!isLoggedIn && (
          <div className="py-8">
            <PageErrorState type="auth" />
          </div>
        )}

        {isLoggedIn && (
        <>
        <div className="flex gap-2 mb-6">
          {([['list', '목록'], ['diagnosis', '원스톱 진단']] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-4 py-2 rounded-lg transition-colors cursor-pointer wp-t-base border border-[var(--border-default)] ${
                activeTab === key
                  ? 'font-bold text-white bg-[var(--accent-blue)]'
                  : 'font-normal text-[var(--text-secondary)] bg-[var(--bg-elev-1)]'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {activeTab === 'list' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="p-4 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
                <div className="wp-t-xs text-[var(--text-tertiary)] mb-1">평균 스코어</div>
                <div className="tabular-nums wp-t-3xl font-bold text-[var(--accent-blue)]">
                  {avgScore.toFixed(1)}
                </div>
              </div>
              <div className="p-4 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
                <div className="wp-t-xs text-[var(--text-tertiary)] mb-1">평균 등락률</div>
                <div
                  className="tabular-nums wp-t-3xl font-bold"
                  style={{ color: avgChange >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
                >
                  {avgChange >= 0 ? '+' : ''}
                  {avgChange.toFixed(2)}%
                </div>
              </div>
              <div className="p-4 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
                <div className="wp-t-xs text-[var(--text-tertiary)] mb-1">BUY 신호</div>
                <div className="tabular-nums wp-t-3xl font-bold text-[var(--text-primary)]">
                  {buyCount}/{watchlist.length}
                </div>
              </div>
            </div>

            <div className="rounded-xl overflow-hidden bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[var(--border-default)]">
                      <th scope="col" className="text-left px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">종목명</th>
                      <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">현재가</th>
                      <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">등락</th>
                      <th scope="col" className="text-center px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">신호</th>
                      <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">스코어</th>
                      <th scope="col" className="text-center px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">삭제</th>
                    </tr>
                  </thead>
                  <tbody>
                    {watchlist.map((stock, idx) => (
                      <tr
                        key={stock.ticker}
                        className={`transition-colors cursor-pointer hover:bg-[var(--bg-elev-2)] ${
                          idx < watchlist.length - 1 ? 'border-b border-[var(--border-default)]' : ''
                        }`}
                      >
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-3">
                            <StockLogo ticker={stock.ticker} name={stock.name} size={36} />
                            <div>
                              <div className="flex items-center gap-1">
                                <Star size={13} style={{ color: '#FFB800', fill: '#FFB800' }} />
                                <span className="wp-t-base font-bold text-[var(--text-primary)]">
                                  {stock.name}
                                </span>
                              </div>
                              <div className="wp-t-xs text-[var(--text-tertiary)]">{stock.ticker}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className="tabular-nums wp-t-base font-bold text-[var(--text-primary)]">
                            {stock.price.toLocaleString('ko-KR')}
                          </div>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div
                            className="tabular-nums wp-t-base font-bold"
                            style={{ color: stock.changePercent >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
                          >
                            {stock.changePercent >= 0 ? '+' : ''}
                            {stock.changePercent.toFixed(2)}%
                          </div>
                        </td>
                        <td className="px-4 py-4 text-center">
                          <div className="inline-block">
                            <SignalLabelChip signal={stock.signal} showIcon={false} />
                          </div>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className="tabular-nums wp-t-base font-bold text-[var(--accent-blue)]">
                            {stock.score.toFixed(1)}
                          </div>
                        </td>
                        <td className="px-4 py-4 text-center">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              removeFromWatchlist(stock.ticker);
                            }}
                            className="p-2 rounded transition-colors text-[var(--text-tertiary)] hover:text-[var(--color-down)]"
                            aria-label="관심종목 삭제"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {activeTab === 'diagnosis' && (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
              <h2 className="wp-t-lg font-bold text-[var(--text-primary)] mb-4">
                포트폴리오 진단
              </h2>
              <div className="flex flex-col items-center">
                <div className="mb-4 font-bold text-[var(--accent-blue)]" style={{ fontSize: 48 }}>
                  {diagnosisScore}점
                </div>
                <div className="wp-t-md text-[var(--text-secondary)] mb-6">
                  {diagnosisScore >= 80 ? '우수' : diagnosisScore >= 70 ? '양호' : diagnosisScore >= 60 ? '보통' : '개선 필요'}
                </div>
                <RadarChart stockData={{
                  growth: diagnosisData.growth,
                  profitability: diagnosisData.quality,
                  safety: diagnosisData.safety,
                  monopoly: diagnosisData.monopoly,
                  cashflow: diagnosisData.value,
                }} />
              </div>
            </div>

            <div className="p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
              <h3 className="wp-t-md font-bold text-[var(--text-primary)] mb-3">
                진단 요약
              </h3>
              <div className="space-y-3">
                {[
                  { title: '가치 지표', body: `현재 관심 종목의 평균 가치 점수는 ${diagnosisData.value}점으로 양호한 수준입니다.` },
                  { title: '모멘텀 지표', body: `상승 모멘텀 점수는 ${diagnosisData.momentum}점입니다. 단기 상승 여력이 있습니다.` },
                  { title: '안전성 지표', body: `포트폴리오의 안전성 점수는 ${diagnosisData.safety}점으로 리스크 관리가 필요합니다.` },
                ].map((row) => (
                  <div key={row.title} className="flex items-start gap-3">
                    <div className="rounded-full bg-[var(--accent-blue)] mt-2" style={{ minWidth: 4, height: 4 }} />
                    <div>
                      <div className="wp-t-base font-bold text-[var(--text-primary)]">{row.title}</div>
                      <div className="wp-t-base text-[var(--text-secondary)]">{row.body}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        </>
        )}
    </AppLayout>
  );
}
