import { spring, useCurrentFrame, useVideoConfig } from "remotion";

type MockCardProps = {
  children: React.ReactNode;
  delay?: number;
};

export const MockCard: React.FC<MockCardProps> = ({ children, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
  });

  const opacity = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
    durationInFrames: 20,
  });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        opacity,
        backgroundColor: "white",
        borderRadius: 12,
        padding: 20,
        boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
        border: "1px solid #e2e8f0",
      }}
    >
      {children}
    </div>
  );
};
