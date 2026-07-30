/**
 * Chapter7Shots.tsx — auto-generated from the ASR-verified >=3s scene
 * plan. Every visual is a real doubao-seedream crude-anime illustration.
 */
import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { EngravingKenBurns } from "./SentenceShots";

const FOLDER = "the-moment/ch7/";

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

export interface Chapter7ShotSpec {
  id: string; durSec: number; voStart: number; voEnd: number; Component: React.FC; voHoldSec?: number;
}

export const CHAPTER7_SHOTS: Chapter7ShotSpec[] = [
  { id:"CH7-01", durSec:4.83, voStart:0, voEnd:4.83, Component: single("ch7_01_westminster_night", "APRIL EIGHTEEN FORTY") },
  { id:"CH7-02", durSec:4.45, voStart:4.83, voEnd:9.28, Component: single("ch7_02_commons_chamber_tense", "THE WAR WAS ALREADY UNDERWAY") },
  { id:"CH7-03", durSec:7.14, voStart:4.83, voEnd:16.42, Component: single("ch7_03_fleet_already_sailing", "THE FLEET WAS ALREADY SAILING") },
  { id:"CH7-04", durSec:4.8, voStart:16.42, voEnd:21.22, Component: single("ch7_04_empty_voting_lobby", "PARLIAMENT NEVER VOTED ON THE WAR") },
  { id:"CH7-05", durSec:7.53, voStart:21.22, voEnd:28.75, Component: single("ch7_05_censure_accusation", "A CENSURE, NOT A WAR VOTE") },
  { id:"CH7-06", durSec:4.98, voStart:28.75, voEnd:33.73, Component: single("ch7_06_government_ship_seesaw", "IF IT PASSED, THE GOVERNMENT COULD FALL") },
  { id:"CH7-07", durSec:7.42, voStart:33.73, voEnd:41.15, Component: single("ch7_07_division_lobby_count", "THIRD NIGHT") },
  { id:"CH7-08", durSec:7.72, voStart:41.15, voEnd:48.87, Component: single("ch7_08_cracked_building_ships_sail", "THE POLICY SURVIVES BY NINE VOTES") },
  { id:"CH7-09", durSec:6.02, voStart:48.87, voEnd:54.88, Component: single("ch7_09_political_chess_standoff", "NOT CONSCIENCE VERSUS GREED") },
  { id:"CH7-10", durSec:3.42, voStart:54.88, voEnd:58.31, Component: single("ch7_10_cornered_minister", "THE GOVERNMENT WAS CORNERED") },
  { id:"CH7-11", durSec:11, voStart:58.31, voEnd:69.31, Component: twoBeat("ch7_11a_cabinet_doubt_map","THE CABINET HESITATED FOR MONTHS",165, "ch7_11b_paper_tips_scale","ONE PAPER TIPS THE SCALE",165) },
  { id:"CH7-12", durSec:11.45, voStart:69.31, voEnd:80.76, Component: twoBeat("ch7_12a_trembling_attacker","EVEN THE ATTACKERS TREMBLED",172, "ch7_12b_graham_warns_chamber","VICTORY COULD TOPPLE THE CABINET",172) },
  { id:"CH7-13", durSec:7.74, voStart:80.76, voEnd:88.5, Component: single("ch7_13_horror_at_success", "THE HORROR OF SUCCESS") },
  { id:"CH7-14", durSec:7.77, voStart:88.5, voEnd:96.27, Component: single("ch7_14_men_pushed_ledger", "NO NATION STRAINED AT THE LEASH") },
  { id:"CH7-15", durSec:5.1, voStart:96.27, voEnd:101.37, Component: single("ch7_15_engineered_motion_scroll", "THE OPPOSITION ENGINEERS THE MOTION") },
  { id:"CH7-16", durSec:12.56, voStart:101.37, voEnd:113.93, Component: twoBeat("ch7_16a_word_inserted_document","PAST CONDUCT — NOT THE PRESENT WAR",188, "ch7_16b_tory_ministers_past_files","ONLY PAST MINISTERS STAND ACCUSED",189) },
  { id:"CH7-17", durSec:5.13, voStart:113.93, voEnd:119.06, Component: single("ch7_17_opium_chest_ignored", "OPIUM DISAPPEARS FROM THE MOTION") },
  { id:"CH7-18", durSec:6.54, voStart:119.06, voEnd:125.6, Component: single("ch7_18_merchants_money_scale", "MORAL CLAUSES COST MERCHANT VOTES") },
  { id:"CH7-19", durSec:9.27, voStart:125.6, voEnd:134.87, Component: single("ch7_19_frustrated_mp_complains", "THE MOTION WAS NOT STRONG ENOUGH") },
  { id:"CH7-20", durSec:11.18, voStart:134.87, voEnd:146.05, Component: twoBeat("ch7_20a_gladstone_stands","REAL CONSCIENCE IN THE ROOM",168, "ch7_20b_sister_laudanum_home","GLADSTONE'S SISTER AND LAUDANUM",167) },
  { id:"CH7-21", durSec:8.98, voStart:146.05, voEnd:155.03, Component: single("ch7_21_gladstone_orator_speech", "GLADSTONE COULD NOT EXPLAIN THE WAR") },
  { id:"CH7-22", durSec:4.62, voStart:155.03, voEnd:159.65, Component: single("ch7_22_private_diary_candlelight", "GLADSTONE'S PRIVATE DOUBT") },
  { id:"CH7-23", durSec:8.7, voStart:159.65, voEnd:168.35, Component: single("ch7_23_sincere_yet_orchestrated", "SINCERE WORDS. ORCHESTRATED MOTION.") },
  { id:"CH7-24", durSec:4.16, voStart:168.35, voEnd:172.51, Component: single("ch7_24_canvassing_lobby", "GLADSTONE CANVASSES THE LOBBIES") },
  { id:"CH7-25", durSec:5.62, voStart:172.51, voEnd:178.13, Component: single("ch7_25_coin_shield_behind_benches", "THE COMPANY'S POLITICAL MACHINE") },
  { id:"CH7-26", durSec:8.53, voStart:178.13, voEnd:186.66, Component: single("ch7_26_palmerston_petition_jardine", "PALMERSTON'S TRUMP CARD: JARDINE") },
  { id:"CH7-27", durSec:8.26, voStart:186.66, voEnd:194.92, Component: single("ch7_27_jardine_hands_documents", "THE SURGEON-TURNED-TAIPAN RETURNS") },
  { id:"CH7-28", durSec:6.57, voStart:194.92, voEnd:201.48, Component: single("ch7_28_war_plan_table", "OVER WHAT AMOUNTED TO A WAR PLAN") },
  { id:"CH7-29", durSec:9.6, voStart:201.48, voEnd:211.08, Component: single("ch7_29_printing_press_profiteers", "THE PRESS NAMES THE PROFITEERS") },
  { id:"CH7-30", durSec:8.89, voStart:211.08, voEnd:219.97, Component: single("ch7_30_merchants_eye_treasure_ships", "THE OPIUM MERCHANTS WANTED WAR") },
  { id:"CH7-31", durSec:4.99, voStart:219.97, voEnd:224.96, Component: single("ch7_31_signing_and_holding_paper", "LOYALTY LETTERS BECOME CLAIMS") },
  { id:"CH7-32", durSec:4.21, voStart:224.96, voEnd:229.17, Component: single("ch7_32_paper_exchanged_for_gold", "PAPER ONLY A VICTORY COULD CASH") },
];

export const CH7_FPS = 30;
export const CH7_AUDIO = "the-moment/audio/sec_08_chapter_seven_nine_votes.wav";
