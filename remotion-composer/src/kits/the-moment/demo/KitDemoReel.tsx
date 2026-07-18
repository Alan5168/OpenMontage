import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { UIChapter } from "../ui/UIChapter";
import { UIDate } from "../ui/UIDate";
import { UIBigNum } from "../ui/UIBigNum";
import { UICensure } from "../ui/UICensure";
import { UICompare } from "../ui/UICompare";
import { UIStamp } from "../ui/UIStamp";
import { UISchematic } from "../ui/UISchematic";
import { UIWire } from "../ui/UIWire";
import { UIQuote } from "../ui/UIQuote";
import { UISectionPause } from "../ui/UISectionPause";
import { MapPearl, MapTriangle, MapCantonApproach, MapTreatyPorts } from "../map/scenes";
import { CharPunch } from "../char/CharPunch";
import { SetShell } from "../set/sets";
import { PaperBackground } from "../paper/PaperBackground";

/**
 * KitDemoReel — R1 kit A–C review render.
 * ALL COPY BELOW IS SAMPLE TEXT for component QA only (script v2 in flight);
 * the persistent watermark makes this unpublishable by construction.
 */

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
      textAlign: "right",
      lineHeight: 1.5,
      pointerEvents: "none",
    }}
  >
    R1 KIT PREVIEW · SAMPLE COPY · NOT FOR PUBLISH
  </div>
);

interface Beat {
  name: string;
  seconds: number;
  node: React.ReactNode;
}

export const KIT_DEMO_BEATS: Beat[] = [
  {
    name: "UI-CHAPTER (EN)",
    seconds: 3.2,
    node: (
      <UIChapter
        kicker="CHAPTER 6 — SAMPLE"
        title="Nine Votes"
        subtitle="sample subtitle slot"
      />
    ),
  },
  {
    name: "UI-CHAPTER (ZH weak)",
    seconds: 2.6,
    node: <UIChapter title="样例·冷开场弱标" locale="zh" weak />,
  },
  {
    name: "UI-DATE",
    seconds: 2.6,
    node: (
      <PaperBackground>
        <UIDate date="22 APRIL 1834" event="sample event line" x={620} y={420} />
      </PaperBackground>
    ),
  },
  {
    name: "UI-BIG-NUM (qualifier)",
    seconds: 3.0,
    node: (
      <UIBigNum
        kicker="SAMPLE · N3"
        value="38,000,000"
        qualifier="taels — qualifier slot (sample)"
        accent={TM.opiumPurple}
      />
    ),
  },
  {
    name: "UI-BIG-NUM (tally)",
    seconds: 3.0,
    node: (
      <UIBigNum
        kicker="SAMPLE TALLY"
        value="271"
        qualifier="Noes"
        valueRight="262"
        qualifierRight="Ayes"
      />
    ),
  },
  {
    name: "UI-CENSURE",
    seconds: 3.6,
    node: <UICensure note="sample clarifier line" />,
  },
  {
    name: "UI-COMPARE",
    seconds: 4.0,
    node: (
      <UICompare
        title="SAMPLE COMPARE"
        leftTitle="Proposal"
        rightTitle="Treaty"
        leftItems={["Item one", "Item two", "Item three"]}
        rightItems={["Port A", "Port B", "Port C"]}
        ties={[
          [0, 0],
          [2, 1],
        ]}
        footnote="alignment ties only — no causal arrows by design"
      />
    ),
  },
  {
    name: "UI-STAMP ×3",
    seconds: 3.4,
    node: (
      <PaperBackground>
        <div
          style={{
            position: "absolute",
            top: 250,
            width: "100%",
            textAlign: "center",
            fontFamily: TM.fontHeading,
            fontSize: 60,
            color: TM.inkFaint,
          }}
        >
          sample list target
        </div>
        <UIStamp kind="rejected" x={640} y={430} delay={5} />
        <UIStamp kind="not-yet" x={1180} y={560} rotation={8} delay={20} />
        <UIStamp kind="counterfactual" x={900} y={740} rotation={-6} delay={35} />
      </PaperBackground>
    ),
  },
  {
    name: "UI-QUOTE",
    seconds: 3.6,
    node: (
      <UIQuote
        quote="Sample quotation text — typeset card, never a facsimile."
        attribution="Sample Speaker"
        context="sample context, 1833"
        kind="paraphrase"
      />
    ),
  },
  {
    name: "UI-SECTION-PAUSE",
    seconds: 1.5,
    node: <UISectionPause />,
  },
  {
    name: "UI-WIRE",
    seconds: 4.6,
    node: (
      <UIWire
        title="sample wire — years reversed"
        beads={[
          { year: "1874" },
          { year: "1858" },
          { year: "1842" },
          { year: "1840", label: "sample label" },
          { year: "1834" },
          { year: "1833" },
          { year: "1813" },
        ]}
      />
    ),
  },
  {
    name: "MAP-PEARL",
    seconds: 4.6,
    node: <MapPearl title="Pearl River Mouth — sample" date="NOV 1839" />,
  },
  {
    name: "MAP-INDIA-CN-UK",
    seconds: 5.4,
    node: <MapTriangle title="The Triangle — sample" date="1813–1833" />,
  },
  {
    name: "MAP-CANTON-APPROACH",
    seconds: 4.2,
    node: <MapCantonApproach step={2} />,
  },
  {
    name: "MAP-TREATY-PORTS",
    seconds: 4.6,
    node: <MapTreatyPorts title="Five Ports — sample" date="AUG 1842" />,
  },
  {
    name: "CHAR line-up 1",
    seconds: 4.0,
    node: (
      <PaperBackground>
        <CharPunch puppet="CHAR-MP" label="M.P. (sample)" x={420} y={860} height={500} delay={0} />
        <CharPunch puppet="CHAR-MERCHANT" label="Private trader" x={860} y={860} height={500} delay={8} />
        <CharPunch puppet="CHAR-CLERK" label="Clerk" x={1300} y={860} height={500} delay={16} />
        <UISchematic />
      </PaperBackground>
    ),
  },
  {
    name: "CHAR line-up 2",
    seconds: 4.0,
    node: (
      <PaperBackground>
        <CharPunch puppet="CHAR-SAILOR" label="R.N. rating" x={420} y={860} height={500} delay={0} />
        <CharPunch puppet="CHAR-OFFICIAL-CN" label="Qing official" x={860} y={860} height={500} delay={8} />
        <CharPunch puppet="CHAR-FARMER" label="Taxpayer" x={1300} y={860} height={500} delay={16} />
        <UISchematic />
      </PaperBackground>
    ),
  },
  {
    name: "CHAR-COMPANY emblem",
    seconds: 3.2,
    node: (
      <PaperBackground>
        <CharPunch puppet="CHAR-COMPANY" label="The Company (emblem)" x={960} y={840} height={560} idle={false} />
        <UISchematic />
      </PaperBackground>
    ),
  },
  {
    name: "SET-COMMONS + punch",
    seconds: 4.2,
    node: (
      <SetShell set="SET-COMMONS">
        <CharPunch puppet="CHAR-MP" x={960} y={900} height={380} delay={20} idle={false} />
        <UISchematic />
      </SetShell>
    ),
  },
  {
    name: "SET-LEDGER",
    seconds: 3.4,
    node: (
      <SetShell set="SET-LEDGER">
        <UISchematic />
      </SetShell>
    ),
  },
  {
    name: "SET-CANTON-FACTORY",
    seconds: 3.4,
    node: (
      <SetShell set="SET-CANTON-FACTORY">
        <UISchematic />
      </SetShell>
    ),
  },
  {
    name: "SET-CALCUTTA-AUCTION",
    seconds: 3.4,
    node: (
      <SetShell set="SET-CALCUTTA-AUCTION">
        <UISchematic />
      </SetShell>
    ),
  },
  {
    name: "SET-DECK",
    seconds: 3.4,
    node: (
      <SetShell set="SET-DECK">
        <UISchematic />
      </SetShell>
    ),
  },
  {
    name: "SET-MAP-TABLE",
    seconds: 3.4,
    node: (
      <SetShell set="SET-MAP-TABLE">
        <UISchematic />
      </SetShell>
    ),
  },
  {
    name: "End card",
    seconds: 2.6,
    node: (
      <UIChapter
        kicker='"THE MOMENT" KIT'
        title="R1 Kit A–C Preview"
        subtitle="UI kit · Map L1 · Char/Set shells — 2026-07-17"
        weak
      />
    ),
  },
];

export const kitDemoDurationInFrames = (fps: number): number =>
  KIT_DEMO_BEATS.reduce((acc, b) => acc + Math.round(b.seconds * fps), 0);

export const KitDemoReel: React.FC = () => {
  const { fps } = useVideoConfig();
  let cursor = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: TM.paper }}>
      {KIT_DEMO_BEATS.map((b) => {
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
