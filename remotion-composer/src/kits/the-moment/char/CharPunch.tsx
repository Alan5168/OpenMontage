import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { PUPPETS, PuppetId, PuppetProps } from "./puppets";

/**
 * W3 painted plates (Schnell FP8, 2026-07-19, gate G + period QC v2) —
 * flat-cel cutouts with alpha, anchored feet-at-bottom like the vector
 * shells. Aspect = trimmed cutout w/h (public/the-moment/chars/MANIFEST).
 * Puppets without a plate (clerk, farmer, company emblem) keep vectors.
 */
const PLATE_DIR = "the-moment/chars";

type PlateEntry = { file: string; aspect: number };
type PlateSet = { stand: PlateEntry; action: PlateEntry };

const PLATES: Partial<Record<string, PlateSet>> = {
  "CHAR-MP": {
    stand: { file: "C6_mp_stand.png", aspect: 500 / 976 },
    action: { file: "C6_mp_action.png", aspect: 761 / 1160 },
  },
  "CHAR-MERCHANT": {
    stand: { file: "C1_merchant_stand.png", aspect: 526 / 1086 },
    action: { file: "C1_merchant_action.png", aspect: 817 / 1112 },
  },
  "CHAR-SAILOR": {
    stand: { file: "C2_sailor_stand.png", aspect: 285 / 1100 },
    action: { file: "C2_sailor_action.png", aspect: 661 / 1052 },
  },
  "CHAR-OFFICIAL-CN": {
    stand: { file: "C3_qing_official_stand.png", aspect: 416 / 1065 },
    action: { file: "C3_qing_official_action.png", aspect: 701 / 1165 },
  },
  "CHAR-COMMISSIONER-CN": {
    stand: { file: "C4_commissioner_stand.png", aspect: 432 / 1172 },
    action: { file: "C4_commissioner_action.png", aspect: 822 / 1181 },
  },
  "CHAR-TRADER": {
    stand: { file: "C5_trader_stand.png", aspect: 784 / 1041 },
    action: { file: "C5_trader_action.png", aspect: 742 / 1133 },
  },
};

/** plate-only archetypes fall back to the closest vector shell */
const VECTOR_FALLBACK: Record<string, PuppetId> = {
  "CHAR-COMMISSIONER-CN": "CHAR-OFFICIAL-CN",
  "CHAR-TRADER": "CHAR-MERCHANT",
};

export type CharId = PuppetId | "CHAR-COMMISSIONER-CN" | "CHAR-TRADER";

export interface CharPunchProps {
  puppet: CharId;
  /** name-card chip under the figure — how named people appear
   * (scene plan: 具名只用姓名字卡 + 职能模板, no likeness packs) */
  label?: string;
  x?: number;
  y?: number;
  height?: number;
  delay?: number;
  accent?: string;
  /** subtle idle bob after pop-in (2px, slow) — set false for group shots */
  idle?: boolean;
  flip?: boolean;
  /** painted-plate pose (CP3 hybrid track); vector shells ignore this */
  pose?: "stand" | "action";
  /** force the R1 vector shell even when a painted plate exists */
  vector?: boolean;
}

/**
 * CHAR punch wrapper — pops a figure in with a spring, optional name
 * chip. A punch is a short accent (~2–4s), never a continuous animation
 * track (char_punch ≤25% of runtime per style lock). CP3: painted W3
 * plates replace vector shells in place — same x/y/height anchors.
 */
export const CharPunch: React.FC<CharPunchProps> = ({
  puppet,
  label,
  x = 960,
  y = 870,
  height = 560,
  delay = 0,
  accent,
  idle = true,
  flip = false,
  pose = "stand",
  vector = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = Math.max(0, frame - delay);
  const pop = spring({ frame: f, fps, config: { damping: 14, stiffness: 200, mass: 0.8 } });
  const bob = idle ? Math.sin((f / fps) * Math.PI * 0.8) * 2 : 0;
  const chip = spring({ frame: Math.max(0, f - 8), fps, config: TM.spring });

  const plate = vector ? undefined : PLATES[puppet]?.[pose];
  const width = height * (plate ? plate.aspect : 240 / 340);

  let body: React.ReactNode;
  if (plate) {
    body = (
      <Img
        src={staticFile(`${PLATE_DIR}/${plate.file}`)}
        style={{ width: "100%", height: "100%", objectFit: "contain", objectPosition: "bottom" }}
      />
    );
  } else {
    const Puppet = PUPPETS[(puppet in PUPPETS ? puppet : VECTOR_FALLBACK[puppet]) as PuppetId];
    const puppetProps: PuppetProps = accent ? { accent } : {};
    body = <Puppet {...puppetProps} />;
  }

  return (
    <div
      style={{
        position: "absolute",
        left: x - width / 2,
        top: y - height,
        width,
        height,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          opacity: pop,
          transform: `translateY(${interpolate(pop, [0, 1], [40, 0]) + bob}px) scale(${interpolate(
            pop,
            [0, 1],
            [0.7, 1]
          )}) ${flip ? "scaleX(-1)" : ""}`,
          transformOrigin: "bottom center",
        }}
      >
        {body}
      </div>
      {label ? (
        <div
          style={{
            marginTop: 6,
            backgroundColor: TM.ink,
            color: TM.paperHi,
            fontFamily: TM.fontBody,
            fontWeight: 600,
            fontSize: 27,
            padding: "6px 22px",
            whiteSpace: "nowrap",
            opacity: chip,
            transform: `translateY(${interpolate(chip, [0, 1], [10, 0])}px)`,
          }}
        >
          {label}
        </div>
      ) : null}
    </div>
  );
};
