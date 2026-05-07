<template>
  <div class="w-full h-full bg-gradient-to-br from-[#1f3756] to-[#14253a] rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.6)] flex flex-col overflow-hidden animate-drop-in border border-white/10 text-white">

    <!-- 헤더 -->
    <div class="px-6 pt-5 pb-3 border-b border-white/15 flex-shrink-0">
      <div class="flex items-center gap-3">
        <h2 class="text-3xl font-black tracking-tighter uppercase">Company List</h2>
        <div v-if="replaceMode" class="px-2.5 py-1 bg-emerald-500/25 rounded-full border border-emerald-500/40">
          <span class="text-[10px] text-emerald-300 font-bold uppercase tracking-wider">교체 선택 중</span>
        </div>
      </div>
      <p v-if="replaceMode" class="text-[10px] text-white/35 mt-1">교체할 종목을 선택하세요</p>
    </div>

    <!-- 기업 리스트 -->
    <div class="flex-1 overflow-y-auto px-4 py-3 space-y-2">
      <div
        v-for="company in companies" :key="company.id"
        class="flex items-center gap-3 p-3 rounded-xl border border-white/5 transition-all duration-200"
        :class="replaceMode
          ? 'bg-white/5 hover:bg-white/10 cursor-pointer hover:border-emerald-500/30'
          : 'bg-white/5'"
        @click="replaceMode && selectCompany(company)"
      >
        <!-- 색상 인디케이터 -->
        <div class="w-1 h-10 rounded-full flex-shrink-0" :style="{ background: company.color }"></div>

        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <p class="font-bold text-sm truncate">{{ company.name }}</p>
            <span class="text-[9px] text-white/35 font-mono flex-shrink-0">{{ company.ticker }}</span>
          </div>
          <p class="text-[9px] text-white/40">{{ company.sector }}</p>
        </div>

        <div class="text-right flex-shrink-0">
          <p class="text-sm font-bold">₩{{ company.price.toLocaleString() }}</p>
          <p class="text-[10px] font-semibold"
            :class="company.change >= 0 ? 'text-green-400' : 'text-red-400'">
            {{ company.change >= 0 ? '+' : '' }}{{ company.change }}%
          </p>
        </div>

        <div v-if="replaceMode" class="w-7 h-7 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center flex-shrink-0">
          <LucidePlus class="w-3.5 h-3.5 text-emerald-400" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { LucidePlus } from 'lucide-vue-next';

const props = defineProps({
  replaceMode: { type: Boolean, default: false }
});
const emit = defineEmits(['select-company']);

const companies = [
  { id: 1,  name: '삼성전자',      ticker: '005930', sector: '반도체',   price: 72400,   change:  6.47, color: '#1428A0' },
  { id: 2,  name: 'SK하이닉스',   ticker: '000660', sector: '반도체',   price: 158000,  change:  8.97, color: '#BE0000' },
  { id: 3,  name: 'NAVER',         ticker: '035420', sector: '인터넷',   price: 172000,  change: -4.44, color: '#03C75A' },
  { id: 4,  name: 'Kakao',         ticker: '035720', sector: '인터넷',   price: 48500,   change: -6.73, color: '#F9E000' },
  { id: 5,  name: 'LG에너지솔루션',ticker: '373220', sector: '배터리',   price: 380000,  change: -9.52, color: '#A50034' },
  { id: 6,  name: '현대차',         ticker: '005380', sector: '자동차',   price: 215000,  change:  2.14, color: '#002C5F' },
  { id: 7,  name: 'POSCO홀딩스',   ticker: '005490', sector: '철강',     price: 310000,  change:  1.32, color: '#6699CC' },
  { id: 8,  name: '셀트리온',       ticker: '068270', sector: '바이오',   price: 148500,  change:  3.88, color: '#00A651' },
  { id: 9,  name: 'KB금융',         ticker: '105560', sector: '금융',     price: 68000,   change:  0.74, color: '#FFBC00' },
  { id: 10, name: '삼성바이오로직스', ticker: '207940', sector: '바이오', price: 820000,  change:  1.23, color: '#0068B7' },
];

const selectCompany = (company) => {
  emit('select-company', {
    id: Date.now(),
    company: company.name,
    ticker: company.ticker,
    sector: company.sector,
    shares: 10,
    avgPrice: company.price,
    currentPrice: company.price,
    change: company.change,
    color: company.color,
    weight: 10
  });
};
</script>

<style scoped>
.animate-drop-in { animation: drop-in 0.7s var(--ease-wallet) forwards; }
</style>
