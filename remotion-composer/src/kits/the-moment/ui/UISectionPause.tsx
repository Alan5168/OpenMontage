import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";

export interface UISectionPauseProps {
  /** total pause length in seconds — default matches the 1.5s section break */
  seconds?: number;
  /** tiny centered ornament; keep subtle, this is a breath not a beat */
  ornament?: "rule" | "dot" | "none";
}

/**
 * UI-SECTION-PAUSE — hard-cut breathing pad aligned with the 1.5s
 * pronunciation-sheet section breaks. Fades from/to plain paper so any
 * neighbour scene can hard-cut into it without a flash.
 */
export const UISectionPause: React.FC<UISectionPauseProps> = ({
  seconds = 1.5,
  ornament = "rule",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const total = Math.max(1, Math.round(seconds * fps));
  // triangular envelope: in over 20%, hold, out over last 25%
  const visible = interpolate(
    frame,
    [0, total * 0.2, total * 0.75, total],
    [0, 0.6, 0.6, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <PaperBackground vignette={false}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        {ornament === "rule" ? (
          <div
            style={{
              width: 160,
              height: 2,
              backgroundColor: TM.inkFaint,
              opacity: visible,
            }}
          />
        ) : ornament === "dot" ? (
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: 5,
              backgroundColor: TM.inkFaint,
              opacity: visible,
            }}
          />
        ) : null}
      </AbsoluteFill>
    </PaperBackground>
  );
};
