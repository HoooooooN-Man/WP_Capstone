import { useState } from 'react';
import { Newspaper, BookOpen, Clock, Trash2 } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import Modal from '../components/Modal';
import NewsThumbnail from '../components/NewsThumbnail';
import { useNewsFeed, useNotes, useAddNote, useDeleteNote, type NewsItem, type NoteItem } from '../api/hooks';
import { useSession } from '../api/client';

type Tab = 'news' | 'notes';

export default function NewsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('news');
  const [showNoteModal, setShowNoteModal] = useState(false);

  // 백엔드 뉴스 피드 + FinBERT 감성
  const { data: newsApi } = useNewsFeed({ limit: 20 });
  // 투자노트 CRUD
  const { data: notesApi } = useNotes();
  const addNote = useAddNote();
  const deleteNote = useDeleteNote();
  const { isLoggedIn } = useSession();

  const apiArticles = newsApi?.items?.map((n: NewsItem, idx: number) => ({
    id: n.news_id ?? idx,
    title: n.title ?? '',
    summary: n.summary ?? n.content?.slice(0, 100) ?? '',
    source: n.source ?? '뉴스',
    timestamp: n.published_at ?? '',
    relatedStocks: (n.related_tickers ?? []) as string[],
    imageUrl: n.image_url ?? null,
    sentiment: n.sentiment_label ?? 'neutral',
  }));

  // 투자노트 — /users/me/notes 실데이터
  const investmentNotes = (notesApi?.items ?? []).map((n: NoteItem) => ({
    id: n.id,
    title: n.title,
    content: n.content,
    createdAt: n.created_at ? n.created_at.slice(0, 10).replace(/-/g, '.') : '',
    tags: (n.tags ?? []) as string[],
  }));

  const newsArticles = apiArticles ?? [];

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

        {activeTab === 'news' && newsArticles.length === 0 && (
          <div className="p-8 rounded-xl text-center wp-t-base text-[var(--text-tertiary)] bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            뉴스 데이터 미수집 — Naver/Daum 뉴스 수집 파이프라인 + news_data.duckdb 적재 필요
            <br />
            (Frontend_DataCollection_Plan.md 참조)
          </div>
        )}

        {activeTab === 'news' && (
          <div className="space-y-4">
            {newsArticles.map((article) => (
              <div
                key={article.id}
                className="p-4 rounded-xl cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(0,0,0,0.1)] bg-[var(--bg-elev-1)] border border-[var(--border-default)]"
              >
                <div className="flex items-start gap-4">
                  {/* 썸네일 — image_url 있으면 이미지, 실패 시 아이콘 폴백 */}
                  <NewsThumbnail imageUrl={article.imageUrl} className="w-28 h-20" iconSize={24} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      {/* FinBERT 감성 칩 */}
                      <span
                        className="px-1.5 py-0.5 rounded wp-t-2xs font-bold"
                        style={{
                          backgroundColor:
                            article.sentiment === 'positive' ? 'var(--buy-bg)' :
                            article.sentiment === 'negative' ? 'var(--sell-bg)' : 'var(--bg-elev-2)',
                          color:
                            article.sentiment === 'positive' ? 'var(--buy-text)' :
                            article.sentiment === 'negative' ? 'var(--sell-text)' : 'var(--text-tertiary)',
                        }}
                      >
                        {article.sentiment === 'positive' ? '긍정' : article.sentiment === 'negative' ? '부정' : '중립'}
                      </span>
                      <span className="wp-t-xs text-[var(--text-tertiary)]">{article.source}</span>
                      <span className="wp-t-xs text-[var(--text-tertiary)]">·</span>
                      <div className="flex items-center gap-1">
                        <Clock size={11} style={{ color: 'var(--text-tertiary)' }} />
                        <span className="wp-t-xs text-[var(--text-tertiary)]">{article.timestamp}</span>
                      </div>
                    </div>
                    <h3 className="wp-t-md font-bold text-[var(--text-primary)] mb-1 line-clamp-2">
                      {article.title}
                    </h3>
                    <p className="wp-t-sm text-[var(--text-secondary)] line-clamp-1">
                      {article.summary}
                    </p>
                    {article.relatedStocks.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {article.relatedStocks.map((stock) => (
                          <span
                            key={stock}
                            className="px-2 py-0.5 rounded wp-t-2xs font-bold bg-[var(--bg-elev-2)] text-[var(--accent-blue)]"
                          >
                            {stock}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
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
