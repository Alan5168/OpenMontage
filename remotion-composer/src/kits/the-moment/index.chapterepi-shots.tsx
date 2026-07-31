/**
 * index.chapterepi-shots.ts — register one <Composition> per shot.
 */
import React from "react";
import { Composition, Sequence, Audio, staticFile, registerRoot } from "remotion";
import { CHAPTERepi_SHOTS, CHepi_FPS, CHepi_AUDIO } from "./compose/ChapterEpiShots";

const W = 1920;
const H = 1080;

const ShotRoot: React.FC<{ shotId: string }> = ({ shotId }) => {
  const shot = CHAPTERepi_SHOTS.find((s) => s.id === shotId);
  if (!shot) return null;
  const { Component } = shot;
  const voStartFrame = Math.round(shot.voStart * CHepi_FPS);
  const voFramesDur = Math.round((shot.voHoldSec ?? shot.durSec) * CHepi_FPS);
  return (
    <>
      <Component />
      <Sequence from={0} durationInFrames={voFramesDur + CHepi_FPS / 2}>
        <Audio src={staticFile(CHepi_AUDIO)} startFrom={Math.max(0, voStartFrame - Math.round(CHepi_FPS * 0.05))} />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => (
  <>
    {CHAPTERepi_SHOTS.map((s) => (
      <Composition
        key={s.id}
        id={s.id}
        component={() => <ShotRoot shotId={s.id} />}
        durationInFrames={Math.max(15, Math.round(s.durSec * CHepi_FPS))}
        fps={CHepi_FPS}
        width={W}
        height={H}
      />
    ))}
  </>
);

registerRoot(RemotionRoot);
