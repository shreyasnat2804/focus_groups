import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "600", "700"],
  subsets: ["latin"],
});

const personas = [
  {
    hat: "Tech Early Adopter",
    color: "#228be6",
    hatShape: "baseball", // forward-facing cap
    quote: "I'd pay for this day one.",
    demographic: "25-34, Urban, $80k+",
  },
  {
    hat: "Budget-Conscious Parent",
    color: "#f59e0b",
    hatShape: "sunhat", // wide brim
    quote: "Show me the value first.",
    demographic: "35-44, Suburban, $50k",
  },
  {
    hat: "Skeptical Executive",
    color: "#8b5cf6",
    hatShape: "tophat", // formal
    quote: "What's the competitive moat?",
    demographic: "45-55, Corporate, $150k+",
  },
];

// Background bar chart data — demographic reach
const chartBars = [
  { label: "18-24", value: 0.35, color: "#228be620" },
  { label: "25-34", value: 0.72, color: "#228be640" },
  { label: "35-44", value: 0.58, color: "#228be630" },
  { label: "45-54", value: 0.45, color: "#228be625" },
  { label: "55+", value: 0.22, color: "#228be615" },
];

const HatIcon: React.FC<{
  shape: string;
  color: string;
  scale: number;
}> = ({ shape, color, scale }) => {
  return (
    <svg
      width={80}
      height={60}
      viewBox="0 0 80 60"
      style={{ transform: `scale(${scale})` }}
    >
      {shape === "baseball" && (
        <>
          {/* Brim */}
          <ellipse cx={40} cy={48} rx={38} ry={8} fill={color} />
          {/* Crown */}
          <path
            d="M12 48 Q12 18 40 14 Q68 18 68 48"
            fill={color}
            opacity={0.85}
          />
          {/* Button on top */}
          <circle cx={40} cy={16} r={3} fill="white" opacity={0.6} />
        </>
      )}
      {shape === "sunhat" && (
        <>
          {/* Wide brim */}
          <ellipse cx={40} cy={48} rx={40} ry={10} fill={color} />
          {/* Dome */}
          <ellipse cx={40} cy={36} rx={22} ry={16} fill={color} opacity={0.85} />
          {/* Ribbon */}
          <rect x={18} y={40} width={44} height={5} rx={2} fill="white" opacity={0.3} />
        </>
      )}
      {shape === "tophat" && (
        <>
          {/* Brim */}
          <ellipse cx={40} cy={50} rx={36} ry={8} fill={color} />
          {/* Tall crown */}
          <rect x={22} y={10} width={36} height={42} rx={4} fill={color} opacity={0.85} />
          {/* Band */}
          <rect x={22} y={40} width={36} height={5} rx={2} fill="white" opacity={0.3} />
          {/* Top */}
          <ellipse cx={40} cy={12} rx={18} ry={4} fill={color} />
        </>
      )}
    </svg>
  );
};

export const LoraScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title fade in
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleY = interpolate(frame, [0, 20], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtitle
  const subtitleOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Which persona is active (cycle through them)
  const PERSONA_START = 40;
  const PERSONA_DURATION = 55; // frames per persona

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        fontFamily,
        overflow: "hidden",
      }}
    >
      {/* Background animated bar chart */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 300,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
          gap: 40,
          padding: "0 80px",
          opacity: 0.35,
        }}
      >
        {chartBars.map((bar, i) => {
          const barProgress = spring({
            frame: frame - 10 - i * 6,
            fps,
            config: { damping: 200 },
          });
          const barHeight = interpolate(barProgress, [0, 1], [0, bar.value * 240]);
          return (
            <div
              key={i}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 8,
              }}
            >
              <div
                style={{
                  width: 60,
                  height: barHeight,
                  backgroundColor: "#228be6",
                  borderRadius: "6px 6px 0 0",
                  opacity: 0.4,
                }}
              />
              <span
                style={{
                  fontSize: 11,
                  color: "#475569",
                  fontWeight: 600,
                  opacity: interpolate(frame, [30, 45], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  }),
                }}
              >
                {bar.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Main content */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: 24,
          zIndex: 1,
          position: "relative",
        }}
      >
        {/* Title */}
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            fontSize: 32,
            fontWeight: 700,
            color: "white",
            textAlign: "center",
          }}
        >
          One AI, many{" "}
          <span style={{ color: "#228be6" }}>hats</span>
        </div>

        {/* Subtitle */}
        <div
          style={{
            opacity: subtitleOpacity,
            fontSize: 16,
            color: "#94a3b8",
            textAlign: "center",
            marginTop: -12,
          }}
        >
          LoRA fine-tuning lets a single model become any persona
        </div>

        {/* AI + Hat visual */}
        <div
          style={{
            position: "relative",
            width: 120,
            height: 120,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginTop: 8,
          }}
        >
          {/* AI circle */}
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: 40,
              background: "linear-gradient(135deg, #1e3a5f, #334155)",
              border: "2px solid #475569",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              fontWeight: 700,
              color: "#94a3b8",
              letterSpacing: 2,
            }}
          >
            AI
          </div>

          {/* Hats — each appears and fades */}
          {personas.map((p, i) => {
            const personaFrame = frame - PERSONA_START - i * PERSONA_DURATION;
            const hatDrop = spring({
              frame: Math.max(0, personaFrame),
              fps,
              config: { damping: 12, stiffness: 120 },
            });
            const hatY = interpolate(hatDrop, [0, 1], [-50, -42]);
            const hatOpacity = interpolate(
              personaFrame,
              [0, 8, PERSONA_DURATION - 12, PERSONA_DURATION],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            );

            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  top: hatY,
                  left: "50%",
                  transform: "translateX(-50%)",
                  opacity: hatOpacity,
                }}
              >
                <HatIcon shape={p.hatShape} color={p.color} scale={1} />
              </div>
            );
          })}
        </div>

        {/* Persona cards — appear one at a time */}
        <div style={{ display: "flex", gap: 16, marginTop: 12 }}>
          {personas.map((p, i) => {
            const personaFrame = frame - PERSONA_START - i * PERSONA_DURATION;
            const cardScale = spring({
              frame: Math.max(0, personaFrame - 5),
              fps,
              config: { damping: 200 },
            });
            const cardOpacity = interpolate(
              personaFrame,
              [0, 10, PERSONA_DURATION - 12, PERSONA_DURATION],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            );

            return (
              <div
                key={i}
                style={{
                  width: 220,
                  backgroundColor: "rgba(255,255,255,0.06)",
                  border: `1px solid ${p.color}40`,
                  borderRadius: 12,
                  padding: "14px 16px",
                  transform: `scale(${cardScale})`,
                  opacity: cardOpacity,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: 5,
                      backgroundColor: p.color,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 700,
                      color: p.color,
                    }}
                  >
                    {p.hat}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 14,
                    color: "#e2e8f0",
                    fontStyle: "italic",
                    lineHeight: 1.4,
                  }}
                >
                  "{p.quote}"
                </div>
                <div style={{ fontSize: 11, color: "#64748b" }}>
                  {p.demographic}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
