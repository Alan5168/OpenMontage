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

export interface UIChapterProps {
  /** e.g. "CHAPTER 4" / "第四章" — empty string gives the cold-open weak card */
  kicker?: string;
  title: string;
  subtitle?: string;
  locale?: "en" | "zh";
  /** weak = cold open / epilogue variant: smaller, no rule lines */
  weak?: boolean;
  accent?: string;
}

/**
 * UI-CHAPTER — chapter title card (EN/ZH via props, same component).
 * Hard-cut friendly: reaches full legibility within ~0.5s.
 */
export const UIChapter: React.FC<UIChapterProps> = ({
  kicker,
  title,
  subtitle,
  locale = "en",
  weak = false,
  accent = TM.britishRed,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: TM.spring });
  const ruleW = interpolate(enter, [0, 1], [0, 340]);
  const zh = locale === "zh";

  return (
    <PaperBackground>
      <AbsoluteFill
        style={{ justifyContent: "center", alignItems: "center", gap: 28 }}
      >
        {kicker ? (
          <div
            style={{
              fontFamily: TM.fontMono,
              fontSize: weak ? 30 : 38,
              letterSpacing: zh ? "0.6em" : "0.42em",
              color: accent,
              opacity: enter,
              textTransform: "uppercase",
              marginLeft: zh ? "0.6em" : "0.42em",
            }}
          >
            {kicker}
          </div>
        ) : null}
        {!weak && (
          <div
            style={{
              width: ruleW,
              height: 3,
              backgroundColor: TM.ink,
              opacity: 0.85,
            }}
          />
        )}
        <div
          style={{
            fontFamily: TM.fontHeading,
            fontWeight: 700,
            fontSize: weak ? 64 : 96,
            color: TM.ink,
            maxWidth: 1500,
            textAlign: "center",
            lineHeight: 1.15,
            opacity: enter,
            transform: `translateY(${interpolate(enter, [0, 1], [26, 0])}px)`,
          }}
        >
          {title}
        </div>
        {!weak && (
          <div
            style={{
              width: ruleW,
              height: 3,
              backgroundColor: TM.ink,
              opacity: 0.85,
            }}
          />
        )}
        {subtitle ? (
          <div
            style={{
              fontFamily: TM.fontBody,
              fontSize: 34,
              color: TM.inkSoft,
              opacity: interpolate(enter, [0.4, 1], [0, 1]),
              maxWidth: 1300,
              textAlign: "center",
            }}
          >
            {subtitle}
          </div>
        ) : null}
      </AbsoluteFill>
    </PaperBackground>
  );
};
