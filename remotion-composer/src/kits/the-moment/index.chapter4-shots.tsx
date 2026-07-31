/**
 * index.chapter4-shots.ts — register one <Composition> per shot.
 */
import React from "react";
import { Composition, Sequence, Audio, staticFile, registerRoot } from "remotion";
import { CHAPTER4_SHOTS, CH4_FPS, CH4_AUDIO } from "./compose/Chapter4Shots";

const W = 1920;
const H = 1080;

const ShotRoot: React.FC<{ shotId: string }> = ({ shotId }) => {
  const shot = CHAPTER4_SHOTS.find((s) => s.id === shotId);
  if (!shot) return null;
  const { Component } = shot;
  const voStartFrame = Math.round(shot.voStart * CH4_FPS);
  const voFramesDur = Math.round((shot.voHoldSec ?? shot.durSec) * CH4_FPS);
  return (
    <>
      <Component />
      <Sequence from={0} durationInFrames={voFramesDur + CH4_FPS / 2}>
        <Audio src={staticFile(CH4_AUDIO)} startFrom={Math.max(0, voStartFrame - Math.round(CH4_FPS * 0.05))} />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => (
  <>
    {CHAPTER4_SHOTS.map((s) => (
      <Composition
        key={s.id}
        id={s.id}
        component={() => <ShotRoot shotId={s.id} />}
        durationInFrames={Math.max(15, Math.round(s.durSec * CH4_FPS))}
        fps={CH4_FPS}
        width={W}
        height={H}
      />
    ))}
  </>
);

registerRoot(RemotionRoot);
