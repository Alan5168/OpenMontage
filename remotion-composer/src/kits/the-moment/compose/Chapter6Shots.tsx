/**
 * Chapter6Shots.tsx — auto-generated from the ASR-verified >=3s scene
 * plan. Every visual is a real doubao-seedream crude-anime illustration.
 */
import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { EngravingKenBurns } from "./SentenceShots";

const FOLDER = "the-moment/ch6/";

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

export interface Chapter6ShotSpec {
  id: string; durSec: number; voStart: number; voEnd: number; Component: React.FC; voHoldSec?: number;
}

export const CHAPTER6_SHOTS: Chapter6ShotSpec[] = [
  { id:"CH6-01", durSec:7.77, voStart:0, voEnd:7.77, Component: single("ch6_01_elliot_besieged", "CHARLES ELLIOT — BESIEGED IN CANTON") },
  { id:"CH6-02", durSec:4.44, voStart:7.77, voEnd:12.21, Component: single("ch6_02_surrender_opium", "SURRENDER EVERY CHEST") },
  { id:"CH6-03", durSec:9.68, voStart:12.21, voEnd:21.89, Component: single("ch6_03_unauthorized_promise", "LONDON WILL REPAY EVERY CHEST") },
  { id:"CH6-04", durSec:12.88, voStart:21.89, voEnd:34.77, Component: twoBeat("ch6_04a_seized_contraband","CONTRABAND BECOMES A CLAIM",193, "ch6_04b_treasury_claim","A PRIVATE PROMISE TO THE TREASURY",193) },
  { id:"CH6-05", durSec:6.89, voStart:34.77, voEnd:41.66, Component: single("ch6_05_treasury_cant_afford", "A £2 MILLION PROMISE LONDON NEVER MADE") },
  { id:"CH6-06", durSec:4.87, voStart:41.66, voEnd:46.53, Component: single("ch6_06_cabinet_fear", "THE CABINET CANNOT REPUDIATE IT") },
  { id:"CH6-07", durSec:10.54, voStart:46.53, voEnd:57.07, Component: single("ch6_07_gunpoint_collection", "COLLECT THE DEBT — AT GUNPOINT") },
  { id:"CH6-08", durSec:8.13, voStart:57.07, voEnd:65.2, Component: single("ch6_08_law_fuse_war", "HOW AN UNDEFENDED LAW BECOMES WAR") },
  { id:"CH6-09", durSec:9.15, voStart:65.2, voEnd:74.35, Component: single("ch6_09_four_steps_institution_falls", "FOUR STEPS DISMANTLED THE BRAKE") },
  { id:"CH6-10", durSec:3.24, voStart:74.35, voEnd:77.59, Component: single("ch6_10_rejected_clause", "THE CLAUSE THAT MIGHT HAVE GOVERNED") },
  { id:"CH6-11", durSec:6.11, voStart:77.59, voEnd:83.7, Component: single("ch6_11_opium_flood_war_debt", "CHEAP OPIUM. PUBLIC DEBT. WAR.") },
  { id:"CH6-12", durSec:9.81, voStart:83.7, voEnd:93.51, Component: single("ch6_12_two_shores_arrogance", "ARROGANCE ON BOTH SHORES") },
  { id:"CH6-13", durSec:10.32, voStart:93.51, voEnd:103.83, Component: single("ch6_13_westminster_silent_switch", "THE SWITCH PASSED SILENTLY") },
  { id:"CH6-14", durSec:12.19, voStart:103.83, voEnd:116.02, Component: twoBeat("ch6_14a_machine_eating_itself","THE MACHINE EATS ITSELF",183, "ch6_14b_captain_ready_to_sign","A CAPTAIN READY TO SIGN",183) },
  { id:"CH6-15", durSec:11.58, voStart:116.02, voEnd:127.6, Component: twoBeat("ch6_15a_navy_fires_on_merchant","THE ROYAL NAVY FIRES ON ITS OWN",174, "ch6_15b_junks_protect_merchant","CHINESE JUNKS SHIELD A BRITISH MERCHANT",173) },
  { id:"CH6-16", durSec:8.32, voStart:127.6, voEnd:135.92, Component: single("ch6_16_commons_near_vote", "A FLEET IS NOT A POLICY") },
];

export const CH6_FPS = 30;
export const CH6_AUDIO = "the-moment/audio/sec_07_chapter_six_the_paper.wav";
