import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";

export default function VanWestendorpChart({ curves, pricePoints }) {
  if (!curves || !curves.price_points || curves.price_points.length === 0) {
    return <p>No Van Westendorp data available.</p>;
  }

  // Transform curves into recharts data format
  const data = curves.price_points.map((price, i) => ({
    price: Math.round(price),
    "Too Cheap": curves.too_cheap[i],
    Bargain: curves.cheap[i],
    Expensive: curves.expensive[i],
    "Too Expensive": curves.too_expensive[i],
  }));

  const optimal = pricePoints?.optimal_price;
  const [rangeLow, rangeHigh] = pricePoints?.acceptable_range || [];

  return (
    <div className="wtp-chart-container">
      <h3>Van Westendorp Price Sensitivity</h3>
      <div className="wtp-price-summary">
        {optimal != null && (
          <div className="wtp-price-badge optimal">
            <span className="wtp-price-badge-label">Optimal Price</span>
            <span className="wtp-price-badge-value">${optimal.toFixed(0)}</span>
          </div>
        )}
        {rangeLow != null && rangeHigh != null && (
          <div className="wtp-price-badge range">
            <span className="wtp-price-badge-label">Acceptable Range</span>
            <span className="wtp-price-badge-value">
              ${rangeLow.toFixed(0)} &ndash; ${rangeHigh.toFixed(0)}
            </span>
          </div>
        )}
      </div>
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
          <XAxis
            dataKey="price"
            tickFormatter={(v) => `$${v}`}
            fontSize={12}
          />
          <YAxis
            tickFormatter={(v) => `${v}%`}
            domain={[0, 100]}
            fontSize={12}
          />
          <Tooltip
            itemSorter={() => 0}
            formatter={(value) => `${value.toFixed(1)}%`}
            labelFormatter={(label) => `$${label}`}
          />
          <Legend />
          {rangeLow != null && rangeHigh != null && (
            <ReferenceArea
              x1={Math.round(rangeLow)}
              x2={Math.round(rangeHigh)}
              fill="#27ae60"
              fillOpacity={0.08}
            />
          )}
          {optimal != null && (
            <ReferenceLine
              x={Math.round(optimal)}
              stroke="#2c3e50"
              strokeDasharray="5 3"
              strokeWidth={1.5}
            />
          )}
          <Line type="monotone" dataKey="Too Cheap" stroke="#2b8a3e" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="Bargain" stroke="#82c91e" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="Expensive" stroke="#f39c12" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="Too Expensive" stroke="#e03131" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
