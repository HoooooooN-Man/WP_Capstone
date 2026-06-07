import { useState, useEffect, useRef } from 'react';
import { Search as SearchIcon, Flame, TrendingUp } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SignalLabelChip from '../components/SignalLabelChip';
import StockLogo from '../components/StockLogo';
import { useStockSearch, useRecommendations, type StockItem } from '../api/hooks';
import { useNavigate } from 'react-router-dom';

const RECENT_KEY = 'recent-searches';

interface SearchRow {
  ticker: string;
  name: string;
  sector?: string;
  price: number;
  changePercent: number;
  signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
}

function loadRecent(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export default function SearchPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);
  const [recentSearches, setRecentSearches] = useState<string[]>(loadRecent);
  const inputRef = useRef<HTMLInputElement>(null);

  // 최근 검색어 저장 (최신순, 중복 제거, 최대 8개) — navigate 전에 동기 처리
  const addRecent = (term: string) => {
    const t = term.trim();
    if (!t) return;
    const next = [t, ...recentSearches.filter((x) => x !== t)].slice(0, 8);
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(next)); } catch { /* ignore */ }
    setRecentSearches(next);
  };

  // API 검색 (q ≥ 1자) + 인기/급등 종목 추천 fallback 활용
  const { data: searchApi } = useStockSearch(query);
  const { data: rec } = useRecommendations({ top_k: 20 });

  const popularStocks: SearchRow[] = (rec?.items ?? []).slice(0, 10).map((it: StockItem) => ({
    ticker: it.ticker, name: it.name, sector: it.sector, price: it.close,
    changePercent: it.change_pct ?? 0, signal: it.signal_label ?? 'WATCH',
  }));
  const risingStocks: SearchRow[] = popularStocks
    .filter((s) => s.changePercent > 0)
    .sort((a, b) => b.changePercent - a.changePercent)
    .slice(0, 10);

  const searchResults: SearchRow[] = query
    ? (searchApi?.items ?? []).map((it: StockItem) => ({
        ticker: it.ticker, name: it.name, sector: it.sector, price: it.close ?? 0,
        changePercent: it.change_pct ?? 0, signal: it.signal_label ?? 'WATCH',
      }))
    : [];

  useEffect(() => { setActiveIdx(0); }, [query]);

  const clearRecent = () => {
    setRecentSearches([]);
    try { localStorage.removeItem(RECENT_KEY); } catch { /* ignore */ }
  };

  const goToStock = (ticker: string) => {
    addRecent(query);
    navigate(`/stocks/${ticker}`);
  };

  // 자동완성 키보드 네비게이션
  const onInputKey = (e: React.KeyboardEvent) => {
    if (searchResults.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, searchResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && searchResults[activeIdx]) {
      e.preventDefault();
      goToStock(searchResults[activeIdx].ticker);
    } else if (e.key === 'Escape') {
      setQuery('');
    }
  };

  return (
    <AppLayout maxWidth={896}>
      {/* 검색 입력 + 자동완성 드롭다운 */}
      <div className="mb-6">
        <div className="relative">
          <SearchIcon
            size={20}
            style={{
              position: 'absolute', left: '16px', top: '50%',
              transform: 'translateY(-50%)', color: 'var(--text-tertiary)', zIndex: 1,
            }}
          />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onInputKey}
            placeholder="종목명 또는 심볼 검색  ( Ctrl+K 어디서나 검색 )"
            className="w-full pl-12 pr-4 py-4 rounded-xl transition-colors"
            style={{
              backgroundColor: 'var(--bg-elev-1)',
              border: '2px solid var(--border-default)',
              color: 'var(--text-primary)',
              fontSize: '16px',
              outline: 'none',
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent-blue)'; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border-default)'; }}
          />

          {/* 자동완성 드롭다운 */}
          {query && (
            <div
              className="absolute left-0 right-0 mt-2 rounded-xl overflow-hidden z-20"
              style={{
                top: '100%',
                backgroundColor: 'var(--bg-elev-1)',
                border: '1px solid var(--border-default)',
                boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                maxHeight: '380px',
                overflowY: 'auto',
              }}
            >
              {searchResults.length === 0 ? (
                <div style={{ padding: '20px', textAlign: 'center', fontSize: '13px', color: 'var(--text-tertiary)' }}>
                  검색 결과가 없습니다.
                </div>
              ) : (
                <>
                  <div
                    className="px-4 py-2"
                    style={{ fontSize: '12px', color: 'var(--text-tertiary)', borderBottom: '1px solid var(--border-default)' }}
                  >
                    검색 결과 {searchResults.length} · ↑↓ 이동 · Enter 이동
                  </div>
                  {searchResults.map((stock: SearchRow, idx: number) => (
                    <button
                      key={stock.ticker}
                      onClick={() => goToStock(stock.ticker)}
                      onMouseEnter={() => setActiveIdx(idx)}
                      className="w-full px-4 py-3 flex items-center justify-between text-left"
                      style={{
                        background: idx === activeIdx ? 'var(--bg-elev-2)' : 'transparent',
                        border: 'none',
                        borderBottom: idx < searchResults.length - 1 ? '1px solid var(--border-default)' : 'none',
                        cursor: 'pointer',
                      }}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <StockLogo ticker={stock.ticker} name={stock.name} size={36} />
                        <div className="min-w-0">
                          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
                            {stock.name}
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                            {stock.ticker}{stock.sector ? ` · ${stock.sector}` : ''}
                          </div>
                        </div>
                      </div>
                      <SignalLabelChip signal={stock.signal} showIcon={false} />
                    </button>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 검색어 없을 때 — 최근 검색 / 인기 / 급등 */}
      {!query && (
        <>
          {recentSearches.length > 0 && (
            <div
              className="mb-6 p-4 rounded-xl"
              style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)' }}
            >
              <div className="flex items-center justify-between mb-3">
                <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-secondary)' }}>최근 검색</div>
                <button
                  onClick={clearRecent}
                  style={{ fontSize: '12px', color: 'var(--text-tertiary)', background: 'none', border: 'none', cursor: 'pointer' }}
                >
                  삭제
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {recentSearches.map((search) => (
                  <button
                    key={search}
                    className="px-3 py-1 rounded-lg"
                    style={{ backgroundColor: 'var(--bg-elev-2)', color: 'var(--text-primary)', fontSize: '14px', border: 'none', cursor: 'pointer' }}
                    onClick={() => { setQuery(search); inputRef.current?.focus(); }}
                  >
                    {search}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div
            className="mb-6 rounded-xl overflow-hidden"
            style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)' }}
          >
            <div
              className="px-4 py-3 flex items-center gap-2"
              style={{ borderBottom: '1px solid var(--border-default)' }}
            >
              <Flame size={18} style={{ color: 'var(--color-up)' }} />
              <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>인기 종목 TOP 10</span>
            </div>
            {popularStocks.map((stock: SearchRow, idx: number) => (
              <button
                type="button"
                key={stock.ticker}
                onClick={() => navigate(`/stocks/${stock.ticker}`)}
                aria-label={`${stock.name} 상세 보기`}
                className="w-full text-left px-4 py-3 flex items-center justify-between cursor-pointer transition-colors hover:bg-[var(--bg-elev-2)]"
                style={{ borderBottom: idx < popularStocks.length - 1 ? '1px solid var(--border-default)' : 'none' }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="flex items-center justify-center tabular-nums"
                    style={{ width: '20px', fontSize: '13px', fontWeight: 700, color: 'var(--text-tertiary)' }}
                  >
                    {idx + 1}
                  </div>
                  <StockLogo ticker={stock.ticker} name={stock.name} size={36} />
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>{stock.name}</div>
                    <div
                      className="tabular-nums"
                      style={{ fontSize: '12px', color: stock.changePercent >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
                    >
                      {stock.changePercent >= 0 ? '+' : ''}{stock.changePercent.toFixed(2)}%
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="tabular-nums" style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {stock.price?.toLocaleString('ko-KR')}
                  </div>
                  <SignalLabelChip signal={stock.signal} showIcon={false} />
                </div>
              </button>
            ))}
          </div>

          <div
            className="rounded-xl overflow-hidden"
            style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)' }}
          >
            <div
              className="px-4 py-3 flex items-center gap-2"
              style={{ borderBottom: '1px solid var(--border-default)' }}
            >
              <TrendingUp size={18} style={{ color: 'var(--color-up)' }} />
              <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>급등 종목 TOP 10</span>
            </div>
            {risingStocks.map((stock: SearchRow, idx: number) => (
              <button
                type="button"
                key={stock.ticker}
                onClick={() => navigate(`/stocks/${stock.ticker}`)}
                aria-label={`${stock.name} 상세 보기`}
                className="w-full text-left px-4 py-3 flex items-center justify-between cursor-pointer transition-colors hover:bg-[var(--bg-elev-2)]"
                style={{ borderBottom: idx < risingStocks.length - 1 ? '1px solid var(--border-default)' : 'none' }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="flex items-center justify-center tabular-nums"
                    style={{ width: '20px', fontSize: '13px', fontWeight: 700, color: 'var(--text-tertiary)' }}
                  >
                    {idx + 1}
                  </div>
                  <StockLogo ticker={stock.ticker} name={stock.name} size={36} />
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>{stock.name}</div>
                    <div className="tabular-nums" style={{ fontSize: '12px', color: 'var(--color-up)' }}>
                      +{stock.changePercent.toFixed(2)}%
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="tabular-nums" style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {stock.price?.toLocaleString('ko-KR')}
                  </div>
                  <SignalLabelChip signal={stock.signal} showIcon={false} />
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </AppLayout>
  );
}
