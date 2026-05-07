<!--
  TransparencyView.vue
  ====================
  Tier 1.5 (PRD §3.5 / 차별화 §2.2) — 박제된 holdout·Model Card 정직성 페이지.

  소비 데이터:
    - GET /transparency/holdout/summary  → ECE/Brier KPI
    - GET /transparency/holdout          → ablation 표 + 운용 KPI
    - GET /transparency/model-card       → 마크다운 원문

  마크다운 렌더는 외부 lib 추가를 피하고 인하우스 미니 파서 사용
  (h1·h2·표·리스트·인용 정도만 처리. 학술 보고서 톤 유지).
-->
<template>
  <main class="transparency">
    <header class="hero">
      <h1>모델 정직성 — Transparency</h1>
      <p class="subhead">
        v9 모델의 holdout 박제 성과·Model Card·앙상블 ablation 결과를
        그대로 공개합니다. 본 페이지의 수치는 우리가 *모델 자체의 진실*로
        남긴 것이며, 본 결과를 보고 모델을 재선택하지 않습니다.
      </p>
    </header>

    <section v-if="summary && summary.available" class="kpi-strip">
      <div class="kpi" :class="eceClass">
        <div class="lbl">ECE (10-bin)</div>
        <div class="val">{{ summary.ece?.toFixed(4) }}</div>
        <div class="hint">{{ eceHint }}</div>
      </div>
      <div class="kpi">
        <div class="lbl">Brier Score</div>
        <div class="val">{{ summary.brier?.toFixed(4) }}</div>
        <div class="hint">낮을수록 좋음</div>
      </div>
      <div class="kpi">
        <div class="lbl">봉인 시각</div>
        <div class="val sealed">{{ formatDate(summary.sealed_at) }}</div>
        <div class="hint">박제 직후 수정 금지</div>
      </div>
    </section>
    <section v-else-if="summary && !summary.available" class="placeholder">
      <p>{{ summary.message ?? 'Holdout 결과가 박제되어 있지 않습니다.' }}</p>
    </section>

    <section v-if="ablation" class="card">
      <h2>앙상블 ablation — 단일 LGBM vs 메타 스태킹</h2>
      <p class="meta-line">표본 {{ ablation.n_observations.toLocaleString() }} 행 · 분류 비교</p>
      <table>
        <thead>
          <tr>
            <th>모델</th>
            <th>AUC</th>
            <th>ECE</th>
            <th>Brier</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in ablation.candidates" :key="c.name"
              :class="{ highlight: c.name === 'ensemble_meta_isotonic' }">
            <td>{{ humanModelName(c.name) }}</td>
            <td>{{ c.auc.toFixed(4) }}</td>
            <td>{{ c.ece.toFixed(4) }}</td>
            <td>{{ c.brier.toFixed(4) }}</td>
          </tr>
        </tbody>
      </table>
      <div class="ablation-delta">
        <strong>앙상블 − 단일 LGBM</strong>:
        ΔAUC <span :class="deltaClass(ablation.ensemble_vs_lgbm.delta_auc)">
          {{ ablation.ensemble_vs_lgbm.delta_auc >= 0 ? '+' : '' }}{{ ablation.ensemble_vs_lgbm.delta_auc.toFixed(4) }}
        </span>,
        ΔECE <span :class="deltaClass(-ablation.ensemble_vs_lgbm.delta_ece)">
          {{ ablation.ensemble_vs_lgbm.delta_ece >= 0 ? '+' : '' }}{{ ablation.ensemble_vs_lgbm.delta_ece.toFixed(4) }}
        </span>,
        ΔBrier <span :class="deltaClass(-ablation.ensemble_vs_lgbm.delta_brier)">
          {{ ablation.ensemble_vs_lgbm.delta_brier >= 0 ? '+' : '' }}{{ ablation.ensemble_vs_lgbm.delta_brier.toFixed(4) }}
        </span>
      </div>
      <p class="interpretation">{{ ablation.ensemble_vs_lgbm.interpretation }}</p>
    </section>

    <section v-if="modelCardHtml" class="card">
      <h2>Model Card</h2>
      <article class="markdown-body" v-html="modelCardHtml" />
      <p class="caption">Mitchell et al. (2018) 표준의 Model Card 박제본.</p>
    </section>

    <section v-if="error" class="error">
      <p>로드 실패: {{ error }}</p>
    </section>

    <footer class="page-footer">
      <p>
        본 페이지의 모든 수치는
        <code>_archive/holdout_2026_q1_q2/</code>
        에 박제되어 있습니다. 캡스톤 발표·보고서·외부 인용은 본 페이지의 결과를 그대로 사용하세요.
      </p>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  fetchHoldoutFull,
  fetchHoldoutSummary,
  fetchModelCard,
  type HoldoutFull,
  type HoldoutSummary,
} from '@/api/transparency'

const summary = ref<HoldoutSummary | null>(null)
const full    = ref<HoldoutFull | null>(null)
const cardMd  = ref<string | null>(null)
const error   = ref<string | null>(null)

const ablation = computed(() => full.value?.ablation ?? null)

const eceClass = computed(() => {
  const e = summary.value?.ece
  if (e == null) return ''
  if (e < 0.05) return 'good'
  if (e < 0.10) return 'warn'
  return 'bad'
})

const eceHint = computed(() => {
  const e = summary.value?.ece
  if (e == null) return ''
  if (e < 0.05) return '< 0.05 양호'
  if (e < 0.10) return '0.05–0.10 주의'
  return '≥ 0.10 재캘리 검토'
})

function deltaClass(v: number): string {
  if (Math.abs(v) < 0.005) return 'neutral'
  return v >= 0 ? 'good' : 'bad'
}

function formatDate(s: string | null | undefined): string {
  if (!s) return '—'
  try {
    return new Date(s).toLocaleString('ko-KR', { hour12: false })
  } catch {
    return s
  }
}

function humanModelName(n: string): string {
  return ({
    lgbm_alone:               'LightGBM 단독',
    xgb_alone:                'XGBoost 단독',
    cat_alone:                'CatBoost 단독',
    ensemble_simple_mean:     '단순 평균 앙상블',
    ensemble_meta_isotonic:   '메타+Isotonic (현행 v9)',
  } as Record<string, string>)[n] ?? n
}

// ── 미니 마크다운 → HTML (외부 lib 회피) ───────────────────────────────────
// h1·h2·h3, 굵게/기울임, 리스트, 표, 인용, 단락만 처리.
function renderMarkdown(md: string): string {
  const escape = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  const lines = md.split(/\r?\n/)
  const out: string[] = []
  let inTable = false
  let tableHeader = false
  let inUl = false
  let inBlockquote = false

  function closeOpen() {
    if (inUl) { out.push('</ul>'); inUl = false }
    if (inBlockquote) { out.push('</blockquote>'); inBlockquote = false }
    if (inTable) { out.push('</tbody></table>'); inTable = false; tableHeader = false }
  }

  function inline(s: string): string {
    return escape(s)
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  }

  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i]
    const stripped = ln.trim()

    if (stripped === '') { closeOpen(); continue }
    if (stripped === '---') { closeOpen(); out.push('<hr/>'); continue }

    // 표.
    if (stripped.startsWith('|') && stripped.endsWith('|')) {
      const cells = stripped.slice(1, -1).split('|').map((c) => c.trim())
      // 구분 행 ":---" 형태
      if (cells.every((c) => /^:?-+:?$/.test(c))) { tableHeader = true; continue }
      if (!inTable) {
        closeOpen()
        out.push('<table><thead><tr>')
        for (const c of cells) out.push(`<th>${inline(c)}</th>`)
        out.push('</tr></thead><tbody>')
        inTable = true
      } else if (tableHeader) {
        // 첫 데이터 행 시작 — header 토글 클리어.
        tableHeader = false
        out.push('<tr>')
        for (const c of cells) out.push(`<td>${inline(c)}</td>`)
        out.push('</tr>')
      } else {
        out.push('<tr>')
        for (const c of cells) out.push(`<td>${inline(c)}</td>`)
        out.push('</tr>')
      }
      continue
    } else if (inTable) {
      out.push('</tbody></table>'); inTable = false; tableHeader = false
    }

    // 헤더.
    const h = stripped.match(/^(#{1,4})\s+(.*)$/)
    if (h) {
      closeOpen()
      const lvl = h[1].length
      out.push(`<h${lvl + 0}>${inline(h[2])}</h${lvl + 0}>`)
      continue
    }

    // 인용.
    if (stripped.startsWith('> ')) {
      if (!inBlockquote) { closeOpen(); out.push('<blockquote>'); inBlockquote = true }
      out.push(`<p>${inline(stripped.slice(2))}</p>`)
      continue
    }

    // 순서 없는 리스트.
    if (stripped.startsWith('- ')) {
      if (!inUl) { closeOpen(); out.push('<ul>'); inUl = true }
      out.push(`<li>${inline(stripped.slice(2))}</li>`)
      continue
    }

    // 일반 단락.
    closeOpen()
    out.push(`<p>${inline(stripped)}</p>`)
  }
  closeOpen()
  return out.join('\n')
}

const modelCardHtml = computed(() => (cardMd.value ? renderMarkdown(cardMd.value) : ''))

onMounted(async () => {
  try {
    const [s, f, m] = await Promise.all([
      fetchHoldoutSummary(),
      fetchHoldoutFull(),
      fetchModelCard(),
    ])
    summary.value = s
    full.value    = f
    cardMd.value  = m.markdown
  } catch (e: any) {
    console.error('[Transparency] load failed', e)
    error.value = e?.message ?? String(e)
  }
})
</script>

<style scoped>
.transparency {
  max-width: 960px;
  margin: 24px auto 64px;
  padding: 0 16px;
  color: #1f2937;
  font-family: inherit;
}

.hero { margin-bottom: 24px; }
.hero h1 { font-size: 24px; margin: 0 0 6px; }
.subhead { color: #4b5563; font-size: 14px; line-height: 1.6; margin: 0; }

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.kpi {
  background: #f9fafb;
  border-left: 3px solid #6b7280;
  padding: 12px 14px;
  border-radius: 4px;
}
.kpi.good { border-left-color: #16a34a; }
.kpi.warn { border-left-color: #f59e0b; }
.kpi.bad  { border-left-color: #dc2626; }
.kpi .lbl { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.04em; }
.kpi .val { font-size: 20px; font-weight: 700; color: #111827; font-variant-numeric: tabular-nums; margin: 2px 0; }
.kpi .val.sealed { font-size: 13px; }
.kpi .hint { font-size: 11px; color: #9ca3af; }

.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 18px 20px;
  margin-bottom: 20px;
}
.card h2 { font-size: 17px; margin: 0 0 8px; }
.meta-line { font-size: 12px; color: #6b7280; margin: 0 0 12px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 6px 10px; border-bottom: 1px solid #e5e7eb; text-align: right; }
th:first-child, td:first-child { text-align: left; }
th { background: #f9fafb; font-weight: 600; color: #374151; }
tr.highlight td { background: #eff6ff; font-weight: 600; }

.ablation-delta { margin: 14px 0 6px; font-size: 13px; color: #1f2937; }
.ablation-delta .good    { color: #16a34a; font-weight: 600; }
.ablation-delta .bad     { color: #dc2626; font-weight: 600; }
.ablation-delta .neutral { color: #6b7280; font-weight: 600; }

.interpretation {
  margin: 6px 0 0;
  font-size: 13px;
  color: #1f2937;
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  padding: 8px 10px;
  border-radius: 4px;
}

.markdown-body :deep(h1) { font-size: 18px; margin: 16px 0 8px; }
.markdown-body :deep(h2) { font-size: 16px; margin: 18px 0 8px; padding-bottom: 4px; border-bottom: 1px solid #e5e7eb; }
.markdown-body :deep(h3) { font-size: 14px; margin: 12px 0 6px; }
.markdown-body :deep(p)  { font-size: 13px; line-height: 1.6; margin: 6px 0; }
.markdown-body :deep(ul) { margin: 6px 0 8px 18px; font-size: 13px; line-height: 1.6; }
.markdown-body :deep(table) { font-size: 12px; margin: 10px 0; }
.markdown-body :deep(blockquote) { border-left: 3px solid #d1d5db; margin: 8px 0; padding: 4px 12px; color: #4b5563; }
.markdown-body :deep(code) { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 12px; }
.markdown-body :deep(a) { color: #2563eb; }

.caption { margin-top: 10px; font-size: 11px; color: #9ca3af; font-style: italic; }
.placeholder, .error {
  padding: 14px;
  border-radius: 6px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 13px;
}

.page-footer {
  margin-top: 28px;
  font-size: 11px;
  color: #6b7280;
  border-top: 1px solid #e5e7eb;
  padding-top: 12px;
}
.page-footer code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; }
</style>
