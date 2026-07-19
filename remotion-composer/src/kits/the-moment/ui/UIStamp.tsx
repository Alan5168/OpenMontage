import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";

export type StampKind = "not-yet" | "rejected" | "counterfactual" | "custom";

export interface UIStampProps {
  kind: StampKind;
  /** custom text (required when kind === "custom", overrides otherwise) */
  text?: string;
  subtext?: string;
  locale?: "en" | "zh";
  x?: number;
  y?: number;
  rotation?: number;
  scale?: number;
  delay?: number;
  /** paper chip behind the stamp — for legibility over busy plates
   * (engraving heroes); default off so existing scenes are unchanged */
  backing?: boolean;
}

const PRESET: Record<
  Exclude<StampKind, "custom">,
  { en: string; zh: string; color: string }
> = {
  "not-yet": { en: "NOT YET FOUNDED", zh: "尚未出生", color: TM.qingBlue },
  rejected: { en: "REJECTED", zh: "未采纳", color: TM.britishRed },
  counterfactual: { en: "COUNTERFACTUAL", zh: "反事实", color: TM.opiumPurple },
};

/**
 * UI-STAMP — rubber-stamp overlay (NOT YET / REJECTED / COUNTERFACTUAL).
 * Slams in with a scale-overshoot; static after settle. Overlay positioning
 * so it can land on lists, cards and quote blocks.
 */
export const UIStamp: React.FC<UIStampProps> = ({
  kind,
  text,
  subtext,
  locale = "en",
  x = 960,
  y = 540,
  rotation = -12,
  scale = 1,
  delay = 0,
  backing = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = Math.max(0, frame - delay);
  const slam = spring({ frame: f, fps, config: { damping: 15, stiffness: 320, mass: 0.6 } });

  const preset = kind === "custom" ? null : PRESET[kind];
  const label = text ?? (preset ? preset[locale] : "");
  const color = preset?.color ?? TM.britishRed;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `translate(-50%, -50%) rotate(${rotation}deg) scale(${
          scale * interpolate(slam, [0, 1], [2.2, 1])
        })`,
        opacity: slam,
      }}
    >
      <div
        style={{
          border: `6px solid ${color}`,
          borderRadius: 10,
          padding: "14px 34px",
          textAlign: "center",
          backgroundColor: backing ? "rgba(246,239,223,0.88)" : undefined,
          // subtle uneven-ink effect without faking an aged document
          boxShadow: `inset 0 0 22px rgba(42,36,28,0.12)`,
        }}
      >
        <div
          style={{
            fontFamily: TM.fontMono,
            fontWeight: 700,
            fontSize: 54,
            letterSpacing: "0.18em",
            color,
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </div>
        {subtext ? (
          <div
            style={{
              fontFamily: TM.fontMono,
              fontSize: 24,
              letterSpacing: "0.12em",
              color,
              marginTop: 4,
              opacity: 0.85,
            }}
          >
            {subtext}
          </div>
        ) : null}
      </div>
    </div>
  );
};
