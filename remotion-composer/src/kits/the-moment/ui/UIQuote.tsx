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

export interface UIQuoteProps {
  quote: string;
  attribution: string;
  /** e.g. "House of Commons, 1833" */
  context?: string;
  /**
   * Honesty tag — REQUIRED semantic: "transcript" for verbatim sourced text,
   * "paraphrase" for reworded content. Rendered as a visible corner tag so a
   * typeset card is never mistaken for a facsimile (no fake scans, R3 rule).
   */
  kind: "transcript" | "paraphrase";
  locale?: "en" | "zh";
  accent?: string;
  /** override the tag label, e.g. 「大意转述」 for the Lin Zexu card
   * (v2 handoff). Only refines wording — kind semantics still required. */
  tagText?: string;
}

/**
 * UI-QUOTE — clean typeset quote card.
 * Deliberately modern typesetting on flat paper: the anti-"fake Hansard
 * facsimile" primitive. The kind tag is mandatory and always visible.
 */
export const UIQuote: React.FC<UIQuoteProps> = ({
  quote,
  attribution,
  context,
  kind,
  locale = "en",
  accent = TM.qingBlue,
  tagText,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: TM.springSlow });
  const tagIn = spring({ frame: Math.max(0, frame - 12), fps, config: TM.spring });
  const zh = locale === "zh";

  const tagLabel =
    tagText ??
    (kind === "transcript"
      ? zh
        ? "转写 · 有源"
        : "TRANSCRIPT"
      : zh
      ? "转述"
      : "PARAPHRASE");

  return (
    <PaperBackground tone="hi">
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{ maxWidth: 1360, position: "relative" }}>
          <div
            style={{
              fontFamily: TM.fontHeading,
              fontSize: 200,
              lineHeight: 0.6,
              color: accent,
              opacity: 0.5 * enter,
              marginBottom: -40,
            }}
          >
            &ldquo;
          </div>
          <div
            style={{
              fontFamily: TM.fontHeading,
              fontSize: 54,
              lineHeight: 1.5,
              color: TM.ink,
              opacity: enter,
              transform: `translateY(${interpolate(enter, [0, 1], [20, 0])}px)`,
            }}
          >
            {quote}
          </div>
          <div
            style={{
              marginTop: 44,
              display: "flex",
              alignItems: "baseline",
              gap: 24,
              opacity: interpolate(enter, [0.5, 1], [0, 1]),
            }}
          >
            <div style={{ width: 70, height: 3, backgroundColor: accent, alignSelf: "center" }} />
            <div style={{ fontFamily: TM.fontBody, fontWeight: 600, fontSize: 36, color: TM.ink }}>
              {attribution}
            </div>
            {context ? (
              <div style={{ fontFamily: TM.fontMono, fontSize: 26, color: TM.inkSoft }}>
                {context}
              </div>
            ) : null}
          </div>
          {/* mandatory honesty tag */}
          <div
            style={{
              position: "absolute",
              top: -30,
              right: -20,
              border: `2px solid ${TM.inkFaint}`,
              color: TM.inkSoft,
              fontFamily: TM.fontMono,
              fontSize: 22,
              letterSpacing: "0.14em",
              padding: "6px 14px",
              borderRadius: 4,
              opacity: 0.9 * tagIn,
              backgroundColor: "rgba(239,230,211,0.8)",
            }}
          >
            {tagLabel}
          </div>
        </div>
      </AbsoluteFill>
    </PaperBackground>
  );
};
