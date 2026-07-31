import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

import { HeroTitle } from "../components/HeroTitle";
import { SectionTitle } from "../components/SectionTitle";
import { TextCard } from "../components/TextCard";
import { EndTag } from "../components/EndTag";
import { BarChart } from "../components/charts/BarChart";
import { CaptionOverlay, WordCaption } from "../components/CaptionOverlay";

import type { WorldCupDailySlots, MatchSlot } from "./slots.types";

// -------------------------------------------------------------------------
// Timing — a fixed slot budget keeps every daily video the same length,
// which matters for Douyin/XiaohongShu algorithmic pacing (~55s sweet spot).
// -------------------------------------------------------------------------

const TIMING = {
  heroInSeconds: 0,
  heroSeconds: 3.5,
  storiesInSeconds: 3.5,
  storySeconds: 7,
  matchesInSeconds: 24.5,
  matchSeconds: 4.5,
  standingsInSeconds: 47,
  standingsSeconds: 8,
  endInSeconds: 55,
  endSeconds: 4,
} as const;

export const calculateWorldCupDailyMetadata = (slots: WorldCupDailySlots) => ({
  durationInFrames: Math.ceil(
    (TIMING.endInSeconds + TIMING.endSeconds) * 30,
  ),
  fps: 30,
  width: 1080,
  height: 1920, // 9:16 for short-form vertical
});

export const calculateWorldCupDailyMetadataFx: ({
  props,
}: {
  props: WorldCupDailySlots;
}) => ReturnType<typeof calculateWorldCupDailyMetadata> = ({ props }) =>
  calculateWorldCupDailyMetadata(props);

// -------------------------------------------------------------------------
// Sub-components (template-local — not promoted to components/ until
// a second template wants them).
// -------------------------------------------------------------------------

const MatchCard: React.FC<{ match: MatchSlot; theme: any }> = ({ match, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const slide = spring({ frame, fps, config: { damping: 18, stiffness: 90 } });

  const scoreText =
    match.status === "scheduled"
      ? "vs"
      : match.status === "live" || match.status === "final"
      ? `${match.scoreA ?? 0}  -  ${match.scoreB ?? 0}`
      : "PPD";

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        transform: `translateY(${interpolate(slide, [0, 1], [80, 0])}px)`,
        opacity: slide,
      }}
    >
      <div
        style={{
          backgroundColor: theme.surfaceColor,
          borderRadius: 32,
          padding: "60px 50px",
          width: "85%",
          display: "flex",
          flexDirection: "column",
          gap: 30,
          boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
        }}
      >
        <div style={{ fontSize: 28, color: theme.mutedTextColor, textAlign: "center" }}>
          {match.stage ?? ""} · {match.kickoff}
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 68,
            fontWeight: 800,
            color: theme.textColor,
          }}
        >
          <div style={{ flex: 1, textAlign: "left" }}>
            {match.flagA ? `${match.flagA} ` : ""}{match.teamA}
          </div>
          <div style={{ color: theme.accentColor, padding: "0 20px" }}>{scoreText}</div>
          <div style={{ flex: 1, textAlign: "right" }}>
            {match.teamB}{match.flagB ? ` ${match.flagB}` : ""}
          </div>
        </div>
        {match.venue && (
          <div style={{ fontSize: 24, color: theme.mutedTextColor, textAlign: "center" }}>
            {match.venue}
          </div>
        )}
        {match.status === "live" && (
          <div
            style={{
              alignSelf: "center",
              backgroundColor: "#EF4444",
              color: "#fff",
              padding: "8px 22px",
              borderRadius: 999,
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: 2,
            }}
          >
            ● LIVE
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

const StoryCard: React.FC<{ headline: string; body?: string; theme: any }> = ({
  headline,
  body,
  theme,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 16, stiffness: 80 } });
  return (
    <AbsoluteFill
      style={{
        padding: 80,
        justifyContent: "center",
        opacity: s,
        transform: `scale(${interpolate(s, [0, 1], [0.96, 1])})`,
      }}
    >
      <div
        style={{
          fontSize: 72,
          fontWeight: 800,
          color: theme.textColor,
          lineHeight: 1.2,
          marginBottom: 30,
        }}
      >
        {headline}
      </div>
      {body && (
        <div style={{ fontSize: 36, color: theme.mutedTextColor, lineHeight: 1.5 }}>
          {body}
        </div>
      )}
    </AbsoluteFill>
  );
};

// -------------------------------------------------------------------------
// Main template composition.
// -------------------------------------------------------------------------

export const WorldCupDaily: React.FC<WorldCupDailySlots> = (slots) => {
  const theme = (THEMES_OVERRIDE[slots.intro.theme ?? ""] ?? THEMES_OVERRIDE["flat-motion-graphics"]) as any;

  const captionWords: WordCaption[] =
    slots.narration?.captions?.map((c) => ({
      word: c.text,
      startMs: c.startMs,
      endMs: c.endMs,
    })) ?? [];

  return (
    <AbsoluteFill style={{ backgroundColor: theme.backgroundColor }}>
      {/* Hero */}
      <Sequence from={TIMING.heroInSeconds * 30} durationInFrames={Math.round(TIMING.heroSeconds * 30)}>
        <AbsoluteFill style={{ backgroundColor: theme.backgroundColor }}>
          <HeroTitle title={slots.intro.title} subtitle={slots.edition} />
          {slots.intro.subtitle && (
            <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 180 }}>
              <div style={{ fontSize: 40, color: theme.mutedTextColor }}>
                {slots.intro.subtitle}
              </div>
            </AbsoluteFill>
          )}
        </AbsoluteFill>
      </Sequence>

      {/* Stories */}
      {slots.stories.length > 0 && (
        <Sequence from={TIMING.storiesInSeconds * 30} durationInFrames={Math.round(slots.stories.length * TIMING.storySeconds * 30)}>
          <AbsoluteFill>
            {slots.stories.map((story, i) => (
              <Sequence
                key={`story-${i}`}
                from={i * TIMING.storySeconds * 30}
                durationInFrames={Math.round(TIMING.storySeconds * 30)}
              >
                <AbsoluteFill>
                  {story.asset?.kind === "image" && (
                    <Img src={story.asset.src} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  )}
                  {story.asset?.kind === "video" && (
                    <OffthreadVideo src={story.asset.src} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  )}
                  <AbsoluteFill style={{ backgroundColor: "rgba(0,0,0,0.55)" }} />
                  <StoryCard headline={story.headline} body={story.body} theme={{ ...theme, textColor: "#FFFFFF", mutedTextColor: "#E5E7EB" }} />
                  {story.source && (
                    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-start", padding: 60 }}>
                      <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 24 }}>
                        来源：{story.source}
                      </div>
                    </AbsoluteFill>
                  )}
                </AbsoluteFill>
              </Sequence>
            ))}
          </AbsoluteFill>
        </Sequence>
      )}

      {/* Matches */}
      {slots.matches.length > 0 && (
        <Sequence from={TIMING.matchesInSeconds * 30} durationInFrames={Math.round(slots.matches.length * TIMING.matchSeconds * 30)}>
          <AbsoluteFill>
            <SectionTitle title="今日赛况" position="top-left" />
            {slots.matches.map((m, i) => (
              <Sequence
                key={`match-${i}`}
                from={i * TIMING.matchSeconds * 30}
                durationInFrames={Math.round(TIMING.matchSeconds * 30)}
              >
                <MatchCard match={m} theme={theme} />
              </Sequence>
            ))}
          </AbsoluteFill>
        </Sequence>
      )}

      {/* Standings */}
      {slots.standings && (
        <Sequence from={TIMING.standingsInSeconds * 30} durationInFrames={Math.round(TIMING.standingsSeconds * 30)}>
          <AbsoluteFill style={{ padding: 60 }}>
            <SectionTitle title={`${slots.standings.group} 积分榜`} position="top-left" />
            <AbsoluteFill style={{ justifyContent: "center", paddingTop: 160 }}>
              <BarChart
                data={slots.standings.rows.map((r) => ({
                  label: `${r.flag ?? ""} ${r.team}`.trim(),
                  value: r.points,
                }))}
                title="积分"
                showValues
                colors={theme.chartColors}
                textColor={theme.textColor}
                backgroundColor="transparent"
              />
            </AbsoluteFill>
          </AbsoluteFill>
        </Sequence>
      )}

      {/* End tag */}
      <Sequence from={TIMING.endInSeconds * 30} durationInFrames={Math.round(TIMING.endSeconds * 30)}>
        <EndTag
          text={slots.outro?.cta ?? "关注每日世界杯"}
          palette="cool_offwhite_on_black"
        />
      </Sequence>

      {/* Narration + captions (full duration overlay) */}
      {slots.narration?.audioSrc && (
        <Audio src={staticFile(slots.narration.audioSrc)} />
      )}
      {captionWords.length > 0 && (
        <AbsoluteFill style={{ justifyContent: "flex-end", paddingBottom: 260 }}>
          <CaptionOverlay words={captionWords} wordsPerPage={6} />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

// Template-local theme fallbacks (Root.tsx THEMES stays source of truth;
// we just re-declare the two we lean on so this file is self-contained
// for the CLI render path).
const THEMES_OVERRIDE: Record<string, any> = {
  "flat-motion-graphics": {
    primaryColor: "#7C3AED",
    accentColor: "#EC4899",
    backgroundColor: "#0F172A",
    surfaceColor: "#1E293B",
    textColor: "#F8FAFC",
    mutedTextColor: "#94A3B8",
    chartColors: ["#7C3AED", "#EC4899", "#06B6D4", "#F59E0B", "#10B981", "#EF4444"],
  },
  "world-cup-2026": {
    primaryColor: "#0B3D2E",
    accentColor: "#FCD34D",
    backgroundColor: "#062018",
    surfaceColor: "#0E3B2A",
    textColor: "#F8FAFC",
    mutedTextColor: "#A7C4B5",
    chartColors: ["#FCD34D", "#EF4444", "#3B82F6", "#10B981", "#F97316", "#A855F7"],
  },
};
