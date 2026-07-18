import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";
import { MapBase } from "./MapBase";
import { MapTitleBar } from "./MapTitleBar";
import { MapMarker } from "./MapMarker";
import { MapArrow } from "./MapArrow";
import { MapRegion, MapLegend } from "./MapRegion";
import { UISchematic } from "../ui/UISchematic";
import { UIDate } from "../ui/UIDate";
import { PLACES } from "./geo";

/**
 * Map scene presets — the four Ep1 base-map scenes from the asset ledger
 * (MAP-PEARL / MAP-INDIA-CN-UK / MAP-CANTON-APPROACH / MAP-TREATY-PORTS),
 * built entirely from L1 primitives on Natural Earth vectors — the ledger's
 * "no-W1 vector fallback" path. When/if W1 painted stills are approved (G),
 * MapBase swaps to an <Img> underlay and every overlay stays unchanged.
 *
 * All copy is props with sample defaults for kit preview; beats re-supply
 * final text at compose time.
 */

const FHD = { width: 1920, height: 1080 };

/** MAP-PEARL — Pearl River mouth, three factions. */
export const MapPearl: React.FC<{
  title?: string;
  date?: string;
}> = ({ title = "Pearl River Mouth", date = "NOV 1839" }) => {
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [112.2, 21.6, 115.4, 23.9], ...FHD, padding: -40 }}
        resolution="10m"
      >
        {(proj) => (
          <>
            <MapMarker proj={proj} lonLat={PLACES.canton} label="Canton" shape="port" faction="qing" delay={8} />
            <MapMarker proj={proj} lonLat={PLACES.boccaTigris} label="Bocca Tigris" shape="port" faction="qing" delay={14} labelSide="left" />
            <MapMarker proj={proj} lonLat={PLACES.macao} label="Macao" shape="port" faction="neutral" delay={20} labelSide="left" />
            <MapMarker proj={proj} lonLat={PLACES.lintin} label="Lintin" shape="ship" faction="merchant" delay={26} />
            <MapMarker proj={proj} lonLat={[113.9, 22.6]} label="Royal Navy" shape="ship" faction="british" delay={34} pulse />
            <MapMarker proj={proj} lonLat={[113.5, 22.95]} label="Qing junks" shape="junk" faction="qing" delay={40} />
          </>
        )}
      </MapBase>
      <MapTitleBar title={title} date={date} />
      <UISchematic text="SCHEMATIC · 示意" />
    </AbsoluteFill>
  );
};

/** MAP-INDIA-CN-UK — the trade triangle with flow arrows. */
export const MapTriangle: React.FC<{
  title?: string;
  date?: string;
}> = ({ title = "The Triangle", date = "1813–1833" }) => {
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [-25, -8, 145, 62], ...FHD, padding: 60 }}
        resolution="50m"
        drift={false}
      >
        {(proj) => (
          <>
            <MapRegion proj={proj} countryIds={["826"]} color={TM.britishRed} opacity={0.4} delay={6} />
            <MapRegion proj={proj} countryIds={["356"]} color={TM.opiumPurple} opacity={0.3} delay={12} hatched />
            <MapRegion proj={proj} countryIds={["156"]} color={TM.qingBlue} opacity={0.28} delay={18} />
            <MapMarker proj={proj} lonLat={PLACES.london} label="London" shape="company" faction="british" delay={16} />
            <MapMarker proj={proj} lonLat={PLACES.calcutta} label="Calcutta" shape="company" faction="merchant" delay={22} labelSide="bottom" />
            <MapMarker proj={proj} lonLat={PLACES.canton} label="Canton" shape="port" faction="qing" delay={28} />
            <MapArrow proj={proj} from={PLACES.canton} to={PLACES.london} flow="tea" label="TEA" delay={40} curve={0.18} />
            <MapArrow proj={proj} from={PLACES.calcutta} to={PLACES.canton} flow="opium" label="OPIUM" delay={58} curve={-0.25} />
            <MapArrow proj={proj} from={PLACES.canton} to={PLACES.calcutta} flow="silver" label="SILVER" delay={76} curve={-0.35} />
            <MapLegend
              delay={90}
              items={[
                { color: TM.flow.tea, label: "Tea", kind: "dash" },
                { color: TM.flow.opium, label: "Opium", kind: "dash" },
                { color: TM.flow.silver, label: "Silver", kind: "dash" },
              ]}
            />
          </>
        )}
      </MapBase>
      <MapTitleBar title={title} date={date} accent={TM.opiumPurple} />
      <UISchematic text="SCHEMATIC · NOT EXACT BORDERS · 示意非精确边界" />
    </AbsoluteFill>
  );
};

/**
 * MAP-CANTON-APPROACH — 1834 Napier standoff as a stylised L1 river schematic
 * (hand-drawn-grade geometry, the ledger's fallback when no base map fits).
 * step: 0 letter refused → 1 trade suspended → 2 standoff.
 */
export const MapCantonApproach: React.FC<{ step?: 0 | 1 | 2 }> = ({ step = 2 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = spring({ frame, fps, config: TM.springSlow });

  const stepTitles = ["The Letter Refused", "Trade Suspended", "The Standoff"] as const;
  const stepDates = ["JUL 1834", "AUG 1834", "SEP 1834"] as const;

  // stylised river: wide estuary narrowing to Canton
  const river = "M 1500 1080 C 1350 800 1250 660 1050 560 C 850 460 700 430 520 400 L 520 330 C 720 350 900 380 1120 490 C 1330 590 1440 780 1600 1080 Z";

  return (
    <AbsoluteFill>
      <PaperBackground>
        <svg width={1920} height={1080}>
          <path d={river} fill={TM.paperHi} stroke={TM.inkSoft} strokeWidth={3} opacity={t} />
          {/* Canton */}
          <g transform="translate(480, 365)" opacity={t}>
            <circle r={12} fill={TM.qingBlue} stroke={TM.ink} strokeWidth={3} />
            <text x={-28} y={-24} textAnchor="end" fontFamily={TM.fontBody} fontWeight={600} fontSize={30} fill={TM.ink}>Canton</text>
            {/* factories row */}
            <g transform="translate(30, -14)">
              {[0, 1, 2].map((i) => (
                <rect key={i} x={i * 30} y={0} width={24} height={28} fill={TM.paperLo} stroke={TM.ink} strokeWidth={2.5} />
              ))}
            </g>
          </g>
          {/* forts at the Bogue */}
          <g transform="translate(1080, 540)" opacity={t}>
            <path d="M -14 10 L -14 -8 L 0 -16 L 14 -8 L 14 10 Z" fill={TM.qingYellow} stroke={TM.ink} strokeWidth={3} />
            <text x={26} y={6} fontFamily={TM.fontBody} fontSize={26} fill={TM.ink}>Bogue forts</text>
          </g>
          {/* Napier's frigates lower river */}
          <g transform="translate(1330, 800)" opacity={t}>
            <path d="M -20 8 L 20 8 L 12 18 L -12 18 Z" fill={TM.britishRed} stroke={TM.ink} strokeWidth={3} />
            <line x1={0} y1={8} x2={0} y2={-20} stroke={TM.ink} strokeWidth={3} />
            <path d="M 0 -20 L 16 -12 L 0 -6 Z" fill={TM.britishRed} stroke={TM.ink} strokeWidth={2} />
            <text x={30} y={12} fontFamily={TM.fontBody} fontSize={26} fill={TM.ink}>HM frigates</text>
          </g>
          {/* step 1+: trade gate closes across the river */}
          {step >= 1 && (
            <g opacity={interpolate(frame, [20, 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}>
              <line x1={980} y1={430} x2={1180} y2={640} stroke={TM.britishRed} strokeWidth={8} strokeDasharray="26 16" />
              <text x={1200} y={430} fontFamily={TM.fontMono} fontSize={26} letterSpacing="0.12em" fill={TM.britishRed}>TRADE SUSPENDED</text>
            </g>
          )}
          {/* step 2: standoff double bar */}
          {step >= 2 && (
            <g opacity={interpolate(frame, [45, 65], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}>
              <line x1={1150} y1={620} x2={1290} y2={760} stroke={TM.qingBlue} strokeWidth={8} />
              <line x1={1190} y1={600} x2={1330} y2={740} stroke={TM.qingBlue} strokeWidth={8} />
            </g>
          )}
        </svg>
      </PaperBackground>
      <MapTitleBar title={stepTitles[step]} date={stepDates[step]} accent={TM.britishRed} />
      <UIDate date="1834" x={1660} y={90} scale={0.9} delay={6} />
      <UISchematic text="SCHEMATIC · 示意" />
    </AbsoluteFill>
  );
};

/** MAP-TREATY-PORTS — five ports + Hong Kong opening in sequence. */
export const MapTreatyPorts: React.FC<{
  title?: string;
  date?: string;
}> = ({ title = "Five Ports, One Island", date = "AUG 1842" }) => {
  const ports: Array<{ p: [number, number]; label: string; side?: "left" | "right" }> = [
    { p: PLACES.canton, label: "Canton", side: "left" },
    { p: PLACES.amoy, label: "Amoy" },
    { p: PLACES.foochow, label: "Foochow" },
    { p: PLACES.ningpo, label: "Ningpo" },
    { p: PLACES.shanghai, label: "Shanghai" },
  ];
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [104, 17, 127, 36], ...FHD, padding: 30 }}
        resolution="10m"
      >
        {(proj) => (
          <>
            {ports.map((pt, i) => (
              <MapMarker
                key={pt.label}
                proj={proj}
                lonLat={pt.p}
                label={pt.label}
                labelSide={pt.side ?? "right"}
                shape="port"
                faction="british"
                delay={10 + i * 12}
                pulse={false}
              />
            ))}
            <MapMarker
              proj={proj}
              lonLat={PLACES.hongkong}
              label="Hong Kong (ceded)"
              labelSide="bottom"
              shape="company"
              faction="british"
              delay={75}
              pulse
            />
          </>
        )}
      </MapBase>
      <MapTitleBar title={title} date={date} />
      <UISchematic text="SCHEMATIC · 示意" />
    </AbsoluteFill>
  );
};
