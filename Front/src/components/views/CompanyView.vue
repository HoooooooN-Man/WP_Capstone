<template>
  <!-- 카드 루트 -->
  <div class="w-full h-full overflow-hidden relative"
       :style="props.darkMode ? {
         background:'#0f1e3d', color:'#e8e4dc', fontFamily:'Inter,sans-serif',
         '--c-fg':'#e8e4dc', '--c-fg2':'rgba(232,228,220,0.55)', '--c-fg3':'rgba(232,228,220,0.35)',
         '--c-border':'rgba(255,255,255,0.12)', '--c-card':'rgba(255,255,255,0.05)',
         '--c-header-border':'rgba(255,255,255,0.15)',
       } : {
         background:'#244d8c', color:'#e8e4dc', fontFamily:'Inter,sans-serif',
         '--c-fg':'#e8e4dc', '--c-fg2':'rgba(232,228,220,0.55)', '--c-fg3':'rgba(232,228,220,0.35)',
         '--c-border':'rgba(255,255,255,0.12)', '--c-card':'rgba(255,255,255,0.05)',
         '--c-header-border':'rgba(255,255,255,0.2)',
       }">

      <!-- ── 앞면 ── -->
      <div class="absolute inset-0 flex flex-col fin-face"
           :class="showFinancial ? 'fin-face--hide' : 'fin-face--show'">

    <!-- 헤더 (보고서 테마) -->
    <div class="px-6 pt-4 pb-3 flex-shrink-0" style="border-bottom:2px solid var(--c-header-border);">
      <!-- 보고서 상단 레이블 -->
      <div class="flex items-center justify-between mb-1" v-if="!detailCompany">
        <span class="text-[9px] font-bold uppercase tracking-[0.3em]" style="color:#888;font-family:sans-serif;">Market Intelligence Report</span>
      </div>
      <div class="flex items-center gap-3">
        <button v-if="detailCompany" @click="closeDetail"
                class="flex items-center gap-1 transition-colors mr-1" style="color:var(--c-fg2)">
          <LucideChevronLeft class="w-5 h-5" />
        </button>
        <h2 class="text-2xl font-black tracking-tighter uppercase" style="color:var(--c-fg);font-family:Georgia,serif;">
          {{ detailCompany ? detailCompany.name : 'STOCK ANALYSIS' }}
        </h2>
        <div v-if="replaceMode && !detailCompany" class="flex items-stretch gap-2">
          <div class="px-2.5 flex items-center rounded border" style="background:rgba(52,211,153,0.15);border-color:rgba(52,211,153,0.35);color:#34d399">
            <span class="text-[12px] font-bold uppercase tracking-wider">교체 선택 중</span>
          </div>
          <button @click="emit('cancel-replace')"
                  class="px-2.5 flex items-center rounded border text-[12px] font-bold uppercase tracking-wider transition-all"
                  style="background:rgba(248,113,113,0.12);border-color:rgba(248,113,113,0.3);color:#f87171">
            취소
          </button>
        </div>
        <button v-if="detailCompany && !replaceMode"
                @click="showFinancial = true"
                class="ml-auto px-2.5 py-1.5 rounded-lg text-[12px] font-bold tracking-wide flex-shrink-0 flex items-center gap-1 transition-all"
                style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.18);color:var(--c-fg2)">
          <LucideBarChart2 class="w-3 h-3" />
          재무제표
        </button>
        <div v-if="!detailCompany" class="ml-auto flex items-center gap-1.5">
          <button @click="openCompareOverlay"
                  class="w-8 h-8 flex items-center justify-center rounded-lg border transition-all flex-shrink-0"
                  :class="showCompare ? '' : ''"
                  :style="showCompare
                    ? 'background:rgba(255,255,255,0.12);border-color:var(--c-fg2);color:var(--c-fg)'
                    : 'background:rgba(255,255,255,0.06);border-color:rgba(255,255,255,0.18);color:var(--c-fg2)'">
            <LucideArrowLeftRight class="w-3.5 h-3.5" />
          </button>
          <button @click="showSearch = true"
                  class="w-8 h-8 flex items-center justify-center rounded-lg transition-all flex-shrink-0"
                  style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.18);color:var(--c-fg2)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
          </button>
        </div>
      </div>
      <p v-if="replaceMode && !detailCompany" class="text-[12px] mt-1" style="color:var(--c-fg2)">교체할 종목을 선택하세요</p>
    </div>

    <!-- 탭 바 (보고서 섹션 탭) -->
    <div v-if="!detailCompany" class="px-4 pt-2.5 pb-2 flex-shrink-0">
      <div class="flex gap-0" style="border-bottom:1px solid var(--c-border)">
        <button v-for="tab in STOCK_TABS" :key="tab.key"
                @click="switchTab(tab.key)"
                class="px-4 py-2 text-[12px] font-bold transition-all duration-150"
                :style="activeTab === tab.key
                  ? 'color:var(--c-fg);border-bottom:2px solid rgba(232,228,220,0.7);margin-bottom:-1px'
                  : 'color:var(--c-fg2)'">
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 기업 상세 뷰 — 좌우 분할 레이아웃 -->
    <div v-if="detailCompany" class="flex-1 flex flex-col overflow-hidden">
    <div class="flex-1 flex flex-row overflow-hidden min-h-0">

      <!-- ── 왼쪽: 주가 차트 (3/5) ── -->
      <div class="flex-[3] flex flex-col border-r border-white/10 overflow-hidden min-w-0">

        <!-- 기간 탭 -->
        <div class="flex gap-0.5 px-3 pt-3 pb-1 flex-shrink-0">
          <button v-for="p in ['1M','3M','6M','1Y']" :key="p"
                  @click="chartPeriod = p"
                  class="px-2 py-0.5 rounded text-[11px] font-bold transition-all duration-150"
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
            <p class="text-[10px] uppercase tracking-widest mb-0.5" style="color:var(--c-fg2)">
              {{ detailCompany.sector }}
            </p>
            <p class="text-xl font-black leading-tight" style="color:var(--c-fg)">₩{{ detailCompany.price.toLocaleString() }}</p>
            <span class="inline-block mt-0.5 px-2 py-0.5 rounded-lg text-[12px] font-bold"
                  :class="detailCompany.change >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'">
              {{ detailCompany.change >= 0 ? '+' : '' }}{{ detailCompany.change }}%
            </span>
            <!-- 공정가치 배지 -->
            <div v-if="fairValue" class="mt-1.5 px-2 py-1 rounded text-[11px]"
                 style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border)">
              <span style="color:var(--c-fg2)">적정가치</span>
              <span class="font-bold ml-1" style="color:var(--c-fg)">₩{{ fairValue.fair_value?.toLocaleString() }}</span>
              <span class="ml-1 font-bold text-[10px]"
                    :class="fairValue.deviation_pct >= 0 ? 'text-green-600' : 'text-red-500'">
                {{ fairValue.deviation_pct >= 0 ? '+' : '' }}{{ fairValue.deviation_pct?.toFixed(1) }}%
              </span>
              <span class="ml-1 text-[10px]" style="color:var(--c-fg2)">{{ fairValue.band_ko }}</span>
            </div>
          </div>

          <!-- 종목 컬러 구분선 -->
          <div class="h-px rounded-full" :style="{ background: detailCompany.color, opacity: 0.45 }"></div>

          <!-- 재무 지표 -->
          <div class="space-y-1.5">
            <div v-for="m in detailMetrics" :key="m.label" class="flex justify-between items-center">
              <span class="text-[10px]" style="color:var(--c-fg2)">{{ m.label }}</span>
              <span class="text-[12px] font-bold" style="color:var(--c-fg)">{{ m.value }}</span>
            </div>
          </div>

          <!-- 5요인 레이더 차트 -->
          <div v-if="radarData" class="mt-3">
            <p class="text-[10px] font-bold uppercase tracking-widest mb-2"
               style="color:var(--c-fg2);font-family:sans-serif;">SMART SCORE</p>
            <div class="relative flex items-center justify-center">
              <svg viewBox="0 0 120 110" class="w-full" style="max-width:140px">
                <!-- 배경 오각형들 -->
                <polygon v-for="level in [0.25,0.5,0.75,1.0]" :key="level"
                         :points="hexPoints(60, 55, 45*level)"
                         fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="0.8"/>
                <!-- 데이터 오각형 -->
                <polygon :points="radarPoints"
                         fill="rgba(201,162,39,0.15)" stroke="#c9a227" stroke-width="1.5"/>
                <!-- 축 라벨 -->
                <text x="60" y="6" text-anchor="middle" font-size="7" fill="rgba(232,228,220,0.55)">성장성</text>
                <text x="108" y="32" text-anchor="middle" font-size="7" fill="rgba(232,228,220,0.55)">수익성</text>
                <text x="90" y="104" text-anchor="middle" font-size="7" fill="rgba(232,228,220,0.55)">안전성</text>
                <text x="30" y="104" text-anchor="middle" font-size="7" fill="rgba(232,228,220,0.55)">해자</text>
                <text x="12" y="32" text-anchor="middle" font-size="7" fill="rgba(232,228,220,0.55)">현금흐름</text>
              </svg>
            </div>
          </div>

          <!-- 배당 정보 -->
          <div v-if="dividendData && dividendData.yield_pct" class="mt-2 pt-2"
               style="border-top:1px solid var(--c-border)">
            <p class="text-[10px] font-bold uppercase tracking-widest mb-1.5"
               style="color:var(--c-fg2);font-family:sans-serif;">배당</p>
            <div class="flex flex-wrap gap-1.5">
              <span class="text-[10px] px-2 py-0.5 rounded-full"
                    style="background:rgba(255,255,255,0.08);color:var(--c-fg)">
                수익률 {{ dividendData.yield_pct?.toFixed(1) }}%
              </span>
              <span v-if="dividendData.years_paid" class="text-[10px] px-2 py-0.5 rounded-full"
                    style="background:rgba(255,255,255,0.08);color:var(--c-fg)">
                {{ dividendData.years_paid }}년 지급
              </span>
              <span v-if="dividendData.dps_growth_yoy > 0" class="text-[10px] px-2 py-0.5 rounded-full"
                    style="background:rgba(5,95,70,0.08);color:#065f46">
                YoY +{{ dividendData.dps_growth_yoy?.toFixed(1) }}%
              </span>
            </div>
          </div>

        </div>

        <!-- 교체 비교 버튼 (교체 모드일 때만) -->
        <div v-if="replaceMode" class="px-3 pb-3 pt-2 flex gap-1.5 flex-shrink-0 border-t border-white/8">
          <button @click="openCompare(detailCompany)"
            class="flex-1 py-2 rounded-xl text-xs font-bold transition-colors
                   bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30">
            교체 비교
          </button>
        </div>
      </div>

    </div><!-- /좌우 분할 -->

    <!-- 경쟁사/동종 섹터 종목 -->
    <div v-if="peers.length" class="flex-shrink-0 px-4 py-3" style="border-top:1px solid var(--c-border)">
      <p class="text-[10px] font-bold uppercase tracking-widest mb-2"
         style="color:var(--c-fg2);font-family:sans-serif;">동종 섹터</p>
      <div class="flex flex-col gap-1">
        <div v-for="peer in peers" :key="peer.ticker"
             class="flex items-center gap-2 py-1 cursor-pointer rounded px-1 transition-colors"
             style="hover:background:var(--c-card)"
             @click="openDetail(peer)">
          <div class="w-1.5 h-1.5 rounded-full flex-shrink-0" :style="{ background: peer.color ?? '#888' }"></div>
          <span class="text-[12px] font-bold flex-1" style="color:var(--c-fg)">{{ peer.name }}</span>
          <span class="text-[10px] font-mono" style="color:var(--c-fg2)">{{ peer.ticker }}</span>
          <span class="text-[10px] font-black px-1.5 py-0.5 leading-none flex-shrink-0"
                :style="tierBadgeStyle(peer.tier)">{{ peer.tier }}</span>
          <span class="text-[11px] font-black flex-shrink-0" style="color:#c9a227">{{ Math.round(peer.score ?? 0) }}</span>
        </div>
      </div>
    </div>

    </div><!-- /기업 상세 뷰 -->

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
            <span class="text-[11px] text-white/30">종목 분석 중...</span>
          </div>
          <!-- 결과 없음 -->
          <div v-else-if="recommendList.length === 0" class="flex flex-col items-center justify-center h-20 gap-1">
            <span class="text-[12px]" style="color:var(--c-fg2)">조건에 맞는 종목이 없습니다</span>
          </div>
          <div v-else
            v-for="company in recommendList" :key="company.id"
            class="flex items-center gap-3 p-3 transition-all duration-200 cursor-pointer"
            style="border-bottom:1px solid var(--c-border);"
            :style="replaceMode ? 'background:rgba(5,150,105,0.03)' : ''"
            @click="replaceMode ? openCompare(company) : openDetail(company)"
          >
            <!-- 티어 배지 + 점수 (맨 왼쪽) -->
            <div class="flex flex-col items-center gap-1 flex-shrink-0 w-[38px]">
              <span class="text-[10px] font-black px-1.5 py-0.5 leading-none w-full text-center"
                    :style="tierBadgeStyle(company.tier)">
                {{ company.tier }}
              </span>
              <span class="text-[12px] font-black" style="color:#c9a227">{{ Math.round(company.quantScore ?? company.score ?? 0) }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <p class="font-bold text-sm truncate" style="color:var(--c-fg)">{{ company.name }}</p>
                <span class="text-[11px] font-mono flex-shrink-0" style="color:var(--c-fg2)">{{ company.ticker }}</span>
              </div>
              <p class="text-[11px]" style="color:var(--c-fg2)">{{ company.sector }}</p>
            </div>
            <div class="text-right flex-shrink-0">
              <p class="text-sm font-bold" style="color:var(--c-fg)">₩{{ company.price.toLocaleString() }}</p>
              <p class="text-[12px] font-semibold"
                 :class="company.change >= 0 ? 'text-green-600' : 'text-red-500'">
                {{ company.change >= 0 ? '+' : '' }}{{ company.change }}%
              </p>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <LucideChevronRight class="w-4 h-4 ml-0.5" style="color:var(--c-fg3)" />
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
            <span class="text-[11px] text-white/30">커뮤니티 데이터 로딩 중...</span>
          </div>
          <div v-else-if="communityError" class="flex flex-col items-center justify-center h-20 gap-1.5">
            <span class="text-[12px] text-white/35">커뮤니티 데이터를 불러올 수 없습니다</span>
            <span class="text-[10px] text-white/20">게시판 DB 연결을 확인해주세요</span>
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
                <span class="text-[11px] font-black">{{ idx + 1 }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5 mb-0.5">
                  <span v-if="post.ticker"
                        class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold"
                        style="background:rgba(96,165,250,0.15);color:#93c5fd;border:1px solid rgba(96,165,250,0.25)">
                    {{ post.ticker }}
                  </span>
                </div>
                <p class="text-[13px] font-semibold leading-snug text-white/88">{{ post.title }}</p>
                <div class="flex items-center gap-3 mt-1">
                  <span class="text-[10px] text-white/25 font-mono">{{ post.views }} views</span>
                  <span class="text-[10px] text-white/25 font-mono">{{ post.likes }} likes</span>
                  <span class="text-[10px] text-white/25 font-mono">{{ post.comment_count }} comments</span>
                  <span class="text-[10px] font-bold ml-auto"
                        style="color:rgba(251,191,36,0.7)">
                    {{ post.popularity }}
                  </span>
                </div>
              </div>
            </div>
          </div>
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
            <span class="text-[11px] text-white/30">급상승 종목 탐색 중...</span>
          </div>
          <div v-else-if="risingError" class="flex flex-col items-center justify-center h-20 gap-1.5">
            <span class="text-[14px] font-bold" style="color:var(--c-fg2)">+</span>
            <span class="text-[12px] text-white/35">급상승 데이터를 불러올 수 없습니다</span>
          </div>
          <div v-else
            v-for="(s, idx) in risingList" :key="s.ticker"
            class="flex items-center gap-3 p-3 rounded-xl border border-white/5 bg-white/5 hover:bg-white/8 hover:border-white/12 transition-all cursor-pointer"
            @click="openDetailByTicker(s.ticker)"
          >
            <div class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-black"
                 style="background:rgba(52,211,153,0.15);color:#34d399;border:1px solid rgba(52,211,153,0.3)">
              {{ idx + 1 }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5">
                <p class="font-bold text-sm truncate">{{ s.name ?? s.ticker }}</p>
                <span class="text-[11px] text-white/35 font-mono flex-shrink-0">{{ s.ticker }}</span>
              </div>
              <p class="text-[11px] text-white/38">{{ s.sector }}</p>
            </div>
            <!-- 점수 변화 -->
            <div class="text-right flex-shrink-0">
              <p class="text-[13px] font-black text-green-300">
                △ {{ s.score_change >= 0 ? '+' : '' }}{{ s.score_change?.toFixed(1) }}
              </p>
              <p class="text-[10px] font-mono text-white/38">점수 {{ s.score?.toFixed(0) }}</p>
            </div>
            <!-- Tier 뱃지 -->
            <span class="text-[11px] font-black px-1.5 py-0.5 rounded flex-shrink-0"
                  :style="tierBadgeStyle(s.tier)">{{ s.tier }}</span>
          </div>
        </div>
      </template>

    </div><!-- /기업 리스트 뷰 -->

    <!-- ══════════════════════════════
         검색 오버레이
    ══════════════════════════════ -->
    <transition name="panel-slide">
      <div v-if="showSearch"
           class="absolute inset-0 z-50 flex overflow-hidden">
        <!-- 왼쪽 배경 (클릭시 닫기) -->
        <div class="flex-[1] cursor-pointer"
             style="background:rgba(244,242,236,0.4);backdrop-filter:blur(2px)"
             @click="closeSearch"></div>
        <!-- 오른쪽 패널 -->
        <div class="flex-[3] flex flex-col overflow-hidden"
             style="background:#244d8c;box-shadow:-12px 0 40px rgba(0,0,0,0.4)">

        <!-- 교체 선택 중 배너 (검색창) -->
        <div v-if="replaceMode" class="px-3 pt-2 pb-1 flex items-center justify-between flex-shrink-0"
             style="background:rgba(52,211,153,0.1);border-bottom:1px solid rgba(52,211,153,0.2)">
          <span class="text-[11px] font-bold" style="color:#34d399">교체 선택 중 — 교체할 종목을 검색하세요</span>
          <button @click="emit('cancel-replace'); closeSearch()"
                  class="text-[11px] font-bold px-2 py-0.5 rounded"
                  style="background:rgba(248,113,113,0.15);color:#f87171;border:1px solid rgba(248,113,113,0.3)">
            취소
          </button>
        </div>

        <!-- 검색 바 -->
        <div class="px-3 pt-4 pb-2.5 flex items-center gap-2 flex-shrink-0 border-b border-black/10">
          <div class="flex-1 flex items-center gap-2 px-2.5 py-1.5 rounded-xl"
               style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border)">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="rgba(232,228,220,0.4)" stroke-width="2.5">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <input ref="searchInputRef"
                   v-model="searchQuery"
                   type="text"
                   placeholder="종목명 · 티커 검색"
                   class="flex-1 bg-transparent outline-none text-[13px] min-w-0"
                   style="color:var(--c-fg)" />
            <button v-if="searchQuery" @click="searchQuery = ''"
                    class="text-[12px] flex-shrink-0 transition-colors"
                    style="color:var(--c-fg3)">✕</button>
          </div>
          <button @click="closeSearch"
                  class="text-[12px] font-bold flex-shrink-0 px-1 transition-colors"
                  style="color:var(--c-fg2)">
            닫기
          </button>
        </div>

        <!-- 본문: 좌(설정) + 가운데(리스트) + 우(결과 요약) -->
        <div class="flex-1 flex overflow-hidden">

          <!-- ── 좌: 상세 설정 ── -->
          <div class="w-[150px] flex-shrink-0 flex flex-col overflow-y-auto border-r border-black/10"
               style="background:rgba(255,255,255,0.04)"

            <!-- 모델 버전 -->
            <div class="px-3 pt-3 pb-2 border-b border-black/10">
              <p class="text-[11px] uppercase tracking-widest mb-1.5" style="color:var(--c-fg2)">버전</p>
              <select :value="searchFilters.model_version"
                      @change="searchFilters.model_version = $event.target.value"
                      class="w-full text-[11px] rounded-md px-2 py-1 outline-none"
                      style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border);color:var(--c-fg)">
                <option value="latest">최신</option>
                <option v-for="v in searchVersions" :key="v" :value="v">{{ v }}</option>
              </select>
            </div>

            <!-- 기준일 -->
            <div class="px-3 py-2 border-b border-black/10">
              <p class="text-[11px] uppercase tracking-widest mb-1.5" style="color:var(--c-fg2)">기준일</p>
              <select :value="searchFilters.date"
                      @change="searchFilters.date = $event.target.value"
                      class="w-full text-[11px] rounded-md px-2 py-1 outline-none"
                      style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border);color:var(--c-fg)">
                <option v-for="d in searchDates" :key="d" :value="d">{{ d }}</option>
              </select>
            </div>

            <!-- 섹터 -->
            <div class="px-3 py-2 border-b border-black/10">
              <p class="text-[11px] uppercase tracking-widest mb-1.5" style="color:var(--c-fg2)">섹터</p>
              <select :value="searchFilters.sector ?? ''"
                      @change="searchFilters.sector = $event.target.value || null"
                      class="w-full text-[11px] rounded-md px-2 py-1 outline-none"
                      style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border);color:var(--c-fg)">
                <option value="">전체</option>
                <option v-for="s in SECTOR_LIST" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>

            <!-- 최소 점수 슬라이더 -->
            <div class="px-3 py-2 border-b border-black/10">
              <div class="flex justify-between mb-1.5">
                <p class="text-[11px] uppercase tracking-widest" style="color:var(--c-fg2)">최소 점수</p>
                <span class="text-[12px] font-bold" style="color:var(--c-fg)">{{ searchFilters.min_score }}</span>
              </div>
              <input type="range" min="0" max="100" step="1"
                     v-model.number="searchFilters.min_score"
                     class="w-full h-1 rounded-full appearance-none cursor-pointer"
                     style="accent-color:var(--c-fg)" />
              <div class="flex justify-between mt-1">
                <span class="text-[10px]" style="color:var(--c-fg3)">0</span>
                <span class="text-[10px]" style="color:var(--c-fg3)">100</span>
              </div>
            </div>

            <!-- Tier 빠른 선택 -->
            <div class="px-3 py-2 border-b border-black/10">
              <p class="text-[11px] uppercase tracking-widest mb-1.5" style="color:var(--c-fg2)">Tier</p>
              <div class="grid grid-cols-2 gap-1">
                <button v-for="t in TIER_PRESETS.filter(p => p.tier !== null)" :key="t.label"
                        @click="searchFilters.min_score = t.min; searchFilters.tier = t.tier"
                        class="py-1 rounded-md text-[11px] font-bold text-center transition-all"
                        :style="searchFilters.tier === t.tier && searchFilters.min_score === t.min
                          ? tierActiveStyle(t.tier)
                          : 'background:rgba(255,255,255,0.06);color:var(--c-fg2);border:1px solid var(--c-border)'">
                  {{ t.label.split(' ')[0] }}
                </button>
                <button class="col-span-2 mt-0.5 py-1 rounded-md text-[11px] font-bold text-center transition-all"
                        @click="searchFilters.min_score = 0; searchFilters.tier = null"
                        :style="searchFilters.tier === null && searchFilters.min_score === 0
                          ? tierActiveStyle('all')
                          : 'background:rgba(255,255,255,0.06);color:var(--c-fg2);border:1px solid var(--c-border)'">
                  전체 ({{ searchAllItems.length }})
                </button>
              </div>
            </div>

            <!-- ══ 부가설정 (접기/펼치기) ══ -->
            <div class="px-3 pt-2">
              <button @click="financialOpen = !financialOpen"
                      class="w-full flex items-center justify-between text-[11px] font-bold uppercase tracking-widest mb-1.5 transition-colors"
                      :style="financialOpen ? 'color:var(--c-fg2)' : 'color:var(--c-fg3)'">
                <span>부가설정</span>
                <span>{{ financialOpen ? '▲' : '▼' }}</span>
              </button>

              <template v-if="financialOpen">
                <div v-for="f in ALL_FINANCE_FILTERS" :key="f.key" class="mb-2">
                  <p class="text-[10px] mb-0.5" style="color:var(--c-fg2)">{{ f.shortLabel }}</p>
                  <input type="number" :placeholder="f.placeholder"
                         :value="searchFilters[f.key]"
                         @change="searchFilters[f.key] = $event.target.value === '' ? null : +$event.target.value"
                         class="w-full px-2 py-1 rounded-md text-[11px] font-mono outline-none"
                         style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border);color:var(--c-fg)" />
                </div>

                <div class="my-2" style="border-top:1px solid var(--c-border)"></div>

                <div class="mb-2">
                  <p class="text-[10px] mb-0.5" style="color:var(--c-fg2)">정렬</p>
                  <select :value="searchFilters.sort_by"
                          @change="searchFilters.sort_by = $event.target.value"
                          class="w-full text-[11px] rounded-md px-2 py-1 outline-none"
                          style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border);color:var(--c-fg)">
                    <option value="composite_score">복합점수</option>
                    <option value="score">ML점수</option>
                    <option value="roe">ROE</option>
                    <option value="per">PER</option>
                    <option value="pbr">PBR</option>
                  </select>
                </div>

                <div class="mb-2">
                  <p class="text-[10px] mb-0.5" style="color:var(--c-fg2)">결과 수</p>
                  <select :value="searchFilters.limit"
                          @change="searchFilters.limit = +$event.target.value"
                          class="w-full text-[11px] rounded-md px-2 py-1 outline-none"
                          style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border);color:var(--c-fg)">
                    <option :value="50">50개</option>
                    <option :value="100">100개</option>
                    <option :value="200">200개</option>
                    <option :value="300">300개</option>
                  </select>
                </div>

                <div class="my-2" style="border-top:1px solid var(--c-border)"></div>

                <div class="mb-2">
                  <p class="text-[10px] mb-1" style="color:var(--c-fg2)">프리셋</p>
                  <div class="flex gap-1 mb-1">
                    <input v-model="presetName" type="text" placeholder="이름"
                           class="flex-1 px-1.5 py-1 rounded-md text-[11px] outline-none min-w-0"
                           style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border);color:var(--c-fg)"
                           @keydown.enter="savePreset" />
                    <button @click="savePreset"
                            class="px-2 py-1 rounded-md text-[11px] font-bold flex-shrink-0 transition-colors"
                            style="background:rgba(255,255,255,0.1);color:var(--c-fg);border:1px solid rgba(255,255,255,0.2)">
                      저장
                    </button>
                  </div>
                  <div v-for="name in savedPresets" :key="name"
                       class="flex items-center justify-between mb-1">
                    <button @click="loadPreset(name)"
                            class="text-[10px] truncate flex-1 text-left transition-colors"
                            style="color:var(--c-fg2)">
                      {{ name }}
                    </button>
                    <button @click="deletePreset(name)"
                            class="text-[11px] ml-1 flex-shrink-0 transition-colors"
                            style="color:var(--c-fg3)">✕</button>
                  </div>
                  <p v-if="!savedPresets.length" class="text-[10px]" style="color:var(--c-fg3)">저장된 프리셋 없음</p>
                </div>

                <div class="flex flex-col gap-1 pb-3">
                  <button @click="resetFinancialFilters"
                          class="text-[10px] text-red-500/60 hover:text-red-500 text-left transition-colors">
                    재무 조건 초기화
                  </button>
                  <button @click="resetSearchFilters"
                          class="text-[10px] text-red-500/60 hover:text-red-500 text-left transition-colors">
                    전체 초기화
                  </button>
                </div>
              </template>
            </div>
          </div>

          <!-- ── 가운데: 종목 리스트 ── -->
          <div class="flex-1 overflow-y-auto">

            <!-- 로딩 -->
            <div v-if="searchLoading" class="flex items-center justify-center h-32 gap-2">
              <div class="w-4 h-4 rounded-full border-2 animate-spin"
                   style="border-color:var(--c-fg3);border-top-color:transparent"></div>
              <span class="text-[12px]" style="color:var(--c-fg2)">로딩 중...</span>
            </div>

            <!-- 결과 없음 -->
            <div v-else-if="searchDisplayList.length === 0"
                 class="flex flex-col items-center justify-center h-32 gap-2">
              <span class="text-[12px]" style="color:var(--c-fg2)">결과 없음</span>
            </div>

            <!-- 리스트 -->
            <div v-else>
              <!-- 건수 + CSV -->
              <div class="px-3 py-2 flex items-center justify-between" style="border-bottom:1px solid var(--c-border)">
                <span class="text-[11px] font-medium" style="color:var(--c-fg2)">{{ searchDisplayList.length }}개 종목 · 가나다순</span>
                <button @click="exportCsv"
                        class="text-[10px] px-2 py-0.5 rounded-md font-bold flex-shrink-0 transition-all"
                        style="background:rgba(52,211,153,0.12);color:rgba(52,211,153,0.75);border:1px solid rgba(52,211,153,0.22)">
                  CSV ↓
                </button>
              </div>
              <div v-for="s in searchDisplayList" :key="s.ticker"
                   class="flex items-center gap-2 px-3 py-2.5 transition-colors cursor-pointer"
                   style="border-bottom:1px solid var(--c-border)"
                   @mouseover="$event.currentTarget.style.background='rgba(0,0,0,0.04)'"
                   @mouseleave="$event.currentTarget.style.background=''"
                   @click="selectSearchResult(s)">
                <!-- Tier 색 바 -->
                <div class="w-0.5 h-8 rounded-full flex-shrink-0" :style="{ background: s.color }"></div>
                <!-- 이름 + 티커 + 점수 바 -->
                <div class="flex-1 min-w-0">
                  <p class="text-[13px] font-bold truncate" style="color:var(--c-fg)">{{ s.name }}</p>
                  <div class="flex items-center gap-1.5 mt-0.5">
                    <p class="text-[10px] font-mono" style="color:var(--c-fg2)">{{ s.ticker }}</p>
                    <span class="text-[10px]" style="color:var(--c-fg3)">·</span>
                    <p class="text-[10px] truncate" style="color:var(--c-fg2)">{{ s.sector }}</p>
                  </div>
                  <div class="w-full h-1 rounded-full mt-1" style="background:rgba(0,0,0,0.08)">
                    <div class="h-full rounded-full transition-all"
                         :style="{ width: s.quantScore + '%', background: s.color }"></div>
                  </div>
                </div>
                <!-- ML 점수 -->
                <div class="text-right flex-shrink-0">
                  <p class="text-[10px]" style="color:var(--c-fg3)">ML</p>
                  <p class="text-[12px] font-mono font-bold" style="color:var(--c-fg2)">{{ s.mlScore }}</p>
                </div>
                <!-- Tier 뱃지 -->
                <span class="text-[12px] font-black px-1.5 py-0.5 rounded-md flex-shrink-0"
                      :style="tierBadgeStyle(s.tier)">{{ s.tier }}</span>
                <!-- 복합점수 -->
                <span class="text-[13px] font-black flex-shrink-0 w-8 text-right"
                      :class="s.quantScore >= 70 ? 'text-green-600' : s.quantScore >= 45 ? 'text-yellow-600' : 'text-red-500'">
                  {{ s.quantScore }}
                </span>
                <LucideChevronRight class="w-3.5 h-3.5 flex-shrink-0" style="color:var(--c-fg3)" />
              </div>
            </div>
          </div>

          <!-- ── 우: 결과 요약 패널 ── -->
          <div class="w-[160px] flex-shrink-0 flex flex-col overflow-y-auto"
               style="border-left:1px solid var(--c-border);background:rgba(255,255,255,0.04)">

            <!-- 결과 요약 -->
            <div class="px-3 pt-3 pb-2.5" style="border-bottom:1px solid var(--c-border)">
              <p class="text-[11px] uppercase tracking-widest mb-2.5" style="color:var(--c-fg2)">결과 요약</p>
              <div class="space-y-2">
                <div class="rounded-lg p-2" style="background:rgba(255,255,255,0.06);border:1px solid var(--c-border)">
                  <p class="text-[10px] mb-0.5" style="color:var(--c-fg2)">검색 결과</p>
                  <p class="text-[16px] font-black leading-none" style="color:var(--c-fg)">{{ searchAllItems.length }}</p>
                  <p class="text-[10px] mt-0.5" style="color:var(--c-fg2)">종목</p>
                </div>
                <div class="rounded-lg p-2"
                     :style="avgScore >= 70
                       ? 'background:rgba(5,95,70,0.06);border:1px solid rgba(5,95,70,0.15)'
                       : avgScore >= 45
                         ? 'background:rgba(180,130,0,0.06);border:1px solid rgba(180,130,0,0.15)'
                         : 'background:rgba(180,30,30,0.06);border:1px solid rgba(180,30,30,0.15)'">
                  <p class="text-[10px] mb-0.5"
                     :style="avgScore >= 70 ? 'color:rgba(5,95,70,0.7)' : avgScore >= 45 ? 'color:rgba(140,100,0,0.7)' : 'color:rgba(160,30,30,0.7)'">
                    평균 점수
                  </p>
                  <p class="text-[16px] font-black leading-none"
                     :style="avgScore >= 70 ? 'color:#065f46' : avgScore >= 45 ? 'color:#92400e' : 'color:#991b1b'">
                    {{ avgScore }}
                  </p>
                  <p class="text-[10px] mt-0.5"
                     :style="avgScore >= 70 ? 'color:rgba(5,95,70,0.5)' : avgScore >= 45 ? 'color:rgba(140,100,0,0.5)' : 'color:rgba(160,30,30,0.5)'">
                    점 (0-100)
                  </p>
                </div>
              </div>
            </div>

            <!-- Tier 분포 -->
            <div class="px-3 py-2.5" style="border-bottom:1px solid var(--c-border)">
              <p class="text-[11px] uppercase tracking-widest mb-2.5" style="color:var(--c-fg2)">Tier 분포</p>

              <!-- SVG 도넛 차트 -->
              <div class="flex justify-center mb-3">
                <svg viewBox="0 0 80 80" class="w-20 h-20">
                  <circle cx="40" cy="40" r="28" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="12" />
                  <template v-for="(seg, i) in tierDonutSegments" :key="i">
                    <circle cx="40" cy="40" r="28"
                            fill="none"
                            :stroke="seg.color"
                            stroke-width="12"
                            stroke-linecap="butt"
                            :stroke-dasharray="`${seg.dash} 175.9`"
                            :stroke-dashoffset="-seg.offset"
                            transform="rotate(-90 40 40)"
                            opacity="0.88" />
                  </template>
                  <text x="40" y="37" text-anchor="middle" fill="rgba(232,228,220,0.9)"
                        font-size="13" font-weight="bold" font-family="sans-serif">
                    {{ searchAllItems.length }}
                  </text>
                  <text x="40" y="49" text-anchor="middle" fill="rgba(232,228,220,0.45)"
                        font-size="7" font-family="sans-serif">종목</text>
                </svg>
              </div>

              <!-- Tier 바 -->
              <div class="space-y-1.5">
                <div v-for="tk in ['A','B','C','D']" :key="tk" class="flex items-center gap-1.5">
                  <span class="text-[11px] font-black w-3.5 flex-shrink-0"
                        :style="{ color: {A:'#34d399',B:'#93c5fd',C:'#fbbf24',D:'#f87171'}[tk] }">{{ tk }}</span>
                  <div class="flex-1 h-1.5 rounded-full" style="background:rgba(255,255,255,0.08)">
                    <div class="h-full rounded-full transition-all duration-500"
                         :style="{
                           width: searchAllItems.length
                             ? ((tierCounts[tk] ?? 0) / searchAllItems.length * 100).toFixed(1) + '%'
                             : '0%',
                           background: {A:'#34d399',B:'#93c5fd',C:'#fbbf24',D:'#f87171'}[tk]
                         }"></div>
                  </div>
                  <span class="text-[10px] w-5 text-right flex-shrink-0 font-mono font-bold"
                        style="color:var(--c-fg2)">
                    {{ tierCounts[tk] ?? 0 }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 점수 분포 히스토그램 -->
            <div class="px-3 py-2.5">
              <p class="text-[11px] uppercase tracking-widest mb-2.5" style="color:var(--c-fg2)">점수 분포</p>
              <div class="flex items-end gap-0.5 h-20">
                <div v-for="(count, i) in scoreBuckets" :key="i"
                     class="flex-1 rounded-t-sm transition-all duration-500 cursor-default"
                     :style="{
                       height: maxBucket > 0 ? Math.max(count / maxBucket * 100, count > 0 ? 4 : 0) + '%' : '0%',
                       background: scoreBucketColors[i],
                       opacity: 0.82,
                     }"
                     :title="`${i*10}~${i*10+10}: ${count}종목`">
                </div>
              </div>
              <div class="flex justify-between mt-1">
                <span class="text-[7px] font-mono" style="color:var(--c-fg3)">0</span>
                <span class="text-[7px] font-mono" style="color:var(--c-fg3)">50</span>
                <span class="text-[7px] font-mono" style="color:var(--c-fg3)">100</span>
              </div>
              <!-- 버킷 레이블 -->
              <div class="mt-1.5 space-y-0.5">
                <div v-for="(count, i) in scoreBuckets" :key="i"
                     v-show="count > 0"
                     class="flex items-center gap-1">
                  <div class="w-1.5 h-1.5 rounded-sm flex-shrink-0"
                       :style="{ background: scoreBucketColors[i] }"></div>
                  <span class="text-[7px] font-mono" style="color:var(--c-fg3)">{{ i*10 }}-{{ i*10+10 }}</span>
                  <span class="text-[7px] font-bold ml-auto" style="color:var(--c-fg2)">{{ count }}</span>
                </div>
              </div>
            </div>

          </div>
        </div>
        </div><!-- /오른쪽 패널 -->
      </div><!-- /백드롭 wrapper -->
    </transition>

    <!-- ══════════════════════════════
         종목 비교 오버레이
    ══════════════════════════════ -->
    <transition name="panel-slide">
      <div v-if="showCompare"
           class="absolute inset-0 z-50 flex overflow-hidden">
        <!-- 왼쪽 배경 -->
        <div class="flex-[1] cursor-pointer"
             style="background:rgba(244,242,236,0.4);backdrop-filter:blur(2px)"
             @click="closeCompareOverlay"></div>
        <!-- 오른쪽 패널 -->
        <div class="flex-[3] flex flex-col overflow-hidden"
             style="background:#244d8c;box-shadow:-12px 0 40px rgba(0,0,0,0.4)">

        <!-- 헤더 -->
        <div class="px-4 pt-4 pb-3 flex items-center gap-2 flex-shrink-0 border-b border-black/10">
          <LucideArrowLeftRight class="w-4 h-4 flex-shrink-0" style="color:var(--c-fg2)" />
          <p class="text-[13px] font-black tracking-tight flex-1" style="color:var(--c-fg)">종목 비교</p>
          <button @click="closeCompareOverlay"
                  class="text-[12px] font-bold transition-colors px-1"
                  style="color:var(--c-fg2)">
            닫기
          </button>
        </div>

        <!-- A / B 슬롯 -->
        <div class="flex gap-2 px-3 pt-3 pb-2 flex-shrink-0">

          <!-- 슬롯 A -->
          <div class="flex-1 rounded-xl p-3 cursor-pointer border transition-all duration-200"
               :style="compareSelectingSlot === 'A'
                 ? 'border:2px solid var(--c-fg);background:rgba(255,255,255,0.08)'
                 : compareStockA
                   ? 'border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.04)'
                   : 'border:1px solid var(--c-border);background:rgba(255,255,255,0.02)'"
               @click="startSelectSlot('A')">
            <p class="text-[10px] font-bold uppercase tracking-widest mb-1"
               :style="compareSelectingSlot === 'A' ? 'color:var(--c-fg)' : 'color:var(--c-fg2)'">
              {{ compareSelectingSlot === 'A' ? '▶ 비교 A 선택 중' : '종목 비교 A' }}
            </p>
            <template v-if="compareStockA">
              <div class="h-0.5 rounded-full mb-1.5" :style="{ background: compareStockA.color }"></div>
              <p class="text-[14px] font-black truncate" style="color:var(--c-fg)">{{ compareStockA.name }}</p>
              <p class="text-[11px] font-mono" style="color:var(--c-fg2)">{{ compareStockA.ticker }}</p>
              <div class="flex items-center gap-1.5 mt-1.5">
                <span class="text-[11px] font-black px-1.5 py-0.5 rounded" :style="tierBadgeStyle(compareStockA.tier)">{{ compareStockA.tier }}</span>
                <span class="text-[14px] font-black ml-auto" :class="quantTextColor(compareStockA.quantScore)">{{ compareStockA.quantScore }}</span>
              </div>
            </template>
            <template v-else>
              <p class="text-[12px] mt-1" style="color:var(--c-fg3)">클릭하여 종목 선택</p>
            </template>
          </div>

          <!-- VS -->
          <div class="flex items-center justify-center px-1 flex-shrink-0">
            <span class="text-[12px] font-black" style="color:var(--c-fg3)">VS</span>
          </div>

          <!-- 슬롯 B -->
          <div class="flex-1 rounded-xl p-3 cursor-pointer border transition-all duration-200"
               :style="compareSelectingSlot === 'B'
                 ? 'border:2px solid #065f46;background:rgba(5,95,70,0.06)'
                 : compareStockB
                   ? 'border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.04)'
                   : 'border:1px solid var(--c-border);background:rgba(255,255,255,0.02)'"
               @click="startSelectSlot('B')">
            <p class="text-[10px] font-bold uppercase tracking-widest mb-1"
               :style="compareSelectingSlot === 'B' ? 'color:#065f46' : 'color:var(--c-fg2)'">
              {{ compareSelectingSlot === 'B' ? '▶ 비교 B 선택 중' : '종목 비교 B' }}
            </p>
            <template v-if="compareStockB">
              <div class="h-0.5 rounded-full mb-1.5" :style="{ background: compareStockB.color }"></div>
              <p class="text-[14px] font-black truncate" style="color:var(--c-fg)">{{ compareStockB.name }}</p>
              <p class="text-[11px] font-mono" style="color:var(--c-fg2)">{{ compareStockB.ticker }}</p>
              <div class="flex items-center gap-1.5 mt-1.5">
                <span class="text-[11px] font-black px-1.5 py-0.5 rounded" :style="tierBadgeStyle(compareStockB.tier)">{{ compareStockB.tier }}</span>
                <span class="text-[14px] font-black ml-auto" :class="quantTextColor(compareStockB.quantScore)">{{ compareStockB.quantScore }}</span>
              </div>
            </template>
            <template v-else>
              <p class="text-[12px] mt-1" style="color:var(--c-fg3)">클릭하여 종목 선택</p>
            </template>
          </div>
        </div>

        <!-- ① 슬롯 선택 중: 종목 리스트 -->
        <template v-if="compareSelectingSlot">
          <!-- 안내 배너 -->
          <div class="px-3 py-2 flex items-center gap-2 flex-shrink-0"
               :style="compareSelectingSlot === 'A'
                 ? 'border-bottom:1px solid var(--c-border);background:rgba(255,255,255,0.05)'
                 : 'border-bottom:1px solid rgba(5,95,70,0.15);background:rgba(5,95,70,0.04)'">
            <div class="w-1.5 h-1.5 rounded-full animate-pulse flex-shrink-0"
                 :style="compareSelectingSlot === 'A' ? 'background:var(--c-fg)' : 'background:#065f46'"></div>
            <span class="text-[12px] font-bold"
                  :style="compareSelectingSlot === 'A' ? 'color:var(--c-fg)' : 'color:#065f46'">
              종목 비교 {{ compareSelectingSlot }} 선택 중 — 아래에서 종목을 클릭하세요
            </span>
          </div>
          <!-- 종목 리스트 -->
          <div class="flex-1 overflow-y-auto">
            <div v-for="s in comparePickList" :key="s.ticker"
                 class="flex items-center gap-2 px-3 py-2.5 transition-colors cursor-pointer"
                 style="border-bottom:1px solid var(--c-border)"
                 @mouseover="$event.currentTarget.style.background='rgba(0,0,0,0.04)'"
                 @mouseleave="$event.currentTarget.style.background=''"
                 @click="assignCompareSlot(s)">
              <div class="w-0.5 h-8 rounded-full flex-shrink-0" :style="{ background: s.color }"></div>
              <div class="flex-1 min-w-0">
                <p class="text-[13px] font-bold truncate" style="color:var(--c-fg)">{{ s.name }}</p>
                <div class="flex items-center gap-1.5 mt-0.5">
                  <p class="text-[10px] font-mono" style="color:var(--c-fg2)">{{ s.ticker }}</p>
                  <span class="text-[10px]" style="color:var(--c-fg3)">·</span>
                  <p class="text-[10px] truncate" style="color:var(--c-fg2)">{{ s.sector }}</p>
                </div>
              </div>
              <span class="text-[11px] font-black px-1.5 py-0.5 rounded flex-shrink-0"
                    :style="tierBadgeStyle(s.tier)">{{ s.tier }}</span>
              <span class="text-[13px] font-black flex-shrink-0 w-8 text-right"
                    :class="s.quantScore >= 70 ? 'text-green-600' : s.quantScore >= 45 ? 'text-yellow-600' : 'text-red-500'">
                {{ s.quantScore }}
              </span>
            </div>
          </div>
        </template>

        <!-- ② 둘 다 선택 완료: 비교 결과 -->
        <template v-else-if="compareStockA && compareStockB">
          <div class="flex-1 overflow-y-auto px-3 py-3 space-y-3">

            <!-- AI 점수 바 비교 -->
            <div class="rounded-xl p-3 space-y-3"
                 style="border:1px solid var(--c-border);background:rgba(255,255,255,0.04)">
              <p class="text-[11px] uppercase tracking-widest" style="color:var(--c-fg2)">AI 점수 비교</p>
              <div class="space-y-2.5">
                <div v-for="(stk, key) in { A: compareStockA, B: compareStockB }" :key="key">
                  <div class="flex justify-between mb-1">
                    <span class="text-[12px] font-bold" :style="{ color: stk.color }">
                      {{ key }} · {{ stk.name }}
                    </span>
                    <span class="text-[13px] font-black" :class="quantTextColor(stk.quantScore)">
                      {{ stk.quantScore }}점
                    </span>
                  </div>
                  <div class="w-full h-2 rounded-full overflow-hidden" style="background:rgba(255,255,255,0.1)">
                    <div class="h-full rounded-full transition-all duration-700"
                         :style="{ width: stk.quantScore + '%', background: stk.color }"></div>
                  </div>
                </div>
              </div>
              <!-- 우위 표시 -->
              <div class="pt-1 flex items-center gap-1.5" style="border-top:1px solid var(--c-border)">
                <span class="text-[11px]" style="color:var(--c-fg2)">AI 점수 우위</span>
                <span class="text-[12px] font-black"
                      :style="{ color: compareStockA.quantScore >= compareStockB.quantScore ? compareStockA.color : compareStockB.color }">
                  {{ compareStockA.quantScore >= compareStockB.quantScore ? compareStockA.name : compareStockB.name }}
                </span>
                <span class="text-[11px] font-bold ml-auto"
                      :class="Math.abs(compareStockA.quantScore - compareStockB.quantScore) >= 15 ? 'text-green-600' : 'text-yellow-600'">
                  +{{ Math.abs(compareStockA.quantScore - compareStockB.quantScore) }}점 차
                </span>
              </div>
            </div>

            <!-- 지표 비교 테이블 -->
            <div class="rounded-xl overflow-hidden" style="border:1px solid var(--c-border)">
              <div class="grid grid-cols-3" style="border-bottom:1px solid var(--c-border);background:rgba(255,255,255,0.06)">
                <div class="px-3 py-2 text-[11px] font-bold uppercase tracking-widest" style="color:var(--c-fg2)">지표</div>
                <div class="px-3 py-2 text-[12px] font-black text-center" :style="{ color: compareStockA.color }">
                  A · {{ compareStockA.ticker }}
                </div>
                <div class="px-3 py-2 text-[12px] font-black text-center" :style="{ color: compareStockB.color }">
                  B · {{ compareStockB.ticker }}
                </div>
              </div>
              <div v-for="row in compareMetricRows" :key="row.label"
                   class="grid grid-cols-3"
                   style="border-bottom:1px solid rgba(255,255,255,0.06);background:rgba(255,255,255,0.02)">
                <div class="px-3 py-2.5 text-[11px]" style="color:var(--c-fg2)">{{ row.label }}</div>
                <div class="px-3 py-2.5 text-center text-[13px] font-black"
                     :style="row.betterA ? 'color:#065f46' : (row.valA === '—' ? 'color:var(--c-fg3)' : 'color:var(--c-fg2)')">
                  {{ row.valA }}
                </div>
                <div class="px-3 py-2.5 text-center text-[13px] font-black"
                     :style="row.betterB ? 'color:#065f46' : (row.valB === '—' ? 'color:var(--c-fg3)' : 'color:var(--c-fg2)')">
                  {{ row.valB }}
                </div>
              </div>
            </div>

            <!-- 점수 이력 스파크라인 -->
            <div class="rounded-xl p-3" style="border:1px solid var(--c-border);background:rgba(255,255,255,0.04)">
              <p class="text-[11px] uppercase tracking-widest mb-2" style="color:var(--c-fg2)">AI 점수 이력</p>
              <div v-if="compareHistoryLoading" class="flex items-center justify-center py-4 gap-2">
                <div class="w-3.5 h-3.5 rounded-full border-2 animate-spin"
                     style="border-color:var(--c-fg3);border-top-color:transparent"></div>
                <span class="text-[11px]" style="color:var(--c-fg2)">로딩 중...</span>
              </div>
              <template v-else>
                <div class="flex items-center gap-4 mb-2">
                  <div class="flex items-center gap-1.5">
                    <div class="w-4 h-0.5 rounded-full" :style="{ background: compareStockA.color }"></div>
                    <span class="text-[10px]" style="color:var(--c-fg2)">A · {{ compareStockA.ticker }}</span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <div class="w-4 h-0.5 rounded-full opacity-60" style="border-top:2px dashed"
                         :style="{ borderColor: compareStockB.color }"></div>
                    <span class="text-[10px]" style="color:var(--c-fg2)">B · {{ compareStockB.ticker }}</span>
                  </div>
                </div>
                <svg viewBox="0 0 300 70" class="w-full" style="height:70px">
                  <path v-if="compareChartPaths.pathA"
                        :d="compareChartPaths.pathA" fill="none"
                        :stroke="compareStockA.color" stroke-width="1.8" stroke-linejoin="round" opacity="0.9"/>
                  <path v-if="compareChartPaths.pathB"
                        :d="compareChartPaths.pathB" fill="none"
                        :stroke="compareStockB.color" stroke-width="1.8" stroke-linejoin="round"
                        stroke-dasharray="5,3" opacity="0.9"/>
                  <text v-if="!compareChartPaths.pathA && !compareChartPaths.pathB"
                        x="150" y="38" text-anchor="middle" fill="rgba(232,228,220,0.3)"
                        font-size="8" font-family="sans-serif">이력 데이터 없음</text>
                </svg>
              </template>
            </div>

            <!-- 다시 선택 버튼 -->
            <div class="flex gap-2 pb-2">
              <button @click="compareStockA = null; compareSelectingSlot = 'A'"
                      class="flex-1 py-2 rounded-xl border text-[12px] font-bold transition-colors"
                      :style="{ borderColor: compareStockA ? compareStockA.color + '50' : 'var(--c-border)', color: 'var(--c-fg2)' }">
                A 다시 선택
              </button>
              <button @click="compareStockB = null; compareSelectingSlot = 'B'"
                      class="flex-1 py-2 rounded-xl border text-[12px] font-bold transition-colors"
                      :style="{ borderColor: compareStockB ? compareStockB.color + '50' : 'var(--c-border)', color: 'var(--c-fg2)' }">
                B 다시 선택
              </button>
            </div>

          </div>
        </template>

        <!-- ③ 초기 안내 -->
        <div v-else class="flex-1 flex flex-col items-center justify-center gap-2">
          <span class="text-[32px]">⚖️</span>
          <p class="text-[13px] text-center px-6" style="color:var(--c-fg2)">
            위 A, B 슬롯을 클릭해서<br>비교할 종목을 선택하세요
          </p>
        </div>

        </div><!-- /오른쪽 패널 -->
      </div><!-- /백드롭 wrapper -->
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
            <p class="text-[12px] text-white/40 uppercase tracking-widest text-center mb-3">종목 교체 비교</p>

            <div class="grid grid-cols-2 gap-2 mb-4">
              <!-- 현재 보유 -->
              <div class="rounded-xl p-3 border border-red-500/25 bg-red-500/8 space-y-2.5">
                <div>
                  <p class="text-[10px] text-red-300/60 uppercase tracking-wide mb-1">현재 보유</p>
                  <div class="h-0.5 rounded-full mb-2" :style="{ background: replaceStock?.color ?? '#888' }"></div>
                  <p class="text-sm font-black truncate">{{ replaceStock?.company }}</p>
                  <p class="text-[10px] text-white/35 font-mono">{{ replaceStock?.ticker }}</p>
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
                  <p class="text-[10px] text-blue-300/60 uppercase tracking-wide mb-1">교체 종목</p>
                  <div class="h-0.5 rounded-full mb-2" :style="{ background: compareCandidate.color }"></div>
                  <p class="text-sm font-black truncate">{{ compareCandidate.name }}</p>
                  <p class="text-[10px] text-white/35 font-mono">{{ compareCandidate.ticker }}</p>
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

            <!-- 교체 확정 / 취소 버튼 -->
            <div class="flex gap-2">
              <button @click="compareCandidate = null"
                class="px-3 py-2.5 rounded-xl bg-white/8 border border-white/15 text-white/50 text-xs font-bold hover:bg-white/12 transition-colors flex-shrink-0">
                취소
              </button>
              <button @click="confirmReplace"
                class="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 bg-blue-500/20 border border-blue-500/35 text-blue-200 hover:bg-blue-500/30">
                교체 확정
              </button>
            </div>
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
              <p class="text-[10px] text-white/30 font-mono uppercase tracking-[0.2em]">Financial Statements</p>
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
                  class="flex-1 py-1.5 rounded-lg text-[12px] font-bold transition-all text-center"
                  :class="finTab === tab.key ? 'bg-white/14 text-white' : 'text-white/30 hover:text-white/60'">
            {{ tab.label }}
          </button>
        </div>

        <!-- 단위 레이블 -->
        <div class="px-5 pt-2 pb-0.5 flex-shrink-0 flex items-center justify-between">
          <span class="text-[10px] text-white/25">(단위: 억원)</span>
          <span class="text-[10px] text-white/25 font-mono" v-if="finData">{{ detailCompany?.ticker }}</span>
        </div>

        <!-- 재무 데이터 본문 -->
        <div class="flex-1 overflow-y-auto px-4 pb-4 pt-1">

          <!-- ─── 손익계산서 ─── -->
          <template v-if="finTab === 'income' && finData">
            <!-- 연도 헤더 -->
            <div class="grid grid-cols-4 gap-1 pb-1.5 mb-0.5 border-b border-white/10">
              <span></span>
              <span v-for="y in finData.years" :key="y"
                    class="text-[11px] text-white/40 font-mono text-right font-bold">{{ y }}</span>
            </div>
            <!-- 데이터 행 -->
            <div v-for="row in incomeRows" :key="row.key"
                 class="grid grid-cols-4 gap-1 py-2 border-b border-white/6 last:border-0"
                 :class="row.hl ? 'bg-white/5 -mx-1 px-1 rounded-lg border-0 my-0.5' : ''">
              <span class="text-[11px] text-white/45 leading-tight">{{ row.label }}</span>
              <span v-for="(val, i) in row.values" :key="i"
                    class="text-[11px] text-right font-bold tabular-nums"
                    :class="row.color ? (val >= 0 ? 'text-green-300' : 'text-red-300') : 'text-white/82'">
                {{ row.pct ? val + '%' : val.toLocaleString() }}
              </span>
            </div>
            <!-- 매출액 미니 바 차트 -->
            <div class="mt-4">
              <p class="text-[10px] text-white/25 uppercase tracking-widest mb-2">매출액 추이</p>
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
            <p class="text-[10px] text-white/28 mb-3">기준: {{ finData.years[2] }}년</p>
            <!-- 자산 / 부채 / 자본 -->
            <div v-for="row in balanceRows" :key="row.key"
                 class="flex items-center justify-between py-2.5 border-b border-white/6 last:border-0"
                 :class="row.hl ? 'bg-white/5 -mx-1 px-1 rounded-lg border-0 my-0.5' : ''">
              <span class="text-[12px] text-white/45">{{ row.label }}</span>
              <span class="text-[13px] font-black tabular-nums"
                    :class="row.hl ? 'text-white' : 'text-white/72'">
                {{ row.val.toLocaleString() }}
              </span>
            </div>
            <!-- 부채비율 게이지 -->
            <div class="mt-4">
              <div class="flex justify-between mb-1.5">
                <span class="text-[11px] text-white/40">부채비율</span>
                <span class="text-[12px] font-black"
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
                  <span class="text-[11px] text-white/55">자본 {{ (equityRatio * 100).toFixed(1) }}%</span>
                </div>
                <div class="flex items-center gap-2">
                  <div class="w-2.5 h-2.5 rounded-sm bg-white/12 flex-shrink-0"></div>
                  <span class="text-[11px] text-white/55">부채 {{ ((1 - equityRatio) * 100).toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </template>

          <!-- ─── 현금흐름표 ─── -->
          <template v-else-if="finTab === 'cashflow' && finData">
            <div class="grid grid-cols-4 gap-1 pb-1.5 mb-0.5 border-b border-white/10">
              <span></span>
              <span v-for="y in finData.years" :key="y"
                    class="text-[11px] text-white/40 font-mono text-right font-bold">{{ y }}</span>
            </div>
            <div v-for="row in cashflowRows" :key="row.key"
                 class="grid grid-cols-4 gap-1 py-2 border-b border-white/6 last:border-0"
                 :class="row.key === 'net' ? 'bg-white/5 -mx-1 px-1 rounded-lg border-0 mt-0.5' : ''">
              <span class="text-[11px] text-white/45">{{ row.label }}</span>
              <span v-for="(val, i) in row.values" :key="i"
                    class="text-[11px] text-right font-bold tabular-nums"
                    :class="val >= 0 ? 'text-green-300' : 'text-red-300'">
                {{ (val >= 0 ? '+' : '') + val.toLocaleString() }}
              </span>
            </div>
            <!-- 영업활동 현금흐름 미니 바차트 -->
            <div class="mt-4">
              <p class="text-[10px] text-white/25 uppercase tracking-widest mb-2">영업활동 현금흐름</p>
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
import { LucideChevronRight, LucideChevronLeft, LucideBarChart2, LucideArrowLeftRight } from 'lucide-vue-next'
import { generateMockOHLC } from '@/mock/data.js'
import StockChartModal from '@/components/modal/StockChartModal.vue'
import { stocksApi } from '@/api/stocks.js'
import { chartApi } from '@/api/chart.js'
// import { financeApi } from '@/api/finance.js'  // [미사용] 재무 API 연결 시 주석 해제
import { useStocksStore } from '@/stores/stocks.js'
import { useScreenerStore } from '@/stores/screener.js'

const props = defineProps({
  darkMode:     { type: Boolean, default: false },
  replaceMode:  { type: Boolean, default: false },
  replaceStock: { type: Object,  default: null  },
  viewTicker:   { type: String,  default: null  },
});
const emit = defineEmits(['select-company', 'add-company', 'back', 'cancel-replace']);

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

// ── AI 추천 랭킹 (screener 연동) ─────────────
const recommendList = computed(() => {
  const src = screenerStore.items.length > 0 ? screenerStore.items : stocksStore.items
  if (src.length === 0) return []
  return src.map(s => ({
    id:         s.ticker,
    name:       s.name ?? s.ticker,
    ticker:     s.ticker,
    sector:     s.sector ?? '',
    price:      s.close_price ?? s.close ?? s.price ?? 0,
    change:     s.change_rate ?? s.change ?? 0,
    color:      scoreToColor(Math.round(s.composite_score ?? s.score ?? 0)),
    marketCap:  s.market_cap_str ?? '',
    per:        s.per ?? null,
    pbr:        s.pbr ?? null,
    dividend:   s.dividend_yield ?? null,
    quantScore: Math.round(s.composite_score ?? s.score ?? 0),
    tier:       s.tier ?? '—',
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
      price:       s.close_price ?? s.close ?? s.price ?? 0,
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
  return []
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

async function fetchCommunity() {
  communityLoading.value = true
  communityError.value   = false
  try {
    const { data } = await stocksApi.getPopularPosts(20)
    communityList.value = data.items ?? []
  } catch {
    communityError.value = true
    communityList.value  = []
  } finally {
    communityLoading.value = false
  }
}

// ── 급상승 종목 ───────────────────────────────
const risingList    = ref([])
const risingLoading = ref(false)
const risingError   = ref(false)

async function fetchRising() {
  risingLoading.value = true
  risingError.value   = false
  try {
    const { data } = await stocksApi.getRisingStocks({ limit: 20 })
    risingList.value = data.items ?? []
  } catch {
    risingError.value = true
    risingList.value  = []
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
  price:      s.close_price ?? s.close ?? s.price ?? 0,
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

// ── 우측 패널: 평균 점수 ──────────────────────
const avgScore = computed(() => {
  if (!searchAllItems.value.length) return 0
  const sum = searchAllItems.value.reduce((acc, s) => acc + (s.quantScore ?? 0), 0)
  return Math.round(sum / searchAllItems.value.length)
})

// ── 우측 패널: 점수 분포 히스토그램 ──────────
const scoreBucketColors = [
  '#f87171','#fb923c','#fbbf24','#a3e635','#4ade80',
  '#34d399','#2dd4bf','#38bdf8','#818cf8','#a78bfa',
]
const scoreBuckets = computed(() => {
  const b = Array(10).fill(0)
  searchAllItems.value.forEach(s => {
    const idx = Math.min(Math.floor((s.quantScore ?? 0) / 10), 9)
    b[idx]++
  })
  return b
})
const maxBucket = computed(() => Math.max(...scoreBuckets.value, 1))

// ── 우측 패널: Tier 도넛 세그먼트 ────────────
const TIER_COLORS_MAP = { A: '#34d399', B: '#93c5fd', C: '#fbbf24', D: '#f87171' }
const tierDonutSegments = computed(() => {
  const total = searchAllItems.value.length || 1
  const C = 175.9   // 2 * π * r (r=28)
  let offset = 0
  return ['A', 'B', 'C', 'D'].map(tk => {
    const count = tierCounts.value[tk] ?? 0
    const dash  = (count / total) * C
    const seg   = { color: TIER_COLORS_MAP[tk], dash, offset }
    offset += dash
    return seg
  })
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

    // ── stocksApi.getScreener에 전달할 파라미터 구성 ──────────────
    const TIER_MIN = { A: 80, B: 60, C: 40, D: 0 }
    const params = {}
    if (f.model_version) params.model_version = f.model_version
    if (f.date)          params.date          = f.date
    if (f.sector)        params.sector        = f.sector
    if (f.tier)          params.tier          = f.tier
    // tier → min_score 변환
    const tierMin  = f.tier ? (TIER_MIN[f.tier] ?? 0) : 0
    const minScore = Math.max(Number(f.min_score ?? 0), tierMin)
    if (minScore > 0) params.min_score = minScore
    // 재무 필터
    if (f.max_per)           params.max_per           = f.max_per
    if (f.max_pbr)           params.max_pbr           = f.max_pbr
    if (f.min_roe)           params.min_roe           = f.min_roe
    if (f.max_debt_ratio)    params.max_debt_ratio    = f.max_debt_ratio
    if (f.min_op_margin)     params.min_op_margin     = f.min_op_margin
    if (f.min_rev_growth)    params.min_rev_growth    = f.min_rev_growth
    if (f.min_finance_score) params.min_finance_score = f.min_finance_score
    params.sort_by = f.sort_by ?? 'composite_score'
    params.limit   = f.limit   ?? 100

    const { data } = await stocksApi.getScreener(params)
    let items = (data.items ?? []).map(rawToItem)

    // ── 클라이언트 사이드: tier 정확 필터 ─────────────────
    // API는 min_score로만 필터 → tier 라벨 정확 매칭은 클라이언트에서 처리
    if (f.tier) {
      items = items.filter(s => s.tier === f.tier)
    }

    // ── 클라이언트 사이드: sort_by ─────────────────────────
    // 백엔드 응답에는 score/tier만 있으므로 score 기준 정렬만 지원
    if (f.sort_by === 'score' || f.sort_by === 'composite_score') {
      items.sort((a, b) => b.quantScore - a.quantScore)
    }
    // per·pbr·roe 정렬은 API에 해당 필드 없으므로 score 정렬 유지

    searchAllItems.value = items
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

// ── 종목 비교 ──────────────────────────────────
const showCompare          = ref(false)
const compareStockA        = ref(null)
const compareStockB        = ref(null)
const compareSelectingSlot = ref(null)   // 'A' | 'B' | null
const compareAHistory      = ref([])
const compareBHistory      = ref([])
const compareHistoryLoading = ref(false)

// 비교 선택용 종목 목록 (screener 또는 recommend 재활용)
const comparePickList = computed(() => {
  const src = screenerStore.items.length > 0 ? screenerStore.items : stocksStore.items
  return src.map(s => ({
    ticker:        s.ticker,
    name:          s.name ?? s.ticker,
    sector:        s.sector ?? '',
    tier:          s.tier ?? '—',
    quantScore:    Math.round(s.composite_score ?? s.score ?? 0),
    prob_ensemble: s.prob_ensemble ?? 0,
    color:         scoreToColor(Math.round(s.composite_score ?? s.score ?? 0)),
  }))
})

function openCompareOverlay() {
  showCompare.value = true
  // 빈 슬롯 자동 포커스
  if (!compareStockA.value)       compareSelectingSlot.value = 'A'
  else if (!compareStockB.value)  compareSelectingSlot.value = 'B'
  else                            compareSelectingSlot.value = null
}

function closeCompareOverlay() {
  showCompare.value         = false
  compareSelectingSlot.value = null
}

function startSelectSlot(slot) {
  compareSelectingSlot.value = slot
}

async function assignCompareSlot(stock) {
  if (compareSelectingSlot.value === 'A') compareStockA.value = stock
  else if (compareSelectingSlot.value === 'B') compareStockB.value = stock

  // 다음 빈 슬롯으로 자동 이동
  if (!compareStockA.value)      compareSelectingSlot.value = 'A'
  else if (!compareStockB.value) compareSelectingSlot.value = 'B'
  else {
    compareSelectingSlot.value = null
    await fetchCompareHistories()
  }
}

async function fetchCompareHistories() {
  if (!compareStockA.value || !compareStockB.value) return
  compareHistoryLoading.value = true
  compareAHistory.value = []
  compareBHistory.value = []
  try {
    const [rA, rB] = await Promise.all([
      stocksApi.getHistory(compareStockA.value.ticker, {}),
      stocksApi.getHistory(compareStockB.value.ticker, {}),
    ])
    compareAHistory.value = rA.data.items ?? []
    compareBHistory.value = rB.data.items ?? []
  } catch {
    // 이력 없어도 기본 비교는 표시
  } finally {
    compareHistoryLoading.value = false
  }
}

// 지표 비교 행 생성
const compareMetricRows = computed(() => {
  if (!compareStockA.value || !compareStockB.value) return []
  const A = compareStockA.value, B = compareStockB.value
  const pct = (v) => v != null ? (v * 100).toFixed(1) + '%' : '—'
  return [
    {
      label: 'Tier',
      valA: A.tier, valB: B.tier,
      betterA: A.tier < B.tier,   // A < B < C < D (문자열 비교)
      betterB: B.tier < A.tier,
    },
    {
      label: 'AI 점수',
      valA: String(A.quantScore), valB: String(B.quantScore),
      betterA: A.quantScore > B.quantScore,
      betterB: B.quantScore > A.quantScore,
    },
    {
      label: '앙상블 확률',
      valA: pct(A.prob_ensemble), valB: pct(B.prob_ensemble),
      betterA: (A.prob_ensemble ?? 0) > (B.prob_ensemble ?? 0),
      betterB: (B.prob_ensemble ?? 0) > (A.prob_ensemble ?? 0),
    },
    {
      label: '섹터',
      valA: A.sector || '—', valB: B.sector || '—',
      betterA: false, betterB: false,
    },
  ]
})

// 이력 스파크라인 SVG 경로
const compareChartPaths = computed(() => {
  const hA = compareAHistory.value.slice(-30)
  const hB = compareBHistory.value.slice(-30)
  if (!hA.length && !hB.length) return { pathA: '', pathB: '' }

  const allScores = [...hA, ...hB].map(d => d.score)
  const minS = Math.min(...allScores), maxS = Math.max(...allScores)
  const range = maxS - minS || 1
  const W = 300, H = 70, PH = 4, PV = 6
  const uw = W - PH * 2, uh = H - PV * 2

  const makePath = (hist) => {
    if (!hist.length) return ''
    const pts = hist.map((d, i) => {
      const x = PH + (i / Math.max(hist.length - 1, 1)) * uw
      const y = PV + (1 - (d.score - minS) / range) * uh
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    return `M ${pts[0]} L ${pts.slice(1).join(' L ')}`
  }

  return { pathA: makePath(hA), pathB: makePath(hB) }
})

// 슬롯 재선택 시 이력도 재로드
watch([compareStockA, compareStockB], ([a, b]) => {
  if (a && b && compareSelectingSlot.value === null) fetchCompareHistories()
})

function selectSearchResult(s) {
  const company = s.id ? s : { ...s, id: s.ticker }
  if (props.replaceMode) {
    closeSearch()
    emit('select-company', buildPortfolioItem(company))
    return
  }
  closeSearch()
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

// ── 상세 뷰 추가 데이터 ───────────────────────
const fairValue    = ref(null)
const radarData    = ref(null)
const dividendData = ref(null)
const peers        = ref([])

// radarPoints computed (오각형 5개 꼭짓점)
const radarPoints = computed(() => {
  if (!radarData.value) return ''
  const groups = radarData.value.groups ?? {}
  const scores = [
    (groups.growth?.score ?? 0) / 100,
    (groups.profitability?.score ?? 0) / 100,
    (groups.safety?.score ?? 0) / 100,
    (groups.moat?.score ?? 0) / 100,
    (groups.cashflow?.score ?? 0) / 100,
  ]
  return pentagon(60, 55, 45, scores)
})

function hexPoints(cx, cy, r) {
  const angles = [-90, -18, 54, 126, 198]
  return angles.map(a => {
    const rad = a * Math.PI / 180
    return `${(cx + r * Math.cos(rad)).toFixed(1)},${(cy + r * Math.sin(rad)).toFixed(1)}`
  }).join(' ')
}

function pentagon(cx, cy, r, scores) {
  const angles = [-90, -18, 54, 126, 198]
  return angles.map((a, i) => {
    const rad = a * Math.PI / 180
    const s = scores[i] ?? 0
    return `${(cx + r * s * Math.cos(rad)).toFixed(1)},${(cy + r * s * Math.sin(rad)).toFixed(1)}`
  }).join(' ')
}

// 상세 데이터 로딩
async function loadDetailData(ticker) {
  fairValue.value    = null
  radarData.value    = null
  dividendData.value = null
  peers.value        = []
  try {
    const [fv, rd, dv, pr] = await Promise.allSettled([
      stocksApi.getFairValue(ticker),
      stocksApi.getStockRadar(ticker),
      stocksApi.getDividend(ticker),
      stocksApi.getPeers(ticker, 4),
    ])
    if (fv.status === 'fulfilled') fairValue.value    = fv.value.data
    if (rd.status === 'fulfilled') radarData.value    = rd.value.data
    if (dv.status === 'fulfilled') dividendData.value = dv.value.data
    if (pr.status === 'fulfilled') {
      peers.value = (pr.value.data?.items ?? []).map(s => ({
        ...s,
        color: scoreToColor(Math.round(s.composite_score ?? s.score ?? 0)),
      }))
    }
  } catch {}
}

const quantBarColor  = (s) => s >= 70 ? 'bg-green-400' : s >= 45 ? 'bg-yellow-400' : 'bg-red-400';
const quantTextColor = (s) => s >= 70 ? 'text-green-300' : s >= 45 ? 'text-yellow-300' : 'text-red-300';

// ── 교체 비교 ──────────────────────────────────
const compareCandidate = ref(null);

const currentStockInfo = computed(() =>
  props.replaceStock ? companies.value.find(c => c.ticker === props.replaceStock.ticker) : null
);

const openCompare = (company) => {
  compareCandidate.value = company;
};

const confirmReplace = () => {
  emit('select-company', {
    id:           Date.now(),
    company:      compareCandidate.value.name,
    ticker:       compareCandidate.value.ticker,
    sector:       compareCandidate.value.sector,
    currentPrice: compareCandidate.value.price,
    change:       compareCandidate.value.change,
    color:        compareCandidate.value.color,
    weight:       10,
    quantScore:   compareCandidate.value.quantScore,
  });
  compareCandidate.value = null;
};

// ── 상세 차트 ─────────────────────────────────
const showChart      = ref(false)
const apiChartData   = ref([])
const chartLoading   = ref(false)

const detailChartData = computed(() => {
  if (apiChartData.value.length > 0) return apiChartData.value
  if (!detailCompany.value) return []
  // fallback: 목업 데이터
  return generateMockOHLC(detailCompany.value.ticker, detailCompany.value.price || 50000)
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

// ── 상세 뷰 ────────────────────────────────────
watch(() => props.viewTicker, (ticker) => {
  if (ticker) {
    detailCompany.value = companies.value.find(c => c.ticker === ticker) ?? null
    fetchChart(ticker)
    loadDetailData(ticker)
  }
}, { immediate: true })

const openDetail = (company) => {
  detailCompany.value = company
  showChart.value     = false
  showFinancial.value = false
  finTab.value        = 'income'
  fetchChart(company.ticker)
  loadDetailData(company.ticker)
}
const closeDetail = () => {
  detailCompany.value = null;
  showChart.value     = false;
  showFinancial.value = false;
  fairValue.value    = null;
  radarData.value    = null;
  dividendData.value = null;
  peers.value        = [];
  if (props.viewTicker) emit('back');
};

// ── 교체 모드 ──────────────────────────────────
const buildPortfolioItem = (company) => ({
  id: Date.now(),
  company: company.name ?? company.company ?? company.ticker,
  ticker: company.ticker,
  sector: company.sector ?? '',
  shares: 10,
  avgPrice: company.price ?? 0,
  currentPrice: company.price ?? 0,
  change: company.change ?? 0,
  color: company.color ?? '#888',
  quantScore: company.quantScore ?? company.score ?? 50,
  weight: 10,
})

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

/* 패널 슬라이드 (오른쪽에서) — 검색/비교 오버레이 */
.panel-slide-enter-active { transition: transform 0.32s cubic-bezier(0.32,0,0.2,1), opacity 0.22s ease; }
.panel-slide-leave-active { transition: transform 0.22s ease, opacity 0.18s ease; }
.panel-slide-enter-from   { transform: translateX(100%); opacity: 0; }
.panel-slide-leave-to     { transform: translateX(100%); opacity: 0; }
</style>
