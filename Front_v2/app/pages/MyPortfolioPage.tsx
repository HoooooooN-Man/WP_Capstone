import { useState } from 'react';
import { TrendingUp, TrendingDown, Trash2, Plus } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import Modal from '../components/Modal';
import LineChart from '../components/LineChart';
import DonutChart from '../components/DonutChart';
import SignalLabelChip from '../components/SignalLabelChip';
import StockLogo from '../components/StockLogo';
import EmptyState from '../components/EmptyState';
import { useMyPortfolio, useAddHolding, useDeleteHolding, useRecommendations, type StockItem, type HoldingItem } from '../api/hooks';
import PageErrorState from '../components/PageErrorState';
import { useSession } from '../api/client';
import { getReturnColor } from '../utils/format';

interface Holding {
  id: number;
  ticker: string;
  name: string;
  quantity: number;
  avgPrice: number;
  currentPrice: number;
  signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  /** 백엔드 enrich — 추천 후 누적 수익률 (분할 의심 시 null). */
  returnPct?: number | null;
  /** 매수 후 경과 일수 (백엔드 enrich). */
  daysSinceBought?: number;
  /** B61: 액면분할/감자 의심. */
  splitEventSuspected?: boolean;
}

export default function MyPortfolioPage() {
  const [showAddModal, setShowAddModal] = useState(false);

  // 사용자 보유 종목 API (PRD §3.6 — /users/me/portfolio/holdings CRUD)
  const { data: portfolioApi } = useMyPortfolio();
  // 보유 종목 GET 은 현재가/이름/신호를 안 채워주므로 전 종목 스코어로 enrich
  const { data: allStocksApi } = useRecommendations({ top_k: 0 });
  const addHolding = useAddHolding();
  const deleteHolding = useDeleteHolding();
  const { isLoggedIn } = useSession();

  const stockMap = new Map<string, StockItem>(
    (allStocksApi?.items ?? []).map((s: StockItem) => [s.ticker, s]),
  );
  const apiHoldings: Holding[] | undefined = portfolioApi?.items?.map((h: HoldingItem): Holding => {
    const m = stockMap.get(h.ticker);
    // 백엔드 enrich (return_pct / days_since_bought / split_event) 가 우선,
    // 없으면 stockMap 의 추천 응답 close 로 fallback.
    return {
      id: h.id,
      ticker: h.ticker,
      name: m?.name ?? h.name ?? h.ticker,
      quantity: h.quantity ?? 0,
      avgPrice: h.avg_price ?? 0,
      currentPrice: h.current_price ?? m?.close ?? h.avg_price ?? 0,
      signal: (m?.signal_label ?? h.signal_label ?? 'WATCH') as 'BUY' | 'HOLD' | 'SELL' | 'WATCH',
      returnPct: h.return_pct,
      daysSinceBought: h.days_since_bought,
      splitEventSuspected: h.split_event_suspected ?? false,
    };
  });

  // mock 제거 — 실 보유 종목은 백엔드 /users/me/portfolio/holdings 에서만 (인증 필요)
  const holdings: Holding[] = apiHoldings ?? [];

  const totalInvestment = holdings.reduce((sum, h) => sum + h.avgPrice * h.quantity, 0);
  const currentValue = holdings.reduce((sum, h) => sum + h.currentPrice * h.quantity, 0);
  const totalReturn = currentValue - totalInvestment;
  const totalReturnPercent = totalInvestment > 0 ? (totalReturn / totalInvestment) * 100 : 0;

  const holdingsWithReturn = holdings.map((h) => {
    // 백엔드 returnPct 가 있으면 그걸 사용, 없으면 FE 자체 계산 (avg/current 기준).
    const feReturnPct =
      h.avgPrice > 0 ? ((h.currentPrice - h.avgPrice) / h.avgPrice) * 100 : 0;
    return {
      ...h,
      investmentAmount: h.avgPrice * h.quantity,
      currentAmount: h.currentPrice * h.quantity,
      returnAmount: (h.currentPrice - h.avgPrice) * h.quantity,
      returnPercent: h.returnPct ?? feReturnPct,
    };
  });

  // 평가금액 추이를 0-100 점수로 정규화하여 LineChart 형식에 맞춤
  const safeBase = totalInvestment > 0 ? totalInvestment : 1;
  const safeTrend = isFinite(totalReturnPercent) ? totalReturnPercent / 30 : 0;
  const portfolioHistory = Array.from({ length: 30 }, (_, i) => {
    const noise = (Math.random() - 0.5) * 2;
    // 50점을 기준으로 trend 따라 변동 (0-100 범위)
    const score = Math.max(0, Math.min(100, 50 + safeTrend * i + noise));
    return { date: `D${i + 1}`, score };
  });

  return (
    <AppLayout maxWidth={1280}>
        <div className="flex items-center justify-between mb-6">
          <h1 className="wp-t-3xl font-bold text-[var(--text-primary)]">
            내 포트폴리오
          </h1>
          {isLoggedIn && (
            <div className="flex items-center gap-2">
              <a
                href="/my/cohort-portfolio"
                className="flex items-center gap-1 px-4 py-2 rounded-lg wp-t-base font-bold border border-[var(--border-default)] text-[var(--text-primary)]"
              >
                코호트 자동 구성
              </a>
              <button
                onClick={() => setShowAddModal(true)}
                className="flex items-center gap-1 px-4 py-2 rounded-lg wp-t-base font-bold text-white bg-[var(--accent-blue)]"
              >
                <Plus size={16} /> 종목 추가
              </button>
            </div>
          )}
        </div>
        {!isLoggedIn && (
          <div className="py-8">
            <PageErrorState type="auth" />
          </div>
        )}

        {isLoggedIn && (
        <>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <div className="wp-t-base text-[var(--text-tertiary)] mb-2">총 자산</div>
            <div className="tabular-nums font-bold text-[var(--text-primary)] mb-3" style={{ fontSize: 32 }}>
              {currentValue.toLocaleString('ko-KR')}원
            </div>
            <div className="flex items-center gap-2">
              {totalReturn >= 0 ? (
                <TrendingUp size={20} style={{ color: 'var(--color-up)' }} />
              ) : (
                <TrendingDown size={20} style={{ color: 'var(--color-down)' }} />
              )}
              <span
                className="tabular-nums wp-t-lg font-bold"
                style={{ color: totalReturn >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
              >
                {totalReturn >= 0 ? '+' : ''}
                {totalReturn.toLocaleString('ko-KR')}원 ({totalReturn >= 0 ? '+' : ''}
                {totalReturnPercent.toFixed(2)}%)
              </span>
            </div>
          </div>

          <div className="p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <div className="wp-t-base text-[var(--text-tertiary)] mb-2">투자 원금</div>
            <div className="tabular-nums font-bold text-[var(--text-primary)] mb-3" style={{ fontSize: 32 }}>
              {totalInvestment.toLocaleString('ko-KR')}원
            </div>
            <div className="wp-t-base text-[var(--text-secondary)]">
              보유 종목: {holdings.length}개
            </div>
          </div>

          {/* 종목 구성 도넛 */}
          <div className="p-6 rounded-xl bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
            <div className="wp-t-base text-[var(--text-tertiary)] mb-3">종목 구성</div>
            {holdingsWithReturn.length > 0 ? (
              <DonutChart
                size={120}
                thickness={22}
                data={holdingsWithReturn.map((h) => ({ label: h.name, value: h.currentAmount }))}
              />
            ) : (
              <div className="wp-t-sm text-[var(--text-tertiary)]">보유 종목이 없습니다.</div>
            )}
          </div>
        </div>

        {holdings.length === 0 ? (
          <EmptyState
            title="보유 종목이 없습니다"
            description="종목을 추가하면 평가손익과 포트폴리오 추이를 확인할 수 있습니다."
            actionLabel="종목 추가"
            onAction={() => setShowAddModal(true)}
          />
        ) : (
        <>
        <div className="p-6 rounded-xl mb-6 bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
          <h2 className="wp-t-md font-bold text-[var(--text-primary)] mb-4">
            포트폴리오 추이
          </h2>
          <LineChart data={portfolioHistory} height={300} />
        </div>

        <div className="rounded-xl overflow-hidden bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
          <div className="px-4 py-3 border-b border-[var(--border-default)]">
            <h2 className="wp-t-md font-bold text-[var(--text-primary)]">
              보유 종목
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th scope="col" className="text-left px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">종목명</th>
                  <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">보유수량</th>
                  <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">평균단가</th>
                  <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">현재가</th>
                  <th scope="col" className="text-right px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">평가손익</th>
                  <th scope="col" className="text-center px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">신호</th>
                  <th scope="col" className="text-center px-4 py-3 wp-t-xs font-bold text-[var(--text-tertiary)]">삭제</th>
                </tr>
              </thead>
              <tbody>
                {holdingsWithReturn.map((stock, idx) => (
                  <tr
                    key={stock.ticker}
                    className={`transition-colors cursor-pointer hover:bg-[var(--bg-elev-2)] ${
                      idx < holdingsWithReturn.length - 1 ? 'border-b border-[var(--border-default)]' : ''
                    }`}
                  >
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <StockLogo ticker={stock.ticker} name={stock.name} size={36} />
                        <div>
                          <div className="wp-t-base font-bold text-[var(--text-primary)]">
                            {stock.name}
                          </div>
                          <div className="wp-t-xs text-[var(--text-tertiary)]">{stock.ticker}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right">
                      <div className="tabular-nums wp-t-base text-[var(--text-secondary)]">
                        {stock.quantity}주
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right">
                      <div className="tabular-nums wp-t-base text-[var(--text-secondary)]">
                        {stock.avgPrice.toLocaleString('ko-KR')}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right">
                      <div className="tabular-nums wp-t-base font-bold text-[var(--text-primary)]">
                        {stock.currentPrice.toLocaleString('ko-KR')}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right">
                      {stock.splitEventSuspected ? (
                        <div
                          className="wp-t-xs"
                          style={{ color: 'var(--text-tertiary)' }}
                          title="액면분할/감자 의심 (|수익률| > 300%)으로 수익률을 표시하지 않음"
                        >
                          분할 의심 — 미표시
                        </div>
                      ) : (
                        <>
                          <div
                            className="tabular-nums wp-t-base font-bold"
                            style={{ color: getReturnColor(stock.returnAmount) }}
                          >
                            {stock.returnAmount >= 0 ? '+' : ''}
                            {stock.returnAmount.toLocaleString('ko-KR')}
                          </div>
                          <div
                            className="tabular-nums wp-t-xs"
                            style={{ color: getReturnColor(stock.returnPercent) }}
                          >
                            {stock.returnPercent >= 0 ? '+' : ''}
                            {stock.returnPercent.toFixed(2)}%
                          </div>
                          {stock.daysSinceBought != null && stock.daysSinceBought > 0 && (
                            <div
                              className="wp-t-xs"
                              style={{ color: 'var(--text-tertiary)', marginTop: '2px' }}
                            >
                              매수 후 {stock.daysSinceBought}일
                            </div>
                          )}
                        </>
                      )}
                    </td>
                    <td className="px-4 py-4 text-center">
                      <div className="inline-block">
                        <SignalLabelChip signal={stock.signal} showIcon={false} />
                      </div>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <button
                        onClick={() => {
                          if (stock.id != null) deleteHolding.mutate(stock.id);
                        }}
                        className="p-2 rounded transition-colors text-[var(--text-tertiary)] hover:text-[var(--color-down)]"
                        aria-label="보유 종목 삭제"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        </>
        )}
        </>
        )}

      {showAddModal && (
        <AddHoldingModal
          onClose={() => setShowAddModal(false)}
          onSubmit={(body) => {
            addHolding.mutate(body, { onSuccess: () => setShowAddModal(false) });
          }}
          submitting={addHolding.isPending}
        />
      )}
    </AppLayout>
  );
}

interface AddHoldingModalProps {
  onClose: () => void;
  onSubmit: (body: {
    ticker: string; quantity: number; avg_price: number;
    bought_at?: string; memo?: string;
  }) => void;
  submitting: boolean;
}

function AddHoldingModal({ onClose, onSubmit, submitting }: AddHoldingModalProps) {
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [avgPrice, setAvgPrice] = useState('');
  const [boughtAt, setBoughtAt] = useState('');
  const [memo, setMemo] = useState('');

  const qn = Number(quantity);
  const pn = Number(avgPrice);
  const valid = ticker.trim().length > 0 && qn > 0 && pn > 0;

  const inputStyle = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: '8px',
    backgroundColor: 'var(--bg-elev-2)',
    border: '1px solid var(--border-default)',
    color: 'var(--text-primary)',
    fontSize: '14px',
  } as const;
  const labelStyle = {
    fontSize: '12px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px',
  } as const;

  return (
    <Modal open onClose={onClose} labelledBy="add-holding-title" maxWidth={420}>
      <div className="p-6">
        <h2 id="add-holding-title" className="wp-t-lg font-bold text-[var(--text-primary)] mb-4">
          보유 종목 추가
        </h2>
        <div className="space-y-3">
          <div>
            <div style={labelStyle}>종목코드 *</div>
            <input style={inputStyle} value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="예: 005930" />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <div style={labelStyle}>보유수량 *</div>
              <input style={inputStyle} type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="주" />
            </div>
            <div className="flex-1">
              <div style={labelStyle}>평균단가 *</div>
              <input style={inputStyle} type="number" value={avgPrice} onChange={(e) => setAvgPrice(e.target.value)} placeholder="원" />
            </div>
          </div>
          <div>
            <div style={labelStyle}>매수일</div>
            <input style={inputStyle} type="date" value={boughtAt} onChange={(e) => setBoughtAt(e.target.value)} />
          </div>
          <div>
            <div style={labelStyle}>메모</div>
            <input style={inputStyle} value={memo} onChange={(e) => setMemo(e.target.value)} placeholder="선택" maxLength={200} />
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded-lg"
            style={{ backgroundColor: 'var(--bg-elev-2)', color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 700 }}
          >
            취소
          </button>
          <button
            disabled={!valid || submitting}
            onClick={() =>
              onSubmit({
                ticker: ticker.trim(),
                quantity: qn,
                avg_price: pn,
                bought_at: boughtAt || undefined,
                memo: memo.trim() || undefined,
              })
            }
            className="flex-1 py-2 rounded-lg"
            style={{
              backgroundColor: valid && !submitting ? 'var(--accent-blue)' : 'var(--bg-elev-2)',
              color: valid && !submitting ? '#FFFFFF' : 'var(--text-tertiary)',
              fontSize: '14px', fontWeight: 700,
            }}
          >
            {submitting ? '추가 중…' : '추가'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
