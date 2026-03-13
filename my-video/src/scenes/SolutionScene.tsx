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

const valueProps = [
  { text: "Instant feedback on any idea" },
  { text: "Built on real opinions from real people" },
  { text: "Scale to any audience size" },
  { text: "Personas grounded in actual demographic data" },
];

export const SolutionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headingOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const headingY = interpolate(frame, [0, 20], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      className="flex flex-col items-center justify-center"
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
        fontFamily,
        gap: 36,
      }}
    >
      <div
        style={{
          opacity: headingOpacity,
          transform: `translateY(${headingY}px)`,
          fontSize: 36,
          fontWeight: 700,
          color: "white",
          textAlign: "center",
        }}
      >
        Test your pitch with{" "}
        <span style={{ color: "#228be6" }}>real audience insights</span>
      </div>
      <div className="flex flex-col gap-4" style={{ width: 520 }}>
        {valueProps.map((vp, i) => {
          const delay = 20 + i * 10;
          const slideX = spring({
            frame: frame - delay,
            fps,
            config: { damping: 200 },
          });
          const x = interpolate(slideX, [0, 1], [-40, 0]);
          const opacity = interpolate(slideX, [0, 1], [0, 1]);
          return (
            <div
              key={i}
              className="flex items-center gap-3"
              style={{
                transform: `translateX(${x}px)`,
                opacity,
                backgroundColor: "rgba(255,255,255,0.05)",
                borderRadius: 12,
                padding: "14px 20px",
                border: "1px solid rgba(255,255,255,0.1)",
              }}
            >
              <div
                className="flex items-center justify-center"
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 14,
                  backgroundColor: "#228be620",
                  flexShrink: 0,
                }}
              >
                <svg width={14} height={14} viewBox="0 0 14 14" fill="none">
                  <path
                    d="M2 7L5.5 10.5L12 3.5"
                    stroke="#228be6"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <span style={{ fontSize: 18, color: "#e2e8f0", fontWeight: 600 }}>
                {vp.text}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
