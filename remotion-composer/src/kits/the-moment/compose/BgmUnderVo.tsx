import React from "react";
import { Audio, staticFile } from "remotion";

/**
 * Ep1 BGM beds under VO — Music Plan v1 / cue_sheet_ep1_v1.
 * solemn/tense source: Epidemic Sound (Creator). resolve source: MiniMax
 * music_generation (2026-07-19, GM listen-picked). Duck volumes are scratch
 * defaults; final loudnorm at mix stage.
 *
 * bed_solemn_01  = Glacier (Anna Dager)
 * bed_tense_01   = Dear Mr. Murderer (Anna Dager) — also main alternate
 * bed_resolve_01 = MiniMax resolve_minimal_01 (GM pick); _alt = resolve_minimal_03
 */

export const BGM_FILES = {
  solemn: "the-moment/audio/music/bed_solemn_01.mp3",
  tense: "the-moment/audio/music/bed_tense_01.mp3",
  resolve: "the-moment/audio/music/bed_resolve_01.mp3",
} as const;

export type BgmKind = keyof typeof BGM_FILES;

/** section label → bed (cue_sheet_ep1_v1) */
export const bgmForLabel = (label: string): BgmKind => {
  const L = label.toUpperCase();
  if (L === "CH3" || L === "CH6") return "tense";
  if (L === "EP") return "resolve";
  return "solemn";
};

/** linear gain under VO */
export const bgmVolumeForLabel = (label: string): number => {
  const L = label.toUpperCase();
  if (L === "EP") return 0.08;
  if (L === "CH3" || L === "CH6") return 0.14;
  return 0.12;
};

export const BgmUnderVo: React.FC<{
  kind?: BgmKind;
  label?: string;
  volume?: number;
}> = ({ kind, label, volume }) => {
  const k = kind ?? (label ? bgmForLabel(label) : "solemn");
  const vol = volume ?? (label ? bgmVolumeForLabel(label) : 0.12);
  return (
    <Audio
      src={staticFile(BGM_FILES[k])}
      volume={vol}
      loop
      name={`bgm-${k}`}
    />
  );
};
