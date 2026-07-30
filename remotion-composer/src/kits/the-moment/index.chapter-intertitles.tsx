import React from "react";
import { Composition, registerRoot } from "remotion";
import {
  CHAPTER_INTERTITLES,
  ChapterIntertitle,
} from "./compose/ChapterIntertitle";

const FPS = 30;
const DURATION_IN_FRAMES = 90;

const RemotionRoot: React.FC = () => (
  <>
    {CHAPTER_INTERTITLES.map((card) => (
      <Composition
        key={card.id}
        id={card.id}
        component={() => <ChapterIntertitle {...card} />}
        durationInFrames={DURATION_IN_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
      />
    ))}
  </>
);

registerRoot(RemotionRoot);
