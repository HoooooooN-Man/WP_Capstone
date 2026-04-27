<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { useThemeStore } from '@/stores/theme.js'
import api from '@/api/axios.js'

const router = useRouter()
const auth   = useAuthStore()
const theme  = useThemeStore()

const activeTab = ref('portfolio')  // 'portfolio' | 'watchlist' | 'settings'

// ── 내 포트폴리오 (localStorage) ──────────────────────────────────────────────
const PORT_KEY = 'my_portfolio'
const holdings = ref([])
const priceMap = ref({})
const loadingPrices = ref(false)

function loadHoldings() {
  holdings.value = JSON.parse(localStorage.getItem(PORT_KEY) || '[]')
}

function saveHoldings() {
  localStorage.setItem(PORT_KEY, JSON.stringify(holdings.value))
}

// 현재가 fetch
async function fetchPrices() {
  if (!holdings.value.length) return
  loadingPrices.value = true
  const tickers = [...new Set(holdings.value.map(h => h.ticker))]
  try {
    const promises = tickers.map(t =>
      api.get(`/stocks/${t}/price`).then(r => ({ ticker: t, price: r.data.close ?? r.data.current_price ?? 0 }))
                                   .catch(() => ({ ticker: t, price: 0 }))
    )
    const results = await Promise.all(promises)
    priceMap.value = Object.fromEntries(results.map(r => [r.ticker, r.price]))
  } catch {}
  finally { loadingPrices.value = false }
}

// ── 개별 종목 수익률 ──────────────────────────────────────────────────────────
function profit(h) {
  const current = priceMap.value[h.ticker] || h.buy_price
  return (current - h.buy_price) * h.qty
}

function profitPct(h) {
  const current = priceMap.value[h.ticker] || h.buy_price
  return ((current - h.buy_price) / h.buy_price) * 100
}

function currentValue(h) {
  const current = priceMap.value[h.ticker] || h.buy_price
  return current * h.qty
}

// ── 포트폴리오 요약 ───────────────────────────────────────────────────────────
const totalBuy = computed(() =>
  holdings.value.reduce((s, h) => s + h.buy_price * h.qty, 0)
)
const totalValue = computed(() =>
  holdings.value.reduce((s, h) => s + currentValue(h), 0)
)
const totalProfit = computed(() => totalValue.value - totalBuy.value)
const totalProfitPct = computed(() =>
  totalBuy.value ? (totalProfit.value / totalBuy.value) * 100 : 0
)

// ── 추가 / 삭제 ───────────────────────────────────────────────────────────────
const addForm = ref({ ticker: '', name: '', buy_price: '', qty: '', sector: '' })
const addError = ref('')
const showAddForm = ref(false)

function addHolding() {
  addError.value = ''
  const { ticker, buy_price, qty } = addForm.value
  if (!ticker || !buy_price || !qty) { addError.value = '종목코드, 매수가, 수량을 입력하세요'; return }
  if (isNaN(Number(buy_price)) || isNaN(Number(qty))) { addError.value = '숫자를 입력하세요'; return }

  holdings.value.push({
    ticker: ticker.trim().toUpperCase(),
    name:   addForm.value.name || ticker,
    buy_price: Number(buy_price),
    qty:  Number(qty),
    added_at: new Date().toISOString(),
  })
  saveHoldings()
  fetchPrices()
  addForm.value = { ticker: '', name: '', buy_price: '', qty: '', sector: '' }
  showAddForm.value = false
}

function removeHolding(idx) {
  holdings.value.splice(idx, 1)
  saveHoldings()
}

function formatKRW(n) {
  if (Math.abs(n) >= 1e8)  return (n / 1e8).toFixed(1) + '억'
  if (Math.abs(n) >= 1e4)  return (n / 1e4).toFixed(0) + '만'
  return n.toFixed(0)
}

onMounted(() => {
  loadHoldings()
  fetchPrices()
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-4 md:py-6 pb-20 md:pb-6">

    <!-- 헤더 -->
    <div class="mb-6">
      <div class="flex items-center gap-3">
        <div
          class="w-12 h-12 rounded-full flex items-center justify-center text-xl"
          :class="theme.isDark ? 'bg-white/10' : 'bg-gray-100'"
        >
          👤
        </div>
        <div>
          <h1 class="text-xl font-semibold">{{ auth.nickname ?? '사용자' }}</h1>
          <p class="text-sm" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">마이페이지</p>
        </div>
      </div>
    </div>

    <!-- 탭 -->
    <div
      class="flex rounded-xl p-1 mb-6 gap-1"
      :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-gray-100'"
    >
      <button
        v-for="tab in [
          { id: 'portfolio', label: '내 포트폴리오', icon: '💰' },
          { id: 'watchlist', label: '관심 종목', icon: '⭐' },
          { id: 'settings',  label: '설정', icon: '⚙️' },
        ]"
        :key="tab.id"
        class="flex-1 flex items-center justify-center gap-1.5 py-2.5 px-2 rounded-lg text-sm font-medium transition-all"
        :class="activeTab === tab.id
          ? (theme.isDark ? 'bg-[#0F1117] text-white shadow-sm' : 'bg-white text-gray-900 shadow-sm')
          : (theme.isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700')"
        @click="activeTab = tab.id"
      >
        <span>{{ tab.icon }}</span>
        <span class="hidden sm:inline">{{ tab.label }}</span>
      </button>
    </div>

    <!-- ── 포트폴리오 탭 ────────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'portfolio'">

      <!-- 요약 카드 -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        <div
          v-for="card in [
            { label: '총 매수금액', value: formatKRW(totalBuy) + '원', sub: '' },
            { label: '평가금액',   value: formatKRW(totalValue) + '원', sub: '' },
            { label: '손익',       value: (totalProfit >= 0 ? '+' : '') + formatKRW(totalProfit) + '원',
              color: totalProfit >= 0 ? 'text-red-500' : 'text-blue-500' },
            { label: '수익률',     value: (totalProfitPct >= 0 ? '+' : '') + totalProfitPct.toFixed(2) + '%',
              color: totalProfitPct >= 0 ? 'text-red-500' : 'text-blue-500' },
          ]"
          :key="card.label"
          class="rounded-xl p-3.5"
          :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
        >
          <p class="text-xs mb-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">{{ card.label }}</p>
          <p class="text-base font-bold" :class="card.color">{{ card.value }}</p>
        </div>
      </div>

      <!-- 추가 버튼 -->
      <div class="flex items-center justify-between mb-3">
        <h2 class="font-semibold text-sm">보유 종목 ({{ holdings.length }})</h2>
        <button
          class="text-sm px-3 py-1.5 rounded-lg transition-colors"
          :class="theme.isDark ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-gray-900 text-white hover:bg-gray-700'"
          @click="showAddForm = !showAddForm"
        >
          {{ showAddForm ? '취소' : '+ 종목 추가' }}
        </button>
      </div>

      <!-- 추가 폼 -->
      <div
        v-if="showAddForm"
        class="rounded-xl p-4 mb-4 border"
        :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-gray-50 border-gray-200'"
      >
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
          <div>
            <label class="text-xs mb-1 block" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">종목코드 *</label>
            <input v-model="addForm.ticker" placeholder="005930" class="w-full rounded-lg px-3 py-2 text-sm border outline-none" :class="theme.isDark ? 'bg-[#0F1117] border-[#2A2D3A] text-white' : 'bg-white border-gray-200'" />
          </div>
          <div>
            <label class="text-xs mb-1 block" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">종목명</label>
            <input v-model="addForm.name" placeholder="삼성전자" class="w-full rounded-lg px-3 py-2 text-sm border outline-none" :class="theme.isDark ? 'bg-[#0F1117] border-[#2A2D3A] text-white' : 'bg-white border-gray-200'" />
          </div>
          <div>
            <label class="text-xs mb-1 block" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">매수가 (원) *</label>
            <input v-model="addForm.buy_price" type="number" placeholder="70000" class="w-full rounded-lg px-3 py-2 text-sm border outline-none" :class="theme.isDark ? 'bg-[#0F1117] border-[#2A2D3A] text-white' : 'bg-white border-gray-200'" />
          </div>
          <div>
            <label class="text-xs mb-1 block" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">수량 *</label>
            <input v-model="addForm.qty" type="number" placeholder="10" class="w-full rounded-lg px-3 py-2 text-sm border outline-none" :class="theme.isDark ? 'bg-[#0F1117] border-[#2A2D3A] text-white' : 'bg-white border-gray-200'" />
          </div>
        </div>
        <p v-if="addError" class="text-red-500 text-xs mb-2">{{ addError }}</p>
        <button
          class="w-full py-2.5 rounded-lg text-sm font-medium transition-colors"
          :class="theme.isDark ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-gray-900 text-white hover:bg-gray-700'"
          @click="addHolding"
        >
          추가하기
        </button>
      </div>

      <!-- 빈 상태 -->
      <div
        v-if="!holdings.length"
        class="text-center py-14 rounded-2xl"
        :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-gray-50'"
      >
        <p class="text-3xl mb-3">📂</p>
        <p class="text-sm font-medium mb-1">보유 종목이 없습니다</p>
        <p class="text-xs" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">+ 종목 추가 버튼으로 추가하세요</p>
      </div>

      <!-- 보유 종목 리스트 -->
      <div
        v-else
        class="rounded-2xl overflow-hidden"
        :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-sm min-w-[520px]">
            <thead>
              <tr :class="theme.isDark ? 'bg-[#0F1117]' : 'bg-gray-50'">
                <th class="text-left px-4 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">종목</th>
                <th class="text-right px-4 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">매수가</th>
                <th class="text-right px-4 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">현재가</th>
                <th class="text-right px-4 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">수량</th>
                <th class="text-right px-4 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">수익률</th>
                <th class="text-right px-4 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">평가손익</th>
                <th class="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(h, idx) in holdings"
                :key="idx"
                class="border-t cursor-pointer transition-colors"
                :class="[
                  theme.isDark ? 'border-[#2A2D3A] hover:bg-white/5' : 'border-gray-50 hover:bg-gray-50'
                ]"
                @click="router.push('/stocks/' + h.ticker)"
              >
                <td class="px-4 py-3">
                  <p class="font-medium text-sm">{{ h.name }}</p>
                  <p class="text-xs" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">{{ h.ticker }}</p>
                </td>
                <td class="px-4 py-3 text-right text-sm" :class="theme.isDark ? 'text-gray-400' : 'text-gray-600'">
                  {{ h.buy_price.toLocaleString() }}
                </td>
                <td class="px-4 py-3 text-right text-sm font-medium">
                  <span v-if="loadingPrices" class="text-xs text-gray-400">로딩...</span>
                  <span v-else>{{ (priceMap[h.ticker] || h.buy_price).toLocaleString() }}</span>
                </td>
                <td class="px-4 py-3 text-right text-sm" :class="theme.isDark ? 'text-gray-400' : 'text-gray-600'">
                  {{ h.qty.toLocaleString() }}주
                </td>
                <td class="px-4 py-3 text-right text-sm font-semibold" :class="profitPct(h) >= 0 ? 'text-red-500' : 'text-blue-500'">
                  {{ profitPct(h) >= 0 ? '+' : '' }}{{ profitPct(h).toFixed(2) }}%
                </td>
                <td class="px-4 py-3 text-right text-sm font-semibold" :class="profit(h) >= 0 ? 'text-red-500' : 'text-blue-500'">
                  {{ profit(h) >= 0 ? '+' : '' }}{{ formatKRW(profit(h)) }}원
                </td>
                <td class="px-4 py-3 text-right" @click.stop>
                  <button
                    class="text-xs transition-colors"
                    :class="theme.isDark ? 'text-gray-600 hover:text-red-400' : 'text-gray-400 hover:text-red-500'"
                    @click="removeHolding(idx)"
                  >삭제</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <!-- ── 관심 종목 탭 ────────────────────────────────────────────────────── -->
    <div v-else-if="activeTab === 'watchlist'">
      <div
        class="text-center py-14 rounded-2xl"
        :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-gray-50'"
      >
        <p class="text-3xl mb-3">⭐</p>
        <p class="text-sm font-medium mb-1">관심 종목</p>
        <p class="text-xs" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
          종목 상세 페이지에서 관심 종목을 추가하세요
        </p>
      </div>
    </div>

    <!-- ── 설정 탭 ────────────────────────────────────────────────────────── -->
    <div v-else-if="activeTab === 'settings'">
      <div
        class="rounded-2xl overflow-hidden"
        :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
      >
        <div class="p-5 border-b" :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-100'">
          <h2 class="font-semibold text-sm mb-3">테마</h2>
          <div class="flex items-center justify-between">
            <span class="text-sm">다크 모드</span>
            <button
              class="relative w-11 h-6 rounded-full transition-colors"
              :class="theme.isDark ? 'bg-indigo-500' : 'bg-gray-300'"
              @click="theme.toggleDark()"
            >
              <div
                class="absolute top-1 w-4 h-4 rounded-full bg-white transition-transform"
                :class="theme.isDark ? 'translate-x-6' : 'translate-x-1'"
              />
            </button>
          </div>
        </div>
        <div class="p-5">
          <h2 class="font-semibold text-sm mb-3">계정</h2>
          <button
            class="text-sm text-red-500 hover:text-red-400 transition-colors"
            @click="auth.logout(); router.push('/login')"
          >
            로그아웃
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
