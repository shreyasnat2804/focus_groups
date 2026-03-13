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

const steps = [
  {
    label: "Real Opinions",
    desc: "We collect millions of real\nviews from online communities",
    color: "#ff4500",
  },
  {
    label: "Demographic Profiles",
    desc: "Each opinion is tagged by\nage, location, and interests",
    color: "#8b5cf6",
  },
  {
    label: "Fine-Tuned Models",
    desc: "Sector-specific AI trained\non this real-world data",
    color: "#f59e0b",
  },
  {
    label: "Your Focus Group",
    desc: "Personas that respond like\nreal people — because they\nlearned from real people",
    color: "#228be6",
  },
];

export const ArchitectureScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headingOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      className="flex flex-col items-center justify-center"
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        fontFamily,
        gap: 36,
      }}
    >
      <div
        style={{
          opacity: headingOpacity,
          fontSize: 32,
          fontWeight: 700,
          color: "white",
          textAlign: "center",
        }}
      >
        Not a GPT wrapper.{" "}
        <span style={{ color: "#228be6" }}>Trained on real data.</span>
      </div>
      <div
        style={{
          opacity: headingOpacity,
          fontSize: 16,
          color: "#94a3b8",
          marginTop: -20,
          textAlign: "center",
        }}
      >
        Our models learn from actual human opinions — not generic prompts
      </div>
      <div className="flex items-start" style={{ gap: 12 }}>
        {steps.map((step, i) => {
          const delay = 15 + i * 20;
          const nodeScale = spring({
            frame: frame - delay,
            fps,
            config: { damping: 15, stiffness: 150 },
          });
          const nodeOpacity = interpolate(frame - delay, [0, 8], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          const arrowOpacity =
            i < steps.length - 1
              ? interpolate(frame - delay - 10, [0, 10], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })
              : 0;

          return (
            <div key={i} className="flex items-center" style={{ gap: 12 }}>
              <div
                className="flex flex-col items-center"
                style={{
                  transform: `scale(${nodeScale})`,
                  opacity: nodeOpacity,
                  width: 190,
                }}
              >
                <div
                  style={{
                    width: 40,
                    height: 4,
                    borderRadius: 2,
                    backgroundColor: step.color,
                    marginBottom: 12,
                  }}
                />
                <div
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: "white",
                    textAlign: "center",
                    marginBottom: 8,
                  }}
                >
                  {step.label}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "#94a3b8",
                    textAlign: "center",
                    lineHeight: 1.5,
                    whiteSpace: "pre-line",
                  }}
                >
                  {step.desc}
                </div>
              </div>
              {i < steps.length - 1 && (
                <svg
                  width={20}
                  height={16}
                  viewBox="0 0 20 16"
                  style={{ opacity: arrowOpacity, marginBottom: 30 }}
                >
                  <line
                    x1="0"
                    y1="8"
                    x2="14"
                    y2="8"
                    stroke="#475569"
                    strokeWidth="2"
                  />
                  <polygon points="14,3 20,8 14,13" fill="#475569" />
                </svg>
              )}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
