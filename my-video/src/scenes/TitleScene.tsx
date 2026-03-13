import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700", "900"],
  subsets: ["latin"],
});

export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12 } });

  const taglineOpacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const taglineY = interpolate(frame, [20, 40], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      className="flex flex-col items-center justify-center"
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
        fontFamily,
      }}
    >
      <div
        style={{
          transform: `scale(${logoScale})`,
          fontSize: 72,
          fontWeight: 900,
          color: "white",
          letterSpacing: -2,
        }}
      >
        Focus<span style={{ color: "#228be6" }}>Test</span>
      </div>
      <div
        style={{
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px)`,
          fontSize: 24,
          color: "#94a3b8",
          marginTop: 16,
          fontWeight: 400,
        }}
      >
        AI-Powered Synthetic Focus Groups
      </div>
    </AbsoluteFill>
  );
};
