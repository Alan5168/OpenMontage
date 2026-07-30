/**
 * Chapter3Shots.tsx — auto-generated from the ASR-verified >=3s scene
 * plan. Every visual is a real doubao-seedream crude-anime illustration.
 */
import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { EngravingKenBurns } from "./SentenceShots";

const FOLDER = "the-moment/ch3/";

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

export interface Chapter3ShotSpec {
  id: string; durSec: number; voStart: number; voEnd: number; Component: React.FC; voHoldSec?: number;
}

export const CHAPTER3_SHOTS: Chapter3ShotSpec[] = [
  { id:"CH3-01", durSec:8.46, voStart:0, voEnd:8.46, Component: single("ch3_01_producer_regulator", "PRODUCER AND REGULATOR — FOR FORTY YEARS") },
  { id:"CH3-02", durSec:6.47, voStart:8.46, voEnd:14.93, Component: single("ch3_02_clean_hands", "THE COMPANY KEPT ITS HANDS CLEAN") },
  { id:"CH3-03", durSec:5.65, voStart:14.93, voEnd:20.58, Component: single("ch3_03_bengal_to_sea", "BENGAL OPIUM, AUCTIONED IN CALCUTTA") },
  { id:"CH3-04", durSec:6.79, voStart:20.58, voEnd:27.37, Component: single("ch3_04_license_threat", "BUT EVERY TRADER NEEDED A COMPANY LICENSE") },
  { id:"CH3-05", durSec:7.61, voStart:27.37, voEnd:34.98, Component: single("ch3_05_auction_high_prices", "HIGH PRICE. LOW VOLUME. MAXIMUM PROFIT.") },
  { id:"CH3-06", durSec:3.05, voStart:34.98, voEnd:38.03, Component: single("ch3_06_cartel_compliance", "A DRUG CARTEL, WITH A COMPLIANCE DEPARTMENT") },
  { id:"CH3-07", durSec:6.2, voStart:38.03, voEnd:44.23, Component: single("ch3_07_partial_brake", "A CYNICAL BRAKE") },
  { id:"CH3-08", durSec:17.2, voStart:44.23, voEnd:61.43, Component: twoBeat("ch3_08a_london_letter","DECEMBER 1833 — A PRIVATE WARNING",258, "ch3_08b_cracking_ledger","THE LEDGER WAS ALREADY CRACKING",258) },
  { id:"CH3-09", durSec:7.4, voStart:61.43, voEnd:68.83, Component: single("ch3_09_small_storm_cloud", "MISCHIEF WAS COMING") },
  { id:"CH3-10", durSec:11.7, voStart:68.83, voEnd:80.53, Component: single("ch3_10_committee_crumbles", "APRIL TWENTY-SECOND, EIGHTEEN THIRTY-FOUR") },
  { id:"CH3-11", durSec:10.17, voStart:80.53, voEnd:90.7, Component: single("ch3_11_napier_alone", "ONE MAN") },
  { id:"CH3-12", durSec:11.99, voStart:90.7, voEnd:102.69, Component: single("ch3_12_lit_fuse_instructions", "PALMERSTON'S INSTRUCTIONS — A LIT FUSE") },
  { id:"CH3-13", durSec:7.84, voStart:102.69, voEnd:110.53, Component: single("ch3_13_letter_refused", "CANTON READ HIM AS AN UNAUTHORIZED OFFICIAL") },
  { id:"CH3-14", durSec:8.94, voStart:110.53, voEnd:119.47, Component: twoBeat("ch3_14a_river_battle","FRIGATES UP THE PEARL RIVER",134, "ch3_14b_macao_grave","FEVER. RETREAT. DEATH AT MACAO.",134) },
  { id:"CH3-15", durSec:6.48, voStart:119.47, voEnd:125.95, Component: single("ch3_15_fizzled_firework", "THE PRESS CALLED IT THE NAPIER FIZZLE") },
  { id:"CH3-16", durSec:8.44, voStart:125.95, voEnd:134.39, Component: single("ch3_16_petition_warships", "THE MERCHANTS DEMAND WARSHIPS") },
  { id:"CH3-17", durSec:12.08, voStart:134.39, voEnd:146.47, Component: twoBeat("ch3_17a_young_surgeon","A FARMER'S SON FROM THE SCOTTISH LOWLANDS",181, "ch3_17b_merchant_kingpin","SHIP'S SURGEON TO OPIUM KINGPIN",181) },
  { id:"CH3-18", durSec:4.5, voStart:146.47, voEnd:150.97, Component: single("ch3_18_doctor_war_plan", "REMEMBER THE DOCTOR") },
  { id:"CH3-19", durSec:6.01, voStart:150.97, voEnd:156.98, Component: single("ch3_19_hourglass_standoff", "SIX MONTHS") },
  { id:"CH3-20", durSec:5.39, voStart:156.98, voEnd:162.37, Component: single("ch3_20_storm_arrives", "MISCHIEF — RIGHT ON SCHEDULE") },
];

export const CH3_FPS = 30;
export const CH3_AUDIO = "the-moment/audio/sec_04_chapter_three_the_brake.wav";
