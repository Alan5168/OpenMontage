/**
 * index.chapter6-shots.ts — register one <Composition> per shot.
 */
import React from "react";
import { Composition, Sequence, Audio, staticFile, registerRoot } from "remotion";
import { CHAPTER6_SHOTS, CH6_FPS, CH6_AUDIO } from "./compose/Chapter6Shots";

const W = 1920;
const H = 1080;

const ShotRoot: React.FC<{ shotId: string }> = ({ shotId }) => {
  const shot = CHAPTER6_SHOTS.find((s) => s.id === shotId);
  if (!shot) return null;
  const { Component } = shot;
  const voStartFrame = Math.round(shot.voStart * CH6_FPS);
  const voFramesDur = Math.round((shot.voHoldSec ?? shot.durSec) * CH6_FPS);
  return (
    <>
      <Component />
      <Sequence from={0} durationInFrames={voFramesDur + CH6_FPS / 2}>
        <Audio src={staticFile(CH6_AUDIO)} startFrom={Math.max(0, voStartFrame - Math.round(CH6_FPS * 0.05))} />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => (
  <>
    {CHAPTER6_SHOTS.map((s) => (
      <Composition
        key={s.id}
        id={s.id}
        component={() => <ShotRoot shotId={s.id} />}
        durationInFrames={Math.max(15, Math.round(s.durSec * CH6_FPS))}
        fps={CH6_FPS}
        width={W}
        height={H}
      />
    ))}
  </>
);

registerRoot(RemotionRoot);
