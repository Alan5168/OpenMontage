/**
 * index.chapter1-shots.ts — register one <Composition> per shot for
 * Chapter 1 "The Last Monopoly" (sec_02).
 *
 * `npx remotion render src/kits/the-moment/index.chapter1-shots.tsx C02 /tmp/C02.mp4`
 */
import React from "react";
import { Composition, Sequence, Audio, staticFile, registerRoot } from "remotion";
import { CHAPTER1_SHOTS, CH1_FPS, CH1_AUDIO } from "./compose/Chapter1Shots";

const W = 1920;
const H = 1080;

const ShotRoot: React.FC<{ shotId: string }> = ({ shotId }) => {
  const shot = CHAPTER1_SHOTS.find((s) => s.id === shotId);
  if (!shot) return null;
  const { Component } = shot;
  const framesDur = Math.round(shot.durSec * CH1_FPS);
  const voStartFrame = Math.round(shot.voStart * CH1_FPS);
  const voFramesDur = Math.round((shot.voHoldSec ?? shot.durSec) * CH1_FPS);
  return (
    <>
      <Component />
      <Sequence from={0} durationInFrames={voFramesDur + CH1_FPS / 2}>
        <Audio src={staticFile(CH1_AUDIO)} startFrom={Math.max(0, voStartFrame - Math.round(CH1_FPS * 0.05))} />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => (
  <>
    {CHAPTER1_SHOTS.map((s) => (
      <Composition
        key={s.id}
        id={s.id}
        component={() => <ShotRoot shotId={s.id} />}
        durationInFrames={Math.max(15, Math.round(s.durSec * CH1_FPS))}
        fps={CH1_FPS}
        width={W}
        height={H}
      />
    ))}
  </>
);

registerRoot(RemotionRoot);
