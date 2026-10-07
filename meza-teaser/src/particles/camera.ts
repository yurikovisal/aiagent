import { T } from "../timeline";
import { easeIn, easeInOut, lerp, prog, pulse } from "../util";

/** World space: pixels relative to the frame centre. */
export const SIL_SIZE = 1300; // on-screen size of the square silhouette image
export const SIL_Y = -110; // silhouette centre
export const FACE: [number, number] = [0, SIL_Y - 0.19 * SIL_SIZE];
export const ORB_Y = -250;

export type Cam = { zoom: number; x: number; y: number; rot: number };

export const camAt = (t: number): Cam => {
  if (t < T.diveStart) {
    const shake = pulse(t, T.hookHit, 0.08) * 14;
    return {
      zoom: 1 + pulse(t, T.hookHit, 0.2) * 0.04,
      x: Math.sin(t * 190) * shake,
      y: Math.cos(t * 170) * shake,
      rot: 0,
    };
  }
  if (t < T.wake) {
    const p = prog(t, T.diveStart, T.wake, easeIn);
    return {
      zoom: lerp(1, 11, p),
      x: lerp(0, FACE[0], p),
      y: lerp(0, FACE[1] + 40, p),
      rot: p * 0.25,
    };
  }
  if (t < T.humanCut) {
    const p = prog(t, T.wake, T.humanCut, easeInOut);
    const breathe = Math.sin(t * 1.3) * 0.006;
    return {
      zoom: lerp(0.92, 1.38, p) + breathe,
      x: Math.sin(t * 0.7) * 6,
      y: lerp(SIL_Y + 60, FACE[1] + 60, p),
      rot: Math.sin(t * 0.9) * 0.012,
    };
  }
  if (t < T.drop) return { zoom: 1, x: 0, y: 0, rot: 0 };
  if (t < T.silence) {
    // kinetic section: zoom punch on each beat-synced word, slow alternating roll
    let punch = 0;
    T.words.forEach((w) => (punch += pulse(t, w, 0.18)));
    const k = T.words.filter((w) => t >= w).length - 1;
    const local = t - T.words[k];
    const dir = k % 2 === 0 ? 1 : -1;
    return {
      zoom: 1 + punch * 0.16 + local * 0.05,
      x: dir * (1 - local) * 30,
      y: 0,
      rot: dir * (0.07 - local * 0.05) + punch * 0.02 * dir,
    };
  }
  return { zoom: 1, x: 0, y: 0, rot: 0 };
};

export const toScreen = (
  cam: Cam,
  wx: number,
  wy: number,
  cx: number,
  cy: number,
): [number, number] => {
  const dx = (wx - cam.x) * cam.zoom;
  const dy = (wy - cam.y) * cam.zoom;
  const c = Math.cos(cam.rot);
  const s = Math.sin(cam.rot);
  return [cx + dx * c - dy * s, cy + dx * s + dy * c];
};

/** CSS transform equivalent of toScreen for a container whose origin is the world origin. */
export const camCss = (cam: Cam, cx: number, cy: number) =>
  `translate(${cx}px, ${cy}px) rotate(${cam.rot}rad) scale(${cam.zoom}) translate(${-cam.x}px, ${-cam.y}px)`;
