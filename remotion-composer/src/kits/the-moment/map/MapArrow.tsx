import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { GeoProjection } from "d3-geo";
import { TM, FlowKind } from "../theme";
import { project } from "./geo";

export interface MapArrowProps {
  proj: GeoProjection;
  from: [number, number];
  to: [number, number];
  /** trade-flow semantic color: tea / silver / opium / fleet */
  flow?: FlowKind;
  color?: string;
  /** dashed = goods/money flows; solid = fleet movement */
  dashed?: boolean;
  /** curve bulge, 0 = straight, positive bows left of travel */
  curve?: number;
  label?: string;
  delay?: number;
  /** frames the draw-on takes */
  duration?: number;
  width?: number;
}

/**
 * Map flow arrow — animated draw-on along a quadratic curve.
 * Color = cargo semantics (tea/silver/opium/fleet from the style-lock palette).
 */
export const MapArrow: React.FC<MapArrowProps> = ({
  proj,
  from,
  to,
  flow,
  color,
  dashed = true,
  curve = 0.22,
  label,
  delay = 0,
  duration = 40,
  width = 5,
}) => {
  const frame = useCurrentFrame();
  const [x1, y1] = project(proj, from);
  const [x2, y2] = project(proj, to);
  if (Number.isNaN(x1) || Number.isNaN(x2)) return null;

  const stroke = color ?? (flow ? TM.flow[flow] : TM.ink);

  // control point: midpoint offset perpendicular to the chord
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  const cx = mx - (dy / len) * len * curve;
  const cy = my + (dx / len) * len * curve;

  const t = interpolate(frame - delay, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (t <= 0) return null;

  // point + tangent on the quadratic at parameter t
  const qx = (1 - t) * (1 - t) * x1 + 2 * (1 - t) * t * cx + t * t * x2;
  const qy = (1 - t) * (1 - t) * y1 + 2 * (1 - t) * t * cy + t * t * y2;
  const tanX = 2 * (1 - t) * (cx - x1) + 2 * t * (x2 - cx);
  const tanY = 2 * (1 - t) * (cy - y1) + 2 * t * (y2 - cy);
  const angle = (Math.atan2(tanY, tanX) * 180) / Math.PI;

  // partial path via stroke-dash trick
  const pathLen = 1000; // normalized via pathLength attr
  const d = `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;

  return (
    <g>
      <path
        d={d}
        pathLength={pathLen}
        fill="none"
        stroke={stroke}
        strokeWidth={width}
        strokeLinecap="round"
        strokeDasharray={dashed ? `18 14` : `${pathLen}`}
        strokeDashoffset={dashed ? 0 : pathLen * (1 - t)}
        opacity={dashed ? t : 1}
      />
      {/* arrowhead riding the tip */}
      <g transform={`translate(${qx}, ${qy}) rotate(${angle})`} opacity={t}>
        <path d="M 0 0 L -18 -8 L -13 0 L -18 8 Z" fill={stroke} />
      </g>
      {label ? (
        <text
          x={cx}
          y={cy - 12}
          textAnchor="middle"
          fontFamily={TM.fontMono}
          fontSize={24}
          letterSpacing="0.1em"
          fill={stroke}
          stroke={TM.paper}
          strokeWidth={5}
          paintOrder="stroke"
          opacity={t}
        >
          {label}
        </text>
      ) : null}
    </g>
  );
};
