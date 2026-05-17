import { useMarketRegime } from '../api/hooks';

/**
 * MarketTickerBar — 화면 하단 고정 시장 지표 띠 (토스 레퍼런스의 글로벌 시세 띠 대응).
 *
 * 별도 지수 API 가 없으므로 /api/v1/market/regime 의 실데이터
 * (시장점수·국면·A티어 비중·전일대비)를 노출해 "살아있는 화면" 감을 준다.
 * 데스크탑 전용 — 모바일은 하단 BottomNav 가 차지하므로 숨김.
 */
export default function MarketTickerBar() {
  const { data: regime } = useMarketRegime();

  const score = regime?.market_score ?? null;
  const daily = regime?.daily_change ?? null;
  const tierA = regime?.tier_a_ratio ?? null;
  const statusKo = regime?.status_ko ?? null;

  const scoreState =
    score == null ? '—' : score >= 70 ? '과열' : score >= 45 ? '중립' : '침체';

  const items: { label: string; value: string; color: string }[] = [
    {
      label: '시장점수',
      value: score != null ? score.toFixed(1) : '—',
      color: 'var(--text-primary)',
    },
    {
      label: '국면',
      value: statusKo ? `${scoreState} · ${statusKo}` : scoreState,
      color: 'var(--text-secondary)',
    },
    {
      // tier_a_ratio 는 이미 퍼센트 단위(예: 19.97 = 19.97%) — ×100 금지
      label: 'A티어 비중',
      value: tierA != null ? `${tierA.toFixed(1)}%` : '—',
      color: 'var(--text-secondary)',
    },
    {
      // daily_change 는 비율(예: 0.0075 = +0.75%)
      label: '전일 대비',
      value: daily != null ? `${daily >= 0 ? '+' : ''}${(daily * 100).toFixed(2)}%` : '—',
      color:
        daily == null
          ? 'var(--text-tertiary)'
          : daily >= 0
            ? 'var(--color-up)'
            : 'var(--color-down)',
    },
  ];

  // FE 평가 #5 fix: xl+ 에서는 ContextRail 사이드바가 같은 정보를 더 풍부하게 표시 →
  // footer 중복 노출 방지. lg ~ xl 사이 (사이드바 없음) 만 footer 노출.
  return (
    <div
      className="hidden lg:flex xl:hidden items-center gap-7 px-8 fixed bottom-0 left-0 right-0 z-40"
      style={{
        height: '36px',
        backgroundColor: 'var(--bg-elev-1)',
        borderTop: '1px solid var(--border-default)',
        fontSize: '13px',
      }}
    >
      <span style={{ fontWeight: 800, color: 'var(--text-primary)' }}>WP 시장 지표</span>
      {items.map((it) => (
        <div key={it.label} className="flex items-center gap-2">
          <span style={{ color: 'var(--text-tertiary)' }}>{it.label}</span>
          <span className="tabular-nums" style={{ fontWeight: 700, color: it.color }}>
            {it.value}
          </span>
        </div>
      ))}
      {regime?.message && (
        <span
          className="truncate"
          style={{ color: 'var(--text-tertiary)', marginLeft: 'auto', maxWidth: '420px' }}
        >
          {regime.message}
        </span>
      )}
    </div>
  );
}
