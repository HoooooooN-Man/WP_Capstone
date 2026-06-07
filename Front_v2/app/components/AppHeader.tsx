import { Search, Bell, Sun, Moon, User } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTheme } from 'next-themes';
import { useSession } from '../api/client';

interface AppHeaderProps {
  variant: 'mobile' | 'desktop';
}

interface SubTab {
  label: string;
  path: string;
}

interface NavTab {
  label: string;
  path: string;
  match: (p: string) => boolean;
  subs: SubTab[];
}

// PRD §2 메인 네비 5탭 + §3.4·§3.5·§3.7 영역별 하위 탭
const NAV_TABS: NavTab[] = [
  {
    label: '추천', path: '/recommend',
    match: (p) => p.startsWith('/recommend') || p.startsWith('/winner') || p.startsWith('/signal') || p === '/',
    subs: [
      { label: '종목추천', path: '/recommend' },
      { label: '승부주',   path: '/winner' },
      { label: '매매신호', path: '/signal' },
    ],
  },
  {
    label: '검색', path: '/search',
    match: (p) => p.startsWith('/search'),
    subs: [],
  },
  {
    label: '탐색', path: '/sectors',
    match: (p) =>
      p.startsWith('/sectors') || p.startsWith('/screener') ||
      p.startsWith('/news') || p.startsWith('/compare'),
    subs: [
      { label: '섹터분석', path: '/sectors' },
      { label: '스크리너', path: '/screener' },
      { label: '뉴스',     path: '/news' },
      { label: '종목비교', path: '/compare' },
    ],
  },
  {
    label: '관심', path: '/watchlist',
    match: (p) => p.startsWith('/watchlist'),
    subs: [],
  },
  {
    label: '마이', path: '/my',
    match: (p) => p.startsWith('/my'),
    subs: [],
  },
];

// 종목상세 등 그룹 미소속 경로는 subs 없음 → 하위 네비 미표시
function activeTab(path: string): NavTab | undefined {
  return NAV_TABS.find((t) => t.match(path));
}

export default function AppHeader({ variant }: AppHeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, setTheme } = useTheme();
  const isDark = theme === 'dark';
  const toggleTheme = () => setTheme(isDark ? 'light' : 'dark');
  const currentPath = location.pathname;
  const current = activeTab(currentPath);
  const subTabs = current?.subs ?? [];
  const { isLoggedIn } = useSession();

  // 하위 네비 바 (데스크탑·모바일 공통) — 중앙 정렬
  const subNav = subTabs.length > 0 && (
    <div
      className="flex items-center justify-center gap-1 overflow-x-auto px-4 sm:px-8"
      style={{
        height: '44px',
        backgroundColor: 'var(--bg-elev-1)',
        borderBottom: '1px solid var(--border-default)',
      }}
    >
      {subTabs.map((sub) => {
        const active = currentPath === sub.path || currentPath.startsWith(sub.path + '/');
        return (
          <button
            key={sub.path}
            onClick={() => navigate(sub.path)}
            className="px-3 py-1.5 rounded-lg whitespace-nowrap transition-all"
            style={{
              fontSize: '14px',
              fontWeight: active ? 700 : 400,
              color: active ? '#FFFFFF' : 'var(--text-secondary)',
              backgroundColor: active ? 'var(--accent-blue)' : 'transparent',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            {sub.label}
          </button>
        );
      })}
    </div>
  );

  if (variant === 'mobile') {
    return (
      <>
        <header
          className="flex items-center justify-between px-4"
          style={{
            height: '56px',
            backgroundColor: 'var(--bg-base)',
            borderBottom: '1px solid var(--border-default)',
          }}
        >
          <button
            onClick={() => navigate('/recommend')}
            style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', background: 'transparent', border: 'none', cursor: 'pointer' }}
          >
            WP Stock
          </button>
          <div className="flex items-center gap-2">
            <button className="p-2" aria-label="Search" onClick={() => navigate('/search')}>
              <Search size={20} style={{ color: 'var(--text-primary)' }} />
            </button>
            <button
              className="p-2"
              aria-label={isLoggedIn ? '마이페이지' : '로그인'}
              onClick={() => navigate(isLoggedIn ? '/my' : '/login')}
            >
              {isLoggedIn ? (
                <User size={20} style={{ color: 'var(--text-primary)' }} />
              ) : (
                <Bell size={20} style={{ color: 'var(--text-primary)' }} />
              )}
            </button>
          </div>
        </header>
        {subNav}
      </>
    );
  }

  return (
    <>
      <header
        className="flex items-center justify-between px-8"
        style={{
          height: '64px',
          backgroundColor: 'var(--bg-base)',
          borderBottom: '1px solid var(--border-default)',
        }}
      >
        <button
          onClick={() => navigate('/recommend')}
          style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', background: 'transparent', border: 'none', cursor: 'pointer' }}
        >
          WP Stock
        </button>
        <nav className="flex items-center gap-8">
          {NAV_TABS.map((tab) => {
            const active = tab.match(currentPath);
            return (
              <button
                key={tab.label}
                onClick={() => navigate(tab.path)}
                style={{
                  fontSize: '16px',
                  fontWeight: active ? 700 : 400,
                  color: active ? 'var(--accent-blue)' : 'var(--text-secondary)',
                  padding: '8px 0',
                  borderBottom: active ? '2px solid var(--accent-blue)' : '2px solid transparent',
                  background: 'transparent',
                  cursor: 'pointer',
                  transition: 'color 150ms ease-out',
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
        <div className="flex items-center gap-4">
          <button className="p-2" aria-label="Notifications" onClick={() => navigate('/my')}>
            <Bell size={20} style={{ color: 'var(--text-primary)' }} />
          </button>
          <button className="p-2" onClick={toggleTheme} aria-label="Toggle theme">
            {isDark ? (
              <Sun size={20} style={{ color: 'var(--text-primary)' }} />
            ) : (
              <Moon size={20} style={{ color: 'var(--text-primary)' }} />
            )}
          </button>
          {isLoggedIn ? (
            <button
              onClick={() => navigate('/my')}
              className="rounded-full flex items-center justify-center"
              style={{
                width: '32px', height: '32px',
                backgroundColor: 'var(--accent-blue)', color: '#FFFFFF',
                border: 'none', cursor: 'pointer',
              }}
              aria-label="마이페이지"
            >
              <User size={18} />
            </button>
          ) : (
            <button
              onClick={() => navigate('/login')}
              className="rounded-lg"
              style={{
                padding: '7px 16px',
                backgroundColor: 'var(--accent-blue)', color: '#FFFFFF',
                border: 'none', cursor: 'pointer',
                fontSize: '14px', fontWeight: 700,
              }}
            >
              로그인
            </button>
          )}
        </div>
      </header>
      {subNav}
    </>
  );
}
