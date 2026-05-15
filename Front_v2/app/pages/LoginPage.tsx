import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from 'next-themes';
import { useLogin } from '../api/hooks';

/**
 * LoginPage — 2단 레이아웃 (리디자인 P2-12)
 *  - 좌: 브랜드 패널 (그라데이션 배경 + 가치 제안 + 핵심 기능 3)
 *  - 우: 로그인 폼
 *  - 모바일: 브랜드 패널 축소 + 폼 세로 스택
 */
export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const navigate = useNavigate();
  const loginMutation = useLogin();
  const { theme, setTheme } = useTheme();
  const isDark = theme === 'dark';

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    try {
      await loginMutation.mutateAsync({ email, password });
      navigate('/recommend');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '';
      setErrorMsg(msg || '로그인에 실패했습니다. 이메일/비밀번호를 확인해 주세요.');
    }
  };

  const handleSocialLogin = () => {
    setErrorMsg('소셜 로그인은 아직 지원하지 않습니다.');
  };

  const inputStyle: React.CSSProperties = {
    backgroundColor: 'var(--bg-elev-2)',
    border: '1px solid var(--border-default)',
    color: 'var(--text-primary)',
    fontSize: '14px',
    outline: 'none',
  };
  const labelStyle: React.CSSProperties = {
    fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)',
    display: 'block', marginBottom: '6px',
  };

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: 'var(--bg-base)' }}>
      {/* 좌: 브랜드 패널 */}
      <div
        className="hidden lg:flex flex-col justify-between p-12"
        style={{
          width: '46%',
          background: 'linear-gradient(150deg, #1E3A8A 0%, #2E5FC9 55%, #E03B4B 140%)',
          color: '#FFFFFF',
        }}
      >
        <div className="wp-t-2xl font-extrabold">WP Stock</div>

        <div>
          <div className="font-extrabold" style={{ fontSize: 40, lineHeight: '52px', letterSpacing: '-0.5px' }}>
            AI가 매일 분석하는<br />오늘의 투자 타이밍
          </div>
          <div className="wp-t-md mt-4" style={{ opacity: 0.85 }}>
            LightGBM 랭킹 모델이 KOSPI·KOSDAQ 종목을 스코어링하고,
            매수·보유·매도 신호와 5요인 진단을 제공합니다.
          </div>
          <div className="mt-8 space-y-3">
            {[
              '스마트스코어 + 매수/보유/매도 신호',
              '투자 성향별 맞춤 추천 (Cohort)',
              '보유 종목 손익·리밸런싱 진단',
            ].map((t) => (
              <div key={t} className="flex items-center gap-3 wp-t-md">
                <span
                  className="flex items-center justify-center rounded-full w-[22px] h-[22px] wp-t-sm font-extrabold"
                  style={{ backgroundColor: 'rgba(255,255,255,0.18)' }}
                >
                  ✓
                </span>
                {t}
              </div>
            ))}
          </div>
        </div>

        <div className="wp-t-xs" style={{ opacity: 0.6 }}>
          투자 판단의 보조 도구이며, 투자 자문이 아닙니다.
        </div>
      </div>

      {/* 우: 로그인 폼 */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full" style={{ maxWidth: '380px' }}>
          <div className="mb-8">
            <div className="font-extrabold text-[var(--text-primary)]" style={{ fontSize: 24 }}>
              로그인
            </div>
            <div className="wp-t-base text-[var(--text-secondary)] mt-1">
              계정에 로그인하고 맞춤 추천을 받아보세요
            </div>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="email" style={labelStyle}>이메일</label>
              <input
                id="email" type="email" value={email} required
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@example.com"
                className="w-full px-4 py-3 rounded-lg transition-all"
                style={inputStyle}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent-blue)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border-default)'; }}
              />
            </div>
            <div>
              <label htmlFor="password" style={labelStyle}>비밀번호</label>
              <input
                id="password" type="password" value={password} required
                onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호를 입력하세요"
                className="w-full px-4 py-3 rounded-lg transition-all"
                style={inputStyle}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent-blue)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border-default)'; }}
              />
            </div>

            {errorMsg && (
              <div className="wp-t-sm text-[var(--color-down)]">{errorMsg}</div>
            )}

            <button
              type="submit"
              disabled={loginMutation.isPending}
              className="w-full py-3 rounded-lg transition-all wp-t-md font-bold mt-2 text-white"
              style={{
                backgroundColor: 'var(--accent-blue)',
                opacity: loginMutation.isPending ? 0.7 : 1,
              }}
            >
              {loginMutation.isPending ? '로그인 중…' : '로그인'}
            </button>
          </form>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full h-px bg-[var(--border-default)]" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-[var(--bg-base)] px-3 wp-t-xs text-[var(--text-tertiary)]">
                또는
              </span>
            </div>
          </div>

          <div className="space-y-2.5">
            <button
              onClick={handleSocialLogin}
              className="w-full py-3 rounded-lg flex items-center justify-center gap-2 transition-colors wp-t-base font-bold bg-[var(--bg-elev-2)] border border-[var(--border-default)] text-[var(--text-primary)]"
            >
              <span className="wp-t-md">G</span> 구글로 시작
            </button>
            <button
              onClick={handleSocialLogin}
              className="w-full py-3 rounded-lg flex items-center justify-center gap-2 transition-colors wp-t-base font-bold"
              style={{ backgroundColor: '#FEE500', border: '1px solid #FEE500', color: '#000000' }}
            >
              <span className="wp-t-md">K</span> 카카오로 시작
            </button>
          </div>

          <div className="flex items-center justify-center gap-3 mt-6 wp-t-sm">
            <button className="text-[var(--text-secondary)]">비밀번호 찾기</button>
            <span className="text-[var(--border-default)]">|</span>
            <button
              onClick={() => navigate('/register')}
              className="font-bold text-[var(--accent-blue)]"
            >
              회원가입
            </button>
          </div>

          <button
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
            className="mt-6 px-3 py-1.5 rounded-lg mx-auto block wp-t-xs bg-[var(--bg-elev-1)] text-[var(--text-tertiary)]"
          >
            {isDark ? '라이트 모드' : '다크 모드'}
          </button>
        </div>
      </div>
    </div>
  );
}
