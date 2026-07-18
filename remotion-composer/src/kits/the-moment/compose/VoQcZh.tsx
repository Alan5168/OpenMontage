import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { SECTION_ORDER, SECTION_SECONDS, voSrc } from "./audioLocale";
import { BgmUnderVo } from "./BgmUnderVo";
import { TM } from "../theme";

/**
 * ZH VO QC reel — lengdan stems only (+ BGM beds).
 * Visuals intentionally absent: EN beat map does not match ZH durations.
 * Director must retime picture to ZH before publish.
 */
export const VoQcZh: React.FC = () => {
  const { fps } = useVideoConfig();
  let cursor = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: TM.paper }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: TM.fontMono,
          fontSize: 36,
          color: TM.inkSoft,
          letterSpacing: "0.08em",
          textAlign: "center",
          padding: 80,
        }}
      >
        ZH VO QC · LENGDAN · NO PICTURE
        <br />
        VISUALS NEED DIRECTOR RETIME
      </div>
      {SECTION_ORDER.map((label) => {
        const sec = SECTION_SECONDS.zh[label];
        const frames = Math.round(sec * fps);
        const from = cursor;
        cursor += frames;
        return (
          <Sequence key={label} from={from} durationInFrames={frames} name={`zh-${label}`} layout="none">
            <Audio src={staticFile(voSrc(label, "zh"))} />
            <BgmUnderVo label={label} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

export const voQcZhDuration = (fps: number): number =>
  SECTION_ORDER.reduce((n, label) => n + Math.round(SECTION_SECONDS.zh[label] * fps), 0);
