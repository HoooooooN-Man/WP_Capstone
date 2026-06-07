import { lazy, Suspense } from 'react';
import type { LineChartProps } from './LineChartImpl';

/**
 * LineChart — recharts 코드 스플리팅 래퍼.
 *
 * recharts(~100KB gzip)는 차트가 실제로 렌더될 때만 로드되도록
 * LineChartImpl 을 React.lazy 로 동적 import 한다 → 초기 번들에서 제외.
 * 호출부는 기존과 동일하게 이 컴포넌트를 import 하면 된다.
 */
const LineChartImpl = lazy(() => import('./LineChartImpl'));

export default function LineChart(props: LineChartProps) {
  const height = props.height ?? 240;
  return (
    <Suspense
      fallback={
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div
            className="wp-skeleton"
            style={{ width: '100%', height: Math.max(0, height - 16), borderRadius: 8 }}
          />
        </div>
      }
    >
      <LineChartImpl {...props} />
    </Suspense>
  );
}
