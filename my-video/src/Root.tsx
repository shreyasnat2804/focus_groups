import "./index.css";
import { Composition } from "remotion";
import { FocusTestDemo, TOTAL_DURATION } from "./FocusTestDemo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="FocusTestDemo"
        component={FocusTestDemo}
        durationInFrames={TOTAL_DURATION}
        fps={30}
        width={1280}
        height={720}
      />
    </>
  );
};
