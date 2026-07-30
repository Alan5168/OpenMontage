import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TM } from "../theme";
import { OldPaperCard } from "./SentenceShots";

export interface ChapterIntertitleSpec {
  id: string;
  kicker: string;
  title: string;
}

export const CHAPTER_INTERTITLES: ChapterIntertitleSpec[] = [
  { id: "EP1-CARD-CH1", kicker: "CHAPTER 1", title: "The Last Monopoly" },
  { id: "EP1-CARD-CH2", kicker: "CHAPTER 2", title: "Three Hammers" },
  { id: "EP1-CARD-CH3", kicker: "CHAPTER 3", title: "The Brake" },
  { id: "EP1-CARD-CH4", kicker: "CHAPTER 4", title: "The Flood" },
  { id: "EP1-CARD-CH5", kicker: "CHAPTER 5", title: "Beijing Hits the Brakes" },
  { id: "EP1-CARD-CH6", kicker: "CHAPTER 6", title: "The Paper" },
  { id: "EP1-CARD-CH7", kicker: "CHAPTER 7", title: "Nine Votes" },
  { id: "EP1-CARD-CH8", kicker: "CHAPTER 8", title: "The Winners' List" },
  { id: "EP1-CARD-EPI", kicker: "EPILOGUE", title: "The Wire" },
];

export const ChapterIntertitle: React.FC<ChapterIntertitleSpec> = ({
  kicker,
  title,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const enter = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 120, mass: 0.8 },
  });
  const exit = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames - 1],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const ruleWidth = interpolate(enter, [0, 1], [0, 420]);

  return (
    <OldPaperCard>
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          opacity: exit,
        }}
      >
        <div
          style={{
            fontFamily: TM.fontMono,
            fontSize: 34,
            fontWeight: 700,
            letterSpacing: "0.42em",
            marginLeft: "0.42em",
            color: TM.britishRed,
            opacity: enter,
          }}
        >
          {kicker}
        </div>
        <div
          style={{
            width: ruleWidth,
            height: 3,
            marginTop: 28,
            marginBottom: 28,
            backgroundColor: TM.ink,
            opacity: 0.82,
          }}
        />
        <div
          style={{
            maxWidth: 1500,
            padding: "0 80px",
            textAlign: "center",
            fontFamily: TM.fontHeading,
            fontSize: title.length > 22 ? 94 : 112,
            fontWeight: 800,
            lineHeight: 1.08,
            color: TM.ink,
            opacity: enter,
            transform: `translateY(${interpolate(enter, [0, 1], [22, 0])}px)`,
          }}
        >
          {title}
        </div>
      </AbsoluteFill>
    </OldPaperCard>
  );
};
