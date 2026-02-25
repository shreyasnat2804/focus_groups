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

const pipelineSteps = [
  { label: "Reddit", color: "#ff4500", icon: "\u{1F4E1}" },
  { label: "Tagging", color: "#8b5cf6", icon: "\u{1F3F7}\uFE0F" },
  { label: "Embeddings", color: "#06b6d4", icon: "\u{1F9E0}" },
  { label: "LoRA", color: "#f59e0b", icon: "\u{2699}\uFE0F" },
  { label: "API", color: "#22c55e", icon: "\u{1F310}" },
  { label: "Frontend", color: "#228be6", icon: "\u{1F5A5}\uFE0F" },
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
        gap: 40,
      }}
    >
      <div
        style={{
          opacity: headingOpacity,
          fontSize: 32,
          fontWeight: 700,
          color: "white",
        }}
      >
        How It Works
      </div>
      <div className="flex items-center" style={{ gap: 8 }}>
        {pipelineSteps.map((step, i) => {
          const delay = 10 + i * 15;
          const nodeScale = spring({
            frame: frame - delay,
            fps,
            config: { damping: 15, stiffness: 150 },
          });
          const nodeOpacity = interpolate(frame - delay, [0, 8], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          // Arrow appears after the node
          const arrowOpacity =
            i < pipelineSteps.length - 1
              ? interpolate(frame - delay - 8, [0, 10], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })
              : 0;

          const arrowWidth =
            i < pipelineSteps.length - 1
              ? interpolate(frame - delay - 8, [0, 10], [0, 32], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })
              : 0;

          return (
            <div key={i} className="flex items-center" style={{ gap: 8 }}>
              <div
                className="flex flex-col items-center"
                style={{
                  transform: `scale(${nodeScale})`,
                  opacity: nodeOpacity,
                }}
              >
                <div
                  className="flex items-center justify-center"
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: 16,
                    backgroundColor: step.color + "20",
                    border: `2px solid ${step.color}`,
                  }}
                >
                  <span style={{ fontSize: 28 }}>{step.icon}</span>
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "#cbd5e1",
                    marginTop: 8,
                    fontWeight: 600,
                  }}
                >
                  {step.label}
                </div>
              </div>
              {i < pipelineSteps.length - 1 && (
                <div
                  style={{
                    opacity: arrowOpacity,
                    overflow: "hidden",
                    marginBottom: 20,
                  }}
                >
                  <svg width={arrowWidth} height={16} viewBox="0 0 32 16">
                    <line
                      x1="0"
                      y1="8"
                      x2="24"
                      y2="8"
                      stroke="#475569"
                      strokeWidth="2"
                    />
                    <polygon points="24,3 32,8 24,13" fill="#475569" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
