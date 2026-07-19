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
import { UISchematic } from "../ui/UISchematic";

export interface MemorialCard {
  year: string;
  author: string;
  position: string;
  points: string[];
  accent: string;
}

export interface MemorialsDuelProps {
  left: MemorialCard; // e.g. 1836 Xu Naiji — legalize
  right: MemorialCard; // e.g. 1838 Huang Juezi — death penalty
  title?: string;
  /** frames before the right plate enters (waveform-timed beats pass the
   * measured VO pause; default keeps the old near-simultaneous demo look) */
  rightDelayFrames?: number;
  /** CP3 density split: render one memorial centered as its own hard-cut
   * state instead of the duel layout */
  solo?: "left" | "right";
}

/**
 * V2 intent #3 — CH5 two memorials side-by-side (弛禁 vs 死刑).
 * Vertical scroll-plates in Qing document grammar — schematic vertical
 * rule lines, NOT a facsimile of real memorial manuscripts (no fake scans).
 */
export const MemorialsDuel: React.FC<MemorialsDuelProps> = ({
  left,
  right,
  title,
  rightDelayFrames = 18,
  solo,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: TM.spring });

  const plate = (m: MemorialCard, side: "left" | "right") => {
    const p = spring({
      frame: Math.max(0, frame - (side === "left" ? 6 : rightDelayFrames)),
      fps,
      config: TM.spring,
    });
    return (
      <div
        style={{
          width: 620,
          backgroundColor: TM.paperHi,
          border: `4px solid ${TM.ink}`,
          boxShadow: `10px 10px 0 rgba(42,36,28,0.14)`,
          opacity: p,
          transform: `translateY(${interpolate(p, [0, 1], [30, 0])}px)`,
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* schematic vertical rule lines (document grammar, not a facsimile) */}
        <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "space-evenly", opacity: 0.12 }}>
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} style={{ width: 2, backgroundColor: TM.inkSoft }} />
          ))}
        </div>
        <div style={{ backgroundColor: m.accent, padding: "14px 26px", position: "relative" }}>
          <div style={{ fontFamily: TM.fontMono, fontSize: 24, letterSpacing: "0.2em", color: TM.paperHi }}>
            {m.year}
          </div>
          <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 40, color: TM.paperHi, marginTop: 4 }}>
            {m.author}
          </div>
        </div>
        <div style={{ padding: "24px 30px 30px", position: "relative" }}>
          <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 34, color: m.accent, marginBottom: 18 }}>
            {m.position}
          </div>
          {m.points.map((pt, i) => {
            const pp = spring({
              frame: Math.max(
                0,
                frame - i * 6 - (side === "right" ? rightDelayFrames + 24 : 30)
              ),
              fps,
              config: TM.spring,
            });
            return (
              <div
                key={i}
                style={{
                  fontFamily: TM.fontBody,
                  fontSize: 28,
                  color: TM.ink,
                  lineHeight: 1.5,
                  marginBottom: 10,
                  opacity: pp,
                  display: "flex",
                  gap: 12,
                }}
              >
                <span style={{ color: m.accent }}>—</span>
                <span>{pt}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  if (solo) {
    const m = solo === "left" ? left : right;
    return (
      <PaperBackground>
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingTop: 20 }}>
          {/* solo plates always enter on the "left" clock — the hard cut is the state change */}
          {plate(m, "left")}
        </AbsoluteFill>
        <UISchematic />
      </PaperBackground>
    );
  }

  return (
    <PaperBackground>
      {title ? (
        <div
          style={{
            position: "absolute",
            top: 96,
            width: "100%",
            textAlign: "center",
            fontFamily: TM.fontMono,
            fontSize: 30,
            letterSpacing: "0.26em",
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
          flexDirection: "row",
          justifyContent: "center",
          alignItems: "center",
          gap: 110,
          paddingTop: 40,
        }}
      >
        {plate(left, "left")}
        <div
          style={{
            fontFamily: TM.fontHeading,
            fontSize: 76,
            color: TM.inkFaint,
            opacity: enter,
          }}
        >
          vs
        </div>
        {plate(right, "right")}
      </AbsoluteFill>
      <UISchematic />
    </PaperBackground>
  );
};
