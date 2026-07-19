import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";

/**
 * MET-SHIELD-NINE — Layer C metaphor #6 (producer CP3 list §3C):
 * the nine-vote shield — a paper shield takes the censure hit, cracks,
 * holds by a sliver. Kit-native; same grammar family as Ident B candidate.
 */
export const ShieldNineVotes: React.FC<{
  value?: string;
  caption?: string;
}> = ({ value = "9", caption = "the nine-vote shield — it held" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const hit = spring({ frame: Math.max(0, frame - 18), fps, config: { damping: 12, stiffness: 300, mass: 0.6 } });
  const crack = spring({ frame: Math.max(0, frame - 24), fps, config: { damping: 20, stiffness: 120, mass: 1 } });
  const settle = spring({ frame: Math.max(0, frame - 44), fps, config: TM.spring });

  // shield recoils on impact then settles
  const recoil = interpolate(hit, [0, 0.4, 1], [0, 26, 8]);
  const shake = hit > 0.01 && hit < 0.9 ? Math.sin(frame * 2.2) * interpolate(hit, [0, 1], [6, 0]) : 0;

  const crackLen = interpolate(crack, [0, 1], [0, 1]);

  return (
    <PaperBackground tone="lo">
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <svg width={1920} height={1080} viewBox="0 0 1920 1080">
          {/* censure bolt coming in from the left */}
          <g opacity={interpolate(hit, [0, 0.3], [0, 1], { extrapolateRight: "clamp" })}>
            <line
              x1={interpolate(hit, [0, 0.4], [180, 760], { extrapolateRight: "clamp" })}
              y1={540}
              x2={interpolate(hit, [0, 0.4], [420, 860], { extrapolateRight: "clamp" })}
              y2={540}
              stroke={TM.britishRed}
              strokeWidth={16}
              strokeLinecap="round"
            />
          </g>
          {/* the shield */}
          <g transform={`translate(${1020 + recoil + shake} 540)`}>
            <path
              d="M 0 -240 C 90 -216 150 -196 170 -180 C 170 -20 130 150 0 240 C -130 150 -170 -20 -170 -180 C -150 -196 -90 -216 0 -240 Z"
              fill={TM.paperHi}
              stroke={TM.ink}
              strokeWidth={10}
            />
            {/* crack from the impact point, growing */}
            <path
              d="M -168 -30 L -96 -8 L -120 40 L -40 52 L -66 110"
              stroke={TM.ink}
              strokeWidth={7}
              fill="none"
              strokeDasharray={420}
              strokeDashoffset={420 - crackLen * 420}
            />
            <text
              x={0}
              y={34}
              textAnchor="middle"
              fontFamily={TM.fontHeading}
              fontWeight={800}
              fontSize={150}
              fill={TM.britishRed}
            >
              {value}
            </text>
            <text
              x={0}
              y={96}
              textAnchor="middle"
              fontFamily={TM.fontMono}
              fontSize={30}
              letterSpacing="0.2em"
              fill={TM.inkSoft}
            >
              VOTES
            </text>
          </g>
        </svg>
        <div
          style={{
            position: "absolute",
            bottom: 120,
            fontFamily: TM.fontHeading,
            fontWeight: 700,
            fontSize: 52,
            color: TM.ink,
            opacity: settle,
          }}
        >
          {caption}
        </div>
      </AbsoluteFill>
    </PaperBackground>
  );
};
