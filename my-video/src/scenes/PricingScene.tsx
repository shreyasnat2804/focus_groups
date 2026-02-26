import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "500", "600", "700", "900"],
  subsets: ["latin"],
});

const PRICING_MODELS = [
  { label: "One-time purchase", color: "#228be6", active: false },
  { label: "Subscription", color: "#228be6", active: true },
  { label: "Upfront + Subscription", color: "#228be6", active: false },
];

// Van Westendorp curve data (simplified)
const VW_CURVES = {
  tooCheap: [
    { x: 0, y: 100 },
    { x: 30, y: 50 },
    { x: 80, y: 5 },
    { x: 120, y: 0 },
  ],
  bargain: [
    { x: 0, y: 100 },
    { x: 20, y: 100 },
    { x: 50, y: 50 },
    { x: 90, y: 0 },
  ],
  expensive: [
    { x: 40, y: 0 },
    { x: 80, y: 30 },
    { x: 120, y: 80 },
    { x: 160, y: 100 },
  ],
  tooExpensive: [
    { x: 60, y: 0 },
    { x: 100, y: 10 },
    { x: 140, y: 60 },
    { x: 170, y: 100 },
  ],
};

const CURVE_COLORS: Record<string, string> = {
  tooCheap: "#22c55e",
  bargain: "#84cc16",
  expensive: "#f59e0b",
  tooExpensive: "#ef4444",
};

const CURVE_LABELS: Record<string, string> = {
  tooCheap: "Too Cheap",
  bargain: "Bargain",
  expensive: "Expensive",
  tooExpensive: "Too Expensive",
};

// Gabor-Granger demand curve data (centered around $39.99/mo, range ~$28-$56)
const GG_POINTS = [
  { x: 0, y: 95 },
  { x: 20, y: 95 },
  { x: 45, y: 92 },
  { x: 70, y: 80 },
  { x: 90, y: 55 },
  { x: 110, y: 30 },
  { x: 135, y: 10 },
  { x: 155, y: 3 },
  { x: 170, y: 0 },
];

function pointsToSmoothPath(points: { x: number; y: number }[]): string {
  if (points.length < 2) return "";
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx1 = prev.x + (curr.x - prev.x) * 0.5;
    const cpy1 = prev.y;
    const cpx2 = prev.x + (curr.x - prev.x) * 0.5;
    const cpy2 = curr.y;
    d += ` C ${cpx1} ${cpy1}, ${cpx2} ${cpy2}, ${curr.x} ${curr.y}`;
  }
  return d;
}

export const PricingScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Header animation
  const headerOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Pricing model tabs animation
  const tabsScale = spring({
    frame: frame - 8,
    fps,
    config: { damping: 200 },
  });

  // Card entrance
  const cardScale = spring({
    frame: frame - 15,
    fps,
    config: { damping: 200 },
  });

  // Recommended price animation
  const priceOpacity = interpolate(frame, [30, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const priceScale = spring({
    frame: frame - 30,
    fps,
    config: { damping: 15, stiffness: 80 },
  });

  // VW chart draw progress
  const chartProgress = interpolate(frame, [40, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  // GG chart (right side)
  const ggCardScale = spring({
    frame: frame - 55,
    fps,
    config: { damping: 200 },
  });
  const ggProgress = interpolate(frame, [65, 120], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  // Acceptable range badge
  const rangeBadgeOpacity = interpolate(frame, [90, 105], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const CHART_W = 170;
  const CHART_H = 100;

  return (
    <AbsoluteFill
      className="flex flex-col items-center justify-center"
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
        fontFamily,
        gap: 16,
        padding: "36px 60px",
      }}
    >
      {/* Header */}
      <div
        style={{
          opacity: headerOpacity,
          fontSize: 28,
          fontWeight: 700,
          color: "white",
          alignSelf: "flex-start",
        }}
      >
        Pricing Analysis
      </div>

      {/* Pricing model selector tabs */}
      <div
        className="flex gap-2"
        style={{
          alignSelf: "flex-start",
          transform: `scale(${tabsScale})`,
          transformOrigin: "left center",
        }}
      >
        {PRICING_MODELS.map((model, i) => (
          <div
            key={i}
            style={{
              padding: "6px 16px",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              backgroundColor: model.active ? "#228be6" : "white",
              color: model.active ? "white" : "#475569",
              border: model.active ? "none" : "1px solid #e2e8f0",
            }}
          >
            {model.label}
          </div>
        ))}
      </div>

      {/* Main content - two cards side by side */}
      <div className="flex gap-4" style={{ width: "100%", flex: 1 }}>
        {/* Left card - Van Westendorp */}
        <div
          style={{
            flex: 1,
            backgroundColor: "white",
            borderRadius: 12,
            padding: 20,
            transform: `scale(${cardScale})`,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Recommended price */}
          <div
            style={{
              textAlign: "center",
              marginBottom: 8,
              opacity: priceOpacity,
            }}
          >
            <div
              style={{
                fontSize: 10,
                fontWeight: 600,
                color: "#228be6",
                letterSpacing: 1.5,
                marginBottom: 2,
              }}
            >
              RECOMMENDED PRICE
            </div>
            <div
              style={{
                fontSize: 36,
                fontWeight: 900,
                color: "#0f172a",
                transform: `scale(${priceScale})`,
              }}
            >
              $39.99/mo
            </div>
            <div style={{ fontSize: 11, color: "#94a3b8" }}>
              Acceptable range: $28 – $52
            </div>
          </div>

          {/* VW Chart Title */}
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "#0f172a",
              marginBottom: 6,
            }}
          >
            Van Westendorp Price Sensitivity
          </div>

          {/* Acceptable Range Badge */}
          <div
            style={{
              opacity: rangeBadgeOpacity,
              display: "inline-flex",
              alignSelf: "flex-start",
              backgroundColor: "#dcfce7",
              border: "1px solid #bbf7d0",
              borderRadius: 8,
              padding: "4px 10px",
              marginBottom: 6,
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 9,
                  fontWeight: 600,
                  color: "#22c55e",
                  letterSpacing: 1,
                }}
              >
                ACCEPTABLE RANGE
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#0f172a" }}>
                $28 – $52
              </div>
            </div>
          </div>

          {/* Van Westendorp SVG Chart */}
          <div style={{ flex: 1, position: "relative" }}>
            <svg
              viewBox={`0 0 ${CHART_W} ${CHART_H + 20}`}
              style={{ width: "100%", height: "100%" }}
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Grid lines */}
              {[0, 25, 50, 75, 100].map((pct) => (
                <line
                  key={pct}
                  x1={0}
                  y1={CHART_H - (pct / 100) * CHART_H}
                  x2={CHART_W}
                  y2={CHART_H - (pct / 100) * CHART_H}
                  stroke="#f1f5f9"
                  strokeWidth={0.5}
                />
              ))}

              {/* Animated curves */}
              {Object.entries(VW_CURVES).map(([key, points]) => {
                const scaledPoints = points.map((p) => ({
                  x: (p.x / 170) * CHART_W,
                  y: CHART_H - (p.y / 100) * CHART_H,
                }));
                const pathD = pointsToSmoothPath(scaledPoints);

                // Animate by clipping
                const clipWidth = chartProgress * CHART_W;

                return (
                  <g key={key}>
                    <clipPath id={`clip-${key}`}>
                      <rect x={0} y={0} width={clipWidth} height={CHART_H + 20} />
                    </clipPath>
                    <path
                      d={pathD}
                      fill="none"
                      stroke={CURVE_COLORS[key]}
                      strokeWidth={2}
                      clipPath={`url(#clip-${key})`}
                    />
                  </g>
                );
              })}

              {/* Y axis labels */}
              {[0, 25, 50, 75, 100].map((pct) => (
                <text
                  key={pct}
                  x={-2}
                  y={CHART_H - (pct / 100) * CHART_H + 3}
                  fontSize={5}
                  fill="#94a3b8"
                  textAnchor="end"
                >
                  {pct}%
                </text>
              ))}
            </svg>
          </div>

          {/* Legend */}
          <div
            className="flex gap-3 justify-center"
            style={{
              marginTop: 4,
              opacity: interpolate(frame, [80, 95], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            {Object.entries(CURVE_LABELS).map(([key, label]) => (
              <div key={key} className="flex items-center gap-1">
                <div
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: CURVE_COLORS[key],
                  }}
                />
                <span style={{ fontSize: 9, color: "#64748b" }}>{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right card - Gabor-Granger */}
        <div
          style={{
            flex: 1,
            backgroundColor: "white",
            borderRadius: 12,
            padding: 20,
            transform: `scale(${ggCardScale})`,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "#0f172a",
              marginBottom: 12,
            }}
          >
            Gabor-Granger Demand Curve
          </div>

          {/* GG Chart */}
          <div style={{ flex: 1, position: "relative" }}>
            <svg
              viewBox={`0 0 ${CHART_W} ${CHART_H + 20}`}
              style={{ width: "100%", height: "100%" }}
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Grid lines */}
              {[0, 30, 60, 90].map((pct) => (
                <line
                  key={pct}
                  x1={0}
                  y1={CHART_H - (pct / 100) * CHART_H}
                  x2={CHART_W}
                  y2={CHART_H - (pct / 100) * CHART_H}
                  stroke="#f1f5f9"
                  strokeWidth={0.5}
                />
              ))}
              {[0, 30, 60, 90].map((pct) => (
                <text
                  key={pct}
                  x={-2}
                  y={CHART_H - (pct / 100) * CHART_H + 3}
                  fontSize={5}
                  fill="#94a3b8"
                  textAnchor="end"
                >
                  {pct}%
                </text>
              ))}

              {/* Demand curve with fill */}
              {(() => {
                const scaledPoints = GG_POINTS.map((p) => ({
                  x: (p.x / 170) * CHART_W,
                  y: CHART_H - (p.y / 100) * CHART_H,
                }));
                const curveD = pointsToSmoothPath(scaledPoints);
                const clipWidth = ggProgress * CHART_W;

                // Area fill path
                const lastPoint = scaledPoints[scaledPoints.length - 1];
                const firstPoint = scaledPoints[0];
                const areaD = `${curveD} L ${lastPoint.x} ${CHART_H} L ${firstPoint.x} ${CHART_H} Z`;

                return (
                  <g>
                    <clipPath id="clip-gg">
                      <rect x={0} y={0} width={clipWidth} height={CHART_H + 20} />
                    </clipPath>
                    <path
                      d={areaD}
                      fill="#228be620"
                      clipPath="url(#clip-gg)"
                    />
                    <path
                      d={curveD}
                      fill="none"
                      stroke="#228be6"
                      strokeWidth={2}
                      clipPath="url(#clip-gg)"
                    />
                  </g>
                );
              })()}

              {/* Price axis labels */}
              {["$28", "$35", "$40", "$48", "$56"].map((label, i) => (
                <text
                  key={label}
                  x={(i / 4) * CHART_W}
                  y={CHART_H + 12}
                  fontSize={5}
                  fill="#94a3b8"
                  textAnchor="middle"
                >
                  {label}
                </text>
              ))}
            </svg>
          </div>

          {/* Personas analyzed badge */}
          <div
            style={{
              marginTop: 8,
              opacity: interpolate(frame, [100, 115], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            <div
              style={{
                fontSize: 11,
                color: "#228be6",
                fontWeight: 500,
              }}
            >
              5 personas analyzed
            </div>
          </div>

          {/* Segment selector */}
          <div
            className="flex items-center gap-3"
            style={{
              marginTop: 8,
              opacity: interpolate(frame, [110, 125], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            <div>
              <div
                style={{ fontSize: 10, color: "#64748b", marginBottom: 2 }}
              >
                Segment by
              </div>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 500,
                  color: "#0f172a",
                  backgroundColor: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: 6,
                  padding: "4px 10px",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                Income bracket
                <span style={{ fontSize: 8, color: "#94a3b8" }}>▼</span>
              </div>
            </div>
            <div
              style={{
                marginLeft: "auto",
                backgroundColor: "#228be6",
                color: "white",
                fontSize: 11,
                fontWeight: 600,
                padding: "6px 14px",
                borderRadius: 6,
              }}
            >
              Re-run Analysis
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
