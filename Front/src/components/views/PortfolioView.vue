<template>
  <div class="w-full h-full overflow-hidden relative select-none text-white"
       style="background: linear-gradient(160deg, #1a2e4a 0%, #0e1d30 100%)">

    <!-- 스크롤 메인 컨텐츠 — 팬 스트립은 CardWallet 레벨에 있으므로 전체 높이 사용 -->
    <div class="absolute inset-0 overflow-y-auto" style="scrollbar-width:thin;padding-bottom:12px">
      <transition name="page-switch" mode="out-in">

        <!-- ── [0] 오버뷰: AI 추천 포트폴리오 (다크 테마) ── -->
        <div v-if="currentIndex === 0" key="overview"
             class="max-w-5xl mx-auto px-6 py-8 flex flex-col gap-8">

          <!-- Section 1: 포트폴리오 전략 -->
          <div class="flex flex-col gap-4">
            <h1 class="text-xl font-semibold text-white">포트폴리오</h1>

            <!-- Strategy Tabs -->
            <div class="flex items-center justify-between">
              <div class="flex gap-2">
                <button v-for="t in [{ value:'growth', label:'성장형' },{ value:'stable', label:'안정형' }]" :key="t.value"
                        class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                        :class="store.activeType === t.value
                          ? 'bg-white/15 text-white border border-white/25'
                          : 'border border-white/12 text-white/40 hover:bg-white/8'"
                        @click="onTypeChange(t.value)">
                  {{ t.label }}
                </button>
              </div>
              <div class="flex items-center gap-3">
                <select :value="store.selectedVersion"
                        class="rounded-lg px-2.5 py-1.5 text-sm text-white focus:outline-none"
                        style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15)"
                        @change="onVersionChange($event.target.value)">
                  <option value="latest" style="background:#1a2e4a">최신 버전</option>
                  <option v-for="v in store.versions" :key="v" :value="v" style="background:#1a2e4a">{{ v }}</option>
                </select>
                <span v-if="store.currentDate" class="text-sm text-white/40">기준일 {{ store.currentDate }}</span>
              </div>
            </div>

            <!-- Portfolio Card Grid -->
            <div v-if="portfolioError === 'not_ready'"
                 class="rounded-xl px-4 py-3 text-sm text-amber-400"
                 style="background:rgba(251,191,36,0.06);border:1px solid rgba(251,191,36,0.15)">
              <template v-if="store.activeType === 'stable'">
                현재 PBR 재무 데이터가 준비중입니다.<br>데이터 준비 완료 후 이용 가능합니다.
              </template>
              <template v-else>KOSPI 추천 데이터가 준비중입니다.</template>
            </div>
            <div v-else-if="portfolioError && portfolioError !== 'not_ready'"
                 class="text-center text-white/40 py-8 text-sm">
              데이터를 불러오지 못했습니다
            </div>
            <div v-else-if="store.loading" class="grid grid-cols-2 gap-3">
              <div v-for="i in 10" :key="i" class="h-28 rounded-xl animate-pulse"
                   style="background:rgba(255,255,255,0.05)"></div>
            </div>
            <div v-else class="grid grid-cols-2 gap-3">
              <div v-for="item in store.currentItems" :key="item.ticker"
                   class="rounded-xl p-4 cursor-pointer border transition-colors"
                   style="background:rgba(255,255,255,0.04);border-color:rgba(255,255,255,0.08)"
                   @click="emit('view-company', item.ticker)">
                <div class="flex items-center justify-between mb-2">
                  <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium text-white/60"
                        style="background:rgba(255,255,255,0.1)">{{ item.rank }}</span>
                  <span class="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-semibold"
                        :style="tierStyle(item.tier)">{{ item.tier }}</span>
                </div>
                <p class="text-sm font-medium text-white mb-0.5 truncate">{{ item.name }}</p>
                <p class="font-mono text-xs text-white/35 mb-2">{{ item.ticker }}</p>
                <div class="flex items-center justify-between">
                  <span class="text-xs text-white/30 rounded-full px-2 py-0.5"
                        style="background:rgba(255,255,255,0.07)">{{ item.sector }}</span>
                  <div class="flex items-center gap-1.5">
                    <div class="w-16 h-1.5 rounded overflow-hidden" style="background:rgba(255,255,255,0.1)">
                      <div class="h-full rounded"
                           :style="{ width: item.score + '%', backgroundColor: barColor(item.score) }"></div>
                    </div>
                    <span class="text-xs font-medium text-white/60">{{ Math.round(item.score) }}</span>
                  </div>
                </div>
                <div v-if="store.activeType === 'stable' && item.pbr != null"
                     class="flex items-center gap-1 mt-1.5">
                  <span class="text-xs text-white/30">PBR</span>
                  <span class="text-xs font-medium text-blue-300">{{ item.pbr.toFixed(2) }}</span>
                </div>
              </div>
            </div>

            <!-- Strategy Explanation -->
            <div v-if="store.activeType === 'growth'"
                 class="rounded-xl p-4" style="background:rgba(255,255,255,0.04)">
              <p class="text-sm font-semibold text-white mb-1">성장형 전략</p>
              <p class="text-sm text-white/50 leading-relaxed">
                ML 모델이 단기 상승 가능성이 높다고 판단한 KOSPI 상장 종목 Top 10입니다.<br>
                LightGBM · XGBoost · CatBoost 앙상블 점수를 기준으로 정렬했습니다.
              </p>
            </div>
            <div v-else class="flex flex-col gap-3">
              <div class="rounded-xl p-4" style="background:rgba(255,255,255,0.04)">
                <p class="text-sm font-semibold text-white mb-1">안정형 전략</p>
                <p class="text-sm text-white/50 leading-relaxed">
                  Tier A·B 종목 (ML점수 60점 이상) 중 최신 분기 PBR이 1.5 미만인 종목을 선별하여
                  하방 리스크를 제한한 가치투자형 전략입니다.
                </p>
              </div>
              <div class="overflow-auto rounded-xl border" style="border-color:rgba(255,255,255,0.1)">
                <table class="w-full text-sm">
                  <thead style="background:rgba(255,255,255,0.05)">
                    <tr>
                      <th class="text-left text-xs text-white/40 font-medium px-4 py-2.5">PBR 범위</th>
                      <th class="text-left text-xs text-white/40 font-medium px-4 py-2.5">해석</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr class="border-t" style="border-color:rgba(255,255,255,0.06)">
                      <td class="px-4 py-2 text-white/60">&lt; 1.0</td>
                      <td class="px-4 py-2 text-white/40">극도 저평가 또는 구조적 문제</td>
                    </tr>
                    <tr class="border-t" style="border-color:rgba(255,255,255,0.06);background:rgba(59,130,246,0.08)">
                      <td class="px-4 py-2 text-blue-300 font-medium">1.0 ~ 1.5</td>
                      <td class="px-4 py-2 text-blue-300 font-medium">안정적 저평가 · 현재 기준 ✓ 해당</td>
                    </tr>
                    <tr class="border-t" style="border-color:rgba(255,255,255,0.06)">
                      <td class="px-4 py-2 text-white/60">1.5 ~ 3.0</td>
                      <td class="px-4 py-2 text-white/40">적정 수준</td>
                    </tr>
                    <tr class="border-t" style="border-color:rgba(255,255,255,0.06)">
                      <td class="px-4 py-2 text-white/60">&gt; 3.0</td>
                      <td class="px-4 py-2 text-white/40">고평가 또는 성장 프리미엄</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <hr style="border-color:rgba(255,255,255,0.08)"/>

          <!-- Section 2: 백테스트 -->
          <div class="flex flex-col gap-4">
            <div class="flex items-center justify-between">
              <h2 class="text-base font-semibold text-white">백테스트 결과</h2>
              <button class="text-xs text-white/40 hover:text-white/70 transition-colors rounded-lg px-2.5 py-1.5 border"
                      style="border-color:rgba(255,255,255,0.12)"
                      @click="backtestOpen = !backtestOpen">
                {{ backtestOpen ? '▲ 접기' : '▼ 결과 보기' }}
              </button>
            </div>
            <template v-if="backtestOpen">
              <div v-if="store.backtestLoading" class="h-32 rounded-xl animate-pulse"
                   style="background:rgba(255,255,255,0.05)"/>
              <template v-else>
                <div v-if="store.backtestSummary?.comparison"
                     class="overflow-auto rounded-xl border" style="border-color:rgba(255,255,255,0.1)">
                  <table class="w-full text-sm">
                    <thead style="background:rgba(255,255,255,0.05)">
                      <tr>
                        <th class="text-left text-xs text-white/40 font-medium px-4 py-2.5">지표명</th>
                        <th class="text-right text-xs text-white/40 font-medium px-4 py-2.5">값</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in store.backtestSummary.comparison" :key="row.key"
                          class="border-t" style="border-color:rgba(255,255,255,0.06)">
                        <td class="px-4 py-2.5 text-white/65">{{ row.key }}</td>
                        <td class="px-4 py-2.5 text-right" :class="valueClass(row.value)">{{ row.value }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="text-center text-white/30 py-6 text-sm">백테스트 데이터 없음</div>
                <BacktestMonthlyChart :data="store.backtestMonthly" />
                <div>
                  <button class="text-sm text-white/40 hover:text-white/65 transition-colors"
                          @click="rawOpen = !rawOpen">
                    {{ rawOpen ? '▲ 원문 결과 닫기' : '▼ 원문 결과 보기' }}
                  </button>
                  <pre v-if="rawOpen"
                       class="mt-2 text-xs text-white/50 rounded-xl p-4 overflow-x-auto whitespace-pre-wrap"
                       style="background:rgba(255,255,255,0.04)">{{ store.backtestSummary?.v8_walk_forward }}</pre>
                </div>
              </template>
            </template>
          </div>
        </div>

        <!-- ── [1+] 보유 종목 상세 페이지 ── -->
        <div v-else key="stock-detail" class="px-6 py-6 flex flex-col gap-5">

          <!-- 오버뷰로 돌아가기 -->
          <button class="flex items-center gap-1.5 text-white/40 hover:text-white/70 transition-colors w-fit"
                  @click="$emit('update:currentIndex', 0)">
            <LucideChevronLeft class="w-4 h-4" />
            <span class="text-sm">포트폴리오</span>
          </button>

          <!-- 종목 헤더 -->
          <div v-if="activeStock" class="rounded-2xl p-5 border"
               :style="{
                 background: `linear-gradient(135deg, ${activeStock.color}22 0%, rgba(14,29,48,0.9) 100%)`,
                 borderColor: `${activeStock.color}35`,
               }">
            <div class="flex items-start justify-between mb-4">
              <div>
                <p class="text-[12px] text-white/40 uppercase tracking-widest mb-1">{{ activeStock.sector }}</p>
                <p class="text-2xl font-black tracking-tight">{{ activeStock.company }}</p>
                <p class="text-[13px] font-mono text-white/35 mt-0.5">{{ activeStock.ticker }}</p>
              </div>
              <div class="text-right">
                <span class="inline-block px-2.5 py-1 rounded-lg text-[13px] font-bold mb-1"
                      :class="activeStock.change >= 0 ? 'text-green-300' : 'text-red-300'"
                      :style="activeStock.change >= 0 ? 'background:rgba(52,211,153,0.15)' : 'background:rgba(248,113,113,0.15)'">
                  {{ activeStock.change >= 0 ? '+' : '' }}{{ activeStock.change }}%
                </span>
                <p class="text-2xl font-black">₩{{ activeStock.currentPrice.toLocaleString() }}</p>
              </div>
            </div>

            <!-- Quant 점수 -->
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <p class="text-[11px] text-white/35 uppercase tracking-wide">Quant Score</p>
                <p class="text-sm font-black"
                   :class="(activeStock.quantScore ?? 50) >= 70 ? 'text-green-300' : (activeStock.quantScore ?? 50) >= 45 ? 'text-yellow-300' : 'text-red-300'">
                  {{ activeStock.quantScore ?? '—' }}
                </p>
              </div>
              <div class="w-full h-2 rounded-full" style="background:rgba(255,255,255,0.1)">
                <div class="h-full rounded-full transition-all"
                     :class="(activeStock.quantScore ?? 50) >= 70 ? 'bg-green-400' : (activeStock.quantScore ?? 50) >= 45 ? 'bg-yellow-400' : 'bg-red-400'"
                     :style="{ width: `${activeStock.quantScore ?? 50}%` }"></div>
              </div>
            </div>
          </div>

          <!-- 안내 -->
          <div class="rounded-xl px-4 py-3 text-center text-[13px] text-white/25"
               style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06)">
            하단 팬 메뉴에서 해당 카드를 <strong class="text-white/40">길게 누른 후</strong> 좌우로 드래그 →
            <span class="text-red-300/70">삭제</span> / <span class="text-emerald-300/70">교체</span>
          </div>

          <!-- Company 상세 보기 버튼 -->
          <button v-if="activeStock"
                  class="w-full py-3 rounded-xl border text-sm font-medium transition-colors hover:bg-white/8"
                  style="border-color:rgba(255,255,255,0.14);color:rgba(255,255,255,0.6)"
                  @click="emit('view-company', activeStock.ticker)">
            {{ activeStock.company }} 상세 보기 →
          </button>
        </div>

      </transition>
    </div><!-- /scrollable -->

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { LucideChevronLeft } from 'lucide-vue-next'
import { usePortfolioStore } from '@/stores/portfolio.js'
import BacktestMonthlyChart  from '@/components/portfolio/BacktestMonthlyChart.vue'

const props = defineProps({
  portfolioGroups: { type: Array,  required: true },
  activeGroupId:   { type: Number, required: true },
  currentIndex:    { type: Number, default: 0 },
})
const emit = defineEmits(['update:currentIndex', 'view-company'])

// ── 포트폴리오 스토어 (AI 추천 / 백테스트) ──
const store          = usePortfolioStore()
const portfolioError = ref(null)
const backtestOpen   = ref(false)
const rawOpen        = ref(false)

async function onTypeChange(type) {
  store.setType(type); portfolioError.value = null
  try   { await store.fetchPortfolio(type) }
  catch (e) { portfolioError.value = e?.response?.status === 404 ? 'not_ready' : 'error' }
}
async function onVersionChange(ver) {
  try   { await store.changeVersion(ver) }
  catch (e) { portfolioError.value = e?.response?.status === 404 ? 'not_ready' : 'error' }
}
onMounted(() => {
  nextTick(() => setTimeout(() => {
    store.initVersions().catch(() => {})
    store.fetchPortfolio('growth').catch(e => {
      portfolioError.value = e?.response?.status === 404 ? 'not_ready' : 'error'
    })
    store.fetchBacktest().catch(() => {})
  }, 320))
})

// ── 색상 헬퍼 ──
const BAR_COLORS = { A:'#1D9E75', B:'#378ADD', C:'#EF9F27', D:'#E24B4A' }
const barColor  = (s) => s>=80?BAR_COLORS.A:s>=60?BAR_COLORS.B:s>=40?BAR_COLORS.C:BAR_COLORS.D
const tierStyle = (t) => ({
  A:'background:rgba(29,158,117,0.25);color:#34d399',
  B:'background:rgba(55,138,221,0.25);color:#60a5fa',
  C:'background:rgba(239,159,39,0.25);color:#fbbf24',
  D:'background:rgba(226,75,74,0.25);color:#f87171',
}[t] ?? 'background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.5)')
const valueClass = (val) => {
  if (!val) return 'text-white/60'
  const s = String(val)
  if (s.startsWith('-')) return 'text-red-400 font-medium'
  if (s.includes('+') || (s.endsWith('%') && !s.startsWith('-'))) return 'text-green-400 font-medium'
  return 'text-white/60'
}

// ── 개인 포트폴리오 (보유 종목 상세용) ──
const activeGroup  = computed(() => props.portfolioGroups.find(g => g.id === props.activeGroupId))
const activeStocks = computed(() => activeGroup.value?.stocks || [])
const activeStock  = computed(() => props.currentIndex === 0 ? null : activeStocks.value[props.currentIndex - 1] ?? null)
</script>

<style scoped>
.page-switch-enter-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.page-switch-leave-active { transition: opacity 0.15s ease; }
.page-switch-enter-from   { opacity: 0; transform: translateY(10px); }
.page-switch-leave-to     { opacity: 0; }
</style>
