import { feature } from "topojson-client";
import { geoMercator, geoNaturalEarth1, geoPath, GeoProjection } from "d3-geo";
import countries10m from "world-atlas/countries-10m.json";
import countries50m from "world-atlas/countries-50m.json";
import land10m from "world-atlas/land-10m.json";
import land50m from "world-atlas/land-50m.json";

/**
 * Geo helpers for Map L1 (Great War-style situation maps).
 *
 * Base data = world-atlas (Natural Earth, public domain) — satisfies ledger
 * R0-01 "Natural Earth PD 裁切" fallback. 10m resolution for regional maps
 * (Pearl River, China coast), 50m for world-scale triangle maps.
 * Modern boundaries — every map scene must carry the schematic disclaimer
 * (UISchematic), per R0-02 "示意非精确边界".
 */

type Topology = { objects: Record<string, unknown> };

const toFC = (topo: unknown, key: string): GeoJSON.FeatureCollection => {
  const fc = feature(topo as Topology, (topo as Topology).objects[key]);
  // land topology yields a single Feature; normalize to a collection
  return (fc as { type: string }).type === "FeatureCollection"
    ? (fc as GeoJSON.FeatureCollection)
    : { type: "FeatureCollection", features: [fc as GeoJSON.Feature] };
};

const COUNTRIES_10M = toFC(countries10m, "countries");
const COUNTRIES_50M = toFC(countries50m, "countries");
// land = coastlines only, no modern political borders — the default for
// historical situation maps (1830s scenes must not show modern boundaries)
const LAND_10M = toFC(land10m, "land");
const LAND_50M = toFC(land50m, "land");

export type Resolution = "10m" | "50m";
export type Dataset = "land" | "countries";

export const worldFeatures = (
  res: Resolution,
  dataset: Dataset = "countries"
): GeoJSON.FeatureCollection =>
  dataset === "land"
    ? res === "10m"
      ? LAND_10M
      : LAND_50M
    : res === "10m"
    ? COUNTRIES_10M
    : COUNTRIES_50M;

export interface MapView {
  /** [minLon, minLat, maxLon, maxLat] */
  bbox: [number, number, number, number];
  width: number;
  height: number;
  /** padding in px around the fitted bbox */
  padding?: number;
  kind?: "mercator" | "naturalEarth";
}

/** Build a projection fitted to a lon/lat bbox inside a width×height frame. */
export const makeProjection = (view: MapView): GeoProjection => {
  const { bbox, width, height, padding = 0, kind = "mercator" } = view;
  const proj = kind === "mercator" ? geoMercator() : geoNaturalEarth1();
  // Fit via MultiPoint corners: spherical polygons are winding-order
  // sensitive in d3-geo (a mis-wound ring selects the whole globe minus the
  // box — exactly the bug this replaced); points have no winding ambiguity.
  const frameGeom = {
    type: "MultiPoint",
    coordinates: [
      [bbox[0], bbox[1]],
      [bbox[2], bbox[1]],
      [bbox[2], bbox[3]],
      [bbox[0], bbox[3]],
    ],
  };
  proj.fitExtent(
    [
      [padding, padding],
      [width - padding, height - padding],
    ],
    frameGeom
  );
  return proj;
};

// ---------------------------------------------------------------------------
// Regional cropping.
//
// At regional zoom (Pearl River, China coast) projecting the raw world
// topology explodes: mainland rings run to ±800k px and d3's planar
// clip-extent mis-classifies the frame corners, filling the whole frame
// (verified empirically on the Pearl view). Cropping rings in lon/lat space
// BEFORE projecting keeps coordinates small and sidesteps d3 clipping
// entirely. Planar Sutherland–Hodgman is a fine approximation at these
// latitudes and any clip-edge artifacts sit outside the visible frame
// (margin ≥ 25% of the bbox).
// ---------------------------------------------------------------------------

type Ring = number[][];

const clipRingToBox = (
  ring: Ring,
  box: [number, number, number, number]
): Ring => {
  const [minX, minY, maxX, maxY] = box;
  type Edge = { inside: (p: number[]) => boolean; intersect: (a: number[], b: number[]) => number[] };
  const edges: Edge[] = [
    {
      inside: (p) => p[0] >= minX,
      intersect: (a, b) => [minX, a[1] + ((b[1] - a[1]) * (minX - a[0])) / (b[0] - a[0])],
    },
    {
      inside: (p) => p[0] <= maxX,
      intersect: (a, b) => [maxX, a[1] + ((b[1] - a[1]) * (maxX - a[0])) / (b[0] - a[0])],
    },
    {
      inside: (p) => p[1] >= minY,
      intersect: (a, b) => [a[0] + ((b[0] - a[0]) * (minY - a[1])) / (b[1] - a[1]), minY],
    },
    {
      inside: (p) => p[1] <= maxY,
      intersect: (a, b) => [a[0] + ((b[0] - a[0]) * (maxY - a[1])) / (b[1] - a[1]), maxY],
    },
  ];
  let output = ring;
  for (const edge of edges) {
    const input = output;
    output = [];
    for (let i = 0; i < input.length; i++) {
      const cur = input[i];
      const prev = input[(i + input.length - 1) % input.length];
      const curIn = edge.inside(cur);
      const prevIn = edge.inside(prev);
      if (curIn) {
        if (!prevIn) output.push(edge.intersect(prev, cur));
        output.push(cur);
      } else if (prevIn) {
        output.push(edge.intersect(prev, cur));
      }
    }
    if (output.length === 0) return [];
  }
  return output;
};

const cropGeometry = (
  geometry: { type: string; coordinates: unknown },
  box: [number, number, number, number]
): { type: string; coordinates: unknown } | null => {
  if (geometry.type === "Polygon") {
    const rings = (geometry.coordinates as Ring[])
      .map((r) => clipRingToBox(r, box))
      .filter((r) => r.length >= 3);
    return rings.length ? { type: "Polygon", coordinates: rings } : null;
  }
  if (geometry.type === "MultiPolygon") {
    const polys = (geometry.coordinates as Ring[][])
      .map((poly) => poly.map((r) => clipRingToBox(r, box)).filter((r) => r.length >= 3))
      .filter((poly) => poly.length > 0);
    return polys.length ? { type: "MultiPolygon", coordinates: polys } : null;
  }
  return null;
};

/** Regional = bbox narrower than 90° of longitude. */
export const isRegionalView = (view: MapView): boolean =>
  view.bbox[2] - view.bbox[0] < 90;

/**
 * Convert (cropped) polygon geometry to an SVG path via direct per-point
 * projection. Bypasses d3-geo's spherical resampling/clipping, which
 * mis-renders regionally cropped rings (verified: corner-to-corner diagonal
 * seam on the Pearl view). Safe exactly because the geometry was already
 * cropped to a small lon/lat box (no antimeridian/horizon crossings).
 */
export const geometryToPlanarPath = (
  proj: GeoProjection,
  geometry: { type: string; coordinates: unknown }
): string => {
  const ringToPath = (ring: Ring): string => {
    if (ring.length < 3) return "";
    const parts: string[] = [];
    for (let i = 0; i < ring.length; i++) {
      const p = proj([ring[i][0], ring[i][1]]);
      if (!p || !Number.isFinite(p[0]) || !Number.isFinite(p[1])) return "";
      parts.push(`${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`);
    }
    return parts.join("") + "Z";
  };
  const polys: Ring[][] =
    geometry.type === "Polygon"
      ? [geometry.coordinates as Ring[]]
      : geometry.type === "MultiPolygon"
      ? (geometry.coordinates as Ring[][])
      : [];
  return polys
    .map((poly) => poly.map(ringToPath).join(""))
    .join("");
};

/**
 * Features cropped for a view. World-scale views (bbox wider than 90°) pass
 * through untouched — d3 handles those fine and cropping would cut graticule
 * context. Regional views get lon/lat-space cropping with a 30% margin.
 */
export const featuresForView = (
  view: MapView,
  res: Resolution,
  dataset: Dataset = "countries"
): GeoJSON.FeatureCollection => {
  const fc = worldFeatures(res, dataset);
  const [minLon, minLat, maxLon, maxLat] = view.bbox;
  if (maxLon - minLon >= 90) return fc;
  const mx = (maxLon - minLon) * 0.3;
  const my = (maxLat - minLat) * 0.3;
  const box: [number, number, number, number] = [
    minLon - mx,
    minLat - my,
    maxLon + mx,
    maxLat + my,
  ];
  const features: GeoJSON.Feature[] = [];
  for (const f of fc.features) {
    const geom = cropGeometry(
      (f as { geometry: { type: string; coordinates: unknown } }).geometry,
      box
    );
    if (geom) {
      features.push({
        type: "Feature",
        geometry: geom,
        properties: (f as { properties?: unknown }).properties,
        ...( { id: (f as { id?: unknown }).id } as object),
      } as GeoJSON.Feature);
    }
  }
  return { type: "FeatureCollection", features };
};

export const pathGenerator = (proj: GeoProjection) => geoPath(proj);

/** Project a lon/lat point, returning [x, y] (NaN-safe). */
export const project = (proj: GeoProjection, lonLat: [number, number]): [number, number] => {
  const p = proj(lonLat);
  return p ?? [NaN, NaN];
};

/**
 * Frequently used places (lon, lat).
 * RULE (producer diagnosis 2026-07-18 §1.2): every MapMarker in a scene MUST
 * take its lonLat from this registry — no bare coordinate literals in scenes.
 * New entries carry a source note.
 */
export const PLACES = {
  london: [-0.13, 51.51] as [number, number],
  calcutta: [88.36, 22.57] as [number, number],
  bombay: [72.88, 19.08] as [number, number],
  canton: [113.26, 23.13] as [number, number],
  whampoa: [113.42, 23.09] as [number, number],
  boccaTigris: [113.6, 22.8] as [number, number],
  lintin: [113.8, 22.42] as [number, number],
  macao: [113.55, 22.19] as [number, number],
  hongkong: [114.17, 22.28] as [number, number],
  amoy: [118.09, 24.48] as [number, number],
  foochow: [119.3, 26.08] as [number, number],
  ningpo: [121.55, 29.87] as [number, number],
  shanghai: [121.47, 31.23] as [number, number],
  /** Chuenpi (穿鼻/沙角) — island/fort at the outer Bocca Tigris; the
   * Nov 1839 Volage/Hyacinth–Kuan Tien-pei engagement ("Battle of Chuenpi")
   * was fought in the anchorage off it. Point sits in the estuary channel. */
  chuenpi: [113.64, 22.75] as [number, number],
  /** RN position off Chuenpi, Nov 1839 — schematic water point SE of the
   * fort in the main estuary channel (approach from Macao roads). */
  chuenpiAnchorage: [113.7, 22.62] as [number, number],
  /** Nanking (Nanjing) on the Yangtze — where the 1842 treaty was signed
   * aboard HMS Cornwallis. */
  nanking: [118.78, 32.06] as [number, number],
  /** Industrial petition cities, 1813 charter fight (standard city coords). */
  manchester: [-2.24, 53.48] as [number, number],
  liverpool: [-2.99, 53.41] as [number, number],
  glasgow: [-4.25, 55.86] as [number, number],
  /** Peking (Beijing) — the court issuing the opium edicts. */
  peking: [116.4, 39.9] as [number, number],
  /** Humen (虎门) town/fort on the east bank of the Bocca Tigris — site of
   * the Jun 1839 public destruction of the surrendered chests. */
  humen: [113.64, 22.82] as [number, number],
  /** Cape of Good Hope — the "east of Africa" monopoly boundary marker. */
  capeGoodHope: [18.47, -34.36] as [number, number],
  /** Schematic open-water point in the South China Sea — arrow origin for
   * "smuggling keeps flowing" flows at country-scale zoom (not a real port). */
  southChinaSea: [117.5, 20.0] as [number, number],
} as const;
