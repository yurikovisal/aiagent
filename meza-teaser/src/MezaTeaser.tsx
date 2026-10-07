import { Audio } from "@remotion/media";
import { AbsoluteFill, getStaticFiles, Sequence, staticFile } from "remotion";
import { Flash, Grain, useTime, Vignette } from "./components";
import { ParticleField } from "./particles/ParticleField";
import { Final } from "./scenes/Final";
import { Human } from "./scenes/Human";
import { MezaAwakens } from "./scenes/MezaAwakens";
import { Unleashed } from "./scenes/Unleashed";
import { f, T } from "./timeline";
import { FontGate } from "./FontGate";

const has = (name: string) => getStaticFiles().some((s) => s.name === name);

export const MezaTeaser: React.FC = () => {
  const t = useTime();
  return (
    <FontGate>
      <AbsoluteFill style={{ backgroundColor: "#000" }}>
        <Sequence
          durationInFrames={f(T.humanCut)}
          name="0:00 Hook + MEZA wakes"
        >
          <MezaAwakens t={t} />
        </Sequence>
        <Sequence
          from={f(T.humanCut)}
          durationInFrames={f(T.drop - T.humanCut)}
          name="0:04 Human"
        >
          <Human t={t} />
        </Sequence>
        <Sequence
          from={f(T.drop)}
          durationInFrames={f(T.silence - T.drop)}
          name="0:07 Unleashed"
        >
          <Unleashed t={t} />
        </Sequence>
        <Sequence from={f(T.silence)} name="0:12 Silence + final">
          <Final t={t} />
        </Sequence>

        {/* one continuous particle system morphs across every scene */}
        <ParticleField />

        <Flash t={t} at={T.hookHit} dur={0.1} peak={0.5} />
        <Flash t={t} at={T.humanCut} dur={0.2} />
        <Flash t={t} at={T.drop} dur={0.16} />
        {t < T.black ? <Vignette strength={0.8} /> : null}
        {t < T.silence || (t > T.final && t < T.black) ? (
          <Grain opacity={0.06} />
        ) : null}

        <Audio src={staticFile("sfx.wav")} />
        {has("voice-meza.mp3") ? (
          <Sequence from={f(T.mezaVoice)} name="VO MEZA">
            <Audio src={staticFile("voice-meza.mp3")} volume={1} />
          </Sequence>
        ) : null}
        {has("voice-chef.mp3") ? (
          <Sequence from={f(T.chefVoice)} name="VO Chef">
            <Audio src={staticFile("voice-chef.mp3")} volume={1} />
          </Sequence>
        ) : null}
      </AbsoluteFill>
    </FontGate>
  );
};
