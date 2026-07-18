import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TM } from "../theme";

export interface BrandIdentProps {
  /** MMX ink-texture bed, path under public/ (e.g. "the-moment/ident_transition_inkwash.mp4") */
  videoSrc: string;
  /** series wordmark, e.g. "THE MOMENT" */
  wordmark?: string;
  /** sub line, e.g. season name or channel handle */
  subline?: string;
  /** seconds into the bed video before the mark reveals (let the ink bloom first) */
  revealAtSeconds?: number;
  /** trim: play the bed from this offset */
  videoStartFrom?: number;
  accent?: string;
}

/**
 * Brand ident block — the ~1–2 min branded transition slot (post-hook,
 * before CH1), which later doubles as the mid-roll ad seam.
 *
 * Architecture: MMX-generated ink texture is the BED (质感层); the channel
 * mark is a crisp Remotion vector overlay (品牌层) — AI never renders the
 * logotype, so the brand is always sharp and revisable without re-burning
 * video quota. Same component drops onto any chapter-break ink wash.
 */
export const BrandIdent: React.FC<BrandIdentProps> = ({
  videoSrc,
  wordmark = "THE MOMENT",
  subline,
  revealAtSeconds = 1.6,
  videoStartFrom = 0,
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
  // everything eases out over the last 20 frames so the block hard-cuts
  // cleanly into the next chapter card
  const exit = interpolate(frame, [durationInFrames - 20, durationInFrames - 4], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // date-pin monogram: the series' own UI-DATE pin doubles as channel icon
  const pinDrop = spring({
    frame: Math.max(0, frame - revealF + 6),
    fps,
    config: { damping: 14, stiffness: 220, mass: 0.8 },
  });

  return (
    <AbsoluteFill style={{ backgroundColor: TM.paper }}>
      <OffthreadVideo
        src={staticFile(videoSrc)}
        startFrom={videoStartFrom}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          // dim the ink bed under the mark so wire/ink never strike through type
          opacity: interpolate(mark, [0, 1], [1, 0.28], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          opacity: exit,
        }}
      >
        {/* pin monogram (channel icon stand-in — same pin as UI-DATE) */}
        <svg
          width={64}
          height={92}
          viewBox="0 0 34 64"
          style={{
            transform: `translateY(${interpolate(pinDrop, [0, 1], [-46, 0])}px)`,
            opacity: pinDrop,
            marginBottom: 18,
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
    </AbsoluteFill>
  );
};
