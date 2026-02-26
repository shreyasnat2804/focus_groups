import { PieChart, Pie, Cell } from "recharts";

function getGaugeComment(fillRatio, optimalPrice, minPrice, maxPrice) {
  if (minPrice === maxPrice) return "Only one price point tested. Try adding more.";
  if (optimalPrice <= minPrice) return "At the floor. Consider testing lower prices.";
  if (optimalPrice >= maxPrice) return "You can go higher. The ceiling has not been found yet.";
  if (fillRatio < 0.25) return "Priced conservatively. There is likely room to move up.";
  if (fillRatio < 0.5) return "Below midpoint. A moderate price increase may work well.";
  if (fillRatio < 0.75) return "Well-positioned near the sweet spot for this audience.";
  return "Near the top of your range. Strong pricing power detected.";
}

export default function PriceGauge({ optimalPrice, minPrice, maxPrice, label, commentOverride }) {
  // fillRatio clamps naturally: out-of-range prices pin the arc to 0% or 100%
  const fillRatio = Math.min(
    1,
    Math.max(0, (optimalPrice - minPrice) / (maxPrice - minPrice))
  );

  const data = [
    { value: fillRatio },
    { value: 1 - fillRatio },
  ];

  const cx = 150;
  const cy = 130;
  const innerRadius = 80;
  const outerRadius = 120;

  return (
    <div className="price-gauge-container">
      {label && <div className="price-gauge-label">{label}</div>}
      <PieChart width={300} height={170}>
        <Pie
          data={data}
          cx={cx}
          cy={cy}
          startAngle={180}
          endAngle={0}
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          dataKey="value"
          isAnimationActive={false}
        >
          <Cell fill="#f97316" />
          <Cell fill="#e5e7eb" />
        </Pie>
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
      </PieChart>
      <div className="price-gauge-range">
        <span>${minPrice.toFixed(0)}</span>
        <span>${maxPrice.toFixed(0)}</span>
      </div>
      <p className="price-gauge-comment">{commentOverride ?? getGaugeComment(fillRatio, optimalPrice, minPrice, maxPrice)}</p>
    </div>
  );
}
