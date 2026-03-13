import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

export const PitchDemoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cardScale = spring({ frame, fps, config: { damping: 200 } });
  const cardOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Typing animation for the pitch text
  const fullText =
    "A new budgeting app that uses AI to categorize your spending and suggest savings goals based on your habits.";
  const charsVisible = Math.min(
    Math.floor(interpolate(frame, [25, 130], [0, fullText.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })),
    fullText.length,
  );
  const typedText = fullText.slice(0, charsVisible);

  // Sector chip appears after typing starts
  const chipOpacity = interpolate(frame, [15, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Submit button appears near end
  const btnOpacity = interpolate(frame, [135, 150], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const btnScale = spring({
    frame: frame - 135,
    fps,
    config: { damping: 200 },
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
          transform: `scale(${cardScale})`,
          opacity: cardOpacity,
          backgroundColor: "white",
          borderRadius: 16,
          padding: 32,
          width: 560,
          boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
        }}
      >
        <div
          style={{
            fontSize: 20,
            fontWeight: 700,
            color: "#0f172a",
            marginBottom: 20,
          }}
        >
          New Focus Group
        </div>

        {/* Sector selector */}
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "#64748b",
              marginBottom: 8,
            }}
          >
            Sector
          </div>
          <div className="flex gap-2">
            {["Tech", "Financial", "Political"].map((s, i) => (
              <div
                key={s}
                style={{
                  opacity: chipOpacity,
                  padding: "6px 16px",
                  borderRadius: 8,
                  fontSize: 14,
                  fontWeight: 500,
                  backgroundColor: i === 0 ? "#228be6" : "#f1f5f9",
                  color: i === 0 ? "white" : "#64748b",
                  border:
                    i === 0
                      ? "1px solid #228be6"
                      : "1px solid #e2e8f0",
                }}
              >
                {s}
              </div>
            ))}
          </div>
        </div>

        {/* Pitch textarea */}
        <div style={{ marginBottom: 20 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "#64748b",
              marginBottom: 8,
            }}
          >
            Your Pitch
          </div>
          <div
            style={{
              backgroundColor: "#f8fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              padding: 16,
              minHeight: 80,
              fontSize: 15,
              color: "#334155",
              lineHeight: 1.5,
            }}
          >
            {typedText}
            <span
              style={{
                opacity: frame % 30 < 15 ? 1 : 0,
                color: "#228be6",
              }}
            >
              |
            </span>
          </div>
        </div>

        {/* Submit button */}
        <div
          style={{
            opacity: btnOpacity,
            transform: `scale(${btnScale})`,
          }}
        >
          <div
            style={{
              backgroundColor: "#228be6",
              color: "white",
              padding: "12px 24px",
              borderRadius: 8,
              fontSize: 15,
              fontWeight: 600,
              textAlign: "center",
            }}
          >
            Run Focus Group
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
