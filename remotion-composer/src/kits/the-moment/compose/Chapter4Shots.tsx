/**
 * Chapter4Shots.tsx — auto-generated from the ASR-verified >=3s scene
 * plan. Every visual is a real doubao-seedream crude-anime illustration.
 */
import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { EngravingKenBurns } from "./SentenceShots";

const FOLDER = "the-moment/ch4/";

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

export interface Chapter4ShotSpec {
  id: string; durSec: number; voStart: number; voEnd: number; Component: React.FC; voHoldSec?: number;
}

export const CHAPTER4_SHOTS: Chapter4ShotSpec[] = [
  { id:"CH4-01", durSec:6, voStart:0.192, voEnd:6.192, Component: single("ch4_01_runaway_wagon", "WHEN THE BRAKE IS GONE") },
  { id:"CH4-02", durSec:4.992, voStart:6.192, voEnd:11.184, Component: single("ch4_02_gap_in_wall", "NUMBER ONE: THE PRICE") },
  { id:"CH4-03", durSec:9.84, voStart:11.184, voEnd:21.024, Component: twoBeat("ch4_03a_veteran_trader","JARDINE MATHESON ENTERS THE GAP",148, "ch4_03b_many_trading_houses","DOZENS OF PRIVATE FIRMS FOLLOW",147) },
  { id:"CH4-04", durSec:6.524, voStart:21.024, voEnd:27.548, Component: single("ch4_04_crate_undercut", "MALWA OPIUM UNDERCUTS BENGAL") },
  { id:"CH4-05", durSec:12.916, voStart:27.548, voEnd:40.464, Component: twoBeat("ch4_05a_price_high","PRICE WAR",194, "ch4_05b_price_crash","PRICE WAR",193) },
  { id:"CH4-06", durSec:8.24, voStart:40.464, voEnd:48.704, Component: twoBeat("ch4_06a_mandarin_smoker","NUMBER TWO: THE VOLUME",124, "ch4_06b_dockworker_smoker","NUMBER TWO: THE VOLUME",123) },
  { id:"CH4-07", durSec:7.09, voStart:48.704, voEnd:55.794, Component: single("ch4_07_overflowing_dock", "22,000 CHESTS BECOME 40,000") },
  { id:"CH4-08", durSec:10.078, voStart:55.794, voEnd:65.872, Component: single("ch4_08_silver_drain", "NUMBER THREE: THE SILVER") },
  { id:"CH4-09", durSec:10.866, voStart:65.872, voEnd:76.738, Component: twoBeat("ch4_09a_farmer_copper","NUMBER FOUR: THE EXCHANGE RATE",163, "ch4_09b_tax_collector_silver","COPPER WAGES. SILVER TAXES.",163) },
  { id:"CH4-10", durSec:7.08, voStart:76.738, voEnd:83.818, Component: single("ch4_10_scale_tipping", "SILVER OUT. COPPER COST RISES.") },
  { id:"CH4-11", durSec:9.616, voStart:83.818, voEnd:93.434, Component: single("ch4_11_farmer_tax_scroll", "FROM A FARMER'S SIDE OF THE TABLE") },
  { id:"CH4-12", durSec:5.552, voStart:93.434, voEnd:98.986, Component: single("ch4_12_crumbling_treasury", "FIVE YEARS OF DEREGULATION") },
  { id:"CH4-13", durSec:7.064, voStart:98.986, voEnd:106.05, Component: single("ch4_13_tense_court_debate", "BEIJING RUNS THE SAME NUMBERS") },
];

export const CH4_FPS = 30;
export const CH4_AUDIO = "the-moment/audio/sec_05_chapter_four_the_flood.wav";
