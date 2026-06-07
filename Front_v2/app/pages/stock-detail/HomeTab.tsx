import { useState, useMemo } from 'react';
import Card from '../../components/Card';
import SectionHeader from '../../components/SectionHeader';
import CandlestickChart from '../../components/CandlestickChart';
import type { FinancialItem, HistoryItem } from '../../api/hooks';

export interface HomeTabSelectedStock {
  ticker: string;
  name: string;
  sector: string;
  headline: string;
}

export interface HomeTabNewsPreview {
  // 백엔드 news_id 는 해시 문자열 — 숫자 가정 불가.
  id: string | number;
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
  candleHistory: { date: string; open: number; high: number; low: number; close: number; volume?: number; ma20?: number | null; ma60?: number | null }[];
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

type Interval = 'D' | 'W' | 'M' | 'Y';
const INTERVAL_LABEL: Record<Interval, string> = { 'D': '일', 'W': '주', 'M': '월', 'Y': '년' };
const INTERVALS: Interval[] = ['D', 'W', 'M', 'Y'];

type RawCandle = HomeTabProps['candleHistory'][number];
type AggCandle = RawCandle;

// 일/주/월/년 OHLC 집계 — 같은 그룹 내 첫 open, max high, min low, 마지막 close, sum volume
function aggregate(data: RawCandle[], interval: Interval): AggCandle[] {
  if (interval === 'D' || data.length === 0) return data;
  const keyOf = (d: string): string => {
    // d 가 'YYYY-MM-DD'
    if (interval === 'Y') return d.slice(0, 4);
    if (interval === 'M') return d.slice(0, 7);
    // weekly — ISO week (월요일 시작) 단순 계산
    const dt = new Date(d);
    const onejan = new Date(dt.getFullYear(), 0, 1);
    const week = Math.ceil((((dt.getTime() - onejan.getTime()) / 86400000) + onejan.getDay() + 1) / 7);
    return `${dt.getFullYear()}-W${String(week).padStart(2, '0')}`;
  };

  const groups = new Map<string, RawCandle[]>();
  const order: string[] = [];
  for (const p of data) {
    const k = keyOf(p.date);
    if (!groups.has(k)) { groups.set(k, []); order.push(k); }
    groups.get(k)!.push(p);
  }
  const agg = order.map((k) => {
    const ps = groups.get(k)!;
    return {
      date: ps[0].date,                                  // 그룹 시작 일자
      open: ps[0].open,
      high: Math.max(...ps.map((p) => p.high)),
      low:  Math.min(...ps.map((p) => p.low)),
      close: ps[ps.length - 1].close,
      volume: ps.reduce((a, p) => a + (p.volume ?? 0), 0),
      ma20: null as number | null,
      ma60: null as number | null,
    };
  });
  // MA 는 집계 단위 위에서 재계산 (주봉 MA20 = 20주 평균)
  const closes = agg.map((p) => p.close);
  const rolling = (vals: number[], w: number): (number | null)[] => {
    const out: (number | null)[] = [];
    let sum = 0;
    for (let i = 0; i < vals.length; i++) {
      sum += vals[i];
      if (i >= w) sum -= vals[i - w];
      out.push(i >= w - 1 ? sum / w : null);
    }
    return out;
  };
  const m20 = rolling(closes, 20);
  const m60 = rolling(closes, 60);
  return agg.map((p, i) => ({ ...p, ma20: m20[i], ma60: m60[i] }));
}

export default function HomeTab({
  selectedStock, candleHistory, fin, latest, w52High, w52Low,
  fmtKRW, fmtEok, radarGroupEntries, newsItems,
  onGoDiagnosis, onGoNews,
}: HomeTabProps) {
  const [interval, setInterval] = useState<Interval>('D');
  const [showMA, setShowMA] = useState(true);

  // 집계 — D 는 그대로, W/M/Y 는 OHLC 합병
  const slicedCandles = useMemo(
    () => aggregate(candleHistory, interval),
    [candleHistory, interval],
  );

  // 기간 수익률 (전체 표시 구간)
  const periodReturn = useMemo(() => {
    if (slicedCandles.length < 2) return null;
    const first = slicedCandles[0].close;
    const last = slicedCandles[slicedCandles.length - 1].close;
    if (!first) return null;
    return (last / first - 1) * 100;
  }, [slicedCandles]);

  return (
    <div className="space-y-6">
      {/* 가격 차트 (일봉 캔들) */}
      <Card>
        <SectionHeader
          title="가격 차트"
          right={
            <span className="wp-t-sm text-[var(--text-tertiary)]">
              {slicedCandles.length > 0
                ? `${slicedCandles[0]?.date?.slice(5) ?? ''} ~ ${slicedCandles.at(-1)?.date?.slice(5) ?? ''} · ${slicedCandles.length} 거래일`
                : '데이터 없음'}
            </span>
          }
        />
        {/* 기간 탭 (일·주·월·년) + MA 토글 + 기간수익률 */}
        <div className="flex items-center justify-between gap-2 mt-3 mb-2">
          <div className="inline-flex rounded-lg overflow-hidden border border-[var(--border-default)]">
            {INTERVALS.map((iv) => (
              <button
                key={iv}
                onClick={() => setInterval(iv)}
                className={`px-4 py-1 wp-t-sm cursor-pointer transition-colors ${
                  interval === iv
                    ? 'font-bold text-white bg-[var(--accent-blue)]'
                    : 'font-normal text-[var(--text-secondary)] bg-[var(--bg-elev-1)] hover:bg-[var(--bg-elev-2)]'
                }`}
                style={{ minWidth: 44 }}
              >
                {INTERVAL_LABEL[iv]}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            {periodReturn != null && (
              <span
                className="wp-t-sm font-bold tabular-nums"
                style={{ color: periodReturn >= 0 ? '#E03B4B' : '#2E69F0' }}
              >
                {periodReturn >= 0 ? '+' : ''}{periodReturn.toFixed(2)}%
              </span>
            )}
            <label className="flex items-center gap-1 cursor-pointer wp-t-sm text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={showMA}
                onChange={(e) => setShowMA(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              MA
            </label>
          </div>
        </div>
        <div className="mt-2">
          <CandlestickChart
            data={slicedCandles}
            height={320}
            ma={showMA ? [20, 60] : []}
            showVolume
          />
          {slicedCandles.length > 0 && slicedCandles.length < 5 && (
            <div className="wp-t-sm text-[var(--text-tertiary)] mt-2 text-center">
              ⓘ 일부 구간 데이터 부재 — 신규상장 또는 데이터 적재 중일 수 있습니다.
            </div>
          )}
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
          {/* FE 평가 #7 — 단위·기준 명시 */}
          <div className="wp-t-xs text-[var(--text-tertiary)] mt-1">
            0~100 백분위 (전체 universe 재무 데이터 대비 순위)
          </div>
          {radarGroupEntries.length > 0 ? (
            <div className="space-y-2.5 mt-4">
              {radarGroupEntries.map((g) => (
                <div key={g.key} className="flex items-center gap-3"
                     title={`${g.label}: 전체 universe 백분위 ${g.score}점 (높을수록 우수)`}>
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
