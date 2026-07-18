import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { PUPPETS, PuppetId, PuppetProps } from "./puppets";

export interface CharPunchProps {
  puppet: PuppetId;
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
}

/**
 * CHAR punch wrapper — pops a puppet shell in with a spring, optional
 * name chip. A punch is a short accent (~2–4s), never a continuous
 * animation track (char_punch ≤25% of runtime per style lock).
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
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = Math.max(0, frame - delay);
  const pop = spring({ frame: f, fps, config: { damping: 14, stiffness: 200, mass: 0.8 } });
  const bob = idle ? Math.sin((f / fps) * Math.PI * 0.8) * 2 : 0;
  const chip = spring({ frame: Math.max(0, f - 8), fps, config: TM.spring });

  const Puppet = PUPPETS[puppet];
  const width = height * (240 / 340);
  const puppetProps: PuppetProps = accent ? { accent } : {};

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
        <Puppet {...puppetProps} />
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
