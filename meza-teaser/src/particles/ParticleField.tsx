import { useEffect, useMemo, useRef, useState } from "react";
import {
  AbsoluteFill,
  cancelRender,
  continueRender,
  delayRender,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { fontsReady } from "../fonts";
import { FPS, HEIGHT, T, WIDTH, WORDS } from "../timeline";
import {
  clamp01,
  easeIn,
  easeInOut,
  easeOut,
  lerp,
  prog,
  pulse,
} from "../util";
import { Cam, camAt, FACE, ORB_Y, toScreen } from "./camera";
import { buildTargets, N, Targets } from "./targets";

type P = { x: number; y: number; a: number; s: number; b: number };

const ORB_R = 170;

/** Particle position/alpha/size for particle i at time t (seconds). Pure + deterministic. */
const particleAt = (g: Targets, i: number, t: number, out: P) => {
  const sd0 = g.seed[i * 4];
  const sd1 = g.seed[i * 4 + 1];
  const sd2 = g.seed[i * 4 + 2];
  const sd3 = g.seed[i * 4 + 3];
  const sx = g.sil[i * 3];
  const sy = g.sil[i * 3 + 1];
  const sb = g.sil[i * 3 + 2];
  // living shimmer around any resting shape
  const jx = Math.sin(t * (1.3 + sd0 * 2) + sd1 * 40) * 2.4;
  const jy = Math.cos(t * (1.1 + sd2 * 2) + sd3 * 40) * 2.4;
  out.b = sb;
  out.s = 1;

  if (t < T.hookHit) {
    out.a = 0;
    out.x = sx;
    out.y = sy;
    return;
  }

  if (t < T.wake) {
    // flash, then dive into the cloud
    const flicker =
      t < 0.36 ? (Math.sin(t * 260 + sd0 * 6) > -0.2 ? 1 : 0.25) : 1;
    const dive = prog(t, T.diveStart, T.wake, easeIn);
    const spread = 1 + dive * sd2 * 0.35;
    out.x = FACE[0] + (sx - FACE[0]) * spread + jx;
    out.y = FACE[1] + (sy - FACE[1]) * spread + jy;
    out.a = flicker * (t < 0.36 ? 1 : 0.85) * (1 - prog(t, 0.9, T.wake));
    out.s = 1 + dive * 0.4;
    return;
  }

  if (t < T.humanCut) {
    // AI wakes: scattered cloud converges into the silhouette, staggered
    const delay = sd0 * 0.75;
    const p = prog(t, T.wake + delay, T.wake + delay + 1.1, easeOut);
    const scx = g.scatter[i * 3];
    const scy = g.scatter[i * 3 + 1];
    // flowing data drift once assembled
    const flow = Math.sin(sy * 0.02 + t * 2.2 + sd1 * 3) * 3 * p;
    // pulse on "шеф": radial push + brightness
    const pu = pulse(t, T.chefPulse, 0.22);
    const dx = sx - 0;
    const dy = sy - -260;
    const d = Math.hypot(dx, dy) + 1;
    out.x = lerp(scx, sx, p) + jx + (dx / d) * pu * 26 * sd2 + flow;
    out.y = lerp(scy, sy, p) + jy + (dy / d) * pu * 26 * sd2;
    out.a = clamp01(0.15 + p) * (0.75 + pu * 0.6);
    out.b = sb + pu * 0.5;
    out.s = lerp(g.scatter[i * 3 + 2] * 1.8, 1, p);
    return;
  }

  if (t < T.drop) {
    // ambient dust over the human scene
    const z = g.dust[i * 3 + 2];
    out.x = g.dust[i * 3] + Math.sin(t * 0.4 + sd0 * 10) * 30 * z;
    out.y = g.dust[i * 3 + 1] - (t - T.humanCut) * 22 * z;
    // pre-drop: dust gets sucked towards the centre
    const suck = prog(t, 6.55, T.drop, easeIn);
    out.x = lerp(out.x, out.x * 0.15, suck);
    out.y = lerp(out.y, out.y * 0.15, suck);
    out.a = (i % 5 === 0 ? 0.55 : 0) * z * (1 - suck * 0.3) + suck * 0.6;
    out.s = 0.7 + z * 0.6;
    out.b = 0.4 + z * 0.3;
    return;
  }

  if (t < T.silence) {
    // VOICE -> VISION -> DATA -> ACTION, morph with burst between words
    const k = T.words.filter((w) => t >= w).length - 1;
    const cur = g.glyphs[k];
    const gx = cur[i * 2];
    const gy = cur[i * 2 + 1];
    let fx: number;
    let fy: number;
    if (k === 0) {
      const z = g.dust[i * 3 + 2];
      fx = g.dust[i * 3] * 0.15;
      fy = (g.dust[i * 3 + 1] - (T.drop - T.humanCut) * 22 * z) * 0.15;
    } else {
      fx = g.glyphs[k - 1][i * 2];
      fy = g.glyphs[k - 1][i * 2 + 1];
    }
    const start = T.words[k] + sd0 * 0.12;
    const p = prog(t, start, start + 0.32, easeInOut);
    const burst = Math.sin(Math.PI * p) * (120 + sd1 * 260);
    const ang = sd2 * Math.PI * 2;
    out.x = lerp(fx, gx, p) + Math.cos(ang) * burst + jx * 0.6;
    out.y = lerp(fy, gy, p) + Math.sin(ang) * burst * 0.6 + jy * 0.6;
    // overload: final word blows apart just before the cut
    const blow = prog(t, 11.72, T.silence, easeIn);
    out.x += gx * blow * (0.6 + sd3 * 2.4);
    out.y += gy * blow * (0.6 + sd3 * 2.4) + (sd1 - 0.5) * blow * 900;
    out.a = 0.95;
    out.b = 0.55 + sd3 * 0.45 + pulse(t, T.words[k], 0.15) * 0.6;
    out.s = 1.05;
    return;
  }

  if (t < T.orbForm || t >= T.black) {
    out.a = 0;
    out.x = 0;
    out.y = ORB_Y;
    return;
  }

  // orb: particles bloom out of the single dot and settle on a rotating sphere
  const rot = t * 0.55;
  const ox = g.orb[i * 3];
  const oy = g.orb[i * 3 + 1];
  const oz = g.orb[i * 3 + 2];
  const c = Math.cos(rot);
  const s = Math.sin(rot);
  const x3 = ox * c + oz * s;
  const z3 = -ox * s + oz * c;
  const tilt = 0.35;
  const y3 = oy * Math.cos(tilt) - z3 * Math.sin(tilt);
  const zz = oy * Math.sin(tilt) + z3 * Math.cos(tilt);
  const grow = prog(
    t,
    T.orbForm + sd0 * 0.4,
    T.orbForm + sd0 * 0.4 + 0.5,
    easeOut,
  );
  const pu = pulse(t, T.orbPulse, 0.35);
  const breathe = 1 + Math.sin(t * 2.4) * 0.015;
  const r = ORB_R * grow * (1 + pu * 0.28) * breathe * (1 + (sd1 - 0.5) * 0.08);
  const persp = 1 / (1 - zz * 0.35);
  out.x = x3 * r * persp;
  out.y = ORB_Y + y3 * r * persp;
  out.a =
    grow * (0.35 + (zz + 1) * 0.35) * (1 - prog(t, T.black - 0.02, T.black));
  out.s = 0.7 + (zz + 1) * 0.35;
  out.b = 0.45 + (zz + 1) * 0.3 + pu * 0.4;
};

const makeSprite = () => {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const ctx = c.getContext("2d")!;
  const gr = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, "rgba(220,255,255,1)");
  gr.addColorStop(0.18, "rgba(90,240,255,0.65)");
  gr.addColorStop(0.5, "rgba(40,200,255,0.16)");
  gr.addColorStop(1, "rgba(0,160,255,0)");
  ctx.fillStyle = gr;
  ctx.fillRect(0, 0, 64, 64);
  return c;
};

const draw = (
  ctx: CanvasRenderingContext2D,
  g: Targets,
  sprite: HTMLCanvasElement,
  t: number,
) => {
  ctx.globalCompositeOperation = "source-over";
  ctx.clearRect(0, 0, WIDTH, HEIGHT);
  ctx.globalCompositeOperation = "lighter";
  const cam: Cam = camAt(t);
  const tPrev = t - 1.6 / FPS;
  const camPrev = camAt(tPrev);
  const cx = WIDTH / 2;
  const cy = HEIGHT / 2;
  const p: P = { x: 0, y: 0, a: 0, s: 1, b: 0 };
  const q: P = { x: 0, y: 0, a: 0, s: 1, b: 0 };
  const zoomSize = Math.sqrt(cam.zoom);
  ctx.lineCap = "round";

  // single dot before the orb blooms
  if (t >= T.dot && t < T.orbForm + 0.3) {
    const grow = prog(t, T.dot, T.orbForm, easeOut);
    const fadeOut = 1 - prog(t, T.orbForm, T.orbForm + 0.3);
    const sz = (10 + grow * 50) * (1 + Math.sin(t * 9) * 0.05);
    ctx.globalAlpha = (0.4 + grow * 0.6) * fadeOut;
    ctx.drawImage(sprite, cx - sz / 2, cy + ORB_Y - sz / 2, sz, sz);
  }

  for (let i = 0; i < N; i++) {
    particleAt(g, i, t, p);
    if (p.a <= 0.01) continue;
    const [x, y] = toScreen(cam, p.x, p.y, cx, cy);
    if (x < -60 || x > WIDTH + 60 || y < -60 || y > HEIGHT + 60) continue;
    particleAt(g, i, tPrev, q);
    const [px, py] = toScreen(camPrev, q.x, q.y, cx, cy);
    const sd = g.seed[i * 4 + 1];
    const size = (0.9 + sd * 1.9) * p.s * zoomSize;
    const bright = clamp01(p.b);
    const alpha = clamp01(p.a * (0.35 + bright * 0.75));
    const dist = Math.hypot(x - px, y - py);
    const r = Math.round(lerp(40, 230, bright * bright));
    const gch = Math.round(lerp(200, 255, bright));
    if (dist > 2.5) {
      // motion streak / light trail
      ctx.globalAlpha = alpha * Math.min(1, 6 / dist + 0.35);
      ctx.strokeStyle = `rgb(${r},${gch},255)`;
      ctx.lineWidth = size;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(x, y);
      ctx.stroke();
    } else {
      ctx.globalAlpha = alpha;
      ctx.fillStyle = `rgb(${r},${gch},255)`;
      ctx.fillRect(x - size / 2, y - size / 2, size, size);
    }
    // a few big soft bokeh glows
    if (sd > 0.965 || (bright > 0.8 && sd > 0.85)) {
      const gs = size * (sd > 0.985 ? 16 : 7);
      ctx.globalAlpha = alpha * 0.55;
      ctx.drawImage(sprite, x - gs / 2, y - gs / 2, gs, gs);
    }
  }
  ctx.globalAlpha = 1;
};

export const ParticleField: React.FC = () => {
  const frame = useCurrentFrame();
  const canvas = useRef<HTMLCanvasElement>(null);
  const [targets, setTargets] = useState<Targets | null>(null);
  const [handle] = useState(() => delayRender("Loading particle targets"));
  const sprite = useMemo(() => makeSprite(), []);

  useEffect(() => {
    Promise.all([
      fetch(staticFile("meza-points.json")).then((r) => r.json()),
      fontsReady(),
    ])
      .then(([pts]) => {
        setTargets(buildTargets(pts as number[][], WORDS));
        continueRender(handle);
      })
      .catch((e) => cancelRender(e));
  }, [handle]);

  useEffect(() => {
    if (!targets || !canvas.current) return;
    draw(canvas.current.getContext("2d")!, targets, sprite, frame / FPS);
  }, [frame, targets, sprite]);

  return (
    <AbsoluteFill>
      <canvas
        ref={canvas}
        width={WIDTH}
        height={HEIGHT}
        style={{ width: "100%", height: "100%" }}
      />
    </AbsoluteFill>
  );
};
