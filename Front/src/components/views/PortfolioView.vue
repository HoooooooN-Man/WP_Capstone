<template>
  <div class="w-full h-full overflow-hidden relative select-none"
       style="background: #ede4d0; color: #2c1f0e;">

    <!-- 스크롤 메인 컨텐츠 -->
    <div class="absolute inset-0 overflow-y-auto" style="scrollbar-width:thin;padding-bottom:12px">
      <transition name="page-switch" mode="out-in">

        <!-- ── [0] 오버뷰 ── -->
        <div v-if="currentIndex === 0" key="overview" class="px-4 py-4 flex flex-col gap-4">

          <!-- ① 포트폴리오 제목 (더블클릭 → 편집) -->
          <div class="flex items-center gap-2">
            <div v-if="!editingName"
                 class="flex items-center gap-2 cursor-pointer group"
                 @dblclick="startNameEdit">
              <h1 class="text-[18px] font-black leading-none" style="color:#2c1f0e">{{ portfolioName }}</h1>
              <LucidePencil class="w-3 h-3 transition-colors" style="color:rgba(44,31,14,0.3)" />
            </div>
            <input v-else
                   ref="nameInput"
                   v-model="portfolioNameInput"
                   class="text-[18px] font-black bg-transparent border-b-2 border-[#c9a227] focus:outline-none leading-none"
                   style="color:#2c1f0e;min-width:160px;max-width:280px"
                   @keyup.enter="confirmNameEdit"
                   @keyup.escape="editingName = false"
                   @blur="confirmNameEdit"
            />
          </div>

          <!-- ② 상단 3단 카드 -->
          <div class="grid grid-cols-3 gap-2.5">

            <!-- 총자산 -->
            <div class="rounded-2xl p-3.5 flex flex-col gap-1"
                 style="background:rgba(201,162,39,0.10);border:1px solid rgba(201,162,39,0.35)">
              <p class="text-[9px] font-black uppercase tracking-widest" style="color:rgba(44,31,14,0.55)">총 자산</p>
              <p class="text-[17px] font-black leading-tight" style="color:#2c1f0e">
                {{ formatKRW(totalAssets) }}
              </p>
              <div class="flex items-center gap-1 mt-0.5">
                <span class="text-[11px] font-bold leading-none"
                      :class="profitAmount >= 0 ? 'text-green-400' : 'text-red-400'">
                  {{ profitAmount >= 0 ? '+' : '' }}{{ formatKRW(profitAmount) }}
                </span>
                <span class="text-[10px] leading-none"
                      :class="totalReturn >= 0 ? 'text-green-400/70' : 'text-red-400/70'">
                  ({{ totalReturn >= 0 ? '+' : '' }}{{ totalReturn.toFixed(1) }}%)
                </span>
              </div>
            </div>

            <!-- 투자 금액 -->
            <div class="rounded-2xl p-3.5 flex flex-col gap-1"
                 style="background:rgba(0,0,0,0.05);border:1px solid rgba(0,0,0,0.12)">
              <p class="text-[9px] font-black uppercase tracking-widest" style="color:rgba(44,31,14,0.55)">투자 금액</p>
              <div v-if="!editingAmount"
                   class="flex items-center gap-1.5 cursor-pointer group"
                   @click="startEdit">
                <p class="text-[17px] font-black leading-tight" style="color:#2c1f0e">{{ formatKRW(investmentAmount) }}</p>
                <LucidePencil class="w-3 h-3 text-white/20 group-hover:text-white/50 transition-colors" />
              </div>
              <div v-else class="flex flex-col gap-1.5">
                <input
                  ref="amountInput"
                  type="number"
                  v-model.number="investmentAmountInput"
                  class="w-full rounded-lg px-2 py-1.5 text-white text-[13px] font-bold focus:outline-none"
                  style="background:rgba(255,255,255,0.12);border:1px solid rgba(201,162,39,0.4)"
                  @keyup.enter="confirmAmount"
                  @blur="confirmAmount"
                />
              </div>
              <p class="text-[9px]" style="color:rgba(44,31,14,0.4)">탭하여 수정</p>
            </div>

            <!-- 종목 구성 파이 차트 -->
            <div class="rounded-2xl p-3.5 flex flex-col items-center gap-1.5"
                 style="background:rgba(0,0,0,0.05);border:1px solid rgba(0,0,0,0.12)">
              <p class="text-[9px] font-black uppercase tracking-widest self-start" style="color:rgba(44,31,14,0.55)">종목 구성</p>
              <svg v-if="pieSegments.length" viewBox="0 0 80 80" class="w-14 h-14 -mt-0.5">
                <path v-for="(seg, i) in pieSegments" :key="i" :d="seg.d" :fill="seg.color" />
                <circle cx="40" cy="40" r="16" fill="rgba(237,228,208,0.95)" />
                <text x="40" y="44" text-anchor="middle" fill="rgba(44,31,14,0.7)" font-size="9" font-weight="bold">
                  {{ activeStocks.length }}종
                </text>
              </svg>
              <div v-else class="w-14 h-14 rounded-full flex items-center justify-center"
                   style="background:rgba(255,255,255,0.06)">
                <span class="text-[10px]" style="color:rgba(44,31,14,0.4)">없음</span>
              </div>
            </div>
          </div>

          <!-- ② 포트폴리오 추이 라인 차트 -->
          <div class="rounded-2xl px-4 py-3.5"
               style="background:rgba(0,0,0,0.04);border:1px solid rgba(0,0,0,0.10)">
            <div class="flex items-center justify-between mb-2.5">
              <p class="text-[10px] font-black uppercase tracking-widest" style="color:rgba(44,31,14,0.5)">포트폴리오 추이</p>
              <span class="text-[10px]" style="color:rgba(44,31,14,0.4)">수익률 변화</span>
            </div>
            <svg viewBox="0 0 380 90" class="w-full" style="height:72px">
              <!-- 그리드 -->
              <line x1="0" y1="45" x2="380" y2="45" stroke="rgba(0,0,0,0.08)" stroke-width="1"/>
              <line x1="0" y1="20" x2="380" y2="20" stroke="rgba(0,0,0,0.08)" stroke-width="1"/>
              <line x1="0" y1="70" x2="380" y2="70" stroke="rgba(0,0,0,0.08)" stroke-width="1"/>
              <!-- 면적 채우기 -->
              <polygon :points="trendAreaPoints" fill="url(#trendGrad)" />
              <!-- 라인 -->
              <polyline :points="trendLinePoints" fill="none" stroke="#c9a227" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round"/>
              <defs>
                <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#c9a227" stop-opacity="0.25"/>
                  <stop offset="100%" stop-color="#c9a227" stop-opacity="0"/>
                </linearGradient>
              </defs>
            </svg>
            <!-- x축 라벨 -->
            <div class="flex justify-between mt-1">
              <span v-for="label in trendLabels" :key="label"
                    class="text-[8px]" style="color:rgba(44,31,14,0.35)">{{ label }}</span>
            </div>
          </div>

          <!-- ③ 보유 종목 리스트 -->
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest mb-2.5" style="color:rgba(44,31,14,0.5)">보유 종목</p>
            <div v-if="!activeStocks.length"
                 class="rounded-xl py-8 text-center text-[13px]"
                 style="color:rgba(44,31,14,0.4);background:rgba(0,0,0,0.03);border:1px solid rgba(0,0,0,0.08)">
              팬 메뉴에서 종목을 추가해주세요
            </div>
            <div v-else class="flex flex-col gap-2">
              <div v-for="(stock, i) in activeStocks" :key="stock.ticker"
                   class="flex items-center gap-3 rounded-xl px-3.5 py-3 cursor-pointer transition-all hover:brightness-110"
                   :style="`background:linear-gradient(135deg,${stock.color}14 0%,rgba(255,255,255,0.04) 100%);border:1px solid ${stock.color}30`"
                   @click="goToStock(i)">
                <!-- 색상 dot -->
                <div class="w-2.5 h-2.5 rounded-full flex-shrink-0" :style="{ background: stock.color }"></div>
                <!-- 종목 정보 -->
                <div class="flex-1 min-w-0">
                  <p class="text-[13px] font-black leading-tight truncate">{{ stock.company }}</p>
                  <p class="text-[10px] font-mono text-white/30 leading-none mt-0.5">{{ stock.ticker }}</p>
                </div>
                <!-- 비중 + 수익률 -->
                <div class="text-right flex-shrink-0">
                  <p class="text-[12px] font-bold leading-tight"
                     :class="stock.change >= 0 ? 'text-green-400' : 'text-red-400'">
                    {{ stock.change >= 0 ? '+' : '' }}{{ stock.change }}%
                  </p>
                  <p class="text-[10px] text-white/30 leading-none mt-0.5">
                    비중 {{ activeStocks.length ? (100 / activeStocks.length).toFixed(1) : 0 }}%
                  </p>
                </div>
                <LucideChevronRight class="w-4 h-4 text-white/20 flex-shrink-0" />
              </div>
            </div>
          </div>

          <!-- AI 추천 포트폴리오 (접기 가능) -->
          <div>
            <button class="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest mb-2 transition-colors" style="color:rgba(44,31,14,0.45)"
                    @click="aiOpen = !aiOpen">
              <span>AI 추천 포트폴리오</span>
              <span>{{ aiOpen ? '▲' : '▼' }}</span>
            </button>
            <template v-if="aiOpen">
              <div class="flex gap-2 mb-3">
                <button v-for="t in [{ value:'growth', label:'성장형' },{ value:'stable', label:'안정형' }]" :key="t.value"
                        class="px-3 py-1.5 rounded-lg text-[12px] font-bold transition-colors"
                        :class="store.activeType === t.value
                          ? 'bg-white/15 text-white border border-white/25'
                          : 'border border-white/12 text-white/40'"
                        @click="onTypeChange(t.value)">
                  {{ t.label }}
                </button>
              </div>
              <div v-if="store.loading" class="grid grid-cols-2 gap-2">
                <div v-for="i in 6" :key="i" class="h-20 rounded-xl animate-pulse"
                     style="background:rgba(255,255,255,0.05)"></div>
              </div>
              <div v-else class="grid grid-cols-2 gap-2">
                <div v-for="item in store.currentItems" :key="item.ticker"
                     class="rounded-xl p-3 cursor-pointer border transition-colors"
                     style="background:rgba(255,255,255,0.04);border-color:rgba(255,255,255,0.08)"
                     @click="emit('view-company', item.ticker)">
                  <div class="flex items-center justify-between mb-1.5">
                    <span class="text-[10px] text-white/40">{{ item.rank }}위</span>
                    <span class="px-1.5 py-0.5 rounded text-[10px] font-bold"
                          :style="tierStyle(item.tier)">{{ item.tier }}</span>
                  </div>
                  <p class="text-[12px] font-black truncate mb-0.5">{{ item.name }}</p>
                  <div class="flex items-center justify-between">
                    <p class="text-[10px] font-mono text-white/30">{{ item.ticker }}</p>
                    <span class="text-[11px] font-bold text-[#c9a227]">{{ Math.round(item.score) }}</span>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
        <!-- /오버뷰 -->

        <!-- ── [1+] 보유 종목 상세 ── -->
        <div v-else key="stock-detail" class="flex flex-col h-full">

          <!-- 헤더 -->
          <div class="flex items-center gap-3 px-5 py-4 flex-shrink-0"
               style="border-bottom:1px solid rgba(255,255,255,0.1)">
            <button @click="$emit('update:currentIndex', 0)"
                    class="w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/10 transition-colors"
                    style="background:rgba(255,255,255,0.06)">
              <LucideChevronLeft class="w-4 h-4 text-white/60" />
            </button>
            <div v-if="activeStock" class="flex-1 min-w-0">
              <p class="text-[10px] font-mono text-white/30">{{ activeStock.ticker }} · {{ activeStock.sector }}</p>
              <p class="text-[15px] font-black truncate">{{ activeStock.company }}</p>
            </div>
            <button v-if="activeStock"
                    class="px-3 py-1.5 rounded-xl text-[11px] font-bold text-white/50 hover:text-white/80 flex-shrink-0"
                    style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12)"
                    @click="emit('view-company', activeStock.ticker)">
              상세 →
            </button>
          </div>

          <!-- 바디 (스크롤) -->
          <div class="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">

            <!-- 현재 수익률 -->
            <div v-if="activeStock" class="flex items-center gap-3 rounded-xl p-3.5"
                 :style="`background:linear-gradient(135deg,${activeStock.color}18 0%,rgba(255,255,255,0.04) 100%);border:1px solid ${activeStock.color}30`">
              <div class="w-2.5 h-2.5 rounded-full flex-shrink-0" :style="{ background: activeStock.color }"></div>
              <div class="flex-1">
                <p class="text-[13px] font-black">현재 수익률</p>
                <p class="text-[10px] text-white/35 mt-0.5">₩{{ activeStock.currentPrice?.toLocaleString() }}</p>
              </div>
              <div class="text-right">
                <p class="text-[20px] font-black leading-none"
                   :class="activeStock.change >= 0 ? 'text-green-400' : 'text-red-400'">
                  {{ activeStock.change >= 0 ? '+' : '' }}{{ activeStock.change }}%
                </p>
                <p class="text-[10px] text-white/30 mt-0.5">Quant {{ activeStock.quantScore ?? '—' }}</p>
              </div>
            </div>

            <!-- 주가 차트 썸네일 (클릭 → 전체 차트 모달) -->
            <div class="rounded-xl overflow-hidden cursor-pointer relative group"
                 style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08)"
                 @click="chartModalOpen = true">
              <!-- 썸네일 헤더 -->
              <div class="flex items-center justify-between px-4 pt-3.5 pb-2">
                <p class="text-[10px] font-black uppercase tracking-widest text-white/35">주가 차트</p>
                <div class="flex items-center gap-2">
                  <div class="flex items-center gap-2 text-[9px] text-white/30">
                    <span class="flex items-center gap-1"><span class="inline-block w-4 h-px bg-white/40"></span>실제</span>
                    <span class="flex items-center gap-1"><span class="inline-block w-4 h-px" style="border-top:1px dashed #c9a227"></span>예측</span>
                  </div>
                  <LucideMaximize2 class="w-3.5 h-3.5 text-white/25 group-hover:text-white/60 transition-colors" />
                </div>
              </div>
              <!-- 썸네일 SVG -->
              <div class="px-3 pb-3">
                <svg v-if="activeStock" viewBox="0 0 380 90" class="w-full" style="height:78px">
                  <defs>
                    <linearGradient :id="`thumb-${activeStock.ticker}`" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" :stop-color="activeStock.color" stop-opacity="0.35"/>
                      <stop offset="100%" :stop-color="activeStock.color" stop-opacity="0.02"/>
                    </linearGradient>
                  </defs>
                  <polygon :points="thumbAreaPoints(activeStock.ticker)" :fill="`url(#thumb-${activeStock.ticker})`"/>
                  <polyline :points="thumbLinePoints(activeStock.ticker)"
                            fill="none" :stroke="activeStock.color" stroke-width="1.8"
                            stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>
                  <polyline :points="thumbPredPoints(activeStock.ticker)"
                            fill="none" stroke="#c9a227" stroke-width="1.5" stroke-dasharray="4,3"
                            stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <div class="flex justify-between mt-0.5">
                  <span v-for="l in ['3M','2M','1M','현재','예측']" :key="l" class="text-[8px] text-white/18">{{ l }}</span>
                </div>
              </div>
              <!-- 호버 오버레이 -->
              <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none rounded-xl"
                   style="background:rgba(0,0,0,0.35)">
                <span class="text-white/80 text-[12px] font-bold flex items-center gap-1.5">
                  <LucideMaximize2 class="w-4 h-4"/>
                  상세 차트 보기
                </span>
              </div>
            </div>

            <!-- 종목 설정 -->
            <div class="rounded-xl overflow-hidden"
                 style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08)">
              <p class="text-[10px] font-black uppercase tracking-widest text-white/35 px-4 pt-3.5 pb-2">종목 설정</p>
              <button v-if="activeStock"
                      class="w-full flex items-center justify-between px-4 py-3 hover:bg-white/6 transition-colors border-t"
                      style="border-color:rgba(255,255,255,0.07)"
                      @click="emit('view-company', activeStock.ticker)">
                <span class="text-[13px] text-white/65">상세 정보 보기</span>
                <LucideChevronRight class="w-4 h-4 text-white/25" />
              </button>
              <div class="px-4 py-3 border-t text-[11px] text-white/25 text-center"
                   style="border-color:rgba(255,255,255,0.07)">
                하단 팬 카드를 <strong class="text-white/40">길게 누른 후</strong> 드래그 →
                <span class="text-red-300/60">삭제</span> / <span class="text-emerald-300/60">교체</span>
              </div>
            </div>

          </div>
        </div>

      </transition>
    </div>


    <!-- ── 주가 상세 차트 모달 ── -->
    <transition name="chart-modal">
      <div v-if="chartModalOpen && activeStock"
           class="absolute inset-0 z-50 flex flex-col rounded-[2rem] overflow-hidden"
           style="background:#060e1c">

        <!-- 모달 헤더 -->
        <div class="flex items-center gap-3 px-5 py-4 flex-shrink-0"
             style="border-bottom:1px solid rgba(255,255,255,0.1)">
          <button @click="chartModalOpen = false"
                  class="w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/10 transition-colors"
                  style="background:rgba(255,255,255,0.07)">
            <LucideX class="w-4 h-4 text-white/60"/>
          </button>
          <div class="flex-1 min-w-0">
            <p class="text-[10px] font-mono text-white/30">{{ activeStock.ticker }} · {{ activeStock.sector }}</p>
            <p class="text-[15px] font-black truncate">{{ activeStock.company }}</p>
          </div>
          <div class="text-right flex-shrink-0">
            <p class="text-[18px] font-black leading-none"
               :class="activeStock.change >= 0 ? 'text-green-400' : 'text-red-400'">
              {{ activeStock.change >= 0 ? '+' : '' }}{{ activeStock.change }}%
            </p>
            <p class="text-[11px] text-white/35 mt-0.5">₩{{ activeStock.currentPrice?.toLocaleString() }}</p>
          </div>
        </div>

        <!-- 기간 탭 -->
        <div class="flex gap-1 px-5 pt-3 pb-2 flex-shrink-0">
          <button v-for="p in ['1M','3M','6M','1Y']" :key="p"
                  @click="chartPeriod = p"
                  class="px-2.5 py-1 rounded text-[11px] font-bold transition-all"
                  :class="chartPeriod === p ? 'bg-white/15 text-white' : 'text-white/30 hover:text-white/55'">
            {{ p }}
          </button>
          <div class="ml-auto flex items-center gap-3 text-[9px] text-white/35">
            <span class="flex items-center gap-1.5"><span class="inline-block w-6 h-px" :style="`background:${activeStock.color}`"></span>실제</span>
            <span class="flex items-center gap-1.5"><span class="inline-block w-6 h-px" style="border-top:1.5px dashed #c9a227"></span>예측</span>
          </div>
        </div>

        <!-- 최고가 -->
        <div class="px-6 flex-shrink-0">
          <span class="text-[9px] font-mono text-white/25">₩{{ modalPriceRange.max.toLocaleString() }}</span>
        </div>

        <!-- 전체 차트 SVG (CompanyView 스타일) -->
        <div class="flex-1 px-4 min-h-0">
          <svg class="w-full h-full" viewBox="0 0 380 240" preserveAspectRatio="none">
            <defs>
              <linearGradient :id="`modal-grad-${activeStock.ticker}`" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   :stop-color="activeStock.color" stop-opacity="0.45"/>
                <stop offset="100%" :stop-color="activeStock.color" stop-opacity="0.02"/>
              </linearGradient>
            </defs>
            <!-- 그리드 -->
            <line v-for="y in [60,120,180]" :key="y" x1="0" :y1="y" x2="380" :y2="y"
                  stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            <!-- 영역 채우기 -->
            <path :d="modalAreaPath(activeStock.ticker)" :fill="`url(#modal-grad-${activeStock.ticker})`"/>
            <!-- 실제 주가 라인 -->
            <path :d="modalLinePath(activeStock.ticker, false)"
                  fill="none" :stroke="activeStock.color" stroke-width="2"
                  stroke-linejoin="round" opacity="0.92"/>
            <!-- 예측선 -->
            <path :d="modalLinePath(activeStock.ticker, true)"
                  fill="none" stroke="#c9a227" stroke-width="2" stroke-dasharray="6,4"
                  stroke-linejoin="round"/>
          </svg>
        </div>

        <!-- 최저가 + x축 -->
        <div class="px-6 pb-2 flex-shrink-0 flex justify-between items-end">
          <span class="text-[9px] font-mono text-white/25">₩{{ modalPriceRange.min.toLocaleString() }}</span>
        </div>
        <div class="px-5 pb-4 flex justify-between flex-shrink-0">
          <span v-for="l in modalXLabels" :key="l" class="text-[9px] text-white/20">{{ l }}</span>
        </div>

      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { LucideChevronLeft, LucideChevronRight, LucidePencil, LucideMaximize2, LucideX } from 'lucide-vue-next'
import { usePortfolioStore } from '@/stores/portfolio.js'
import BacktestMonthlyChart from '@/components/portfolio/BacktestMonthlyChart.vue'

const props = defineProps({
  portfolioGroups: { type: Array,  required: true },
  activeGroupId:   { type: Number, required: true },
  currentIndex:    { type: Number, default: 0 },
})
const emit = defineEmits(['update:currentIndex', 'view-company'])

const store = usePortfolioStore()
const aiOpen = ref(false)

async function onTypeChange(type) {
  store.setType(type)
  try { await store.fetchPortfolio(type) } catch {}
}

onMounted(() => {
  nextTick(() => setTimeout(() => {
    store.initVersions().catch(() => {})
    store.fetchPortfolio('growth').catch(() => {})
    store.fetchBacktest().catch(() => {})
  }, 320))
})

// ── 개인 포트폴리오 데이터 ──
const activeGroup  = computed(() => props.portfolioGroups.find(g => g.id === props.activeGroupId))
const activeStocks = computed(() => activeGroup.value?.stocks || [])
const activeStock  = computed(() => props.currentIndex === 0 ? null : activeStocks.value[props.currentIndex - 1] ?? null)

// ── 포트폴리오 제목 ──
const portfolioName      = ref('내 포트폴리오 1')
const portfolioNameInput = ref('내 포트폴리오 1')
const editingName        = ref(false)
const nameInput          = ref(null)

function startNameEdit() {
  portfolioNameInput.value = portfolioName.value
  editingName.value = true
  nextTick(() => {
    nameInput.value?.focus()
    nameInput.value?.select()
  })
}
function confirmNameEdit() {
  if (portfolioNameInput.value.trim()) portfolioName.value = portfolioNameInput.value.trim()
  editingName.value = false
}

// ── 투자 금액 ──
const investmentAmount      = ref(10_000_000)
const investmentAmountInput = ref(10_000_000)
const editingAmount         = ref(false)
const amountInput           = ref(null)

function startEdit() {
  investmentAmountInput.value = investmentAmount.value
  editingAmount.value = true
  nextTick(() => amountInput.value?.focus())
}
function confirmAmount() {
  if (investmentAmountInput.value > 0) investmentAmount.value = investmentAmountInput.value
  editingAmount.value = false
}

// ── 수익 계산 ──
const totalReturn = computed(() => {
  if (!activeStocks.value.length) return 0
  return activeStocks.value.reduce((s, st) => s + (st.change ?? 0), 0) / activeStocks.value.length
})
const profitAmount = computed(() => Math.round(investmentAmount.value * totalReturn.value / 100))
const totalAssets  = computed(() => investmentAmount.value + profitAmount.value)

// ── 금액 포맷 ──
function formatKRW(n) {
  const abs = Math.abs(n)
  if (abs >= 100_000_000) return (n < 0 ? '-' : '') + (abs / 100_000_000).toFixed(1) + '억'
  if (abs >= 10_000)      return (n < 0 ? '-' : '') + Math.round(abs / 10_000) + '만'
  return (n < 0 ? '-' : '') + abs.toLocaleString()
}

// ── 파이 차트 ──
const pieSegments = computed(() => {
  const stocks = activeStocks.value
  if (!stocks.length) return []
  const n = stocks.length
  const slice = (2 * Math.PI) / n
  const cx = 40, cy = 40, r = 37
  return stocks.map((s, i) => {
    const a1 = i * slice - Math.PI / 2
    const a2 = a1 + slice * 0.90
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1)
    const x2 = cx + r * Math.cos(a2), y2 = cy + r * Math.sin(a2)
    const large = slice > Math.PI ? 1 : 0
    return {
      d: `M${cx},${cy} L${x1.toFixed(1)},${y1.toFixed(1)} A${r},${r} 0 ${large},1 ${x2.toFixed(1)},${y2.toFixed(1)} Z`,
      color: s.color ?? '#888',
    }
  })
})

// ── 트렌드 라인 차트 ──
const MOCK_TREND = [0, 2, -1, 4, 3, 7, 5, 9, 6, 12, 10, 15, 11, 18, 14, 20, 16, 22, 19, 25, 22, 28]

const trendData = computed(() => {
  const raw = store.backtestMonthly
  if (raw?.length) return raw.map(d => d.portfolio_return ?? d.return ?? 0)
  return MOCK_TREND
})

const trendLinePoints = computed(() => {
  const d = trendData.value
  const min = Math.min(...d), max = Math.max(...d)
  const range = (max - min) || 1
  return d.map((v, i) => {
    const x = (i / (d.length - 1)) * 378
    const y = 80 - ((v - min) / range) * 65
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const trendAreaPoints = computed(() => {
  const d = trendData.value
  const min = Math.min(...d), max = Math.max(...d)
  const range = (max - min) || 1
  const pts = d.map((v, i) => {
    const x = (i / (d.length - 1)) * 378
    const y = 80 - ((v - min) / range) * 65
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `${pts.join(' ')} 378,85 0,85`
})

const trendLabels = computed(() => {
  const d = trendData.value
  if (!d.length) return []
  const step = Math.ceil(d.length / 5)
  return Array.from({ length: 5 }, (_, i) => {
    const idx = Math.min(i * step, d.length - 1)
    const raw = store.backtestMonthly
    if (raw?.length) return raw[idx]?.date?.slice(0, 7) ?? `M${idx + 1}`
    return `M${idx + 1}`
  })
})

// ── 보유 종목 클릭 → 팬카드로 이동 ──
function goToStock(i) {
  emit('update:currentIndex', i + 1)
}

// ── 차트 모달 ──
const chartModalOpen = ref(false)
const chartPeriod    = ref('3M')

// 모의 가격 포인트 생성 (ticker 기반 결정론적)
function mockPricePoints(ticker, count, startX, width, height, isPred) {
  const seed = ticker.split('').reduce((s, c) => s + c.charCodeAt(0), 0)
  const base = height * 0.55
  return Array.from({ length: count }, (_, i) => {
    const t = i / (count - 1)
    const wave = Math.sin(i * 1.4 + seed * 0.05) * (height * 0.2)
            + Math.cos(i * 0.8 + seed * 0.03) * (height * 0.1)
    const trend = isPred ? -t * (height * 0.08) : t * (height * 0.04)
    const y = base + wave + trend
    return { x: startX + t * width, y: Math.max(8, Math.min(height - 8, y)) }
  })
}

// 썸네일용
function thumbLinePoints(ticker) {
  const pts = mockPricePoints(ticker, 16, 0, 278, 85, false)
  return pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
}
function thumbAreaPoints(ticker) {
  const pts = mockPricePoints(ticker, 16, 0, 278, 85, false)
  const line = pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  return `${line} ${pts[pts.length-1].x.toFixed(1)},88 0,88`
}
function thumbPredPoints(ticker) {
  const realEnd = mockPricePoints(ticker, 16, 0, 278, 85, false)
  const lastPt = realEnd[realEnd.length - 1]
  const pts = mockPricePoints(ticker, 7, lastPt.x, 100, 85, true)
  pts[0] = lastPt
  return pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
}

// 모달용 SVG path (smooth bezier)
function smoothPath(pts) {
  if (!pts.length) return ''
  let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`
  for (let i = 1; i < pts.length; i++) {
    const cp1x = (pts[i-1].x + pts[i].x) / 2
    const cp1y = pts[i-1].y
    const cp2x = (pts[i-1].x + pts[i].x) / 2
    const cp2y = pts[i].y
    d += ` C${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${pts[i].x.toFixed(1)},${pts[i].y.toFixed(1)}`
  }
  return d
}

function modalLinePath(ticker, isPred) {
  const realPts = mockPricePoints(ticker, 22, 0, 300, 230, false)
  if (!isPred) return smoothPath(realPts)
  const last = realPts[realPts.length - 1]
  const predPts = mockPricePoints(ticker, 9, last.x, 78, 230, true)
  predPts[0] = last
  return smoothPath(predPts)
}
function modalAreaPath(ticker) {
  const pts = mockPricePoints(ticker, 22, 0, 300, 230, false)
  const line = smoothPath(pts)
  return `${line} L${pts[pts.length-1].x.toFixed(1)},235 L0,235 Z`
}

const modalPriceRange = computed(() => {
  if (!activeStock.value) return { max: 100000, min: 80000 }
  const base = activeStock.value.currentPrice ?? 50000
  return { max: Math.round(base * 1.15), min: Math.round(base * 0.85) }
})

const modalXLabels = computed(() => {
  const labels = {
    '1M': ['4주전','3주전','2주전','1주전','현재','예측'],
    '3M': ['3개월전','2개월전','1개월전','현재','예측',''],
    '6M': ['6개월전','4개월전','2개월전','현재','예측',''],
    '1Y': ['12개월전','8개월전','4개월전','현재','예측',''],
  }
  return labels[chartPeriod.value] ?? labels['3M']
})


// ── 색상 헬퍼 ──
const tierStyle = (t) => ({
  A: 'background:rgba(29,158,117,0.25);color:#34d399',
  B: 'background:rgba(55,138,221,0.25);color:#60a5fa',
  C: 'background:rgba(239,159,39,0.25);color:#fbbf24',
  D: 'background:rgba(226,75,74,0.25);color:#f87171',
}[t] ?? 'background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.5)')
</script>

<style scoped>
.page-switch-enter-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.page-switch-leave-active { transition: opacity 0.15s ease; }
.page-switch-enter-from   { opacity: 0; transform: translateY(10px); }
.page-switch-leave-to     { opacity: 0; }

.chart-modal-enter-active { transition: transform 0.32s cubic-bezier(0.32,0,0.2,1), opacity 0.22s ease; }
.chart-modal-leave-active { transition: transform 0.22s ease, opacity 0.18s ease; }
.chart-modal-enter-from   { transform: translateY(100%); opacity: 0; }
.chart-modal-leave-to     { transform: translateY(100%); opacity: 0; }
</style>
