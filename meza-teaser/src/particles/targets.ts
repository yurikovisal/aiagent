import { DISPLAY } from "../fonts";
import { rng } from "../util";
import { ORB_Y, SIL_SIZE, SIL_Y } from "./camera";

export const N = 5200;

export type Targets = {
  sil: Float32Array; // x, y, brightness
  scatter: Float32Array; // x, y, depth
  dust: Float32Array; // x, y, depth
  orb: Float32Array; // unit sphere x, y, z
  glyphs: Float32Array[]; // x, y
  seed: Float32Array; // per particle random 0..1 (4 values)
};

const sampleText = (text: string, rand: () => number): Float32Array => {
  const W = 1080;
  const H = 520;
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const ctx = c.getContext("2d")!;
  let size = 260;
  ctx.font = `800 ${size}px ${DISPLAY}`;
  const w = ctx.measureText(text).width;
  size = Math.min(size, (size * 990) / w);
  ctx.font = `800 ${size}px ${DISPLAY}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "#fff";
  ctx.fillText(text, W / 2, H / 2);
  const data = ctx.getImageData(0, 0, W, H).data;
  const px: number[] = [];
  for (let y = 0; y < H; y += 2) {
    for (let x = 0; x < W; x += 2) {
      if (data[(y * W + x) * 4 + 3] > 140) px.push(x, y);
    }
  }
  const out = new Float32Array(N * 2);
  const count = px.length / 2;
  for (let i = 0; i < N; i++) {
    const k = Math.floor(rand() * count);
    out[i * 2] = px[k * 2] - W / 2 + (rand() - 0.5) * 2.5;
    out[i * 2 + 1] = px[k * 2 + 1] - H / 2 + (rand() - 0.5) * 2.5;
  }
  return out;
};

export const buildTargets = (
  points: number[][],
  words: readonly string[],
): Targets => {
  const rand = rng(1337);
  const sil = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const p = points[i % points.length];
    sil[i * 3] = p[0] * SIL_SIZE;
    sil[i * 3 + 1] = p[1] * SIL_SIZE + SIL_Y;
    sil[i * 3 + 2] = p[2];
  }
  const scatter = new Float32Array(N * 3);
  const dust = new Float32Array(N * 3);
  const orb = new Float32Array(N * 3);
  const seed = new Float32Array(N * 4);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < N; i++) {
    const a = rand() * Math.PI * 2;
    const r = 700 + rand() * 1700;
    scatter[i * 3] = Math.cos(a) * r;
    scatter[i * 3 + 1] = Math.sin(a) * r * 1.3;
    scatter[i * 3 + 2] = 0.3 + rand() * 1.4;
    dust[i * 3] = (rand() - 0.5) * 1300;
    dust[i * 3 + 1] = (rand() - 0.5) * 2100;
    dust[i * 3 + 2] = 0.2 + rand() * 1.2;
    const y = 1 - (i / (N - 1)) * 2;
    const rr = Math.sqrt(1 - y * y);
    orb[i * 3] = Math.cos(golden * i) * rr;
    orb[i * 3 + 1] = y;
    orb[i * 3 + 2] = Math.sin(golden * i) * rr;
    for (let k = 0; k < 4; k++) seed[i * 4 + k] = rand();
  }
  const glyphs = words.map((w) => sampleText(w, rand));
  return { sil, scatter, dust, orb, glyphs, seed };
};

export { ORB_Y };
