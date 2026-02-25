import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "600", "700", "900"],
  subsets: ["latin"],
});

const techBadges = [
  "FastAPI",
  "React",
  "Mistral-7B",
  "LoRA",
  "pgvector",
  "Cloud Run",
];

export const ClosingScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12 } });

  const ctaOpacity = interpolate(frame, [20, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const ctaY = interpolate(frame, [20, 35], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const badgesOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      className="flex flex-col items-center justify-center"
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
        fontFamily,
        gap: 24,
      }}
    >
      <div
        style={{
          transform: `scale(${logoScale})`,
          fontSize: 56,
          fontWeight: 900,
          color: "white",
          letterSpacing: -2,
        }}
      >
        Focus<span style={{ color: "#228be6" }}>Test</span>
      </div>

      <div
        style={{
          opacity: ctaOpacity,
          transform: `translateY(${ctaY}px)`,
          fontSize: 24,
          fontWeight: 600,
          color: "#228be6",
        }}
      >
        Try FocusTest Today
      </div>

      <div
        className="flex flex-wrap justify-center gap-2"
        style={{ opacity: badgesOpacity, maxWidth: 500 }}
      >
        {techBadges.map((badge, i) => {
          const badgeScale = spring({
            frame: frame - (45 + i * 5),
            fps,
            config: { damping: 200 },
          });
          return (
            <div
              key={badge}
              style={{
                transform: `scale(${badgeScale})`,
                backgroundColor: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.15)",
                borderRadius: 8,
                padding: "6px 14px",
                fontSize: 13,
                color: "#94a3b8",
                fontWeight: 500,
              }}
            >
              {badge}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
