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
  { icon: "\u{26A1}", text: "Results in seconds, not weeks" },
  { icon: "\u{1F4B8}", text: "Fraction of the cost" },
  { icon: "\u{1F4CA}", text: "Scale to any sample size" },
  { icon: "\u{1F3AF}", text: "Demographic-targeted AI personas" },
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
        Test your pitch on{" "}
        <span style={{ color: "#228be6" }}>AI personas</span> in seconds
      </div>
      <div className="flex flex-col gap-4" style={{ width: 500 }}>
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
              <span style={{ fontSize: 24 }}>{vp.icon}</span>
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
