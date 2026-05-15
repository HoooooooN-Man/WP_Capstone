interface SignalLabelChipProps {
  signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  showIcon?: boolean;
}

export default function SignalLabelChip({ signal, showIcon = true }: SignalLabelChipProps) {
  const getStyles = (signal: string) => {
    switch (signal) {
      case 'BUY':
        return { bg: 'var(--buy-bg)', text: 'var(--buy-text)', icon: '▲' };
      case 'HOLD':
        return { bg: 'var(--hold-bg)', text: 'var(--hold-text)', icon: '◆' };
      case 'SELL':
        return { bg: 'var(--sell-bg)', text: 'var(--sell-text)', icon: '▼' };
      case 'WATCH':
        return { bg: 'var(--watch-bg)', text: 'var(--watch-text)', icon: '○' };
      default:
        return { bg: 'var(--watch-bg)', text: 'var(--watch-text)', icon: '○' };
    }
  };

  const styles = getStyles(signal);

  return (
    <div
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1"
      style={{
        backgroundColor: styles.bg,
        color: styles.text,
        fontSize: '14px',
        fontWeight: 700,
        lineHeight: '16px',
        minWidth: '44px',
        minHeight: '24px',
      }}
    >
      {showIcon && <span style={{ fontSize: '12px' }}>{styles.icon}</span>}
      {signal}
    </div>
  );
}
