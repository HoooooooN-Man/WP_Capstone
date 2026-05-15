interface TrendMarker {
  short: 'up' | 'neutral' | 'down';
  medium: 'up' | 'neutral' | 'down';
  long: 'up' | 'neutral' | 'down';
}

interface WinnerCardProps {
  name: string;
  ticker: string;
  recommendPrice: number;
  score: number;
  targetPrice: number;
  trend: TrendMarker;
  cumulativeReturn: number;
  isLocked?: boolean;
}

export default function WinnerCard({
  name,
  ticker,
  recommendPrice,
  score,
  targetPrice,
  trend,
  cumulativeReturn,
  isLocked = false,
}: WinnerCardProps) {
  const getTrendIcon = (direction: 'up' | 'neutral' | 'down') => {
    if (direction === 'up') return '▲';
    if (direction === 'down') return '▼';
    return '●';
  };

  const getTrendColor = (direction: 'up' | 'neutral' | 'down') => {
    if (direction === 'up') return 'var(--color-up)';
    if (direction === 'down') return 'var(--color-down)';
    return 'var(--color-neutral)';
  };

  const returnColor = cumulativeReturn >= 0 ? 'var(--color-up)' : 'var(--color-down)';

  return (
    <div
      className="rounded-xl p-5 transition-all relative"
      style={{
        width: '220px',
        minHeight: '320px',
        backgroundColor: 'var(--bg-elev-1)',
        border: '1px solid var(--border-default)',
        filter: isLocked ? 'blur(4px)' : 'none',
        opacity: isLocked ? 0.6 : 1,
      }}
    >
      <div className="space-y-4">
        <div className="text-center pb-3" style={{ borderBottom: '1px solid var(--border-default)' }}>
          <div
            style={{
              fontSize: '18px',
              fontWeight: 700,
              lineHeight: '24px',
              color: 'var(--text-primary)',
              marginBottom: '2px',
            }}
          >
            {name}
          </div>
          <div style={{ fontSize: '12px', lineHeight: '16px', color: 'var(--text-tertiary)' }}>{ticker}</div>
        </div>

        <div>
          <div style={{ fontSize: '12px', lineHeight: '16px', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
            추천가
          </div>
          <div
            className="tabular-nums"
            style={{ fontSize: '20px', fontWeight: 700, lineHeight: '28px', color: 'var(--text-primary)' }}
          >
            {recommendPrice.toLocaleString('ko-KR')}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '12px', lineHeight: '16px', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
            스코어
          </div>
          <div
            className="tabular-nums"
            style={{ fontSize: '20px', fontWeight: 700, lineHeight: '28px', color: 'var(--accent-blue)' }}
          >
            {score.toFixed(1)}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '12px', lineHeight: '16px', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
            목표가
          </div>
          <div
            className="tabular-nums"
            style={{ fontSize: '20px', fontWeight: 700, lineHeight: '28px', color: 'var(--text-primary)' }}
          >
            {targetPrice > 0 ? targetPrice.toLocaleString('ko-KR') : '-'}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '12px', lineHeight: '16px', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
            추세
          </div>
          <div className="flex items-center gap-2">
            <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>단</span>
            <span style={{ fontSize: '14px', color: getTrendColor(trend.short) }}>{getTrendIcon(trend.short)}</span>
            <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>중</span>
            <span style={{ fontSize: '14px', color: getTrendColor(trend.medium) }}>{getTrendIcon(trend.medium)}</span>
            <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>장</span>
            <span style={{ fontSize: '14px', color: getTrendColor(trend.long) }}>{getTrendIcon(trend.long)}</span>
          </div>
        </div>

        <div className="pt-3" style={{ borderTop: '1px solid var(--border-default)' }}>
          <div
            className="tabular-nums"
            style={{
              fontSize: '16px',
              fontWeight: 700,
              lineHeight: '24px',
              color: returnColor,
              textAlign: 'center',
            }}
          >
            추천 후 {cumulativeReturn >= 0 ? '+' : ''}
            {cumulativeReturn.toFixed(1)}%
          </div>
        </div>
      </div>

      {isLocked && (
        <div
          className="absolute inset-0 flex flex-col items-center justify-center rounded-xl"
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔒</div>
          <div
            style={{
              fontSize: '14px',
              fontWeight: 700,
              color: '#FFFFFF',
              marginBottom: '12px',
            }}
          >
            로그인하고 더 보기
          </div>
          <button
            className="px-4 py-2 rounded-lg"
            style={{
              backgroundColor: 'var(--accent-blue)',
              color: '#FFFFFF',
              fontSize: '12px',
              fontWeight: 700,
            }}
            onClick={() => (window.location.href = '/login')}
          >
            로그인
          </button>
        </div>
      )}
    </div>
  );
}
