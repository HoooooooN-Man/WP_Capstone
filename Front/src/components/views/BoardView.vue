<template>
  <div class="w-full h-full bg-gradient-to-br from-[#12100e] via-[#1a1510] to-[#0e0c0a] rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.6)] overflow-hidden border border-white/8 text-white relative flex flex-col">

    <!-- 헤더 -->
    <div class="px-6 pt-5 pb-3 border-b border-white/10 flex-shrink-0">
      <div class="flex items-center gap-3">
        <LucideLayoutList class="w-5 h-5 text-amber-400/80 flex-shrink-0" />
        <h2 class="text-3xl font-black tracking-tighter uppercase">Board</h2>
        <div class="ml-auto flex items-center gap-2">
          <!-- 새 글 작성 버튼 -->
          <button @click="openWrite"
                  class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-bold transition-all
                         bg-amber-500/15 border border-amber-500/25 text-amber-300 hover:bg-amber-500/25">
            <LucidePencil class="w-3 h-3" />
            글쓰기
          </button>
        </div>
      </div>

      <!-- 탭 -->
      <div class="flex gap-1 mt-3 p-1 rounded-xl" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.07)">
        <button v-for="tab in TABS" :key="tab.key"
                @click="activeTab = tab.key"
                class="flex-1 py-1.5 rounded-lg text-[12px] font-bold transition-all duration-150"
                :class="activeTab === tab.key ? 'bg-white/15 text-white shadow-sm' : 'text-white/38 hover:text-white/65'">
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 게시글 목록 -->
    <div class="flex-1 overflow-y-auto">

      <!-- 로딩 -->
      <div v-if="loading" class="flex items-center justify-center h-32 gap-2">
        <div class="w-4 h-4 rounded-full border-2 animate-spin"
             style="border-color:rgba(251,191,36,0.5);border-top-color:transparent"></div>
        <span class="text-[12px] text-white/35">불러오는 중...</span>
      </div>

      <!-- 목록 -->
      <div v-else>
        <!-- 고정 공지 -->
        <div v-for="post in pinnedPosts" :key="'pin-' + post.id"
             class="flex items-start gap-3 px-5 py-3.5 border-b border-white/6 cursor-pointer hover:bg-white/4 transition-colors"
             @click="openPost(post)">
          <span class="text-[10px] font-black px-1.5 py-0.5 rounded mt-0.5 flex-shrink-0"
                style="background:rgba(251,191,36,0.18);color:#fbbf24;border:1px solid rgba(251,191,36,0.3)">공지</span>
          <div class="flex-1 min-w-0">
            <p class="text-[14px] font-bold text-white/90 truncate">{{ post.title }}</p>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="text-[10px] text-white/30">{{ post.author }}</span>
              <span class="text-[10px] text-white/20">·</span>
              <span class="text-[10px] text-white/25 font-mono">{{ post.date }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0 text-[10px] text-white/25 font-mono">
            <span>{{ post.views }}</span>
            <span>{{ post.comments }}</span>
          </div>
        </div>

        <!-- 일반 게시글 -->
        <div v-for="(post, idx) in displayPosts" :key="post.id"
             class="flex items-start gap-3 px-5 py-3.5 border-b border-white/5 cursor-pointer hover:bg-white/4 transition-colors"
             @click="openPost(post)">
          <!-- 순위/번호 -->
          <span class="text-[11px] font-black text-white/20 w-5 flex-shrink-0 mt-0.5 text-center font-mono">
            {{ post.id }}
          </span>
          <div class="flex-1 min-w-0">
            <!-- 카테고리 + 제목 -->
            <div class="flex items-center gap-1.5 mb-0.5">
              <span v-if="post.category"
                    class="text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                    :style="categoryStyle(post.category)">{{ post.category }}</span>
              <span v-if="post.ticker"
                    class="text-[10px] font-mono px-1.5 py-0.5 rounded flex-shrink-0"
                    style="background:rgba(96,165,250,0.12);color:#93c5fd;border:1px solid rgba(96,165,250,0.22)">
                {{ post.ticker }}
              </span>
            </div>
            <p class="text-[14px] font-semibold text-white/88 truncate">{{ post.title }}</p>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="text-[10px] text-white/30">{{ post.author }}</span>
              <span class="text-[10px] text-white/20">·</span>
              <span class="text-[10px] text-white/25 font-mono">{{ post.date }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0 text-[10px] text-white/25 font-mono">
            <span>{{ post.views }}</span>
            <span>{{ post.comments }}</span>
            <span v-if="post.likes > 0" class="text-amber-400/60">{{ post.likes }}</span>
          </div>
        </div>

        <!-- 데이터 없음 -->
        <div v-if="displayPosts.length === 0 && !loading"
             class="flex flex-col items-center justify-center py-16 gap-2">
          <span class="text-3xl">📋</span>
          <p class="text-[12px] text-white/30">게시글이 없습니다</p>
        </div>
      </div>
    </div>

    <!-- 하단 페이지네이션 -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-1.5 py-3 border-t border-white/8 flex-shrink-0">
      <button @click="page = Math.max(1, page - 1)" :disabled="page === 1"
              class="w-7 h-7 rounded-lg text-[12px] font-bold transition-all disabled:opacity-25"
              style="background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.5)">‹</button>
      <button v-for="p in totalPages" :key="p"
              @click="page = p"
              class="w-7 h-7 rounded-lg text-[12px] font-bold transition-all"
              :class="page === p
                ? 'bg-amber-500/25 text-amber-200 border border-amber-500/40'
                : 'text-white/35 hover:bg-white/8'">
        {{ p }}
      </button>
      <button @click="page = Math.min(totalPages, page + 1)" :disabled="page === totalPages"
              class="w-7 h-7 rounded-lg text-[12px] font-bold transition-all disabled:opacity-25"
              style="background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.5)">›</button>
    </div>

    <!-- ── 게시글 상세 오버레이 ── -->
    <transition name="slide-up">
      <div v-if="activePost"
           class="absolute inset-0 z-40 flex flex-col rounded-[2rem] overflow-hidden"
           style="background:linear-gradient(160deg,#141210 0%,#0e0c0a 100%)">

        <!-- 헤더 -->
        <div class="px-5 pt-4 pb-3 border-b border-white/10 flex-shrink-0">
          <div class="flex items-center gap-2 mb-2">
            <button @click="activePost = null"
                    class="flex items-center gap-1 text-white/45 hover:text-white/75 transition-colors">
              <LucideChevronLeft class="w-5 h-5" />
            </button>
            <span v-if="activePost.category"
                  class="text-[10px] font-bold px-1.5 py-0.5 rounded"
                  :style="categoryStyle(activePost.category)">{{ activePost.category }}</span>
            <span v-if="activePost.ticker"
                  class="text-[10px] font-mono px-1.5 py-0.5 rounded"
                  style="background:rgba(96,165,250,0.12);color:#93c5fd;border:1px solid rgba(96,165,250,0.22)">
              {{ activePost.ticker }}
            </span>
          </div>
          <h3 class="text-[16px] font-black leading-snug text-white/92">{{ activePost.title }}</h3>
          <div class="flex items-center gap-3 mt-2">
            <span class="text-[11px] text-white/40 font-bold">{{ activePost.author }}</span>
            <span class="text-[11px] text-white/25 font-mono">{{ activePost.date }}</span>
            <span class="text-[10px] text-white/22 ml-auto font-mono">{{ activePost.views }}</span>
          </div>
        </div>

        <!-- 본문 -->
        <div class="flex-1 overflow-y-auto px-5 py-4">
          <p class="text-[14px] text-white/72 leading-relaxed whitespace-pre-wrap">{{ activePost.body }}</p>

          <!-- 좋아요 -->
          <div class="flex justify-center mt-6">
            <button @click="activePost.likes++"
                    class="flex items-center gap-2 px-5 py-2 rounded-full border transition-all"
                    style="background:rgba(251,191,36,0.08);border-color:rgba(251,191,36,0.22);color:rgba(251,191,36,0.75)">
              <span class="text-sm font-bold">+</span>
              <span class="text-[12px] font-bold">{{ activePost.likes }}</span>
            </button>
          </div>

          <!-- 댓글 -->
          <div class="mt-5 border-t border-white/8 pt-4">
            <p class="text-[11px] text-white/35 uppercase tracking-widest mb-3">댓글 {{ activePost.commentList?.length ?? 0 }}</p>
            <div v-for="c in (activePost.commentList ?? [])" :key="c.id"
                 class="mb-3 p-3 rounded-xl"
                 style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07)">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-[11px] font-bold text-white/55">{{ c.author }}</span>
                <span class="text-[10px] text-white/22 font-mono ml-auto">{{ c.date }}</span>
              </div>
              <p class="text-[13px] text-white/70">{{ c.text }}</p>
            </div>
            <!-- 댓글 입력 -->
            <div class="flex gap-2 mt-2">
              <input v-model="newComment" type="text" placeholder="댓글을 입력하세요"
                     class="flex-1 px-3 py-2 rounded-xl text-[13px] bg-black/25 border border-white/10 text-white/80 outline-none placeholder:text-white/22"
                     @keydown.enter="submitComment" />
              <button @click="submitComment"
                      class="px-3 py-2 rounded-xl text-[12px] font-bold flex-shrink-0 transition-all"
                      style="background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.28)">
                등록
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- ── 글쓰기 오버레이 ── -->
    <transition name="slide-up">
      <div v-if="showWrite"
           class="absolute inset-0 z-40 flex flex-col rounded-[2rem] overflow-hidden"
           style="background:linear-gradient(160deg,#141210 0%,#0e0c0a 100%)">

        <div class="px-5 pt-4 pb-3 border-b border-white/10 flex-shrink-0 flex items-center gap-2">
          <button @click="showWrite = false" class="text-white/45 hover:text-white/75 transition-colors">
            <LucideChevronLeft class="w-5 h-5" />
          </button>
          <span class="text-[13px] font-black text-white/85 flex-1">새 게시글</span>
          <button @click="submitPost"
                  class="px-3 py-1.5 rounded-xl text-[12px] font-bold transition-all"
                  style="background:rgba(251,191,36,0.2);color:#fbbf24;border:1px solid rgba(251,191,36,0.35)">
            등록
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          <!-- 카테고리 -->
          <div>
            <p class="text-[11px] text-white/35 uppercase tracking-widest mb-1.5">카테고리</p>
            <div class="flex gap-1.5 flex-wrap">
              <button v-for="cat in CATEGORIES" :key="cat"
                      @click="newPost.category = cat"
                      class="px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all"
                      :style="newPost.category === cat ? categoryStyle(cat) : 'background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.4);border:1px solid rgba(255,255,255,0.10)'">
                {{ cat }}
              </button>
            </div>
          </div>
          <!-- 티커 (선택) -->
          <div>
            <p class="text-[11px] text-white/35 uppercase tracking-widest mb-1.5">종목 티커 (선택)</p>
            <input v-model="newPost.ticker" type="text" placeholder="예) 005930"
                   class="w-full px-3 py-2 rounded-xl text-[13px] bg-black/25 border border-white/10 text-white/80 outline-none placeholder:text-white/22" />
          </div>
          <!-- 제목 -->
          <div>
            <p class="text-[11px] text-white/35 uppercase tracking-widest mb-1.5">제목</p>
            <input v-model="newPost.title" type="text" placeholder="제목을 입력하세요"
                   class="w-full px-3 py-2 rounded-xl text-[13px] bg-black/25 border border-white/10 text-white/80 outline-none placeholder:text-white/22" />
          </div>
          <!-- 본문 -->
          <div>
            <p class="text-[11px] text-white/35 uppercase tracking-widest mb-1.5">내용</p>
            <textarea v-model="newPost.body" rows="8" placeholder="내용을 입력하세요"
                      class="w-full px-3 py-2 rounded-xl text-[13px] bg-black/25 border border-white/10 text-white/80 outline-none placeholder:text-white/22 resize-none leading-relaxed">
            </textarea>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { LucideLayoutList, LucidePencil, LucideChevronLeft } from 'lucide-vue-next'

const TABS = [
  { key: 'all',    label: '전체' },
  { key: 'stock',  label: '종목토론' },
  { key: 'quant',  label: '퀀트분석' },
  { key: 'free',   label: '자유' },
]

const CATEGORIES = ['종목토론', '퀀트분석', '시장분석', '자유', '공지']

const activeTab  = ref('all')
const page       = ref(1)
const PER_PAGE   = 15

const activePost  = ref(null)
const showWrite   = ref(false)
const newComment  = ref('')

const newPost = ref({ category: '자유', ticker: '', title: '', body: '' })

const loading = ref(false)

// ── 목업 데이터 ──────────────────────────────────
const posts = ref([
  {
    id: 15, category: '퀀트분석', ticker: '005930', title: '삼성전자 AI 점수 급등 — 매수 타이밍 분석',
    author: 'quant_master', date: '2026-05-27', views: 1240, likes: 38, comments: 12,
    body: '최근 AI 추천 점수가 72점으로 급등했습니다. 반도체 섹터 전반이 상승 모멘텀을 보이는 가운데 삼성전자의 퀀트 지표가 크게 개선되었습니다.\n\nPER 12.4, PBR 1.3으로 밸류에이션이 매력적인 구간입니다. 물량 분할 매수 전략을 추천드립니다.',
    commentList: [
      { id: 1, author: 'user01', date: '05-27', text: '동의합니다. 저도 분할 매수 진행 중입니다.' },
      { id: 2, author: 'trader_k', date: '05-27', text: '반도체 업황 회복 시그널이 나오고 있네요.' },
    ]
  },
  {
    id: 14, category: '종목토론', ticker: '000660', title: 'SK하이닉스 HBM 수주 호재 — 단기 vs 장기 전망',
    author: 'invest_pro', date: '2026-05-27', views: 890, likes: 24, comments: 8,
    body: 'HBM3E 대규모 수주 소식이 들어왔습니다. 단기적으로 주가 상승이 예상되지만, 이미 많이 올라있는 상태라 추격 매수는 신중해야 할 것 같습니다.',
    commentList: []
  },
  {
    id: 13, category: '시장분석', ticker: null, title: '2026년 5월 코스피 섹터별 AI 점수 요약',
    author: 'market_watcher', date: '2026-05-26', views: 756, likes: 31, comments: 5,
    body: 'IT 섹터 평균 점수: 68점\n금융 섹터 평균 점수: 54점\n에너지 섹터 평균 점수: 49점\n\n전반적으로 IT 섹터가 강세를 보이고 있으며, 반도체·2차전지 관련주가 상위권을 차지하고 있습니다.',
    commentList: []
  },
  {
    id: 12, category: '자유', ticker: null, title: '퀀트 투자 입문자를 위한 AI 점수 활용법',
    author: 'newbie_guide', date: '2026-05-26', views: 2134, likes: 87, comments: 23,
    body: 'AI 점수 보는 방법을 정리해 드립니다.\n\n• A티어(80점+): 강력 매수 신호\n• B티어(60점+): 매수 고려\n• C티어(40점+): 관망\n• D티어(40점 미만): 매도 또는 회피\n\n점수는 매일 업데이트되므로 정기적으로 확인하는 것이 중요합니다.',
    commentList: []
  },
  {
    id: 11, category: '퀀트분석', ticker: '035720', title: '카카오 저점 매수 가능성 검토',
    author: 'deep_value', date: '2026-05-25', views: 445, likes: 9, comments: 4,
    body: '현재 D티어로 분류되어 있지만, PBR이 1.0 이하로 역사적 저점 수준입니다. 반등 시 빠른 점수 상승이 기대됩니다.',
    commentList: []
  },
  {
    id: 10, category: '종목토론', ticker: '207940', title: '삼성바이오로직스 임상 결과 기대감',
    author: 'bio_trader', date: '2026-05-25', views: 612, likes: 15, comments: 7,
    body: '3분기 임상 발표를 앞두고 기대감이 높아지고 있습니다. AI 점수도 서서히 상승 중입니다.',
    commentList: []
  },
  {
    id: 9, category: '시장분석', ticker: null, title: '코스피 2800 돌파 — 다음 저항선은?',
    author: 'chart_king', date: '2026-05-24', views: 1087, likes: 42, comments: 18,
    body: '기술적 분석 관점에서 2800~2850 구간이 주요 저항선입니다. 이 구간을 돌파할 경우 3000 목표를 기대해볼 수 있습니다.',
    commentList: []
  },
  {
    id: 8, category: '자유', ticker: null, title: '이 앱 포트폴리오 기능 너무 좋네요',
    author: 'happy_user', date: '2026-05-24', views: 334, likes: 28, comments: 11,
    body: 'AI 추천 Top10으로 포트폴리오 자동 구성해주는 기능이 특히 마음에 듭니다. 자동매매 기능도 기대됩니다!',
    commentList: []
  },
])

const pinnedPosts = ref([
  {
    id: 0, title: '[공지] 게시판 이용 규칙 및 안내', author: '관리자',
    date: '2026-01-01', views: 5420, likes: 0, comments: 2,
    body: '게시판 이용 시 다음 사항을 준수해주세요.\n\n1. 허위 정보 및 과도한 종목 추천 금지\n2. 욕설 및 비방 금지\n3. 투자는 본인 책임 하에 진행하시기 바랍니다.',
    commentList: []
  },
])

// ── 탭 필터 ──────────────────────────────────────
const filteredPosts = computed(() => {
  if (activeTab.value === 'all') return posts.value
  const map = { stock: '종목토론', quant: '퀀트분석', free: '자유' }
  const cat = map[activeTab.value]
  return posts.value.filter(p => p.category === cat)
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredPosts.value.length / PER_PAGE)))

const displayPosts = computed(() => {
  const start = (page.value - 1) * PER_PAGE
  return filteredPosts.value.slice(start, start + PER_PAGE)
})

// ── 카테고리 스타일 ───────────────────────────────
const categoryStyle = (cat) => ({
  '종목토론': 'background:rgba(96,165,250,0.15);color:#93c5fd;border:1px solid rgba(96,165,250,0.28)',
  '퀀트분석': 'background:rgba(52,211,153,0.15);color:#34d399;border:1px solid rgba(52,211,153,0.28)',
  '시장분석': 'background:rgba(167,139,250,0.15);color:#a78bfa;border:1px solid rgba(167,139,250,0.28)',
  '자유':     'background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.28)',
  '공지':     'background:rgba(248,113,113,0.15);color:#f87171;border:1px solid rgba(248,113,113,0.28)',
}[cat] ?? 'background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.4)')

// ── 게시글 열기 ───────────────────────────────────
function openPost(post) {
  post.views++
  activePost.value = post
}

// ── 댓글 등록 ────────────────────────────────────
function submitComment() {
  const text = newComment.value.trim()
  if (!text || !activePost.value) return
  if (!activePost.value.commentList) activePost.value.commentList = []
  activePost.value.commentList.push({
    id:     Date.now(),
    author: '나',
    date:   new Date().toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }).replace('. ', '-').replace('.',''),
    text,
  })
  activePost.value.comments++
  newComment.value = ''
}

// ── 글 등록 ──────────────────────────────────────
function openWrite() {
  newPost.value = { category: '자유', ticker: '', title: '', body: '' }
  showWrite.value = true
}

function submitPost() {
  const { category, ticker, title, body } = newPost.value
  if (!title.trim() || !body.trim()) return
  const newId = Math.max(...posts.value.map(p => p.id), 0) + 1
  posts.value.unshift({
    id: newId, category, ticker: ticker.trim() || null, title: title.trim(),
    author: '나', date: new Date().toISOString().slice(0, 10),
    views: 0, likes: 0, comments: 0, body: body.trim(), commentList: [],
  })
  showWrite.value = false
}
</script>

<style scoped>
.slide-up-enter-active { transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.2s ease; }
.slide-up-leave-active { transition: transform 0.22s ease-in, opacity 0.18s ease; }
.slide-up-enter-from,
.slide-up-leave-to    { transform: translateY(30px); opacity: 0; }
</style>
