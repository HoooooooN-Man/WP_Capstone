import { useState, type CSSProperties } from 'react';
import { TrendingUp } from 'lucide-react';

interface NewsThumbnailProps {
  imageUrl?: string | null;
  className?: string;
  /** 아이콘 폴백 크기 (px) */
  iconSize?: number;
}

/**
 * 뉴스 카드 썸네일.
 * imageUrl 이 있으면 이미지, 없거나 로드 실패 시 TrendingUp 아이콘 폴백.
 * 컨테이너 크기는 부모(`className`)가 결정한다 — 컴포넌트는 채우기만 한다.
 */
const FILL: CSSProperties = { width: '100%', height: '100%', objectFit: 'cover' };

export default function NewsThumbnail({ imageUrl, className, iconSize = 22 }: NewsThumbnailProps) {
  const [failed, setFailed] = useState(false);
  const showImage = !!imageUrl && !failed;
  return (
    <div
      className={`flex-shrink-0 rounded-lg overflow-hidden flex items-center justify-center bg-[var(--bg-elev-2)] ${className ?? ''}`}
    >
      {showImage ? (
        <img
          src={imageUrl ?? ''}
          alt=""
          style={FILL}
          onError={() => setFailed(true)}
        />
      ) : (
        <TrendingUp size={iconSize} style={{ color: 'var(--text-tertiary)' }} />
      )}
    </div>
  );
}
