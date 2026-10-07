import { Easing, interpolate } from "remotion";

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** Progress 0..1 between two times (seconds), with optional easing. */
export const prog = (
  t: number,
  a: number,
  b: number,
  ease: (x: number) => number = (x) => x,
) => ease(clamp01((t - a) / (b - a)));

export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);
export const easeIn = Easing.bezier(0.7, 0, 0.84, 0);

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export const fade = (t: number, a: number, b: number, c: number, d: number) =>
  interpolate(t, [a, b, c, d], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** Deterministic PRNG (mulberry32). */
export const rng = (seed: number) => {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let x = s;
    x = Math.imul(x ^ (x >>> 15), x | 1);
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
};

/** Decaying pulse that starts at `at` seconds. */
export const pulse = (t: number, at: number, decay = 0.25) =>
  t < at ? 0 : Math.exp(-(t - at) / decay);
