import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";

export interface MapTitleBarProps {
  /** event name — the "one sentence one state" headline */
  title: string;
  date?: string;
  accent?: string;
  delay?: number;
}

/**
 * Map title bar — Great War grammar: top-left plate with event + date.
 * Every map state change swaps this bar's copy (one sentence, one state).
 */
export const MapTitleBar: React.FC<MapTitleBarProps> = ({
  title,
  date,
  accent = TM.britishRed,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: Math.max(0, frame - delay), fps, config: TM.spring });

  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        top: 70,
        display: "flex",
        alignItems: "stretch",
        opacity: p,
        transform: `translateX(${interpolate(p, [0, 1], [-30, 0])}px)`,
      }}
    >
      <div style={{ width: 12, backgroundColor: accent }} />
      <div
        style={{
          backgroundColor: "rgba(246,239,223,0.94)",
          border: `3px solid ${TM.ink}`,
          borderLeft: "none",
          padding: "16px 30px",
          maxWidth: 900,
        }}
      >
        <div
          style={{
            fontFamily: TM.fontHeading,
            fontWeight: 700,
            fontSize: 42,
            color: TM.ink,
            lineHeight: 1.2,
          }}
        >
          {title}
        </div>
        {date ? (
          <div
            style={{
              fontFamily: TM.fontMono,
              fontSize: 26,
              letterSpacing: "0.16em",
              color: accent,
              marginTop: 6,
            }}
          >
            {date}
          </div>
        ) : null}
      </div>
    </div>
  );
};
