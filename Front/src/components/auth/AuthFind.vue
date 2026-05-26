<template>
  <div class="flex flex-col w-full max-w-[320px] px-6 gap-3">

    <!-- 헤더 -->
    <div class="flex items-center gap-3">
      <button @click="emit('go-login')"
              class="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center hover:bg-white/10 transition-all flex-shrink-0">
        <LucideChevronLeft class="w-3.5 h-3.5 text-white/60" />
      </button>
      <div>
        <p class="text-[8px] text-[#9a7418] font-bold uppercase tracking-[0.3em]">Account Recovery</p>
        <h2 class="text-base font-black text-white tracking-tight uppercase leading-none">계정 찾기</h2>
      </div>
    </div>

    <!-- 탭 -->
    <div class="flex border-b border-white/10">
      <button @click="tab = 'id'; result = null"
              class="flex-1 pb-2 text-[10px] font-bold tracking-widest uppercase transition-all"
              :class="tab === 'id' ? 'text-[#c9a227] border-b-2 border-[#c9a227] -mb-px' : 'text-white/30 hover:text-white/55'">
        아이디 찾기
      </button>
      <button @click="tab = 'pw'; result = null"
              class="flex-1 pb-2 text-[10px] font-bold tracking-widest uppercase transition-all"
              :class="tab === 'pw' ? 'text-[#c9a227] border-b-2 border-[#c9a227] -mb-px' : 'text-white/30 hover:text-white/55'">
        비밀번호 찾기
      </button>
    </div>

    <!-- 아이디 찾기 -->
    <div v-if="tab === 'id'" class="space-y-2">
      <input v-model="findName" type="text" placeholder="이름"
        class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
      <input v-model="findPhone" type="text" placeholder="연락처 (010-0000-0000)"
        class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
      <button v-if="!result" @click="result = 'id'"
              class="w-full py-2.5 bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 rounded-xl text-[11px] font-black text-[#1a0e04] tracking-[0.2em] uppercase hover:brightness-110 active:scale-[0.98] transition-all shadow-[0_4px_12px_rgba(0,0,0,0.4)]">
        아이디 찾기
      </button>
      <!-- 임시 결과 -->
      <div v-else class="px-4 py-3 bg-[#c9a227]/10 border border-[#c9a227]/25 rounded-xl">
        <p class="text-[9px] text-[#c9a227]/60 uppercase tracking-widest mb-1">찾은 아이디</p>
        <p class="text-sm font-bold text-white tracking-wider">user@example.com</p>
        <button @click="emit('go-login'); result = null"
                class="mt-2 text-[9px] text-[#c9a227]/70 hover:text-[#c9a227] transition-colors font-semibold">
          로그인으로 돌아가기 →
        </button>
      </div>
    </div>

    <!-- 비밀번호 찾기 -->
    <div v-else class="space-y-2">
      <input v-model="findEmail" type="text" placeholder="가입한 이메일"
        class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
      <p v-if="pwError" class="text-[9px] text-red-400/80 px-1">{{ pwError }}</p>
      <button v-if="!pwResult" @click="handleResetPw" :disabled="pwLoading"
              class="w-full py-2.5 bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 rounded-xl text-[11px] font-black text-[#1a0e04] tracking-[0.2em] uppercase hover:brightness-110 active:scale-[0.98] transition-all shadow-[0_4px_12px_rgba(0,0,0,0.4)] disabled:opacity-60 disabled:cursor-not-allowed">
        {{ pwLoading ? '발송 중...' : '재설정 링크 발송' }}
      </button>
      <div v-else class="px-4 py-3 bg-[#c9a227]/10 border border-[#c9a227]/25 rounded-xl">
        <p class="text-[10px] font-bold text-white mb-1">이메일을 확인하세요</p>
        <p class="text-[9px] text-white/50 leading-relaxed">{{ findEmail }} 으로<br>비밀번호 재설정 링크를 발송했습니다.</p>
        <button @click="emit('go-login'); pwResult = false"
                class="mt-2 text-[9px] text-[#c9a227]/70 hover:text-[#c9a227] transition-colors font-semibold">
          로그인으로 돌아가기 →
        </button>
      </div>
      <p v-if="!pwResult" class="text-[9px] text-[#7a5c20]/50 text-center leading-relaxed">
        가입 시 등록한 이메일로 재설정 링크를 보내드립니다
      </p>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { LucideChevronLeft } from 'lucide-vue-next';
import authApi from '@/api/auth.js';

const emit = defineEmits(['go-login']);

const tab       = ref('id');
const result    = ref(null);
const findName  = ref('');
const findPhone = ref('');
const findEmail = ref('');

// 비밀번호 찾기 상태
const pwLoading = ref(false);
const pwError   = ref('');
const pwResult  = ref(false);

async function handleResetPw() {
  pwError.value = '';
  if (!findEmail.value) { pwError.value = '이메일을 입력해주세요'; return }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(findEmail.value)) {
    pwError.value = '올바른 이메일 형식을 입력해주세요'; return
  }
  pwLoading.value = true;
  try {
    await authApi.resetPasswordViaEmail({ email: findEmail.value });
    pwResult.value = true;
  } catch (err) {
    const status = err.response?.status;
    if (status === 404) pwError.value = '가입되지 않은 이메일입니다';
    else if (status === 429) pwError.value = '요청이 너무 많습니다. 잠시 후 다시 시도해주세요';
    else pwError.value = err.response?.data?.detail ?? '발송에 실패했습니다';
  } finally {
    pwLoading.value = false;
  }
}
</script>

<style scoped>
input:focus {
  border-color: rgba(201, 162, 39, 0.4);
  box-shadow: inset 0 0 0 1px rgba(201, 162, 39, 0.08), 0 0 12px rgba(150, 110, 20, 0.12);
}
</style>
