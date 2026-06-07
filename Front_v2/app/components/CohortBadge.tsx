// 투자 성향(cohort) 배지 — 백엔드 cohort 키(영문)를 받아 한글 라벨·색으로 표시
type CohortKey = 'conservative' | 'balanced' | 'growth' | 'dividend' | 'value';

interface CohortBadgeProps {
  cohort: CohortKey | string;
}

const COHORT_STYLES: Record<CohortKey, { label: string; bg: string; text: string; icon: string }> = {
  conservative: { label: '보수형', bg: '#DBEAFE', text: '#1E40AF', icon: '🛡️' },
  balanced:     { label: '균형',   bg: '#F3F4F6', text: '#4B5563', icon: '⚖️' },
  growth:       { label: '성장',   bg: '#FEE2E2', text: '#B91C1C', icon: '🌱' },
  dividend:     { label: '배당',   bg: '#FEF3C7', text: '#92400E', icon: '💰' },
  value:        { label: '가치',   bg: '#DCFCE7', text: '#15803D', icon: '💎' },
};

export default function CohortBadge({ cohort }: CohortBadgeProps) {
  const styles = COHORT_STYLES[cohort as CohortKey] ?? COHORT_STYLES.balanced;

  return (
    <div
      className="inline-flex items-center gap-1 px-2 py-1 rounded"
      style={{
        backgroundColor: styles.bg,
        color: styles.text,
        fontSize: '12px',
        fontWeight: 700,
        lineHeight: '16px',
      }}
    >
      <span>{styles.icon}</span>
      {styles.label}
    </div>
  );
}
