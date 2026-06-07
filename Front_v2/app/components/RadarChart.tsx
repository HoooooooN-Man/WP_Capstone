interface RadarChartProps {
  stockData: {
    growth: number;
    profitability: number;
    safety: number;
    monopoly: number;
    cashflow: number;
  };
  sectorAvg?: {
    growth: number;
    profitability: number;
    safety: number;
    monopoly: number;
    cashflow: number;
  };
}

export default function RadarChart({ stockData, sectorAvg }: RadarChartProps) {
  const factors = [
    { label: '성장성', key: 'growth' as const, angle: -90 },
    { label: '수익성', key: 'profitability' as const, angle: -18 },
    { label: '안전성', key: 'safety' as const, angle: 54 },
    { label: '현금창출', key: 'cashflow' as const, angle: 126 },
    { label: '독점력', key: 'monopoly' as const, angle: 198 },
  ];

  const center = 200;
  const maxRadius = 130;

  const polarToCartesian = (angle: number, radius: number) => {
    const rad = (angle * Math.PI) / 180;
    return {
      x: center + radius * Math.cos(rad),
      y: center + radius * Math.sin(rad),
    };
  };

  const getPoints = (data: typeof stockData) => {
    return factors
      .map((factor) => {
        const value = data[factor.key];
        const radius = (value / 100) * maxRadius;
        return polarToCartesian(factor.angle, radius);
      })
      .map((p) => `${p.x},${p.y}`)
      .join(' ');
  };

  const stockPoints = getPoints(stockData);
  const sectorPoints = sectorAvg ? getPoints(sectorAvg) : '';

  return (
    <div className="flex flex-col items-center">
      <svg width="400" height="400" viewBox="0 0 400 400">
        {[20, 40, 60, 80, 100].map((percent) => {
          const radius = (percent / 100) * maxRadius;
          const gridPoints = factors
            .map((factor) => polarToCartesian(factor.angle, radius))
            .map((p) => `${p.x},${p.y}`)
            .join(' ');
          const isOuter = percent === 100;
          return (
            <polygon
              key={percent}
              points={gridPoints}
              fill={percent === 100 ? 'var(--bg-elev-2)' : 'none'}
              fillOpacity={percent === 100 ? 0.35 : 0}
              stroke="var(--text-tertiary)"
              strokeWidth={isOuter ? 1.5 : 1}
              opacity={isOuter ? 0.55 : 0.32}
            />
          );
        })}

        {factors.map((factor) => {
          const end = polarToCartesian(factor.angle, maxRadius);
          return (
            <line
              key={factor.key}
              x1={center}
              y1={center}
              x2={end.x}
              y2={end.y}
              stroke="var(--text-tertiary)"
              strokeWidth="1"
              opacity="0.4"
            />
          );
        })}

        {sectorAvg && (
          <polygon
            points={sectorPoints}
            fill="none"
            stroke="var(--text-tertiary)"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />
        )}

        <polygon
          points={stockPoints}
          fill="rgba(59, 130, 246, 0.15)"
          stroke="var(--accent-blue)"
          strokeWidth="2"
        />

        {factors.map((factor) => {
          const labelPos = polarToCartesian(factor.angle, maxRadius + 40);
          const value = stockData[factor.key];
          return (
            <g key={factor.key}>
              <text
                x={labelPos.x}
                y={labelPos.y}
                textAnchor="middle"
                dominantBaseline="middle"
                style={{
                  fontSize: '14px',
                  fontWeight: 700,
                  fill: 'var(--text-primary)',
                }}
              >
                {factor.label}
              </text>
              <text
                x={labelPos.x}
                y={labelPos.y + 18}
                textAnchor="middle"
                dominantBaseline="middle"
                style={{
                  fontSize: '12px',
                  fill: 'var(--text-secondary)',
                }}
              >
                {value}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="flex items-center gap-4 mt-4">
        <div className="flex items-center gap-2">
          <div
            style={{
              width: '16px',
              height: '2px',
              backgroundColor: 'var(--accent-blue)',
            }}
          />
          <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>종목</span>
        </div>
        {sectorAvg && (
          <div className="flex items-center gap-2">
            <div
              style={{
                width: '16px',
                height: '2px',
                backgroundColor: 'var(--text-tertiary)',
                backgroundImage: 'repeating-linear-gradient(to right, var(--text-tertiary) 0, var(--text-tertiary) 4px, transparent 4px, transparent 8px)',
              }}
            />
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>섹터 평균</span>
          </div>
        )}
      </div>
    </div>
  );
}
