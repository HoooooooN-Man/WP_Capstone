// UX W7B — vitest 전역 setup. jsdom 환경에 부재한 Web API mock.

// Notification API (notifications.js store 가 import 시 평가)
class FakeNotification {
  static permission: NotificationPermission = 'default'
  static requestPermission(): Promise<NotificationPermission> {
    return Promise.resolve('granted')
  }
  constructor(_title: string, _options?: any) { /* no-op */ }
}
;(globalThis as any).Notification = FakeNotification
