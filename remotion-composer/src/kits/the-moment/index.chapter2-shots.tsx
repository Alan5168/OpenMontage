/**
 * index.chapter2-shots.ts — register one <Composition> per shot for
 * Chapter 2 "Three Hammers" (sec_03).
 */
import React from "react";
import { Composition, Sequence, Audio, staticFile, registerRoot } from "remotion";
import { CHAPTER2_SHOTS, CH2_FPS, CH2_AUDIO } from "./compose/Chapter2Shots";

const W = 1920;
const H = 1080;

const ShotRoot: React.FC<{ shotId: string }> = ({ shotId }) => {
  const shot = CHAPTER2_SHOTS.find((s) => s.id === shotId);
  if (!shot) return null;
  const { Component } = shot;
  const voStartFrame = Math.round(shot.voStart * CH2_FPS);
  const voFramesDur = Math.round((shot.voHoldSec ?? shot.durSec) * CH2_FPS);
  return (
    <>
      <Component />
      <Sequence from={0} durationInFrames={voFramesDur + CH2_FPS / 2}>
        <Audio src={staticFile(CH2_AUDIO)} startFrom={Math.max(0, voStartFrame - Math.round(CH2_FPS * 0.05))} />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => (
  <>
    {CHAPTER2_SHOTS.map((s) => (
      <Composition
        key={s.id}
        id={s.id}
        component={() => <ShotRoot shotId={s.id} />}
        durationInFrames={Math.max(15, Math.round(s.durSec * CH2_FPS))}
        fps={CH2_FPS}
        width={W}
        height={H}
      />
    ))}
  </>
);

registerRoot(RemotionRoot);
