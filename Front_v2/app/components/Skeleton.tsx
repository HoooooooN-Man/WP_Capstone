/**
 * Skeleton — 로딩 플레이스홀더 프리미티브
 *
 * "불러오는 중…" 텍스트 대신 콘텐츠 형태의 회색 블록을 펄스 애니메이션으로 표시한다.
 */
interface SkeletonProps {
  width?: number | string;
  height?: number | string;
  radius?: number;
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ width = '100%', height = 16, radius = 8, className = '', style }: SkeletonProps) {
  return (
    <div
      className={`wp-skeleton ${className}`}
      style={{ width, height, borderRadius: radius, ...style }}
    />
  );
}

/** 리스트 행 형태 스켈레톤 (로고 + 2줄 텍스트 + 우측 숫자) */
export function RowSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 px-5"
          style={{ height: '92px', borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-base)' }}
        >
          <Skeleton width={40} height={40} radius={20} />
          <div className="flex-1 space-y-2">
            <Skeleton width={160} height={18} />
            <Skeleton width={100} height={13} />
          </div>
          <Skeleton width={80} height={32} />
          <Skeleton width={90} height={18} />
        </div>
      ))}
    </div>
  );
}

/** 카드 그리드 스켈레톤 */
export function CardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="flex flex-col sm:flex-row gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex-1 rounded-2xl p-5 space-y-4"
          style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border)' }}
        >
          <div className="flex items-center justify-between">
            <Skeleton width={52} height={52} radius={26} />
            <Skeleton width={88} height={88} radius={44} />
          </div>
          <Skeleton width={140} height={22} />
          <Skeleton width={90} height={14} />
          <Skeleton width="100%" height={36} />
        </div>
      ))}
    </div>
  );
}
