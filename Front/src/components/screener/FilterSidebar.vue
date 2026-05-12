<script setup lang="ts">
// UX W6A — FilterSidebar 다듬기. 토큰 적용, native select·input 유지.
// PrimeVue Select 전면 도입은 차차차차기 후보 (변경 영향 큼).
// @ts-nocheck — 캡스톤 시기 store .js (점진적 마이그레이션).

import { ref } from 'vue'
// @ts-ignore
import { useScreenerStore } from '@/stores/screener'

const props = defineProps<{ filters: Record<string, any> }>()
const emit  = defineEmits<{
  (e: 'filter-change', payload: { key: string; value: any }): void
  (e: 'reset-financial'): void
  (e: 'reset-all'): void
}>()
const store = useScreenerStore()

const financialOpen = ref(true)
const presetName    = ref('')
const presets       = ref<string[]>(store.getSavedPresets())

const SECTORS = [
  'IT', '헬스케어', '금융', '경기소비재', '필수소비재',
  '산업재', '에너지', '소재', '유틸리티', '부동산', '커뮤니케이션서비스',
]
const SORT_OPTIONS = [
  { value: 'composite_score',  label: '복합점수' },
  { value: 'score',            label: 'ML점수' },
  { value: 'finance_score',    label: '재무점수' },
  { value: 'roe',              label: 'ROE' },
  { value: 'per',              label: 'PER' },
  { value: 'pbr',              label: 'PBR' },
  { value: 'rev_growth_yoy',   label: '매출성장률' },
]

const FINANCIAL_FIELDS = [
  { key: 'max_per',           label: '최대 PER',          placeholder: '제한없음' },
  { key: 'max_pbr',           label: '최대 PBR',          placeholder: '제한없음' },
  { key: 'min_roe',           label: '최소 ROE (%)',      placeholder: '제한없음' },
  { key: 'max_debt_ratio',    label: '최대 부채비율 (%)', placeholder: '제한없음' },
  { key: 'min_op_margin',     label: '최소 영업이익률 (%)', placeholder: '제한없음' },
  { key: 'min_rev_growth',    label: '최소 매출성장률 (%)', placeholder: '제한없음' },
  { key: 'min_finance_score', label: '최소 재무점수',     placeholder: '제한없음' },
]

function change(key: string, value: any) { emit('filter-change', { key, value }) }

function savePreset() {
  if (!presetName.value.trim()) return
  store.savePreset(presetName.value.trim())
  presets.value = store.getSavedPresets()
  presetName.value = ''
}
function loadPreset(name: string) {
  store.loadPreset(name)
  emit('filter-change', { key: '_reload', value: null })
}
function deletePreset(name: string) {
  store.deletePreset(name)
  presets.value = store.getSavedPresets()
}
</script>

<template>
  <aside class="filter-sidebar">
    <section class="filter-sidebar__section">
      <h3 class="filter-sidebar__heading">ML 조건</h3>

      <div class="field">
        <label>모델 버전</label>
        <select
          :value="filters.model_version"
          @change="change('model_version', ($event.target as HTMLSelectElement).value)"
        >
          <option value="latest">최신 버전</option>
        </select>
      </div>

      <div class="field">
        <div class="field__head">
          <label>최소 ML 점수</label>
          <span class="field__value">{{ filters.min_score }}점</span>
        </div>
        <input
          type="range" min="0" max="100" step="1"
          :value="filters.min_score"
          class="field__range"
          @input="change('min_score', Number(($event.target as HTMLInputElement).value))"
        />
      </div>

      <div class="field">
        <label>Tier</label>
        <select
          :value="filters.tier ?? ''"
          @change="change('tier', ($event.target as HTMLSelectElement).value || null)"
        >
          <option value="">전체</option>
          <option v-for="t in ['A','B','C','D']" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>

      <div class="field">
        <label>섹터</label>
        <select
          :value="filters.sector ?? ''"
          @change="change('sector', ($event.target as HTMLSelectElement).value || null)"
        >
          <option value="">전체</option>
          <option v-for="s in SECTORS" :key="s" :value="s">{{ s }}</option>
        </select>
      </div>
    </section>

    <hr class="filter-sidebar__divider" />

    <section class="filter-sidebar__section">
      <button
        class="filter-sidebar__collapse"
        :aria-expanded="financialOpen"
        @click="financialOpen = !financialOpen"
      >
        <span>재무 조건</span>
        <i :class="['pi', financialOpen ? 'pi-chevron-up' : 'pi-chevron-down']" aria-hidden="true" />
      </button>

      <template v-if="financialOpen">
        <div v-for="f in FINANCIAL_FIELDS" :key="f.key" class="field">
          <label>{{ f.label }}</label>
          <input
            type="number"
            :value="filters[f.key] ?? ''"
            :placeholder="f.placeholder"
            @blur="change(f.key, ($event.target as HTMLInputElement).value ? Number(($event.target as HTMLInputElement).value) : null)"
          />
        </div>
        <button class="filter-sidebar__reset-link" @click="emit('reset-financial')">
          재무 조건만 초기화
        </button>
      </template>
    </section>

    <hr class="filter-sidebar__divider" />

    <section class="filter-sidebar__section">
      <h3 class="filter-sidebar__heading">정렬 & 결과수</h3>
      <div class="field">
        <label>정렬 기준</label>
        <select
          :value="filters.sort_by"
          @change="change('sort_by', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </div>
      <div class="field">
        <label>결과 수</label>
        <select
          :value="filters.limit"
          @change="change('limit', Number(($event.target as HTMLSelectElement).value))"
        >
          <option :value="50">50</option>
          <option :value="100">100</option>
          <option :value="200">200</option>
        </select>
      </div>
    </section>

    <hr class="filter-sidebar__divider" />

    <section class="filter-sidebar__section">
      <h3 class="filter-sidebar__heading">프리셋</h3>
      <div class="filter-sidebar__preset-row">
        <input
          v-model="presetName"
          type="text"
          placeholder="프리셋 이름"
          @keydown.enter="savePreset"
        />
        <button class="filter-sidebar__preset-save" @click="savePreset">저장</button>
      </div>
      <div v-if="presets.length" class="filter-sidebar__preset-list">
        <div v-for="name in presets" :key="name" class="filter-sidebar__preset-item">
          <button class="filter-sidebar__preset-load" @click="loadPreset(name)">
            {{ name }}
          </button>
          <button
            class="filter-sidebar__preset-del"
            :aria-label="`프리셋 ${name} 삭제`"
            @click="deletePreset(name)"
          ><i class="pi pi-times" aria-hidden="true" /></button>
        </div>
      </div>
      <p v-else class="filter-sidebar__empty">저장된 프리셋 없음</p>
    </section>

    <button class="filter-sidebar__reset-all" @click="emit('reset-all')">
      전체 조건 초기화
    </button>
  </aside>
</template>

<style scoped>
.filter-sidebar {
  position: sticky; top: var(--space-6);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex; flex-direction: column; gap: var(--space-5);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--text-primary);
  max-height: calc(100vh - var(--space-12));
  overflow-y: auto;
}

.filter-sidebar__section {
  display: flex; flex-direction: column; gap: var(--space-3);
}
.filter-sidebar__heading {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.filter-sidebar__divider {
  border: 0; height: 1px;
  background: var(--border-subtle); margin: 0;
}
.filter-sidebar__collapse {
  display: flex; justify-content: space-between; align-items: center;
  background: transparent; border: 0; padding: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  cursor: pointer;
  font-family: inherit;
}
.filter-sidebar__collapse i { color: var(--text-tertiary); font-size: var(--text-sm); }

.field {
  display: flex; flex-direction: column; gap: var(--space-1);
}
.field__head { display: flex; justify-content: space-between; }
.field__value { font-size: var(--text-xs); font-weight: var(--font-medium); color: var(--text-primary); }
.field label {
  font-size: var(--text-xs); color: var(--text-secondary);
}
.field select,
.field input[type="text"],
.field input[type="number"],
.filter-sidebar__preset-row input {
  width: 100%;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-family: inherit;
  background: var(--surface-card);
  color: var(--text-primary);
}
.field select:focus,
.field input:focus,
.filter-sidebar__preset-row input:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: var(--shadow-focus);
}
.field__range {
  width: 100%;
  accent-color: var(--color-primary-600);
}

.filter-sidebar__reset-link {
  background: transparent; border: 0; padding: 0;
  font-size: var(--text-xs);
  color: var(--color-danger);
  cursor: pointer; text-align: left;
  font-family: inherit;
}
.filter-sidebar__reset-link:hover { text-decoration: underline; }

.filter-sidebar__preset-row {
  display: flex; gap: var(--space-1);
}
.filter-sidebar__preset-row input { flex: 1; }
.filter-sidebar__preset-save {
  padding: var(--space-1) var(--space-3);
  background: var(--color-primary-600);
  color: var(--text-inverse);
  border: 0; border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-family: inherit;
  cursor: pointer;
}
.filter-sidebar__preset-save:hover { background: var(--color-primary-700); }
.filter-sidebar__preset-list {
  display: flex; flex-direction: column; gap: var(--space-1);
}
.filter-sidebar__preset-item {
  display: flex; justify-content: space-between; align-items: center;
  font-size: var(--text-xs);
}
.filter-sidebar__preset-load {
  flex: 1; text-align: left;
  background: transparent; border: 0; cursor: pointer;
  font-family: inherit; color: var(--text-secondary);
  font-size: inherit;
}
.filter-sidebar__preset-load:hover { color: var(--text-primary); }
.filter-sidebar__preset-del {
  background: transparent; border: 0; cursor: pointer;
  color: var(--text-tertiary);
  margin-left: var(--space-2);
}
.filter-sidebar__preset-del:hover { color: var(--color-danger); }
.filter-sidebar__empty {
  font-size: var(--text-xs); color: var(--text-tertiary); margin: 0;
}

.filter-sidebar__reset-all {
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--space-3);
  background: transparent; border-bottom: 0; border-left: 0; border-right: 0;
  font-size: var(--text-xs);
  color: var(--color-danger);
  cursor: pointer; text-align: left;
  font-family: inherit;
}
.filter-sidebar__reset-all:hover { text-decoration: underline; }
</style>
