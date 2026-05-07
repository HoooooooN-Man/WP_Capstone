/**
 * api/events.ts — :8000 events 라우터 클라이언트 (W1B).
 *
 * fire-and-forget 적재용. 모든 호출은 *실패해도 사용자 흐름을 막지 않음*.
 * 호출 실패는 console.error 로 남기고 reject — 호출자가 catch 로 무시 가능.
 */
import dbapi from './dbapi'
import { useSessionId } from '@/composables/useSessionId'

// ── 타입 ────────────────────────────────────────────────────────────────────

export interface ShownTickerEntry {
  ticker: string
  rank: number
  score?: number
  tier?: string
}

export interface ImpressionPayload {
  shown_tickers: ShownTickerEntry[]
  model_version: string
  cohort?: string | null
  embedding_version?: string | null
  page_context?: string | null
}

export interface ImpressionRecorded {
  impression_id: string
  shown_at: string
}

export interface ClickPayload {
  impression_id: string
  ticker: string
  rank_clicked: number
}

export interface ClickRecorded {
  click_id: string
  impression_id: string
  clicked_at: string
}

// ── 적재 함수 ───────────────────────────────────────────────────────────────

/**
 * 추천 노출 배치 적재. 백엔드 :8001 의 응답을 받자마자 호출.
 * fire-and-forget — Promise rejection 은 console.error 만 남기고 흡수.
 */
export async function recordImpressions(
  items: ImpressionPayload[],
): Promise<ImpressionRecorded[]> {
  const sid = useSessionId()
  const body = {
    items: items.map((it) => ({ ...it, session_id: sid })),
  }
  try {
    const r = await dbapi.post<{ accepted: number; items: ImpressionRecorded[] }>(
      '/events/impressions',
      body,
    )
    return r.data.items
  } catch (e) {
    console.error('[events] recordImpressions failed', e)
    throw e
  }
}

/** 추천 카드 클릭 적재. */
export async function recordClick(payload: ClickPayload): Promise<ClickRecorded | null> {
  const sid = useSessionId()
  try {
    const r = await dbapi.post<ClickRecorded>('/events/clicks', {
      ...payload,
      session_id: sid,
    })
    return r.data
  } catch (e) {
    console.error('[events] recordClick failed', e)
    return null
  }
}

/** 종목 상세 이탈 시 dwell_ms · followup_action 갱신. */
export async function patchClickDwell(
  click_id: string,
  body: { dwell_ms?: number; followup_action?: string },
): Promise<void> {
  if (body.dwell_ms === undefined && !body.followup_action) return
  const sid = useSessionId()
  try {
    await dbapi.patch(`/events/clicks/${click_id}`, { ...body, session_id: sid })
  } catch (e) {
    console.error('[events] patchClickDwell failed', e)
  }
}
