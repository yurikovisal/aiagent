import { AbsoluteFill, Img, staticFile } from "remotion";
import { DISPLAY, MONO } from "../fonts";
import { camAt, camCss, SIL_SIZE, SIL_Y } from "../particles/camera";
import { CYAN, SUB_MEZA, T } from "../timeline";
import { HudFrame, ScanGrid, Subtitle, Waveform } from "../components";
import { clamp01, easeOut, fade, prog, pulse } from "../util";

/** 0:00–0:04 — hook flash, dive into the cloud, MEZA assembles and speaks. */
export const MezaAwakens: React.FC<{ t: number }> = ({ t }) => {
  const cam = camAt(t);

  // the photoreal silhouette sits under the particles for density
  const flash =
    t >= T.hookHit && t < 0.36 ? (Math.sin(t * 300) > -0.3 ? 0.95 : 0.3) : 0;
  const dim = t >= 0.36 && t < T.wake ? 0.55 * (1 - prog(t, 0.8, T.wake)) : 0;
  const assembled = t >= T.wake ? prog(t, 1.75, 2.6, easeOut) * 0.62 : 0;
  const shefPulse = pulse(t, T.chefPulse, 0.25);
  const imgOpacity = Math.max(flash, dim, assembled) * (1 + shefPulse * 0.4);

  // glitch slices during the hook
  const glitchOn = t > 0.14 && t < 0.34;
  const slices = glitchOn ? [0.18, 0.41, 0.63] : [];

  const hudIn = prog(t, 1.4, 2.0) * (1 - prog(t, 3.85, T.humanCut));
  const voiceLevel = fade(t, T.mezaVoice, T.mezaVoice + 0.2, 3.7, 3.95);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* volumetric glow behind the head */}
      <AbsoluteFill
        style={{
          opacity: clamp01(assembled * 1.4) * (0.8 + shefPulse * 0.6),
          background:
            "radial-gradient(ellipse 45% 30% at 50% 36%, rgba(40,200,255,0.30), rgba(0,0,0,0) 70%)",
        }}
      />
      <ScanGrid t={t} opacity={hudIn * 0.9} />
      <AbsoluteFill
        style={{ transformOrigin: "0 0", transform: camCss(cam, 540, 960) }}
      >
        <Img
          src={staticFile("meza-silhouette.jpg")}
          style={{
            position: "absolute",
            left: -SIL_SIZE / 2,
            top: SIL_Y - SIL_SIZE / 2,
            width: SIL_SIZE,
            height: SIL_SIZE,
            opacity: imgOpacity,
            mixBlendMode: "screen",
            filter: `brightness(${1 + shefPulse * 0.5}) contrast(1.15)`,
          }}
        />
        {slices.map((s, i) => (
          <Img
            key={i}
            src={staticFile("meza-silhouette.jpg")}
            style={{
              position: "absolute",
              left: -SIL_SIZE / 2 + (i % 2 ? -1 : 1) * (30 + i * 22),
              top: SIL_Y - SIL_SIZE / 2,
              width: SIL_SIZE,
              height: SIL_SIZE,
              opacity: 0.8,
              mixBlendMode: "screen",
              clipPath: `inset(${s * 100}% 0 ${100 - s * 100 - 6}% 0)`,
              filter: i === 1 ? "hue-rotate(160deg) saturate(3)" : "none",
            }}
          />
        ))}
      </AbsoluteFill>

      {/* HOOK text: 8 frames @60fps ≈ 4 frames @30fps */}
      {t >= T.hookTextIn && t < T.hookTextOut ? (
        <AbsoluteFill
          style={{ justifyContent: "center", alignItems: "center" }}
        >
          {[
            { dx: -8, c: "rgba(255,40,90,0.7)" },
            { dx: 8, c: "rgba(40,255,255,0.8)" },
            { dx: 0, c: "#fff" },
          ].map((l, i) => (
            <div
              key={i}
              style={{
                position: "absolute",
                fontFamily: DISPLAY,
                fontWeight: 800,
                fontSize: 104,
                letterSpacing: "0.04em",
                color: l.c,
                transform: `translateX(${l.dx * (t > 0.2 ? -1 : 1)}px) skewX(${t > 0.22 ? -6 : 0}deg)`,
                mixBlendMode: "screen",
                whiteSpace: "nowrap",
              }}
            >
              MEZA // ONLINE
            </div>
          ))}
        </AbsoluteFill>
      ) : null}

      <HudFrame
        t={t}
        opacity={hudIn}
        labels={["MEZA // CORE", "NEURAL SYNC", "BOOT 0.9.7", "STATE : AWAKE"]}
      />

      {/* floating data labels near the silhouette */}
      <AbsoluteFill style={{ opacity: hudIn, pointerEvents: "none" }}>
        {[
          { x: 120, y: 540, txt: "VOICE.MODEL\nRU · KZ · EN", d: 1.6 },
          { x: 760, y: 470, txt: "LATENCY\n0.02s", d: 1.8 },
          { x: 790, y: 860, txt: "CONTEXT\n∞", d: 2.0 },
          { x: 110, y: 930, txt: "IDENTITY\nMEZA", d: 2.2 },
        ].map((l, i) => {
          const p = prog(t, l.d, l.d + 0.35, easeOut);
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: l.x,
                top: l.y + Math.sin(t * 1.2 + i) * 8,
                fontFamily: MONO,
                fontSize: 18,
                letterSpacing: "0.3em",
                color: "rgba(200,250,255,0.8)",
                whiteSpace: "pre",
                lineHeight: 1.7,
                opacity: p,
                clipPath: `inset(0 ${(1 - p) * 100}% 0 0)`,
                borderLeft: `1px solid ${CYAN}`,
                paddingLeft: 12,
              }}
            >
              {l.txt}
            </div>
          );
        })}
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          alignItems: "center",
          paddingBottom: 520,
          opacity: hudIn,
        }}
      >
        <Waveform t={t} level={0.12 + voiceLevel * 0.88} />
      </AbsoluteFill>
      <Subtitle
        t={t}
        text={SUB_MEZA}
        speaker="MEZA"
        start={T.mezaVoice}
        end={T.humanCut - 0.1}
      />
    </AbsoluteFill>
  );
};
