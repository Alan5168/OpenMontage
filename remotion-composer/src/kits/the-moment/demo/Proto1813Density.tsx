import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TM } from "../theme";
import { EngravingScene } from "../engraving/EngravingScene";
import { UIDate } from "../ui/UIDate";
import { UIStamp } from "../ui/UIStamp";
import { PaperBackground } from "../paper/PaperBackground";

const FPS = 30;

/**
 * PRE-RESEARCH PROTO (2026-07-19, not wired into any cut) — CO-3 redone.
 *
 * CEO 07-19: "最好 1 句话换一下画面；动态比静态好；参考 goodcase 视觉把
 * 年龄段往下探"。 Current CO-3 = ONE puppet scene held for 17.4s / 3 sentences
 * (the screenshot CEO attached). This proto covers the same 17.4s VO window
 * with FOUR visual states, PD engravings as moving hero layers:
 *
 *   S1 0.0–3.4s   "No fleet. No emperor."      — warship plate, struck out
 *   S2 3.4–9.6s   "A room of men…"             — Commons 1833, push-in + spotlight sweep
 *   S3 9.6–13.4s  "…couldn't find Canton"      — same plate, hard reframe + stamp
 *   S4 13.4–17.4s "…pulled the first pin"      — pin physically pulled, wire snaps
 *
 * Rights: both plates PD (see goodcase_pull/pd_engraving_index.md), credited
 * on screen. No generated imagery in this scene.
 */

const S1_END = 3.4;
const S2_END = 9.6;
const S3_END = 13.4;
const TOTAL = 17.4;

/** S4 — the first pin pulled out of the institution (kit-native, animated). */
const PinPulled: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pull = spring({ frame: Math.max(0, frame - 12), fps, config: { damping: 16, stiffness: 140, mass: 1 } });
  const snap = spring({ frame: Math.max(0, frame - 34), fps, config: { damping: 13, stiffness: 240, mass: 0.7 } });

  const pinY = interpolate(pull, [0, 1], [0, -260]);
  const pinRot = interpolate(pull, [0, 1], [0, 24]);
  // wire sags then snaps once the pin is out
  const sag = interpolate(pull, [0, 1], [0, 90]);
  const gap = interpolate(snap, [0, 1], [0, 120]);

  return (
    <PaperBackground tone="lo">
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <svg width={1920} height={1080} viewBox="0 0 1920 1080">
          {/* the wire (institution) */}
          <path
            d={`M 160 620 Q 660 ${620 + sag} ${960 - gap} ${640 + sag}`}
            stroke={TM.ink}
            strokeWidth={10}
            fill="none"
          />
          <path
            d={`M ${960 + gap} ${640 + sag} Q 1260 ${620 + sag} 1760 620`}
            stroke={TM.ink}
            strokeWidth={10}
            fill="none"
          />
          {/* anchor pins left/right (still holding) */}
          {[160, 1760].map((px) => (
            <g key={px}>
              <line x1={px} y1={620} x2={px} y2={520} stroke={TM.ink} strokeWidth={8} />
              <circle cx={px} cy={510} r={16} fill={TM.inkSoft} stroke={TM.ink} strokeWidth={5} />
            </g>
          ))}
          {/* the pulled pin */}
          <g transform={`translate(960 ${560 + pinY}) rotate(${pinRot})`}>
            <line x1={0} y1={60} x2={0} y2={-40} stroke={TM.ink} strokeWidth={10} />
            <circle cx={0} cy={-52} r={22} fill={TM.britishRed} stroke={TM.ink} strokeWidth={6} />
          </g>
        </svg>
        <div
          style={{
            position: "absolute",
            bottom: 150,
            fontFamily: TM.fontHeading,
            fontWeight: 700,
            fontSize: 58,
            color: TM.ink,
            opacity: snap,
          }}
        >
          the first pin
        </div>
        <div
          style={{
            position: "absolute",
            bottom: 96,
            fontFamily: TM.fontMono,
            fontSize: 26,
            letterSpacing: "0.2em",
            color: TM.britishRed,
            opacity: snap,
          }}
        >
          1813 · CHARTER VOTE
        </div>
      </AbsoluteFill>
    </PaperBackground>
  );
};

export const Proto1813Density: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* S1 — "No fleet. No emperor." warship plate struck out */}
      <Sequence from={0} durationInFrames={Math.round(S1_END * FPS)}>
        <EngravingScene
          src="the-moment/engravings/ship_hms_wellesley.jpg"
          kenBurns={{ scaleFrom: 1.25, scaleTo: 1.12, yFrom: -2, yTo: 0 }}
          duotone={0.9}
          sourceLabel="RMG PU5981 · public domain"
        >
          <UIStamp kind="custom" text="NO FLEET" x={620} y={430} rotation={-10} delay={8} />
          <UIStamp kind="custom" text="NO EMPEROR" x={1240} y={640} rotation={6} delay={38} />
        </EngravingScene>
      </Sequence>

      {/* S2 — "A room of men in Westminster…" slow push into the chamber */}
      <Sequence
        from={Math.round(S1_END * FPS)}
        durationInFrames={Math.round((S2_END - S1_END) * FPS)}
      >
        <EngravingScene
          src="the-moment/engravings/commons_house_1833.jpg"
          kenBurns={{ scaleFrom: 1.05, scaleTo: 1.28, yFrom: 0, yTo: -3 }}
          duotone={0.8}
          spotlight={{ xFrom: 560, xTo: 1340, y: 560, r: 620 }}
          sourceLabel="Hayter, The House of Commons 1833 · public domain"
        >
          <UIDate date="1813" event="a vote about India" x={110} y={90} delay={6} />
        </EngravingScene>
      </Sequence>

      {/* S3 — hard reframe on the same plate + the Canton gag */}
      <Sequence
        from={Math.round(S2_END * FPS)}
        durationInFrames={Math.round((S3_END - S2_END) * FPS)}
      >
        <EngravingScene
          src="the-moment/engravings/commons_house_1833.jpg"
          kenBurns={{ scaleFrom: 1.6, scaleTo: 1.75, xFrom: 6, xTo: -4, yFrom: -6, yTo: -8 }}
          duotone={0.8}
          sourceLabel="Hayter, The House of Commons 1833 · public domain"
        >
          <UIStamp
            kind="custom"
            text="COULDN'T FIND CANTON"
            subtext="ON A MAP"
            x={960}
            y={780}
            rotation={-6}
            delay={20}
            backing
          />
        </EngravingScene>
      </Sequence>

      {/* S4 — the first pin, physically pulled */}
      <Sequence from={Math.round(S3_END * FPS)} durationInFrames={Math.round((TOTAL - S3_END) * FPS)}>
        <PinPulled />
      </Sequence>
    </AbsoluteFill>
  );
};

export const proto1813Duration = (fps: number) => Math.round(TOTAL * fps);
