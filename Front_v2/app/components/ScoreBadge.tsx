/**
 * ScoreBadge — 스마트스코어 + 등급
 *
 * 리디자인(Frontend_Redesign_Plan P0): 회색 테두리 원 → 등급색 채움 배지.
 * 제품의 핵심 자산인 점수를 시각적으로 강조한다.
 *  - lg : 종목상세 히어로용 (큰 원 + 점수 + 등급 라벨)
 *  - sm : 리스트 행 인라인용 (점수 + 작은 등급 pill)
 */
interface ScoreBadgeProps {
  score: number;
  tier: 'A' | 'B' | 'C' | 'D';
  size?: 'sm' | 'lg';
}

// 등급별 색 — 진한색(채움) / 연한 배경(서브)
const TIER = {
  A: { solid: '#E03B4B', soft: 'rgba(224,59,75,0.12)', label: '우수' },
  B: { solid: '#E08E3C', soft: 'rgba(224,142,60,0.14)', label: '양호' },
  C: { solid: '#8A93A0', soft: 'rgba(138,147,160,0.14)', label: '보통' },
  D: { solid: '#3D7BD9', soft: 'rgba(61,123,217,0.12)', label: '주의' },
} as const;

export default function ScoreBadge({ score, tier, size = 'lg' }: ScoreBadgeProps) {
  const t = TIER[tier] ?? TIER.C;
  const scoreText = Number.isFinite(score) ? score.toFixed(1) : '—';

  if (size === 'sm') {
    return (
      <div className="inline-flex items-center gap-1.5">
        <span
          className="tabular-nums"
          style={{ fontSize: '20px', fontWeight: 800, lineHeight: '24px', color: 'var(--text-primary)' }}
        >
          {scoreText}
        </span>
        <span
          className="flex items-center justify-center rounded-md"
          style={{
            minWidth: '22px', height: '22px', padding: '0 5px',
            backgroundColor: t.solid, color: '#FFFFFF',
            fontSize: '13px', fontWeight: 800, lineHeight: 1,
          }}
        >
          {tier}
        </span>
      </div>
    );
  }

  // lg — 채움 원형 배지
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className="flex flex-col items-center justify-center rounded-full"
        style={{
          width: '88px', height: '88px',
          background: `linear-gradient(135deg, ${t.solid} 0%, ${t.solid}cc 100%)`,
          color: '#FFFFFF',
          boxShadow: `0 6px 18px ${t.soft.replace('0.1', '0.35')}`,
        }}
      >
        <div className="tabular-nums" style={{ fontSize: '30px', fontWeight: 800, lineHeight: 1 }}>
          {scoreText}
        </div>
        <div style={{ fontSize: '13px', fontWeight: 700, opacity: 0.92, marginTop: '2px' }}>
          {tier} · {t.label}
        </div>
      </div>
    </div>
  );
}
