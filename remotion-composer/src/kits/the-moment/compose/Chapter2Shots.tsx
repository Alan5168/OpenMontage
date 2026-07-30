/**
 * Chapter2Shots.tsx — "Three Hammers" (sec_03, ~121.2s VO)
 * Built 07-24 following the same from-the-start method as Chapter 1:
 * ASR-derived word timestamps, every shot >=3s, every visual a real
 * doubao-seedream crude-anime illustration (no baked-in text).
 */
import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { TM } from "../theme";
import { EngravingKenBurns } from "./SentenceShots";

const CH2 = "the-moment/ch2/";

const single = (img: string, caption: string) => () => (
  <EngravingKenBurns src={`${CH2}${img}.png`} startScale={1.0} endScale={1.14} sepia={0} dim={0.12} caption={caption} />
);

const twoBeat = (imgA: string, capA: string, framesA: number, imgB: string, capB: string, framesB: number) => () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={framesA}>
      <EngravingKenBurns src={`${CH2}${imgA}.png`} startScale={1.0} endScale={1.12} sepia={0} dim={0.12} caption={capA} />
    </Sequence>
    <Sequence from={framesA} durationInFrames={framesB}>
      <EngravingKenBurns src={`${CH2}${imgB}.png`} startScale={1.0} endScale={1.12} sepia={0} dim={0.12} caption={capB} />
    </Sequence>
  </AbsoluteFill>
);

export interface Chapter2ShotSpec {
  id: string; durSec: number; voStart: number; voEnd: number; Component: React.FC; voHoldSec?: number;
}

export const CHAPTER2_SHOTS: Chapter2ShotSpec[] = [
  { id:"C2-01", durSec:3.23, voStart:0.00, voEnd:3.23, Component: single("ch2_01_three_hammers", "THREE HAMMERS FALL") },
  { id:"C2-02", durSec:3.30, voStart:3.23, voEnd:6.53, Component: single("ch2_02_two_hammers_land", "THE FIRST TWO LAND TOGETHER") },
  { id:"C2-03", durSec:8.86, voStart:6.53, voEnd:15.39, Component: single("ch2_03_rotten_boroughs_bloc", "THE COMPANY'S BLOC IN PARLIAMENT") },
  { id:"C2-04", durSec:5.75, voStart:15.39, voEnd:21.14, Component: single("ch2_04_reform_act_factory_towns", "THE REFORM ACT, 1832") },
  { id:"C2-05", durSec:10.76, voStart:21.14, voEnd:31.90, Component: twoBeat("ch2_05a_calcutta_houses_collapse","CALCUTTA COLLAPSES",195, "ch2_05b_votes_credit_broken","THE CREDIT WAS BROKEN",128) },
  { id:"C2-06", durSec:3.16, voStart:31.90, voEnd:35.06, Component: single("ch2_06_third_hammer_argument", "HAMMER THREE") },
  { id:"C2-07", durSec:11.42, voStart:35.06, voEnd:46.48, Component: single("ch2_07_macaulay_stands_alone", "NOT ONE VOICE DEFENDED IT") },
  { id:"C2-08", durSec:3.67, voStart:46.48, voEnd:50.15, Component: single("ch2_08_whigs_tories_silent", "NO WHIG. NO TORY.") },
  { id:"C2-09", durSec:4.63, voStart:50.15, voEnd:54.78, Component: single("ch2_09_monopoly_ends_unmourned", "ENDED WITHOUT A DEFENDER") },
  { id:"C2-10", durSec:9.39, voStart:54.78, voEnd:64.17, Component: twoBeat("ch2_10a_reveal_curtain","THE REAL REVEAL",105, "ch2_10b_company_fights_for_empire","IT FOUGHT FOR THE EMPIRE",177) },
  { id:"C2-11", durSec:5.82, voStart:64.17, voEnd:69.99, Component: single("ch2_11_lobbying_wins", "LOBBYING FOR INDIA — AND WINNING") },
  { id:"C2-12", durSec:5.76, voStart:69.99, voEnd:75.75, Component: single("ch2_12_shareholders_guaranteed_dividend", "10.5% GUARANTEED, PAID BY INDIA") },
  { id:"C2-13", durSec:3.95, voStart:75.75, voEnd:79.70, Component: single("ch2_13_corporate_state_survives", "A CORPORATE STATE SURVIVED") },
  { id:"C2-14", durSec:5.71, voStart:79.70, voEnd:85.41, Component: single("ch2_14_forgotten_clause", "THE FORGOTTEN CLAUSE") },
  { id:"C2-15", durSec:10.88, voStart:85.41, voEnd:96.29, Component: twoBeat("ch2_15a_fallback_proposal","THE FALLBACK PROPOSAL",163, "ch2_15b_merchants_flood_canton","CANTON'S MERCHANT FLOOD",163) },
  { id:"C2-16", durSec:3.91, voStart:96.29, voEnd:100.20, Component: single("ch2_16_parliament_rejects_clause", "REJECTED. UNNECESSARY.") },
  { id:"C2-17", durSec:5.28, voStart:100.20, voEnd:105.48, Component: single("ch2_17_ghost_clause", "THE GHOST CLAUSE") },
  { id:"C2-18", durSec:9.58, voStart:105.48, voEnd:115.06, Component: twoBeat("ch2_18a_twenty_years_pass","TWENTY YEARS LATER",129, "ch2_18b_china_monopoly_dies","THE CHINA MONOPOLY DIES",158) },
  { id:"C2-19", durSec:4.20, voStart:115.06, voEnd:119.26, Component: single("ch2_19_flag_lowered_canton", "APRIL 22, 1834") },
];

export const CH2_FPS = 30;
export const CH2_AUDIO = "the-moment/audio/sec_03_chapter_two_three_hammers.wav";
