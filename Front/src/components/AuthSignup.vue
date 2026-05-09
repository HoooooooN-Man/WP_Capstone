<template>
  <div class="flex flex-col w-full max-w-[320px] px-6 gap-3">

    <!-- 헤더 -->
    <div class="flex items-center gap-3">
      <button @click="emit('go-login')"
              class="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center hover:bg-white/10 transition-all flex-shrink-0">
        <LucideChevronLeft class="w-3.5 h-3.5 text-white/60" />
      </button>
      <div>
        <p class="text-[8px] text-[#9a7418] font-bold uppercase tracking-[0.3em]">New Account</p>
        <h2 class="text-base font-black text-white tracking-tight uppercase leading-none">회원가입</h2>
      </div>
    </div>

    <!-- 입력 -->
    <div class="space-y-2">
      <input v-model="name" type="text" placeholder="이름"
        class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
      <input v-model="email" type="text" placeholder="이메일"
        class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
      <input v-model="pw" type="password" placeholder="비밀번호 (6자 이상)"
        class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
      <div>
        <input v-model="pwConfirm" type="password" placeholder="비밀번호 확인"
          class="w-full px-4 py-2.5 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all"
          :class="pwConfirm && pw !== pwConfirm ? 'border-red-500/60' : 'border-white/10 focus:border-[#c9a227]/40'" />
        <p v-if="pwConfirm && pw !== pwConfirm"
           class="text-[9px] text-red-400/80 flex items-center gap-1 px-1 mt-0.5">
          <LucideAlertCircle class="w-2.5 h-2.5 flex-shrink-0"/>비밀번호가 일치하지 않습니다
        </p>
      </div>
    </div>

    <button class="w-full py-2.5 bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 rounded-xl text-[11px] font-black text-[#1a0e04] tracking-[0.2em] uppercase hover:brightness-110 active:scale-[0.98] transition-all shadow-[0_4px_12px_rgba(0,0,0,0.4)]">
      가입하기
    </button>

    <p class="text-center text-[9px] text-[#7a5c20]/60">
      이미 계정이 있으신가요?
      <button @click="emit('go-login')" class="text-[#c9a227]/70 hover:text-[#c9a227] ml-1 font-semibold transition-colors">로그인</button>
    </p>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { LucideChevronLeft, LucideAlertCircle } from 'lucide-vue-next';

const emit = defineEmits(['go-login']);

const name      = ref('');
const email     = ref('');
const pw        = ref('');
const pwConfirm = ref('');
</script>

<style scoped>
input:focus {
  border-color: rgba(201, 162, 39, 0.4);
  box-shadow: inset 0 0 0 1px rgba(201, 162, 39, 0.08), 0 0 12px rgba(150, 110, 20, 0.12);
}
</style>
