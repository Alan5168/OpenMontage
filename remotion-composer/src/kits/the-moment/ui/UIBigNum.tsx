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

export interface UIBigNumProps {
  /** the number/word itself, e.g. "ZERO", "38,000,000", "£2,000,000+" */
  value: string;
  /**
   * REQUIRED qualifier slot (scene-plan honesty rule: big numbers carry their
   * qualifier — e.g. "direct commercial gain, China trade" under "ZERO").
   */
  qualifier: string;
  /** small kicker above, e.g. "N3 · SILVER OUTFLOW" */
  kicker?: string;
  /** versus mode: renders value vs valueRight (e.g. 271 vs 262 tally) */
  valueRight?: string;
  qualifierRight?: string;
  accent?: string;
  /** half = boxed panel (composable over maps), full = fullscreen beat */
  layout?: "full" | "half";
  /** frames before enter */
  delay?: number;
}

/**
 * UI-BIG-NUM — fullscreen/half big number with a mandatory qualifier slot.
 * Also covers the CH6 tally board via `valueRight` ("271 | 262").
 * Stamp-in entrance (scale-overshoot), no bouncing after settle.
 */
export const UIBigNum: React.FC<UIBigNumProps> = ({
  value,
  qualifier,
  kicker,
  valueRight,
  qualifierRight,
  accent = TM.britishRed,
  layout = "full",
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = Math.max(0, frame - delay);
  const stamp = spring({ frame: f, fps, config: { damping: 16, stiffness: 180, mass: 0.9 } });
  const sub = spring({ frame: Math.max(0, f - 6), fps, config: TM.spring });
  const versus = valueRight != null;

  const numBlock = (v: string, q: string | undefined, color: string) => (
    <div style={{ textAlign: "center" }}>
      <div
        style={{
          fontFamily: TM.fontHeading,
          fontWeight: 700,
          fontSize: versus ? 200 : layout === "full" ? 240 : 150,
          lineHeight: 1,
          color,
          transform: `scale(${interpolate(stamp, [0, 1], [1.25, 1])})`,
          opacity: stamp,
        }}
      >
        {v}
      </div>
      {q ? (
        <div
          style={{
            fontFamily: TM.fontBody,
            fontSize: versus ? 30 : 38,
            color: TM.inkSoft,
            marginTop: 18,
            opacity: sub,
            maxWidth: 700,
          }}
        >
          {q}
        </div>
      ) : null}
    </div>
  );

  const inner = (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 30 }}>
      {kicker ? (
        <div
          style={{
            fontFamily: TM.fontMono,
            fontSize: 30,
            letterSpacing: "0.3em",
            color: TM.inkSoft,
            opacity: sub,
            textTransform: "uppercase",
          }}
        >
          {kicker}
        </div>
      ) : null}
      {versus ? (
        <div style={{ display: "flex", alignItems: "center", gap: 70 }}>
          {numBlock(value, qualifier, accent)}
          <div
            style={{
              fontFamily: TM.fontHeading,
              fontSize: 90,
              color: TM.inkFaint,
              opacity: sub,
            }}
          >
            —
          </div>
          {numBlock(valueRight as string, qualifierRight, TM.qingBlue)}
        </div>
      ) : (
        numBlock(value, qualifier, accent)
      )}
    </AbsoluteFill>
  );

  if (layout === "half") {
    return (
      <div
        style={{
          position: "absolute",
          right: 90,
          top: 90,
          width: 760,
          height: 460,
          backgroundColor: TM.paperHi,
          border: `4px solid ${TM.ink}`,
          boxShadow: `10px 10px 0 rgba(42,36,28,0.16)`,
        }}
      >
        <div style={{ position: "relative", width: "100%", height: "100%" }}>{inner}</div>
      </div>
    );
  }
  return <PaperBackground>{inner}</PaperBackground>;
};
