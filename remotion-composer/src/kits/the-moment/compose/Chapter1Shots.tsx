/**
 * Chapter1Shots.tsx — "The Last Monopoly" (sec_02, 104.8s VO)
 *
 * Built 07-23 following the Cold Open's now-validated method from the start
 * (not patched in after the fact): every shot's voStart/voEnd comes from a
 * real ASR transcription of sec_02_chapter_one_the_last_monopoly.wav aligned
 * against the clean script text (see /tmp/ch1_word_spans.json's derivation),
 * every shot is >=3s, and every visual is either a real generated crude-anime
 * illustration (locked house style) or a legible code-driven data graphic —
 * no abstract icon-soup, no baked-in text on generated images.
 */
import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { OldPaperCard, EngravingKenBurns, StampSlam, DatePunch } from "./SentenceShots";

const CH1 = "the-moment/ch1/";

/* C01 — Chapter title + EIC flag/crest */
const C01_Title: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s01_eic_flag_crude.png`} startScale={1.0} endScale={1.1} sepia={0} dim={0.1}
    caption="CHAPTER 1 — THE LAST MONOPOLY" />
);

/* C02 — India map with marching army, single sustained push (12.82s, matches
   CO precedent for long single-image holds e.g. S12/S13/S15) */
const C02_PrivateArmy: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s02_india_army_crude.png`} startScale={1.0} endScale={1.2} sepia={0} dim={0.1}
    caption="A PRIVATE ARMY — BIGGER THAN THE KING'S" />
);

/* C03 — East India House, London */
const C03_IndiaHouse: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s03_india_house_crude.png`} startScale={1.0} endScale={1.15} sepia={0} dim={0.1}
    caption="ONE FIRM. ONE LONDON STREET." />
);

/* C04 — tea crates + ledger */
const C04_TeaLedger: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s04_tea_ledger_crude.png`} startScale={1.0} endScale={1.12} sepia={0} dim={0.1}
    caption="EVERY CUP OF TEA" />
);

/* C05 — petitions pile */
const C05_Petitions: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s05_petitions_crude.png`} startScale={1.0} endScale={1.15} sepia={0} dim={0.1}
    caption="130 PETITIONS" />
);

/* C06 (merged) — factory+ships, then a "MONOPOLY DEAD" stamp finale,
   mirroring the Cold Open's GunboatsToWrongMoment merge pattern: internal
   Sequence beats, no external hard cut needed between them. */
const C06_DeadMonopoly: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={185}>
      <EngravingKenBurns src={`${CH1}ch1_s06_factory_ships_crude.png`} startScale={1.0} endScale={1.15} sepia={0} dim={0.15}
        caption="COTTON THEY COULDN'T SELL" />
    </Sequence>
    <Sequence from={185} durationInFrames={102}>
      <StampSlam text="MONOPOLY DEAD" color={TM.britishRed} />
    </Sequence>
  </AbsoluteFill>
);

/* C07 — Perceval shot dead in the Commons lobby */
const C07_Perceval: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s08_perceval_shot_crude.png`} startScale={1.02} endScale={1.18} sepia={0} dim={0.1}
    caption="THE SHIELD, SHOT DEAD" />
);

/* C08 — shield cracking */
const C08_ShieldCrack: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s09_shield_crack_crude.png`} startScale={1.05} endScale={1.25} sepia={0} dim={0.15}
    caption="THE SHIELD VANISHED" />
);

/* C09 (merged) — India gates opening, then a "1813" date-punch reveal */
const C09_VoteAboutIndia: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={160}>
      <EngravingKenBurns src={`${CH1}ch1_s10_india_gates_crude.png`} startScale={1.0} endScale={1.15} sepia={0} dim={0.1}
        caption="THE VOTE ABOUT INDIA" />
    </Sequence>
    <Sequence from={160} durationInFrames={77}>
      <DatePunch year="1813" color={TM.qingYellow} variant="dark" sub="MONOPOLY BROKEN" />
    </Sequence>
  </AbsoluteFill>
);

/* C10 — China locked, chained */
const C10_ChinaLocked: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s11_china_locked_crude.png`} startScale={1.0} endScale={1.15} sepia={0} dim={0.1}
    caption="BUT CHINA? LOCKED." />
);

/* C11 — 1/6 of combined revenue: a legible code-driven pie chart (data
   graphic, not a decode-required icon — same category as NineVotes' tally
   bars in the Cold Open, which Alan did not flag as "too abstract"). */
const RevenuePie: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const draw = spring({ frame: frame - 15, fps, config: { damping: 18, stiffness: 90 } });
  const R = 180, CX = 960, CY = 560;
  const sliceAngle = (1 / 6) * 360 * Math.min(1, draw);
  const toXY = (angleDeg: number) => {
    const a = (angleDeg - 90) * (Math.PI / 180);
    return [CX + R * Math.cos(a), CY + R * Math.sin(a)];
  };
  const [x1, y1] = toXY(0);
  const [x2, y2] = toXY(sliceAngle);
  const large = sliceAngle > 180 ? 1 : 0;
  return (
    <OldPaperCard variant="dark">
      <div style={{ position:"absolute", left:0, right:0, top: 50, textAlign:"center", fontFamily: TM.fontHeading, fontSize: 40, color: TM.paper, opacity: Math.min(1, frame / 15) }}>
        ONE SIXTH OF THE BUDGET
      </div>
      <svg viewBox="0 0 1920 1080" style={{ position:"absolute", inset:0, width:"100%", height:"100%" }}>
        <circle cx={CX} cy={CY} r={R} fill="none" stroke={TM.paper} strokeWidth={3} opacity={0.35} />
        {sliceAngle > 0.5 && (
          <path d={`M ${CX} ${CY} L ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2} Z`} fill={TM.britishRed} opacity={0.9} />
        )}
      </svg>
      <div style={{ position:"absolute", left:0, right:0, top: 800, textAlign:"center", fontFamily: TM.fontHeading, fontSize: 90, fontWeight: 900, color: TM.qingYellow, opacity: Math.min(1, (frame-20) / 15) }}>
        1 / 6
      </div>
      <div style={{ position:"absolute", left:0, right:0, top: 910, textAlign:"center", fontFamily: TM.fontMono, fontSize: 20, letterSpacing:"0.15em", color: TM.paper, opacity: 0.75 * Math.min(1, (frame-20) / 15) }}>
        OF BRITAIN + INDIA'S COMBINED REVENUE
      </div>
    </OldPaperCard>
  );
};

/* C12 — balance scale, gold vs books */
const C12_ScaleBalance: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s13_scale_balance_crude.png`} startScale={1.0} endScale={1.12} sepia={0} dim={0.1}
    caption="FISCAL FEAR BEAT FREE TRADE" />
);

/* C13 — hourglass, twenty-year timer */
const C13_TwentyYearTimer: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <EngravingKenBurns src={`${CH1}ch1_s14_hourglass_crude.png`} startScale={1.0} endScale={1.15} sepia={0} dim={0.15}
        caption="A TWENTY-YEAR TIMER" />
      <div style={{ position:"absolute", left:0, right:0, bottom: 140, textAlign:"center",
        fontFamily: TM.fontMono, fontSize: 34, letterSpacing:"0.2em", color: TM.paper,
        opacity: Math.min(1, (frame - 20) / 15), textShadow:"0 2px 8px rgba(0,0,0,0.8)" }}>
        1813 → 1833
      </div>
    </AbsoluteFill>
  );
};

/* C14 — closing: the company standing alone, no friends left */
const C14_NoFriendsLeft: React.FC = () => (
  <EngravingKenBurns src={`${CH1}ch1_s15_isolated_crude.png`} startScale={1.0} endScale={1.18} sepia={0} dim={0.25}
    caption="NO FRIENDS LEFT AT ALL" />
);

export interface Chapter1ShotSpec {
  id: string;
  durSec: number;
  voStart: number;
  voEnd: number;
  Component: React.FC;
  voHoldSec?: number;
}

export const CHAPTER1_SHOTS: Chapter1ShotSpec[] = [
  { id:"C01", durSec:3.60, voStart:0.00, voEnd:3.60, Component:C01_Title },
  { id:"C02", durSec:12.82, voStart:3.60, voEnd:16.42, Component:C02_PrivateArmy },
  { id:"C03", durSec:8.68, voStart:16.42, voEnd:25.10, Component:C03_IndiaHouse },
  { id:"C04", durSec:3.11, voStart:25.10, voEnd:28.21, Component:C04_TeaLedger },
  { id:"C05", durSec:7.17, voStart:28.21, voEnd:35.38, Component:C05_Petitions },
  { id:"C06", durSec:9.56, voStart:35.38, voEnd:44.94, Component:C06_DeadMonopoly },
  { id:"C07", durSec:10.91, voStart:44.94, voEnd:55.85, Component:C07_Perceval },
  { id:"C08", durSec:3.19, voStart:55.85, voEnd:59.04, Component:C08_ShieldCrack },
  { id:"C09", durSec:7.89, voStart:59.04, voEnd:66.93, Component:C09_VoteAboutIndia },
  { id:"C10", durSec:6.00, voStart:66.93, voEnd:72.93, Component:C10_ChinaLocked },
  { id:"C11", durSec:11.53, voStart:72.93, voEnd:84.46, Component:RevenuePie },
  { id:"C12", durSec:7.09, voStart:84.46, voEnd:91.55, Component:C12_ScaleBalance },
  { id:"C13", durSec:4.98, voStart:91.55, voEnd:96.53, Component:C13_TwentyYearTimer },
  { id:"C14", durSec:6.46, voStart:96.53, voEnd:102.99, Component:C14_NoFriendsLeft },
];

export const CH1_FPS = 30;
export const CH1_AUDIO = "the-moment/audio/sec_02_chapter_one_the_last_monopoly.wav";
