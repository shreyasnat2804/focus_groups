import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { SentimentBar } from "../components/SentimentBar";
import { MockCard } from "../components/MockCard";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

const responses = [
  {
    persona: "Sarah, 28, Tech Professional",
    text: "Love the AI categorization idea. Would definitely try this if it integrates with my bank.",
    sentiment: "Positive",
    sentimentColor: "#22c55e",
  },
  {
    persona: "Mike, 45, Small Business Owner",
    text: "Interesting concept, but I'd need to see how it handles business expenses vs personal.",
    sentiment: "Neutral",
    sentimentColor: "#f59e0b",
  },
];

export const ResultsDemoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const barDelay = 15;

  return (
    <AbsoluteFill
      className="flex flex-col items-center justify-center"
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
        fontFamily,
        gap: 20,
        padding: "40px 80px",
      }}
    >
      <div
        style={{
          opacity: headerOpacity,
          fontSize: 28,
          fontWeight: 700,
          color: "white",
          alignSelf: "flex-start",
        }}
      >
        Focus Group Results
      </div>

      {/* Sentiment overview */}
      <div
        style={{
          width: "100%",
          backgroundColor: "white",
          borderRadius: 12,
          padding: 20,
          opacity: spring({
            frame: frame - 10,
            fps,
            config: { damping: 200 },
          }),
        }}
      >
        <div
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: "#64748b",
            marginBottom: 12,
          }}
        >
          Overall Sentiment
        </div>
        <SentimentBar
          delay={barDelay}
          segments={[
            { label: "Positive", value: 58, color: "#22c55e" },
            { label: "Neutral", value: 28, color: "#f59e0b" },
            { label: "Negative", value: 14, color: "#ef4444" },
          ]}
        />
      </div>

      {/* Response cards */}
      <div className="flex gap-4" style={{ width: "100%" }}>
        {responses.map((r, i) => (
          <MockCard key={i} delay={40 + i * 20}>
            <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
              <span
                style={{ fontSize: 13, fontWeight: 600, color: "#0f172a" }}
              >
                {r.persona}
              </span>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: r.sentimentColor,
                  backgroundColor: r.sentimentColor + "15",
                  padding: "2px 8px",
                  borderRadius: 6,
                }}
              >
                {r.sentiment}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.5 }}>
              {r.text}
            </div>
          </MockCard>
        ))}
      </div>
    </AbsoluteFill>
  );
};
