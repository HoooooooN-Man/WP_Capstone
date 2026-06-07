import { useState } from 'react';
import { Newspaper, BookOpen, Clock, Trash2, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import Modal from '../components/Modal';
import { useNotes, useAddNote, useDeleteNote,
         useNewsFeed, useNewsCategories,
         type NewsItem, type NoteItem } from '../api/hooks';
import { useSession } from '../api/client';

type Tab = 'news' | 'notes';

type CategoryMeta = {
  category: string; category_label: string;
  one_line?: string; executive_brief?: string;
  sector_signals?: Array<{ sector: string; signal: string; reason?: string }>;
  watch_points?: string[];
  item_count: number;
};

export default function NewsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('news');
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  const { data: catApi } = useNewsCategories();
  // 최신순 평면 리스트 — webnews 14일 적재분 시간순
  const { data: feedApi } = useNewsFeed({ limit: 60 });
  const { data: notesApi } = useNotes();
  const addNote = useAddNote();
  const deleteNote = useDeleteNote();
  const { isLoggedIn } = useSession();

  const investmentNotes = (notesApi?.items ?? []).map((n: NoteItem) => ({
    id: n.id,
    title: n.title,
    content: n.content,
    createdAt: n.created_at ? n.created_at.slice(0, 10).replace(/-/g, '.') : '',
    tags: (n.tags ?? []) as string[],
  }));

  return (
    <AppLayout maxWidth={1280}>
        <h1 className="wp-t-3xl font-bold text-[var(--text-primary)] mb-6">
          뉴스 & 투자노트
        </h1>

        <div className="flex gap-2 mb-6">
          {([['news', '뉴스', Newspaper], ['notes', '투자노트', BookOpen]] as const).map(([key, label, Icon]) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors cursor-pointer wp-t-base border border-[var(--border-default)] ${
                activeTab === key
                  ? 'font-bold text-white bg-[var(--accent-blue)]'
                  : 'font-normal text-[var(--text-secondary)] bg-[var(--bg-elev-1)]'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        {activeTab === 'news' && (
          <>
            {/* ── 카테고리 요약 (헤더만, 클릭 시 LLM 요약 펼침) ── */}
            {catApi && catApi.categories.length > 0 && (
              <section className="mb-8">
                <div className="flex items-baseline justify-between mb-3">
                  <h2 className="wp-t-lg font-bold text-[var(--text-primary)]">카테고리 요약</h2>
                  <p className="wp-t-xs text-[var(--text-tertiary)]">
                    {catApi.date ? `${catApi.date} 기준` : ''} · 카테고리 클릭 시 LLM 요약이 펼쳐집니다
                  </p>
                </div>
                <div className="space-y-3">
                  {catApi.categories.map((c) => (
                    <CategoryCard
                      key={c.category}
                      meta={c as CategoryMeta}
                      expanded={expandedCategory === c.category}
                      onToggle={() =>
                        setExpandedCategory((prev) => (prev === c.category ? null : c.category))
                      }
                    />
                  ))}
                </div>
              </section>
            )}

            {/* ── 최신 기사 (모든 카테고리 통합 · 시간순) ── */}
            <section>
              <div className="flex items-baseline justify-between mb-3">
                <h2 className="wp-t-lg font-bold text-[var(--text-primary)]">최신 기사</h2>
                <p className="wp-t-xs text-[var(--text-tertiary)]">
                  webnews 14일 적재분 · 최신순 {feedApi?.items?.length ?? 0}건
                </p>
              </div>
              <FlatNewsList items={feedApi?.items ?? []} />
            </section>

            {(!catApi || catApi.categories.length === 0) && (feedApi?.items?.length ?? 0) === 0 && (
              <div className="p-8 mt-4 rounded-xl text-center wp-t-base text-[var(--text-tertiary)] bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
                아직 적재된 webnews 가 없습니다.
              </div>
            )}
          </>
        )}

        {activeTab === 'notes' && (
          <>
            <button
              onClick={() => isLoggedIn && setShowNoteModal(true)}
              disabled={!isLoggedIn}
              className="w-full mb-4 px-4 py-3 rounded-lg transition-colors wp-t-base font-bold"
              style={{
                backgroundColor: isLoggedIn ? 'var(--accent-blue)' : 'var(--bg-elev-2)',
                color: isLoggedIn ? '#FFFFFF' : 'var(--text-tertiary)',
              }}
            >
              {isLoggedIn ? '+ 새 노트 작성' : '로그인 후 노트를 작성할 수 있습니다'}
            </button>

            {investmentNotes.length === 0 && (
              <div className="p-8 rounded-xl text-center wp-t-base text-[var(--text-tertiary)] bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
                {isLoggedIn ? '작성한 투자노트가 없습니다. 새 노트를 작성해 보세요.' : '로그인하면 투자노트를 저장할 수 있습니다.'}
              </div>
            )}

            <div className="space-y-4">
              {investmentNotes.map((note) => (
                <div
                  key={note.id}
                  className="p-5 rounded-xl cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(0,0,0,0.1)] bg-[var(--bg-elev-1)] border border-[var(--border-default)]"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="wp-t-md font-bold text-[var(--text-primary)]">
                      {note.title}
                    </h3>
                    <button
                      onClick={() => deleteNote.mutate(note.id)}
                      className="p-1 rounded shrink-0 transition-colors text-[var(--text-tertiary)] hover:text-[var(--color-down)]"
                      aria-label="노트 삭제"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <p
                    className="wp-t-base text-[var(--text-secondary)] mb-3"
                    style={{ whiteSpace: 'pre-wrap' }}
                  >
                    {note.content}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="wp-t-xs text-[var(--text-tertiary)]">
                      {note.createdAt}
                    </span>
                    <div className="flex gap-2">
                      {note.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-1 rounded wp-t-2xs bg-[var(--bg-elev-2)] text-[var(--text-tertiary)]"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      {showNoteModal && (
        <NoteModal
          onClose={() => setShowNoteModal(false)}
          onSubmit={(body) => addNote.mutate(body, { onSuccess: () => setShowNoteModal(false) })}
          submitting={addNote.isPending}
        />
      )}
    </AppLayout>
  );
}

interface NoteModalProps {
  onClose: () => void;
  onSubmit: (body: { title: string; content: string; tags: string[] }) => void;
  submitting: boolean;
}

function NoteModal({ onClose, onSubmit, submitting }: NoteModalProps) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const valid = title.trim().length > 0 && content.trim().length > 0;

  const inputStyle = {
    width: '100%', padding: '10px 12px', borderRadius: '8px',
    backgroundColor: 'var(--bg-elev-2)', border: '1px solid var(--border-default)',
    color: 'var(--text-primary)', fontSize: '14px', outline: 'none',
  } as const;
  const labelStyle = {
    fontSize: '12px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px',
  } as const;

  return (
    <Modal open onClose={onClose} labelledBy="note-modal-title" maxWidth={480}>
      <div className="p-6">
        <h2 id="note-modal-title" className="wp-t-lg font-bold text-[var(--text-primary)] mb-4">
          새 투자노트
        </h2>
        <div className="space-y-3">
          <div>
            <div style={labelStyle}>제목 *</div>
            <input style={inputStyle} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: 5월 포트폴리오 리밸런싱" maxLength={200} />
          </div>
          <div>
            <div style={labelStyle}>내용 *</div>
            <textarea
              style={{ ...inputStyle, minHeight: '120px', resize: 'vertical' }}
              value={content} onChange={(e) => setContent(e.target.value)}
              placeholder="투자 메모를 작성하세요"
            />
          </div>
          <div>
            <div style={labelStyle}>태그 (쉼표 구분)</div>
            <input style={inputStyle} value={tags} onChange={(e) => setTags(e.target.value)} placeholder="포트폴리오, 리밸런싱" />
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded-lg"
            style={{ backgroundColor: 'var(--bg-elev-2)', color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 700 }}
          >
            취소
          </button>
          <button
            disabled={!valid || submitting}
            onClick={() => onSubmit({
              title: title.trim(),
              content: content.trim(),
              tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
            })}
            className="flex-1 py-2 rounded-lg"
            style={{
              backgroundColor: valid && !submitting ? 'var(--accent-blue)' : 'var(--bg-elev-2)',
              color: valid && !submitting ? '#FFFFFF' : 'var(--text-tertiary)',
              fontSize: '14px', fontWeight: 700,
            }}
          >
            {submitting ? '저장 중…' : '저장'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── 카테고리 accordion 카드: 헤더(제목+개수)만 보이고, 펼침 시 LLM 요약 + 기사 ──
interface CategoryCardProps {
  meta: CategoryMeta;
  expanded: boolean;
  onToggle: () => void;
}

function CategoryCard({ meta, expanded, onToggle }: CategoryCardProps) {
  return (
    <div className="rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)] overflow-hidden transition-shadow hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)]">
      {/* 헤더 — 항상 보임 (제목 + 개수 + chevron) */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left cursor-pointer transition-colors hover:bg-[var(--bg-elev-2)]"
        aria-expanded={expanded}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="wp-t-lg font-bold text-[var(--text-primary)]">{meta.category_label}</span>
            <span className="px-2 py-0.5 rounded wp-t-2xs font-bold bg-[var(--bg-elev-2)] text-[var(--text-tertiary)]">
              {meta.item_count}건
            </span>
          </div>
        </div>
        {expanded
          ? <ChevronUp size={18} style={{ color: 'var(--text-tertiary)' }} />
          : <ChevronDown size={18} style={{ color: 'var(--text-tertiary)' }} />}
      </button>

      {/* 펼침 본문 — 클릭 시에만 렌더 */}
      {expanded && (
        <div className="px-5 pb-5 pt-1 border-t border-[var(--border-default)]">
          {meta.one_line && (
            <p className="wp-t-md font-bold text-[var(--text-primary)] mt-4 mb-3" style={{ lineHeight: 1.5 }}>
              {meta.one_line}
            </p>
          )}
          {meta.executive_brief && (
            <p className="wp-t-sm text-[var(--text-secondary)] mb-3 whitespace-pre-wrap" style={{ lineHeight: 1.7 }}>
              {meta.executive_brief}
            </p>
          )}
          {meta.sector_signals && meta.sector_signals.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {meta.sector_signals.map((s, i) => (
                <span
                  key={i}
                  className="px-2 py-1 rounded wp-t-xs bg-[var(--bg-elev-2)] text-[var(--text-secondary)]"
                  title={s.reason}
                >
                  <b>{s.sector}</b> · {s.signal}
                </span>
              ))}
            </div>
          )}
          {meta.watch_points && meta.watch_points.length > 0 && (
            <div className="mt-4 pt-3 border-t border-[var(--border-default)]">
              <p className="wp-t-2xs font-bold text-[var(--text-tertiary)] mb-2">모니터링 포인트</p>
              <ul className="space-y-1">
                {meta.watch_points.slice(0, 4).map((w, i) => (
                  <li key={i} className="wp-t-xs text-[var(--text-secondary)] flex gap-1">
                    <span className="text-[var(--accent-blue)]">·</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── 평면 최신순 리스트 (모든 카테고리 통합) ──
function FlatNewsList({ items }: { items: NewsItem[] }) {
  if (items.length === 0) {
    return (
      <div className="p-6 rounded-xl text-center wp-t-base text-[var(--text-tertiary)] bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
        적재된 기사가 없습니다.
      </div>
    );
  }
  return (
    <div className="rounded-xl overflow-hidden bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
      {items.map((it, idx) => (
        <a
          key={(it.news_id ?? it.id) as string | number}
          href={it.url || '#'}
          target="_blank"
          rel="noopener noreferrer"
          className={`flex items-center gap-3 px-4 py-3 transition-colors hover:bg-[var(--bg-elev-2)] ${
            idx < items.length - 1 ? 'border-b border-[var(--border-default)]' : ''
          }`}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {it.category_label && (
                <span className="px-1.5 py-0.5 rounded wp-t-2xs font-bold bg-[var(--bg-elev-2)] text-[var(--accent-blue)]">
                  {it.category_label}
                </span>
              )}
              <span className="wp-t-2xs text-[var(--text-tertiary)]">{it.source ?? '뉴스'}</span>
              <span className="wp-t-2xs text-[var(--text-tertiary)]">·</span>
              <Clock size={9} style={{ color: 'var(--text-tertiary)' }} />
              <span className="wp-t-2xs text-[var(--text-tertiary)]">
                {(it.published_at ?? '').slice(0, 16).replace('T', ' ')}
              </span>
            </div>
            <h3 className="wp-t-md font-bold text-[var(--text-primary)] line-clamp-2">
              {it.title}
            </h3>
          </div>
          <ExternalLink size={14} style={{ color: 'var(--text-tertiary)' }} className="shrink-0" />
        </a>
      ))}
    </div>
  );
}
