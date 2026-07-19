import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
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

/**
 * MAP-PEARL — Pearl River mouth, three factions (Nov 1839, Chuenpi).
 * Coordinate fix 2026-07-18 (producer diagnosis §1.2): RN / junk markers now
 * come from the PLACES registry (Chuenpi anchorage at the outer Bocca
 * Tigris) instead of unverified bare literals that projected onto land.
 * Fleet approach uses the animated MapArrow (route_arc, P0 per
 * VISUAL_AE_LAYERS_JH_20260717.md).
 */
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
            {/* RN works up from the Macao roads to the Chuenpi anchorage */}
            <MapArrow proj={proj} from={PLACES.macao} to={PLACES.chuenpiAnchorage} flow="fleet" dashed={false} delay={30} duration={34} curve={-0.18} />
            <MapMarker proj={proj} lonLat={PLACES.chuenpiAnchorage} label="Royal Navy" shape="ship" faction="british" delay={58} pulse />
            <MapMarker proj={proj} lonLat={PLACES.chuenpi} label="Qing junks" shape="junk" faction="qing" delay={70} />
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

/**
 * MAP-TREATY-PORTS — five ports + Hong Kong, with the expedition's line of
 * advance as animated fleet arcs (route_arc P0, VISUAL_AE_LAYERS_JH §4;
 * CEO CP2 feedback #1). Route legs are the documented 1841–42 campaign:
 * Hong Kong → Amoy (Aug 1841) → Ningpo (Oct 1841) → Shanghai (Jun 1842) →
 * up the Yangtze to Nanking (Aug 1842). Foochow was opened by the treaty,
 * not a campaign stop — it pops as a port only, off the route line.
 */
export const MapTreatyPorts: React.FC<{
  title?: string;
  date?: string;
  /** draw the animated campaign route (default on) */
  campaignRoute?: boolean;
}> = ({ title = "Five Ports, One Island", date = "AUG 1842", campaignRoute = true }) => {
  const ports: Array<{ p: [number, number]; label: string; side?: "left" | "right"; delay: number }> = [
    { p: PLACES.canton, label: "Canton", side: "left", delay: 10 },
    { p: PLACES.amoy, label: "Amoy", delay: campaignRoute ? 46 : 22 },
    { p: PLACES.foochow, label: "Foochow", delay: campaignRoute ? 90 : 34 },
    { p: PLACES.ningpo, label: "Ningpo", delay: campaignRoute ? 84 : 46 },
    { p: PLACES.shanghai, label: "Shanghai", delay: campaignRoute ? 112 : 58 },
  ];
  const legs: Array<{ from: [number, number]; to: [number, number]; delay: number; duration: number; curve: number }> = [
    { from: PLACES.hongkong, to: PLACES.amoy, delay: 16, duration: 28, curve: 0.14 },
    { from: PLACES.amoy, to: PLACES.ningpo, delay: 50, duration: 28, curve: 0.16 },
    { from: PLACES.ningpo, to: PLACES.shanghai, delay: 84, duration: 20, curve: 0.12 },
    { from: PLACES.shanghai, to: PLACES.nanking, delay: 110, duration: 26, curve: -0.12 },
  ];
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [104, 17, 127, 36], ...FHD, padding: 30 }}
        resolution="10m"
      >
        {(proj) => (
          <>
            {ports.map((pt) => (
              <MapMarker
                key={pt.label}
                proj={proj}
                lonLat={pt.p}
                label={pt.label}
                labelSide={pt.side ?? "right"}
                shape="port"
                faction="british"
                delay={pt.delay}
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
              delay={campaignRoute ? 8 : 75}
              pulse
            />
            {campaignRoute && (
              <>
                {legs.map((leg, i) => (
                  <MapArrow
                    key={i}
                    proj={proj}
                    from={leg.from}
                    to={leg.to}
                    flow="fleet"
                    dashed={false}
                    delay={leg.delay}
                    duration={leg.duration}
                    curve={leg.curve}
                  />
                ))}
                <MapMarker
                  proj={proj}
                  lonLat={PLACES.nanking}
                  label="Nanking — the treaty"
                  labelSide="left"
                  shape="ship"
                  faction="british"
                  delay={140}
                  pulse
                />
              </>
            )}
          </>
        )}
      </MapBase>
      <MapTitleBar title={title} date={date} />
      <UISchematic text="SCHEMATIC · 示意" />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* Map-share batch 1 (2026-07-19 night run) — six info beats converted */
/* to map state changes per grammar_stack §4 (map 8.3% → 目标 35–45%,   */
/* producer diagnosis: CH1/CH5 info cards were the low-hanging swaps).  */
/* All geometry stays Natural Earth vector (CEO ruling 07-18: coastline */
/* never delegated to a text-to-image model).                           */
/* ------------------------------------------------------------------ */

/**
 * MAP-MONOPOLY-ZONE — C1-4: "royal monopoly — all trade east of Africa".
 * World view; the 20°E meridian splits the frame and everything east of it
 * tints as the Company's legal domain; London→Cape→Canton route arc.
 */
export const MapMonopolyZone: React.FC<{
  title?: string;
  date?: string;
}> = ({ title = "All trade east of Africa", date = "SINCE 1600" }) => {
  const frame = useCurrentFrame();
  const zoneIn = interpolate(frame, [14, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [-25, -38, 145, 62], ...FHD, padding: 40 }}
        resolution="50m"
        drift={false}
      >
        {(proj) => {
          const [meridianX] = proj([20, 0]) ?? [960];
          return (
            <>
              {/* the Company's legal domain — everything east of Africa */}
              <rect
                x={meridianX}
                y={0}
                width={FHD.width - meridianX}
                height={FHD.height}
                fill={TM.opiumPurple}
                opacity={0.09 * zoneIn}
              />
              <line
                x1={meridianX}
                y1={0}
                x2={meridianX}
                y2={FHD.height}
                stroke={TM.opiumPurple}
                strokeWidth={4}
                strokeDasharray="20 14"
                opacity={0.75 * zoneIn}
              />
              <text
                x={meridianX + 22}
                y={560}
                fontFamily={TM.fontMono}
                fontSize={26}
                letterSpacing="0.14em"
                fill={TM.opiumPurple}
                opacity={zoneIn}
              >
                THE COMPANY&apos;S — BY LAW
              </text>
              <MapMarker proj={proj} lonLat={PLACES.london} label="London" shape="company" faction="british" delay={6} />
              <MapMarker proj={proj} lonLat={PLACES.canton} label="Canton" shape="port" faction="qing" delay={46} labelSide="top" />
              <MapArrow proj={proj} from={PLACES.london} to={PLACES.capeGoodHope} flow="fleet" dashed delay={30} duration={30} curve={0.12} />
              <MapArrow proj={proj} from={PLACES.capeGoodHope} to={PLACES.canton} flow="fleet" dashed delay={58} duration={34} curve={0.16} />
            </>
          );
        }}
      </MapBase>
      <MapTitleBar title={title} date={date} accent={TM.opiumPurple} />
      <UISchematic text="SCHEMATIC · 示意" />
    </AbsoluteFill>
  );
};

/**
 * MAP-PETITION-CITIES — C1-6: Manchester / Liverpool / Glasgow converge on
 * Westminster (the 1813 petition wave; the "cities at the door").
 */
export const MapPetitionCities: React.FC<{
  title?: string;
  date?: string;
}> = ({ title = "The cities at the door", date = "1813 · 130 PETITIONS" }) => {
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [-8.5, 49.6, 3.2, 59.2], ...FHD, padding: 30 }}
        resolution="10m"
      >
        {(proj) => (
          <>
            <MapMarker proj={proj} lonLat={PLACES.glasgow} label="Glasgow" shape="dot" faction="merchant" delay={8} labelSide="left" />
            <MapMarker proj={proj} lonLat={PLACES.liverpool} label="Liverpool" shape="dot" faction="merchant" delay={16} labelSide="left" />
            <MapMarker proj={proj} lonLat={PLACES.manchester} label="Manchester" shape="dot" faction="merchant" delay={24} />
            <MapMarker proj={proj} lonLat={PLACES.london} label="Westminster" shape="company" faction="british" delay={4} pulse />
            <MapArrow proj={proj} from={PLACES.glasgow} to={PLACES.london} flow="silver" dashed delay={34} duration={40} curve={0.14} label="PETITIONS" />
            <MapArrow proj={proj} from={PLACES.liverpool} to={PLACES.london} flow="silver" dashed delay={44} duration={36} curve={-0.1} />
            <MapArrow proj={proj} from={PLACES.manchester} to={PLACES.london} flow="silver" dashed delay={54} duration={34} curve={0.08} />
          </>
        )}
      </MapBase>
      <MapTitleBar title={title} date={date} accent={TM.qingBlue} />
      <UISchematic text="SCHEMATIC · 示意" />
    </AbsoluteFill>
  );
};

/**
 * MAP-SPLIT-1813 — C1-7: India thrown open, China monopoly survives.
 * One frame, two region states (the 1813 split).
 */
export const MapSplit1813: React.FC<{
  title?: string;
  date?: string;
}> = ({ title = "The 1813 split", date = "INDIA OPEN · CHINA LOCKED" }) => {
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [55, 0, 130, 45], ...FHD, padding: 50 }}
        resolution="50m"
        drift={false}
      >
        {(proj) => (
          <>
            <MapRegion proj={proj} countryIds={["356"]} color={TM.qingBlue} opacity={0.4} delay={8} />
            <MapRegion proj={proj} countryIds={["156"]} color={TM.britishRed} opacity={0.3} delay={26} hatched />
            <MapMarker proj={proj} lonLat={PLACES.calcutta} label="India — thrown open" shape="port" faction="merchant" delay={16} labelSide="bottom" />
            <MapMarker proj={proj} lonLat={PLACES.canton} label="China — the monopoly survives" shape="company" faction="british" delay={38} labelSide="top" />
            <MapLegend
              delay={50}
              items={[
                { color: TM.qingBlue, label: "Opened 1813", kind: "block" },
                { color: TM.britishRed, label: "Still the Company's", kind: "block" },
              ]}
            />
          </>
        )}
      </MapBase>
      <MapTitleBar title={title} date={date} accent={TM.qingBlue} />
      <UISchematic text="SCHEMATIC · NOT EXACT BORDERS · 示意非精确边界" />
    </AbsoluteFill>
  );
};

/**
 * MAP-QING-BANS — C5-2: a century of edicts that kept failing.
 * Peking issues; the coast leaks. "BANNED" plates strike and fade while the
 * smuggling arrow keeps flowing — the failing-brake state, drawn.
 */
export const MapQingBans: React.FC<{
  title?: string;
  date?: string;
}> = ({ title = "Banned for over a century", date = "1729 · THE FIRST EDICT" }) => {
  const frame = useCurrentFrame();
  const stamps = [
    { x: 640, y: 380, delay: 20, label: "1729 · BANNED" },
    { x: 900, y: 520, delay: 55, label: "BANNED — AGAIN" },
    { x: 700, y: 680, delay: 90, label: "AND AGAIN" },
  ];
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [95, 16, 128, 44], ...FHD, padding: 40 }}
        resolution="50m"
        drift={false}
      >
        {(proj) => (
          <>
            <MapMarker proj={proj} lonLat={PLACES.peking} label="Peking" shape="company" faction="qing" delay={8} labelSide="top" />
            <MapMarker proj={proj} lonLat={PLACES.canton} label="Canton — where it leaks" shape="port" faction="qing" delay={14} labelSide="bottom" />
            {/* the flow the paper never stopped — from open water at this zoom */}
            <MapArrow proj={proj} from={PLACES.southChinaSea} to={PLACES.canton} flow="opium" dashed delay={30} duration={50} curve={-0.22} label="STILL FLOWING" />
            {stamps.map((s, i) => {
              const inT = interpolate(frame - s.delay, [0, 8], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.quad),
              });
              const fade = interpolate(frame - s.delay, [26, 60], [1, 0.3], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return (
                <g
                  key={i}
                  transform={`translate(${s.x}, ${s.y}) rotate(-7) scale(${interpolate(inT, [0, 1], [1.6, 1])})`}
                  opacity={inT * fade}
                >
                  <rect x={-150} y={-32} width={300} height={64} fill="none" stroke={TM.britishRed} strokeWidth={5} rx={4} />
                  <text
                    textAnchor="middle"
                    y={12}
                    fontFamily={TM.fontMono}
                    fontSize={30}
                    letterSpacing="0.14em"
                    fill={TM.britishRed}
                  >
                    {s.label}
                  </text>
                </g>
              );
            })}
          </>
        )}
      </MapBase>
      <MapTitleBar title={title} date={date} accent={TM.qingBlue} />
      <UISchematic text="SCHEMATIC · 示意" />
    </AbsoluteFill>
  );
};

/**
 * MAP-HUMEN — C5-8: the surrendered chests converge on Humen beach and are
 * destroyed in public. Count plate carries the ledger number.
 */
export const MapHumen: React.FC<{
  title?: string;
  date?: string;
}> = ({ title = "Humen — destroyed in public", date = "JUN 1839" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const plateIn = spring({ frame: Math.max(0, frame - 70), fps, config: TM.spring });
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [112.2, 21.6, 115.4, 23.9], ...FHD, padding: -40 }}
        resolution="10m"
      >
        {(proj) => (
          <>
            <MapMarker proj={proj} lonLat={PLACES.canton} label="Canton" shape="port" faction="qing" delay={8} />
            <MapMarker proj={proj} lonLat={PLACES.lintin} label="the receiving ships" shape="ship" faction="merchant" delay={16} />
            <MapArrow proj={proj} from={PLACES.lintin} to={PLACES.humen} flow="opium" dashed delay={28} duration={40} curve={0.2} label="20,000+ CHESTS" />
            <MapMarker proj={proj} lonLat={PLACES.humen} label="Humen" shape="port" faction="qing" delay={66} pulse />
          </>
        )}
      </MapBase>
      <MapTitleBar title={title} date={date} accent={TM.opiumPurple} />
      {/* ledger plate — the number is the point */}
      <div
        style={{
          position: "absolute",
          right: 90,
          bottom: 120,
          maxWidth: 560,
          backgroundColor: "rgba(246,239,223,0.94)",
          border: `3px solid ${TM.ink}`,
          borderRight: `12px solid ${TM.opiumPurple}`,
          padding: "22px 30px",
          opacity: plateIn,
          transform: `translateY(${interpolate(plateIn, [0, 1], [24, 0])}px)`,
        }}
      >
        <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 64, color: TM.ink }}>
          20,000+
        </div>
        <div style={{ fontFamily: TM.fontBody, fontSize: 28, color: TM.inkSoft, marginTop: 6, lineHeight: 1.35 }}>
          chests surrendered and destroyed — the largest drug seizure in history, before or since
        </div>
      </div>
      <UISchematic text="SCHEMATIC · 示意" />
    </AbsoluteFill>
  );
};

/**
 * MAP-LETTER-ROUTE — C5-9: Lin's letter to Queen Victoria sets out from
 * Canton and never lands — the arc reaches London and the NEVER DELIVERED
 * stamp strikes over it.
 */
export const MapLetterRoute: React.FC<{
  title?: string;
  date?: string;
}> = ({ title = "The letter to Queen Victoria", date = "1839" }) => {
  const frame = useCurrentFrame();
  const stampDelay = 120;
  const stampIn = interpolate(frame - stampDelay, [0, 9], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });
  return (
    <AbsoluteFill>
      <MapBase
        view={{ bbox: [-25, -38, 145, 62], ...FHD, padding: 40 }}
        resolution="50m"
        drift={false}
      >
        {(proj) => (
          <>
            <MapMarker proj={proj} lonLat={PLACES.canton} label="Canton — Commissioner Lin" shape="port" faction="qing" delay={6} labelSide="top" />
            <MapMarker proj={proj} lonLat={PLACES.london} label="Queen Victoria" shape="company" faction="british" delay={90} />
            <MapArrow proj={proj} from={PLACES.canton} to={PLACES.capeGoodHope} flow="silver" color={TM.qingBlue} dashed delay={20} duration={46} curve={-0.14} />
            <MapArrow proj={proj} from={PLACES.capeGoodHope} to={PLACES.london} flow="silver" color={TM.qingBlue} dashed delay={64} duration={44} curve={-0.12} />
          </>
        )}
      </MapBase>
      <MapTitleBar title={title} date={date} accent={TM.qingBlue} />
      {/* the strike */}
      <div
        style={{
          position: "absolute",
          left: 430,
          top: 400,
          border: `6px solid ${TM.britishRed}`,
          color: TM.britishRed,
          fontFamily: TM.fontMono,
          fontSize: 46,
          letterSpacing: "0.2em",
          padding: "14px 30px",
          borderRadius: 6,
          transform: `rotate(-8deg) scale(${interpolate(stampIn, [0, 1], [1.7, 1])})`,
          opacity: stampIn,
          backgroundColor: "rgba(246,239,223,0.85)",
        }}
      >
        NEVER DELIVERED
      </div>
      <div
        style={{
          position: "absolute",
          left: 500,
          top: 585,
          fontFamily: TM.fontBody,
          fontSize: 30,
          color: TM.inkSoft,
          opacity: interpolate(frame - stampDelay - 20, [0, 12], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        London&apos;s papers print it — as a curiosity.
      </div>
      <UISchematic text="SCHEMATIC · 示意" />
    </AbsoluteFill>
  );
};
