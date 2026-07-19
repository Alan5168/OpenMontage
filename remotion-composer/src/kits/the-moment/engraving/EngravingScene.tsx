import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TM } from "../theme";

export interface KenBurns {
  /** start / end scale (1 = fit) */
  scaleFrom: number;
  scaleTo: number;
  /** start / end pan, in % of frame (positive = image moves right/down) */
  xFrom?: number;
  xTo?: number;
  yFrom?: number;
  yTo?: number;
}

export interface EngravingSceneProps {
  /** staticFile path, e.g. "the-moment/engravings/commons_house_1833.jpg" */
  src: string;
  /** slow push/pan — every engraving must move (CEO 07-19: 除老照片外不许静止，
   * 老照片/版画也走 Ken Burns 而不是站桩) */
  kenBurns?: KenBurns;
  /** duotone strength 0–1: 0 = original, 1 = full ink/paper duotone */
  duotone?: number;
  /** darken edges and pull the eye to a moving focus point */
  spotlight?: {
    xFrom: number;
    xTo: number;
    y: number;
    /** radius in px at 1920×1080 */
    r: number;
  };
  /** source chip bottom-left (rights pointer stays on screen — Picture Gate) */
  sourceLabel?: string;
  children?: React.ReactNode;
}

/**
 * ENGRAVING scene — PD/CC0 plate as a *moving* hero layer.
 *
 * Grammar (CEO 07-18 #3/#8/#14 + 07-19 density note): real period artwork,
 * duotoned into the kit palette so it reads as one visual system, always in
 * slow motion (Ken Burns + optional spotlight sweep), overlays (UIDate,
 * UIStamp, text plates) ride on top. This is the W3 版画 main path — no
 * generated faces, no fake facsimile; the plate is credited on screen.
 */
export const EngravingScene: React.FC<EngravingSceneProps> = ({
  src,
  kenBurns = { scaleFrom: 1.06, scaleTo: 1.16 },
  duotone = 0.85,
  spotlight,
  sourceLabel,
  children,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width, height } = useVideoConfig();
  const t = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
  });

  const scale = interpolate(t, [0, 1], [kenBurns.scaleFrom, kenBurns.scaleTo]);
  const x = interpolate(t, [0, 1], [kenBurns.xFrom ?? 0, kenBurns.xTo ?? 0]);
  const y = interpolate(t, [0, 1], [kenBurns.yFrom ?? 0, kenBurns.yTo ?? 0]);

  const spotX = spotlight
    ? interpolate(t, [0, 1], [spotlight.xFrom, spotlight.xTo])
    : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: TM.paperLo, overflow: "hidden" }}>
      {/* engraving plate, grayscaled then tinted toward ink */}
      <Img
        src={staticFile(src)}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translate(${x}%, ${y}%)`,
          filter: `grayscale(${duotone}) sepia(${0.35 * duotone}) contrast(1.08) brightness(1.07)`,
        }}
      />
      {/* paper tint pulls the plate into the kit palette (duotone highlight) */}
      <AbsoluteFill
        style={{
          backgroundColor: TM.paper,
          mixBlendMode: "multiply",
          opacity: 0.35 * duotone,
        }}
      />
      {/* ink tint in the shadows */}
      <AbsoluteFill
        style={{
          backgroundColor: TM.ink,
          mixBlendMode: "soft-light",
          opacity: 0.25 * duotone,
        }}
      />
      {spotlight ? (
        <AbsoluteFill
          style={{
            background: `radial-gradient(circle ${spotlight.r}px at ${
              (spotX / 1920) * width
            }px ${(spotlight.y / 1080) * height}px, rgba(0,0,0,0) 0%, rgba(0,0,0,0) 55%, rgba(28,24,18,0.42) 100%)`,
          }}
        />
      ) : (
        <AbsoluteFill
          style={{
            background:
              "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(28,24,18,0.35) 100%)",
          }}
        />
      )}
      {sourceLabel ? (
        <div
          style={{
            position: "absolute",
            left: 40,
            bottom: 32,
            fontFamily: TM.fontMono,
            fontSize: 20,
            letterSpacing: "0.08em",
            color: TM.paperHi,
            backgroundColor: "rgba(42,36,28,0.72)",
            padding: "6px 14px",
          }}
        >
          {sourceLabel}
        </div>
      ) : null}
      <AbsoluteFill>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};
