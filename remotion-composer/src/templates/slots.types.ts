// -------------------------------------------------------------------------
// Slot primitives — typed building blocks every template can declare.
// No runtime validation lib here; keep schemas as TS types and validate
// lightly inside the template's `toCompositionProps()`.
// -------------------------------------------------------------------------

export interface AssetSlot {
  kind: "video" | "image" | "audio";
  src: string;
  durationInSeconds?: number;
  alt?: string;
}

export interface MatchSlot {
  kickoff: string; // "18:00" or ISO
  teamA: string;
  teamB: string;
  flagA?: string; // emoji or asset path
  flagB?: string;
  scoreA?: number;
  scoreB?: number;
  stage?: string; // "Group A" / "R16" / "SF" / "F"
  venue?: string;
  status?: "scheduled" | "live" | "final" | "postponed";
}

export interface StandingRowSlot {
  pos: number;
  team: string;
  flag?: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd?: number;
  points: number;
}

export interface StorySlot {
  headline: string;
  body?: string;
  source?: string;
  asset?: AssetSlot;
}

// -------------------------------------------------------------------------
// World Cup Daily slots — one template, one bundle.
// -------------------------------------------------------------------------

export interface WorldCupDailySlots {
  edition: string; // "Day 12 · June 22, 2026"
  host: {
    name: string;
    avatar?: AssetSlot;
    voice?: string; // TTS voice id for narration track
  };
  intro: {
    title: string; // "今日世界杯"
    subtitle?: string;
    theme?: string; // key from Root.tsx THEMES
  };
  stories: StorySlot[];
  matches: MatchSlot[];
  standings?: {
    group: string; // "Group A"
    rows: StandingRowSlot[];
  };
  outro?: {
    cta?: string;
    endCardAsset?: AssetSlot;
  };
  narration?: {
    audioSrc: string; // pre-rendered TTS track
    captions?: { text: string; startMs: number; endMs: number }[];
  };
}
