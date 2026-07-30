/**
 * ChapterepiShots.tsx — auto-generated from the ASR-verified >=3s scene
 * plan. Every visual is a real doubao-seedream crude-anime illustration.
 */
import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { EngravingKenBurns } from "./SentenceShots";

const FOLDER = "the-moment/epi/";

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

export interface ChapterepiShotSpec {
  id: string; durSec: number; voStart: number; voEnd: number; Component: React.FC; voHoldSec?: number;
}

export const CHAPTERepi_SHOTS: ChapterepiShotSpec[] = [
  { id:"EPI-01", durSec:5.973, voStart:0.192, voEnd:6.165, Component: single("epi_01_wire_rewind_company_dissolved", "RUN THE WIRE BACKWARDS, ONE LAST TIME") },
  { id:"EPI-02", durSec:8.213, voStart:6.165, voEnd:14.378, Component: twoBeat("epi_02a_crown_takeover","1858 — THE CROWN TAKES INDIA",123, "epi_02b_war_indemnity_denied","1842 — THE COMPANY GETS NOTHING",123) },
  { id:"EPI-03", durSec:7.12, voStart:14.378, voEnd:21.498, Component: single("epi_03_parliament_narrow_vote", "NINE VOTES KEEP THE POLICY ALIVE") },
  { id:"EPI-04", durSec:5.104, voStart:21.498, voEnd:26.602, Component: single("epi_04_signature_contraband_to_debt", "1839 — CONTRABAND BECOMES DEBT") },
  { id:"EPI-05", durSec:6.72, voStart:26.602, voEnd:33.322, Component: single("epi_05_market_flooded_broken_brake", "1834 — THE MARKET FLOODS") },
  { id:"EPI-06", durSec:8.8, voStart:33.322, voEnd:42.122, Component: twoBeat("epi_06a_law_passed_no_defense","1833 — THE MONOPOLY DIES UNDEFENDED",132, "epi_06b_rejected_clause_discarded","THE GOVERNING CLAUSE IS REJECTED",132) },
  { id:"EPI-07", durSec:9.68, voStart:42.122, voEnd:51.802, Component: twoBeat("epi_07a_empty_battlefield_throne","THE WIRE BEGINS IN 1813",145, "epi_07b_london_vote_1813","A VOTE ABOUT INDIA",145) },
  { id:"EPI-08", durSec:7.552, voStart:51.802, voEnd:59.354, Component: single("epi_08_ground_cracks_dominoes_falling", "THE GROUND STARTS TO MOVE") },
  { id:"EPI-09", durSec:9.36, voStart:59.354, voEnd:68.714, Component: twoBeat("epi_09a_no_brake_no_payer_government_exit","NO BRAKE. NO PAYER. NO EXIT.",140, "epi_09b_empire_brakes_too_late","BEIJING'S BRAKE ARRIVES TOO LATE",141) },
  { id:"EPI-10", durSec:7.792, voStart:68.714, voEnd:76.506, Component: single("epi_10_opium_loading_india_dock", "ONE THREAD LEFT HANGING") },
  { id:"EPI-11", durSec:3.09, voStart:76.506, voEnd:79.596, Component: single("epi_11_textbook_smuggler_crossed_out", "THE TEXTBOOK SAYS BRITISH SMUGGLERS") },
  { id:"EPI-12", durSec:5.817, voStart:79.596, voEnd:85.413, Component: single("epi_12_parsi_merchants_bombay_dock", "PARSI MERCHANTS MOVED THE OPIUM") },
  { id:"EPI-13", durSec:7.109, voStart:85.413, voEnd:92.522, Component: single("epi_13_jardine_parsi_friend_shipdeck", "ONE OF THEM WAS JARDINE'S OLDEST FRIEND") },
  { id:"EPI-14", durSec:5.784, voStart:92.522, voEnd:98.306, Component: single("epi_14_opium_sellers_teaser", "WHO REALLY SOLD OPIUM TO CHINA?") },
];

export const CHepi_FPS = 30;
export const CHepi_AUDIO = "the-moment/audio/sec_10_epilogue_the_wire.wav";
