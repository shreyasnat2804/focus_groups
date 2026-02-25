import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type Segment = {
  label: string;
  value: number;
  color: string;
};

type SentimentBarProps = {
  segments: Segment[];
  delay?: number;
};

export const SentimentBar: React.FC<SentimentBarProps> = ({
  segments,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const total = segments.reduce((sum, s) => sum + s.value, 0);

  const progress = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
    durationInFrames: 40,
  });

  return (
    <div className="flex flex-col gap-2" style={{ width: "100%" }}>
      <div
        className="flex overflow-hidden"
        style={{ height: 32, borderRadius: 8 }}
      >
        {segments.map((seg, i) => {
          const widthPct = (seg.value / total) * 100;
          const segWidth = interpolate(progress, [0, 1], [0, widthPct]);
          return (
            <div
              key={i}
              style={{
                width: `${segWidth}%`,
                backgroundColor: seg.color,
                height: "100%",
              }}
            />
          );
        })}
      </div>
      <div className="flex justify-between" style={{ fontSize: 12 }}>
        {segments.map((seg, i) => {
          const labelOpacity = interpolate(
            frame - delay,
            [20, 35],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );
          return (
            <div
              key={i}
              className="flex items-center gap-1"
              style={{ opacity: labelOpacity }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: seg.color,
                }}
              />
              <span style={{ color: "#64748b" }}>
                {seg.label} {seg.value}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
