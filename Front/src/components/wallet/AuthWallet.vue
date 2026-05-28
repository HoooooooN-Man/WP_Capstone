<template>
  <div class="auth-wallet min-h-screen w-full flex items-center justify-center relative font-sans perspective-container px-6 py-4">

    <!-- 배경 -->
    <div class="fixed inset-0 z-[-1] overflow-hidden bg-[#07080b]">
      <div class="absolute w-[90vw] h-[70vh] rounded-full blur-[180px] -top-[25%] -left-[15%] bg-[#1d1306] opacity-75"></div>
      <div class="absolute w-[70vw] h-[60vh] rounded-full blur-[150px] -bottom-[20%] right-0 bg-[#120e04] opacity-55"></div>
      <div class="absolute w-[50vw] h-[50vh] rounded-full blur-[120px] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
           style="background: radial-gradient(circle, rgba(201,162,39,0.06) 0%, transparent 70%)"></div>
    </div>

    <!-- 지갑 래퍼 -->
    <div
      class="relative z-10 w-full max-w-[540px] preserve-3d transition-transform duration-[1200ms] ease-in-out"
      style="height: clamp(380px, 52vh, 440px)"
      :class="{
        'translate-x-1/2': step === 2,
        'translate-x-1/2 translate-y-[120vh]': step >= 3
      }"
    >
      <!-- 지갑 두께감 패널 (우측) -->
      <div class="absolute inset-0 rounded-r-[2rem] overflow-hidden"
           style="background: linear-gradient(180deg, #181108 0%, #0d0a05 50%, #161009 100%);
                  box-shadow: inset -8px 0 28px rgba(0,0,0,0.85);">
        <div class="absolute inset-y-10 right-0 w-px"
             style="background: linear-gradient(180deg, transparent, rgba(201,162,39,0.18) 25%, rgba(201,162,39,0.3) 50%, rgba(201,162,39,0.18) 75%, transparent)"></div>
      </div>

      <!-- 3D 플립 -->
      <div
        class="absolute inset-0 origin-left preserve-3d transition-transform duration-[1200ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
        :class="{'rotate-y-flip': step >= 2}"
      >
        <!-- ── 앞면 ── -->
        <div class="absolute inset-0 backface-hidden rounded-r-[2rem]"
             style="background: linear-gradient(155deg, #1f1509 0%, #140f07 30%, #1b1309 65%, #100d06 100%);
                    box-shadow: 18px 36px 110px -10px rgba(0,0,0,0.98), inset 0 1px 0 rgba(201,162,39,0.09);">

          <!-- 좌측 접힘선 -->
          <div class="absolute left-0 inset-y-0 w-8 pointer-events-none"
               style="background: linear-gradient(to right, rgba(0,0,0,0.5) 0%, rgba(255,255,255,0.025) 60%, transparent 100%)"></div>
          <div class="absolute left-0 inset-y-0 w-[1.5px]" style="background: rgba(0,0,0,0.55)"></div>

          <!-- 상하 골드 엣지 라인 -->
          <div class="absolute top-0 left-6 right-14 h-px"
               style="background: linear-gradient(to right, rgba(201,162,39,0.55) 0%, rgba(201,162,39,0.15) 60%, transparent 100%)"></div>
          <div class="absolute bottom-0 left-6 right-14 h-px"
               style="background: linear-gradient(to right, rgba(201,162,39,0.4) 0%, rgba(201,162,39,0.1) 60%, transparent 100%)"></div>

          <!-- 뷰 컨텐츠 -->
          <div
            class="absolute inset-0 flex items-center justify-center z-20 transition-opacity duration-300 overflow-hidden"
            :class="{'opacity-0 pointer-events-none': step >= 1}"
          >
            <transition name="auth-slide" mode="out-in">
              <AuthLogin  v-if="authView === 'login'"   key="login"   ref="authLoginRef"
                          @go-signup="authView = 'signup'" @go-find="authView = 'find'" />
              <AuthSignup v-else-if="authView === 'signup'" key="signup" @go-login="authView = 'login'" />
              <AuthFind   v-else-if="authView === 'find'"   key="find"   @go-login="authView = 'login'" />
            </transition>
          </div>

          <!-- 스냅 버튼 -->
          <div
            @click="submitLogin"
            class="absolute z-30 cursor-pointer group"
            style="right: -30px; top: 50%; transform: translateY(-50%); transition: opacity 0.3s"
            :class="{'opacity-0 pointer-events-none': step >= 1}"
          >
            <!-- 스트랩 본체 -->
            <div class="relative flex items-center justify-center overflow-hidden"
                 style="width: 78px; height: 78px;
                        border-radius: 50% 14px 14px 50%;
                        background: linear-gradient(135deg, #1d1409 0%, #110e06 100%);
                        box-shadow: -5px 0 18px rgba(0,0,0,0.65), inset 0 1px 0 rgba(255,255,255,0.04);">
              <!-- 우측 단면 그라데이션 -->
              <div class="absolute right-0 top-0 bottom-0 w-5 pointer-events-none"
                   style="background: linear-gradient(to right, transparent 0%, rgba(55,33,8,0.45) 40%, rgba(5,3,1,0.96) 100%)"></div>
              <!-- 골드 단추 -->
              <div
                class="relative z-10 flex items-center justify-center rounded-full transition-transform group-hover:scale-105 active:scale-90"
                :class="{'animate-snap-shake': shakeActive}"
                style="width: 54px; height: 54px;
                       background: linear-gradient(145deg, #edd876 0%, #c9a227 45%, #8a6b10 100%);
                       box-shadow: 0 0 22px rgba(201,162,39,0.24), 0 4px 12px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.22);">
                <LucideLock class="w-[18px] h-[18px]" style="color: #120c02" />
              </div>
            </div>
          </div>
        </div>

        <!-- ── 뒷면 ── -->
        <div class="absolute inset-0 backface-hidden rotate-y-180 rounded-l-[2rem] overflow-hidden"
             style="background: linear-gradient(145deg, #141009 0%, #0d0a05 50%, #181108 100%);
                    box-shadow: inset 2px 0 20px rgba(0,0,0,0.45);">
          <div class="absolute top-0 left-0 right-8 h-px"
               style="background: linear-gradient(to right, transparent, rgba(201,162,39,0.18) 50%, rgba(201,162,39,0.32) 100%)"></div>
          <div class="absolute bottom-0 left-0 right-8 h-px"
               style="background: linear-gradient(to right, transparent, rgba(201,162,39,0.14) 50%, rgba(201,162,39,0.26) 100%)"></div>
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

  const valid = authLoginRef.value?.validate()
  if (!valid) { triggerShake(); return }

  const success = await authLoginRef.value?.login()
  if (!success) { triggerShake(); return }

  step.value = 1
  setTimeout(() => { step.value = 2 }, 300)
  setTimeout(() => { step.value = 3 }, 1700)
}
</script>

<style scoped>
.perspective-container { perspective: 2000px; }
.preserve-3d { transform-style: preserve-3d; }
.backface-hidden { backface-visibility: hidden; }
.origin-left { transform-origin: left center; }
.rotate-y-180 { transform: rotateY(180deg); }
.rotate-y-flip { transform: rotateY(-180deg); }

.auth-slide-enter-active,
.auth-slide-leave-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.auth-slide-enter-from   { opacity: 0; transform: translateX(16px); }
.auth-slide-leave-to     { opacity: 0; transform: translateX(-16px); }

@keyframes snap-shake {
  0%, 100% { transform: translateX(0); }
  15%       { transform: translateX(-6px); }
  30%       { transform: translateX(5px); }
  45%       { transform: translateX(-4px); }
  60%       { transform: translateX(3px); }
  75%       { transform: translateX(-2px); }
}
.animate-snap-shake { animation: snap-shake 0.45s ease-in-out; }
</style>
