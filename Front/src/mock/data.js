/**
 * ──────────────────────────────────────────────
 *  MOCK DATA  (임시 데이터)
 *  TODO: 각 항목을 실제 API 응답으로 교체하세요.
 *        교체 위치는 각 주석의 [API] 태그를 참조.
 * ──────────────────────────────────────────────
 */

// ── 사용자 프로필 ─────────────────────────────
// [API] GET /api/user/profile
export const MOCK_USER = {
  name: 'User',
  style: '보수형',
  totalAsset: '12,500,000 원',
  issueDate: '2026. 04. 14',
  status: 'ACTIVE',
};

// ── 피드 ─────────────────────────────────────
// [API] GET /api/feed?limit=20
export const MOCK_FEEDS = [
  { id: 1, category: 'EARNINGS', title: '삼성전자 1Q 영업이익 6.6조 달성', body: 'DS부문 반도체 수익 회복세 뚜렷. HBM3E 공급 확대 효과.', ticker: '005930', change: +2.14, time: '2h ago' },
  { id: 2, category: 'NEWS',     title: 'SK하이닉스 HBM4 양산 본격 돌입', body: 'TSMC와 협력해 차세대 HBM4 하반기 양산 계획 확정.', ticker: '000660', change: +5.31, time: '4h ago' },
  { id: 3, category: 'TECH',     title: 'NAVER 클라우드 B2B 사업 확장 발표', body: '공공·금융 분야 하이퍼클로바X 도입 계약 3건 체결.', ticker: '035420', change: -0.82, time: '6h ago' },
  { id: 4, category: 'MARKET',   title: '코스피 2,650선 회복… 외국인 순매수', body: '반도체·2차전지 업종 중심으로 외국인 자금 유입 지속.', ticker: null,    change: +0.63, time: '8h ago' },
  { id: 5, category: 'EARNINGS', title: 'LG에너지솔루션 분기 적자 전환', body: '전기차 수요 둔화로 북미 공장 가동률 하락. 하반기 반등 기대.', ticker: '373220', change: -9.52, time: '10h ago' },
  { id: 6, category: 'NEWS',     title: '카카오 AI 사업부 독립 법인화 검토', body: '카카오브레인과 AI서비스 통합 후 별도 상장 추진 소식.', ticker: '035720', change: -1.20, time: '12h ago' },
];

// ── 기업 리스트 ───────────────────────────────
// [API] GET /api/companies?market=KOSPI
// quantScore: 머신러닝 퀀트 모델 점수 (0-100). 70↑ 매수신호, 45↓ 매도신호
// [API] GET /api/quant/scores 로 교체
export const MOCK_COMPANIES = [
  { id: 1,  name: '삼성전자',         ticker: '005930', sector: '반도체', price: 72400,  change:  6.47, color: '#1428A0', marketCap: '443조', per: 15.3, pbr: 1.8, dividend: 2.1, quantScore: 82, description: '글로벌 반도체·스마트폰·가전 선도 기업. DRAM·NAND 세계 1위.' },
  { id: 2,  name: 'SK하이닉스',      ticker: '000660', sector: '반도체', price: 158000, change:  8.97, color: '#BE0000', marketCap: '115조', per: 18.7, pbr: 2.1, dividend: 0.8, quantScore: 78, description: 'HBM·DRAM 글로벌 2위. AI 서버용 HBM3E 공급 확대 중.' },
  { id: 3,  name: 'NAVER',            ticker: '035420', sector: '인터넷', price: 172000, change: -4.44, color: '#03C75A', marketCap: '28조',  per: 22.4, pbr: 1.6, dividend: 0.3, quantScore: 55, description: '국내 1위 검색·클라우드 플랫폼. 하이퍼클로바X AI 서비스 확장.' },
  { id: 4,  name: 'Kakao',            ticker: '035720', sector: '인터넷', price: 48500,  change: -6.73, color: '#F9E000', marketCap: '21조',  per: 30.1, pbr: 1.2, dividend: 0.1, quantScore: 31, description: '국민 메신저 카카오톡 기반 플랫폼. 커머스·핀테크 사업 확장.' },
  { id: 5,  name: 'LG에너지솔루션',  ticker: '373220', sector: '배터리', price: 380000, change: -9.52, color: '#A50034', marketCap: '89조',  per: 42.0, pbr: 3.5, dividend: 0.0, quantScore: 28, description: '전기차 배터리 글로벌 2위. GM·현대차·BMW 등 주요 완성차 공급.' },
  { id: 6,  name: '현대차',           ticker: '005380', sector: '자동차', price: 215000, change:  2.14, color: '#002C5F', marketCap: '46조',  per:  6.2, pbr: 0.7, dividend: 3.5, quantScore: 71, description: '국내 1위 완성차 기업. 전기차 아이오닉 시리즈 글로벌 판매 확대.' },
  { id: 7,  name: 'POSCO홀딩스',     ticker: '005490', sector: '철강',   price: 310000, change:  1.32, color: '#6699CC', marketCap: '27조',  per:  9.1, pbr: 0.6, dividend: 4.2, quantScore: 62, description: '국내 최대 철강 기업. 2차전지 소재(양·음극재) 신사업 추진 중.' },
  { id: 8,  name: '셀트리온',         ticker: '068270', sector: '바이오', price: 148500, change:  3.88, color: '#00A651', marketCap: '18조',  per: 28.5, pbr: 2.9, dividend: 0.5, quantScore: 58, description: '항체 바이오시밀러 국내 1위. 램시마·트룩시마 유럽·미국 판매 중.' },
  { id: 9,  name: 'KB금융',           ticker: '105560', sector: '금융',   price: 68000,  change:  0.74, color: '#FFBC00', marketCap: '28조',  per:  6.8, pbr: 0.7, dividend: 5.1, quantScore: 74, description: '국내 1위 금융지주. KB국민은행·카드·증권·보험 계열사 보유.' },
  { id: 10, name: '삼성바이오로직스', ticker: '207940', sector: '바이오', price: 820000, change:  1.23, color: '#0068B7', marketCap: '58조',  per: 65.2, pbr: 7.1, dividend: 0.0, quantScore: 67, description: '글로벌 CMO 1위. 바이오의약품 위탁생산·개발 서비스 전문.' },
];

// ── 포트폴리오 ────────────────────────────────
// [API] GET /api/portfolio/me
export const MOCK_PORTFOLIOS = [
  { id: 1, company: '삼성전자',       ticker: '005930', sector: '반도체', shares: 50, avgPrice: 68000,  currentPrice: 72400,  change:  6.47, color: '#1428A0', weight: 32, quantScore: 82 },
  { id: 2, company: 'SK하이닉스',    ticker: '000660', sector: '반도체', shares: 20, avgPrice: 145000, currentPrice: 158000, change:  8.97, color: '#BE0000', weight: 28, quantScore: 78 },
  { id: 3, company: 'NAVER',          ticker: '035420', sector: '인터넷', shares: 10, avgPrice: 180000, currentPrice: 172000, change: -4.44, color: '#03C75A', weight: 15, quantScore: 55 },
  { id: 4, company: 'LG에너지솔루션', ticker: '373220', sector: '배터리', shares:  5, avgPrice: 420000, currentPrice: 380000, change: -9.52, color: '#A50034', weight: 17, quantScore: 28 },
  { id: 5, company: 'Kakao',          ticker: '035720', sector: '인터넷', shares: 30, avgPrice: 52000,  currentPrice: 48500,  change: -6.73, color: '#3A1D1D', weight:  8, quantScore: 31 },
];
