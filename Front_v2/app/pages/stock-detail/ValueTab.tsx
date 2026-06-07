import Card from '../../components/Card';
import SectionHeader from '../../components/SectionHeader';
import StatTile from '../../components/StatTile';
import type { FairValueResponse, DividendResponse } from '../../api/hooks';

export interface ValueTabFinancialRow {
  year: string;
  revenue: number;
  operatingIncome: number;
  netIncome: number;
}

interface ValueTabProps {
  fairValue?: FairValueResponse;
  financialData: ValueTabFinancialRow[];
  dividend?: DividendResponse;
}

export default function ValueTab({ fairValue, financialData, dividend }: ValueTabProps) {
  return (
    <div className="space-y-6">
      {/* 적정주가 밴드 */}
      <Card>
        <SectionHeader title="밸류에이션 — 적정주가 밴드차트" />
        {fairValue ? (
          <div className="mt-4">
            <div className="grid grid-cols-3 gap-4 mb-6">
              <StatTile label="현재가" valueSize={22} value={`${fairValue.current_price?.toLocaleString('ko-KR') ?? '-'}원`} />
              <StatTile label="적정가" valueSize={22} value={`${fairValue.fair_value?.toLocaleString('ko-KR') ?? '-'}원`} />
              <StatTile
                label="편차"
                valueSize={22}
                valueColor={fairValue.deviation_pct > 10 ? 'var(--color-down)' : fairValue.deviation_pct < -10 ? 'var(--accent-blue)' : 'var(--text-primary)'}
                value={`${fairValue.deviation_pct >= 0 ? '+' : ''}${fairValue.deviation_pct?.toFixed(1)}% ${fairValue.band_ko ?? ''}`}
              />
            </div>
            <div
              className="relative h-16 rounded-lg overflow-hidden"
              style={{ background: 'linear-gradient(to right, #3B82F6 0%, #3B82F6 20%, #60A5FA 20%, #60A5FA 40%, #9CA3AF 40%, #9CA3AF 60%, #F87171 60%, #F87171 80%, #B91C1C 80%, #B91C1C 100%)' }}
            >
              <div className="absolute inset-0 flex items-center justify-around text-white wp-t-xs font-bold">
                <span>매우저평가</span><span>저평가</span><span>적정</span><span>고평가</span><span>매우고평가</span>
              </div>
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-[var(--text-primary)]"
                style={{ left: `${Math.max(0, Math.min(100, 50 + (fairValue.deviation_pct || 0)))}%` }}
              />
            </div>
            <div className="mt-6 p-4 rounded-lg bg-[var(--bg-elev-2)]">
              <div className="wp-t-base font-bold text-[var(--text-primary)] mb-2">계산 근거 (multiple 기반)</div>
              <div className="wp-t-sm text-[var(--text-secondary)]">
                EPS {fairValue.inputs?.eps?.toLocaleString() ?? '—'} · BPS {fairValue.inputs?.bps?.toLocaleString() ?? '—'} ·
                섹터 PER {fairValue.inputs?.sector_per?.toFixed(1) ?? '—'} · 섹터 PBR {fairValue.inputs?.sector_pbr?.toFixed(2) ?? '—'} ·
                자기 PER {fairValue.inputs?.self_per_med?.toFixed(1) ?? '—'} · 자기 PBR {fairValue.inputs?.self_pbr_med?.toFixed(2) ?? '—'}
              </div>
            </div>
          </div>
        ) : (
          <div className="wp-t-sm text-[var(--text-tertiary)] mt-4">적정주가 데이터를 불러오는 중입니다.</div>
        )}
      </Card>

      {/* 재무 정보 */}
      <Card>
        <SectionHeader title="재무 정보" sub="단위: 억원" />
        {financialData.length === 0 ? (
          <div className="wp-t-sm text-[var(--text-tertiary)] py-6 text-center">
            재무 데이터 미수집 — DART/FnGuide 연동 필요
          </div>
        ) : (
          <div className="overflow-x-auto mt-4">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th scope="col" className="text-left px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">구분</th>
                  {financialData.map((year) => (
                    <th scope="col" key={year.year} className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">
                      {year.year}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {([
                  { label: '매출액', key: 'revenue' },
                  { label: '영업이익', key: 'operatingIncome' },
                  { label: '순이익', key: 'netIncome' },
                ] as const).map((row, ri) => (
                  <tr key={row.key} className={ri < 2 ? 'border-b border-[var(--border-default)]' : ''}>
                    <td className="px-4 py-3 wp-t-base text-[var(--text-secondary)]">{row.label}</td>
                    {financialData.map((year) => (
                      <td key={year.year} className="px-4 py-3 text-right tabular-nums wp-t-base font-bold text-[var(--text-primary)]">
                        {year[row.key].toLocaleString()}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* 배당스코어 */}
      <Card>
        <SectionHeader title="배당스코어" />
        {dividend ? (
          <div className="mt-4">
            <div className="flex items-center gap-6 mb-6">
              <div
                className="tabular-nums font-bold text-[var(--accent-blue)]"
                style={{ fontSize: 48, lineHeight: 1 }}
              >
                {dividend.dividend_score?.toFixed(0) ?? '-'}
              </div>
              <div className="wp-t-base text-[var(--text-secondary)]">
                배당수익률 {dividend.yield_pct?.toFixed(2) ?? '-'}% · 주당배당금 {dividend.dps?.toLocaleString() ?? '-'}원 ·
                {dividend.years_paid ?? '-'}년 연속 배당
              </div>
            </div>
            <div className="space-y-3 mb-6">
              {dividend.scores && Object.entries(dividend.scores).map(([key, value]: [string, number | undefined]) => {
                const labels: Record<string, string> = {
                  yield_score: '배당수익률', consecutive_score: '연속배당',
                  growth_score: '배당금 인상', payout_score: '배당성향', eps_growth_score: 'EPS 성장률',
                };
                const v = value ?? 0;
                return (
                  <div key={key} className="flex items-center gap-4">
                    <div className="wp-t-base text-[var(--text-secondary)]" style={{ width: 120 }}>{labels[key] ?? key}</div>
                    <div className="flex-1 rounded-full overflow-hidden h-3 bg-[var(--bg-elev-2)]">
                      <div className="h-full bg-[var(--accent-blue)]" style={{ width: `${v}%` }} />
                    </div>
                    <div className="tabular-nums font-bold text-[var(--text-primary)] text-right" style={{ width: 50 }}>{v.toFixed(0)}</div>
                  </div>
                );
              })}
            </div>
            {(dividend.investment_points?.length ?? 0) > 0 && (
              <div className="p-4 rounded-lg bg-[var(--bg-elev-2)]">
                <div className="wp-t-base font-bold text-[var(--text-primary)] mb-2">투자 포인트</div>
                <ul className="wp-t-sm text-[var(--text-secondary)] list-disc pl-5">
                  {dividend.investment_points?.map((p: string, idx: number) => <li key={idx}>{p}</li>)}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="wp-t-sm text-[var(--text-tertiary)] mt-4">배당 데이터를 불러오는 중입니다.</div>
        )}
      </Card>
    </div>
  );
}
