// Bundled locally (fontsource) so rendering never depends on fonts.googleapis.com.
import "@fontsource-variable/unbounded";
import "@fontsource-variable/manrope";
import "@fontsource-variable/jetbrains-mono";

export const DISPLAY = "'Unbounded Variable', sans-serif";
export const BODY = "'Manrope Variable', sans-serif";
export const MONO = "'JetBrains Mono Variable', monospace";

const SAMPLES = "MEZA VOICE ДАВАЙ шеф 0123";

/** Resolves once every face (latin + cyrillic) is ready — needed before sampling glyphs on canvas. */
export const fontsReady = () =>
  Promise.all(
    [
      `800 100px ${DISPLAY}`,
      `300 100px ${DISPLAY}`,
      `500 100px ${BODY}`,
      `300 100px ${MONO}`,
      `500 100px ${MONO}`,
    ].map((f) => document.fonts.load(f, SAMPLES)),
  ).then(() => document.fonts.ready);
