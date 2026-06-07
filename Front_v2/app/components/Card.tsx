import type { CSSProperties, ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  /** 내부 패딩(p-6) 사용. 헤더+리스트형 카드는 false 로 두고 내부에서 패딩 제어. 기본 true */
  padded?: boolean;
  style?: CSSProperties;
  onClick?: () => void;
}

/**
 * Card — bg-elev-1 + border-default + rounded-xl 표준 카드.
 * Front_v2 전반에 흩어진 `p-6 rounded-xl` 인라인 카드를 일원화한다.
 */
export default function Card({ children, className = '', padded = true, style, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={`rounded-xl ${padded ? 'p-6' : 'overflow-hidden'} ${onClick ? 'cursor-pointer' : ''} ${className}`}
      style={{
        backgroundColor: 'var(--bg-elev-1)',
        border: '1px solid var(--border-default)',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
