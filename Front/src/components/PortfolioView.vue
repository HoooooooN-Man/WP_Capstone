<template>
  <div class="w-full h-full rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden animate-drop-in border border-white/10 text-white"
    style="background: linear-gradient(160deg, #0f0c08 0%, #1a1408 100%)">

    <!-- 헤더: 총 자산 -->
    <div class="px-6 pt-5 pb-3 border-b border-white/10 flex-shrink-0">
      <div class="flex justify-between items-center">
        <div>
          <p class="text-[9px] text-white/40 uppercase tracking-widest mb-0.5">Total Portfolio</p>
          <p class="text-[22px] font-black tracking-tight leading-none">
            ₩{{ totalValue.toLocaleString() }}
          </p>
        </div>
        <div class="text-right">
          <p class="text-base font-bold" :class="totalReturn >= 0 ? 'text-green-400' : 'text-red-400'">
            {{ totalReturn >= 0 ? '+' : '' }}{{ totalReturn.toFixed(2) }}%
          </p>
          <p class="text-[9px] text-white/30">{{ portfolios.length }}개 종목</p>
        </div>
      </div>
    </div>

    <!-- 카드 스택 영역 -->
    <div class="flex-1 relative flex flex-col items-center justify-center px-5 py-3 overflow-hidden">

      <!-- 스와이프 액션 힌트 -->
      <transition name="hint">
        <div v-if="dragX < -50" class="absolute left-3 top-1/2 -translate-y-1/2 z-50 pointer-events-none">
          <div class="bg-red-500 text-white px-3 py-1.5 rounded-xl font-bold text-sm shadow-xl ring-1 ring-red-400">← 청산</div>
        </div>
      </transition>
      <transition name="hint">
        <div v-if="dragX > 50" class="absolute right-3 top-1/2 -translate-y-1/2 z-50 pointer-events-none">
          <div class="bg-emerald-500 text-white px-3 py-1.5 rounded-xl font-bold text-sm shadow-xl ring-1 ring-emerald-400">교체 →</div>
        </div>
      </transition>

      <!-- 카드 스택 -->
      <div class="relative w-full max-w-[440px]" style="height: 230px">

        <!-- 뒤 카드 peek (2장) -->
        <template v-for="offset in [2, 1]" :key="`bg-${offset}`">
          <div
            v-if="portfolios[currentIndex + offset]"
            class="absolute inset-x-2 rounded-2xl border border-white/10"
            :style="{
              top: `${offset * 9}px`,
              height: '210px',
              background: `linear-gradient(135deg, ${portfolios[currentIndex + offset].color}bb, ${portfolios[currentIndex + offset].color}55)`,
              zIndex: 10 - offset * 2,
              transform: `scale(${1 - offset * 0.025})`,
              opacity: 0.6 - (offset - 1) * 0.25,
              transformOrigin: 'top center'
            }"
          ></div>
        </template>

        <!-- 현재 카드 (드래그) -->
        <div
          v-if="portfolios.length > 0"
          class="absolute inset-x-0 rounded-2xl cursor-grab active:cursor-grabbing select-none overflow-hidden border border-white/15"
          :style="{
            top: 0,
            height: '210px',
            transform: `translateX(${dragX}px) rotate(${dragX * 0.012}deg)`,
            background: `linear-gradient(135deg, ${currentPortfolio.color}ee 0%, ${currentPortfolio.color}77 100%)`,
            zIndex: 20,
            transition: isDragging ? 'none' : 'transform 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
            boxShadow: `0 16px 48px ${currentPortfolio.color}40`
          }"
          @mousedown.prevent="startDrag"
          @mousemove.prevent="onDrag"
          @mouseup.prevent="endDrag"
          @mouseleave="endDragIfActive"
          @touchstart.prevent="startDrag"
          @touchmove.prevent="onDrag"
          @touchend.prevent="endDrag"
        >
          <div class="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent pointer-events-none"></div>

          <div class="relative h-full flex flex-col p-5">
            <!-- 상단 -->
            <div class="flex justify-between items-start mb-3">
              <div>
                <p class="text-[9px] text-white/55 uppercase tracking-widest">{{ currentPortfolio.sector }}</p>
                <p class="text-lg font-black leading-tight">{{ currentPortfolio.company }}</p>
                <p class="text-[10px] text-white/45 font-mono">{{ currentPortfolio.ticker }}</p>
              </div>
              <div class="px-2.5 py-1 rounded-lg text-xs font-bold"
                :class="currentPortfolio.change >= 0 ? 'bg-green-500/25 text-green-200' : 'bg-red-500/25 text-red-200'">
                {{ currentPortfolio.change >= 0 ? '+' : '' }}{{ currentPortfolio.change }}%
              </div>
            </div>

            <!-- 핵심 수치 -->
            <div class="grid grid-cols-2 gap-x-4 gap-y-2 flex-1">
              <div>
                <p class="text-[8px] text-white/35 uppercase tracking-wide">보유수량</p>
                <p class="text-sm font-bold">{{ currentPortfolio.shares.toLocaleString() }}주</p>
              </div>
              <div>
                <p class="text-[8px] text-white/35 uppercase tracking-wide">평가금액</p>
                <p class="text-sm font-bold">₩{{ (currentPortfolio.shares * currentPortfolio.currentPrice).toLocaleString() }}</p>
              </div>
              <div>
                <p class="text-[8px] text-white/35 uppercase tracking-wide">평균단가</p>
                <p class="text-sm font-bold">₩{{ currentPortfolio.avgPrice.toLocaleString() }}</p>
              </div>
              <div>
                <p class="text-[8px] text-white/35 uppercase tracking-wide">평가손익</p>
                <p class="text-sm font-bold" :class="profitLoss >= 0 ? 'text-green-300' : 'text-red-300'">
                  {{ profitLoss >= 0 ? '+' : '' }}₩{{ Math.abs(profitLoss).toLocaleString() }}
                </p>
              </div>
            </div>

            <!-- 비중 바 -->
            <div class="mt-2">
              <div class="flex justify-between text-[8px] text-white/35 mb-1">
                <span>비중</span><span>{{ currentPortfolio.weight }}%</span>
              </div>
              <div class="h-1 bg-white/15 rounded-full">
                <div class="h-full bg-white/65 rounded-full transition-all duration-500"
                  :style="{ width: currentPortfolio.weight + '%' }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 포트폴리오 없음 -->
        <div v-if="portfolios.length === 0"
          class="absolute inset-0 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
          <p class="text-white/25 text-sm font-bold">포트폴리오가 비어있습니다</p>
        </div>
      </div>
    </div>

    <!-- 네비게이션 -->
    <div class="px-6 pb-4 flex items-center justify-between flex-shrink-0 border-t border-white/10 pt-3">
      <button @click="prevCard" :disabled="currentIndex === 0"
        class="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors disabled:opacity-20 disabled:cursor-not-allowed">
        <LucideChevronUp class="w-3.5 h-3.5" />
      </button>

      <div class="flex items-center gap-1.5">
        <div v-for="(_, i) in portfolios" :key="i"
          class="rounded-full transition-all duration-300"
          :class="i === currentIndex ? 'w-4 h-1.5 bg-white' : 'w-1.5 h-1.5 bg-white/25'">
        </div>
      </div>

      <button @click="nextCard" :disabled="currentIndex >= portfolios.length - 1"
        class="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors disabled:opacity-20 disabled:cursor-not-allowed">
        <LucideChevronDown class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { LucideChevronUp, LucideChevronDown } from 'lucide-vue-next';

const props = defineProps({
  portfolios: { type: Array, required: true }
});
const emit = defineEmits(['liquidate', 'replace']);

const currentIndex = ref(0);
const dragX = ref(0);
const isDragging = ref(false);
const startX = ref(0);
const THRESHOLD = 110;

const currentPortfolio = computed(() => props.portfolios[currentIndex.value] ?? {});

const profitLoss = computed(() => {
  const p = currentPortfolio.value;
  return p.shares ? (p.currentPrice - p.avgPrice) * p.shares : 0;
});

const totalValue = computed(() =>
  props.portfolios.reduce((s, p) => s + p.shares * p.currentPrice, 0)
);

const totalReturn = computed(() => {
  const cost = props.portfolios.reduce((s, p) => s + p.shares * p.avgPrice, 0);
  return cost ? ((totalValue.value - cost) / cost) * 100 : 0;
});

const prevCard = () => { if (currentIndex.value > 0) currentIndex.value--; };
const nextCard = () => { if (currentIndex.value < props.portfolios.length - 1) currentIndex.value++; };

const getClientX = (e) => e.type.includes('touch') ? e.touches[0].clientX : e.clientX;

const startDrag = (e) => { isDragging.value = true; startX.value = getClientX(e); };

const onDrag = (e) => {
  if (!isDragging.value) return;
  dragX.value = getClientX(e) - startX.value;
};

const endDrag = () => {
  if (!isDragging.value) return;
  isDragging.value = false;
  const x = dragX.value;
  if (x > THRESHOLD) {
    dragX.value = 600;
    setTimeout(() => {
      emit('replace', currentIndex.value);
      dragX.value = 0;
    }, 350);
  } else if (x < -THRESHOLD) {
    dragX.value = -600;
    setTimeout(() => {
      emit('liquidate', currentIndex.value);
      if (currentIndex.value > 0 && currentIndex.value >= props.portfolios.length - 1) {
        currentIndex.value--;
      }
      dragX.value = 0;
    }, 350);
  } else {
    dragX.value = 0;
  }
};

const endDragIfActive = () => { if (isDragging.value) endDrag(); };
</script>

<style scoped>
@keyframes dropIn {
  0%   { opacity: 0; transform: translateY(-40px) scale(0.97); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}
.animate-drop-in { animation: dropIn 0.7s cubic-bezier(0.165, 0.84, 0.44, 1) forwards; }

.hint-enter-active, .hint-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.hint-enter-from, .hint-leave-to { opacity: 0; transform: translateY(-50%) scale(0.85); }
</style>