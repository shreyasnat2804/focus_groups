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
  { component: TitleScene, duration: 150 },
  { component: ProblemScene, duration: 190 },
  { component: SolutionScene, duration: 200 },
  { component: ArchitectureScene, duration: 250 },
  { component: LoraScene, duration: 280 },
  { component: PitchDemoScene, duration: 240 },
  { component: ResultsDemoScene, duration: 250 },
  { component: PricingScene, duration: 280 },
  { component: FeaturesScene, duration: 210 },
  { component: ClosingScene, duration: 150 },
];

// Total = sum(durations) - (numTransitions * transitionDuration)
// = 2200 - (9 * 15) = 2200 - 135 = 2065 frames
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
