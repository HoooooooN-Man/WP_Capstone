<template>
  <div class="card-wallet w-full min-h-screen flex flex-col items-center justify-end relative font-sans overflow-hidden pb-0 transition-colors duration-300"
       :class="darkMode ? 'text-white' : 'text-gray-900'">

    <!-- 배경 -->
    <div class="fixed inset-0 z-[-1] overflow-hidden transition-colors duration-500"
         :class="darkMode ? 'bg-gradient-to-br from-[#0a0804] via-[#060402] to-[#0d0a05]' : 'bg-gradient-to-br from-[#f0ebe0] via-[#e8e0d0] to-[#ede6d8]'">
      <template v-if="darkMode">
        <div class="absolute w-[140vw] h-[80vh] bg-[#2a1e08] rounded-full blur-[160px] -top-[20vh] left-0 opacity-25"></div>
        <div class="absolute w-[100vw] h-[60vh] bg-[#1a1208] rounded-full blur-[120px] -bottom-[10vh] right-0 opacity-20"></div>
        <div class="absolute w-[60vw] h-[60vh] bg-[#3a2a0a] rounded-full blur-[100px] top-[20vh] right-[10vw] opacity-10"></div>
        <div class="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/30"></div>
      </template>
      <template v-else>
        <div class="absolute w-[140vw] h-[80vh] bg-[#e8d5b0] rounded-full blur-[160px] -top-[20vh] left-0 opacity-50"></div>
        <div class="absolute w-[100vw] h-[60vh] bg-[#d4c090] rounded-full blur-[120px] -bottom-[10vh] right-0 opacity-30"></div>
        <div class="absolute w-[60vw] h-[60vh] bg-[#f0e0c0] rounded-full blur-[100px] top-[20vh] right-[10vw] opacity-25"></div>
      </template>
    </div>

    <!-- 메인 컨텐츠 -->
    <!-- absolute 래퍼 안에 각 뷰가 absolute inset-0으로 겹침 → mode 없이 동시 fade 가능 -->
    <!-- 고정 모드(비포트폴리오)일 때 지갑 바(100px)와 겹치지 않도록 bottom 확보 -->
    <div class="absolute inset-0 z-0 overflow-hidden">
      <transition name="fade-scale">
        <ProfileView   v-if="activeCard === 'profile'"   key="profile"
          class="absolute inset-0"
          :user="user" :menu-bar-locked="menuBarLocked" :dark-mode="darkMode"
          @toggle-menu-lock="toggleMenuLock"
          @navigate="activeCard = $event" />
        <FlashCardView v-else-if="activeCard === 'feed'" key="feed"
          class="absolute inset-0" :dark-mode="darkMode" />
        <CompanyView   v-else-if="activeCard === 'company'" key="company"
          class="absolute inset-0"
          :dark-mode="darkMode"
          :replace-mode="replaceMode"
          :replace-stock="replaceStock"
          :view-ticker="viewTicker"
          @select-company="handleCompanySelect"
          @add-company="handleCompanyAdd"
          @back="handleCompanyBack"
          @sell-replace="handleSellReplace"
          @cancel-replace="handleCancelReplace"
        />
        <PortfolioView v-else-if="activeCard === 'portfolio'" key="portfolio"
          class="absolute inset-0"
          :dark-mode="darkMode"
          :portfolio-groups="portfolioGroups"
          :active-group-id="activeGroupId"
          v-model:current-index="portfolioCurrentIndex"
          @view-company="handleViewCompany"
          @switch-group="activeGroupId = $event; portfolioCurrentIndex = 0"
          @add-portfolio="addPortfolio"
          @rename-group="(e) => handleRenameGroup(e.id, e.name)"
        />
        <BoardView v-else-if="activeCard === 'board'" key="board"
          class="absolute inset-0" />
        <div v-else key="standby" class="absolute inset-0 flex items-center justify-center animate-fade-in-delayed">
          <h2 class="text-4xl font-black italic tracking-tighter text-white uppercase opacity-20">{{ activeCard }} MODULE STANDBY</h2>
        </div>
      </transition>
    </div>

    <!-- 바닥 호버 트리거 — 고정이거나 포트폴리오 모드엔 비활성 -->
    <div v-show="!menuBarLocked && activeCard !== 'portfolio'"
         class="fixed bottom-0 left-0 right-0 h-4 z-20"
         @mouseenter="walletVisible = true"></div>

    <!-- 지갑 바 + 게시판 버튼 — 포트폴리오 모드엔 숨김, 함께 슬라이드 -->
    <div v-show="activeCard !== 'portfolio'"
         class="fixed bottom-0 left-0 right-0 z-10"
         :style="{
           transform: (menuBarLocked || walletVisible) ? 'translateY(16px)' : 'translateY(calc(100% + 14px))',
           transition: 'transform 0.38s cubic-bezier(0.32, 0, 0.2, 1)'
         }"
         @mouseleave="!menuBarLocked && !portfolioDropOpen && (walletVisible = false)">

      <!-- 게시판 버튼 — 우측 하단 -->
      <button
        class="absolute bottom-[22px] right-4 z-30 flex flex-col items-center gap-1 px-3 py-2 rounded-2xl border transition-all duration-200 shadow-lg"
        :class="activeCard === 'board'
          ? 'border-[rgba(201,162,39,0.45)] text-[rgba(201,162,39,0.9)]'
          : 'border-white/10 text-white/40 hover:text-white/65 hover:border-white/20'"
        :style="activeCard === 'board'
          ? 'background: rgba(201,162,39,0.14);'
          : 'background: rgba(20,14,6,0.75);'"
        @click="activeCard = activeCard === 'board' ? 'feed' : 'board'"
      >
        <LucideLayoutList class="w-4 h-4" />
        <span class="text-[10px] font-bold tracking-wide leading-none">게시판</span>
      </button>

      <!-- 지갑 바 -->
      <div class="flex justify-center">
      <div class="wallet-bar relative z-10 w-full max-w-[860px] rounded-t-[2rem] overflow-visible flex border-t"
           style="border-color: rgba(201,162,39,0.38)">


        <!-- ── 중앙 부드러운 접힘 (선 없이 그라디언트 그림자만) ── -->
        <div class="absolute left-1/2 -translate-x-1/2 inset-y-0 pointer-events-none z-[10]"
             style="width: 52px">
          <!-- 왼쪽 페이지 끝 → 중심으로 어두워짐 -->
          <div class="absolute left-0 inset-y-0 w-1/2 rounded-r-none"
               style="background: linear-gradient(to right, transparent 0%, rgba(0,0,0,0.42) 100%)"></div>
          <!-- 오른쪽 페이지 끝 → 중심으로 어두워짐 -->
          <div class="absolute right-0 inset-y-0 w-1/2"
               style="background: linear-gradient(to left, transparent 0%, rgba(0,0,0,0.42) 100%)"></div>
        </div>

        <!-- ── 카드 슬롯 ── -->
        <div class="w-full h-full flex relative z-10">

          <!-- 왼쪽 열 -->
          <div class="flex-1 flex flex-col items-center pt-0 pb-2 gap-0">

            <!-- 슬롯 1: Feed (디폴트) -->
            <div class="w-[80%] flex-1 relative">
              <div
                @click="activeCard = 'feed'"
                class="absolute top-0 left-[3px] right-[3px] bottom-0 rounded-t-[10px] transition-transform duration-300 cursor-pointer overflow-hidden flex flex-col justify-center px-3"
                style="background:#ccc8c0; background-image:repeating-linear-gradient(0deg,transparent,transparent 10px,rgba(0,0,0,0.03) 10px,rgba(0,0,0,0.03) 11px);"
                :class="activeCard === 'feed' ? '-translate-y-1' : 'hover:-translate-y-1'"
              >
                <span class="text-[8px] uppercase tracking-widest leading-none mb-0.5" style="color:#777; font-family:sans-serif; border-bottom:1px solid rgba(0,0,0,0.2); padding-bottom:2px;">AI Intelligence</span>
                <span class="font-black leading-tight tracking-tight" style="font-size:15px; color:#1a1209; font-family:Georgia,'Times New Roman',serif;">GAZETTE</span>
              </div>
              <div class="absolute bottom-0 w-full h-[4px] bg-[#090705] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] pointer-events-none rounded-b-sm"></div>
            </div>

            <!-- 슬롯 2: Profile (기어 버튼 포함) -->
            <div class="w-[80%] flex-1 relative">
              <div
                @click="activeCard = 'profile'"
                class="absolute top-0 left-[3px] right-[3px] bottom-0 rounded-t-[10px] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2.5 overflow-hidden"
                style="background: linear-gradient(135deg, #f7f4ee 0%, #e8e2d4 100%);"
                :class="activeCard === 'profile' ? '-translate-y-2' : 'hover:-translate-y-2'"
              >
                <div class="w-6 h-6 rounded bg-black/6 flex items-center justify-center flex-shrink-0">
                  <LucideUser class="w-3.5 h-3.5 text-black/55" />
                </div>
                <div class="flex flex-col justify-center min-w-0 flex-1">
                  <span class="text-[15px] font-bold text-gray-800 leading-tight truncate">{{ user.name || 'User' }}</span>
                  <span class="text-[10px] font-bold text-gray-400 leading-tight tracking-widest uppercase" style="font-family:sans-serif;">Personal ID</span>
                </div>
                <!-- 설정 기어 버튼 -->
                <button @click.stop="showSettings = true"
                        class="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full transition-all hover:bg-black/10"
                        style="color:rgba(0,0,0,0.3)">
                  <LucideSettings class="w-3.5 h-3.5" />
                </button>
              </div>
              <div class="absolute bottom-0 left-0 right-0 h-[8px] pointer-events-none z-[24]"
                   style="background: linear-gradient(to bottom, #181208, #0f0c06)"></div>
              <div class="absolute bottom-[8px] w-full h-[4px] bg-[#090705] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-[25] pointer-events-none rounded-b-sm"></div>
            </div>

          </div>

          <!-- 오른쪽 열 -->
          <div class="flex-1 flex flex-col items-center pt-0 pb-2 gap-0">

            <!-- 슬롯 3: Company -->
            <div class="w-[80%] flex-1 relative">
              <div
                @click="activeCard = 'company'"
                class="absolute top-0 left-[3px] right-[3px] bottom-0 rounded-t-[10px] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2 overflow-hidden"
                :style="`background:${darkMode ? '#0f1e3d' : '#1a3a6b'};`"
                :class="activeCard === 'company' ? '-translate-y-1' : 'hover:-translate-y-1'"
              >
                <LucideBuilding2 class="w-4 h-4 flex-shrink-0" style="color:rgba(201,162,39,0.7);" />
                <div class="flex flex-col justify-center min-w-0">
                  <span class="text-[9px] font-bold tracking-widest uppercase leading-none" style="color:rgba(201,162,39,0.55);font-family:sans-serif;">Market</span>
                  <span class="text-[15px] font-black leading-tight tracking-tight" style="color:#f0ebe0;font-family:Georgia,serif;">ANALYSIS</span>
                </div>
              </div>
              <div class="absolute bottom-0 w-full h-[4px] bg-[#090705] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] pointer-events-none rounded-b-sm"></div>
            </div>

            <!-- 슬롯 4: Portfolio (드롭다운 포함) -->
            <div class="w-[80%] flex-1 relative">
              <div
                class="absolute top-0 left-[3px] right-[3px] bottom-0 rounded-t-[10px] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2 overflow-visible"
                style="background:linear-gradient(135deg,#e8c87c 0%,#d4a853 100%);"
                :class="activeCard === 'portfolio' || portfolioDropOpen ? '-translate-y-2' : 'hover:-translate-y-2'"
                @click="activeCard = 'portfolio'"
              >
                <!-- 왼쪽: PORTFOLIO 레이블 (페이지 이동) -->
                <LucideFolder class="w-4 h-4 flex-shrink-0" style="color:#5c3d0e;opacity:0.8;" />
                <div class="flex flex-col justify-center min-w-0">
                  <span class="text-[9px] font-bold tracking-widest uppercase leading-none" style="color:rgba(92,61,14,0.6);font-family:sans-serif;">My</span>
                  <span class="text-[15px] font-black leading-tight" style="color:#3d2208;">PORTFOLIO</span>
                </div>

                <!-- 오른쪽: 셀렉트박스형 드롭다운 -->
                <div class="flex items-center gap-1.5 ml-auto relative flex-shrink-0 px-2 py-1 rounded-lg cursor-pointer transition-all"
                     style="background:rgba(0,0,0,0.12); border:1px solid rgba(0,0,0,0.15); max-width:120px;"
                     @click.stop="openPortfolioDrop">
                  <span class="text-[11px] font-bold truncate" style="color:#3d2208; max-width:80px;">
                    {{ activeGroup?.name ?? '포트폴리오 1' }}
                  </span>
                  <LucideChevronDown class="w-3 h-3 flex-shrink-0 transition-transform"
                                     :class="portfolioDropOpen ? 'rotate-180' : ''"
                                     style="color:rgba(61,34,8,0.55)" />

                  <!-- 드롭다운 메뉴 (위로 열림) -->
                  <div v-if="portfolioDropOpen"
                       class="absolute bottom-full right-0 mb-2 rounded-xl shadow-2xl z-[200] overflow-hidden"
                       style="min-width:200px; background:#1e1a12; border:1px solid rgba(201,162,39,0.3);"
                       @click.stop
                       @mouseenter="walletVisible = true">
                    <div class="px-3 py-2" style="border-bottom:1px solid rgba(255,255,255,0.08);">
                      <p class="text-[10px] font-bold uppercase tracking-widest" style="color:rgba(201,162,39,0.7);">포트폴리오 선택</p>
                    </div>
                    <div v-for="group in portfolioGroups" :key="group.id"
                         class="flex items-center gap-2 px-3 py-2.5 cursor-pointer hover:bg-white/8 transition-colors"
                         @click="switchPortfolio(group.id)">
                      <LucideCheck v-if="group.id === activeGroupId" class="w-3.5 h-3.5 flex-shrink-0" style="color:#c9a227;" />
                      <span v-else class="w-3.5 h-3.5 flex-shrink-0"></span>
                      <span class="text-[13px] font-bold text-white flex-1 truncate">{{ group.name }}</span>
                      <span class="text-[10px]" style="color:rgba(255,255,255,0.3);">{{ group.stocks.length }}종목</span>
                    </div>
                    <button class="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-white/8 transition-colors"
                            style="border-top:1px solid rgba(255,255,255,0.08);"
                            @click="addPortfolio">
                      <LucidePlus class="w-3.5 h-3.5" style="color:#c9a227;" />
                      <span class="text-[13px] font-bold" style="color:#c9a227;">포트폴리오 추가</span>
                    </button>
                  </div>
                </div>
              </div>
              <div class="absolute bottom-0 left-0 right-0 h-[8px] pointer-events-none z-[24]"
                   style="background: linear-gradient(to bottom, #181208, #0f0c06)"></div>
              <div class="absolute bottom-[8px] w-full h-[4px] bg-[#090705] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-[25] pointer-events-none rounded-b-sm"></div>
            </div>

          </div>
        </div>

      </div><!-- /wallet-bar -->
      </div><!-- /flex justify-center -->
    </div><!-- /지갑 바 + 게시판 wrapper -->

    <!-- ── 포트폴리오 팬 스트립 ── -->
    <div v-if="activeCard === 'portfolio'"
         class="fixed left-0 right-0 z-10"
         style="height:240px; bottom:-18px">
      <PortfolioFanStrip
        :dark-mode="darkMode"
        :display-items="portfolioDisplayItems"
        :current-index="portfolioCurrentIndex"
        :total-value="portfolioTotalValue"
        :total-return="portfolioTotalReturn"
        :active-stocks-count="portfolioActiveStocks.length"
        :auto-trade-state="autoTradeState"
        :wallet-locked="menuBarLocked"
        @update:current-index="portfolioCurrentIndex = $event"
        @fan-open="portfolioFanOpen = $event"
        @back="handlePortfolioBack"
        @liquidate="handlePortfolioLiquidate"
        @replace="handleReplace"
        @view-company="handleViewCompany"
        @toggle-auto-trade="handleToggleAutoTrade"
      />
    </div>

    <!-- 자동매매 결과 (포트폴리오 팬 바로 위) -->
    <transition name="trade-log">
      <div v-if="tradeLog && activeCard === 'portfolio'"
           class="fixed z-40 left-4 right-4 rounded-xl border border-white/10 overflow-hidden text-[12px] text-white"
           style="bottom:218px;background:linear-gradient(135deg,#0a1e0e,#0d1a0a)">
        <div class="px-3 py-1.5 border-b border-white/10 flex items-center gap-1.5">
          <div class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></div>
          <p class="text-[10px] text-green-400 font-bold uppercase tracking-widest">자동매매 완료</p>
        </div>
        <div class="px-3 py-1.5 space-y-0.5">
          <div v-if="tradeLog.bought.length" class="flex gap-2">
            <span class="text-blue-400 font-black flex-shrink-0">추가</span>
            <span class="text-white/55">{{ tradeLog.bought.join(', ') }}</span>
          </div>
          <div v-if="tradeLog.sold.length" class="flex gap-2">
            <span class="text-red-400 font-black flex-shrink-0">삭제</span>
            <span class="text-white/55">{{ tradeLog.sold.join(', ') }}</span>
          </div>
        </div>
      </div>
    </transition>

    <!-- ── 설정 오버레이 ── -->
    <transition name="settings-up">
      <div v-if="showSettings"
           class="fixed inset-0 z-[100] flex items-end"
           style="background:rgba(0,0,0,0.6)"
           @click.self="showSettings = false">
        <div class="w-full rounded-t-2xl overflow-hidden"
             style="background:#1a1209; max-height:82vh; overflow-y:auto">

          <!-- 헤더 -->
          <div class="flex items-center justify-between px-5 py-4 sticky top-0 z-10"
               style="background:#1a1209; border-bottom:1px solid rgba(255,255,255,0.1)">
            <p class="text-[15px] font-black text-white">설정</p>
            <button @click="showSettings = false" class="text-white/40 hover:text-white/70 text-xl leading-none">✕</button>
          </div>

          <!-- 화면 설정 -->
          <div class="px-5 pt-5 pb-4" style="border-bottom:1px solid rgba(255,255,255,0.08)">
            <p class="text-[10px] font-black uppercase tracking-widest text-white/35 mb-3">화면 설정</p>
            <div class="rounded-xl overflow-hidden" style="border:1px solid rgba(255,255,255,0.1)">
              <!-- 다크 모드 -->
              <div class="flex items-center justify-between p-4" style="background:rgba(255,255,255,0.05); border-bottom:1px solid rgba(255,255,255,0.08)">
                <div class="flex items-center gap-3">
                  <component :is="darkMode ? LucideMoon : LucideSun" class="w-4 h-4"
                             :class="darkMode ? 'text-blue-400' : 'text-amber-400'"/>
                  <div>
                    <p class="text-[13px] font-bold text-white">다크 모드</p>
                    <p class="text-[11px] text-white/40">어두운 배경으로 전환합니다</p>
                  </div>
                </div>
                <button @click="darkMode = !darkMode"
                        class="w-11 h-6 rounded-full transition-all duration-300 relative flex-shrink-0"
                        :class="darkMode ? 'bg-blue-500' : 'bg-white/20'">
                  <span class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300"
                        :class="darkMode ? 'left-[22px]' : 'left-0.5'"></span>
                </button>
              </div>
              <!-- 메뉴바 고정 -->
              <div class="flex items-center justify-between p-4" style="background:rgba(255,255,255,0.05)">
                <div class="flex items-center gap-3">
                  <LucideSettings class="w-4 h-4 text-white/40"/>
                  <div>
                    <p class="text-[13px] font-bold text-white">메뉴바 고정</p>
                    <p class="text-[11px] text-white/40">지갑 바를 항상 표시합니다</p>
                  </div>
                </div>
                <button @click="toggleMenuLock"
                        class="w-11 h-6 rounded-full transition-all duration-300 relative flex-shrink-0"
                        :class="menuBarLocked ? 'bg-amber-500' : 'bg-white/20'">
                  <span class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300"
                        :class="menuBarLocked ? 'left-[22px]' : 'left-0.5'"></span>
                </button>
              </div>
            </div>
          </div>

          <!-- 알림 설정 -->
          <div class="px-5 pt-5 pb-4" style="border-bottom:1px solid rgba(255,255,255,0.08)">
            <p class="text-[10px] font-black uppercase tracking-widest text-white/35 mb-3">알림 설정</p>
            <div class="rounded-xl overflow-hidden" style="border:1px solid rgba(255,255,255,0.1)">
              <div v-for="(notif, idx) in settingsNotifications" :key="notif.key"
                   class="flex items-center justify-between p-4"
                   style="background:rgba(255,255,255,0.05)"
                   :style="idx < settingsNotifications.length-1 ? 'border-bottom:1px solid rgba(255,255,255,0.08)' : ''">
                <div>
                  <p class="text-[13px] font-bold text-white">{{ notif.label }}</p>
                  <p class="text-[11px] text-white/40">{{ notif.desc }}</p>
                </div>
                <button @click="notif.enabled = !notif.enabled"
                        class="w-11 h-6 rounded-full transition-all duration-300 relative flex-shrink-0"
                        :class="notif.enabled ? 'bg-blue-500' : 'bg-white/20'">
                  <span class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300"
                        :class="notif.enabled ? 'left-[22px]' : 'left-0.5'"></span>
                </button>
              </div>
            </div>
          </div>

          <!-- 연결된 소셜 계정 -->
          <div class="px-5 pt-5 pb-4" style="border-bottom:1px solid rgba(255,255,255,0.08)">
            <p class="text-[10px] font-black uppercase tracking-widest text-white/35 mb-3">연결된 소셜 계정</p>
            <div class="rounded-xl overflow-hidden" style="border:1px solid rgba(255,255,255,0.1)">
              <div v-for="(provider, idx) in settingsSocialProviders" :key="provider.id"
                   class="flex items-center justify-between p-4"
                   style="background:rgba(255,255,255,0.05)"
                   :style="idx < settingsSocialProviders.length-1 ? 'border-bottom:1px solid rgba(255,255,255,0.08)' : ''">
                <div class="flex items-center gap-3">
                  <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                       :style="{ background: provider.bgColor }">
                    <span v-html="provider.icon"></span>
                  </div>
                  <div>
                    <p class="text-[13px] font-bold text-white">{{ provider.label }}</p>
                    <p class="text-[11px]" :class="provider.linked ? 'text-green-400' : 'text-white/35'">
                      {{ provider.linked ? '연결됨' : '연결되지 않음' }}
                    </p>
                  </div>
                </div>
                <button @click="handleSettingsSocialConnect(provider)"
                        :disabled="provider.loading"
                        class="px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all disabled:opacity-50"
                        :class="provider.linked
                          ? 'text-red-400 hover:bg-red-500/20'
                          : 'text-white/60 hover:bg-white/10'"
                        :style="provider.linked
                          ? 'background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.25)'
                          : 'background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.12)'">
                  {{ provider.loading ? '처리 중...' : (provider.linked ? '연결 해제' : '연결하기') }}
                </button>
              </div>
            </div>
            <p v-if="settingsSocialError" class="text-[11px] text-red-400/80 px-1 mt-1.5">{{ settingsSocialError }}</p>
          </div>

          <!-- 앱 정보 -->
          <div class="px-5 pt-5 pb-4" style="border-bottom:1px solid rgba(255,255,255,0.08)">
            <p class="text-[10px] font-black uppercase tracking-widest text-white/35 mb-3">앱 정보</p>
            <div class="rounded-xl overflow-hidden" style="border:1px solid rgba(255,255,255,0.1)">
              <div v-for="(item, idx) in settingsAppInfo" :key="item.label"
                   class="flex justify-between items-center p-4"
                   style="background:rgba(255,255,255,0.05)"
                   :style="idx < settingsAppInfo.length-1 ? 'border-bottom:1px solid rgba(255,255,255,0.08)' : ''">
                <span class="text-[13px] text-white/55">{{ item.label }}</span>
                <span class="text-[13px] font-bold text-white/70">{{ item.value }}</span>
              </div>
            </div>
          </div>

          <!-- 계정 + 로그아웃 -->
          <div class="px-5 pt-5 pb-6">
            <p class="text-[10px] font-black uppercase tracking-widest text-white/35 mb-3">계정</p>
            <div class="rounded-xl overflow-hidden" style="border:1px solid rgba(255,255,255,0.1)">
              <!-- 사용자 정보 -->
              <div class="flex items-center justify-between p-4"
                   style="background:rgba(255,255,255,0.05); border-bottom:1px solid rgba(255,255,255,0.08)">
                <div class="flex items-center gap-3">
                  <LucideUser class="w-4 h-4 text-white/40"/>
                  <div>
                    <p class="text-[13px] font-bold text-white">{{ auth.nickname || '사용자' }}</p>
                    <p class="text-[11px] text-white/40">현재 로그인 중</p>
                  </div>
                </div>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-bold"
                      style="background:rgba(34,197,94,0.15);color:#4ade80;border:1px solid rgba(34,197,94,0.25)">
                  ACTIVE
                </span>
              </div>
              <!-- 로그아웃 -->
              <div class="p-4" style="background:rgba(255,255,255,0.05)">
                <button @click="handleLogout"
                        class="w-full py-2.5 rounded-xl flex items-center justify-center gap-2 text-[13px] font-bold transition-all"
                        style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.25);color:#f87171">
                  <LucideLogOut class="w-4 h-4"/>
                  로그아웃
                </button>
              </div>
            </div>
          </div>

        </div>
      </div>
    </transition>

    <!-- 드롭다운 외부 클릭 닫기 -->
    <div v-if="portfolioDropOpen"
         class="fixed inset-0 z-[100]"
         @click="portfolioDropOpen = false; walletVisible = false"></div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import authApi from '@/api/auth.js'
import { LucideUser, LucideSparkles, LucideBuilding2, LucideFolder, LucideLayoutList, LucideNewspaper, LucideSettings, LucideChevronDown, LucidePlus, LucideCheck, LucideLogOut, LucideMoon, LucideSun } from 'lucide-vue-next'
import ProfileView   from '@/components/views/ProfileView.vue'
import FlashCardView from '@/components/views/FlashCardView.vue'
import CompanyView   from '@/components/views/CompanyView.vue'
import PortfolioView from '@/components/views/PortfolioView.vue'
import BoardView     from '@/components/views/BoardView.vue'
import PortfolioFanStrip from '@/components/portfolio/PortfolioFanStrip.vue'
import { useStocksStore } from '@/stores/stocks.js'
import { stocksApi } from '@/api/stocks.js'

const stocksStore = useStocksStore()

const props = defineProps({
  user: { type: Object, required: true, default: () => ({ name: '', style: '', totalAsset: '' }) }
});

const emit = defineEmits(['toggle-wallet', 'toggle-portfolio']);
const activeCard    = ref('feed');
const viewTicker    = ref(null);
const darkMode      = ref(false);
const walletVisible = ref(false);

// 메뉴바 고정 (localStorage 영속)
const menuBarLocked = ref(JSON.parse(localStorage.getItem('wp_menubar_locked') ?? 'false'))
const toggleMenuLock = () => {
  menuBarLocked.value = !menuBarLocked.value
  localStorage.setItem('wp_menubar_locked', JSON.stringify(menuBarLocked.value))
  if (menuBarLocked.value) walletVisible.value = true
}

// AI 추천 Top10 → 포트폴리오 초기 종목
const TIER_COLORS = { A: '#1D9E75', B: '#378ADD', C: '#EF9F27', D: '#E24B4A' }

// ── 설정 오버레이 ──────────────────────────────────────────────
const showSettings = ref(false)

// 알림 설정
const settingsNotifications = reactive([
  { key: 'price', label: '시세 알림',    desc: '관심 종목 등락률 알림',   enabled: true  },
  { key: 'news',  label: '뉴스 알림',    desc: '주요 경제 뉴스 알림',     enabled: true  },
  { key: 'trade', label: '자동매매 알림', desc: '퀀트 자동매매 체결 알림', enabled: false },
])

// 앱 정보
const settingsAppInfo = [
  { label: '버전',     value: 'v0.0.3'            },
  { label: '빌드일',   value: '2026.05.09'         },
  { label: '라이선스', value: 'WP Capstone © 2026' },
]

// 소셜 계정 연동
const settingsSocialError = ref('')
const settingsSocialProviders = reactive([
  {
    id: 'google', label: 'Google', bgColor: '#fff', linked: false, loading: false,
    icon: `<svg viewBox="0 0 24 24" width="14" height="14" fill="none"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>`,
  },
  {
    id: 'kakao', label: '카카오', bgColor: '#FEE500', linked: false, loading: false,
    icon: `<svg viewBox="0 0 24 24" width="14" height="14"><path d="M12 3C6.477 3 2 6.477 2 10.5c0 2.584 1.574 4.857 3.969 6.22l-.994 3.695a.375.375 0 0 0 .553.415L9.86 18.54A11.578 11.578 0 0 0 12 18c5.523 0 10-3.477 10-7.5S17.523 3 12 3z" fill="#3C1E1E"/></svg>`,
  },
  {
    id: 'naver', label: '네이버', bgColor: '#03C75A', linked: false, loading: false,
    icon: `<svg viewBox="0 0 24 24" width="14" height="14"><path d="M13.6 12.4 10.1 7H7v10h3.4v-5.4L14 17H17V7h-3.4z" fill="white"/></svg>`,
  },
])

async function handleSettingsSocialConnect(provider) {
  if (provider.loading) return
  settingsSocialError.value = ''
  provider.loading = true
  try {
    if (provider.linked) {
      provider.linked = false
    } else {
      window.location.href = `${import.meta.env.VITE_API_BASE_AUTH ?? 'http://localhost:8000'}/auth/social/login/${provider.id}`
    }
  } catch {
    settingsSocialError.value = '처리 중 오류가 발생했습니다.'
  } finally {
    provider.loading = false
  }
}

// ── 포트폴리오 드롭다운 ─────────────────────────────────────────
const portfolioDropOpen = ref(false)

const portfolioGroups = ref([
  { id: 1, name: '내 포트폴리오 1', stocks: [] }
]);
const activeGroupId = ref(1);
const activeGroup   = computed(() => portfolioGroups.value.find(g => g.id === activeGroupId.value));

const auth = useAuthStore()
async function handleLogout() {
  try { await authApi.logout() } catch {}
  auth.logout?.()
  showSettings.value = false
}

function openPortfolioDrop() {
  portfolioDropOpen.value = !portfolioDropOpen.value
  if (portfolioDropOpen.value) {
    // 메뉴바 고정이 아니어도 드롭다운 열리는 동안 유지
    walletVisible.value = true
  }
}

function switchPortfolio(id) {
  activeGroupId.value = id
  portfolioDropOpen.value = false
  activeCard.value = 'portfolio'
  walletVisible.value = false
}
function addPortfolio() {
  const nextId = Math.max(...portfolioGroups.value.map(g => g.id)) + 1
  portfolioGroups.value.push({ id: nextId, name: `내 포트폴리오 ${nextId}`, stocks: [] })
  switchPortfolio(nextId)
}

// ── 포트폴리오 팬 스트립 상태 (CardWallet 레벨로 이동) ──
const portfolioCurrentIndex = ref(0)
watch(() => activeGroupId.value, () => { portfolioCurrentIndex.value = 0 })
const portfolioFanOpen = ref(false)

const portfolioActiveStocks = computed(() => activeGroup.value?.stocks ?? [])
const portfolioDisplayItems = computed(() => [
  { isOverview: true, id: '__overview__', color: '#c9a227' },
  ...portfolioActiveStocks.value,
])
const portfolioTotalValue = computed(() =>
  portfolioActiveStocks.value.reduce((s, p) => s + p.currentPrice, 0)
)
const portfolioTotalReturn = computed(() => 0)
const handlePortfolioLiquidate = (si) => {
  handleLiquidate(si)
  if (portfolioCurrentIndex.value > 1 && portfolioCurrentIndex.value >= portfolioDisplayItems.value.length - 1)
    portfolioCurrentIndex.value--
}

onMounted(async () => {
  try {
    const { data } = await stocksApi.getRecommendations({ top_k: 10 })
    const items = data.items ?? []
    console.log('[Portfolio] AI 추천 종목:', items.length, '개', items)
    portfolioGroups.value[0].stocks = items.map((item, i) => ({
      id:           i + 1,
      company:      item.name ?? item.ticker,
      ticker:       item.ticker,
      sector:       item.sector ?? 'Market',
      currentPrice: item.close ?? 0,
      change:       0,
      color:        TIER_COLORS[item.tier ?? 'C'] ?? '#4A90E2',
      weight:       10,
      quantScore:   Math.round(item.score ?? 50),
    }))
  } catch (err) {
    console.error('[Portfolio] AI 추천 API 실패:', err?.response?.status, err?.response?.data ?? err?.message)
    portfolioGroups.value[0].stocks = []
  }
});

// 교체 모드 상태
const replaceMode  = ref(false);
const replaceIndex = ref(-1);
const replaceStock = ref(null);

// ── 포트폴리오 그룹 관리 ───────────────────────
const handleRemoveGroup = (id) => {
  const idx = portfolioGroups.value.findIndex(g => g.id === id);
  if (idx < 0 || portfolioGroups.value.length <= 1) return;
  portfolioGroups.value.splice(idx, 1);
  if (activeGroupId.value === id)
    activeGroupId.value = portfolioGroups.value[Math.max(0, idx - 1)].id;
};

const handleRenameGroup = (id, name) => {
  const g = portfolioGroups.value.find(g => g.id === id);
  if (g) g.name = name;
};

const handleSwitchGroup = (id) => { activeGroupId.value = id; };

// ── 종목 관리 ──────────────────────────────────
const handleLiquidate = (index) => {
  activeGroup.value?.stocks.splice(index, 1);
};

const handleReplace = (index) => {
  replaceIndex.value = index;
  replaceStock.value = activeGroup.value?.stocks[index] ?? null;
  replaceMode.value  = true;
  activeCard.value   = 'company';
};

const handleCompanySelect = (company) => {
  if (replaceIndex.value >= 0 && activeGroup.value)
    activeGroup.value.stocks.splice(replaceIndex.value, 1, company);
  replaceMode.value  = false;
  replaceIndex.value = -1;
  replaceStock.value = null;
  activeCard.value   = 'portfolio';
};

const handleCompanyAdd = (company) => {
  activeGroup.value?.stocks.push(company);
};

const handleSellReplace = () => {
  if (replaceIndex.value >= 0 && activeGroup.value)
    activeGroup.value.stocks.splice(replaceIndex.value, 1);
  replaceMode.value  = false;
  replaceIndex.value = -1;
  replaceStock.value = null;
  activeCard.value   = 'portfolio';
};

const handleCancelReplace = () => {
  replaceMode.value  = false;
  replaceIndex.value = -1;
  replaceStock.value = null;
  activeCard.value   = 'portfolio';
};

const handleViewCompany = (ticker) => {
  viewTicker.value  = ticker;
  activeCard.value  = 'company';
};

const handleCompanyBack = () => {
  viewTicker.value = null;
  activeCard.value = 'portfolio';
};

// 포트폴리오 뷰 → 뒤로가기 (Company List로)
const handlePortfolioBack = () => {
  activeCard.value = 'company';
};

// ── 자동매매 ───────────────────────────────────
const BUY_THRESHOLD  = 70;  // 퀀트스코어 ≥ 70 → 추가
const SELL_THRESHOLD = 45;  // 퀀트스코어 < 45 → 삭제

const autoTradeState = ref('off'); // 'off' | 'analyzing' | 'on'
const tradeLog       = ref(null);

const runAutoTrade = () => {
  const stocks = activeGroup.value?.stocks;
  if (!stocks) return;

  const bought = [];
  const sold   = [];

  // 낮은 점수 종목 삭제
  for (let i = stocks.length - 1; i >= 0; i--) {
    if ((stocks[i].quantScore ?? 50) < SELL_THRESHOLD) {
      sold.push(stocks[i].company);
      stocks.splice(i, 1);
    }
  }

  // 높은 점수 미포함 종목 추가 (실제 API 데이터만 사용)
  const currentTickers = new Set(stocks.map(s => s.ticker));
  const candidateList  = stocksStore.items
  for (const c of candidateList) {
    const score = c.quantScore ?? c.score ?? 50
    const name  = c.name ?? c.company ?? c.ticker
    if (score >= BUY_THRESHOLD && !currentTickers.has(c.ticker)) {
      bought.push(name)
      stocks.push({
        id: Date.now() + Math.random(),
        company: name, ticker: c.ticker, sector: c.sector ?? '',
        currentPrice: c.price ?? 0,
        change: c.change ?? 0, color: c.color ?? '#4A90E2', weight: 10,
        quantScore: score,
      });
    }
  }

  if (bought.length || sold.length) {
    tradeLog.value = { bought, sold };
    setTimeout(() => { tradeLog.value = null; }, 5000);
  }
};

const handleToggleAutoTrade = () => {
  if (autoTradeState.value !== 'off') {
    autoTradeState.value = 'off';
    return;
  }
  autoTradeState.value = 'analyzing';
  setTimeout(() => {
    runAutoTrade();
    autoTradeState.value = 'on';
  }, 1400);
};
</script>

<style scoped>
.settings-up-enter-active { transition: transform 0.32s cubic-bezier(0.32,0,0.2,1), opacity 0.22s ease; }
.settings-up-leave-active { transition: transform 0.22s ease, opacity 0.18s ease; }
.settings-up-enter-from   { transform: translateY(100%); opacity: 0; }
.settings-up-leave-to     { transform: translateY(100%); opacity: 0; }

.wallet-bar {
  background: linear-gradient(180deg, #1e1509 0%, #161008 55%, #191209 100%);
  box-shadow: none;
  height: 100px;
}

.animate-slide-up-wallet {
  animation: slide-up-wallet 1s var(--ease-wallet) forwards;
}

.animate-fade-in-delayed {
  opacity: 0;
  animation: fade-in-delayed 0.5s ease forwards;
}
</style>
