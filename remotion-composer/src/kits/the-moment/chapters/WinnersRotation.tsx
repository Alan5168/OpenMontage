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
import { UIStamp } from "../ui/UIStamp";

/**
 * CH8 — the winners' list as a GRAMMAR ROTATION (five distinct visual
 * grammars so the chapter never becomes a card-flip list — scene plan
 * anti-fatigue rule). Each item picks one grammar:
 *
 *  compare   — two aligned columns (proposal vs outcome)
 *  lifespan  — a company/person arc that rises then terminates (or runs on)
 *  bignum    — treasury-grade single number
 *  notyet    — myth-check row killed by NOT YET stamps
 *  forecast  — a promised number that fails (stamped)
 */

export type WinnerItem =
  | {
      kind: "compare";
      title: string;
      leftTitle: string;
      rightTitle: string;
      rows: Array<[string, string]>;
    }
  | {
      kind: "lifespan";
      title: string;
      events: Array<{ year: string; text: string }>;
      terminal?: string; // e.g. "1866 — dragged down by a London banking collapse"
    }
  | { kind: "bignum"; title: string; value: string; qualifier: string }
  | { kind: "notyet"; title: string; names: Array<{ name: string; founded: string }> }
  | { kind: "forecast"; title: string; promise: string; outcome: string };

const SectionTitle: React.FC<{ text: string; index: number; total: number }> = ({
  text,
  index,
  total,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame, fps, config: TM.spring });
  return (
    <div style={{ position: "absolute", top: 84, width: "100%", textAlign: "center", opacity: p }}>
      <div style={{ fontFamily: TM.fontMono, fontSize: 24, letterSpacing: "0.3em", color: TM.inkFaint }}>
        {`WINNERS' LIST · ${index + 1}/${total}`}
      </div>
      <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 52, color: TM.ink, marginTop: 10 }}>
        {text}
      </div>
    </div>
  );
};

const CompareScene: React.FC<Extract<WinnerItem, { kind: "compare" }>> = (it) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingTop: 90 }}>
      <div style={{ display: "flex", gap: 0, border: `4px solid ${TM.ink}`, backgroundColor: TM.paperHi }}>
        {[it.leftTitle, it.rightTitle].map((h, cI) => (
          <div key={cI} style={{ width: 620, borderLeft: cI ? `3px solid ${TM.inkFaint}` : "none" }}>
            <div
              style={{
                fontFamily: TM.fontHeading,
                fontWeight: 700,
                fontSize: 36,
                color: cI ? TM.britishRed : TM.opiumPurple,
                padding: "18px 30px",
                borderBottom: `3px solid ${TM.inkFaint}`,
              }}
            >
              {h}
            </div>
            {it.rows.map((row, rI) => {
              const p = spring({ frame: Math.max(0, frame - 14 - rI * 8), fps, config: TM.spring });
              return (
                <div
                  key={rI}
                  style={{
                    fontFamily: TM.fontBody,
                    fontSize: 30,
                    color: TM.ink,
                    padding: "16px 30px",
                    opacity: p,
                    borderBottom: rI < it.rows.length - 1 ? `2px dashed ${TM.paperLo}` : "none",
                  }}
                >
                  {row[cI]}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const LifespanScene: React.FC<Extract<WinnerItem, { kind: "lifespan" }>> = (it) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const draw = interpolate(frame, [10, 70], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const W = 1400;
  const left = (1920 - W) / 2;
  // rise-then-fall arc
  const arc = `M ${left} 640 Q ${left + W * 0.3} 400 ${left + W * 0.55} 430 Q ${left + W * 0.8} 460 ${left + W} 700`;
  return (
    <AbsoluteFill>
      <svg width={1920} height={1080}>
        <path d={arc} fill="none" stroke={TM.opiumPurple} strokeWidth={6} pathLength={100} strokeDasharray="100" strokeDashoffset={100 * (1 - draw)} />
        {draw >= 1 && <line x1={left + W - 30} y1={700} x2={left + W + 30} y2={700} stroke={TM.britishRed} strokeWidth={7} />}
      </svg>
      {it.events.map((ev, i) => {
        const p = spring({ frame: Math.max(0, frame - 16 - i * 14), fps, config: TM.spring });
        const x = left + (i / Math.max(1, it.events.length - 1)) * (W - 100);
        return (
          <div key={i} style={{ position: "absolute", left: x, top: 720 + (i % 2) * 70, opacity: p, width: 320 }}>
            <div style={{ fontFamily: TM.fontMono, fontWeight: 700, fontSize: 28, color: TM.opiumPurple }}>{ev.year}</div>
            <div style={{ fontFamily: TM.fontBody, fontSize: 25, color: TM.ink, lineHeight: 1.35 }}>{ev.text}</div>
          </div>
        );
      })}
      {it.terminal ? (
        <div
          style={{
            position: "absolute",
            right: 180,
            top: 560,
            fontFamily: TM.fontBody,
            fontSize: 27,
            color: TM.britishRed,
            maxWidth: 380,
            opacity: interpolate(frame, [72, 90], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}
        >
          {it.terminal}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const BigNumScene: React.FC<Extract<WinnerItem, { kind: "bignum" }>> = (it) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: Math.max(0, frame - 12), fps, config: { damping: 15, stiffness: 200, mass: 0.8 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingTop: 60 }}>
      <div
        style={{
          fontFamily: TM.fontHeading,
          fontWeight: 700,
          fontSize: 190,
          color: TM.qingYellow,
          textShadow: `4px 4px 0 ${TM.ink}`,
          opacity: p,
          transform: `scale(${interpolate(p, [0, 1], [1.25, 1])})`,
        }}
      >
        {it.value}
      </div>
      <div style={{ fontFamily: TM.fontBody, fontSize: 34, color: TM.inkSoft, marginTop: 28, opacity: p }}>
        {it.qualifier}
      </div>
    </AbsoluteFill>
  );
};

const NotYetScene: React.FC<Extract<WinnerItem, { kind: "notyet" }>> = (it) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 50, paddingTop: 80 }}>
      {it.names.map((n, i) => {
        const p = spring({ frame: Math.max(0, frame - 8 - i * 10), fps, config: TM.spring });
        return (
          <div
            key={i}
            style={{
              position: "relative",
              opacity: p,
              display: "flex",
              alignItems: "center",
              gap: 70,
              width: 900,
              justifyContent: "flex-start",
            }}
          >
            <div
              style={{
                fontFamily: TM.fontHeading,
                fontWeight: 700,
                fontSize: 84,
                color: TM.ink,
                letterSpacing: "0.04em",
                width: 320,
              }}
            >
              {n.name}
            </div>
            {/* stamp lands beside the name, clipping its tail — name stays legible */}
            <UIStamp
              kind="not-yet"
              subtext={n.founded}
              x={620 + i * 30}
              y={44}
              rotation={i % 2 ? 7 : -9}
              scale={0.72}
              delay={34 + i * 14}
            />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const ForecastScene: React.FC<Extract<WinnerItem, { kind: "forecast" }>> = (it) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: Math.max(0, frame - 10), fps, config: TM.spring });
  const out = spring({ frame: Math.max(0, frame - 50), fps, config: TM.spring });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 46, paddingTop: 70 }}>
      <div
        style={{
          fontFamily: TM.fontHeading,
          fontWeight: 700,
          fontSize: 92,
          color: TM.opiumPurple,
          opacity: p,
          position: "relative",
        }}
      >
        {it.promise}
        <UIStamp kind="custom" text="FORECAST FAILED" x={520} y={40} rotation={-11} scale={0.8} delay={40} />
      </div>
      <div
        style={{
          fontFamily: TM.fontBody,
          fontSize: 34,
          color: TM.inkSoft,
          maxWidth: 1200,
          textAlign: "center",
          opacity: out,
        }}
      >
        {it.outcome}
      </div>
    </AbsoluteFill>
  );
};

export interface WinnersRotationProps {
  items: WinnerItem[];
  secondsPerItem?: number;
}

export const WinnersRotation: React.FC<WinnersRotationProps> = ({
  items,
  secondsPerItem = 5,
}) => {
  const { fps } = useVideoConfig();
  const dur = Math.round(secondsPerItem * fps);
  return (
    <PaperBackground>
      {items.map((it, i) => (
        <Sequence key={i} from={i * dur} durationInFrames={dur} name={`winner-${it.kind}`}>
          <SectionTitle text={it.title} index={i} total={items.length} />
          {it.kind === "compare" && <CompareScene {...it} />}
          {it.kind === "lifespan" && <LifespanScene {...it} />}
          {it.kind === "bignum" && <BigNumScene {...it} />}
          {it.kind === "notyet" && <NotYetScene {...it} />}
          {it.kind === "forecast" && <ForecastScene {...it} />}
        </Sequence>
      ))}
    </PaperBackground>
  );
};

export const winnersRotationDuration = (
  items: WinnerItem[],
  fps: number,
  secondsPerItem = 5
): number => items.length * Math.round(secondsPerItem * fps);
