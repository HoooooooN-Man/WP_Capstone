import type { ReactNode } from 'react';

interface StatTileProps {
  label: string;
  value: ReactNode;
  /** 값 아래 보조 텍스트/요소 (등락률, 단위 등) */
  sub?: ReactNode;
  /** 값 색상 — 등락 색 등. 기본 text-primary */
  valueColor?: string;
  /** 값 폰트 크기(px). 기본 28 */
  valueSize?: number;
}

/**
 * StatTile — 라벨 + 큰 수치 + 보조 의 표준 지표 타일.
 * 종목상세 대시보드·ContextRail·포트폴리오 요약 등에서 재사용.
 */
export default function StatTile({ label, value, sub, valueColor, valueSize = 28 }: StatTileProps) {
  return (
    <div>
      <div style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginBottom: 6 }}>{label}</div>
      <div
        className="tabular-nums"
        style={{
          fontSize: `${valueSize}px`,
          fontWeight: 700,
          lineHeight: 1.15,
          color: valueColor ?? 'var(--text-primary)',
        }}
      >
        {value}
      </div>
      {sub != null && <div style={{ marginTop: 4 }}>{sub}</div>}
    </div>
  );
}
