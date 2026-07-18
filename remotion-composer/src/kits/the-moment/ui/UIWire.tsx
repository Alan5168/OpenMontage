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

export interface WireBead {
  year: string;
  label?: string;
}

export interface UIWireProps {
  /** beads in the order they light up (epilogue runs years in reverse) */
  beads: WireBead[];
  title?: string;
  /** frames between bead hits — keep steady, VO-alignable */
  beatFrames?: number;
  accent?: string;
}

/**
 * UI-WIRE — "run the wire backwards" timeline.
 * A wire with beads; each bead lights in sequence at a constant beat so
 * Sound can align narration hits. Constant speed per scene plan (匀速).
 */
export const UIWire: React.FC<UIWireProps> = ({
  beads,
  title,
  beatFrames = 22,
  accent = TM.opiumPurple,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const intro = spring({ frame, fps, config: TM.springSlow });

  const W = 1560;
  const left = (1920 - W) / 2;
  const y = 560;
  const n = beads.length;
  const activeIdx = Math.min(n - 1, Math.floor(Math.max(0, frame - 18) / beatFrames));
  const wireProgress = interpolate(
    Math.max(0, frame - 18),
    [0, (n - 1) * beatFrames],
    [0, 1],
    { extrapolateRight: "clamp" }
  );

  return (
    <PaperBackground>
      {title ? (
        <div
          style={{
            position: "absolute",
            top: 300,
            width: "100%",
            textAlign: "center",
            fontFamily: TM.fontHeading,
            fontWeight: 700,
            fontSize: 58,
            color: TM.ink,
            opacity: intro,
          }}
        >
          {title}
        </div>
      ) : null}
      <AbsoluteFill>
        <svg width="100%" height="100%">
          {/* base wire */}
          <line x1={left} y1={y} x2={left + W} y2={y} stroke={TM.inkFaint} strokeWidth={4} />
          {/* lit portion */}
          <line
            x1={left}
            y1={y}
            x2={left + W * wireProgress}
            y2={y}
            stroke={accent}
            strokeWidth={5}
          />
          {beads.map((b, i) => {
            const cx = left + (n === 1 ? 0.5 : i / (n - 1)) * W;
            const lit = i <= activeIdx;
            const hit = spring({
              frame: Math.max(0, frame - 18 - i * beatFrames),
              fps,
              config: { damping: 13, stiffness: 260, mass: 0.7 },
            });
            return (
              <g key={i}>
                <circle
                  cx={cx}
                  cy={y}
                  r={interpolate(hit, [0, 1], [10, 20])}
                  fill={lit ? accent : TM.paperLo}
                  stroke={TM.ink}
                  strokeWidth={4}
                />
                <text
                  x={cx}
                  y={y - 52}
                  textAnchor="middle"
                  fontFamily={TM.fontMono}
                  fontWeight={700}
                  fontSize={lit && i === activeIdx ? 46 : 34}
                  fill={lit ? TM.ink : TM.inkFaint}
                  opacity={hit}
                >
                  {b.year}
                </text>
                {b.label ? (
                  <text
                    x={cx}
                    y={y + 64}
                    textAnchor="middle"
                    fontFamily={TM.fontBody}
                    fontSize={24}
                    fill={TM.inkSoft}
                    opacity={lit ? hit : 0}
                  >
                    {b.label}
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
      </AbsoluteFill>
    </PaperBackground>
  );
};
