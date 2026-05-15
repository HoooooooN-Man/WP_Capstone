import Card from '../../components/Card';
import SectionHeader from '../../components/SectionHeader';
import LineChart from '../../components/LineChart';
import type { FinancialItem, HistoryItem } from '../../api/hooks';

export interface HomeTabSelectedStock {
  ticker: string;
  name: string;
  sector: string;
  headline: string;
}

export interface HomeTabNewsPreview {
  id: number;
  title: string;
  source: string;
  time: string;
}

export interface HomeTabRadarEntry {
  key: string;
  label: string;
  score: number;
}

interface HomeTabProps {
  selectedStock: HomeTabSelectedStock;
  performanceHistory: { date: string; score: number }[];
  fin?: FinancialItem;
  latest?: HistoryItem;
  w52High: number;
  w52Low: number;
  fmtKRW: (v: number | null | undefined) => string;
  fmtEok: (v: number | null | undefined) => string;
  radarGroupEntries: HomeTabRadarEntry[];
  newsItems: HomeTabNewsPreview[];
  onGoDiagnosis: () => void;
  onGoNews: () => void;
}

const ROW_LABEL = 'wp-t-base text-[var(--text-tertiary)]';
const ROW_VALUE = 'tabular-nums wp-t-base font-bold text-[var(--text-primary)]';

export default function HomeTab({
  selectedStock, performanceHistory, fin, latest, w52High, w52Low,
  fmtKRW, fmtEok, radarGroupEntries, newsItems,
  onGoDiagnosis, onGoNews,
}: HomeTabProps) {
  return (
    <div className="space-y-6">
      {/* 스마트스코어 추이 */}
      <Card>
        <SectionHeader title="스마트스코어 추이" right={<span className="wp-t-sm text-[var(--text-tertiary)]">최근 30 거래일</span>} />
        <div className="mt-4">
          <LineChart data={performanceHistory} height={260} />
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <SectionHeader title="기업 개요" />
          <p className="wp-t-base text-[var(--text-secondary)] mt-3">
            {selectedStock.name} ({selectedStock.ticker}) — {selectedStock.sector || '섹터 미분류'} 섹터.
            {selectedStock.headline ? ` ${selectedStock.headline}` : ''}
          </p>
        </Card>

        <Card>
          <SectionHeader
            title="5요인 진단"
            right={
              <button
                onClick={onGoDiagnosis}
                className="wp-t-sm font-bold text-[var(--accent-blue)] bg-transparent border-none cursor-pointer"
              >
                자세히
              </button>
            }
          />
          {radarGroupEntries.length > 0 ? (
            <div className="space-y-2.5 mt-4">
              {radarGroupEntries.map((g) => (
                <div key={g.key} className="flex items-center gap-3">
                  <span className="wp-t-sm text-[var(--text-secondary)]" style={{ width: 64 }}>{g.label}</span>
                  <div className="flex-1 rounded-full overflow-hidden h-2 bg-[var(--bg-elev-2)]">
                    <div className="h-full bg-[var(--accent-blue)]" style={{ width: `${Math.max(0, Math.min(100, g.score))}%` }} />
                  </div>
                  <span className="tabular-nums wp-t-sm font-bold text-[var(--text-primary)] text-right w-8">
                    {g.score}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="wp-t-sm text-[var(--text-tertiary)] mt-4">
              5요인 진단 데이터를 불러오는 중입니다.
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <SectionHeader title="주요 지표" />
          <div className="space-y-3 mt-4">
            <div className="flex justify-between">
              <span className={ROW_LABEL}>시가총액</span>
              <span className={ROW_VALUE}>{fmtEok(latest?.market_cap ?? fin?.market_cap)}</span>
            </div>
            <div className="flex justify-between">
              <span className={ROW_LABEL}>PER</span>
              <span className={ROW_VALUE}>{fin?.per != null ? `${fin.per.toFixed(1)}배` : '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className={ROW_LABEL}>PBR</span>
              <span className={ROW_VALUE}>{fin?.pbr != null ? `${fin.pbr.toFixed(2)}배` : '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className={ROW_LABEL}>배당수익률</span>
              <span className={ROW_VALUE}>{fin?.dividend_yield != null ? `${Number(fin.dividend_yield).toFixed(2)}%` : '-'}</span>
            </div>
          </div>
        </Card>

        <Card>
          <SectionHeader title="거래 정보" />
          <div className="space-y-3 mt-4">
            <div className="flex justify-between">
              <span className={ROW_LABEL}>거래량</span>
              <span className={ROW_VALUE}>{latest?.volume != null ? `${fmtKRW(latest.volume)}주` : '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className={ROW_LABEL}>52주 최고</span>
              <span className={ROW_VALUE}>{w52High > 0 ? `${fmtKRW(w52High)}원` : '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className={ROW_LABEL}>52주 최저</span>
              <span className={ROW_VALUE}>{w52Low > 0 ? `${fmtKRW(w52Low)}원` : '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className={ROW_LABEL}>상장주식수</span>
              <span className={ROW_VALUE}>
                {latest?.shares_outstanding != null ? `${(latest.shares_outstanding / 1e6).toFixed(1)}M주` : '-'}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* 관련 뉴스 미리보기 — 전체는 뉴스 탭 */}
      <Card padded={false}>
        <div className="px-6 pt-6 pb-3">
          <SectionHeader
            title="관련 뉴스"
            right={
              newsItems.length > 0 ? (
                <button
                  onClick={onGoNews}
                  className="wp-t-sm font-bold text-[var(--accent-blue)] bg-transparent border-none cursor-pointer"
                >
                  전체 ({newsItems.length})
                </button>
              ) : undefined
            }
          />
        </div>
        {newsItems.length === 0 ? (
          <div className="wp-t-sm text-[var(--text-tertiary)] px-6 pt-2 pb-6">
            연결된 뉴스가 없습니다.
          </div>
        ) : (
          newsItems.slice(0, 3).map((news) => (
            <div key={news.id} className="px-6 py-3.5 border-t border-[var(--border-default)]">
              <div className="wp-t-base font-bold text-[var(--text-primary)] mb-1">
                {news.title}
              </div>
              <div className="wp-t-xs text-[var(--text-tertiary)]">
                {news.source} · {news.time}
              </div>
            </div>
          ))
        )}
      </Card>
    </div>
  );
}
