import Card from '../../components/Card';
import SectionHeader from '../../components/SectionHeader';
import RadarChart from '../../components/RadarChart';
import LineChart from '../../components/LineChart';
import type { RadarResponse } from '../../api/hooks';
import type { HomeTabRadarEntry } from './HomeTab';

interface DiagnosisTabProps {
  radar?: RadarResponse;
  radarGroupEntries: HomeTabRadarEntry[];
  strengths: HomeTabRadarEntry[];
  cautions: HomeTabRadarEntry[];
  performanceHistory: { date: string; score: number }[];
}

export default function DiagnosisTab({
  radar, radarGroupEntries, strengths, cautions, performanceHistory,
}: DiagnosisTabProps) {
  return (
    <div className="space-y-6">
      <Card>
        <SectionHeader title="AI 분석 리포트" sub="5요인 진단은 radar API 그룹 점수 기반 — 종목별 자동 산출" />
        <div className="flex justify-center my-6">
          <RadarChart
            stockData={{
              growth:        radar?.groups?.growth ?? 0,
              profitability: radar?.groups?.profitability ?? 0,
              safety:        radar?.groups?.safety ?? 0,
              monopoly:      radar?.groups?.moat ?? 0,
              cashflow:      radar?.groups?.cashflow ?? 0,
            }}
            sectorAvg={radar?.sector_average ? {
              growth:        radar.sector_average.growth ?? 50,
              profitability: radar.sector_average.profitability ?? 50,
              safety:        radar.sector_average.safety ?? 50,
              monopoly:      radar.sector_average.moat ?? 50,
              cashflow:      radar.sector_average.cashflow ?? 50,
            } : undefined}
          />
        </div>
        {radarGroupEntries.length === 0 ? (
          <div className="wp-t-sm text-[var(--text-tertiary)] py-2">
            5요인 진단 데이터를 불러오는 중입니다.
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <div className="wp-t-base font-bold text-[var(--text-primary)] mb-1">강점</div>
              {strengths.length > 0 ? (
                <ul className="space-y-2">
                  {strengths.map((g) => (
                    <li key={g.key} className="wp-t-base text-[var(--text-secondary)] pl-4">
                      • {g.label} ({g.score}점) — 5요인 진단 상위 요인
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="wp-t-sm text-[var(--text-tertiary)] pl-4">
                  70점 이상의 두드러진 강점 요인이 없습니다.
                </div>
              )}
            </div>
            <div>
              <div className="wp-t-base font-bold text-[var(--text-primary)] mb-1">주의사항</div>
              {cautions.length > 0 ? (
                <ul className="space-y-2">
                  {cautions.map((g) => (
                    <li key={g.key} className="wp-t-base text-[var(--text-secondary)] pl-4">
                      • {g.label} ({g.score}점) — 상대적으로 취약, 모니터링 필요
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="wp-t-sm text-[var(--text-tertiary)] pl-4">
                  50점 미만의 취약 요인이 없습니다.
                </div>
              )}
            </div>
          </div>
        )}
      </Card>

      <Card>
        <SectionHeader title="스코어 추이" right={<span className="wp-t-sm text-[var(--text-tertiary)]">최근 30 거래일</span>} />
        <div className="mt-4">
          <LineChart data={performanceHistory} height={220} />
        </div>
      </Card>
    </div>
  );
}
