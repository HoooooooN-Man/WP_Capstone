# 프론트엔드 API 연동 가이드

## 📋 구현된 기능

### 1. **API 클라이언트** (`src/api/client.ts`)
백엔드와 통신하는 모든 API 함수가 정의되어 있습니다.

#### 세션 토큰 관리
```typescript
import { getSessionToken, setSessionToken, clearSessionToken } from '@/api/client';

// 토큰 저장
setSessionToken(token);

// 토큰 조회
const token = getSessionToken();

// 토큰 삭제 (로그아웃)
clearSessionToken();
```

#### 인증 API
```typescript
import { authAPI } from '@/api/client';

// 이메일 중복 검사
await authAPI.checkEmail('user@example.com');

// 인증 코드 확인
await authAPI.verifyCode('user@example.com', '123456');

// 회원가입
await authAPI.register('user@example.com', 'password', 'nickname');

// 로그인
const response = await authAPI.login('user@example.com', 'password');
// → { session_token: '...', nickname: '...' }

// 로그아웃
authAPI.logout();
```

#### 주식 데이터 API
```typescript
import { stocksAPI } from '@/api/client';

// 모델 버전 조회
const versions = await stocksAPI.getVersions();

// 날짜 조회
const dates = await stocksAPI.getDates('latest');

// 특정 날짜 추천 종목
const scores = await stocksAPI.getStockScores('2024-01-15', 'latest');

// 특정 종목 이력
const history = await stocksAPI.getStockHistory('005930', 'latest');

// 섹터 정보
const sectors = await stocksAPI.getSectorInfo('latest');
```

#### 포트폴리오 API
```typescript
import { portfolioAPI } from '@/api/client';

// 백테스트 요약
const summary = await portfolioAPI.getBacktestSummary();

// 월별 수익률
const monthly = await portfolioAPI.getBacktestMonthly();
```

### 2. **로그인 화면** (`src/components/LoginView.vue`)
- 이메일/비밀번호 입력
- 백엔드 로그인 API 호출
- 지갑 애니메이션 + 신분증 표시
- 오류 메시지 표시
- 회원가입 링크

### 3. **회원가입 화면** (`src/components/SignUpView.vue`)
3단계 회원가입 플로우:
1. **이메일 검증**: 이메일 입력 → 인증 코드 발송
2. **코드 확인**: 인증 코드 입력 → 검증
3. **정보 입력**: 닉네임, 비밀번호 입력 → 회원가입 완료

### 4. **App.vue** (메인 컴포넌트)
로그인/회원가입/대시보드 화면 전환 관리

---

## 🔧 환경 설정

`.env` 파일에서 API 서버 주소 설정:
```
VITE_API_URL=http://localhost:8001
```

---

## 📐 새로운 컴포넌트에서 API 사용 예시

```typescript
<template>
  <div>
    <button @click="fetchStocks">추천 종목 조회</button>
    <p v-if="loading">로딩 중...</p>
    <p v-if="error" class="error">{{ error }}</p>
    <ul v-if="stocks">
      <li v-for="stock in stocks" :key="stock.ticker">
        {{ stock.name }} : {{ stock.score }}
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { stocksAPI } from '@/api/client';

const stocks = ref(null);
const loading = ref(false);
const error = ref('');

const fetchStocks = async () => {
  loading.value = true;
  error.value = '';
  
  try {
    const data = await stocksAPI.getStockScores('2024-01-15', 'latest');
    stocks.value = data.items;
  } catch (err) {
    error.value = err instanceof Error ? err.message : '데이터 조회 실패';
  } finally {
    loading.value = false;
  }
};
</script>
```

---

## 🚀 실행 방법

### 1. 백엔드 시작
```bash
cd Back/FastAPI
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. 프론트엔드 시작
```bash
cd Front
npm install
npm run dev
```

---

## 📝 API 응답/요청 형식

### 로그인 요청
```json
POST /auth/login
{
  "email": "user@example.com",
  "password": "password123"
}
```

### 로그인 응답
```json
{
  "session_token": "uuid-token-here",
  "nickname": "사용자닉네임"
}
```

### 추천 종목 응답
```json
{
  "date": "2024-01-15",
  "items": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "score": 87,
      "tier": "A",
      "rank_in_date": 1,
      "prob_ensemble": 0.85,
      "close": 65000
    }
  ]
}
```

---

## 🔗 API 서버 주소

- **개발 환경**: `http://localhost:8001`
- **문서 URL**: 
  - Swagger UI: `http://localhost:8001/docs`
  - ReDoc: `http://localhost:8001/redoc`

---

## ⚠️ 주의사항

1. **CORS 설정**: 백엔드의 CORS 미들웨어 확인 필요
2. **세션 토큰**: 모든 인증 요청에 `session-token` 헤더 자동 추가됨
3. **에러 처리**: 모든 API 호출은 try-catch로 감싸기
4. **토큰 만료**: 백엔드에서 토큰 만료 시 재로그인 필요

---

## 📚 패키지 추가 필요 시

```bash
# 라우팅이 필요하면
npm install vue-router@next

# 상태 관리가 필요하면
npm install pinia
```
