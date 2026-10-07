import { AbsoluteFill, Img, random, staticFile } from "remotion";
import { DISPLAY, MONO } from "../fonts";
import { camAt, camCss } from "../particles/camera";
import { CYAN, T, WORDS } from "../timeline";
import { fitFont, HudFrame, LightStreak, Waveform } from "../components";
import { clamp01, easeIn, easeOut, lerp, prog, pulse } from "../util";

const SEG = 1.25;

const mono: React.CSSProperties = {
  fontFamily: MONO,
  fontSize: 19,
  letterSpacing: "0.28em",
  color: "rgba(210,250,255,0.85)",
  whiteSpace: "pre",
};

/** Whip in from one side with horizontal blur, whip out the other way. */
const Whip: React.FC<{
  t: number;
  a: number;
  b: number;
  dir: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ t, a, b, dir, children, style }) => {
  if (t < a || t > b) return null;
  const pin = prog(t, a, a + 0.18, easeOut);
  const pout = prog(t, b - 0.12, b, easeIn);
  const x = (1 - pin) * 520 * dir - pout * 620 * dir;
  const blur = (1 - pin) * 18 + pout * 22;
  return (
    <div
      style={{
        position: "absolute",
        transform: `translateX(${x}px)`,
        filter: `blur(${blur}px)`,
        opacity: 1 - pout * 0.6,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

const Panel: React.FC<{
  w: number;
  h: number;
  label: string;
  children: React.ReactNode;
}> = ({ w, h, label, children }) => (
  <div
    style={{
      width: w,
      height: h,
      position: "relative",
      border: `1px solid rgba(62,242,255,0.45)`,
      background: "rgba(0,18,26,0.35)",
      overflow: "hidden",
    }}
  >
    <div
      style={{
        ...mono,
        position: "absolute",
        left: 14,
        top: 10,
        fontSize: 15,
        color: CYAN,
      }}
    >
      {label}
    </div>
    {children}
  </div>
);

const VoiceFrag: React.FC<{ t: number }> = ({ t }) => (
  <Panel w={760} h={250} label="VOICE INTERFACE · RU / KZ / EN">
    <div style={{ position: "absolute", left: 120, top: 80 }}>
      <Waveform t={t * 1.6} level={0.9} width={520} height={130} bars={64} />
    </div>
  </Panel>
);

const VoiceOrb: React.FC<{ t: number }> = ({ t }) => (
  <svg width={360} height={360} viewBox="-180 -180 360 360">
    {[0, 1, 2, 3].map((i) => {
      const k = (t * 1.4 + i / 4) % 1;
      return (
        <circle
          key={i}
          r={40 + k * 130}
          fill="none"
          stroke={CYAN}
          strokeOpacity={(1 - k) * 0.7}
          strokeWidth={1.5}
        />
      );
    })}
    <circle r={34} fill={CYAN} opacity={0.85} />
  </svg>
);

const VisionFrag: React.FC<{ t: number; local: number }> = ({ t, local }) => {
  // macro close-up of the eyes with tracking boxes
  const zoom = 4.2 + local * 0.6;
  return (
    <Panel w={780} h={360} label="VISION · TRACKING">
      <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
        <Img
          src={staticFile("chef.jpg")}
          style={{
            position: "absolute",
            width: 941 * zoom * 0.83,
            left: 390 - 498 * zoom * 0.83,
            top: 180 - 724 * zoom * 0.83,
            filter: "grayscale(0.6) contrast(1.3) brightness(0.9)",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "rgba(0,80,110,0.35)",
            mixBlendMode: "color",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: ((t * 1.8) % 1) * 360,
            height: 2,
            background: CYAN,
            boxShadow: `0 0 18px ${CYAN}`,
          }}
        />
        {[
          { x: 70, y: 70, w: 270, h: 200, l: "LENS.L 0.998" },
          { x: 450, y: 70, w: 270, h: 200, l: "LENS.R 0.997" },
        ].map((b, i) => {
          const p = prog(local, 0.2 + i * 0.12, 0.45 + i * 0.12, easeOut);
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: b.x + (1 - p) * 40,
                top: b.y,
                width: b.w * lerp(1.3, 1, p),
                height: b.h * lerp(1.3, 1, p),
                border: `1.5px solid ${CYAN}`,
                opacity: p,
              }}
            >
              <div
                style={{
                  ...mono,
                  position: "absolute",
                  top: -26,
                  left: 0,
                  fontSize: 14,
                }}
              >
                {b.l}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
};

const DetectGrid: React.FC<{ local: number }> = ({ local }) => (
  <svg width={760} height={300}>
    {Array.from({ length: 12 }).map((_, i) => {
      const x = (i % 6) * 126 + 6;
      const y = Math.floor(i / 6) * 150 + 6;
      const on = random(`d${i}`) > 0.5 && local > 0.2 + random(`e${i}`) * 0.5;
      return (
        <g key={i}>
          <rect
            x={x}
            y={y}
            width={114}
            height={138}
            fill="none"
            stroke={CYAN}
            strokeOpacity={on ? 0.9 : 0.2}
          />
          {on ? (
            <text
              x={x + 8}
              y={y + 24}
              fill={CYAN}
              fontFamily={MONO}
              fontSize={13}
            >{`OBJ ${(random(`f${i}`) * 0.3 + 0.7).toFixed(2)}`}</text>
          ) : null}
        </g>
      );
    })}
  </svg>
);

const DataFrag: React.FC<{ local: number }> = ({ local }) => {
  const pts = Array.from({ length: 24 }).map((_, i) => {
    const x = 30 + i * 30;
    const y = 220 - (Math.sin(i * 0.55) * 30 + i * 6.5 + random(`p${i}`) * 26);
    return [x, y] as const;
  });
  const draw = prog(local, 0.05, 0.75, easeOut);
  const path = pts.map((p, i) => `${i ? "L" : "M"}${p[0]},${p[1]}`).join(" ");
  return (
    <Panel w={780} h={290} label="ANALYTICS · REAL-TIME">
      <svg width={780} height={290} style={{ position: "absolute", top: 20 }}>
        {pts.map((p, i) => (
          <rect
            key={i}
            x={p[0] - 9}
            y={250 - (250 - p[1]) * 0.6 * draw}
            width={18}
            height={(250 - p[1]) * 0.6 * draw}
            fill={CYAN}
            opacity={0.18}
          />
        ))}
        <path
          d={path}
          fill="none"
          stroke={CYAN}
          strokeWidth={3}
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - draw}
          style={{ filter: `drop-shadow(0 0 6px ${CYAN})` }}
        />
      </svg>
    </Panel>
  );
};

const BigNumber: React.FC<{ local: number }> = ({ local }) => {
  const v = Math.floor(prog(local, 0, 0.8, easeOut) * 247);
  return (
    <div style={{ textAlign: "center" }}>
      <div
        style={{
          fontFamily: DISPLAY,
          fontWeight: 300,
          fontSize: 150,
          color: "#eafcff",
          textShadow: `0 0 40px ${CYAN}`,
        }}
      >
        +{v}%
      </div>
      <div style={{ ...mono, color: CYAN }}>THROUGHPUT · 24H</div>
    </div>
  );
};

const ActionFrag: React.FC<{ local: number }> = ({ local }) => {
  const rows = [
    "BRIEF → TEAM",
    "REPORT · WEEK 41",
    "CALL · 15:00",
    "WORKFLOW #12",
  ];
  const states = ["DONE", "DONE", "SET", "RUNNING"];
  return (
    <Panel w={780} h={300} label="TASKS · AUTONOMOUS">
      <div style={{ position: "absolute", top: 58, left: 26, right: 26 }}>
        {rows.map((r, i) => {
          const p = prog(local, 0.1 + i * 0.12, 0.25 + i * 0.12, easeOut);
          const blurred = i >= 2; // keep the product half-hidden
          return (
            <div
              key={i}
              style={{
                ...mono,
                display: "flex",
                justifyContent: "space-between",
                fontSize: 22,
                padding: "10px 0",
                borderBottom: "1px solid rgba(62,242,255,0.18)",
                opacity: 0.3 + p * 0.7,
                filter: blurred ? "blur(2.5px)" : "none",
              }}
            >
              <span>{`${p > 0.9 ? "◼" : "◻"} ${r}`}</span>
              <span style={{ color: CYAN }}>{p > 0.9 ? states[i] : "···"}</span>
            </div>
          );
        })}
      </div>
    </Panel>
  );
};

const NodeGraph: React.FC<{ local: number }> = ({ local }) => {
  const nodes = [
    [80, 150],
    [260, 60],
    [270, 240],
    [460, 150],
    [640, 70],
    [650, 230],
  ];
  const edges = [
    [0, 1],
    [0, 2],
    [1, 3],
    [2, 3],
    [3, 4],
    [3, 5],
  ];
  return (
    <svg width={740} height={300}>
      {edges.map(([a, b], i) => {
        const p = prog(local, 0.05 + i * 0.08, 0.3 + i * 0.08, easeOut);
        const [x1, y1] = nodes[a];
        const [x2, y2] = nodes[b];
        return (
          <line
            key={i}
            x1={x1}
            y1={y1}
            x2={lerp(x1, x2, p)}
            y2={lerp(y1, y2, p)}
            stroke={CYAN}
            strokeWidth={2}
            opacity={0.8}
          />
        );
      })}
      {nodes.map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r={i === 3 ? 18 : 10}
          fill={i === 3 ? CYAN : "#001820"}
          stroke={CYAN}
          strokeWidth={2}
          opacity={clamp01(local * 4 - i * 0.3)}
        />
      ))}
    </svg>
  );
};

/** 0:07–0:12 — VOICE → VISION → DATA → ACTION with capability fragments. */
export const Unleashed: React.FC<{ t: number }> = ({ t }) => {
  const cam = camAt(t);
  const k = Math.max(0, T.words.filter((w) => t >= w).length - 1);
  const start = T.words[k];
  const local = (t - start) / SEG;
  const word = WORDS[k];
  const size = fitFont(word, DISPLAY, 800, 990, 260);
  // crisp word fades in once particles have settled, RGB split on entry
  const settle =
    prog(t, start + 0.3, start + 0.5, easeOut) * (1 - prog(t, 11.7, T.silence));
  const split = pulse(t, start + 0.3, 0.1) * 14;
  const dir = k % 2 === 0 ? 1 : -1;
  const fragA = start + 0.32;
  const fragB = start + SEG - 0.04;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 70% 40% at 50% 50%, rgba(20,140,200,${0.18 + pulse(t, start, 0.2) * 0.25}), rgba(0,0,0,0) 70%)`,
        }}
      />
      {/* fragments behind the word (parallax: top slower than bottom) */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 230 + local * 30,
          display: "flex",
          justifyContent: "center",
          opacity: 0.9,
        }}
      >
        <Whip t={t} a={fragA} b={fragB} dir={dir}>
          {k === 0 ? (
            <VoiceFrag t={t} />
          ) : k === 1 ? (
            <VisionFrag t={t} local={local} />
          ) : k === 2 ? (
            <DataFrag local={local} />
          ) : (
            <ActionFrag local={local} />
          )}
        </Whip>
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 1300 - local * 80,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <Whip t={t} a={fragA + 0.1} b={fragB} dir={-dir}>
          {k === 0 ? (
            <VoiceOrb t={t} />
          ) : k === 1 ? (
            <DetectGrid local={local} />
          ) : k === 2 ? (
            <BigNumber local={local} />
          ) : (
            <NodeGraph local={local} />
          )}
        </Whip>
      </div>
      {/* crisp kinetic word, locked to the particle camera */}
      <AbsoluteFill
        style={{ transformOrigin: "0 0", transform: camCss(cam, 540, 960) }}
      >
        {[
          { dx: -split, c: "rgba(255,60,120,0.55)" },
          { dx: split, c: "rgba(60,255,255,0.6)" },
          { dx: 0, c: "rgba(235,252,255,0.92)" },
        ].map((l, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: -540,
              width: 1080,
              top: -size * 0.62,
              textAlign: "center",
              fontFamily: DISPLAY,
              fontWeight: 800,
              fontSize: size,
              lineHeight: 1.24,
              color: l.c,
              opacity: settle * (i === 2 ? 0.55 : 0.8),
              transform: `translateX(${l.dx}px)`,
              mixBlendMode: "screen",
              textShadow: i === 2 ? `0 0 40px rgba(62,242,255,0.6)` : "none",
            }}
          >
            {word}
          </div>
        ))}
      </AbsoluteFill>
      {T.words.map((w) => (
        <LightStreak key={w} t={t} at={w} y={960} />
      ))}
      <HudFrame
        t={t}
        opacity={0.8}
        labels={[
          "MEZA // UNLEASHED",
          "LOAD",
          `0${k + 1} / 04`,
          `MODE : ${word}`,
        ]}
      />
    </AbsoluteFill>
  );
};
