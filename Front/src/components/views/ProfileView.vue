<template>
  <div
    class="w-full h-full rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.5)] flex flex-col relative overflow-hidden border transition-colors duration-300"
    :class="localDark ? 'bg-[#0f1520] border-white/10 text-gray-100' : 'bg-[#f7f4ee] border-black/12 text-gray-800'"
  >
    <!-- 신분증 상단 컬러 스트라이프 -->
    <div class="flex-shrink-0 h-1.5 bg-gradient-to-r from-[#1a3a6b] via-[#c9a227] to-[#1a3a6b] z-10"></div>

    <!-- 배경 장식 (홀로그램 원) -->
    <div class="absolute right-4 top-8 w-40 h-40 rounded-full pointer-events-none z-0 opacity-[0.04]"
         :class="localDark ? 'border-8 border-white' : 'border-8 border-black'"></div>
    <div class="absolute -left-8 bottom-24 w-64 h-64 rounded-full pointer-events-none z-0 opacity-[0.025]"
         :class="localDark ? 'border-4 border-white' : 'border-4 border-black'"></div>

    <!-- 탭 바 -->
    <div
      class="flex border-b px-5 pt-3.5 gap-0.5 z-10 flex-shrink-0 transition-colors duration-300"
      :class="localDark ? 'border-white/10' : 'border-gray-200'"
    >
      <button
        v-for="tab in TABS" :key="tab.id"
        @click="activeTab = tab.id"
        class="px-3.5 py-2 rounded-t-lg text-[13px] font-bold tracking-wide transition-all flex items-center gap-1.5"
        :class="activeTab === tab.id
          ? (localDark ? 'bg-white/10 text-white' : 'bg-white text-gray-800 shadow')
          : (localDark ? 'text-white/35 hover:text-white/60' : 'text-gray-400 hover:text-gray-600')"
      >
        <component :is="tab.icon" class="w-3 h-3"/>
        {{ tab.label }}
      </button>
    </div>

    <!-- ───────────────────────────────────── -->
    <!-- 콘텐츠 영역 -->
    <!-- ───────────────────────────────────── -->
    <div class="flex-1 overflow-y-auto z-10">

      <!-- ══════════ 홈 탭 ══════════ -->
      <div v-if="activeTab === 'home'" class="p-4 lg:p-5 flex flex-col gap-4">

        <!-- ① AI 마켓 스코어 + 사용자 인사 -->
        <div class="flex gap-3">

          <!-- 사용자 인사 카드 -->
          <div
            class="flex-1 rounded-2xl border p-4 flex flex-col justify-between transition-colors duration-300"
            :class="localDark ? 'bg-white/5 border-white/10' : 'bg-white border-gray-200'"
          >
            <div>
              <p class="text-[11px] font-bold uppercase tracking-[0.3em] transition-colors duration-300"
                 :class="localDark ? 'text-[#9a7418]' : 'text-[#c9a227]'">Welcome back</p>
              <p class="text-xl font-black text-white mt-0.5 leading-tight"
                 :class="localDark ? 'text-white' : 'text-[#1a0f0a]'">
                {{ auth.nickname || 'User' }}
              </p>
            </div>
            <div>
              <p class="text-[11px] transition-colors duration-300"
                 :class="localDark ? 'text-white/35' : 'text-gray-400'">기준일</p>
              <p class="text-[13px] font-bold" :class="localDark ? 'text-white/70' : 'text-gray-600'">
                {{ recDate || '—' }}
              </p>
            </div>
          </div>

          <!-- AI 마켓 스코어 카드 -->
          <div
            class="flex-1 rounded-2xl border p-4 flex flex-col justify-between cursor-pointer hover:brightness-110 transition-all duration-200"
            :class="localDark ? 'bg-[#c9a227]/8 border-[#c9a227]/25' : 'bg-amber-50 border-amber-200'"
            @click="emit('navigate', 'company')"
          >
            <div>
              <p class="text-[11px] font-bold uppercase tracking-[0.3em] text-[#c9a227]">AI Market Score</p>
              <div class="flex items-baseline gap-1 mt-0.5">
                <span class="text-3xl font-black" :class="localDark ? 'text-white' : 'text-[#1a0f0a]'">
                  {{ recLoading ? '—' : marketScore }}
                </span>
                <span class="text-sm font-bold text-[#c9a227]/80">/ 100</span>
              </div>
            </div>
            <div>
              <div class="flex gap-0.5 items-end mb-1">
                <div v-for="i in 8" :key="i"
                     class="rounded-sm flex-1 transition-colors"
                     :style="{ height: (8 + i * 3.5) + 'px' }"
                     :class="i <= Math.round(marketScore / 12.5)
                       ? 'bg-[#c9a227]'
                       : (localDark ? 'bg-white/10' : 'bg-gray-200')">
                </div>
              </div>
              <p class="text-[12px] font-bold" :class="localDark ? 'text-white/60' : 'text-gray-500'">
                {{ marketLabel }}
              </p>
            </div>
          </div>
        </div>

        <!-- ② 지수 스크롤 -->
        <div>
          <p class="text-[11px] font-black uppercase tracking-[0.35em] mb-2 transition-colors duration-300"
             :class="localDark ? 'text-white/30' : 'text-gray-400'">Market Indices</p>
          <div class="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
            <div
              v-for="idx in indices" :key="idx.name"
              class="flex-shrink-0 rounded-xl border px-3 py-2.5 min-w-[80px] transition-colors duration-300"
              :class="localDark ? 'bg-white/5 border-white/10' : 'bg-white border-gray-200'"
            >
              <p class="text-[11px] font-bold uppercase tracking-wider mb-1 transition-colors duration-300"
                 :class="localDark ? 'text-white/35' : 'text-gray-400'">{{ idx.name }}</p>
              <p class="text-[14px] font-black" :class="localDark ? 'text-white' : 'text-gray-800'">{{ idx.value }}</p>
              <p class="text-[11px] font-bold flex items-center gap-0.5" :class="idx.up ? 'text-emerald-400' : 'text-red-400'">
                {{ idx.up ? '▲' : '▼' }} {{ idx.change }}
              </p>
            </div>
          </div>
        </div>

        <!-- ③ AI 추천 종목 -->
        <div>
          <div class="flex items-center justify-between mb-2.5">
            <p class="text-[11px] font-black uppercase tracking-[0.35em] transition-colors duration-300"
               :class="localDark ? 'text-white/30' : 'text-gray-400'">AI 추천 종목</p>
            <button
              class="text-[11px] font-bold text-[#c9a227]/70 hover:text-[#c9a227] transition-colors uppercase tracking-widest"
              @click="emit('navigate', 'company')"
            >더보기 →</button>
          </div>

          <!-- 티어 탭 -->
          <div class="flex gap-1 mb-2.5">
            <button
              v-for="t in recTabs" :key="t.id"
              @click="activeRecTab = t.id"
              class="px-3 py-1 rounded-lg text-[11px] font-black uppercase tracking-wider transition-all"
              :class="activeRecTab === t.id
                ? 'bg-[#c9a227]/20 border border-[#c9a227]/40 text-[#c9a227]'
                : (localDark ? 'bg-white/5 border border-white/10 text-white/40 hover:text-white/60' : 'bg-white border border-gray-200 text-gray-400 hover:text-gray-600')"
            >{{ t.label }}</button>
          </div>

          <!-- 로딩 -->
          <div v-if="recLoading" class="flex justify-center py-6">
            <svg class="animate-spin w-5 h-5 text-[#c9a227]/60" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-dasharray="60" stroke-dashoffset="20" stroke-linecap="round"/>
            </svg>
          </div>

          <!-- 종목 리스트 -->
          <div v-else class="flex flex-col gap-1.5">
            <div
              v-for="(stock, i) in filteredRecs" :key="stock.ticker"
              class="flex items-center gap-2.5 rounded-xl border px-3 py-2.5 cursor-pointer hover:brightness-110 transition-all duration-150 group"
              :class="localDark ? 'bg-white/5 border-white/8 hover:border-white/15' : 'bg-white border-gray-100 hover:border-gray-300'"
              @click="emit('navigate', 'company')"
            >
              <!-- 순위 -->
              <span class="text-[13px] font-black w-4 text-center flex-shrink-0 transition-colors duration-300"
                    :class="localDark ? 'text-white/25' : 'text-gray-300'">{{ i + 1 }}</span>

              <!-- 이니셜 아바타 -->
              <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-[13px] font-black"
                   :class="tierBg(stock.tier)">
                {{ (stock.name || stock.ticker)?.[0] }}
              </div>

              <!-- 종목명 + 섹터 -->
              <div class="flex-1 min-w-0">
                <p class="text-[13px] font-black truncate" :class="localDark ? 'text-white' : 'text-gray-800'">
                  {{ stock.name ?? stock.ticker }}
                </p>
                <p class="text-[11px] truncate transition-colors duration-300"
                   :class="localDark ? 'text-white/35' : 'text-gray-400'">
                  {{ stock.ticker }}{{ stock.sector ? ' · ' + stock.sector : '' }}
                </p>
              </div>

              <!-- 점수 바 -->
              <div class="flex flex-col items-end gap-1 flex-shrink-0 w-16">
                <span class="text-[13px] font-black text-[#c9a227]">{{ Math.round(stock.score) }}</span>
                <div class="w-full h-1 rounded-full transition-colors duration-300"
                     :class="localDark ? 'bg-white/10' : 'bg-gray-100'">
                  <div class="h-full rounded-full bg-gradient-to-r from-[#c9a227] to-[#9a7218]"
                       :style="{ width: Math.round(stock.score) + '%' }"></div>
                </div>
              </div>

              <!-- 티어 뱃지 -->
              <span class="w-5 h-5 rounded-md flex items-center justify-center text-[11px] font-black flex-shrink-0"
                    :class="tierBadgeClass(stock.tier)">
                {{ stock.tier }}
              </span>
            </div>

            <div v-if="!filteredRecs.length"
                 class="text-center py-6 text-[13px] transition-colors duration-300"
                 :class="localDark ? 'text-white/25' : 'text-gray-300'">
              해당 티어 종목이 없습니다
            </div>
          </div>
        </div>

        <!-- ④ 섹터별 현황 -->
        <div>
          <div class="flex items-center justify-between mb-2.5">
            <p class="text-[11px] font-black uppercase tracking-[0.35em] transition-colors duration-300"
               :class="localDark ? 'text-white/30' : 'text-gray-400'">섹터별 현황</p>
          </div>
          <div v-if="sectorsLoading" class="flex justify-center py-4">
            <svg class="animate-spin w-5 h-5 text-[#c9a227]/60" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-dasharray="60" stroke-dashoffset="20" stroke-linecap="round"/>
            </svg>
          </div>
          <div v-else class="grid grid-cols-2 lg:grid-cols-3 gap-2">
            <div
              v-for="sector in sectors" :key="sector.sector"
              class="rounded-xl border p-3 cursor-pointer hover:brightness-110 transition-all duration-150"
              :class="localDark ? 'bg-white/5 border-white/10 hover:border-white/20' : 'bg-white border-gray-200 hover:border-gray-300'"
              @click="emit('navigate', 'company')"
            >
              <p class="text-[12px] font-black truncate mb-2 transition-colors duration-300"
                 :class="localDark ? 'text-white/80' : 'text-gray-700'">{{ sector.sector }}</p>
              <div class="flex items-baseline gap-1 mb-1">
                <span class="text-lg font-black text-[#c9a227]">{{ Math.round(sector.avg_score) }}</span>
                <span class="text-[11px] transition-colors duration-300"
                      :class="localDark ? 'text-white/30' : 'text-gray-400'">점</span>
              </div>
              <div class="w-full h-1 rounded-full mb-2 transition-colors duration-300"
                   :class="localDark ? 'bg-white/10' : 'bg-gray-100'">
                <div class="h-full rounded-full bg-gradient-to-r from-[#c9a227] to-[#9a7218]"
                     :style="{ width: Math.round(sector.avg_score) + '%' }"></div>
              </div>
              <div class="flex justify-between">
                <span class="text-[11px] font-bold text-emerald-400">A {{ sector.a_tier_count ?? 0 }}종목</span>
                <span class="text-[11px] transition-colors duration-300"
                      :class="localDark ? 'text-white/30' : 'text-gray-400'">전체 {{ sector.total_count ?? 0 }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ⑤ 주요 기능 -->
        <div>
          <p class="text-[11px] font-black uppercase tracking-[0.35em] mb-2.5 transition-colors duration-300"
             :class="localDark ? 'text-white/30' : 'text-gray-400'">주요 기능</p>
          <div class="flex flex-col gap-2">
            <button
              v-for="cta in ctas" :key="cta.id"
              class="flex items-center gap-3 rounded-xl border p-3.5 hover:brightness-110 transition-all duration-150 text-left w-full"
              :class="localDark ? 'bg-white/5 border-white/10 hover:border-white/20' : 'bg-white border-gray-200 hover:border-gray-300'"
              @click="emit('navigate', cta.target)"
            >
              <div class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 text-lg"
                   :class="localDark ? 'bg-white/8' : 'bg-gray-50'">{{ cta.icon }}</div>
              <div class="flex-1">
                <p class="text-[11px] transition-colors duration-300"
                   :class="localDark ? 'text-white/35' : 'text-gray-400'">{{ cta.sub }}</p>
                <p class="text-[14px] font-black" :class="localDark ? 'text-white' : 'text-gray-800'">{{ cta.label }}</p>
              </div>
              <svg class="w-4 h-4 flex-shrink-0 transition-colors duration-300"
                   :class="localDark ? 'text-white/20' : 'text-gray-300'"
                   fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- ⑥ FAQ -->
        <div>
          <p class="text-[11px] font-black uppercase tracking-[0.35em] mb-2.5 transition-colors duration-300"
             :class="localDark ? 'text-white/30' : 'text-gray-400'">자주 묻는 질문</p>

          <!-- FAQ 카테고리 탭 -->
          <div class="flex gap-1.5 mb-2.5">
            <button
              v-for="cat in faqCategories" :key="cat.id"
              @click="activeFaqCat = cat.id"
              class="px-2.5 py-1 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all"
              :class="activeFaqCat === cat.id
                ? 'bg-[#c9a227]/20 border border-[#c9a227]/40 text-[#c9a227]'
                : (localDark ? 'bg-white/5 border border-white/10 text-white/35 hover:text-white/55' : 'bg-white border border-gray-200 text-gray-400')"
            >{{ cat.label }}</button>
          </div>

          <!-- FAQ 아이템 -->
          <div class="flex flex-col gap-1.5">
            <div
              v-for="faq in currentFaqs" :key="faq.id"
              class="rounded-xl border overflow-hidden transition-colors duration-300"
              :class="localDark ? 'bg-white/5 border-white/10' : 'bg-white border-gray-200'"
            >
              <button
                class="w-full flex items-center justify-between px-4 py-3 text-left hover:brightness-105 transition-all"
                @click="toggleFaq(faq.id)"
              >
                <span class="text-[13px] font-bold pr-4 leading-snug"
                      :class="localDark ? 'text-white/80' : 'text-gray-700'">{{ faq.q }}</span>
                <span class="flex-shrink-0 text-[14px] font-bold text-[#c9a227]/70 transition-transform duration-200"
                      :style="activeFaq === faq.id ? 'transform: rotate(45deg)' : ''">＋</span>
              </button>
              <div
                class="overflow-hidden transition-all duration-300"
                :style="activeFaq === faq.id ? 'max-height: 200px; opacity: 1' : 'max-height: 0; opacity: 0'"
              >
                <p class="px-4 pb-3 text-[12px] leading-relaxed border-t transition-colors duration-300"
                   :class="localDark ? 'text-white/45 border-white/8' : 'text-gray-500 border-gray-100'">
                  {{ faq.a }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- 하단 면책 -->
        <p class="text-[10px] leading-relaxed text-center pb-2 transition-colors duration-300"
           :class="localDark ? 'text-white/20' : 'text-gray-300'">
          이 서비스가 제공하는 모든 정보는 투자 참고용으로만 제공되며 특정 주식 매매를 추천하거나<br>
          투자 결정의 유일한 근거로 사용되어서는 안 됩니다. 모든 투자에는 원금 손실 위험이 따릅니다.
        </p>

      </div>
      <!-- /홈 탭 -->


      <!-- ══════════ 회원정보 탭 ══════════ -->
      <div v-else-if="activeTab === 'info'" class="p-5 lg:p-6 flex flex-col gap-5">
        <section v-for="section in infoSections" :key="section.title">
          <h3
            class="text-[11px] font-black uppercase tracking-[0.4em] mb-2.5 transition-colors duration-300"
            :class="localDark ? 'text-white/35' : 'text-gray-400'"
          >{{ section.title }}</h3>
          <div class="grid grid-cols-2 gap-2">
            <div
              v-for="row in section.rows" :key="row.label"
              class="rounded-xl p-3 border transition-colors duration-300"
              :class="localDark ? 'border-white/10 bg-white/5' : 'border-gray-200 bg-white'"
            >
              <p class="text-[10px] font-bold uppercase tracking-wider mb-1 transition-colors duration-300"
                 :class="localDark ? 'text-white/35' : 'text-gray-400'">{{ row.label }}</p>
              <p class="text-[14px] font-bold truncate">{{ row.value }}</p>
              <span
                v-if="row.badge"
                class="inline-block mt-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-500/20 text-green-500"
              >{{ row.badge }}</span>
            </div>
          </div>
        </section>
      </div>


      <!-- ══════════ 설정 탭 ══════════ -->
      <div v-else-if="activeTab === 'settings'" class="p-5 lg:p-6 flex flex-col gap-5">

        <!-- 화면 설정 -->
        <section>
          <h3 class="text-[11px] font-black uppercase tracking-[0.4em] mb-2.5 transition-colors duration-300"
              :class="localDark ? 'text-white/35' : 'text-gray-400'">화면 설정</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="localDark ? 'border-white/10' : 'border-gray-200'">
            <!-- 다크 모드 -->
            <div class="flex items-center justify-between p-4 transition-colors duration-300 border-b"
                 :class="localDark ? 'bg-white/5 border-white/8' : 'bg-white border-gray-100'">
              <div class="flex items-center gap-3">
                <component :is="localDark ? LucideMoon : LucideSun"
                           class="w-4 h-4"
                           :class="localDark ? 'text-blue-400' : 'text-amber-500'"/>
                <div>
                  <p class="text-sm font-bold">다크 모드</p>
                  <p class="text-[12px] mt-0.5 transition-colors duration-300"
                     :class="localDark ? 'text-white/40' : 'text-gray-400'">어두운 배경으로 전환합니다</p>
                </div>
              </div>
              <button
                @click="localDark = !localDark"
                class="w-11 h-6 rounded-full transition-all duration-300 relative flex-shrink-0 focus:outline-none"
                :class="localDark ? 'bg-blue-500' : 'bg-gray-300'"
              >
                <span
                  class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300"
                  :class="localDark ? 'left-[22px]' : 'left-0.5'"
                ></span>
              </button>
            </div>
            <!-- 메뉴바 고정 -->
            <div class="flex items-center justify-between p-4 transition-colors duration-300"
                 :class="localDark ? 'bg-white/5' : 'bg-white'">
              <div class="flex items-center gap-3">
                <span class="text-[16px]">📌</span>
                <div>
                  <p class="text-sm font-bold">메뉴바 고정</p>
                  <p class="text-[12px] mt-0.5 transition-colors duration-300"
                     :class="localDark ? 'text-white/40' : 'text-gray-400'">지갑 바·포트폴리오 카드를 항상 표시합니다</p>
                </div>
              </div>
              <button
                @click="$emit('toggle-menu-lock')"
                class="w-11 h-6 rounded-full transition-all duration-300 relative flex-shrink-0 focus:outline-none"
                :class="menuBarLocked ? 'bg-amber-500' : (localDark ? 'bg-white/15' : 'bg-gray-300')"
              >
                <span
                  class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300"
                  :class="menuBarLocked ? 'left-[22px]' : 'left-0.5'"
                ></span>
              </button>
            </div>
          </div>
        </section>

        <!-- 알림 설정 -->
        <section>
          <h3 class="text-[11px] font-black uppercase tracking-[0.4em] mb-2.5 transition-colors duration-300"
              :class="localDark ? 'text-white/35' : 'text-gray-400'">알림 설정</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="localDark ? 'border-white/10' : 'border-gray-200'">
            <div
              v-for="(notif, idx) in notifications" :key="notif.key"
              class="flex items-center justify-between p-4 transition-colors duration-300"
              :class="[
                localDark ? 'bg-white/5' : 'bg-white',
                idx < notifications.length - 1 ? (localDark ? 'border-b border-white/10' : 'border-b border-gray-100') : ''
              ]"
            >
              <div>
                <p class="text-sm font-bold">{{ notif.label }}</p>
                <p class="text-[12px] mt-0.5 transition-colors duration-300"
                   :class="localDark ? 'text-white/40' : 'text-gray-400'">{{ notif.desc }}</p>
              </div>
              <button
                @click="notif.enabled = !notif.enabled"
                class="w-11 h-6 rounded-full transition-all duration-300 relative flex-shrink-0 focus:outline-none"
                :class="notif.enabled ? 'bg-blue-500' : (localDark ? 'bg-white/15' : 'bg-gray-300')"
              >
                <span
                  class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300"
                  :class="notif.enabled ? 'left-[22px]' : 'left-0.5'"
                ></span>
              </button>
            </div>
          </div>
        </section>

        <!-- 앱 정보 -->
        <section>
          <h3 class="text-[11px] font-black uppercase tracking-[0.4em] mb-2.5 transition-colors duration-300"
              :class="localDark ? 'text-white/35' : 'text-gray-400'">앱 정보</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="localDark ? 'border-white/10' : 'border-gray-200'">
            <div
              v-for="(item, idx) in appInfo" :key="item.label"
              class="flex justify-between items-center p-4 transition-colors duration-300"
              :class="[
                localDark ? 'bg-white/5' : 'bg-white',
                idx < appInfo.length - 1 ? (localDark ? 'border-b border-white/10' : 'border-b border-gray-100') : ''
              ]"
            >
              <span class="text-sm font-medium transition-colors duration-300"
                    :class="localDark ? 'text-white/55' : 'text-gray-500'">{{ item.label }}</span>
              <span class="text-sm font-bold">{{ item.value }}</span>
            </div>
          </div>
        </section>

        <!-- 연결된 소셜 계정 -->
        <section>
          <h3 class="text-[11px] font-black uppercase tracking-[0.4em] mb-2.5 transition-colors duration-300"
              :class="localDark ? 'text-white/35' : 'text-gray-400'">연결된 소셜 계정</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="localDark ? 'border-white/10' : 'border-gray-200'">
            <div
              v-for="(provider, idx) in socialProviders" :key="provider.id"
              class="flex items-center justify-between p-4 transition-colors duration-300"
              :class="[
                localDark ? 'bg-white/5' : 'bg-white',
                idx < socialProviders.length - 1 ? (localDark ? 'border-b border-white/10' : 'border-b border-gray-100') : ''
              ]"
            >
              <div class="flex items-center gap-3">
                <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                     :style="{ background: provider.bgColor }">
                  <span v-html="provider.icon"></span>
                </div>
                <div>
                  <p class="text-sm font-bold">{{ provider.label }}</p>
                  <p class="text-[12px] transition-colors duration-300"
                     :class="provider.linked ? 'text-green-500' : (localDark ? 'text-white/30' : 'text-gray-400')"
                  >{{ provider.linked ? '연결됨' : '연결되지 않음' }}</p>
                </div>
              </div>
              <button
                @click="handleSocialConnect(provider)"
                :disabled="provider.loading"
                class="px-3 py-1.5 rounded-lg text-[12px] font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                :class="provider.linked
                  ? (localDark ? 'bg-red-500/10 border border-red-500/25 text-red-400 hover:bg-red-500/20' : 'bg-red-50 border border-red-200 text-red-500 hover:bg-red-100')
                  : (localDark ? 'bg-white/5 border border-white/10 text-white/60 hover:bg-white/10' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50')"
              >
                {{ provider.loading ? '처리 중...' : (provider.linked ? '연결 해제' : '연결하기') }}
              </button>
            </div>
          </div>
          <p v-if="socialError" class="text-[11px] text-red-400/80 px-1 mt-1.5">{{ socialError }}</p>
        </section>

        <!-- 계정 -->
        <section>
          <h3 class="text-[11px] font-black uppercase tracking-[0.4em] mb-2.5 transition-colors duration-300"
              :class="localDark ? 'text-white/35' : 'text-gray-400'">계정</h3>
          <div class="rounded-xl border overflow-hidden transition-colors duration-300"
               :class="localDark ? 'border-white/10' : 'border-gray-200'">

            <!-- 로그인 정보 -->
            <div class="flex items-center justify-between p-4 transition-colors duration-300"
                 :class="[localDark ? 'bg-white/5 border-b border-white/10' : 'bg-white border-b border-gray-100']">
              <div class="flex items-center gap-3">
                <LucideLogOut class="w-4 h-4 flex-shrink-0" :class="localDark ? 'text-white/40' : 'text-gray-400'"/>
                <div>
                  <p class="text-sm font-bold">{{ auth.nickname || '사용자' }}</p>
                  <p class="text-[12px] mt-0.5 transition-colors duration-300"
                     :class="localDark ? 'text-white/38' : 'text-gray-400'">현재 로그인 중</p>
                </div>
              </div>
              <span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-green-500/15 text-green-500 border border-green-500/25">
                ACTIVE
              </span>
            </div>

            <!-- 로그아웃 버튼 -->
            <div class="p-4 transition-colors duration-300"
                 :class="localDark ? 'bg-white/5' : 'bg-white'">
              <button
                @click="handleLogout"
                :disabled="logoutLoading"
                class="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 border"
                :class="logoutLoading
                  ? 'opacity-50 cursor-not-allowed border-red-500/20 text-red-400/50'
                  : (localDark
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
      <!-- /설정 탭 -->

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { LucideHome, LucideInfo, LucideSettings, LucideMoon, LucideSun, LucideLogOut } from 'lucide-vue-next';
import authApi  from '@/api/auth.js';
import dbapi    from '@/api/dbapi.js';
import { stocksApi } from '@/api/stocks.js';
import { useAuthStore } from '@/stores/auth.js';

defineProps({
  user:          { type: Object,  default: () => ({}) },
  menuBarLocked: { type: Boolean, default: false },
});
const emit = defineEmits(['navigate', 'toggle-menu-lock']);

// 신분증 테마: 로컬 다크모드 (기본 OFF = 라이트)
const localDark = ref(false);

const auth = useAuthStore();

// ── 탭 ──────────────────────────────────────────────────────
const activeTab = ref('home');
const TABS = [
  { id: 'home',     label: '홈',    icon: LucideHome     },
  { id: 'info',     label: '회원정보', icon: LucideInfo  },
  { id: 'settings', label: '설정',  icon: LucideSettings },
];

// ── 추천 종목 데이터 ─────────────────────────────────────────
const recommendations = ref([]);
const recLoading      = ref(true);
const recDate         = ref('');
const activeRecTab    = ref('A');

const recTabs = [
  { id: 'A',   label: 'A 티어' },
  { id: 'B',   label: 'B 티어' },
  { id: 'all', label: 'TOP 10' },
];

const filteredRecs = computed(() => {
  if (activeRecTab.value === 'all') return recommendations.value.slice(0, 10);
  return recommendations.value.filter(r => r.tier === activeRecTab.value).slice(0, 8);
});

const marketScore = computed(() => {
  if (!recommendations.value.length) return 0;
  const top = recommendations.value.slice(0, 50);
  return Math.round(top.reduce((s, r) => s + (r.score ?? 0), 0) / top.length);
});

const marketLabel = computed(() => {
  const s = marketScore.value;
  if (s >= 80) return '강세 🔥';
  if (s >= 65) return '양호 📈';
  if (s >= 50) return '보통 ➡️';
  if (s >= 35) return '약세 📉';
  return '침체 ❄️';
});

// ── 섹터 데이터 ──────────────────────────────────────────────
const sectors        = ref([]);
const sectorsLoading = ref(true);

// ── 지수 (placeholder) ───────────────────────────────────────
const indices = [
  { name: 'KOSPI',   value: '2,504',  change: '+12.3', up: true  },
  { name: 'KOSDAQ',  value: '721',    change: '-3.2',  up: false },
  { name: 'USD/KRW', value: '1,365',  change: '+2.5',  up: true  },
  { name: 'KP200',   value: '332',    change: '+1.8',  up: true  },
  { name: 'WTI',     value: '78.6',   change: '-0.3',  up: false },
];

// ── 주요 기능 CTA ─────────────────────────────────────────────
const ctas = [
  { id: 'stocks',    icon: '⭐', label: 'AI 추천 종목',  sub: 'ML 모델이 선별한 오늘의 추천',   target: 'company'   },
  { id: 'portfolio', icon: '💼', label: '포트폴리오',     sub: '보유 종목 관리 및 수익률 분석',  target: 'portfolio' },
  { id: 'feed',      icon: '📰', label: '뉴스 피드',      sub: 'AI 요약 주요 경제 뉴스',        target: 'feed'      },
];

// ── FAQ ───────────────────────────────────────────────────────
const activeFaq    = ref(null);
const activeFaqCat = ref('ai');

const faqCategories = [
  { id: 'ai',      label: 'AI 점수'  },
  { id: 'screener', label: '종목 탐색' },
  { id: 'chart',   label: '차트/재무' },
];

const faqs = {
  ai: [
    { id: 'f1', q: 'AI 점수는 어떻게 계산되나요?',
      a: 'LightGBM, XGBoost, CatBoost 앙상블 모델의 예측 확률 평균을 날짜별 퍼센타일 랭킹(1~100)으로 환산합니다. 80점 이상은 A티어, 60~79점은 B티어입니다.' },
    { id: 'f2', q: '티어 기준은 무엇인가요?',
      a: 'A티어: 80점 이상, B티어: 60~79점, C티어: 40~59점, D티어: 40점 미만. ML 앙상블 점수 기준으로 자동 분류됩니다.' },
    { id: 'f3', q: '데이터는 언제 업데이트되나요?',
      a: '모델 예측 데이터는 사전 계산되어 DuckDB에 저장됩니다. 신규 데이터 적재 후 precompute 스크립트를 실행하면 반영됩니다.' },
  ],
  screener: [
    { id: 'f4', q: '종목 탐색에서 어떤 조건을 설정할 수 있나요?',
      a: 'ML 점수, 티어, 섹터, 기준일, 최소 점수 등 다양한 조건을 복합 적용할 수 있습니다.' },
    { id: 'f5', q: '정렬 기준을 바꿀 수 있나요?',
      a: '점수(기본), 섹터, 티어 기준으로 필터링이 가능하며 상위 종목만 확인할 수 있습니다.' },
  ],
  chart: [
    { id: 'f6', q: '차트에서 어떤 정보를 볼 수 있나요?',
      a: '종목별 주가 차트, ML 점수 이력, 재무 데이터를 확인할 수 있습니다.' },
    { id: 'f7', q: '조회 가능한 기간은 얼마나 되나요?',
      a: 'DuckDB에 적재된 데이터 기간 전체를 조회할 수 있습니다.' },
  ],
};

const currentFaqs = computed(() => faqs[activeFaqCat.value] ?? []);

function toggleFaq(id) {
  activeFaq.value = activeFaq.value === id ? null : id;
}

// ── 티어 스타일 헬퍼 ─────────────────────────────────────────
function tierBg(tier) {
  const c = { A: 'bg-emerald-400/15 text-emerald-400', B: 'bg-blue-400/15 text-blue-400', C: 'bg-amber-400/15 text-amber-400', D: 'bg-red-400/15 text-red-400' };
  return c[tier] ?? 'bg-white/10 text-white/50';
}

function tierBadgeClass(tier) {
  const c = { A: 'bg-emerald-400/20 text-emerald-400', B: 'bg-blue-400/20 text-blue-400', C: 'bg-amber-400/20 text-amber-400', D: 'bg-red-400/20 text-red-400' };
  return c[tier] ?? 'bg-white/10 text-white/40';
}

// ── API 로드 ─────────────────────────────────────────────────
async function loadRecommendations() {
  recLoading.value = true;
  try {
    const { data } = await stocksApi.getRecommendations({ top_k: 100 });
    recommendations.value = data.items ?? [];
    recDate.value = data.date ?? '';
  } catch {
    recommendations.value = [];
  } finally {
    recLoading.value = false;
  }
}

async function loadSectors() {
  sectorsLoading.value = true;
  try {
    const { data } = await stocksApi.getSectorsSummary();
    sectors.value = (data.items ?? []).slice(0, 6);
  } catch {
    sectors.value = [];
  } finally {
    sectorsLoading.value = false;
  }
}

onMounted(() => {
  loadRecommendations();
  loadSectors();
});

// ── 로그아웃 ─────────────────────────────────────────────────
const logoutLoading = ref(false);

async function handleLogout() {
  if (logoutLoading.value) return;
  logoutLoading.value = true;
  try {
    await authApi.logout(auth.token);
  } catch { /* 실패해도 로컬 처리 진행 */ } finally {
    auth.logout();
    logoutLoading.value = false;
  }
}

// ── 회원정보 섹션 ────────────────────────────────────────────
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

// ── 앱 정보 ──────────────────────────────────────────────────
const appInfo = [
  { label: '버전',     value: 'v0.0.3'            },
  { label: '빌드일',   value: '2026.05.09'         },
  { label: '라이선스', value: 'WP Capstone © 2026' },
];

// ── 알림 설정 ────────────────────────────────────────────────
const notifications = reactive([
  { key: 'price', label: '시세 알림',    desc: '관심 종목 등락률 알림',   enabled: true  },
  { key: 'news',  label: '뉴스 알림',    desc: '주요 경제 뉴스 알림',     enabled: true  },
  { key: 'trade', label: '자동매매 알림', desc: '퀀트 자동매매 체결 알림', enabled: false },
]);

// ── 소셜 계정 연동 ────────────────────────────────────────────
const socialError = ref('');

const socialProviders = reactive([
  {
    id: 'google', label: 'Google', bgColor: '#fff', linked: false, loading: false,
    icon: `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>`,
  },
  {
    id: 'kakao', label: '카카오', bgColor: '#FEE500', linked: false, loading: false,
    icon: `<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg"><path d="M12 3C6.477 3 2 6.477 2 10.5c0 2.584 1.574 4.857 3.969 6.22l-.994 3.695a.375.375 0 0 0 .553.415L9.86 18.54A11.578 11.578 0 0 0 12 18c5.523 0 10-3.477 10-7.5S17.523 3 12 3z" fill="#3C1E1E"/></svg>`,
  },
  {
    id: 'naver', label: '네이버', bgColor: '#03C75A', linked: false, loading: false,
    icon: `<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg"><path d="M13.6 12.4 10.1 7H7v10h3.4v-5.4L14 17H17V7h-3.4z" fill="white"/></svg>`,
  },
]);

async function handleSocialConnect(provider) {
  if (provider.loading) return;
  socialError.value = '';
  provider.loading  = true;
  try {
    if (provider.linked) {
      provider.linked  = false;
      provider.loading = false;
      return;
    }
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
    const popup = window.open(`https://kauth.kakao.com/oauth/authorize?response_type=code&client_id=${import.meta.env.VITE_KAKAO_REST_KEY}&redirect_uri=${encodeURIComponent('http://localhost:8000/auth/kakao/callback')}`, 'kakao_link', 'width=500,height=600');
    const timer = setInterval(() => { if (popup?.closed) { clearInterval(timer); reject(new Error('창이 닫혔습니다.')); } }, 500);
    window.addEventListener('message', function handler(e) {
      if (e.origin !== 'http://localhost:8000') return;
      clearInterval(timer); window.removeEventListener('message', handler); popup?.close();
      if (e.data?.access_token) resolve(e.data.access_token); else reject(new Error('토큰 수신 실패'));
    });
  });
}
function getNaverToken() {
  return new Promise((resolve, reject) => {
    const state = Math.random().toString(36).substring(2);
    const popup = window.open(`https://nid.naver.com/oauth2.0/authorize?response_type=code&client_id=${import.meta.env.VITE_NAVER_CLIENT_ID}&redirect_uri=${encodeURIComponent('http://localhost:8000/auth/naver/callback')}&state=${state}`, 'naver_link', 'width=500,height=600');
    const timer = setInterval(() => { if (popup?.closed) { clearInterval(timer); reject(new Error('창이 닫혔습니다.')); } }, 500);
    window.addEventListener('message', function handler(e) {
      if (e.origin !== 'http://localhost:8000') return;
      clearInterval(timer); window.removeEventListener('message', handler); popup?.close();
      if (e.data?.access_token) resolve(e.data.access_token); else reject(new Error('토큰 수신 실패'));
    });
  });
}
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
