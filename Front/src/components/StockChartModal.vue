<template>
  <div class="absolute inset-0 z-50 flex flex-col justify-end">
    <!-- 딤 배경 -->
    <div class="absolute inset-0 bg-black/72 backdrop-blur-sm rounded-[2rem]" @click="emit('close')"></div>

    <!-- 차트 시트 -->
    <div class="relative flex flex-col rounded-t-[2rem] border-t border-x border-white/12 overflow-hidden"
         style="height: 92%; background: linear-gradient(175deg, #080f1a 0%, #040810 100%)">

      <!-- 핸들 -->
      <div class="flex justify-center pt-2 pb-1 flex-shrink-0">
        <div class="w-8 h-1 rounded-full bg-white/20"></div>
      </div>

      <!-- 헤더 -->
      <div class="px-4 pt-1 pb-2 flex-shrink-0 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="w-1 h-9 rounded-full flex-shrink-0" :style="{ background: company.color }"></div>
          <div>
            <p class="text-[9px] text-white/35 font-mono tracking-wider">{{ company.ticker }} · {{ company.sector }}</p>
            <p class="text-sm font-black text-white leading-tight">{{ company.name }}</p>
          </div>
        </div>
        <div class="text-right">
          <p class="text-base font-black"
             :class="hoveredCandle
               ? (hoveredCandle.close >= hoveredCandle.open ? 'text-green-300' : 'text-red-300')
               : 'text-white'">
            ₩{{ (hoveredCandle?.close ?? company.price).toLocaleString() }}
          </p>
          <p class="text-[11px] font-bold" :class="company.change >= 0 ? 'text-green-400' : 'text-red-400'">
            {{ company.change >= 0 ? '+' : '' }}{{ company.change }}%
          </p>
        </div>
      </div>

      <!-- 기간 탭 -->
      <!-- [TODO] 1일 탭은 분봉 API 연동 후 활성화 예정 -->
      <div class="flex px-3 gap-0.5 mb-1 flex-shrink-0">
        <button v-for="r in RANGES" :key="r.key"
                @click="selectedRange = r.key"
                class="px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all"
                :class="selectedRange === r.key ? 'bg-white/15 text-white' : 'text-white/30 hover:text-white/60'">
          {{ r.label }}
        </button>
      </div>

      <!-- MA 범례 -->
      <div class="flex items-center px-4 mb-0.5 flex-shrink-0">
        <div class="flex items-center gap-1 mr-3">
          <div class="w-4 h-0.5" style="background:#f59e0b"></div>
          <span class="text-[8px] text-[#f59e0b]/60">MA5</span>
        </div>
        <div class="flex items-center gap-1">
          <div class="w-4 h-0.5" style="background:#60a5fa"></div>
          <span class="text-[8px] text-[#60a5fa]/60">MA20</span>
        </div>
        <!-- [API] 실제 주가 데이터 연동 후 이 주석 제거 -->
        <span class="text-[7px] text-white/18 ml-auto">※ 임시 데이터</span>
      </div>

      <!-- ─── 메인 캔들스틱 차트 ─── -->
      <div class="flex-1 min-h-0 px-1 relative">
        <svg
          class="w-full h-full"
          :viewBox="`0 0 ${VW} ${VH}`"
          preserveAspectRatio="none"
          @mousemove="onMouseMove"
          @mouseleave="hoveredIndex = -1"
        >
          <!-- 수평 그리드 -->
          <line v-for="gl in gridLines" :key="'g'+gl.y"
                :x1="PAD_L" :y1="gl.y" :x2="VW - PAD_R" :y2="gl.y"
                stroke="rgba(255,255,255,0.055)" stroke-width="0.5" />

          <!-- 가격 레이블 -->
          <text v-for="gl in gridLines" :key="'t'+gl.y"
                :x="VW - PAD_R + 3" :y="gl.y + 2.5"
                font-size="5.5" fill="rgba(255,255,255,0.28)">
            {{ gl.label }}
          </text>

          <!-- 현재가 점선 -->
          <line :x1="PAD_L" :y1="pyC(company.price)" :x2="VW - PAD_R" :y2="pyC(company.price)"
                stroke="rgba(255,200,50,0.28)" stroke-width="0.8" stroke-dasharray="3,2" />

          <!-- MA20 -->
          <path v-if="ma20Path" :d="ma20Path"
                fill="none" stroke="#60a5fa" stroke-width="1" stroke-linejoin="round" opacity="0.6" />
          <!-- MA5 -->
          <path v-if="ma5Path" :d="ma5Path"
                fill="none" stroke="#f59e0b" stroke-width="1" stroke-linejoin="round" opacity="0.75" />

          <!-- 캔들스틱 -->
          <g v-for="(c, i) in visibleData" :key="i">
            <line :x1="cxMid(i)" :y1="pyC(c.high)"
                  :x2="cxMid(i)" :y2="pyC(Math.max(c.open, c.close))"
                  :stroke="c.close >= c.open ? '#4ade80' : '#f87171'" stroke-width="0.9" />
            <line :x1="cxMid(i)" :y1="pyC(Math.min(c.open, c.close))"
                  :x2="cxMid(i)" :y2="pyC(c.low)"
                  :stroke="c.close >= c.open ? '#4ade80' : '#f87171'" stroke-width="0.9" />
            <rect :x="cxLeft(i)"
                  :y="pyC(Math.max(c.open, c.close))"
                  :width="cw"
                  :height="Math.max(1, Math.abs(pyC(c.open) - pyC(c.close)))"
                  :fill="c.close >= c.open ? '#4ade80' : '#f87171'"
                  :opacity="hoveredIndex === i ? 1 : 0.82" />
          </g>

          <!-- 호버 수직선 -->
          <line v-if="hoveredIndex >= 0"
                :x1="cxMid(hoveredIndex)" :y1="PAD_T"
                :x2="cxMid(hoveredIndex)" :y2="VH - PAD_B"
                stroke="rgba(255,255,255,0.22)" stroke-width="0.7" stroke-dasharray="2,2" />

          <!-- 히트박스 (cursor 스타일용) -->
          <rect :x="PAD_L" :y="PAD_T" :width="CHART_W" :height="CHART_H"
                fill="transparent" class="cursor-crosshair" />
        </svg>

        <!-- OHLCV 툴팁 -->
        <transition name="tip-fade">
          <div v-if="hoveredCandle"
               class="absolute top-1 left-2 bg-[#0a1525]/90 backdrop-blur-sm border border-white/12 rounded-xl px-2.5 py-1.5 pointer-events-none z-10">
            <p class="text-[8px] text-white/35 mb-1 font-mono">{{ hoveredDate }}</p>
            <div class="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[9px]">
              <span class="text-white/40">시가</span>
              <span class="font-bold text-white/90">{{ hoveredCandle.open.toLocaleString() }}</span>
              <span class="text-white/40">고가</span>
              <span class="font-bold text-green-300">{{ hoveredCandle.high.toLocaleString() }}</span>
              <span class="text-white/40">저가</span>
              <span class="font-bold text-red-300">{{ hoveredCandle.low.toLocaleString() }}</span>
              <span class="text-white/40">종가</span>
              <span class="font-bold text-white">{{ hoveredCandle.close.toLocaleString() }}</span>
              <span class="text-white/40">거래량</span>
              <span class="font-bold text-white/55">{{ (hoveredCandle.volume / 10000).toFixed(0) }}만주</span>
            </div>
          </div>
        </transition>
      </div>

      <!-- ─── 거래량 차트 ─── -->
      <div class="flex-shrink-0 px-1" style="height: 34px">
        <svg class="w-full h-full" :viewBox="`0 0 ${VW} 34`" preserveAspectRatio="none">
          <text :x="PAD_L + 2" y="8" font-size="4.5" fill="rgba(255,255,255,0.18)">VOL</text>
          <rect v-for="(c, i) in visibleData" :key="i"
                :x="cxLeft(i)" :y="34 - volH(c.volume)"
                :width="cw" :height="volH(c.volume)"
                :fill="c.close >= c.open ? 'rgba(74,222,128,0.32)' : 'rgba(248,113,113,0.32)'"
                :opacity="hoveredIndex === i ? 1 : 0.75" />
        </svg>
      </div>

      <!-- 날짜 축 -->
      <div class="flex justify-between px-3 pb-3 pt-0.5 flex-shrink-0">
        <span v-for="lbl in dateLabels" :key="lbl" class="text-[8px] text-white/22 font-mono">{{ lbl }}</span>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  company: { type: Object, required: true },
  allData: { type: Array,  required: true }, // generateMockOHLC() 결과 (252 candles)
});
const emit = defineEmits(['close']);

// ── 기간 설정 ─────────────────────────────────
const RANGES = [
  { key: '1W', label: '1주',   days: 5   },
  { key: '1M', label: '1개월', days: 22  },
  { key: '3M', label: '3개월', days: 66  },
  { key: '6M', label: '6개월', days: 130 },
  { key: '1Y', label: '1년',   days: 252 },
];

const selectedRange = ref('3M');
const hoveredIndex  = ref(-1);

// ── SVG viewBox 상수 ──────────────────────────
const VW     = 400;
const VH     = 170;
const PAD_T  = 6;
const PAD_B  = 4;
const PAD_L  = 2;
const PAD_R  = 48;   // 가격 레이블 공간
const CHART_W = VW - PAD_L - PAD_R;  // 350
const CHART_H = VH - PAD_T - PAD_B;  // 160

// ── 데이터 슬라이싱 ───────────────────────────
const visibleDays = computed(() => RANGES.find(r => r.key === selectedRange.value)?.days ?? 66);
const visibleData = computed(() => props.allData.slice(-visibleDays.value));

const priceMin = computed(() => Math.min(...visibleData.value.map(d => d.low))  * 0.997);
const priceMax = computed(() => Math.max(...visibleData.value.map(d => d.high)) * 1.003);
const volMax   = computed(() => Math.max(...visibleData.value.map(d => d.volume)));

// ── 좌표 변환 ─────────────────────────────────
const pyC = (price) => {
  const range = priceMax.value - priceMin.value;
  if (!range) return PAD_T + CHART_H / 2;
  return PAD_T + (1 - (price - priceMin.value) / range) * CHART_H;
};

const n       = computed(() => visibleData.value.length);
const slotW   = computed(() => CHART_W / (n.value || 1));
const cw      = computed(() => Math.max(1.5, slotW.value * 0.7));

const cxLeft = (i) => PAD_L + i * slotW.value + (slotW.value - cw.value) / 2;
const cxMid  = (i) => cxLeft(i) + cw.value / 2;

const volH = (vol) => (vol / (volMax.value || 1)) * 27;

// ── 그리드 & 가격 레이블 ─────────────────────
const fmtPrice = (p) => {
  if (p >= 100000) return (p / 10000).toFixed(0) + '만';
  if (p >= 10000)  return (p / 10000).toFixed(1) + '만';
  return p.toFixed(0);
};

const gridLines = computed(() => {
  const step = (priceMax.value - priceMin.value) / 4;
  return Array.from({ length: 5 }, (_, i) => {
    const price = priceMin.value + step * i;
    return { y: pyC(price), label: fmtPrice(price) };
  });
});

// ── 날짜 레이블 ───────────────────────────────
const dateLabels = computed(() => {
  const data = visibleData.value;
  if (!data.length) return [];
  const picks = [0, 0.25, 0.5, 0.75, 1].map(r => data[Math.round(r * (data.length - 1))]);
  return picks.map(d => {
    if (!d) return '';
    return `${(d.date.getMonth() + 1).toString().padStart(2,'0')}/${d.date.getDate().toString().padStart(2,'0')}`;
  });
});

// ── 이동평균 경로 ─────────────────────────────
const buildMAPath = (period) => {
  const closes = visibleData.value.map(d => d.close);
  let path = '';
  let started = false;
  closes.forEach((_, i) => {
    if (i < period - 1) return;
    const avg = closes.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period;
    const x = cxMid(i), y = pyC(avg);
    path += started ? ` L${x.toFixed(2)},${y.toFixed(2)}` : `M${x.toFixed(2)},${y.toFixed(2)}`;
    started = true;
  });
  return path || null;
};

const ma5Path  = computed(() => buildMAPath(5));
const ma20Path = computed(() => buildMAPath(20));

// ── 호버 ─────────────────────────────────────
const hoveredCandle = computed(() =>
  hoveredIndex.value >= 0 ? visibleData.value[hoveredIndex.value] : null
);
const hoveredDate = computed(() => {
  if (!hoveredCandle.value) return '';
  const d = hoveredCandle.value.date;
  return `${d.getFullYear()}.${d.getMonth()+1}.${d.getDate()}`;
});

const onMouseMove = (e) => {
  const rect = e.currentTarget.getBoundingClientRect();
  const svgX  = ((e.clientX - rect.left) / rect.width) * VW;
  const chartX = svgX - PAD_L;
  const idx = Math.floor(chartX / slotW.value);
  hoveredIndex.value = Math.max(0, Math.min(n.value - 1, idx));
};
</script>

<style scoped>
.tip-fade-enter-active, .tip-fade-leave-active { transition: opacity 0.12s; }
.tip-fade-enter-from, .tip-fade-leave-to { opacity: 0; }
</style>
