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

export interface UICensureProps {
  /** locale only switches the fixed semantic copy; the ≠ semantics are locked */
  locale?: "en" | "zh";
  /** optional clarifier line under the board */
  note?: string;
}

/**
 * UI-CENSURE — the mandatory CH6 semantic board.
 *
 * HARD RULE (scene plan §0.2 #5): the nine-votes scene must read
 * "CENSURE MOTION ≠ WAR VOTE". The two labels are intentionally NOT
 * free-text props so no compose step can regress this into "WAR YES/NO".
 */
export const UICensure: React.FC<UICensureProps> = ({ locale = "en", note }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const left = spring({ frame, fps, config: TM.spring });
  const neq = spring({ frame: Math.max(0, frame - 10), fps, config: { damping: 12, stiffness: 240, mass: 0.7 } });
  const right = spring({ frame: Math.max(0, frame - 5), fps, config: TM.spring });
  const zh = locale === "zh";

  const box = (
    label: string,
    sub: string,
    color: string,
    p: number,
    struck: boolean
  ) => (
    <div
      style={{
        border: `5px solid ${color}`,
        backgroundColor: TM.paperHi,
        padding: "44px 58px",
        textAlign: "center",
        opacity: p,
        transform: `translateY(${interpolate(p, [0, 1], [24, 0])}px)`,
        position: "relative",
        minWidth: 520,
      }}
    >
      <div
        style={{
          fontFamily: TM.fontHeading,
          fontWeight: 700,
          fontSize: 66,
          color,
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: TM.fontBody,
          fontSize: 28,
          color: TM.inkSoft,
          marginTop: 12,
        }}
      >
        {sub}
      </div>
      {struck && (
        <svg
          width="100%"
          height="100%"
          style={{ position: "absolute", inset: 0 }}
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <line
            x1={6}
            y1={82}
            x2={interpolate(neq, [0, 1], [6, 94])}
            y2={18}
            stroke={TM.ink}
            strokeWidth={2.6}
            vectorEffect="non-scaling-stroke"
            strokeLinecap="round"
            opacity={0.9}
          />
        </svg>
      )}
    </div>
  );

  return (
    <PaperBackground>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 36 }}>
        <div
          style={{
            fontFamily: TM.fontMono,
            fontSize: 30,
            letterSpacing: "0.3em",
            color: TM.inkSoft,
            opacity: left,
          }}
        >
          {zh ? "1840 年 4 月 · 下议院" : "APRIL 1840 · HOUSE OF COMMONS"}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 56 }}>
          {box(
            zh ? "谴责动议" : "CENSURE MOTION",
            zh ? "针对内阁处置的问责表决" : "a verdict on the cabinet's conduct",
            TM.qingBlue,
            left,
            false
          )}
          <div
            style={{
              fontFamily: TM.fontHeading,
              fontSize: 130,
              fontWeight: 700,
              color: TM.britishRed,
              transform: `scale(${interpolate(neq, [0, 1], [1.6, 1])})`,
              opacity: neq,
            }}
          >
            ≠
          </div>
          {box(
            zh ? "宣战表决" : "WAR VOTE",
            zh ? "议会从未就开战投票" : "Parliament never voted for war",
            TM.inkFaint,
            right,
            true
          )}
        </div>
        {note ? (
          <div
            style={{
              fontFamily: TM.fontBody,
              fontSize: 30,
              color: TM.inkSoft,
              opacity: interpolate(neq, [0.5, 1], [0, 1]),
              maxWidth: 1300,
              textAlign: "center",
            }}
          >
            {note}
          </div>
        ) : null}
      </AbsoluteFill>
    </PaperBackground>
  );
};
