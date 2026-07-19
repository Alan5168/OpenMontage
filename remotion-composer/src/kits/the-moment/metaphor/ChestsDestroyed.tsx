import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";

/**
 * MET-CHESTS-DESTROYED — Layer C metaphor #3 (producer CP3 list §3C):
 * the Humen destruction as schematic chests tipping into a trench.
 * 示意非假史料 — kit-native shapes only, no fake archival imagery.
 */
export const ChestsDestroyed: React.FC<{
  count?: string;
  tag?: string;
}> = ({ count = "20,000+ CHESTS", tag = "HUMEN · JUN 1839 · DESTROYED IN PUBLIC" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const CHEST_W = 120;
  const CHEST_H = 74;
  // three rows of chests stacked above the trench
  const stack: { x: number; y: number; d: number }[] = [];
  const rows = [5, 4, 3];
  rows.forEach((n, r) => {
    for (let i = 0; i < n; i++) {
      stack.push({
        x: 960 - (n * (CHEST_W + 10)) / 2 + i * (CHEST_W + 10),
        y: 560 - r * (CHEST_H + 8),
        d: r * 6 + i * 3,
      });
    }
  });

  const tipStart = 22;
  const smoke = spring({ frame: Math.max(0, frame - tipStart - 16), fps, config: { damping: 40, stiffness: 40, mass: 2 } });
  const plate = spring({ frame: Math.max(0, frame - tipStart - 26), fps, config: TM.spring });

  return (
    <PaperBackground tone="lo">
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <svg width={1920} height={1080} viewBox="0 0 1920 1080">
          {/* trench */}
          <rect x={420} y={648} width={1080} height={110} fill={TM.paperLo} stroke={TM.ink} strokeWidth={8} />
          <rect x={420} y={648} width={1080} height={110} fill={TM.ink} opacity={0.12} />
          {/* chests: pop in, then tip into the trench one by one */}
          {stack.map((c, i) => {
            const pop = spring({ frame: Math.max(0, frame - c.d), fps, config: { damping: 15, stiffness: 260, mass: 0.7 } });
            const tip = spring({
              frame: Math.max(0, frame - tipStart - i * 2),
              fps,
              config: { damping: 18, stiffness: 90, mass: 1.1 },
            });
            const fallY = interpolate(tip, [0, 1], [0, 660 - c.y + 20]);
            const rot = interpolate(tip, [0, 1], [0, i % 2 ? 24 : -18]);
            const fade = interpolate(tip, [0.7, 1], [1, 0.55], { extrapolateLeft: "clamp" });
            return (
              <g
                key={i}
                opacity={pop * fade}
                transform={`translate(${c.x + CHEST_W / 2} ${c.y + CHEST_H / 2 + fallY}) rotate(${rot}) scale(${interpolate(pop, [0, 1], [0.6, 1])})`}
              >
                <rect x={-CHEST_W / 2} y={-CHEST_H / 2} width={CHEST_W} height={CHEST_H} fill={TM.paperHi} stroke={TM.ink} strokeWidth={6} />
                <line x1={-CHEST_W / 2} y1={-6} x2={CHEST_W / 2} y2={-6} stroke={TM.ink} strokeWidth={4} />
                <circle cx={0} cy={16} r={9} fill="none" stroke={TM.opiumPurple} strokeWidth={5} />
              </g>
            );
          })}
          {/* lime-and-water wash rising from the trench (schematic smoke) */}
          {[640, 960, 1280].map((sx, i) => (
            <path
              key={sx}
              d={`M ${sx} 650 C ${sx - 40} ${560 - smoke * 120} ${sx + 50} ${480 - smoke * 160} ${sx - 10 + i * 14} ${420 - smoke * 200}`}
              stroke={TM.inkSoft}
              strokeWidth={20}
              strokeLinecap="round"
              fill="none"
              opacity={smoke * 0.65}
            />
          ))}
        </svg>
        <div
          style={{
            position: "absolute",
            bottom: 168,
            fontFamily: TM.fontHeading,
            fontWeight: 700,
            fontSize: 62,
            color: TM.ink,
            opacity: plate,
          }}
        >
          {count}
        </div>
        <div
          style={{
            position: "absolute",
            bottom: 108,
            fontFamily: TM.fontMono,
            fontSize: 26,
            letterSpacing: "0.18em",
            color: TM.britishRed,
            opacity: plate,
          }}
        >
          {tag}
        </div>
      </AbsoluteFill>
    </PaperBackground>
  );
};
