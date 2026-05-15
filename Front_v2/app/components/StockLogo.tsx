/**
 * StockLogo — 종목 식별 로고
 *
 * 외부 로고 자산이 없으므로 ticker 해시 기반의 결정적 색상 + 종목명 이니셜 원형으로
 * 폴백한다. 모든 리스트·상세 행에 투입해 시각적 텍스처와 인지 속도를 높인다.
 */
interface StockLogoProps {
  ticker: string;
  name?: string;
  size?: number;
}

// 라이트/다크 양쪽에서 무난한 채도 낮춘 팔레트
const PALETTE = [
  '#5B8DEF', '#E0746B', '#56B68B', '#C9914A',
  '#8C6FD6', '#4FA8C9', '#D17BA8', '#6FAF5C',
  '#E08E3C', '#5F7BC4',
];

export default function StockLogo({ ticker, name, size = 40 }: StockLogoProps) {
  const key = ticker || name || '';
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  }
  const color = PALETTE[hash % PALETTE.length];
  const label = (name || ticker || '?').trim();
  const initial = label.charAt(0).toUpperCase();

  return (
    <div
      className="flex items-center justify-center rounded-full flex-shrink-0 select-none"
      style={{
        width: size,
        height: size,
        backgroundColor: color,
        color: '#FFFFFF',
        fontSize: Math.round(size * 0.42),
        fontWeight: 700,
        lineHeight: 1,
      }}
      aria-hidden="true"
    >
      {initial}
    </div>
  );
}
