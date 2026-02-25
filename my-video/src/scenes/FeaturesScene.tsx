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

const features = [
  { icon: "\u{1F50D}", title: "Session Search", desc: "Find past focus groups instantly" },
  { icon: "\u{1F3AF}", title: "Sector Filter", desc: "Tech, Financial, Political" },
  { icon: "\u{1F4E4}", title: "Export Results", desc: "Download as CSV or PDF" },
  { icon: "\u{1F5D1}\uFE0F", title: "Soft Delete", desc: "Recover deleted sessions" },
  { icon: "\u{1F504}", title: "Rerun Groups", desc: "Iterate on your pitch" },
  { icon: "\u{1F465}", title: "Custom Personas", desc: "Tune demographic mix" },
];

export const FeaturesScene: React.FC = () => {
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
        gap: 32,
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
        Everything You Need
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 200px)",
          gap: 16,
        }}
      >
        {features.map((f, i) => {
          const row = Math.floor(i / 3);
          const col = i % 3;
          const delay = 10 + (row * 3 + col) * 8;
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
                borderRadius: 12,
                padding: "20px 16px",
                border: "1px solid rgba(255,255,255,0.1)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: 32 }}>{f.icon}</div>
              <div
                style={{
                  fontSize: 15,
                  fontWeight: 700,
                  color: "white",
                  marginTop: 8,
                }}
              >
                {f.title}
              </div>
              <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                {f.desc}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
