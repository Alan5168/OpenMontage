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

export interface ReplyCountProps {
  total?: number;
  minority?: number;
  /**
   * REQUIRED hedge line (claim #69 is soft-graded): e.g.
   * "By the count historians usually give" / 「据史家通行的统计」.
   * Not optional — the qualifier must be on screen with the number.
   */
  hedge: string;
  minorityLabel: string; // e.g. "for the death penalty"
  majorityLabel?: string; // e.g. "against / other"
  /** highlight one minority tile as Lin Zexu's reply */
  highlightLabel?: string; // e.g. "Lin Zexu"
  accent?: string;
}

/**
 * V2 intent #4 — CH5 29:8 provincial replies counter.
 * 29 memorial tiles pop in a grid; 8 flip to the minority color; one of
 * the 8 gets a name chip (Lin). Echoes the CH7 tally board grammar so the
 * two "counting scenes" rhyme across the episode (中英两侧数字互文).
 */
export const ReplyCount: React.FC<ReplyCountProps> = ({
  total = 29,
  minority = 8,
  hedge,
  minorityLabel,
  majorityLabel,
  highlightLabel,
  accent = TM.qingBlue,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const intro = spring({ frame, fps, config: TM.spring });

  const COLS = 10;
  const TILE = 86;
  const GAP = 18;
  const rows = Math.ceil(total / COLS);
  const gridW = COLS * TILE + (COLS - 1) * GAP;
  const gridH = rows * TILE + (rows - 1) * GAP;
  const left = (1920 - gridW) / 2;
  const top = (1080 - gridH) / 2 - 40;

  // pop order: sequential; last `minority` indices flip red after all pop
  const flipStart = 14 + total * 2 + 12;
  const numbersIn = spring({ frame: Math.max(0, frame - flipStart - minority * 4 - 8), fps, config: TM.spring });

  return (
    <PaperBackground>
      {/* hedge line — always visible before/with the number */}
      <div
        style={{
          position: "absolute",
          top: 120,
          width: "100%",
          textAlign: "center",
          fontFamily: TM.fontBody,
          fontStyle: "italic",
          fontSize: 32,
          color: TM.inkSoft,
          opacity: intro,
        }}
      >
        {hedge}
      </div>

      <AbsoluteFill>
        {Array.from({ length: total }).map((_, i) => {
          const pop = spring({ frame: Math.max(0, frame - 14 - i * 2), fps, config: { damping: 16, stiffness: 260, mass: 0.6 } });
          const isMinority = i >= total - minority;
          const flipP = isMinority
            ? spring({ frame: Math.max(0, frame - flipStart - (i - (total - minority)) * 4), fps, config: TM.spring })
            : 0;
          const col = i % COLS;
          const row = Math.floor(i / COLS);
          const isLin = highlightLabel != null && i === total - 1;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: left + col * (TILE + GAP),
                top: top + row * (TILE + GAP),
                width: TILE,
                height: TILE,
                border: `3.5px solid ${flipP > 0.5 ? TM.britishRed : TM.ink}`,
                backgroundColor: flipP > 0.5 ? TM.britishRed : TM.paperHi,
                opacity: pop,
                transform: `scale(${interpolate(pop, [0, 1], [0.3, 1])})`,
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
              }}
            >
              {/* schematic memorial tile: three rule lines */}
              <div style={{ display: "flex", gap: 8, height: "58%" }}>
                {[0, 1, 2].map((k) => (
                  <div
                    key={k}
                    style={{
                      width: 3,
                      backgroundColor: flipP > 0.5 ? TM.paperHi : TM.inkFaint,
                    }}
                  />
                ))}
              </div>
              {isLin && flipP > 0.7 && (
                <div
                  style={{
                    position: "absolute",
                    bottom: -44,
                    left: "50%",
                    transform: "translateX(-50%)",
                    backgroundColor: TM.ink,
                    color: TM.paperHi,
                    fontFamily: TM.fontBody,
                    fontWeight: 600,
                    fontSize: 24,
                    padding: "4px 16px",
                    whiteSpace: "nowrap",
                  }}
                >
                  {highlightLabel}
                </div>
              )}
            </div>
          );
        })}
      </AbsoluteFill>

      {/* totals strip */}
      <div
        style={{
          position: "absolute",
          bottom: 130,
          width: "100%",
          display: "flex",
          justifyContent: "center",
          gap: 110,
          opacity: numbersIn,
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 110, color: accent, lineHeight: 1 }}>
            {total}
          </div>
          <div style={{ fontFamily: TM.fontBody, fontSize: 28, color: TM.inkSoft, marginTop: 6 }}>
            {majorityLabel ?? "replies"}
          </div>
        </div>
        <div style={{ fontFamily: TM.fontHeading, fontSize: 70, color: TM.inkFaint, alignSelf: "center" }}>:</div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 110, color: TM.britishRed, lineHeight: 1 }}>
            {minority}
          </div>
          <div style={{ fontFamily: TM.fontBody, fontSize: 28, color: TM.inkSoft, marginTop: 6 }}>{minorityLabel}</div>
        </div>
      </div>
    </PaperBackground>
  );
};
