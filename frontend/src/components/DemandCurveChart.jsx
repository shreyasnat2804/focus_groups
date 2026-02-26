import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const SEGMENT_COLORS = [
  "#e74c3c",
  "#3498db",
  "#27ae60",
  "#f39c12",
  "#8e44ad",
  "#1abc9c",
];

function formatPriceLabel(price, pricingModel, hybridTiers) {
  if (pricingModel === "hybrid" && hybridTiers) {
    const tier = hybridTiers.find((t) => t.total_12m === price);
    if (tier) return `$${tier.upfront} + $${tier.monthly}/mo`;
  }
  if (pricingModel === "subscription") return `$${price}/mo`;
  return `$${price}`;
}

export default function DemandCurveChart({
  demandCurve, segmentDemand, segmentDimension,
  pricingModel = "one_time", hybridTiers,
}) {
  if (!demandCurve || !demandCurve.price_points) {
    return <p>No demand data available.</p>;
  }

  // Overall demand chart data
  const overallData = demandCurve.price_points.map((price, i) => ({
    price,
    label: formatPriceLabel(price, pricingModel, hybridTiers),
    "Would Buy": demandCurve.demand_pct[i],
  }));

  // Segmented demand data
  const hasSegments = segmentDemand && Object.keys(segmentDemand).length > 0;
  const segmentNames = hasSegments ? Object.keys(segmentDemand).sort() : [];

  let segmentData = [];
  if (hasSegments) {
    const firstSeg = segmentDemand[segmentNames[0]];
    segmentData = firstSeg.price_points.map((price, i) => {
      const point = { price };
      for (const name of segmentNames) {
        point[name] = segmentDemand[name].demand_pct[i];
      }
      return point;
    });
  }

  return (
    <div className="wtp-chart-container">
      <h3>Gabor-Granger Demand Curve</h3>

      {/* Overall demand */}
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={overallData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
          <XAxis
            dataKey="label"
            fontSize={12}
          />
          <YAxis
            tickFormatter={(v) => `${v}%`}
            domain={[0, 105]}
            fontSize={12}
          />
          <Tooltip
            formatter={(value) => `${value.toFixed(1)}%`}
          />
          <Area
            type="monotone"
            dataKey="Would Buy"
            stroke="#2980b9"
            fill="#2980b9"
            fillOpacity={0.12}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Demand table */}
      <table className="wtp-demand-table">
        <thead>
          <tr>
            <th>Price</th>
            <th>% Would Buy</th>
          </tr>
        </thead>
        <tbody>
          {demandCurve.price_points.map((price, i) => (
            <tr key={price}>
              <td>{formatPriceLabel(price, pricingModel, hybridTiers)}</td>
              <td>{demandCurve.demand_pct[i].toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Segmented demand */}
      {hasSegments && (
        <>
          <h4>Demand by {segmentDimension?.replace("_", " ") || "segment"}</h4>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={segmentData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis
                dataKey="price"
                tickFormatter={(v) => `$${v}`}
                fontSize={12}
              />
              <YAxis
                tickFormatter={(v) => `${v}%`}
                domain={[0, 105]}
                fontSize={12}
              />
              <Tooltip
                formatter={(value) => `${value.toFixed(1)}%`}
                labelFormatter={(label) => `$${label}`}
              />
              <Legend />
              {segmentNames.map((name, i) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={SEGMENT_COLORS[i % SEGMENT_COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
