/**
 * SentenceShot — 21 句话 = 21 shots, CO 冷开场 v5 (CEO 07-20 反馈：一句话一画面)
 *
 * 15 OM-native 程序化 shots 在此文件实现；6 ComfyUI Wan2.2 shots 由 Win 机 5070ti 渲染后
 * 作为 <Video> 静态底（或在 assemble 阶段 ffmpeg 拼接）。本文件 OM 端先把所有可程序化
 * 的 shot 都注册成 composition，输出独立 mp4 供 ffmpeg 拼接。
 *
 * 设计：
 * - 每个 Shot 是一个短 composition (时长 = 对应 VO 句子时长)
 * - 同屏 motion 在一个 shot 内完成（如 S02 条约桌面三条 pop + 金币堆）
 * - 转场不在 OM 做，留给 OM 后 burn overlay 或 FCP（本文件只输出干净 shot 本体 + 可选 burn alpha）
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TRIPTYCH, TRIPTYCH_LEGEND, triptychColor } from "../triptych-palette";
import { TM } from "../theme";

/* ============================================================
 * G1 — shared old-paper design token (07-22 CEO review: unify CO's
 * background to match CH1-EP, which is built against theme.ts's TM tokens,
 * not the triptych-palette.ts dark-navy re-skin CO had drifted onto).
 * ============================================================ */

export const OldPaperCard: React.FC<{ children?: React.ReactNode; variant?: "light" | "dark" | "bloodRed" }> = ({ children, variant = "light" }) => {
  const bg =
    variant === "bloodRed" ? `linear-gradient(180deg, #3A1210 0%, #2A0D0C 100%)` // S06 "深红纸质感"
    : variant === "dark" ? `radial-gradient(ellipse at 50% 45%, #2E2721, #1C1712)` // aged/charcoal paper for date-punch numerals
    : `radial-gradient(ellipse at 50% 40%, ${TM.paperHi}, ${TM.paper} 70%, ${TM.paperLo})`;
  return (
    <AbsoluteFill style={{ background: bg, fontFamily: TM.fontHeading, color: variant === "light" ? TM.ink : TM.paper }}>
      {children}
    </AbsoluteFill>
  );
};

/* ============================================================
 * Shared chrome
 * ============================================================ */

export const Paper: React.FC<{ children?: React.ReactNode; dark?: boolean }> = ({ children, dark }) => (
  <AbsoluteFill
    style={{
      background: dark
        ? `radial-gradient(circle at 50% 40%, ${TRIPTYCH.oceanHi}, ${TRIPTYCH.oceanDeep})`
        : TRIPTYCH.quoteBg,
      fontFamily: TRIPTYCH.fontMono,
      color: TRIPTYCH.onDark,
    }}
  >
    {children}
  </AbsoluteFill>
);

export const Label: React.FC<{ children: React.ReactNode; x?: number; y?: number; size?: number; opacity?: number }> = ({
  children, x = 60, y = 60, size = 18, opacity = 0.7,
}) => (
  <div style={{ position: "absolute", left: x, top: y, fontSize: size, letterSpacing: "0.2em", opacity, fontFamily: TRIPTYCH.fontMono, color: TRIPTYCH.onDarkSoft }}>
    {children}
  </div>
);

/* ============================================================
 * S02 — Treaty table with three sequential items + gold coin pour
 * (VO: signing away five ports, an island called Hong Kong, 21M silver dollars)
 * ============================================================ */

const TreatyTable: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // VO timings within S02 (9.43s total). Word-boundary timing (VO is ~0.8s in before first clause):
  //   "officials signing…" ~ 1.0s
  //   "five ports" ~ 2.5s
  //   "Hong Kong" ~ 5.2s
  //   "twenty-one million silver dollars" ~ 7.2s
  const portStart = 2.0 * fps;
  const hkStart = 4.8 * fps;
  const coinStart = 6.8 * fps;
  const portS = spring({ frame: frame - portStart, fps, config: { damping: 14, stiffness: 160 } });
  const hkS = spring({ frame: frame - hkStart, fps, config: { damping: 14, stiffness: 160 } });
  const coinCardS = spring({ frame: frame - coinStart, fps, config: { damping: 14, stiffness: 160 } });

  return (
    <AbsoluteFill style={{ background: TM.paper }}>
      {/* Table / parchment background — narrower so the 3 cards fit on it */}
      <div style={{ position: "absolute", left: 80, right: 80, top: 180, bottom: 100, background: "#EFE6D3", borderRadius: 8, boxShadow: "0 30px 80px rgba(0,0,0,0.6)", transform: "perspective(1200px) rotateX(6deg)" }}>
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 30% 20%, rgba(255,240,200,0.4), transparent 60%), radial-gradient(ellipse at 70% 80%, rgba(100,70,20,0.15), transparent 60%)", borderRadius: 8 }} />
        <div style={{ position: "absolute", left: 50, top: 30, fontSize: 34, opacity: 0.55 }}>✒</div>
        <div style={{ position: "absolute", right: 50, top: 40, width: 52, height: 52, borderRadius: "50%", background: TRIPTYCH.qingRed, boxShadow: "0 4px 10px rgba(0,0,0,0.4)", opacity: 0.85, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, color: TRIPTYCH.onDark, fontFamily: TRIPTYCH.fontHeading }}>N</div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 32, textAlign: "center", fontFamily: TRIPTYCH.fontHeading, fontSize: 28, color: "#2A241C", letterSpacing: "0.08em" }}>
          TREATY OF NANKING · 1842
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 70, textAlign: "center", fontFamily: TRIPTYCH.fontMono, fontSize: 13, color: "#6B5D3F", letterSpacing: "0.2em" }}>
          ARTICLES OF CEDED TERRITORY & INDEMNITY
        </div>

        {/* Three cards in a row: ports / HK / indemnity-chest */}
        <div style={{ position:"absolute", left:60, right:60, top:120, bottom:140, display:"flex", gap: 24, alignItems:"stretch" }}>
          {/* Card 1: 5 ports — 5 port icons (enlarged to ≥18% card width per
              V6, was 56px/unreadable) + big FIVE PORTS. Each also gets a big
              faded grayscale watermark of the same icon surfacing behind the
              card (V6: "剪影效果logo放大以后水印一样浮出水面") */}
          <div style={{
                flex:1, opacity: portS, transform:`translateY(${(1-portS)*30}px)`,
                padding: "24px 22px 18px", background: "rgba(255,250,235,0.97)", borderRadius: 6,
                boxShadow: "0 10px 30px rgba(0,0,0,0.3)", borderLeft: `8px solid ${TRIPTYCH.local}`,
                display:"flex", flexDirection:"column", justifyContent:"space-between", position:"relative", overflow:"hidden" }}>
            <Img src={staticFile("the-moment/icons/canton.png")} style={{
              position:"absolute", right:-30, bottom:-30, width:220, height:220, objectFit:"cover", borderRadius:"50%",
              filter:"grayscale(1)", opacity: portS * 0.12, transform:`translateY(${(1-portS)*60}px)`,
            }} />
            <div style={{ fontFamily: TRIPTYCH.fontHeading, fontSize: 46, fontWeight: 800, color: TRIPTYCH.local, lineHeight: 1.0, marginTop: 4, position:"relative" }}>
              FIVE<br/>PORTS
            </div>
            {/* 07-23: enlarged 100px→150px per user feedback ("城市logo咋还是
                这么小") — 3+2 layout at this size actually fills the card
                instead of reading as a row of tiny thumbnails */}
            <div style={{ display:"flex", gap: 10, marginTop: 14, flexWrap:"wrap", position:"relative" }}>
              {["canton","amoy","foochow","ningpo","shanghai"].map((c, i) => (
                <div key={c} style={{
                  width: 150, height: 150, borderRadius: "50%", overflow:"hidden",
                  border: `4px solid ${TRIPTYCH.britGold}`,
                  boxShadow: "0 3px 10px rgba(0,0,0,0.35)",
                  opacity: portS > (i+1)/6 ? 1 : 0,
                  transform: `scale(${portS > (i+1)/6 ? 1 : 0.5})`,
                }}>
                  <Img src={staticFile(`the-moment/icons/${c}.png`)} style={{ width:"100%", height:"100%", objectFit:"cover" }} />
                </div>
              ))}
            </div>
          </div>
          {/* Card 2: HK — same enlarge + watermark-surfacing treatment (V6:
              "HK beat 没做剪影效果logo放大以后水印一样浮出水面") */}
          <div style={{
                flex:1, opacity: hkS, transform:`translateY(${(1-hkS)*30}px)`,
                padding: "24px 22px 18px", background: "rgba(255,250,235,0.97)", borderRadius: 6,
                boxShadow: "0 10px 30px rgba(0,0,0,0.3)", borderLeft: `8px solid ${TRIPTYCH.britNavy}`,
                display:"flex", flexDirection:"column", justifyContent:"space-between", position:"relative", overflow:"hidden" }}>
            <Img src={staticFile("the-moment/icons/hongkong.png")} style={{
              position:"absolute", right:-40, bottom:-40, width:260, height:260, objectFit:"cover", borderRadius:"50%",
              filter:"grayscale(1)", opacity: hkS * 0.14, transform:`translateY(${(1-hkS)*60}px)`,
            }} />
            <div style={{ fontFamily: TRIPTYCH.fontHeading, fontSize: 46, fontWeight: 800, color: TRIPTYCH.britNavy, lineHeight: 1.0, marginTop: 4, position:"relative" }}>
              HONG<br/>KONG
            </div>
            {/* 07-23: enlarged 140px→190px to match the ports medallion fix */}
            <div style={{
              width: 190, height: 190, borderRadius: "50%", overflow:"hidden",
              border: `5px solid ${TRIPTYCH.britGold}`, marginTop: 12, position:"relative",
              boxShadow: "0 5px 14px rgba(0,0,0,0.4)",
            }}>
              <Img src={staticFile("the-moment/icons/hongkong.png")} style={{ width:"100%", height:"100%", objectFit:"cover" }} />
            </div>
          </div>
          {/* Card 3: 21M — treasure-chest card that COINS POUR DOWN INTO */}
          <div style={{
                flex:1, opacity: coinCardS, transform:`translateY(${(1-coinCardS)*30}px)`,
                // 21M is SILVER dollars — was tinted gold throughout, a real
                // historical-accuracy bug (07-22 review)
                padding: "18px 22px 14px", background: "linear-gradient(180deg, rgba(240,244,248,0.98), rgba(150,164,178,0.22))",
                borderRadius: 6,
                boxShadow: "0 10px 30px rgba(0,0,0,0.3), inset 0 -4px 12px rgba(90,100,110,0.25)",
                borderLeft: `8px solid ${TM.silver}`, borderBottom: `4px solid #5C6570`,
                display:"flex", flexDirection:"column", justifyContent:"space-between", position:"relative", overflow:"hidden" }}>
            <div style={{ fontFamily: TM.fontHeading, fontSize: 42, fontWeight: 800, color: "#3E4A54", lineHeight: 1.0, marginTop: 4, zIndex: 5 }}>
              21M<br/>SILVER
            </div>
            {/* Coins pile accumulating at bottom of card */}
            <CoinChestFill startFrame={coinStart} />
          </div>
        </div>

        {/* A treasure barrel/chest at top that tips and pours coins down into card 3 */}
        <GoldPourFromTop startFrame={coinStart} />
      </div>

      <div style={{ position: "absolute", left: 60, top: 54 }}>
        <div style={{ fontFamily: TRIPTYCH.fontMono, fontSize: 20, letterSpacing: "0.3em", color: TRIPTYCH.onDarkSoft }}>ON HER DECK</div>
        <div style={{ fontFamily: TRIPTYCH.fontHeading, fontSize: 40, fontWeight: 800, color: TRIPTYCH.onDark, marginTop: 2 }}>Signing away…</div>
      </div>
    </AbsoluteFill>
  );
};
/* Treasure chest at top tipping over, pouring coins straight down into card 3 */
const GoldPourFromTop: React.FC<{ startFrame: number }> = ({ startFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Chest sits above the 3rd card (which is on the right). Parchment is 880px wide inside 80 margins,
  // so card 3 center is around x=+(~300) from paper center. Paper center is at screen center.
  // Chest rendered inside parchment div which is left:80 right:80 top:180 bottom:100
  const COINS = 20; // V6: "瀑布式银元粒子（保方向，加量）" — was 14
  const CHEST_X = 470; // offset from parchment center, in px (toward card 3)
  return (
    <div style={{ position:"absolute", inset:0, pointerEvents:"none", overflow:"visible" }}>
      {/* Chest itself — tips over from upright to pouring */}
      {(() => {
        const tip = spring({ frame: frame - startFrame, fps, config: { damping: 14, stiffness: 90 } });
        const angle = -10 + tip * -100; // rotate from -10deg (tilted forward) to -110deg (pouring down)
        return (
          <div style={{
            position:"absolute", left: `calc(50% + ${CHEST_X - 80}px)`, top: 20,
            width: 120, height: 90, transform: `rotate(${angle}deg)`, transformOrigin: "bottom left",
            zIndex: 10,
          }}>
            {/* Chest body */}
            <div style={{
              position:"absolute", left:0, top:20, width:120, height:65,
              background:"linear-gradient(180deg, #8B4513 0%, #5A2D0C 100%)",
              borderRadius: "6px 6px 10px 10px",
              border: "3px solid #3E1F08",
              boxShadow: "0 6px 14px rgba(0,0,0,0.5)",
            }}>
              {/* Iron bands */}
              <div style={{ position:"absolute", left:0, right:0, top:20, height:6, background:"#3a2a1a" }}/>
              <div style={{ position:"absolute", left:0, right:0, top:44, height:6, background:"#3a2a1a" }}/>
              {/* Lock */}
              <div style={{ position:"absolute", left:"50%", top:30, marginLeft:-7, width:14, height:14, background:TM.silver, borderRadius:2 }}/>
            </div>
            {/* Lid — opens */}
            <div style={{
              position:"absolute", left:-4, top:0, width:128, height:26,
              background:"linear-gradient(180deg, #A0522D 0%, #6B3010 100%)",
              borderRadius: "10px 10px 2px 2px",
              border: "3px solid #3E1F08",
              transform: `rotate(${tip * -50}deg)`, transformOrigin:"bottom left",
            }}/>
          </div>
        );
      })()}
      {/* Coins pouring from chest mouth straight down into card 3 */}
      {Array.from({length: COINS}).map((_, i) => {
        const launch = 10 + i * 5;
        const lf = frame - startFrame - launch;
        if (lf < 0) return null;
        // Each coin falls in a near-vertical trajectory with slight L jitter, over ~30 frames
        const fallT = Math.min(1, lf / 32);
        const x = CHEST_X + Math.sin(i*1.7)*18 + fallT*(-8 + (i%3)*8);
        // start above the chest (y=-120 from parchment center) → end at bottom of card (y=170)
        const y = -90 + fallT * 300;
        const rot = lf * 12 + i*40;
        const op = lf < 4 ? lf/4 : 1;
        return (
          <div key={i} style={{
            position:"absolute", left:`calc(50% + ${x}px)`, top: `calc(50% + ${y}px)`,
            width: 26, height: 26, marginLeft:-13, marginTop:-13,
            borderRadius:"50%",
            background:`radial-gradient(circle at 35% 30%, #F4F7FA, ${TM.silver} 55%, #5C6570)`,
            border:"1.5px solid #4A535C",
            boxShadow:"0 0 8px rgba(200,210,220,0.6), 0 2px 4px rgba(0,0,0,0.4)",
            transform:`rotate(${rot}deg)`, opacity: op, zIndex: 8,
            display:"flex", alignItems:"center", justifyContent:"center",
            fontFamily: TM.fontMono, fontSize: 11, color:"#2E353C", fontWeight:900,
          }}>$</div>
        );
      })}
    </div>
  );
};

/* Pile of coins accumulating at the bottom of card 3 */
const CoinChestFill: React.FC<{ startFrame: number }> = ({ startFrame }) => {
  const frame = useCurrentFrame();
  // coins land 1 by 1 into a small pile at the bottom of the card
  const COINS = 26; // V6: "加量" — was 16
  const COL_X = [-84, -49, -14, 21, 56, 91];
  const COL_H = [3, 5, 6, 6, 4, 2]; // bell curve, one more column than before
  const plan: Array<{lx:number; ly:number; launch:number; rot:number}> = [];
  let idx = 0;
  COL_X.forEach((cx, ci) => {
    for (let k=0; k<COL_H[ci]; k++) {
      plan.push({ lx: cx + ((idx*29)%10) - 5, ly: -(k*15), launch: 36 + idx*5 + ((idx*13)%4), rot: ((idx*71)%360) });
      idx++;
    }
  });
  return (
    <div style={{ position:"absolute", left:0, right:0, bottom: 0, height: 100, zIndex: 3 }}>
      <div style={{ position:"absolute", left:"50%", bottom: 0, width:0, height:0 }}>
        {/* pile glow — 07-23: was a gold glow, switched to a cool silver glow
            to match the coins (still tinted gold below, another instance of
            the same "21M is silver not gold" bug user flagged again) */}
        <div style={{ position:"absolute", left:-110, top:-20, width:220, height:60, background:"radial-gradient(ellipse at center, rgba(200,212,224,0.55), transparent 70%)", filter:"blur(4px)" }} />
        {plan.slice(0, COINS).map((p, i) => {
          const lf = frame - startFrame - p.launch;
          const t = Math.max(0, Math.min(1, lf/10));
          const bounce = lf > 10 ? 1 + 0.08*Math.exp(-(lf-10)/5)*Math.cos((lf-10)*1.2) : 1;
          return (
            <div key={i} style={{
              position:"absolute",
              left: p.lx - 12, bottom: -p.ly,
              width: 24, height: 24,
              borderRadius:"50%",
              background:`radial-gradient(circle at 35% 30%, #F4F7FA, ${TM.silver} 55%, #5C6570)`,
              border:"1.5px solid #4A535C",
              boxShadow:"0 3px 6px rgba(0,0,0,0.4), inset 0 1px 2px rgba(255,255,255,0.5)",
              opacity: lf < 0 ? 0 : t,
              transform: `scale(${bounce}) rotate(${p.rot*t}deg)`,
            }}/>
          );
        })}
      </div>
    </div>
  );
};
/* ============================================================
 * S04 / S05 — Stamp slam
 * ============================================================ */

export const StampSlam: React.FC<{ text: string; sub?: string; color?: string; photoSrc?: string }> = ({ text, sub, color = TM.britishRed, photoSrc }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const slam = spring({ frame, fps, config: { damping: 8, stiffness: 400 } });
  const shake = Math.max(0, 1 - frame/12) * Math.sin(frame*1.5) * 6 * slam;
  return (
    <AbsoluteFill style={{ background: "#0c0a06" }}>
      {photoSrc ? (
        // 07-23: sepia/dim dropped for the new crude-anime illustration style
        // (flat colors — a 50% sepia wash was designed for aged photos, not this).
        <EngravingKenBurns src={photoSrc} startScale={1.0} endScale={1.12} sepia={0} dim={0.15} />
      ) : (
        <OldPaperCard variant="dark" />
      )}
      <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", transform:`translate(${shake}px, ${shake*0.5}px) scale(${0.5 + slam*0.5})` }}>
        <div style={{ textAlign:"center" }}>
          <div style={{ fontFamily: TM.fontHeading, fontSize: 200, fontWeight: 900, color, letterSpacing:"0.02em", textShadow:`0 3px 8px rgba(0,0,0,0.8), 0 0 2px rgba(0,0,0,0.9)`, WebkitTextStroke: `1px rgba(0,0,0,0.4)` }}>
            {text}
          </div>
          {sub ? <div style={{ fontFamily: TM.fontMono, fontSize: 28, color: TM.paper, letterSpacing:"0.3em", marginTop: 10, textShadow: "0 2px 6px rgba(0,0,0,0.8)" }}>{sub}</div> : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ============================================================
 * S06 / S17 / S18 / S19 — Big year/date punch
 * ============================================================ */

export const DatePunch: React.FC<{ year: string; sub?: string; color?: string; variant?: "bloodRed" | "dark"; residualSrc?: string }> = ({
  year, sub, color = TM.qingYellow, variant = "dark", residualSrc,
}) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 14, stiffness: 180 } });
  return (
    <OldPaperCard variant={variant}>
      {residualSrc && (
        <Img src={staticFile(residualSrc)} style={{ position:"absolute", inset:0, width:"100%", height:"100%", objectFit:"cover", opacity:0.1, filter:"sepia(0.6) contrast(1.1)" }}/>
      )}
      <div style={{ position:"absolute", inset:0, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", opacity: pop, transform:`scale(${0.7 + pop*0.3})` }}>
        <div style={{ fontFamily: TM.fontHeading, fontSize: height * 0.55, fontWeight: 900, color, letterSpacing:"0.02em", textShadow:`0 4px 16px rgba(0,0,0,0.6)` }}>
          {year}
        </div>
        {sub ? <div style={{ fontFamily: TM.fontMono, fontSize: 26, color: TM.paper, letterSpacing:"0.3em", marginTop: 20, textShadow:"0 2px 6px rgba(0,0,0,0.7)" }}>{sub}</div> : null}
      </div>
    </OldPaperCard>
  );
};

/* ============================================================
 * S07 — Wrong moment stamp
 * ============================================================ */

export const InkSplatter: React.FC<{ appearFrame: number }> = ({ appearFrame }) => {
  const frame = useCurrentFrame();
  const t = Math.max(0, Math.min(1, (frame - appearFrame) / 6));
  if (t <= 0) return null;
  const spots = [
    { x: 62, y: 38, r: 14 }, { x: 68, y: 44, r: 8 }, { x: 58, y: 30, r: 6 },
    { x: 40, y: 58, r: 10 }, { x: 35, y: 52, r: 5 }, { x: 72, y: 33, r: 4 },
  ];
  return (
    <svg style={{ position:"absolute", inset:0, width:"100%", height:"100%" }} viewBox="0 0 100 100" preserveAspectRatio="none">
      {spots.map((s, i) => (
        <circle key={i} cx={s.x} cy={s.y} r={s.r * t} fill={TM.ink} opacity={0.8 * t} />
      ))}
    </svg>
  );
};

/* 07-22: shared backdrop for shots that had no photographic content at all
   (pure flat OldPaperCard) — crossfades a doubao-seedream-5.0-lite first+last
   keyframe pair behind the existing precise foreground graphics/typography,
   which stay code-driven (crisp text/stamps are still better done in Remotion
   than baked into a generated image). Not used on the data/chart shots
   (S02/S06/S14/S17-19/S20) where Alan asked to keep the programmatic approach. */
export const PhotoBGCrossfade: React.FC<{ firstSrc: string; lastSrc: string; revealFrame?: number; dim?: number }> = ({ firstSrc, lastSrc, revealFrame = 0, dim = 0.55 }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const reveal = spring({ frame: frame - revealFrame, fps, config: { damping: 22, stiffness: 140 } });
  const t = Math.min(1, frame / Math.max(1, durationInFrames - 1));
  const zoom = 1.0 + t * 0.06;
  return (
    <div style={{ position:"absolute", inset:0, overflow:"hidden" }}>
      <Img src={staticFile(firstSrc)} style={{ position:"absolute", inset:0, width:"100%", height:"100%", objectFit:"cover", transform:`scale(${zoom})`, opacity: 1 - reveal }} />
      <Img src={staticFile(lastSrc)} style={{ position:"absolute", inset:0, width:"100%", height:"100%", objectFit:"cover", transform:`scale(${zoom})`, opacity: reveal }} />
      <div style={{ position:"absolute", inset:0, background: `rgba(239,230,211,${dim})` }} />
    </div>
  );
};

const WrongMoment: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const FINAL_TILT = -7; // settles tilted, not horizontal (was 0deg — the "非斜盖" bug)
  const slam = spring({ frame, fps, config: { damping: 9, stiffness: 380 } });
  const shake = Math.max(0, 1-frame/10) * Math.sin(frame*2) * 10;
  return (
    <AbsoluteFill style={{ fontFamily: TM.fontHeading, color: TM.ink }}>
      <PhotoBGCrossfade firstSrc="the-moment/engravings/s07_paper_blank_crude.png" lastSrc="the-moment/engravings/s07_paper_stamped_crude.png" revealFrame={4} />
      {/* Faded 1842 ghost behind */}
      <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", opacity:0.2 }}>
        <div style={{ fontFamily: TM.fontMono, fontSize: 280, fontWeight: 900, color: TM.ink, textDecoration:"line-through", textDecorationColor: TM.britishRed, textDecorationThickness: 12 }}>1842</div>
      </div>
      <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", transform:`translate(${shake}px,0) rotate(${FINAL_TILT * slam}deg) scale(${0.4 + slam*0.6})` }}>
        <div style={{
          border:`10px solid ${TM.britishRed}`, padding:"20px 60px", position: "relative",
          background: "rgba(239,230,211,0.15)",
          boxShadow:`2px 4px 0px rgba(42,36,28,0.5)`, // hard matte ink-stamp shadow, not a soft neon glow
        }}>
          <div style={{ fontFamily: TM.fontHeading, fontSize: 180, fontWeight: 900, color: TM.britishRed }}>WRONG</div>
          <div style={{ fontFamily: TM.fontHeading, fontSize: 100, fontWeight: 800, color: TM.britishRed, textAlign:"center", marginTop: -10 }}>MOMENT.</div>
          <InkSplatter appearFrame={2} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ============================================================
 * S04 (merged S04+S05+S06+S07) — 07-23: these were 4 separate shots at
 * 0.82/0.82/1.23/0.82s, each individually under the 3s-minimum-shot-length
 * rule ("关键帧、首尾帧之间最少要差3秒...有些语义切的太碎了"). The VO is one
 * continuous staccato clause (GUNBOATS. / TREATY. / 1842. / WRONG MOMENT.),
 * so instead of adding dead air, they're folded into ONE shot whose internal
 * beats keep their original VO-synced timing exactly via nested <Sequence>
 * (local-frame reset, no code changes needed inside StampSlam/DatePunch/
 * WrongMoment) — only the external hard cuts between them are removed.
 * Combined length 3.69s clears the 3s rule with zero added runtime.
 * ============================================================ */
const GunboatsToWrongMoment: React.FC = () => (
  <AbsoluteFill style={{ background: "#0c0a06" }}>
    <Sequence from={0} durationInFrames={25}>
      <StampSlam text="THE GUNBOATS" photoSrc="the-moment/engravings/s04_gunboat_crude.png" />
    </Sequence>
    <Sequence from={25} durationInFrames={24}>
      <StampSlam text="THE TREATY." color={TM.qingYellow} photoSrc="the-moment/engravings/s05_treaty_crude.png" />
    </Sequence>
    <Sequence from={49} durationInFrames={37}>
      <DatePunch year="1842" color={TM.qingYellow} variant="bloodRed" />
    </Sequence>
    <Sequence from={86} durationInFrames={25}>
      <WrongMoment />
    </Sequence>
  </AbsoluteFill>
);

/* ============================================================
 * S08 — Not 1842 Nanking (strike + slide)
 * ============================================================ */

const StrikeAndSlide: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const strike = spring({ frame, fps, config: { damping: 20, stiffness: 100 } });
  // exit pushed right up against the tail — was [18,45] which left ~40 dead
  // frames of empty background after sliding off (V6: "出画点压镜尾无空窗")
  const exitStart = Math.max(20, durationInFrames - 46);
  // 07-22: missing extrapolateLeft:"clamp" made this interpolate() extrapolate
  // LINEARLY backwards for every frame before exitStart, pushing the text far
  // off-screen to the left for ~90% of the shot's duration (blank first frame).
  const slide = interpolate(frame, [exitStart, durationInFrames - 1], [0, -1400], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ fontFamily: TM.fontHeading, color: TM.ink }}>
      <PhotoBGCrossfade firstSrc="the-moment/engravings/s08_map_blank_crude.png" lastSrc="the-moment/engravings/s08_map_marked_crude.png" revealFrame={Math.max(0, exitStart - 8)} dim={0.3} />
      <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", transform:`translateX(${slide}px)` }}>
        <div style={{ position:"relative", textAlign:"center" }}>
          <div style={{ fontFamily: TM.fontHeading, fontSize: 120, fontWeight: 800, color: TM.ink }}>1842 — NANKING</div>
          {/* rough scratch-strike THROUGH the text (was a clean underline bar
              sitting below both lines, reading as emphasis not a strike-out) */}
          <svg style={{ position:"absolute", left:"-4%", top:"38%", width:"108%", height:"30%" }} viewBox="0 0 100 30" preserveAspectRatio="none">
            <path d="M 2 20 Q 30 8, 55 15 T 98 10" fill="none" stroke={TM.britishRed} strokeWidth={5}
              strokeLinecap="round" pathLength={100} strokeDasharray={100} strokeDashoffset={100 * (1 - strike)} />
            <path d="M 4 24 Q 32 12, 58 19 T 96 14" fill="none" stroke={TM.britishRed} strokeWidth={2.5} opacity={0.6}
              strokeLinecap="round" pathLength={100} strokeDasharray={100} strokeDashoffset={100 * (1 - strike)} />
          </svg>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ============================================================
 * S10/S11 — Negation cards
 * ============================================================ */

/* 07-22: replaced the flat SVG silhouettes with a real doubao-seedream-5.0-lite
   first+last keyframe pair per Alan's direct instruction ("所有没用老照片的，
   全用首帧尾帧用doubao-seedream-5.0-lite生成+动画的方法") — first frame shows
   the absence (empty sea / empty throne room), crossfading into a second
   generated frame showing what SHOULD be there (a full fleet / the throne in
   close-up), with the red X still struck across it in code (keeps that mark
   crisp and precisely timed rather than baking it into the generated image).
   Also fixes the "flash by too fast" complaint on this exact pair: the old
   version's pop-in spring started from scale(0) at frame 0, burning most of
   this already-short (~27 frame) shot on an entrance animation before the
   content was even legible. Reveal now completes by frame ~10, leaving the
   rest of the shot to actually be readable. */
export const NegationPhoto: React.FC<{ text: string; firstSrc: string; lastSrc: string }> = ({ text, firstSrc, lastSrc }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const reveal = spring({ frame, fps, config: { damping: 20, stiffness: 260 } }); // settles ~frame 8-9
  const gS = spring({ frame: frame - 4, fps, config: { damping: 14, stiffness: 260 } }); // X starts right after reveal, not after an 8f wait
  const t = Math.min(1, frame / Math.max(1, durationInFrames - 1));
  const zoom = 1.02 + t * 0.08;
  return (
    <AbsoluteFill style={{ background: "#0c0a06" }}>
      {/* 07-23: sepia dropped for the crude-anime flat-color illustration style */}
      <div style={{ position:"absolute", inset:0, overflow:"hidden" }}>
        <Img src={staticFile(firstSrc)} style={{ position:"absolute", inset:0, width:"100%", height:"100%", objectFit:"cover", transform:`scale(${zoom})`, opacity: 1 - reveal }} />
        <Img src={staticFile(lastSrc)} style={{ position:"absolute", inset:0, width:"100%", height:"100%", objectFit:"cover", transform:`scale(${zoom})`, opacity: reveal }} />
      </div>
      <div style={{ position:"absolute", inset:0, background:"radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,0.55) 100%)" }} />
      {/* red X strikes across the frame once the "present" keyframe has resolved in */}
      <svg style={{ position:"absolute", left:"17.5%", top:"20%", width:"65%", height:"60%" }} viewBox="0 0 100 100" preserveAspectRatio="none">
        <line x1="6" y1="6" x2="94" y2="94" stroke={TM.britishRed} strokeWidth="5" strokeLinecap="round"
          pathLength={100} strokeDasharray={100} strokeDashoffset={100 * (1 - gS)} style={{ filter: `drop-shadow(0 0 8px ${TM.britishRed}88)` }} />
        <line x1="94" y1="6" x2="6" y2="94" stroke={TM.britishRed} strokeWidth="5" strokeLinecap="round"
          pathLength={100} strokeDasharray={100} strokeDashoffset={100 * (1 - Math.max(0, Math.min(1, (frame - 9) / 8)))} style={{ filter: `drop-shadow(0 0 8px ${TM.britishRed}88)` }} />
      </svg>
      <div style={{ position:"absolute", left:0, right:0, top:60, textAlign:"center",
        fontFamily: TM.fontHeading, fontSize: 90, fontWeight: 900, color: TM.paper,
        textShadow:"0 3px 14px rgba(0,0,0,0.9)", opacity: Math.min(1, frame / 5) }}>{text}</div>
    </AbsoluteFill>
  );
};

/* ============================================================
 * S10 (merged S10+S11) — 07-23: "NO FLEET." (0.82s) + "NO EMPEROR." (0.82s)
 * combined only reach 1.64s of actual speech — still under the 3s-minimum
 * rule even folded together. Unlike the S04 merge, the fix here is a real
 * held pause, not just removing a hard cut: the VO Audio only plays for the
 * first 49 frames (the 1.64s of actual lines, via voHoldSec in the shot
 * table — see index.sentence-shots.tsx), then "NO EMPEROR." simply holds on
 * screen in silence for another ~1.36s before the cut to S12. A beat of
 * silence after a two-punch negation ("no fleet, no emperor") reads as a
 * deliberate pause, not dead air.
 * ============================================================ */
const NoFleetNoEmperor: React.FC = () => (
  <AbsoluteFill style={{ background: "#0c0a06" }}>
    <Sequence from={0} durationInFrames={25}>
      <NegationPhoto text="NO FLEET." firstSrc="the-moment/engravings/s10_fleet_empty_crude.png" lastSrc="the-moment/engravings/s10_fleet_present_crude.png" />
    </Sequence>
    <Sequence from={25} durationInFrames={65}>
      <NegationPhoto text="NO EMPEROR." firstSrc="the-moment/engravings/s11_throne_wide_crude.png" lastSrc="the-moment/engravings/s11_throne_close_crude.png" />
    </Sequence>
  </AbsoluteFill>
);

/* ============================================================
 * S13 — Pin pulled metaphor (reuse existing PinPulled component)
 * ============================================================ */

// India-outline silhouette with an opium icon, for S13's left panel
/* 07-23: Alan flagged these panels as "太抽象看不懂" (too abstract to read) —
   a bare hexagon outline + a purple dot + the word "INDIA" required reading
   the caption to understand what it was. Replaced with real doubao-seedream
   crude-anime illustrations (farmer harvesting poppies / a man smoking an
   opium pipe) that are legible on sight, no caption needed. */
const IndiaOpiumPanel: React.FC<{ opacity: number }> = ({ opacity }) => (
  <div style={{ position:"absolute", left:40, top:"50%", transform:"translateY(-50%)", width:220, opacity,
    borderRadius: 10, overflow:"hidden", boxShadow:"0 8px 24px rgba(0,0,0,0.5)" }}>
    <Img src={staticFile("the-moment/engravings/s13_india_panel_crude.png")} style={{ width:"100%", height:220, objectFit:"cover", display:"block" }} />
    <div style={{ textAlign:"center", fontFamily: TM.fontMono, fontSize:16, letterSpacing:"0.2em", color: TM.paper, opacity:0.85, marginTop:6 }}>INDIA</div>
  </div>
);

const QingSmokerPanel: React.FC<{ opacity: number }> = ({ opacity }) => (
  <div style={{ position:"absolute", right:40, top:"50%", transform:"translateY(-50%)", width:220, opacity,
    borderRadius: 10, overflow:"hidden", boxShadow:"0 8px 24px rgba(0,0,0,0.5)" }}>
    <Img src={staticFile("the-moment/engravings/s13_qing_panel_crude.png")} style={{ width:"100%", height:220, objectFit:"cover", display:"block" }} />
    <div style={{ textAlign:"center", fontFamily: TM.fontMono, fontSize:16, letterSpacing:"0.2em", color: TM.paper, opacity:0.85, marginTop:6 }}>QING</div>
  </div>
);

// Three-beat animation: pin yanked out and flies off-screen → fuse ignites →
// spark crawls along fuse with particles, camera pushes in on the spark.
/* 07-23: Alan flagged this shot as still "很抽象，中间为什么写个这字儿" — the
   barrel was a flat SVG shape with "EIC" baked in as literal centered SVG
   text (the earlier "S13 fix" only added the India/Qing side panels, never
   touched this centerpiece). Replaced the barrel itself with a real
   doubao-seedream crude-anime illustration (no text baked in, to avoid the
   garbled-text failure mode from the S12 wrong-map incident); the pin
   ring/fuse/spark stay as precise code-driven overlays positioned against
   the illustrated barrel's rim, and "EIC" is now a small crisp text overlay
   (like a wood-stencil brand mark) instead of SVG-drawn lettering. */
const PinPull: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const BEAT1_END = 30, BEAT2_END = 55; // pin-pull, ignite, then crawl+push for the rest
  const pull = spring({ frame: frame - 10, fps, config: { damping: 14, stiffness: 90 } });
  const flyOff = interpolate(frame, [18, BEAT1_END], [0, -900], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ignite = spring({ frame: frame - BEAT1_END, fps, config: { damping: 10, stiffness: 140 } });
  const crawl = interpolate(frame, [BEAT2_END, durationInFrames - 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pushIn = interpolate(frame, [BEAT2_END, durationInFrames - 1], [1, 1.35], { extrapolateRight: "clamp" });
  const sparkJitter = (Math.sin(frame * 1.6) * 0.5 + 0.5);
  const fuseLen = 160, sparkX = crawl * fuseLen;

  return (
    <OldPaperCard variant="dark">
      <IndiaOpiumPanel opacity={Math.min(1, frame / 20)} />
      <QingSmokerPanel opacity={Math.min(1, frame / 20)} />
      <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", transform:`scale(${pushIn})` }}>
        <div style={{ position:"relative", width:340, height:400 }}>
          <Img src={staticFile("the-moment/engravings/s13_barrel_crude.png")} style={{ width:"100%", height:"100%", objectFit:"contain" }} />
          {/* EIC brand — precise text overlay on the barrel's front face */}
          <div style={{ position:"absolute", left:"50%", top:"56%", transform:"translate(-50%,-50%) rotate(-2deg)",
            fontFamily: TM.fontHeading, fontSize: 30, fontWeight: 900, color: "#2A1608", opacity:0.55, letterSpacing:2 }}>EIC</div>
          {/* Pin ring — yanked out and flies off-frame, anchored at the barrel's rim */}
          <div style={{ position:"absolute", left:"66%", top:"11%", transform:`translate(calc(-50% + ${flyOff}px), ${flyOff !== 0 ? -Math.abs(flyOff)*0.3 : 0}px) rotate(${flyOff*0.3}deg)`,
            fontSize: 42, color: TM.qingYellow, opacity: pull > 0.05 && frame < BEAT1_END + 6 ? 1 : 0 }}>⬭</div>
          {/* Fuse + spark crawling along it, ignites at BEAT1_END */}
          <svg style={{ position:"absolute", left:"58%", top:"-6%", transform:"translateX(-50%)" }} width={fuseLen} height={70} viewBox={`0 0 ${fuseLen} 70`}>
            <path d="M 0 60 Q 48 32 80 40 T 160 8" fill="none" stroke="#3a2a1a" strokeWidth={5} />
          </svg>
          {ignite > 0.1 && (
            <div style={{ position:"absolute", left:`calc(58% - ${fuseLen/2}px + ${sparkX}px)`, top: `calc(-6% - ${crawl*40}px)`,
              width: 18 + sparkJitter*10, height: 18 + sparkJitter*10, borderRadius:"50%",
              background:"radial-gradient(circle, #FFE088, #FF8800 60%, transparent)", filter:"blur(2px)",
              opacity: ignite }} />
          )}
        </div>
      </div>
      {/* short keyword caption, moved to top, no longer the full VO sentence */}
      <div style={{ position:"absolute", left:0, right:0, top: 50, textAlign:"center",
        fontFamily: TM.fontHeading, fontSize: 42, fontWeight: 800, color: TM.qingYellow, letterSpacing:1,
        opacity: Math.min(1, frame / 15) }}>
        THE FIRST PIN
      </div>
    </OldPaperCard>
  );
};

/* ============================================================
 * S14 — Machine 27 years timeline
 * ============================================================ */

// 07-22: replaces the gear-mechanism idea with a lit fuse traveling along the
// timeline, triggering a small explosion (spark build-up, then debris) at
// each of 4 nodes (was 3 — missing an explicit 1839 node).
const TimelineBomb: React.FC<{ x: number; year: string; litFrame: number; frame: number; fps: number }> = ({ x, year, litFrame, frame, fps }) => {
  const t = frame - litFrame;
  const spark = t >= -12 && t < 0 ? Math.min(1, (t + 12) / 12) : 0;
  const blast = spring({ frame: t, fps, config: { damping: 8, stiffness: 300 } });
  const exploded = t >= 0;
  return (
    <div style={{ position:"absolute", left: x, top: "50%", transform:"translate(-50%,-50%)" }}>
      {!exploded && spark > 0 && (
        <div style={{ position:"absolute", left:-10, top:-40, width:16+spark*10, height:16+spark*10, borderRadius:"50%",
          background:"radial-gradient(circle, #FFE088, #FF8800 60%, transparent)", filter:"blur(1.5px)", opacity: spark }} />
      )}
      {exploded && blast < 1 && (
        <>
          <div style={{ position:"absolute", left:-30, top:-60, width: 60+blast*40, height:60+blast*40, borderRadius:"50%",
            background:"radial-gradient(circle, rgba(255,220,140,0.9), rgba(200,80,20,0.4) 60%, transparent)",
            transform:"translate(-50%,-50%)", opacity: Math.max(0, 1-blast) }} />
          {[0,1,2,3,4].map(i => {
            const ang = (i / 5) * Math.PI * 2;
            const d = blast * 34;
            return <div key={i} style={{ position:"absolute", left: Math.cos(ang)*d, top: -50 + Math.sin(ang)*d,
              width:5, height:5, background: TM.ink, opacity: Math.max(0,1-blast) }} />;
          })}
        </>
      )}
      {/* 07-22: exploded fill was #2A2018 (near-black) and the year label was
          TM.ink (dark brown) — both nearly invisible against OldPaperCard's
          "dark" charcoal background (#1C1712). Exploded now keeps a visible
          scorched-bronze fill with a paper-cream outline; label matches the
          sibling caption text above (TM.paper) instead of the light-variant ink color. */}
      <div style={{ width: 16, height: 16, borderRadius:"50%", background: exploded ? "#4A3020" : TM.britishRed,
        border: exploded ? `2px solid ${TM.paper}` : "none",
        boxShadow: exploded ? "none" : `0 0 12px ${TM.britishRed}` }} />
      <div style={{ fontFamily: TM.fontMono, fontSize: 22, color: TM.paper, marginTop: 12, textAlign:"center" }}>{year}</div>
    </div>
  );
};

const MachineTimeline: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const NODES = [
    { year: "1813", x: 100 },
    { year: "1833/34", x: 380 },
    { year: "1839", x: 660 },
    { year: "1840", x: 940 },
  ];
  const litFrames = NODES.map((_, i) => 20 + i * ((durationInFrames - 40) / (NODES.length - 1)));
  const crawl = interpolate(frame, [10, durationInFrames - 10], [0, 1000], { extrapolateRight: "clamp" });
  return (
    <OldPaperCard variant="dark">
      {/* 07-23: Alan flagged the bare dot-and-line timeline as "太抽象看不懂"
          (too abstract to read) — added the crude-anime cracking-gears
          illustration as a dimmed backdrop so "took 27 years to come apart"
          has an actual picture behind it, not just a progress bar. */}
      <div style={{ position:"absolute", inset:0, overflow:"hidden", opacity:0.4 }}>
        <Img src={staticFile("the-moment/engravings/s14_machine_bg_crude.png")} style={{ width:"100%", height:"100%", objectFit:"cover" }} />
      </div>
      <div style={{ position:"absolute", inset:0, background:"radial-gradient(ellipse at center, transparent 30%, rgba(28,23,18,0.85) 100%)" }} />
      <div style={{ position:"absolute", left:0, right:0, top: 50, textAlign:"center",
        fontFamily: TM.fontHeading, fontSize: 44, color: TM.paper, opacity: Math.min(1, frame/15) }}>
        took <span style={{ color: TM.britishRed }}>27 years</span> to come apart
      </div>
      <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center" }}>
        <div style={{ position:"relative", width: 1040, height: 4 }}>
          {/* copper-engraving style timeline rail */}
          <div style={{ position:"absolute", inset:0, background: `repeating-linear-gradient(90deg, ${TM.qingYellow} 0 6px, transparent 6px 10px)`, opacity:0.5 }} />
          {/* traveling lit fuse */}
          <div style={{ position:"absolute", left:0, top:-2, width: Math.min(1040, crawl), height:8,
            background:"linear-gradient(90deg, transparent, #FF8800 90%)", filter:"blur(1px)" }} />
          {NODES.map((n, i) => (
            <TimelineBomb key={n.year} x={n.x} year={n.year} litFrame={litFrames[i]} frame={frame} fps={fps} />
          ))}
        </div>
      </div>
    </OldPaperCard>
  );
};

/* ============================================================
 * S16 — Wire pulled tight
 * ============================================================ */

// 07-22 fusion (per Alan's call on the wire-vs-soldiers question): keep the
// taut-wire/three-date-node main action (it IS the "wire" the VO names), but
// stand a line of British/Qing 1840s soldier silhouettes at each end of the
// wire — the wire snapping taut reads as the standoff tightening, the
// soldiers make the standoff's two sides concrete without abandoning the
// metaphor the VO is actually describing.
const WirePull: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const draw = spring({ frame, fps, config: { damping: 20, stiffness: 60 } });
  const soldiersIn = spring({ frame: frame - 8, fps, config: { damping: 18, stiffness: 90 } });
  return (
    <OldPaperCard variant="dark">
      {/* soldier silhouettes anchored at each end of the wire */}
      <div style={{ position:"absolute", left: 0, top: "50%", width: 340, height: 180, transform:`translateY(-50%) scale(${0.7 + soldiersIn*0.3})`, opacity: soldiersIn }}>
        <Img src={staticFile("the-moment/engravings/s16_soldiers_crude.png")}
          style={{ width:"200%", height:"100%", objectFit:"cover", objectPosition:"left center" }} />
      </div>
      <div style={{ position:"absolute", right: 0, top: "50%", width: 340, height: 180, transform:`translateY(-50%) scale(${0.7 + soldiersIn*0.3})`, opacity: soldiersIn }}>
        <Img src={staticFile("the-moment/engravings/s16_soldiers_crude.png")}
          style={{ width:"200%", height:"100%", objectFit:"cover", objectPosition:"right center", marginLeft:"-100%" }} />
      </div>
      <svg style={{ position:"absolute", inset:0, width:"100%", height:"100%" }} viewBox="0 0 1920 1080" preserveAspectRatio="none">
        <polyline
          points={`340,700 700,${700 - draw*200} 960,${700 - draw*380} 1220,${700 - draw*200} 1580,700`}
          fill="none" stroke={TM.qingYellow} strokeWidth={4}
          strokeDasharray="2000" strokeDashoffset={2000*(1-draw)}
        />
        {[
          {x:340,y:700,label:"1813",c:TM.britishRed},
          {x:960,y:320,label:"1834",c:TM.inkSoft},
          {x:1580,y:700,label:"1840",c:TM.qingBlue},
        ].map((p,i) => (
          <g key={i} opacity={draw > (i+1)/4 ? 1 : 0}>
            <circle cx={p.x} cy={draw*p.y + (1-draw)*700} r={14} fill={p.c} />
            <text x={p.x} y={draw*p.y + (1-draw)*700 + 50} textAnchor="middle" fontSize={32} fill={TM.paper} fontFamily="Menlo">{p.label}</text>
          </g>
        ))}
      </svg>
      <div style={{ position:"absolute", left:0, right:0, top: 50, textAlign:"center", fontFamily: TM.fontHeading, fontSize: 60, color: TM.paper, opacity: draw }}>
        runs that wire, end to end
      </div>
    </OldPaperCard>
  );
};

/* ============================================================
 * S17 (merged S17+S18) — 07-23: "1813" (2.05s) + "1834" (1.23s) individually
 * under 3s; combined they're already 3.28s, so no padding needed — just
 * remove the external hard cut between them and let DatePunch's own pop-in
 * play out as an internal date-to-date transition inside one shot.
 * ============================================================ */
const DatePunchPair: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={62}>
      <DatePunch year="1813" color={TM.qingYellow} residualSrc="the-moment/engravings/commons_house_1833.jpg" />
    </Sequence>
    <Sequence from={62} durationInFrames={36}>
      <DatePunch year="1834" color={TM.qingYellow} residualSrc="the-moment/engravings/commons_house_1833.jpg" />
    </Sequence>
  </AbsoluteFill>
);

/* ============================================================
 * S19 — Nine votes (stacking votes)
 * ============================================================ */

// V6: "flat UI 圆角卡；5红4蓝会被读成'5:4表决'——史实是271:262九票差" — the
// old 5-red/4-navy split coded the tally sticks as if they were the vote
// count itself. Now all 9 sticks are the SAME color (they represent the
// margin, not opposing sides) with a small "271 — 262" annotation to prevent
// the misread.
const NineVotes: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lastStickFrame = 10 + 8*8;
  const settle = spring({ frame: frame - lastStickFrame, fps, config: { damping: 10, stiffness: 200 } });
  return (
    <OldPaperCard variant="dark">
      <div style={{ position:"absolute", left:0, right:0, top: 50, textAlign:"center", fontFamily: TM.fontMono, fontSize: 22, letterSpacing:"0.3em", color: TM.paper, opacity:0.7 }}>ONE SPRING NIGHT · 1840</div>
      <div style={{ position:"absolute", inset:0, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", transform:`scale(${1 + Math.max(0,1-settle)*0.03})` }}>
        <div style={{ fontFamily: TM.fontHeading, fontSize: 54, color: TM.paper, marginBottom: 40 }}>
          came down to <span style={{ color: TM.qingYellow, fontSize: 160, fontWeight: 900 }}>9</span> VOTES
        </div>
        <div style={{ display:"flex", gap: 18 }}>
          {Array.from({length:9}).map((_,i) => {
            const s = spring({ frame: frame - 10 - i*8, fps, config: { damping:12, stiffness:200 }});
            return <div key={i} style={{
              width: 22, height: 120, background: TM.qingYellow,
              borderRadius: 2, transform:`translateY(${(1-s)*200}px) rotate(${(1-s)*30}deg)`,
              opacity: s, boxShadow:"0 8px 16px rgba(0,0,0,0.5)",
            }}/>;
          })}
        </div>
        <div style={{ marginTop: 24, fontFamily: TM.fontMono, fontSize: 30, color: TM.paper, opacity: settle }}>271 — 262</div>
      </div>
    </OldPaperCard>
  );
};

/* ============================================================
 * PD-engraving Ken Burns shots (replaces Wan2.2 Comfy S01/S03/S12/S15)
 * ============================================================ */

export const EngravingKenBurns: React.FC<{
  src: string; startScale?: number; endScale?: number; panFrom?: [number, number]; panTo?: [number, number];
  caption?: string; captionColor?: string; sepia?: number; dim?: number;
}> = ({ src, startScale=1.0, endScale=1.25, panFrom=[50,50], panTo=[50,50], caption, captionColor, sepia=0.4, dim=0.15 }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = Math.min(1, frame / Math.max(1, durationInFrames - 1));
  const scale = startScale + (endScale - startScale) * t;
  const px = panFrom[0] + (panTo[0] - panFrom[0]) * t;
  const py = panFrom[1] + (panTo[1] - panFrom[1]) * t;
  return (
    <AbsoluteFill style={{ background: "#0c0a06" }}>
      <div style={{
        position:"absolute", inset:0, overflow:"hidden",
        filter: `sepia(${sepia}) contrast(1.05) brightness(${1 - dim})`,
      }}>
        <Img src={staticFile(src)} style={{
          position:"absolute", left:0, top:0, width:"100%", height:"100%",
          objectFit:"cover", transform: `scale(${scale})`, transformOrigin: `${px}% ${py}%`,
        }} />
      </div>
      {/* vignette */}
      <div style={{ position:"absolute", inset:0, background:"radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.6) 100%)", pointerEvents:"none" }}/>
      {caption && (
        // moved from bottom:60 to top — bottom is reserved for subtitles (07-22 global note)
        <div style={{ position:"absolute", left:0, right:0, top: 50, textAlign:"center",
          fontFamily: TM.fontHeading, fontSize: 48, fontWeight: 800, color: captionColor || TM.paper,
          textShadow: "0 2px 10px rgba(0,0,0,0.9)", letterSpacing: 2,
          opacity: spring({ frame: frame - 6, fps: 30, config: { damping: 20, stiffness: 60 } }),
        }}>{caption}</div>
      )}
    </AbsoluteFill>
  );
};

/* S00 — old Nanjing/China riverside city (07-22 CEO note: an Earth-globe
   opening didn't fit the tone here and needed explaining; a real period city
   image does the job directly). Push-in only, no Wan — matches the "old
   photo = Ken Burns, not animation" rule applied throughout. */
/* S00 — 07-22: 1.64s is a hard VO-locked floor, so the zoom itself now moves
   further (1.0->1.35 vs the old 1.18) to read as a deliberate push rather than
   a flash; FADE_IN from black is handled at conform (see tools/conform_co.py
   TRANSITION_MAP) since Remotion has no "previous shot" to fade from. */
/* 07-22 (round 2): Alan flagged that the whole CO pass skipped
   documentary-montage's own asset-director rule — real archival sources
   (Wikimedia/Archive.org/NASA/etc.) should be searched BEFORE falling back
   to generated images, especially on a "vintage" documentary brief. Swapped
   the AI-generated city view for a real period view of Nanking (looking
   down from the Porcelain Tower — Wikimedia Commons, public domain). */
/* 07-23: style pivot test — Alan compared goodcase reference channels
   (Simple History flat-cutout / StickTory+Agent Flappy stick-figure /
   History with Dave "crude anime") and picked the "crude anime" doubao-
   seedream-5.0-lite prompt recipe as the locked house style. Swapping the
   real archival photo for a generated illustration in this style — sepia/
   dim dropped to 0 since these are flat-color illustrations, not aged
   photos needing a sepia treatment. */
const S00_NanjingCity: React.FC = () => (
  <EngravingKenBurns src="the-moment/engravings/s00_nanjing_crude.png"
    startScale={1.0} endScale={1.3} panFrom={[50, 60]} panTo={[50, 45]}
    caption="AUGUST, 1842" captionColor={TM.qingYellow} sepia={0} dim={0}/>
);

/* S01 — 07-22 round 2: replaced the generated warship image with the real
   painting "HMS Cornwallis and Squadron in Nanking" (R.B. Watson, 1844,
   Wikimedia Commons, public domain) — an authentic depiction of exactly
   this scene (sailors manning the yards, Chinese shore in the background),
   not an AI approximation. (Earlier round-1 fix replaced a wrong European-
   harbor stock image with a generated one; this replaces THAT with the
   real archival painting per the same-scene continuity goal from S00.) */
const S01_Wellesley: React.FC = () => (
  <EngravingKenBurns src="the-moment/engravings/s01_warship_crude.png"
    startScale={1.0} endScale={1.3} panFrom={[45, 55]} panTo={[55, 50]}
    caption="A BRITISH WARSHIP · NANKING, 1842" captionColor={TM.qingYellow} sepia={0} dim={0}/>
);

/* S09 — British Parliament interior, early 1800s (07-22: replaces the
   ComfyUI Wan I2V stub, which read as cheap — a real period engraving with a
   plain push-in reads stronger, and matches every other historical shot's
   "old photo = Ken Burns only" treatment). Distinct crop/angle from S12's
   commons_house_1833.jpg so the two Parliament beats don't feel identical. */
const S09_CommonsAlt: React.FC = () => (
  <EngravingKenBurns src="the-moment/engravings/s09_commons_crude.png"
    startScale={1.0} endScale={1.22} panFrom={[50, 60]} panTo={[50, 45]}
    caption="LONDON, 1813" captionColor={TM.qingYellow} sepia={0} dim={0}/>
);

/* S03 — textbook moment: PD engraving of Treaty of Nanking + overlay caption */
const S03_Textbook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const draw = spring({ frame: frame - 12, fps, config: { damping: 18, stiffness: 50 }});
  // information hierarchy was inverted (07-22): the date/treaty name was
  // buried in unreadable 14px body text while "Ask any textbook." (the
  // low-information line) got the giant title treatment. Now "1842 — THE
  // OPIUM WAR" is the primary title and "Ask any textbook." is a small
  // secondary line. Continuous slow pan across the full duration (was a
  // near-static single entrance spring) to avoid reading as a freeze-frame.
  const panT = interpolate(frame, [0, durationInFrames - 1], [0, 1]);
  return (
    <AbsoluteFill style={{ background: "#2a241a" }}>
      <EngravingKenBurns src="the-moment/engravings/map_pearl_river_old.jpg"
        startScale={1.0} endScale={1.16} panFrom={[25,45]} panTo={[60,55]}
        sepia={0.7} dim={0.35} />
      {/* primary title — date + treaty name, now the dominant element */}
      <div style={{ position:"absolute", left:0, right:0, top:"6%", textAlign:"center", opacity: draw }}>
        <div style={{ fontFamily: TM.fontHeading, fontSize: 76, fontWeight: 900, color: TM.qingYellow, textShadow:"0 4px 16px rgba(0,0,0,0.7)" }}>
          1842 — THE OPIUM WAR
        </div>
        <div style={{ fontFamily: TM.fontMono, fontSize: 24, color: TM.paper, opacity:0.75, letterSpacing:"0.15em", marginTop: 6 }}>
          Ask any textbook.
        </div>
      </div>
      <div style={{ position:"absolute", left:"14%", right:"14%", top:"30%", bottom:"14%",
        background:"#f0e3c4", border:"1px solid #8a7248", borderRadius:6,
        boxShadow:"0 16px 50px rgba(0,0,0,0.7)",
        transform: `perspective(1200px) rotateY(${-8 + draw*2 + panT*3}deg) rotateX(${2 - draw*0.5}deg)`,
        opacity: draw,
        display:"flex", flexDirection:"column",
      }}>
        <div style={{ padding:"22px 36px 0", fontFamily: TM.fontHeading, fontSize:18, color:"#4a3820", borderBottom:"1px solid #b89e6c" }}>
          HISTORY OF EUROPE · CHAPTER XIV
        </div>
        <div style={{ flex:1, padding:"12px 36px 30px", display:"flex", gap: 20 }}>
          <div style={{ flex:1, fontFamily: TM.fontBody, fontSize:13, color:"#3a2d18", lineHeight:1.45, textAlign:"justify" }}>
            <p><i>29 August, 1842</i> — aboard HMS Cornwallis at Nanking, the Treaty of Nanking was signed by Sir Henry Pottinger and Qing commissioners Keying, Yilibu, and Niujian.</p>
            <p>Five ports opened to foreign trade (Canton, Amoy, Foochow, Ningpo, Shanghai); the island of Hong Kong ceded to the British Crown.</p>
            <p>An indemnity of <b>21,000,000 silver dollars</b> imposed upon the Chinese government, payable in instalments over three years.</p>
          </div>
          <div style={{ width:"45%", border:"1px solid #8a7248", alignSelf:"center" }}>
            <Img src={staticFile("the-moment/engravings/canton_factories.jpg")} style={{ width:"100%", height:"100%", objectFit:"cover", display:"block", filter:"sepia(0.5)" }}/>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* S12 — Commons debate, 1813 (PD engraving of the House + "WRONG MAP" overlay) */
const S12_Commons: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const mapAppear = spring({ frame: frame - 90, fps, config: { damping: 14, stiffness: 60 }});
  const wrongStamp = spring({ frame: frame - 160, fps, config: { damping: 10, stiffness: 200 }});
  return (
    <AbsoluteFill>
      <EngravingKenBurns src="the-moment/engravings/commons_house_1833.jpg"
        startScale={1.0} endScale={1.2} panFrom={[40,40]} panTo={[55,55]}
        sepia={0.45} dim={0.2}/>
      {/* 07-22: was a flat SVG rectangle + a clean-bordered text badge — read
          as a stray placeholder/error graphic against the painted engraving
          background, not an intentional visual joke (Alan: "总是有个wrongmap
          的标志"). Replaced with a real doubao-seedream-5.0-lite hand-torn
          parchment map (no baked-in text — AI text rendering is unreliable,
          so "CANTON?" stays a crisp code overlay) + an ink-stamp treatment
          matching WrongMoment's stamp aesthetic instead of a UI-style badge. */}
      <div style={{ position:"absolute", left:"52%", top:"30%", width:"320px", transform: `rotate(6deg) scale(${mapAppear})`,
        filter: "drop-shadow(0 10px 20px rgba(0,0,0,0.6))" }}>
        <Img src={staticFile("the-moment/engravings/s12_wrongmap_crude.png")} style={{ width:"100%", height:"auto", display:"block" }} />
        <div style={{ position:"absolute", left:"38%", top:"58%", transform:"rotate(-4deg)",
          fontFamily: "Georgia, serif", fontSize: 20, fontWeight: 700, color: "#5a2a20", letterSpacing: 1 }}>CANTON?</div>
      </div>
      {/* WRONG MAP — red ink stamp (rotated + splatter + matte shadow), not a clean badge */}
      <div style={{ position:"absolute", left:"56%", top:"32%", transform:`translate(-50%,-50%) rotate(-11deg) scale(${wrongStamp})`, opacity: wrongStamp }}>
        <div style={{ position:"relative", border:`5px solid ${TM.britishRed}`, color: TM.britishRed, fontFamily: TM.fontHeading,
          fontSize: 25, fontWeight: 900, padding:"5px 14px", letterSpacing: 2,
          boxShadow:"2px 4px 0px rgba(42,36,28,0.5)" }}>
          WRONG MAP
          <InkSplatter appearFrame={160} />
        </div>
      </div>
      {/* caption moved to top — bottom is reserved for subtitles (07-22 global note) */}
      <div style={{ position:"absolute", left:0, right:0, top: 50, textAlign:"center",
        fontFamily: TM.fontHeading, fontSize: 38, fontWeight: 800, color: TM.paper,
        textShadow:"0 2px 10px #000",
        opacity: spring({ frame: frame - 6, fps, config: { damping: 20, stiffness: 60 } }),
      }}>Westminster, 1813 — arguing about a map they had wrong.</div>
    </AbsoluteFill>
  );
};

/* S15 — First Opium War naval battle (PD engraving of Nemesis attacking junks) */
const S15_NemesisBattle: React.FC = () => (
  <EngravingKenBurns src="the-moment/engravings/s15_nemesis_crude.png"
    startScale={1.0} endScale={1.35} panFrom={[50,55]} panTo={[45,50]}
    caption="THE NAVY'S SHELLS ON CHINESE JUNKS" captionColor={TRIPTYCH.britGold} sepia={0} dim={0}/>
);

/* ============================================================
 * S20 — Map push to London
 * ============================================================ */

const MapPush: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const draw = spring({ frame: frame - 10, fps, config: { damping: 20, stiffness: 60 }});
  // V6: 3 labeled nodes (London/India/Canton) along the route — was 1 (London only)
  const NODES = [
    { x: 1550, y: 350, label: "LONDON · 1813", at: 0.3 },
    { x: 950, y: 500, label: "INDIA", at: 0.6 },
    { x: 650, y: 560, label: "CANTON", at: 0.85 },
  ];
  return (
    <OldPaperCard variant="dark">
      {/* 07-23: Alan flagged the abstract two-blob SVG landmass as "太抽象看不懂"
          — replaced with the real crude-anime illustrated map so the shapes
          on screen actually read as Britain/India/China, not schematic blobs.
          Route line + node dots stay as a precise SVG overlay on top. */}
      <div style={{ position:"absolute", inset:0, overflow:"hidden" }}>
        <Img src={staticFile("the-moment/engravings/s20_world_map_crude.png")} style={{ width:"100%", height:"100%", objectFit:"cover" }} />
      </div>
      <div style={{ position:"absolute", inset:0, background:"rgba(28,23,18,0.25)" }} />
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <path d={`M 1550 350 Q 1200 480 900 500 Q 500 520 800 560`} fill="none" stroke={TM.qingYellow} strokeWidth={3} strokeDasharray="8 6"
              strokeDashoffset={4000*(1-draw)} />
        {NODES.map((n, i) => (
          <g key={i} opacity={draw > n.at ? 1 : 0}>
            <circle cx={n.x} cy={n.y} r={16}><animate attributeName="r" values="16;22;16" dur="1s" repeatCount="indefinite"/></circle>
            <circle cx={n.x} cy={n.y} r={16} fill={TM.britishRed} />
            <text x={n.x} y={n.y - 30} textAnchor="middle" fontSize={26} fill={TM.paper} fontFamily="Menlo">{n.label}</text>
          </g>
        ))}
      </svg>
      <div style={{ position:"absolute", left:0, right:0, top: 50, textAlign:"center", fontFamily: TM.fontHeading, fontSize: 64, color: TM.paper, opacity: draw }}>
        Let's go find <span style={{ color: TM.qingYellow }}>the vote about India</span>
      </div>
    </OldPaperCard>
  );
};

/* ============================================================
 * Export map — used by index.sentence-shots to register compositions
 * ============================================================ */

export interface SentenceShotSpec {
  id: string;
  durSec: number;
  voStart: number;
  voEnd: number;
  Component: React.FC;
  comfy?: boolean; // if true, replaced by ComfyUI video at assemble time
  comfyPrompt?: string;
  // 07-23: when a shot's visual durSec is padded longer than its real VO
  // (e.g. a merged shot holding on its final beat for pacing), voHoldSec
  // caps how much of the underlying continuous VO track actually plays —
  // defaults to durSec (today's behavior) so no other shot is affected.
  // See index.sentence-shots.tsx's ShotRoot.
  voHoldSec?: number;
}

export const SENTENCE_SHOTS: SentenceShotSpec[] = [
  // 07-23: S00/S01 were 2.41s/2.56s, just under the 3s-minimum-shot rule —
  // padded to 3.0s with a trailing silent hold (voHoldSec), same technique
  // as the S10 merge. VO timing for both is unchanged.
  { id:"S00", durSec:3.0, voStart:0.0, voEnd:2.41, voHoldSec:2.41, Component:S00_NanjingCity },
  { id:"S01", durSec:3.0, voStart:2.41, voEnd:4.97, voHoldSec:2.56, Component:S01_Wellesley },
  { id:"S02", durSec:9.43, voStart:4.97, voEnd:14.4, Component:TreatyTable },
  { id:"S03", durSec:7.63, voStart:14.4, voEnd:22.03, Component:S03_Textbook },
  // 07-23: S04+S05+S06+S07 merged into one 3.69s shot (see GunboatsToWrongMoment) —
  // each was individually under the 3s-minimum-shot rule; combined VO is unchanged.
  { id:"S04", durSec:3.69, voStart:22.03, voEnd:25.72, Component:GunboatsToWrongMoment },
  { id:"S08", durSec:3.66, voStart:25.72, voEnd:29.37, Component:StrikeAndSlide },
  { id:"S09", durSec:4.92, voStart:29.37, voEnd:34.29, Component:S09_CommonsAlt },
  // 07-23: S10+S11 merged (see NoFleetNoEmperor). Combined VO is only 1.64s, so
  // durSec is padded to 3.0s for a held silent pause on "NO EMPEROR" — voHoldSec
  // caps audio playback to the real 1.64s so S12's line doesn't bleed in early.
  { id:"S10", durSec:3.0, voStart:34.29, voEnd:35.93, voHoldSec:1.64, Component:NoFleetNoEmperor },
  { id:"S12", durSec:8.86, voStart:35.93, voEnd:44.8, Component:S12_Commons },
  { id:"S13", durSec:10.72, voStart:44.8, voEnd:55.52, Component:PinPull },
  { id:"S14", durSec:4.1, voStart:55.52, voEnd:59.62, Component:MachineTimeline },
  { id:"S15", durSec:11.06, voStart:59.62, voEnd:70.68, Component:S15_NemesisBattle },
  { id:"S16", durSec:3.28, voStart:70.68, voEnd:73.96, Component:WirePull },
  // 07-23: S17+S18 merged into one 3.28s shot (see DatePunchPair) — already
  // clears 3s combined, no padding needed.
  { id:"S17", durSec:3.28, voStart:73.96, voEnd:77.24, Component:DatePunchPair },
  { id:"S19", durSec:5.33, voStart:77.24, voEnd:82.57, Component:NineVotes },
  // 07-23: S20 was 2.85s, just under 3s — padded with a trailing hold (final
  // shot, so this only extends the fade-out by 0.15s).
  { id:"S20", durSec:3.0, voStart:82.57, voEnd:85.42, voHoldSec:2.85, Component:MapPush },
];

export const FPS = 30;
