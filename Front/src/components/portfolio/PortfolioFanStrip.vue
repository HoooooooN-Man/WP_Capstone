<template>
  <!-- 팬 트리거 스트립 -->
  <div class="absolute bottom-0 left-0 right-0 h-5 z-30"
       @mouseenter="fanVisible = true"></div>

  <!-- 팬 바 — 지갑 바와 동일한 슬라이드-업 구조 -->
  <div class="absolute bottom-0 left-0 right-0 z-20 fan-bar"
       :style="{ transform: effectiveFanVisible ? 'translateY(0)' : 'translateY(100%)', transition: 'transform 0.38s cubic-bezier(0.32,0,0.2,1)', background: props.darkMode ? '#100c07' : '#ede4d0' }"
       @mouseleave="!swipeMode && !props.walletLocked && (fanVisible = false)">

    <!-- 스와이프 힌트 -->
    <transition name="fade">
      <div v-if="swipeMode" class="absolute inset-0 pointer-events-none z-[5]">
        <div class="absolute left-5 top-[30%] -translate-y-1/2 flex flex-col items-center gap-1.5"
             :style="{ opacity: dragX < -20 ? Math.min(1, (-dragX-20)/55) : 0.15 }">
          <div class="w-10 h-10 rounded-full flex items-center justify-center"
               style="background:rgba(239,68,68,0.2);border:1.5px solid rgba(239,68,68,0.4)">
            <LucideTrash2 class="w-3.5 h-3.5 text-red-400" />
          </div>
          <p class="text-[10px] text-red-400 font-bold uppercase tracking-wide">삭제</p>
        </div>
        <div class="absolute right-5 top-[30%] -translate-y-1/2 flex flex-col items-center gap-1.5"
             :style="{ opacity: dragX > 20 ? Math.min(1, (dragX-20)/55) : 0.15 }">
          <div class="w-10 h-10 rounded-full flex items-center justify-center"
               style="background:rgba(16,185,129,0.2);border:1.5px solid rgba(16,185,129,0.4)">
            <LucideRefreshCw class="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <p class="text-[10px] text-emerald-400 font-bold uppercase tracking-wide">교체</p>
        </div>
      </div>
    </transition>

    <!-- 카드 + 버튼 영역 (높이 고정) -->
    <div class="relative" style="height:230px">

      <!-- 부채꼴 카드들 -->
      <div v-for="(item, i) in displayItems" :key="item.id"
           class="absolute rounded-2xl overflow-hidden text-white"
           :style="cardFanStyle(i)"
           @click="onCardClick(i)"
           @mousedown="(e) => onCardDown(i, e)"
           @mousemove="(e) => onCardMove(i, e)"
           @mouseup="() => onCardUp(i)"
           @mouseleave="() => onCardLeave(i)"
           @touchstart.prevent="(e) => onCardDown(i, e)"
           @touchmove.prevent="(e) => onCardMove(i, e)"
           @touchend.prevent="() => onCardUp(i)">

        <!-- 퀀트 스코어 경고 테두리 (< 45점) -->
        <div v-if="!item.isOverview && (item.quantScore ?? 50) < 45"
             class="warn-border absolute inset-0 rounded-2xl pointer-events-none z-[60]"></div>

        <!-- 오버뷰 카드 -->
        <div v-if="item.isOverview" class="relative h-full flex flex-col justify-between p-2.5">
          <div>
            <p class="text-[6.5px] font-bold uppercase tracking-widest mb-0.5"
               style="color:rgba(201,162,39,0.9)">Portfolio</p>
            <p class="text-[12px] font-black leading-tight">
              {{ totalValue >= 1_000_000
                ? '₩' + (totalValue/1_000_000).toFixed(1)+'M'
                : '₩' + totalValue.toLocaleString() }}
            </p>
          </div>
          <div>
            <div v-if="activeStocksCount > 0" class="flex gap-[1.5px] h-1 rounded-full overflow-hidden mb-1.5">
              <div v-for="s in displayItems.slice(1, 7)" :key="s.id"
                   class="h-full flex-1" :style="{ background: s.color ?? '#4A90E2' }"></div>
            </div>
            <p class="text-[12px] font-black"
               :class="totalReturn >= 0 ? 'text-green-300' : 'text-red-300'">
              {{ totalReturn >= 0 ? '+' : '' }}{{ totalReturn.toFixed(1) }}%
            </p>
            <p class="text-[9px] mt-0.5" style="color:rgba(255,255,255,0.38)">{{ activeStocksCount }}종목</p>
          </div>
        </div>

        <!-- 종목 카드 -->
        <div v-else class="relative h-full flex flex-col justify-between p-2.5">
          <div>
            <p class="text-[10px] font-black leading-tight truncate">{{ item.company }}</p>
            <p class="text-[8px] font-mono mt-0.5" style="color:rgba(255,255,255,0.38)">{{ item.ticker }}</p>
          </div>
          <div>
            <div class="w-full h-0.5 rounded-full mb-1.5" style="background:rgba(255,255,255,0.12)">
              <div class="h-full rounded-full"
                   :class="(item.quantScore??50)>=70?'bg-green-400':(item.quantScore??50)>=45?'bg-yellow-400':'bg-red-400'"
                   :style="{ width:`${item.quantScore??50}%` }"></div>
            </div>
            <div class="flex items-center justify-between">
              <p class="text-[10px] font-bold" :class="item.change>=0?'text-green-300':'text-red-300'">
                {{ item.change>=0?'+':'' }}{{ item.change }}%
              </p>
              <p class="text-[12px] font-black"
                 :class="(item.quantScore??50)>=70?'text-green-300':(item.quantScore??50)>=45?'text-yellow-300':'text-red-300'">
                {{ item.quantScore??'—' }}
              </p>
            </div>
          </div>
        </div>

        <!-- 롱프레스 오버레이 -->
        <transition name="fade">
          <div v-if="longPressingIdx === i"
               class="absolute inset-0 flex items-center justify-center rounded-2xl pointer-events-none"
               style="background:rgba(255,255,255,0.08)">
            <div class="w-6 h-6 rounded-full border-2 border-white/60 border-t-transparent animate-spin"></div>
          </div>
        </transition>
      </div>

      <!-- 뒤로가기 버튼 (둥근 원형) -->
      <button class="absolute z-10 flex flex-col items-center justify-center gap-1 rounded-full border
                     active:scale-95 transition-all duration-200 shadow-lg"
              style="width:52px; height:52px;"
              :style="{
                bottom:`${BTN_BOTTOM}px`, left:'50%', transform:'translateX(-50%)',
                background: swipeMode ? 'rgba(201,162,39,0.14)' : 'rgba(20,14,6,0.75)',
                borderColor: swipeMode ? 'rgba(201,162,39,0.45)' : 'rgba(255,255,255,0.1)',
                color: swipeMode ? 'rgba(201,162,39,0.9)' : 'rgba(255,255,255,0.4)',
              }"
              @click="swipeMode ? cancelSwipe() : emit('back')">
        <component :is="swipeMode ? LucideX : LucideChevronLeft" class="w-4 h-4" />
        <span class="text-[10px] font-bold tracking-wide leading-none">
          {{ swipeMode ? '취소' : '메뉴' }}
        </span>
      </button>

      <!-- 자동매매 버튼 (게시판 버튼 스타일) -->
      <button class="absolute z-10 flex flex-col items-center gap-1 px-3 py-2 rounded-2xl border
                     active:scale-95 transition-all duration-200 shadow-lg"
              :style="{
                bottom:`${BTN_BOTTOM}px`, right:'14px',
                background: autoTradeState!=='off' ? 'rgba(16,185,129,0.18)' : 'rgba(20,14,6,0.75)',
                borderColor: autoTradeState!=='off' ? 'rgba(16,185,129,0.45)' : 'rgba(255,255,255,0.1)',
                color: autoTradeState!=='off' ? 'rgba(52,211,153,0.9)' : 'rgba(255,255,255,0.4)',
              }"
              @click="emit('toggle-auto-trade')">
        <div class="relative w-5 h-5 flex items-center justify-center">
          <div class="w-4 h-2 rounded-full transition-all duration-200"
               :class="autoTradeState!=='off' ? 'bg-green-400/60' : 'bg-white/20'">
            <div class="absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all duration-200 shadow"
                 :class="autoTradeState!=='off' ? 'right-0' : 'left-0 opacity-40'"></div>
          </div>
          <div v-if="autoTradeState==='analyzing'"
               class="absolute inset-0 rounded-full bg-green-400/30 animate-ping pointer-events-none"></div>
        </div>
        <span class="text-[10px] font-bold tracking-wide leading-none">AUTO</span>
      </button>

    </div><!-- /카드+버튼 -->
  </div><!-- /팬 바 -->
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { LucideX, LucideChevronLeft, LucideTrash2, LucideRefreshCw } from 'lucide-vue-next'

const props = defineProps({
  displayItems:     { type: Array,   required: true },
  currentIndex:     { type: Number,  required: true },
  totalValue:       { type: Number,  default: 0 },
  totalReturn:      { type: Number,  default: 0 },
  activeStocksCount:{ type: Number,  default: 0 },
  autoTradeState:   { type: String,  default: 'off' },
  walletLocked:     { type: Boolean, default: false },
  darkMode:         { type: Boolean, default: false },
})
const emit = defineEmits([
  'update:currentIndex',
  'back', 'liquidate', 'replace', 'view-company', 'toggle-auto-trade',
  'fan-open',   // 팬이 열릴 때 부모에 알림
])

// ── 팬 가시성 ─────────────────────────────────────
const fanVisible          = ref(false)
const effectiveFanVisible = computed(() => props.walletLocked || fanVisible.value)

// 팬 열림/닫힘 상태를 부모(PortfolioView)에 알림 → 콘텐츠 영역 bottom 동적 조정
watch(effectiveFanVisible, (v) => emit('fan-open', v), { immediate: true })

// ── 카드 포지셔닝 상수 ─────────────────────────────
const BTN_BOTTOM   = 26
const BTN_SIZE     = 50
const BTN_CENTER_Y = BTN_BOTTOM + BTN_SIZE / 2

const CARD_W     = 84
const CARD_H     = 128
const FAN_RADIUS = 118
const ANGLE_STEP = 27

// ── 색상 헬퍼 (불투명 카드용) ──────────────────────
const darkenHex = (hex, amount) => {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const d = (v) => Math.max(0, v - amount).toString(16).padStart(2, '0')
  return `#${d(r)}${d(g)}${d(b)}`
}

// ── 스와이프 상태 ──────────────────────────────────
const swipeMode       = ref(false)
const dragX           = ref(0)
const isDragging      = ref(false)
const startX          = ref(0)
const longPressingIdx = ref(null)
const THRESHOLD       = 80
const LONG_PRESS_MS   = 480
let   longPressTimer  = null

// ── 카드 스타일 계산 ───────────────────────────────
const cardFanStyle = (i) => {
  const relIdx = i - props.currentIndex
  if (Math.abs(relIdx) > 3) return { display: 'none' }

  const angleDeg = relIdx * ANGLE_STEP
  const rad      = (angleDeg * Math.PI) / 180
  const swipeDX  = isSwipeDragging(i) ? dragX.value : 0
  const offsetX  = FAN_RADIUS * Math.sin(rad) + swipeDX
  const offsetY  = FAN_RADIUS * Math.cos(rad)

  const cardBottom = (BTN_CENTER_Y + offsetY) - CARD_H / 2
  const cardLeft   = offsetX - CARD_W / 2
  const isActive   = relIdx === 0
  const isLP       = longPressingIdx.value === i

  const scale   = isLP ? 1.18 : (swipeMode.value && isActive) ? 1.18 : isActive ? 1.10 : Math.max(0.80, 1 - Math.abs(relIdx) * 0.09)
  const opacity  = (swipeMode.value && !isActive) ? 0.15 : 1
  const zIndex   = isActive ? 25 : Math.max(1, 20 - Math.abs(relIdx) * 2)
  const rotate   = angleDeg * 0.28 + (isSwipeDragging(i) ? swipeDX * 0.06 : 0)
  const col      = props.displayItems[i]?.color ?? '#888888'

  // 불투명 그라디언트: active는 선명하게, 비활성은 더 어둡게
  const bgTop    = isActive ? col                : darkenHex(col, 30)
  const bgBottom = isActive ? darkenHex(col, 65) : darkenHex(col, 95)

  return {
    position: 'absolute', width: `${CARD_W}px`, height: `${CARD_H}px`,
    bottom: `${cardBottom}px`, left: `calc(50% + ${cardLeft}px)`,
    transform: `scale(${scale}) rotate(${rotate}deg)`,
    transformOrigin: 'center center',
    opacity, zIndex,
    transition: (isSwipeDragging(i) && isDragging.value)
      ? 'opacity 0.1s, transform 0.1s'
      : isLP ? 'transform 0.2s ease' : 'all 0.38s cubic-bezier(0.22,1,0.36,1)',
    background: `linear-gradient(145deg, ${bgTop} 0%, ${bgBottom} 100%)`,
    boxShadow: isLP
      ? `0 16px 40px ${col}88, 0 0 0 2px rgba(255,255,255,0.3)`
      : isActive
        ? `0 8px 28px ${col}66, 0 0 0 1px rgba(255,255,255,0.22)`
        : `0 3px 12px rgba(0,0,0,0.55)`,
    border: isActive ? '1px solid rgba(255,255,255,0.28)' : '1px solid rgba(255,255,255,0.12)',
    cursor: 'pointer', borderRadius: '16px', overflow: 'hidden',
    pointerEvents: (swipeMode.value && !isActive) || Math.abs(relIdx) > 3 ? 'none' : 'auto',
  }
}

// ── 이벤트 핸들러 ──────────────────────────────────
const isSwipeDragging = (i) => swipeMode.value && i === props.currentIndex
const getClientX = (e) => e.type?.includes('touch') ? e.touches[0]?.clientX : e.clientX

const onCardClick = (i) => {
  if (swipeMode.value || longPressingIdx.value !== null) return
  if (i !== props.currentIndex) { emit('update:currentIndex', i); return }
  const item = props.displayItems[i]
  if (item && !item.isOverview) emit('view-company', item.ticker)
}

const cancelSwipe = () => {
  clearLP()
  swipeMode.value = false; dragX.value = 0; isDragging.value = false
  fanVisible.value = true
}
const clearLP = () => {
  if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null }
  longPressingIdx.value = null
}

const onCardDown = (i, e) => {
  if (swipeMode.value) {
    if (i !== props.currentIndex) return
    isDragging.value = true; startX.value = getClientX(e)
    return
  }
  if (i !== props.currentIndex) return
  if (props.displayItems[i]?.isOverview) return
  startX.value = getClientX(e)
  longPressingIdx.value = i
  longPressTimer = setTimeout(() => {
    longPressingIdx.value = null
    swipeMode.value = true; isDragging.value = true; dragX.value = 0
    fanVisible.value = true
  }, LONG_PRESS_MS)
}
const onCardMove = (i, e) => {
  const x = getClientX(e)
  if (longPressingIdx.value !== null) { if (Math.abs(x - startX.value) > 6) clearLP(); return }
  if (!swipeMode.value || !isDragging.value || i !== props.currentIndex) return
  dragX.value = x - startX.value
}
const onCardUp = (i) => {
  clearLP()
  if (!isDragging.value || !swipeMode.value || i !== props.currentIndex) return
  endDrag()
}
const onCardLeave = (i) => {
  if (longPressingIdx.value === i) clearLP()
  if (isDragging.value && i === props.currentIndex) endDrag()
}
const endDrag = () => {
  if (!isDragging.value) return
  isDragging.value = false
  const x = dragX.value
  const si = props.currentIndex - 1
  if (x > THRESHOLD) {
    dragX.value = 500
    setTimeout(() => { emit('replace', si); swipeMode.value = false; dragX.value = 0 }, 280)
  } else if (x < -THRESHOLD) {
    dragX.value = -500
    setTimeout(() => {
      emit('liquidate', si)
      if (props.currentIndex > 1 && props.currentIndex >= props.displayItems.length - 1)
        emit('update:currentIndex', props.currentIndex - 1)
      swipeMode.value = false; dragX.value = 0
    }, 280)
  } else {
    dragX.value = 0
  }
}

onUnmounted(() => clearLP())
</script>

<style scoped>
/* 팬바 배경 제거 — 앱 배경이 그대로 보여 지갑바처럼 구분됨 */
.fan-bar {
  /* background은 :style 바인딩으로 동적 처리 */
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,  .fade-leave-to      { opacity: 0; }

@keyframes warn-pulse {
  0%, 100% {
    box-shadow: inset 0 0 0 1.5px rgba(248,113,113,0.55),
                0 0 10px rgba(248,113,113,0.2);
  }
  50% {
    box-shadow: inset 0 0 0 2.5px rgba(248,113,113,1),
                0 0 22px rgba(248,113,113,0.55);
  }
}
.warn-border {
  animation: warn-pulse 1.6s ease-in-out infinite;
}
</style>
