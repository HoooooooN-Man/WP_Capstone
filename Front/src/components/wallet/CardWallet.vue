<template>
  <div class="card-wallet w-full min-h-screen flex flex-col items-center justify-end relative font-sans overflow-hidden pb-0 transition-colors duration-300"
       :class="darkMode ? 'text-white' : 'text-gray-900'">

    <!-- 배경 -->
    <div class="fixed inset-0 z-[-1] overflow-hidden transition-colors duration-500"
         :class="darkMode ? 'bg-gradient-to-br from-[#0a0804] via-[#060402] to-[#0d0a05]' : 'bg-gradient-to-br from-[#f0ebe0] via-[#e8e0d0] to-[#ede6d8]'">
      <template v-if="darkMode">
        <div class="absolute w-[140vw] h-[80vh] bg-[#2a1e08] rounded-full blur-[160px] -top-[20vh] left-0 opacity-25"></div>
        <div class="absolute w-[100vw] h-[60vh] bg-[#1a1208] rounded-full blur-[120px] -bottom-[10vh] right-0 opacity-20"></div>
        <div class="absolute w-[60vw] h-[60vh] bg-[#3a2a0a] rounded-full blur-[100px] top-[20vh] right-[10vw] opacity-10"></div>
        <div class="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/30"></div>
      </template>
      <template v-else>
        <div class="absolute w-[140vw] h-[80vh] bg-[#e8d5b0] rounded-full blur-[160px] -top-[20vh] left-0 opacity-50"></div>
        <div class="absolute w-[100vw] h-[60vh] bg-[#d4c090] rounded-full blur-[120px] -bottom-[10vh] right-0 opacity-30"></div>
        <div class="absolute w-[60vw] h-[60vh] bg-[#f0e0c0] rounded-full blur-[100px] top-[20vh] right-[10vw] opacity-25"></div>
      </template>
    </div>

    <!-- 메인 컨텐츠 -->
    <!-- absolute 래퍼 안에 각 뷰가 absolute inset-0으로 겹침 → mode 없이 동시 fade 가능 -->
    <!-- 고정 모드(비포트폴리오)일 때 지갑 바(100px)와 겹치지 않도록 bottom 확보 -->
    <div class="absolute top-[1.5%] left-[1%] right-[1%] z-0 overflow-hidden rounded-[2rem]"
         :style="{
           bottom: activeCard === 'portfolio'
             ? (menuBarLocked ? '224px' : '10px')
             : (menuBarLocked ? '104px' : '10px'),
           transition: 'bottom 0.38s cubic-bezier(0.32,0,0.2,1)',
         }">
      <transition name="fade-scale">
        <ProfileView   v-if="activeCard === 'profile'"   key="profile"
          class="absolute inset-0"
          :user="user" :menu-bar-locked="menuBarLocked"
          @toggle-menu-lock="toggleMenuLock"
          @navigate="activeCard = $event" />
        <FlashCardView v-else-if="activeCard === 'feed'" key="feed"
          class="absolute inset-0" />
        <CompanyView   v-else-if="activeCard === 'company'" key="company"
          class="absolute inset-0"
          :replace-mode="replaceMode"
          :replace-stock="replaceStock"
          :view-ticker="viewTicker"
          @select-company="handleCompanySelect"
          @add-company="handleCompanyAdd"
          @back="handleCompanyBack"
          @sell-replace="handleSellReplace"
        />
        <PortfolioView v-else-if="activeCard === 'portfolio'" key="portfolio"
          class="absolute inset-0"
          :portfolio-groups="portfolioGroups"
          :active-group-id="activeGroupId"
          v-model:current-index="portfolioCurrentIndex"
          @view-company="handleViewCompany"
        />
        <BoardView v-else-if="activeCard === 'board'" key="board"
          class="absolute inset-0" />
        <div v-else key="standby" class="absolute inset-0 flex items-center justify-center animate-fade-in-delayed">
          <h2 class="text-4xl font-black italic tracking-tighter text-white uppercase opacity-20">{{ activeCard }} MODULE STANDBY</h2>
        </div>
      </transition>
    </div>

    <!-- 바닥 호버 트리거 — 고정이거나 포트폴리오 모드엔 비활성 -->
    <div v-show="!menuBarLocked && activeCard !== 'portfolio'"
         class="fixed bottom-0 left-0 right-0 h-4 z-20"
         @mouseenter="walletVisible = true"></div>

    <!-- 지갑 바 + 게시판 버튼 — 포트폴리오 모드엔 숨김, 함께 슬라이드 -->
    <div v-show="activeCard !== 'portfolio'"
         class="fixed bottom-0 left-0 right-0 z-10"
         :style="{
           transform: (menuBarLocked || walletVisible) ? 'translateY(0)' : 'translateY(100%)',
           transition: 'transform 0.38s cubic-bezier(0.32, 0, 0.2, 1)'
         }"
         @mouseleave="!menuBarLocked && (walletVisible = false)">

      <!-- 게시판 버튼 — 지갑 바 위, 오른쪽 끝에 붙여서 함께 슬라이드 -->
      <div class="flex justify-end px-5 pb-2 pt-1.5 pointer-events-none">
        <button
          class="pointer-events-auto flex flex-col items-center gap-1 px-3 py-2 rounded-2xl border transition-all duration-200 shadow-lg"
          :class="activeCard === 'board'
            ? 'border-[rgba(201,162,39,0.45)] text-[rgba(201,162,39,0.9)]'
            : 'border-white/10 text-white/40 hover:text-white/65 hover:border-white/20'"
          :style="activeCard === 'board'
            ? 'background: rgba(201,162,39,0.14);'
            : 'background: rgba(20,14,6,0.75);'"
          @click="activeCard = activeCard === 'board' ? 'profile' : 'board'"
        >
          <LucideLayoutList class="w-4 h-4" />
          <span class="text-[10px] font-bold tracking-wide leading-none">게시판</span>
        </button>
      </div>

      <!-- 지갑 바 -->
      <div class="flex justify-center">
      <div class="wallet-bar relative z-10 w-full max-w-[860px] rounded-t-[2rem] overflow-visible flex border-t"
           style="border-color: rgba(201,162,39,0.38)">


        <!-- ── 중앙 부드러운 접힘 (선 없이 그라디언트 그림자만) ── -->
        <div class="absolute left-1/2 -translate-x-1/2 inset-y-0 pointer-events-none z-[10]"
             style="width: 52px">
          <!-- 왼쪽 페이지 끝 → 중심으로 어두워짐 -->
          <div class="absolute left-0 inset-y-0 w-1/2 rounded-r-none"
               style="background: linear-gradient(to right, transparent 0%, rgba(0,0,0,0.42) 100%)"></div>
          <!-- 오른쪽 페이지 끝 → 중심으로 어두워짐 -->
          <div class="absolute right-0 inset-y-0 w-1/2"
               style="background: linear-gradient(to left, transparent 0%, rgba(0,0,0,0.42) 100%)"></div>
        </div>

        <!-- ── 카드 슬롯 ── -->
        <div class="w-full h-full flex relative z-10">

          <!-- 왼쪽 열 -->
          <div class="flex-1 flex flex-col items-center pt-0 pb-2 gap-0">

            <!-- 슬롯 1: Profile -->
            <div class="w-[74%] flex-1 relative">
              <div
                @click="activeCard = 'profile'"
                class="absolute top-0 left-[3px] right-[3px] bottom-0 rounded-t-[10px] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2.5 overflow-hidden"
                style="background: linear-gradient(135deg, #f7f4ee 0%, #e8e2d4 100%);"
                :class="activeCard === 'profile' ? '-translate-y-1' : 'hover:-translate-y-1'"
              >
                <!-- 신분증 컬러 스트라이프 -->
                <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-gradient-to-b from-[#1a3a6b] via-[#c9a227] to-[#1a3a6b] flex-shrink-0"></div>
                <div class="w-6 h-6 rounded bg-black/6 flex items-center justify-center flex-shrink-0 ml-1">
                  <LucideUser class="w-3.5 h-3.5 text-black/55" />
                </div>
                <div class="flex flex-col justify-center min-w-0">
                  <span class="text-[13px] font-bold text-gray-800 leading-tight truncate">{{ user.name || 'User' }}</span>
                  <span class="text-[10px] font-bold text-gray-400 leading-tight tracking-widest uppercase" style="font-family:sans-serif;">Personal ID</span>
                </div>
              </div>
              <div class="absolute bottom-0 w-full h-[4px] bg-[#090705] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] pointer-events-none rounded-b-sm"></div>
            </div>

            <!-- 슬롯 2: Feed -->
            <div class="w-[74%] flex-1 relative">
              <div
                @click="activeCard = 'feed'"
                class="absolute top-0 left-[3px] right-[3px] bottom-0 rounded-t-[10px] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2 overflow-hidden"
                style="background: linear-gradient(135deg, #f0e8d0 0%, #e4dcc4 100%); border-top: 2px solid #1a1209;"
                :class="activeCard === 'feed' ? '-translate-y-2' : 'hover:-translate-y-2'"
              >
                <LucideNewspaper class="w-4 h-4 flex-shrink-0" style="color:#1a1209; opacity:0.6;" />
                <div class="flex flex-col justify-center min-w-0">
                  <span class="text-[9px] font-bold tracking-widest uppercase leading-none" style="color:#999; font-family:sans-serif;">Latest</span>
                  <span class="text-[13px] font-black text-gray-800 leading-tight tracking-tight" style="font-family:Georgia,serif;">Feed</span>
                </div>
              </div>
              <div class="absolute bottom-0 left-0 right-0 h-[8px] pointer-events-none z-[24]"
                   style="background: linear-gradient(to bottom, #181208, #0f0c06)"></div>
              <div class="absolute bottom-[8px] w-full h-[4px] bg-[#090705] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-[25] pointer-events-none rounded-b-sm"></div>
            </div>

          </div>

          <!-- 오른쪽 열 -->
          <div class="flex-1 flex flex-col items-center pt-0 pb-2 gap-0">

            <!-- 슬롯 3: Company -->
            <div class="w-[74%] flex-1 relative">
              <div
                @click="activeCard = 'company'"
                class="absolute top-0 left-[3px] right-[3px] bottom-0 rounded-t-[10px] bg-gradient-to-br from-[#1f3756] to-[#14253a] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2"
                :class="activeCard === 'company' ? '-translate-y-1' : 'hover:-translate-y-1'"
              >
                <LucideBuilding2 class="w-4 h-4 text-blue-200 flex-shrink-0" />
                <span class="text-[13px] font-bold text-gray-100 tracking-wide">종목 리스트</span>
              </div>
              <div class="absolute bottom-0 w-full h-[4px] bg-[#090705] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] pointer-events-none rounded-b-sm"></div>
            </div>

            <!-- 슬롯 4: Portfolio -->
            <div class="w-[74%] flex-1 relative">
              <div
                @click="activeCard = 'portfolio'; $emit('toggle-portfolio')"
                class="absolute top-0 left-[3px] right-[3px] bottom-0 rounded-t-[10px] bg-gradient-to-br from-[#007ad9] to-[#0052a3] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2"
                :class="activeCard === 'portfolio' ? '-translate-y-2' : 'hover:-translate-y-2'"
              >
                <LucideFolder class="w-4 h-4 text-blue-100 flex-shrink-0" />
                <span class="text-[13px] font-bold text-white tracking-wide">Portfolio</span>
              </div>
              <div class="absolute bottom-0 left-0 right-0 h-[8px] pointer-events-none z-[24]"
                   style="background: linear-gradient(to bottom, #181208, #0f0c06)"></div>
              <div class="absolute bottom-[8px] w-full h-[4px] bg-[#090705] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-[25] pointer-events-none rounded-b-sm"></div>
            </div>

          </div>
        </div>

      </div><!-- /wallet-bar -->
      </div><!-- /flex justify-center -->
    </div><!-- /지갑 바 + 게시판 wrapper -->

    <!-- ── 포트폴리오 팬 스트립 — 지갑 바와 동일한 레벨 (fixed bottom) ── -->
    <div v-if="activeCard === 'portfolio'"
         class="fixed bottom-0 left-0 right-0 z-10"
         style="height:220px">
      <PortfolioFanStrip
        :display-items="portfolioDisplayItems"
        :current-index="portfolioCurrentIndex"
        :total-value="portfolioTotalValue"
        :total-return="portfolioTotalReturn"
        :active-stocks-count="portfolioActiveStocks.length"
        :auto-trade-state="autoTradeState"
        :wallet-locked="menuBarLocked"
        @update:current-index="portfolioCurrentIndex = $event"
        @fan-open="portfolioFanOpen = $event"
        @back="handlePortfolioBack"
        @liquidate="handlePortfolioLiquidate"
        @replace="handleReplace"
        @view-company="handleViewCompany"
        @toggle-auto-trade="handleToggleAutoTrade"
      />
    </div>

    <!-- 자동매매 결과 (포트폴리오 팬 바로 위) -->
    <transition name="trade-log">
      <div v-if="tradeLog && activeCard === 'portfolio'"
           class="fixed z-40 left-4 right-4 rounded-xl border border-white/10 overflow-hidden text-[12px] text-white"
           style="bottom:218px;background:linear-gradient(135deg,#0a1e0e,#0d1a0a)">
        <div class="px-3 py-1.5 border-b border-white/10 flex items-center gap-1.5">
          <div class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></div>
          <p class="text-[10px] text-green-400 font-bold uppercase tracking-widest">자동매매 완료</p>
        </div>
        <div class="px-3 py-1.5 space-y-0.5">
          <div v-if="tradeLog.bought.length" class="flex gap-2">
            <span class="text-blue-400 font-black flex-shrink-0">추가</span>
            <span class="text-white/55">{{ tradeLog.bought.join(', ') }}</span>
          </div>
          <div v-if="tradeLog.sold.length" class="flex gap-2">
            <span class="text-red-400 font-black flex-shrink-0">삭제</span>
            <span class="text-white/55">{{ tradeLog.sold.join(', ') }}</span>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { LucideUser, LucideSparkles, LucideBuilding2, LucideFolder, LucideLayoutList, LucideNewspaper } from 'lucide-vue-next'
import ProfileView   from '@/components/views/ProfileView.vue'
import FlashCardView from '@/components/views/FlashCardView.vue'
import CompanyView   from '@/components/views/CompanyView.vue'
import PortfolioView from '@/components/views/PortfolioView.vue'
import BoardView     from '@/components/views/BoardView.vue'
import PortfolioFanStrip from '@/components/portfolio/PortfolioFanStrip.vue'
import { useStocksStore } from '@/stores/stocks.js'
import { stocksApi } from '@/api/stocks.js'

const stocksStore = useStocksStore()

const props = defineProps({
  user: { type: Object, required: true, default: () => ({ name: '', style: '', totalAsset: '' }) }
});

const emit = defineEmits(['toggle-wallet', 'toggle-portfolio']);
const activeCard    = ref('profile');
const viewTicker    = ref(null);
const darkMode      = ref(true);
const walletVisible = ref(false);

// 메뉴바 고정 (localStorage 영속)
const menuBarLocked = ref(JSON.parse(localStorage.getItem('wp_menubar_locked') ?? 'false'))
const toggleMenuLock = () => {
  menuBarLocked.value = !menuBarLocked.value
  localStorage.setItem('wp_menubar_locked', JSON.stringify(menuBarLocked.value))
  if (menuBarLocked.value) walletVisible.value = true
}

// AI 추천 Top10 → 포트폴리오 초기 종목
const TIER_COLORS = { A: '#1D9E75', B: '#378ADD', C: '#EF9F27', D: '#E24B4A' }

const portfolioGroups = ref([
  { id: 1, name: 'AI 추천 포트폴리오', stocks: [] }
]);
const activeGroupId = ref(1);
const activeGroup   = computed(() => portfolioGroups.value.find(g => g.id === activeGroupId.value));

// ── 포트폴리오 팬 스트립 상태 (CardWallet 레벨로 이동) ──
const portfolioCurrentIndex = ref(0)
watch(() => activeGroupId.value, () => { portfolioCurrentIndex.value = 0 })
const portfolioFanOpen = ref(false)

const portfolioActiveStocks = computed(() => activeGroup.value?.stocks ?? [])
const portfolioDisplayItems = computed(() => [
  { isOverview: true, id: '__overview__', color: '#c9a227' },
  ...portfolioActiveStocks.value,
])
const portfolioTotalValue = computed(() =>
  portfolioActiveStocks.value.reduce((s, p) => s + p.currentPrice, 0)
)
const portfolioTotalReturn = computed(() => 0)
const handlePortfolioLiquidate = (si) => {
  handleLiquidate(si)
  if (portfolioCurrentIndex.value > 1 && portfolioCurrentIndex.value >= portfolioDisplayItems.value.length - 1)
    portfolioCurrentIndex.value--
}

onMounted(async () => {
  try {
    const { data } = await stocksApi.getRecommendations({ top_k: 10 })
    const items = data.items ?? []
    console.log('[Portfolio] AI 추천 종목:', items.length, '개', items)
    portfolioGroups.value[0].stocks = items.map((item, i) => ({
      id:           i + 1,
      company:      item.name ?? item.ticker,
      ticker:       item.ticker,
      sector:       item.sector ?? 'Market',
      currentPrice: item.close ?? 0,
      change:       0,
      color:        TIER_COLORS[item.tier ?? 'C'] ?? '#4A90E2',
      weight:       10,
      quantScore:   Math.round(item.score ?? 50),
    }))
  } catch (err) {
    console.error('[Portfolio] AI 추천 API 실패:', err?.response?.status, err?.response?.data ?? err?.message)
    portfolioGroups.value[0].stocks = []
  }
});

// 교체 모드 상태
const replaceMode  = ref(false);
const replaceIndex = ref(-1);
const replaceStock = ref(null);

// ── 포트폴리오 그룹 관리 ───────────────────────
const handleRemoveGroup = (id) => {
  const idx = portfolioGroups.value.findIndex(g => g.id === id);
  if (idx < 0 || portfolioGroups.value.length <= 1) return;
  portfolioGroups.value.splice(idx, 1);
  if (activeGroupId.value === id)
    activeGroupId.value = portfolioGroups.value[Math.max(0, idx - 1)].id;
};

const handleRenameGroup = (id, name) => {
  const g = portfolioGroups.value.find(g => g.id === id);
  if (g) g.name = name;
};

const handleSwitchGroup = (id) => { activeGroupId.value = id; };

// ── 종목 관리 ──────────────────────────────────
const handleLiquidate = (index) => {
  activeGroup.value?.stocks.splice(index, 1);
};

const handleReplace = (index) => {
  replaceIndex.value = index;
  replaceStock.value = activeGroup.value?.stocks[index] ?? null;
  replaceMode.value  = true;
  activeCard.value   = 'company';
};

const handleCompanySelect = (company) => {
  if (replaceIndex.value >= 0 && activeGroup.value)
    activeGroup.value.stocks.splice(replaceIndex.value, 1, company);
  replaceMode.value  = false;
  replaceIndex.value = -1;
  replaceStock.value = null;
  activeCard.value   = 'portfolio';
};

const handleCompanyAdd = (company) => {
  activeGroup.value?.stocks.push(company);
};

const handleSellReplace = () => {
  if (replaceIndex.value >= 0 && activeGroup.value)
    activeGroup.value.stocks.splice(replaceIndex.value, 1);
  replaceMode.value  = false;
  replaceIndex.value = -1;
  replaceStock.value = null;
  activeCard.value   = 'portfolio';
};

const handleViewCompany = (ticker) => {
  viewTicker.value  = ticker;
  activeCard.value  = 'company';
};

const handleCompanyBack = () => {
  viewTicker.value = null;
  activeCard.value = 'portfolio';
};

// 포트폴리오 뷰 → 뒤로가기 (Company List로)
const handlePortfolioBack = () => {
  activeCard.value = 'company';
};

// ── 자동매매 ───────────────────────────────────
const BUY_THRESHOLD  = 70;  // 퀀트스코어 ≥ 70 → 추가
const SELL_THRESHOLD = 45;  // 퀀트스코어 < 45 → 삭제

const autoTradeState = ref('off'); // 'off' | 'analyzing' | 'on'
const tradeLog       = ref(null);

const runAutoTrade = () => {
  const stocks = activeGroup.value?.stocks;
  if (!stocks) return;

  const bought = [];
  const sold   = [];

  // 낮은 점수 종목 삭제
  for (let i = stocks.length - 1; i >= 0; i--) {
    if ((stocks[i].quantScore ?? 50) < SELL_THRESHOLD) {
      sold.push(stocks[i].company);
      stocks.splice(i, 1);
    }
  }

  // 높은 점수 미포함 종목 추가 (실제 API 데이터만 사용)
  const currentTickers = new Set(stocks.map(s => s.ticker));
  const candidateList  = stocksStore.items
  for (const c of candidateList) {
    const score = c.quantScore ?? c.score ?? 50
    const name  = c.name ?? c.company ?? c.ticker
    if (score >= BUY_THRESHOLD && !currentTickers.has(c.ticker)) {
      bought.push(name)
      stocks.push({
        id: Date.now() + Math.random(),
        company: name, ticker: c.ticker, sector: c.sector ?? '',
        currentPrice: c.price ?? 0,
        change: c.change ?? 0, color: c.color ?? '#4A90E2', weight: 10,
        quantScore: score,
      });
    }
  }

  if (bought.length || sold.length) {
    tradeLog.value = { bought, sold };
    setTimeout(() => { tradeLog.value = null; }, 5000);
  }
};

const handleToggleAutoTrade = () => {
  if (autoTradeState.value !== 'off') {
    autoTradeState.value = 'off';
    return;
  }
  autoTradeState.value = 'analyzing';
  setTimeout(() => {
    runAutoTrade();
    autoTradeState.value = 'on';
  }, 1400);
};
</script>

<style scoped>
.wallet-bar {
  background: linear-gradient(180deg, #1e1509 0%, #161008 55%, #191209 100%);
  box-shadow: 0 -16px 48px rgba(0,0,0,0.7);
  height: 100px;
}

.animate-slide-up-wallet {
  animation: slide-up-wallet 1s var(--ease-wallet) forwards;
}

.animate-fade-in-delayed {
  opacity: 0;
  animation: fade-in-delayed 0.5s ease forwards;
}
</style>
