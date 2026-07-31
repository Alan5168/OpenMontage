import React from "react";
import { Composition } from "remotion";
import { Cp1ColdOpenTriptych, triptychDemoDuration } from "./compose/TriptychColdOpen";

const FPS = 30;

/**
 * Isolated Root for the CP3 Triptych A/B demo (NF_DIRECTOR, 2026-07-20).
 * Kept OUT of KitRoot.tsx so the main kit registry (and the shipped cp1-co)
 * stays untouched — new + old coexist for the CEO comparison.
 *
 *   npx remotion render src/kits/the-moment/KitRoot.triptych-demo.tsx \
 *     cp1-co-triptych-demo out.mp4 --frames=0-1799
 */
export const TriptychDemoRoot: React.FC = () => (
  <Composition
    id="cp1-co-triptych-demo"
    component={Cp1ColdOpenTriptych}
    durationInFrames={triptychDemoDuration(FPS)}
    fps={FPS}
    width={1920}
    height={1080}
  />
);
