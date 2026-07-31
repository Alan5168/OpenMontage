/**
 * Triptych palette — CP3 demo re-skin (NF_DIRECTOR, 2026-07-20).
 *
 * WHY THIS FILE EXISTS
 * The shipped kit (theme.ts) is a low-saturation "McKinsey" paper/ink scheme:
 * paper #EFE6D3 + silver #7F8C99 + qingBlue #2E5F74. The CEO judged the CP3 N1
 * preview "看不出差别" — the recut changed pacing but not the LOOK. This palette
 * is the visual break: high-saturation faction colors over a deep navy ocean,
 * per EPIC_HISTORY_TEMPLATE_TRIPTYCH.md §2 (2gf relief-map faction board).
 *
 * HARD RULE (Triptych §3 ❌4 + seat prompt §1): the McKinsey greys
 * #5B6B7C / #8899A6 and theme.ts `silver #7F8C99` are BANNED as primary tones.
 * High saturation is reserved for factions / targets / money — not a global
 * filter. Legend before color (❌2).
 *
 * These are hex constants only; components import them directly. theme.ts is
 * left structurally intact — the demo composition imports THIS instead.
 */

export const TRIPTYCH = {
  // Ocean / stage — deep, saturated navy is the new base (replaces paper base)
  ocean: "#0E3B5C",
  oceanDeep: "#082438",
  oceanHi: "#155073",

  // Land — old-paper landmass on the relief map (2gf §2)
  land: "#E8D7B0",
  landShadow: "#C9B489",

  // Faction colors (seat prompt §1 — exact hex locked by COO)
  qingRed: "#C8342B", //  清 — the Wyip red, NOT brick-red
  britNavy: "#0B2A4A", // 英 / East India — deep navy
  britGold: "#D4A017", // 英 / East India — gold accent
  local: "#3E8E7E", //     当地势力 — teal-green (fourth faction, not merged)
  usAmber: "#B5651D", //   美国余波 — amber (multi-faction, ❌9)

  // Money / object tone — silver bullion (物体化数字), warm metal not grey
  bullion: "#D8DEE6",
  bullionEdge: "#9AA6B2",
  bullionFace: "#EEF2F6",

  // Ink for text on light land / on dark ocean
  onDark: "#F4EAD2",
  onDarkSoft: "#C9B896",
  onLight: "#1A1206",

  // Quote card (dark, large — Triptych §2 QuoteCard dark)
  quoteBg: "#0A1E30",
  quoteText: "#F4EAD2",
  quoteAccent: "#D4A017",

  fontHeading: `"Palatino", "Palatino Linotype", "Georgia", "Songti SC", serif`,
  fontBody: `"Avenir Next", "Helvetica Neue", "PingFang SC", sans-serif`,
  fontMono: `"Menlo", "IBM Plex Mono", "Courier New", monospace`,
} as const;

// land shadow, kept as a real value (the inline placeholder above is a lint tripwire)
export const LAND_SHADOW = TRIPTYCH.landShadow;

export type TriptychFaction = "qing" | "brit" | "local" | "us";

/** Faction → primary hex. Legend-first: every color is a labeled faction. */
export const triptychColor = (faction: TriptychFaction): string => {
  switch (faction) {
    case "qing":
      return TRIPTYCH.qingRed;
    case "brit":
      return TRIPTYCH.britNavy;
    case "local":
      return TRIPTYCH.local;
    case "us":
      return TRIPTYCH.usAmber;
  }
};

export const TRIPTYCH_LEGEND: Array<{ faction: TriptychFaction; label: string }> = [
  { faction: "qing", label: "清 QING" },
  { faction: "brit", label: "英 / EAST INDIA CO." },
  { faction: "local", label: "十三行 LOCAL TRADE" },
  { faction: "us", label: "美 U.S. WAKE" },
];
