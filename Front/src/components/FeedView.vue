<template>
  <div class="w-full h-full bg-gradient-to-br from-[#1a1f1a] to-[#0e120e] rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden animate-drop-in border border-white/10 text-white">

    <!-- 헤더 -->
    <div class="px-6 pt-5 pb-3 border-b border-white/10 flex-shrink-0 flex items-center justify-between">
      <div>
        <p class="text-[9px] text-white/40 uppercase tracking-widest mb-0.5">Market Intelligence</p>
        <h2 class="text-3xl font-black tracking-tighter uppercase">Latest Feed</h2>
      </div>
      <div class="px-2.5 py-1 bg-green-500/20 rounded-full border border-green-500/40">
        <span class="text-[10px] text-green-300 font-bold uppercase tracking-wider">LIVE</span>
      </div>
    </div>

    <!-- 피드 리스트 -->
    <div class="flex-1 overflow-y-auto px-4 py-3 space-y-2">
      <div
        v-for="item in feeds" :key="item.id"
        class="p-3 rounded-xl bg-white/5 border border-white/8 hover:bg-white/8 transition-colors"
      >
        <div class="flex items-start justify-between gap-3 mb-1">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="badge" :class="categoryColor(item.category)">{{ item.category }}</span>
            <span v-if="item.ticker" class="text-[9px] text-white/30 font-mono">{{ item.ticker }}</span>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-[10px] font-bold" :class="item.change >= 0 ? 'text-green-400' : 'text-red-400'">
              {{ item.change >= 0 ? '+' : '' }}{{ item.change }}%
            </span>
            <span class="text-[9px] text-white/25">{{ item.time }}</span>
          </div>
        </div>
        <p class="text-sm font-bold leading-snug">{{ item.title }}</p>
        <p class="text-[10px] text-white/45 mt-0.5 leading-snug">{{ item.body }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
// TODO: 아래 mock import를 실제 API 호출(pinia store 등)로 교체
import { MOCK_FEEDS } from '@/mock/data.js';

// TODO: [API] GET /api/feed?limit=20 로 교체
const feeds = MOCK_FEEDS;

const categoryColor = (cat) => ({
  EARNINGS: 'badge-gold',
  NEWS:     'badge-green',
  TECH:     'badge-green',
  MARKET:   'bg-blue-500/20 text-blue-300 border border-blue-500/35',
}[cat] ?? 'badge-gold');
</script>

<style scoped>
.animate-drop-in { animation: drop-in 0.7s var(--ease-wallet) forwards; }
</style>
