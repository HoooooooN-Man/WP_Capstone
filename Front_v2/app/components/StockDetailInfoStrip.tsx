/**
 * StockDetailInfoStrip — PRD §4.6 종목상세 헤더 6컬럼 정보 띠
 *
 * 토스증권 종목 상세 톤. 가격 아래, 캔들차트 위에 위치.
 * 데스크탑: 가로 8 컬럼 (1일 범위 / 52주 / 거래대금 / 체결강도 / 외국인 / 기관 / 시총순위 / 시총)
 * 모바일: 2×3 그리드 + "더보기" 토글
 */

interface InfoItem {
  label: string;
  value: string;
  sub?: string;       // 부가 정보 (한 줄 작게)
}

interface StockDetailInfoStripProps {
  items: InfoItem[];        // 6~8 개 권장
  className?: string;
}

export default function StockDetailInfoStrip({ items, className = '' }: StockDetailInfoStripProps) {
  return (
    <>
      {/* 데스크탑 — 가로 스크롤 컬럼 */}
      <div
        className={`hidden md:flex overflow-x-auto ${className}`}
        style={{
          backgroundColor: 'var(--bg-elev-1)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
        }}
      >
        {items.map((item, idx) => (
          <div
            key={idx}
            className="flex-1 min-w-[120px] px-4 py-3 flex flex-col justify-center"
            style={{
              borderRight: idx < items.length - 1 ? '1px solid var(--border)' : 'none',
            }}
          >
            <div
              style={{
                fontSize: '14px',
                lineHeight: '20px',
                color: 'var(--text-secondary)',
                marginBottom: '4px',
              }}
            >
              {item.label}
            </div>
            <div
              className="tabular-nums"
              style={{
                fontSize: '16px',
                fontWeight: 700,
                lineHeight: '24px',
                color: 'var(--text-primary)',
              }}
            >
              {item.value}
            </div>
            {item.sub && (
              <div
                className="tabular-nums"
                style={{
                  fontSize: '12px',
                  lineHeight: '16px',
                  color: 'var(--text-tertiary)',
                }}
              >
                {item.sub}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 모바일 — 2 칼럼 그리드 */}
      <div
        className={`md:hidden grid grid-cols-2 gap-3 p-4 ${className}`}
        style={{
          backgroundColor: 'var(--bg-elev-1)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
        }}
      >
        {items.map((item, idx) => (
          <div key={idx}>
            <div
              style={{
                fontSize: '12px',
                lineHeight: '16px',
                color: 'var(--text-secondary)',
                marginBottom: '2px',
              }}
            >
              {item.label}
            </div>
            <div
              className="tabular-nums"
              style={{
                fontSize: '14px',
                fontWeight: 700,
                lineHeight: '20px',
                color: 'var(--text-primary)',
              }}
            >
              {item.value}
            </div>
            {item.sub && (
              <div
                className="tabular-nums"
                style={{
                  fontSize: '11px',
                  lineHeight: '14px',
                  color: 'var(--text-tertiary)',
                }}
              >
                {item.sub}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
