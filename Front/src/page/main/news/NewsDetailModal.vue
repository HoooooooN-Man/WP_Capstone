<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
    @click.self="$emit('close')"
  >
    <div class="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl transition-all">
      
      <div class="relative h-72 w-full bg-gray-200">
        <img 
          :src="newsData.image_url || 'https://via.placeholder.com/600x400?text=No+Image'" 
          class="h-full w-full object-cover"
          @error="(e) => e.target.src = 'https://via.placeholder.com/600x400?text=Image+Load+Error'"
        />
        <button 
          @click="$emit('close')" 
          class="absolute top-4 right-4 p-2 bg-black/30 hover:bg-black/50 text-white rounded-full transition-all"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="p-8">
        <div class="flex flex-wrap items-center gap-3 mb-5">
          <span class="px-3 py-1 rounded-md bg-blue-600 text-white text-xs font-bold">
            RANK {{ newsData.rank }}
          </span>
          <span class="text-sm font-bold text-gray-700">{{ newsData.publisher }}</span>
          <span class="text-gray-300">|</span>
          <span class="text-sm text-gray-500">{{ formatDateTime(newsData.published_at) }}</span>
        </div>

        <h2 class="text-2xl font-extrabold text-gray-900 leading-tight mb-8">
          {{ newsData.title }}
        </h2>

        <div class="bg-slate-50 border border-slate-100 rounded-2xl p-6 mb-8">
          <div class="flex items-center justify-between mb-5">
            <div class="flex items-center gap-2">
              <span class="text-lg">🤖</span>
              <h3 class="text-sm font-bold text-slate-800">AI 감성 분석 결과</h3>
            </div>
            <div 
              class="px-3 py-1 rounded-lg text-xs font-black uppercase shadow-sm"
              :class="sentimentBadgeClass"
            >
              {{ newsData.sentiment_label }}
            </div>
          </div>

          <div class="relative w-full h-5 bg-gray-200 rounded-full overflow-hidden flex shadow-inner">
            <div 
              :style="{ width: (newsData.pos_prob * 100) + '%' }" 
              class="bg-emerald-500 h-full transition-all duration-1000 ease-out"
            ></div>
            <div 
              :style="{ width: (newsData.neu_prob * 100) + '%' }" 
              class="bg-slate-400 h-full transition-all duration-1000 ease-out"
            ></div>
            <div 
              :style="{ width: (newsData.neg_prob * 100) + '%' }" 
              class="bg-rose-500 h-full transition-all duration-1000 ease-out"
            ></div>
          </div>
          
          <div class="grid grid-cols-3 mt-4 text-[12px] font-bold">
            <div class="text-emerald-600 text-left">Positive {{ (newsData.pos_prob * 100).toFixed(1) }}%</div>
            <div class="text-slate-500 text-center">Neutral {{ (newsData.neu_prob * 100).toFixed(1) }}%</div>
            <div class="text-rose-600 text-right">Negative {{ (newsData.neg_prob * 100).toFixed(1) }}%</div>
          </div>
        </div>

        <div class="flex flex-col gap-3">
          <a 
            :href="newsData.origin_url" 
            target="_blank" 
            class="w-full bg-slate-900 hover:bg-blue-700 text-white text-center py-4 rounded-xl font-bold transition-all shadow-lg active:scale-[0.98]"
          >
            기사 원문 읽기
          </a>
          <p class="text-center text-[11px] text-gray-400">
            원문 기사로 이동하여 상세 내용을 확인하실 수 있습니다.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';

const props = defineProps({
  isOpen: Boolean,
  news: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['close']);

// ---------------------------------------------------------
// [임시 데이터: UI 확인용]
// ---------------------------------------------------------
const mockData = {
  rank: 1,
  news_id: "tmp_001",
  title: "임시 데이터입니다: AI 반도체 시장의 새로운 패러다임 변화",
  publisher: "경제포커스",
  origin_url: "https://google.com",
  image_url: "https://picsum.photos/800/500",
  sentiment_label: "positive",
  sentiment_score: 0.92,
  pos_prob: 0.82,
  neu_prob: 0.13,
  neg_prob: 0.05,
  published_at: "2026-04-22T14:00:00"
};
// ---------------------------------------------------------

// 실제 데이터가 없으면 임시 데이터를 사용하도록 설정
const newsData = computed(() => {
  return (props.news && Object.keys(props.news).length > 0) ? props.news : mockData;
});

// [임시 연결 주석: 실제 백엔드 연동 시 참고]
/*
import axios from 'axios';

const fetchNewsDetail = async (newsId) => {
  try {
    const res = await axios.get(`/api/news/detail/${newsId}`);
    // state 업데이트 로직
  } catch (err) {
    console.error("Failed to load news detail", err);
  }
};
*/

// 감성 라벨에 따른 배지 색상 계산
const sentimentBadgeClass = computed(() => {
  const label = newsData.value.sentiment_label;
  if (label === 'positive') return 'bg-emerald-100 text-emerald-700 border border-emerald-200';
  if (label === 'negative') return 'bg-rose-100 text-rose-700 border border-rose-200';
  return 'bg-slate-100 text-slate-700 border border-slate-200';
});

// 날짜 포맷 함수
const formatDateTime = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};
</script>

<style scoped>
/* 부드러운 모달 애니메이션을 위한 커스텀 스타일 */
.transition-all {
  transition-duration: 300ms;
}
</style>