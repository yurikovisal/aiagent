import { AbsoluteFill } from "remotion";
import { BODY, DISPLAY, MONO } from "../fonts";
import { ORB_Y } from "../particles/camera";
import { CYAN, T } from "../timeline";

import { easeOut, prog, pulse } from "../util";

/** 0:12–0:15 — silence, a single dot becomes the orb, logo drop. */
export const Final: React.FC<{ t: number }> = ({ t }) => {
  if (t >= T.black) return <AbsoluteFill style={{ backgroundColor: "#000" }} />;
  const glow =
    prog(t, T.orbForm, T.final, easeOut) *
    (1 + pulse(t, T.orbPulse, 0.35) * 0.8);
  const logo = prog(t, T.logo, T.logo + 0.45, easeOut);
  const soon = prog(t, T.soon, T.soon + 0.4, easeOut);
  const tag = prog(t, T.soon + 0.25, T.soon + 0.7, easeOut);
  const hit = pulse(t, T.logo, 0.3);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <div
        style={{
          position: "absolute",
          left: 540 - 420,
          top: 960 + ORB_Y - 420,
          width: 840,
          height: 840,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(62,242,255,0.28) 0%, rgba(20,120,200,0.10) 35%, rgba(0,0,0,0) 70%)",
          opacity: glow,
        }}
      />
      <AbsoluteFill style={{ alignItems: "center", top: 960 + 90 }}>
        <div
          style={{
            fontFamily: DISPLAY,
            fontWeight: 800,
            fontSize: 168,
            letterSpacing: `${0.5 - logo * 0.2}em`,
            paddingLeft: `${0.5 - logo * 0.2}em`,
            color: "#f2feff",
            opacity: logo,
            filter: `blur(${(1 - logo) * 16}px)`,
            transform: `scale(${1.1 - logo * 0.1 + hit * 0.02})`,
            textShadow: `0 0 ${30 + hit * 60}px rgba(62,242,255,${0.55 + hit * 0.4})`,
          }}
        >
          MEZA
        </div>
        <div
          style={{
            marginTop: 36,
            fontFamily: BODY,
            fontWeight: 500,
            fontSize: 40,
            letterSpacing: "0.62em",
            paddingLeft: "0.62em",
            color: CYAN,
            opacity: soon,
            transform: `translateY(${(1 - soon) * 16}px)`,
          }}
        >
          СОВСЕМ СКОРО
        </div>
        <div
          style={{
            marginTop: 26,
            width: 120 * soon,
            height: 1,
            background: "rgba(200,250,255,0.6)",
          }}
        />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          alignItems: "center",
          paddingBottom: 170,
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            fontWeight: 300,
            fontSize: 18,
            letterSpacing: "0.34em",
            color: "rgba(210,250,255,0.6)",
            opacity: tag,
            textAlign: "center",
            lineHeight: 1.8,
          }}
        >
          THE NEXT INTERFACE
          <br />
          BETWEEN HUMAN AND AI
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
