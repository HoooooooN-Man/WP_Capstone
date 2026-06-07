import { useMemo } from 'react';
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Bar, Cell,
  CartesianGrid, Line, ReferenceLine,
} from 'recharts';

export interface CandlePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  /** 미리 계산된 MA (외부에서 전체 history 로 계산해 슬라이스에도 끊김 없게) */
  ma20?: number | null;
  ma60?: number | null;
}

export interface CandlestickChartProps {
  data: CandlePoint[];
  /** @deprecated ResponsiveContainer 사용 */
  width?: number;
  /** 가격 차트 높이(px). 기본 320. 아래에 거래량 100px 추가 */
  height?: number;
  /** 이동평균선 (기본 [20, 60]). 빈 배열이면 미표시 */
  ma?: number[];
  /** 거래량 sub-chart 표시 (기본 true) */
  showVolume?: boolean;
}

const COLOR_UP = '#E03B4B';   // 한국식 상승
const COLOR_DN = '#2E69F0';   // 한국식 하락
const COLOR_MA20 = '#F0B429'; // 단기 MA
const COLOR_MA60 = '#8E44AD'; // 중기 MA

function rollingMean(values: (number | null)[], window: number): (number | null)[] {
  const out: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i < window - 1) { out.push(null); continue; }
    let sum = 0; let n = 0;
    for (let j = i - window + 1; j <= i; j++) {
      const v = values[j];
      if (v == null) { n = -1; break; }
      sum += v; n++;
    }
    out.push(n === window ? sum / window : null);
  }
  return out;
}

/**
 * 캔들스틱(일봉) + 이동평균선 + 거래량 sub-chart.
 *
 * - 가격 영역(상단): 캔들 + MA20·MA60 라인 + CartesianGrid + 첫/마지막 종가 ReferenceLine
 * - 거래량 영역(하단, 100px): Bar (상승=적, 하락=청)
 * - 한국식 색(상승 적·하락 청). recharts ComposedChart range Bar 로 OHLC 인코딩.
 *
 * recharts 코드분리 위해 CandlestickChart.tsx 가 lazy 로드.
 */
export default function CandlestickChartImpl({
  data, height = 320, ma = [20, 60], showVolume = true,
}: CandlestickChartProps) {
  const prepared = useMemo(() => {
    if (!data || data.length === 0) return [];
    const closes = data.map((p) => p.close);
    // 외부에서 ma20/ma60 미리 채워 들어오면 그것을 사용(슬라이스 시작점도 끊김 X).
    // 둘 다 없으면 슬라이스 내부에서 rolling — 호환성용.
    const hasExtMa20 = ma.includes(20) && data.some((p) => p.ma20 != null);
    const hasExtMa60 = ma.includes(60) && data.some((p) => p.ma60 != null);
    const ma20local = ma.includes(20) && !hasExtMa20 ? rollingMean(closes, 20) : null;
    const ma60local = ma.includes(60) && !hasExtMa60 ? rollingMean(closes, 60) : null;
    return data.map((p, i) => ({
      date: p.date,
      wick: [p.low, p.high] as [number, number],
      body: [Math.min(p.open, p.close), Math.max(p.open, p.close)] as [number, number],
      isUp: p.close >= p.open,
      open: p.open, high: p.high, low: p.low, close: p.close,
      volume: p.volume ?? 0,
      ma20: ma.includes(20) ? (hasExtMa20 ? (p.ma20 ?? null) : (ma20local ? ma20local[i] : null)) : null,
      ma60: ma.includes(60) ? (hasExtMa60 ? (p.ma60 ?? null) : (ma60local ? ma60local[i] : null)) : null,
    }));
  }, [data, ma]);

  if (prepared.length < 2) {
    return (
      <div style={{
        height: height + (showVolume ? 100 : 0),
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, color: 'var(--text-tertiary)',
      }}>
        캔들 데이터가 충분하지 않습니다.
      </div>
    );
  }

  const firstClose = prepared[0].close;
  const lastClose = prepared[prepared.length - 1].close;
  const xMargin = { top: 10, right: 30, bottom: 0, left: 0 };

  // X축 tick — 각 월의 *첫 일자*만 명시. recharts 자동 추출이 중복월/누락월을 유발하는 문제 회피.
  const monthFirstDates = (() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const p of prepared) {
      const ym = p.date.slice(0, 7);
      if (!seen.has(ym)) {
        seen.add(ym);
        out.push(p.date);
      }
    }
    return out;
  })();

  return (
    <div>
      {/* 가격 + MA */}
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={prepared}
          margin={xMargin}
          barCategoryGap={1}   /* 캔들 간 간격 따닥따닥 */
          barGap={0}
        >
          <CartesianGrid stroke="var(--border-default)" strokeDasharray="2 3" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--border-default)' }}
            ticks={monthFirstDates}
            interval={0}
            tickFormatter={(d: string) => `${parseInt(d.slice(5, 7), 10)}월`}
          />
          <YAxis
            yAxisId="price"
            tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
            tickLine={false}
            axisLine={false}
            width={64}
            domain={['dataMin', 'dataMax']}
            tickFormatter={(v: number) => v.toLocaleString('ko-KR')}
          />
          <Tooltip
            cursor={{ stroke: 'var(--text-tertiary)', strokeDasharray: '2 3' }}
            content={(args) => {
              if (!args.active || !args.payload || args.payload.length === 0) return null;
              const p = args.payload[0].payload as typeof prepared[number];
              const chg = p.close - p.open;
              const chgPct = p.open ? (chg / p.open) * 100 : 0;
              const chgColor = chg >= 0 ? COLOR_UP : COLOR_DN;
              return (
                <div style={{
                  backgroundColor: 'var(--bg-elev-1)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 8, padding: '8px 12px', fontSize: 12, minWidth: 180,
                }}>
                  <div style={{ color: 'var(--text-tertiary)', marginBottom: 4 }}>{p.date}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'auto auto', columnGap: 8, rowGap: 2 }}>
                    <span style={{ color: 'var(--text-tertiary)' }}>시</span><span>{p.open.toLocaleString('ko-KR')}</span>
                    <span style={{ color: 'var(--text-tertiary)' }}>고</span><span style={{ color: COLOR_UP }}>{p.high.toLocaleString('ko-KR')}</span>
                    <span style={{ color: 'var(--text-tertiary)' }}>저</span><span style={{ color: COLOR_DN }}>{p.low.toLocaleString('ko-KR')}</span>
                    <span style={{ color: 'var(--text-tertiary)' }}>종</span><span style={{ fontWeight: 700 }}>{p.close.toLocaleString('ko-KR')}</span>
                    <span style={{ color: 'var(--text-tertiary)' }}>변동</span>
                    <span style={{ color: chgColor, fontWeight: 700 }}>
                      {chg >= 0 ? '+' : ''}{chg.toLocaleString('ko-KR')} ({chgPct >= 0 ? '+' : ''}{chgPct.toFixed(2)}%)
                    </span>
                    {p.ma20 != null && (
                      <><span style={{ color: COLOR_MA20 }}>MA20</span><span>{Math.round(p.ma20).toLocaleString('ko-KR')}</span></>
                    )}
                    {p.ma60 != null && (
                      <><span style={{ color: COLOR_MA60 }}>MA60</span><span>{Math.round(p.ma60).toLocaleString('ko-KR')}</span></>
                    )}
                    {p.volume > 0 && (
                      <><span style={{ color: 'var(--text-tertiary)' }}>거래량</span><span>{p.volume.toLocaleString('ko-KR')}</span></>
                    )}
                  </div>
                </div>
              );
            }}
          />
          {/* 시작/종료 종가 reference */}
          <ReferenceLine yAxisId="price" y={firstClose} stroke="var(--text-tertiary)" strokeDasharray="3 4" strokeOpacity={0.35} />
          <ReferenceLine yAxisId="price" y={lastClose} stroke={lastClose >= firstClose ? COLOR_UP : COLOR_DN}
            strokeDasharray="3 4" strokeOpacity={0.6}
            label={{ value: `${lastClose.toLocaleString('ko-KR')}`, position: 'right', fontSize: 11,
                     fill: lastClose >= firstClose ? COLOR_UP : COLOR_DN }} />

          {/* 단일 range Bar(low~high) + Custom shape — wick(중앙선) + body(박스) 같은 X 좌표 보장 */}
          <Bar
            yAxisId="price"
            dataKey="wick"
            isAnimationActive={false}
            // recharts 가 wick(low,high) 의 픽셀 box (x,y,width,height) 를 제공.
            // 그 box 내부에서 wick 세로선(중앙) + body 박스(open~close 비율 위치) 를 SVG 로 그림.
            shape={(props: {
              x?: number; y?: number; width?: number; height?: number;
              payload?: typeof prepared[number];
            }) => {
              const { x = 0, y = 0, width = 0, height = 0, payload } = props;
              if (!payload) return <g />;
              const cx = x + width / 2;
              const color = payload.isUp ? COLOR_UP : COLOR_DN;
              const lo = payload.low, hi = payload.high;
              const op = payload.open, cl = payload.close;
              const range = hi - lo || 1;
              const topVal = Math.max(op, cl);
              const botVal = Math.min(op, cl);
              // wick (low~high) 가 (y, y+height) 픽셀에 매핑됨.
              // val → pixel: (hi - val) / range × height + y
              const bodyTopY = y + ((hi - topVal) / range) * height;
              const bodyBotY = y + ((hi - botVal) / range) * height;
              const bodyH = Math.max(1, bodyBotY - bodyTopY);
              const bodyW = Math.max(2, Math.min(10, width * 0.72));
              return (
                <g>
                  <line x1={cx} y1={y} x2={cx} y2={y + height}
                    stroke={color} strokeWidth={1.2} />
                  <rect x={cx - bodyW / 2} y={bodyTopY}
                    width={bodyW} height={bodyH} fill={color} />
                </g>
              );
            }}
          />
          {ma.includes(20) && (
            <Line yAxisId="price" type="monotone" dataKey="ma20" stroke={COLOR_MA20}
              strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls />
          )}
          {ma.includes(60) && (
            <Line yAxisId="price" type="monotone" dataKey="ma60" stroke={COLOR_MA60}
              strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* 거래량 sub-chart */}
      {showVolume && (
        <ResponsiveContainer width="100%" height={100}>
          <ComposedChart
            data={prepared}
            margin={{ top: 6, right: 30, bottom: 0, left: 0 }}
            barCategoryGap={1}
            barGap={0}
          >
            <CartesianGrid stroke="var(--border-default)" strokeDasharray="2 3" vertical={false} />
            <XAxis dataKey="date" tick={false} axisLine={{ stroke: 'var(--border-default)' }} />
            <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} tickLine={false} axisLine={false}
              width={64} tickFormatter={(v: number) => v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `${(v/1e3).toFixed(0)}K` : `${v}`} />
            <Bar dataKey="volume" isAnimationActive={false}>
              {prepared.map((d, i) => <Cell key={`v-${i}`} fill={d.isUp ? COLOR_UP : COLOR_DN} fillOpacity={0.55} />)}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {/* MA 범례 */}
      {(ma.includes(20) || ma.includes(60)) && (
        <div style={{
          display: 'flex', gap: 12, marginTop: 4, paddingLeft: 64,
          fontSize: 11, color: 'var(--text-tertiary)',
        }}>
          {ma.includes(20) && <span><span style={{ color: COLOR_MA20 }}>━</span> MA20</span>}
          {ma.includes(60) && <span><span style={{ color: COLOR_MA60 }}>━</span> MA60</span>}
        </div>
      )}
    </div>
  );
}
