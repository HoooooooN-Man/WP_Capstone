<template>
  <div class="w-full h-full rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden animate-drop-in border border-white/10 text-white"
    style="background: linear-gradient(160deg, #0f0c08 0%, #1a1408 100%)">

    <!-- 크롬 탭 바 -->
    <div class="flex-shrink-0 border-b border-white/10">
      <div class="flex items-end gap-0 pt-3 px-3 overflow-x-auto" style="scrollbar-width:none">
        <div
          v-for="group in portfolioGroups"
          :key="group.id"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg border-t border-x transition-all duration-200 cursor-pointer flex-shrink-0 min-w-[72px] max-w-[120px]"
          :class="group.id === activeGroupId
            ? 'bg-[#1a1408] border-white/20 text-white'
            : 'bg-black/20 border-white/8 text-white/40 hover:bg-black/30 hover:text-white/60'"
          @click="emit('switch-group', group.id)"
        >
          <input
            v-if="editingId === group.id"
            v-model="editingName"
            ref="renameInputRef"
            class="bg-transparent outline-none text-[11px] font-bold w-full min-w-0"
            @blur="confirmRename"
            @keydown.enter="confirmRename"
            @keydown.escape.stop="cancelRename"
            @click.stop
          />
          <span
            v-else
            class="text-[11px] font-bold truncate flex-1 leading-none"
            @dblclick.stop="startRename(group)"
          >{{ group.name }}</span>
          <button
            v-if="portfolioGroups.length > 1"
            @click.stop="emit('remove-group', group.id)"
            class="w-3 h-3 rounded flex items-center justify-center opacity-50 hover:opacity-100 hover:bg-white/20 flex-shrink-0 transition-opacity"
          >
            <LucideX class="w-2.5 h-2.5" />
          </button>
        </div>
        <button
          @click="emit('add-group')"
          class="px-2 py-1.5 flex items-center justify-center text-white/30 hover:text-white/60 hover:bg-white/5 rounded-t-lg transition-all duration-200 flex-shrink-0"
        >
          <LucidePlus class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- 요약 + 자동매매 토글 -->
      <div class="px-4 py-2 flex items-center justify-between gap-2">
        <div class="flex-1 min-w-0">
          <p class="text-[8px] text-white/40 uppercase tracking-widest mb-0.5">Total</p>
          <p class="text-[16px] font-black tracking-tight leading-none">₩{{ totalValue.toLocaleString() }}</p>
        </div>
        <div class="text-right flex-shrink-0">
          <p class="text-xs font-bold" :class="totalReturn >= 0 ? 'text-green-400' : 'text-red-400'">
            {{ totalReturn >= 0 ? '+' : '' }}{{ totalReturn.toFixed(2) }}%
          </p>
          <p class="text-[8px] text-white/30">{{ activeStocks.length }}개 종목</p>
        </div>
        <!-- 자동매매 토글 -->
        <button
          @click="emit('toggle-auto-trade')"
          class="flex flex-col items-center gap-1 flex-shrink-0 px-1"
        >
          <p class="text-[7px] uppercase tracking-widest font-bold transition-colors"
            :class="autoTradeState !== 'off' ? 'text-green-400' : 'text-white/30'">AUTO</p>
          <div class="relative w-10 h-5 rounded-full transition-all duration-300"
            :class="autoTradeState !== 'off' ? 'bg-green-500/50' : 'bg-white/15'">
            <div class="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all duration-300"
              :class="autoTradeState !== 'off' ? 'right-0.5' : 'left-0.5 opacity-40'"></div>
            <div v-if="autoTradeState === 'analyzing'"
              class="absolute inset-0 rounded-full bg-green-400/40 animate-ping pointer-events-none"></div>
          </div>
        </button>
      </div>

      <!-- 분석 중 배너 -->
      <transition name="banner">
        <div v-if="autoTradeState === 'analyzing'"
          class="px-4 pb-2 flex items-center gap-2">
          <div class="flex-1 h-px bg-green-500/30"></div>
          <p class="text-[9px] text-green-400 font-bold uppercase tracking-widest animate-pulse">퀀트 분석 중...</p>
          <div class="flex-1 h-px bg-green-500/30"></div>
        </div>
      </transition>
    </div>

    <!-- 본문: 좌우 분할 -->
    <div class="flex-1 flex overflow-hidden min-h-0">

      <!-- 왼쪽: 큰 상세 카드 -->
      <div class="flex-1 p-3 pr-2 overflow-hidden flex flex-col gap-2">

        <!-- 자동매매 거래 결과 알림 -->
        <transition name="trade-log">
          <div v-if="tradeLog"
            class="flex-shrink-0 rounded-xl border border-white/15 overflow-hidden text-[10px]"
            style="background: linear-gradient(135deg, #0a1e0e 0%, #0d1a0a 100%)">
            <div class="px-3 py-2 border-b border-white/10 flex items-center gap-1.5">
              <div class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></div>
              <p class="text-[9px] text-green-400 font-bold uppercase tracking-widest">자동매매 완료</p>
            </div>
            <div class="px-3 py-2 space-y-1">
              <div v-if="tradeLog.bought.length" class="flex items-start gap-2">
                <span class="text-blue-400 font-black flex-shrink-0">매수</span>
                <span class="text-white/60">{{ tradeLog.bought.join(', ') }}</span>
              </div>
              <div v-if="tradeLog.sold.length" class="flex items-start gap-2">
                <span class="text-red-400 font-black flex-shrink-0">청산</span>
                <span class="text-white/60">{{ tradeLog.sold.join(', ') }}</span>
              </div>
            </div>
          </div>
        </transition>

        <transition name="card-switch" mode="out-in">
          <div
            v-if="activeStock"
            :key="activeStock.id"
            class="flex-1 rounded-2xl border border-white/20 overflow-hidden relative flex flex-col"
            :style="{
              background: `linear-gradient(145deg, ${activeStock.color}cc 0%, ${activeStock.color}55 50%, #0f0c0820 100%)`,
              boxShadow: `0 20px 60px ${activeStock.color}45`
            }"
          >
            <div class="absolute inset-0 bg-gradient-to-br from-white/12 to-transparent pointer-events-none"></div>
            <div class="relative p-4 flex flex-col h-full">
              <div
                class="mb-3 cursor-pointer group"
                @click="emit('view-company', activeStock.ticker)"
              >
                <p class="text-[8px] text-white/50 uppercase tracking-widest">{{ activeStock.sector }}</p>
                <div class="flex items-center gap-1 mt-0.5">
                  <p class="text-lg font-black leading-tight group-hover:text-white/80 transition-colors">{{ activeStock.company }}</p>
                  <LucideChevronRight class="w-4 h-4 text-white/40 group-hover:text-white/70 transition-colors flex-shrink-0" />
                </div>
                <div class="flex items-center gap-2 mt-1">
                  <span class="text-[9px] text-white/40 font-mono">{{ activeStock.ticker }}</span>
                  <span class="px-2 py-0.5 rounded-md text-[10px] font-bold"
                    :class="activeStock.change >= 0 ? 'bg-green-500/25 text-green-200' : 'bg-red-500/25 text-red-200'">
                    {{ activeStock.change >= 0 ? '+' : '' }}{{ activeStock.change }}%
                  </span>
                </div>
              </div>
              <div class="pb-3 mb-3 border-b border-white/15">
                <div class="flex items-end justify-between mb-1">
                  <div>
                    <p class="text-[7px] text-white/40 uppercase tracking-wide mb-0.5">현재가</p>
                    <p class="text-2xl font-black">₩{{ activeStock.currentPrice.toLocaleString() }}</p>
                  </div>
                  <!-- 퀀트 스코어 -->
                  <div class="text-right">
                    <p class="text-[7px] text-white/40 uppercase tracking-wide mb-0.5">Quant Score</p>
                    <p class="text-xl font-black" :class="quantTextColor(activeStock.quantScore ?? 50)">
                      {{ activeStock.quantScore ?? '—' }}
                    </p>
                  </div>
                </div>
                <div class="h-1.5 bg-black/30 rounded-full overflow-hidden mt-1">
                  <div class="h-full rounded-full transition-all duration-700"
                    :class="quantBarColor(activeStock.quantScore ?? 50)"
                    :style="{ width: (activeStock.quantScore ?? 50) + '%' }"></div>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2 flex-1">
                <div class="bg-black/25 rounded-xl p-2.5">
                  <p class="text-[7px] text-white/40 uppercase tracking-wide mb-1">보유수량</p>
                  <p class="text-sm font-bold">{{ activeStock.shares.toLocaleString() }}주</p>
                </div>
                <div class="bg-black/25 rounded-xl p-2.5">
                  <p class="text-[7px] text-white/40 uppercase tracking-wide mb-1">평가금액</p>
                  <p class="text-sm font-bold">₩{{ (activeStock.shares * activeStock.currentPrice).toLocaleString() }}</p>
                </div>
                <div class="bg-black/25 rounded-xl p-2.5">
                  <p class="text-[7px] text-white/40 uppercase tracking-wide mb-1">평균단가</p>
                  <p class="text-sm font-bold">₩{{ activeStock.avgPrice.toLocaleString() }}</p>
                </div>
                <div class="bg-black/25 rounded-xl p-2.5">
                  <p class="text-[7px] text-white/40 uppercase tracking-wide mb-1">평가손익</p>
                  <p class="text-sm font-bold" :class="calcPL(activeStock) >= 0 ? 'text-green-300' : 'text-red-300'">
                    {{ calcPL(activeStock) >= 0 ? '+' : '' }}₩{{ Math.abs(calcPL(activeStock)).toLocaleString() }}
                  </p>
                </div>
              </div>
              <div class="mt-3">
                <div class="flex justify-between text-[7px] text-white/40 mb-1">
                  <span>포트폴리오 비중</span><span>{{ activeStock.weight }}%</span>
                </div>
                <div class="h-1.5 bg-black/30 rounded-full overflow-hidden">
                  <div class="h-full bg-white/70 rounded-full transition-all duration-700"
                    :style="{ width: activeStock.weight + '%' }"></div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="flex-1 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
            <p class="text-white/20 text-xs font-bold text-center">종목을<br>선택하세요</p>
          </div>
        </transition>
        <div class="flex items-center justify-center gap-1.5 flex-shrink-0 py-1">
          <div v-for="(_, i) in activeStocks" :key="i"
            class="rounded-full transition-all duration-300 cursor-pointer"
            :class="i === currentIndex ? 'w-3 h-1.5 bg-white' : 'w-1.5 h-1.5 bg-white/25'"
            @click="goToIndex(i)">
          </div>
        </div>
      </div>

      <!-- 오른쪽: 좁은 캐러셀 -->
      <div class="relative overflow-hidden flex-shrink-0" style="width:26%" @wheel.prevent="onWheel">

        <!-- 스와이프 힌트 -->
        <transition name="hint">
          <div v-if="dragX < -40" class="absolute inset-x-1 top-3 z-50 pointer-events-none flex justify-center">
            <div class="bg-red-500 text-white px-2 py-1 rounded-lg font-bold text-[10px] shadow-lg">청산</div>
          </div>
        </transition>
        <transition name="hint">
          <div v-if="dragX > 40" class="absolute inset-x-1 bottom-3 z-50 pointer-events-none flex justify-center">
            <div class="bg-emerald-500 text-white px-2 py-1 rounded-lg font-bold text-[10px] shadow-lg">교체</div>
          </div>
        </transition>

        <!-- 페이드 마스크 -->
        <div class="absolute inset-x-0 top-0 h-12 pointer-events-none z-40"
          style="background: linear-gradient(to bottom, #0f0c08 0%, transparent 100%)"></div>
        <div class="absolute inset-x-0 bottom-0 h-12 pointer-events-none z-40"
          style="background: linear-gradient(to top, #1a1408 0%, transparent 100%)"></div>

        <!-- 카드 스택 -->
        <div
          v-for="(stock, i) in activeStocks"
          :key="stock.id"
          class="absolute rounded-xl overflow-hidden select-none border"
          :class="i === currentIndex
            ? 'border-white/20 cursor-grab active:cursor-grabbing'
            : 'border-white/8 cursor-pointer'"
          :style="cardStyle(i)"
          @click="i !== currentIndex && goToIndex(i)"
          @mousedown.prevent="i === currentIndex && startDrag($event)"
          @mousemove.prevent="i === currentIndex && onDrag($event)"
          @mouseup.prevent="i === currentIndex && endDrag()"
          @mouseleave="i === currentIndex && endDragIfActive()"
          @touchstart.prevent="i === currentIndex && startDrag($event)"
          @touchmove.prevent="i === currentIndex && onDrag($event)"
          @touchend.prevent="i === currentIndex && endDrag()"
        >
          <div class="absolute inset-0 bg-gradient-to-b from-white/15 to-transparent pointer-events-none"></div>
          <div class="relative h-full flex flex-col justify-between p-2.5">
            <div>
              <p class="text-[7px] text-white/50 uppercase tracking-wide truncate">{{ stock.sector }}</p>
              <p class="text-[11px] font-black leading-tight truncate mt-0.5">{{ stock.company }}</p>
              <p class="text-[8px] text-white/35 font-mono">{{ stock.ticker }}</p>
            </div>
            <div>
              <p class="text-[11px] font-bold mb-1"
                :class="stock.change >= 0 ? 'text-green-300' : 'text-red-300'">
                {{ stock.change >= 0 ? '+' : '' }}{{ stock.change }}%
              </p>
              <!-- 퀀트 스코어 미니 바 -->
              <div class="flex items-center gap-1">
                <div class="flex-1 h-0.5 bg-black/30 rounded-full overflow-hidden">
                  <div class="h-full rounded-full" :class="quantBarColor(stock.quantScore ?? 50)"
                    :style="{ width: (stock.quantScore ?? 50) + '%' }"></div>
                </div>
                <p class="text-[8px] font-black flex-shrink-0" :class="quantTextColor(stock.quantScore ?? 50)">
                  {{ stock.quantScore ?? '—' }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- 비어있음 -->
        <div v-if="activeStocks.length === 0"
          class="absolute inset-2 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
          <p class="text-white/20 text-[10px] font-bold text-center">비어<br>있음</p>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { LucidePlus, LucideX, LucideChevronRight } from 'lucide-vue-next';

const props = defineProps({
  portfolioGroups:  { type: Array,   required: true },
  activeGroupId:    { type: Number,  required: true },
  autoTradeState:   { type: String,  default: 'off' },
  tradeLog:         { type: Object,  default: null  },
});
const emit = defineEmits(['liquidate', 'replace', 'add-group', 'remove-group', 'rename-group', 'switch-group', 'view-company', 'toggle-auto-trade']);

const activeGroup  = computed(() => props.portfolioGroups.find(g => g.id === props.activeGroupId));
const activeStocks = computed(() => activeGroup.value?.stocks || []);
const activeStock  = computed(() => activeStocks.value[currentIndex.value] ?? null);

const currentIndex = ref(0);
const dragX        = ref(0);
const isDragging   = ref(false);
const startX       = ref(0);
const THRESHOLD    = 90;
const CARD_HEIGHT  = 130;
const SPACING      = 88;

watch(() => props.activeGroupId, () => { currentIndex.value = 0; });

// ── 이름 편집 ──────────────────────────────────
const editingId      = ref(null);
const editingName    = ref('');
const renameInputRef = ref(null);

const startRename = (group) => {
  if (group.id !== props.activeGroupId) return;
  editingId.value   = group.id;
  editingName.value = group.name;
  nextTick(() => {
    const el = Array.isArray(renameInputRef.value) ? renameInputRef.value[0] : renameInputRef.value;
    el?.focus(); el?.select();
  });
};
const confirmRename = () => {
  if (editingId.value && editingName.value.trim())
    emit('rename-group', editingId.value, editingName.value.trim());
  editingId.value = null; editingName.value = '';
};
const cancelRename = () => { editingId.value = null; editingName.value = ''; };

// ── 카드 스타일 ────────────────────────────────
const cardStyle = (i) => {
  const offset    = i - currentIndex.value;
  const absOffset = Math.abs(offset);
  if (absOffset > 2) return { display: 'none' };

  const isActive   = offset === 0;
  const scale      = isActive ? 1 : Math.max(0.74, 1 - absOffset * 0.13);
  const opacity    = isActive ? 1 : Math.max(0.28, 1 - absOffset * 0.36);
  const translateY = offset * SPACING;
  const translateX = isActive ? dragX.value : 0;
  const rotate     = isActive ? dragX.value * 0.015 : 0;
  const stock      = activeStocks.value[i];

  return {
    left:      '6px',
    right:     '6px',
    height:    `${CARD_HEIGHT}px`,
    top:       '50%',
    marginTop: `-${CARD_HEIGHT / 2}px`,
    transform: `translateY(${translateY}px) translateX(${translateX}px) scale(${scale}) rotate(${rotate}deg)`,
    opacity,
    zIndex:    20 - absOffset * 3,
    transition: isActive && isDragging.value
      ? 'none'
      : 'transform 0.32s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.32s cubic-bezier(0.22, 1, 0.36, 1)',
    background: `linear-gradient(145deg, ${stock?.color}${isActive ? 'ee' : '77'} 0%, ${stock?.color}${isActive ? '66' : '33'} 100%)`,
    boxShadow:  isActive ? `0 10px 30px ${stock?.color}50` : 'none',
    pointerEvents: absOffset > 1 ? 'none' : 'auto',
  };
};

// ── 퀀트 스코어 색상 ────────────────────────────
const quantBarColor  = (s) => s >= 70 ? 'bg-green-400' : s >= 45 ? 'bg-yellow-400' : 'bg-red-400';
const quantTextColor = (s) => s >= 70 ? 'text-green-300' : s >= 45 ? 'text-yellow-300' : 'text-red-300';

// ── 계산값 ─────────────────────────────────────
const calcPL = (p) => p.shares ? (p.currentPrice - p.avgPrice) * p.shares : 0;

const totalValue = computed(() =>
  activeStocks.value.reduce((s, p) => s + p.shares * p.currentPrice, 0)
);
const totalReturn = computed(() => {
  const cost = activeStocks.value.reduce((s, p) => s + p.shares * p.avgPrice, 0);
  return cost ? ((totalValue.value - cost) / cost) * 100 : 0;
});

// ── 내비게이션 ─────────────────────────────────
const goToIndex = (i) => { currentIndex.value = i; };
const prevCard  = () => { if (currentIndex.value > 0) currentIndex.value--; };
const nextCard  = () => { if (currentIndex.value < activeStocks.value.length - 1) currentIndex.value++; };

let lastWheel = 0;
const onWheel = (e) => {
  const now = Date.now();
  if (now - lastWheel < 200) return;
  lastWheel = now;
  e.deltaY > 0 ? nextCard() : prevCard();
};

// ── 드래그 ─────────────────────────────────────
const getClientX = (e) => e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
const startDrag  = (e) => { isDragging.value = true; startX.value = getClientX(e); };
const onDrag     = (e) => { if (!isDragging.value) return; dragX.value = getClientX(e) - startX.value; };

const endDrag = () => {
  if (!isDragging.value) return;
  isDragging.value = false;
  const x = dragX.value;
  if (x > THRESHOLD) {
    dragX.value = 400;
    setTimeout(() => { emit('replace', currentIndex.value); dragX.value = 0; }, 320);
  } else if (x < -THRESHOLD) {
    dragX.value = -400;
    setTimeout(() => {
      emit('liquidate', currentIndex.value);
      if (currentIndex.value > 0 && currentIndex.value >= activeStocks.value.length - 1)
        currentIndex.value--;
      dragX.value = 0;
    }, 320);
  } else {
    dragX.value = 0;
  }
};
const endDragIfActive = () => { if (isDragging.value) endDrag(); };
</script>

<style scoped>
.animate-drop-in { animation: drop-in 0.7s var(--ease-wallet) forwards; }

.card-switch-enter-active,
.card-switch-leave-active { transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.22, 1, 0.36, 1); }
.card-switch-enter-from  { opacity: 0; transform: translateX(12px) scale(0.97); }
.card-switch-leave-to    { opacity: 0; transform: translateX(-8px) scale(0.97); }

.trade-log-enter-active  { transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.22, 1, 0.36, 1); }
.trade-log-leave-active  { transition: opacity 0.25s ease, transform 0.2s ease; }
.trade-log-enter-from,
.trade-log-leave-to      { opacity: 0; transform: translateY(-8px); }

.banner-enter-active, .banner-leave-active { transition: opacity 0.3s ease, max-height 0.3s ease; max-height: 40px; }
.banner-enter-from, .banner-leave-to       { opacity: 0; max-height: 0; }
</style>
