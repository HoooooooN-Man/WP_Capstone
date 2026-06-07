/**
 * PageErrorState — 페이지 레벨 에러/빈 상태 공통 컴포넌트.
 *
 * useQuery 의 isError 또는 데이터 없을 때 일관된 UI 로 표시.
 *
 * Usage:
 *   if (isError) return <PageErrorState type="error" />;
 *   if (!isLoading && items.length === 0) return <PageErrorState type="empty" />;
 */

interface PageErrorStateProps {
  type?: 'error' | 'empty' | 'auth';
  title?: string;
  description?: string;
  /** description 의 별칭 — 호출부 호환용 */
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function PageErrorState({
  type = 'error',
  title,
  description,
  message,
  actionLabel,
  onAction,
}: PageErrorStateProps) {
  const presets = {
    error: {
      title: '데이터를 불러올 수 없습니다',
      description: '서버 연결을 확인해 주세요. (백엔드 :8001 / :8000 실행 중인지 확인)',
      actionLabel: '다시 시도',
      onAction: () => window.location.reload(),
      icon: '⚠',
      color: 'var(--color-down)',
    },
    empty: {
      title: '데이터가 없습니다',
      description: '필터 조건을 바꾸거나 잠시 후 다시 확인해 주세요.',
      actionLabel: '',
      onAction: () => {},
      icon: '○',
      color: 'var(--text-tertiary)',
    },
    auth: {
      title: '로그인이 필요합니다',
      description: '이 페이지를 보려면 로그인하세요.',
      actionLabel: '로그인하기',
      onAction: () => { window.location.href = '/login'; },
      icon: '◉',
      color: 'var(--accent-blue)',
    },
  };

  const preset = presets[type];
  const finalTitle = title ?? preset.title;
  const finalDesc = description ?? message ?? preset.description;
  const finalAction = actionLabel ?? preset.actionLabel;
  const finalOnAction = onAction ?? preset.onAction;

  return (
    <div
      className="flex flex-col items-center justify-center text-center py-16 px-6 rounded-xl"
      style={{
        backgroundColor: 'var(--bg-elev-1)',
        border: '1px solid var(--border)',
        minHeight: '320px',
      }}
    >
      <div
        className="flex items-center justify-center rounded-full mb-4"
        style={{
          width: '64px',
          height: '64px',
          backgroundColor: 'var(--bg-elev-2)',
          color: preset.color,
          fontSize: '32px',
          fontWeight: 700,
        }}
      >
        {preset.icon}
      </div>
      <div
        style={{
          fontSize: '20px',
          fontWeight: 700,
          lineHeight: '28px',
          color: 'var(--text-primary)',
          marginBottom: '8px',
        }}
      >
        {finalTitle}
      </div>
      <div
        style={{
          fontSize: '14px',
          lineHeight: '20px',
          color: 'var(--text-secondary)',
          marginBottom: finalAction ? '20px' : 0,
          maxWidth: '480px',
        }}
      >
        {finalDesc}
      </div>
      {finalAction && (
        <button
          onClick={finalOnAction}
          className="px-6 py-2 rounded-lg transition-all duration-150"
          style={{
            backgroundColor: 'var(--accent-blue)',
            color: '#FFFFFF',
            fontSize: '14px',
            fontWeight: 700,
            border: 'none',
            cursor: 'pointer',
          }}
        >
          {finalAction}
        </button>
      )}
    </div>
  );
}
