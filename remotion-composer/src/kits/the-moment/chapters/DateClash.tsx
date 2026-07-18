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

export interface DateClashProps {
  /** the textbook date, shown first, e.g. "1842" */
  wrongYear: string;
  wrongCaption?: string;
  /** the real starting date, slams in and strikes the first, e.g. "1813" */
  rightYear: string;
  rightCaption?: string;
  /** verdict word between the two states, e.g. "WRONG MOMENT." */
  verdict?: string;
  accent?: string;
}

/**
 * V2 intent #1 — cold-open date clash card (1842 vs 1813).
 * The textbook year establishes big, the verdict strikes it through,
 * the real year slams in larger. Timing follows the CO stress beats:
 * "Wrong moment." then "It started in 1813".
 */
export const DateClash: React.FC<DateClashProps> = ({
  wrongYear,
  wrongCaption,
  rightYear,
  rightCaption,
  verdict = "WRONG MOMENT.",
  accent = TM.britishRed,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const first = spring({ frame, fps, config: TM.spring });
  const strike = spring({ frame: Math.max(0, frame - 34), fps, config: { damping: 15, stiffness: 260, mass: 0.7 } });
  const slam = spring({ frame: Math.max(0, frame - 52), fps, config: { damping: 14, stiffness: 220, mass: 0.8 } });

  return (
    <PaperBackground>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        {/* textbook year — pushed up and dimmed once the real year lands */}
        <div
          style={{
            position: "absolute",
            top: interpolate(slam, [0, 1], [280, 170]),
            textAlign: "center",
            opacity: first,
          }}
        >
          <div style={{ position: "relative", display: "inline-block" }}>
            <div
              style={{
                fontFamily: TM.fontHeading,
                fontWeight: 700,
                fontSize: interpolate(slam, [0, 1], [190, 130]),
                lineHeight: 1,
                color: TM.ink,
                opacity: interpolate(slam, [0, 1], [1, 0.45]),
              }}
            >
              {wrongYear}
            </div>
            {/* strike-through */}
            <div
              style={{
                position: "absolute",
                left: "-4%",
                top: "50%",
                width: `${108 * strike}%`,
                height: 9,
                backgroundColor: accent,
                transform: "rotate(-7deg)",
              }}
            />
          </div>
          {wrongCaption ? (
            <div
              style={{
                fontFamily: TM.fontBody,
                fontSize: 30,
                color: TM.inkSoft,
                marginTop: 8,
                opacity: interpolate(slam, [0, 1], [1, 0.5]),
              }}
            >
              {wrongCaption}
            </div>
          ) : null}
        </div>

        {/* verdict chip */}
        <div
          style={{
            position: "absolute",
            top: 468,
            fontFamily: TM.fontMono,
            fontSize: 34,
            letterSpacing: "0.3em",
            color: accent,
            opacity: strike,
            transform: `scale(${interpolate(strike, [0, 1], [1.4, 1])})`,
          }}
        >
          {verdict}
        </div>

        {/* the real year */}
        <div style={{ position: "absolute", top: 545, textAlign: "center", opacity: slam }}>
          <div
            style={{
              fontFamily: TM.fontHeading,
              fontWeight: 700,
              fontSize: 260,
              lineHeight: 1,
              color: accent,
              transform: `scale(${interpolate(slam, [0, 1], [1.3, 1])})`,
            }}
          >
            {rightYear}
          </div>
          {rightCaption ? (
            <div
              style={{
                fontFamily: TM.fontBody,
                fontSize: 34,
                color: TM.inkSoft,
                marginTop: 14,
                opacity: interpolate(slam, [0.6, 1], [0, 1]),
              }}
            >
              {rightCaption}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </PaperBackground>
  );
};
