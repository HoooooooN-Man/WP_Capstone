import { useState, useEffect } from 'react';
import { Star, TrendingUp, TrendingDown, ChevronLeft } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import StatTile from '../components/StatTile';
import SignalLabelChip from '../components/SignalLabelChip';
import StockLogo from '../components/StockLogo';
import StarRating from '../components/StarRating';
import ScoreBadge from '../components/ScoreBadge';
import StockDetailInfoStrip from '../components/StockDetailInfoStrip';
import NewsThumbnail from '../components/NewsThumbnail';
import HomeTab from './stock-detail/HomeTab';
import DiagnosisTab from './stock-detail/DiagnosisTab';
import ValueTab from './stock-detail/ValueTab';
import { useParams, useNavigate } from 'react-router-dom';
import {
  useStockHistory, useStockOutcome, useStockRadar,
  useStockFairValue, useStockDividend, useStockPeers,
  useRecommendations, useStockFinancials, useNewsFeed,
  useWatchlist, useAddWatchlist, useDeleteWatchlist,
} from '../api/hooks';
import { useSession } from '../api/client';
import { pushRecentStock } from '../utils/recent';
import { getReturnColor } from '../utils/format';

// 종목 상세 — 토스 레퍼런스 기반 5탭 (종목홈 / 진단 / 밸류·재무 / 뉴스 / 경쟁사)
// Home / Diagnosis / Value 탭 콘텐츠는 ./stock-detail/{Home,Diagnosis,Value}Tab.tsx 분리
type Tab = 'home' | 'diagnosis' | 'value' | 'news' | 'peers';

export default function StockDetailPage() {
  const { ticker = '005930' } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('home');

  // 관심종목 — 로컬 state 대신 watchlist API 기준 (서버 단일 소스)
  const { isLoggedIn } = useSession();
  const { data: watchlistApi } = useWatchlist();
  const addWatchlist = useAddWatchlist();
  const deleteWatchlist = useDeleteWatchlist();
  const isWatchlisted = (watchlistApi?.items ?? []).some((w) => w.ticker === ticker);
  const toggleWatchlist = () => {
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }
    if (isWatchlisted) deleteWatchlist.mutate(ticker);
    else addWatchlist.mutate({ ticker });
  };

  // 종목 API 묶음
  const { data: history } = useStockHistory(ticker);
  const { data: outcome } = useStockOutcome(ticker);
  const { data: radar } = useStockRadar(ticker);
  const { data: fairValue } = useStockFairValue(ticker);
  const { data: dividend } = useStockDividend(ticker);
  const { data: peers } = useStockPeers(ticker);
  const { data: financials } = useStockFinancials(ticker);
  const { data: stockNews } = useNewsFeed({ ticker, limit: 20 });

  // 추천 리스트에서 enrich (signal/star_rating/headline 등)
  const { data: recApi } = useRecommendations({ top_k: 0 });
  const recRow = recApi?.items?.find((it) => it.ticker === ticker);

  const items = history?.items ?? [];
  const latest = items[items.length - 1];
  const prev = items.length >= 2 ? items[items.length - 2] : null;
  const computedChangePct = latest?.close && prev?.close && prev.close > 0
    ? ((latest.close - prev.close) / prev.close) * 100
    : (recRow?.change_pct ?? 0);
  const selectedStock = {
    ticker,
    name: latest?.name ?? recRow?.name ?? ticker,
    sector: latest?.sector ?? recRow?.sector ?? '',
    price: latest?.close ?? recRow?.close ?? 0,
    changePercent: computedChangePct,
    signal: (latest?.signal_label ?? recRow?.signal_label ?? 'WATCH') as 'BUY' | 'HOLD' | 'SELL' | 'WATCH',
    score: latest?.score ?? recRow?.score ?? 0,
    tier: (latest?.tier ?? recRow?.tier ?? 'C') as 'A' | 'B' | 'C' | 'D',
    starRating: recRow?.star_rating ?? 0,
    cumulativeReturn: outcome?.cumulative_return_pct ?? recRow?.cumulative_return_pct ?? 0,
    headline: recRow?.headline ?? '',
  };

  // 최근 본 종목 기록 — ContextRail "최근 본 종목" 에 노출
  useEffect(() => {
    pushRecentStock({ ticker, name: selectedStock.name || ticker });
  }, [ticker, selectedStock.name]);

  // 개요 탭 실데이터 — history(OHLCV)·financials 에서 산출
  const fin = financials?.items?.find((f) => f.revenue != null) ?? financials?.items?.[0];
  const w52 = items.slice(-252);
  const w52High = Math.max(...w52.map((it) => it.high ?? it.close ?? 0).filter((v): v is number => v != null && v > 0), 0);
  const w52Low = (() => {
    const lows = w52.map((it) => it.low ?? it.close).filter((v): v is number => v != null && v > 0);
    return lows.length ? Math.min(...lows) : 0;
  })();
  const fmtKRW = (v: number | null | undefined) =>
    v != null && Number.isFinite(v) ? Math.round(v).toLocaleString('ko-KR') : '-';
  const fmtEok = (v: number | null | undefined) => {
    if (v == null || !Number.isFinite(v)) return '-';
    const eok = v / 1e8;
    return eok >= 10000 ? `${(eok / 10000).toFixed(1)}조원` : `${Math.round(eok).toLocaleString('ko-KR')}억원`;
  };

  // 5탭 — 토스 레퍼런스 정렬
  const tabs = [
    { key: 'home'      as const, label: '종목홈'  },
    { key: 'diagnosis' as const, label: '진단'    },
    { key: 'value'     as const, label: '밸류·재무' },
    { key: 'news'      as const, label: '뉴스'    },
    { key: 'peers'     as const, label: '경쟁사'  },
  ];

  // 재무 실데이터 — /api/v1/finance/{ticker} (단위 원 → 억원 환산)
  const financialData = (financials?.items ?? [])
    .filter((f) => f.revenue != null || f.op_profit != null || f.net_profit != null)
    .map((f) => ({
      year: `${f.year}.${f.quarter}Q`,
      revenue: f.revenue != null ? Math.round(f.revenue / 1e8) : 0,
      operatingIncome: f.op_profit != null ? Math.round(f.op_profit / 1e8) : 0,
      netIncome: f.net_profit != null ? Math.round(f.net_profit / 1e8) : 0,
    }));
  // 뉴스 실데이터 — /api/v1/news/feed?ticker= (news_company_map 매핑 기반)
  const newsItems = (stockNews?.items ?? []).map((n) => ({
    id: n.id,
    title: n.title ?? '',
    summary: n.summary ?? n.content?.slice(0, 120) ?? '',
    source: n.source ?? n.company_name ?? '뉴스',
    time: n.published_at ?? '',
    imageUrl: n.image_url ?? null,
    sentiment: (n.sentiment_label ?? 'neutral') as 'positive' | 'negative' | 'neutral',
  }));

  // 점수 추이 — 실데이터: history 의 score 시계열 (최근 30 거래일)
  const performanceHistory = (history?.items ?? []).slice(-30).map((it) => ({
    date: it.date,
    score: it.score ?? 0,
  }));

  // 진단 강·약점 — radar API 5요인 그룹 점수에서 자동 도출 (종목별 하드코딩 제거)
  const radarGroupLabels: Record<string, string> = {
    growth: '성장성', profitability: '수익성', safety: '안전성',
    moat: '독점력', cashflow: '현금창출력',
  };
  const radarGroupEntries = radar?.groups
    ? Object.entries(radar.groups)
        .filter(([, v]) => v != null)
        .map(([k, v]) => ({ key: k, label: radarGroupLabels[k] ?? k, score: Math.round(Number(v)) }))
    : [];
  const strengths = radarGroupEntries.filter((g) => g.score >= 70).sort((a, b) => b.score - a.score);
  const cautions  = radarGroupEntries.filter((g) => g.score < 50).sort((a, b) => a.score - b.score);

  return (
    <AppLayout maxWidth={1280} rail={false}>
      {/* ── 종목 헤더 ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <button
              onClick={() => navigate(-1)}
              className="p-2 rounded-full transition-colors cursor-pointer hover:bg-[var(--bg-elev-1)]"
              aria-label="뒤로 가기"
            >
              <ChevronLeft size={24} style={{ color: 'var(--text-primary)' }} />
            </button>
            <StockLogo ticker={selectedStock.ticker} name={selectedStock.name} size={44} />
            <h1 className="wp-t-3xl font-bold text-[var(--text-primary)]">
              {selectedStock.name}
            </h1>
            <button
              onClick={toggleWatchlist}
              className="p-2"
              aria-label={isWatchlisted ? '관심종목 해제' : '관심종목 추가'}
              aria-pressed={isWatchlisted}
            >
              <Star
                size={24}
                style={{
                  color: isWatchlisted ? '#FFB800' : 'var(--text-tertiary)',
                  fill: isWatchlisted ? '#FFB800' : 'none',
                }}
              />
            </button>
          </div>
          <div className="flex items-center gap-2 wp-t-base text-[var(--text-tertiary)]">
            <span>{selectedStock.ticker}</span>
            <span>·</span>
            <span>{selectedStock.sector}</span>
          </div>
        </div>
        <SignalLabelChip signal={selectedStock.signal} showIcon={true} />
      </div>

      {/* ── 핵심 지표 3카드 (전 탭 공통 헤더) ───────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card>
          <StatTile
            label="현재가"
            valueSize={36}
            value={selectedStock.price.toLocaleString('ko-KR')}
            sub={
              <div className="flex items-center gap-1.5">
                {selectedStock.changePercent >= 0 ? (
                  <TrendingUp size={18} style={{ color: 'var(--color-up)' }} />
                ) : (
                  <TrendingDown size={18} style={{ color: 'var(--color-down)' }} />
                )}
                <span
                  className="tabular-nums wp-t-md font-bold"
                  style={{ color: selectedStock.changePercent >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
                >
                  {selectedStock.changePercent >= 0 ? '+' : ''}
                  {selectedStock.changePercent.toFixed(2)}%
                </span>
              </div>
            }
          />
        </Card>

        <Card>
          <div className="wp-t-sm text-[var(--text-tertiary)] mb-2.5">스마트스코어</div>
          <div className="flex items-center gap-4">
            <ScoreBadge score={selectedStock.score} tier={selectedStock.tier} />
            <StarRating rating={selectedStock.starRating} size="sm" showNumber={false} />
          </div>
        </Card>

        <Card>
          <StatTile
            label="최근 30일 수익률"
            valueSize={36}
            valueColor={getReturnColor(selectedStock.cumulativeReturn)}
            value={`${selectedStock.cumulativeReturn >= 0 ? '+' : ''}${selectedStock.cumulativeReturn.toFixed(1)}%`}
          />
        </Card>
      </div>

      {/* 정보 띠 — history OHLCV + financials 실데이터 */}
      <div className="mb-6">
        <StockDetailInfoStrip
          items={[
            {
              label: '1일 범위',
              value: latest?.low != null && latest?.high != null
                ? `${fmtKRW(latest.low)} ~ ${fmtKRW(latest.high)}` : '-',
              sub: '원',
            },
            {
              label: '52주 범위',
              value: w52High > 0 && w52Low > 0
                ? `${fmtKRW(w52Low)} ~ ${fmtKRW(w52High)}` : '-',
              sub: '원',
            },
            { label: '거래량', value: latest?.volume != null ? fmtKRW(latest.volume) : '-', sub: '주' },
            // PER/PBR — fairValue API 의 TTM EPS·BPS + 현재가 기반 (분기 stale 회피).
            // 폴백: financials 의 분기 종가 기준 컬럼.
            {
              label: 'PER',
              value: (() => {
                const curPx = selectedStock?.price;
                const eps = fairValue?.inputs?.eps;
                if (curPx && eps && eps > 0) return `${(curPx / eps).toFixed(1)}배`;
                return fin?.per != null ? `${fin.per.toFixed(1)}배` : '-';
              })(),
            },
            {
              label: 'PBR',
              value: (() => {
                const curPx = selectedStock?.price;
                const bps = fairValue?.inputs?.bps;
                if (curPx && bps && bps > 0) return `${(curPx / bps).toFixed(2)}배`;
                return fin?.pbr != null ? `${fin.pbr.toFixed(2)}배` : '-';
              })(),
            },
            {
              label: '외국인 비중',
              value: latest?.foreign_ratio != null ? `${Number(latest.foreign_ratio).toFixed(1)}%` : '-',
            },
            {
              label: '상장주식수',
              value: latest?.shares_outstanding != null
                ? `${(latest.shares_outstanding / 1e6).toFixed(1)}M` : '-', sub: '주',
            },
            { label: '시가총액', value: fmtEok(latest?.market_cap ?? fin?.market_cap) },
          ]}
        />
      </div>

      {/* ── 탭 ───────────────────────────────────────────────────── */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 rounded-lg whitespace-nowrap transition-colors cursor-pointer wp-t-base border border-[var(--border-default)] ${
              activeTab === tab.key
                ? 'font-bold text-white bg-[var(--accent-blue)]'
                : 'font-normal text-[var(--text-secondary)] bg-[var(--bg-elev-1)]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Home / Diagnosis / Value — pages/stock-detail/ 분리 ────── */}
      {activeTab === 'home' && (
        <HomeTab
          selectedStock={selectedStock}
          performanceHistory={performanceHistory}
          fin={fin}
          latest={latest}
          w52High={w52High}
          w52Low={w52Low}
          fmtKRW={fmtKRW}
          fmtEok={fmtEok}
          radarGroupEntries={radarGroupEntries}
          newsItems={newsItems}
          onGoDiagnosis={() => setActiveTab('diagnosis')}
          onGoNews={() => setActiveTab('news')}
        />
      )}

      {activeTab === 'diagnosis' && (
        <DiagnosisTab
          radar={radar}
          radarGroupEntries={radarGroupEntries}
          strengths={strengths}
          cautions={cautions}
          performanceHistory={performanceHistory}
        />
      )}

      {activeTab === 'value' && (
        <ValueTab
          fairValue={fairValue}
          financialData={financialData}
          dividend={dividend}
        />
      )}

      {/* ── 뉴스 — 썸네일 + 요약 스니펫 + 감성 칩 ───────────────────── */}
      {activeTab === 'news' && (
        <Card padded={false}>
          <div className="px-6 py-4 border-b border-[var(--border-default)]">
            <SectionHeader title="관련 뉴스" />
          </div>
          {newsItems.length === 0 ? (
            <div className="wp-t-sm text-[var(--text-tertiary)] p-6 text-center">
              종목별 뉴스 매핑 미구현 — news_data.duckdb + ticker 매핑 필요
            </div>
          ) : (
            newsItems.map((news, idx) => (
              <div
                key={news.id}
                className={`px-6 py-4 flex gap-4 transition-colors hover:bg-[var(--bg-elev-2)] ${
                  idx < newsItems.length - 1 ? 'border-b border-[var(--border-default)]' : ''
                }`}
              >
                {/* 썸네일 — image_url 있으면 이미지, 실패 시 아이콘 폴백 */}
                <NewsThumbnail imageUrl={news.imageUrl} className="w-28 h-[76px]" iconSize={22} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="px-1.5 py-0.5 rounded wp-t-2xs font-bold"
                      style={{
                        backgroundColor:
                          news.sentiment === 'positive' ? 'var(--buy-bg)'
                            : news.sentiment === 'negative' ? 'var(--sell-bg)' : 'var(--bg-elev-2)',
                        color:
                          news.sentiment === 'positive' ? 'var(--buy-text)'
                            : news.sentiment === 'negative' ? 'var(--sell-text)' : 'var(--text-tertiary)',
                      }}
                    >
                      {news.sentiment === 'positive' ? '긍정' : news.sentiment === 'negative' ? '부정' : '중립'}
                    </span>
                    <span className="wp-t-xs text-[var(--text-tertiary)]">
                      {news.source} · {news.time}
                    </span>
                  </div>
                  <div className="wp-t-base font-bold text-[var(--text-primary)] mb-1 line-clamp-2">
                    {news.title}
                  </div>
                  {news.summary && (
                    <div className="wp-t-sm text-[var(--text-secondary)] line-clamp-1">
                      {news.summary}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </Card>
      )}

      {/* ── 경쟁사 ───────────────────────────────────────────────── */}
      {activeTab === 'peers' && (
        <Card>
          <SectionHeader title="경쟁사" sub="같은 섹터 · 시가총액 유사" />
          {peers?.items && peers.items.length > 0 ? (
            <div className="overflow-x-auto mt-4">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-default)]">
                    <th scope="col" className="text-left py-3 wp-t-sm text-[var(--text-tertiary)]">종목명</th>
                    <th scope="col" className="text-right py-3 wp-t-sm text-[var(--text-tertiary)]">점수</th>
                    <th scope="col" className="text-center py-3 wp-t-sm text-[var(--text-tertiary)]">신호</th>
                    <th scope="col" className="text-right py-3 wp-t-sm text-[var(--text-tertiary)]">현재가</th>
                  </tr>
                </thead>
                <tbody>
                  {peers.items.map((p) => (
                    <tr
                      key={p.ticker}
                      className="cursor-pointer transition-colors hover:bg-[var(--bg-elev-2)] border-b border-[var(--border-default)]"
                      onClick={() => navigate(`/stocks/${p.ticker}`)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          navigate(`/stocks/${p.ticker}`);
                        }
                      }}
                      tabIndex={0}
                      role="button"
                      aria-label={`${p.name} 상세 보기`}
                    >
                      <td className="py-3">
                        <div className="font-bold text-[var(--text-primary)]">{p.name}</div>
                        <div className="wp-t-xs text-[var(--text-tertiary)]">{p.ticker}</div>
                      </td>
                      <td className="text-right py-3 tabular-nums font-bold text-[var(--text-primary)]">{p.score?.toFixed(1)} [{p.tier}]</td>
                      <td className="text-center py-3">
                        <SignalLabelChip signal={p.signal_label ?? 'WATCH'} showIcon={false} />
                      </td>
                      <td className="text-right py-3 tabular-nums text-[var(--text-primary)]">{p.close?.toLocaleString('ko-KR')}원</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="wp-t-sm text-[var(--text-tertiary)] mt-4">경쟁사 데이터를 불러오는 중입니다.</div>
          )}
        </Card>
      )}
    </AppLayout>
  );
}
