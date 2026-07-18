import React from "react";
import { Audio, Sequence, staticFile, useVideoConfig } from "remotion";

/**
 * Event SFX (icons / paper) — not motion UI SFX.
 * Cues from sound_scratch_timing_ep1_v1.md (EN absolute → section-relative).
 * Epidemic Partner API SFX (see run assets/sfx/ATTRIBUTION.md).
 */

const SFX = {
  cannon: "the-moment/audio/sfx/sfx_cannon_distant.mp3",
  paper: "the-moment/audio/sfx/sfx_paper.mp3",
  stamp: "the-moment/audio/sfx/sfx_stamp.mp3",
} as const;

type Hit = { at: number; src: keyof typeof SFX; volume: number; name: string };

/** section-relative hits */
const HITS: Record<string, Hit[]> = {
  CO: [{ at: 24.0, src: "cannon", volume: 0.32, name: "sfx-wrong-moment" }],
  CH6: [
    { at: 31.0, src: "paper", volume: 0.4, name: "sfx-one-signature" },
    { at: 55.0, src: "stamp", volume: 0.38, name: "sfx-at-gunpoint" },
    { at: 117.0, src: "cannon", volume: 0.42, name: "sfx-opened-fire" },
  ],
  CH7: [{ at: 37.0, src: "stamp", volume: 0.3, name: "sfx-nine-votes-board" }],
};

export const EventSfx: React.FC<{ label: string }> = ({ label }) => {
  const { fps } = useVideoConfig();
  const hits = HITS[label.toUpperCase()] ?? [];
  return (
    <>
      {hits.map((h) => {
        const from = Math.round(h.at * fps);
        const dur = Math.round(2.5 * fps);
        return (
          <Sequence key={h.name} from={from} durationInFrames={dur} name={h.name} layout="none">
            <Audio src={staticFile(SFX[h.src])} volume={h.volume} />
          </Sequence>
        );
      })}
    </>
  );
};
