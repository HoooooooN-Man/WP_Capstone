import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function EmptyState({
  title = '데이터가 없습니다',
  description = '조건에 맞는 종목을 찾을 수 없습니다.',
  actionLabel = '검색 조건 변경',
  onAction,
}: EmptyStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-xl p-12"
      style={{
        backgroundColor: 'var(--bg-elev-1)',
        border: '1px solid var(--border-default)',
        minHeight: '240px',
      }}
    >
      <Inbox size={64} style={{ color: 'var(--text-tertiary)', marginBottom: '16px' }} strokeWidth={1} />
      <div style={{ fontSize: '20px', fontWeight: 700, lineHeight: '28px', color: 'var(--text-primary)', marginBottom: '8px' }}>
        {title}
      </div>
      <div style={{ fontSize: '14px', lineHeight: '20px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
        {description}
      </div>
      {onAction && (
        <button
          onClick={onAction}
          className="px-6 py-2 rounded-lg"
          style={{
            fontSize: '14px',
            fontWeight: 700,
            backgroundColor: 'var(--accent-blue)',
            color: '#FFFFFF',
          }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
