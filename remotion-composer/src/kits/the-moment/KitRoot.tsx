import React from "react";
import { Composition } from "remotion";
import { KitDemoReel, KIT_DEMO_BEATS, kitDemoDurationInFrames } from "./demo/KitDemoReel";
import { DChapterReel, D_DEMO_BEATS, dChapterReelDuration } from "./demo/DChapterReel";
import {
  IdentDemoReel,
  IDENT_DEMO_BEATS,
  IdentTransitionMark,
  identDemoDuration,
} from "./demo/IdentDemoReel";
import { BrandIdent } from "./chapters/BrandIdent";
import { InkWashBed } from "./chapters/InkWashBed";

const FPS = 30;

const IdentIntroComp: React.FC = () => (
  <BrandIdent
    videoSrc="the-moment/ident_intro_wire.mp4"
    wordmark="THE MOMENT"
    subline="Episode One"
    revealAtSeconds={3.6}
  />
);

const IdentOutroComp: React.FC = () => (
  <BrandIdent
    videoSrc="the-moment/ident_outro_ledger_closes_trim.mp4"
    wordmark="THE MOMENT"
    subline="The ledger closes"
    revealAtSeconds={0.4}
  />
);

const slug = (s: string) =>
  s
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();

/**
 * Kit preview root — self-contained entry so the shared Root.tsx (owned by
 * the compose stage and currently mid-edit by another seat) stays untouched.
 * Usage:
 *   npx remotion still src/kits/the-moment/index.ts <comp-id> out.png
 *   npx remotion render src/kits/the-moment/index.ts kit-demo-reel out.mp4
 */
export const KitRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="kit-demo-reel"
        component={KitDemoReel}
        durationInFrames={kitDemoDurationInFrames(FPS)}
        fps={FPS}
        width={1920}
        height={1080}
      />
      {KIT_DEMO_BEATS.map((b, i) => {
        const Comp: React.FC = () => <>{b.node}</>;
        return (
          <Composition
            key={b.name}
            id={`kit-${String(i + 1).padStart(2, "0")}-${slug(b.name)}`}
            component={Comp}
            durationInFrames={Math.round(b.seconds * FPS)}
            fps={FPS}
            width={1920}
            height={1080}
          />
        );
      })}
      <Composition
        id="d-chapter-reel"
        component={DChapterReel}
        durationInFrames={dChapterReelDuration(FPS)}
        fps={FPS}
        width={1920}
        height={1080}
      />
      {D_DEMO_BEATS.map((b, i) => {
        const Comp: React.FC = () => <>{b.node}</>;
        return (
          <Composition
            key={b.name}
            id={`d-${String(i + 1).padStart(2, "0")}-${slug(b.name)}`}
            component={Comp}
            durationInFrames={Math.round(b.seconds * FPS)}
            fps={FPS}
            width={1920}
            height={1080}
          />
        );
      })}
      <Composition
        id="ident-demo-reel"
        component={IdentDemoReel}
        durationInFrames={identDemoDuration(FPS)}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="ident-intro"
        component={IdentIntroComp}
        durationInFrames={Math.round(5.5 * FPS)}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="ident-transition"
        component={IdentTransitionMark}
        durationInFrames={Math.round(5.5 * FPS)}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="ident-outro"
        component={IdentOutroComp}
        durationInFrames={Math.round(4.5 * FPS)}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="ident-inkwash-bed"
        component={InkWashBed}
        durationInFrames={Math.round(5.5 * FPS)}
        fps={FPS}
        width={1920}
        height={1080}
      />
      {IDENT_DEMO_BEATS.map((b, i) => {
        const Comp: React.FC = () => <>{b.node}</>;
        return (
          <Composition
            key={b.name}
            id={`ident-${String(i + 1).padStart(2, "0")}-${slug(b.name)}`}
            component={Comp}
            durationInFrames={Math.round(b.seconds * FPS)}
            fps={FPS}
            width={1920}
            height={1080}
          />
        );
      })}
    </>
  );
};
