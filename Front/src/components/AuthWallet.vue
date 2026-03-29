<template>
  <div class="auth-wallet min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-900 via-indigo-950 to-slate-900 text-white p-4">
    <div class="bifold-wallet relative w-[520px] h-[320px] rounded-3xl shadow-2xl border border-slate-700 overflow-hidden transition-all duration-700" :class="{'scale-105': isHolding}">
      <div class="w-full h-full absolute inset-0 bg-gradient-to-r from-indigo-800 via-slate-900 to-indigo-900 opacity-90"></div>
      <div class="relative z-10 flex flex-col items-center justify-center h-full gap-4 p-6">
        <div class="text-center">
          <LucideLock class="mx-auto text-6xl text-yellow-300" />
          <h1 class="mt-3 text-2xl font-extrabold tracking-tight">The Smart Wallet</h1>
          <p class="mt-1 text-sm text-slate-300">과거 투자 전략 시뮬레이션에 오신 것을 환영합니다.</p>
        </div>

        <form @submit.prevent="submitLogin" class="w-full max-w-md grid gap-3">
          <input v-model="email" type="email" placeholder="Email" required class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-600 focus:border-cyan-400 outline-none" />
          <input v-model="password" type="password" placeholder="Password" required class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-600 focus:border-cyan-400 outline-none" />
          <button type="submit" class="w-full py-2 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-600 text-slate-900 font-bold">로그인</button>
        </form>

        <div class="w-full max-w-md flex gap-3 justify-center">
          <button class="flex-1 py-2 rounded-xl bg-white/10 border border-slate-500 hover:bg-white/20 transition">Google</button>
          <button class="flex-1 py-2 rounded-xl bg-white/10 border border-slate-500 hover:bg-white/20 transition">GitHub</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { LucideLock } from 'lucide-vue-next';

const emit = defineEmits(['login']);

const email = ref('');
const password = ref('');
const isHolding = ref(false);

const submitLogin = () => {
  isHolding.value = true;

  setTimeout(() => {
    emit('login', {
      name: '진우',
      style: '보수형',
      totalAsset: '12,500,000원',
    });
  }, 550);
};
</script>

<style scoped>
@keyframes wallet-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.04); }
  100% { transform: scale(1); }
}

.bifold-wallet:hover { animation: wallet-pulse 1.2s ease-in-out infinite; }
</style>