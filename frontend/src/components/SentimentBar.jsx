const SEGMENTS = ["positive", "mixed", "negative", "neutral"];

export default function SentimentBar({ sentiments, size = "small", showLabels = false, showPercent = false }) {
  if (!sentiments || sentiments.total === 0) return null;

  const barClass = size === "large" ? "sentiment-bar-large" : "sentiment-bar";

  return (
    <div className="sentiment-bar-container">
      <div className={barClass}>
        {SEGMENTS.map((seg) =>
          sentiments[seg] > 0 ? (
            <div
              key={seg}
              className={`sentiment-segment ${seg}`}
              style={{ width: `${(sentiments[seg] / sentiments.total) * 100}%` }}
            />
          ) : null
        )}
      </div>
      {showPercent && sentiments.total > 0 && (
        <span className="sentiment-pct">
          {Math.round((sentiments.positive / sentiments.total) * 100)}% positive
        </span>
      )}
      {showLabels && (
        <div className="sentiment-labels">
          {SEGMENTS.map((seg) =>
            sentiments[seg] > 0 ? (
              <span key={seg} className={`sentiment-label ${seg}`}>
                {sentiments[seg]} {seg}
              </span>
            ) : null
          )}
        </div>
      )}
    </div>
  );
}
