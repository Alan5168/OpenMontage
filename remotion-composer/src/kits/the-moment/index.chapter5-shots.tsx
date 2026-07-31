/**
 * index.chapter5-shots.ts — register one <Composition> per shot.
 */
import React from "react";
import { Composition, Sequence, Audio, staticFile, registerRoot } from "remotion";
import { CHAPTER5_SHOTS, CH5_FPS, CH5_AUDIO } from "./compose/Chapter5Shots";

const W = 1920;
const H = 1080;

const ShotRoot: React.FC<{ shotId: string }> = ({ shotId }) => {
  const shot = CHAPTER5_SHOTS.find((s) => s.id === shotId);
  if (!shot) return null;
  const { Component } = shot;
  const voStartFrame = Math.round(shot.voStart * CH5_FPS);
  const voFramesDur = Math.round((shot.voHoldSec ?? shot.durSec) * CH5_FPS);
  return (
    <>
      <Component />
      <Sequence from={0} durationInFrames={voFramesDur + CH5_FPS / 2}>
        <Audio src={staticFile(CH5_AUDIO)} startFrom={Math.max(0, voStartFrame - Math.round(CH5_FPS * 0.05))} />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => (
  <>
    {CHAPTER5_SHOTS.map((s) => (
      <Composition
        key={s.id}
        id={s.id}
        component={() => <ShotRoot shotId={s.id} />}
        durationInFrames={Math.max(15, Math.round(s.durSec * CH5_FPS))}
        fps={CH5_FPS}
        width={W}
        height={H}
      />
    ))}
  </>
);

registerRoot(RemotionRoot);
