import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  ReferenceLine, Tooltip,
} from 'recharts';

export interface DataPoint {
  date: string;
  score: number;
}

export interface LineChartProps {
  data: DataPoint[];
  /** @deprecated ResponsiveContainer 사용 — width 는 무시됨(호출부 호환 위해 남김) */
  width?: number;
  /** 차트 높이(px). 기본 240 */
  height?: number;
}

/**
 * LineChartImpl — recharts 실제 구현.
 *
 * recharts(~100KB gzip)를 초기 번들에서 분리하기 위해 LineChart.tsx 가
 * 이 모듈을 React.lazy 로 동적 import 한다. 직접 import 하지 말 것.
 */
export default function LineChartImpl({ data, height = 240 }: LineChartProps) {
  if (data.length < 2) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '13px',
          color: 'var(--text-tertiary)',
        }}
      >
        추이 데이터가 충분하지 않습니다.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 48, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="wp-lc-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent-blue)" stopOpacity={0.28} />
            <stop offset="100%" stopColor="var(--accent-blue)" stopOpacity={0.02} />
          </linearGradient>
        </defs>

        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
          tickLine={false}
          axisLine={{ stroke: 'var(--border-default)' }}
          minTickGap={40}
        />
        <YAxis
          domain={[0, 100]}
          ticks={[0, 50, 70, 100]}
          tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
          tickLine={false}
          axisLine={false}
          width={32}
        />

        {/* 기준선 — A티어(70) / 중립(50) */}
        <ReferenceLine
          y={70}
          stroke="#E03B4B"
          strokeDasharray="4 4"
          strokeOpacity={0.5}
          label={{ value: 'A티어', position: 'right', fontSize: 11, fill: '#E03B4B' }}
        />
        <ReferenceLine
          y={50}
          stroke="#9CA3AF"
          strokeDasharray="4 4"
          strokeOpacity={0.5}
          label={{ value: '중립', position: 'right', fontSize: 11, fill: '#9CA3AF' }}
        />

        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--bg-elev-1)',
            border: '1px solid var(--border-default)',
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: 'var(--text-tertiary)' }}
          formatter={(v: number | string) => [Number(v).toFixed(1), '스코어']}
        />

        <Area
          type="monotone"
          dataKey="score"
          stroke="var(--accent-blue)"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="url(#wp-lc-grad)"
          dot={false}
          activeDot={{ r: 4.5, fill: 'var(--accent-blue)', stroke: 'var(--bg-elev-1)', strokeWidth: 2 }}
          isAnimationActive
          animationDuration={900}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
