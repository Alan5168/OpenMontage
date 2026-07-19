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
import { CharPunch } from "../char/CharPunch";
import { UISchematic } from "../ui/UISchematic";

export interface LifelineEvent {
  year: string;
  text: string;
}

export interface PersonVsFirmProps {
  personTitle: string; // e.g. "The man"
  personName: string; // e.g. "William Jardine"
  personEvents: LifelineEvent[]; // ends with death — line terminates
  firmTitle: string; // e.g. "The firm"
  firmName: string; // e.g. "Jardine Matheson"
  firmEvents: LifelineEvent[]; // line continues off-frame
  divider?: string; // e.g. "The firm is another story."
  personAccent?: string;
  firmAccent?: string;
  /** CP3 density split: which lane carries this hard-cut state; the other
   * lane stays as a faint anchor so the geometry never jumps */
  show?: "person" | "firm" | "both";
  /** frames between successive event reveals (VO-paced cascade) */
  eventStaggerFrames?: number;
}

/**
 * V2 intent #7 — CH8 split screen: Jardine the person vs the brand.
 * Left lane = biography line that TERMINATES (closed bracket, no glory
 * fade); right lane = company line that runs off-frame. The A4 audit
 * separation made visual: 人物线收束 / 品牌线另叙.
 */
export const PersonVsFirm: React.FC<PersonVsFirmProps> = ({
  personTitle,
  personName,
  personEvents,
  firmTitle,
  firmName,
  firmEvents,
  divider,
  personAccent = TM.inkSoft,
  firmAccent = TM.britishRed,
  show = "both",
  eventStaggerFrames = 14,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const intro = spring({ frame, fps, config: TM.spring });

  const LANE_TOP = 300;
  const LANE_BOTTOM = 900;

  const lane = (
    x: number,
    title: string,
    name: string,
    events: LifelineEvent[],
    accent: string,
    terminates: boolean,
    delayBase: number
  ) => {
    const lineP = interpolate(frame, [delayBase, delayBase + 60], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const lineEnd = LANE_TOP + 90 + (LANE_BOTTOM - LANE_TOP - 90) * lineP;
    return (
      <>
        <div
          style={{
            position: "absolute",
            left: x - 260,
            top: 170,
            width: 520,
            textAlign: "center",
            opacity: intro,
          }}
        >
          <div style={{ fontFamily: TM.fontMono, fontSize: 26, letterSpacing: "0.3em", color: TM.inkSoft, textTransform: "uppercase" }}>
            {title}
          </div>
          <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 46, color: accent, marginTop: 8 }}>
            {name}
          </div>
        </div>
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
          <line x1={x} y1={LANE_TOP + 90} x2={x} y2={lineEnd} stroke={accent} strokeWidth={5} />
          {/* terminator vs continuation */}
          {terminates
            ? lineP >= 1 && (
                <line x1={x - 34} y1={LANE_BOTTOM} x2={x + 34} y2={LANE_BOTTOM} stroke={accent} strokeWidth={6} />
              )
            : lineP >= 1 && (
                <g stroke={accent} strokeWidth={5}>
                  <line x1={x} y1={LANE_BOTTOM} x2={x} y2={LANE_BOTTOM + 40} strokeDasharray="10 10" />
                  <path d={`M ${x - 12} ${LANE_BOTTOM + 34} L ${x} ${LANE_BOTTOM + 52} L ${x + 12} ${LANE_BOTTOM + 34}`} fill="none" />
                </g>
              )}
        </svg>
        {events.map((ev, i) => {
          const evP = spring({
            frame: Math.max(0, frame - delayBase - 8 - i * eventStaggerFrames),
            fps,
            config: TM.spring,
          });
          const y = LANE_TOP + 110 + (i * (LANE_BOTTOM - LANE_TOP - 160)) / Math.max(1, events.length - 1);
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x + 26,
                top: y - 20,
                opacity: evP,
                transform: `translateX(${interpolate(evP, [0, 1], [16, 0])}px)`,
                display: "flex",
                alignItems: "baseline",
                gap: 14,
                width: 400,
              }}
            >
              <div style={{ fontFamily: TM.fontMono, fontWeight: 700, fontSize: 27, color: accent }}>{ev.year}</div>
              <div style={{ fontFamily: TM.fontBody, fontSize: 26, color: TM.ink, lineHeight: 1.35 }}>{ev.text}</div>
            </div>
          );
        })}
      </>
    );
  };

  return (
    <PaperBackground>
      {/* center divider */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: 150,
          bottom: 110,
          width: 3,
          backgroundColor: TM.inkFaint,
          opacity: 0.5 * intro,
        }}
      />
      {divider ? (
        <div
          style={{
            position: "absolute",
            top: 92,
            width: "100%",
            textAlign: "center",
            fontFamily: TM.fontHeading,
            fontStyle: "italic",
            fontSize: 34,
            color: TM.inkSoft,
            opacity: intro,
          }}
        >
          {divider}
        </div>
      ) : null}

      {/* person lane: puppet anchor, name-card grammar (no likeness) */}
      <div style={{ opacity: show === "firm" ? 0.22 : 1 }}>
        <CharPunch puppet="CHAR-MERCHANT" x={210} y={880} height={330} delay={4} idle={false} />
        {show === "firm"
          ? lane(480, personTitle, personName, [], personAccent, true, 0)
          : lane(480, personTitle, personName, personEvents, personAccent, true, 16)}
      </div>

      {/* firm lane: company emblem anchor */}
      <div style={{ opacity: show === "person" ? 0.22 : 1 }}>
        <CharPunch puppet="CHAR-COMPANY" x={1710} y={860} height={300} delay={10} idle={false} />
        {show === "person"
          ? lane(1210, firmTitle, firmName, [], firmAccent, false, 0)
          : lane(1210, firmTitle, firmName, firmEvents, firmAccent, false, 28)}
      </div>

      <UISchematic />
    </PaperBackground>
  );
};
