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

export interface UICompareProps {
  title?: string;
  leftTitle: string;
  rightTitle: string;
  leftItems: string[];
  rightItems: string[];
  /** rows to visually connect (index pairs [leftIdx, rightIdx]) — drawn as
   * neutral alignment ties, NEVER as causal arrows (scene plan §0.2 #7) */
  ties?: Array<[number, number]>;
  leftAccent?: string;
  rightAccent?: string;
  footnote?: string;
}

/**
 * UI-COMPARE — side-by-side panel (e.g. Jardine's proposal vs treaty terms).
 * By design there is no arrow primitive between the panels: comparison only.
 */
export const UICompare: React.FC<UICompareProps> = ({
  title,
  leftTitle,
  rightTitle,
  leftItems,
  rightItems,
  ties = [],
  leftAccent = TM.opiumPurple,
  rightAccent = TM.britishRed,
  footnote,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: TM.spring });

  const ROW_H = 86;
  const PANEL_W = 700;
  const listTop = title ? 300 : 220;

  const panel = (
    heading: string,
    items: string[],
    accent: string,
    side: "left" | "right"
  ) => (
    <div style={{ width: PANEL_W }}>
      <div
        style={{
          fontFamily: TM.fontHeading,
          fontWeight: 700,
          fontSize: 44,
          color: accent,
          borderBottom: `4px solid ${accent}`,
          paddingBottom: 14,
          marginBottom: 22,
          textAlign: side === "left" ? "right" : "left",
        }}
      >
        {heading}
      </div>
      {items.map((it, i) => {
        const p = spring({
          frame: Math.max(0, frame - 8 - i * 5),
          fps,
          config: TM.spring,
        });
        return (
          <div
            key={i}
            style={{
              height: ROW_H,
              display: "flex",
              alignItems: "center",
              justifyContent: side === "left" ? "flex-end" : "flex-start",
              fontFamily: TM.fontBody,
              fontSize: 32,
              color: TM.ink,
              opacity: p,
              transform: `translateX(${interpolate(
                p,
                [0, 1],
                [side === "left" ? -24 : 24, 0]
              )}px)`,
              textAlign: side === "left" ? "right" : "left",
            }}
          >
            {it}
          </div>
        );
      })}
    </div>
  );

  return (
    <PaperBackground>
      {title ? (
        <div
          style={{
            position: "absolute",
            top: 130,
            width: "100%",
            textAlign: "center",
            fontFamily: TM.fontMono,
            fontSize: 32,
            letterSpacing: "0.24em",
            color: TM.inkSoft,
            opacity: enter,
            textTransform: "uppercase",
          }}
        >
          {title}
        </div>
      ) : null}
      <AbsoluteFill
        style={{
          top: listTop,
          flexDirection: "row",
          justifyContent: "center",
          gap: 180,
          alignItems: "flex-start",
        }}
      >
        {panel(leftTitle, leftItems, leftAccent, "left")}
        {panel(rightTitle, rightItems, rightAccent, "right")}
      </AbsoluteFill>
      {/* neutral ties (no arrowheads, no direction) */}
      <svg width="100%" height="100%" style={{ position: "absolute", inset: 0 }}>
        {ties.map(([li, ri], k) => {
          const p = spring({
            frame: Math.max(0, frame - 24 - k * 6),
            fps,
            config: TM.springSlow,
          });
          const headerOffset = listTop + 44 + 22 + 14 + 4; // heading block height
          const y1 = headerOffset + li * ROW_H + ROW_H / 2;
          const y2 = headerOffset + ri * ROW_H + ROW_H / 2;
          const x1 = 960 - 90 + 6;
          const x2 = 960 + 90 - 6;
          return (
            <line
              key={k}
              x1={x1}
              y1={y1}
              x2={interpolate(p, [0, 1], [x1, x2])}
              y2={interpolate(p, [0, 1], [y1, y2])}
              stroke={TM.inkFaint}
              strokeWidth={3}
              strokeDasharray="10 10"
              opacity={0.8 * p}
            />
          );
        })}
      </svg>
      {footnote ? (
        <div
          style={{
            position: "absolute",
            bottom: 90,
            width: "100%",
            textAlign: "center",
            fontFamily: TM.fontBody,
            fontSize: 26,
            color: TM.inkSoft,
            opacity: interpolate(enter, [0.6, 1], [0, 1]),
          }}
        >
          {footnote}
        </div>
      ) : null}
    </PaperBackground>
  );
};
