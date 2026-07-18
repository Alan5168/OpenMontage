import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";

export interface ExecutionDateProps {
  /** law line, e.g. "Act of 1833 — passed" */
  lawLine: string;
  /** the execution date, e.g. "22 APRIL 1834" */
  date: string;
  /** label under the date, e.g. "EXECUTION DATE" */
  label?: string;
  /** countdown years ticking down to the date (CH2→CH3 bridge) */
  fromYear?: string;
  toYear?: string;
  accent?: string;
}

/**
 * V2 intent #2 — CH2-tail "execution date" calendar/countdown card.
 * A year band ticks from law-passed to effect date, then the calendar
 * plate stamps down. Countdown grammar, not a physical calendar prop.
 */
export const ExecutionDate: React.FC<ExecutionDateProps> = ({
  lawLine,
  date,
  label = "EXECUTION DATE",
  fromYear = "1833",
  toYear = "1834",
  accent = TM.britishRed,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const law = spring({ frame, fps, config: TM.spring });
  const tick = interpolate(frame, [16, 46], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const stamp = spring({ frame: Math.max(0, frame - 50), fps, config: { damping: 14, stiffness: 280, mass: 0.7 } });

  return (
    <PaperBackground>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 44 }}>
        <div
          style={{
            fontFamily: TM.fontBody,
            fontSize: 40,
            color: TM.ink,
            opacity: law,
          }}
        >
          {lawLine}
        </div>

        {/* countdown band */}
        <div style={{ display: "flex", alignItems: "center", gap: 26, opacity: law }}>
          <div style={{ fontFamily: TM.fontMono, fontSize: 34, color: TM.inkSoft }}>{fromYear}</div>
          <div style={{ position: "relative", width: 560, height: 10, backgroundColor: TM.paperLo, border: `2px solid ${TM.inkFaint}` }}>
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                bottom: 0,
                width: `${tick * 100}%`,
                backgroundColor: accent,
              }}
            />
          </div>
          <div style={{ fontFamily: TM.fontMono, fontSize: 34, color: tick >= 1 ? accent : TM.inkSoft, fontWeight: 700 }}>
            {toYear}
          </div>
        </div>

        {/* calendar plate */}
        <div
          style={{
            border: `5px solid ${TM.ink}`,
            backgroundColor: TM.paperHi,
            boxShadow: `10px 10px 0 rgba(42,36,28,0.16)`,
            padding: "0 0 26px 0",
            minWidth: 620,
            textAlign: "center",
            opacity: stamp,
            transform: `scale(${interpolate(stamp, [0, 1], [1.25, 1])})`,
          }}
        >
          <div
            style={{
              backgroundColor: accent,
              color: TM.paperHi,
              fontFamily: TM.fontMono,
              fontSize: 26,
              letterSpacing: "0.3em",
              padding: "12px 0",
              marginBottom: 20,
            }}
          >
            {label}
          </div>
          <div
            style={{
              fontFamily: TM.fontHeading,
              fontWeight: 700,
              fontSize: 92,
              color: TM.ink,
              padding: "0 46px",
            }}
          >
            {date}
          </div>
        </div>
      </AbsoluteFill>
    </PaperBackground>
  );
};
