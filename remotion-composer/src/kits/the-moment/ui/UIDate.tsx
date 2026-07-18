import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";

export interface UIDateProps {
  /** e.g. "22 APRIL 1834" or "1839年11月" */
  date: string;
  /** optional event line under the date, Great War title-bar style */
  event?: string;
  /** absolute position; defaults to Great War top-left slot */
  x?: number;
  y?: number;
  accent?: string;
  /** delay (in frames) before the pin drops */
  delay?: number;
  scale?: number;
}

/**
 * UI-DATE — date pin, "one sentence one state" Great War grammar.
 * A small flag-pin drops, the date plate stamps next to it.
 * Rendered as an overlay (absolute), so it can sit on maps or info scenes.
 */
export const UIDate: React.FC<UIDateProps> = ({
  date,
  event,
  x = 96,
  y = 84,
  accent = TM.britishRed,
  delay = 0,
  scale = 1,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = Math.max(0, frame - delay);
  const drop = spring({ frame: f, fps, config: { damping: 14, stiffness: 220, mass: 0.8 } });
  const plate = spring({ frame: Math.max(0, f - 4), fps, config: TM.spring });

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        display: "flex",
        alignItems: "stretch",
        transform: `scale(${scale})`,
        transformOrigin: "top left",
      }}
    >
      {/* pin */}
      <svg
        width={34}
        height={64}
        viewBox="0 0 34 64"
        style={{
          transform: `translateY(${interpolate(drop, [0, 1], [-40, 0])}px)`,
          opacity: drop,
        }}
      >
        <line x1={17} y1={14} x2={17} y2={60} stroke={TM.ink} strokeWidth={4} />
        <circle cx={17} cy={12} r={9} fill={accent} stroke={TM.ink} strokeWidth={3} />
      </svg>
      {/* plate */}
      <div
        style={{
          marginLeft: 10,
          alignSelf: "flex-start",
          backgroundColor: TM.paperHi,
          border: `3px solid ${TM.ink}`,
          boxShadow: `6px 6px 0 rgba(42,36,28,0.18)`,
          padding: "10px 22px",
          opacity: plate,
          transform: `translateX(${interpolate(plate, [0, 1], [-14, 0])}px)`,
        }}
      >
        <div
          style={{
            fontFamily: TM.fontMono,
            fontSize: 30,
            fontWeight: 700,
            letterSpacing: "0.14em",
            color: TM.ink,
            whiteSpace: "nowrap",
          }}
        >
          {date}
        </div>
        {event ? (
          <div
            style={{
              fontFamily: TM.fontBody,
              fontSize: 22,
              color: TM.inkSoft,
              marginTop: 2,
              whiteSpace: "nowrap",
            }}
          >
            {event}
          </div>
        ) : null}
      </div>
    </div>
  );
};
