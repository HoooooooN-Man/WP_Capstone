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

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { LucideUser, LucideInfo, LucideSettings, LucideMoon, LucideSun } from 'lucide-vue-next';
import { MOCK_USER } from '@/mock/data.js';

defineProps({
  user:     { type: Object,  required: true, default: () => ({}) },
  darkMode: { type: Boolean, default: true },
});
defineEmits(['toggle-dark-mode']);

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
</script>

<style scoped>
.animate-scan {
  animation: scan 3s linear infinite;
}
</style>
