import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { DateClash } from "../chapters/DateClash";
import { ExecutionDate } from "../chapters/ExecutionDate";
import { MemorialsDuel } from "../chapters/MemorialsDuel";
import { ReplyCount } from "../chapters/ReplyCount";
import { NeverDelivered } from "../chapters/NeverDelivered";
import { PersonVsFirm } from "../chapters/PersonVsFirm";
import { FourReadings } from "../chapters/FourReadings";
import { TallyBoard, PresentInsertion } from "../chapters/TallyBoard";
import { WinnersRotation, WinnerItem } from "../chapters/WinnersRotation";
import { NapierFiveCut } from "../chapters/NapierFiveCut";
import { UIQuote } from "../ui/UIQuote";

/**
 * D-package review reel — chapter-specialized scenes with v2-accepted copy.
 * Values come from the SCRIPT_ACCEPTED_V2 text/claim log; exact motion
 * wording for PresentInsertion is typeset-approximate pending Producer
 * confirmation at compose. Watermarked — still a preview, not a publish.
 */

export const D_DEMO_PROPS = {
  dateClash: {
    wrongYear: "1842",
    wrongCaption: "Nanking — the gunboats, the treaty",
    rightYear: "1813",
    rightCaption: "London — a vote about India",
  },
  executionDate: {
    lawLine: "The Act of 1833 — the China monopoly's death warrant",
    date: "22 APRIL 1834",
    fromYear: "1833",
    toYear: "1834",
  },
  memorials: {
    title: "TWO MEMORIALS · ONE DESK",
    left: {
      year: "1836",
      author: "Xu Naiji",
      position: "Legalize it",
      points: ["You cannot stop this trade", "Tax it — keep the silver home", "Run the market instead of fighting it"],
      accent: TM.qingBlue,
    },
    right: {
      year: "1838",
      author: "Huang Juezi",
      position: "Death penalty",
      points: ["One year for every smoker to quit", "After that — execution", "Aimed at demand itself"],
      accent: TM.britishRed,
    },
  },
  // hedge is EN-only: EN/ZH are independent tracks, never bilingual on one
  // screen (producer diagnosis 2026-07-18 §1.1)
  replyCount: {
    total: 29,
    minority: 8,
    hedge: "By the count historians usually give",
    minorityLabel: "for the death penalty",
    majorityLabel: "provincial replies",
    highlightLabel: "Lin Zexu",
  },
  linQuote: {
    quote:
      "Keep drifting like this, and in a few decades China will have almost no soldiers left fit to fight an enemy — and no silver left to pay them.",
    attribution: "Lin Zexu — memorial to the throne",
    context: "1838",
    kind: "paraphrase" as const,
    tagText: "WORDS TO THIS EFFECT",
    accent: TM.britishRed,
  },
  neverDelivered: {
    fromLabel: "Canton — Commissioner Lin",
    toLabel: "Queen Victoria",
    endLabel: "London papers — a curiosity",
    stampText: "NEVER DELIVERED",
  },
  fourReadings: {
    n1: {
      kicker: "N1 · PRICE",
      dateBand: "early 1820s → 1838",
      headline: "collapse ~70%",
      sub: "Patna, per chest, benchmark series",
      from: "$2,500",
      to: "<$600",
    },
    n2: {
      kicker: "N2 · VOLUME",
      dateBand: "last 5 years before the war",
      headline: "roughly ×2",
      fromVal: 22,
      toVal: 40,
      fromLabel: "22,000",
      toLabel: "40,000 chests",
    },
    n3: {
      kicker: "N3 · SILVER",
      dateBand: "8 years, British accounts",
      headline: "$38,000,000",
      sub: "net outflow from China",
    },
    n4: {
      kicker: "N4 · EXCHANGE",
      dateBand: "old parity → late 1830s",
      headline: "taxes up ~half",
      sub: "no decree — the exchange rate did it",
      fromRate: "1 : 1,000",
      toRate: "1 : 1,600",
    },
  },
  tally: {
    noes: 271,
    ayes: 262,
    date: "APRIL 1840",
  },
  // wording corrected per producer_cp1_checkpoint_ep1_20260718.md ruling #1
  // (Hansard 1840-04-07 motion verbatim; "present" hosts on "advisers")
  present: {
    before: "…on the part of her Majesty's",
    inserted: "present",
    after: "advisers…",
    note: "inserted mid-debate — so the censure couldn't touch future policy, or the Tory ministers who'd run China before",
  },
  winners: [
    {
      kind: "compare",
      title: "Jardine Matheson",
      leftTitle: "The proposal",
      rightTitle: "The treaty",
      rows: [
        ["Which ports to take", "Five ports open"],
        ["An island base", "Hong Kong ceded"],
        ["Costs charged to China", "21M silver dollars"],
      ],
    },
    {
      kind: "notyet",
      title: "The internet's list — mostly fake",
      names: [
        { name: "HSBC", founded: "FOUNDED 1865" },
        { name: "Swire", founded: "SHANGHAI 1866" },
      ],
    },
    {
      kind: "lifespan",
      title: "Dent & Company",
      events: [
        { year: "1842", text: "victory buys a boom" },
        { year: "1850s", text: "Jardine's great rival" },
        { year: "1866", text: "gone" },
      ],
      terminal: "dragged down by a London banking collapse — a generation, not immortality",
    },
    {
      kind: "bignum",
      title: "The biggest winner never left London",
      value: "£3,660,000",
      qualifier: "tea revenue to the Exchequer in a single year — Graham, to the Commons",
    },
    {
      kind: "forecast",
      title: "Manchester — the loudest lobby, lost",
      promise: "\u201C400,000,000 customers\u201D",
      outcome: "The customers never came. China wove its own cotton — the bonanza was a mirage.",
    },
  ] as WinnerItem[],
  personVsFirm: {
    personTitle: "The man",
    personName: "William Jardine",
    personEvents: [
      { year: "—", text: "farm boy from Lochmaben; east at 19 with a surgeon's kit" },
      { year: "1841", text: "elected MP for Ashburton" },
      { year: "1843", text: "dead of cancer — three days past his 59th birthday; never married" },
    ],
    firmTitle: "The firm — another story",
    firmName: "Jardine Matheson",
    firmEvents: [
      { year: "1832", text: "founded at Canton" },
      { year: "1841", text: "land at Hong Kong's first auctions; HQ moves" },
      { year: "today", text: "still trades — under the borrowed name \u201CEwo\u201D" },
    ],
    divider: "The firm is another story.",
  },
};

const Watermark: React.FC = () => (
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
      pointerEvents: "none",
    }}
  >
    D PACKAGE PREVIEW · NOT FOR PUBLISH
  </div>
);

interface Beat {
  name: string;
  seconds: number;
  node: React.ReactNode;
}

export const D_DEMO_BEATS: Beat[] = [
  { name: "CO date clash", seconds: 4.0, node: <DateClash {...D_DEMO_PROPS.dateClash} /> },
  { name: "CH2 execution date", seconds: 4.0, node: <ExecutionDate {...D_DEMO_PROPS.executionDate} /> },
  { name: "CH3 Napier five-cut", seconds: 17.0, node: <NapierFiveCut totalSeconds={17} /> },
  { name: "CH4 four readings", seconds: 6.5, node: <FourReadings {...D_DEMO_PROPS.fourReadings} /> },
  { name: "CH5 memorials duel", seconds: 4.6, node: <MemorialsDuel {...D_DEMO_PROPS.memorials} /> },
  { name: "CH5 reply count 29:8", seconds: 5.4, node: <ReplyCount {...D_DEMO_PROPS.replyCount} /> },
  { name: "CH5 Lin quote card", seconds: 4.0, node: <UIQuote {...D_DEMO_PROPS.linQuote} /> },
  { name: "CH5 never delivered", seconds: 6.0, node: <NeverDelivered {...D_DEMO_PROPS.neverDelivered} /> },
  { name: "CH7 tally board", seconds: 5.0, node: <TallyBoard {...D_DEMO_PROPS.tally} /> },
  { name: "CH7 present insertion", seconds: 4.0, node: <PresentInsertion {...D_DEMO_PROPS.present} /> },
  { name: "CH8 winners rotation", seconds: 25.0, node: <WinnersRotation items={D_DEMO_PROPS.winners} secondsPerItem={5} /> },
  { name: "CH8 person vs firm", seconds: 6.0, node: <PersonVsFirm {...D_DEMO_PROPS.personVsFirm} /> },
];

export const dChapterReelDuration = (fps: number): number =>
  D_DEMO_BEATS.reduce((acc, b) => acc + Math.round(b.seconds * fps), 0);

export const DChapterReel: React.FC = () => {
  const { fps } = useVideoConfig();
  let cursor = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: TM.paper }}>
      {D_DEMO_BEATS.map((b) => {
        const from = cursor;
        const dur = Math.round(b.seconds * fps);
        cursor += dur;
        return (
          <Sequence key={b.name} from={from} durationInFrames={dur} name={b.name}>
            {b.node}
            <div
              style={{
                position: "absolute",
                left: 46,
                bottom: 40,
                fontFamily: TM.fontMono,
                fontSize: 22,
                letterSpacing: "0.1em",
                color: TM.inkSoft,
                opacity: 0.55,
              }}
            >
              {b.name}
            </div>
          </Sequence>
        );
      })}
      <Watermark />
    </AbsoluteFill>
  );
};
