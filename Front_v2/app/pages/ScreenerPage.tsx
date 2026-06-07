import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import Card from '../components/Card';
import SignalLabelChip from '../components/SignalLabelChip';
import StockLogo from '../components/StockLogo';
import DataTable, { type DataTableColumn } from '../components/DataTable';
import { useScreener, type StockItem } from '../api/hooks';
import { formatPrice, formatPercent } from '../utils/format';

interface ScreenerRow {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  changePercent: number;
  signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  score: number;
  tier: string;
}

const EMPTY_FILTERS = {
  signal: [] as string[],
  sector: [] as string[],
  priceMin: '',
  priceMax: '',
  changeMin: '',
  changeMax: '',
  scoreMin: '',
};

export default function ScreenerPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  // 백엔드 스크리너 호출 — 필터를 백엔드 파라미터로 매핑
  const { data: screenerApi } = useScreener({
    min_score: filters.scoreMin || undefined,
    sector: filters.sector[0] || undefined,
    limit: 100,
  });
  // API 응답 → 행 매핑은 screenerApi 변경 시에만 재계산
  const baseStocks: ScreenerRow[] = useMemo(
    () =>
      (screenerApi?.items ?? []).map((it: StockItem) => ({
        ticker: it.ticker,
        name: it.name,
        sector: it.sector ?? '',
        price: it.close ?? 0,
        changePercent: it.change_pct ?? 0,
        signal: (it.signal_label ?? 'WATCH') as ScreenerRow['signal'],
        score: it.score ?? 0,
        tier: it.tier ?? 'C',
      })),
    [screenerApi],
  );

  const sectors = useMemo(
    () => Array.from(new Set(baseStocks.map((s) => s.sector).filter(Boolean))),
    [baseStocks],
  );

  const toggleSignal = (signal: string) =>
    setFilters((p) => ({
      ...p,
      signal: p.signal.includes(signal) ? p.signal.filter((s) => s !== signal) : [...p.signal, signal],
    }));
  const toggleSector = (sector: string) =>
    setFilters((p) => ({
      ...p,
      sector: p.sector.includes(sector) ? p.sector.filter((s) => s !== sector) : [...p.sector, sector],
    }));
  const resetFilters = () => setFilters(EMPTY_FILTERS);

  // 필터 적용 — DataTable 에 안정적 ref 를 넘겨 내부 정렬·렌더 최적화
  const rows = useMemo(
    () =>
      baseStocks.filter((s) => {
        if (filters.signal.length > 0 && !filters.signal.includes(s.signal)) return false;
        if (filters.sector.length > 0 && !filters.sector.includes(s.sector)) return false;
        if (filters.priceMin && s.price < parseFloat(filters.priceMin)) return false;
        if (filters.priceMax && s.price > parseFloat(filters.priceMax)) return false;
        if (filters.changeMin && s.changePercent < parseFloat(filters.changeMin)) return false;
        if (filters.changeMax && s.changePercent > parseFloat(filters.changeMax)) return false;
        if (filters.scoreMin && s.score < parseFloat(filters.scoreMin)) return false;
        return true;
      }),
    [baseStocks, filters],
  );

  const presets = [
    { label: '고스코어 A급', desc: '스코어 80+', apply: { scoreMin: '80' } },
    { label: '매수 신호', desc: 'BUY 신호', apply: { signal: ['BUY'] } },
    { label: '급등주', desc: '등락 +3%↑', apply: { changeMin: '3' } },
    { label: '안정 우량주', desc: '스코어 70+ · BUY/HOLD', apply: { scoreMin: '70', signal: ['BUY', 'HOLD'] } },
    { label: '저가 매력주', desc: '1만원 이하 · 스코어 70+', apply: { priceMax: '10000', scoreMin: '70' } },
  ];

  // 칩 공통 스타일
  const chip = (active: boolean): React.CSSProperties => ({
    padding: '5px 12px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: active ? 700 : 400,
    cursor: 'pointer',
    backgroundColor: active ? 'var(--accent-blue)' : 'var(--bg-elev-2)',
    color: active ? '#FFFFFF' : 'var(--text-secondary)',
    border: '1px solid var(--border-default)',
  });
  const numInput: React.CSSProperties = {
    width: '88px',
    padding: '6px 10px',
    borderRadius: '8px',
    backgroundColor: 'var(--bg-elev-2)',
    border: '1px solid var(--border-default)',
    color: 'var(--text-primary)',
    fontSize: '13px',
    outline: 'none',
  };
  const groupLabel: React.CSSProperties = {
    fontSize: '12px',
    fontWeight: 700,
    color: 'var(--text-tertiary)',
    width: '64px',
    flexShrink: 0,
  };

  const columns: DataTableColumn<ScreenerRow>[] = [
    {
      key: 'rank',
      header: '#',
      align: 'center',
      width: 44,
      render: (_row, idx) => (
        <span className="tabular-nums" style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-tertiary)' }}>
          {idx + 1}
        </span>
      ),
    },
    {
      key: 'name',
      header: '종목명',
      sortable: true,
      sortValue: (r) => r.name,
      render: (r) => (
        <div className="flex items-center gap-3">
          <StockLogo ticker={r.ticker} name={r.name} size={32} />
          <div className="min-w-0">
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>{r.name}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
              {r.ticker}{r.sector ? ` · ${r.sector}` : ''}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'price',
      header: '현재가',
      align: 'right',
      sortable: true,
      sortValue: (r) => r.price,
      render: (r) => (
        <span className="tabular-nums" style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
          {formatPrice(r.price)}
        </span>
      ),
    },
    {
      key: 'change',
      header: '등락률',
      align: 'right',
      sortable: true,
      sortValue: (r) => r.changePercent,
      render: (r) => (
        <span
          className="tabular-nums"
          style={{
            fontSize: '14px',
            fontWeight: 700,
            color: r.changePercent >= 0 ? 'var(--color-up)' : 'var(--color-down)',
          }}
        >
          {formatPercent(r.changePercent)}
        </span>
      ),
    },
    {
      key: 'score',
      header: '스코어',
      align: 'right',
      sortable: true,
      sortValue: (r) => r.score,
      render: (r) => (
        <span className="tabular-nums" style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-blue)' }}>
          {r.score.toFixed(1)} <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>[{r.tier}]</span>
        </span>
      ),
    },
    {
      key: 'signal',
      header: '신호',
      align: 'center',
      sortable: true,
      sortValue: (r) => r.signal,
      render: (r) => (
        <div className="inline-block">
          <SignalLabelChip signal={r.signal} showIcon={false} />
        </div>
      ),
    },
  ];

  return (
    <AppLayout maxWidth={1280}>
      <div className="flex items-baseline justify-between mb-6">
        <h1 style={{ fontSize: '28px', fontWeight: 700, lineHeight: '36px', color: 'var(--text-primary)' }}>
          스크리너
        </h1>
        <button
          onClick={resetFilters}
          style={{ fontSize: '14px', color: 'var(--accent-blue)', fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer' }}
        >
          필터 초기화
        </button>
      </div>

      {/* 투자레시피 — 프리셋 빠른 적용 */}
      <div className="mb-5">
        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px' }}>
          투자레시피
        </div>
        <div className="flex flex-wrap gap-2">
          {presets.map((preset) => (
            <button
              key={preset.label}
              onClick={() => setFilters({ ...EMPTY_FILTERS, ...preset.apply })}
              className="text-left px-3.5 py-2 rounded-lg transition-colors hover:border-[var(--accent-blue)]"
              style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>{preset.label}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{preset.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 슬림 필터 바 — 6개 카드 → 단일 카드 3행 */}
      <Card className="mb-4" style={{ padding: '16px 20px' }}>
        <div className="space-y-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span style={groupLabel}>매매신호</span>
            {(['BUY', 'HOLD', 'SELL', 'WATCH'] as const).map((s) => (
              <button key={s} onClick={() => toggleSignal(s)} style={chip(filters.signal.includes(s))}>
                {s}
              </button>
            ))}
          </div>

          {sectors.length > 0 && (
            <div className="flex items-start gap-2 flex-wrap">
              <span style={{ ...groupLabel, marginTop: '5px' }}>섹터</span>
              <div className="flex flex-wrap gap-2 flex-1">
                {sectors.map((sec) => (
                  <button key={sec} onClick={() => toggleSector(sec)} style={chip(filters.sector.includes(sec))}>
                    {sec}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center gap-2 flex-wrap">
            <span style={groupLabel}>가격</span>
            <input type="number" placeholder="최소" value={filters.priceMin}
              onChange={(e) => setFilters({ ...filters, priceMin: e.target.value })} style={numInput} />
            <span style={{ color: 'var(--text-tertiary)' }}>~</span>
            <input type="number" placeholder="최대" value={filters.priceMax}
              onChange={(e) => setFilters({ ...filters, priceMax: e.target.value })} style={numInput} />

            <span style={{ ...groupLabel, marginLeft: '12px' }}>등락 %</span>
            <input type="number" placeholder="최소" value={filters.changeMin}
              onChange={(e) => setFilters({ ...filters, changeMin: e.target.value })} style={numInput} />
            <span style={{ color: 'var(--text-tertiary)' }}>~</span>
            <input type="number" placeholder="최대" value={filters.changeMax}
              onChange={(e) => setFilters({ ...filters, changeMax: e.target.value })} style={numInput} />

            <span style={{ ...groupLabel, marginLeft: '12px', width: 'auto' }}>스코어 ≥</span>
            <input type="number" placeholder="예: 70" value={filters.scoreMin}
              onChange={(e) => setFilters({ ...filters, scoreMin: e.target.value })} style={numInput} />
          </div>
        </div>
      </Card>

      <div className="mb-3" style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{rows.length}</span>개 종목 검색됨
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(r) => r.ticker}
        onRowClick={(r) => navigate(`/stocks/${r.ticker}`)}
        defaultSort={{ key: 'score', dir: 'desc' }}
        emptyMessage="조건에 맞는 종목이 없습니다. 필터를 조정해 보세요."
      />
    </AppLayout>
  );
}
