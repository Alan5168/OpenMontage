// -------------------------------------------------------------------------
// Template registry — each entry declares a composition, its slot schema,
// and the duration/fps/dimensions calculator so the CLI can render without
// importing the React tree.
// -------------------------------------------------------------------------

import { WorldCupDaily, calculateWorldCupDailyMetadata } from "./world-cup-daily";
import type { WorldCupDailySlots } from "./slots.types";

export interface TemplateManifest<S> {
  id: string;
  version: string;
  description: string;
  composition: React.FC<S>;
  calculateMetadata: (slots: S) => {
    durationInFrames: number;
    fps: number;
    width: number;
    height: number;
  };
}

export const TEMPLATES = {
  "world-cup-daily": {
    id: "world-cup-daily",
    version: "1.0.0",
    description:
      "每日世界杯快报：Hero + 多条新闻卡 + 赛况卡片轮播 + 积分榜 + EndTag。~55s 竖屏。",
    composition: WorldCupDaily,
    calculateMetadata: calculateWorldCupDailyMetadata,
  } as TemplateManifest<WorldCupDailySlots>,
} as const;

export type TemplateId = keyof typeof TEMPLATES;

export const getTemplate = (id: string): TemplateManifest<any> => {
  const t = (TEMPLATES as Record<string, TemplateManifest<any>>)[id];
  if (!t) {
    throw new Error(
      `Unknown template "${id}". Available: ${Object.keys(TEMPLATES).join(", ")}`,
    );
  }
  return t;
};
