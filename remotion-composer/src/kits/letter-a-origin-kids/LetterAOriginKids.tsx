/**
 * Letter A Origin — Kindergarten small-class (~1 min)
 * Track A: Astra spritesheet + bright cartoon morph (no GPU)
 * Track B: same composition with optional I2V plate overlay
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  Easing,
  Sequence,
  Video,
} from "remotion";

export type LetterATrack = "mac" | "gpu";

export type LetterAOriginKidsProps = {
  track?: LetterATrack;
  narrationSrc?: string;
  spritesheetSrc?: string;
  i2vWaveSrc?: string;
  i2vCelebrateSrc?: string;
};

const CELL_W = 192;
const CELL_H = 208;
const COLS = 8;

/** row, startCol, frameCount */
const ACTIONS: Record<string, { row: number; start: number; count: number }> = {
  idle: { row: 0, start: 0, count: 7 },
  waving: { row: 3, start: 0, count: 4 },
  jumping: { row: 4, start: 0, count: 5 },
  waiting: { row: 6, start: 0, count: 6 },
};

function AstraSprite({
  action,
  fps,
  scale = 2.4,
}: {
  action: keyof typeof ACTIONS;
  fps: number;
  scale?: number;
}) {
  const frame = useCurrentFrame();
  const a = ACTIONS[action] ?? ACTIONS.idle;
  const idx = Math.floor(frame / Math.max(1, Math.floor(fps / 8))) % a.count;
  const col = a.start + idx;
  const x = -col * CELL_W * scale;
  const y = -a.row * CELL_H * scale;
  return (
    <div
      style={{
        width: CELL_W * scale,
        height: CELL_H * scale,
        overflow: "hidden",
        filter: "drop-shadow(0 12px 18px rgba(27,27,58,0.25))",
      }}
    >
      <Img
        src={staticFile("letter-a-origin-kids/astra-spritesheet.webp")}
        style={{
          width: COLS * CELL_W * scale,
          height: 11 * CELL_H * scale,
          transform: `translate(${x}px, ${y}px)`,
          imageRendering: "auto",
          maxWidth: "none",
        }}
      />
    </div>
  );
}

function CandyBG({ t }: { t: number }) {
  const hueShift = interpolate(t, [0, 1], [0, 20]);
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg,
          hsl(${48 + hueShift} 100% 68%) 0%,
          hsl(${18 + hueShift} 100% 68%) 45%,
          hsl(${262 + hueShift} 90% 72%) 100%)`,
      }}
    >
      {/* confetti dots */}
      {Array.from({ length: 18 }).map((_, i) => {
        const left = ((i * 53) % 100);
        const top = ((i * 37) % 100);
        const size = 10 + (i % 5) * 4;
        const colors = ["#FF2D55", "#FFD60A", "#00C2FF", "#7CFF6B", "#FFFFFF"];
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${left}%`,
              top: `${top}%`,
              width: size,
              height: size,
              borderRadius: i % 2 === 0 ? "50%" : 4,
              background: colors[i % colors.length],
              opacity: 0.35,
              transform: `rotate(${i * 20}deg)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
}

function BigA({
  progress,
  pulse = 0,
}: {
  progress: number;
  pulse?: number;
}) {
  const scale = 0.6 + progress * 0.5 + pulse * 0.08;
  const rot = interpolate(progress, [0, 1], [-12, 0]);
  return (
    <div
      style={{
        fontSize: 340,
        fontWeight: 900,
        fontFamily: 'system-ui, "PingFang SC", "Segoe UI", sans-serif',
        color: "#FF2D55",
        WebkitTextStroke: "14px #FFD60A",
        paintOrder: "stroke fill",
        transform: `scale(${scale}) rotate(${rot}deg)`,
        textShadow: "0 18px 0 rgba(27,27,58,0.12)",
        lineHeight: 1,
      }}
    >
      A
    </div>
  );
}

function OxHead({ simplify }: { simplify: number }) {
  // simplify 0 = full ox, 1 = abstract A-like
  const hornSpread = interpolate(simplify, [0, 1], [70, 55]);
  const earOp = interpolate(simplify, [0, 0.4], [1, 0], {
    extrapolateRight: "clamp",
  });
  const eyeOp = interpolate(simplify, [0, 0.5], [1, 0], {
    extrapolateRight: "clamp",
  });
  const crossbar = interpolate(simplify, [0.55, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fill = simplify > 0.7 ? "#FF2D55" : "#FFB703";
  const stroke = simplify > 0.7 ? "#FFD60A" : "#E85D04";

  return (
    <svg width={420} height={360} viewBox="0 0 420 360">
      {/* horns */}
      <path
        d={`M 210 160 L ${210 - hornSpread} 40 L ${210 - hornSpread + 30} 50 Z`}
        fill={fill}
        stroke={stroke}
        strokeWidth={10}
        strokeLinejoin="round"
      />
      <path
        d={`M 210 160 L ${210 + hornSpread} 40 L ${210 + hornSpread - 30} 50 Z`}
        fill={fill}
        stroke={stroke}
        strokeWidth={10}
        strokeLinejoin="round"
      />
      {/* head */}
      {simplify < 0.75 ? (
        <ellipse
          cx={210}
          cy={200}
          rx={interpolate(simplify, [0, 0.75], [110, 70])}
          ry={interpolate(simplify, [0, 0.75], [90, 50])}
          fill={fill}
          stroke={stroke}
          strokeWidth={10}
        />
      ) : (
        <>
          <line
            x1={210 - hornSpread}
            y1={50}
            x2={210}
            y2={280}
            stroke={fill}
            strokeWidth={28}
            strokeLinecap="round"
          />
          <line
            x1={210 + hornSpread}
            y1={50}
            x2={210}
            y2={280}
            stroke={fill}
            strokeWidth={28}
            strokeLinecap="round"
          />
        </>
      )}
      {/* crossbar of A */}
      {crossbar > 0 && (
        <line
          x1={210 - 55}
          y1={200}
          x2={210 + 55}
          y2={200}
          stroke={fill}
          strokeWidth={24 * crossbar}
          strokeLinecap="round"
          opacity={crossbar}
        />
      )}
      {/* face details */}
      <g opacity={eyeOp}>
        <circle cx={175} cy={190} r={12} fill="#1B1B3A" />
        <circle cx={245} cy={190} r={12} fill="#1B1B3A" />
        <ellipse cx={210} cy={230} rx={22} ry={14} fill="#FFE5B4" opacity={earOp} />
      </g>
      <g opacity={earOp}>
        <ellipse cx={120} cy={170} rx={28} ry={22} fill="#FFB703" stroke={stroke} strokeWidth={6} />
        <ellipse cx={300} cy={170} rx={28} ry={22} fill="#FFB703" stroke={stroke} strokeWidth={6} />
      </g>
    </svg>
  );
}

function SceneHello({ track }: { track: LetterATrack }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 12, stiffness: 100 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 48 }}>
        {track === "gpu" ? (
          <div style={{ width: 420, borderRadius: 32, overflow: "hidden", boxShadow: "0 16px 40px rgba(0,0,0,0.2)" }}>
            <Video
              src={staticFile("letter-a-origin-kids/astra_i2v_wave.mp4")}
              style={{ width: "100%" }}
              muted
            />
          </div>
        ) : (
          <div style={{ transform: `scale(${0.9 + pop * 0.1})` }}>
            <AstraSprite action="waving" fps={fps} scale={2.6} />
          </div>
        )}
        <div style={{ transform: `scale(${pop})` }}>
          <BigA progress={pop} />
        </div>
      </div>
    </AbsoluteFill>
  );
}

function SceneLookA() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({ frame, fps, config: { damping: 14, stiffness: 90 } });
  const bob = Math.sin(frame / 8) * 8;
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `translateY(${bob}px)` }}>
        <BigA progress={progress} />
      </div>
    </AbsoluteFill>
  );
}

function SceneOx() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 16, stiffness: 100 } });
  const hornPulse = 0.5 + 0.5 * Math.sin(frame / 6);
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          background: "rgba(255,248,220,0.85)",
          borderRadius: 40,
          padding: 24,
          border: "8px solid #E85D04",
          transform: `scale(${0.85 + enter * 0.15})`,
          boxShadow: "0 20px 0 rgba(232,93,4,0.2)",
        }}
      >
        <OxHead simplify={0} />
      </div>
      {/* visual horn callouts — dots only, no glyphs */}
      <div
        style={{
          position: "absolute",
          top: 120,
          display: "flex",
          gap: 200,
          opacity: hornPulse,
        }}
      >
        <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#FF2D55" }} />
        <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#FF2D55" }} />
      </div>
    </AbsoluteFill>
  );
}

function SceneMorph() {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const simplify = interpolate(frame, [0, durationInFrames * 0.85], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <OxHead simplify={simplify} />
    </AbsoluteFill>
  );
}

function SceneBecomeA({ track }: { track: LetterATrack }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const beat = Math.floor(frame / (fps * 0.55)) % 4;
  const pulse = beat < 3 ? (frame % Math.floor(fps * 0.55) < 8 ? 1 : 0.3) : 0.5;
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
        {track === "gpu" ? (
          <div style={{ width: 360, borderRadius: 28, overflow: "hidden" }}>
            <Video
              src={staticFile("letter-a-origin-kids/astra_i2v_celebrate.mp4")}
              style={{ width: "100%" }}
              muted
            />
          </div>
        ) : (
          <AstraSprite action={beat < 3 ? "jumping" : "waving"} fps={fps} scale={2.4} />
        )}
        <BigA progress={1} pulse={pulse} />
      </div>
      {/* Letter-only follow-along graphic (not Chinese subtitles) */}
      <div
        style={{
          position: "absolute",
          top: 110,
          fontSize: 88,
          fontWeight: 900,
          color: "#FF2D55",
          WebkitTextStroke: "6px #FFD60A",
          paintOrder: "stroke fill",
          letterSpacing: 16,
          fontFamily: 'system-ui, "Segoe UI", sans-serif',
        }}
      >
        {beat === 0 ? "A" : beat === 1 ? "A · A" : beat === 2 ? "A · A · A" : "★"}
      </div>
    </AbsoluteFill>
  );
}

function SceneBye({ track }: { track: LetterATrack }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
          opacity: enter,
          transform: `scale(${0.9 + enter * 0.1})`,
        }}
      >
        {track === "gpu" ? (
          <div style={{ width: 380, borderRadius: 28, overflow: "hidden" }}>
            <Video
              src={staticFile("letter-a-origin-kids/astra_i2v_wave.mp4")}
              style={{ width: "100%" }}
              muted
              startFrom={0}
            />
          </div>
        ) : (
          <AstraSprite action="waving" fps={fps} scale={2.5} />
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
          <div style={{ transform: "scale(0.45)", transformOrigin: "center" }}>
            <BigA progress={1} />
          </div>
          <div style={{ transform: "scale(0.55)" }}>
            <OxHead simplify={0} />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
}

/** Total ~55s @ 30fps = 1650; narration ~48s */
export const LETTER_A_DURATION_FRAMES = 55 * 30;

export const LetterAOriginKids: React.FC<LetterAOriginKidsProps> = ({
  track = "mac",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / durationInFrames;

  // Scene frame ranges (aligned loosely to script beats + audio 48s)
  const sc = {
    hello: [0, 9 * fps],
    look: [9 * fps, 17 * fps],
    ox: [17 * fps, 30 * fps],
    morph: [30 * fps, 41 * fps],
    become: [41 * fps, 50 * fps],
    bye: [50 * fps, durationInFrames],
  } as const;

  return (
    <AbsoluteFill style={{ backgroundColor: "#FFE566" }}>
      <CandyBG t={t} />
      <Audio src={staticFile("letter-a-origin-kids/narration.mp3")} />

      <Sequence from={sc.hello[0]} durationInFrames={sc.hello[1] - sc.hello[0]}>
        <SceneHello track={track} />
      </Sequence>
      <Sequence from={sc.look[0]} durationInFrames={sc.look[1] - sc.look[0]}>
        <SceneLookA />
      </Sequence>
      <Sequence from={sc.ox[0]} durationInFrames={sc.ox[1] - sc.ox[0]}>
        <SceneOx />
      </Sequence>
      <Sequence from={sc.morph[0]} durationInFrames={sc.morph[1] - sc.morph[0]}>
        <SceneMorph />
      </Sequence>
      <Sequence from={sc.become[0]} durationInFrames={sc.become[1] - sc.become[0]}>
        <SceneBecomeA track={track} />
      </Sequence>
      <Sequence from={sc.bye[0]} durationInFrames={sc.bye[1] - sc.bye[0]}>
        <SceneBye track={track} />
      </Sequence>
    </AbsoluteFill>
  );
};
