/**
 * Chapter5Shots.tsx — auto-generated from the ASR-verified >=3s scene
 * plan. Every visual is a real doubao-seedream crude-anime illustration.
 */
import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { EngravingKenBurns } from "./SentenceShots";

const FOLDER = "the-moment/ch5/";

const single = (img: string, caption: string) => () => (
  <EngravingKenBurns src={`${FOLDER}${img}.png`} startScale={1.0} endScale={1.14} sepia={0} dim={0.12} caption={caption} />
);

const twoBeat = (imgA: string, capA: string, framesA: number, imgB: string, capB: string, framesB: number) => () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={framesA}>
      <EngravingKenBurns src={`${FOLDER}${imgA}.png`} startScale={1.0} endScale={1.12} sepia={0} dim={0.12} caption={capA} />
    </Sequence>
    <Sequence from={framesA} durationInFrames={framesB}>
      <EngravingKenBurns src={`${FOLDER}${imgB}.png`} startScale={1.0} endScale={1.12} sepia={0} dim={0.12} caption={capB} />
    </Sequence>
  </AbsoluteFill>
);

const threeBeat = (imgA: string, capA: string, framesA: number, imgB: string, capB: string, framesB: number, imgC: string, capC: string, framesC: number) => () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={framesA}>
      <EngravingKenBurns src={`${FOLDER}${imgA}.png`} startScale={1.0} endScale={1.1} sepia={0} dim={0.12} caption={capA} />
    </Sequence>
    <Sequence from={framesA} durationInFrames={framesB}>
      <EngravingKenBurns src={`${FOLDER}${imgB}.png`} startScale={1.0} endScale={1.1} sepia={0} dim={0.12} caption={capB} />
    </Sequence>
    <Sequence from={framesA + framesB} durationInFrames={framesC}>
      <EngravingKenBurns src={`${FOLDER}${imgC}.png`} startScale={1.0} endScale={1.1} sepia={0} dim={0.12} caption={capC} />
    </Sequence>
  </AbsoluteFill>
);

export interface Chapter5ShotSpec {
  id: string; durSec: number; voStart: number; voEnd: number; Component: React.FC; voHoldSec?: number;
}

export const CHAPTER5_SHOTS: Chapter5ShotSpec[] = [
  { id:"CH5-01", durSec:5.192, voStart:0.192, voEnd:5.384, Component: single("ch5_01_parliament_brake_torn", "LONDON TORE ITS BRAKE OUT") },
  { id:"CH5-02", durSec:3.448, voStart:5.384, voEnd:8.832, Component: single("ch5_02_beijing_council_debate", "BEIJING TRIED TO BUILD ONE") },
  { id:"CH5-03", durSec:9.408, voStart:8.832, voEnd:18.24, Component: single("ch5_03_ignored_opium_edict", "A CENTURY OF FAILED BANS") },
  { id:"CH5-04", durSec:4.208, voStart:18.24, voEnd:22.448, Component: single("ch5_04_silver_desk_memorials", "TWO MEMORIALS. TWO ANSWERS.") },
  { id:"CH5-05", durSec:5.144, voStart:22.448, voEnd:27.592, Component: single("ch5_05_xu_naiji_portrait", "1836 — XU NAIJI, THE PRAGMATIST") },
  { id:"CH5-06", durSec:6.66, voStart:27.592, voEnd:34.252, Component: single("ch5_06_xu_naiji_legalize_stamp", "LEGALIZE IT. TAX IT. KEEP THE SILVER.") },
  { id:"CH5-07", durSec:5.02, voStart:34.252, voEnd:39.272, Component: single("ch5_07_qing_court_weighing_scale", "THE COURT WEIGHS LEGALIZATION") },
  { id:"CH5-08", durSec:6.792, voStart:39.272, voEnd:46.064, Component: single("ch5_08_huang_juezi_portrait", "1838 — HUANG JUEZI, THE HARDLINER") },
  { id:"CH5-09", durSec:6.64, voStart:46.064, voEnd:52.704, Component: single("ch5_09_hourglass_execution_threat", "ONE YEAR TO QUIT — THEN DEATH") },
  { id:"CH5-10", durSec:6.56, voStart:52.704, voEnd:59.264, Component: single("ch5_10_emperor_provincial_replies", "TWENTY-NINE PROVINCIAL REPLIES") },
  { id:"CH5-11", durSec:4.826, voStart:59.264, voEnd:64.09, Component: single("ch5_11_minority_death_penalty_scrolls", "ONLY EIGHT CHOSE DEATH") },
  { id:"CH5-12", durSec:9.91, voStart:64.09, voEnd:74, Component: single("ch5_12_lin_zexu_clean_hands_portrait", "ONE OF THE EIGHT: LIN ZEXU") },
  { id:"CH5-13", durSec:11.078, voStart:74, voEnd:85.078, Component: single("ch5_13_weakened_army_empty_treasury", "NO SOLDIERS. NO SILVER.") },
  { id:"CH5-14", durSec:6.956, voStart:85.078, voEnd:92.034, Component: single("ch5_14_daoguang_emperor_reading", "AN EMPIRE THAT CAN'T PAY ITS OWN") },
  { id:"CH5-15", durSec:4.888, voStart:92.034, voEnd:96.922, Component: single("ch5_15_xu_naiji_demoted", "THE LEGALIZER IS DEMOTED") },
  { id:"CH5-16", durSec:4.08, voStart:96.922, voEnd:101.002, Component: single("ch5_16_lin_zexu_commissioner_seal", "LIN RECEIVES THE IMPERIAL SEAL") },
  { id:"CH5-17", durSec:3.856, voStart:101.002, voEnd:104.858, Component: single("ch5_17_lin_arrives_canton_harbor", "MARCH EIGHTEEN THIRTY-NINE") },
  { id:"CH5-18", durSec:10.314, voStart:104.858, voEnd:115.172, Component: single("ch5_18_jardine_club_unfazed", "THE IRON-HEADED OLD RAT") },
  { id:"CH5-19", durSec:6.962, voStart:115.172, voEnd:122.134, Component: single("ch5_19_jardine_ship_departs", "HE'D SAILED FOR LONDON IN JANUARY") },
  { id:"CH5-20", durSec:5.66, voStart:122.134, voEnd:127.794, Component: single("ch5_20_lin_reverse_lever", "LIN PULLS THE REVERSE LEVER") },
  { id:"CH5-21", durSec:7.787, voStart:127.794, voEnd:135.581, Component: single("ch5_21_blockade_foreign_factories", "THE FACTORIES ARE BLOCKADED") },
  { id:"CH5-22", durSec:4.661, voStart:135.581, voEnd:140.242, Component: single("ch5_22_humen_opium_destruction", "20,000 CHESTS DESTROYED AT HUMEN") },
  { id:"CH5-23", durSec:5.531, voStart:140.242, voEnd:145.773, Component: single("ch5_23_largest_seizure_scale", "THE LARGEST DRUG SEIZURE IN HISTORY") },
  { id:"CH5-24", durSec:6.562, voStart:145.773, voEnd:152.335, Component: single("ch5_24_lin_letter_queen_victoria", "ONE MORE DETAIL HISTORY KEEPS FORGETTING") },
  { id:"CH5-25", durSec:6.325, voStart:152.335, voEnd:158.66, Component: single("ch5_25_forbidden_home_sold_abroad", "FORBIDDEN AT HOME. SOLD ABROAD.") },
  { id:"CH5-26", durSec:6.974, voStart:158.66, voEnd:165.634, Component: single("ch5_26_unread_royal_letter", "THE LETTER VICTORIA NEVER READ") },
  { id:"CH5-27", durSec:7.864, voStart:165.634, voEnd:173.498, Component: single("ch5_27_printing_press_papers", "THE LETTER BECOMES A CURIOSITY") },
  { id:"CH5-28", durSec:8.733, voStart:173.498, voEnd:182.231, Component: single("ch5_28_beijing_brake_completed", "LAW ENFORCEMENT, ON BEIJING'S TERMS") },
  { id:"CH5-29", durSec:3.147, voStart:182.231, voEnd:185.378, Component: single("ch5_29_looming_clock", "THE PROBLEM WAS THE CLOCK") },
  { id:"CH5-30", durSec:6.64, voStart:185.378, voEnd:192.018, Component: single("ch5_30_british_signature_debt", "ONE SIGNATURE TURNS DRUGS INTO DEBT") },
];

export const CH5_FPS = 30;
export const CH5_AUDIO = "the-moment/audio/sec_06_chapter_five_beijing_hits_the_brakes.wav";
