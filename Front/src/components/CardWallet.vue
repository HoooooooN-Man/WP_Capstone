<template>
  <section class="card-wallet p-4 min-h-screen bg-slate-50">
    <div class="max-w-4xl mx-auto">
      <h2 class="text-2xl font-bold mb-4">AI 투자 전략 시뮬레이터</h2>
      <p class="text-sm text-slate-500 mb-5">스와이프 오른쪽: 매도(Swap) / 왼쪽: 보유</p>

      <Swiper
        :modules="[EffectCards]"
        effect="cards"
        grab-cursor
        :loop="false"
        class="my-swiper h-[28rem] w-72 mx-auto"
        @slideChange="onSlideChange"
        @swiper="onSwiper"
      >
        <SwiperSlide v-for="card in cards" :key="card.id" class="rounded-2xl">
          <InvestmentCard
            :stock-name="card.name"
            :price="card.price"
            :score="card.score"
            :isRisk="card.isRisk"
          />
        </SwiperSlide>
      </Swiper>

      <div class="mt-5 text-center">
        <button @click="swapRight" class="px-4 py-2 bg-blue-600 text-white rounded-md shadow">우측 스와이프 매도</button>
      </div>

      <div class="mt-6 grid grid-cols-2 gap-3 text-xs">
        <div class="p-3 bg-white border rounded-lg shadow-sm">
          <p class="font-semibold">풀에 남은 종목</p>
          <p>{{ pool.length }}개</p>
        </div>
        <div class="p-3 bg-white border rounded-lg shadow-sm">
          <p class="font-semibold">현재 지갑 보유</p>
          <p>{{ cards.length }}개</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Swiper, SwiperSlide } from 'swiper/vue';
import { EffectCards } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/effect-cards';

import InvestmentCard from './InvestmentCard.vue';

const cards = ref(Array.from({ length: 20 }, (_, i) => ({
  id: i + 1,
  name: ['삼성전자', '카카오', 'LG에너지', 'NAVER', '현대차', '셀트리온', 'SK하이닉스', '삼성SDI', '카카오뱅크', '네이버', '롯데케미칼', '네이버', 'LG화학', '포스코', '현대모비스', '기아', '엔씨소프트', '카카오페이', 'SK텔레콤', 'LG전자'][i % 20],
  price: Math.round(30000 + Math.random() * 200000),
  score: Math.round(40 + Math.random() * 60),
  isRisk: Math.random() > 0.7,
}))); 

const pool = ref(Array.from({ length: 20 }, (_, i) => ({
  id: 100 + i + 1,
  name: ['KB금융', '현대제철', 'LG생활건강', 'CJ제일제당', '넷마블', '셀트리온헬스케어', '삼성바이오', '두산퓨얼셀', '대한항공', '아모레퍼시픽', '한미약품', '금호석유', '삼성에스디에스', 'SK이노베이션', '현대글로비스', '에코프로', '영원무역', 'CJ대한통운', '한온시스템', '카카오게임즈'][i % 20],
  price: Math.round(20000 + Math.random() * 180000),
  score: Math.round(35 + Math.random() * 65),
  isRisk: Math.random() > 0.6,
})));

const activeSwiper = ref<any>(null);
const lastIndex = ref(0);

const onSwiper = (swiper: any) => {
  activeSwiper.value = swiper;
  lastIndex.value = swiper.activeIndex;
};

const onSlideChange = (swiper: any) => {
  if (swiper.activeIndex > lastIndex.value) {
    onSwap('right');
  } else if (swiper.activeIndex < lastIndex.value) {
    onSwap('left');
  }
  lastIndex.value = swiper.activeIndex;
};

const swapRight = () => {
  onSwap('right');
};

const onSwap = (direction: 'left' | 'right') => {
  if (direction !== 'right') return;

  if (!cards.value.length) return;

  // 현재 카드 매도 처리
  cards.value.shift();

  // 풀에서 한 종목 추가
  if (pool.value.length) {
    const nextStock = pool.value.shift();
    if (nextStock) {
      cards.value.push(nextStock);
    }
  }
};
</script>

<style scoped>
.card-wallet { min-height: calc(100vh - 2rem); }
.my-swiper .swiper-slide { display: flex; justify-content: center; align-items: center; }
</style>
