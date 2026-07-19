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

/* ------------------------------------------------------------------ */
/* Cold Open — 83.18s                                                  */
/* chunk starts: 0.00 / 23.69 / 25.84 / 35.90 / 67.03 / 79.55          */
/* ------------------------------------------------------------------ */

const CO_BEATS: TimedBeat[] = [
  {
    from: 0,
    to: 22.6,
    name: "CO-1 textbook 1842 — Nanking treaty map",
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
  {
    from: 35.9,
    to: 53.3,
    name: "CO-3 Westminster — a room of men",
    node: (
      <SetShell set="SET-COMMONS">
        <UIDate date="1813" event="a vote about India" x={110} y={90} delay={6} />
        <CharPunch puppet="CHAR-MP" x={760} y={900} height={400} delay={14} idle={false} />
        <CharPunch puppet="CHAR-MP" x={1160} y={900} height={400} delay={20} idle={false} flip />
        <UISchematic />
      </SetShell>
    ),
  },
  {
    from: 53.3,
    to: 67.03,
    name: "CO-4 27 years later — shells on war junks",
    node: <MapPearl title="The Pearl River — 27 years later" date="NOV 1839" />,
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
  {
    from: 24.0,
    to: 53.49,
    name: "C5-3 two memorials, one desk",
    // §3.10 waveform fix (night run 07-19): Huang's plate holds until the
    // measured 1.03s VO pause at +15.35s (frame ≈ 460) — the 29.5s single
    // shot now carries an in-shot state change instead of a static duel
    node: (
      <MemorialsDuel
        rightDelayFrames={462}
        title="TWO MEMORIALS · ONE DESK"
        left={{
          year: "1836",
          author: "Xu Naiji",
          position: "Legalize it",
          points: [
            "You cannot stop this trade",
            "Tax it — keep the silver home",
            "Run the market instead of fighting it",
          ],
          accent: TM.qingBlue,
        }}
        right={{
          year: "1838",
          author: "Huang Juezi",
          position: "Death penalty",
          points: [
            "One year for every smoker to quit",
            "After that — execution",
            "Aimed at demand itself",
          ],
          accent: TM.britishRed,
        }}
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
    to: 100.5,
    name: "C5-6 the emperor picks a side",
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
    from: 100.5,
    to: 123.3,
    name: "C5-7 Lin reaches Canton — Jardine gone",
    node: (
      <SetShell set="SET-CANTON-FACTORY">
        <UIDate date="MAR 1839" event="Lin reaches Canton" x={110} y={90} delay={4} />
        <CharPunch
          puppet="CHAR-OFFICIAL-CN"
          label="Lin Zexu — Imperial Commissioner"
          x={700}
          y={910}
          height={430}
          delay={12}
          idle={false}
        />
        <CharPunch
          puppet="CHAR-MERCHANT"
          label="Jardine — sailed for London in January"
          x={1290}
          y={910}
          height={430}
          delay={26}
          idle={false}
          flip
        />
        <UISchematic />
      </SetShell>
    ),
  },
  {
    from: 123.3,
    to: 145.49,
    name: "C5-8 Humen — 20,000+ chests",
    // map-share batch 1: the seizure drawn as chests converging on Humen;
    // the 20,000+ ledger number survives as the corner plate
    node: <MapHumen title="Humen — destroyed in public" date="JUN 1839" />,
  },
  {
    from: 145.49,
    to: 173.26,
    name: "C5-9 the letter never delivered",
    // map-share batch 1: the letter's failed route drawn Canton→Cape→London
    // with the NEVER DELIVERED strike (replaces the abstract wire diagram)
    node: <MapLetterRoute title="The letter to Queen Victoria" date="1839" />,
  },
  {
    from: 173.26,
    to: CP1_SECTION_SECONDS.ch5,
    name: "C5-10 two brakes, one clock",
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
];

/* ------------------------------------------------------------------ */
/* CH7 — Nine Votes — 231.63s                                          */
/* chunk starts: 0.00 / 35.01 / 41.53 / 46.61 / 226.78                 */
/* ------------------------------------------------------------------ */

const CH7_BEATS: TimedBeat[] = [
  {
    from: 0,
    to: 9.6,
    name: "C7-1 chapter card",
    node: (
      <UIChapter
        kicker="CHAPTER SEVEN"
        title="Nine Votes"
        subtitle="April 1840 · the House of Commons · three nights"
      />
    ),
  },
  {
    from: 9.6,
    to: 35.01,
    name: "C7-2 censure ≠ war vote",
    node: (
      <UICensure note="If it passed, the government could fall — and take the expedition down with it." />
    ),
  },
  {
    from: 35.01,
    to: 46.61,
    name: "C7-3 division — 271 / 262",
    node: <TallyBoard noes={271} ayes={262} date="APRIL 1840" />,
  },
  {
    from: 46.61,
    to: 68.6,
    name: "C7-4 cornered, not bloodthirsty",
    node: (
      <SetShell set="SET-COMMONS">
        <UIDate date="1840" event="the Melbourne cabinet — cornered" x={110} y={90} delay={6} />
        <CharPunch puppet="CHAR-MP" x={760} y={900} height={400} delay={14} idle={false} />
        <CharPunch puppet="CHAR-MP" x={1160} y={900} height={400} delay={22} idle={false} flip />
        <UISchematic />
      </SetShell>
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
          label="Sir James Graham — moved the censure"
          x={700}
          y={900}
          height={440}
          delay={6}
          idle={false}
        />
        <CharPunch
          puppet="CHAR-MP"
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
  {
    from: 116.0,
    to: 136.5,
    name: "C7-8 the motion that dared not",
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
          label="William Gladstone, 30"
          x={960}
          y={900}
          height={480}
          delay={10}
          idle={false}
        />
        <UISchematic />
      </PaperBackground>
    ),
  },
  {
    from: 152.0,
    to: 172.8,
    name: "C7-10 a war more unjust",
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
  {
    from: 200.0,
    to: 226.78,
    name: "C7-12 the Spectator's anatomy",
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
