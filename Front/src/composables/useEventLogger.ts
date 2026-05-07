/**
 * useEventLogger.ts — 추천 카드 클릭·종목 상세 dwell 시간 적재.
 *
 * fire-and-forget. 사용 패턴:
 *
 *   // 추천 카드 컴포넌트
 *   const { logClickAndNavigate, beginDwell, endDwell } = useEventLogger()
 *   <button @click="logClickAndNavigate('005930', 1, impressionId)">…</button>
 *
 *   // 종목 상세 페이지
 *   onMounted(() => beginDwell(clickIdFromQuery))
 *   onBeforeUnmount(() => endDwell())
 *
 * meta.impression_id 는 axios response interceptor 가 자동 적재하므로
 * impression 측은 본 composable 의 책임이 아님 — 클릭/dwell 만.
 */
import { ref } from 'vue'
import { recordClick, patchClickDwell } from '@/api/events'

export function useEventLogger() {
  const lastClickId = ref<string | null>(null)
  const dwellStart = ref<number | null>(null)
  const dwellClickId = ref<string | null>(null)

  /**
   * 추천 카드 클릭 시 호출. impression_id 는 추천 응답 meta 에서 받아온 것.
   * Vue Router 이동은 호출자가 제어 — 본 함수는 *적재* 만.
   */
  async function logClick(
    impression_id: string,
    ticker: string,
    rank_clicked: number,
  ): Promise<string | null> {
    const rec = await recordClick({ impression_id, ticker, rank_clicked })
    lastClickId.value = rec?.click_id ?? null
    return lastClickId.value
  }

  /** 종목 상세 진입 시 호출 — dwell 측정 시작. */
  function beginDwell(click_id: string | null) {
    if (!click_id) return
    dwellClickId.value = click_id
    dwellStart.value = Date.now()
  }

  /** 종목 상세 이탈 시 호출 — dwell_ms PATCH. */
  async function endDwell(followup_action?: string): Promise<void> {
    if (!dwellClickId.value || !dwellStart.value) return
    const dwell_ms = Math.max(0, Date.now() - dwellStart.value)
    await patchClickDwell(dwellClickId.value, { dwell_ms, followup_action })
    dwellStart.value = null
    dwellClickId.value = null
  }

  /** 관심종목 추가·게시판 작성 등 단순 후속 액션 표시 — dwell 종료 후에도 사용 가능. */
  async function markFollowup(action: 'watchlist_add' | 'board_post' | 'compare_add') {
    if (!lastClickId.value) return
    await patchClickDwell(lastClickId.value, { followup_action: action })
  }

  return {
    lastClickId,
    logClick,
    beginDwell,
    endDwell,
    markFollowup,
  }
}
