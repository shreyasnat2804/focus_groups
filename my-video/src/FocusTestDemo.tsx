import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { TitleScene } from "./scenes/TitleScene";
import { ProblemScene } from "./scenes/ProblemScene";
import { SolutionScene } from "./scenes/SolutionScene";
import { ArchitectureScene } from "./scenes/ArchitectureScene";
import { PitchDemoScene } from "./scenes/PitchDemoScene";
import { ResultsDemoScene } from "./scenes/ResultsDemoScene";
import { FeaturesScene } from "./scenes/FeaturesScene";
import { ClosingScene } from "./scenes/ClosingScene";
import { LoraScene } from "./scenes/LoraScene";
import { PricingScene } from "./scenes/PricingScene";

const TRANSITION_DURATION = 15;
const fadeTransition = fade();
const fadeTiming = linearTiming({ durationInFrames: TRANSITION_DURATION });

const scenes = [
  { component: TitleScene, duration: 120 },
  { component: ProblemScene, duration: 150 },
  { component: SolutionScene, duration: 150 },
  { component: ArchitectureScene, duration: 180 },
  { component: LoraScene, duration: 210 },
  { component: PitchDemoScene, duration: 180 },
  { component: ResultsDemoScene, duration: 180 },
  { component: PricingScene, duration: 210 },
  { component: FeaturesScene, duration: 150 },
  { component: ClosingScene, duration: 120 },
];

// Total = sum(durations) - (numTransitions * transitionDuration)
// = 1230 - (7 * 15) = 1230 - 105 = 1125 frames
export const TOTAL_DURATION = scenes.reduce((sum, s) => sum + s.duration, 0) -
  (scenes.length - 1) * TRANSITION_DURATION;

export const FocusTestDemo: React.FC = () => {
  return (
    <TransitionSeries>
      {scenes.map((scene, i) => {
        const Scene = scene.component;
        return [
          <TransitionSeries.Sequence
            key={`scene-${i}`}
            durationInFrames={scene.duration}
          >
            <Scene />
          </TransitionSeries.Sequence>,
          i < scenes.length - 1 ? (
            <TransitionSeries.Transition
              key={`transition-${i}`}
              presentation={fadeTransition}
              timing={fadeTiming}
            />
          ) : null,
        ];
      })}
    </TransitionSeries>
  );
};
