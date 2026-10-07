import { AbsoluteFill, Img, random, staticFile } from "remotion";
import { CYAN, SUB_CHEF, T } from "../timeline";
import { Subtitle } from "../components";
import { easeInOut, easeOut, lerp, prog, pulse } from "../util";

const IMG_W = 941;
const IMG_H = 1672;
const BASE = 1080 / IMG_W;
// lens centres in source-image pixels (for the particle reflections)
const LENSES = [
  { cx: 410, cy: 724, rx: 58, ry: 54 },
  { cx: 586, cy: 724, rx: 56, ry: 54 },
];

/** 0:04–0:07 — match-cut to the human, camera tilts from phone to face. */
export const Human: React.FC<{ t: number }> = ({ t }) => {
  const p = prog(t, T.humanCut + 0.15, 6.4, easeInOut);
  const zoom = lerp(2.0, 1.72, p);
  const fx = 480;
  const fy = lerp(990, 712, p);
  const enter = prog(t, T.humanCut, T.humanCut + 0.3, easeOut);
  const impact = pulse(t, 6.82, 0.12);
  const scale = BASE * zoom * (1 + (1 - enter) * 0.08 + impact * 0.03);
  const transform = `translate(540px, 960px) scale(${scale}) translate(${-fx}px, ${-fy}px)`;
  const phoneGlow = 0.6 + Math.sin(t * 5) * 0.1 + Math.sin(t * 13) * 0.05;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill
        style={{
          transformOrigin: "0 0",
          transform,
          filter: `blur(${(1 - enter) * 10}px)`,
        }}
      >
        <Img
          src={staticFile("chef.jpg")}
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: IMG_W,
            height: IMG_H,
            filter: "contrast(1.08) saturate(0.9)",
          }}
        />
        <svg
          width={IMG_W}
          height={IMG_H}
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            mixBlendMode: "screen",
          }}
        >
          <defs>
            <clipPath id="lenses">
              {LENSES.map((l, i) => (
                <ellipse key={i} cx={l.cx} cy={l.cy} rx={l.rx} ry={l.ry} />
              ))}
            </clipPath>
            <radialGradient id="phone" cx="0.5" cy="0.5" r="0.5">
              <stop offset="0" stopColor={CYAN} stopOpacity="0.55" />
              <stop offset="1" stopColor={CYAN} stopOpacity="0" />
            </radialGradient>
          </defs>
          {/* digital particles reflected in the glasses */}
          <g clipPath="url(#lenses)">
            {LENSES.map((l, li) =>
              Array.from({ length: 70 }).map((_, i) => {
                const r1 = random(`l${li}-${i}`);
                const r2 = random(`m${li}-${i}`);
                const x =
                  l.cx -
                  l.rx +
                  ((r1 * 2 * l.rx + t * (20 + r2 * 40)) % (2 * l.rx));
                const y =
                  l.cy -
                  l.ry +
                  ((r2 * 2 * l.ry + Math.sin(t * 2 + r1 * 9) * 6 + 2 * l.ry) %
                    (2 * l.ry));
                return (
                  <circle
                    key={`${li}-${i}`}
                    cx={x}
                    cy={y}
                    r={0.5 + r1 * 1.3}
                    fill={CYAN}
                    opacity={0.35 + r2 * 0.6}
                  />
                );
              }),
            )}
          </g>
          {/* cold light from the phone */}
          <ellipse
            cx={455}
            cy={1070}
            rx={230}
            ry={160}
            fill="url(#phone)"
            opacity={phoneGlow}
          />
        </svg>
      </AbsoluteFill>
      {/* cool grade + falloff */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,10,20,0.5) 0%, rgba(0,0,0,0) 25%, rgba(0,0,0,0) 62%, rgba(0,0,0,0.92) 100%)",
        }}
      />
      <AbsoluteFill
        style={{ background: "rgba(0,60,90,0.12)", mixBlendMode: "color" }}
      />
      <Subtitle
        t={t}
        text={SUB_CHEF}
        speaker="ШЕФ"
        start={T.chefVoice}
        end={T.drop - 0.05}
        bottom={260}
      />
    </AbsoluteFill>
  );
};
