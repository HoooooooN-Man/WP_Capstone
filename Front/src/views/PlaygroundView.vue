<!--
  PlaygroundView.vue
  ==================
  Tier 2.5 (차별화 §2.4 / 캡스톤 §5.5) — 사용자가 정책 슬라이더 2개로 조작.

  슬라이더:
    - tier_a_cutoff ∈ {85, 88, 90, 93, 95, 97}
    - top_k         ∈ {10, 20, 50}

  18 조합의 Sharpe·cumulative return·MDD·alpha 가 사전계산돼 grid JSON 으로 박제.
  본 페이지는 lookup + 시각화만 (실시간 백테스트 X — 캡스톤 §5.5 명시).

  포지셔닝: "사용자가 모델을 *만질 수 있는* 도구" — 다른 서비스에 거의 없는 차별화.
-->
<template>
  <main class="playground">
    <header class="hero">
      <h1>백테스트 Playground</h1>
      <p class="subhead">
        Tier A 컷오프와 포트폴리오 종목 수를 조작하며 holdout 기간(2026 Q1·Q2)의
        성과 변화를 즉시 확인. 18 조합은 사전 계산되어 박제되었다.
      </p>
    </header>

    <section v-if="loading" class="placeholder">로드 중…</section>
    <section v-else-if="error" class="placeholder error">로드 실패: {{ error }}</section>

    <template v-else-if="grid">
      <section class="card controls">
        <div class="ctrl">
          <label>Tier A 백분위 컷오프</label>
          <div class="seg">
            <button
              v-for="v in grid.axis_cutoff"
              :key="`cut-${v}`"
              type="button"
              :class="{ active: chosenCutoff === v }"
              @click="chosenCutoff = v"
            >{{ v }}</button>
          </div>
          <p class="hint">
            높을수록 *덜 자주* 매수 신호 — 보수적 전략.
          </p>
        </div>
        <div class="ctrl">
          <label>포트폴리오 종목 수 한도 (top_k)</label>
          <div class="seg">
            <button
              v-for="v in grid.axis_top_k"
              :key="`top-${v}`"
              type="button"
              :class="{ active: chosenTopK === v }"
              @click="chosenTopK = v"
            >{{ v }}</button>
          </div>
          <p class="hint">
            적을수록 *집중* 투자, 많을수록 *분산* (변동성 안정).
          </p>
        </div>
      </section>

      <section v-if="current" class="card result">
        <h2>선택된 조합 결과</h2>
        <div class="kpi-row">
          <div class="kpi" :class="sharpeClass">
            <div class="lbl">Sharpe (annualized)</div>
            <div class="val">{{ fmtNum(current.sharpe, 3) }}</div>
          </div>
          <div class="kpi" :class="retClass">
            <div class="lbl">Cumulative Return</div>
            <div class="val">{{ fmtPct(current.cumulative_return) }}</div>
          </div>
          <div class="kpi">
            <div class="lbl">Max Drawdown</div>
            <div class="val">{{ fmtPct(current.max_drawdown) }}</div>
          </div>
          <div class="kpi" :class="alphaClass">
            <div class="lbl">α vs KOSPI</div>
            <div class="val">{{ fmtPct(current.alpha_cum) }}</div>
          </div>
          <div class="kpi muted">
            <div class="lbl">기간당 평균 종목</div>
            <div class="val">{{ current.avg_picks?.toFixed(1) ?? '—' }}</div>
          </div>
        </div>
        <p class="meta">
          n_periods = {{ current.n_periods }} (non-overlapping 20거래일 리밸런싱)
        </p>
        <p v-if="current.note" class="warn">⚠ {{ current.note }}</p>
      </section>

      <section v-if="grid" class="card heatmap-card">
        <h2>전체 grid 히트맵 (Sharpe)</h2>
        <p class="hint">색이 짙을수록 Sharpe 높음. 클릭해서 조합 선택.</p>
        <div class="heatmap">
          <div></div>
          <div
            v-for="k in grid.axis_top_k"
            :key="`hh-${k}`"
            class="hm-col-label"
          >top_k={{ k }}</div>

          <template v-for="c in grid.axis_cutoff" :key="`row-${c}`">
            <div class="hm-row-label">{{ c }}</div>
            <div
              v-for="k in grid.axis_top_k"
              :key="`cell-${c}-${k}`"
              class="hm-cell"
              :class="{ active: chosenCutoff === c && chosenTopK === k }"
              :style="{ background: cellColor(c, k) }"
              :title="`cutoff=${c}, top_k=${k}: Sharpe=${cellSharpe(c, k)?.toFixed(3) ?? '—'}`"
              @click="chosenCutoff = c; chosenTopK = k"
            >{{ cellSharpe(c, k)?.toFixed(2) ?? '—' }}</div>
          </template>
        </div>
      </section>

      <section class="card note-card">
        <p class="caveat">
          ⚠ <strong>학술적 한계 명시</strong>:
          본 grid 는 holdout 4개월 기간으로 n_periods = 3 의 작은 표본에서 산출됨.
          PSR (Sharpe&gt;0 의 진실 가능성) 은 0.5 — *통계적 유의성은 약함*.
          본 페이지의 1차 목적은 *사용자가 모델을 만질 수 있다*는 경험을 제공하는 것.
        </p>
        <p class="meta">
          박제 시각: {{ formatDate(grid.generated_at) }} · model {{ grid.model_version }}
        </p>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '@/api/axios'

interface Combo {
  cutoff: number
  top_k: number
  n_periods: number
  avg_picks: number | null
  sharpe: number | null
  cumulative_return: number | null
  benchmark_return: number | null
  alpha_cum: number | null
  max_drawdown: number | null
  psr_threshold_0: number | null
  note: string | null
}

interface Grid {
  available: boolean
  message?: string
  generated_at?: string
  model_version?: string
  axis_cutoff?: number[]
  axis_top_k?: number[]
  combinations?: Combo[]
}

const grid = ref<Grid | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const chosenCutoff = ref<number>(93)
const chosenTopK   = ref<number>(20)

const current = computed(() => {
  if (!grid.value?.combinations) return null
  return grid.value.combinations.find(
    (c) => c.cutoff === chosenCutoff.value && c.top_k === chosenTopK.value,
  ) ?? null
})

const sharpeClass = computed(() => _sharpeBucket(current.value?.sharpe ?? null))
const retClass    = computed(() => _signBucket(current.value?.cumulative_return ?? null))
const alphaClass  = computed(() => _signBucket(current.value?.alpha_cum ?? null))

function _sharpeBucket(s: number | null): string {
  if (s === null) return ''
  if (s > 1.0) return 'good'
  if (s > 0)   return 'warn'
  return 'bad'
}
function _signBucket(v: number | null): string {
  if (v === null) return ''
  return v >= 0 ? 'good' : 'bad'
}

function fmtNum(v: number | null | undefined, d = 2): string {
  return v == null ? '—' : v.toFixed(d)
}
function fmtPct(v: number | null | undefined): string {
  return v == null ? '—' : `${(v * 100).toFixed(2)}%`
}
function formatDate(s?: string): string {
  if (!s) return ''
  try { return new Date(s).toLocaleString('ko-KR', { hour12: false }) }
  catch { return s }
}

function cellSharpe(c: number, k: number): number | null {
  return grid.value?.combinations?.find(
    (x) => x.cutoff === c && x.top_k === k,
  )?.sharpe ?? null
}
function cellColor(c: number, k: number): string {
  const s = cellSharpe(c, k)
  if (s === null) return '#f3f4f6'
  // -1 ~ +2 범위 매핑.
  const norm = Math.max(-1, Math.min(2, s))
  if (norm >= 0) {
    // 녹색: 0=연 → 2=짙
    const a = norm / 2
    return `rgba(22, 163, 74, ${0.15 + a * 0.55})`
  }
  // 빨강: 0=연 → -1=짙
  const a = -norm
  return `rgba(220, 38, 38, ${0.15 + a * 0.55})`
}

onMounted(async () => {
  try {
    const r = await api.get<Grid>('/playground/grid')
    grid.value = r.data
    if (!r.data.available) {
      error.value = r.data.message ?? '박제된 grid 없음'
    }
  } catch (e: any) {
    console.error('[Playground] fetch failed', e)
    error.value = e?.message ?? String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.playground {
  max-width: 960px;
  margin: 24px auto 64px;
  padding: 0 16px;
  color: #1f2937;
}
.hero h1 { font-size: 22px; margin: 0 0 4px; }
.subhead { color: #4b5563; font-size: 13px; line-height: 1.6; margin: 0 0 16px; }

.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px 18px;
  margin-bottom: 16px;
}
.card h2 { font-size: 16px; margin: 0 0 8px; }

.controls {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
.ctrl label { font-size: 13px; font-weight: 600; color: #374151; }
.seg {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.seg button {
  padding: 6px 12px;
  font-size: 13px;
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-variant-numeric: tabular-nums;
}
.seg button:hover { background: #f9fafb; }
.seg button.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
  font-weight: 600;
}
.hint { font-size: 11px; color: #6b7280; margin: 6px 0 0; }

.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}
.kpi {
  background: #f9fafb;
  border-left: 3px solid #6b7280;
  padding: 8px 10px;
  border-radius: 4px;
}
.kpi.good { border-left-color: #16a34a; }
.kpi.warn { border-left-color: #f59e0b; }
.kpi.bad  { border-left-color: #dc2626; }
.kpi.muted { border-left-color: #d1d5db; }
.kpi .lbl { font-size: 10px; color: #6b7280; text-transform: uppercase; }
.kpi .val { font-size: 16px; font-weight: 700; color: #111827; font-variant-numeric: tabular-nums; margin-top: 3px; }

.meta { font-size: 11px; color: #9ca3af; margin: 10px 0 0; }
.warn { font-size: 12px; color: #b45309; margin: 8px 0 0; }

.heatmap {
  display: grid;
  grid-template-columns: 60px repeat(3, 1fr);
  gap: 4px;
  font-size: 12px;
  margin-top: 10px;
}
.hm-col-label, .hm-row-label {
  font-weight: 600;
  color: #4b5563;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hm-cell {
  padding: 14px 8px;
  border-radius: 4px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  cursor: pointer;
  border: 2px solid transparent;
  transition: transform 0.1s;
}
.hm-cell:hover { transform: scale(1.04); }
.hm-cell.active { border-color: #2563eb; outline: 2px solid #93c5fd; }

.note-card { background: #fffbeb; border-color: #f59e0b; }
.caveat { font-size: 12px; line-height: 1.6; margin: 0 0 6px; color: #78350f; }

.placeholder { padding: 40px; text-align: center; color: #6b7280; }
.placeholder.error { background: #fef2f2; color: #b91c1c; border-radius: 8px; }
</style>
