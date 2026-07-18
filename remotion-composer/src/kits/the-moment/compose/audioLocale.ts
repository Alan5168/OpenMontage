/**
 * EN/ZH VO stem paths under public/the-moment/audio/
 * EN: flat sec_*.wav (legacy)
 * ZH: zh/sec_*.wav (lengdan_xiongzhang, 2026-07-18)
 */

export type VoLocale = "en" | "zh";

/** Remotion section labels used by Cp1Section / cue sheet */
export type SectionLabel =
  | "CO"
  | "CH1"
  | "CH2"
  | "CH3"
  | "CH4"
  | "CH5"
  | "CH6"
  | "CH7"
  | "CH8"
  | "EP";

const EN_FILES: Record<SectionLabel, string> = {
  CO: "the-moment/audio/sec_01_cold_open.wav",
  CH1: "the-moment/audio/sec_02_chapter_one_the_last_monopoly.wav",
  CH2: "the-moment/audio/sec_03_chapter_two_three_hammers.wav",
  CH3: "the-moment/audio/sec_04_chapter_three_the_brake.wav",
  CH4: "the-moment/audio/sec_05_chapter_four_the_flood.wav",
  CH5: "the-moment/audio/sec_06_chapter_five_beijing_hits_the_brakes.wav",
  CH6: "the-moment/audio/sec_07_chapter_six_the_paper.wav",
  CH7: "the-moment/audio/sec_08_chapter_seven_nine_votes.wav",
  CH8: "the-moment/audio/sec_09_chapter_eight_the_winners_list.wav",
  EP: "the-moment/audio/sec_10_epilogue_the_wire.wav",
};

const ZH_FILES: Record<SectionLabel, string> = {
  CO: "the-moment/audio/zh/sec_01_cold_open.wav",
  CH1: "the-moment/audio/zh/sec_02_chapter_one_the_last_monopoly.wav",
  CH2: "the-moment/audio/zh/sec_03_chapter_two_three_hammers.wav",
  CH3: "the-moment/audio/zh/sec_04_chapter_three_the_brake.wav",
  CH4: "the-moment/audio/zh/sec_05_chapter_four_the_flood.wav",
  CH5: "the-moment/audio/zh/sec_06_chapter_five_beijing_hits_the_brakes.wav",
  CH6: "the-moment/audio/zh/sec_07_chapter_six_the_paper.wav",
  CH7: "the-moment/audio/zh/sec_08_chapter_seven_nine_votes.wav",
  CH8: "the-moment/audio/zh/sec_09_chapter_eight_the_winners_list.wav",
  EP: "the-moment/audio/zh/sec_10_epilogue_the_wire.wav",
};

/** measured section_audio_s from manifests */
export const SECTION_SECONDS: Record<VoLocale, Record<SectionLabel, number>> = {
  en: {
    CO: 83.184,
    CH1: 104.775,
    CH2: 121.196,
    CH3: 165.014,
    CH4: 108.137,
    CH5: 193.891,
    CH6: 138.222,
    CH7: 231.634,
    CH8: 240.173,
    EP: 98.856,
  },
  zh: {
    CO: 98.802,
    CH1: 122.982,
    CH2: 127.977,
    CH3: 191.147,
    CH4: 119.289,
    CH5: 215.601,
    CH6: 144.457,
    CH7: 264.061,
    CH8: 285.034,
    EP: 116.227,
  },
};

export const voSrc = (label: string, locale: VoLocale = "en"): string => {
  const L = label.toUpperCase() as SectionLabel;
  const table = locale === "zh" ? ZH_FILES : EN_FILES;
  if (!(L in table)) {
    throw new Error(`Unknown section label for VO: ${label}`);
  }
  return table[L];
};

export const SECTION_ORDER: SectionLabel[] = [
  "CO",
  "CH1",
  "CH2",
  "CH3",
  "CH4",
  "CH5",
  "CH6",
  "CH7",
  "CH8",
  "EP",
];
