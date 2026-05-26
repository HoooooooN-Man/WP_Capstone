<template>
  <div
    class="w-full h-full rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.6)] flex flex-col relative overflow-hidden border transition-colors duration-300"
    :class="darkMode ? 'bg-[#181410] border-white/10 text-gray-100' : 'bg-[#fcfbf7] border-black/10 text-gray-800'"
  >
    <div class="absolute -right-32 -bottom-32 opacity-[0.02] pointer-events-none z-0">
      <svg class="w-[700px] h-[700px]" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
      </svg>
    </div>

    <!-- 탭 바 -->
    <div
      class="flex border-b px-6 pt-4 gap-1 z-10 flex-shrink-0 transition-colors duration-300"
      :class="darkMode ? 'border-white/10' : 'border-gray-200'"
    >
      <button
        v-for="tab in TABS" :key="tab.id"
        @click="activeTab = tab.id"
        class="px-4 py-2.5 rounded-t-lg text-[12px] font-bold tracking-wide transition-all flex items-center gap-1.5"
        :class="activeTab === tab.id
          ? (darkMode ? 'bg-white/10 text-white' : 'bg-white text-gray-800 shadow')
          : (darkMode ? 'text-white/35 hover:text-white/60' : 'text-gray-400 hover:text-gray-600')"
      >
        <component :is="tab.icon" class="w-3.5 h-3.5"/>
        {{ tab.label }}
      </button>
    </div>

    <!-- 콘텐츠 -->
    <div class="flex-1 overflow-y-auto z-10">

      <!-- ── 프로필 탭 ── -->
      <div v-if="activeTab === 'profile'" class="p-8 lg:p-10">
        <div
          class="flex justify-between items-center pb-5 mb-6 border-b-4 border-dashed transition-colors duration-300"
          :class="darkMode ? 'border-white/10' : 'border-gray-200'"
        >
          <div class="flex flex-col gap-1">
            <h2
              class="text-4xl lg:text-6xl font-black tracking-tighter uppercase transition-colors duration-300"
              :class="darkMode ? 'text-white' : 'text-[#2a170f]'"
            >Protector ID</h2>
            <span
              class="text-xs font-bold tracking-[0.4em] uppercase transition-colors duration-300"
              :class="darkMode ? 'text-white/40' : 'text-gray-400'"
            >Advanced Security Clearance • S-Tier Master</span>
          </div>
          <div class="px-5 py-2.5 bg-[#2a170f] rounded-2xl text-white text-xl lg:text-3xl font-black tracking-widest shadow-xl rotate-[-5deg]">PASSED</div>
        </div>

        <div class="flex gap-8 lg:gap-12">
          <div class="w-[30%] max-w-[220px] flex flex-col gap-4">
            <div
              class="w-full aspect-[3/4] rounded-[1.5rem] shadow-inner flex items-center justify-center relative overflow-hidden border-4 transition-colors duration-300"
              :class="darkMode ? 'bg-gradient-to-br from-white/[0.07] to-white/[0.03] border-white/10' : 'bg-gradient-to-br from-gray-100 to-gray-300 border-gray-200/50'"
            >
              <LucideUser
                class="w-28 h-28 lg:w-40 lg:h-40 transition-colors duration-300"
                :class="darkMode ? 'text-white/20' : 'text-gray-400/70'"
              />
              <div class="absolute inset-0 bg-gradient-to-b from-transparent via-green-400/20 to-transparent animate-scan"></div>
            </div>
            <div
              class="w-full h-10 flex items-center p-2 rounded-xl border shadow-inner opacity-40 transition-colors duration-300"
              :class="darkMode ? 'bg-white/5 border-white/10' : 'bg-white border-gray-200'"
            >
              <div class="w-full h-full bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjcGF0dGVybikiIC8+PGRlZnM+PHBhdHRlcm4gaWQ9InBhdHRlcm4iIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHJlY3Qgd2lkdGg9IjIiIGhlaWdodD0iMjAiIGZpbGw9IiMwMDAiIC8+PHJlY3QgeD0iNCIgd2lkdGg9IjYiIGhlaWdodD0iMjAiIGZpbGw9IiMwMDAiIC8+PHJlY3QgeD0iMTQiIHdpZHRoPSI0IiBoZWlnaHQ9IjIwIiBmaWxsPSIjMDAwIiAvPjwvcGF0dGVybj48L2RlZnM+PC9zdmc+')]"></div>
            </div>
          </div>

          <div class="flex-1 flex flex-col justify-between gap-6">
            <div>
              <p
                class="text-sm font-bold uppercase tracking-[0.3em] mb-2 transition-colors duration-300"
                :class="darkMode ? 'text-white/40' : 'text-gray-500'"
              >Authorized Holder</p>
              <p
                class="text-4xl lg:text-[72px] font-black uppercase tracking-tighter leading-none transition-colors duration-300"
                :class="darkMode ? 'text-white' : 'text-[#1a0f0a]'"
              >{{ user.name || 'USER' }}</p>
              <div
                class="h-1.5 w-24 lg:w-32 mt-3 rounded-full transition-colors duration-300"
                :class="darkMode ? 'bg-white/20' : 'bg-[#d9b9a9]'"
              ></div>
            </div>

            <div
              class="grid grid-cols-2 lg:grid-cols-3 gap-x-5 gap-y-5 border-t-4 pt-5 border-dashed transition-colors duration-300"
              :class="darkMode ? 'border-white/10' : 'border-gray-200'"
            >
              <div class="flex flex-col gap-1">
                <p class="text-[10px] font-bold uppercase tracking-widest transition-colors duration-300" :class="darkMode ? 'text-white/40' : 'text-gray-400'">Invest Style</p>
                <p class="text-xl lg:text-2xl font-extrabold">{{ user.style || '보수형' }}</p>
              </div>
              <div class="flex flex-col gap-1">
                <p class="text-[10px] font-bold uppercase tracking-widest transition-colors duration-300" :class="darkMode ? 'text-white/40' : 'text-gray-400'">Status</p>
                <p class="text-xl lg:text-2xl font-extrabold text-green-500 flex items-center gap-2">
                  <span class="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></span>{{ status }}
                </p>
              </div>
              <div class="flex flex-col gap-1 col-span-2 lg:col-span-1">
                <p class="text-[10px] font-bold uppercase tracking-widest transition-colors duration-300" :class="darkMode ? 'text-white/40' : 'text-gray-400'">Issue Date</p>
                <p class="text-xl lg:text-2xl font-extrabold">{{ issueDate }}</p>
              </div>
              <div class="flex flex-col gap-1 col-span-2 lg:col-span-3">
                <p class="text-[10px] font-bold uppercase tracking-widest transition-colors duration-300" :class="darkMode ? 'text-white/40' : 'text-gray-400'">Total Registered Assets</p>
                <p class="text-3xl lg:text-5xl font-black tracking-tight">{{ user.totalAsset || '12,500,000 원' }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── 회원정보 탭 ── -->
      <div v-else-if="activeTab === 'info'" class="p-6 lg:p-8 flex flex-col gap-6">
        <section v-for="section in infoSections" :key="section.title">
          <h3
            class="text-[10px] font-black uppercase tracking-[0.4em] mb-3 transition-colors duration-300"
            :class="darkMode ? 'text-white/35' : 'text-gray-400'"
          >{{ section.title }}</h3>
          <div class="grid grid-cols-2 gap-2.5">
            <div
              v-for="row in section.rows" :key="row.label"
              class="rounded-xl p-3.5 border transition-colors duration-300"
              :class="darkMode ? 'border-white/10 bg-white/5' : 'border-gray-200 bg-white'"
            >
              <p
                class="text-[9px] font-bold uppercase tracking-wider mb-1 transition-colors duration-300"
                :class="darkMode ? 'text-white/35' : 'text-gray-400'"
              >{{ row.label }}</p>
              <p class="text-sm font-bold truncate">{{ row.value }}</p>
              <span
                v-if="row.badge"
                class="inline-block mt-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-green-500/20 text-green-500"
              >{{ row.badge }}</span>
            </div>
          </div>
        </section>
      </div>

      <!-- ── 설정 탭 ── -->
      <div v-else-if="activeTab === 'settings'" class="p-6 lg:p-8 flex flex-col gap-6">

        <!-- 화면 설정 -->
        <section>
          <h3 class="text-[10px] font-black uppercase tracking-[0.4em] mb-3 transition-colors duration-300"
              :class="darkMode ? 'text-white/35' : 'text-gray-400'">화면 설정</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="darkMode ? 'border-white/10' : 'border-gray-200'">
            <div class="flex items-center justify-between p-4 transition-colors duration-300"
                 :class="darkMode ? 'bg-white/5' : 'bg-white'">
              <div class="flex items-center gap-3">
                <component :is="darkMode ? LucideMoon : LucideSun"
                           class="w-4 h-4"
                           :class="darkMode ? 'text-blue-400' : 'text-amber-500'"/>
                <div>
                  <p class="text-sm font-bold">다크 모드</p>
                  <p class="text-[11px] mt-0.5 transition-colors duration-300"
                     :class="darkMode ? 'text-white/40' : 'text-gray-400'">어두운 배경으로 전환합니다</p>
                </div>
              </div>
              <button
                @click="$emit('toggle-dark-mode')"
                class="w-12 h-6 rounded-full transition-all duration-300 relative flex-shrink-0 focus:outline-none"
                :class="darkMode ? 'bg-blue-500' : 'bg-gray-300'"
              >
                <span
                  class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300"
                  :class="darkMode ? 'left-[26px]' : 'left-0.5'"
                ></span>
              </button>
            </div>
          </div>
        </section>

        <!-- 알림 설정 -->
        <section>
          <h3 class="text-[10px] font-black uppercase tracking-[0.4em] mb-3 transition-colors duration-300"
              :class="darkMode ? 'text-white/35' : 'text-gray-400'">알림 설정</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="darkMode ? 'border-white/10' : 'border-gray-200'">
            <div
              v-for="(notif, idx) in notifications" :key="notif.key"
              class="flex items-center justify-between p-4 transition-colors duration-300"
              :class="[
                darkMode ? 'bg-white/5' : 'bg-white',
                idx < notifications.length - 1 ? (darkMode ? 'border-b border-white/10' : 'border-b border-gray-100') : ''
              ]"
            >
              <div>
                <p class="text-sm font-bold">{{ notif.label }}</p>
                <p class="text-[11px] mt-0.5 transition-colors duration-300"
                   :class="darkMode ? 'text-white/40' : 'text-gray-400'">{{ notif.desc }}</p>
              </div>
              <button
                @click="notif.enabled = !notif.enabled"
                class="w-12 h-6 rounded-full transition-all duration-300 relative flex-shrink-0 focus:outline-none"
                :class="notif.enabled ? 'bg-blue-500' : (darkMode ? 'bg-white/15' : 'bg-gray-300')"
              >
                <span
                  class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300"
                  :class="notif.enabled ? 'left-[26px]' : 'left-0.5'"
                ></span>
              </button>
            </div>
          </div>
        </section>

        <!-- 앱 정보 -->
        <section>
          <h3 class="text-[10px] font-black uppercase tracking-[0.4em] mb-3 transition-colors duration-300"
              :class="darkMode ? 'text-white/35' : 'text-gray-400'">앱 정보</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="darkMode ? 'border-white/10' : 'border-gray-200'">
            <div
              v-for="(item, idx) in appInfo" :key="item.label"
              class="flex justify-between items-center p-4 transition-colors duration-300"
              :class="[
                darkMode ? 'bg-white/5' : 'bg-white',
                idx < appInfo.length - 1 ? (darkMode ? 'border-b border-white/10' : 'border-b border-gray-100') : ''
              ]"
            >
              <span class="text-sm font-medium transition-colors duration-300"
                    :class="darkMode ? 'text-white/60' : 'text-gray-500'">{{ item.label }}</span>
              <span class="text-sm font-bold transition-colors duration-300"
                    :class="darkMode ? 'text-white/80' : 'text-gray-700'">{{ item.value }}</span>
            </div>
          </div>
        </section>

        <!-- 연결된 소셜 계정 -->
        <section>
          <h3 class="text-[10px] font-black uppercase tracking-[0.4em] mb-3 transition-colors duration-300"
              :class="darkMode ? 'text-white/35' : 'text-gray-400'">연결된 소셜 계정</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="darkMode ? 'border-white/10' : 'border-gray-200'">
            <div
              v-for="(provider, idx) in socialProviders" :key="provider.id"
              class="flex items-center justify-between p-4 transition-colors duration-300"
              :class="[
                darkMode ? 'bg-white/5' : 'bg-white',
                idx < socialProviders.length - 1 ? (darkMode ? 'border-b border-white/10' : 'border-b border-gray-100') : ''
              ]"
            >
              <div class="flex items-center gap-3">
                <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                     :style="{ background: provider.bgColor }">
                  <span v-html="provider.icon" class="w-4 h-4 flex items-center justify-center"></span>
                </div>
                <div>
                  <p class="text-sm font-bold">{{ provider.label }}</p>
                  <p class="text-[10px] transition-colors duration-300"
                     :class="provider.linked
                       ? 'text-green-500'
                       : (darkMode ? 'text-white/30' : 'text-gray-400')"
                  >{{ provider.linked ? '연결됨' : '연결되지 않음' }}</p>
                </div>
              </div>
              <button
                @click="handleSocialConnect(provider)"
                :disabled="provider.loading"
                class="px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                :class="provider.linked
                  ? (darkMode ? 'bg-red-500/10 border border-red-500/25 text-red-400 hover:bg-red-500/20' : 'bg-red-50 border border-red-200 text-red-500 hover:bg-red-100')
                  : (darkMode ? 'bg-white/5 border border-white/10 text-white/60 hover:bg-white/10' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50')"
              >
                {{ provider.loading ? '처리 중...' : (provider.linked ? '연결 해제' : '연결하기') }}
              </button>
            </div>
          </div>
          <p v-if="socialError" class="text-[9px] text-red-400/80 px-1 mt-1.5">{{ socialError }}</p>
        </section>

        <!-- 계정 -->
        <section>
          <h3 class="text-[10px] font-black uppercase tracking-[0.4em] mb-3 transition-colors duration-300"
              :class="darkMode ? 'text-white/35' : 'text-gray-400'">계정</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="darkMode ? 'border-white/10' : 'border-gray-200'">

            <!-- 로그인 정보 -->
            <div class="flex items-center justify-between p-4 transition-colors duration-300"
                 :class="[darkMode ? 'bg-white/5 border-b border-white/10' : 'bg-white border-b border-gray-100']">
              <div class="flex items-center gap-3">
                <LucideLogOut class="w-4 h-4" :class="darkMode ? 'text-white/40' : 'text-gray-400'"/>
                <div>
                  <p class="text-sm font-bold">{{ auth.nickname || '사용자' }}</p>
                  <p class="text-[11px] mt-0.5 transition-colors duration-300"
                     :class="darkMode ? 'text-white/38' : 'text-gray-400'">현재 로그인 중</p>
                </div>
              </div>
              <span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-green-500/15 text-green-500 border border-green-500/25">
                ACTIVE
              </span>
            </div>

            <!-- 로그아웃 버튼 -->
            <div class="p-4 transition-colors duration-300"
                 :class="darkMode ? 'bg-white/5' : 'bg-white'">
              <button
                @click="handleLogout"
                :disabled="logoutLoading"
                class="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 border"
                :class="logoutLoading
                  ? 'opacity-50 cursor-not-allowed border-red-500/20 text-red-400/50'
                  : (darkMode
                      ? 'bg-red-500/10 border-red-500/25 text-red-400 hover:bg-red-500/20 hover:border-red-500/40'
                      : 'bg-red-50 border-red-200 text-red-500 hover:bg-red-100')"
              >
                <LucideLogOut class="w-4 h-4"/>
                {{ logoutLoading ? '로그아웃 중...' : '로그아웃' }}
              </button>
            </div>
          </div>
        </section>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { LucideUser, LucideInfo, LucideSettings, LucideMoon, LucideSun, LucideLogOut } from 'lucide-vue-next';
import { MOCK_USER } from '@/mock/data.js';
import authApi from '@/api/auth.js';
import dbapi from '@/api/dbapi.js';
import { useAuthStore } from '@/stores/auth.js';

defineProps({
  user:     { type: Object,  required: true, default: () => ({}) },
  darkMode: { type: Boolean, default: true },
});
defineEmits(['toggle-dark-mode']);

const auth = useAuthStore();
const logoutLoading = ref(false);

async function handleLogout() {
  if (logoutLoading.value) return;
  logoutLoading.value = true;
  try {
    // 서버에 로그아웃 요청 (실패해도 로컬 처리 진행)
    await authApi.logout(auth.token);
  } catch {
    // POST /auth/logout 미연결 또는 실패 → 로컬만 처리
  } finally {
    auth.logout();   // 로컬 토큰/세션 초기화
    logoutLoading.value = false;
  }
}

const issueDate = MOCK_USER.issueDate;
const status    = MOCK_USER.status;
const activeTab = ref('profile');

const TABS = [
  { id: 'profile',  label: '프로필',  icon: LucideUser     },
  { id: 'info',     label: '회원정보', icon: LucideInfo     },
  { id: 'settings', label: '설정',    icon: LucideSettings },
];

const infoSections = [
  {
    title: '기본 정보',
    rows: [
      { label: '이름',     value: 'Kim Jinwoo'       },
      { label: '이메일',   value: 'user@example.com' },
      { label: '연락처',   value: '010-****-5678'    },
      { label: '생년월일', value: '1995. 03. 22'     },
      { label: '가입일',   value: '2026. 01. 15'     },
      { label: 'KYC 인증', value: '인증 완료', badge: 'VERIFIED' },
    ],
  },
  {
    title: '연결 계좌',
    rows: [
      { label: '은행',      value: 'KB국민은행'      },
      { label: '계좌번호',  value: '****-**-012345'  },
      { label: '계좌명',    value: 'WP-2026-001234' },
      { label: '일일 한도', value: '5,000,000 원'   },
    ],
  },
  {
    title: '투자 프로필',
    rows: [
      { label: '투자 성향', value: '보수형'        },
      { label: '위험 등급', value: '낮음 (1등급)'  },
      { label: '총 자산',   value: '12,500,000 원' },
      { label: '수익률',    value: '+8.42%'        },
    ],
  },
];

const notifications = reactive([
  { key: 'price', label: '시세 알림',    desc: '관심 종목 등락률 알림',   enabled: true  },
  { key: 'news',  label: '뉴스 알림',    desc: '주요 경제 뉴스 알림',     enabled: true  },
  { key: 'trade', label: '자동매매 알림', desc: '퀀트 자동매매 체결 알림', enabled: false },
]);

const appInfo = [
  { label: '버전',     value: 'v0.0.3'            },
  { label: '빌드일',   value: '2026.05.09'         },
  { label: '라이선스', value: 'WP Capstone © 2026' },
];

// ── 소셜 계정 연동 ──────────────────────────────────────────
const socialError = ref('');

const socialProviders = reactive([
  {
    id:      'google',
    label:   'Google',
    bgColor: '#fff',
    linked:  false,
    loading: false,
    icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>`,
  },
  {
    id:      'kakao',
    label:   '카카오',
    bgColor: '#FEE500',
    linked:  false,
    loading: false,
    icon: `<svg viewBox="0 0 24 24" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 3C6.477 3 2 6.477 2 10.5c0 2.584 1.574 4.857 3.969 6.22l-.994 3.695a.375.375 0 0 0 .553.415L9.86 18.54A11.578 11.578 0 0 0 12 18c5.523 0 10-3.477 10-7.5S17.523 3 12 3z" fill="#3C1E1E"/>
    </svg>`,
  },
  {
    id:      'naver',
    label:   '네이버',
    bgColor: '#03C75A',
    linked:  false,
    loading: false,
    icon: `<svg viewBox="0 0 24 24" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
      <path d="M13.6 12.4 10.1 7H7v10h3.4v-5.4L14 17H17V7h-3.4z" fill="white"/>
    </svg>`,
  },
]);

async function handleSocialConnect(provider) {
  if (provider.loading) return;
  socialError.value  = '';
  provider.loading   = true;

  try {
    if (provider.linked) {
      // 연결 해제: 현재 백엔드 엔드포인트 미구현 — 로컬만 처리
      provider.linked  = false;
      provider.loading = false;
      return;
    }

    // 소셜 OAuth 토큰 획득 후 백엔드에 연동 요청
    // dbapi 인터셉터가 session-token을 자동으로 헤더에 추가함
    let accessToken = '';
    if (provider.id === 'google')     accessToken = await getGoogleToken();
    else if (provider.id === 'kakao') accessToken = await getKakaoToken();
    else if (provider.id === 'naver') accessToken = await getNaverToken();

    await dbapi.post(`/auth/login/${provider.id}`, { access_token: accessToken });
    provider.linked = true;
  } catch (err) {
    const status = err.response?.status;
    if (status === 429) socialError.value = '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.';
    else socialError.value = err.response?.data?.detail ?? `${provider.label} 연동에 실패했습니다.`;
  } finally {
    provider.loading = false;
  }
}

// ── 소셜 OAuth 토큰 스텁 (SocialLoginButtons와 동일) ─────────
function getGoogleToken() {
  return new Promise((resolve, reject) => {
    if (!window.google?.accounts?.oauth2) { reject(new Error('Google SDK가 로드되지 않았습니다.')); return; }
    const client = window.google.accounts.oauth2.initTokenClient({
      client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
      scope: 'email profile',
      callback: (res) => { if (res.error) reject(new Error(res.error)); else resolve(res.access_token); },
    });
    client.requestAccessToken();
  });
}

function getKakaoToken() {
  return new Promise((resolve, reject) => {
    const redirectUri = 'http://localhost:8000/auth/kakao/callback';
    const url = `https://kauth.kakao.com/oauth/authorize?response_type=code&client_id=${import.meta.env.VITE_KAKAO_REST_KEY}&redirect_uri=${encodeURIComponent(redirectUri)}`;
    const popup = window.open(url, 'kakao_link', 'width=500,height=600');
    const timer = setInterval(() => { if (popup?.closed) { clearInterval(timer); reject(new Error('창이 닫혔습니다.')); } }, 500);
    window.addEventListener('message', function handler(e) {
      if (e.origin !== 'http://localhost:8000') return;
      clearInterval(timer); window.removeEventListener('message', handler); popup?.close();
      if (e.data?.error) reject(new Error(e.data.error));
      else if (e.data?.access_token) resolve(e.data.access_token);
      else reject(new Error('토큰 수신 실패'));
    });
  });
}

function getNaverToken() {
  return new Promise((resolve, reject) => {
    const state = Math.random().toString(36).substring(2);
    const redirectUri = 'http://localhost:8000/auth/naver/callback';
    const url = `https://nid.naver.com/oauth2.0/authorize?response_type=code&client_id=${import.meta.env.VITE_NAVER_CLIENT_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&state=${state}`;
    const popup = window.open(url, 'naver_link', 'width=500,height=600');
    const timer = setInterval(() => { if (popup?.closed) { clearInterval(timer); reject(new Error('창이 닫혔습니다.')); } }, 500);
    window.addEventListener('message', function handler(e) {
      if (e.origin !== 'http://localhost:8000') return;
      clearInterval(timer); window.removeEventListener('message', handler); popup?.close();
      if (e.data?.error) reject(new Error(e.data.error));
      else if (e.data?.access_token) resolve(e.data.access_token);
      else reject(new Error('토큰 수신 실패'));
    });
  });
}
</script>

<style scoped>
.animate-scan {
  animation: scan 3s linear infinite;
}
</style>
