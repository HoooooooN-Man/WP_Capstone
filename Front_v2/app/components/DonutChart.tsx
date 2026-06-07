/**
 * DonutChart — 비중 도넛 차트
 *
 * 리디자인(Frontend_Redesign_Plan P2-11): 포트폴리오 종목별 비중 등 구성비를
 * 시각 앵커로 표시. 범례 포함.
 */
interface DonutSlice {
  label: string;
  value: number;
}

interface DonutChartProps {
  data: DonutSlice[];
  size?: number;
  thickness?: number;
  centerLabel?: string;
  centerSub?: string;
}

const PALETTE = [
  '#3D7BD9', '#E03B4B', '#E08E3C', '#56B68B',
  '#8C6FD6', '#4FA8C9', '#D17BA8', '#8A93A0',
];

export default function DonutChart({
  data, size = 160, thickness = 26, centerLabel, centerSub,
}: DonutChartProps) {
  const total = data.reduce((s, d) => s + (d.value > 0 ? d.value : 0), 0);
  const r = (size - thickness) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;

  let offset = 0;
  const segments = total > 0
    ? data.map((d, i) => {
        const frac = Math.max(0, d.value) / total;
        const seg = {
          color: PALETTE[i % PALETTE.length],
          dash: frac * circ,
          gap: circ - frac * circ,
          rotation: (offset / circ) * 360,
          pct: frac * 100,
          label: d.label,
        };
        offset += frac * circ;
        return seg;
      })
    : [];

  return (
    <div className="flex items-center gap-5">
      <svg width={size} height={size} style={{ flexShrink: 0 }}>
        {total > 0 ? (
          segments.map((s, i) => (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={s.color}
              strokeWidth={thickness}
              strokeDasharray={`${s.dash} ${s.gap}`}
              transform={`rotate(${-90 + s.rotation} ${cx} ${cy})`}
              strokeLinecap="butt"
            />
          ))
        ) : (
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--bg-elev-2)" strokeWidth={thickness} />
        )}
        {centerLabel && (
          <text
            x={cx} y={cy - 2} textAnchor="middle"
            style={{ fontSize: '18px', fontWeight: 800, fill: 'var(--text-primary)' }}
          >
            {centerLabel}
          </text>
        )}
        {centerSub && (
          <text
            x={cx} y={cy + 16} textAnchor="middle"
            style={{ fontSize: '11px', fill: 'var(--text-tertiary)' }}
          >
            {centerSub}
          </text>
        )}
      </svg>

      {/* 범례 */}
      <div className="space-y-1.5 min-w-0">
        {segments.map((s, i) => (
          <div key={i} className="flex items-center gap-2" style={{ fontSize: '13px' }}>
            <span
              style={{ width: '10px', height: '10px', borderRadius: '3px', backgroundColor: s.color, flexShrink: 0 }}
            />
            <span
              style={{
                color: 'var(--text-secondary)', overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '110px',
              }}
            >
              {s.label}
            </span>
            <span className="tabular-nums" style={{ color: 'var(--text-primary)', fontWeight: 700, marginLeft: 'auto' }}>
              {s.pct.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
