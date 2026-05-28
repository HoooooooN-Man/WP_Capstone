<template>
  <div class="flex flex-col w-full max-w-[320px] px-6 gap-3">

    <!-- 헤더 -->
    <div class="flex items-center gap-3">
      <button @click="handleBack"
              class="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center hover:bg-white/10 transition-all flex-shrink-0">
        <LucideChevronLeft class="w-3.5 h-3.5 text-white/60" />
      </button>
      <div>
        <p class="text-[10px] text-[#9a7418] font-bold uppercase tracking-[0.3em]">Account Recovery</p>
        <h2 class="text-base font-black text-white tracking-tight uppercase leading-none">계정 찾기</h2>
      </div>
    </div>

    <!-- 탭 -->
    <div class="flex border-b border-white/10">
      <button @click="tab = 'id'; resetPwState()"
              class="flex-1 pb-2 text-[12px] font-bold tracking-widest uppercase transition-all"
              :class="tab === 'id' ? 'text-[#c9a227] border-b-2 border-[#c9a227] -mb-px' : 'text-white/30 hover:text-white/55'">
        아이디 찾기
      </button>
      <button @click="tab = 'pw'; resetIdState()"
              class="flex-1 pb-2 text-[12px] font-bold tracking-widest uppercase transition-all"
              :class="tab === 'pw' ? 'text-[#c9a227] border-b-2 border-[#c9a227] -mb-px' : 'text-white/30 hover:text-white/55'">
        비밀번호 찾기
      </button>
    </div>

    <!-- ── 아이디 찾기 ── -->
    <div v-if="tab === 'id'" class="space-y-2">
      <input v-model="findName" type="text" placeholder="이름"
        class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
      <input v-model="findPhone" type="text" placeholder="연락처 (010-0000-0000)"
        class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
      <button v-if="!idResult" @click="idResult = true"
              class="w-full py-2.5 bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 rounded-xl text-[11px] font-black text-[#1a0e04] tracking-[0.2em] uppercase hover:brightness-110 active:scale-[0.98] transition-all shadow-[0_4px_12px_rgba(0,0,0,0.4)]">
        아이디 찾기
      </button>
      <div v-else class="px-4 py-3 bg-[#c9a227]/10 border border-[#c9a227]/25 rounded-xl">
        <p class="text-[11px] text-[#c9a227]/60 uppercase tracking-widest mb-1">찾은 아이디</p>
        <p class="text-sm font-bold text-white tracking-wider">user@example.com</p>
        <button @click="emit('go-login'); resetIdState()"
                class="mt-2 text-[11px] text-[#c9a227]/70 hover:text-[#c9a227] transition-colors font-semibold">
          로그인으로 돌아가기 →
        </button>
      </div>
    </div>

    <!-- ── 비밀번호 찾기 ── -->
    <div v-else class="space-y-2">

      <!-- 단계 표시 -->
      <div class="flex items-center gap-2 mb-1">
        <div v-for="s in 3" :key="s"
             class="flex-1 h-0.5 rounded-full transition-colors duration-300"
             :class="pwStep >= s ? 'bg-[#c9a227]/70' : 'bg-white/10'"></div>
      </div>
      <p class="text-[11px] text-white/35 text-center">
        {{ ['이메일 입력', '인증코드 확인', '새 비밀번호 설정'][pwStep - 1] }}
      </p>

      <!-- Step 1: 이메일 입력 -->
      <template v-if="pwStep === 1">
        <input v-model="findEmail" type="text" placeholder="가입한 이메일"
          class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
        <p v-if="pwError" class="text-[11px] text-red-400/80 px-1">{{ pwError }}</p>
        <button @click="handleSendCode" :disabled="pwLoading"
                class="w-full py-2.5 bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 rounded-xl text-[11px] font-black text-[#1a0e04] tracking-[0.2em] uppercase hover:brightness-110 active:scale-[0.98] transition-all shadow-[0_4px_12px_rgba(0,0,0,0.4)] disabled:opacity-60 disabled:cursor-not-allowed">
          {{ pwLoading ? '발송 중...' : '인증코드 발송' }}
        </button>
      </template>

      <!-- Step 2: 인증코드 입력 -->
      <template v-else-if="pwStep === 2">
        <p class="text-[12px] text-white/50 leading-relaxed px-1">
          <span class="text-[#c9a227]/80">{{ findEmail }}</span> 으로<br>발송된 6자리 코드를 입력하세요
        </p>
        <input v-model="verifyCode" type="text" placeholder="인증코드 6자리" maxlength="6"
          class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40 text-center font-mono tracking-[0.5em]" />
        <p v-if="pwError" class="text-[11px] text-red-400/80 px-1">{{ pwError }}</p>
        <button @click="handleVerifyCode" :disabled="pwLoading"
                class="w-full py-2.5 bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 rounded-xl text-[11px] font-black text-[#1a0e04] tracking-[0.2em] uppercase hover:brightness-110 active:scale-[0.98] transition-all shadow-[0_4px_12px_rgba(0,0,0,0.4)] disabled:opacity-60 disabled:cursor-not-allowed">
          {{ pwLoading ? '확인 중...' : '코드 확인' }}
        </button>
        <button @click="pwStep = 1; pwError = ''" class="text-[11px] text-white/30 hover:text-white/50 transition-colors text-center w-full">
          ← 이메일 다시 입력
        </button>
      </template>

      <!-- Step 3: 새 비밀번호 설정 -->
      <template v-else-if="pwStep === 3">
        <input v-model="newPassword" type="password" placeholder="새 비밀번호 (영문+숫자+특수문자 8~24자)"
          class="w-full px-4 py-2.5 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40" />
        <input v-model="newPasswordConfirm" type="password" placeholder="새 비밀번호 확인"
          :class="['w-full px-4 py-2.5 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all focus:border-[#c9a227]/40',
            newPasswordConfirm && newPassword !== newPasswordConfirm ? 'border-red-500/60' : 'border-white/10']" />
        <p v-if="newPasswordConfirm && newPassword !== newPasswordConfirm"
           class="text-[11px] text-red-400/80 px-1">비밀번호가 일치하지 않습니다</p>
        <p v-if="pwError" class="text-[11px] text-red-400/80 px-1">{{ pwError }}</p>
        <button @click="handleResetPw" :disabled="pwLoading || newPassword !== newPasswordConfirm"
                class="w-full py-2.5 bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 rounded-xl text-[11px] font-black text-[#1a0e04] tracking-[0.2em] uppercase hover:brightness-110 active:scale-[0.98] transition-all shadow-[0_4px_12px_rgba(0,0,0,0.4)] disabled:opacity-60 disabled:cursor-not-allowed">
          {{ pwLoading ? '변경 중...' : '비밀번호 변경' }}
        </button>
      </template>

      <!-- 완료 -->
      <div v-else class="px-4 py-3 bg-[#c9a227]/10 border border-[#c9a227]/25 rounded-xl">
        <p class="text-[12px] font-bold text-white mb-1">비밀번호가 변경되었습니다</p>
        <p class="text-[11px] text-white/50 leading-relaxed">새 비밀번호로 로그인해주세요.</p>
        <button @click="emit('go-login'); resetPwState()"
                class="mt-2 text-[11px] text-[#c9a227]/70 hover:text-[#c9a227] transition-colors font-semibold">
          로그인으로 돌아가기 →
        </button>
      </div>

    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { LucideChevronLeft } from 'lucide-vue-next';
import authApi from '@/api/auth.js';

const emit = defineEmits(['go-login']);

// ── 공통 ────────────────────────────────────────────────
const tab = ref('id');

// ── 아이디 찾기 ──────────────────────────────────────────
const findName  = ref('');
const findPhone = ref('');
const idResult  = ref(false);

function resetIdState() { findName.value = ''; findPhone.value = ''; idResult.value = false; }

// ── 비밀번호 찾기 (3단계) ─────────────────────────────────
// Step 1: 이메일 → /auth/check-email
// Step 2: 코드 → /auth/verify-code
// Step 3: 새 비밀번호 → /auth/reset-password-via-email

const pwStep            = ref(1);   // 1 | 2 | 3 | 4(완료)
const findEmail         = ref('');
const verifyCode        = ref('');
const newPassword       = ref('');
const newPasswordConfirm = ref('');
const pwLoading         = ref(false);
const pwError           = ref('');

const PW_RE = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,24}$/

function resetPwState() {
  pwStep.value             = 1;
  findEmail.value          = '';
  verifyCode.value         = '';
  newPassword.value        = '';
  newPasswordConfirm.value = '';
  pwError.value            = '';
  pwLoading.value          = false;
}

function handleBack() {
  if (tab.value === 'pw' && pwStep.value > 1) {
    pwStep.value--;
    pwError.value = '';
  } else {
    emit('go-login');
  }
}

// Step 1: 인증코드 발송
async function handleSendCode() {
  pwError.value = '';
  if (!findEmail.value) { pwError.value = '이메일을 입력해주세요'; return; }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(findEmail.value)) {
    pwError.value = '올바른 이메일 형식을 입력해주세요'; return;
  }
  pwLoading.value = true;
  try {
    await authApi.checkEmail(findEmail.value);
    pwStep.value = 2;
  } catch (err) {
    const status = err.response?.status;
    if (status === 400) pwError.value = '가입되지 않은 이메일입니다';
    else if (status === 429) pwError.value = '요청이 너무 많습니다. 잠시 후 다시 시도해주세요';
    else pwError.value = err.response?.data?.detail ?? '코드 발송에 실패했습니다';
  } finally {
    pwLoading.value = false;
  }
}

// Step 2: 인증코드 확인
async function handleVerifyCode() {
  pwError.value = '';
  if (!verifyCode.value || verifyCode.value.length < 6) {
    pwError.value = '6자리 코드를 입력해주세요'; return;
  }
  pwLoading.value = true;
  try {
    await authApi.verifyCode({ email: findEmail.value, code: verifyCode.value });
    pwStep.value = 3;
  } catch (err) {
    const status = err.response?.status;
    if (status === 400) pwError.value = '인증코드가 틀렸거나 만료되었습니다';
    else pwError.value = err.response?.data?.detail ?? '인증에 실패했습니다';
  } finally {
    pwLoading.value = false;
  }
}

// Step 3: 새 비밀번호 설정
async function handleResetPw() {
  pwError.value = '';
  if (!newPassword.value) { pwError.value = '새 비밀번호를 입력해주세요'; return; }
  if (!PW_RE.test(newPassword.value)) {
    pwError.value = '영문·숫자·특수문자(@$!%*#?&) 포함 8~24자'; return;
  }
  if (newPassword.value !== newPasswordConfirm.value) { pwError.value = '비밀번호가 일치하지 않습니다'; return; }
  pwLoading.value = true;
  try {
    await authApi.resetPasswordViaEmail({
      email:        findEmail.value,
      code:         verifyCode.value,
      new_password: newPassword.value,
    });
    pwStep.value = 4;
  } catch (err) {
    const status = err.response?.status;
    if (status === 400) pwError.value = '인증이 만료되었습니다. 처음부터 다시 시도해주세요';
    else pwError.value = err.response?.data?.detail ?? '비밀번호 변경에 실패했습니다';
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
