import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { TM } from "../theme";

/**
 * Flat paper base for every kit scene.
 *
 * Deliberately NOT a fake aged-document scan (banned: 假包浆/伪史料感)。
 * Uniform tone + very subtle procedural grain + soft edge falloff, so text
 * and ink lines stay the star. Grain is static (no shimmer between frames).
 *
 * textureSrc (2026-07-19, CEO feedback #14 "放一张老的纸上"): optional real
 * paper-texture plate (Schnell, Apache-2.0) multiplied in at low opacity as
 * an ambience layer only — typesetting stays modern, honesty tags stay on;
 * this is texture, not a facsimile.
 */
export const PaperBackground: React.FC<{
  tone?: "default" | "hi" | "lo";
  vignette?: boolean;
  /** staticFile path, e.g. "the-moment/textures/paper_quote.jpg" */
  textureSrc?: string;
  children?: React.ReactNode;
}> = ({ tone = "default", vignette = true, textureSrc, children }) => {
  const bg =
    tone === "hi" ? TM.paperHi : tone === "lo" ? TM.paperLo : TM.paper;
  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      {textureSrc ? (
        <Img
          src={staticFile(textureSrc)}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            opacity: 0.5,
            mixBlendMode: "multiply",
          }}
        />
      ) : null}
      {/* static procedural grain */}
      <svg
        width="100%"
        height="100%"
        style={{ position: "absolute", inset: 0, opacity: 0.05 }}
      >
        <filter id="tm-grain">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.9"
            numOctaves="2"
            seed="7"
            stitchTiles="stitch"
          />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#tm-grain)" />
      </svg>
      {vignette && (
        <AbsoluteFill
          style={{
            background:
              "radial-gradient(ellipse at center, rgba(0,0,0,0) 62%, rgba(42,36,28,0.10) 100%)",
          }}
        />
      )}
      <AbsoluteFill>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};
