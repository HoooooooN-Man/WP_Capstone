import { useState, useEffect } from 'react';
import AppLayout from '../components/AppLayout';
import MarketScoreGauge from '../components/MarketScoreGauge';
import SignalLabelChip from '../components/SignalLabelChip';
import StockLogo from '../components/StockLogo';
import BottomDisclaimer from '../components/BottomDisclaimer';
import { useRecommendations, useMarketRegime, type StockItem } from '../api/hooks';
import { getReturnColor } from '../utils/format';

const PAGE_SIZE = 30;

type SignalKind = 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
type SignalRow = StockItem & {
  signal: SignalKind;
  price: number;
  changePercent: number;
  cumulativeReturn?: number;
};

export default function SignalPage() {
  const [selectedSignals, setSelectedSignals] = useState<SignalKind[]>(['BUY']);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  // API 우선, 실패 시 mock 폴백
  const { data: regime } = useMarketRegime();
  const { data: rec } = useRecommendations({ top_k: 0 });
  const apiItems = rec?.items;
  const stocks: SignalRow[] = (apiItems ?? []).map((it: StockItem) => ({
    ...it,
    signal: it.signal_label ?? 'WATCH',
    price: it.close,
    changePercent: it.change_pct ?? 0,
    cumulativeReturn: it.cumulative_return_pct,
  }));

  const signalCounts: Record<SignalKind, number> = {
    BUY:   stocks.filter((s) => s.signal === 'BUY').length,
    HOLD:  stocks.filter((s) => s.signal === 'HOLD').length,
    SELL:  stocks.filter((s) => s.signal === 'SELL').length,
    WATCH: stocks.filter((s) => s.signal === 'WATCH').length,
  };

  const total = Object.values(signalCounts).reduce((sum, count) => sum + count, 0);

  const filteredStocks = stocks.filter((stock) => selectedSignals.includes(stock.signal));
  const visibleStocks = filteredStocks.slice(0, visibleCount);

  // 필터가 바뀌면 페이지 초기화
  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [selectedSignals]);

  const toggleSignal = (signal: SignalKind) => {
    if (selectedSignals.includes(signal)) {
      setSelectedSignals(selectedSignals.filter((s) => s !== signal));
    } else {
      setSelectedSignals([...selectedSignals, signal]);
    }
  };

  const th = 'px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]';

  return (
    <AppLayout maxWidth={1280}>
      <div className="flex items-baseline justify-between mb-8">
        <h1 className="wp-t-3xl font-bold text-[var(--text-primary)]">매매신호</h1>
        <div className="wp-t-base text-[var(--text-tertiary)]">2026.05.13</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="p-6 rounded-xl flex flex-col items-center bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
          <div className="self-start wp-t-md font-bold text-[var(--text-primary)] mb-2">
            마켓스코어
          </div>
          <MarketScoreGauge score={regime?.market_score ?? 75} />
        </div>

        <div className="p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
          <div className="wp-t-md font-bold text-[var(--text-primary)] mb-4">시장 분포</div>
          <div className="space-y-3">
            {Object.entries(signalCounts).map(([signal, count]) => (
              <div key={signal} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <SignalLabelChip signal={signal as SignalKind} showIcon={false} />
                  <div className="tabular-nums wp-t-xl font-bold text-[var(--text-primary)]">
                    {count}
                  </div>
                </div>
                <div className="tabular-nums wp-t-base text-[var(--text-tertiary)]">
                  {((count / total) * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="p-6 rounded-xl mb-6 bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
        <div className="wp-t-base font-bold text-[var(--text-secondary)] mb-3">필터</div>
        <div className="flex flex-wrap gap-3">
          {(['BUY', 'HOLD', 'SELL', 'WATCH'] as const).map((signal) => {
            const active = selectedSignals.includes(signal);
            return (
              <button
                key={signal}
                onClick={() => toggleSignal(signal)}
                className={`px-4 py-2 rounded-lg transition-colors cursor-pointer wp-t-base border border-[var(--border-default)] ${
                  active
                    ? 'font-bold text-white bg-[var(--accent-blue)]'
                    : 'font-normal text-[var(--text-secondary)] bg-[var(--bg-elev-2)]'
                }`}
              >
                {signal} ({signalCounts[signal]})
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-xl overflow-hidden bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-default)]">
                <th scope="col" className={`text-left ${th}`}>종목명</th>
                <th scope="col" className={`text-right ${th}`}>현재가</th>
                <th scope="col" className={`text-right ${th}`}>등락</th>
                <th scope="col" className={`text-center ${th}`}>신호</th>
                <th scope="col" className={`text-right ${th}`}>최근 30일</th>
              </tr>
            </thead>
            <tbody>
              {visibleStocks.map((stock) => (
                <tr
                  key={stock.ticker}
                  className="transition-colors cursor-pointer hover:bg-[var(--bg-elev-2)] border-b border-[var(--border-default)]"
                >
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <StockLogo ticker={stock.ticker} name={stock.name} size={36} />
                      <div>
                        <div className="wp-t-base font-bold text-[var(--text-primary)]">
                          {stock.name}
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
                      style={{ color: (stock.changePercent ?? 0) >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
                    >
                      {(stock.changePercent ?? 0) >= 0 ? '+' : ''}
                      {(stock.changePercent ?? 0).toFixed(2)}%
                    </div>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <div className="inline-block">
                      <SignalLabelChip signal={stock.signal} showIcon={false} />
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right">
                    <div
                      className="tabular-nums wp-t-base font-bold"
                      style={{ color: getReturnColor(stock.cumulativeReturn) }}
                    >
                      {stock.cumulativeReturn != null && Number.isFinite(stock.cumulativeReturn)
                        ? `${stock.cumulativeReturn >= 0 ? '+' : ''}${stock.cumulativeReturn.toFixed(1)}%`
                        : '—'}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredStocks.length > visibleCount && (
          <div className="p-4 flex justify-center border-t border-[var(--border-default)]">
            <button
              onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
              className="px-6 py-2 rounded-lg transition-colors cursor-pointer wp-t-base font-bold
                bg-[var(--bg-elev-2)] text-[var(--text-secondary)] border border-[var(--border-default)]"
            >
              더 보기 ({visibleStocks.length} / {filteredStocks.length})
            </button>
          </div>
        )}
        {filteredStocks.length === 0 && (
          <div className="p-8 text-center wp-t-base text-[var(--text-tertiary)]">
            선택한 신호에 해당하는 종목이 없습니다.
          </div>
        )}
      </div>

      <BottomDisclaimer />
    </AppLayout>
  );
}
