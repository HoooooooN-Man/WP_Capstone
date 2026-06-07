import { useState, type ReactNode } from 'react';

export interface DataTableColumn<T> {
  key: string;
  header: string;
  align?: 'left' | 'right' | 'center';
  width?: number | string;
  /** 헤더 클릭 정렬 활성화 — sortValue 와 함께 지정 */
  sortable?: boolean;
  /** 정렬 비교용 값 추출 (number | string) */
  sortValue?: (row: T) => number | string;
  /** 셀 렌더 — row 와 정렬 후 인덱스(순위 등) 전달 */
  render: (row: T, index: number) => ReactNode;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  /** 초기 정렬 컬럼/방향 */
  defaultSort?: { key: string; dir: 'asc' | 'desc' };
  emptyMessage?: string;
}

/**
 * DataTable — 정렬 가능한 고밀도 표준 표 (토스 스크리너 레퍼런스).
 * 헤더 클릭 정렬, hover 행 강조, 행 높이 ~52px.
 */
export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  defaultSort,
  emptyMessage = '결과가 없습니다.',
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(defaultSort?.key ?? null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>(defaultSort?.dir ?? 'desc');

  const sortCol = columns.find((c) => c.key === sortKey);
  const sorted = sortCol?.sortValue
    ? [...rows].sort((a, b) => {
        const va = sortCol.sortValue!(a);
        const vb = sortCol.sortValue!(b);
        const cmp =
          typeof va === 'number' && typeof vb === 'number'
            ? va - vb
            : String(va).localeCompare(String(vb));
        return sortDir === 'asc' ? cmp : -cmp;
      })
    : rows;

  const toggleSort = (col: DataTableColumn<T>) => {
    if (!col.sortable || !col.sortValue) return;
    if (sortKey === col.key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(col.key);
      setSortDir('desc');
    }
  };

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)' }}
    >
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
              {columns.map((col) => {
                const active = sortKey === col.key;
                const canSort = !!(col.sortable && col.sortValue);
                return (
                  <th
                    key={col.key}
                    scope="col"
                    onClick={() => toggleSort(col)}
                    className={canSort ? 'cursor-pointer select-none' : ''}
                    style={{
                      textAlign: col.align ?? 'left',
                      padding: '10px 16px',
                      fontSize: '12px',
                      fontWeight: 700,
                      color: active ? 'var(--accent-blue)' : 'var(--text-tertiary)',
                      width: col.width,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {col.header}
                    {canSort && (
                      <span style={{ marginLeft: 4, fontSize: '10px' }}>
                        {active ? (sortDir === 'asc' ? '▲' : '▼') : '↕'}
                      </span>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{ padding: '32px', textAlign: 'center', fontSize: '13px', color: 'var(--text-tertiary)' }}
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              sorted.map((row, idx) => (
                <tr
                  key={rowKey(row)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  onKeyDown={
                    onRowClick
                      ? (e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            onRowClick(row);
                          }
                        }
                      : undefined
                  }
                  tabIndex={onRowClick ? 0 : undefined}
                  role={onRowClick ? 'button' : undefined}
                  className={`${onRowClick ? 'cursor-pointer' : ''} transition-colors hover:bg-[var(--bg-elev-2)]`}
                  style={{ borderBottom: '1px solid var(--border-default)' }}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      style={{ textAlign: col.align ?? 'left', padding: '10px 16px', fontSize: '14px' }}
                    >
                      {col.render(row, idx)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
