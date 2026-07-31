import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BgmUnderVo } from "./BgmUnderVo";
import { EventSfx } from "./EventSfx";
import { TRIPTYCH, TRIPTYCH_LEGEND, triptychColor } from "../triptych-palette";

/**
 * cp1-co-triptych-demo — 60s cold-open demo (NF_DIRECTOR, 2026-07-20).
 *
 * Same audio + same VO + same duration structure as cp1-co. The ONLY thing
 * that changes is the visual layer + palette: this is the CEO A/B against the
 * shipped McKinsey-grey preview. Six perceptible differences vs cp1-co, each
 * landing on a named second (see DEMO_NOTE.md):
 *   1. palette breaks out of grey-blue (deep navy ocean, saturated factions)
 *   2. object-ized number: 21,000,000 silver dollars as a bullion stack + pop + SFX
 *   3. PersistentMapBg + ArchiveInset (map stays under, archive in a window)
 *   4. GlobeZoomToLocal in the first 15s (globe -> Canton)
 *   5. QuoteCard dark + large
 *   6. >=3 keyframe SFX (bullion drop / map turn / quote-in)
 *
 * Reuses the shipped CO stem (sec_01_cold_open.wav) + BgmUnderVo + EventSfx;
 * adds three demo SFX hits on top. No TTS/script rewrite.
 */

const AUDIO_CO = "the-moment/audio/sec_01_cold_open.wav";

// demo SFX overlay — object/keyframe sounds (§1.6). Reuse the run's existing
// royalty-free stamp/paper/cannon; volumes <= -12dB-ish so VO stays on top.
const DEMO_SFX = {
  drop: "the-moment/audio/sfx/sfx_stamp.mp3", // bullion/coin落位 — dry stamp thud
  turn: "the-moment/audio/sfx/sfx_paper.mp3", // map fill / globe turn
  quote: "the-moment/audio/sfx/sfx_cannon_distant.mp3", // quote-in low hit
} as const;

/* ============================ shared chrome ============================ */

/** YearChip — right-top hard stamp, always on (2gf §2, ❌2/❌6). */
const YearChip: React.FC<{ year: string; sub?: string; delay?: number }> = ({
  year,
  sub,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 16, stiffness: 160 } });
  return (
    <div
      style={{
        position: "absolute",
        right: 60,
        top: 54,
        transform: `scale(${0.85 + s * 0.15})`,
        opacity: s,
        background: TRIPTYCH.qingRed,
        color: TRIPTYCH.onDark,
        padding: "12px 22px",
        borderRadius: 4,
        boxShadow: "0 6px 20px rgba(0,0,0,0.45)",
        textAlign: "right",
      }}
    >
      <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 46, fontWeight: 800, letterSpacing: "0.06em", lineHeight: 1 }}>
        {year}
      </div>
      {sub ? (
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 18, letterSpacing: "0.18em", opacity: 0.85, marginTop: 6 }}>
          {sub}
        </div>
      ) : null}
    </div>
  );
};

/** FactionLegend — legend BEFORE color (❌2/❌4), left-bottom, always on. */
const FactionLegend: React.FC = () => {
  const frame = useCurrentFrame();
  const op = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        bottom: 54,
        opacity: op,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        background: "rgba(8,36,56,0.72)",
        padding: "14px 18px",
        borderRadius: 6,
        backdropFilter: "blur(2px)",
      }}
    >
      {TRIPTYCH_LEGEND.map((l) => (
        <div key={l.faction} style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ width: 20, height: 12, background: triptychColor(l.faction), borderRadius: 2, display: "inline-block" }} />
          <span style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 17, letterSpacing: "0.1em", color: TRIPTYCH.onDark }}>
            {l.label}
          </span>
        </div>
      ))}
    </div>
  );
};

/* ===================== 1. GlobeZoomToLocal (0–8s) ====================== */
/** globe spin then zoom into East Asia / Canton. First-15s bridge (P0). */
const GlobeZoomToLocal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  // phase A (0-3.5s) spin, phase B (3.5-8s) zoom-to-Canton
  const spin = interpolate(frame, [0, 3.5 * fps], [-40, 20]);
  const zoom = interpolate(frame, [3.5 * fps, 8 * fps], [1, 3.4], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const cx = width / 2;
  const cy = height / 2;
  const R = 320;
  // Canton is on the globe's right-upper quadrant; zoom origin tracks toward it
  const ox = interpolate(frame, [3.5 * fps, 8 * fps], [cx, cx + 120], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const oy = interpolate(frame, [3.5 * fps, 8 * fps], [cy, cy - 70], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pinPop = spring({ frame: frame - 6.2 * fps, fps, config: { damping: 12, stiffness: 180 } });
  return (
    <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 40%, ${TRIPTYCH.oceanHi}, ${TRIPTYCH.oceanDeep})` }}>
      <div style={{ position: "absolute", left: 0, top: 0, width, height, transform: `scale(${zoom})`, transformOrigin: `${ox}px ${oy}px` }}>
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          <defs>
            <radialGradient id="globe" cx="42%" cy="36%">
              <stop offset="0%" stopColor={TRIPTYCH.oceanHi} />
              <stop offset="70%" stopColor={TRIPTYCH.ocean} />
              <stop offset="100%" stopColor={TRIPTYCH.oceanDeep} />
            </radialGradient>
          </defs>
          <circle cx={cx} cy={cy} r={R} fill="url(#globe)" stroke={TRIPTYCH.britGold} strokeWidth={2} opacity={0.9} />
          {/* longitude lines rotating */}
          <g transform={`rotate(${spin} ${cx} ${cy})`} opacity={0.28}>
            {[-3, -2, -1, 0, 1, 2, 3].map((i) => (
              <ellipse key={i} cx={cx} cy={cy} rx={Math.abs(R * Math.cos((i * Math.PI) / 7)) || 2} ry={R} fill="none" stroke={TRIPTYCH.onDark} strokeWidth={1} />
            ))}
            {[-2, -1, 0, 1, 2].map((i) => (
              <line key={`lat${i}`} x1={cx - R} y1={cy + (i * R) / 3} x2={cx + R} y2={cy + (i * R) / 3} stroke={TRIPTYCH.onDark} strokeWidth={1} />
            ))}
          </g>
          {/* East-Asia landmass blob (approx) rotating in with the globe */}
          <g transform={`rotate(${spin * 0.4} ${cx} ${cy})`}>
            <path
              d={`M ${cx + 60} ${cy - 150} q 90 30 110 120 q 10 70 -40 120 q -60 40 -120 10 q -50 -30 -40 -110 q 10 -110 90 -150 z`}
              fill={TRIPTYCH.land}
              opacity={0.92}
            />
          </g>
          {/* Canton pin — at end of zoom, resolve into real Canton factories image so
              the audience actually SEES Canton, not just an abstract dot on a globe (CEO feedback 07-20) */}
          <g transform={`translate(${cx + 110},${cy - 30}) scale(${0.6 + pinPop * 0.6})`} opacity={pinPop}>
            <circle r={13} fill={TRIPTYCH.qingRed} stroke={TRIPTYCH.onDark} strokeWidth={2} />
            <circle r={26} fill="none" stroke={TRIPTYCH.qingRed} strokeWidth={2} opacity={0.5} />
          </g>
        </svg>
        {/* Canton resolve: as zoom caps, the pin opens into the real Thirteen Factories painting */}
        <div
          style={{
            position: "absolute",
            // zoom origin = (cx+120, cy-70); place inset there so it looks like the globe zoomed INTO it
            left: (() => {
              const ox = interpolate(frame, [3.5 * fps, 8 * fps], [cx, cx + 120], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
              return ox - 280;
            })(),
            top: (() => {
              const oy = interpolate(frame, [3.5 * fps, 8 * fps], [cy, cy - 70], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
              return oy - 170;
            })(),
            width: 560,
            height: 340,
            borderRadius: 10,
            overflow: "hidden",
            boxShadow: "0 20px 60px rgba(0,0,0,0.6)",
            border: `3px solid ${TRIPTYCH.britGold}`,
            opacity: interpolate(frame, [6.5 * fps, 8 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            transform: `scale(${interpolate(frame, [6.5 * fps, 8 * fps], [0.7, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })})`,
          }}
        >
          <Img
            src={staticFile("the-moment/engravings/canton_factories.jpg")}
            style={{ width: "100%", height: "100%", objectFit: "cover", filter: "saturate(1.08) contrast(1.05)" }}
          />
          <div
            style={{
              position: "absolute",
              left: 0,
              bottom: 0,
              right: 0,
              padding: "12px 18px",
              background: "linear-gradient(transparent, rgba(8,36,56,0.92))",
            }}
          >
            <div style={{ fontFamily: TRIPTYCH.fontHeading, fontSize: 26, fontWeight: 700, color: TRIPTYCH.onDark }}>
              The Thirteen Factories · Canton
            </div>
            <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 13, letterSpacing: "0.14em", color: TRIPTYCH.onDarkSoft, marginTop: 2 }}>
              广州十三行 · c.1800s · public domain
            </div>
          </div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 60, top: 70, opacity: interpolate(frame, [4 * fps, 5 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 22, letterSpacing: "0.3em", color: TRIPTYCH.onDarkSoft }}>THE MOMENT · EP.1</div>
        <div style={{ fontFamily: TRIPTYCH.fontHeading, fontSize: 58, fontWeight: 800, color: TRIPTYCH.onDark, marginTop: 8 }}>广州 · Canton</div>
      </div>
    </AbsoluteFill>
  );
};

/* =============== ReliefMap base (persistent under content) ============= */
const ReliefMapBg: React.FC<{ fill?: number }> = ({ fill = 1 }) => {
  const { width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const grow = interpolate(frame, [0, 40], [0.4, 1], { extrapolateRight: "clamp" }) * fill;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(circle at 60% 30%, ${TRIPTYCH.ocean}, ${TRIPTYCH.oceanDeep})` }}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ position: "absolute" }}>
        {/* Qing coast landmass (paper land, FillByYear reveal) */}
        <path
          d={`M 0 ${height} L 0 300 Q 480 220 760 360 Q 1000 470 1180 400 Q 1420 300 1920 380 L 1920 ${height} Z`}
          fill={TRIPTYCH.land}
          opacity={0.5 + grow * 0.45}
        />
        <path
          d={`M 0 300 Q 480 220 760 360 Q 1000 470 1180 400 Q 1420 300 1920 380`}
          fill="none"
          stroke={TRIPTYCH.landShadow}
          strokeWidth={3}
          opacity={0.6}
        />
        {/* Canton battle dot + Pearl River route arc */}
        <circle cx={880} cy={430} r={10} fill={triptychColor("qing")} stroke={TRIPTYCH.onDark} strokeWidth={2} />
        <path d={`M 880 430 Q 1250 250 1720 300`} fill="none" stroke={triptychColor("brit")} strokeWidth={4} strokeDasharray="14 10" opacity={0.85 * grow} />
        <circle cx={1720} cy={300} r={8} fill={triptychColor("brit")} />
      </svg>
    </AbsoluteFill>
  );
};

/* ============ 3. PersistentMapBg + ArchiveInset (8–16s) =============== */
const ArchiveInset: React.FC<{ src: string; caption: string; sourceLabel: string; delay?: number }> = ({
  src,
  caption,
  sourceLabel,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 120 } });
  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        top: "46%",
        transform: `translate(-50%,-50%) scale(${0.9 + s * 0.1})`,
        opacity: s,
        width: 980,
        height: 560,
        borderRadius: 14,
        overflow: "hidden",
        boxShadow: "0 24px 70px rgba(0,0,0,0.55)",
        border: `3px solid ${TRIPTYCH.britGold}`,
      }}
    >
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "saturate(1.05) contrast(1.05)" }} />
      <div style={{ position: "absolute", left: 0, bottom: 0, right: 0, padding: "16px 22px", background: "linear-gradient(transparent, rgba(10,30,48,0.9))" }}>
        <div style={{ fontFamily: TRIPTYCH.fontHeading, fontSize: 34, fontWeight: 700, color: TRIPTYCH.onDark }}>{caption}</div>
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 15, letterSpacing: "0.14em", color: TRIPTYCH.onDarkSoft, marginTop: 4 }}>{sourceLabel}</div>
      </div>
    </div>
  );
};

/* ============== 2. GoldCoinRain — object-ized money, coins fall FROM BOTH SIDES (16–30s) ========== */
/** CEO feedback 07-20: "钱没有变成两边落金币的" — coins are gold, fall from left/right edges in
 *  parabolic arcs and pile into a central MOUND (tight cluster, not a wide line) over 16–30s. */
const GoldCoinRain: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Deterministic mound layout: 8 columns, stacked into a bell-curve pile (2-3-4-5-5-4-3-2 = 28 coins).
  // Column x-positions are tight so the pile base is ~400px wide (NOT 800px).
  const COL_X = [-200, -140, -80, -30, 30, 80, 140, 200];
  const COL_HEIGHT = [2, 3, 4, 5, 5, 4, 3, 2]; // coins per column → bell mound
  const COIN_SIZE = 62;
  const COL_STEP = 26; // vertical stack step (px) — slightly less than coin size so they overlap
  // Build the per-coin plan deterministically
  const coinPlan: Array<{
    side: "L" | "R";
    launch: number;
    landX: number;
    landY: number; // negative = above pile centerline
    arcWidth: number;
    rot: number;
  }> = [];
  let i = 0;
  COL_X.forEach((cx, ci) => {
    const h = COL_HEIGHT[ci];
    for (let k = 0; k < h; k++) {
      const side: "L" | "R" = i % 2 === 0 ? "L" : "R";
      // stagger launches across T3: from frame 6 (0.2s in) to ~ frame 380 (12.7s in)
      const launch = 6 + Math.round((i / 27) * 360) + ((i * 17) % 12);
      // land position: column cx, stack upward (negative y = higher on screen)
      const landX = cx + ((i * 41) % 18) - 9; // small jitter ±9px
      const landY = -(k * COL_STEP) + ((i * 29) % 8) - 4; // jitter ±4px
      // arc width — outer columns arc wider, center columns arc tighter
      const arcWidth = 340 + Math.abs(cx) * 0.7 + ((i * 53) % 80);
      const rot = ((i * 137) % 720) - 360;
      coinPlan.push({ side, launch, landX, landY, arcWidth, rot });
      i++;
    }
  });

  // Pile centerline is shifted UP so coins visibly mound in the center of the screen
  // (top:50% puts y=0 on the sea/land wave line; -60 moves the pile base up onto the land)
  const PILE_BASE_Y = -60;

  return (
    <AbsoluteFill style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
      {/* coin stage */}
      <div style={{ position: "relative", width: 900, height: 400 }}>
        {/* glowing treasure-hoard under the pile */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: 460,
            height: 180,
            marginLeft: -230,
            marginTop: PILE_BASE_Y - 40,
            background: "radial-gradient(ellipse at 50% 70%, rgba(255,220,120,0.55), rgba(212,160,23,0.25) 40%, transparent 75%)",
            filter: "blur(6px)",
          }}
        />
        {coinPlan.map((c, idx) => {
          const localFrame = frame - c.launch;
          const flight = 40; // ~1.3s of flight — long enough that viewers SEE the arc across the screen
          const t = Math.max(0, Math.min(1, localFrame / flight));
          // parabolic arc: x from ±arcWidth (well off-screen on L/R) to landX
          const startX = c.side === "L" ? -c.arcWidth : c.arcWidth;
          const x = startX + (c.landX - startX) * t;
          // Pour-in arc: coins enter from the LEFT/RIGHT edges at upper height (y = -120, in the sky),
          // arc UP slightly to a visible peak (-200), then DROP onto the mound at endY (around -60).
          // This looks like money pouring in from both sides, not falling straight down.
          // Stage is 400px tall, center is y=0; keep arc fully on screen: y ∈ [-220, +100].
          const startY = -120; // coin enters L/R in the upper-sky region
          const peakY = -180;  // rainbow peak, still well inside the 400px stage (stage top = -200)
          const endY = c.landY + PILE_BASE_Y;
          // piecewise parabola: 0→0.5 go up, 0.5→1 come down
          const y =
            t < 0.5
              ? startY + (peakY - startY) * (1 - Math.pow(1 - t / 0.5, 2)) // ease-up arc to peak
              : peakY + (endY - peakY) * Math.pow((t - 0.5) / 0.5, 2); // ease-down to pile
          const rot = c.rot * t;
          const opacity = localFrame < 0 ? 0 : localFrame < 4 ? localFrame / 4 : 1;
          // small bounce on landing (t>1): squash 1.0 → 1.12 → 1.0 over 6 frames
          const landBounce =
            localFrame > flight
              ? 1 + 0.12 * Math.exp(-(localFrame - flight) / 6) * Math.cos((localFrame - flight) * 1.2)
              : 1;
          // coins in-flight get slightly larger + trail glow to make them visible across the screen
          const inFlight = localFrame >= 0 && localFrame < flight;
          return (
            <div
              key={idx}
              style={{
                position: "absolute",
                left: "50%",
                top: "50%",
                width: COIN_SIZE,
                height: COIN_SIZE,
                marginLeft: -COIN_SIZE / 2,
                marginTop: -COIN_SIZE / 2,
                transform: `translate(${x}px, ${y}px) rotate(${rot}deg) scale(${landBounce})`,
                opacity,
                borderRadius: "50%",
                background: `radial-gradient(circle at 35% 30%, #FFF3B0, ${TRIPTYCH.britGold} 55%, #8C6A0B)`,
                border: `2px solid #7A5C08`,
                boxShadow: inFlight
                  ? `0 0 18px rgba(255,210,90,0.7), 0 6px 14px rgba(0,0,0,0.5), inset 0 2px 5px rgba(255,255,255,0.6)`
                  : "0 6px 14px rgba(0,0,0,0.5), inset 0 2px 5px rgba(255,255,255,0.6), inset 0 -3px 6px rgba(120,80,10,0.5)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: TRIPTYCH.fontMono,
                fontSize: 20,
                color: "#5A3F05",
                fontWeight: 900,
                textShadow: "0 1px 0 rgba(255,255,255,0.4)",
                zIndex: inFlight ? 5 : 3,
              }}
            >
              $
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: -20, textAlign: "center", position: "relative", zIndex: 2 }}>
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 84, fontWeight: 800, color: TRIPTYCH.britGold, letterSpacing: "0.02em", textShadow: "0 4px 22px rgba(0,0,0,0.65), 0 0 30px rgba(212,160,23,0.3)" }}>
          21,000,000
        </div>
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 26, letterSpacing: "0.24em", color: TRIPTYCH.onDark, marginTop: 6 }}>
          SILVER DOLLARS · TREATY INDEMNITY
        </div>
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 17, letterSpacing: "0.14em", color: TRIPTYCH.onDarkSoft, marginTop: 8 }}>
          ~ est. Treaty of Nanking, 1842 · paid in Spanish silver dollars
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ============ DateClash 1842 -> 1813 (saturated) (30–42s) ============= */
const DateClashTri: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const strike = spring({ frame: frame - 5.5 * fps, fps, config: { damping: 14, stiffness: 150 } });
  const rightIn = spring({ frame: frame - 6.5 * fps, fps, config: { damping: 18, stiffness: 120 } });
  return (
    <AbsoluteFill style={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 40 }}>
      <div style={{ textAlign: "center", position: "relative", opacity: interpolate(strike, [0, 1], [1, 0.4]) }}>
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 150, fontWeight: 800, color: triptychColor("qing") }}>1842</div>
        <div style={{ fontFamily: TRIPTYCH.fontBody, fontSize: 26, color: TRIPTYCH.onDark, maxWidth: 420 }}>Nanking — the gunboats, the treaty</div>
        {/* strike-through */}
        <div style={{ position: "absolute", top: "42%", left: 0, height: 8, background: triptychColor("brit"), width: `${strike * 100}%`, boxShadow: `0 0 12px ${TRIPTYCH.britGold}` }} />
      </div>
      <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 70, color: TRIPTYCH.britGold, opacity: rightIn }}>→</div>
      <div style={{ textAlign: "center", opacity: rightIn, transform: `translateX(${interpolate(rightIn, [0, 1], [60, 0])}px)` }}>
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 150, fontWeight: 800, color: triptychColor("brit") }}>1813</div>
        <div style={{ fontFamily: TRIPTYCH.fontBody, fontSize: 26, color: TRIPTYCH.onDark, maxWidth: 420 }}>London — a vote about India</div>
      </div>
    </AbsoluteFill>
  );
};

/* ================= 5. QuoteCard dark + large (42–52s) ================= */
const QuoteCardDark: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 20, stiffness: 90 } });
  return (
    <AbsoluteFill style={{ background: TRIPTYCH.quoteBg, display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 180px" }}>
      <div style={{ opacity: s, transform: `translateY(${interpolate(s, [0, 1], [30, 0])}px)` }}>
        <div style={{ fontFamily: TRIPTYCH.fontHeading, fontSize: 78, fontWeight: 700, lineHeight: 1.18, color: TRIPTYCH.quoteText }}>
          “The war began in London, in a vote — years before the first shot was fired at Canton.”
        </div>
        <div style={{ height: 4, width: 160, background: TRIPTYCH.quoteAccent, margin: "36px 0 20px" }} />
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 24, letterSpacing: "0.14em", color: TRIPTYCH.quoteAccent }}>
          THE MOMENT · thesis
        </div>
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 17, letterSpacing: "0.1em", color: TRIPTYCH.onDarkSoft, marginTop: 10 }}>
          ScholarCredit: framing after historiography of the First Opium War
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ===================== assembly — 60s cold open ======================= */

interface TriBeat {
  from: number;
  to: number;
  name: string;
  node: React.ReactNode;
  /** persistent relief map under the content (2gf double-layer) */
  map?: boolean;
}

const TRI_BEATS: TriBeat[] = [
  { from: 0, to: 8, name: "T1 globe zoom to Canton", node: <GlobeZoomToLocal /> },
  {
    from: 8,
    to: 16,
    name: "T2 archive inset over map",
    map: true,
    node: (
      <>
        <ArchiveInset
          src="the-moment/engravings/ship_hms_wellesley.jpg"
          caption="A British warship off Nanking"
          sourceLabel="RMG PU5981 · public domain"
          delay={6}
        />
        <YearChip year="AUG 1842" sub="OFF NANKING" delay={10} />
      </>
    ),
  },
  {
    from: 16,
    to: 30,
    name: "T3 gold coin rain — 21,000,000",
    map: true,
    node: (
      <>
        <GoldCoinRain />
        <YearChip year="1842" sub="THE INDEMNITY" delay={6} />
      </>
    ),
  },
  {
    from: 30,
    to: 42,
    name: "T4 date clash 1842 -> 1813",
    map: true,
    node: (
      <>
        <DateClashTri />
        <YearChip year="1813" sub="THE REAL START" delay={190} />
      </>
    ),
  },
  { from: 42, to: 52, name: "T5 quote card dark large", node: <QuoteCardDark /> },
  {
    from: 52,
    to: 60,
    name: "T6 hold the thread — Canton map",
    map: true,
    node: (
      <>
        <AbsoluteFill style={{ display: "flex", justifyContent: "center", alignItems: "flex-start", paddingTop: 140 }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 24, letterSpacing: "0.28em", color: TRIPTYCH.onDarkSoft }}>THE MOMENT · EPISODE ONE</div>
            <div style={{ fontFamily: TRIPTYCH.fontHeading, fontSize: 66, fontWeight: 800, color: TRIPTYCH.onDark, marginTop: 12 }}>
              Let’s go find the vote about India.
            </div>
          </div>
        </AbsoluteFill>
        <YearChip year="1813 → 1842" delay={6} />
      </>
    ),
  },
];

const fmtTc = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

// demo SFX overlay — object/keyframe sounds (§1.6). Coin landings fire repeatedly 17→28s so
// the gold rain has a real audible "shower of coins" texture, not one dry thud (CEO feedback 07-20).
const DEMO_HITS: Array<{ at: number; src: keyof typeof DEMO_SFX; volume: number; name: string }> = [
  { at: 8.4, src: "turn", volume: 0.22, name: "sfx-map-turn-in" },
  // coin landings — one thud every ~0.8s across the rain beat, slight volume rolloff
  ...Array.from({ length: 14 }).map((_, i) => ({
    at: 17 + i * 0.82,
    src: "drop" as const,
    volume: 0.12 + (i === 0 ? 0.08 : 0), // first hit a touch louder
    name: `sfx-coin-land-${i}`,
  })),
  { at: 42.2, src: "quote", volume: 0.2, name: "sfx-quote-in" },
];

export const Cp1ColdOpenTriptych: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: TRIPTYCH.oceanDeep }}>
      {TRI_BEATS.map((b) => {
        const from = Math.round(b.from * fps);
        const dur = Math.max(1, Math.round(b.to * fps) - from);
        return (
          <Sequence key={b.name} from={from} durationInFrames={dur} name={b.name}>
            {b.map ? <ReliefMapBg /> : null}
            {b.node}
            <FactionLegend />
            <div
              style={{
                position: "absolute",
                right: 60,
                bottom: 40,
                fontFamily: TRIPTYCH.fontMono,
                fontSize: 20,
                letterSpacing: "0.1em",
                color: TRIPTYCH.onDarkSoft,
                opacity: 0.6,
                textAlign: "right",
              }}
            >
              {fmtTc(b.from)} · {b.name} · TRIPTYCH DEMO
            </div>
          </Sequence>
        );
      })}
      {/* reused audio: CO stem + BGM bed + shipped event SFX */}
      <Audio src={staticFile(AUDIO_CO)} />
      <BgmUnderVo label="CO" />
      <EventSfx label="CO" />
      {/* demo SFX overlay */}
      {DEMO_HITS.map((h) => (
        <Sequence key={h.name} from={Math.round(h.at * fps)} durationInFrames={Math.round(2 * fps)} name={h.name} layout="none">
          <Audio src={staticFile(DEMO_SFX[h.src])} volume={h.volume} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

/** 60s @ fps */
export const triptychDemoDuration = (fps: number): number => Math.round(60 * fps);
