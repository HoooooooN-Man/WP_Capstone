import { useState } from 'react';
import { X } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import RadarChart from '../components/RadarChart';
import SignalLabelChip from '../components/SignalLabelChip';
import EmptyState from '../components/EmptyState';
import { useCompare, useStockSearch, useStockRadar, type StockItem } from '../api/hooks';

interface CompareRow {
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
  headline: string;
}

// 종목별 레이더 — map 내부에서 hook 호출 불가하므로 1종목 = 1컴포넌트로 분리
function CompareRadarCard({ ticker, name }: { ticker: string; name: string }) {
  const { data: radar } = useStockRadar(ticker);
  const g = radar?.groups;
  return (
    <div className="flex flex-col items-center">
      <div className="wp-t-md font-bold text-[var(--text-primary)] mb-4">
        {name}
      </div>
      <RadarChart
        stockData={{
          growth:        g?.growth ?? 0,
          profitability: g?.profitability ?? 0,
          safety:        g?.safety ?? 0,
          monopoly:      g?.moat ?? 0,
          cashflow:      g?.cashflow ?? 0,
        }}
        sectorAvg={radar?.sector_average ? {
          growth:        radar.sector_average.growth ?? 50,
          profitability: radar.sector_average.profitability ?? 50,
          safety:        radar.sector_average.safety ?? 50,
          monopoly:      radar.sector_average.moat ?? 50,
          cashflow:      radar.sector_average.cashflow ?? 50,
        } : undefined}
      />
      {!g && (
        <div className="wp-t-2xs text-[var(--text-tertiary)] mt-2 text-center">
          레이더 데이터를 불러오는 중…
        </div>
      )}
    </div>
  );
}

export default function ComparePage() {
  const [selectedStocks, setSelectedStocks] = useState<CompareRow[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  // 백엔드 비교 API
  const tickers = selectedStocks.map((s) => s.ticker);
  const { data: compareData } = useCompare(tickers, '1y');
  const { data: searchApi } = useStockSearch(searchQuery);
  void compareData;

  const apiSearchResults: CompareRow[] | undefined = searchApi?.items?.filter(
    (s: StockItem) => !selectedStocks.find((sel) => sel.ticker === s.ticker),
  ).map((it: StockItem) => ({
    ticker: it.ticker, name: it.name, sector: it.sector,
    price: it.close ?? 0, changePercent: it.change_pct ?? 0,
    signal: it.signal_label ?? 'WATCH',
    score: it.score ?? 0, tier: it.tier ?? 'C',
    starRating: it.star_rating ?? 0, cumulativeReturn: it.cumulative_return_pct ?? 0,
    headline: it.headline ?? '',
  }));
  const searchResults: CompareRow[] = searchQuery ? (apiSearchResults ?? []) : [];

  const addStock = (stock: CompareRow) => {
    if (selectedStocks.length < 4) {
      setSelectedStocks([...selectedStocks, stock]);
      setSearchQuery('');
    }
  };

  const removeStock = (ticker: string) => {
    setSelectedStocks(selectedStocks.filter((s) => s.ticker !== ticker));
  };

  const metrics = [
    { key: 'score', label: '스마트스코어' },
    { key: 'changePercent', label: '등락률' },
    { key: 'cumulativeReturn', label: '누적수익' },
  ];

  return (
    <AppLayout maxWidth={1280}>
        <h1 className="wp-t-3xl font-bold text-[var(--text-primary)] mb-2">
          종목 비교
        </h1>
        <p className="wp-t-base text-[var(--text-tertiary)] mb-8">
          최대 4개 종목까지 비교 가능
        </p>

        <div className="mb-6">
          <div className="relative mb-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="종목 검색 (최대 4개)"
              className="w-full px-4 py-3 rounded-lg wp-t-base bg-[var(--bg-elev-1)] border border-[var(--border-default)] text-[var(--text-primary)]"
            />
            {searchQuery && searchResults.length > 0 && (
              <div
                className="absolute top-full left-0 right-0 mt-2 rounded-lg overflow-hidden z-10 bg-[var(--bg-elev-1)] border border-[var(--border-default)]"
                style={{ maxHeight: '200px', overflowY: 'auto' }}
              >
                {searchResults.slice(0, 5).map((stock) => (
                  <button
                    key={stock.ticker}
                    onClick={() => addStock(stock)}
                    className="w-full text-left px-4 py-3 transition-colors hover:bg-[var(--bg-elev-2)] border-b border-[var(--border-default)]"
                  >
                    <div className="wp-t-base font-bold text-[var(--text-primary)]">
                      {stock.name}
                    </div>
                    <div className="wp-t-xs text-[var(--text-tertiary)]">
                      {stock.ticker} · {stock.sector}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {selectedStocks.map((stock) => (
              <div
                key={stock.ticker}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--bg-elev-1)] border border-[var(--border-default)]"
              >
                <span className="wp-t-base font-bold text-[var(--text-primary)]">
                  {stock.name}
                </span>
                <button onClick={() => removeStock(stock.ticker)} aria-label="종목 제거">
                  <X size={16} style={{ color: 'var(--text-tertiary)' }} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {selectedStocks.length < 2 && (
          <EmptyState
            title="비교할 종목을 선택하세요"
            description={
              selectedStocks.length === 1
                ? '1개 더 추가하면 지표와 레이더 차트를 나란히 비교할 수 있습니다.'
                : '검색창에서 종목을 2~4개 추가하면 지표와 레이더 차트를 비교할 수 있습니다.'
            }
          />
        )}

        {selectedStocks.length >= 2 && (
          <div className="p-6 rounded-xl mb-6 bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <h2 className="wp-t-lg font-bold text-[var(--text-primary)] mb-6">
              종합 지표
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-default)]">
                    <th scope="col" className="text-left px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">지표</th>
                    {selectedStocks.map((stock) => (
                      <th scope="col" key={stock.ticker} className="text-center px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">
                        {stock.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-[var(--border-default)]">
                    <td className="px-4 py-3 wp-t-base text-[var(--text-secondary)]">현재가</td>
                    {selectedStocks.map((stock) => (
                      <td key={stock.ticker} className="px-4 py-3 text-center tabular-nums wp-t-base font-bold text-[var(--text-primary)]">
                        {stock.price.toLocaleString('ko-KR')}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-default)]">
                    <td className="px-4 py-3 wp-t-base text-[var(--text-secondary)]">등락률</td>
                    {selectedStocks.map((stock) => (
                      <td
                        key={stock.ticker}
                        className="px-4 py-3 text-center tabular-nums wp-t-base font-bold"
                        style={{ color: stock.changePercent >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
                      >
                        {stock.changePercent >= 0 ? '+' : ''}
                        {stock.changePercent.toFixed(2)}%
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-default)]">
                    <td className="px-4 py-3 wp-t-base text-[var(--text-secondary)]">신호</td>
                    {selectedStocks.map((stock) => (
                      <td key={stock.ticker} className="px-4 py-3 text-center">
                        <div className="inline-block">
                          <SignalLabelChip signal={stock.signal} showIcon={false} />
                        </div>
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-default)]">
                    <td className="px-4 py-3 wp-t-base text-[var(--text-secondary)]">스마트스코어</td>
                    {selectedStocks.map((stock) => (
                      <td key={stock.ticker} className="px-4 py-3 text-center tabular-nums wp-t-base font-bold text-[var(--accent-blue)]">
                        {stock.score.toFixed(1)}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-default)]">
                    <td className="px-4 py-3 wp-t-base text-[var(--text-secondary)]">누적수익</td>
                    {selectedStocks.map((stock) => (
                      <td
                        key={stock.ticker}
                        className="px-4 py-3 text-center tabular-nums wp-t-base font-bold"
                        style={{ color: stock.cumulativeReturn >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
                      >
                        {stock.cumulativeReturn >= 0 ? '+' : ''}
                        {stock.cumulativeReturn.toFixed(1)}%
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-4 py-3 wp-t-base text-[var(--text-secondary)]">섹터</td>
                    {selectedStocks.map((stock) => (
                      <td key={stock.ticker} className="px-4 py-3 text-center wp-t-base text-[var(--text-tertiary)]">
                        {stock.sector}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {selectedStocks.length >= 2 && (
          <div className="p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <h2 className="wp-t-lg font-bold text-[var(--text-primary)] mb-6">
              레이더 차트 비교
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {selectedStocks.map((stock) => (
                <CompareRadarCard key={stock.ticker} ticker={stock.ticker} name={stock.name} />
              ))}
            </div>
          </div>
        )}
    </AppLayout>
  );
}
