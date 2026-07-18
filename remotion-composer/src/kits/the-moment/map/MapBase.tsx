import React, { useMemo } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";
import { GeoProjection } from "d3-geo";
import {
  MapView,
  makeProjection,
  pathGenerator,
  featuresForView,
  geometryToPlanarPath,
  isRegionalView,
  Resolution,
  Dataset,
} from "./geo";

export interface MapBaseProps {
  view: MapView;
  resolution?: Resolution;
  /**
   * "land" (default) = coastlines only — correct for 1830s situation maps.
   * "countries" adds modern political borders; only for deliberately
   * present-day framings, never as implied historical borders.
   */
  dataset?: Dataset;
  /** slow ken-burns-like scale drift; keep tiny (situation map, not cinema) */
  drift?: boolean;
  children?: (proj: GeoProjection) => React.ReactNode;
}

/**
 * Map L1 base — flat paper-tone landmass + ink coastlines.
 * Explicitly NOT GIS-photoreal (grammar_stack Layer M: 灰白/纸色简化).
 * Children render-prop receives the fitted projection so markers/arrows/
 * regions share the same coordinate space.
 */
export const MapBase: React.FC<MapBaseProps> = ({
  view,
  resolution = "10m",
  dataset = "land",
  drift = true,
  children,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const proj = useMemo(() => makeProjection(view), [view]);
  const path = useMemo(() => pathGenerator(proj), [proj]);
  const world = useMemo(
    () => featuresForView(view, resolution, dataset),
    [view, resolution, dataset]
  );

  // Regional views: geometry is pre-cropped in lon/lat, so project points
  // directly (d3's spherical pipeline draws seam artifacts on cropped rings).
  // World views: use d3-geo's path with its proper spherical clipping.
  const regional = isRegionalView(view);
  const landPaths = useMemo(
    () =>
      world.features
        .map((f) =>
          regional
            ? geometryToPlanarPath(
                proj,
                (f as { geometry: { type: string; coordinates: unknown } }).geometry
              )
            : path(f) ?? ""
        )
        .filter(Boolean),
    [world, path, proj, regional]
  );

  const scale = drift
    ? interpolate(frame, [0, durationInFrames], [1, 1.035], {
        extrapolateRight: "clamp",
      })
    : 1;

  return (
    <PaperBackground>
      <AbsoluteFill style={{ transform: `scale(${scale})` }}>
        <svg width={view.width} height={view.height}>
          {landPaths.map((d, i) => (
            <path
              key={i}
              d={d}
              fill={TM.paperLo}
              // evenodd: winding-independent fill — regional crops and d3 clip
              // output can emit rings whose direction breaks nonzero in Chrome
              // (verified: whole-frame fill on the Pearl view).
              fillRule="evenodd"
              stroke={TM.inkSoft}
              strokeWidth={2.2}
              strokeLinejoin="round"
            />
          ))}
          {children ? children(proj) : null}
        </svg>
      </AbsoluteFill>
    </PaperBackground>
  );
};
