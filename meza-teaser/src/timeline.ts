// All cue times in seconds. scripts/make_sfx.py mirrors these values.
export const FPS = 60;
export const WIDTH = 1080;
export const HEIGHT = 1920;
export const DURATION_S = 15;

export const T = {
  hookHit: 0.1,
  hookTextIn: 0.13,
  hookTextOut: 0.27,
  diveStart: 0.42,
  wake: 1.0,
  mezaVoice: 1.3,
  chefPulse: 1.95, // the word "шеф"
  humanCut: 4.0,
  chefVoice: 4.65,
  drop: 7.0,
  words: [7.0, 8.25, 9.5, 10.75] as const,
  silence: 12.0,
  dot: 12.3,
  orbForm: 12.75,
  final: 13.5,
  orbPulse: 13.6,
  logo: 13.75,
  soon: 14.05,
  black: 14.9,
};

export const WORDS = ["VOICE", "VISION", "DATA", "ACTION"] as const;

export const SUB_MEZA = "Здравствуйте, шеф. Какие задачи на сегодня?";
export const SUB_CHEF = "Давай покажем всем, на что ты способна.";

export const f = (s: number) => Math.round(s * FPS);

export const CYAN = "#3ef2ff";
export const CYAN_SOFT = "rgba(62, 242, 255, 0.35)";
