<script setup>
import { ref, computed } from 'vue'
import { useScreenerStore } from '@/stores/screener'

const props = defineProps({ filters: { type: Object, required: true } })
const emit  = defineEmits(['filter-change', 'reset-financial', 'reset-all'])
const store = useScreenerStore()

const financialOpen = ref(true)
const presetName    = ref('')
const presets       = ref(store.getSavedPresets())

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

function change(key, value) { emit('filter-change', { key, value }) }

function savePreset() {
  if (!presetName.value.trim()) return
  store.savePreset(presetName.value.trim())
  presets.value = store.getSavedPresets()
  presetName.value = ''
}

function loadPreset(name) {
  store.loadPreset(name)
  emit('filter-change', { key: '_reload', value: null })
}

function deletePreset(name) {
  store.deletePreset(name)
  presets.value = store.getSavedPresets()
}
</script>

<template>
  <aside class="sticky top-6 bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-5 text-sm max-h-[calc(100vh-6rem)] overflow-y-auto">

    <!-- Section 1: ML 조건 -->
    <div class="flex flex-col gap-3">
      <p class="text-xs font-semibold text-gray-700 uppercase tracking-wide">ML 조건</p>

      <div class="flex flex-col gap-1">
        <label class="text-xs text-gray-500">모델 버전</label>
        <select
          :value="filters.model_version"
          class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
          @change="change('model_version', $event.target.value)"
        >
          <option value="latest">최신 버전</option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <div class="flex justify-between">
          <label class="text-xs text-gray-500">최소 ML 점수</label>
          <span class="text-xs font-medium text-gray-700">{{ filters.min_score }}점</span>
        </div>
        <input
          type="range" min="0" max="100" step="1"
          :value="filters.min_score"
          class="w-full accent-gray-700"
          @input="change('min_score', Number($event.target.value))"
        />
      </div>

      <div class="flex flex-col gap-1">
        <label class="text-xs text-gray-500">Tier</label>
        <select
          :value="filters.tier ?? ''"
          class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
          @change="change('tier', $event.target.value || null)"
        >
          <option value="">전체</option>
          <option value="A">A</option>
          <option value="B">B</option>
          <option value="C">C</option>
          <option value="D">D</option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label class="text-xs text-gray-500">섹터</label>
        <select
          :value="filters.sector ?? ''"
          class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
          @change="change('sector', $event.target.value || null)"
        >
          <option value="">전체</option>
          <option v-for="s in SECTORS" :key="s" :value="s">{{ s }}</option>
        </select>
      </div>
    </div>

    <hr class="border-gray-100" />

    <!-- Section 2: 재무 조건 (접기/펼치기) -->
    <div class="flex flex-col gap-3">
      <button
        class="flex items-center justify-between text-xs font-semibold text-gray-700 uppercase tracking-wide"
        @click="financialOpen = !financialOpen"
      >
        <span>재무 조건</span>
        <span class="text-gray-400">{{ financialOpen ? '▲' : '▼' }}</span>
      </button>

      <template v-if="financialOpen">
        <div
          v-for="f in [
            { key: 'max_per',           label: '최대 PER',        placeholder: '제한없음' },
            { key: 'max_pbr',           label: '최대 PBR',        placeholder: '제한없음' },
            { key: 'min_roe',           label: '최소 ROE (%)',    placeholder: '제한없음' },
            { key: 'max_debt_ratio',    label: '최대 부채비율 (%)', placeholder: '제한없음' },
            { key: 'min_op_margin',     label: '최소 영업이익률 (%)', placeholder: '제한없음' },
            { key: 'min_rev_growth',    label: '최소 매출성장률 (%)', placeholder: '제한없음' },
            { key: 'min_finance_score', label: '최소 재무점수',   placeholder: '제한없음' },
          ]"
          :key="f.key"
          class="flex flex-col gap-1"
        >
          <label class="text-xs text-gray-500">{{ f.label }}</label>
          <input
            type="number"
            :value="filters[f.key] ?? ''"
            :placeholder="f.placeholder"
            class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
            @blur="change(f.key, $event.target.value ? Number($event.target.value) : null)"
          />
        </div>

        <button
          class="text-xs text-red-400 hover:text-red-600 transition-colors text-left"
          @click="emit('reset-financial')"
        >
          재무 조건만 초기화
        </button>
      </template>
    </div>

    <hr class="border-gray-100" />

    <!-- Section 3: 정렬 & 결과수 -->
    <div class="flex flex-col gap-3">
      <p class="text-xs font-semibold text-gray-700 uppercase tracking-wide">정렬 & 결과수</p>

      <div class="flex flex-col gap-1">
        <label class="text-xs text-gray-500">정렬 기준</label>
        <select
          :value="filters.sort_by"
          class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
          @change="change('sort_by', $event.target.value)"
        >
          <option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label class="text-xs text-gray-500">결과 수</label>
        <select
          :value="filters.limit"
          class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
          @change="change('limit', Number($event.target.value))"
        >
          <option :value="50">50</option>
          <option :value="100">100</option>
          <option :value="200">200</option>
        </select>
      </div>
    </div>

    <hr class="border-gray-100" />

    <!-- Section 4: 프리셋 저장/불러오기 -->
    <div class="flex flex-col gap-3">
      <p class="text-xs font-semibold text-gray-700 uppercase tracking-wide">프리셋</p>
      <div class="flex gap-1.5">
        <input
          v-model="presetName"
          type="text"
          placeholder="프리셋 이름"
          class="flex-1 border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none"
          @keydown.enter="savePreset"
        />
        <button
          class="px-2.5 py-1.5 text-xs bg-gray-900 text-white rounded-lg hover:bg-gray-700 transition-colors"
          @click="savePreset"
        >
          저장
        </button>
      </div>
      <div v-if="presets.length" class="flex flex-col gap-1">
        <div
          v-for="name in presets"
          :key="name"
          class="flex items-center justify-between text-xs"
        >
          <button class="text-gray-600 hover:text-gray-900 flex-1 text-left" @click="loadPreset(name)">
            {{ name }}
          </button>
          <button class="text-gray-300 hover:text-red-400 ml-2" @click="deletePreset(name)">✕</button>
        </div>
      </div>
      <p v-else class="text-xs text-gray-300">저장된 프리셋 없음</p>
    </div>

    <!-- 전체 초기화 -->
    <button
      class="text-xs text-red-400 hover:text-red-600 text-left transition-colors border-t border-gray-100 pt-3"
      @click="emit('reset-all')"
    >
      전체 조건 초기화
    </button>

  </aside>
</template>
