<template>
  <div class="flex flex-col items-center gap-4 w-full max-w-[320px] px-6">

    <div class="text-center w-full">
      <h1 class="font-black text-white tracking-tighter uppercase italic leading-none"
          style="font-size: clamp(24px, 5vw, 38px); text-shadow: 0 2px 30px rgba(0,0,0,0.9), 0 0 50px rgba(100,75,15,0.25)"
      >WALLET PROTECTOR</h1>
      <div class="h-px w-16 bg-gradient-to-r from-transparent via-[#c9a227]/55 to-transparent mt-2.5 mx-auto"></div>
      <p class="text-[8px] text-[#9a7418] font-bold uppercase tracking-[0.35em] mt-1.5">Advanced Security Access</p>
    </div>

    <form @submit.prevent class="w-full space-y-1.5">
      <div>
        <input v-model="email" type="text" placeholder="EMAIL ADDRESS"
          @input="emailTouched = true" @blur="emailTouched = true"
          class="w-full px-4 py-3 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.18em] shadow-inner transition-all"
          :class="emailError ? 'border-red-500/60' : (email && !emailError ? 'border-green-500/40' : 'border-white/10')" />
        <div class="min-h-[14px] mt-0.5 px-1">
          <p v-if="emailError" class="text-[9px] text-red-400/80 flex items-center gap-1">
            <LucideAlertCircle class="w-2.5 h-2.5 flex-shrink-0"/>{{ emailError }}
          </p>
          <p v-else-if="email && !email.includes('@')" class="text-[9px] text-[#c9a227]/70 flex items-center gap-1">
            <LucideInfo class="w-2.5 h-2.5 flex-shrink-0"/>이메일에는 @ 가 필요합니다
          </p>
        </div>
      </div>
      <div>
        <input v-model="password" type="password" placeholder="PASSWORD"
          @blur="passwordTouched = true"
          class="w-full px-4 py-3 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.18em] shadow-inner transition-all"
          :class="passwordError ? 'border-red-500/60' : (password && !passwordError ? 'border-green-500/40' : 'border-white/10')" />
        <div class="min-h-[14px] mt-0.5 px-1">
          <p v-if="passwordError" class="text-[9px] text-red-400/80 flex items-center gap-1">
            <LucideAlertCircle class="w-2.5 h-2.5 flex-shrink-0"/>{{ passwordError }}
          </p>
        </div>
      </div>
    </form>

    <!-- 소셜 로그인 -->
    <div class="flex flex-col items-center w-full">
      <div class="flex items-center gap-3 mb-2.5 w-full">
        <div class="flex-1 h-px bg-gradient-to-r from-transparent to-white/10"></div>
        <span class="text-[8px] text-[#7a5c20]/70 uppercase tracking-[0.3em] font-semibold">or</span>
        <div class="flex-1 h-px bg-gradient-to-l from-transparent to-white/10"></div>
      </div>
      <div class="flex gap-3">
        <button type="button" class="w-9 h-9 rounded-full bg-black/40 border border-white/10 flex items-center justify-center hover:border-[#c9a227]/30 hover:bg-black/60 transition-all">
          <img src="https://www.gstatic.com/images/branding/product/2x/googleg_48dp.png" class="w-[15px] h-[15px]" />
        </button>
        <button type="button" class="w-9 h-9 rounded-full bg-black/40 border border-white/10 flex items-center justify-center hover:border-[#c9a227]/30 hover:bg-black/60 transition-all">
          <svg viewBox="0 0 24 24" fill="#03C75A" class="w-[15px] h-[15px]"><path d="M15.5 12.4L8.5 3H6v18h3.5V8.6L16.5 18H19V3h-3.5z"/></svg>
        </button>
        <button type="button" class="w-9 h-9 rounded-full bg-black/40 border border-white/10 flex items-center justify-center hover:border-[#c9a227]/30 hover:bg-black/60 transition-all">
          <svg viewBox="0 0 24 24" fill="#FEE500" class="w-[16px] h-[16px]"><path d="M12 3.5C6.75 3.5 2.5 7.05 2.5 11.45c0 2.76 1.8 5.2 4.54 6.64l-.96 3.97 4.28-2.6c.51.07 1.05.11 1.64.11 5.25 0 9.5-3.55 9.5-7.95S17.25 3.5 12 3.5z"/></svg>
        </button>
      </div>
    </div>

    <!-- 하단 링크 -->
    <div class="flex items-center gap-3">
      <button @click="emit('go-signup')"
              class="text-[9px] text-[#7a5c20]/70 hover:text-[#c9a227]/80 transition-colors uppercase tracking-widest font-semibold">
        회원가입
      </button>
      <span class="w-px h-3 bg-white/15 flex-shrink-0"></span>
      <button @click="emit('go-find')"
              class="text-[9px] text-[#7a5c20]/70 hover:text-[#c9a227]/80 transition-colors uppercase tracking-widest font-semibold">
        아이디 / 비밀번호 찾기
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { LucideAlertCircle, LucideInfo } from 'lucide-vue-next';

const emit = defineEmits(['go-signup', 'go-find']);

const email    = ref('');
const password = ref('');
const emailTouched    = ref(false);
const passwordTouched = ref(false);

const emailError = computed(() => {
  if (!emailTouched.value) return null;
  if (!email.value)               return '이메일을 입력해주세요';
  if (!email.value.includes('@'))  return '이메일 형식이 올바르지 않습니다 (@ 필요)';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value))
                                   return '올바른 이메일 형식을 입력해주세요';
  return null;
});

const passwordError = computed(() => {
  if (!passwordTouched.value)       return null;
  if (!password.value)              return '비밀번호를 입력해주세요';
  if (password.value.length < 6)   return '비밀번호는 6자 이상이어야 합니다';
  return null;
});

const isFormValid = computed(() =>
  email.value && password.value &&
  !emailError.value && !passwordError.value &&
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value) &&
  password.value.length >= 6
);

defineExpose({
  validate() {
    emailTouched.value    = true;
    passwordTouched.value = true;
    return isFormValid.value;
  },
  getCredentials() {
    return { email: email.value, password: password.value };
  },
});
</script>

<style scoped>
input:focus {
  border-color: rgba(201, 162, 39, 0.4);
  box-shadow: inset 0 0 0 1px rgba(201, 162, 39, 0.08), 0 0 12px rgba(150, 110, 20, 0.12);
}
</style>
