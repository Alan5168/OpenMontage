import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";

/**
 * MET-PIN-PULLED — Layer C metaphor #1 (producer CP3 list §3C):
 * the first pin physically pulled out of the institution wire.
 * Kit-native, zero GPU. Promoted from Proto1813Density S4 (CEO-accepted
 * grammar) into the metaphor kit for the CO cut.
 */
export const PinPulled: React.FC<{ caption?: string; tag?: string }> = ({
  caption = "the first pin",
  tag = "1813 · CHARTER VOTE",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pull = spring({ frame: Math.max(0, frame - 12), fps, config: { damping: 16, stiffness: 140, mass: 1 } });
  const snap = spring({ frame: Math.max(0, frame - 34), fps, config: { damping: 13, stiffness: 240, mass: 0.7 } });

  const pinY = interpolate(pull, [0, 1], [0, -260]);
  const pinRot = interpolate(pull, [0, 1], [0, 24]);
  // wire sags then snaps once the pin is out
  const sag = interpolate(pull, [0, 1], [0, 90]);
  const gap = interpolate(snap, [0, 1], [0, 120]);

  return (
    <PaperBackground tone="lo">
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <svg width={1920} height={1080} viewBox="0 0 1920 1080">
          {/* the wire (institution) */}
          <path
            d={`M 160 620 Q 660 ${620 + sag} ${960 - gap} ${640 + sag}`}
            stroke={TM.ink}
            strokeWidth={10}
            fill="none"
          />
          <path
            d={`M ${960 + gap} ${640 + sag} Q 1260 ${620 + sag} 1760 620`}
            stroke={TM.ink}
            strokeWidth={10}
            fill="none"
          />
          {/* anchor pins left/right (still holding) */}
          {[160, 1760].map((px) => (
            <g key={px}>
              <line x1={px} y1={620} x2={px} y2={520} stroke={TM.ink} strokeWidth={8} />
              <circle cx={px} cy={510} r={16} fill={TM.inkSoft} stroke={TM.ink} strokeWidth={5} />
            </g>
          ))}
          {/* the pulled pin */}
          <g transform={`translate(960 ${560 + pinY}) rotate(${pinRot})`}>
            <line x1={0} y1={60} x2={0} y2={-40} stroke={TM.ink} strokeWidth={10} />
            <circle cx={0} cy={-52} r={22} fill={TM.britishRed} stroke={TM.ink} strokeWidth={6} />
          </g>
        </svg>
        <div
          style={{
            position: "absolute",
            bottom: 150,
            fontFamily: TM.fontHeading,
            fontWeight: 700,
            fontSize: 58,
            color: TM.ink,
            opacity: snap,
          }}
        >
          {caption}
        </div>
        <div
          style={{
            position: "absolute",
            bottom: 96,
            fontFamily: TM.fontMono,
            fontSize: 26,
            letterSpacing: "0.2em",
            color: TM.britishRed,
            opacity: snap,
          }}
        >
          {tag}
        </div>
      </AbsoluteFill>
    </PaperBackground>
  );
};
