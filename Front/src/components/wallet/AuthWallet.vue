<template>
  <div class="auth-wallet min-h-screen w-full flex items-center justify-center relative font-sans perspective-container pl-4 pr-10 py-4">

    <!-- 배경: 다크골드 그라데이션 -->
    <div class="fixed inset-0 z-[-1] overflow-hidden bg-gradient-to-br from-[#0a0804] via-[#060402] to-[#0d0a05]">
      <div class="absolute w-[140vw] h-[80vh] bg-[#2a1e08] rounded-full blur-[160px] -top-[20vh] left-0 opacity-25"></div>
      <div class="absolute w-[100vw] h-[60vh] bg-[#1a1208] rounded-full blur-[120px] -bottom-[10vh] right-0 opacity-20"></div>
      <div class="absolute w-[60vw] h-[60vh] bg-[#3a2a0a] rounded-full blur-[100px] top-[20vh] right-[10vw] opacity-10"></div>
      <div class="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/30"></div>
    </div>

    <!-- 지갑 래퍼 -->
    <div
      class="relative z-10 w-full max-w-[600px] preserve-3d transition-transform duration-[1200ms] ease-in-out"
      style="height: clamp(380px, 55vh, 460px)"
      :class="{
        'translate-x-1/2': step === 2,
        'translate-x-1/2 translate-y-[120vh]': step >= 3
      }"
    >
      <!-- 지갑 두께감 (오른쪽 패널 — 뒷면의 좌우 대칭) -->
      <div class="absolute inset-0 bg-gradient-to-br from-[#2a1a0d] via-[#1e1209] to-[#261608] rounded-r-[2.5rem] shadow-[inset_-10px_0_30px_rgba(0,0,0,0.9)] border border-white/5 overflow-hidden">
        <div class="absolute inset-0 opacity-55 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
        <div class="absolute top-4 right-4 bottom-4 left-0 border-t-2 border-r-2 border-b-2 border-dashed border-[#c9a227]/18 rounded-tr-[2rem] rounded-br-[2rem] pointer-events-none"></div>
      </div>

      <!-- 3D 플립 -->
      <div
        class="absolute inset-0 origin-left preserve-3d transition-transform duration-[1200ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
        :class="{'rotate-y-flip': step >= 2}"
      >
        <!-- ── 앞면 ── -->
        <div class="absolute inset-0 backface-hidden bg-gradient-to-br from-[#3d2616] via-[#2c1a0d] to-[#3a2210] rounded-r-[2.5rem] shadow-[30px_80px_150px_-20px_rgba(0,0,0,0.95)] border-t border-white/5">

          <div class="absolute inset-0 rounded-r-[2.5rem] overflow-hidden pointer-events-none">
            <div class="absolute inset-0 opacity-65 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
            <div class="absolute left-0 inset-y-0 w-8 bg-gradient-to-r from-black/30 via-white/5 to-transparent z-10"></div>
            <div class="absolute left-0 inset-y-0 w-px bg-black/40"></div>
          </div>
          <div class="absolute top-4 right-4 bottom-4 left-0 border-t-2 border-r-2 border-b-2 border-dashed border-[#c9a227]/20 rounded-tr-[2rem] rounded-br-[2rem] pointer-events-none z-20"></div>

          <!-- 뷰 컨텐츠 -->
          <div
            class="absolute inset-0 flex items-center justify-center z-20 transition-opacity duration-300 overflow-hidden"
            :class="{'opacity-0 pointer-events-none': step >= 1}"
          >
            <transition name="auth-slide" mode="out-in">

              <AuthLogin
                v-if="authView === 'login'"
                key="login"
                ref="authLoginRef"
                @go-signup="authView = 'signup'"
                @go-find="authView = 'find'"
              />

              <AuthSignup
                v-else-if="authView === 'signup'"
                key="signup"
                @go-login="authView = 'login'"
              />

              <AuthFind
                v-else-if="authView === 'find'"
                key="find"
                @go-login="authView = 'login'"
              />

            </transition>
          </div>

          <!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
               스냅 스트랩 & 단추 조정 가이드
               ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
               [스트랩 전체 위치] -right-[??px] : 지갑 오른쪽에서 얼마나 튀어나올지
               [스트랩 너비]      w-??          : 스트랩 가로 크기  ← 현재 w-28
               [스트랩 높이]      h-??          : 스트랩 세로 크기  ← 현재 h-24
               [스트랩 좌측 라운드] rounded-l-?? ← 현재 rounded-l-2xl
               [스트랩 우측 라운드] rounded-r-?? ← 현재 rounded-r-lg
               [단추 왼쪽 여백]   ml-??         : 단추의 좌측 위치  ← 현재 ml-2
               [단추 크기]        w-?? h-??     ← 현재 w-16 h-16
               [여닫이 단면 너비]  w-[??px]     ← 현재 20px
               ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
          <div
            @click="submitLogin"
            class="absolute -right-4 top-1/2 -translate-y-1/2 z-30 cursor-pointer group transition-opacity duration-300"
            :class="{'opacity-0 pointer-events-none': step >= 1}"
          >
            <div class="relative w-25 h-24 bg-[#2c1a0e] border-y border-l border-white/10 rounded-l-2xl rounded-r-lg shadow-[-10px_10px_20px_rgba(0,0,0,0.6)] overflow-hidden flex items-center">
              <!-- 가죽 질감 -->
              <div class="absolute inset-0 opacity-40 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>

              <!-- 오른쪽 여닫이 단면 그라데이션 -->
              <div class="absolute right-0 top-0 bottom-0 w-[20px] pointer-events-none"
                   style="background: linear-gradient(to right,
                     transparent          0%,
                     rgba(50,28,10,0.35) 20%,
                     rgba(95,52,18,0.60) 46%,
                     rgba(30,15,5,0.88)  74%,
                     rgba(4,2,1,1)      100%)">
              </div>

              <!-- 스냅 단추 — ml-?? 로 좌우 위치 조정 / 현재 왼쪽에 붙임(ml-2) -->
              <div class="relative w-16 h-16 ml-2 rounded-full bg-gradient-to-br from-[#e0c96a] to-[#a87820] border-4 border-[#2c1a0e] shadow-[0_0_20px_rgba(180,140,40,0.3)] flex items-center justify-center active:scale-90 transition-transform group-hover:brightness-110"
                   :class="{'animate-snap-shake': shakeActive}">
                <LucideLock class="w-6 h-6 text-[#1a0e04]" />
              </div>
            </div>
          </div>
        </div>

        <!-- ── 뒷면 ── -->
        <div class="absolute inset-0 backface-hidden rotate-y-180 bg-gradient-to-br from-[#2a1a0d] via-[#1e1209] to-[#261608] rounded-l-[2.5rem] shadow-inner border-t border-b border-l border-white/5 overflow-hidden">
          <div class="absolute inset-0 opacity-55 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
          <div class="absolute top-4 left-4 bottom-4 right-0 border-t-2 border-l-2 border-b-2 border-dashed border-[#c9a227]/18 rounded-tl-[2rem] rounded-bl-[2rem] pointer-events-none"></div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { LucideLock } from 'lucide-vue-next'
import AuthLogin  from '@/components/auth/AuthLogin.vue'
import AuthSignup from '@/components/auth/AuthSignup.vue'
import AuthFind   from '@/components/auth/AuthFind.vue'

const authView     = ref('login')
const step         = ref(0)
const shakeActive  = ref(false)
const authLoginRef = ref(null)

const triggerShake = () => {
  shakeActive.value = true
  setTimeout(() => { shakeActive.value = false }, 500)
}

const submitLogin = async () => {
  if (step.value !== 0 || authView.value !== 'login') return

  // 1. 폼 유효성 검사
  const valid = authLoginRef.value?.validate()
  if (!valid) { triggerShake(); return }

  // 2. 실제 API 로그인 (authStore.login() 내부에서 호출됨)
  const success = await authLoginRef.value?.login()
  if (!success) { triggerShake(); return }

  // 3. 성공 → 지갑 닫기 애니메이션
  // authStore.isLoggedIn = true가 되었으므로 App.vue가 자동 전환하기 전에 애니메이션
  step.value = 1
  setTimeout(() => { step.value = 2 }, 300)
  setTimeout(() => { step.value = 3 }, 1700)
  // App.vue는 authStore.isLoggedIn을 감시하여 CardWallet으로 자동 전환
}
</script>

<style scoped>
.perspective-container { perspective: 2000px; }
.preserve-3d { transform-style: preserve-3d; }
.backface-hidden { backface-visibility: hidden; }
.origin-left { transform-origin: left center; }
.rotate-y-180 { transform: rotateY(180deg); }
.rotate-y-flip { transform: rotateY(-180deg); }

/* 뷰 전환 슬라이드 */
.auth-slide-enter-active,
.auth-slide-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.auth-slide-enter-from   { opacity: 0; transform: translateX(18px); }
.auth-slide-leave-to     { opacity: 0; transform: translateX(-18px); }

/* 스냅 버튼만 흔들리는 애니메이션 */
@keyframes snap-shake {
  0%, 100% { transform: translateX(0);    }
  15%       { transform: translateX(-6px); }
  30%       { transform: translateX(5px);  }
  45%       { transform: translateX(-4px); }
  60%       { transform: translateX(3px);  }
  75%       { transform: translateX(-2px); }
}
.animate-snap-shake {
  animation: snap-shake 0.45s ease-in-out;
}
</style>
