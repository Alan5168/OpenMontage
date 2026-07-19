import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";
import { UIChapter } from "../ui/UIChapter";
import { UIDate } from "../ui/UIDate";
import { UIBigNum } from "../ui/UIBigNum";
import { UICompare } from "../ui/UICompare";
import { UIQuote } from "../ui/UIQuote";
import { UIWire } from "../ui/UIWire";
import { UIStamp } from "../ui/UIStamp";
import { UISchematic } from "../ui/UISchematic";
import {
  MapTriangle,
  MapCantonApproach,
  MapTreatyPorts,
  MapPearl,
  MapMonopolyZone,
  MapPetitionCities,
  MapSplit1813,
} from "../map/scenes";
import { SetShell } from "../set/sets";
import { CharPunch } from "../char/CharPunch";
import { ExecutionDate } from "../chapters/ExecutionDate";
import { NapierContinuous } from "../chapters/NapierFiveCut";
import { FourReadings } from "../chapters/FourReadings";
import { PersonVsFirm } from "../chapters/PersonVsFirm";
import { WinnersRotation, WinnerItem } from "../chapters/WinnersRotation";
import { D_DEMO_PROPS } from "../demo/DChapterReel";
import { Cp1Section, TimedBeat, Cp1ColdOpen, Cp1ChapterFive, Cp1ChapterSeven, CP1_SECTION_SECONDS } from "./Cp1RoughCut";

/**
 * CP2 rough cut — the seven sections outside CP1, aligned to the EN dry
 * stems the same way (manifest chunk starts exact; char-share interpolation
 * inside long chunks, ±2s scratch tolerance). Together with the CP1
 * sections this yields the full-episode scratch (Ep1FullScratch, 24:45).
 *
 * Copy values are v2-accepted script values; D-package demo values are
 * imported from D_DEMO_PROPS (single source — includes the producer-ruled
 * "present/advisers" wording).
 *
 * Ident seams (intro after CO, outro after EP) are compose-stage inserts —
 * deliberately NOT in this scratch so section TCs stay stem-aligned.
 */

const AUDIO2 = {
  ch1: "the-moment/audio/sec_02_chapter_one_the_last_monopoly.wav",
  ch2: "the-moment/audio/sec_03_chapter_two_three_hammers.wav",
  ch3: "the-moment/audio/sec_04_chapter_three_the_brake.wav",
  ch4: "the-moment/audio/sec_05_chapter_four_the_flood.wav",
  ch6: "the-moment/audio/sec_07_chapter_six_the_paper.wav",
  ch8: "the-moment/audio/sec_09_chapter_eight_the_winners_list.wav",
  ep: "the-moment/audio/sec_10_epilogue_the_wire.wav",
} as const;

/** measured stem durations (ffprobe / manifest) */
export const CP2_SECTION_SECONDS = {
  ch1: 104.78,
  ch2: 121.2,
  ch3: 165.007,
  ch4: 108.14,
  ch6: 138.216,
  ch8: 240.174,
  ep: 98.865,
} as const;

/* ---------------- CH1 · The Last Monopoly — 104.78s ---------------- */
/* chunks: 0.00 / 15.41 / 17.39 / 59.43 / 97.50 */

const CH1_BEATS: TimedBeat[] = [
  { from: 0, to: 6.5, name: "C1-1 chapter card", node: (
      <UIChapter kicker="CHAPTER ONE" title="The Last Monopoly" subtitle="the vote's target" />
    ) },
  { from: 6.5, to: 14.0, name: "C1-2 the Company", node: (
      <PaperBackground>
        <CharPunch puppet="CHAR-COMPANY" label="The East India Company" x={960} y={840} height={560} idle={false} />
        <UISchematic />
      </PaperBackground>
    ) },
  { from: 14.0, to: 22.0, name: "C1-3 bigger than the King's", node: (
      <UIBigNum kicker="A PRIVATE ARMY" value="200,000" qualifier="strong — bigger than the King's" accent={TM.britishRed} />
    ) },
  // map-share batch 1 (night run 07-19): "all trade east of Africa" is a
  // geographic claim — drawn as the monopoly zone, not told as a date pin
  { from: 22.0, to: 32.8, name: "C1-4 one firm, one street", node: (
      <MapMonopolyZone title="All trade east of Africa — one firm's, by law" date="SINCE 1600" />
    ) },
  { from: 32.8, to: 46.5, name: "C1-5 1813 — 130 petitions", node: (
      <UIBigNum kicker="1813 · CHARTER RENEWAL" value="130" qualifier="petitions — half of industrial Britain wanted the monopoly dead" accent={TM.qingBlue} />
    ) },
  // map-share batch 1: petition wave drawn as converging arcs on Westminster
  // (route_arc grammar) — replaces the three-merchant puppet row
  { from: 46.5, to: 59.43, name: "C1-6 the cities at the door", node: (
      <MapPetitionCities title="The cities at the door" date="1813 · 130 PETITIONS" />
    ) },
  // map-share batch 1: the 1813 split shown as two region states
  { from: 59.43, to: 67.2, name: "C1-7 India open, China locked", node: (
      <MapSplit1813 title="The 1813 split" date="INDIA OPEN · CHINA LOCKED" />
    ) },
  // §3.10 waveform fix (night run 07-19): 25.7s static card split at the
  // measured VO pause 67.2+10.10s — number first, verdict second
  { from: 67.2, to: 77.3, name: "C1-8a the tea pillar — the number", node: (
      <UIBigNum kicker="WHY CHINA SURVIVED · TEA" value="1/6" qualifier="of the combined revenue of Britain and India" accent={TM.qingYellow} />
    ) },
  { from: 77.3, to: 92.9, name: "C1-8b no Chancellor gambles", node: (
      <UIBigNum kicker="ONE POUND IN SIX" value="NO CHANCELLOR" qualifier="gambles that on an ideology" accent={TM.qingYellow} />
    ) },
  { from: 92.9, to: 97.5, name: "C1-9 twenty-year timer", node: (
      <UIBigNum kicker="THE SURVIVING MONOPOLY" value="20 YEARS" qualifier="on a timer" accent={TM.inkSoft} />
    ) },
  { from: 97.5, to: CP2_SECTION_SECONDS.ch1, name: "C1-10 no friends left", node: (
      <UIBigNum kicker="NEXT TIME THE CHARTER COMES UP" value="0" qualifier="friends left at all" accent={TM.britishRed} />
    ) },
];

/* ---------------- CH2 · Three Hammers — 121.20s ---------------- */
/* chunks: 0.00 / 56.46 / 101.10 / 107.28 */

const ClauseCard: React.FC<{ ghost?: boolean }> = ({ ghost = false }) => (
  <PaperBackground tone="hi">
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: ghost ? 0.55 : 1 }}>
      <div
        style={{
          fontFamily: TM.fontMono,
          fontSize: 26,
          letterSpacing: "0.24em",
          color: TM.inkSoft,
          marginBottom: 50,
        }}
      >
        THE FALLBACK CLAUSE · TYPESET
      </div>
      <div
        style={{
          fontFamily: TM.fontHeading,
          fontSize: 52,
          lineHeight: 1.5,
          color: TM.ink,
          maxWidth: 1250,
          textAlign: "center",
        }}
      >
        …consular powers at Canton — legal authority over the British merchants about to flood in…
      </div>
      {ghost ? (
        <div style={{ fontFamily: TM.fontBody, fontSize: 32, color: TM.inkSoft, marginTop: 56 }}>
          Hold that clause. It's the ghost in everything that follows.
        </div>
      ) : null}
    </AbsoluteFill>
    <UIStamp kind="rejected" x={1230} y={700} rotation={-8} delay={ghost ? 0 : 55} />
  </PaperBackground>
);

const CH2_BEATS: TimedBeat[] = [
  { from: 0, to: 3.7, name: "C2-1 chapter card", node: (
      <UIChapter kicker="CHAPTER TWO" title="Three Hammers" subtitle="1813–1833" />
    ) },
  { from: 3.7, to: 18.5, name: "C2-2 hammers 1+2 — Reform Act", node: (
      <SetShell set="SET-COMMONS">
        <UIDate date="1832" event="Reform Act — the rotten boroughs abolished" x={110} y={90} delay={6} />
        <CharPunch puppet="CHAR-MP" x={960} y={900} height={400} delay={16} idle={false} />
        <UISchematic />
      </SetShell>
    ) },
  { from: 18.5, to: 30.8, name: "C2-3 Calcutta houses collapse", node: (
      <SetShell set="SET-CALCUTTA-AUCTION">
        <UIDate date="1830s" event="the great Calcutta houses fall — credit broken" x={110} y={90} delay={6} />
        <UISchematic />
      </SetShell>
    ) },
  { from: 30.8, to: 45.0, name: "C2-4 Macaulay — not one voice", node: (
      <UIQuote
        quote="Not one voice — not one — had been raised in support of the monopoly."
        attribution="Thomas Macaulay"
        context="Commons, 1833"
        kind="paraphrase"
        accent={TM.qingBlue}
      />
    ) },
  { from: 45.0, to: 56.46, name: "C2-5 zero defenders", node: (
      <UIBigNum kicker="THE MOST POWERFUL COMMERCIAL PRIVILEGE ON EARTH" value="0" qualifier="defenders — no Whig, no Tory" accent={TM.britishRed} />
    ) },
  { from: 56.46, to: 81.0, name: "C2-6 empire, not trade", node: (
      <UICompare
        title="WHAT THE COMPANY ACTUALLY FOUGHT FOR"
        leftTitle="The trade"
        rightTitle="The empire"
        leftItems={["let go"]}
        rightItems={["India, army, territory, tax revenue", "10.5%/yr guaranteed — out of Indian taxes"]}
        leftAccent={TM.inkFaint}
        rightAccent={TM.britishRed}
        footnote="a trading company died; a corporate state survived"
      />
    ) },
  { from: 81.0, to: 101.1, name: "C2-7 the clause, rejected", node: <ClauseCard /> },
  { from: 101.1, to: 107.28, name: "C2-8 hold the ghost", node: <ClauseCard ghost /> },
  { from: 107.28, to: CP2_SECTION_SECONDS.ch2, name: "C2-9 execution date", node: (
      // DELIBERATE D_DEMO_PROPS reuse: values ("Act of 1833", 22 APRIL 1834)
      // are the accepted v2 script content (re-verified 2026-07-18)
      <ExecutionDate {...D_DEMO_PROPS.executionDate} />
    ) },
];

/* ---------------- CH3 · The Brake — 165.01s ---------------- */
/* chunks: 0.00 / 36.84 / 39.31 / 62.65 / 64.07 / 81.74 / 83.34 / 152.50 */

const CH3_BEATS: TimedBeat[] = [
  { from: 0, to: 9.1, name: "C3-1 chapter card", node: (
      <UIChapter kicker="CHAPTER THREE" title="The Brake" subtitle="producer and regulator at once" />
    ) },
  { from: 9.1, to: 24.0, name: "C3-2 the triangle", node: <MapTriangle title="Grow · Auction · Ship" date="1794–1834" /> },
  { from: 24.0, to: 36.84, name: "C3-3 licenses — the brake", node: (
      <PaperBackground>
        <CharPunch puppet="CHAR-CLERK" label="Select Committee, Canton — licenses, revocable" x={960} y={880} height={470} idle={false} />
        <UISchematic />
      </PaperBackground>
    ) },
  { from: 36.84, to: 40.2, name: "C3-4 a brake", node: (
      <UIBigNum kicker="A DRUG CARTEL — WITH A COMPLIANCE DEPARTMENT" value="A BRAKE." qualifier="cynical. But a brake." accent={TM.qingBlue} />
    ) },
  { from: 40.2, to: 62.65, name: "C3-5 the December 1833 letter", node: (
      <UIQuote
        quote="A sudden and entire stop … would produce mischief which might have been avoided by a more gradual change."
        attribution="Company correspondent, London — private letter"
        context="December 1833"
        kind="paraphrase"
        accent={TM.opiumPurple}
      />
    ) },
  { from: 62.65, to: 70.0, name: "C3-6 MISCHIEF", node: (
      <UIBigNum value="MISCHIEF." qualifier="remember the word" accent={TM.britishRed} />
    ) },
  { from: 70.0, to: 81.74, name: "C3-7 the brake comes out", node: (
      <PaperBackground>
        <UIDate date="22 APRIL 1834" event="monopoly ends — Select Committee dissolves, licenses void" x={560} y={420} scale={1.4} delay={4} />
        <UISchematic />
      </PaperBackground>
    ) },
  { from: 81.74, to: 90.5, name: "C3-8 one man", node: (
      <PaperBackground>
        <CharPunch puppet="CHAR-SAILOR" label="Lord Napier — zero China experience, zero legal power" x={960} y={880} height={490} idle={false} />
        <UISchematic />
      </PaperBackground>
    ) },
  // C3-9..12 retimed to sentence-level VO offsets (producer diagnosis §2:
  // WARSHIPS card measured 14.0s static; five cuts ~4.3s each)
  { from: 90.5, to: 110.9, name: "C3-9 letter refused, trade suspended", node: <MapCantonApproach step={1} /> },
  { from: 110.9, to: 123.3, name: "C3-10 Napier — one continuous scene", node: (
      // continuous staging replaces five hard cuts (CEO #7 "太抽象");
      // fractions pin advance/batteries/fever/retreat/death to VO phrases
      <NapierContinuous totalSeconds={12.4} eventFractions={[0.09, 0.33, 0.46, 0.6, 0.74]} />
    ) },
  { from: 123.3, to: 129.1, name: "C3-11 petition for warships", node: (
      <UIBigNum kicker="THE MAN DIED — THE MEN WHO EGGED HIM ON DID NOT" value="WARSHIPS" qualifier="the traders' petition to London, immediately" accent={TM.britishRed} />
    ) },
  { from: 129.1, to: 141.0, name: "C3-12a a name to remember", node: (
      <PaperBackground>
        <UIDate date="A NAME TO REMEMBER" event="head of the warships petition" x={110} y={90} delay={4} />
        <CharPunch puppet="CHAR-MERCHANT" label="William Jardine — ship's surgeon at 19" x={960} y={880} height={490} delay={8} idle={false} />
        <UISchematic />
      </PaperBackground>
    ) },
  { from: 141.0, to: 152.5, name: "C3-12b surgeon turned taipan", node: (
      <SetShell set="SET-CANTON-FACTORY">
        <CharPunch puppet="CHAR-MERCHANT" label="…turned taipan — top of Canton's private merchant world" x={960} y={900} height={440} delay={6} idle={false} flip />
        <UISchematic />
      </SetShell>
    ) },
  { from: 152.5, to: CP2_SECTION_SECONDS.ch3, name: "C3-13 six months", node: (
      <UIBigNum kicker="THE PREDICTION HELD" value="6 MONTHS" qualifier="from abolition to the first armed standoff" accent={TM.inkSoft} />
    ) },
];

/* ---------------- CH4 · The Flood — 108.14s ---------------- */
/* chunks: 0.00 / 92.08 / 95.05 */

/**
 * CH4 rebuilt as page-flips (CEO feedback #10; producer diagnosis §1.3):
 * one reading per narration beat via the new FourReadings `focus` prop,
 * then the full grid appears exactly ONCE as the recap under "That's what
 * a deregulated drug market did…". Page boundaries = char-share offsets of
 * the N1–N4 paragraphs inside chunk ch01.
 *
 * D_DEMO_PROPS.fourReadings data itself is DELIBERATE reuse — every value
 * ($2,500→<$600 / 22,000→40,000 chests / $38M / 1:1,000→1:1,600) matches
 * the accepted v2 script verbatim (re-verified against tts sidecar
 * 2026-07-18); what was wrong was the assembly, not the numbers.
 */
const CH4_BEATS: TimedBeat[] = [
  { from: 0, to: 6.5, name: "C4-1 chapter card", node: (
      <UIChapter kicker="CHAPTER FOUR" title="The Flood" subtitle="four readings — parallel, not a chain" />
    ) },
  { from: 6.5, to: 39.6, name: "C4-2 reading 1 — the price", node: (
      <FourReadings {...D_DEMO_PROPS.fourReadings} focus={1} />
    ) },
  { from: 39.6, to: 53.8, name: "C4-3 reading 2 — the volume", node: (
      <FourReadings {...D_DEMO_PROPS.fourReadings} focus={2} />
    ) },
  { from: 53.8, to: 64.4, name: "C4-4 reading 3 — the silver", node: (
      <FourReadings {...D_DEMO_PROPS.fourReadings} focus={3} />
    ) },
  { from: 64.4, to: 92.08, name: "C4-5 reading 4 — the exchange", node: (
      <FourReadings {...D_DEMO_PROPS.fourReadings} focus={4} />
    ) },
  { from: 92.08, to: 95.05, name: "C4-6 silently", node: (
      <UIChapter title="Silently. To everyone." weak />
    ) },
  { from: 95.05, to: CP2_SECTION_SECONDS.ch4, name: "C4-7 recap — all four at once", node: (
      <FourReadings {...D_DEMO_PROPS.fourReadings} />
    ) },
];

/* ---------------- CH6 · The Paper — 138.22s ---------------- */
/* chunks: 0.00 / 21.90 / 54.40 / 56.88 / 103.68 / 119.79 */

const CH6_BEATS: TimedBeat[] = [
  { from: 0, to: 8.0, name: "C6-1 chapter card", node: (
      <UIChapter kicker="CHAPTER SIX" title="The Paper" subtitle="one signature" />
    ) },
  { from: 8.0, to: 21.9, name: "C6-2 Elliot under siege", node: (
      <SetShell set="SET-CANTON-FACTORY">
        <UIDate date="1839" event="merchants besieged — no fleet behind him" x={110} y={90} delay={4} />
        <CharPunch puppet="CHAR-SAILOR" label="Charles Elliot — superintendent of trade" x={960} y={900} height={430} delay={14} idle={false} />
        <UISchematic />
      </SetShell>
    ) },
  { from: 21.9, to: 35.0, name: "C6-3 what the paper really was", node: (
      <UIWire
        title="Read what the paper really was"
        beads={[
          { year: "CONTRABAND" },
          { year: "SEIZED", label: "by a foreign state, enforcing its law" },
          { year: "SIGNED", label: "no authorization whatsoever" },
          { year: "DEBT", label: "a claim on the British Treasury" },
        ]}
        beatFrames={70}
        accent={TM.britishRed}
      />
    ) },
  { from: 35.0, to: 41.0, name: "C6-4 two million pounds", node: (
      <UIBigNum value="£2,000,000+" qualifier="a promise London never approved — and couldn't afford" accent={TM.britishRed} />
    ) },
  { from: 41.0, to: 53.0, name: "C6-5 least resistance", node: (
      <UIBigNum kicker="FOR THE CABINET" value="LEAST RESISTANCE" qualifier="collect the money from China" accent={TM.inkSoft} />
    ) },
  { from: 53.0, to: 56.88, name: "C6-6 at gunpoint", node: (
      <UIBigNum value="AT GUNPOINT." qualifier="in the end" accent={TM.britishRed} />
    ) },
  { from: 56.88, to: 86.0, name: "C6-7 four steps — the episode claim", node: (
      <UIWire
        title="How a law with zero defenders detonates a war"
        beads={[
          { year: "1833", label: "the brake dissolved" },
          { year: "CLAUSE", label: "the one replacement — rejected" },
          { year: "FLOOD", label: "cheap opium into China" },
          { year: "DEBT", label: "only a war could cash it" },
        ]}
        beatFrames={130}
        accent={TM.opiumPurple}
      />
    ) },
  { from: 86.0, to: 103.68, name: "C6-8 the switch in Westminster", node: (
      <UIBigNum kicker="NOT THE ONLY CAUSE — THE MOST UNDERRATED ONE" value="THE SWITCH" qualifier="sits in Westminster — passed while not one voice defended what was being torn down" accent={TM.qingBlue} />
    ) },
  { from: 103.68, to: 129.5, name: "C6-9 the machine eats itself", node: (
      <MapPearl title="The machine eats itself" date="NOV 1839" />
    ) },
  { from: 129.5, to: CP2_SECTION_SECONDS.ch6, name: "C6-10 a fleet is not a policy", node: (
      <UIChapter title="A fleet is not a policy." weak />
    ) },
];

/* ---------------- CH8 · The Winners' List — 240.17s ---------------- */
/* chunks: 0.00 / 63.68 / 173.29 / 182.13 / 183.50 / 237.34 */

// DELIBERATE D_DEMO_PROPS reuse (×3 slices): HSBC 1865 / Swire 1866, Dent
// 1866 collapse, Treasury £3.66M, Manchester forecast — all match the
// accepted v2 script verbatim (re-verified against tts sidecar 2026-07-18).
// winners[0] (proposal-vs-treaty compare) is intentionally NOT used here —
// CH8-4 builds its own UICompare with alignment ties instead.
const winnersNotYet: WinnerItem[] = [D_DEMO_PROPS.winners[1]];
const winnersRealList: WinnerItem[] = [D_DEMO_PROPS.winners[2], D_DEMO_PROPS.winners[3]];
const winnersForecast: WinnerItem[] = [D_DEMO_PROPS.winners[4]];

const CH8_BEATS: TimedBeat[] = [
  { from: 0, to: 7.0, name: "C8-1 chapter card", node: (
      <UIChapter kicker="CHAPTER EIGHT" title="The Winners' List" subtitle="it's not who you think" />
    ) },
  { from: 7.0, to: 20.1, name: "C8-2 Treaty of Nanking", node: (
      <MapTreatyPorts title="Treaty of Nanking — the paper cashed in full" date="AUG 1842" />
    ) },
  { from: 20.1, to: 25.6, name: "C8-3 who actually won?", node: (
      <UIChapter title="So who actually won?" weak />
    ) },
  { from: 25.6, to: 39.6, name: "C8-4 proposal vs treaty", node: (
      <UICompare
        title="JARDINE MATHESON — FIRST AND BIGGEST"
        leftTitle="The proposal"
        rightTitle="The treaty"
        leftItems={["which ports to take", "an island base", "costs charged to China"]}
        rightItems={["five ports open", "Hong Kong ceded", "21M silver dollars"]}
        ties={[[0, 0], [1, 1], [2, 2]]}
        leftAccent={TM.opiumPurple}
        rightAccent={TM.britishRed}
        footnote="alignment, port for port — comparison only, no causal arrows"
      />
    ) },
  { from: 39.6, to: 92.6, name: "C8-5 the man and the firm", node: (
      // DELIBERATE D_DEMO_PROPS reuse: Jardine biography values verified
      // against claim_log #60/#65 (producer diagnosis §1.3 confirms)
      <PersonVsFirm {...D_DEMO_PROPS.personVsFirm} />
    ) },
  { from: 92.6, to: 114.5, name: "C8-6 the internet's list — mostly fake", node: (
      <WinnersRotation items={winnersNotYet} secondsPerItem={21.9} />
    ) },
  { from: 114.5, to: 150.5, name: "C8-7 the real winners", node: (
      <WinnersRotation items={winnersRealList} secondsPerItem={18} />
    ) },
  { from: 150.5, to: 173.29, name: "C8-8 the loudest lobby lost", node: (
      <WinnersRotation items={winnersForecast} secondsPerItem={22.8} />
    ) },
  { from: 173.29, to: 182.13, name: "C8-9 one name left", node: (
      <PaperBackground>
        <CharPunch puppet="CHAR-COMPANY" label="The East India Company — its take:" x={960} y={840} height={540} idle={false} />
        <UISchematic />
      </PaperBackground>
    ) },
  { from: 182.13, to: 196.0, name: "C8-10 ZERO", node: (
      <UIBigNum value="ZERO" qualifier="direct commercial gain — China trade (banned from it since '34)" accent={TM.britishRed} />
    ) },
  { from: 196.0, to: 216.0, name: "C8-11 the exposure", node: (
      <UIBigNum kicker="OPIUM SHARE OF BRITISH INDIA'S REVENUE" value="7% → 20%+" qualifier="over two decades — openly, on the parliamentary record" accent={TM.opiumPurple} />
    ) },
  { from: 216.0, to: 237.34, name: "C8-12 the India line", node: (
      <UIWire
        title="The India line — its own grievances, not China's"
        beads={[
          { year: "1853", label: "charter renewed — no end date" },
          { year: "1857", label: "India rises" },
          { year: "1858", label: "the Crown takes India" },
          { year: "1874", label: "dissolved — 274 years" },
        ]}
        beatFrames={110}
        accent={TM.qingYellow}
      />
    ) },
  { from: 237.34, to: CP2_SECTION_SECONDS.ch8, name: "C8-13 the ledger closes", node: (
      <UIChapter title="The ledger closes." weak />
    ) },
];

/* ---------------- EP · The Wire — 98.87s ---------------- */
/* chunks: 0.00 / 53.25 / 70.08 / 94.07 / 97.38 */

const EP_BEATS: TimedBeat[] = [
  { from: 0, to: 4.0, name: "EP-1 epilogue card", node: (
      <UIChapter kicker="EPILOGUE" title="The Wire" weak />
    ) },
  { from: 4.0, to: 53.25, name: "EP-2 run the wire backwards", node: (
      <UIWire
        title="Run the wire backwards, one last time"
        beads={[
          { year: "1874", label: "dissolved" },
          { year: "1858", label: "nationalized" },
          { year: "1842", label: "the treaty" },
          { year: "1840", label: "nine votes" },
          { year: "1839", label: "the signature" },
          { year: "1834", label: "the flood" },
          { year: "1833", label: "zero defenders" },
          { year: "1813", label: "a vote about India" },
        ]}
        beatFrames={200}
        accent={TM.opiumPurple}
      />
    ) },
  { from: 53.25, to: 70.08, name: "EP-3 no villain", node: (
      <UIBigNum kicker="NO MASTER PLAN" value="NO VILLAIN" qualifier="a market with no brake, a debt with no payer, a government nine votes from the exit" accent={TM.inkSoft} />
    ) },
  // §3.10 waveform fix (night run 07-19): the surgeon now enters on the
  // measured VO pause at +15.5s (frame ≈ 470) — the 24s shot changes state
  // mid-way instead of front-loading both puppets
  { from: 70.08, to: 94.07, name: "EP-4 the thread left hanging", node: (
      <PaperBackground>
        <CharPunch puppet="CHAR-MERCHANT" label="Parsi merchants out of Bombay" x={760} y={880} height={470} delay={8} idle={false} />
        <CharPunch puppet="CHAR-SAILOR" label="a 19-year-old surgeon, first sailing east" x={1220} y={880} height={470} delay={470} idle={false} flip />
        <UISchematic />
      </PaperBackground>
    ) },
  { from: 94.07, to: CP2_SECTION_SECONDS.ep, name: "EP-5 next episode", node: (
      <UIChapter kicker="NEXT EPISODE" title="The men who really sold opium to China" weak />
    ) },
];

/* ---------------- assembly ---------------- */

export const CP2_BEAT_MAP = {
  ch1: CH1_BEATS,
  ch2: CH2_BEATS,
  ch3: CH3_BEATS,
  ch4: CH4_BEATS,
  ch6: CH6_BEATS,
  ch8: CH8_BEATS,
  ep: EP_BEATS,
} as const;

export const Cp2ChapterOne: React.FC = () => (
  <Cp1Section audioSrc={AUDIO2.ch1} beats={CH1_BEATS} label="CH1" phase="CP2" />
);
export const Cp2ChapterTwo: React.FC = () => (
  <Cp1Section audioSrc={AUDIO2.ch2} beats={CH2_BEATS} label="CH2" phase="CP2" />
);
export const Cp2ChapterThree: React.FC = () => (
  <Cp1Section audioSrc={AUDIO2.ch3} beats={CH3_BEATS} label="CH3" phase="CP2" />
);
export const Cp2ChapterFour: React.FC = () => (
  <Cp1Section audioSrc={AUDIO2.ch4} beats={CH4_BEATS} label="CH4" phase="CP2" />
);
export const Cp2ChapterSix: React.FC = () => (
  <Cp1Section audioSrc={AUDIO2.ch6} beats={CH6_BEATS} label="CH6" phase="CP2" />
);
export const Cp2ChapterEight: React.FC = () => (
  <Cp1Section audioSrc={AUDIO2.ch8} beats={CH8_BEATS} label="CH8" phase="CP2" />
);
export const Cp2Epilogue: React.FC = () => (
  <Cp1Section audioSrc={AUDIO2.ep} beats={EP_BEATS} label="EP" phase="CP2" />
);

export const cp2SectionFrames = (fps: number) =>
  Object.fromEntries(
    Object.entries(CP2_SECTION_SECONDS).map(([k, v]) => [k, Math.round(v * fps)])
  ) as Record<keyof typeof CP2_SECTION_SECONDS, number>;

/** full-episode scratch: all 10 sections in stem order (idents are compose-stage seams, not included) */
export const Ep1FullScratch: React.FC = () => {
  const { fps } = useVideoConfig();
  const f2 = cp2SectionFrames(fps);
  const order: Array<{ name: string; frames: number; node: React.ReactNode }> = [
    { name: "CO", frames: Math.round(CP1_SECTION_SECONDS.co * fps), node: <Cp1ColdOpen /> },
    { name: "CH1", frames: f2.ch1, node: <Cp2ChapterOne /> },
    { name: "CH2", frames: f2.ch2, node: <Cp2ChapterTwo /> },
    { name: "CH3", frames: f2.ch3, node: <Cp2ChapterThree /> },
    { name: "CH4", frames: f2.ch4, node: <Cp2ChapterFour /> },
    { name: "CH5", frames: Math.round(CP1_SECTION_SECONDS.ch5 * fps), node: <Cp1ChapterFive /> },
    { name: "CH6", frames: f2.ch6, node: <Cp2ChapterSix /> },
    { name: "CH7", frames: Math.round(CP1_SECTION_SECONDS.ch7 * fps), node: <Cp1ChapterSeven /> },
    { name: "CH8", frames: f2.ch8, node: <Cp2ChapterEight /> },
    { name: "EP", frames: f2.ep, node: <Cp2Epilogue /> },
  ];
  let cursor = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: TM.paper }}>
      {order.map((s) => {
        const from = cursor;
        cursor += s.frames;
        return (
          <Sequence key={s.name} from={from} durationInFrames={s.frames} name={s.name}>
            {s.node}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

export const ep1FullScratchDuration = (fps: number): number => {
  const f2 = cp2SectionFrames(fps);
  return (
    Math.round(CP1_SECTION_SECONDS.co * fps) +
    Math.round(CP1_SECTION_SECONDS.ch5 * fps) +
    Math.round(CP1_SECTION_SECONDS.ch7 * fps) +
    f2.ch1 + f2.ch2 + f2.ch3 + f2.ch4 + f2.ch6 + f2.ch8 + f2.ep
  );
};
