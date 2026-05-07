<template>
  <div class="w-full h-full bg-gradient-to-br from-[#1f3756] to-[#14253a] rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.6)] flex flex-col overflow-hidden animate-drop-in border border-white/10 text-white relative">

    <!-- 헤더 -->
    <div class="px-6 pt-5 pb-3 border-b border-white/15 flex-shrink-0">
      <div class="flex items-center gap-3">
        <button
          v-if="detailCompany"
          @click="closeDetail"
          class="flex items-center gap-1 text-white/50 hover:text-white/80 transition-colors mr-1"
        >
          <LucideChevronLeft class="w-5 h-5" />
        </button>
        <h2 class="text-3xl font-black tracking-tighter uppercase">
          {{ detailCompany ? detailCompany.name : 'Company List' }}
        </h2>
        <div v-if="replaceMode && !detailCompany" class="px-2.5 py-1 bg-emerald-500/25 rounded-full border border-emerald-500/40">
          <span class="text-[10px] text-emerald-300 font-bold uppercase tracking-wider">교체 선택 중</span>
        </div>
      </div>
      <p v-if="replaceMode && !detailCompany" class="text-[10px] text-white/35 mt-1">교체할 종목을 선택하세요</p>
    </div>

    <!-- 기업 상세 뷰 -->
    <div v-if="detailCompany" class="flex-1 overflow-y-auto px-4 py-4 space-y-3">
      <div class="flex items-end justify-between">
        <div>
          <p class="text-[9px] text-white/40 uppercase tracking-widest mb-1">{{ detailCompany.sector }}</p>
          <p class="text-3xl font-black">₩{{ detailCompany.price.toLocaleString() }}</p>
        </div>
        <div class="px-3 py-1.5 rounded-xl text-sm font-bold"
          :class="detailCompany.change >= 0 ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'">
          {{ detailCompany.change >= 0 ? '+' : '' }}{{ detailCompany.change }}%
        </div>
      </div>
      <div class="h-1 rounded-full" :style="{ background: detailCompany.color }"></div>
      <div class="bg-white/5 rounded-xl p-3 border border-white/8">
        <p class="text-[9px] text-white/40 uppercase tracking-widest mb-1.5">기업 소개</p>
        <p class="text-sm text-white/80 leading-relaxed">{{ detailCompany.description }}</p>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div class="bg-white/5 rounded-xl p-3 border border-white/8">
          <p class="text-[9px] text-white/40 uppercase tracking-widest mb-1">시가총액</p>
          <p class="text-base font-bold">{{ detailCompany.marketCap }}</p>
        </div>
        <div class="bg-white/5 rounded-xl p-3 border border-white/8">
          <p class="text-[9px] text-white/40 uppercase tracking-widest mb-1">PER</p>
          <p class="text-base font-bold">{{ detailCompany.per }}x</p>
        </div>
        <div class="bg-white/5 rounded-xl p-3 border border-white/8">
          <p class="text-[9px] text-white/40 uppercase tracking-widest mb-1">PBR</p>
          <p class="text-base font-bold">{{ detailCompany.pbr }}x</p>
        </div>
        <div class="bg-white/5 rounded-xl p-3 border border-white/8">
          <p class="text-[9px] text-white/40 uppercase tracking-widest mb-1">배당수익률</p>
          <p class="text-base font-bold">{{ detailCompany.dividend }}%</p>
        </div>
      </div>
      <div class="flex gap-2 pt-1">
        <button
          v-if="replaceMode"
          @click="openCompare(detailCompany)"
          class="flex-1 py-2.5 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-sm font-bold hover:bg-emerald-500/30 transition-colors"
        >교체 비교하기</button>
        <template v-else>
          <button
            @click="openOrderModal(detailCompany, 'buy')"
            class="flex-1 py-2.5 rounded-xl border text-sm font-bold transition-all duration-200 bg-blue-500/20 border-blue-500/40 text-blue-200 hover:bg-blue-500/35"
          >매수</button>
          <button
            @click="openOrderModal(detailCompany, 'sell')"
            class="flex-1 py-2.5 rounded-xl border text-sm font-bold transition-all duration-200 bg-red-500/20 border-red-500/40 text-red-200 hover:bg-red-500/35"
          >매도</button>
        </template>
      </div>
    </div>

    <!-- 기업 리스트 뷰 -->
    <div v-else class="flex-1 overflow-y-auto px-4 py-3 space-y-2">
      <div
        v-for="company in companies" :key="company.id"
        class="flex items-center gap-3 p-3 rounded-xl border border-white/5 transition-all duration-200 cursor-pointer"
        :class="replaceMode
          ? 'bg-white/5 hover:bg-white/10 hover:border-emerald-500/30'
          : 'bg-white/5 hover:bg-white/8 hover:border-white/15'"
        @click="replaceMode ? openCompare(company) : openDetail(company)"
      >
        <div class="w-1 h-10 rounded-full flex-shrink-0" :style="{ background: company.color }"></div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <p class="font-bold text-sm truncate">{{ company.name }}</p>
            <span class="text-[9px] text-white/35 font-mono flex-shrink-0">{{ company.ticker }}</span>
          </div>
          <p class="text-[9px] text-white/40">{{ company.sector }}</p>
        </div>
        <!-- 퀀트 스코어 -->
        <div class="flex flex-col items-center flex-shrink-0 min-w-[36px]">
          <p class="text-[7px] text-white/30 uppercase tracking-wide">Quant</p>
          <p class="text-sm font-black" :class="quantTextColor(company.quantScore)">{{ company.quantScore }}</p>
          <div class="w-6 h-0.5 bg-black/30 rounded-full overflow-hidden mt-0.5">
            <div class="h-full rounded-full" :class="quantBarColor(company.quantScore)"
              :style="{ width: company.quantScore + '%' }"></div>
          </div>
        </div>
        <div class="text-right flex-shrink-0">
          <p class="text-sm font-bold">₩{{ company.price.toLocaleString() }}</p>
          <p class="text-[10px] font-semibold"
            :class="company.change >= 0 ? 'text-green-400' : 'text-red-400'">
            {{ company.change >= 0 ? '+' : '' }}{{ company.change }}%
          </p>
        </div>
        <div class="flex items-center gap-1 flex-shrink-0">
          <template v-if="!replaceMode">
            <button
              @click.stop="openOrderModal(company, 'buy')"
              class="px-2 py-1 rounded-lg text-[10px] font-bold border transition-all duration-200 bg-blue-500/15 border-blue-500/30 text-blue-300 hover:bg-blue-500/30"
            >매수</button>
            <button
              @click.stop="openOrderModal(company, 'sell')"
              class="px-2 py-1 rounded-lg text-[10px] font-bold border transition-all duration-200 bg-red-500/15 border-red-500/30 text-red-300 hover:bg-red-500/30"
            >매도</button>
          </template>
          <LucideChevronRight class="w-4 h-4 text-white/25 ml-0.5" />
        </div>
      </div>
    </div>

    <!-- 교체 비교 모달 -->
    <transition name="order-modal">
      <div v-if="compareCandidate" class="absolute inset-0 z-50 flex flex-col justify-end">
        <div class="absolute inset-0 bg-black/65 backdrop-blur-sm rounded-[2rem]" @click="compareCandidate = null"></div>
        <div class="relative rounded-t-[2rem] border-t border-x border-white/15 overflow-hidden"
          style="background: linear-gradient(160deg, #0f1e30 0%, #0a1420 100%)">
          <div class="flex justify-center pt-3 pb-1">
            <div class="w-8 h-1 rounded-full bg-white/20"></div>
          </div>
          <div class="px-4 pb-5 pt-2">
            <p class="text-[10px] text-white/40 uppercase tracking-widest text-center mb-3">종목 교체 비교</p>

            <div class="grid grid-cols-2 gap-2 mb-4">
              <!-- 현재 보유 -->
              <div class="rounded-xl p-3 border border-red-500/25 bg-red-500/8 space-y-2.5">
                <div>
                  <p class="text-[8px] text-red-300/60 uppercase tracking-wide mb-1">현재 보유</p>
                  <div class="h-0.5 rounded-full mb-2" :style="{ background: replaceStock?.color ?? '#888' }"></div>
                  <p class="text-sm font-black truncate">{{ replaceStock?.company }}</p>
                  <p class="text-[8px] text-white/35 font-mono">{{ replaceStock?.ticker }}</p>
                </div>
                <div class="space-y-1.5 text-xs">
                  <div class="flex justify-between">
                    <span class="text-white/40">현재가</span>
                    <span class="font-bold">₩{{ replaceStock?.currentPrice?.toLocaleString() }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">등락</span>
                    <span class="font-bold" :class="(replaceStock?.change ?? 0) >= 0 ? 'text-green-300' : 'text-red-300'">
                      {{ (replaceStock?.change ?? 0) >= 0 ? '+' : '' }}{{ replaceStock?.change }}%
                    </span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">Quant</span>
                    <span class="font-black" :class="quantTextColor(replaceStock?.quantScore ?? 50)">
                      {{ replaceStock?.quantScore ?? '—' }}
                    </span>
                  </div>
                  <template v-if="currentStockInfo">
                    <div class="flex justify-between">
                      <span class="text-white/40">PER</span>
                      <span class="font-bold">{{ currentStockInfo.per }}x</span>
                    </div>
                    <div class="flex justify-between">
                      <span class="text-white/40">PBR</span>
                      <span class="font-bold">{{ currentStockInfo.pbr }}x</span>
                    </div>
                    <div class="flex justify-between">
                      <span class="text-white/40">배당</span>
                      <span class="font-bold">{{ currentStockInfo.dividend }}%</span>
                    </div>
                  </template>
                </div>
              </div>

              <!-- 교체 종목 -->
              <div class="rounded-xl p-3 border border-blue-500/25 bg-blue-500/8 space-y-2.5">
                <div>
                  <p class="text-[8px] text-blue-300/60 uppercase tracking-wide mb-1">교체 종목</p>
                  <div class="h-0.5 rounded-full mb-2" :style="{ background: compareCandidate.color }"></div>
                  <p class="text-sm font-black truncate">{{ compareCandidate.name }}</p>
                  <p class="text-[8px] text-white/35 font-mono">{{ compareCandidate.ticker }}</p>
                </div>
                <div class="space-y-1.5 text-xs">
                  <div class="flex justify-between">
                    <span class="text-white/40">현재가</span>
                    <span class="font-bold">₩{{ compareCandidate.price.toLocaleString() }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">등락</span>
                    <span class="font-bold" :class="compareCandidate.change >= 0 ? 'text-green-300' : 'text-red-300'">
                      {{ compareCandidate.change >= 0 ? '+' : '' }}{{ compareCandidate.change }}%
                    </span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">Quant</span>
                    <span class="font-black" :class="quantTextColor(compareCandidate.quantScore)">
                      {{ compareCandidate.quantScore }}
                    </span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">PER</span>
                    <span class="font-bold">{{ compareCandidate.per }}x</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">PBR</span>
                    <span class="font-bold">{{ compareCandidate.pbr }}x</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">배당</span>
                    <span class="font-bold">{{ compareCandidate.dividend }}%</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 인라인 주문 폼 -->
            <transition name="order-inline">
              <div v-if="compareAction" class="mb-3 rounded-xl border overflow-hidden"
                :class="compareAction === 'sell'
                  ? 'border-red-500/30 bg-red-500/8'
                  : 'border-blue-500/30 bg-blue-500/8'">
                <div class="flex items-center justify-between px-3 pt-2.5 pb-1.5 border-b"
                  :class="compareAction === 'sell' ? 'border-red-500/20' : 'border-blue-500/20'">
                  <div class="flex items-center gap-2">
                    <p class="text-[10px] font-black"
                      :class="compareAction === 'sell' ? 'text-red-300' : 'text-blue-300'">
                      {{ compareAction === 'sell' ? '매도' : '매수' }}
                    </p>
                    <p class="text-[10px] text-white/50 font-bold">
                      {{ compareAction === 'sell' ? replaceStock?.company : compareCandidate.name }}
                    </p>
                  </div>
                  <button @click="compareAction = null" class="text-white/30 hover:text-white/60 text-xs">✕</button>
                </div>
                <div class="px-3 py-2.5 space-y-2">
                  <!-- 가격 -->
                  <div class="flex items-center gap-2 bg-black/20 rounded-lg px-2.5 py-2 border border-white/8">
                    <span class="text-white/40 text-xs flex-shrink-0">₩</span>
                    <input v-model.number="comparePrice" type="number"
                      class="flex-1 bg-transparent outline-none text-sm font-black text-white min-w-0" />
                  </div>
                  <!-- 수량 -->
                  <div class="flex items-center gap-2">
                    <button @click="compareQty = Math.max(1, compareQty - 1)"
                      class="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 font-bold text-base flex-shrink-0 transition-colors">−</button>
                    <input v-model.number="compareQty" type="number"
                      class="flex-1 bg-black/20 border border-white/8 rounded-lg outline-none text-center text-sm font-black py-1.5" />
                    <button @click="compareQty++"
                      class="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 font-bold text-base flex-shrink-0 transition-colors">+</button>
                  </div>
                  <!-- 총액 + 확정 -->
                  <div class="flex items-center gap-2">
                    <div class="flex-1">
                      <p class="text-[7px] text-white/35 uppercase tracking-wide">총 금액</p>
                      <p class="text-sm font-black"
                        :class="compareAction === 'sell' ? 'text-red-200' : 'text-blue-200'">
                        ₩{{ (comparePrice * compareQty).toLocaleString() }}
                      </p>
                    </div>
                    <button @click="confirmCompareOrder"
                      class="px-4 py-2 rounded-xl text-xs font-black transition-colors"
                      :class="compareAction === 'sell'
                        ? 'bg-red-500/30 border border-red-500/40 text-red-100 hover:bg-red-500/45'
                        : 'bg-blue-500/30 border border-blue-500/40 text-blue-100 hover:bg-blue-500/45'">
                      {{ compareAction === 'sell' ? '매도 확정' : '매수 확정' }}
                    </button>
                  </div>
                </div>
              </div>
            </transition>

            <!-- 매도 / 매수 버튼 -->
            <div class="flex gap-2">
              <button @click="compareCandidate = null; compareAction = null"
                class="px-3 py-2.5 rounded-xl bg-white/8 border border-white/15 text-white/50 text-xs font-bold hover:bg-white/12 transition-colors flex-shrink-0">
                취소
              </button>
              <button @click="openCompareOrder('sell')"
                class="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all duration-200"
                :class="compareAction === 'sell'
                  ? 'bg-red-500/35 border border-red-500/50 text-red-200'
                  : 'bg-red-500/15 border border-red-500/30 text-red-300 hover:bg-red-500/25'">
                현재 매도
              </button>
              <button @click="openCompareOrder('buy')"
                class="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all duration-200"
                :class="compareAction === 'buy'
                  ? 'bg-blue-500/35 border border-blue-500/50 text-blue-200'
                  : 'bg-blue-500/15 border border-blue-500/30 text-blue-300 hover:bg-blue-500/25'">
                신규 매수
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 주문 모달 (슬라이드업) -->
    <transition name="order-modal">
      <div v-if="orderCompany" class="absolute inset-0 z-50 flex flex-col justify-end">
        <!-- 배경 딤 -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm rounded-[2rem]" @click="closeOrderModal"></div>

        <!-- 모달 시트 -->
        <div class="relative rounded-t-[2rem] border-t border-x border-white/15 overflow-hidden"
          style="background: linear-gradient(160deg, #0f1e30 0%, #0a1420 100%)">

          <!-- 핸들 -->
          <div class="flex justify-center pt-3 pb-1">
            <div class="w-8 h-1 rounded-full bg-white/20"></div>
          </div>

          <div class="px-5 pb-6 pt-2 space-y-4">

            <!-- 종목 정보 + 타입 배지 -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <div class="w-2 h-8 rounded-full flex-shrink-0" :style="{ background: orderCompany.color }"></div>
                <div>
                  <p class="text-sm font-black leading-tight">{{ orderCompany.name }}</p>
                  <p class="text-[9px] text-white/40 font-mono">{{ orderCompany.ticker }}</p>
                </div>
              </div>
              <div class="flex flex-col items-end gap-1">
                <span class="px-2.5 py-1 rounded-lg text-xs font-black"
                  :class="orderType === 'buy'
                    ? 'bg-blue-500/25 text-blue-200 border border-blue-500/40'
                    : 'bg-red-500/25 text-red-200 border border-red-500/40'">
                  {{ orderType === 'buy' ? '매수' : '매도' }}
                </span>
                <p class="text-xs text-white/40">₩{{ orderCompany.price.toLocaleString() }}</p>
              </div>
            </div>

            <!-- 가격 입력 -->
            <div class="bg-white/5 rounded-xl border border-white/10 p-3">
              <p class="text-[9px] text-white/40 uppercase tracking-widest mb-2">주문 가격</p>
              <div class="flex items-center gap-2">
                <span class="text-white/50 font-bold">₩</span>
                <input
                  v-model.number="orderPrice"
                  type="number"
                  class="flex-1 bg-transparent outline-none text-lg font-black text-white"
                  min="1"
                />
              </div>
            </div>

            <!-- 수량 입력 -->
            <div class="bg-white/5 rounded-xl border border-white/10 p-3">
              <p class="text-[9px] text-white/40 uppercase tracking-widest mb-2">수량</p>
              <div class="flex items-center gap-3">
                <button
                  @click="orderQty = Math.max(1, orderQty - 1)"
                  class="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center font-bold text-lg transition-colors"
                >−</button>
                <input
                  v-model.number="orderQty"
                  type="number"
                  class="flex-1 bg-transparent outline-none text-center text-xl font-black text-white"
                  min="1"
                />
                <button
                  @click="orderQty++"
                  class="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center font-bold text-lg transition-colors"
                >+</button>
              </div>
            </div>

            <!-- 총 금액 -->
            <div class="flex items-center justify-between px-1">
              <p class="text-[10px] text-white/40 uppercase tracking-widest">총 {{ orderType === 'buy' ? '매수' : '매도' }}금액</p>
              <p class="text-lg font-black"
                :class="orderType === 'buy' ? 'text-blue-200' : 'text-red-200'">
                ₩{{ (orderPrice * orderQty).toLocaleString() }}
              </p>
            </div>

            <!-- 확인 버튼 -->
            <button
              @click="confirmOrder"
              class="w-full py-3 rounded-xl font-black text-sm tracking-wide transition-all duration-200"
              :class="orderType === 'buy'
                ? 'bg-blue-500/30 hover:bg-blue-500/45 text-blue-100 border border-blue-500/40'
                : 'bg-red-500/30 hover:bg-red-500/45 text-red-100 border border-red-500/40'"
            >
              {{ orderType === 'buy' ? '매수 주문 확인' : '매도 주문 확인' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { LucidePlus, LucideCheck, LucideChevronRight, LucideChevronLeft } from 'lucide-vue-next';
// TODO: 아래 mock import를 실제 API 호출(pinia store 등)로 교체
import { MOCK_COMPANIES } from '@/mock/data.js';

const props = defineProps({
  replaceMode:  { type: Boolean, default: false },
  replaceStock: { type: Object,  default: null  },
  viewTicker:   { type: String,  default: null  },
});
const emit = defineEmits(['select-company', 'add-company', 'back', 'sell-replace']);

// TODO: [API] GET /api/companies?market=KOSPI 로 교체
const companies = MOCK_COMPANIES;

const addedIds      = ref(new Set());
const detailCompany = ref(null);

const quantBarColor  = (s) => s >= 70 ? 'bg-green-400' : s >= 45 ? 'bg-yellow-400' : 'bg-red-400';
const quantTextColor = (s) => s >= 70 ? 'text-green-300' : s >= 45 ? 'text-yellow-300' : 'text-red-300';

// ── 교체 비교 ──────────────────────────────────
const compareCandidate = ref(null);
const compareAction    = ref(null); // 'sell' | 'buy' | null
const comparePrice     = ref(0);
const compareQty       = ref(1);

const currentStockInfo = computed(() =>
  props.replaceStock ? companies.find(c => c.ticker === props.replaceStock.ticker) : null
);

const openCompare = (company) => {
  compareCandidate.value = company;
  compareAction.value    = null;
};

const openCompareOrder = (type) => {
  compareAction.value = type;
  comparePrice.value  = type === 'sell'
    ? (props.replaceStock?.currentPrice ?? 0)
    : compareCandidate.value.price;
  compareQty.value = type === 'sell'
    ? (props.replaceStock?.shares ?? 1)
    : 1;
};

const confirmCompareOrder = () => {
  if (compareAction.value === 'buy') {
    emit('select-company', {
      id:           Date.now(),
      company:      compareCandidate.value.name,
      ticker:       compareCandidate.value.ticker,
      sector:       compareCandidate.value.sector,
      shares:       compareQty.value,
      avgPrice:     comparePrice.value,
      currentPrice: compareCandidate.value.price,
      change:       compareCandidate.value.change,
      color:        compareCandidate.value.color,
      weight:       10,
      quantScore:   compareCandidate.value.quantScore,
    });
  } else if (compareAction.value === 'sell') {
    emit('sell-replace');
  }
  compareCandidate.value = null;
  compareAction.value    = null;
};

// ── 상세 뷰 ────────────────────────────────────
watch(() => props.viewTicker, (ticker) => {
  if (ticker) detailCompany.value = companies.find(c => c.ticker === ticker) ?? null;
}, { immediate: true });

const openDetail  = (company) => { detailCompany.value = company; };
const closeDetail = () => {
  detailCompany.value = null;
  if (props.viewTicker) emit('back');
};

// ── 주문 모달 ──────────────────────────────────
const orderCompany = ref(null);
const orderType    = ref('buy');
const orderPrice   = ref(0);
const orderQty     = ref(1);

const openOrderModal = (company, type = 'buy') => {
  orderCompany.value = company;
  orderType.value    = type;
  orderPrice.value   = company.price;
  orderQty.value     = 1;
};
const closeOrderModal = () => { orderCompany.value = null; };

const confirmOrder = () => {
  if (orderType.value === 'buy') {
    addedIds.value = new Set([...addedIds.value, orderCompany.value.id]);
    emit('add-company', {
      id:           Date.now(),
      company:      orderCompany.value.name,
      ticker:       orderCompany.value.ticker,
      sector:       orderCompany.value.sector,
      shares:       orderQty.value,
      avgPrice:     orderPrice.value,
      currentPrice: orderCompany.value.price,
      change:       orderCompany.value.change,
      color:        orderCompany.value.color,
      weight:       10,
    });
  }
  closeOrderModal();
};

// ── 교체 모드 ──────────────────────────────────
const buildPortfolioItem = (company) => ({
  id:           Date.now(),
  company:      company.name,
  ticker:       company.ticker,
  sector:       company.sector,
  shares:       10,
  avgPrice:     company.price,
  currentPrice: company.price,
  change:       company.change,
  color:        company.color,
  weight:       10,
});

const selectCompany = (company) => {
  emit('select-company', buildPortfolioItem(company));
};
</script>

<style scoped>
.animate-drop-in { animation: drop-in 0.7s var(--ease-wallet) forwards; }

.order-modal-enter-active { transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.25s ease; }
.order-modal-leave-active { transition: transform 0.25s ease-in, opacity 0.2s ease; }
.order-modal-enter-from,
.order-modal-leave-to    { transform: translateY(100%); opacity: 0; }

.order-inline-enter-active { transition: opacity 0.2s ease, max-height 0.3s cubic-bezier(0.22, 1, 0.36, 1); max-height: 200px; overflow: hidden; }
.order-inline-leave-active { transition: opacity 0.15s ease, max-height 0.2s ease; max-height: 200px; overflow: hidden; }
.order-inline-enter-from,
.order-inline-leave-to    { opacity: 0; max-height: 0; }
</style>
