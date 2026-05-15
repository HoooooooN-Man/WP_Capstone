export default function BottomDisclaimer() {
  return (
    <div
      className="py-8"
      style={{
        borderTop: '1px solid var(--border-default)',
        marginTop: '64px',
      }}
    >
      <div className="max-w-4xl mx-auto text-center space-y-2">
        <p
          style={{
            fontSize: '14px',
            lineHeight: '20px',
            fontWeight: 700,
            color: 'var(--text-secondary)',
          }}
        >
          투자 유의사항
        </p>
        <p
          style={{
            fontSize: '14px',
            lineHeight: '20px',
            color: 'var(--text-tertiary)',
          }}
        >
          본 서비스는 투자 자문이 아닙니다. 투자 결정은 본인 책임입니다.
        </p>
        <p
          style={{
            fontSize: '12px',
            lineHeight: '16px',
            color: 'var(--text-tertiary)',
            marginTop: '8px',
          }}
        >
          과거 수익률이 미래 수익을 보장하지 않습니다. 모든 투자는 원금 손실 위험이 있습니다.
        </p>
        <p
          style={{
            fontSize: '12px',
            lineHeight: '16px',
            color: 'var(--text-tertiary)',
          }}
        >
          WP Capstone Project — Korean Stock Recommendation Platform
        </p>
      </div>
    </div>
  );
}
