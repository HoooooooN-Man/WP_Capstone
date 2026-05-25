<template>
  <div class="w-full h-full overflow-hidden relative select-none text-white"
       style="background: linear-gradient(160deg, #1a2e4a 0%, #0e1d30 100%)">

    <!-- ── 스크롤 메인 컨텐츠 (카드별 화면 전환) ── -->
    <div class="absolute inset-0 overflow-y-auto" style="scrollbar-width:thin;padding-bottom:220px">
      <transition name="page-switch" mode="out-in">

        <!-- ── [0] 오버뷰: main 브랜치 포트폴리오 그대로 (다크 테마) ── -->
        <div v-if="currentIndex === 0" key="overview"
             class="max-w-5xl mx-auto px-6 py-8 flex flex-col gap-8">

          <!-- Section 1: 포트폴리오 전략 -->
          <div class="flex flex-col gap-4">
            <h1 class="text-xl font-semibold text-white">포트폴리오</h1>

            <!-- Strategy Tabs (다크) -->
            <div class="flex items-center justify-between">
              <div class="flex gap-2">
                <button v-for="t in [{ value:'growth', label:'성장형' },{ value:'stable', label:'안정형' }]" :key="t.value"
                        class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                        :class="store.activeType === t.value
                          ? 'bg-white/15 text-white border border-white/25'
                          : 'border border-white/12 text-white/40 hover:bg-white/8'"
                        @click="onTypeChange(t.value)">
                  {{ t.label }}
                </button>
              </div>
              <div class="flex items-center gap-3">
                <select :value="store.selectedVersion"
                        class="rounded-lg px-2.5 py-1.5 text-sm text-white focus:outline-none"
                        style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15)"
                        @change="onVersionChange($event.target.value)">
                  <option value="latest" style="background:#1a2e4a">최신 버전</option>
                  <option v-for="v in store.versions" :key="v" :value="v" style="background:#1a2e4a">{{ v }}</option>
                </select>
                <span v-if="store.currentDate" class="text-sm text-white/40">기준일 {{ store.currentDate }}</span>
              </div>
            </div>

            <!-- Portfolio Card Grid (다크) -->
            <div v-if="portfolioError === 'not_ready'"
                 class="rounded-xl px-4 py-3 text-sm text-amber-400"
                 style="background:rgba(251,191,36,0.06);border:1px solid rgba(251,191,36,0.15)">
              <template v-if="store.activeType === 'stable'">
                현재 PBR 재무 데이터가 준비중입니다.<br>데이터 준비 완료 후 이용 가능합니다.
              </template>
              <template v-else>KOSPI 추천 데이터가 준비중입니다.</template>
            </div>
            <div v-else-if="portfolioError && portfolioError !== 'not_ready'"
                 class="text-center text-white/40 py-8 text-sm">
              데이터를 불러오지 못했습니다
            </div>
            <div v-else-if="store.loading" class="grid grid-cols-2 gap-3">
              <div v-for="i in 10" :key="i" class="h-28 rounded-xl animate-pulse"
                   style="background:rgba(255,255,255,0.05)"></div>
            </div>
            <div v-else class="grid grid-cols-2 gap-3">
              <div v-for="item in store.currentItems" :key="item.ticker"
                   class="rounded-xl p-4 cursor-pointer border transition-colors"
                   style="background:rgba(255,255,255,0.04);border-color:rgba(255,255,255,0.08)"
                   @click="emit('view-company', item.ticker)">
                <div class="flex items-center justify-between mb-2">
                  <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium text-white/60"
                        style="background:rgba(255,255,255,0.1)">{{ item.rank }}</span>
                  <span class="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-semibold"
                        :style="tierStyle(item.tier)">{{ item.tier }}</span>
                </div>
                <p class="text-sm font-medium text-white mb-0.5 truncate">{{ item.name }}</p>
                <p class="font-mono text-xs text-white/35 mb-2">{{ item.ticker }}</p>
                <div class="flex items-center justify-between">
                  <span class="text-xs text-white/30 rounded-full px-2 py-0.5"
                        style="background:rgba(255,255,255,0.07)">{{ item.sector }}</span>
                  <div class="flex items-center gap-1.5">
                    <div class="w-16 h-1.5 rounded overflow-hidden" style="background:rgba(255,255,255,0.1)">
                      <div class="h-full rounded"
                           :style="{ width: item.score + '%', backgroundColor: barColor(item.score) }"></div>
                    </div>
                    <span class="text-xs font-medium text-white/60">{{ Math.round(item.score) }}</span>
                  </div>
                </div>
                <div v-if="store.activeType === 'stable' && item.pbr != null"
                     class="flex items-center gap-1 mt-1.5">
                  <span class="text-xs text-white/30">PBR</span>
                  <span class="text-xs font-medium text-blue-300">{{ item.pbr.toFixed(2) }}</span>
                </div>
              </div>
            </div>

            <!-- Strategy Explanation (다크) -->
            <div v-if="store.activeType === 'growth'"
                 class="rounded-xl p-4" style="background:rgba(255,255,255,0.04)">
              <p class="text-sm font-semibold text-white mb-1">성장형 전략</p>
              <p class="text-sm text-white/50 leading-relaxed">
                ML 모델이 단기 상승 가능성이 높다고 판단한 KOSPI 상장 종목 Top 10입니다.<br>
                LightGBM · XGBoost · CatBoost 앙상블 점수를 기준으로 정렬했습니다.
              </p>
            </div>
            <div v-else class="flex flex-col gap-3">
              <div class="rounded-xl p-4" style="background:rgba(255,255,255,0.04)">
                <p class="text-sm font-semibold text-white mb-1">안정형 전략</p>
                <p class="text-sm text-white/50 leading-relaxed">
                  Tier A·B 종목 (ML점수 60점 이상) 중 최신 분기 PBR이 1.5 미만인 종목을 선별하여
                  하방 리스크를 제한한 가치투자형 전략입니다.
                </p>
              </div>
              <div class="overflow-auto rounded-xl border" style="border-color:rgba(255,255,255,0.1)">
                <table class="w-full text-sm">
                  <thead style="background:rgba(255,255,255,0.05)">
                    <tr>
                      <th class="text-left text-xs text-white/40 font-medium px-4 py-2.5">PBR 범위</th>
                      <th class="text-left text-xs text-white/40 font-medium px-4 py-2.5">해석</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr class="border-t" style="border-color:rgba(255,255,255,0.06)">
                      <td class="px-4 py-2 text-white/60">&lt; 1.0</td>
                      <td class="px-4 py-2 text-white/40">극도 저평가 또는 구조적 문제</td>
                    </tr>
                    <tr class="border-t" style="border-color:rgba(255,255,255,0.06);background:rgba(59,130,246,0.08)">
                      <td class="px-4 py-2 text-blue-300 font-medium">1.0 ~ 1.5</td>
                      <td class="px-4 py-2 text-blue-300 font-medium">안정적 저평가 · 현재 기준 ✓ 해당</td>
                    </tr>
                    <tr class="border-t" style="border-color:rgba(255,255,255,0.06)">
                      <td class="px-4 py-2 text-white/60">1.5 ~ 3.0</td>
                      <td class="px-4 py-2 text-white/40">적정 수준</td>
                    </tr>
                    <tr class="border-t" style="border-color:rgba(255,255,255,0.06)">
                      <td class="px-4 py-2 text-white/60">&gt; 3.0</td>
                      <td class="px-4 py-2 text-white/40">고평가 또는 성장 프리미엄</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <hr style="border-color:rgba(255,255,255,0.08)"/>

          <!-- Section 2: 백테스트 -->
          <div class="flex flex-col gap-4">
            <div class="flex items-center justify-between">
              <h2 class="text-base font-semibold text-white">백테스트 결과</h2>
              <button class="text-xs text-white/40 hover:text-white/70 transition-colors rounded-lg px-2.5 py-1.5 border"
                      style="border-color:rgba(255,255,255,0.12)"
                      @click="backtestOpen = !backtestOpen">
                {{ backtestOpen ? '▲ 접기' : '▼ 펼치기' }}
              </button>
            </div>
            <template v-if="backtestOpen">
              <div v-if="store.backtestLoading" class="h-32 rounded-xl animate-pulse"
                   style="background:rgba(255,255,255,0.05)"/>
              <template v-else>
                <!-- BacktestSummaryTable 다크 -->
                <div v-if="store.backtestSummary?.comparison"
                     class="overflow-auto rounded-xl border" style="border-color:rgba(255,255,255,0.1)">
                  <table class="w-full text-sm">
                    <thead style="background:rgba(255,255,255,0.05)">
                      <tr>
                        <th class="text-left text-xs text-white/40 font-medium px-4 py-2.5">지표명</th>
                        <th class="text-right text-xs text-white/40 font-medium px-4 py-2.5">값</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in store.backtestSummary.comparison" :key="row.key"
                          class="border-t" style="border-color:rgba(255,255,255,0.06)">
                        <td class="px-4 py-2.5 text-white/65">{{ row.key }}</td>
                        <td class="px-4 py-2.5 text-right" :class="valueClass(row.value)">{{ row.value }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="text-center text-white/30 py-6 text-sm">백테스트 데이터 없음</div>
                <!-- BacktestMonthlyChart (차트는 그대로 사용) -->
                <BacktestMonthlyChart :data="store.backtestMonthly" />
                <div>
                  <button class="text-sm text-white/40 hover:text-white/65 transition-colors"
                          @click="rawOpen = !rawOpen">
                    {{ rawOpen ? '▲ 원문 결과 닫기' : '▼ 원문 결과 보기' }}
                  </button>
                  <pre v-if="rawOpen"
                       class="mt-2 text-xs text-white/50 rounded-xl p-4 overflow-x-auto whitespace-pre-wrap"
                       style="background:rgba(255,255,255,0.04)">{{ store.backtestSummary?.v8_walk_forward }}</pre>
                </div>
              </template>
            </template>
          </div>
        </div>

        <!-- ── [1+] 보유 종목 상세 페이지 ── -->
        <div v-else key="stock-detail" class="px-6 py-6 flex flex-col gap-5">

          <!-- 오버뷰로 돌아가기 -->
          <button class="flex items-center gap-1.5 text-white/40 hover:text-white/70 transition-colors w-fit"
                  @click="currentIndex = 0">
            <LucideChevronLeft class="w-4 h-4" />
            <span class="text-sm">포트폴리오</span>
          </button>

          <!-- 종목 헤더 -->
          <div v-if="activeStock" class="rounded-2xl p-5 border"
               :style="{
                 background: `linear-gradient(135deg, ${activeStock.color}22 0%, rgba(14,29,48,0.9) 100%)`,
                 borderColor: `${activeStock.color}35`,
               }">
            <div class="flex items-start justify-between mb-4">
              <div>
                <p class="text-[10px] text-white/40 uppercase tracking-widest mb-1">{{ activeStock.sector }}</p>
                <p class="text-2xl font-black tracking-tight">{{ activeStock.company }}</p>
                <p class="text-[11px] font-mono text-white/35 mt-0.5">{{ activeStock.ticker }}</p>
              </div>
              <div class="text-right">
                <span class="inline-block px-2.5 py-1 rounded-lg text-[11px] font-bold mb-1"
                      :class="activeStock.change >= 0 ? 'text-green-300' : 'text-red-300'"
                      :style="activeStock.change >= 0 ? 'background:rgba(52,211,153,0.15)' : 'background:rgba(248,113,113,0.15)'">
                  {{ activeStock.change >= 0 ? '+' : '' }}{{ activeStock.change }}%
                </span>
                <p class="text-2xl font-black">₩{{ activeStock.currentPrice.toLocaleString() }}</p>
              </div>
            </div>

            <!-- 보유 정보 그리드 -->
            <div class="grid grid-cols-2 gap-2.5 mb-4">
              <div class="rounded-xl px-3 py-2.5 text-center" style="background:rgba(0,0,0,0.25)">
                <p class="text-[8px] text-white/30 uppercase mb-1">보유수량</p>
                <p class="text-base font-bold">{{ activeStock.shares }}<span class="text-xs text-white/40 ml-0.5">주</span></p>
              </div>
              <div class="rounded-xl px-3 py-2.5 text-center" style="background:rgba(0,0,0,0.25)">
                <p class="text-[8px] text-white/30 uppercase mb-1">평균단가</p>
                <p class="text-base font-bold">₩{{ activeStock.avgPrice.toLocaleString() }}</p>
              </div>
              <div class="rounded-xl px-3 py-2.5 text-center" style="background:rgba(0,0,0,0.25)">
                <p class="text-[8px] text-white/30 uppercase mb-1">평가금액</p>
                <p class="text-base font-bold">₩{{ (activeStock.shares * activeStock.currentPrice).toLocaleString() }}</p>
              </div>
              <div class="rounded-xl px-3 py-2.5 text-center" style="background:rgba(0,0,0,0.25)">
                <p class="text-[8px] text-white/30 uppercase mb-1">평가손익</p>
                <p class="text-base font-bold" :class="calcPL(activeStock) >= 0 ? 'text-green-300' : 'text-red-300'">
                  {{ calcPL(activeStock) >= 0 ? '+' : '' }}₩{{ Math.abs(calcPL(activeStock)).toLocaleString() }}
                </p>
              </div>
            </div>

            <!-- Quant 점수 -->
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <p class="text-[9px] text-white/35 uppercase tracking-wide">Quant Score</p>
                <p class="text-sm font-black"
                   :class="(activeStock.quantScore ?? 50) >= 70 ? 'text-green-300' : (activeStock.quantScore ?? 50) >= 45 ? 'text-yellow-300' : 'text-red-300'">
                  {{ activeStock.quantScore ?? '—' }}
                </p>
              </div>
              <div class="w-full h-2 rounded-full" style="background:rgba(255,255,255,0.1)">
                <div class="h-full rounded-full transition-all"
                     :class="(activeStock.quantScore ?? 50) >= 70 ? 'bg-green-400' : (activeStock.quantScore ?? 50) >= 45 ? 'bg-yellow-400' : 'bg-red-400'"
                     :style="{ width: `${activeStock.quantScore ?? 50}%` }"></div>
              </div>
            </div>
          </div>

          <!-- 안내 -->
          <div class="rounded-xl px-4 py-3 text-center text-[11px] text-white/25"
               style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06)">
            하단 팬 메뉴에서 해당 카드를 <strong class="text-white/40">길게 누른 후</strong> 좌우로 드래그 →
            <span class="text-red-300/70">청산</span> / <span class="text-emerald-300/70">교체</span>
          </div>

          <!-- Company 상세 보기 버튼 -->
          <button v-if="activeStock"
                  class="w-full py-3 rounded-xl border text-sm font-medium transition-colors hover:bg-white/8"
                  style="border-color:rgba(255,255,255,0.14);color:rgba(255,255,255,0.6)"
                  @click="emit('view-company', activeStock.ticker)">
            {{ activeStock.company }} 상세 보기 →
          </button>
        </div>

      </transition>
    </div><!-- /scrollable -->

    <!-- ── 팬 트리거 스트립 ── -->
    <div class="absolute bottom-0 left-0 right-0 h-6 z-30"
         @mouseenter="fanVisible = true"></div>

    <!-- ── 팬 스트립 (지갑 바와 동일한 슬라이드-업 애니메이션) ── -->
    <div class="absolute bottom-0 left-0 right-0 z-20"
         :style="{
           transform: fanVisible ? 'translateY(0)' : 'translateY(100%)',
           transition: 'transform 0.38s cubic-bezier(0.32, 0, 0.2, 1)',
         }"
         @mouseleave="!swipeMode && (fanVisible = false)">

      <!-- 그라데이션 배경 -->
      <div class="absolute inset-0 pointer-events-none"
           style="background:linear-gradient(to top, #0e1d30 0%, #0e1d30 55%, rgba(14,29,48,0.88) 75%, transparent 100%)"></div>

      <!-- 팬 카드 + 버튼 컨테이너 (210px) -->
      <div class="relative" style="height:210px">

        <!-- 스와이프 힌트 -->
        <transition name="fade">
          <div v-if="swipeMode" class="absolute inset-0 pointer-events-none" style="z-index:5">
            <div class="absolute left-5 top-[45%] -translate-y-1/2 flex flex-col items-center gap-1.5"
                 :style="{ opacity: dragX < -20 ? Math.min(1, (-dragX - 20) / 55) : 0.15 }">
              <div class="w-11 h-11 rounded-full flex items-center justify-center"
                   style="background:rgba(239,68,68,0.2);border:1.5px solid rgba(239,68,68,0.4)">
                <LucideTrash2 class="w-4 h-4 text-red-400" />
              </div>
              <p class="text-[8px] text-red-400 font-bold uppercase tracking-wide">청산</p>
            </div>
            <div class="absolute right-5 top-[45%] -translate-y-1/2 flex flex-col items-center gap-1.5"
                 :style="{ opacity: dragX > 20 ? Math.min(1, (dragX - 20) / 55) : 0.15 }">
              <div class="w-11 h-11 rounded-full flex items-center justify-center"
                   style="background:rgba(16,185,129,0.2);border:1.5px solid rgba(16,185,129,0.4)">
                <LucideRefreshCw class="w-4 h-4 text-emerald-400" />
              </div>
              <p class="text-[8px] text-emerald-400 font-bold uppercase tracking-wide">교체</p>
            </div>
          </div>
        </transition>

        <!-- 부채꼴 카드들 -->
        <div v-for="(item, i) in displayItems" :key="item.id"
             class="absolute rounded-2xl overflow-hidden text-white"
             :style="cardFanStyle(i)"
             @click="onCardClick(i)"
             @mousedown="(e) => onCardDown(i, e)"
             @mousemove="(e) => onCardMove(i, e)"
             @mouseup="() => onCardUp(i)"
             @mouseleave="() => onCardLeave(i)"
             @touchstart.prevent="(e) => onCardDown(i, e)"
             @touchmove.prevent="(e) => onCardMove(i, e)"
             @touchend.prevent="() => onCardUp(i)">

          <div class="absolute inset-0 pointer-events-none"
               style="background:linear-gradient(135deg,rgba(255,255,255,0.2) 0%,transparent 60%)"></div>

          <!-- 오버뷰 카드 -->
          <div v-if="item.isOverview" class="relative h-full flex flex-col justify-between p-2.5">
            <div>
              <p class="text-[6.5px] font-bold uppercase tracking-widest mb-0.5"
                 style="color:rgba(201,162,39,0.9)">Portfolio</p>
              <p class="text-[12px] font-black leading-tight">
                {{ totalValue >= 1_000_000
                  ? '₩' + (totalValue/1_000_000).toFixed(1)+'M'
                  : '₩' + totalValue.toLocaleString() }}
              </p>
            </div>
            <div>
              <div v-if="activeStocks.length" class="flex gap-[1.5px] h-1 rounded-full overflow-hidden mb-1.5">
                <div v-for="s in activeStocks.slice(0,6)" :key="s.id"
                     class="h-full flex-1" :style="{ background: s.color ?? '#4A90E2' }"></div>
              </div>
              <p class="text-[11px] font-black"
                 :class="totalReturn >= 0 ? 'text-green-300' : 'text-red-300'">
                {{ totalReturn >= 0 ? '+' : '' }}{{ totalReturn.toFixed(1) }}%
              </p>
              <p class="text-[7px] mt-0.5" style="color:rgba(255,255,255,0.38)">{{ activeStocks.length }}종목</p>
            </div>
          </div>

          <!-- 종목 카드 -->
          <div v-else class="relative h-full flex flex-col justify-between p-2.5">
            <div>
              <p class="text-[9px] font-black leading-tight truncate">{{ item.company }}</p>
              <p class="text-[7px] font-mono mt-0.5" style="color:rgba(255,255,255,0.38)">{{ item.ticker }}</p>
            </div>
            <div>
              <div class="w-full h-0.5 rounded-full mb-1.5" style="background:rgba(255,255,255,0.12)">
                <div class="h-full rounded-full"
                     :class="(item.quantScore??50)>=70?'bg-green-400':(item.quantScore??50)>=45?'bg-yellow-400':'bg-red-400'"
                     :style="{ width:`${item.quantScore??50}%` }"></div>
              </div>
              <div class="flex items-center justify-between">
                <p class="text-[9px] font-bold" :class="item.change>=0?'text-green-300':'text-red-300'">
                  {{ item.change>=0?'+':'' }}{{ item.change }}%
                </p>
                <p class="text-[11px] font-black"
                   :class="(item.quantScore??50)>=70?'text-green-300':(item.quantScore??50)>=45?'text-yellow-300':'text-red-300'">
                  {{ item.quantScore??'—' }}
                </p>
              </div>
              <p class="text-[6.5px] mt-0.5" style="color:rgba(255,255,255,0.28)">{{ item.shares }}주</p>
            </div>
          </div>

          <!-- 롱프레스 진행 오버레이 -->
          <transition name="fade">
            <div v-if="longPressingIdx === i"
                 class="absolute inset-0 flex items-center justify-center rounded-2xl pointer-events-none"
                 style="background:rgba(255,255,255,0.08)">
              <div class="w-6 h-6 rounded-full border-2 border-white/60 border-t-transparent animate-spin"></div>
            </div>
          </transition>
        </div>

        <!-- 메뉴(뒤로가기) 버튼 -->
        <button class="absolute z-10 rounded-full flex flex-col items-center justify-center gap-0.5
                       active:scale-90 transition-all duration-150 text-white"
                :style="{
                  width:'50px', height:'50px',
                  bottom:`${BTN_BOTTOM}px`, left:'50%', transform:'translateX(-50%)',
                  background:'linear-gradient(145deg, #243347 0%, #162030 100%)',
                  boxShadow:'0 0 0 1px rgba(255,255,255,0.12), 0 6px 18px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.08)',
                }"
                @click="swipeMode ? cancelSwipe() : emit('back')">
          <component :is="swipeMode ? LucideX : LucideChevronLeft"
                     class="w-4 h-4"
                     :class="swipeMode ? 'text-yellow-300' : 'text-white/50'" />
          <span class="text-[6px] font-bold uppercase tracking-wide leading-none"
                :class="swipeMode ? 'text-yellow-300/60' : 'text-white/28'">
            {{ swipeMode ? '취소' : '메뉴' }}
          </span>
        </button>

        <!-- 자동매매 버튼 -->
        <button class="absolute z-10 flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-xl border transition-all text-white"
                :style="{
                  bottom:`${BTN_BOTTOM+2}px`, right:'14px',
                  ...(autoTradeState!=='off'
                    ? { background:'rgba(16,185,129,0.18)', borderColor:'rgba(16,185,129,0.35)' }
                    : { background:'rgba(20,32,50,0.9)', borderColor:'rgba(255,255,255,0.14)' })
                }"
                @click="emit('toggle-auto-trade')">
          <p class="text-[7px] uppercase tracking-widest font-bold leading-none"
             :class="autoTradeState!=='off'?'text-green-400':'text-white/35'">AUTO</p>
          <div class="relative w-8 h-4 rounded-full mt-0.5"
               :class="autoTradeState!=='off'?'bg-green-500/45':'bg-white/12'">
            <div class="absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all duration-200"
                 :class="autoTradeState!=='off'?'right-0.5':'left-0.5 opacity-35'"></div>
            <div v-if="autoTradeState==='analyzing'"
                 class="absolute inset-0 rounded-full bg-green-400/40 animate-ping pointer-events-none"></div>
          </div>
        </button>

      </div>
    </div><!-- /팬 스트립 -->

    <!-- 자동매매 결과 -->
    <transition name="trade-log">
      <div v-if="tradeLog"
           class="absolute z-40 left-4 right-4 rounded-xl border border-white/10 overflow-hidden text-[10px] text-white"
           style="bottom:225px;background:linear-gradient(135deg,#0a1e0e,#0d1a0a)">
        <div class="px-3 py-1.5 border-b border-white/10 flex items-center gap-1.5">
          <div class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></div>
          <p class="text-[8px] text-green-400 font-bold uppercase tracking-widest">자동매매 완료</p>
        </div>
        <div class="px-3 py-1.5 space-y-0.5">
          <div v-if="tradeLog.bought.length" class="flex gap-2">
            <span class="text-blue-400 font-black flex-shrink-0">매수</span>
            <span class="text-white/55">{{ tradeLog.bought.join(', ') }}</span>
          </div>
          <div v-if="tradeLog.sold.length" class="flex gap-2">
            <span class="text-red-400 font-black flex-shrink-0">청산</span>
            <span class="text-white/55">{{ tradeLog.sold.join(', ') }}</span>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { LucideX, LucideChevronLeft, LucideTrash2, LucideRefreshCw } from 'lucide-vue-next'
import { usePortfolioStore } from '@/stores/portfolio.js'
import BacktestMonthlyChart from '@/components/portfolio/BacktestMonthlyChart.vue'

const props = defineProps({
  portfolioGroups: { type: Array,  required: true },
  activeGroupId:   { type: Number, required: true },
  autoTradeState:  { type: String, default: 'off' },
  tradeLog:        { type: Object, default: null  },
})
const emit = defineEmits([
  'liquidate','replace','remove-group',
  'rename-group','switch-group','view-company','toggle-auto-trade','back',
])

// ── main 브랜치 포트폴리오 로직 ──────────────────
const store          = usePortfolioStore()
const portfolioError = ref(null)
const backtestOpen   = ref(true)
const rawOpen        = ref(false)

async function onTypeChange(type) {
  store.setType(type)
  portfolioError.value = null
  try   { await store.fetchPortfolio(type) }
  catch (e) { portfolioError.value = e?.response?.status === 404 ? 'not_ready' : 'error' }
}
async function onVersionChange(ver) {
  try   { await store.changeVersion(ver) }
  catch (e) { portfolioError.value = e?.response?.status === 404 ? 'not_ready' : 'error' }
}
onMounted(async () => {
  await store.initVersions().catch(() => {})
  await Promise.all([
    store.fetchPortfolio('growth').catch(e => {
      portfolioError.value = e?.response?.status === 404 ? 'not_ready' : 'error'
    }),
    store.fetchBacktest().catch(() => {}),
  ])
})

// ── 색상 헬퍼 ───────────────────────────────────
const BAR_COLORS = { A:'#1D9E75', B:'#378ADD', C:'#EF9F27', D:'#E24B4A' }
const barColor = (score) => score>=80?BAR_COLORS.A:score>=60?BAR_COLORS.B:score>=40?BAR_COLORS.C:BAR_COLORS.D
const tierStyle = (tier) => ({
  A:'background:rgba(29,158,117,0.25);color:#34d399',
  B:'background:rgba(55,138,221,0.25);color:#60a5fa',
  C:'background:rgba(239,159,39,0.25);color:#fbbf24',
  D:'background:rgba(226,75,74,0.25);color:#f87171',
}[tier] ?? 'background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.5)')
const valueClass = (val) => {
  if (!val) return 'text-white/60'
  const s = String(val)
  if (s.startsWith('-')) return 'text-red-400 font-medium'
  if (s.includes('+') || (s.endsWith('%') && !s.startsWith('-'))) return 'text-green-400 font-medium'
  return 'text-white/60'
}

// ── 팬 + 개인 포트폴리오 ────────────────────────
const fanVisible   = ref(false)
const activeGroup  = computed(() => props.portfolioGroups.find(g => g.id === props.activeGroupId))
const activeStocks = computed(() => activeGroup.value?.stocks || [])

const displayItems = computed(() => [
  { isOverview:true, id:'__overview__', color:'#c9a227' },
  ...activeStocks.value,
])

const currentIndex = ref(0)
watch(() => props.activeGroupId, () => { currentIndex.value = 0 })

const activeStock = computed(() => {
  if (currentIndex.value === 0) return null
  return activeStocks.value[currentIndex.value - 1] ?? null
})

const totalValue  = computed(() => activeStocks.value.reduce((s,p) => s + p.shares*p.currentPrice, 0))
const totalReturn = computed(() => {
  const cost = activeStocks.value.reduce((s,p) => s + p.shares*p.avgPrice, 0)
  return cost ? ((totalValue.value - cost)/cost)*100 : 0
})
const calcPL = (p) => p.shares ? (p.currentPrice - p.avgPrice)*p.shares : 0

// ── 팬 카드 포지셔닝 ────────────────────────────
const BTN_BOTTOM   = 14
const BTN_SIZE     = 50
const BTN_CENTER_Y = BTN_BOTTOM + BTN_SIZE/2   // 39

const CARD_W    = 74
const CARD_H    = 114
const FAN_RADIUS = 95   // 카드-버튼 간 약 7~10px 시각적 간격
const ANGLE_STEP = 22

const cardFanStyle = (i) => {
  const relIdx = i - currentIndex.value
  if (Math.abs(relIdx) > 3) return { display:'none' }

  const angleDeg = relIdx * ANGLE_STEP
  const rad      = (angleDeg * Math.PI) / 180
  const swipeDX  = isSwipeDragging(i) ? dragX.value : 0
  const offsetX  = FAN_RADIUS * Math.sin(rad) + swipeDX
  const offsetY  = FAN_RADIUS * Math.cos(rad)

  const cardBottom = (BTN_CENTER_Y + offsetY) - CARD_H/2
  const cardLeft   = offsetX - CARD_W/2

  const isActive      = relIdx === 0
  const isLongPress   = longPressingIdx.value === i
  // 롱프레스 중 살짝 커짐 → 스와이프 모드 진입시 더 커짐
  const scale = isLongPress  ? 1.18
              : (swipeMode.value && isActive) ? 1.18
              : isActive     ? 1.10
              : Math.max(0.80, 1 - Math.abs(relIdx)*0.09)
  // 스와이프 모드에서 비활성 카드 어둡게
  const opacity = (swipeMode.value && !isActive) ? 0.18
                : isActive ? 1
                : Math.max(0.35, 1 - Math.abs(relIdx)*0.18)
  const zIndex   = isActive ? 25 : Math.max(1, 20 - Math.abs(relIdx)*2)
  const rotate   = angleDeg*0.28 + (isSwipeDragging(i) ? swipeDX*0.06 : 0)
  const col      = displayItems.value[i]?.color ?? '#888888'

  return {
    position:'absolute', width:`${CARD_W}px`, height:`${CARD_H}px`,
    bottom:`${cardBottom}px`, left:`calc(50% + ${cardLeft}px)`,
    transform:`scale(${scale}) rotate(${rotate}deg)`,
    transformOrigin:'center center',
    opacity, zIndex,
    transition: (isSwipeDragging(i) && isDragging.value)
      ? 'opacity 0.1s, transform 0.1s'
      : isLongPress ? 'transform 0.2s ease' : 'all 0.38s cubic-bezier(0.22,1,0.36,1)',
    background:`linear-gradient(145deg, ${col}${isActive?'ee':'99'} 0%, ${col}${isActive?'55':'30'} 100%)`,
    boxShadow: isLongPress ? `0 16px 40px ${col}66, 0 0 0 2px rgba(255,255,255,0.3)` :
               isActive ? `0 8px 26px ${col}55, 0 0 0 1px rgba(255,255,255,0.18)` : 'none',
    border: isActive ? '1px solid rgba(255,255,255,0.22)' : '1px solid rgba(255,255,255,0.08)',
    cursor:'pointer', borderRadius:'16px', overflow:'hidden',
    pointerEvents: (swipeMode.value && !isActive) || Math.abs(relIdx)>3 ? 'none' : 'auto',
  }
}

// ── 카드 단순 클릭 ──────────────────────────────
const onCardClick = (i) => {
  if (swipeMode.value || longPressingIdx.value !== null) return
  if (i !== currentIndex.value) { currentIndex.value = i; return }
  const item = displayItems.value[i]
  if (item && !item.isOverview) emit('view-company', item.ticker)
}

// ── 롱프레스 + 스와이프 ─────────────────────────
const swipeMode       = ref(false)
const dragX           = ref(0)
const isDragging      = ref(false)
const startX          = ref(0)
const longPressingIdx = ref(null)  // 롱프레스 진행 중인 카드 인덱스
const THRESHOLD       = 80
const LONG_PRESS_MS   = 480

let longPressTimer = null

const isSwipeDragging = (i) => swipeMode.value && i === currentIndex.value

const cancelSwipe = () => {
  clearLongPress()
  swipeMode.value  = false
  dragX.value      = 0
  isDragging.value = false
  fanVisible.value = true
}

const clearLongPress = () => {
  if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null }
  longPressingIdx.value = null
}

const getClientX = (e) => e.type?.includes('touch') ? e.touches[0]?.clientX : e.clientX

const onCardDown = (i, e) => {
  // 스와이프 모드 중이면 드래그 시작
  if (swipeMode.value) {
    if (i !== currentIndex.value) return
    isDragging.value = true
    startX.value     = getClientX(e)
    return
  }
  // 비활성 카드 클릭은 focusCard만
  if (i !== currentIndex.value) return
  // 오버뷰 카드는 롱프레스 없음
  if (displayItems.value[i]?.isOverview) return

  // 롱프레스 시작
  startX.value          = getClientX(e)
  longPressingIdx.value = i
  longPressTimer = setTimeout(() => {
    longPressingIdx.value = null
    swipeMode.value   = true
    isDragging.value  = true
    dragX.value       = 0
    // 팬이 마우스아웃으로 닫히지 않도록
    fanVisible.value  = true
  }, LONG_PRESS_MS)
}

const onCardMove = (i, e) => {
  const x = getClientX(e)
  // 롱프레스 중 조금이라도 움직이면 취소
  if (longPressingIdx.value !== null) {
    if (Math.abs(x - startX.value) > 6) clearLongPress()
    return
  }
  if (!swipeMode.value || !isDragging.value || i !== currentIndex.value) return
  dragX.value = x - startX.value
}

const onCardUp = (i) => {
  clearLongPress()
  if (!isDragging.value || !swipeMode.value || i !== currentIndex.value) return
  endDrag()
}

const onCardLeave = (i) => {
  if (longPressingIdx.value === i) clearLongPress()
  if (isDragging.value && i === currentIndex.value) endDrag()
}

const endDrag = () => {
  if (!isDragging.value) return
  isDragging.value = false
  const x          = dragX.value
  const stockIndex = currentIndex.value - 1

  if (x > THRESHOLD) {
    dragX.value = 500
    setTimeout(() => { emit('replace', stockIndex); swipeMode.value=false; dragX.value=0 }, 280)
  } else if (x < -THRESHOLD) {
    dragX.value = -500
    setTimeout(() => {
      emit('liquidate', stockIndex)
      if (currentIndex.value > 1 && currentIndex.value >= displayItems.value.length-1) currentIndex.value--
      swipeMode.value=false; dragX.value=0
    }, 280)
  } else {
    dragX.value = 0
  }
}

// 컴포넌트 해제 시 타이머 정리
onUnmounted(() => clearLongPress())
</script>

<style scoped>
.page-switch-enter-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.page-switch-leave-active { transition: opacity 0.15s ease; }
.page-switch-enter-from   { opacity: 0; transform: translateY(10px); }
.page-switch-leave-to     { opacity: 0; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,  .fade-leave-to      { opacity: 0; }

.trade-log-enter-active { transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.22,1,0.36,1); }
.trade-log-leave-active { transition: opacity 0.18s ease; }
.trade-log-enter-from, .trade-log-leave-to { opacity: 0; transform: translateY(8px); }
</style>
