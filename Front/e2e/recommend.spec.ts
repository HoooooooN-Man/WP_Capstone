import { test, expect } from '@playwright/test'

// UX W3 — RecommendView e2e (1 spec).
// 백엔드 라이브 응답 의존 — fetch 를 route mock 으로 격리.

const MOCK_META = {
  model_version: 'v11a_prime',
  cohort: 'balanced',
  diversify: null,
  market_regime: 'normal',
  as_of_date: '2026-04-29',
  is_advice: false,
}

const MOCK_ITEMS = [
  { ticker: '005930', name: '삼성전자',   sector: 'IT',     score: 87, tier: 'A', rank_in_date: 1 },
  { ticker: '000660', name: 'SK하이닉스', sector: 'IT',     score: 85, tier: 'A', rank_in_date: 2 },
  { ticker: '035420', name: 'NAVER',      sector: 'IT',     score: 82, tier: 'A', rank_in_date: 3 },
  { ticker: '005380', name: '현대차',     sector: '자동차', score: 78, tier: 'B', rank_in_date: 4 },
  { ticker: '051910', name: 'LG화학',     sector: '화학',   score: 75, tier: 'B', rank_in_date: 5 },
]

test('비로그인 추천 화면 — 헤더·grid·CTA·고급 옵션', async ({ page }) => {
  // 추천 API mock
  await page.route('**/stocks/recommendations**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        date: '2026-04-29',
        model_version: 'v11a_prime',
        total: MOCK_ITEMS.length,
        items: MOCK_ITEMS,
        meta: MOCK_META,
      }),
    })
  })

  await page.goto('/recommend')

  // 1. 헤드라인 (비로그인 fallback)
  await expect(page.getByRole('heading', { name: '오늘의 추천' })).toBeVisible()

  // 2. subtitle 메타 표시
  const subtitle = page.locator('.recommend-view__subtitle')
  await expect(subtitle).toContainText('v11a_prime')
  await expect(subtitle).toContainText('균형')
  await expect(subtitle).toContainText('5개')
  await expect(subtitle).toContainText('4월 29일 기준')

  // 3. 추천 카드 5개 + inline CTA 1개 (5번째 자리)
  const cards = page.locator('.recommend-view__grid > article.recommend-card')
  await expect(cards).toHaveCount(5)
  await expect(page.locator('.inline-cta')).toBeVisible()
  await expect(page.locator('.inline-cta')).toContainText('로그인하면 맞춤 추천')

  // 4. 그리드 끝 footer CTA 표시
  await expect(page.locator('.footer-cta')).toBeVisible()
  await expect(page.locator('.footer-cta__btn')).toHaveText('로그인하기')

  // 5. 자문 면책 footer
  await expect(page.locator('.recommend-view__footer')).toContainText('자문이 아닙니다')

  // 6. 고급 옵션 default 접힘 → 클릭 시 펼침
  const toggle = page.locator('.recommend-view__toggle')
  await expect(toggle).toHaveAttribute('aria-expanded', 'false')
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-expanded', 'true')
  const advanced = page.locator('.recommend-view__advanced')
  await expect(advanced).toBeVisible()
  await expect(advanced).toContainText('다양성')
  await expect(advanced).toContainText('실험적')   // embedding 경고

  // 7. diversify 변경 → URL query 동기
  await page.locator('input[type="radio"][value="correlation"]').check()
  await expect(page).toHaveURL(/diversify=correlation/)
})
