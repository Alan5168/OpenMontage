import React from "react";
import { AbsoluteFill } from "remotion";
import { TM } from "../theme";

/**
 * Flat paper base for every kit scene.
 *
 * Deliberately NOT a fake aged-document scan (banned: 假包浆/伪史料感)。
 * Uniform tone + very subtle procedural grain + soft edge falloff, so text
 * and ink lines stay the star. Grain is static (no shimmer between frames).
 */
export const PaperBackground: React.FC<{
  tone?: "default" | "hi" | "lo";
  vignette?: boolean;
  children?: React.ReactNode;
}> = ({ tone = "default", vignette = true, children }) => {
  const bg =
    tone === "hi" ? TM.paperHi : tone === "lo" ? TM.paperLo : TM.paper;
  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
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
