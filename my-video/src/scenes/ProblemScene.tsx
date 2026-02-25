import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});

const problems = [
  { icon: "\u{1F4B0}", text: "Expensive", sub: "$5,000 - $10,000 per session" },
  { icon: "\u{23F3}", text: "Slow", sub: "Weeks to recruit & schedule" },
  { icon: "\u{1F4C9}", text: "Hard to Scale", sub: "Limited sample sizes" },
];

export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headingOpacity = interpolate(frame, [0, 20], [0, 1], {
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
          fontSize: 36,
          fontWeight: 700,
          color: "white",
          textAlign: "center",
        }}
      >
        Traditional focus groups are broken
      </div>
      <div className="flex gap-8">
        {problems.map((p, i) => {
          const delay = 15 + i * 12;
          const scale = spring({
            frame: frame - delay,
            fps,
            config: { damping: 15, stiffness: 150 },
          });
          const opacity = interpolate(frame - delay, [0, 10], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={i}
              className="flex flex-col items-center"
              style={{
                transform: `scale(${scale})`,
                opacity,
                backgroundColor: "rgba(255,255,255,0.05)",
                borderRadius: 16,
                padding: "32px 28px",
                width: 200,
                border: "1px solid rgba(255,255,255,0.1)",
              }}
            >
              <div style={{ fontSize: 48 }}>{p.icon}</div>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  color: "#f87171",
                  marginTop: 12,
                }}
              >
                {p.text}
              </div>
              <div
                style={{ fontSize: 13, color: "#94a3b8", marginTop: 6, textAlign: "center" }}
              >
                {p.sub}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
