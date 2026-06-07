import { lazy, Suspense } from 'react';
import type { CandlestickChartProps } from './CandlestickChartImpl';

/**
 * CandlestickChart — recharts 코드분리 래퍼. LineChart 와 동일 패턴.
 */
const CandlestickChartImpl = lazy(() => import('./CandlestickChartImpl'));

export default function CandlestickChart(props: CandlestickChartProps) {
  const height = props.height ?? 280;
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
      <CandlestickChartImpl {...props} />
    </Suspense>
  );
}
