/**
 * index.sentence-shots.ts — register one <Composition> per sentence for cold open v5
 *
 * `npx remotion render src/kits/the-moment/index.sentence-shots.ts S02 /tmp/S02.mp4`
 * or render ALL and stitch with ffmpeg.
 */
import React from "react";
import { Composition, Sequence, Audio, staticFile, registerRoot } from "remotion";
import { SENTENCE_SHOTS, FPS } from "./compose/SentenceShots";

const W = 1920;
const H = 1080;

// A single shot's root — renders its visual with the matching slice of the VO stem
const ShotRoot: React.FC<{ shotId: string }> = ({ shotId }) => {
  const shot = SENTENCE_SHOTS.find((s) => s.id === shotId);
  if (!shot) return null;
  const { Component } = shot;
  const framesDur = Math.round(shot.durSec * FPS);
  const voStartFrame = Math.round(shot.voStart * FPS);
  // 07-23: voHoldSec lets a shot's visual run longer than its real VO (a
  // held pause) without bleeding the NEXT shot's speech in early — defaults
  // to durSec so every other shot's audio timing is unchanged.
  const voFramesDur = Math.round((shot.voHoldSec ?? shot.durSec) * FPS);
  return (
    <>
      <Component />
      {/* Voiceover slice: offset into the CO stem so only this shot's VO plays */}
      <Sequence from={0} durationInFrames={voFramesDur + FPS / 2}>
        <Audio src={staticFile("the-moment/audio/sec_01_cold_open.wav")} startFrom={Math.max(0, voStartFrame - Math.round(FPS * 0.05))} />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => (
  <>
    {SENTENCE_SHOTS.map((s) => (
      <Composition
        key={s.id}
        id={s.id}
        component={() => <ShotRoot shotId={s.id} />}
        durationInFrames={Math.max(15, Math.round(s.durSec * FPS))}
        fps={FPS}
        width={W}
        height={H}
      />
    ))}
  </>
);

registerRoot(RemotionRoot);
