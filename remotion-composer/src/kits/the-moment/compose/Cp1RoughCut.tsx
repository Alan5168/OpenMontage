import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { BgmUnderVo } from "./BgmUnderVo";
import { EventSfx } from "./EventSfx";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";
import { UIChapter } from "../ui/UIChapter";
import { UIDate } from "../ui/UIDate";
import { UIBigNum } from "../ui/UIBigNum";
import { UICensure } from "../ui/UICensure";
import { UICompare } from "../ui/UICompare";
import { UIQuote } from "../ui/UIQuote";
import { UIWire } from "../ui/UIWire";
import { UISchematic } from "../ui/UISchematic";
import {
  MapTreatyPorts,
  MapPearl,
  MapQingBans,
  MapHumen,
  MapLetterRoute,
} from "../map/scenes";
import { SetShell } from "../set/sets";
import { CharPunch } from "../char/CharPunch";
import { EngravingScene } from "../engraving/EngravingScene";
import { PinPulled } from "../metaphor/PinPulled";
import { ChestsDestroyed } from "../metaphor/ChestsDestroyed";
import { ShieldNineVotes } from "../metaphor/ShieldNineVotes";
import { UIStamp } from "../ui/UIStamp";
import { DateClash } from "../chapters/DateClash";
import { MemorialsDuel } from "../chapters/MemorialsDuel";
import { ReplyCount } from "../chapters/ReplyCount";
import { TallyBoard, PresentInsertion } from "../chapters/TallyBoard";

/**
 * CP1 rough cut — CO + CH5 + CH7 aligned to the EN dry stems
 * (audio/tts_ep1/en, manifest_en.json, synth 2026-07-17; full track 24:45).
 *
 * Beat boundaries come from the manifest chunk starts (exact) and, inside
 * long chunks, from char-share interpolation (±2s scratch tolerance — the
 * sound_scratch_timing_ep1_v1.md contract locks only chapter cards and the
 * ~12–15 main hits, not every cut).
 *
 * Copy values are the v2-accepted script values (same source as the
 * D-package demos). PresentInsertion motion wording is typeset-approximate
 * pending the Producer claim_log pass — flagged in the checkpoint note.
 */

const AUDIO = {
  co: "the-moment/audio/sec_01_cold_open.wav",
  ch5: "the-moment/audio/sec_06_chapter_five_beijing_hits_the_brakes.wav",
  ch7: "the-moment/audio/sec_08_chapter_seven_nine_votes.wav",
} as const;

/** measured stem durations (ffprobe) */
export const CP1_SECTION_SECONDS = {
  co: 83.184,
  ch5: 193.891,
  ch7: 231.634,
} as const;

interface TimedBeat {
  /** absolute seconds from section start */
  from: number;
  to: number;
  name: string;
  node: React.ReactNode;
}

/** chapter card set over an engraving hero (CP3: C7-1 opens in the chamber) */
const ChapterOverlay: React.FC<{ kicker: string; title: string; subtitle?: string }> = ({
  kicker,
  title,
  subtitle,
}) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      textAlign: "center",
      backgroundColor: "rgba(28,24,18,0.34)",
    }}
  >
    <div style={{ fontFamily: TM.fontMono, fontSize: 30, letterSpacing: "0.3em", color: TM.paperHi, opacity: 0.85 }}>
      {kicker}
    </div>
    <div style={{ fontFamily: TM.fontHeading, fontWeight: 800, fontSize: 130, color: TM.paperHi, marginTop: 14, textShadow: "0 4px 22px rgba(28,24,18,0.6)" }}>
      {title}
    </div>
    {subtitle ? (
      <div style={{ fontFamily: TM.fontMono, fontSize: 27, letterSpacing: "0.14em", color: TM.paperHi, opacity: 0.8, marginTop: 18 }}>
        {subtitle}
      </div>
    ) : null}
  </div>
);

/* ------------------------------------------------------------------ */
/* Cold Open — 83.18s                                                  */
/* chunk starts: 0.00 / 23.69 / 25.84 / 35.90 / 67.03 / 79.55          */
/* ------------------------------------------------------------------ */

// CP3-N1 density recut (producer_cp3_correction_list §3, CEO ≤2 sentences/cut):
// CO 6 beats -> 12 perceptible states; sub-beat boundaries by char-share
// interpolation inside manifest chunks (±2s scratch tolerance holds).
const CO_BEATS: TimedBeat[] = [
  {
    from: 0,
    to: 4.9,
    name: "CO-1a a British warship off Nanking",
    node: (
      <EngravingScene
        src="the-moment/engravings/ship_hms_wellesley.jpg"
        kenBurns={{ scaleFrom: 1.3, scaleTo: 1.14, yFrom: -3, yTo: 0 }}
        duotone={0.9}
        sourceLabel="RMG PU5981 · public domain"
      >
        <UIDate date="AUG 1842" event="off Nanking" x={110} y={90} delay={4} />
      </EngravingScene>
    ),
  },
  {
    from: 4.9,
    to: 14.4,
    name: "CO-1b signing away — three stamps",
    node: (
      <EngravingScene
        src="the-moment/engravings/ship_hms_wellesley.jpg"
        kenBurns={{ scaleFrom: 1.5, scaleTo: 1.62, xFrom: -4, xTo: 3, yFrom: -4, yTo: -6 }}
        duotone={0.9}
        sourceLabel="RMG PU5981 · public domain"
      >
        <UIStamp kind="custom" text="FIVE PORTS" x={560} y={380} rotation={-9} delay={26} backing />
        <UIStamp kind="custom" text="HONG KONG" x={1030} y={560} rotation={5} delay={86} backing />
        <UIStamp
          kind="custom"
          text="21,000,000"
          subtext="SILVER DOLLARS"
          x={1440}
          y={760}
          rotation={-6}
          delay={150}
          backing
        />
      </EngravingScene>
    ),
  },
  {
    from: 14.4,
    to: 22.6,
    name: "CO-1c the textbook picture — treaty map",
    node: (
      // campaign route arcs animate HK→Amoy→Ningpo→Shanghai→Nanking
      // (route_arc P0; CEO CP2 feedback #1)
      <MapTreatyPorts title="Nanking — the treaty" date="AUG 1842" />
    ),
  },
  {
    // starts on the spoken "…Eighteen forty-two." so the 1842 plate is on
    // screen with the word, and the strike lands on "Wrong moment." at
    // 23.7s (CEO CP2 feedback #2: card was ~1s late)
    from: 22.6,
    to: 35.9,
    name: "CO-2 date clash 1842 → 1813",
    node: (
      <DateClash
        wrongYear="1842"
        wrongCaption="Nanking — the gunboats, the treaty"
        rightYear="1813"
        rightCaption="London — a vote about India"
      />
    ),
  },
  // CO-3 (was ONE 17.4s puppet scene — the CEO screenshot pain) -> proto
  // grammar promoted: 4 states, 1 sentence each (Proto1813Density S1–S4)
  {
    from: 35.9,
    to: 39.3,
    name: "CO-3a no fleet, no emperor",
    node: (
      <EngravingScene
        src="the-moment/engravings/ship_hms_wellesley.jpg"
        kenBurns={{ scaleFrom: 1.25, scaleTo: 1.12, yFrom: -2, yTo: 0 }}
        duotone={0.9}
        sourceLabel="RMG PU5981 · public domain"
      >
        <UIStamp kind="custom" text="NO FLEET" x={620} y={430} rotation={-10} delay={8} />
        <UIStamp kind="custom" text="NO EMPEROR" x={1240} y={640} rotation={6} delay={38} />
      </EngravingScene>
    ),
  },
  {
    from: 39.3,
    to: 45.5,
    name: "CO-3b a room of men in Westminster",
    node: (
      <EngravingScene
        src="the-moment/engravings/commons_house_1833.jpg"
        kenBurns={{ scaleFrom: 1.05, scaleTo: 1.28, yFrom: 0, yTo: -3 }}
        duotone={0.8}
        spotlight={{ xFrom: 560, xTo: 1340, y: 560, r: 620 }}
        sourceLabel="Hayter, The House of Commons 1833 · public domain"
      >
        <UIDate date="1813" event="a vote about India" x={110} y={90} delay={6} />
      </EngravingScene>
    ),
  },
  {
    from: 45.5,
    to: 49.3,
    name: "CO-3c couldn't find Canton",
    node: (
      <EngravingScene
        src="the-moment/engravings/commons_house_1833.jpg"
        kenBurns={{ scaleFrom: 1.6, scaleTo: 1.75, xFrom: 6, xTo: -4, yFrom: -6, yTo: -8 }}
        duotone={0.8}
        sourceLabel="Hayter, The House of Commons 1833 · public domain"
      >
        <UIStamp
          kind="custom"
          text="COULDN'T FIND CANTON"
          subtext="ON A MAP"
          x={960}
          y={780}
          rotation={-6}
          delay={20}
          backing
        />
      </EngravingScene>
    ),
  },
  {
    from: 49.3,
    to: 53.3,
    name: "CO-3d the first pin pulled",
    node: <PinPulled />,
  },
  {
    from: 53.3,
    to: 57.1,
    name: "CO-4a 27 years to come apart",
    node: <MapPearl title="The Pearl River — 27 years later" date="NOV 1839" />,
  },
  {
    from: 57.1,
    to: 67.03,
    name: "CO-4b shells falling on war junks",
    node: (
      <EngravingScene
        src="the-moment/engravings/ship_nemesis.jpg"
        kenBurns={{ scaleFrom: 1.08, scaleTo: 1.3, xFrom: 2, xTo: -3, yFrom: 1, yTo: -2 }}
        duotone={0.75}
        sourceLabel="E. Duncan, 1843 · public domain"
      >
        <UIDate date="BY THE END" event="Royal Navy shells on Chinese war junks" x={110} y={90} delay={10} />
      </EngravingScene>
    ),
  },
  {
    from: 67.03,
    to: 79.55,
    name: "CO-5 hold three dates",
    node: (
      <UIWire
        title="Hold three dates"
        beads={[
          { year: "1813", label: "a vote about India" },
          { year: "1834" },
          { year: "1840", label: "nine votes" },
        ]}
        beatFrames={50}
      />
    ),
  },
  {
    from: 79.55,
    to: CP1_SECTION_SECONDS.co,
    name: "CO-6 go find the vote",
    node: (
      <UIChapter
        kicker="THE MOMENT · EPISODE ONE"
        title="Let's go find the vote about India."
        weak
      />
    ),
  },
];

/* ------------------------------------------------------------------ */
/* CH5 — Beijing Hits the Brakes — 193.89s                             */
/* chunk starts: 0.00 / 53.49 / 86.40 / 145.49 / 170.89 / 173.26       */
/* ------------------------------------------------------------------ */

const XU_MEMORIAL = {
  year: "1836",
  author: "Xu Naiji",
  position: "Legalize it",
  points: [
    "You cannot stop this trade",
    "Tax it — keep the silver home",
    "Run the market instead of fighting it",
  ],
  accent: TM.qingBlue,
};

const HUANG_MEMORIAL = {
  year: "1838",
  author: "Huang Juezi",
  position: "Death penalty",
  points: [
    "One year for every smoker to quit",
    "After that — execution",
    "Aimed at demand itself",
  ],
  accent: TM.britishRed,
};

const CH5_BEATS: TimedBeat[] = [
  {
    from: 0,
    to: 11.2,
    name: "C5-1 chapter card",
    node: (
      <UIChapter
        kicker="CHAPTER FIVE"
        title="Beijing Hits the Brakes"
        subtitle="the half of the story London never tells"
      />
    ),
  },
  {
    from: 11.2,
    to: 24.0,
    name: "C5-2 banned for a century",
    // map-share batch 1 (night run 07-19): failing edicts drawn as map state
    // — BANNED plates strike and fade while the smuggling arrow keeps flowing
    node: <MapQingBans title="Banned for over a century" date="1729 · THE FIRST EDICT" />,
  },
  // C5-3 (was one 29.5s duel with an in-shot change) -> CP3-N1 hard split:
  // Xu solo / Huang solo / duel recap — cut points at the measured VO pause
  // (+15.35s) and the char-share estimate for the death-penalty payoff
  {
    from: 24.0,
    to: 39.35,
    name: "C5-3a Xu Naiji — legalize it",
    node: <MemorialsDuel solo="left" left={XU_MEMORIAL} right={HUANG_MEMORIAL} />,
  },
  {
    from: 39.35,
    to: 48.5,
    name: "C5-3b Huang Juezi — death penalty",
    node: <MemorialsDuel solo="right" left={XU_MEMORIAL} right={HUANG_MEMORIAL} />,
  },
  {
    from: 48.5,
    to: 53.49,
    name: "C5-3c two memorials, one desk",
    node: (
      <MemorialsDuel
        rightDelayFrames={10}
        title="TWO MEMORIALS · ONE DESK"
        left={XU_MEMORIAL}
        right={HUANG_MEMORIAL}
      />
    ),
  },
  {
    from: 53.49,
    to: 73.2,
    name: "C5-4 reply count 29:8",
    node: (
      // EN track carries EN-only copy — the ZH hedge belongs to the future
      // ZH-locale compose (producer diagnosis §1.1, CEO feedback #13)
      <ReplyCount
        total={29}
        minority={8}
        hedge="By the count historians usually give"
        minorityLabel="for the death penalty"
        majorityLabel="provincial replies"
        highlightLabel="Lin Zexu"
      />
    ),
  },
  {
    from: 73.2,
    to: 86.4,
    name: "C5-5 Lin quote (paraphrase)",
    node: (
      <UIQuote
        quote="Keep drifting like this, and in a few decades China will have almost no soldiers left fit to fight an enemy — and no silver left to pay them."
        attribution="Lin Zexu — memorial to the throne"
        context="1838"
        kind="paraphrase"
        tagText="WORDS TO THIS EFFECT"
        accent={TM.britishRed}
      />
    ),
  },
  {
    from: 86.4,
    to: 93.5,
    name: "C5-6a the emperor picks a side",
    node: (
      <UICompare
        title="THE EMPEROR PICKS A SIDE"
        leftTitle="Xu Naiji"
        rightTitle="Lin Zexu"
        leftItems={["the legalizer", "demoted into retirement"]}
        rightItems={["a commissioner's seal", "one mandate: end it"]}
        leftAccent={TM.inkFaint}
        rightAccent={TM.qingBlue}
      />
    ),
  },
  {
    // CP3-N1: the mandate gets its own state — W3 commissioner plate,
    // commanding pose (hybrid track Layer D)
    from: 93.5,
    to: 100.5,
    name: "C5-6b one mandate — end it",
    node: (
      <PaperBackground>
        <UIDate date="1838" event="a commissioner's seal" x={110} y={90} delay={4} />
        <CharPunch
          puppet="CHAR-COMMISSIONER-CN"
          pose="action"
          label="Lin Zexu — Imperial Commissioner"
          x={960}
          y={900}
          height={520}
          delay={8}
          idle={false}
        />
        <UIStamp kind="custom" text="END IT" x={1380} y={420} rotation={8} delay={34} />
        <UISchematic />
      </PaperBackground>
    ),
  },
  // C5-7 (was one 22.8s two-puppet hold) -> CP3-N1: engraving arrival /
  // the Iron-Headed Old Rat / the rat has fled
  {
    from: 100.5,
    to: 109.5,
    name: "C5-7a Lin reaches Canton",
    node: (
      <EngravingScene
        src="the-moment/engravings/canton_factories.jpg"
        kenBurns={{ scaleFrom: 1.06, scaleTo: 1.26, xFrom: -2, xTo: 2, yFrom: 0, yTo: -2 }}
        duotone={0.8}
        sourceLabel="W. Daniell, Canton factories · public domain"
      >
        <UIDate date="MAR 1839" event="Lin reaches Canton" x={110} y={90} delay={6} />
      </EngravingScene>
    ),
  },
  {
    from: 109.5,
    to: 117.5,
    name: "C5-7b the Iron-Headed Old Rat",
    node: (
      <SetShell set="SET-CANTON-FACTORY">
        <CharPunch
          puppet="CHAR-MERCHANT"
          pose="stand"
          label="Jardine — the Iron-Headed Old Rat"
          x={960}
          y={910}
          height={470}
          delay={8}
          idle={false}
        />
        <UISchematic />
      </SetShell>
    ),
  },
  {
    from: 117.5,
    to: 123.3,
    name: "C5-7c the rat had fled",
    node: (
      <SetShell set="SET-CANTON-FACTORY">
        <CharPunch
          puppet="CHAR-MERCHANT"
          pose="stand"
          x={1350}
          y={910}
          height={440}
          delay={0}
          idle={false}
          flip
        />
        <UIStamp
          kind="custom"
          text="SAILED FOR LONDON"
          subtext="JANUARY 1839"
          x={760}
          y={520}
          rotation={-8}
          delay={16}
          backing
        />
        <UISchematic />
      </SetShell>
    ),
  },
  {
    from: 123.3,
    to: 134.5,
    name: "C5-8a Humen — chests converge",
    // map-share batch 1: the seizure drawn as chests converging on Humen;
    // the 20,000+ ledger number survives as the corner plate
    node: <MapHumen title="Humen — destroyed in public" date="JUN 1839" />,
  },
  {
    // CP3-N1 Layer C metaphor #3: the destruction itself (示意非假史料)
    from: 134.5,
    to: 145.49,
    name: "C5-8b the stockpile destroyed",
    node: <ChestsDestroyed />,
  },
  // C5-9 (was one 27.8s map hold) -> route / the letter itself / the fate
  {
    from: 145.49,
    to: 152.5,
    name: "C5-9a a letter to Queen Victoria",
    node: <MapLetterRoute title="The letter to Queen Victoria" date="1839" />,
  },
  {
    from: 152.5,
    to: 162.5,
    name: "C5-9b what the letter said",
    node: (
      <UIQuote
        quote="Your country forbids opium at home — you know what this drug does. Why sell it to ours?"
        attribution="Lin Zexu — letter to Queen Victoria"
        context="1839 · the letter, in essence"
        kind="paraphrase"
        tagText="IN ESSENCE"
        accent={TM.qingBlue}
      />
    ),
  },
  {
    from: 162.5,
    to: 173.26,
    name: "C5-9c never delivered — a curiosity",
    node: (
      <MapLetterRoute
        title="Printed in the London papers — as a curiosity"
        date="NEVER DELIVERED"
      />
    ),
  },
  {
    from: 173.26,
    to: 184.5,
    name: "C5-10a two brakes, one clock",
    node: (
      <UICompare
        title="TWO BRAKES · ONE CLOCK"
        leftTitle="London"
        rightTitle="Beijing"
        leftItems={["tears its brake out", "1834"]}
        rightItems={["finally builds one", "1839 — six years later"]}
        leftAccent={TM.britishRed}
        rightAccent={TM.qingBlue}
        footnote="The problem was never the will. It was the clock."
      />
    ),
  },
  {
    from: 184.5,
    to: CP1_SECTION_SECONDS.ch5,
    name: "C5-10b one signature away",
    node: (
      <UIChapter
        kicker="ONE BRITISH SIGNATURE"
        title="law enforcement → a national debt"
        weak
      />
    ),
  },
];

/* ------------------------------------------------------------------ */
/* CH7 — Nine Votes — 231.63s                                          */
/* chunk starts: 0.00 / 35.01 / 41.53 / 46.61 / 226.78                 */
/* ------------------------------------------------------------------ */

const CH7_BEATS: TimedBeat[] = [
  {
    // CP3-N1 (producer §2.2 C7-1): chapter opens INSIDE the chamber —
    // Hayter plate as hero, chapter title set over it (age-down texture)
    from: 0,
    to: 9.6,
    name: "C7-1 chapter card — in the chamber",
    node: (
      <EngravingScene
        src="the-moment/engravings/commons_house_1833.jpg"
        kenBurns={{ scaleFrom: 1.04, scaleTo: 1.18, yFrom: 0, yTo: -2 }}
        duotone={0.9}
        sourceLabel="Hayter, The House of Commons 1833 · public domain"
      >
        <ChapterOverlay
          kicker="CHAPTER SEVEN"
          title="Nine Votes"
          subtitle="April 1840 · the House of Commons · three nights"
        />
      </EngravingScene>
    ),
  },
  // C7-2 (was one 25.4s hold on the compare card) -> semantic compare
  // stays (禁转 map), the stakes get their own state
  {
    from: 9.6,
    to: 21.5,
    name: "C7-2a censure ≠ war vote",
    node: (
      <UICensure note="If it passed, the government could fall — and take the expedition down with it." />
    ),
  },
  {
    from: 21.5,
    to: 35.01,
    name: "C7-2b if it passed — the stakes",
    node: (
      <EngravingScene
        src="the-moment/engravings/commons_house_1833.jpg"
        kenBurns={{ scaleFrom: 1.3, scaleTo: 1.48, xFrom: -3, xTo: 4, yFrom: -4, yTo: -6 }}
        duotone={0.8}
        spotlight={{ xFrom: 1200, xTo: 700, y: 560, r: 560 }}
        sourceLabel="Hayter, The House of Commons 1833 · public domain"
      >
        <UIStamp
          kind="custom"
          text="IF IT PASSED"
          subtext="THE GOVERNMENT COULD FALL"
          x={960}
          y={720}
          rotation={-7}
          delay={22}
          backing
        />
      </EngravingScene>
    ),
  },
  {
    from: 35.01,
    to: 46.61,
    name: "C7-3 division — 271 / 262",
    node: <TallyBoard noes={271} ayes={262} date="APRIL 1840" />,
  },
  // C7-4 (was one 22s two-puppet hold) -> shield metaphor / cornered
  // cabinet / Elliot's paper tips them in
  {
    // CP3-N1 Layer C metaphor #6: nine votes as the shield that held
    from: 46.61,
    to: 52.5,
    name: "C7-4a survived by nine votes",
    node: <ShieldNineVotes />,
  },
  {
    from: 52.5,
    to: 61.0,
    name: "C7-4b cornered, not bloodthirsty",
    node: (
      <SetShell set="SET-COMMONS">
        <UIDate date="1840" event="the Melbourne cabinet — cornered" x={110} y={90} delay={6} />
        <CharPunch puppet="CHAR-MP" pose="stand" x={720} y={900} height={420} delay={14} idle={false} />
        <CharPunch puppet="CHAR-MP" pose="stand" x={1200} y={900} height={420} delay={22} idle={false} flip />
        <UISchematic />
      </SetShell>
    ),
  },
  {
    from: 61.0,
    to: 68.6,
    name: "C7-4c Elliot's paper tipped them in",
    node: (
      <PaperBackground>
        <UIDate date="MONTHS OF HESITATION" event="ministers openly doubting" x={110} y={90} delay={4} />
        <UIStamp
          kind="custom"
          text="ELLIOT'S PAPER"
          subtext="THE ARITHMETIC TIPPED THEM IN"
          x={960}
          y={560}
          rotation={-5}
          delay={20}
          backing
        />
        <UISchematic />
      </PaperBackground>
    ),
  },
  {
    from: 68.6,
    to: 82.0,
    name: "C7-5 the attackers trembled",
    node: (
      <PaperBackground>
        <CharPunch
          puppet="CHAR-MP"
          pose="action"
          label="Sir James Graham — moved the censure"
          x={700}
          y={900}
          height={460}
          delay={6}
          idle={false}
        />
        <CharPunch
          puppet="CHAR-MP"
          pose="stand"
          label="Hogg — Company-aligned"
          x={1260}
          y={900}
          height={440}
          delay={18}
          idle={false}
          flip
        />
        <UISchematic />
      </PaperBackground>
    ),
  },
  {
    from: 82.0,
    to: 96.2,
    name: "C7-6 horror even to success",
    node: (
      <UIQuote
        quote="He looked with horror even to success — pushed by a ledger, shaking as they went."
        attribution="Hogg, from the floor"
        context="April 1840"
        kind="paraphrase"
        accent={TM.qingBlue}
      />
    ),
  },
  {
    from: 96.2,
    to: 116.0,
    name: "C7-7 the word 'present' inserted",
    node: (
      // wording per producer_cp1_checkpoint_ep1_20260718.md ruling #1 —
      // Hansard 1840-04-07 motion text verbatim; "present" hosts on "advisers"
      <PresentInsertion
        before="…on the part of her Majesty's"
        inserted="present"
        after="advisers…"
        note="inserted mid-debate — so the censure couldn't touch future policy, or the Tory ministers who'd run China before"
      />
    ),
  },
  // C7-8 (was one 20.5s big-number hold) -> what the motion dared not say /
  // the +20 arithmetic
  {
    from: 116.0,
    to: 126.5,
    name: "C7-8a nothing against the trade, nothing against the war",
    node: (
      <PaperBackground>
        <UIDate date="THE ENGINEERED MOTION" event="moral clauses cost merchant votes" x={110} y={90} delay={4} />
        <UIStamp
          kind="custom"
          text="THE OPIUM TRADE"
          subtext="NOT MENTIONED"
          x={620}
          y={480}
          rotation={-8}
          delay={14}
          backing
        />
        <UIStamp
          kind="custom"
          text="THE WAR ITSELF"
          subtext="NOT MENTIONED"
          x={1300}
          y={660}
          rotation={6}
          delay={64}
          backing
        />
        <UISchematic />
      </PaperBackground>
    ),
  },
  {
    from: 126.5,
    to: 136.5,
    name: "C7-8b the motion that dared not",
    node: (
      <UIBigNum
        kicker="THE ENGINEERED MOTION"
        value="+20"
        qualifier="votes it might have caught — had it dared denounce the war. The opposition preferred losing to that."
        accent={TM.inkSoft}
      />
    ),
  },
  {
    from: 136.5,
    to: 152.0,
    name: "C7-9 Gladstone, thirty",
    node: (
      <PaperBackground>
        <UIDate date="SECOND NIGHT" event="a sister addicted to laudanum at home" x={110} y={90} delay={6} />
        <CharPunch
          puppet="CHAR-MP"
          pose="action"
          label="William Gladstone, 30"
          x={960}
          y={900}
          height={500}
          delay={10}
          idle={false}
        />
        <UISchematic />
      </PaperBackground>
    ),
  },
  // C7-10 (was one 20.8s quote hold) -> the verbatim quote / both things
  // are true (sincere AND cleared by the party)
  {
    from: 152.0,
    to: 164.0,
    name: "C7-10a a war more unjust",
    node: (
      // verbatim per producer_cp1_checkpoint_ep1_20260718.md ruling #2
      // (Hansard vol. 53, cc. 818–20 — narration may compress, transcript may not)
      <UIQuote
        quote="A war more unjust in its origin, a war more calculated in its progress to cover this country with permanent disgrace, I do not know, and I have not read of."
        attribution="William Gladstone"
        context="Commons debate · second night, April 1840"
        kind="transcript"
        accent={TM.britishRed}
      />
    ),
  },
  {
    from: 164.0,
    to: 172.8,
    name: "C7-10b both things are true",
    node: (
      <PaperBackground>
        <CharPunch
          puppet="CHAR-MP"
          pose="stand"
          label="William Gladstone, 30"
          x={520}
          y={900}
          height={520}
          delay={0}
          idle={false}
        />
        <UIStamp kind="custom" text="EVERY WORD SINCERE" x={1280} y={380} rotation={-7} delay={12} backing />
        <UIStamp
          kind="custom"
          text="CLEARED BY THE PARTY"
          subtext="AMMUNITION IN THE OPERATION"
          x={1280}
          y={640}
          rotation={5}
          delay={52}
          backing
        />
        <UISchematic />
      </PaperBackground>
    ),
  },
  {
    from: 172.8,
    to: 200.0,
    name: "C7-11 the petition and the war plan",
    node: (
      <UICompare
        title="BEHIND THE NINE-VOTE SHIELD"
        leftTitle="The petition"
        rightTitle="The war plan"
        leftItems={[
          "\u201Ctrade can no longer be conducted in safety\u201D",
          "headed by William Jardine",
        ]}
        rightItems={[
          "which ports to take",
          "what size fleet",
          "what to write into the treaty",
        ]}
        leftAccent={TM.inkSoft}
        rightAccent={TM.britishRed}
        footnote="the same signature on both — Jardine, in Palmerston's office since autumn"
      />
    ),
  },
  // C7-12 (was one 26.8s quote hold) -> the anatomy / the same men
  {
    from: 200.0,
    to: 216.0,
    name: "C7-12a the Spectator's anatomy",
    node: (
      <UIQuote
        quote="Aristocrats eyeing commissions. Contractors. Shipowners. Lenders. And above all the opium merchants — assured their compensation could only be obtained by war."
        attribution="The Spectator"
        context="1840 · press comment"
        kind="paraphrase"
        accent={TM.opiumPurple}
      />
    ),
  },
  {
    from: 216.0,
    to: 226.78,
    name: "C7-12b the same men",
    node: (
      <PaperBackground>
        <CharPunch
          puppet="CHAR-MERCHANT"
          pose="stand"
          label="signing loyalty letters"
          x={700}
          y={900}
          height={450}
          delay={6}
          idle={false}
        />
        <CharPunch
          puppet="CHAR-TRADER"
          pose="action"
          label="holding Elliot's paper"
          x={1260}
          y={900}
          height={450}
          delay={20}
          idle={false}
          flip
        />
        <UIStamp kind="custom" text="THE SAME MEN" x={960} y={330} rotation={-6} delay={44} />
        <UISchematic />
      </PaperBackground>
    ),
  },
  {
    from: 226.78,
    to: CP1_SECTION_SECONDS.ch7,
    name: "C7-13 nine votes cashed it",
    node: (
      <UIBigNum
        kicker="PAPER ONLY A VICTORY COULD CASH"
        value="NINE VOTES"
        qualifier="cashed it"
        accent={TM.britishRed}
      />
    ),
  },
];

/* ------------------------------------------------------------------ */
/* assembly                                                            */
/* ------------------------------------------------------------------ */

const Watermark: React.FC<{ label: string; phase?: string }> = ({ label, phase = "CP1" }) => (
  <div
    style={{
      position: "absolute",
      right: 46,
      bottom: 40,
      fontFamily: TM.fontMono,
      fontSize: 22,
      letterSpacing: "0.12em",
      color: TM.inkSoft,
      opacity: 0.55,
      textAlign: "right",
      pointerEvents: "none",
    }}
  >
    {label} · {phase} ROUGH CUT · SCRATCH TIMING · NOT FOR PUBLISH
  </div>
);

const fmtTc = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
};

export const Cp1Section: React.FC<{
  audioSrc: string;
  beats: TimedBeat[];
  label: string;
  phase?: string;
}> = ({ audioSrc, beats, label, phase }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: TM.paper }}>
      {beats.map((b) => {
        const from = Math.round(b.from * fps);
        const dur = Math.max(1, Math.round(b.to * fps) - from);
        return (
          <Sequence key={b.name} from={from} durationInFrames={dur} name={b.name}>
            {b.node}
            {/* top-right: the only corner free of schematic badges, footnotes,
                margin lines and date pins across all CP1 beats */}
            <div
              style={{
                position: "absolute",
                right: 46,
                top: 40,
                fontFamily: TM.fontMono,
                fontSize: 22,
                letterSpacing: "0.1em",
                color: TM.inkSoft,
                opacity: 0.55,
                pointerEvents: "none",
                textAlign: "right",
              }}
            >
              {fmtTc(b.from)} · {b.name}
            </div>
          </Sequence>
        );
      })}
      <Audio src={staticFile(audioSrc)} />
      <BgmUnderVo label={label} />
      <EventSfx label={label} />
      <Watermark label={label} phase={phase} />
    </AbsoluteFill>
  );
};

export type { TimedBeat };

export const Cp1ColdOpen: React.FC = () => (
  <Cp1Section audioSrc={AUDIO.co} beats={CO_BEATS} label="CO" />
);
export const Cp1ChapterFive: React.FC = () => (
  <Cp1Section audioSrc={AUDIO.ch5} beats={CH5_BEATS} label="CH5" />
);
export const Cp1ChapterSeven: React.FC = () => (
  <Cp1Section audioSrc={AUDIO.ch7} beats={CH7_BEATS} label="CH7" />
);

export const cp1SectionFrames = (fps: number) => ({
  co: Math.round(CP1_SECTION_SECONDS.co * fps),
  ch5: Math.round(CP1_SECTION_SECONDS.ch5 * fps),
  ch7: Math.round(CP1_SECTION_SECONDS.ch7 * fps),
});

/** all three CP1 sections back-to-back (each stem carries its own tail pause) */
export const Cp1RoughCutReel: React.FC = () => {
  const { fps } = useVideoConfig();
  const f = cp1SectionFrames(fps);
  return (
    <AbsoluteFill style={{ backgroundColor: TM.paper }}>
      <Sequence from={0} durationInFrames={f.co} name="CO">
        <Cp1ColdOpen />
      </Sequence>
      <Sequence from={f.co} durationInFrames={f.ch5} name="CH5">
        <Cp1ChapterFive />
      </Sequence>
      <Sequence from={f.co + f.ch5} durationInFrames={f.ch7} name="CH7">
        <Cp1ChapterSeven />
      </Sequence>
    </AbsoluteFill>
  );
};

export const cp1ReelDuration = (fps: number): number => {
  const f = cp1SectionFrames(fps);
  return f.co + f.ch5 + f.ch7;
};
