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
import { UIStamp } from "../ui/UIStamp";
import { UISchematic } from "../ui/UISchematic";

export interface NeverDeliveredProps {
  fromLabel: string; // e.g. "Canton — Lin Zexu"
  toLabel: string; // e.g. "Queen Victoria"
  endLabel: string; // e.g. "London newspapers — printed as a curiosity"
  stampText?: string; // e.g. "NEVER DELIVERED"
  accent?: string;
}

/**
 * V2 intent #6 — CH5 letter-to-Victoria routing map.
 * A letter icon travels a dotted route toward the addressee, gets bounced
 * (route forks), and lands at "the papers" with a NEVER DELIVERED stamp.
 * Icon + route grammar only — explicitly NOT a facsimile of the letter
 * (handoff: 勿伪造信件原稿扫描).
 */
export const NeverDelivered: React.FC<NeverDeliveredProps> = ({
  fromLabel,
  toLabel,
  endLabel,
  stampText = "NEVER DELIVERED",
  accent = TM.qingBlue,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const intro = spring({ frame, fps, config: TM.spring });

  // route: Canton (left-bottom) → toward crown (right-top), bounce at gate → papers (right-bottom)
  const P0 = { x: 330, y: 760 };
  const GATE = { x: 1180, y: 420 };
  const CROWN = { x: 1560, y: 300 };
  const PAPERS = { x: 1500, y: 780 };

  const leg1 = interpolate(frame, [15, 70], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const bounce = spring({ frame: Math.max(0, frame - 72), fps, config: { damping: 13, stiffness: 240, mass: 0.7 } });
  const leg2 = interpolate(frame, [84, 130], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // letter position along the two legs
  const lerp = (a: { x: number; y: number }, b: { x: number; y: number }, t: number) => ({
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
  });
  const pos = leg2 > 0 ? lerp(GATE, PAPERS, leg2) : lerp(P0, GATE, leg1);

  const node = (
    p: { x: number; y: number },
    label: string,
    icon: React.ReactNode,
    show: number,
    labelBelow = true
  ) => (
    <g transform={`translate(${p.x}, ${p.y})`} opacity={show}>
      {icon}
      <text
        x={0}
        y={labelBelow ? 64 : -46}
        textAnchor="middle"
        fontFamily={TM.fontBody}
        fontWeight={600}
        fontSize={26}
        fill={TM.ink}
        stroke={TM.paper}
        strokeWidth={6}
        paintOrder="stroke"
      >
        {label}
      </text>
    </g>
  );

  return (
    <PaperBackground>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* leg 1: dotted intended route */}
        <line
          x1={P0.x}
          y1={P0.y}
          x2={P0.x + (GATE.x - P0.x) * leg1}
          y2={P0.y + (GATE.y - P0.y) * leg1}
          stroke={accent}
          strokeWidth={4}
          strokeDasharray="4 14"
          strokeLinecap="round"
        />
        {/* intended (never travelled) continuation to the crown */}
        <line
          x1={GATE.x}
          y1={GATE.y}
          x2={CROWN.x}
          y2={CROWN.y}
          stroke={TM.inkFaint}
          strokeWidth={3}
          strokeDasharray="2 16"
          opacity={0.7 * intro}
        />
        {/* bounce gate: double bar */}
        <g opacity={bounce}>
          <line x1={GATE.x + 34} y1={GATE.y - 52} x2={GATE.x + 62} y2={GATE.y + 6} stroke={TM.britishRed} strokeWidth={9} />
          <line x1={GATE.x + 62} y1={GATE.y - 60} x2={GATE.x + 90} y2={GATE.y - 2} stroke={TM.britishRed} strokeWidth={9} />
        </g>
        {/* leg 2: deflected route to the papers */}
        {leg2 > 0 && (
          <line
            x1={GATE.x}
            y1={GATE.y}
            x2={GATE.x + (PAPERS.x - GATE.x) * leg2}
            y2={GATE.y + (PAPERS.y - GATE.y) * leg2}
            stroke={TM.inkSoft}
            strokeWidth={4}
            strokeDasharray="4 14"
            strokeLinecap="round"
          />
        )}

        {/* origin: sealed letter plate */}
        {node(
          P0,
          fromLabel,
          <g>
            <rect x={-40} y={-28} width={80} height={56} fill={TM.paperHi} stroke={TM.ink} strokeWidth={4} />
            <path d="M -40 -28 L 0 4 L 40 -28" fill="none" stroke={TM.ink} strokeWidth={3.5} />
            <circle cx={0} cy={10} r={9} fill={accent} />
          </g>,
          intro
        )}

        {/* addressee: crown icon (schematic) */}
        {node(
          CROWN,
          toLabel,
          <g opacity={0.85}>
            <path
              d="M -34 18 L -40 -14 L -18 2 L 0 -22 L 18 2 L 40 -14 L 34 18 Z"
              fill={TM.qingYellow}
              stroke={TM.ink}
              strokeWidth={4}
            />
            <rect x={-34} y={18} width={68} height={12} fill={TM.qingYellow} stroke={TM.ink} strokeWidth={4} />
          </g>,
          intro,
          false
        )}

        {/* endpoint: newspaper plate */}
        {node(
          PAPERS,
          endLabel,
          <g>
            <rect x={-46} y={-32} width={92} height={64} fill={TM.paperHi} stroke={TM.ink} strokeWidth={4} />
            <line x1={-32} y1={-16} x2={32} y2={-16} stroke={TM.inkSoft} strokeWidth={5} />
            <line x1={-32} y1={0} x2={32} y2={0} stroke={TM.inkFaint} strokeWidth={3} />
            <line x1={-32} y1={12} x2={10} y2={12} stroke={TM.inkFaint} strokeWidth={3} />
          </g>,
          leg2
        )}

        {/* travelling letter */}
        {frame >= 15 && leg2 < 1 && (
          <g transform={`translate(${pos.x}, ${pos.y})`}>
            <rect x={-26} y={-18} width={52} height={36} fill={TM.paperHi} stroke={TM.ink} strokeWidth={3.5} />
            <path d="M -26 -18 L 0 2 L 26 -18" fill="none" stroke={TM.ink} strokeWidth={3} />
          </g>
        )}
      </svg>

      {/* final stamp on the endpoint */}
      <UIStamp
        kind="custom"
        text={stampText}
        x={PAPERS.x}
        y={PAPERS.y - 100}
        rotation={-10}
        scale={0.82}
        delay={136}
      />
      <UISchematic />
    </PaperBackground>
  );
};
