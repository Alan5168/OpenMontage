import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BrandIdent } from "../chapters/BrandIdent";
import { InkWashBed } from "../chapters/InkWashBed";
import { TM } from "../theme";

const FPS = 30;

type Beat = { name: string; seconds: number; node: React.ReactNode };

/** Pin + wordmark overlay — shared by MMX beds and procedural InkWash. */
const PinWordmark: React.FC<{
  wordmark?: string;
  subline?: string;
  revealAtSeconds?: number;
  accent?: string;
}> = ({
  wordmark = "THE MOMENT",
  subline,
  revealAtSeconds = 1.4,
  accent = TM.britishRed,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const revealF = Math.round(revealAtSeconds * fps);
  const mark = spring({
    frame: Math.max(0, frame - revealF),
    fps,
    config: { damping: 22, stiffness: 110, mass: 1 },
  });
  const sub = spring({
    frame: Math.max(0, frame - revealF - 10),
    fps,
    config: TM.springSlow,
  });
  const exit = interpolate(frame, [durationInFrames - 20, durationInFrames - 4], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pinDrop = spring({
    frame: Math.max(0, frame - revealF + 6),
    fps,
    config: { damping: 14, stiffness: 220, mass: 0.8 },
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: exit,
        flexDirection: "column",
      }}
    >
      <div
        style={{
          position: "absolute",
          width: 980,
          height: 320,
          borderRadius: "50%",
          background: `radial-gradient(ellipse, ${TM.paper} 0%, ${TM.paper} 42%, transparent 72%)`,
          opacity: mark * 0.92,
          pointerEvents: "none",
        }}
      />
      <svg
        width={64}
        height={92}
        viewBox="0 0 34 64"
        style={{
          transform: `translateY(${interpolate(pinDrop, [0, 1], [-46, 0])}px)`,
          opacity: pinDrop,
          marginBottom: 18,
          zIndex: 1,
        }}
      >
        <line x1={17} y1={14} x2={17} y2={60} stroke={TM.ink} strokeWidth={4} />
        <circle cx={17} cy={12} r={9} fill={accent} stroke={TM.ink} strokeWidth={3} />
      </svg>
      <div
        style={{
          fontFamily: TM.fontHeading,
          fontWeight: 700,
          fontSize: 108,
          letterSpacing: "0.14em",
          color: TM.ink,
          opacity: mark,
          transform: `scale(${interpolate(mark, [0, 1], [0.96, 1])})`,
          textShadow: `0 0 28px ${TM.paper}, 0 0 48px ${TM.paper}`,
          zIndex: 1,
        }}
      >
        {wordmark}
      </div>
      <div
        style={{
          width: interpolate(mark, [0, 1], [0, 380]),
          height: 3,
          backgroundColor: accent,
          marginTop: 22,
          opacity: mark,
        }}
      />
      {subline ? (
        <div
          style={{
            fontFamily: TM.fontMono,
            fontSize: 28,
            letterSpacing: "0.34em",
            color: TM.inkSoft,
            marginTop: 24,
            opacity: sub,
            textTransform: "uppercase",
            marginLeft: "0.34em",
          }}
        >
          {subline}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/** Chapter-break transition: Remotion ink wash (clip3 substitute) + mark. */
export const IdentTransitionMark: React.FC = () => (
  <AbsoluteFill>
    <InkWashBed />
    <PinWordmark subline="A History Series" revealAtSeconds={1.4} />
  </AbsoluteFill>
);

export const IDENT_DEMO_BEATS: Beat[] = [
  {
    name: "intro BrandIdent",
    seconds: 5.5,
    node: (
      <BrandIdent
        videoSrc="the-moment/ident_intro_wire.mp4"
        wordmark="THE MOMENT"
        subline="Episode One"
        revealAtSeconds={3.6}
      />
    ),
  },
  {
    name: "transition InkWash + mark",
    seconds: 5.5,
    node: <IdentTransitionMark />,
  },
  {
    name: "outro BrandIdent (trimmed bed)",
    seconds: 4.5,
    node: (
      <BrandIdent
        videoSrc="the-moment/ident_outro_ledger_closes_trim.mp4"
        wordmark="THE MOMENT"
        subline="The ledger closes"
        revealAtSeconds={0.4}
      />
    ),
  },
];

export const identDemoDuration = (fps: number) =>
  IDENT_DEMO_BEATS.reduce((acc, b) => acc + Math.round(b.seconds * fps), 0);

export const IdentDemoReel: React.FC = () => {
  let cursor = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: TM.paper }}>
      {IDENT_DEMO_BEATS.map((b) => {
        const dur = Math.round(b.seconds * FPS);
        const from = cursor;
        cursor += dur;
        return (
          <Sequence key={b.name} from={from} durationInFrames={dur}>
            {b.node}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
