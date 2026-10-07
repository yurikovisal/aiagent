import { useEffect, useState } from "react";
import { cancelRender, continueRender, delayRender } from "remotion";
import { fontsReady } from "./fonts";

/** Blocks rendering of each frame until the local fonts have loaded. */
export const FontGate: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [handle] = useState(() => delayRender("Loading fonts"));
  useEffect(() => {
    fontsReady()
      .then(() => continueRender(handle))
      .catch((e) => cancelRender(e));
  }, [handle]);
  return <>{children}</>;
};
