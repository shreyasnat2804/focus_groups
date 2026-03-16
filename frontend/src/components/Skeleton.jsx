export function SkeletonLine({ width = "100%", height = "1rem" }) {
  return <div className="skeleton-line" style={{ width, height }} />;
}

export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <SkeletonLine width="70%" height="1rem" />
      <SkeletonLine width="40%" height="0.75rem" />
      <SkeletonLine width="100%" height="6px" />
      <div className="skeleton-card-footer">
        <SkeletonLine width="60px" height="0.75rem" />
        <SkeletonLine width="80px" height="0.75rem" />
      </div>
    </div>
  );
}

export function PitchGridSkeleton({ count = 6 }) {
  return (
    <div className="pitch-grid">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function SessionDetailSkeleton() {
  return (
    <div className="skeleton-detail">
      <SkeletonLine width="50%" height="1.75rem" />
      <div className="skeleton-meta">
        <SkeletonLine width="60px" height="0.85rem" />
        <SkeletonLine width="80px" height="0.85rem" />
        <SkeletonLine width="100px" height="0.85rem" />
      </div>
      <SkeletonLine width="120px" height="2rem" />
      <SkeletonLine width="100%" height="10px" />
      <div className="skeleton-responses">
        {Array.from({ length: 3 }, (_, i) => (
          <div key={i} className="skeleton-response">
            <div className="skeleton-response-header">
              <SkeletonLine width="70px" height="1.2rem" />
              <SkeletonLine width="200px" height="0.85rem" />
            </div>
            <SkeletonLine width="100%" height="0.9rem" />
            <SkeletonLine width="90%" height="0.9rem" />
            <SkeletonLine width="60%" height="0.9rem" />
          </div>
        ))}
      </div>
    </div>
  );
}
