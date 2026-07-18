import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";

/**
 * CH4 — the four readings, as four PARALLEL panels (scene plan hard rules:
 * 并列非多米诺, each panel carries its own date band, N1 = two endpoints
 * with a dashed gap — never a smooth interpolated curve).
 *
 * Panels light up in sequence but no arrows/dominoes connect them.
 */

export interface ReadingPanel {
  kicker: string; // "N1 · PRICE"
  dateBand: string; // "early 1820s → 1838"
  headline: string; // "-70%"
  sub?: string; // "per chest, benchmark series"
}

export interface FourReadingsProps {
  n1: ReadingPanel & { from: string; to: string }; // price endpoints
  n2: ReadingPanel & { fromVal: number; toVal: number; fromLabel: string; toLabel: string }; // chests bars
  n3: ReadingPanel; // silver outflow big number
  n4: ReadingPanel & { fromRate: string; toRate: string }; // exchange
  /** which panels are lit (for building the chapter progressively); default all */
  activeCount?: number;
}

const PANEL_W = 860;
const PANEL_H = 420;

const PanelShell: React.FC<{
  p: ReadingPanel;
  x: number;
  y: number;
  delay: number;
  accent: string;
  children?: React.ReactNode;
}> = ({ p, x, y, delay, accent, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame: Math.max(0, frame - delay), fps, config: TM.spring });
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: PANEL_W,
        height: PANEL_H,
        backgroundColor: TM.paperHi,
        border: `4px solid ${TM.ink}`,
        boxShadow: `8px 8px 0 rgba(42,36,28,0.14)`,
        opacity: enter,
        transform: `translateY(${interpolate(enter, [0, 1], [26, 0])}px)`,
        overflow: "hidden",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 24px 0" }}>
        <div style={{ fontFamily: TM.fontMono, fontSize: 26, letterSpacing: "0.2em", color: accent, fontWeight: 700 }}>
          {p.kicker}
        </div>
        {/* own date band — the honesty anchor */}
        <div
          style={{
            fontFamily: TM.fontMono,
            fontSize: 21,
            color: TM.inkSoft,
            border: `2px solid ${TM.inkFaint}`,
            padding: "3px 12px",
            borderRadius: 4,
          }}
        >
          {p.dateBand}
        </div>
      </div>
      {children}
    </div>
  );
};

export const FourReadings: React.FC<FourReadingsProps> = ({
  n1,
  n2,
  n3,
  n4,
  activeCount = 4,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const intro = spring({ frame, fps, config: TM.spring });
  const D = [10, 34, 58, 82]; // per-panel delays

  const X0 = (1920 - PANEL_W * 2 - 60) / 2;
  const Y0 = 140;

  return (
    <PaperBackground>
      <div
        style={{
          position: "absolute",
          top: 72,
          width: "100%",
          textAlign: "center",
          fontFamily: TM.fontMono,
          fontSize: 28,
          letterSpacing: "0.26em",
          color: TM.inkSoft,
          opacity: intro,
        }}
      >
        FOUR READINGS · PARALLEL — NOT A CHAIN
      </div>

      {/* N1 price: two endpoints + dashed gap, no smooth curve */}
      {activeCount >= 1 && (
        <PanelShell p={n1} x={X0} y={Y0} delay={D[0]} accent={TM.opiumPurple}>
          {(() => {
            const p = spring({ frame: Math.max(0, frame - D[0] - 10), fps, config: TM.springSlow });
            const x1 = 150, y1 = 150, x2 = PANEL_W - 150, y2 = 320;
            return (
              <svg width={PANEL_W} height={PANEL_H - 70} style={{ position: "absolute", top: 64 }}>
                <line x1={70} y1={340} x2={PANEL_W - 70} y2={340} stroke={TM.inkFaint} strokeWidth={2.5} />
                <circle cx={x1} cy={y1} r={13} fill={TM.opiumPurple} stroke={TM.ink} strokeWidth={3} opacity={p} />
                <text x={x1} y={y1 - 26} textAnchor="middle" fontFamily={TM.fontMono} fontWeight={700} fontSize={32} fill={TM.ink} opacity={p}>
                  {n1.from}
                </text>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x1 + (x2 - x1) * p}
                  y2={y1 + (y2 - y1) * p}
                  stroke={TM.opiumPurple}
                  strokeWidth={4}
                  strokeDasharray="12 14"
                />
                <circle cx={x2} cy={y2} r={13} fill={TM.opiumPurple} stroke={TM.ink} strokeWidth={3} opacity={p} />
                <text x={x2} y={y2 - 26} textAnchor="middle" fontFamily={TM.fontMono} fontWeight={700} fontSize={32} fill={TM.ink} opacity={p}>
                  {n1.to}
                </text>
                <text x={PANEL_W / 2} y={120} textAnchor="middle" fontFamily={TM.fontHeading} fontWeight={700} fontSize={56} fill={TM.opiumPurple} opacity={p}>
                  {n1.headline}
                </text>
                {n1.sub && (
                  <text x={PANEL_W / 2} y={385} textAnchor="middle" fontFamily={TM.fontBody} fontSize={22} fill={TM.inkSoft} opacity={p}>
                    {n1.sub} · two data points — gap not interpolated
                  </text>
                )}
              </svg>
            );
          })()}
        </PanelShell>
      )}

      {/* N2 volume: two bars */}
      {activeCount >= 2 && (
        <PanelShell p={n2} x={X0 + PANEL_W + 60} y={Y0} delay={D[1]} accent={TM.qingBlue}>
          {(() => {
            const p = spring({ frame: Math.max(0, frame - D[1] - 10), fps, config: TM.springSlow });
            // keep bar labels clear of the headline row (no overlap at full height)
            const maxH = 155;
            const h1 = (n2.fromVal / Math.max(n2.fromVal, n2.toVal)) * maxH * p;
            const h2 = (n2.toVal / Math.max(n2.fromVal, n2.toVal)) * maxH * p;
            return (
              <svg width={PANEL_W} height={PANEL_H - 70} style={{ position: "absolute", top: 64 }}>
                <line x1={70} y1={330} x2={PANEL_W - 70} y2={330} stroke={TM.inkFaint} strokeWidth={2.5} />
                <rect x={230} y={330 - h1} width={110} height={h1} fill={TM.paperLo} stroke={TM.ink} strokeWidth={3} />
                <rect x={520} y={330 - h2} width={110} height={h2} fill={TM.qingBlue} stroke={TM.ink} strokeWidth={3} />
                <text x={285} y={330 - h1 - 14} textAnchor="middle" fontFamily={TM.fontMono} fontWeight={700} fontSize={30} fill={TM.ink} opacity={p}>
                  {n2.fromLabel}
                </text>
                <text x={575} y={330 - h2 - 14} textAnchor="middle" fontFamily={TM.fontMono} fontWeight={700} fontSize={30} fill={TM.ink} opacity={p}>
                  {n2.toLabel}
                </text>
                <text x={PANEL_W / 2} y={100} textAnchor="middle" fontFamily={TM.fontHeading} fontWeight={700} fontSize={56} fill={TM.qingBlue} opacity={p}>
                  {n2.headline}
                </text>
              </svg>
            );
          })()}
        </PanelShell>
      )}

      {/* N3 silver: big number + outflow glyph */}
      {activeCount >= 3 && (
        <PanelShell p={n3} x={X0} y={Y0 + PANEL_H + 44} delay={D[2]} accent={TM.silver}>
          {(() => {
            const p = spring({ frame: Math.max(0, frame - D[2] - 10), fps, config: TM.springSlow });
            return (
              <div style={{ position: "absolute", top: 90, width: "100%", textAlign: "center", opacity: p }}>
                <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 108, color: TM.silver, lineHeight: 1 }}>
                  {n3.headline}
                </div>
                <div style={{ fontFamily: TM.fontBody, fontSize: 28, color: TM.inkSoft, marginTop: 16 }}>{n3.sub}</div>
                <svg width={340} height={60} style={{ marginTop: 10 }}>
                  <line x1={20} y1={30} x2={280} y2={30} stroke={TM.silver} strokeWidth={5} strokeDasharray="16 12" />
                  <path d="M 280 30 L 258 18 L 264 30 L 258 42 Z" fill={TM.silver} />
                  <text x={150} y={16} textAnchor="middle" fontFamily={TM.fontMono} fontSize={20} fill={TM.inkSoft}>
                    OUT OF CHINA
                  </text>
                </svg>
              </div>
            );
          })()}
        </PanelShell>
      )}

      {/* N4 exchange: conversion strip */}
      {activeCount >= 4 && (
        <PanelShell p={n4} x={X0 + PANEL_W + 60} y={Y0 + PANEL_H + 44} delay={D[3]} accent={TM.britishRed}>
          {(() => {
            const p = spring({ frame: Math.max(0, frame - D[3] - 10), fps, config: TM.springSlow });
            return (
              <div style={{ position: "absolute", top: 100, width: "100%", textAlign: "center", opacity: p }}>
                <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 40 }}>
                  <div style={{ fontFamily: TM.fontMono, fontWeight: 700, fontSize: 62, color: TM.inkSoft }}>{n4.fromRate}</div>
                  <div style={{ fontFamily: TM.fontHeading, fontSize: 52, color: TM.inkFaint }}>→</div>
                  <div style={{ fontFamily: TM.fontMono, fontWeight: 700, fontSize: 62, color: TM.britishRed }}>{n4.toRate}</div>
                </div>
                <div style={{ fontFamily: TM.fontHeading, fontWeight: 700, fontSize: 52, color: TM.britishRed, marginTop: 24 }}>
                  {n4.headline}
                </div>
                <div style={{ fontFamily: TM.fontBody, fontSize: 26, color: TM.inkSoft, marginTop: 10 }}>{n4.sub}</div>
              </div>
            );
          })()}
        </PanelShell>
      )}
    </PaperBackground>
  );
};
