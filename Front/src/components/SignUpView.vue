<template>
  <div class="signup-container">
    <div class="overlay"></div>

    <div class="signup-form-wrapper">
      <div class="signup-card">
        <h2>Create Account</h2>
        <p class="subtitle">Wallet Protector에 가입하세요</p>

        <!-- 이메일 인증 단계 -->
        <div v-if="step === 'email'" class="form-section">
          <input 
            v-model="form.email"
            type="email" 
            placeholder="이메일 주소"
            class="input-field"
            :disabled="isLoading"
          />
          <button @click="handleCheckEmail" class="btn-primary" :disabled="isLoading">
            {{ isLoading ? '확인 중...' : '인증 코드 발송' }}
          </button>
          <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        </div>

        <!-- 인증 코드 단계 -->
        <div v-if="step === 'verify'" class="form-section">
          <p class="info-text">{{ form.email }}로 보낸 인증 코드를 입력하세요.</p>
          <input 
            v-model="form.code"
            type="text" 
            placeholder="6자리 인증 코드"
            class="input-field"
            maxlength="6"
            :disabled="isLoading"
          />
          <button @click="handleVerifyCode" class="btn-primary" :disabled="isLoading">
            {{ isLoading ? '확인 중...' : '인증 확인' }}
          </button>
          <button @click="step = 'email'" class="btn-secondary">뒤로 가기</button>
          <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        </div>

        <!-- 회원정보 입력 단계 -->
        <div v-if="step === 'register'" class="form-section">
          <input 
            v-model="form.nickname"
            type="text" 
            placeholder="닉네임"
            class="input-field"
            :disabled="isLoading"
          />
          <input 
            v-model="form.password"
            type="password" 
            placeholder="비밀번호"
            class="input-field"
            :disabled="isLoading"
          />
          <input 
            v-model="form.confirmPassword"
            type="password" 
            placeholder="비밀번호 확인"
            class="input-field"
            :disabled="isLoading"
          />
          <button @click="handleRegister" class="btn-primary" :disabled="isLoading">
            {{ isLoading ? '가입 중...' : '회원가입 완료' }}
          </button>
          <button @click="step = 'verify'" class="btn-secondary">뒤로 가기</button>
          <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        </div>

        <div class="footer">
          <p>이미 계정이 있으신가요? <button @click="emit('switch-to-login')" class="link-btn">로그인</button></p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { authAPI } from '../api/client';

const emit = defineEmits(['switch-to-login', 'signup-success']);

type Step = 'email' | 'verify' | 'register';

const step = ref<Step>('email');
const isLoading = ref(false);
const errorMessage = ref('');

const form = reactive({
  email: '',
  code: '',
  nickname: '',
  password: '',
  confirmPassword: '',
});

const handleCheckEmail = async () => {
  if (!form.email) {
    errorMessage.value = '이메일을 입력하세요.';
    return;
  }

  isLoading.value = true;
  errorMessage.value = '';

  try {
    await authAPI.checkEmail(form.email);
    step.value = 'verify';
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '이메일 확인 실패';
  } finally {
    isLoading.value = false;
  }
};

const handleVerifyCode = async () => {
  if (!form.code || form.code.length !== 6) {
    errorMessage.value = '6자리 인증 코드를 입력하세요.';
    return;
  }

  isLoading.value = true;
  errorMessage.value = '';

  try {
    await authAPI.verifyCode(form.email, form.code);
    step.value = 'register';
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '인증 실패';
  } finally {
    isLoading.value = false;
  }
};

const handleRegister = async () => {
  if (!form.nickname) {
    errorMessage.value = '닉네임을 입력하세요.';
    return;
  }

  if (!form.password || form.password.length < 8) {
    errorMessage.value = '비밀번호는 최소 8자 이상이어야 합니다.';
    return;
  }

  if (form.password !== form.confirmPassword) {
    errorMessage.value = '비밀번호가 일치하지 않습니다.';
    return;
  }

  isLoading.value = true;
  errorMessage.value = '';

  try {
    await authAPI.register(form.email, form.password, form.nickname);
    emit('signup-success'); // 부모 컴포넌트에 전달
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '회원가입 실패';
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.signup-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;
}

.overlay {
  position: absolute;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
  z-index: 1;
}

.signup-form-wrapper {
  position: relative;
  z-index: 10;
}

.signup-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  padding: 40px;
  width: 350px;
  text-align: center;
}

.signup-card h2 {
  font-size: 1.8rem;
  color: #333;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #666;
  font-size: 0.9rem;
  margin: 0 0 30px 0;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-field {
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: border-color 0.2s;
}

.input-field:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.input-field:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
  opacity: 0.7;
}

.btn-primary {
  padding: 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 8px;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px;
  background: transparent;
  color: #667eea;
  border: 1px solid #667eea;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #f5f5f5;
}

.info-text {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 12px;
}

.error-message {
  color: #ff6b6b;
  font-size: 0.8rem;
  background: rgba(255, 107, 107, 0.1);
  padding: 8px;
  border-radius: 4px;
  margin-top: 8px;
}

.footer {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #eee;
  font-size: 0.9rem;
  color: #666;
}

.link-btn {
  background: none;
  border: none;
  color: #667eea;
  cursor: pointer;
  font-weight: bold;
  text-decoration: underline;
}

.link-btn:hover {
  color: #5568d3;
}
</style>
