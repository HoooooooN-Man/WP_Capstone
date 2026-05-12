import { test, expect } from '@playwright/test'

// UX W4 — StockDetailView e2e (1 spec).
// 5~6 endpoint 호출을 route mock 으로 격리.

const MOCK_HISTORY = Array.from({ length: 90 }, (_, i) => ({
  date:   `2026-${String(Math.floor(i / 30) + 1).padStart(2, '0')}-${String((i % 30) + 1).padStart(2, '0')}`,
  ticker: '005930',
  name:   '삼성전자',
  sector: 'IT',
  close:  70000 + i * 50,
  score:  87,
  tier:   'A',
  model_version: 'v11a_prime',
}))

const MOCK_CHART = MOCK_HISTORY.map(r => ({
  date: r.date,
  open: r.close - 100, high: r.close + 200, low: r.close - 200,
  close: r.close, volume: 1_000_000,
}))

const MOCK_FINANCE = [
  { year: 2026, quarter: 1, per: 12.5, pbr: 1.8, roe: 15.2, debt_ratio: 35.1, op_margin: 18.5, rev_growth_yoy: 8.2 },
  { year: 2025, quarter: 4, per: 13.1, pbr: 1.9, roe: 14.8, debt_ratio: 36.0, op_margin: 17.9, rev_growth_yoy: 7.1 },
]

const MOCK_NEWS = [
  { news_id: 'n1', title: '삼성전자, AI 칩 양산 발표',  source: '매일경제',   published_at: '2026-04-29' },
  { news_id: 'n2', title: '반도체 시장 회복 전망',       source: '연합뉴스',   published_at: '2026-04-28' },
]

test('종목 상세 — 기본정보·차트 즉시, 재무·뉴스 lazy, 공시 empty', async ({ page }) => {
  // 기본정보 (history) + 차트 — 즉시 로드
  await page.route('**/stocks/005930/history', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json',
                body: JSON.stringify({ items: MOCK_HISTORY }) }),
  )
  await page.route('**/chart/005930', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json',
                body: JSON.stringify({ items: MOCK_CHART }) }),
  )
  // 재무·뉴스 — lazy
  let financeFetched = false
  let newsFetched    = false
  await page.route('**/finance/005930', (r) => {
    financeFetched = true
    return r.fulfill({ status: 200, contentType: 'application/json',
                       body: JSON.stringify({ items: MOCK_FINANCE }) })
  })
  await page.route('**/news/feed**', (r) => {
    newsFetched = true
    return r.fulfill({ status: 200, contentType: 'application/json',
                       body: JSON.stringify({ items: MOCK_NEWS }) })
  })

  // 추천 컨텍스트로 진입
  await page.goto('/stock/005930?from=recommend&model_version=v11a_prime&cohort=balanced&diversify=correlation')

  // 1. 기본정보 헤더
  await expect(page.getByRole('heading', { name: '삼성전자' })).toBeVisible()
  await expect(page.locator('.stock-detail__ticker')).toContainText('005930')
  await expect(page.locator('.stock-detail__sector')).toContainText('IT')

  // 2. 가격·score·tier 표시
  await expect(page.locator('.stock-detail__price')).toBeVisible()
  await expect(page.locator('.stock-detail__score')).toContainText('87점')

  // 3. 추천 컨텍스트 MetaBadge
  await expect(page.locator('.stock-detail__meta-row')).toBeVisible()
  await expect(page.locator('.stock-detail__meta-row')).toContainText('v11a_prime')
  await expect(page.locator('.stock-detail__meta-row')).toContainText('균형')
  await expect(page.locator('.stock-detail__meta-row')).toContainText('상관')

  // 4. CoverageBadge — history 90 day 이라 'ok' 라 미표시
  await expect(page.locator('.coverage-badge')).toHaveCount(0)

  // 5. 차트 영역 표시 (기간 버튼)
  await expect(page.locator('.stock-detail__chart')).toBeVisible()
  await expect(page.locator('.period-btn.is-active')).toContainText('6M')

  // 6. 탭 default = 재무
  const tabs = page.locator('[role="tab"]')
  await expect(tabs).toHaveCount(3)
  await expect(tabs.nth(0)).toHaveAttribute('aria-selected', 'true')
  await expect(tabs.nth(0)).toContainText('재무')
  await expect(page.locator('.finance-table')).toBeVisible()
  expect(financeFetched).toBe(true)

  // 7. 뉴스 탭 클릭 → lazy fetch
  expect(newsFetched).toBe(false)
  await tabs.nth(1).click()
  await expect(page.locator('.news-list')).toBeVisible()
  expect(newsFetched).toBe(true)
  await expect(page).toHaveURL(/tab=news/)

  // 8. 공시 탭 → empty state (백엔드 endpoint 부재)
  await tabs.nth(2).click()
  await expect(page.locator('.empty-state')).toContainText('추후 제공')
})
