import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from 'next-themes';
import {
  useRegister, useSetCohort, useLogin, useCheckEmail, useVerifyCode,
} from '../api/hooks';

interface Question {
  id: number;
  question: string;
  options: { label: string; sublabel?: string; cohort: string }[];
}

const questions: Question[] = [
  {
    id: 1,
    question: '투자 가능 기간은 얼마나 되시나요?',
    options: [
      { label: '단기', sublabel: '1년 미만', cohort: 'growth' },
      { label: '중기', sublabel: '1~3년', cohort: 'balanced' },
      { label: '장기', sublabel: '3년 이상', cohort: 'dividend' },
    ],
  },
  {
    id: 2,
    question: '최대 손실 감수 한도는?',
    options: [
      { label: '10% 이내', sublabel: '안정 우선', cohort: 'conservative' },
      { label: '20% 이내', sublabel: '균형', cohort: 'balanced' },
      { label: '30% 이상', sublabel: '고수익 추구', cohort: 'growth' },
    ],
  },
  {
    id: 3,
    question: '선호하는 수익 창출 방식은?',
    options: [
      { label: '주가 상승', sublabel: '시세차익', cohort: 'growth' },
      { label: '배당 수익', sublabel: '정기 현금흐름', cohort: 'dividend' },
      { label: '둘 다', sublabel: '균형', cohort: 'balanced' },
    ],
  },
  {
    id: 4,
    question: '재무제표에 얼마나 익숙하신가요?',
    options: [
      { label: '익숙하지 않음', cohort: 'balanced' },
      { label: '기본 지표 이해', cohort: 'value' },
      { label: '전문가 수준', cohort: 'value' },
    ],
  },
  {
    id: 5,
    question: '종목 선정 시 가장 중요한 요소는?',
    options: [
      { label: '안정성', sublabel: '재무 건전성', cohort: 'conservative' },
      { label: '성장성', sublabel: '매출 증가율', cohort: 'growth' },
      { label: '가치', sublabel: '저평가 종목', cohort: 'value' },
      { label: '배당', sublabel: '배당 수익률', cohort: 'dividend' },
    ],
  },
];

// 이모지 제거 — PRD §3.17 아이콘 정책. 텍스트 라벨만.
const cohortInfo: Record<string, { label: string; description: string; color: string }> = {
  conservative: {
    label: '보수형',
    description: '안정적인 재무 건전성이 높은 종목 우선',
    color: '#1E40AF',
  },
  balanced: { label: '균형', description: '성장과 안정의 균형을 추구', color: '#4B5563' },
  growth:   { label: '성장', description: '매출 성장률이 높은 종목 우선', color: '#B91C1C' },
  dividend: { label: '배당', description: '배당 수익률이 높은 종목 우선', color: '#92400E' },
  value:    { label: '가치', description: '저평가된 우량 종목 발굴', color: '#15803D' },
};

export default function RegisterPage() {
  const navigate = useNavigate();
  const setCohortMutation = useSetCohort();
  const registerMutation = useRegister();
  const loginMutation = useLogin();
  const checkEmailMutation = useCheckEmail();
  const verifyCodeMutation = useVerifyCode();

  const { theme, setTheme } = useTheme();
  const isDark = theme === 'dark';
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<string[]>([]);
  const [finalCohort, setFinalCohort] = useState<string>('');
  const [showResult, setShowResult] = useState(false);

  // 가입 폼 상태
  const [showSignup, setShowSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [emailSent, setEmailSent] = useState(false);
  const [emailVerified, setEmailVerified] = useState(false);
  const [signupError, setSignupError] = useState('');

  const PW_RE = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,24}$/;

  // 결과 화면에서 "시작하기" → 가입 폼으로 진행
  const handleStart = () => {
    setShowSignup(true);
  };

  // 인증코드 발송
  const handleSendCode = async () => {
    setSignupError('');
    try {
      await checkEmailMutation.mutateAsync(email.trim());
      setEmailSent(true);
    } catch (e: unknown) {
      setSignupError(e instanceof Error && e.message ? e.message : '인증코드 발송에 실패했습니다.');
    }
  };

  // 인증코드 확인
  const handleVerifyCode = async () => {
    setSignupError('');
    try {
      await verifyCodeMutation.mutateAsync({ email: email.trim(), code: code.trim() });
      setEmailVerified(true);
    } catch (e: unknown) {
      setSignupError(e instanceof Error && e.message ? e.message : '인증코드가 올바르지 않습니다.');
    }
  };

  // 가입 완료 → 회원가입 → 로그인 → cohort 저장 → 추천 페이지
  const handleSignup = async () => {
    setSignupError('');
    if (!PW_RE.test(password)) {
      setSignupError('비밀번호는 영문·숫자·특수문자(@$!%*#?&) 포함 8~24자여야 합니다.');
      return;
    }
    if (nickname.trim().length < 2) {
      setSignupError('닉네임은 2자 이상이어야 합니다.');
      return;
    }
    try {
      await registerMutation.mutateAsync({
        email: email.trim(), nickname: nickname.trim(), password,
      });
      await loginMutation.mutateAsync({ email: email.trim(), password });
      if (finalCohort) {
        try { await setCohortMutation.mutateAsync(finalCohort); } catch { /* 비치명적 */ }
      }
      navigate('/recommend');
    } catch (e: unknown) {
      setSignupError(e instanceof Error && e.message ? e.message : '회원가입에 실패했습니다.');
    }
  };

  // 가입 없이 둘러보기 (비로그인) — cohort 만 localStorage 임시 저장
  const handleSkip = () => {
    if (finalCohort) {
      try { localStorage.setItem('pending-cohort', finalCohort); } catch { /* ignore */ }
    }
    navigate('/recommend');
  };

  const handleAnswer = (cohort: string) => {
    const newAnswers = [...answers, cohort];
    setAnswers(newAnswers);

    if (currentStep < questions.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // 최빈값 cohort 계산
      const cohortCounts: Record<string, number> = {};
      newAnswers.forEach((c) => {
        cohortCounts[c] = (cohortCounts[c] || 0) + 1;
      });
      const mostFrequent = Object.entries(cohortCounts).sort((a, b) => b[1] - a[1])[0][0];
      setFinalCohort(mostFrequent);
      setShowResult(true);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
      setAnswers(answers.slice(0, -1));
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setAnswers([]);
    setShowResult(false);
    setFinalCohort('');
  };

  const progress = ((currentStep + 1) / questions.length) * 100;

  // ── 가입 폼 화면 ──────────────────────────────────────────────────────────
  if (showSignup) {
    const cohort = cohortInfo[finalCohort];
    const inputStyle = {
      width: '100%', padding: '12px 14px', borderRadius: '10px',
      backgroundColor: 'var(--bg-elev-2)', border: '1px solid var(--border-default)',
      color: 'var(--text-primary)', fontSize: '14px', outline: 'none',
    } as const;
    const labelStyle = {
      fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px',
    } as const;
    const busy = checkEmailMutation.isPending || verifyCodeMutation.isPending
      || registerMutation.isPending || loginMutation.isPending;

    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: 'var(--bg-base)' }}>
        <div className="w-full max-w-md">
          <div
            className="rounded-2xl p-8"
            style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)' }}
          >
            <div className="text-center mb-6">
              <div className="wp-t-2xl font-bold text-[var(--text-primary)]">회원가입</div>
              <div className="wp-t-sm text-[var(--text-secondary)] mt-1">
                투자자 유형: <span className="font-bold" style={{ color: cohort?.color }}>{cohort?.label}</span>
              </div>
            </div>

            <div className="space-y-4">
              {/* 이메일 + 인증코드 발송 */}
              <div>
                <div style={labelStyle}>이메일 *</div>
                <div className="flex gap-2">
                  <input
                    style={inputStyle} type="email" value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="email@example.com" disabled={emailVerified}
                  />
                  <button
                    onClick={handleSendCode}
                    disabled={!email.trim() || emailVerified || busy}
                    className="px-3 rounded-lg whitespace-nowrap wp-t-sm font-bold"
                    style={{
                      backgroundColor: emailVerified ? 'var(--bg-elev-2)' : 'var(--accent-blue)',
                      color: emailVerified ? 'var(--text-tertiary)' : '#FFFFFF',
                    }}
                  >
                    {emailSent ? '재발송' : '코드 받기'}
                  </button>
                </div>
              </div>

              {/* 인증코드 입력 */}
              {emailSent && !emailVerified && (
                <div>
                  <div style={labelStyle}>인증코드 *</div>
                  <div className="flex gap-2">
                    <input
                      style={inputStyle} value={code}
                      onChange={(e) => setCode(e.target.value)}
                      placeholder="이메일로 받은 6자리 코드"
                    />
                    <button
                      onClick={handleVerifyCode}
                      disabled={!code.trim() || busy}
                      className="px-3 rounded-lg whitespace-nowrap wp-t-sm font-bold text-white bg-[var(--accent-blue)]"
                    >
                      확인
                    </button>
                  </div>
                </div>
              )}
              {emailVerified && (
                <div className="wp-t-sm font-bold text-[var(--color-up)]">
                  ✓ 이메일 인증 완료
                </div>
              )}

              {/* 닉네임 + 비밀번호 (인증 후 활성화) */}
              <div>
                <div style={labelStyle}>닉네임 *</div>
                <input
                  style={{ ...inputStyle, opacity: emailVerified ? 1 : 0.5 }}
                  value={nickname} onChange={(e) => setNickname(e.target.value)}
                  placeholder="2~20자" disabled={!emailVerified} maxLength={20}
                />
              </div>
              <div>
                <div style={labelStyle}>비밀번호 *</div>
                <input
                  style={{ ...inputStyle, opacity: emailVerified ? 1 : 0.5 }}
                  type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="영문·숫자·특수문자 8~24자" disabled={!emailVerified}
                />
              </div>

              {signupError && (
                <div className="wp-t-sm text-[var(--color-down)]">{signupError}</div>
              )}

              <button
                onClick={handleSignup}
                disabled={!emailVerified || !nickname.trim() || !password || busy}
                className="w-full py-3 rounded-xl wp-t-base font-bold"
                style={{
                  backgroundColor: emailVerified && nickname.trim() && password && !busy
                    ? 'var(--accent-blue)' : 'var(--bg-elev-2)',
                  color: emailVerified && nickname.trim() && password && !busy
                    ? '#FFFFFF' : 'var(--text-tertiary)',
                }}
              >
                {busy ? '처리 중…' : '가입 완료'}
              </button>

              <button
                onClick={handleSkip}
                className="w-full py-2 wp-t-sm text-[var(--text-tertiary)]"
              >
                가입 없이 둘러보기
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (showResult) {
    const cohort = cohortInfo[finalCohort];
    return (
      <div
        className="min-h-screen flex items-center justify-center p-4"
        style={{ backgroundColor: 'var(--bg-base)' }}
      >
        <div className="w-full max-w-2xl">
          <div
            className="rounded-2xl p-8 sm:p-12"
            style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)' }}
          >
            <div className="text-center space-y-8">
              <div>
                <div className="wp-t-xl font-bold text-[var(--text-secondary)] mb-4">
                  당신의 투자자 유형은
                </div>
                <div
                  className="font-extrabold mb-3"
                  style={{ fontSize: 48, lineHeight: '56px', color: cohort.color }}
                >
                  {cohort.label}
                </div>
                <div className="wp-t-md text-[var(--text-secondary)]">
                  {cohort.description}
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-6 rounded-xl bg-[var(--bg-elev-2)]">
                {Object.entries(cohortInfo).map(([key, info]) => (
                  <div
                    key={key}
                    className="flex flex-col items-center gap-2 p-3 rounded-lg transition-all"
                    style={{
                      backgroundColor: key === finalCohort ? 'var(--accent-blue)' : 'transparent',
                      color: key === finalCohort ? '#FFFFFF' : 'var(--text-secondary)',
                      opacity: key === finalCohort ? 1 : 0.5,
                    }}
                  >
                    <span className="wp-t-md font-bold">{info.label}</span>
                  </div>
                ))}
              </div>

              <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
                <button
                  onClick={handleReset}
                  className="px-6 py-3 rounded-full transition-colors wp-t-base font-bold bg-[var(--bg-elev-2)] text-[var(--text-primary)] border border-[var(--border-default)]"
                >
                  다시 답변하기
                </button>
                <button
                  onClick={handleStart}
                  className="px-8 py-3 rounded-full transition-colors wp-t-base font-bold text-white bg-[var(--accent-blue)]"
                >
                  시작하기
                </button>
              </div>
            </div>
          </div>

          <button
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
            className="mt-4 px-4 py-2 rounded-lg mx-auto block wp-t-xs bg-[var(--bg-elev-1)] text-[var(--text-secondary)]"
          >
            {isDark ? '🌙 Dark' : '☀️ Light'}
          </button>
        </div>
      </div>
    );
  }

  const currentQuestion = questions[currentStep];

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ backgroundColor: 'var(--bg-base)' }}
    >
      <div className="w-full max-w-2xl">
        <div
          className="rounded-2xl p-8 sm:p-12"
          style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)' }}
        >
          <div className="text-center mb-8">
            <div className="font-bold text-[var(--text-primary)]" style={{ fontSize: 24 }}>
              WP Stock
            </div>
            <div className="wp-t-md text-[var(--text-secondary)] mt-1">
              3초만에 시작하기
            </div>
          </div>

          <div className="mb-8">
            <div className="flex items-center justify-between mb-2 wp-t-xs text-[var(--text-tertiary)]">
              <span>Step {currentStep + 1}/5</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full rounded-full overflow-hidden h-2 bg-[var(--bg-elev-2)]">
              <div
                className="h-full transition-all duration-300 bg-[var(--accent-blue)]"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="mb-8">
            <div className="mb-6 text-center wp-t-xl font-bold text-[var(--text-primary)]">
              {currentQuestion.question}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {currentQuestion.options.map((option, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAnswer(option.cohort)}
                  className="p-6 rounded-xl transition-all duration-150 cursor-pointer
                    border-2 border-[var(--border-default)] hover:border-[var(--accent-blue)] hover:-translate-y-0.5 bg-[var(--bg-elev-2)]"
                >
                  <div className={`wp-t-md font-bold text-[var(--text-primary)] ${option.sublabel ? 'mb-1' : ''}`}>
                    {option.label}
                  </div>
                  {option.sublabel && (
                    <div className="wp-t-base text-[var(--text-secondary)]">
                      {option.sublabel}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-between">
            <button
              onClick={handlePrevious}
              disabled={currentStep === 0}
              className="px-6 py-2 rounded-lg transition-colors wp-t-base font-bold"
              style={{
                backgroundColor: currentStep === 0 ? 'transparent' : 'var(--bg-elev-2)',
                color: currentStep === 0 ? 'var(--text-tertiary)' : 'var(--text-primary)',
                opacity: currentStep === 0 ? 0.5 : 1,
                cursor: currentStep === 0 ? 'not-allowed' : 'pointer',
              }}
            >
              ← 이전
            </button>
            <div className="wp-t-base text-[var(--text-tertiary)] self-center">
              질문 {currentStep + 1} / {questions.length}
            </div>
          </div>
        </div>

        <button
          onClick={() => setTheme(isDark ? 'light' : 'dark')}
          className="mt-4 px-4 py-2 rounded-lg mx-auto block wp-t-xs bg-[var(--bg-elev-1)] text-[var(--text-secondary)]"
        >
          {isDark ? '🌙 Dark' : '☀️ Light'}
        </button>
      </div>
    </div>
  );
}
