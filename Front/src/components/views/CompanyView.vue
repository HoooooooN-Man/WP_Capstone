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
        <!-- 재무제표 버튼: 상세 뷰 + 일반 모드에서만 -->
        <button v-if="detailCompany && !replaceMode"
                @click="showFinancial = true"
                class="ml-auto px-2.5 py-1.5 rounded-lg bg-white/8 border border-white/15 text-[10px] text-white/55 hover:bg-white/14 hover:text-white/80 transition-all font-bold tracking-wide flex-shrink-0 flex items-center gap-1">
          <LucideBarChart2 class="w-3 h-3" />
          재무제표
        </button>
      </div>
      <p v-if="replaceMode && !detailCompany" class="text-[10px] text-white/35 mt-1">교체할 종목을 선택하세요</p>
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

    <!-- 기업 리스트 뷰 -->
    <div v-else class="flex-1 overflow-y-auto px-4 py-3 space-y-2">
      <div
        v-for="company in companies" :key="company.id"
        class="flex items-center gap-3 p-3 rounded-xl border border-white/5 transition-all duration-200 cursor-pointer"
        :class="replaceMode
          ? 'bg-white/5 hover:bg-white/10 hover:border-emerald-500/30'
          : 'bg-white/5 hover:bg-white/8 hover:border-white/15'"
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
        <!-- 퀀트 스코어 -->
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
            <button
              @click.stop="openOrderModal(company, 'buy')"
              class="px-2 py-1 rounded-lg text-[10px] font-bold border transition-all duration-200 bg-blue-500/15 border-blue-500/30 text-blue-300 hover:bg-blue-500/30"
            >매수</button>
            <button
              @click.stop="openOrderModal(company, 'sell')"
              class="px-2 py-1 rounded-lg text-[10px] font-bold border transition-all duration-200 bg-red-500/15 border-red-500/30 text-red-300 hover:bg-red-500/30"
            >매도</button>
          </template>
          <LucideChevronRight class="w-4 h-4 text-white/25 ml-0.5" />
        </div>
      </div>
    </div>

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
import { ref, computed, watch, onMounted } from 'vue'
import { LucidePlus, LucideCheck, LucideChevronRight, LucideChevronLeft, LucideBarChart2 } from 'lucide-vue-next'
import { MOCK_COMPANIES, generateMockOHLC } from '@/mock/data.js'
import StockChartModal from '@/components/modal/StockChartModal.vue'
import { stocksApi } from '@/api/stocks.js'
import { chartApi } from '@/api/chart.js'
import { financeApi } from '@/api/finance.js'
import { useStocksStore } from '@/stores/stocks.js'
import { useMarketStore } from '@/stores/market.js'

const props = defineProps({
  replaceMode:  { type: Boolean, default: false },
  replaceStock: { type: Object,  default: null  },
  viewTicker:   { type: String,  default: null  },
});
const emit = defineEmits(['select-company', 'add-company', 'back', 'sell-replace']);

const stocksStore = useStocksStore()
const marketStore = useMarketStore()

// 실제 API 데이터 우선 사용, fallback → 목업
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

onMounted(async () => {
  if (stocksStore.items.length === 0) {
    await stocksStore.initVersionsAndDates()
    await stocksStore.fetchRecommendations()
  }
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

// 개요 스파크라인용: 마지막 60일 종가
const overviewPrices = computed(() => detailChartData.value.slice(-60).map(d => d.close));

const overviewPaths = computed(() => {
  const prices = overviewPrices.value;
  if (prices.length < 2) return { area: '', line: '' };
  const W = 300, H = 72, PH = 10, PV = 8;
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
const buildPortfolioItem = (company) => ({
  id:           Date.now(),
  company:      company.name,
  ticker:       company.ticker,
  sector:       company.sector,
  shares:       10,
  avgPrice:     company.price,
  currentPrice: company.price,
  change:       company.change,
  color:        company.color,
  weight:       10,
});

const selectCompany = (company) => {
  emit('select-company', buildPortfolioItem(company));
};

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
</style>
