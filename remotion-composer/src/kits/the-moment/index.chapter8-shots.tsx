/**
 * index.chapter8-shots.ts — register one <Composition> per shot.
 */
import React from "react";
import { Composition, Sequence, Audio, staticFile, registerRoot } from "remotion";
import { CHAPTER8_SHOTS, CH8_FPS, CH8_AUDIO } from "./compose/Chapter8Shots";

const W = 1920;
const H = 1080;

const ShotRoot: React.FC<{ shotId: string }> = ({ shotId }) => {
  const shot = CHAPTER8_SHOTS.find((s) => s.id === shotId);
  if (!shot) return null;
  const { Component } = shot;
  const voStartFrame = Math.round(shot.voStart * CH8_FPS);
  const voFramesDur = Math.round((shot.voHoldSec ?? shot.durSec) * CH8_FPS);
  return (
    <>
      <Component />
      <Sequence from={0} durationInFrames={voFramesDur + CH8_FPS / 2}>
        <Audio src={staticFile(CH8_AUDIO)} startFrom={Math.max(0, voStartFrame - Math.round(CH8_FPS * 0.05))} />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => (
  <>
    {CHAPTER8_SHOTS.map((s) => (
      <Composition
        key={s.id}
        id={s.id}
        component={() => <ShotRoot shotId={s.id} />}
        durationInFrames={Math.max(15, Math.round(s.durSec * CH8_FPS))}
        fps={CH8_FPS}
        width={W}
        height={H}
      />
    ))}
  </>
);

registerRoot(RemotionRoot);
