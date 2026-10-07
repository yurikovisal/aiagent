import { Composition } from "remotion";
import { MezaTeaser } from "./MezaTeaser";
import { DURATION_S, FPS, HEIGHT, WIDTH } from "./timeline";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MezaTeaser"
      component={MezaTeaser}
      durationInFrames={DURATION_S * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />
  );
};
