import type { ReactNode } from 'react';

interface SectionHeaderProps {
  title: string;
  /** 부제목 — 제목 아래 작은 글씨 */
  sub?: string;
  /** 우측 보조 영역 — 기간 라벨·액션 버튼 등 */
  right?: ReactNode;
  className?: string;
}

/**
 * SectionHeader — 카드/섹션 상단의 제목 + 우측 보조영역 표준 헤더.
 */
export default function SectionHeader({ title, sub, right, className = '' }: SectionHeaderProps) {
  return (
    <div className={`flex items-baseline justify-between gap-3 ${className}`}>
      <div className="min-w-0">
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)' }}>{title}</h2>
        {sub && (
          <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginTop: 2 }}>{sub}</p>
        )}
      </div>
      {right && <div className="flex-shrink-0">{right}</div>}
    </div>
  );
}
