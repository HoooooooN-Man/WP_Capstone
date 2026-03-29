<template>
  <div class="login-container" :class="{ 'is-unlocked': authState !== 'locked' }">
    <div class="overlay"></div>

    <Transition name="fade-out">
      <div v-if="authState === 'locked'" class="lock-screen">
        
        <div class="leather-wallet">
          <div class="wallet-texture"></div>
          
          <div class="auth-screen">
            <h1 class="project-name">Wallet<br/>Protector</h1>
            <p class="instruction">자산 보호를 위해 UNLOCK 하세요.</p>
            <div class="auth-form">
              <input type="text" placeholder="ID" class="input-field" />
              <input type="password" placeholder="Password" class="input-field" />
              <button @click="handleLogin" class="login-btn">LOGIN</button>
            </div>
          </div>
          
          <div class="wallet-clasp" :class="{ 'unclasping': authState === 'unlocking' }">
            <span class="clasp-icon">🔒</span>
          </div>
        </div>
      </div>
    </Transition>

    <Transition name="id-card-drop">
      <div v-if="authState === 'unlocking' || authState === 'unlocked'" class="unlocked-screen">
        <IdCardVisual :user-info="user" @animation-finished="authState = 'unlocked'" />
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import IdCardVisual from './IdCardVisual.vue';

const authState = ref('locked');
const isUnlocked = ref(false); // 배경 전환용
const user = reactive({ nickname: '주진우', email: 'jinwoo@example.com' });

const handleLogin = () => {
  // 버튼 클릭 시 애니메이션 상태로 전환 (자물쇠 풀리는 시각 효과)
  authState.value = 'unlocking';
  // 배경색 밝게 변경 시작
  isUnlocked.value = true;
};
</script>

<style scoped>
.login-container {
  position: relative; width: 100vw; height: 100vh; display: flex;
  justify-content: center; align-items: center; overflow: hidden;
  background: #111; transition: background 1.5s ease; /* 잠금 시 매우 어둡게 */
}
.is-unlocked { background: #d0e1f9; } /* 해제 시 밝은 배경 */

.overlay { position: absolute; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1; }
.lock-screen { position: relative; z-index: 10; text-align: center; color: white; display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; }

/* --- 가죽 지갑 컨테이너 스타일 --- */
.leather-wallet {
  position: relative;
  width: 500px; height: 350px;
  background: #6f4e37; /* 가죽 갈색 */
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  display: flex; justify-content: center; align-items: center;
  overflow: hidden; /* 내부 스크린이 넘치지 않게 */
  border: 4px solid #5a3f2c; /* 테두리 */
}

/* 나중에 가죽 질감 이미지를 src/assets/leather-texture.jpg에 넣으면 교체하세요 */
.wallet-texture {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  background: linear-gradient(135deg, #7b5840 0%, #6f4e37 50%, #5a3f2c 100%);
  opacity: 0.8; z-index: 2;
}

/* 지갑 내부 내장 스크린 */
.auth-screen {
  position: relative; z-index: 5;
  width: 320px; height: 280px;
  background: rgba(0,0,0,0.7); /* 어두운 화면 느낌 */
  border-radius: 10px; border: 2px solid #aaa;
  padding: 20px; display: flex; flex-direction: column; justify-content: center;
}

.project-name { font-size: 2rem; margin: 0 0 10px 0; color: #ffeb3b; text-transform: uppercase; letter-spacing: 2px; }
.instruction { font-size: 0.8rem; opacity: 0.8; margin-bottom: 20px; }

.auth-form { display: flex; flex-direction: column; gap: 8px; width: 250px; margin: 0 auto; }
.input-field { padding: 10px; border-radius: 5px; border: none; background: rgba(255,255,255,0.2); color: white; }
.input-field::placeholder { color: #ccc; }
.login-btn { padding: 10px; background: #e67e22; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin-top: 10px; transition: transform 0.2s; }
.login-btn:hover { transform: scale(1.05); }

/* --- 지갑 오른편 열리는 부분 & 자물쇠 --- */
.wallet-clasp {
  position: absolute; top: 50%; right: 0; transform: translateY(-50%);
  width: 80px; height: 120px;
  background: #5a3f2c; /* 지갑보다 진한 갈색 */
  border-radius: 10px 0 0 10px;
  display: flex; justify-content: center; align-items: center;
  z-index: 3; transition: all 1s ease; /* 자물쇠 풀리는 애니메이션 시간 */
}
.clasp-icon { font-size: 2.5rem; transition: transform 0.8s ease; }

/* 자물쇠 풀리는 효과 CSS */
.unclasping { transform: translateY(-50%) translateX(100%); opacity: 0; } /* 우측으로 사라짐 */
.unclasping .clasp-icon { transform: rotate(-90deg); } /* 자물쇠가 돌아가는 느낌 */

/* 신분증 화면 */
.unlocked-screen { position: relative; z-index: 20; width: 100vw; height: 100vh; }

/* --- 애니메이션 정의 (CSS Transitions) --- */
.fade-out-leave-active { transition: opacity 0.8s; }
.fade-out-leave-to { opacity: 0; }
.id-card-drop-enter-active { transition: all 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.id-card-drop-enter-from { opacity: 0; transform: translate(-50%, -1000px) rotate(20deg); }
</style>