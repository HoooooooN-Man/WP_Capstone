import { useEffect, useRef, type ReactNode } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  /** 제목 요소 id — aria-labelledby 연결 (label 과 둘 중 하나) */
  labelledBy?: string;
  /** aria-label 직접 지정 (제목 요소가 없을 때) */
  label?: string;
  /** 패널 최대 폭(px). 기본 480 */
  maxWidth?: number;
  /** 세로 정렬 — 'center'(폼 모달) | 'top'(커맨드 팔레트). 기본 center */
  align?: 'center' | 'top';
}

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])';

/**
 * Modal — 접근성을 갖춘 공통 오버레이.
 *
 * role="dialog" + aria-modal, 포커스 트랩(Tab 순환)·포커스 복원,
 * Esc·backdrop 클릭 닫기, body 스크롤 잠금을 일원화한다.
 * CommandPalette / NoteModal / AddHoldingModal 이 공유.
 */
export default function Modal({
  open,
  onClose,
  children,
  labelledBy,
  label,
  maxWidth = 480,
  align = 'center',
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  // onClose 가 매 렌더 새 함수여도 effect 가 재실행되지 않도록 ref 로 고정
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    const prevFocused = document.activeElement as HTMLElement | null;

    const focusables = () =>
      Array.from(panel?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
    // 패널 내 첫 포커스 가능 요소로 이동
    focusables()[0]?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCloseRef.current();
        return;
      }
      if (e.key !== 'Tab') return;
      const list = focusables();
      if (list.length === 0) return;
      const first = list[0];
      const last = list[list.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
      // 모달 닫힐 때 직전 포커스 복원
      prevFocused?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className={`fixed inset-0 z-[100] flex justify-center p-4 ${align === 'top' ? 'items-start' : 'items-center'}`}
      style={{
        backgroundColor: 'rgba(0,0,0,0.5)',
        paddingTop: align === 'top' ? '12vh' : undefined,
      }}
      onClick={onClose}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-label={labelledBy ? undefined : label}
        className="w-full rounded-xl"
        style={{ maxWidth, backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
