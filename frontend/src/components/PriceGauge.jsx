function getGaugeComment(fillRatio, optimalPrice, minPrice, maxPrice) {
  if (minPrice === maxPrice) return "Only one price point tested. Try adding more.";
  if (optimalPrice <= minPrice) return "At the floor. Consider testing lower prices.";
  if (optimalPrice >= maxPrice) return "You can go higher. The ceiling has not been found yet.";
  if (fillRatio < 0.25) return "Priced conservatively. There is likely room to move up.";
  if (fillRatio < 0.5) return "Below midpoint. A moderate price increase may work well.";
  if (fillRatio < 0.75) return "Well-positioned near the sweet spot for this audience.";
  return "Near the top of your range. Strong pricing power detected.";
}

function arcPoint(cx, cy, radius, ratio) {
  const angle = (180 - ratio * 180) * (Math.PI / 180);
  return {
    x: cx + radius * Math.cos(angle),
    y: cy - radius * Math.sin(angle),
  };
}

function arcPath(cx, cy, innerR, outerR, startRatio, endRatio) {
  const s1 = arcPoint(cx, cy, outerR, startRatio);
  const s2 = arcPoint(cx, cy, outerR, endRatio);
  const s3 = arcPoint(cx, cy, innerR, endRatio);
  const s4 = arcPoint(cx, cy, innerR, startRatio);
  const large = (endRatio - startRatio) > 0.5 ? 1 : 0;
  return [
    `M ${s1.x} ${s1.y}`,
    `A ${outerR} ${outerR} 0 ${large} 1 ${s2.x} ${s2.y}`,
    `L ${s3.x} ${s3.y}`,
    `A ${innerR} ${innerR} 0 ${large} 0 ${s4.x} ${s4.y}`,
    "Z",
  ].join(" ");
}

export default function PriceGauge({ optimalPrice, minPrice, maxPrice, label, commentOverride, rawOptimalPrice }) {
  const cx = 150;
  const cy = 130;
  const innerRadius = 80;
  const outerRadius = 120;

  // Arc fill always tracks the snapped price
  const fillRatio = Math.min(1, Math.max(0, (optimalPrice - minPrice) / (maxPrice - minPrice)));

  // Comment uses the raw price to avoid false floor/ceiling warnings
  const priceForComment = rawOptimalPrice ?? optimalPrice;
  const commentRatio = Math.min(1, Math.max(0, (priceForComment - minPrice) / (maxPrice - minPrice)));

  return (
    <div className="price-gauge-container">
      {label && <div className="price-gauge-label">{label}</div>}
      <svg width={300} height={170} viewBox="0 0 300 170">
        <path d={arcPath(cx, cy, innerRadius, outerRadius, 0, 1)} fill="#e5e7eb" />
        {fillRatio > 0 && (
          <path d={arcPath(cx, cy, innerRadius, outerRadius, 0, fillRatio)} fill="#f97316" />
        )}
        <text
          x={cx}
          y={cy + 10}
          textAnchor="middle"
          dominantBaseline="middle"
          style={{ fontSize: "1.6rem", fontWeight: 700, fill: "#1a1a1a" }}
        >
          ${optimalPrice.toFixed(0)}
        </text>
        <text
          x={cx}
          y={cy + 34}
          textAnchor="middle"
          dominantBaseline="middle"
          style={{ fontSize: "0.75rem", fill: "#868e96" }}
        >
          optimal price
        </text>
      </svg>
      <div className="price-gauge-range">
        <span>${minPrice.toFixed(0)}</span>
        <span>${maxPrice.toFixed(0)}</span>
      </div>
      {rawOptimalPrice != null && rawOptimalPrice !== optimalPrice && (
        <p className="price-gauge-raw">AI recommendation: ${rawOptimalPrice.toFixed(0)}</p>
      )}
      <p className="price-gauge-comment">{commentOverride ?? getGaugeComment(commentRatio, priceForComment, minPrice, maxPrice)}</p>
    </div>
  );
}
