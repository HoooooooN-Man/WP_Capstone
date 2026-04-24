<template>
  <div class="p-10 text-center">
    <h1 class="text-2xl font-bold mb-5">뉴스 다이얼로그 테스트</h1>
    
    <button 
      @click="openNewsModal" 
      class="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-blue-700 transition-all shadow-lg"
    >
      상세 모달 열기 (UI 확인용)
    </button>

    <NewsDetailModal 
      :is-open="isModalOpen" 
      :news="selectedNews" 
      @close="isModalOpen = false" 
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
// 1. 파일 경로에 맞춰서 임포트 (상대 경로 확인 필수)
import NewsDetailModal from '@/page/main/news/NewsDetailModal.vue';

// 2. 모달 제어를 위한 상태값
const isModalOpen = ref(false);
const selectedNews = ref({}); // 실제 데이터를 담을 객체

// ---------------------------------------------------------
// [임시 데이터: 리스트에서 클릭했을 때 넘어갈 값 샘플]
// ---------------------------------------------------------
const dummyNews = {
  rank: 1,
  news_id: "real_001",
  title: "실제 연동 시 보여질 뉴스 제목 샘플입니다.",
  publisher: "연합뉴스",
  origin_url: "https://www.yna.co.kr",
  image_url: "https://picsum.photos/seed/post/800/500",
  sentiment_label: "positive",
  sentiment_score: 0.95,
  pos_prob: 0.90,
  neu_prob: 0.08,
  neg_prob: 0.02,
  published_at: "2026-04-22T20:00:00"
};
// ---------------------------------------------------------

const openNewsModal = () => {
  // 나중에 리스트의 v-for 안에서는 openNewsModal(item) 식으로 넘겨주면 됩니다.
  selectedNews.value = dummyNews; 
  isModalOpen.value = true;
};
</script>