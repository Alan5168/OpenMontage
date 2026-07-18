// Kit-local ambient declarations.
// d3-geo / topojson-client ship no types and the repo intentionally avoids
// adding @types packages while another seat has package.json in flight.
// Only the surface used by this kit is declared, loosely typed.

declare module "topojson-client" {
  export function feature(topology: unknown, object: unknown): GeoJSON.FeatureCollection | GeoJSON.Feature;
  export function mesh(topology: unknown, object: unknown, filter?: (a: unknown, b: unknown) => boolean): GeoJSON.MultiLineString;
}

declare module "d3-geo" {
  export interface GeoProjection {
    (point: [number, number]): [number, number] | null;
    fitExtent(extent: [[number, number], [number, number]], object: unknown): GeoProjection;
    fitSize(size: [number, number], object: unknown): GeoProjection;
    clipExtent(extent: [[number, number], [number, number]] | null): GeoProjection;
    scale(scale?: number): GeoProjection & number;
    translate(point?: [number, number]): GeoProjection & [number, number];
    center(point?: [number, number]): GeoProjection & [number, number];
    rotate(angles?: [number, number] | [number, number, number]): GeoProjection;
    precision(precision?: number): GeoProjection & number;
  }
  export function geoMercator(): GeoProjection;
  export function geoNaturalEarth1(): GeoProjection;
  export function geoEquirectangular(): GeoProjection;
  export function geoPath(projection?: GeoProjection): (object: unknown) => string | null;
  export function geoGraticule10(): unknown;
}

declare module "world-atlas/countries-10m.json" {
  const topology: unknown;
  export default topology;
}

declare module "world-atlas/countries-50m.json" {
  const topology: unknown;
  export default topology;
}

declare module "world-atlas/land-10m.json" {
  const topology: unknown;
  export default topology;
}

declare module "world-atlas/land-50m.json" {
  const topology: unknown;
  export default topology;
}

declare namespace GeoJSON {
  interface Feature {
    type: "Feature";
    geometry: unknown;
    properties?: unknown;
  }
  interface FeatureCollection {
    type: "FeatureCollection";
    features: Feature[];
  }
  interface MultiLineString {
    type: "MultiLineString";
    coordinates: number[][][];
  }
}
