import { Home, Search, Activity, Heart, User } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

interface BottomNavProps {
  activeTab?: number;
}

const TABS = [
  { icon: Home,     label: '추천', path: '/recommend', match: (p: string) => p.startsWith('/recommend') || p.startsWith('/winner') || p.startsWith('/signal') || p === '/' },
  { icon: Search,   label: '검색', path: '/search',    match: (p: string) => p.startsWith('/search') },
  { icon: Activity, label: '발굴', path: '/scores',    match: (p: string) => p.startsWith('/scores') || p.startsWith('/sectors') || p.startsWith('/screener') || p.startsWith('/news') || p.startsWith('/compare') },
  { icon: Heart,    label: '관심', path: '/watchlist', match: (p: string) => p.startsWith('/watchlist') },
  { icon: User,     label: '마이', path: '/my',        match: (p: string) => p.startsWith('/my') },
];

export default function BottomNav({ activeTab }: BottomNavProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname;

  return (
    <nav
      className="flex items-center justify-around"
      style={{
        height: '56px',
        backgroundColor: 'var(--bg-base)',
        borderTop: '1px solid var(--border-default)',
      }}
    >
      {TABS.map((tab, idx) => {
        const Icon = tab.icon;
        // activeTab prop 우선, 미지정 시 path 매칭
        const isActive = activeTab !== undefined ? idx === activeTab : tab.match(currentPath);
        return (
          <button
            key={tab.label}
            onClick={() => navigate(tab.path)}
            className="flex flex-col items-center justify-center flex-1 relative"
            style={{ height: '100%', background: 'transparent', border: 'none', cursor: 'pointer' }}
          >
            <Icon
              size={24}
              style={{
                color: isActive ? 'var(--accent-blue)' : 'var(--text-tertiary)',
              }}
            />
            <div
              style={{
                fontSize: '12px',
                lineHeight: '16px',
                color: isActive ? 'var(--accent-blue)' : 'var(--text-tertiary)',
                marginTop: '2px',
              }}
            >
              {tab.label}
            </div>
            {isActive && (
              <div
                className="absolute bottom-0 left-0 right-0"
                style={{
                  height: '2px',
                  backgroundColor: 'var(--accent-blue)',
                }}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
}
