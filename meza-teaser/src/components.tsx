import { AbsoluteFill, random, useCurrentFrame } from "remotion";
import { BODY, MONO } from "./fonts";
import { CYAN, FPS } from "./timeline";
import { clamp01, easeOut, prog } from "./util";

export const useTime = () => useCurrentFrame() / FPS;

const measureCanvas =
  typeof document !== "undefined" ? document.createElement("canvas") : null;
/** Font size that makes `text` exactly `maxW` wide (capped at `max`). */
export const fitFont = (
  text: string,
  font: string,
  weight: number,
  maxW: number,
  max: number,
) => {
  const ctx = measureCanvas?.getContext("2d");
  if (!ctx) return max;
  ctx.font = `${weight} 100px ${font}`;
  return Math.min(max, (100 * maxW) / ctx.measureText(text).width);
};

export const Vignette: React.FC<{ strength?: number }> = ({
  strength = 0.85,
}) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(ellipse 75% 60% at 50% 45%, rgba(0,0,0,0) 40%, rgba(0,0,0,${strength}) 100%)`,
      pointerEvents: "none",
    }}
  />
);

export const Grain: React.FC<{ opacity?: number }> = ({ opacity = 0.07 }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{ opacity, mixBlendMode: "screen", pointerEvents: "none" }}
    >
      <svg width="100%" height="100%">
        <filter id={`grain-${frame % 8}`}>
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.85"
            numOctaves="2"
            seed={frame % 8}
          />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain-${frame % 8})`} />
      </svg>
    </AbsoluteFill>
  );
};

/** Scanning grid with perspective floor + horizontal scan line. */
export const ScanGrid: React.FC<{ t: number; opacity: number }> = ({
  t,
  opacity,
}) => {
  const scanY = ((t * 0.35) % 1) * 1920;
  return (
    <AbsoluteFill style={{ opacity, pointerEvents: "none" }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <defs>
          <linearGradient id="fadeGrid" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={CYAN} stopOpacity="0" />
            <stop offset="0.6" stopColor={CYAN} stopOpacity="0.16" />
            <stop offset="1" stopColor={CYAN} stopOpacity="0.32" />
          </linearGradient>
          <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={CYAN} stopOpacity="0" />
            <stop offset="1" stopColor={CYAN} stopOpacity="0.22" />
          </linearGradient>
        </defs>
        {/* perspective floor */}
        {Array.from({ length: 15 }).map((_, i) => {
          const x = -1400 + i * 260;
          return (
            <line
              key={`v${i}`}
              x1={540}
              y1={1180}
              x2={x}
              y2={1920}
              stroke="url(#fadeGrid)"
              strokeWidth={1}
            />
          );
        })}
        {Array.from({ length: 9 }).map((_, i) => {
          const k = ((i + ((t * 0.6) % 1)) / 9) ** 2.2;
          const y = 1180 + k * 740;
          return (
            <line
              key={`h${i}`}
              x1={0}
              y1={y}
              x2={1080}
              y2={y}
              stroke={CYAN}
              strokeOpacity={0.05 + k * 0.22}
              strokeWidth={1}
            />
          );
        })}
        <rect
          x={0}
          y={scanY - 120}
          width={1080}
          height={120}
          fill="url(#scan)"
        />
        <line
          x1={0}
          y1={scanY}
          x2={1080}
          y2={scanY}
          stroke={CYAN}
          strokeOpacity={0.55}
          strokeWidth={1.2}
        />
      </svg>
    </AbsoluteFill>
  );
};

/** Thin corner brackets + tiny interface labels (dark-tech HUD). */
export const HudFrame: React.FC<{
  t: number;
  opacity: number;
  labels?: [string, string, string, string];
}> = ({
  t,
  opacity,
  labels = ["MEZA // CORE", "SYNC", "NODE 07", "STATE : WAKING"],
}) => {
  const L = 46;
  const bracket = (x: number, y: number, dx: number, dy: number, k: string) => (
    <path
      key={k}
      d={`M ${x} ${y + dy * L} L ${x} ${y} L ${x + dx * L} ${y}`}
      stroke={CYAN}
      strokeOpacity={0.7}
      strokeWidth={1.4}
      fill="none"
    />
  );
  const code = (n: number) =>
    String(Math.floor(random(`c${n}${Math.floor(t * 12)}`) * 9999)).padStart(
      4,
      "0",
    );
  const label: React.CSSProperties = {
    position: "absolute",
    fontFamily: MONO,
    fontWeight: 300,
    fontSize: 19,
    letterSpacing: "0.32em",
    color: "rgba(200,250,255,0.75)",
    lineHeight: 1.7,
    whiteSpace: "pre",
  };
  return (
    <AbsoluteFill style={{ opacity, pointerEvents: "none" }}>
      <svg width="1080" height="1920" style={{ position: "absolute" }}>
        {bracket(60, 120, 1, 1, "a")}
        {bracket(1020, 120, -1, 1, "b")}
        {bracket(60, 1800, 1, -1, "c")}
        {bracket(1020, 1800, -1, -1, "d")}
      </svg>
      <div
        style={{ ...label, left: 64, top: 150 }}
      >{`${labels[0]}\n${code(1)}.${code(2)}`}</div>
      <div style={{ ...label, right: 64, top: 150, textAlign: "right" }}>
        {`${labels[1]}\n${"▮".repeat(1 + Math.floor(clamp01(t / 4) * 6))}${"▯".repeat(6 - Math.floor(clamp01(t / 4) * 6))}`}
      </div>
      <div
        style={{ ...label, left: 64, bottom: 150 }}
      >{`${labels[2]}\n${(t * 1000).toFixed(0).padStart(5, "0")} ms`}</div>
      <div
        style={{ ...label, right: 64, bottom: 150, textAlign: "right" }}
      >{`${labels[3]}\n—`}</div>
    </AbsoluteFill>
  );
};

/** Procedural voice waveform; `level` 0..1 drives amplitude. */
export const Waveform: React.FC<{
  t: number;
  level: number;
  width?: number;
  height?: number;
  bars?: number;
}> = ({ t, level, width = 520, height = 70, bars = 48 }) => (
  <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
    {Array.from({ length: bars }).map((_, i) => {
      const x = (i / (bars - 1)) * (width - 6) + 3;
      const centre = 1 - Math.abs(i / (bars - 1) - 0.5) * 1.6;
      const v =
        (Math.abs(Math.sin(t * 11 + i * 0.7)) * 0.5 +
          Math.abs(Math.sin(t * 23.3 + i * 1.9)) * 0.5) *
        centre *
        level;
      const h = 3 + v * (height - 6);
      return (
        <rect
          key={i}
          x={x - 1.5}
          y={(height - h) / 2}
          width={3}
          height={h}
          rx={1.5}
          fill={CYAN}
          opacity={0.5 + v * 0.5}
        />
      );
    })}
  </svg>
);

/** Word-by-word subtitle reveal for the voice lines. */
export const Subtitle: React.FC<{
  t: number;
  text: string;
  speaker: string;
  start: number;
  end: number;
  bottom?: number;
}> = ({ t, text, speaker, start, end, bottom = 330 }) => {
  const words = text.split(" ");
  const span = end - start - 0.5;
  const out = 1 - prog(t, end - 0.25, end);
  if (t < start - 0.1 || out <= 0) return null;
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: bottom,
        opacity: out,
      }}
    >
      <div
        style={{
          fontFamily: MONO,
          fontSize: 18,
          letterSpacing: "0.5em",
          color: CYAN,
          marginBottom: 18,
          opacity: prog(t, start - 0.1, start + 0.2),
        }}
      >
        {speaker}
      </div>
      <div
        style={{
          fontFamily: BODY,
          fontWeight: 500,
          fontSize: 44,
          color: "#eafcff",
          textAlign: "center",
          maxWidth: 900,
          lineHeight: 1.35,
          letterSpacing: "0.01em",
        }}
      >
        {words.map((w, i) => {
          const at = start + (i / words.length) * span;
          const p = prog(t, at, at + 0.22, easeOut);
          return (
            <span
              key={i}
              style={{
                opacity: p,
                filter: `blur(${(1 - p) * 8}px)`,
                display: "inline-block",
                transform: `translateY(${(1 - p) * 10}px)`,
                marginRight: 12,
                textShadow: "0 0 24px rgba(62,242,255,0.45)",
              }}
            >
              {w}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const Flash: React.FC<{
  t: number;
  at: number;
  dur?: number;
  color?: string;
  peak?: number;
}> = ({ t, at, dur = 0.14, color = "rgb(190,250,255)", peak = 0.9 }) => {
  if (t < at || t > at + dur) return null;
  const k = 1 - (t - at) / dur;
  return (
    <AbsoluteFill
      style={{
        background: color,
        opacity: k * k * peak,
        mixBlendMode: "screen",
      }}
    />
  );
};

/** Horizontal anamorphic light streak. */
export const LightStreak: React.FC<{ t: number; at: number; y?: number }> = ({
  t,
  at,
  y = 960,
}) => {
  const k = t < at ? 0 : Math.exp(-(t - at) / 0.12);
  if (k < 0.02) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: -200,
        right: -200,
        top: y - 3,
        height: 6,
        background:
          "linear-gradient(90deg, transparent, rgba(120,245,255,0.9) 35%, #fff 50%, rgba(120,245,255,0.9) 65%, transparent)",
        filter: "blur(3px)",
        opacity: k,
        boxShadow: "0 0 60px 18px rgba(62,242,255,0.5)",
        transform: `scaleY(${1 + (1 - k) * 4})`,
      }}
    />
  );
};
