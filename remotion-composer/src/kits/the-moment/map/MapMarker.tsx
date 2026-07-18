import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { GeoProjection } from "d3-geo";
import { TM, FACTION, FactionKind } from "../theme";
import { project } from "./geo";

export type MarkerShape = "port" | "ship" | "junk" | "vote" | "company" | "dot";

export interface MapMarkerProps {
  proj: GeoProjection;
  lonLat: [number, number];
  label?: string;
  labelSide?: "left" | "right" | "top" | "bottom";
  shape?: MarkerShape;
  faction?: FactionKind;
  delay?: number;
  /** pulse ring for "active" states */
  pulse?: boolean;
  scale?: number;
}

/**
 * Map point marker — ports, ships, junks, votes, company posts.
 * Icon/line-art grammar (ledger rule: 图标/线稿/地图点标, never archive photos).
 * Renders inside the MapBase <svg> via the shared projection.
 */
export const MapMarker: React.FC<MapMarkerProps> = ({
  proj,
  lonLat,
  label,
  labelSide = "right",
  shape = "port",
  faction = "neutral",
  delay = 0,
  pulse = false,
  scale = 1,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = Math.max(0, frame - delay);
  const pop = spring({ frame: f, fps, config: { damping: 15, stiffness: 240, mass: 0.7 } });
  const [x, y] = project(proj, lonLat);
  if (Number.isNaN(x)) return null;

  const color = FACTION[faction];
  const s = scale * interpolate(pop, [0, 1], [0.2, 1]);

  const icon = () => {
    switch (shape) {
      case "ship": // square-rigged silhouette (schematic side view)
        return (
          <g>
            <path d="M -16 6 L 16 6 L 10 14 L -10 14 Z" fill={color} stroke={TM.ink} strokeWidth={2.5} />
            <line x1={0} y1={6} x2={0} y2={-16} stroke={TM.ink} strokeWidth={2.5} />
            <path d="M 0 -16 L 12 -10 L 0 -4 Z" fill={color} stroke={TM.ink} strokeWidth={2} />
          </g>
        );
      case "junk": // battened-sail junk silhouette
        return (
          <g>
            <path d="M -14 8 Q 0 13 14 8 L 10 14 L -10 14 Z" fill={color} stroke={TM.ink} strokeWidth={2.5} />
            <path d="M 0 8 L 0 -14 M -8 -2 Q 0 -8 8 -2 M -6 -8 Q 0 -12 6 -8" fill="none" stroke={TM.ink} strokeWidth={2.5} />
          </g>
        );
      case "vote":
        return (
          <g>
            <rect x={-11} y={-11} width={22} height={22} fill={TM.paperHi} stroke={color} strokeWidth={3} />
            <path d="M -5 0 L -1 5 L 6 -5" fill="none" stroke={color} strokeWidth={3.5} strokeLinecap="round" />
          </g>
        );
      case "company": // trading post flag
        return (
          <g>
            <line x1={0} y1={10} x2={0} y2={-14} stroke={TM.ink} strokeWidth={3} />
            <path d="M 0 -14 L 16 -10 L 0 -6 Z" fill={color} stroke={TM.ink} strokeWidth={2} />
            <circle cx={0} cy={10} r={3.5} fill={TM.ink} />
          </g>
        );
      case "dot":
        return <circle r={7} fill={color} stroke={TM.ink} strokeWidth={2.5} />;
      case "port":
      default: // anchor-less port ring
        return (
          <g>
            <circle r={9} fill={TM.paperHi} stroke={color} strokeWidth={3.5} />
            <circle r={3} fill={color} />
          </g>
        );
    }
  };

  const labelOffset =
    labelSide === "right"
      ? { x: 24, y: 8, anchor: "start" as const }
      : labelSide === "left"
      ? { x: -24, y: 8, anchor: "end" as const }
      : labelSide === "top"
      ? { x: 0, y: -26, anchor: "middle" as const }
      : { x: 0, y: 38, anchor: "middle" as const };

  return (
    <g transform={`translate(${x}, ${y})`} opacity={pop}>
      {pulse && (
        <circle
          r={interpolate((frame - delay) % 60, [0, 60], [10, 34])}
          fill="none"
          stroke={color}
          strokeWidth={2.5}
          opacity={interpolate((frame - delay) % 60, [0, 60], [0.7, 0])}
        />
      )}
      <g transform={`scale(${s})`}>{icon()}</g>
      {label ? (
        <text
          x={labelOffset.x}
          y={labelOffset.y}
          textAnchor={labelOffset.anchor}
          fontFamily={TM.fontBody}
          fontWeight={600}
          fontSize={26}
          fill={TM.ink}
          stroke={TM.paper}
          strokeWidth={5}
          paintOrder="stroke"
        >
          {label}
        </text>
      ) : null}
    </g>
  );
};
