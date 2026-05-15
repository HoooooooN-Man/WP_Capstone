import { useState } from 'react';
import AppLayout from '../components/AppLayout';
import StockLogo from '../components/StockLogo';
import { useSectorsSummary, useRecommendations, type StockItem, type SectorSummary } from '../api/hooks';

interface SectorRow {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  changePercent: number;
  signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  score: number;
  tier: 'A' | 'B' | 'C' | 'D';
  starRating: number;
}

interface SectorStat {
  name: string;
  stockCount: number;
  avgChange: number;
  avgScore: number;
  buyCount: number;
  totalMarketCap: number;
  stocks: SectorRow[];
}

export default function SectorsPage() {
  const [selectedSector, setSelectedSector] = useState<string | null>(null);

  // API: 섹터 요약 + 전 종목 (섹터 필터링용)
  const { data: sectorsApi } = useSectorsSummary();
  const { data: rec } = useRecommendations({ top_k: 0 });

  // API 응답 우선
  const apiAll: SectorRow[] | undefined = rec?.items?.map((it: StockItem) => ({
    ticker: it.ticker, name: it.name, sector: it.sector ?? '미분류',
    price: it.close ?? 0, changePercent: it.change_pct ?? 0,
    signal: it.signal_label ?? 'WATCH',
    score: it.score ?? 0, tier: it.tier ?? 'C',
    starRating: it.star_rating ?? 0,
  }));
  const baseStocks: SectorRow[] = apiAll ?? [];

  // 섹터 요약 엔드포인트는 등락률을 안 주므로 전 종목(baseStocks)에서 섹터별 평균 등락 산출
  const sectorChangeMap = new Map<string, number>();
  {
    const acc = new Map<string, { sum: number; n: number }>();
    for (const s of baseStocks) {
      const cur = acc.get(s.sector) ?? { sum: 0, n: 0 };
      cur.sum += s.changePercent ?? 0;
      cur.n += 1;
      acc.set(s.sector, cur);
    }
    for (const [sec, { sum, n }] of acc) sectorChangeMap.set(sec, n > 0 ? sum / n : 0);
  }

  const apiSectors: SectorStat[] | undefined = sectorsApi?.items?.map((s: SectorSummary) => {
    const name = s.sector ?? s.name ?? '미분류';
    return {
      name,
      stockCount: s.stock_count ?? s.count ?? 0,
      avgChange: s.avg_change_pct ?? sectorChangeMap.get(name) ?? 0,
      avgScore: s.avg_score ?? 0,
      buyCount: s.tier_a_count ?? 0,
      totalMarketCap: s.total_market_cap ?? 0,
      stocks: [],
    };
  });

  const sectorStats: SectorStat[] = (apiSectors && apiSectors.length > 0)
    ? apiSectors
    : Array.from(new Set(baseStocks.map((s) => s.sector))).map((sector) => {
        const stocks = baseStocks.filter((s) => s.sector === sector);
        const avgChange = stocks.reduce((sum, s) => sum + s.changePercent, 0) / stocks.length;
        const avgScore = stocks.reduce((sum, s) => sum + s.score, 0) / stocks.length;
        const buyCount = stocks.filter((s) => s.signal === 'BUY').length;
        const totalMarketCap = stocks.reduce((sum, s) => sum + s.price * 1000000, 0);
        return { name: sector, stockCount: stocks.length, avgChange, avgScore, buyCount, totalMarketCap, stocks };
      });

  const sortedSectors = [...sectorStats].sort((a, b) => b.avgChange - a.avgChange);

  const filteredStocks: SectorRow[] = selectedSector
    ? baseStocks.filter((s) => s.sector === selectedSector)
    : [];

  return (
    <AppLayout maxWidth={1280}>
        <h1 className="wp-t-3xl font-bold text-[var(--text-primary)] mb-8">
          섹터 분석
        </h1>

        {/* 섹터 카드 그리드 (리디자인 P1-8) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {sortedSectors.map((sector) => {
            const selected = selectedSector === sector.name;
            const up = sector.avgChange >= 0;
            return (
              <button
                key={sector.name}
                onClick={() => setSelectedSector(selected ? null : sector.name)}
                className={`text-left p-5 rounded-xl transition-colors duration-150 cursor-pointer border-[1.5px] ${
                  selected
                    ? 'border-[var(--accent-blue)]'
                    : 'border-[var(--border-default)] hover:border-[var(--text-tertiary)]'
                }`}
                style={{ backgroundColor: 'var(--bg-elev-1)' }}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="wp-t-md font-extrabold text-[var(--text-primary)]">
                    {sector.name}
                  </span>
                  <span
                    className="tabular-nums wp-t-sm font-bold"
                    style={{ color: up ? 'var(--color-up)' : 'var(--color-down)' }}
                  >
                    {up ? '+' : ''}{sector.avgChange.toFixed(2)}%
                  </span>
                </div>
                <div className="flex items-end justify-between">
                  <div>
                    <div className="wp-t-xs text-[var(--text-tertiary)] mb-0.5">
                      평균 스코어
                    </div>
                    <div className="tabular-nums wp-t-3xl font-extrabold text-[var(--accent-blue)]" style={{ lineHeight: 1 }}>
                      {sector.avgScore.toFixed(1)}
                    </div>
                  </div>
                  <div className="text-right space-y-1">
                    <div className="wp-t-xs text-[var(--text-tertiary)]">
                      종목 {sector.stockCount}개
                    </div>
                    <div className="inline-flex items-center tabular-nums rounded px-2 py-0.5 wp-t-xs font-bold bg-[var(--buy-bg)] text-[var(--buy-text)]">
                      BUY {sector.buyCount}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {selectedSector && (
          <div className="rounded-xl overflow-hidden bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <div className="px-4 py-3 border-b border-[var(--border-default)]">
              <div className="wp-t-md font-bold text-[var(--text-primary)]">
                {selectedSector} 종목 ({filteredStocks.length})
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-default)]">
                    <th scope="col" className="text-left px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">종목명</th>
                    <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">현재가</th>
                    <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">등락</th>
                    <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">스코어</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStocks.map((stock, idx) => (
                    <tr
                      key={stock.ticker}
                      className={`transition-colors cursor-pointer hover:bg-[var(--bg-elev-2)] ${
                        idx < filteredStocks.length - 1 ? 'border-b border-[var(--border-default)]' : ''
                      }`}
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
                          style={{ color: stock.changePercent >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
                        >
                          {stock.changePercent >= 0 ? '+' : ''}
                          {stock.changePercent.toFixed(2)}%
                        </div>
                      </td>
                      <td className="px-4 py-4 text-right">
                        <div className="tabular-nums wp-t-base font-bold text-[var(--accent-blue)]">
                          {stock.score.toFixed(1)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
    </AppLayout>
  );
}
