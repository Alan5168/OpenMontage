/**
 * "The Moment" series kit — design tokens.
 *
 * Visual contract: runs/2026-07-14-canton-vs-east-india-company/director_style_lock_ep1.md
 *   Main track = Great War-style situation-map UI + info boards.
 *   Palette (style lock §1.5): paper base / ink line / British red accent /
 *   Qing blue+yellow / opium purple.
 *
 * Everything is a token so a later W4 style-contact sheet can re-skin the kit
 * without touching component code. No copy is hardcoded in components — the
 * script is being rewritten (v2) while this kit is built.
 */

export const TM = {
  // Paper base (flat, NOT fake-aged-scan; grain kept subtle and uniform)
  paper: "#EFE6D3",
  paperHi: "#F6EFDF",
  paperLo: "#E3D6BC",

  // Ink
  ink: "#2A241C",
  inkSoft: "#5C5344",
  inkFaint: "#8D8270",

  // Accents
  britishRed: "#A93226",
  qingBlue: "#2E5F74",
  qingYellow: "#C99A2E",
  opiumPurple: "#5F4B70",
  silver: "#7F8C99",

  // Semantic flow colors (map arrows)
  flow: {
    tea: "#4A6741",
    silver: "#7F8C99",
    opium: "#5F4B70",
    fleet: "#A93226",
  },

  // Fonts — system stacks only (renders must not depend on network font fetch)
  fontHeading: `"Palatino", "Palatino Linotype", "Georgia", "Songti SC", "STSong", serif`,
  fontBody: `"Avenir Next", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", sans-serif`,
  fontMono: `"Menlo", "IBM Plex Mono", "Courier New", monospace`,

  // Motion
  spring: { damping: 22, stiffness: 130, mass: 1 },
  springSlow: { damping: 26, stiffness: 70, mass: 1 },

  // Layout
  safePct: 0.05, // title-safe margin as fraction of frame
} as const;

export type FlowKind = keyof typeof TM.flow;

/** Per-faction colors used by map markers and puppets. */
export const FACTION = {
  british: TM.britishRed,
  qing: TM.qingBlue,
  merchant: TM.inkSoft,
  neutral: TM.inkFaint,
} as const;

export type FactionKind = keyof typeof FACTION;
