import { useState } from 'react';
import { User, Bell, Shield, HelpCircle, LogOut, ChevronRight } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import CohortBadge from '../components/CohortBadge';
import { useCohort, useSetCohort, useNotifications, useLogout, useMe } from '../api/hooks';
import PageErrorState from '../components/PageErrorState';
import { useSession } from '../api/client';

export default function MyPage() {
  const [notifications, setNotifications] = useState({
    signal: true,
    winner: true,
    news: false,
    marketing: false,
  });

  // 사용자 프로필 + cohort + 알림 API
  const { data: meApi } = useMe();
  const { data: cohortApi } = useCohort();
  const setCohortMutation = useSetCohort();
  const { data: notifApi } = useNotifications();
  const logout = useLogout();
  const { isLoggedIn } = useSession();

  // 실 사용자 정보 — /users/me 우선, 미로그인/로딩 시 폴백
  const userInfo = {
    name: meApi?.nickname ?? '게스트',
    email: meApi?.email ?? '로그인이 필요합니다',
    cohort: (meApi?.cohort ?? cohortApi?.cohort ?? 'balanced') as string,
    joinDate: meApi?.created_at ? meApi.created_at.slice(0, 10).replace(/-/g, '.') : '-',
    isVerified: meApi?.is_verified ?? false,
    unreadCount: notifApi?.unread_count ?? 0,
  };

  const toggleNotification = (key: keyof typeof notifications) => {
    setNotifications({ ...notifications, [key]: !notifications[key] });
  };

  const menuSections = [
    {
      title: '계정',
      items: [
        { icon: User, label: '프로필 수정', action: () => {} },
        { icon: Shield, label: '비밀번호 변경', action: () => {} },
      ],
    },
    {
      title: '설정',
      items: [
        { icon: Bell, label: '알림 설정', expandable: true },
        { icon: HelpCircle, label: '고객센터', action: () => {} },
      ],
    },
  ];

  return (
    <AppLayout maxWidth={896}>
        <h1 className="wp-t-3xl font-bold text-[var(--text-primary)] mb-6">
          마이페이지
        </h1>
        {!isLoggedIn && (
          <div className="mb-6">
            <PageErrorState type="auth" />
          </div>
        )}

        <div className="p-6 rounded-xl mb-6 bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
          <div className="flex items-center gap-4 mb-4">
            <div
              className="flex items-center justify-center rounded-full w-16 h-16 text-white wp-t-3xl font-bold"
              style={{ backgroundColor: 'var(--accent-blue)' }}
            >
              {userInfo.name.charAt(0)}
            </div>
            <div>
              <div className="wp-t-xl font-bold text-[var(--text-primary)] mb-1">
                {userInfo.name}
              </div>
              <div className="wp-t-base text-[var(--text-tertiary)]">
                {userInfo.email}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <CohortBadge cohort={userInfo.cohort} />
            <div
              className="px-3 py-1 rounded-lg wp-t-xs font-bold"
              style={{
                backgroundColor: userInfo.isVerified ? 'var(--accent-blue)' : 'var(--bg-elev-2)',
                color: userInfo.isVerified ? '#FFFFFF' : 'var(--text-secondary)',
              }}
            >
              {userInfo.isVerified ? '이메일 인증됨' : '미인증'}
            </div>
            <div className="px-3 py-1 rounded-lg wp-t-xs bg-[var(--bg-elev-2)] text-[var(--text-secondary)]">
              가입일: {userInfo.joinDate}
            </div>
          </div>
        </div>

        {isLoggedIn && menuSections.map((section) => (
          <div key={section.title} className="mb-6">
            <div className="wp-t-base font-bold text-[var(--text-secondary)] mb-3 pl-1">
              {section.title}
            </div>
            <div className="rounded-xl overflow-hidden bg-[var(--bg-elev-1)] border border-[var(--border-default)]">
              {section.items.map((item, idx) => (
                <div key={item.label}>
                  <button
                    onClick={item.action}
                    className={`w-full flex items-center justify-between px-4 py-4 transition-colors hover:bg-[var(--bg-elev-2)] ${
                      idx < section.items.length - 1 ? 'border-b border-[var(--border-default)]' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <item.icon size={20} style={{ color: 'var(--text-tertiary)' }} />
                      <span className="wp-t-base text-[var(--text-primary)]">
                        {item.label}
                      </span>
                    </div>
                    <ChevronRight size={20} style={{ color: 'var(--text-tertiary)' }} />
                  </button>

                  {item.expandable && item.label === '알림 설정' && (
                    <div className="px-4 pb-4 pt-2 space-y-3">
                      {([
                        ['signal', '매매신호 알림'],
                        ['winner', '승부주 알림'],
                        ['news', '뉴스 알림'],
                        ['marketing', '마케팅 알림'],
                      ] as const).map(([key, label]) => {
                        const on = notifications[key];
                        return (
                          <div key={key} className="flex items-center justify-between">
                            <span className="wp-t-base text-[var(--text-secondary)]">{label}</span>
                            <button
                              onClick={() => toggleNotification(key)}
                              className="relative rounded-full"
                              aria-label={`${label} ${on ? '끄기' : '켜기'}`}
                              style={{
                                width: 48, height: 28,
                                backgroundColor: on ? 'var(--accent-blue)' : 'var(--bg-elev-2)',
                                transition: 'all 0.2s',
                              }}
                            >
                              <div
                                className="absolute rounded-full bg-white"
                                style={{ top: 2, left: on ? 22 : 2, width: 24, height: 24, transition: 'all 0.2s' }}
                              />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {isLoggedIn && (
          <button
            onClick={() => {
              logout();
              window.location.href = '/login';
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-4 rounded-xl transition-colors cursor-pointer
              bg-[var(--bg-elev-1)] hover:bg-[var(--bg-elev-2)] border border-[var(--border-default)] text-[var(--color-down)]"
          >
            <LogOut size={20} />
            <span className="wp-t-base font-bold">로그아웃</span>
          </button>
        )}
    </AppLayout>
  );
}
