/**
 * Chapter8Shots.tsx — auto-generated from the ASR-verified >=3s scene
 * plan. Every visual is a real doubao-seedream crude-anime illustration.
 */
import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { EngravingKenBurns } from "./SentenceShots";

const FOLDER = "the-moment/ch8/";

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

export interface Chapter8ShotSpec {
  id: string; durSec: number; voStart: number; voEnd: number; Component: React.FC; voHoldSec?: number;
}

export const CHAPTER8_SHOTS: Chapter8ShotSpec[] = [
  { id:"CH8-01", durSec:6.032, voStart:0, voEnd:6.032, Component: single("ch8_01_treaty_signing", "TREATY OF NANKING — FIVE PORTS OPEN") },
  { id:"CH8-02", durSec:11.84, voStart:6.032, voEnd:17.872, Component: twoBeat("ch8_02a_indemnity_chests","21,000,000 SILVER DOLLARS IN INDEMNITY",178, "ch8_02b_ledger_stamped_paid","21,000,000 SILVER DOLLARS IN INDEMNITY",177) },
  { id:"CH8-03", durSec:5.664, voStart:17.872, voEnd:23.536, Component: single("ch8_03_winners_scroll", "WHO ACTUALLY WON") },
  { id:"CH8-04", durSec:12.72, voStart:23.536, voEnd:36.256, Component: twoBeat("ch8_04a_proposal_handoff","JARDINE MATHESON — FIRST AND BIGGEST",191, "ch8_04b_hong_kong_headquarters","HONG KONG BECOMES HEADQUARTERS",191) },
  { id:"CH8-05", durSec:9.328, voStart:36.256, voEnd:45.584, Component: single("ch8_05_young_jardine_departs", "WILLIAM JARDINE — FARM BOY TO TRADER") },
  { id:"CH8-06", durSec:10.382, voStart:45.584, voEnd:55.966, Component: twoBeat("ch8_06a_parliament_chamber","MP FOR ASHBURTON",156, "ch8_06b_deathbed_gravestone","DEAD WITHIN TWO MONTHS",155) },
  { id:"CH8-07", durSec:6.402, voStart:55.966, voEnd:62.368, Component: single("ch8_07_fortune_scattered", "NEVER MARRIED — FORTUNE SPLIT AMONG NEPHEWS") },
  { id:"CH8-08", durSec:12.002, voStart:62.368, voEnd:74.37, Component: twoBeat("ch8_08a_isle_of_lewis_map","JARDINE'S MONEY REBUILDS LEWIS",180, "ch8_08b_enduring_trading_house","THE TRADING HOUSE ENDURES",180) },
  { id:"CH8-09", durSec:12.096, voStart:74.37, voEnd:86.466, Component: twoBeat("ch8_09a_canton_hong_closing","EWO — HAPPY HARMONY",182, "ch8_09b_signboard_rehung","THE CANTON SIGNBOARD ENDURES",181) },
  { id:"CH8-10", durSec:6.062, voStart:86.466, voEnd:92.528, Component: single("ch8_10_fake_winner_unmasked", "MYTH-CHECK: MOST 'WINNERS' LISTS ARE WRONG") },
  { id:"CH8-11", durSec:7.362, voStart:92.528, voEnd:99.89, Component: twoBeat("ch8_11a_bank_under_construction","HSBC, 1865",110, "ch8_11b_shanghai_house_construction","SWIRE, SHANGHAI — 1866",111) },
  { id:"CH8-12", durSec:6.672, voStart:99.89, voEnd:106.562, Component: single("ch8_12_grandfather_grandchild_contrast", "NEITHER EXISTED WHEN THE WAR WAS FOUGHT") },
  { id:"CH8-13", durSec:12.054, voStart:106.562, voEnd:118.616, Component: twoBeat("ch8_13a_dent_company_thriving","DENT & CO",181, "ch8_13b_bank_collapse_crumbling","DENT & CO",181) },
  { id:"CH8-14", durSec:4.194, voStart:118.616, voEnd:122.81, Component: single("ch8_14_wreath_on_grave", "VICTORY BOUGHT A GENERATION, NOT IMMORTALITY") },
  { id:"CH8-15", durSec:9.96, voStart:122.81, voEnd:132.77, Component: twoBeat("ch8_15a_shipyard_building_gunboat","THE NEMESIS — THE WAR'S REAL STAR",150, "ch8_15b_nemesis_attacking_junks","THE NEMESIS ATTACKS THE JUNKS",149) },
  { id:"CH8-16", durSec:6.32, voStart:132.77, voEnd:139.09, Component: single("ch8_16_treasury_silver_and_tea", "THE TREASURY — THE INVISIBLE WINNER") },
  { id:"CH8-17", durSec:8.16, voStart:139.09, voEnd:147.25, Component: single("ch8_17_commons_tea_scale", "TEA DUTIES PAID MILLIONS") },
  { id:"CH8-18", durSec:11.404, voStart:147.25, voEnd:158.654, Component: twoBeat("ch8_18a_mill_owners_petition","MANCHESTER'S 20-YEAR LOBBY FOR NEW CUSTOMERS",171, "ch8_18b_empty_marketplace","MANCHESTER'S CUSTOMERS NEVER ARRIVE",171) },
  { id:"CH8-19", durSec:13.028, voStart:158.654, voEnd:171.682, Component: twoBeat("ch8_19a_chinese_village_weavers","THE CUSTOMERS NEVER CAME",196, "ch8_19b_mirage_market_fading","THE CUSTOMERS NEVER CAME",195) },
  { id:"CH8-20", durSec:10.632, voStart:171.682, voEnd:182.314, Component: single("ch8_20_empty_treasure_chest", "THE EAST INDIA COMPANY'S OWN TAKE: ZERO") },
  { id:"CH8-21", durSec:6.487, voStart:182.314, voEnd:188.801, Component: single("ch8_21_locked_out_of_port", "BANNED FROM THE CHINA TRADE SINCE 1834") },
  { id:"CH8-22", durSec:8.873, voStart:188.801, voEnd:197.674, Component: single("ch8_22_sepoy_column_marching", "INDIAN SOLDIERS. INDIAN MONEY.") },
  { id:"CH8-23", durSec:10.976, voStart:197.674, voEnd:208.65, Component: single("ch8_23_poppy_fields_and_scale", "OPIUM'S GROWING SHARE OF INDIA'S REVENUE") },
  { id:"CH8-24", durSec:7.64, voStart:208.65, voEnd:216.29, Component: single("ch8_24_charter_from_crowned_hand", "A CHARTER THE CROWN COULD REVOKE") },
  { id:"CH8-25", durSec:11.304, voStart:216.29, voEnd:227.594, Component: twoBeat("ch8_25a_sepoy_uprising","1857 — INDIA RISES",170, "ch8_25b_shareholders_boardroom_map","WHO SHOULD RULE INDIA?",169) },
  { id:"CH8-26", durSec:5.28, voStart:227.594, voEnd:232.874, Component: single("ch8_26_crown_descends_on_map", "THE CROWN TAKES INDIA") },
  { id:"CH8-27", durSec:5.08, voStart:232.874, voEnd:237.954, Component: single("ch8_27_ledger_closes_final", "274 YEARS LATER — THE LEDGER CLOSES") },
];

export const CH8_FPS = 30;
export const CH8_AUDIO = "the-moment/audio/sec_09_chapter_eight_the_winners_list.wav";
