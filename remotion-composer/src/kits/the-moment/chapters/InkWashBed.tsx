import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";

/**
 * Procedural ink-wash texture bed — Remotion substitute for the missing
 * MMX `ident_transition_inkwash.mp4` (interval quota exhausted mid-batch).
 *
 * Blooms from center as soft ink tendrils, then settles back to paper.
 * No text, no faces, no camera move. Loop-friendly when duration ≥ 5s.
 */
export const InkWashBed: React.FC<{ accent?: string }> = ({
  accent = TM.ink,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  // bloom 0→1 over first 45%, settle 1→0 over last 45%, hold peak briefly
  const bloom = interpolate(
    frame,
    [0, durationInFrames * 0.42, durationInFrames * 0.55, durationInFrames - 1],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const blobs = [
    { cx: 50, cy: 48, r: 28, delay: 0 },
    { cx: 38, cy: 42, r: 18, delay: 0.08 },
    { cx: 62, cy: 54, r: 16, delay: 0.12 },
    { cx: 46, cy: 58, r: 14, delay: 0.18 },
    { cx: 58, cy: 40, r: 12, delay: 0.22 },
    { cx: 52, cy: 62, r: 10, delay: 0.28 },
  ];

  return (
    <PaperBackground vignette={false}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        {blobs.map((b, i) => {
          const local = interpolate(bloom, [b.delay, Math.min(1, b.delay + 0.55)], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const size = b.r * (0.35 + local * 1.65);
          const opacity = local * (0.38 - i * 0.03);
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: `${b.cx}%`,
                top: `${b.cy}%`,
                width: `${size}vmin`,
                height: `${size}vmin`,
                marginLeft: `${-size / 2}vmin`,
                marginTop: `${-size / 2}vmin`,
                borderRadius: "50%",
                background: `radial-gradient(circle, ${accent} 0%, transparent 70%)`,
                opacity,
                filter: "blur(14px)",
                mixBlendMode: "multiply",
              }}
            />
          );
        })}
        {/* fine stipple grain over the wash */}
        <AbsoluteFill
          style={{
            opacity: bloom * 0.28,
            backgroundImage:
              "radial-gradient(circle, rgba(42,36,28,0.35) 0.6px, transparent 0.7px)",
            backgroundSize: "5px 5px",
            mixBlendMode: "multiply",
          }}
        />
      </AbsoluteFill>
    </PaperBackground>
  );
};
