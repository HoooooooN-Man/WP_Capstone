<template>
  <!-- 로그인 컨테이너: 잠금 상태에 따라 배경색 변경 -->
  <div class="login-container" :class="{ 'is-unlocked': authState !== 'locked' }">
    <!-- 배경 오버레이 -->
    <div class="overlay"></div>

    <!-- 잠금 화면 애니메이션 전환 -->
    <Transition name="fade-out">
      <div v-if="authState === 'locked'" class="lock-screen">
        
        <!-- 가죽 지갑 UI 디자인 -->
        <div class="leather-wallet">
          <!-- 지갑 텍스처 배경 -->
          <div class="wallet-texture"></div>
          
          <!-- 지갑 내부 인증 화면 -->
          <div class="auth-screen">
            <h1 class="project-name">Wallet<br/>Protector</h1>
            <p class="instruction">자산 보호를 위해 UNLOCK 하세요.</p>
            
            <!-- 로그인 폼 -->
            <div class="auth-form">
              <!-- 이메일 입력 필드 -->
              <input 
                v-model="loginForm.email"
                type="text" 
                placeholder="ID (test1234)" 
                class="input-field"
                @keyup.enter="handleLogin"
                :disabled="isLoading"
              />
              
              <!-- 비밀번호 입력 필드 -->
              <input 
                v-model="loginForm.password"
                type="password" 
                placeholder="Password (test1234)" 
                class="input-field"
                @keyup.enter="handleLogin"
                :disabled="isLoading"
              />
              
              <!-- 로그인 버튼 -->
              <button @click="handleLogin" class="login-btn" :disabled="isLoading">
                {{ isLoading ? 'LOGGING IN...' : 'LOGIN' }}
              </button>
              
              <!-- 오류 메시지 표시 -->
              <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
              
              <!-- 회원가입 링크 -->
              <p class="signup-link">처음이신가요? <button @click="$emit('switch-to-signup')" class="link-btn">회원가입</button></p>
            </div>
          </div>
          
          <!-- 지갑 옆 자물쇠 (해제 애니메이션) -->
          <div class="wallet-clasp" :class="{ 'unclasping': authState === 'unlocking' }">
            <span class="clasp-icon">🔒</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 신분증 카드 애니메이션 전환 -->
    <Transition name="id-card-drop">
      <div v-if="authState === 'unlocking' || authState === 'unlocked'" class="unlocked-screen">
        <!-- 로그인 성공 후 신분증 표시 -->
        <IdCardVisual :user-info="user" @animation-finished="authState = 'unlocked'" />
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import IdCardVisual from './IdCardVisual.vue';
import { setSessionToken } from '../api/client';

// ── 상태 관리 ────────────────────────────────────────────────────────────
/** 로그인 화면 상태: 'locked'(잠금) / 'unlocking'(해제중) / 'unlocked'(해제됨) */
const authState = ref('locked');
/** API 호출 중 여부 */
const isLoading = ref(false);
/** 오류 메시지 표시 */
const errorMessage = ref('');
/** 입력 폼 데이터 */
const loginForm = reactive({ email: '', password: '' });
/** 로그인된 사용자 정보 */
const user = reactive({ nickname: '', email: '' });

// 부모 컴포넌트로 이벤트 전달 (emit)
const emit = defineEmits(['switch-to-signup', 'login-success']);

/** 테스트 계정 (개발 단계용, 나중에 제거 필요) */
const TEST_ACCOUNT = {
  email: 'test1234',
  password: 'test1234',
  nickname: '테스트사용자',
};

/**
 * 로그인 버튼 클릭 핸들러
 * 하드코드된 테스트 계정으로 검증하는 간단한 로그인 로직
 */
const handleLogin = async () => {
  // 입력값 검증: 이메일과 비밀번호가 모두 입력되었는지 확인
  if (!loginForm.email || !loginForm.password) {
    errorMessage.value = '이메일과 비밀번호를 입력하세요.';
    return;
  }

  isLoading.value = true;
  errorMessage.value = '';

  try {
    // 테스트 계정과 비교하여 로그인 여부 판단
    if (loginForm.email === TEST_ACCOUNT.email && loginForm.password === TEST_ACCOUNT.password) {
      // 로그인 성공: 세션 토큰 저장 (테스트용 UUID 생성)
      const testToken = `test_token_${Date.now()}`;
      setSessionToken(testToken);
      
      // 로그인된 사용자 정보 설정
      user.nickname = TEST_ACCOUNT.nickname;
      user.email = loginForm.email;

      // 애니메이션 상태로 전환 (지갑이 열리는 효과)
      authState.value = 'unlocking';

      // 애니메이션 완료 후 부모 컴포넌트에 로그인 성공 이벤트 전달
      setTimeout(() => {
        emit('login-success', { nickname: user.nickname, email: user.email });
      }, 2000);
    } else {
      // 로그인 실패: 오류 메시지 표시
      errorMessage.value = '이메일 또는 비밀번호가 틀렸습니다.';
      console.error('Login failed: Invalid credentials');
    }
  } catch (error) {
    // 예외 발생 시 오류 처리
    errorMessage.value = error instanceof Error ? error.message : '로그인 실패';
    console.error('Login error:', error);
  } finally {
    // 로딩 상태 해제
    isLoading.value = false;
  }
};
</script>

<style scoped>
/** 로그인 컨테이너: 전체 화면 배경 */
.login-container {
  position: relative; 
  width: 100vw; 
  height: 100vh; 
  display: flex;
  justify-content: center; 
  align-items: center; 
  overflow: hidden;
  background: #111; /** 잠금 상태: 매우 어두운 배경 */
  transition: background 1.5s ease;
}

/** 로그인 성공 시: 배경색 변경 */
.is-unlocked { 
  background: #d0e1f9; /** 밝은 파란색으로 변경 */
}

/** 배경 오버레이: 어두운 반투명 레이어 */
.overlay { 
  position: absolute; 
  width: 100%; 
  height: 100%; 
  background: rgba(0,0,0,0.5); 
  z-index: 1;
}

/** 잠금 화면: 가죽 지갑이 표시되는 영역 */
.lock-screen { 
  position: relative; 
  z-index: 10; 
  text-align: center; 
  color: white; 
  display: flex; 
  justify-content: center; 
  align-items: center; 
  width: 100%; 
  height: 100%;
}

/* ═══ 가죽 지갑 컨테이너 스타일 ═══ */
/** 지갑 외부 컨테이너: 갈색 지갑 모양 */
.leather-wallet {
  position: relative;
  width: 500px; 
  height: 350px;
  background: #6f4e37; /** 가죽 갈색 */
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5); /** 그림자 효과 */
  display: flex; 
  justify-content: center; 
  align-items: center;
  overflow: hidden; /** 내부 스크린이 경계선을 넘지 않게 */
  border: 4px solid #5a3f2c;
}

/** 가죽 질감: 그라데이션으로 구현 (향후 이미지로 교체 가능) */
.wallet-texture {
  position: absolute; 
  top: 0; 
  left: 0; 
  width: 100%; 
  height: 100%;
  background: linear-gradient(135deg, #7b5840 0%, #6f4e37 50%, #5a3f2c 100%);
  opacity: 0.8; 
  z-index: 2;
}

/** 지갑 내부 인증 화면: 어두운 LCD 스크린 같은 모양 */
.auth-screen {
  position: relative; 
  z-index: 5;
  width: 320px; 
  height: 280px;
  background: rgba(0,0,0,0.7); /** 어두운 화면 배경 */
  border-radius: 10px; 
  border: 2px solid #aaa; /** 은색 테두리 */
  padding: 20px; 
  display: flex; 
  flex-direction: column; 
  justify-content: center;
}

/** 프로젝트 제목 */
.project-name { 
  font-size: 2rem; 
  margin: 0 0 10px 0; 
  color: #ffeb3b; /** 밝은 노랑색 */
  text-transform: uppercase; 
  letter-spacing: 2px;
}

/** 안내 메시지 */
.instruction { 
  font-size: 0.8rem; 
  opacity: 0.8; 
  margin-bottom: 20px;
}

/** 폼 컨테이너: 입력 필드들을 세로로 배열 */
.auth-form { 
  display: flex; 
  flex-direction: column; 
  gap: 8px; 
  width: 250px; 
  margin: 0 auto;
}

/** 입력 필드: 이메일/비밀번호 입력칸 */
.input-field { 
  padding: 10px; 
  border-radius: 5px; 
  border: none; 
  background: rgba(255,255,255,0.2); /** 반투명 흰색 */
  color: white; 
  transition: background 0.2s;
}

/** 입력 필드 비활성화 상태 */
.input-field:disabled { 
  opacity: 0.6; 
  cursor: not-allowed;
}

/** 플레이스홀더 텍스트 color */
.input-field::placeholder { 
  color: #ccc;
}

/** 로그인 버튼 스타일 */
.login-btn { 
  padding: 10px; 
  background: #e67e22; /** 주황색 */
  color: white; 
  border: none; 
  border-radius: 5px; 
  cursor: pointer; 
  font-weight: bold; 
  margin-top: 10px; 
  transition: transform 0.2s;
}

/** 로그인 버튼 호버 효과 */
.login-btn:hover:not(:disabled) { 
  transform: scale(1.05); /** 클릭하면 조금 커짐 */
}

/** 로그인 버튼 비활성화 상태 (로딩 중일 때) */
.login-btn:disabled { 
  opacity: 0.7; 
  cursor: not-allowed;
}

/** 오류 메시지 표시 영역 */
.error-message { 
  color: #ff6b6b; /** 빨간색 */
  font-size: 0.8rem; 
  margin-top: 8px; 
  text-align: center; 
  background: rgba(255,107,107,0.1); /** 연한 빨강색 배경 */
  padding: 6px; 
  border-radius: 4px;
}

/** 회원가입 링크 영역 */
.signup-link {
  font-size: 0.75rem;
  color: #ccc;
  margin-top: 12px;
  margin-bottom: 0;
}

/** 회원가입 링크 버튼 */
.link-btn {
  background: none;
  border: none;
  color: #ffeb3b; /** 노란색 */
  cursor: pointer;
  font-weight: bold;
  text-decoration: underline;
  font-size: 0.75rem;
}

/** 회원가입 링크 호버 효과 */
.link-btn:hover {
  color: #fff;
}

/* ═══ 지갑 옆 자물쇠 애니메이션 ═══ */
/** 자물쇠: 지갑 옆에 붙어있는 부분 */
.wallet-clasp {
  position: absolute; 
  top: 50%; 
  right: 0; 
  transform: translateY(-50%);
  width: 80px; 
  height: 120px;
  background: #5a3f2c; /** 지갑보다 더 진한 갈색 */
  border-radius: 10px 0 0 10px;
  display: flex; 
  justify-content: center; 
  align-items: center;
  z-index: 3; 
  transition: all 1s ease; /** 자물쇠 풀리는 애니메이션 */
}

/** 자물쇠 아이콘 */
.clasp-icon { 
  font-size: 2.5rem; 
  transition: transform 0.8s ease;
}

/** 자물쇠 풀리는 상태: 우측으로 사라지며 회전 */
.unclasping { 
  transform: translateY(-50%) translateX(100%); /** 우측으로 이동 */
  opacity: 0; /** 투명해짐 */
}

/** 자물쇠 풀리는 애니메이션 시 회전 */
.unclasping .clasp-icon { 
  transform: rotate(-90deg); /** 자물쇠가 반시계 회전 */
}

/** 신분증 카드 표시 영역: 로그인 성공 후 표시됨 */
.unlocked-screen { 
  position: relative; 
  z-index: 20; 
  width: 100vw; 
  height: 100vh;
}

/* ═══ Vue Transition 애니메이션 정의 ═══ */
/** 로그인 화면 페이드 아웃 애니메이션 */
.fade-out-leave-active { 
  transition: opacity 0.8s;
}

.fade-out-leave-to { 
  opacity: 0; /** 화면이 투명해지면서 사라짐 */
}

/** 신분증 카드 드롭 애니메이션: 위에서 아래로 떨어지며 회전 */
.id-card-drop-enter-active { 
  transition: all 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); /** 부드러운 곡선 애니메이션 */
}

.id-card-drop-enter-from { 
  opacity: 0; 
  transform: translate(-50%, -1000px) rotate(20deg); /** 위에서 아래로 떨어지며 회전 */
}
</style>