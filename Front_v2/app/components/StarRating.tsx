interface StarRatingProps {
  rating: number;
  showNumber?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export default function StarRating({ rating, showNumber = true, size = 'md' }: StarRatingProps) {
  const sizes = {
    sm: { star: '12px', text: '12px' },
    md: { star: '16px', text: '14px' },
    lg: { star: '20px', text: '16px' },
  };

  const renderStars = () => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;

    for (let i = 0; i < 5; i++) {
      if (i < fullStars) {
        stars.push(
          <span key={i} style={{ fontSize: sizes[size].star, color: '#F59E0B' }}>
            ★
          </span>
        );
      } else if (i === fullStars && hasHalfStar) {
        stars.push(
          <span key={i} style={{ fontSize: sizes[size].star, color: '#F59E0B', position: 'relative', display: 'inline-block' }}>
            <span style={{ position: 'absolute', width: '50%', overflow: 'hidden' }}>★</span>
            <span style={{ color: 'var(--text-tertiary)' }}>★</span>
          </span>
        );
      } else {
        stars.push(
          <span key={i} style={{ fontSize: sizes[size].star, color: 'var(--text-tertiary)' }}>
            ★
          </span>
        );
      }
    }
    return stars;
  };

  return (
    <div className="inline-flex items-center gap-1">
      <div className="inline-flex">{renderStars()}</div>
      {showNumber && (
        <span
          className="tabular-nums"
          style={{
            fontSize: sizes[size].text,
            fontWeight: 700,
            lineHeight: '20px',
            color: 'var(--text-secondary)',
          }}
        >
          {rating.toFixed(1)}
        </span>
      )}
    </div>
  );
}
