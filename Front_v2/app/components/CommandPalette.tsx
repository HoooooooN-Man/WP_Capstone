import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import Modal from './Modal';
import StockLogo from './StockLogo';
import { useStockSearch } from '../api/hooks';

/**
 * CommandPalette — 전역 Ctrl/Cmd+K 종목 검색.
 * 어느 화면에서나 종목을 빠르게 찾아 상세로 이동한다. AppLayout 에서 항상 마운트.
 * 오버레이 a11y(role=dialog·포커스 트랩·복원)는 공통 Modal 이 담당.
 */
export default function CommandPalette() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);

  const { data } = useStockSearch(query);
  const results = (data?.items ?? []).slice(0, 8);

  // 전역 Ctrl/Cmd+K 토글
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // 열릴 때 입력 초기화
  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIdx(0);
    }
  }, [open]);

  useEffect(() => {
    setActiveIdx(0);
  }, [query]);

  const go = (ticker: string) => {
    setOpen(false);
    navigate(`/stocks/${ticker}`);
  };

  const onInputKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[activeIdx]) {
      e.preventDefault();
      go(results[activeIdx].ticker);
    }
  };

  return (
    <Modal open={open} onClose={() => setOpen(false)} label="종목 검색" maxWidth={560} align="top">
      <div
        className="flex items-center gap-3 px-4"
        style={{ borderBottom: '1px solid var(--border-default)', height: 56 }}
      >
        <Search size={18} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
        <input
          // Modal 이 마운트 시 첫 포커스 요소(=이 input)로 포커스를 옮긴다
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onInputKey}
          placeholder="종목명 또는 코드 검색…"
          aria-label="종목명 또는 코드 검색"
          className="flex-1"
          style={{ background: 'transparent', border: 'none', outline: 'none', fontSize: '15px', color: 'var(--text-primary)' }}
        />
        <kbd
          style={{
            fontSize: '11px',
            color: 'var(--text-tertiary)',
            border: '1px solid var(--border-default)',
            borderRadius: '4px',
            padding: '2px 6px',
          }}
        >
          Esc
        </kbd>
      </div>
      <div style={{ maxHeight: 360, overflowY: 'auto' }}>
        {!query && (
          <div style={{ padding: '24px', textAlign: 'center', fontSize: '13px', color: 'var(--text-tertiary)' }}>
            종목명을 입력하세요 · ↑↓ 이동 · Enter 이동
          </div>
        )}
        {query && results.length === 0 && (
          <div style={{ padding: '24px', textAlign: 'center', fontSize: '13px', color: 'var(--text-tertiary)' }}>
            검색 결과가 없습니다.
          </div>
        )}
        {results.map((s, idx: number) => (
          <button
            key={s.ticker}
            onClick={() => go(s.ticker)}
            onMouseEnter={() => setActiveIdx(idx)}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-left"
            style={{
              background: idx === activeIdx ? 'var(--bg-elev-2)' : 'transparent',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <StockLogo ticker={s.ticker} name={s.name} size={32} />
            <div className="flex-1 min-w-0">
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>{s.name}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                {s.ticker}{s.sector ? ` · ${s.sector}` : ''}
              </div>
            </div>
          </button>
        ))}
      </div>
    </Modal>
  );
}
