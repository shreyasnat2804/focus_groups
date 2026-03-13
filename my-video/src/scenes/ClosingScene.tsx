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

  const subOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      className="flex flex-col items-center justify-center"
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
        fontFamily,
        gap: 20,
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
        Real opinions. Real insights. In seconds.
      </div>

      <div
        style={{
          opacity: subOpacity,
          fontSize: 16,
          color: "#64748b",
          textAlign: "center",
          maxWidth: 400,
          lineHeight: 1.6,
        }}
      >
        AI focus groups trained on millions of real human opinions
      </div>
    </AbsoluteFill>
  );
};
