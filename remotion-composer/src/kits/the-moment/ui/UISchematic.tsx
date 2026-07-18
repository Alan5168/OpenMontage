import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";

export interface UISchematicProps {
  locale?: "en" | "zh" | "both";
  corner?: "bottom-left" | "bottom-right" | "top-left" | "top-right";
  /** e.g. override to "SCHEMATIC · NOT EXACT BORDERS" for map disclaimers */
  text?: string;
}

/**
 * UI-SCHEMATIC — honesty corner badge.
 * Marks puppet punches / schematic maps as illustrative, per the
 * fact-check-footage gate (no unlabelled generated "footage").
 */
export const UISchematic: React.FC<UISchematicProps> = ({
  locale = "both",
  corner = "bottom-left",
  text,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame, fps, config: TM.springSlow });

  const label =
    text ??
    (locale === "en" ? "SCHEMATIC" : locale === "zh" ? "示意画面" : "SCHEMATIC · 示意");

  const pos: React.CSSProperties =
    corner === "bottom-left"
      ? { left: 60, bottom: 54 }
      : corner === "bottom-right"
      ? { right: 60, bottom: 54 }
      : corner === "top-left"
      ? { left: 60, top: 54 }
      : { right: 60, top: 54 };

  return (
    <div
      style={{
        position: "absolute",
        ...pos,
        opacity: 0.8 * p,
        display: "flex",
        alignItems: "center",
        gap: 12,
        backgroundColor: "rgba(239,230,211,0.7)",
        border: `2px solid ${TM.inkFaint}`,
        padding: "8px 18px",
        borderRadius: 4,
      }}
    >
      <svg width={22} height={22} viewBox="0 0 22 22">
        <rect
          x={3}
          y={3}
          width={16}
          height={16}
          fill="none"
          stroke={TM.inkSoft}
          strokeWidth={2}
          strokeDasharray="4 3"
        />
      </svg>
      <div
        style={{
          fontFamily: TM.fontMono,
          fontSize: 22,
          letterSpacing: "0.14em",
          color: TM.inkSoft,
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </div>
    </div>
  );
};
