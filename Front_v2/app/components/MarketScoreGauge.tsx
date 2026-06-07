/**
 * MarketScoreGauge — 단일 연속 그라데이션 반원 게이지.
 *
 * 5 구간을 SVG linearGradient 의 stop 으로 인코딩 → 끊김 없는 연속 호로 표시.
 * 구간 라벨(호 바깥) + 눈금(호 안쪽) + 바늘 + 점수 + 상태 메시지.
 */
interface MarketScoreGaugeProps {
  score: number;
}

const ZONES = [
  { min: 0,   max: 20,  label: '공포', color: '#3B6FD4' },
  { min: 20,  max: 40,  label: '불안', color: '#5BA0E0' },
  { min: 40,  max: 60,  label: '보통', color: '#8A93A0' },
  { min: 60,  max: 80,  label: '과욕', color: '#F0B429' },
  { min: 80,  max: 100, label: '탐욕', color: '#E0564E' },
];

const MESSAGES: Record<string, string> = {
  공포: '극단적 공포 — 저가 매수 기회를 검토하세요.',
  불안: '시장 불안이 이어지는 관망 국면입니다.',
  보통: '뚜렷한 방향성 없는 중립 국면입니다.',
  과욕: '낙관론이 우세한 시장 분위기입니다.',
  탐욕: '과열 구간 — 차익 실현을 검토하세요.',
};

export default function MarketScoreGauge({ score }: MarketScoreGaugeProps) {
  const s = Math.max(0, Math.min(100, score));
  const active = ZONES.find((z) => s < z.max) ?? ZONES[ZONES.length - 1];

  // 기하 — 상단 반원 (좌 0 → 우 100)
  const cx = 150, cy = 142, R = 98, band = 22;

  const pt = (val: number, radius: number) => {
    const ang = Math.PI * (1 - val / 100); // 180°(좌) → 0°(우)
    return { x: cx + radius * Math.cos(ang), y: cy - radius * Math.sin(ang) };
  };
  const arc = (v1: number, v2: number, radius: number) => {
    const a = pt(v1, radius);
    const b = pt(v2, radius);
    return `M ${a.x.toFixed(2)} ${a.y.toFixed(2)} A ${radius} ${radius} 0 0 1 ${b.x.toFixed(2)} ${b.y.toFixed(2)}`;
  };

  const needle = pt(s, R - band / 2 - 8);

  // 5 ZONE 중앙값에 색 stop — 0% / 50% / ... / 100% 분포로 부드럽게 보간
  // linearGradient 는 좌→우 (반원 호의 x 진행 방향과 일치)
  return (
    <div className="flex flex-col items-center" style={{ width: '100%', maxWidth: '320px' }}>
      <svg viewBox="0 0 300 200" width="100%" style={{ maxWidth: '300px' }}>
        <defs>
          <linearGradient id="wp-gauge-grad" x1="0" y1="0" x2="1" y2="0">
            {ZONES.map((z, i) => (
              <stop
                key={z.label}
                offset={`${(i / (ZONES.length - 1)) * 100}%`}
                stopColor={z.color}
              />
            ))}
          </linearGradient>
        </defs>

        {/* 단일 연속 호 (0 → 100) — 끊김 없음, 그라데이션 채색 */}
        <path
          d={arc(0.5, 99.5, R)}
          fill="none"
          stroke="url(#wp-gauge-grad)"
          strokeWidth={band}
          strokeLinecap="round"
        />

        {/* 구간 라벨 — 호 바깥 */}
        {ZONES.map((z) => {
          const p = pt((z.min + z.max) / 2, R + 30);
          const isActive = z.label === active.label;
          return (
            <text
              key={z.label}
              x={p.x}
              y={p.y + 4}
              textAnchor="middle"
              style={{
                fontSize: '13px',
                fontWeight: isActive ? 800 : 600,
                fill: isActive ? z.color : 'var(--text-tertiary)',
              }}
            >
              {z.label}
            </text>
          );
        })}

        {/* 눈금 — 호 안쪽 */}
        {[0, 25, 50, 75, 100].map((t) => {
          const p = pt(t, R - band / 2 - 13);
          return (
            <text
              key={t}
              x={p.x}
              y={p.y + 4}
              textAnchor="middle"
              className="tabular-nums"
              style={{ fontSize: '11px', fill: 'var(--text-tertiary)' }}
            >
              {t}
            </text>
          );
        })}

        {/* 바늘 */}
        <line
          x1={cx}
          y1={cy}
          x2={needle.x}
          y2={needle.y}
          stroke="var(--text-secondary)"
          strokeWidth="4.5"
          strokeLinecap="round"
          style={{ transition: 'all 0.6s cubic-bezier(0.34, 1.4, 0.64, 1)' }}
        />

        {/* 허브 */}
        <circle cx={cx} cy={cy} r="13" fill="var(--bg-elev-1)" stroke="var(--border-default)" strokeWidth="1.5" />
        <circle cx={cx} cy={cy} r="5" fill="var(--text-secondary)" />

        {/* 점수 */}
        <text
          x={cx}
          y={cy + 44}
          textAnchor="middle"
          className="tabular-nums"
          style={{ fontSize: '36px', fontWeight: 800, fill: 'var(--text-primary)' }}
        >
          {Math.round(s)}
        </text>
      </svg>

      {/* 상태 메시지 */}
      <div
        className="mt-2 px-4 py-2.5 rounded-xl text-center"
        style={{
          backgroundColor: `color-mix(in srgb, ${active.color} 12%, transparent)`,
          fontSize: '14px',
          color: 'var(--text-secondary)',
          fontWeight: 500,
        }}
      >
        {MESSAGES[active.label]}
      </div>
    </div>
  );
}
