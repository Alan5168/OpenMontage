import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";
import { UIDate } from "../ui/UIDate";
import { UISchematic } from "../ui/UISchematic";

/**
 * CH3 — the Napier "fizzle" as a FIVE-CUT pacing burst (~34s of flat VO
 * becomes 5 hard cuts, GM acceptance §1.5: 分镜五连剪冲节奏, no new claims).
 * Every beat visualizes a phrase already in the accepted script sentence:
 *   frigates up the Pearl → shore batteries answering → fever → retreat
 *   → death at Macao (October).
 * All icon/line grammar on the stylised river; no naval-battle tableau,
 * no archive imagery, no invented facts.
 */

// stylised Pearl River shared by all five cuts (Canton upriver left,
// estuary lower right) — same geometry family as MapCantonApproach
const RIVER = "M 1500 1080 C 1350 800 1250 660 1050 560 C 850 460 700 430 520 400 L 520 330 C 720 350 900 380 1120 490 C 1330 590 1440 780 1600 1080 Z";

const RiverBase: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
    <path d={RIVER} fill={TM.paperHi} stroke={TM.inkSoft} strokeWidth={3} />
    {/* Canton marker */}
    <g transform="translate(480, 365)">
      <circle r={11} fill={TM.qingBlue} stroke={TM.ink} strokeWidth={3} />
      <text x={-26} y={-22} textAnchor="end" fontFamily={TM.fontBody} fontWeight={600} fontSize={28} fill={TM.ink}>
        Canton
      </text>
    </g>
    {/* Bogue forts */}
    <g transform="translate(1080, 540)">
      <path d="M -14 10 L -14 -8 L 0 -16 L 14 -8 L 14 10 Z" fill={TM.qingYellow} stroke={TM.ink} strokeWidth={3} />
    </g>
    {children}
  </svg>
);

export const Frigate: React.FC<{ x: number; y: number; angle?: number; dim?: boolean }> = ({
  x,
  y,
  angle = 0,
  dim = false,
}) => (
  <g transform={`translate(${x}, ${y}) rotate(${angle})`} opacity={dim ? 0.45 : 1}>
    <path d="M -22 8 L 22 8 L 14 18 L -14 18 Z" fill={TM.britishRed} stroke={TM.ink} strokeWidth={3} />
    <line x1={0} y1={8} x2={0} y2={-20} stroke={TM.ink} strokeWidth={3} />
    <path d="M 0 -20 L 16 -12 L 0 -6 Z" fill={TM.britishRed} stroke={TM.ink} strokeWidth={2} />
  </g>
);

const CutLabel: React.FC<{ n: number; text: string }> = ({ n, text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame, fps, config: { damping: 16, stiffness: 300, mass: 0.6 } });
  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        top: 74,
        display: "flex",
        alignItems: "center",
        gap: 20,
        opacity: p,
      }}
    >
      <div
        style={{
          width: 58,
          height: 58,
          backgroundColor: TM.ink,
          color: TM.paperHi,
          fontFamily: TM.fontMono,
          fontWeight: 700,
          fontSize: 32,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {n}
      </div>
      <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 44, color: TM.ink }}>{text}</div>
    </div>
  );
};

/** Cut 1 — frigates push upriver (movement arrows against the current). */
const Cut1: React.FC = () => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [4, 60], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const x = 1330 - 180 * t;
  const y = 800 - 190 * t;
  return (
    <PaperBackground>
      <RiverBase>
        <Frigate x={x} y={y} angle={-28} />
        <Frigate x={x + 90} y={y + 80} angle={-28} />
        <path
          d={`M ${x + 40} ${y - 60} L ${x - 40} ${y - 130}`}
          stroke={TM.britishRed}
          strokeWidth={5}
          strokeDasharray="14 10"
          fill="none"
          markerEnd="none"
        />
        <path d={`M ${x - 40} ${y - 130} L ${x - 18} ${y - 122} L ${x - 32} ${y - 104} Z`} fill={TM.britishRed} />
      </RiverBase>
      <CutLabel n={1} text="Frigates, upriver" />
      <UISchematic />
    </PaperBackground>
  );
};

/** Cut 2 — shore batteries answer (fort flashes, icon-grade). */
const Cut2: React.FC = () => {
  const frame = useCurrentFrame();
  const flash = (delay: number) =>
    interpolate((frame - delay) % 26, [0, 5, 12], [0, 1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  return (
    <PaperBackground>
      <RiverBase>
        <Frigate x={1080} y={660} angle={-20} />
        {/* fort muzzle flashes: simple star bursts, no explosion tableau */}
        {[0, 9].map((d, i) => (
          <g key={i} transform={`translate(${1062 + i * 40}, ${520 - i * 10})`} opacity={frame > d ? flash(d) : 0}>
            <path
              d="M 0 -18 L 5 -5 L 18 0 L 5 5 L 0 18 L -5 5 L -18 0 L -5 -5 Z"
              fill={TM.qingYellow}
              stroke={TM.ink}
              strokeWidth={2.5}
            />
          </g>
        ))}
        {/* answering arc from fort toward river (dashed, schematic) */}
        <path d="M 1080 528 Q 1110 590 1085 645" stroke={TM.qingBlue} strokeWidth={4} strokeDasharray="8 10" fill="none" opacity={0.9} />
      </RiverBase>
      <CutLabel n={2} text="Shore batteries answer" />
      <UISchematic />
    </PaperBackground>
  );
};

/** Cut 3 — fever (pulse line degrading over the ship, no sickbed drama). */
const Cut3: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame, fps, config: TM.springSlow });
  const flat = interpolate(frame, [30, 75], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const mid = 430;
  const amp = 46 * (1 - flat);
  const pulse = `M 560 ${mid} L 760 ${mid} L 800 ${mid - amp} L 840 ${mid + amp} L 880 ${mid} L 1080 ${mid} L 1120 ${mid - amp * 0.7} L 1160 ${mid + amp * 0.7} L 1200 ${mid} L 1400 ${mid}`;
  return (
    <PaperBackground>
      <RiverBase>
        <Frigate x={1000} y={620} angle={0} dim />
      </RiverBase>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <path d={pulse} fill="none" stroke={TM.britishRed} strokeWidth={5} opacity={p} />
      </svg>
      <div
        style={{
          position: "absolute",
          top: 300,
          width: "100%",
          textAlign: "center",
          fontFamily: TM.fontMono,
          fontSize: 30,
          letterSpacing: "0.3em",
          color: TM.britishRed,
          opacity: flat,
        }}
      >
        FEVER
      </div>
      <CutLabel n={3} text="Then fever" />
      <UISchematic />
    </PaperBackground>
  );
};

/** Cut 4 — retreat (same track, reversed, ships dimmed). */
const Cut4: React.FC = () => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [4, 60], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const x = 1150 + 250 * t;
  const y = 610 + 220 * t;
  return (
    <PaperBackground>
      <RiverBase>
        <Frigate x={x} y={y} angle={24} dim />
        <path
          d={`M ${x - 60} ${y + 20} L ${x + 30} ${y + 100}`}
          stroke={TM.inkSoft}
          strokeWidth={5}
          strokeDasharray="14 10"
          fill="none"
        />
        <path d={`M ${x + 30} ${y + 100} L ${x + 10} ${y + 88} L ${x + 16} ${y + 110} Z`} fill={TM.inkSoft} />
      </RiverBase>
      <CutLabel n={4} text="Retreat" />
      <UISchematic />
    </PaperBackground>
  );
};

/** Cut 5 — death at Macao: date pin + name plate + terminated line. */
const Cut5: React.FC<{ name: string; place: string; date: string }> = ({ name, place, date }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: Math.max(0, frame - 8), fps, config: TM.spring });
  const bar = spring({ frame: Math.max(0, frame - 30), fps, config: { damping: 15, stiffness: 240, mass: 0.7 } });
  return (
    <PaperBackground>
      <RiverBase>
        {/* Macao marker, lower estuary west bank */}
        <g transform="translate(1400, 900)" opacity={p}>
          <circle r={11} fill={TM.inkSoft} stroke={TM.ink} strokeWidth={3} />
          <text x={26} y={8} fontFamily={TM.fontBody} fontWeight={600} fontSize={28} fill={TM.ink}>
            {place}
          </text>
        </g>
      </RiverBase>
      <UIDate date={date} x={1290} y={640} delay={4} />
      {/* name plate with terminated life-line (biography grammar, no portrait) */}
      <div
        style={{
          position: "absolute",
          left: 340,
          top: 420,
          opacity: p,
        }}
      >
        <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 64, color: TM.ink }}>{name}</div>
        <svg width={520} height={40}>
          <line x1={0} y1={20} x2={430 * bar} y2={20} stroke={TM.inkSoft} strokeWidth={5} />
          {bar >= 1 && <line x1={430} y1={2} x2={430} y2={38} stroke={TM.britishRed} strokeWidth={6} />}
        </svg>
      </div>
      <CutLabel n={5} text="Death at Macao" />
      <UISchematic />
    </PaperBackground>
  );
};

export interface NapierFiveCutProps {
  /** total seconds — defaults to the flat segment length being replaced */
  totalSeconds?: number;
  name?: string;
  place?: string;
  date?: string;
}

/**
 * NapierContinuous — the same five story beats as ONE continuous scene.
 *
 * Why: the v2 read delivers all five phrases in ~8s of VO; five hard cuts
 * there run <2s each (CEO CP2 feedback #7 "太抽象看不懂" + producer
 * diagnosis §2, 4.3s/拍 already over the line). Instead of cutting, the
 * frigate itself plays the story on one river stage — sail up, batteries
 * flash, the pulse over the ship flatlines, the ship turns back dimmed,
 * the date pin and terminated life-line land at Macao. Event times are
 * fractions of totalSeconds so compose can pin them to VO phrase offsets.
 */
export interface NapierContinuousProps {
  totalSeconds?: number;
  name?: string;
  place?: string;
  date?: string;
  /** event start times as fractions of the total window [advance, batteries, fever, retreat, death] */
  eventFractions?: [number, number, number, number, number];
}

export const NapierContinuous: React.FC<NapierContinuousProps> = ({
  totalSeconds = 20,
  name = "Lord Napier",
  place = "Macao",
  date = "OCT 1834",
  eventFractions = [0.0, 0.3, 0.42, 0.58, 0.78],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const total = totalSeconds * fps;
  const [fAdv, fBat, fFev, fRet, fDeath] = eventFractions.map((f) => f * total);

  // ship track: up-river (Canton-ward) then back down, dimming after fever
  const up = interpolate(frame, [fAdv, fBat], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const down = interpolate(frame, [fRet, fDeath], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const x = 1330 - 260 * up + 320 * down;
  const y = 800 - 210 * up + 260 * down;
  const dim = frame >= fFev;

  // battery muzzle flashes (two bursts, then done — not a loop)
  const flash = (start: number) =>
    interpolate(frame - start, [0, 5, 14], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // fever pulse directly above the ship, flatlining; exits during retreat
  // so it never lingers into the death plate
  const pulseIn = spring({ frame: Math.max(0, frame - fFev), fps, config: TM.spring });
  const pulseOut = interpolate(frame, [fRet, fRet + 16], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pulseOpacity = pulseIn * pulseOut;
  const flat = interpolate(frame, [fFev + 20, fRet], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const amp = 26 * (1 - flat);
  const px = x - 130;
  const py = y - 90;
  const pulse = `M ${px} ${py} L ${px + 70} ${py} L ${px + 92} ${py - amp} L ${px + 114} ${py + amp} L ${px + 136} ${py} L ${px + 200} ${py} L ${px + 218} ${py - amp * 0.7} L ${px + 236} ${py + amp * 0.7} L ${px + 260} ${py}`;

  const death = spring({ frame: Math.max(0, frame - fDeath), fps, config: TM.spring });
  const bar = spring({ frame: Math.max(0, frame - fDeath - 14), fps, config: { damping: 15, stiffness: 240, mass: 0.7 } });

  // caption strip follows the phase (one label at a time, VO-aligned)
  const phase =
    frame >= fDeath ? "Death at Macao" : frame >= fRet ? "Retreat" : frame >= fFev ? "Fever aboard" : frame >= fBat ? "Shore batteries answer" : "Frigates, upriver";
  const phaseN = frame >= fDeath ? 5 : frame >= fRet ? 4 : frame >= fFev ? 3 : frame >= fBat ? 2 : 1;

  return (
    <PaperBackground>
      <RiverBase>
        <Frigate x={x} y={y} angle={up < 1 && down === 0 ? -28 : down > 0 ? 24 : 0} dim={dim} />
        <Frigate x={x + 90} y={y + 80} angle={up < 1 && down === 0 ? -28 : down > 0 ? 24 : 0} dim={dim} />
        {frame >= fBat &&
          [0, 10].map((d, i) => (
            <g key={i} transform={`translate(${1062 + i * 40}, ${520 - i * 10})`} opacity={flash(fBat + d)}>
              <path
                d="M 0 -18 L 5 -5 L 18 0 L 5 5 L 0 18 L -5 5 L -18 0 L -5 -5 Z"
                fill={TM.qingYellow}
                stroke={TM.ink}
                strokeWidth={2.5}
              />
            </g>
          ))}
        {frame >= fFev && pulseOpacity > 0.01 && (
          <>
            <path d={pulse} fill="none" stroke={TM.britishRed} strokeWidth={5} opacity={pulseOpacity} />
            <text
              x={px + 130}
              y={py - 44}
              textAnchor="middle"
              fontFamily={TM.fontMono}
              fontSize={26}
              letterSpacing="0.2em"
              fill={TM.britishRed}
              opacity={pulseOpacity}
            >
              FEVER — the line goes flat
            </text>
          </>
        )}
        {frame >= fDeath && (
          <g transform="translate(1400, 900)" opacity={death}>
            <circle r={11} fill={TM.inkSoft} stroke={TM.ink} strokeWidth={3} />
            <text x={26} y={8} fontFamily={TM.fontBody} fontWeight={600} fontSize={28} fill={TM.ink}>
              {place}
            </text>
          </g>
        )}
      </RiverBase>
      {frame >= fDeath && (
        <>
          <UIDate date={date} x={1290} y={640} delay={0} />
          <div style={{ position: "absolute", left: 340, top: 420, opacity: death }}>
            <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 64, color: TM.ink }}>{name}</div>
            <svg width={520} height={40}>
              <line x1={0} y1={20} x2={430 * bar} y2={20} stroke={TM.inkSoft} strokeWidth={5} />
              {bar >= 1 && <line x1={430} y1={2} x2={430} y2={38} stroke={TM.britishRed} strokeWidth={6} />}
            </svg>
          </div>
        </>
      )}
      <CutLabel n={phaseN} text={phase} />
      <UISchematic />
    </PaperBackground>
  );
};

export const NapierFiveCut: React.FC<NapierFiveCutProps> = ({
  totalSeconds = 34,
  name = "Lord Napier",
  place = "Macao",
  date = "OCT 1834",
}) => {
  const { fps } = useVideoConfig();
  const total = Math.round(totalSeconds * fps);
  // pacing: cuts shorten toward the end (7.5/7/6.5/6.5/6.5s at 34s) for
  // acceleration; hard cuts, no cross-dissolves.
  const weights = [0.22, 0.21, 0.19, 0.19, 0.19];
  const durs = weights.map((w) => Math.round(total * w));
  const starts = durs.reduce<number[]>((acc, _, i) => {
    acc.push(i === 0 ? 0 : acc[i - 1] + durs[i - 1]);
    return acc;
  }, []);
  const cuts = [
    <Cut1 key={1} />,
    <Cut2 key={2} />,
    <Cut3 key={3} />,
    <Cut4 key={4} />,
    <Cut5 key={5} name={name} place={place} date={date} />,
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: TM.paper }}>
      {cuts.map((c, i) => (
        <Sequence key={i} from={starts[i]} durationInFrames={durs[i]} name={`napier-cut-${i + 1}`}>
          {c}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
