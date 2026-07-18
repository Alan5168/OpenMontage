import React, { useMemo } from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { GeoProjection } from "d3-geo";
import { TM } from "../theme";
import { pathGenerator, worldFeatures, Resolution } from "./geo";

export interface MapRegionProps {
  proj: GeoProjection;
  /** ISO numeric country ids to tint, e.g. ["156"] China, ["356"] India */
  countryIds: string[];
  color: string;
  /** fill opacity target */
  opacity?: number;
  delay?: number;
  duration?: number;
  resolution?: Resolution;
  /** hatched = claimed/contested rather than solid control */
  hatched?: boolean;
}

/**
 * Map region tint — status color block over country shapes
 * (monopoly zone / open zone / control). Modern borders, so pair the scene
 * with UISchematic("SCHEMATIC · NOT EXACT BORDERS") per ledger R0-02.
 */
export const MapRegion: React.FC<MapRegionProps> = ({
  proj,
  countryIds,
  color,
  opacity = 0.35,
  delay = 0,
  duration = 24,
  resolution = "50m",
  hatched = false,
}) => {
  const frame = useCurrentFrame();
  const path = useMemo(() => pathGenerator(proj), [proj]);
  const world = worldFeatures(resolution);

  const ds = useMemo(
    () =>
      world.features
        .filter((f) => countryIds.includes(String((f as { id?: unknown }).id ?? "")))
        .map((f) => path(f) ?? "")
        .filter(Boolean),
    [world, countryIds, path]
  );

  const t = interpolate(frame - delay, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <g opacity={t * opacity}>
      {hatched && (
        <defs>
          <pattern
            id={`tm-hatch-${color.replace(/[^a-zA-Z0-9]/g, "")}`}
            width={14}
            height={14}
            patternTransform="rotate(45)"
            patternUnits="userSpaceOnUse"
          >
            <line x1={0} y1={0} x2={0} y2={14} stroke={color} strokeWidth={5} />
          </pattern>
        </defs>
      )}
      {ds.map((d, i) => (
        <path
          key={i}
          d={d}
          fill={
            hatched
              ? `url(#tm-hatch-${color.replace(/[^a-zA-Z0-9]/g, "")})`
              : color
          }
          fillRule="evenodd"
          stroke={color}
          strokeWidth={2}
        />
      ))}
    </g>
  );
};

export interface MapLegendItem {
  color: string;
  label: string;
  kind?: "block" | "dash" | "solid";
}

/**
 * Map legend — bottom-right plate, ink-on-paper.
 */
export const MapLegend: React.FC<{
  items: MapLegendItem[];
  x?: number;
  y?: number;
  delay?: number;
}> = ({ items, x = 1560, y = 830, delay = 0 }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame - delay, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <g transform={`translate(${x}, ${y})`} opacity={t}>
      <rect
        x={0}
        y={0}
        width={300}
        height={items.length * 46 + 24}
        fill="rgba(246,239,223,0.92)"
        stroke={TM.ink}
        strokeWidth={2.5}
      />
      {items.map((it, i) => {
        const ry = 24 + i * 46;
        return (
          <g key={i}>
            {it.kind === "dash" ? (
              <line x1={18} y1={ry + 8} x2={58} y2={ry + 8} stroke={it.color} strokeWidth={5} strokeDasharray="10 8" />
            ) : it.kind === "solid" ? (
              <line x1={18} y1={ry + 8} x2={58} y2={ry + 8} stroke={it.color} strokeWidth={5} />
            ) : (
              <rect x={18} y={ry - 4} width={40} height={22} fill={it.color} opacity={0.55} stroke={it.color} />
            )}
            <text
              x={74}
              y={ry + 14}
              fontFamily={TM.fontBody}
              fontSize={23}
              fill={TM.ink}
            >
              {it.label}
            </text>
          </g>
        );
      })}
    </g>
  );
};
