<template>
  <!-- 카드 루트 -->
  <div class="w-full h-full bg-gradient-to-br from-[#1f3756] to-[#14253a] rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.6)] overflow-hidden border border-white/10 text-white relative">

      <!-- ── 앞면 ── -->
      <div class="absolute inset-0 flex flex-col fin-face"
           :class="showFinancial ? 'fin-face--hide' : 'fin-face--show'">

    <!-- 헤더 -->
    <div class="px-6 pt-5 pb-3 border-b border-white/15 flex-shrink-0">
      <div class="flex items-center gap-3">
        <button
          v-if="detailCompany"
          @click="closeDetail"
          class="flex items-center gap-1 text-white/50 hover:text-white/80 transition-colors mr-1"
        >
          <LucideChevronLeft class="w-5 h-5" />
        </button>
        <h2 class="text-3xl font-black tracking-tighter uppercase">
          {{ detailCompany ? detailCompany.name : 'Company List' }}
        </h2>
        <div v-if="replaceMode && !detailCompany" class="px-2.5 py-1 bg-emerald-500/25 rounded-full border border-emerald-500/40">
          <span class="text-[10px] text-emerald-300 font-bold uppercase tracking-wider">교체 선택 중</span>
        </div>
        <!-- 재무제표 버튼: 상세 뷰 + 일반 모드 -->
        <button v-if="detailCompany && !replaceMode"
                @click="showFinancial = true"
                class="ml-auto px-2.5 py-1.5 rounded-lg bg-white/8 border border-white/15 text-[10px] text-white/55 hover:bg-white/14 hover:text-white/80 transition-all font-bold tracking-wide flex-shrink-0 flex items-center gap-1">
          <LucideBarChart2 class="w-3 h-3" />
          재무제표
        </button>
        <!-- 검색 버튼: 리스트 뷰에서만 -->
        <button v-if="!detailCompany"
                @click="showSearch = true"
                class="ml-auto w-8 h-8 flex items-center justify-center rounded-xl bg-white/8 border border-white/12 text-white/50 hover:bg-white/14 hover:text-white/80 transition-all flex-shrink-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
        </button>
      </div>
      <p v-if="replaceMode && !detailCompany" class="text-[10px] text-white/35 mt-1">교체할 종목을 선택하세요</p>
    </div>

    <!-- 탭 바: 리스트 뷰에서만 -->
    <div v-if="!detailCompany" class="px-4 pt-2.5 pb-2 flex-shrink-0">
      <div class="flex gap-1 p-1 rounded-xl" style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.07)">
        <button v-for="tab in STOCK_TABS" :key="tab.key"
                @click="switchTab(tab.key)"
                class="flex-1 py-1.5 rounded-lg text-[10px] font-bold transition-all duration-150"
                :class="activeTab === tab.key
                  ? 'bg-white/15 text-white shadow-sm'
                  : 'text-white/38 hover:text-white/65'">
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 기업 상세 뷰 — 좌우 분할 레이아웃 -->
    <div v-if="detailCompany" class="flex-1 flex flex-row overflow-hidden">

      <!-- ── 왼쪽: 주가 차트 (3/5) ── -->
      <div class="flex-[3] flex flex-col border-r border-white/10 overflow-hidden min-w-0">

        <!-- 기간 탭 -->
        <div class="flex gap-0.5 px-3 pt-3 pb-1 flex-shrink-0">
          <button v-for="p in ['1M','3M','6M','1Y']" :key="p"
                  @click="chartPeriod = p"
                  class="px-2 py-0.5 rounded text-[9px] font-bold transition-all duration-150"
                  :class="chartPeriod === p ? 'bg-white/15 text-white' : 'text-white/30 hover:text-white/55'">
            {{ p }}
          </button>
        </div>

        <!-- 최고가 -->
        <div class="px-3 flex-shrink-0">
          <span class="text-[7.5px] font-mono" style="color:rgba(255,255,255,0.22)">
            ₩{{ chartPriceRange.max.toLocaleString() }}
          </span>
        </div>

        <!-- SVG 차트 -->
        <div class="flex-1 px-2 cursor-pointer group" @click="showChart = true">
          <svg class="w-full h-full" viewBox="0 0 300 200" preserveAspectRatio="none">
            <defs>
              <linearGradient :id="`dp-${detailCompany.ticker}`" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   :stop-color="detailCompany.color" stop-opacity="0.42" />
                <stop offset="100%" :stop-color="detailCompany.color" stop-opacity="0.02" />
              </linearGradient>
            </defs>
            <path :d="detailPaths.area" :fill="`url(#dp-${detailCompany.ticker})`" />
            <path :d="detailPaths.line" fill="none"
                  :stroke="detailCompany.color" stroke-width="1.8" stroke-linejoin="round" opacity="0.92" />
          </svg>
        </div>

        <!-- 최저가 + 시작 레이블 -->
        <div class="px-3 pb-3 flex-shrink-0 flex justify-between items-end">
          <span class="text-[7.5px] font-mono" style="color:rgba(255,255,255,0.22)">
            ₩{{ chartPriceRange.min.toLocaleString() }}
          </span>
          <span class="text-[7.5px] font-mono" style="color:rgba(255,255,255,0.22)">{{ chartStartLabel }}</span>
        </div>
      </div>

      <!-- ── 오른쪽: 정보 패널 (2/5) ── -->
      <div class="flex-[2] flex flex-col overflow-hidden min-w-0">

        <!-- 스크롤 영역 -->
        <div class="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">

          <!-- 가격 + 등락 -->
          <div>
            <p class="text-[8px] uppercase tracking-widest mb-0.5" style="color:rgba(255,255,255,0.35)">
              {{ detailCompany.sector }}
            </p>
            <p class="text-xl font-black leading-tight">₩{{ detailCompany.price.toLocaleString() }}</p>
            <span class="inline-block mt-0.5 px-2 py-0.5 rounded-lg text-[10px] font-bold"
                  :class="detailCompany.change >= 0 ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'">
              {{ detailCompany.change >= 0 ? '+' : '' }}{{ detailCompany.change }}%
            </span>
          </div>

          <!-- 종목 컬러 구분선 -->
          <div class="h-px rounded-full" :style="{ background: detailCompany.color, opacity: 0.45 }"></div>

          <!-- 재무 지표 -->
          <div class="space-y-1.5">
            <div v-for="m in detailMetrics" :key="m.label" class="flex justify-between items-center">
              <span class="text-[8.5px]" style="color:rgba(255,255,255,0.38)">{{ m.label }}</span>
              <span class="text-[10px] font-bold">{{ m.value }}</span>
            </div>
          </div>

          <!-- 구분선 -->
          <div class="h-px" style="background:rgba(255,255,255,0.08)"></div>

          <!-- 포트폴리오 보유 현황 -->
          <div>
            <p class="text-[7.5px] uppercase tracking-widest mb-1.5" style="color:rgba(255,255,255,0.3)">보유 현황</p>
            <template v-if="mockHoldings.length > 0">
              <div v-for="h in mockHoldings" :key="h.portfolio"
                   class="rounded-lg p-2 mb-1.5 space-y-1"
                   style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08)">
                <div class="flex justify-between items-center">
                  <span class="text-[9px] font-bold" style="color:rgba(255,255,255,0.72)">{{ h.portfolio }}</span>
                  <span class="text-[9px] font-mono" style="color:rgba(255,255,255,0.5)">{{ h.shares }}주</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-[8px]" style="color:rgba(255,255,255,0.32)">매수단가</span>
                  <span class="text-[8.5px] font-mono">₩{{ h.avgPrice.toLocaleString() }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-[8px]" style="color:rgba(255,255,255,0.32)">평가금액</span>
                  <span class="text-[8.5px] font-bold"
                        :class="detailCompany.price >= h.avgPrice ? 'text-green-300' : 'text-red-300'">
                    ₩{{ (detailCompany.price * h.shares).toLocaleString() }}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-[8px]" style="color:rgba(255,255,255,0.32)">수익률</span>
                  <span class="text-[8.5px] font-bold"
                        :class="detailCompany.price >= h.avgPrice ? 'text-green-400' : 'text-red-400'">
                    {{ ((detailCompany.price - h.avgPrice) / h.avgPrice * 100 >= 0 ? '+' : '') }}{{ ((detailCompany.price - h.avgPrice) / h.avgPrice * 100).toFixed(1) }}%
                  </span>
                </div>
              </div>
            </template>
            <p v-else class="text-[9px]" style="color:rgba(255,255,255,0.22)">보유 없음</p>
          </div>
        </div>

        <!-- 매수 / 매도 버튼 (하단 고정) -->
        <div class="px-3 pb-3 pt-2 flex gap-1.5 flex-shrink-0 border-t border-white/8">
          <template v-if="replaceMode">
            <button @click="openCompare(detailCompany)"
              class="flex-1 py-2 rounded-xl text-xs font-bold transition-colors
                     bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30">
              교체 비교
            </button>
          </template>
          <template v-else>
            <button @click="openOrderModal(detailCompany, 'buy')"
              class="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all duration-200
                     bg-blue-500/20 border border-blue-500/40 text-blue-200 hover:bg-blue-500/35">
              매수
            </button>
            <button @click="openOrderModal(detailCompany, 'sell')"
              class="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all duration-200
                     bg-red-500/20 border border-red-500/40 text-red-200 hover:bg-red-500/35">
              매도
            </button>
          </template>
        </div>
      </div>

    </div>

    <!-- 기업 리스트 뷰 (탭) -->
    <div v-else class="flex-1 flex flex-col overflow-hidden">

      <!-- ──────────────────────────────────────
           탭 A: AI 추천 랭킹
      ────────────────────────────────────── -->
      <template v-if="activeTab === 'recommend'">

        <!-- 종목 리스트 -->
        <div class="flex-1 overflow-y-auto px-4 pb-3 space-y-2">
          <!-- 로딩 -->
          <div v-if="screenerStore.loading" class="flex items-center justify-center h-20 gap-2">
            <div class="w-4 h-4 rounded-full border-2 animate-spin"
                 style="border-color:rgba(96,165,250,0.5);border-top-color:transparent"></div>
            <span class="text-[9px] text-white/30">종목 분석 중...</span>
          </div>
          <!-- 결과 없음 -->
          <div v-else-if="recommendList.length === 0" class="flex flex-col items-center justify-center h-20 gap-1">
            <span class="text-[20px]">🔍</span>
            <span class="text-[10px] text-white/35">조건에 맞는 종목이 없습니다</span>
          </div>
          <div v-else
            v-for="company in recommendList" :key="company.id"
            class="flex items-center gap-3 p-3 rounded-xl border transition-all duration-200 cursor-pointer"
            :class="replaceMode
              ? 'bg-white/5 border-white/5 hover:bg-white/10 hover:border-emerald-500/30'
              : 'bg-white/5 border-white/5 hover:bg-white/8 hover:border-white/15'"
            @click="replaceMode ? openCompare(company) : openDetail(company)"
          >
            <div class="w-1 h-10 rounded-full flex-shrink-0" :style="{ background: company.color }"></div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <p class="font-bold text-sm truncate">{{ company.name }}</p>
                <span class="text-[9px] text-white/35 font-mono flex-shrink-0">{{ company.ticker }}</span>
              </div>
              <p class="text-[9px] text-white/40">{{ company.sector }}</p>
            </div>
            <div class="flex flex-col items-center flex-shrink-0 min-w-[36px]">
              <p class="text-[7px] text-white/30 uppercase tracking-wide">Quant</p>
              <p class="text-sm font-black" :class="quantTextColor(company.quantScore)">{{ company.quantScore }}</p>
              <div class="w-6 h-0.5 bg-black/30 rounded-full overflow-hidden mt-0.5">
                <div class="h-full rounded-full" :class="quantBarColor(company.quantScore)"
                     :style="{ width: company.quantScore + '%' }"></div>
              </div>
            </div>
            <div class="text-right flex-shrink-0">
              <p class="text-sm font-bold">₩{{ company.price.toLocaleString() }}</p>
              <p class="text-[10px] font-semibold"
                 :class="company.change >= 0 ? 'text-green-400' : 'text-red-400'">
                {{ company.change >= 0 ? '+' : '' }}{{ company.change }}%
              </p>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <template v-if="!replaceMode">
                <button @click.stop="openOrderModal(company, 'buy')"
                        class="px-2 py-1 rounded-lg text-[10px] font-bold border transition-all bg-blue-500/15 border-blue-500/30 text-blue-300 hover:bg-blue-500/30">매수</button>
                <button @click.stop="openOrderModal(company, 'sell')"
                        class="px-2 py-1 rounded-lg text-[10px] font-bold border transition-all bg-red-500/15 border-red-500/30 text-red-300 hover:bg-red-500/30">매도</button>
              </template>
              <LucideChevronRight class="w-4 h-4 text-white/25 ml-0.5" />
            </div>
          </div>
        </div>
      </template>

      <!-- ──────────────────────────────────────
           탭 B: 커뮤니티 인기
      ────────────────────────────────────── -->
      <template v-else-if="activeTab === 'community'">
        <div class="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          <div v-if="communityLoading" class="flex items-center justify-center h-20 gap-2">
            <div class="w-4 h-4 rounded-full border-2 animate-spin"
                 style="border-color:rgba(251,191,36,0.5);border-top-color:transparent"></div>
            <span class="text-[9px] text-white/30">커뮤니티 데이터 로딩 중...</span>
          </div>
          <div v-else-if="communityError" class="flex flex-col items-center justify-center h-20 gap-1.5">
            <span class="text-[18px]">💬</span>
            <span class="text-[10px] text-white/35">커뮤니티 데이터를 불러올 수 없습니다</span>
            <span class="text-[8px] text-white/20">게시판 DB 연결을 확인해주세요</span>
          </div>
          <div v-else
            v-for="(post, idx) in communityList" :key="post.id"
            class="p-3 rounded-xl border border-white/5 bg-white/5 hover:bg-white/8 transition-all cursor-pointer"
            @click="post.ticker ? openDetailByTicker(post.ticker) : null"
          >
            <div class="flex items-start gap-2.5">
              <!-- 순위 -->
              <div class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5"
                   :style="rankBadge(idx + 1)">
                <span class="text-[9px] font-black">{{ idx + 1 }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5 mb-0.5">
                  <span v-if="post.ticker"
                        class="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold"
                        style="background:rgba(96,165,250,0.15);color:#93c5fd;border:1px solid rgba(96,165,250,0.25)">
                    {{ post.ticker }}
                  </span>
                </div>
                <p class="text-[11px] font-semibold leading-snug text-white/88">{{ post.title }}</p>
                <div class="flex items-center gap-3 mt-1">
                  <span class="text-[8px] text-white/25 font-mono">👁 {{ post.views }}</span>
                  <span class="text-[8px] text-white/25 font-mono">♥ {{ post.likes }}</span>
                  <span class="text-[8px] text-white/25 font-mono">💬 {{ post.comment_count }}</span>
                  <span class="text-[8px] font-bold ml-auto"
                        style="color:rgba(251,191,36,0.7)">
                    🔥 {{ post.popularity }}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <!-- fallback mock -->
          <template v-if="!communityLoading && !communityError && communityList.length === 0">
            <div v-for="(post, idx) in MOCK_POPULAR" :key="post.id"
                 class="p-3 rounded-xl border border-white/4 bg-white/4 opacity-60">
              <div class="flex items-start gap-2.5">
                <div class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5"
                     :style="rankBadge(idx + 1)">
                  <span class="text-[9px] font-black">{{ idx + 1 }}</span>
                </div>
                <div class="flex-1 min-w-0">
                  <span v-if="post.ticker" class="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold mr-1.5"
                        style="background:rgba(96,165,250,0.15);color:#93c5fd;border:1px solid rgba(96,165,250,0.25)">
                    {{ post.ticker }}
                  </span>
                  <p class="text-[11px] font-semibold leading-snug text-white/70 mt-0.5">{{ post.title }}</p>
                  <div class="flex items-center gap-3 mt-1">
                    <span class="text-[8px] text-white/22 font-mono">👁 {{ post.views }}</span>
                    <span class="text-[8px] text-white/22 font-mono">♥ {{ post.likes }}</span>
                    <span class="text-[8px] font-bold ml-auto" style="color:rgba(251,191,36,0.5)">🔥 {{ post.popularity }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </template>

      <!-- ──────────────────────────────────────
           탭 C: 급상승 종목
      ────────────────────────────────────── -->
      <template v-else-if="activeTab === 'rising'">
        <div class="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          <div v-if="risingLoading" class="flex items-center justify-center h-20 gap-2">
            <div class="w-4 h-4 rounded-full border-2 animate-spin"
                 style="border-color:rgba(52,211,153,0.5);border-top-color:transparent"></div>
            <span class="text-[9px] text-white/30">급상승 종목 탐색 중...</span>
          </div>
          <div v-else-if="risingError" class="flex flex-col items-center justify-center h-20 gap-1.5">
            <span class="text-[18px]">📈</span>
            <span class="text-[10px] text-white/35">급상승 데이터를 불러올 수 없습니다</span>
          </div>
          <div v-else
            v-for="(s, idx) in risingList" :key="s.ticker"
            class="flex items-center gap-3 p-3 rounded-xl border border-white/5 bg-white/5 hover:bg-white/8 hover:border-white/12 transition-all cursor-pointer"
            @click="openDetailByTicker(s.ticker)"
          >
            <div class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-black"
                 style="background:rgba(52,211,153,0.15);color:#34d399;border:1px solid rgba(52,211,153,0.3)">
              {{ idx + 1 }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5">
                <p class="font-bold text-sm truncate">{{ s.name ?? s.ticker }}</p>
                <span class="text-[9px] text-white/35 font-mono flex-shrink-0">{{ s.ticker }}</span>
              </div>
              <p class="text-[9px] text-white/38">{{ s.sector }}</p>
            </div>
            <!-- 점수 변화 -->
            <div class="text-right flex-shrink-0">
              <p class="text-[11px] font-black text-green-300">
                △ {{ s.score_change >= 0 ? '+' : '' }}{{ s.score_change?.toFixed(1) }}
              </p>
              <p class="text-[8.5px] font-mono text-white/38">점수 {{ s.score?.toFixed(0) }}</p>
            </div>
            <!-- Tier 뱃지 -->
            <span class="text-[9px] font-black px-1.5 py-0.5 rounded flex-shrink-0"
                  :style="tierBadgeStyle(s.tier)">{{ s.tier }}</span>
          </div>
          <!-- fallback mock -->
          <template v-if="!risingLoading && !risingError && risingList.length === 0">
            <div v-for="(s, idx) in MOCK_RISING" :key="s.ticker"
                 class="flex items-center gap-3 p-3 rounded-xl border border-white/4 bg-white/4 opacity-60">
              <div class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-black"
                   style="background:rgba(52,211,153,0.12);color:#34d399;border:1px solid rgba(52,211,153,0.2)">
                {{ idx + 1 }}
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-bold text-sm truncate">{{ s.name }}</p>
                <p class="text-[9px] text-white/32">{{ s.sector }}</p>
              </div>
              <div class="text-right flex-shrink-0">
                <p class="text-[11px] font-black text-green-300">△ +{{ s.score_change }}</p>
                <p class="text-[8.5px] font-mono text-white/35">점수 {{ s.score }}</p>
              </div>
              <span class="text-[9px] font-black px-1.5 py-0.5 rounded" :style="tierBadgeStyle(s.tier)">{{ s.tier }}</span>
            </div>
          </template>
        </div>
      </template>

    </div><!-- /기업 리스트 뷰 -->

    <!-- ══════════════════════════════
         검색 오버레이
    ══════════════════════════════ -->
    <transition name="search-slide">
      <div v-if="showSearch"
           class="absolute inset-0 z-50 flex flex-col rounded-[2rem] overflow-hidden"
           style="background:linear-gradient(160deg,#0c1622 0%,#080e18 100%)">

        <!-- 검색 바 -->
        <div class="px-3 pt-4 pb-2.5 flex items-center gap-2 flex-shrink-0 border-b border-white/8">
          <div class="flex-1 flex items-center gap-2 px-2.5 py-1.5 rounded-xl"
               style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.11)">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="2.5">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <input ref="searchInputRef"
                   v-model="searchQuery"
                   type="text"
                   placeholder="종목명 · 티커 검색"
                   class="flex-1 bg-transparent outline-none text-[11px] text-white placeholder:text-white/25 min-w-0" />
            <button v-if="searchQuery" @click="searchQuery = ''"
                    class="text-white/28 hover:text-white/55 text-[10px] flex-shrink-0">✕</button>
          </div>
          <button @click="closeSearch"
                  class="text-[10px] font-bold text-white/40 hover:text-white/65 flex-shrink-0 px-1 transition-colors">
            닫기
          </button>
        </div>

        <!-- 본문: 좌(1/5 상세설정) + 우(4/5 종목 리스트) -->
        <div class="flex-1 flex overflow-hidden">

          <!-- ── 좌: 상세 설정 (1/5) ── -->
          <div class="w-1/5 flex-shrink-0 flex flex-col overflow-y-auto border-r border-white/8"
               style="background:rgba(0,0,0,0.18)">

            <!-- ▸ 모델 버전 -->
            <div class="px-2 pt-2.5 pb-1.5 border-b border-white/6">
              <p class="text-[7px] text-white/28 uppercase tracking-widest mb-1">버전</p>
              <select :value="searchFilters.model_version"
                      @change="searchFilters.model_version = $event.target.value"
                      class="w-full text-[8px] bg-black/20 border border-white/10 text-white/70 rounded px-1 py-0.5 outline-none">
                <option value="latest">최신</option>
                <option v-for="v in searchVersions" :key="v" :value="v">{{ v }}</option>
              </select>
            </div>

            <!-- ▸ 기준일 -->
            <div class="px-2 py-1.5 border-b border-white/6">
              <p class="text-[7px] text-white/28 uppercase tracking-widest mb-1">기준일</p>
              <select :value="searchFilters.date"
                      @change="searchFilters.date = $event.target.value"
                      class="w-full text-[8px] bg-black/20 border border-white/10 text-white/70 rounded px-1 py-0.5 outline-none">
                <option v-for="d in searchDates" :key="d" :value="d">{{ d }}</option>
              </select>
            </div>

            <!-- ▸ 섹터 -->
            <div class="px-2 py-1.5 border-b border-white/6">
              <p class="text-[7px] text-white/28 uppercase tracking-widest mb-1">섹터</p>
              <select :value="searchFilters.sector ?? ''"
                      @change="searchFilters.sector = $event.target.value || null"
                      class="w-full text-[8px] bg-black/20 border border-white/10 text-white/70 rounded px-1 py-0.5 outline-none">
                <option value="">전체</option>
                <option v-for="s in SECTOR_LIST" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>

            <!-- ▸ 최소 점수 슬라이더 -->
            <div class="px-2 py-1.5 border-b border-white/6">
              <div class="flex justify-between mb-1">
                <p class="text-[7px] text-white/28 uppercase tracking-widest">최소 점수</p>
                <span class="text-[8px] font-bold text-blue-300">{{ searchFilters.min_score }}</span>
              </div>
              <input type="range" min="0" max="100" step="1"
                     v-model.number="searchFilters.min_score"
                     class="w-full h-0.5 rounded-full appearance-none cursor-pointer"
                     style="accent-color:#60a5fa" />
              <div class="flex justify-between mt-0.5">
                <span class="text-[6px] text-white/18">0</span>
                <span class="text-[6px] text-white/18">100</span>
              </div>
            </div>

            <!-- ▸ Tier 빠른 선택 -->
            <div class="px-2 py-1.5 border-b border-white/6">
              <p class="text-[7px] text-white/28 uppercase tracking-widest mb-1">Tier</p>
              <div class="grid grid-cols-2 gap-0.5">
                <!-- A / B / C / D -->
                <button v-for="t in TIER_PRESETS.filter(p => p.tier !== null)" :key="t.label"
                        @click="searchFilters.min_score = t.min; searchFilters.tier = t.tier"
                        class="py-0.5 rounded text-[8px] font-bold text-center transition-all flex items-center justify-center gap-0.5"
                        :style="searchFilters.tier === t.tier && searchFilters.min_score === t.min
                          ? tierActiveStyle(t.tier)
                          : 'background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.38);border:1px solid rgba(255,255,255,0.08)'">
                  <span>{{ t.label }}</span>
                  <span class="text-[6px] opacity-55">({{ tierCounts[t.tier] ?? 0 }})</span>
                </button>
                <!-- 전체: col-span-2 -->
                <button class="col-span-2 mt-0.5 py-0.5 rounded text-[8px] font-bold text-center transition-all"
                        @click="searchFilters.min_score = 0; searchFilters.tier = null"
                        :style="searchFilters.tier === null && searchFilters.min_score === 0
                          ? tierActiveStyle('all')
                          : 'background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.38);border:1px solid rgba(255,255,255,0.08)'">
                  전체 ({{ searchAllItems.length }})
                </button>
              </div>
            </div>

            <!-- ▸ Tier 분포 -->
            <div class="px-2 py-1.5 border-b border-white/6">
              <p class="text-[7px] text-white/28 uppercase tracking-widest mb-1.5">Tier 분포</p>
              <div class="space-y-0.5">
                <div v-for="tk in ['A','B','C','D']" :key="tk" class="flex items-center gap-1.5">
                  <span class="text-[7px] font-black w-3 flex-shrink-0"
                        :style="{ color: {A:'#34d399',B:'#93c5fd',C:'#fbbf24',D:'#f87171'}[tk] }">{{ tk }}</span>
                  <div class="flex-1 h-0.5 rounded-full" style="background:rgba(255,255,255,0.06)">
                    <div class="h-full rounded-full transition-all duration-300"
                         :style="{
                           width: searchAllItems.length
                             ? ((tierCounts[tk] ?? 0) / searchAllItems.length * 100).toFixed(1) + '%'
                             : '0%',
                           background: {A:'#34d399',B:'#93c5fd',C:'#fbbf24',D:'#f87171'}[tk]
                         }"></div>
                  </div>
                  <span class="text-[7px] text-white/30 w-4 text-right flex-shrink-0">{{ tierCounts[tk] ?? 0 }}</span>
                </div>
              </div>
            </div>

            <!-- ══ 부가설정 (접기/펼치기) ══ -->
            <div class="px-2 pt-1.5">
              <button @click="financialOpen = !financialOpen"
                      class="w-full flex items-center justify-between text-[7px] font-bold uppercase tracking-widest mb-1 transition-colors"
                      :class="financialOpen ? 'text-white/50' : 'text-white/25'">
                <span>부가설정</span>
                <span class="text-[8px]">{{ financialOpen ? '▲' : '▼' }}</span>
              </button>

              <template v-if="financialOpen">
                <!-- 재무 조건 7개 -->
                <div v-for="f in ALL_FINANCE_FILTERS" :key="f.key" class="mb-1.5">
                  <p class="text-[6.5px] text-white/22 mb-0.5">{{ f.shortLabel }}</p>
                  <input type="number" :placeholder="f.placeholder"
                         :value="searchFilters[f.key]"
                         @change="searchFilters[f.key] = $event.target.value === '' ? null : +$event.target.value"
                         class="w-full px-1.5 py-0.5 rounded text-[8px] font-mono bg-black/20 border border-white/8 text-white/70 outline-none" />
                </div>

                <!-- 구분선 -->
                <div class="border-t border-white/6 my-1.5"></div>

                <!-- 정렬 기준 -->
                <div class="mb-1.5">
                  <p class="text-[6.5px] text-white/22 mb-0.5">정렬</p>
                  <select :value="searchFilters.sort_by"
                          @change="searchFilters.sort_by = $event.target.value"
                          class="w-full text-[8px] bg-black/20 border border-white/8 text-white/60 rounded px-1 py-0.5 outline-none">
                    <option value="composite_score">복합점수</option>
                    <option value="score">ML점수</option>
                    <option value="finance_score">재무점수</option>
                    <option value="roe">ROE</option>
                    <option value="per">PER</option>
                    <option value="pbr">PBR</option>
                    <option value="rev_growth_yoy">매출성장률</option>
                  </select>
                </div>

                <!-- 결과 수 -->
                <div class="mb-1.5">
                  <p class="text-[6.5px] text-white/22 mb-0.5">결과 수</p>
                  <select :value="searchFilters.limit"
                          @change="searchFilters.limit = +$event.target.value"
                          class="w-full text-[8px] bg-black/20 border border-white/8 text-white/60 rounded px-1 py-0.5 outline-none">
                    <option :value="50">50개</option>
                    <option :value="100">100개</option>
                    <option :value="200">200개</option>
                    <option :value="300">300개</option>
                  </select>
                </div>

                <!-- 구분선 -->
                <div class="border-t border-white/6 my-1.5"></div>

                <!-- 프리셋 -->
                <div class="mb-1.5">
                  <p class="text-[6.5px] text-white/22 mb-1">프리셋</p>
                  <div class="flex gap-0.5 mb-1">
                    <input v-model="presetName" type="text" placeholder="이름"
                           class="flex-1 px-1 py-0.5 rounded text-[8px] bg-black/20 border border-white/8 text-white/70 outline-none min-w-0"
                           @keydown.enter="savePreset" />
                    <button @click="savePreset"
                            class="px-1.5 py-0.5 rounded text-[8px] font-bold flex-shrink-0 transition-colors"
                            style="background:rgba(96,165,250,0.2);color:#93c5fd;border:1px solid rgba(96,165,250,0.3)">
                      저장
                    </button>
                  </div>
                  <div v-for="name in savedPresets" :key="name"
                       class="flex items-center justify-between mb-0.5">
                    <button @click="loadPreset(name)"
                            class="text-[7.5px] text-white/45 hover:text-white/70 truncate flex-1 text-left transition-colors">
                      {{ name }}
                    </button>
                    <button @click="deletePreset(name)"
                            class="text-[8px] text-white/20 hover:text-red-400 ml-1 flex-shrink-0 transition-colors">✕</button>
                  </div>
                  <p v-if="!savedPresets.length" class="text-[7px] text-white/18">저장된 프리셋 없음</p>
                </div>

                <!-- 재무만 초기화 / 전체 초기화 -->
                <div class="flex flex-col gap-0.5 pb-2">
                  <button @click="resetFinancialFilters"
                          class="text-[7px] text-red-400/60 hover:text-red-400 text-left transition-colors">
                    재무 조건 초기화
                  </button>
                  <button @click="resetSearchFilters"
                          class="text-[7px] text-red-400/60 hover:text-red-400 text-left transition-colors">
                    전체 초기화
                  </button>
                </div>
              </template>
            </div>
          </div>

          <!-- ── 우: 종목 리스트 (4/5) ── -->
          <div class="flex-1 overflow-y-auto">

            <!-- 로딩 -->
            <div v-if="searchLoading" class="flex items-center justify-center h-20 gap-2">
              <div class="w-3 h-3 rounded-full border-2 animate-spin"
                   style="border-color:rgba(96,165,250,0.5);border-top-color:transparent"></div>
              <span class="text-[8px] text-white/28">로딩 중...</span>
            </div>

            <!-- 결과 없음 -->
            <div v-else-if="searchDisplayList.length === 0"
                 class="flex flex-col items-center justify-center h-20 gap-1">
              <span class="text-[14px]">🔍</span>
              <span class="text-[9px] text-white/30">결과 없음</span>
            </div>

            <!-- 리스트 -->
            <div v-else>
              <!-- 건수 + CSV -->
              <div class="px-2 py-1.5 border-b border-white/6 flex items-center justify-between">
                <span class="text-[7.5px] text-white/25">{{ searchDisplayList.length }}개 종목</span>
                <div class="flex items-center gap-2">
                  <span class="text-[7.5px] text-white/18">가나다순</span>
                  <button @click="exportCsv"
                          class="text-[7px] px-1.5 py-0.5 rounded font-bold flex-shrink-0 transition-all"
                          style="background:rgba(52,211,153,0.12);color:rgba(52,211,153,0.7);border:1px solid rgba(52,211,153,0.2)">
                    CSV ↓
                  </button>
                </div>
              </div>
              <div v-for="s in searchDisplayList" :key="s.ticker"
                   class="flex items-center gap-1.5 px-2 py-1.5 border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer"
                   @click="selectSearchResult(s)">
                <!-- 이름 + 티커 + 점수 바 -->
                <div class="flex-1 min-w-0">
                  <p class="text-[10px] font-bold truncate text-white/88">{{ s.name }}</p>
                  <p class="text-[7.5px] font-mono text-white/30">{{ s.ticker }}</p>
                  <div class="w-full h-0.5 bg-black/30 rounded-full mt-0.5">
                    <div class="h-full rounded-full transition-all"
                         :style="{ width: s.quantScore + '%', background: s.color }"></div>
                  </div>
                </div>
                <!-- ML / 재무 점수 -->
                <div class="text-right flex-shrink-0 min-w-[28px]">
                  <p class="text-[6.5px] text-white/28">ML <span class="font-mono font-bold">{{ s.mlScore }}</span></p>
                  <p class="text-[6.5px] text-white/28">재무 <span class="font-mono font-bold">{{ s.finScore }}</span></p>
                </div>
                <!-- Tier -->
                <span class="text-[8px] font-black px-1 py-0.5 rounded flex-shrink-0"
                      :style="tierBadgeStyle(s.tier)">{{ s.tier }}</span>
                <!-- 복합점수 -->
                <span class="text-[9px] font-black flex-shrink-0"
                      :class="s.quantScore >= 70 ? 'text-green-300' : s.quantScore >= 45 ? 'text-yellow-300' : 'text-red-300'">
                  {{ s.quantScore }}
                </span>
                <LucideChevronRight class="w-3 h-3 text-white/20 flex-shrink-0" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 상세 주가 차트 모달 -->
    <transition name="order-modal">
      <StockChartModal
        v-if="showChart && detailCompany"
        :company="detailCompany"
        :all-data="detailChartData"
        @close="showChart = false"
      />
    </transition>

    <!-- 교체 비교 모달 -->
    <transition name="order-modal">
      <div v-if="compareCandidate" class="absolute inset-0 z-50 flex flex-col justify-end">
        <div class="absolute inset-0 bg-black/65 backdrop-blur-sm rounded-[2rem]" @click="compareCandidate = null"></div>
        <div class="relative rounded-t-[2rem] border-t border-x border-white/15 overflow-hidden"
          style="background: linear-gradient(160deg, #0f1e30 0%, #0a1420 100%)">
          <div class="flex justify-center pt-3 pb-1">
            <div class="w-8 h-1 rounded-full bg-white/20"></div>
          </div>
          <div class="px-4 pb-5 pt-2">
            <p class="text-[10px] text-white/40 uppercase tracking-widest text-center mb-3">종목 교체 비교</p>

            <div class="grid grid-cols-2 gap-2 mb-4">
              <!-- 현재 보유 -->
              <div class="rounded-xl p-3 border border-red-500/25 bg-red-500/8 space-y-2.5">
                <div>
                  <p class="text-[8px] text-red-300/60 uppercase tracking-wide mb-1">현재 보유</p>
                  <div class="h-0.5 rounded-full mb-2" :style="{ background: replaceStock?.color ?? '#888' }"></div>
                  <p class="text-sm font-black truncate">{{ replaceStock?.company }}</p>
                  <p class="text-[8px] text-white/35 font-mono">{{ replaceStock?.ticker }}</p>
                </div>
                <div class="space-y-1.5 text-xs">
                  <div class="flex justify-between">
                    <span class="text-white/40">현재가</span>
                    <span class="font-bold">₩{{ replaceStock?.currentPrice?.toLocaleString() }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">등락</span>
                    <span class="font-bold" :class="(replaceStock?.change ?? 0) >= 0 ? 'text-green-300' : 'text-red-300'">
                      {{ (replaceStock?.change ?? 0) >= 0 ? '+' : '' }}{{ replaceStock?.change }}%
                    </span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">Quant</span>
                    <span class="font-black" :class="quantTextColor(replaceStock?.quantScore ?? 50)">
                      {{ replaceStock?.quantScore ?? '—' }}
                    </span>
                  </div>
                  <template v-if="currentStockInfo">
                    <div class="flex justify-between">
                      <span class="text-white/40">PER</span>
                      <span class="font-bold">{{ currentStockInfo.per }}x</span>
                    </div>
                    <div class="flex justify-between">
                      <span class="text-white/40">PBR</span>
                      <span class="font-bold">{{ currentStockInfo.pbr }}x</span>
                    </div>
                    <div class="flex justify-between">
                      <span class="text-white/40">배당</span>
                      <span class="font-bold">{{ currentStockInfo.dividend }}%</span>
                    </div>
                  </template>
                </div>
              </div>

              <!-- 교체 종목 -->
              <div class="rounded-xl p-3 border border-blue-500/25 bg-blue-500/8 space-y-2.5">
                <div>
                  <p class="text-[8px] text-blue-300/60 uppercase tracking-wide mb-1">교체 종목</p>
                  <div class="h-0.5 rounded-full mb-2" :style="{ background: compareCandidate.color }"></div>
                  <p class="text-sm font-black truncate">{{ compareCandidate.name }}</p>
                  <p class="text-[8px] text-white/35 font-mono">{{ compareCandidate.ticker }}</p>
                </div>
                <div class="space-y-1.5 text-xs">
                  <div class="flex justify-between">
                    <span class="text-white/40">현재가</span>
                    <span class="font-bold">₩{{ compareCandidate.price.toLocaleString() }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">등락</span>
                    <span class="font-bold" :class="compareCandidate.change >= 0 ? 'text-green-300' : 'text-red-300'">
                      {{ compareCandidate.change >= 0 ? '+' : '' }}{{ compareCandidate.change }}%
                    </span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">Quant</span>
                    <span class="font-black" :class="quantTextColor(compareCandidate.quantScore)">
                      {{ compareCandidate.quantScore }}
                    </span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">PER</span>
                    <span class="font-bold">{{ compareCandidate.per }}x</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">PBR</span>
                    <span class="font-bold">{{ compareCandidate.pbr }}x</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-white/40">배당</span>
                    <span class="font-bold">{{ compareCandidate.dividend }}%</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 인라인 주문 폼 -->
            <transition name="order-inline">
              <div v-if="compareAction" class="mb-3 rounded-xl border overflow-hidden"
                :class="compareAction === 'sell'
                  ? 'border-red-500/30 bg-red-500/8'
                  : 'border-blue-500/30 bg-blue-500/8'">
                <div class="flex items-center justify-between px-3 pt-2.5 pb-1.5 border-b"
                  :class="compareAction === 'sell' ? 'border-red-500/20' : 'border-blue-500/20'">
                  <div class="flex items-center gap-2">
                    <p class="text-[10px] font-black"
                      :class="compareAction === 'sell' ? 'text-red-300' : 'text-blue-300'">
                      {{ compareAction === 'sell' ? '매도' : '매수' }}
                    </p>
                    <p class="text-[10px] text-white/50 font-bold">
                      {{ compareAction === 'sell' ? replaceStock?.company : compareCandidate.name }}
                    </p>
                  </div>
                  <button @click="compareAction = null" class="text-white/30 hover:text-white/60 text-xs">✕</button>
                </div>
                <div class="px-3 py-2.5 space-y-2">
                  <!-- 가격 -->
                  <div class="flex items-center gap-2 bg-black/20 rounded-lg px-2.5 py-2 border border-white/8">
                    <span class="text-white/40 text-xs flex-shrink-0">₩</span>
                    <input v-model.number="comparePrice" type="number"
                      class="flex-1 bg-transparent outline-none text-sm font-black text-white min-w-0" />
                  </div>
                  <!-- 수량 -->
                  <div class="flex items-center gap-2">
                    <button @click="compareQty = Math.max(1, compareQty - 1)"
                      class="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 font-bold text-base flex-shrink-0 transition-colors">−</button>
                    <input v-model.number="compareQty" type="number"
                      class="flex-1 bg-black/20 border border-white/8 rounded-lg outline-none text-center text-sm font-black py-1.5" />
                    <button @click="compareQty++"
                      class="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 font-bold text-base flex-shrink-0 transition-colors">+</button>
                  </div>
                  <!-- 총액 + 확정 -->
                  <div class="flex items-center gap-2">
                    <div class="flex-1">
                      <p class="text-[7px] text-white/35 uppercase tracking-wide">총 금액</p>
                      <p class="text-sm font-black"
                        :class="compareAction === 'sell' ? 'text-red-200' : 'text-blue-200'">
                        ₩{{ (comparePrice * compareQty).toLocaleString() }}
                      </p>
                    </div>
                    <button @click="confirmCompareOrder"
                      class="px-4 py-2 rounded-xl text-xs font-black transition-colors"
                      :class="compareAction === 'sell'
                        ? 'bg-red-500/30 border border-red-500/40 text-red-100 hover:bg-red-500/45'
                        : 'bg-blue-500/30 border border-blue-500/40 text-blue-100 hover:bg-blue-500/45'">
                      {{ compareAction === 'sell' ? '매도 확정' : '매수 확정' }}
                    </button>
                  </div>
                </div>
              </div>
            </transition>

            <!-- 매도 / 매수 버튼 -->
            <div class="flex gap-2">
              <button @click="compareCandidate = null; compareAction = null"
                class="px-3 py-2.5 rounded-xl bg-white/8 border border-white/15 text-white/50 text-xs font-bold hover:bg-white/12 transition-colors flex-shrink-0">
                취소
              </button>
              <button @click="openCompareOrder('sell')"
                class="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all duration-200"
                :class="compareAction === 'sell'
                  ? 'bg-red-500/35 border border-red-500/50 text-red-200'
                  : 'bg-red-500/15 border border-red-500/30 text-red-300 hover:bg-red-500/25'">
                현재 매도
              </button>
              <button @click="openCompareOrder('buy')"
                class="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all duration-200"
                :class="compareAction === 'buy'
                  ? 'bg-blue-500/35 border border-blue-500/50 text-blue-200'
                  : 'bg-blue-500/15 border border-blue-500/30 text-blue-300 hover:bg-blue-500/25'">
                신규 매수
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 주문 모달 (슬라이드업) -->
    <transition name="order-modal">
      <div v-if="orderCompany" class="absolute inset-0 z-50 flex flex-col justify-end">
        <!-- 배경 딤 -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm rounded-[2rem]" @click="closeOrderModal"></div>

        <!-- 모달 시트 -->
        <div class="relative rounded-t-[2rem] border-t border-x border-white/15 overflow-hidden"
          style="background: linear-gradient(160deg, #0f1e30 0%, #0a1420 100%)">

          <!-- 핸들 -->
          <div class="flex justify-center pt-3 pb-1">
            <div class="w-8 h-1 rounded-full bg-white/20"></div>
          </div>

          <div class="px-5 pb-6 pt-2 space-y-4">

            <!-- 종목 정보 + 타입 배지 -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <div class="w-2 h-8 rounded-full flex-shrink-0" :style="{ background: orderCompany.color }"></div>
                <div>
                  <p class="text-sm font-black leading-tight">{{ orderCompany.name }}</p>
                  <p class="text-[9px] text-white/40 font-mono">{{ orderCompany.ticker }}</p>
                </div>
              </div>
              <div class="flex flex-col items-end gap-1">
                <span class="px-2.5 py-1 rounded-lg text-xs font-black"
                  :class="orderType === 'buy'
                    ? 'bg-blue-500/25 text-blue-200 border border-blue-500/40'
                    : 'bg-red-500/25 text-red-200 border border-red-500/40'">
                  {{ orderType === 'buy' ? '매수' : '매도' }}
                </span>
                <p class="text-xs text-white/40">₩{{ orderCompany.price.toLocaleString() }}</p>
              </div>
            </div>

            <!-- 가격 입력 -->
            <div class="bg-white/5 rounded-xl border border-white/10 p-3">
              <p class="text-[9px] text-white/40 uppercase tracking-widest mb-2">주문 가격</p>
              <div class="flex items-center gap-2">
                <span class="text-white/50 font-bold">₩</span>
                <input
                  v-model.number="orderPrice"
                  type="number"
                  class="flex-1 bg-transparent outline-none text-lg font-black text-white"
                  min="1"
                />
              </div>
            </div>

            <!-- 수량 입력 -->
            <div class="bg-white/5 rounded-xl border border-white/10 p-3">
              <p class="text-[9px] text-white/40 uppercase tracking-widest mb-2">수량</p>
              <div class="flex items-center gap-3">
                <button
                  @click="orderQty = Math.max(1, orderQty - 1)"
                  class="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center font-bold text-lg transition-colors"
                >−</button>
                <input
                  v-model.number="orderQty"
                  type="number"
                  class="flex-1 bg-transparent outline-none text-center text-xl font-black text-white"
                  min="1"
                />
                <button
                  @click="orderQty++"
                  class="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center font-bold text-lg transition-colors"
                >+</button>
              </div>
            </div>

            <!-- 총 금액 -->
            <div class="flex items-center justify-between px-1">
              <p class="text-[10px] text-white/40 uppercase tracking-widest">총 {{ orderType === 'buy' ? '매수' : '매도' }}금액</p>
              <p class="text-lg font-black"
                :class="orderType === 'buy' ? 'text-blue-200' : 'text-red-200'">
                ₩{{ (orderPrice * orderQty).toLocaleString() }}
              </p>
            </div>

            <!-- 확인 버튼 -->
            <button
              @click="confirmOrder"
              class="w-full py-3 rounded-xl font-black text-sm tracking-wide transition-all duration-200"
              :class="orderType === 'buy'
                ? 'bg-blue-500/30 hover:bg-blue-500/45 text-blue-100 border border-blue-500/40'
                : 'bg-red-500/30 hover:bg-red-500/45 text-red-100 border border-red-500/40'"
            >
              {{ orderType === 'buy' ? '매수 주문 확인' : '매도 주문 확인' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

      </div><!-- /앞면 -->

      <!-- ── 뒷면: 재무제표 ── -->
      <div class="absolute inset-0 bg-gradient-to-br from-[#111c2c] to-[#090f1a] flex flex-col overflow-hidden fin-face"
           :class="showFinancial ? 'fin-face--show' : 'fin-face--hide'">

        <!-- 헤더 -->
        <div class="px-5 pt-4 pb-3 border-b border-white/12 flex-shrink-0">
          <div class="flex items-center gap-2.5">
            <button @click="showFinancial = false"
                    class="flex items-center gap-1 text-white/50 hover:text-white/85 transition-colors flex-shrink-0">
              <LucideChevronLeft class="w-5 h-5" />
            </button>
            <div class="flex-1 min-w-0">
              <p class="text-[8px] text-white/30 font-mono uppercase tracking-[0.2em]">Financial Statements</p>
              <h2 class="text-xl font-black tracking-tight leading-tight truncate">{{ detailCompany?.name }}</h2>
            </div>
            <!-- [API] 실제 재무 데이터 연동 후 제거 -->
            <span class="text-[7px] text-white/18 flex-shrink-0">임시 데이터</span>
          </div>
        </div>

        <!-- 탭 -->
        <div class="flex px-4 gap-1 pt-2.5 pb-0 flex-shrink-0">
          <button v-for="tab in FIN_TABS" :key="tab.key"
                  @click="finTab = tab.key"
                  class="flex-1 py-1.5 rounded-lg text-[10px] font-bold transition-all text-center"
                  :class="finTab === tab.key ? 'bg-white/14 text-white' : 'text-white/30 hover:text-white/60'">
            {{ tab.label }}
          </button>
        </div>

        <!-- 단위 레이블 -->
        <div class="px-5 pt-2 pb-0.5 flex-shrink-0 flex items-center justify-between">
          <span class="text-[8px] text-white/25">(단위: 억원)</span>
          <span class="text-[8px] text-white/25 font-mono" v-if="finData">{{ detailCompany?.ticker }}</span>
        </div>

        <!-- 재무 데이터 본문 -->
        <div class="flex-1 overflow-y-auto px-4 pb-4 pt-1">

          <!-- ─── 손익계산서 ─── -->
          <template v-if="finTab === 'income' && finData">
            <!-- 연도 헤더 -->
            <div class="grid grid-cols-4 gap-1 pb-1.5 mb-0.5 border-b border-white/10">
              <span></span>
              <span v-for="y in finData.years" :key="y"
                    class="text-[9px] text-white/40 font-mono text-right font-bold">{{ y }}</span>
            </div>
            <!-- 데이터 행 -->
            <div v-for="row in incomeRows" :key="row.key"
                 class="grid grid-cols-4 gap-1 py-2 border-b border-white/6 last:border-0"
                 :class="row.hl ? 'bg-white/5 -mx-1 px-1 rounded-lg border-0 my-0.5' : ''">
              <span class="text-[9px] text-white/45 leading-tight">{{ row.label }}</span>
              <span v-for="(val, i) in row.values" :key="i"
                    class="text-[9px] text-right font-bold tabular-nums"
                    :class="row.color ? (val >= 0 ? 'text-green-300' : 'text-red-300') : 'text-white/82'">
                {{ row.pct ? val + '%' : val.toLocaleString() }}
              </span>
            </div>
            <!-- 매출액 미니 바 차트 -->
            <div class="mt-4">
              <p class="text-[8px] text-white/25 uppercase tracking-widest mb-2">매출액 추이</p>
              <div class="flex items-end gap-2 h-14">
                <div v-for="(d, i) in finData.income" :key="i"
                     class="flex-1 flex flex-col items-center gap-1.5">
                  <div class="w-full rounded-t-sm transition-all"
                       :style="{ height: (d.revenue / maxRevenue * 46) + 'px',
                                 background: detailCompany?.color ?? '#60a5fa',
                                 opacity: 0.55 + i * 0.2 }">
                  </div>
                  <span class="text-[7px] text-white/28 font-mono">{{ d.year }}</span>
                </div>
              </div>
            </div>
          </template>

          <!-- ─── 재무상태표 ─── -->
          <template v-else-if="finTab === 'balance' && finData">
            <p class="text-[8px] text-white/28 mb-3">기준: {{ finData.years[2] }}년</p>
            <!-- 자산 / 부채 / 자본 -->
            <div v-for="row in balanceRows" :key="row.key"
                 class="flex items-center justify-between py-2.5 border-b border-white/6 last:border-0"
                 :class="row.hl ? 'bg-white/5 -mx-1 px-1 rounded-lg border-0 my-0.5' : ''">
              <span class="text-[10px] text-white/45">{{ row.label }}</span>
              <span class="text-[11px] font-black tabular-nums"
                    :class="row.hl ? 'text-white' : 'text-white/72'">
                {{ row.val.toLocaleString() }}
              </span>
            </div>
            <!-- 부채비율 게이지 -->
            <div class="mt-4">
              <div class="flex justify-between mb-1.5">
                <span class="text-[9px] text-white/40">부채비율</span>
                <span class="text-[10px] font-black"
                      :class="finData.balance.debtRatio < 100 ? 'text-green-300' : finData.balance.debtRatio < 200 ? 'text-yellow-300' : 'text-red-300'">
                  {{ finData.balance.debtRatio }}%
                </span>
              </div>
              <div class="h-2 bg-white/8 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-700"
                     :class="finData.balance.debtRatio < 100 ? 'bg-green-500/65' : finData.balance.debtRatio < 200 ? 'bg-yellow-500/65' : 'bg-red-500/65'"
                     :style="{ width: Math.min(finData.balance.debtRatio / 3, 100) + '%' }">
                </div>
              </div>
              <div class="flex justify-between mt-0.5">
                <span class="text-[7px] text-white/18">0%</span>
                <span class="text-[7px] text-white/18">300%</span>
              </div>
            </div>
            <!-- 자본 구성 도넛 -->
            <div class="mt-4 flex items-center gap-4">
              <svg viewBox="0 0 60 60" class="w-14 h-14 flex-shrink-0">
                <circle cx="30" cy="30" r="20" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="10" />
                <circle cx="30" cy="30" r="20" fill="none"
                        :stroke="detailCompany?.color ?? '#60a5fa'"
                        stroke-width="10" stroke-linecap="round"
                        :stroke-dasharray="`${equityRatio * 125.6} 125.6`"
                        transform="rotate(-90 30 30)" opacity="0.72" />
              </svg>
              <div class="space-y-2">
                <div class="flex items-center gap-2">
                  <div class="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                       :style="{ background: detailCompany?.color ?? '#60a5fa', opacity: 0.72 }"></div>
                  <span class="text-[9px] text-white/55">자본 {{ (equityRatio * 100).toFixed(1) }}%</span>
                </div>
                <div class="flex items-center gap-2">
                  <div class="w-2.5 h-2.5 rounded-sm bg-white/12 flex-shrink-0"></div>
                  <span class="text-[9px] text-white/55">부채 {{ ((1 - equityRatio) * 100).toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </template>

          <!-- ─── 현금흐름표 ─── -->
          <template v-else-if="finTab === 'cashflow' && finData">
            <div class="grid grid-cols-4 gap-1 pb-1.5 mb-0.5 border-b border-white/10">
              <span></span>
              <span v-for="y in finData.years" :key="y"
                    class="text-[9px] text-white/40 font-mono text-right font-bold">{{ y }}</span>
            </div>
            <div v-for="row in cashflowRows" :key="row.key"
                 class="grid grid-cols-4 gap-1 py-2 border-b border-white/6 last:border-0"
                 :class="row.key === 'net' ? 'bg-white/5 -mx-1 px-1 rounded-lg border-0 mt-0.5' : ''">
              <span class="text-[9px] text-white/45">{{ row.label }}</span>
              <span v-for="(val, i) in row.values" :key="i"
                    class="text-[9px] text-right font-bold tabular-nums"
                    :class="val >= 0 ? 'text-green-300' : 'text-red-300'">
                {{ (val >= 0 ? '+' : '') + val.toLocaleString() }}
              </span>
            </div>
            <!-- 영업활동 현금흐름 미니 바차트 -->
            <div class="mt-4">
              <p class="text-[8px] text-white/25 uppercase tracking-widest mb-2">영업활동 현금흐름</p>
              <div class="flex items-end gap-2 h-14">
                <div v-for="(d, i) in finData.cashflow" :key="i"
                     class="flex-1 flex flex-col items-center gap-1.5">
                  <div class="w-full rounded-t-sm"
                       :style="{ height: (d.operating / maxOperating * 46) + 'px',
                                 background: '#4ade80', opacity: 0.5 + i * 0.2 }">
                  </div>
                  <span class="text-[7px] text-white/28 font-mono">{{ d.year }}</span>
                </div>
              </div>
            </div>
          </template>

        </div><!-- /재무 본문 -->
      </div><!-- /뒷면 -->

  </div><!-- /카드 루트 -->
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { LucideChevronRight, LucideChevronLeft, LucideBarChart2 } from 'lucide-vue-next'
import { MOCK_COMPANIES, generateMockOHLC } from '@/mock/data.js'
import StockChartModal from '@/components/modal/StockChartModal.vue'
import { stocksApi } from '@/api/stocks.js'
import { screenerApi } from '@/api/screener.js'
import { chartApi } from '@/api/chart.js'
// import { financeApi } from '@/api/finance.js'  // [미사용] 재무 API 연결 시 주석 해제
import { useStocksStore } from '@/stores/stocks.js'
import { useScreenerStore } from '@/stores/screener.js'

const props = defineProps({
  replaceMode:  { type: Boolean, default: false },
  replaceStock: { type: Object,  default: null  },
  viewTicker:   { type: String,  default: null  },
});
const emit = defineEmits(['select-company', 'add-company', 'back', 'sell-replace']);

const stocksStore   = useStocksStore()
const screenerStore = useScreenerStore()

// ── 탭 설정 ──────────────────────────────────
const STOCK_TABS = [
  { key: 'recommend', label: 'AI 추천 랭킹' },
  { key: 'community', label: '커뮤니티 인기' },
  { key: 'rising',    label: '급상승 종목'  },
]
const activeTab = ref('recommend')

// ── 섹터 목록 ────────────────────────────────
const SECTOR_LIST = ['IT','에너지','건강관리','산업재','커뮤니케이션','경기소비재','소재','금융','유틸리티','필수소비재']

// ── Tier 빠른선택 (FilterPanel 스타일) ────────
const TIER_PRESETS = [
  { label: 'A (80+)', min: 80, tier: 'A' },
  { label: 'B (60+)', min: 60, tier: 'B' },
  { label: 'C (40+)', min: 40, tier: 'C' },
  { label: 'D (0+)',  min: 0,  tier: 'D' },
  { label: '전체',    min: 0,  tier: null },
]

// ── 재무+부가 필터 목록 (FilterSidebar 7개) ──
const ALL_FINANCE_FILTERS = [
  { key: 'max_per',           shortLabel: '최대 PER',          placeholder: '제한없음' },
  { key: 'max_pbr',           shortLabel: '최대 PBR',          placeholder: '제한없음' },
  { key: 'min_roe',           shortLabel: '최소 ROE (%)',       placeholder: '제한없음' },
  { key: 'max_debt_ratio',    shortLabel: '최대 부채비율 (%)',   placeholder: '제한없음' },
  { key: 'min_op_margin',     shortLabel: '최소 영업이익률 (%)', placeholder: '제한없음' },
  { key: 'min_rev_growth',    shortLabel: '최소 매출성장률 (%)', placeholder: '제한없음' },
  { key: 'min_finance_score', shortLabel: '최소 재무점수',       placeholder: '제한없음' },
]

// ══════════════════════════════════════════════
// [더미데이터] API 연결 후 아래 MOCK_RECOMMEND 블록 전체 삭제
// ══════════════════════════════════════════════
const MOCK_RECOMMEND = [
  //                                                                                                                               mlScore  finScore  (composite ≈ ml*0.6 + fin*0.4)
  { id:'005930', ticker:'005930', name:'삼성전자',        sector:'IT',          price:78400,  change: 1.83, color:'#34d399', marketCap:'467조', per:20.1, pbr:1.5, dividend:2.1, quantScore:91, mlScore:88, finScore:96, tier:'A', description:'' },
  { id:'000660', ticker:'000660', name:'SK하이닉스',       sector:'IT',          price:198500, change: 2.41, color:'#34d399', marketCap:'144조', per:16.3, pbr:2.2, dividend:0.8, quantScore:87, mlScore:92, finScore:79, tier:'A', description:'' },
  { id:'035420', ticker:'035420', name:'NAVER',           sector:'커뮤니케이션', price:214500, change: 0.94, color:'#34d399', marketCap:'35조',  per:35.2, pbr:2.8, dividend:0.3, quantScore:82, mlScore:80, finScore:85, tier:'A', description:'' },
  { id:'207940', ticker:'207940', name:'삼성바이오로직스', sector:'건강관리',     price:996000, change: 1.12, color:'#34d399', marketCap:'71조',  per:99.6, pbr:7.1, dividend:0.0, quantScore:79, mlScore:75, finScore:85, tier:'B', description:'' },
  { id:'051910', ticker:'051910', name:'LG화학',          sector:'소재',         price:312000, change:-0.64, color:'#fbbf24', marketCap:'22조',  per:28.4, pbr:1.1, dividend:1.2, quantScore:73, mlScore:70, finScore:78, tier:'B', description:'' },
  { id:'086520', ticker:'086520', name:'에코프로',         sector:'소재',         price:87500,  change: 3.17, color:'#34d399', marketCap:'12조',  per:42.1, pbr:5.3, dividend:0.0, quantScore:68, mlScore:72, finScore:62, tier:'B', description:'' },
  { id:'035720', ticker:'035720', name:'카카오',           sector:'커뮤니케이션', price:41200,  change:-1.32, color:'#fbbf24', marketCap:'18조',  per:48.7, pbr:1.3, dividend:0.0, quantScore:61, mlScore:65, finScore:55, tier:'B', description:'' },
  { id:'196170', ticker:'196170', name:'알테오젠',         sector:'건강관리',     price:321000, change: 4.23, color:'#34d399', marketCap:'19조',  per:null, pbr:18.4,dividend:0.0, quantScore:58, mlScore:60, finScore:55, tier:'C', description:'' },
  { id:'041510', ticker:'041510', name:'에스엠',           sector:'커뮤니케이션', price:87700,  change: 0.57, color:'#fbbf24', marketCap:'2.1조', per:22.3, pbr:2.6, dividend:0.5, quantScore:54, mlScore:52, finScore:57, tier:'C', description:'' },
  { id:'006400', ticker:'006400', name:'삼성SDI',          sector:'소재',         price:189000, change:-0.79, color:'#fbbf24', marketCap:'13조',  per:31.8, pbr:0.9, dividend:0.6, quantScore:51, mlScore:48, finScore:56, tier:'C', description:'' },
  { id:'068270', ticker:'068270', name:'셀트리온',         sector:'건강관리',     price:165000, change: 1.47, color:'#fbbf24', marketCap:'22조',  per:44.6, pbr:3.2, dividend:0.0, quantScore:48, mlScore:50, finScore:45, tier:'C', description:'' },
  { id:'005380', ticker:'005380', name:'현대차',           sector:'경기소비재',   price:218000, change: 0.23, color:'#fbbf24', marketCap:'46조',  per:7.4,  pbr:0.7, dividend:3.4, quantScore:45, mlScore:42, finScore:50, tier:'C', description:'' },
]
// ══════════════════════════════════════════════ [더미데이터 끝]

// ── AI 추천 랭킹 (screener 연동) ─────────────
const recommendList = computed(() => {
  const src = screenerStore.items.length > 0 ? screenerStore.items : stocksStore.items
  if (src.length === 0) return MOCK_RECOMMEND   // [더미데이터] 연결 후 → return [] 로 변경
  return src.map(s => ({
    id:         s.ticker,
    name:       s.name ?? s.ticker,
    ticker:     s.ticker,
    sector:     s.sector ?? '',
    price:      s.close_price ?? s.price ?? 0,
    change:     s.change_rate ?? s.change ?? 0,
    color:      scoreToColor(Math.round(s.composite_score ?? s.score ?? 0)),
    marketCap:  s.market_cap_str ?? '',
    per:        s.per ?? null,
    pbr:        s.pbr ?? null,
    dividend:   s.dividend_yield ?? null,
    quantScore: Math.round(s.composite_score ?? s.score ?? 0),
    description:'',
  }))
})

// 기존 companies computed (detail 뷰용)
const companies = computed(() => {
  if (stocksStore.items.length > 0) {
    return stocksStore.items.map(s => ({
      id:          s.ticker,
      name:        s.name ?? s.ticker,
      ticker:      s.ticker,
      sector:      s.sector ?? '',
      price:       s.close_price ?? s.price ?? 0,
      change:      s.change_rate ?? s.change ?? 0,
      color:       '#4A90E2',
      marketCap:   s.market_cap_str ?? '',
      per:         s.per ?? null,
      pbr:         s.pbr ?? null,
      dividend:    s.dividend_yield ?? null,
      quantScore:  Math.round(s.score ?? 0),
      description: s.description ?? '',
    }))
  }
  return MOCK_COMPANIES
})

const scoreToColor = (s) => s >= 70 ? '#34d399' : s >= 45 ? '#fbbf24' : '#f87171'

const tierActiveStyle = (t) => ({
  A:   'background:rgba(52,211,153,0.2);color:#34d399;border:1px solid rgba(52,211,153,0.4)',
  B:   'background:rgba(96,165,250,0.2);color:#93c5fd;border:1px solid rgba(96,165,250,0.4)',
  C:   'background:rgba(251,191,36,0.2);color:#fbbf24;border:1px solid rgba(251,191,36,0.4)',
  D:   'background:rgba(248,113,113,0.2);color:#f87171;border:1px solid rgba(248,113,113,0.4)',
  all: 'background:rgba(255,255,255,0.12);color:rgba(255,255,255,0.75);border:1px solid rgba(255,255,255,0.25)',
}[t] ?? '')

const tierBadgeStyle = (t) => ({
  A: 'background:rgba(52,211,153,0.15);color:#34d399;border:1px solid rgba(52,211,153,0.3)',
  B: 'background:rgba(96,165,250,0.15);color:#93c5fd;border:1px solid rgba(96,165,250,0.3)',
  C: 'background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.3)',
  D: 'background:rgba(248,113,113,0.15);color:#f87171;border:1px solid rgba(248,113,113,0.3)',
}[t] ?? 'background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.4)')

// ── 커뮤니티 인기 ────────────────────────────
const communityList    = ref([])
const communityLoading = ref(false)
const communityError   = ref(false)

// ══════════════════════════════════════════════
// [더미데이터] API 연결 후 아래 MOCK_POPULAR 블록 전체 삭제
// ══════════════════════════════════════════════
const MOCK_POPULAR = [
  { id:1, ticker:'005930', title:'삼성전자 AI 칩 수요 폭발…목표주가 상향 잇따라',         views:3420, likes:187, comment_count:34, popularity:601 },
  { id:2, ticker:'000660', title:'SK하이닉스 HBM3E 독점 공급 체제 굳힌다',                views:2891, likes:143, comment_count:28, popularity:499 },
  { id:3, ticker:'035420', title:'NAVER 하이퍼클로바X 기업 서비스 확대, 실적 전망↑',      views:2104, likes:98,  comment_count:19, popularity:353 },
  { id:4, ticker:'051910', title:'LG화학 배터리 소재 수주 급증…2분기 깜짝 실적 예상',     views:1876, likes:76,  comment_count:15, popularity:283 },
  { id:5, ticker:null,     title:'코스피 2900선 돌파 시도, 외국인 5거래일 연속 순매수',   views:5200, likes:224, comment_count:47, popularity:819 },
  { id:6, ticker:'035720', title:'카카오 AI 에이전트 서비스 출시…플랫폼 경쟁력 강화',     views:1654, likes:62,  comment_count:11, popularity:241 },
  { id:7, ticker:'207940', title:'삼성바이오로직스, 글로벌 CMO 계약 연속 수주',           views:1432, likes:55,  comment_count:9,  popularity:198 },
  { id:8, ticker:null,     title:'Fed 금리 동결 시사에 성장주 강세…나스닥 +1.8%',         views:4870, likes:198, comment_count:39, popularity:742 },
]
// ══════════════════════════════════════════════ [더미데이터 끝]

async function fetchCommunity() {
  communityLoading.value = true
  communityError.value   = false
  try {
    const { data } = await stocksApi.getPopularPosts(20)
    communityList.value = data.items ?? []
  } catch {
    communityError.value = false               // [더미데이터] 연결 후 → true 로 변경
    communityList.value  = MOCK_POPULAR        // [더미데이터] 연결 후 → [] 로 변경
  } finally {
    communityLoading.value = false
  }
}

// ── 급상승 종목 ───────────────────────────────
const risingList    = ref([])
const risingLoading = ref(false)
const risingError   = ref(false)

// ══════════════════════════════════════════════
// [더미데이터] API 연결 후 아래 MOCK_RISING 블록 전체 삭제
// ══════════════════════════════════════════════
const MOCK_RISING = [
  { ticker:'060230', name:'제이케이시냅스',  sector:'IT',       score:100, score_change:18.5, tier:'A' },
  { ticker:'373110', name:'엑셀세라퓨틱스',  sector:'건강관리',  score:98,  score_change:15.2, tier:'A' },
  { ticker:'246710', name:'티엔알바이오팹',  sector:'건강관리',  score:97,  score_change:13.8, tier:'A' },
  { ticker:'279600', name:'미디어젠',        sector:'IT',       score:96,  score_change:12.1, tier:'A' },
  { ticker:'313760', name:'캐리',            sector:'경기소비재', score:94,  score_change:10.7, tier:'A' },
  { ticker:'086520', name:'에코프로',        sector:'소재',      score:91,  score_change: 9.3, tier:'A' },
  { ticker:'196170', name:'알테오젠',        sector:'건강관리',  score:89,  score_change: 8.1, tier:'B' },
  { ticker:'041510', name:'에스엠',          sector:'커뮤니케이션', score:85, score_change: 7.4, tier:'B' },
]
// ══════════════════════════════════════════════ [더미데이터 끝]

async function fetchRising() {
  risingLoading.value = true
  risingError.value   = false
  try {
    const { data } = await stocksApi.getRisingStocks({ limit: 20 })
    risingList.value = data.items ?? []
  } catch {
    risingError.value = false                  // [더미데이터] 연결 후 → true 로 변경
    risingList.value  = MOCK_RISING            // [더미데이터] 연결 후 → [] 로 변경
  } finally {
    risingLoading.value = false
  }
}

// ── 탭 전환 ──────────────────────────────────
function switchTab(key) {
  activeTab.value = key
  showSearch.value = false
  if (key === 'recommend' && screenerStore.items.length === 0) screenerStore.fetchScreener()
  if (key === 'community' && communityList.value.length === 0) fetchCommunity()
  if (key === 'rising'    && risingList.value.length === 0)    fetchRising()
}

// ── 검색 오버레이 ─────────────────────────────
const showSearch     = ref(false)
const searchQuery    = ref('')
const searchLoading  = ref(false)
const searchInputRef = ref(null)

// 버전/기준일 (FilterPanel 요소)
const searchVersions = ref([])
const searchDates    = ref([])

// 부가설정 기본 펼침
const financialOpen = ref(true)

// 프리셋
const PRESET_KEY  = 'company_search_presets'
const presetName  = ref('')
const savedPresets = ref(JSON.parse(localStorage.getItem(PRESET_KEY) ?? '[]'))

// 검색 오버레이 전용 필터 (screener store와 독립)
const searchFilters = ref({
  model_version:     'latest',
  date:              null,
  tier:              null,
  min_score:         0,
  sector:            null,
  // 재무 (부가설정)
  max_per:           null,
  max_pbr:           null,
  min_roe:           null,
  max_debt_ratio:    null,
  min_op_margin:     null,
  min_rev_growth:    null,
  min_finance_score: null,
  // 정렬 & 결과수 (부가설정)
  sort_by:           'composite_score',
  limit:             100,
})

// 검색 오버레이용 종목 목록
const searchAllItems = ref([])

const rawToItem = (s) => ({
  id:         s.ticker,
  ticker:     s.ticker,
  name:       s.name ?? s.ticker,
  sector:     s.sector ?? '',
  score:      Math.round(s.composite_score ?? s.score ?? 0),
  tier:       s.tier ?? '—',
  price:      s.close_price ?? s.price ?? 0,
  change:     s.change_rate ?? s.change ?? 0,
  color:      scoreToColor(Math.round(s.composite_score ?? s.score ?? 0)),
  marketCap:  s.market_cap_str ?? '',
  per:        s.per ?? null,
  pbr:        s.pbr ?? null,
  dividend:   s.dividend_yield ?? null,
  quantScore: Math.round(s.composite_score ?? s.score ?? 0),
  mlScore:    Math.round(s.score ?? 0),
  finScore:   Math.round(s.finance_score ?? 0),
  description: '',
})

// ── Tier 분포 집계 ────────────────────────────
const tierCounts = computed(() => {
  const c = { A: 0, B: 0, C: 0, D: 0 }
  for (const s of searchAllItems.value) {
    if (s.tier in c) c[s.tier]++
  }
  return c
})

// ── CSV 내보내기 ──────────────────────────────
function exportCsv() {
  const headers = ['티커', '종목명', '섹터', 'Tier', '복합점수', 'ML점수', '재무점수', '현재가', '등락률']
  const rows = searchDisplayList.value.map(s => [
    s.ticker, s.name, s.sector, s.tier,
    s.quantScore, s.mlScore, s.finScore,
    s.price, s.change,
  ])
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url
  a.download = `stocks_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// 텍스트 검색 + 가나다 정렬
const searchDisplayList = computed(() => {
  let list = searchAllItems.value
  const q = searchQuery.value.trim().toLowerCase()
  if (q) list = list.filter(s => s.name.toLowerCase().includes(q) || s.ticker.toLowerCase().includes(q))
  return [...list].sort((a, b) => a.name.localeCompare(b.name, 'ko-KR'))
})

// 필터 → 서버 fetch (300ms 디바운스)
let searchFetchTimer = null
async function fetchSearchAll() {
  searchLoading.value = true
  try {
    const f = searchFilters.value
    const params = {}
    if (f.model_version)          params.model_version      = f.model_version
    if (f.date)                   params.date               = f.date
    if (f.tier)                   params.tier               = f.tier
    if (f.min_score > 0)          params.min_score          = f.min_score
    if (f.sector)                 params.sector             = f.sector
    if (f.max_per != null)        params.max_per            = f.max_per
    if (f.max_pbr != null)        params.max_pbr            = f.max_pbr
    if (f.min_roe != null)        params.min_roe            = f.min_roe
    if (f.max_debt_ratio != null) params.max_debt_ratio     = f.max_debt_ratio
    if (f.min_op_margin != null)  params.min_op_margin      = f.min_op_margin
    if (f.min_rev_growth != null) params.min_rev_growth     = f.min_rev_growth
    if (f.min_finance_score != null) params.min_finance_score = f.min_finance_score
    params.sort_by = f.sort_by ?? 'composite_score'
    params.limit   = f.limit   ?? 100

    const { data } = await screenerApi.getScreener(params)
    searchAllItems.value = (data.items ?? []).map(rawToItem)
  } catch {
    searchAllItems.value = []
  } finally {
    searchLoading.value = false
  }
}

watch(searchFilters, () => {
  clearTimeout(searchFetchTimer)
  searchFetchTimer = setTimeout(fetchSearchAll, 300)
}, { deep: true })

// 검색창 열릴 때: 버전/날짜 로드 + fetch + 포커스
watch(showSearch, async (v) => {
  if (v) {
    if (searchAllItems.value.length === 0) fetchSearchAll()
    if (searchVersions.value.length === 0) {
      try {
        const { data } = await stocksApi.getVersions()
        searchVersions.value = data.versions ?? []
      } catch {}
    }
    if (searchDates.value.length === 0) {
      try {
        const { data } = await stocksApi.getDates('latest')
        searchDates.value = [...(data.dates ?? [])].reverse()
      } catch {}
    }
    await nextTick()
    searchInputRef.value?.focus()
  } else {
    searchQuery.value = ''
  }
})

// 프리셋
function savePreset() {
  const name = presetName.value.trim()
  if (!name) return
  const list = JSON.parse(localStorage.getItem(PRESET_KEY) ?? '[]')
  if (!list.includes(name)) list.push(name)
  localStorage.setItem(PRESET_KEY, JSON.stringify(list))
  localStorage.setItem(`${PRESET_KEY}:${name}`, JSON.stringify(searchFilters.value))
  savedPresets.value = list
  presetName.value = ''
}
function loadPreset(name) {
  const saved = localStorage.getItem(`${PRESET_KEY}:${name}`)
  if (saved) Object.assign(searchFilters.value, JSON.parse(saved))
}
function deletePreset(name) {
  const list = savedPresets.value.filter(n => n !== name)
  localStorage.setItem(PRESET_KEY, JSON.stringify(list))
  localStorage.removeItem(`${PRESET_KEY}:${name}`)
  savedPresets.value = list
}

function resetFinancialFilters() {
  const f = searchFilters.value
  f.max_per = f.max_pbr = f.min_roe = f.max_debt_ratio = null
  f.min_op_margin = f.min_rev_growth = f.min_finance_score = null
}
function resetSearchFilters() {
  searchFilters.value = {
    model_version: 'latest', date: null, tier: null, min_score: 0, sector: null,
    max_per: null, max_pbr: null, min_roe: null, max_debt_ratio: null,
    min_op_margin: null, min_rev_growth: null, min_finance_score: null,
    sort_by: 'composite_score', limit: 100,
  }
}

function closeSearch() {
  showSearch.value = false
}

function selectSearchResult(s) {
  closeSearch()
  const company = s.id ? s : { ...s, id: s.ticker }
  openDetail(company)
}

async function openDetailByTicker(ticker) {
  const allItems = [...screenerStore.items, ...risingList.value, ...searchAllItems.value]
  const raw = allItems.find(s => s.ticker === ticker)
  const company = raw
    ? rawToItem(raw)
    : companies.value.find(c => c.ticker === ticker)
  if (company) openDetail(company)
}

// ── 공통 배지 헬퍼 ───────────────────────────
const rankBadge = (rank) => {
  if (rank === 1) return 'background:rgba(251,191,36,0.22);color:#fbbf24;border:1px solid rgba(251,191,36,0.38)'
  if (rank === 2) return 'background:rgba(148,163,184,0.18);color:#94a3b8;border:1px solid rgba(148,163,184,0.3)'
  if (rank === 3) return 'background:rgba(180,120,60,0.18);color:#cd7f32;border:1px solid rgba(180,120,60,0.32)'
  return 'background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.38);border:1px solid rgba(255,255,255,0.1)'
}

// ── 초기 로드 ────────────────────────────────
onMounted(async () => {
  if (stocksStore.items.length === 0) {
    await stocksStore.initVersionsAndDates()
    await stocksStore.fetchRecommendations()
  }
  await screenerStore.fetchScreener()
})

const addedIds      = ref(new Set());
const detailCompany = ref(null);

const quantBarColor  = (s) => s >= 70 ? 'bg-green-400' : s >= 45 ? 'bg-yellow-400' : 'bg-red-400';
const quantTextColor = (s) => s >= 70 ? 'text-green-300' : s >= 45 ? 'text-yellow-300' : 'text-red-300';

// ── 교체 비교 ──────────────────────────────────
const compareCandidate = ref(null);
const compareAction    = ref(null); // 'sell' | 'buy' | null
const comparePrice     = ref(0);
const compareQty       = ref(1);

const currentStockInfo = computed(() =>
  props.replaceStock ? companies.value.find(c => c.ticker === props.replaceStock.ticker) : null
);

const openCompare = (company) => {
  compareCandidate.value = company;
  compareAction.value    = null;
};

const openCompareOrder = (type) => {
  compareAction.value = type;
  comparePrice.value  = type === 'sell'
    ? (props.replaceStock?.currentPrice ?? 0)
    : compareCandidate.value.price;
  compareQty.value = type === 'sell'
    ? (props.replaceStock?.shares ?? 1)
    : 1;
};

const confirmCompareOrder = () => {
  if (compareAction.value === 'buy') {
    emit('select-company', {
      id:           Date.now(),
      company:      compareCandidate.value.name,
      ticker:       compareCandidate.value.ticker,
      sector:       compareCandidate.value.sector,
      shares:       compareQty.value,
      avgPrice:     comparePrice.value,
      currentPrice: compareCandidate.value.price,
      change:       compareCandidate.value.change,
      color:        compareCandidate.value.color,
      weight:       10,
      quantScore:   compareCandidate.value.quantScore,
    });
  } else if (compareAction.value === 'sell') {
    emit('sell-replace');
  }
  compareCandidate.value = null;
  compareAction.value    = null;
};

// ── 상세 차트 ─────────────────────────────────
const showChart      = ref(false)
const apiChartData   = ref([])
const chartLoading   = ref(false)

const detailChartData = computed(() => {
  if (apiChartData.value.length > 0) return apiChartData.value
  if (!detailCompany.value) return []
  // fallback: 목업 데이터
  return generateMockOHLC(detailCompany.value.ticker, detailCompany.value.price ?? 50000)
})

async function fetchChart(ticker) {
  chartLoading.value = true
  apiChartData.value = []
  try {
    const { data } = await chartApi.getCandles(ticker, '1y')
    apiChartData.value = (data.items ?? []).map(c => ({ close: c.close ?? c.price ?? 0, ...c }))
  } catch {
    // fallback to mock
  } finally {
    chartLoading.value = false
  }
}

// 개요 스파크라인: 템플릿에서 사용 시 아래 주석 해제
// const overviewPrices = computed(() => detailChartData.value.slice(-60).map(d => d.close))
// const overviewPaths = computed(() => { /* SVG path 계산 */ })

// ── 상세 차트 (기간별) ────────────────────────────
const chartPeriod = ref('3M');
const periodSlice = { '1M': 20, '3M': 60, '6M': 120, '1Y': 252 };

const detailPrices = computed(() => {
  const n = periodSlice[chartPeriod.value] ?? 60;
  return detailChartData.value.slice(-n).map(d => d.close);
});

const detailPaths = computed(() => {
  const prices = detailPrices.value;
  if (prices.length < 2) return { area: '', line: '' };
  const W = 300, H = 200, PH = 6, PV = 8;
  const uw = W - PH * 2, uh = H - PV * 2;
  const minP = Math.min(...prices), maxP = Math.max(...prices);
  const range = maxP - minP || 1;
  const pts = prices.map((p, i) => {
    const x = PH + (i / (prices.length - 1)) * uw;
    const y = PV + (1 - (p - minP) / range) * uh;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const line = `M ${pts[0]} L ${pts.slice(1).join(' L ')}`;
  const area = `${line} L ${(PH + uw).toFixed(1)},${H} L ${PH},${H} Z`;
  return { area, line };
});

const chartPriceRange = computed(() => {
  const prices = detailPrices.value;
  if (!prices.length) return { min: 0, max: 0 };
  return { min: Math.round(Math.min(...prices)), max: Math.round(Math.max(...prices)) };
});

const chartStartLabel = computed(() => ({
  '1M': '1개월 전', '3M': '3개월 전', '6M': '6개월 전', '1Y': '1년 전',
}[chartPeriod.value] ?? ''));

// ── 재무 지표 (우측 패널) ────────────────────────
const detailMetrics = computed(() => {
  if (!detailCompany.value) return [];
  return [
    { label: '시가총액',   value: detailCompany.value.marketCap },
    { label: 'PER',        value: detailCompany.value.per + 'x' },
    { label: 'PBR',        value: detailCompany.value.pbr + 'x' },
    { label: '배당수익률', value: detailCompany.value.dividend + '%' },
  ];
});

// ── 보유 현황 (임시 데이터) ──────────────────────
const mockHoldings = computed(() => {
  if (!detailCompany.value) return [];
  const t = detailCompany.value.ticker;
  let seed = t.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  if (seed % 3 === 0) return [];
  const n = (seed % 2) + 1;
  const pfNames = ['포트폴리오 A', '포트폴리오 B', '포트폴리오 C'];
  return Array.from({ length: n }, (_, i) => {
    const adj = ((seed + i * 13) % 30) - 10;
    return {
      portfolio: pfNames[i],
      shares:    5 + (seed + i * 7) % 20,
      avgPrice:  Math.round(detailCompany.value.price * (1 + adj / 100)),
    };
  });
});

// ── 상세 뷰 ────────────────────────────────────
watch(() => props.viewTicker, (ticker) => {
  if (ticker) {
    detailCompany.value = companies.value.find(c => c.ticker === ticker) ?? null
    if (ticker) fetchChart(ticker)
  }
}, { immediate: true })

const openDetail = (company) => {
  detailCompany.value = company
  showChart.value     = false
  showFinancial.value = false
  finTab.value        = 'income'
  fetchChart(company.ticker)
}
const closeDetail = () => {
  detailCompany.value = null;
  showChart.value     = false;
  showFinancial.value = false;
  if (props.viewTicker) emit('back');
};

// ── 주문 모달 ──────────────────────────────────
const orderCompany = ref(null);
const orderType    = ref('buy');
const orderPrice   = ref(0);
const orderQty     = ref(1);

const openOrderModal = (company, type = 'buy') => {
  orderCompany.value = company;
  orderType.value    = type;
  orderPrice.value   = company.price;
  orderQty.value     = 1;
};
const closeOrderModal = () => { orderCompany.value = null; };

const confirmOrder = () => {
  if (orderType.value === 'buy') {
    addedIds.value = new Set([...addedIds.value, orderCompany.value.id]);
    emit('add-company', {
      id:           Date.now(),
      company:      orderCompany.value.name,
      ticker:       orderCompany.value.ticker,
      sector:       orderCompany.value.sector,
      shares:       orderQty.value,
      avgPrice:     orderPrice.value,
      currentPrice: orderCompany.value.price,
      change:       orderCompany.value.change,
      color:        orderCompany.value.color,
      weight:       10,
    });
  }
  closeOrderModal();
};

// ── 교체 모드 ──────────────────────────────────
// selectCompany 사용 시 아래 주석 해제
// const buildPortfolioItem = (company) => ({
//   id: Date.now(), company: company.name, ticker: company.ticker,
//   sector: company.sector, shares: 10, avgPrice: company.price,
//   currentPrice: company.price, change: company.change, color: company.color, weight: 10,
// })

// 포트폴리오 직접 추가용 (필요 시 템플릿에서 @click="selectCompany(company)" 로 연결)
// const selectCompany = (company) => { emit('select-company', buildPortfolioItem(company)) }

// ── 재무제표 ─────────────────────────────────
// [API] GET /api/financials/{ticker}/annual 로 교체
const showFinancial = ref(false);
const finTab        = ref('income');

const FIN_TABS = [
  { key: 'income',   label: '손익계산서' },
  { key: 'balance',  label: '재무상태표' },
  { key: 'cashflow', label: '현금흐름표' },
];

const finData = computed(() => {
  const co = detailCompany.value;
  if (!co) return null;
  // marketCap 파싱: "443조" → 4430000억
  const mcMatch = co.marketCap?.match(/(\d+)조/);
  const mcBil   = mcMatch ? parseInt(mcMatch[1]) * 10000 : 10000;
  // ticker 기반 결정론적 시드
  let seed = co.ticker.split('').reduce((a, c) => a * 31 + c.charCodeAt(0), 1);
  const rng = () => { seed = (seed * 1664525 + 1013904223) & 0x7fffffff; return seed / 0x7fffffff; };

  const baseRev = mcBil * (0.28 + rng() * 0.44);
  const years   = [2022, 2023, 2024];

  const income = years.map(() => {
    const rev  = Math.round(baseRev * (0.80 + rng() * 0.40));
    const opM  = 0.04 + rng() * 0.18;
    const netM = opM * (0.42 + rng() * 0.42);
    return {
      revenue:         rev,
      operatingProfit: Math.round(rev * opM),
      operatingMargin: +(opM  * 100).toFixed(1),
      netIncome:       Math.round(rev * netM),
      netMargin:       +(netM * 100).toFixed(1),
    };
  });

  const assetBase        = mcBil * (0.65 + rng() * 1.0);
  const liabRatio        = 0.25 + rng() * 0.42;
  const totalAssets      = Math.round(assetBase);
  const totalLiabilities = Math.round(assetBase * liabRatio);
  const totalEquity      = totalAssets - totalLiabilities;

  const cashflow = years.map(() => {
    const op = Math.round(baseRev * (0.05 + rng() * 0.14));
    return {
      operating:  op,
      investing: -Math.round(op * (0.22 + rng() * 0.48)),
      financing: -Math.round(op * (0.07 + rng() * 0.28)),
    };
  });

  return {
    years,
    income,
    balance: { totalAssets, totalLiabilities, totalEquity,
               debtRatio: Math.round((totalLiabilities / (totalEquity || 1)) * 100) },
    cashflow,
  };
});

const incomeRows = computed(() => {
  if (!finData.value) return [];
  const { income } = finData.value;
  return [
    { key: 'rev',  label: '매출액',     values: income.map(d => d.revenue),          color: false },
    { key: 'op',   label: '영업이익',   values: income.map(d => d.operatingProfit),  color: true, hl: true },
    { key: 'opM',  label: '영업이익률', values: income.map(d => d.operatingMargin),  color: true, pct: true },
    { key: 'net',  label: '당기순이익', values: income.map(d => d.netIncome),        color: true },
    { key: 'netM', label: '순이익률',   values: income.map(d => d.netMargin),        color: true, pct: true },
  ];
});

const maxRevenue = computed(() =>
  finData.value ? Math.max(...finData.value.income.map(d => d.revenue)) : 1
);

const balanceRows = computed(() => {
  if (!finData.value) return [];
  const { balance } = finData.value;
  return [
    { key: 'asset', label: '자산총계', val: balance.totalAssets,      hl: true  },
    { key: 'liab',  label: '부채총계', val: balance.totalLiabilities, hl: false },
    { key: 'eq',    label: '자본총계', val: balance.totalEquity,       hl: false },
  ];
});

const equityRatio = computed(() => {
  if (!finData.value) return 0.5;
  return finData.value.balance.totalEquity / (finData.value.balance.totalAssets || 1);
});

const cashflowRows = computed(() => {
  if (!finData.value) return [];
  const { cashflow } = finData.value;
  return [
    { key: 'op',  label: '영업활동', values: cashflow.map(d => d.operating) },
    { key: 'inv', label: '투자활동', values: cashflow.map(d => d.investing) },
    { key: 'fin', label: '재무활동', values: cashflow.map(d => d.financing) },
    { key: 'net', label: '순현금',   values: cashflow.map(d => d.operating + d.investing + d.financing) },
  ];
});

const maxOperating = computed(() =>
  finData.value ? Math.max(...finData.value.cashflow.map(d => d.operating)) : 1
);
</script>

<style scoped>
/* 재무제표 앞/뒷면 전환 — opacity만 사용 */
.fin-face {
  transition: opacity 0.25s ease;
}
.fin-face--show {
  opacity: 1;
  pointer-events: auto;
}
.fin-face--hide {
  opacity: 0;
  pointer-events: none;
}

.order-modal-enter-active { transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.25s ease; }
.order-modal-leave-active { transition: transform 0.25s ease-in, opacity 0.2s ease; }
.order-modal-enter-from,
.order-modal-leave-to    { transform: translateY(100%); opacity: 0; }

.order-inline-enter-active { transition: opacity 0.2s ease, max-height 0.3s cubic-bezier(0.22, 1, 0.36, 1); max-height: 200px; overflow: hidden; }
.order-inline-leave-active { transition: opacity 0.15s ease, max-height 0.2s ease; max-height: 200px; overflow: hidden; }
.order-inline-enter-from,
.order-inline-leave-to    { opacity: 0; max-height: 0; }

/* 검색 오버레이 — 위에서 슬라이드 */
.search-slide-enter-active { transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.2s ease; }
.search-slide-leave-active { transition: transform 0.22s ease-in, opacity 0.18s ease; }
.search-slide-enter-from,
.search-slide-leave-to    { transform: translateY(-100%); opacity: 0; }
</style>
