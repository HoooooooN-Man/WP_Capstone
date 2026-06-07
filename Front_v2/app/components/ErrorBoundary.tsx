import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * ErrorBoundary — 렌더 중 throw 된 오류가 전체 화이트스크린이 되지 않도록 차단.
 * main.tsx 에서 <App/> 을 감싼다. 운영에선 componentDidCatch 가 모니터링 전송 지점.
 */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // 운영 환경에서는 Sentry 등 모니터링으로 전송
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  private reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div
        className="min-h-screen flex items-center justify-center p-6"
        style={{ backgroundColor: 'var(--bg-base)' }}
      >
        <div
          className="w-full max-w-md rounded-xl p-8 text-center"
          style={{ backgroundColor: 'var(--bg-elev-1)', border: '1px solid var(--border-default)' }}
        >
          <div className="wp-t-3xl font-bold text-[var(--text-primary)] mb-2">
            문제가 발생했습니다
          </div>
          <p className="wp-t-base text-[var(--text-secondary)] mb-6">
            화면을 그리는 중 오류가 발생했습니다. 다시 시도하거나 페이지를 새로고침해 주세요.
          </p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={this.reset}
              className="px-5 py-2.5 rounded-lg wp-t-base font-bold text-white bg-[var(--accent-blue)]"
            >
              다시 시도
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-5 py-2.5 rounded-lg wp-t-base font-bold bg-[var(--bg-elev-2)] text-[var(--text-primary)] border border-[var(--border-default)]"
            >
              새로고침
            </button>
          </div>
          {import.meta.env.DEV && (
            <pre
              className="mt-6 p-3 rounded-lg text-left wp-t-xs text-[var(--color-down)] overflow-auto"
              style={{ backgroundColor: 'var(--bg-elev-2)', maxHeight: 160, whiteSpace: 'pre-wrap' }}
            >
              {error.message}
            </pre>
          )}
        </div>
      </div>
    );
  }
}
