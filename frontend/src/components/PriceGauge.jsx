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

// SVG arc path for a donut segment from ratio startR to endR (0 = left, 1 = right)
function arcPath(cx, cy, innerR, outerR, startRatio, endRatio) {
  const s1 = arcPoint(cx, cy, outerR, startRatio);
  const s2 = arcPoint(cx, cy, outerR, endRatio);
  const s3 = arcPoint(cx, cy, innerR, endRatio);
  const s4 = arcPoint(cx, cy, innerR, startRatio);
  // largeArc flag: the arc spans more than 180° when ratio range > 0.5
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

  const fillRatio = Math.min(1, Math.max(0, (optimalPrice - minPrice) / (maxPrice - minPrice)));

  const priceForComment = rawOptimalPrice ?? optimalPrice;
  const rawFillRatio = Math.min(1, Math.max(0, (priceForComment - minPrice) / (maxPrice - minPrice)));

  // Marker for the true recommended price (only shown when different from snapped)
  const showMarker = rawOptimalPrice != null && rawOptimalPrice !== optimalPrice;
  const markerInner = showMarker ? arcPoint(cx, cy, innerRadius + 2, rawFillRatio) : null;
  const markerOuter = showMarker ? arcPoint(cx, cy, outerRadius - 2, rawFillRatio) : null;

  let markerLabel = null;
  if (showMarker) {
    const outside = arcPoint(cx, cy, outerRadius + 14, rawFillRatio);
    markerLabel = outside.y < 8
      ? arcPoint(cx, cy, innerRadius - 14, rawFillRatio)
      : outside;
  }

  return (
    <div className="price-gauge-container">
      {label && <div className="price-gauge-label">{label}</div>}
      <svg width={300} height={170} viewBox="0 0 300 170">
        {/* Gray background arc (always full semicircle) */}
        <path
          d={arcPath(cx, cy, innerRadius, outerRadius, 0, 1)}
          fill="#e5e7eb"
        />
        {/* Orange fill arc */}
        {fillRatio > 0 && (
          <path
            d={arcPath(cx, cy, innerRadius, outerRadius, 0, fillRatio)}
            fill="#f97316"
          />
        )}

        {/* True recommended price marker */}
        {showMarker && (
          <>
            <line
              x1={markerInner.x}
              y1={markerInner.y}
              x2={markerOuter.x}
              y2={markerOuter.y}
              stroke="#1a1a1a"
              strokeWidth={2.5}
              strokeLinecap="round"
            />
            <text
              x={markerLabel.x}
              y={markerLabel.y}
              textAnchor="middle"
              dominantBaseline="middle"
              style={{ fontSize: "0.65rem", fill: "#1a1a1a", fontWeight: 600 }}
            >
              ${rawOptimalPrice.toFixed(0)}
            </text>
          </>
        )}

        {/* Bold price label at center of arc */}
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
      <p className="price-gauge-comment">{commentOverride ?? getGaugeComment(rawFillRatio, priceForComment, minPrice, maxPrice)}</p>
    </div>
  );
}
