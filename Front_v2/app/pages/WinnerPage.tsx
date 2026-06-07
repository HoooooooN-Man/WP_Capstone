import AppLayout from '../components/AppLayout';
import WinnerCard from '../components/WinnerCard';
import BottomDisclaimer from '../components/BottomDisclaimer';
import PageErrorState from '../components/PageErrorState';
import { useWinnerHistory, type WinnerStock, type WinnerDateGroup } from '../api/hooks';
import { useSession } from '../api/client';

export default function WinnerPage() {
  // 8일 이전 이력 잠금은 실제 로그인 상태 기준
  const { isLoggedIn } = useSession();

  // 일자별 승부주 Top-5 이력 — /api/v1/winners (scores 테이블에서 직접 도출)
  const { data: winnerApi } = useWinnerHistory(21, 5);
  const dateGroups = winnerApi?.items ?? [];

  // 시스템 today 가 아닌 *API 응답의 최신 일자* 기준 — 데이터 stale 시에도 일관된 lock 정책.
  // 이전: 시스템 today(2026-05-17) - API 최신(2026-04-29) = 18일 > 7 → 모든 카드 blur.
  const apiLatestDate = dateGroups.length > 0 ? dateGroups[0].date : null;

  const getDayOfWeek = (dateStr: string) => {
    const date = new Date(dateStr);
    const days = ['일', '월', '화', '수', '목', '금', '토'];
    return days[date.getDay()];
  };

  const getDaysAgo = (dateStr: string) => {
    if (!apiLatestDate) return 0;
    const date = new Date(dateStr);
    const ref  = new Date(apiLatestDate);
    const diffTime = Math.abs(ref.getTime() - date.getTime());
    return Math.floor(diffTime / (1000 * 60 * 60 * 24));
  };

  return (
    <AppLayout maxWidth={1280}>
        <div className="mb-8">
          <div className="flex items-baseline gap-3 mb-2">
            <h1 className="wp-t-3xl font-bold text-[var(--text-primary)]">
              승부주
            </h1>
            <span className="wp-t-md text-[var(--text-secondary)]">
              AI가 매일 5종목 자동 추천
            </span>
          </div>
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <span className="wp-t-base text-[var(--text-tertiary)]">※</span>
            <span className="wp-t-base text-[var(--text-secondary)]">
              추천가 대비 -10% 도달 시 손절 알림
            </span>
          </div>
        </div>

        {!isLoggedIn && (
          <div className="mb-6 p-3 rounded-lg flex items-center gap-2 bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <span className="wp-t-base">🔒</span>
            <span className="wp-t-sm text-[var(--text-secondary)]">
              로그인하면 8일 이전 승부주 이력까지 모두 열람할 수 있습니다.
            </span>
          </div>
        )}

        {dateGroups.length === 0 && (
          <PageErrorState type="empty" message="승부주 이력이 아직 준비되지 않았습니다. 잠시 후 다시 확인해주세요." />
        )}

        <div className="space-y-12">
          {dateGroups.map((group: WinnerDateGroup, dateIdx: number) => {
            const date = group.date;
            const daysAgo = getDaysAgo(date);
            const isLocked = !isLoggedIn && daysAgo > 7;
            const stocks = group.winners ?? [];

            return (
              <div key={date}>
                <div className="flex items-center gap-4 mb-6">
                  <h2 className="wp-t-xl font-bold text-[var(--text-primary)]">
                    {date} ({getDayOfWeek(date)})
                  </h2>
                  <span className="wp-t-base text-[var(--text-tertiary)]">
                    {daysAgo === 0 ? '오늘' : daysAgo === 1 ? '어제' : `${daysAgo}일 전`}
                  </span>
                  {dateIdx === 0 && (
                    <span className="px-2 py-1 rounded wp-t-xs font-bold text-white bg-[var(--accent-blue)]">
                      최신
                    </span>
                  )}
                  {isLocked && (
                    <span className="wp-t-xs text-[var(--text-tertiary)]">
                      🔒 로그인 시 열람
                    </span>
                  )}
                </div>

                <div className="flex gap-4 overflow-x-auto pb-4">
                  {stocks.map((stock: WinnerStock) => (
                    <WinnerCard
                      key={`${date}-${stock.ticker}`}
                      name={stock.name}
                      ticker={stock.ticker}
                      recommendPrice={stock.recommend_price ?? 0}
                      score={stock.score ?? 0}
                      targetPrice={stock.target_price ?? 0}
                      trend={stock.trend ?? { short: 'neutral', medium: 'neutral', long: 'neutral' }}
                      cumulativeReturn={stock.cumulative_return_pct ?? null}
                      daysSinceRec={daysAgo}
                      splitEventSuspected={stock.split_event_suspected ?? false}
                      isLocked={isLocked}
                    />
                  ))}
                </div>

                {dateIdx < dateGroups.length - 1 && (
                  <div className="mt-8 h-px bg-[var(--border-default)]" />
                )}
              </div>
            );
          })}
        </div>

        <BottomDisclaimer />
    </AppLayout>
  );
}
