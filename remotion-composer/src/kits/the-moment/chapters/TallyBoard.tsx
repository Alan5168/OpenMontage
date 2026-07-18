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

export interface TallyBoardProps {
  /** header is semantically fixed to censure grammar; only locale switches */
  locale?: "en" | "zh";
  noes?: number; // 271 against the motion (government side survives)
  ayes?: number; // 262 for the motion
  noesLabel?: string;
  ayesLabel?: string;
  /** margin line, e.g. "Government survives by NINE" */
  marginLine?: string;
  date?: string;
}

/**
 * CH7 — division tally board.
 * HARD RULE: header always carries CENSURE MOTION wording (locale-switched,
 * not free-text) so the board can never read as a war vote. Digits flip in
 * odometer style; the nine-vote margin lands last as the payoff.
 */
export const TallyBoard: React.FC<TallyBoardProps> = ({
  locale = "en",
  noes = 271,
  ayes = 262,
  noesLabel,
  ayesLabel,
  marginLine,
  date,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zh = locale === "zh";
  const intro = spring({ frame, fps, config: TM.spring });
  const margin = spring({ frame: Math.max(0, frame - 95), fps, config: { damping: 14, stiffness: 220, mass: 0.8 } });

  const counted = (target: number, delay: number) => {
    const t = interpolate(frame, [delay, delay + 55], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    // ease-out count-up
    return Math.round(target * (1 - Math.pow(1 - t, 3)));
  };

  const col = (
    value: number,
    label: string,
    color: string,
    delay: number
  ) => (
    <div style={{ textAlign: "center", width: 560 }}>
      <div
        style={{
          fontFamily: TM.fontMono,
          fontWeight: 700,
          fontSize: 210,
          lineHeight: 1,
          color,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {counted(value, delay)}
      </div>
      <div
        style={{
          fontFamily: TM.fontBody,
          fontSize: 34,
          color: TM.inkSoft,
          marginTop: 16,
          borderTop: `3px solid ${color}`,
          paddingTop: 14,
        }}
      >
        {label}
      </div>
    </div>
  );

  return (
    <PaperBackground>
      {/* censure header strip — fixed semantics */}
      <div
        style={{
          position: "absolute",
          top: 90,
          width: "100%",
          textAlign: "center",
          opacity: intro,
        }}
      >
        <div
          style={{
            display: "inline-block",
            border: `4px solid ${TM.ink}`,
            backgroundColor: TM.paperHi,
            padding: "16px 44px",
          }}
        >
          <div
            style={{
              fontFamily: TM.fontMono,
              fontSize: 34,
              letterSpacing: "0.3em",
              color: TM.qingBlue,
              fontWeight: 700,
            }}
          >
            {zh ? "谴责动议 · 表决" : "CENSURE MOTION · DIVISION"}
          </div>
          <div style={{ fontFamily: TM.fontBody, fontSize: 24, color: TM.inkSoft, marginTop: 6 }}>
            {zh ? "非宣战表决 — 议会从未就开战投票" : "not a war vote — Parliament never voted on the war"}
            {date ? ` · ${date}` : ""}
          </div>
        </div>
      </div>

      <AbsoluteFill style={{ flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 120, paddingTop: 60 }}>
        {col(noes, noesLabel ?? (zh ? "反对动议（政府方）" : "Against the motion — government"), TM.qingBlue, 20)}
        {col(ayes, ayesLabel ?? (zh ? "支持动议（问责方）" : "For the motion — censure"), TM.britishRed, 34)}
      </AbsoluteFill>

      {/* nine-vote margin payoff */}
      <div
        style={{
          position: "absolute",
          bottom: 130,
          width: "100%",
          textAlign: "center",
          opacity: margin,
          transform: `scale(${interpolate(margin, [0, 1], [1.3, 1])})`,
        }}
      >
        <span
          style={{
            fontFamily: TM.fontHeading,
            fontWeight: 700,
            fontSize: 54,
            color: TM.ink,
            backgroundColor: TM.qingYellow,
            padding: "10px 36px",
            boxDecorationBreak: "clone",
          }}
        >
          {marginLine ?? (zh ? "政府以九票幸存 — 远征继续" : "Survived by NINE — the expedition lives")}
        </span>
      </div>
    </PaperBackground>
  );
};

export interface PresentInsertionProps {
  /** motion text before the insertion point */
  before: string; // e.g. "…the conduct of the"
  inserted: string; // "present"
  after: string; // e.g. "Government…"
  note?: string; // e.g. "inserted mid-debate — so the censure couldn't touch future policy"
}

/**
 * CH7 — the "present" insertion close-up. Typeset line of the motion;
 * a caret opens the gap and the word drops in with an editorial mark.
 * Typeset grammar — not a fake Hansard facsimile.
 */
export const PresentInsertion: React.FC<PresentInsertionProps> = ({
  before,
  inserted,
  after,
  note,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const line = spring({ frame, fps, config: TM.springSlow });
  const gap = spring({ frame: Math.max(0, frame - 26), fps, config: TM.spring });
  const drop = spring({ frame: Math.max(0, frame - 44), fps, config: { damping: 13, stiffness: 240, mass: 0.7 } });

  return (
    <PaperBackground tone="hi">
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div
          style={{
            fontFamily: TM.fontMono,
            fontSize: 26,
            letterSpacing: "0.24em",
            color: TM.inkSoft,
            marginBottom: 60,
            opacity: line,
          }}
        >
          THE MOTION · TYPESET
        </div>
        <div
          style={{
            fontFamily: TM.fontHeading,
            fontSize: 58,
            color: TM.ink,
            display: "flex",
            alignItems: "baseline",
            opacity: line,
            maxWidth: 1700,
            flexWrap: "wrap",
            justifyContent: "center",
            rowGap: 20,
          }}
        >
          <span>{before}&nbsp;</span>
          {/* the opening gap + dropped word */}
          <span
            style={{
              display: "inline-block",
              width: gap > 0 ? undefined : 0,
              overflow: "visible",
              position: "relative",
            }}
          >
            <span
              style={{
                display: "inline-block",
                transform: `translateY(${interpolate(drop, [0, 1], [-70, 0])}px)`,
                opacity: drop,
                color: TM.britishRed,
                fontStyle: "italic",
                fontWeight: 700,
                borderBottom: `4px solid ${TM.britishRed}`,
                margin: `0 ${interpolate(gap, [0, 1], [0, 12])}px`,
              }}
            >
              {inserted}
            </span>
            {/* editorial caret */}
            <span
              style={{
                position: "absolute",
                left: "50%",
                bottom: -34,
                transform: "translateX(-50%)",
                color: TM.britishRed,
                fontSize: 46,
                opacity: gap,
              }}
            >
              ^
            </span>
          </span>
          <span>&nbsp;{after}</span>
        </div>
        {note ? (
          <div
            style={{
              marginTop: 90,
              fontFamily: TM.fontBody,
              fontSize: 30,
              color: TM.inkSoft,
              maxWidth: 1300,
              textAlign: "center",
              opacity: interpolate(drop, [0.6, 1], [0, 1]),
            }}
          >
            {note}
          </div>
        ) : null}
      </AbsoluteFill>
    </PaperBackground>
  );
};
