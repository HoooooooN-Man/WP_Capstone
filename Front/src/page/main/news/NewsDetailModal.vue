<template>
  <!-- ── 모달 오버레이 ──────────────────────────────────────────────────────── -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-container">

          <!-- 닫기 버튼 -->
          <button class="modal-close" @click="$emit('close')">✕</button>

          <!-- ── 단건 뉴스 상세 ────────────────────────────────────────────── -->
          <div v-if="news" class="news-detail">
            <div class="news-meta">
              <span class="news-publisher">{{ news.publisher ?? news.source }}</span>
              <span class="news-date">{{ fmtDate(news.published_at) }}</span>
              <span v-if="news.category_label" class="news-cat-label">{{ news.category_label }}</span>
            </div>
            <h2 class="news-title">{{ news.title }}</h2>
            <div v-if="news.sentiment_label" class="news-sentiment">
              <span class="s-badge" :class="badgeClass(news.sentiment_label)">
                {{ sentimentEmoji(news.sentiment_label) }} {{ sentimentText(news.sentiment_label) }}
              </span>
              <div class="prob-bars">
                <div class="prob-wrap" title="긍정">
                  <div class="prob-bar pos" :style="{ width: pct(news.pos_prob) }"/>
                  <span class="prob-label">{{ pct(news.pos_prob) }}</span>
                </div>
                <div class="prob-wrap" title="중립">
                  <div class="prob-bar neu" :style="{ width: pct(news.neu_prob) }"/>
                  <span class="prob-label">{{ pct(news.neu_prob) }}</span>
                </div>
                <div class="prob-wrap" title="부정">
                  <div class="prob-bar neg" :style="{ width: pct(news.neg_prob) }"/>
                  <span class="prob-label">{{ pct(news.neg_prob) }}</span>
                </div>
              </div>
            </div>
            <a
              v-if="news.origin_url || news.google_news_url"
              :href="news.origin_url ?? news.google_news_url"
              target="_blank" rel="noopener noreferrer"
              class="news-link"
            >원문 보기 →</a>
          </div>

          <hr class="divider"/>

          <!-- ── 탭 ────────────────────────────────────────────────────────── -->
          <div class="tab-row">
            <button
              v-for="t in TABS" :key="t.id"
              class="tab-btn" :class="{ active: activeTab === t.id }"
              @click="activeTab = t.id"
            >{{ t.label }}</button>
          </div>

          <!-- ── 탭 컨텐츠 ──────────────────────────────────────────────────── -->
          <div class="tab-content">
            <div v-if="webnewsLoading" class="sk-list">
              <div v-for="n in 5" :key="n" class="sk-item">
                <div class="sk-rank"/><div class="sk-body"><div class="sk-t"/><div class="sk-m"/></div>
              </div>
            </div>

            <template v-else>
              <!-- TAB: 랭킹 -->
              <div v-if="activeTab === 'ranking'">
                <div v-if="catData?.sentiment_summary" class="s-banner">
                  <div class="s-stat pos">
                    <span class="s-count">{{ catData.sentiment_summary.label_counts?.positive ?? '-' }}</span>
                    <span class="s-lbl">📈 긍정</span>
                  </div>
                  <div class="s-div"/>
                  <div class="s-stat neu">
                    <span class="s-count">{{ catData.sentiment_summary.label_counts?.neutral ?? '-' }}</span>
                    <span class="s-lbl">➖ 중립</span>
                  </div>
                  <div class="s-div"/>
                  <div class="s-stat neg">
                    <span class="s-count">{{ catData.sentiment_summary.label_counts?.negative ?? '-' }}</span>
                    <span class="s-lbl">📉 부정</span>
                  </div>
                  <div class="s-div"/>
                  <div class="s-stat avg">
                    <span class="s-count" :class="scoreColor(catData.sentiment_summary.avg_score)">
                      {{ fmtScore(catData.sentiment_summary.avg_score) }}
                    </span>
                    <span class="s-lbl">평균 감성</span>
                  </div>
                </div>
                <div v-else class="info-banner">ℹ️ 감성 분석은 매일 09:30 자동 실행됩니다.</div>

                <div v-if="catData?.items?.length" class="rank-list">
                  <a
                    v-for="item in catData.items" :key="item.item_id"
                    :href="item.google_news_url || '#'"
                    target="_blank" rel="noopener noreferrer"
                    class="rank-item" :class="sentimentClass(item.sentiment)"
                    :aria-current="item.title === news?.title ? 'true' : undefined"
                  >
                    <div class="rank-badge" :class="rankClass(item.rank)">{{ item.rank }}</div>
                    <div class="rank-body">
                      <div class="rank-meta">
                        <span class="rank-pub">{{ item.publisher }}</span>
                        <span class="rank-date">{{ fmtDate(item.published_at) }}</span>
                      </div>
                      <p class="rank-title" :class="{ 'current-item': item.title === news?.title }">
                        {{ item.title }}
                      </p>
                      <div v-if="item.sentiment" class="rank-sentiment">
                        <span class="s-badge sm" :class="badgeClass(item.sentiment.label)">
                          {{ sentimentEmoji(item.sentiment.label) }} {{ sentimentText(item.sentiment.label) }}
                        </span>
                        <span class="rank-score" :class="scoreColor(item.sentiment.score)">
                          {{ fmtScore(item.sentiment.score) }}점
                        </span>
                      </div>
                    </div>
                  </a>
                </div>
                <div v-else class="empty">📭 랭킹 데이터가 없습니다.</div>
              </div>

              <!-- TAB: 카테고리 리포트 -->
              <div v-else-if="activeTab === 'report'">
                <div v-if="catData?.report" class="report-card">
                  <h3 class="report-title">{{ catData.report.report_title }}</h3>
                  <p class="report-one-line">{{ catData.report.one_line }}</p>
                  <p class="report-brief">{{ catData.report.executive_brief }}</p>
                  <div v-if="catData.report.sector_signals?.length" class="section-block">
                    <div class="section-label">📊 섹터 시그널</div>
                    <div v-for="(sig, i) in catData.report.sector_signals" :key="i" class="signal-row">
                      <span class="sig-sector">{{ sig.sector }}</span>
                      <span class="sig-badge" :class="`sig-${sig.signal}`">{{ sig.signal }}</span>
                      <span class="sig-reason">{{ sig.reason }}</span>
                    </div>
                  </div>
                  <div v-if="catData.report.investor_checklist?.length" class="section-block">
                    <div class="section-label">✅ 투자자 체크리스트</div>
                    <ul><li v-for="(c, i) in catData.report.investor_checklist" :key="i">{{ c }}</li></ul>
                  </div>
                </div>
                <div v-else class="empty">📄 리포트 데이터가 없습니다.</div>
              </div>

              <!-- TAB: Daily -->
              <div v-else-if="activeTab === 'daily'">
                <div v-if="daily" class="report-card">
                  <div class="daily-header">
                    <span class="tone-badge" :class="`tone-${daily.market_tone}`">{{ toneLabel(daily.market_tone) }}</span>
                    <h3 class="report-title">{{ daily.report_title }}</h3>
                  </div>
                  <p class="report-one-line">{{ daily.headline_summary }}</p>
                  <p class="report-brief">{{ daily.market_overview }}</p>
                  <div v-if="daily.top_themes?.length" class="section-block">
                    <div class="section-label">🔑 주요 테마</div>
                    <div v-for="(t, i) in daily.top_themes" :key="i" class="theme-item">
                      <div class="theme-name">{{ t.theme }}</div>
                      <div class="theme-summary">{{ t.summary }}</div>
                      <div v-if="t.market_relevance" class="theme-rel">💡 {{ t.market_relevance }}</div>
                    </div>
                  </div>
                  <div v-if="daily.today_watchlist?.length" class="section-block">
                    <div class="section-label">🔍 오늘 확인할 변수</div>
                    <ul><li v-for="(w, i) in daily.today_watchlist" :key="i">{{ w }}</li></ul>
                  </div>
                  <div v-if="daily.category_briefs?.length" class="section-block">
                    <div class="section-label">📌 분야별 한 줄 요약</div>
                    <div v-for="b in daily.category_briefs" :key="b.category" class="brief-row">
                      <span class="brief-cat">{{ b.category_label }}</span>
                      <span class="brief-text">{{ b.brief }}</span>
                    </div>
                  </div>
                </div>
                <div v-else class="empty">📄 Daily 리포트 데이터가 없습니다.</div>
              </div>

            </template>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import dbapi from '@/api/dbapi'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  news:   { type: Object,  default: null  },
})
defineEmits(['close'])

const TABS = [
  { id: 'ranking', label: '📊 같은 카테고리 랭킹' },
  { id: 'report',  label: '📋 카테고리 리포트' },
  { id: 'daily',   label: '🌐 Daily 리포트' },
]

const activeTab      = ref('ranking')
const webnewsLoading = ref(false)
const catData        = ref(null)
const daily          = ref(null)

function getDate(news) {
  if (!news) return new Date().toISOString().slice(0, 10)
  if (news.display_date) return news.display_date
  if (news.published_at) return news.published_at.slice(0, 10)
  return new Date().toISOString().slice(0, 10)
}

function getCategoryId(news) {
  if (!news) return 'business'
  return news.category_id ?? news.category ?? 'business'
}

async function loadWebnews(news) {
  if (!news) return
  webnewsLoading.value = true
  catData.value = null
  daily.value   = null

  const date = getDate(news)
  const cat  = getCategoryId(news)

  await Promise.allSettled([
    dbapi.get(`/api/webnews/${date}/${cat}`)
      .then(({ data }) => { catData.value = data })
      .catch(() => {}),
    dbapi.get(`/api/webnews/${date}/daily`)
      .then(({ data }) => { daily.value = data })
      .catch(() => {}),
  ])
  webnewsLoading.value = false
}

watch(() => props.isOpen, (open) => {
  if (open) { activeTab.value = 'ranking'; loadWebnews(props.news) }
})

const pct            = v => v != null ? `${(v * 100).toFixed(0)}%` : '0%'
const fmtScore       = s => s == null ? '-' : (s * 100).toFixed(0)
const rankClass      = r => r === 1 ? 'rank-gold' : r === 2 ? 'rank-silver' : r === 3 ? 'rank-bronze' : ''
const sentimentClass = s => s ? `sentiment-${s.label}` : ''
const badgeClass     = l => ({ positive: 'badge-pos', neutral: 'badge-neu', negative: 'badge-neg' }[l] || 'badge-neu')
const sentimentEmoji = l => ({ positive: '📈', neutral: '➖', negative: '📉' }[l] || '➖')
const sentimentText  = l => ({ positive: '긍정', neutral: '중립', negative: '부정' }[l] || '중립')
const scoreColor     = s => s == null ? '' : s > 0.1 ? 'score-pos' : s < -0.1 ? 'score-neg' : 'score-neu'
const toneLabel      = t => ({ positive: '📈 긍정적', negative: '📉 부정적', mixed: '🔀 혼재', neutral: '➖ 중립' }[t] || t)

function fmtDate(val) {
  if (!val) return ''
  const d = new Date(val)
  return isNaN(d) ? val : d.toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: 999;
  background: rgba(0,0,0,0.55);
  display: flex; align-items: center; justify-content: center; padding: 16px;
}
.modal-container {
  position: relative; background: #fff; border-radius: 18px;
  width: 100%; max-width: 680px; max-height: 88vh; overflow-y: auto;
  padding: 28px 24px 32px; box-shadow: 0 20px 60px rgba(0,0,0,0.18);
}
.modal-close {
  position: absolute; top: 16px; right: 16px;
  background: #f1f5f9; border: none; border-radius: 50%;
  width: 32px; height: 32px; cursor: pointer; font-size: .9rem; color: #475569;
  display: flex; align-items: center; justify-content: center;
}
.modal-close:hover { background: #e2e8f0; }
.modal-enter-active, .modal-leave-active { transition: opacity .2s, transform .2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: scale(.96); }

.news-detail { margin-bottom: 16px; }
.news-meta { display: flex; gap: 10px; font-size: .78rem; color: #94a3b8; margin-bottom: 6px; flex-wrap: wrap; }
.news-publisher { font-weight: 600; color: #64748b; }
.news-cat-label { background: #eff6ff; color: #3b82f6; padding: 1px 8px; border-radius: 999px; font-size: .75rem; }
.news-title { font-size: 1.05rem; font-weight: 700; color: #1e293b; line-height: 1.5; margin: 0 0 12px; }
.news-sentiment { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.news-link { display: inline-block; margin-top: 4px; font-size: .85rem; color: #6366f1; font-weight: 600; text-decoration: none; }
.news-link:hover { text-decoration: underline; }

.divider { border: none; border-top: 1px solid #e2e8f0; margin: 0 0 16px; }

.tab-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.tab-btn { padding: 7px 14px; border: 1px solid #e2e8f0; border-radius: 999px; background: #fff; font-size: .83rem; cursor: pointer; color: #64748b; transition: all .15s; }
.tab-btn:hover  { border-color: #a5b4fc; color: #4f46e5; }
.tab-btn.active { background: #6366f1; color: #fff; border-color: #6366f1; font-weight: 600; }

.sk-list { display: flex; flex-direction: column; gap: 10px; }
.sk-item { display: flex; gap: 12px; padding: 12px; background: #f8fafc; border-radius: 10px; animation: pulse 1.4s ease-in-out infinite; }
.sk-rank { width: 36px; height: 36px; border-radius: 50%; background: #e2e8f0; flex-shrink: 0; }
.sk-body { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.sk-t { height: 16px; background: #e2e8f0; border-radius: 4px; width: 70%; }
.sk-m { height: 11px; background: #e2e8f0; border-radius: 4px; width: 40%; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }

.s-banner { display: flex; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 20px; margin-bottom: 14px; }
.s-stat   { display: flex; flex-direction: column; align-items: center; flex: 1; gap: 2px; }
.s-count  { font-size: 1.3rem; font-weight: 700; }
.s-lbl    { font-size: .72rem; color: #64748b; }
.s-stat.pos .s-count { color: #16a34a; }
.s-stat.neg .s-count { color: #dc2626; }
.s-stat.neu .s-count { color: #64748b; }
.s-div { width: 1px; height: 36px; background: #e2e8f0; margin: 0 6px; }
.info-banner { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 10px 14px; color: #3b82f6; font-size: .83rem; margin-bottom: 14px; }

.rank-list { display: flex; flex-direction: column; gap: 8px; }
.rank-item {
  display: flex; align-items: center; gap: 12px; padding: 12px 14px;
  background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
  text-decoration: none; color: inherit; transition: box-shadow .15s, transform .15s;
  position: relative; overflow: hidden;
}
.rank-item::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; border-radius: 3px 0 0 3px; }
.rank-item.sentiment-positive::before { background: #16a34a; }
.rank-item.sentiment-negative::before { background: #dc2626; }
.rank-item.sentiment-neutral::before  { background: #94a3b8; }
.rank-item.sentiment-positive { background: linear-gradient(135deg,#f0fdf4 0%,#fff 40%); }
.rank-item.sentiment-negative { background: linear-gradient(135deg,#fff1f2 0%,#fff 40%); }
.rank-item:hover { box-shadow: 0 3px 14px rgba(0,0,0,.09); transform: translateY(-1px); }
.rank-item[aria-current="true"] { border-color: #6366f1; box-shadow: 0 0 0 2px #c7d2fe; }

.rank-badge  { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: .88rem; font-weight: 700; flex-shrink: 0; background: #f1f5f9; color: #475569; }
.rank-gold   { background: #fef9c3; color: #b45309; border: 2px solid #f59e0b; }
.rank-silver { background: #f1f5f9; color: #475569; border: 2px solid #94a3b8; }
.rank-bronze { background: #fff7ed; color: #92400e; border: 2px solid #d97706; }

.rank-body { flex: 1; min-width: 0; }
.rank-meta { display: flex; gap: 8px; font-size: .72rem; color: #94a3b8; margin-bottom: 3px; }
.rank-pub  { font-weight: 600; color: #64748b; }
.rank-title {
  font-size: .9rem; font-weight: 600; color: #1e293b; line-height: 1.4; margin-bottom: 5px;
  overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.rank-title.current-item { color: #4f46e5; }
.rank-sentiment { display: flex; align-items: center; gap: 8px; }
.rank-score { font-size: .8rem; font-weight: 700; }

.s-badge { display: inline-flex; align-items: center; gap: 3px; padding: 2px 10px; border-radius: 999px; font-size: .75rem; font-weight: 600; }
.s-badge.sm { font-size: .72rem; padding: 1px 8px; }
.badge-pos { background: #dcfce7; color: #15803d; }
.badge-neu { background: #f1f5f9; color: #475569; }
.badge-neg { background: #fee2e2; color: #b91c1c; }

.prob-bars { display: flex; gap: 8px; flex: 1; min-width: 0; }
.prob-wrap { display: flex; align-items: center; gap: 4px; flex: 1; min-width: 0; }
.prob-bar  { height: 5px; border-radius: 3px; min-width: 4px; transition: width .3s ease; }
.prob-bar.pos { background: #4ade80; }
.prob-bar.neu { background: #94a3b8; }
.prob-bar.neg { background: #f87171; }
.prob-label { font-size: .68rem; color: #94a3b8; white-space: nowrap; }

.score-pos { color: #16a34a; }
.score-neg { color: #dc2626; }
.score-neu { color: #64748b; }

.report-card     { display: flex; flex-direction: column; gap: 10px; }
.report-title    { font-size: 1rem; font-weight: 700; color: #1e293b; margin: 0; }
.report-one-line { font-size: .88rem; font-weight: 600; color: #6366f1; margin: 0; }
.report-brief    { font-size: .88rem; color: #475569; line-height: 1.7; margin: 0; }

.section-block { margin-top: 10px; }
.section-label { font-size: .78rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 8px; }
.section-block ul { margin: 4px 0 0; padding-left: 18px; color: #475569; font-size: .85rem; line-height: 1.8; }

.signal-row  { display: flex; align-items: flex-start; gap: 8px; padding: 7px 0; border-bottom: 1px solid #f1f5f9; font-size: .83rem; flex-wrap: wrap; }
.sig-sector  { font-weight: 600; color: #1e293b; min-width: 64px; }
.sig-reason  { color: #475569; flex: 1; line-height: 1.5; }
.sig-badge   { padding: 1px 8px; border-radius: 999px; font-size: .72rem; font-weight: 600; flex-shrink: 0; }
.sig-긍정,.sig-positive { background: #dcfce7; color: #15803d; }
.sig-부정,.sig-negative { background: #fee2e2; color: #b91c1c; }
.sig-혼재,.sig-mixed    { background: #fef9c3; color: #b45309; }
.sig-중립,.sig-neutral  { background: #f1f5f9; color: #475569; }

.daily-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tone-badge   { padding: 2px 10px; border-radius: 999px; font-size: .75rem; font-weight: 600; }
.tone-positive { background: #dcfce7; color: #15803d; }
.tone-negative { background: #fee2e2; color: #b91c1c; }
.tone-mixed    { background: #fef9c3; color: #b45309; }
.tone-neutral  { background: #f1f5f9; color: #475569; }

.theme-item    { background: #f8fafc; border-radius: 8px; padding: 10px 12px; margin-bottom: 6px; }
.theme-name    { font-weight: 700; font-size: .87rem; color: #1e293b; margin-bottom: 3px; }
.theme-summary { color: #475569; font-size: .83rem; line-height: 1.5; }
.theme-rel     { color: #6366f1; font-size: .78rem; margin-top: 4px; }

.brief-row  { display: flex; gap: 10px; padding: 5px 0; border-bottom: 1px solid #f1f5f9; font-size: .83rem; }
.brief-cat  { font-weight: 600; color: #6366f1; min-width: 64px; flex-shrink: 0; }
.brief-text { color: #475569; line-height: 1.5; }

.empty { text-align: center; padding: 32px; color: #94a3b8; font-size: .9rem; }

@media (max-width: 640px) {
  .modal-container { padding: 20px 16px 28px; max-height: 92vh; }
  .prob-bars { display: none; }
  .s-banner  { padding: 10px; }
}
</style>