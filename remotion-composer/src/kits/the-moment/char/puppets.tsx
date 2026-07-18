import React from "react";
import { TM } from "../theme";

/**
 * KIT-CHAR-* — flat vector puppet shells (R1 stage).
 *
 * Style contract (grammar_stack Layer C / style lock §6):
 *  - Simple-History-grade flat fills + thick ink outlines.
 *  - Identity via costume/props only — dot eyes, NO detailed faces,
 *    no anime faces, no likeness of real historical figures.
 *  - One uniform schematic skin tone across all figures.
 *  - These are vector SHELLS: W3 painted replacements (if G is approved)
 *    swap in later; sizing/anchors stay stable.
 *
 * Each puppet renders into a 240×340 viewBox, feet at y≈330.
 */

const SKIN = "#E3C39D";
const OUT = TM.ink;
const OW = 6; // outline width

const Head: React.FC<{ cx?: number; cy?: number; r?: number }> = ({
  cx = 120,
  cy = 78,
  r = 34,
}) => (
  <g>
    <circle cx={cx} cy={cy} r={r} fill={SKIN} stroke={OUT} strokeWidth={OW} />
    {/* dot eyes only — schematic face */}
    <circle cx={cx - 11} cy={cy - 2} r={3.4} fill={OUT} />
    <circle cx={cx + 11} cy={cy - 2} r={3.4} fill={OUT} />
  </g>
);

const Legs: React.FC<{ color?: string }> = ({ color = "#3A342B" }) => (
  <g>
    <rect x={92} y={240} width={22} height={86} fill={color} stroke={OUT} strokeWidth={OW} />
    <rect x={126} y={240} width={22} height={86} fill={color} stroke={OUT} strokeWidth={OW} />
    <path d="M 86 326 L 118 326 L 118 338 L 80 338 Z" fill={OUT} />
    <path d="M 122 326 L 154 326 L 160 338 L 122 338 Z" fill={OUT} />
  </g>
);

export interface PuppetProps {
  accent?: string;
}

/** CHAR-MP — Member of Parliament: top hat, tailcoat, order paper. */
export const CharMP: React.FC<PuppetProps> = ({ accent = "#2F2A22" }) => (
  <svg viewBox="0 0 240 340" width="100%" height="100%">
    <Legs />
    {/* tailcoat */}
    <path
      d="M 84 148 L 156 148 L 162 246 L 140 246 L 136 200 L 104 200 L 100 246 L 78 246 Z"
      fill={accent}
      stroke={OUT}
      strokeWidth={OW}
    />
    {/* cravat */}
    <path d="M 110 148 L 130 148 L 120 176 Z" fill={TM.paperHi} stroke={OUT} strokeWidth={4} />
    {/* arms */}
    <path d="M 84 156 L 62 210 L 78 218 L 96 172 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    <path d="M 156 156 L 178 206 L 162 216 L 144 172 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    {/* order paper in hand */}
    <rect x={166} y={196} width={34} height={44} fill={TM.paperHi} stroke={OUT} strokeWidth={4} transform="rotate(12 183 218)" />
    <Head />
    {/* top hat */}
    <rect x={92} y={12} width={56} height={38} fill={OUT} />
    <rect x={78} y={46} width={84} height={10} fill={OUT} />
  </svg>
);

/** CHAR-MERCHANT — private trader: lighter coat, ledger under arm. */
export const CharMerchant: React.FC<PuppetProps> = ({ accent = "#6E5A3E" }) => (
  <svg viewBox="0 0 240 340" width="100%" height="100%">
    <Legs color="#4A4238" />
    <path
      d="M 84 148 L 156 148 L 164 250 L 76 250 Z"
      fill={accent}
      stroke={OUT}
      strokeWidth={OW}
    />
    {/* waistcoat line + buttons */}
    <line x1={120} y1={152} x2={120} y2={246} stroke={OUT} strokeWidth={4} />
    <circle cx={112} cy={180} r={3} fill={OUT} />
    <circle cx={112} cy={204} r={3} fill={OUT} />
    {/* left arm clamping ledger */}
    <path d="M 84 156 L 58 200 L 74 212 L 96 172 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    <rect x={40} y={186} width={46} height={60} rx={4} fill={TM.britishRed} stroke={OUT} strokeWidth={5} />
    <line x1={48} y1={196} x2={48} y2={238} stroke={TM.paperHi} strokeWidth={5} />
    {/* right arm */}
    <path d="M 156 156 L 180 212 L 164 220 L 144 172 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    <Head />
    {/* short brim hat */}
    <rect x={94} y={20} width={52} height={30} fill={accent} stroke={OUT} strokeWidth={5} />
    <rect x={82} y={46} width={76} height={9} fill={accent} stroke={OUT} strokeWidth={5} />
  </svg>
);

/** CHAR-CLERK — company clerk: shirtsleeves, quill. */
export const CharClerk: React.FC<PuppetProps> = ({ accent = "#7F8C99" }) => (
  <svg viewBox="0 0 240 340" width="100%" height="100%">
    <Legs color="#55503F" />
    {/* waistcoat over shirt */}
    <path d="M 88 148 L 152 148 L 158 248 L 82 248 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    <path d="M 104 148 L 136 148 L 120 188 Z" fill={TM.paperHi} stroke={OUT} strokeWidth={4} />
    {/* shirtsleeve arms */}
    <path d="M 88 156 L 64 206 L 80 216 L 100 172 Z" fill={TM.paperHi} stroke={OUT} strokeWidth={OW} />
    <path d="M 152 156 L 186 190 L 176 204 L 142 172 Z" fill={TM.paperHi} stroke={OUT} strokeWidth={OW} />
    {/* quill */}
    <path d="M 184 150 C 196 132 210 126 218 124 C 210 140 202 152 190 162 Z" fill={TM.qingYellow} stroke={OUT} strokeWidth={4} />
    <line x1={186} y1={160} x2={178} y2={182} stroke={OUT} strokeWidth={4} />
    <Head />
    {/* green eyeshade visor */}
    <path d="M 86 52 Q 120 34 154 52 L 154 62 Q 120 46 86 62 Z" fill="#4A6741" stroke={OUT} strokeWidth={4} />
  </svg>
);

/** CHAR-SAILOR — Royal Navy rating: cap, navy jacket. */
export const CharSailor: React.FC<PuppetProps> = ({ accent = "#223A52" }) => (
  <svg viewBox="0 0 240 340" width="100%" height="100%">
    <Legs color={TM.paperHi} />
    <path d="M 84 148 L 156 148 L 160 244 L 80 244 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    {/* collar flap */}
    <path d="M 96 148 L 144 148 L 120 184 Z" fill={TM.paperHi} stroke={OUT} strokeWidth={4} />
    <path d="M 84 156 L 60 204 L 76 214 L 98 172 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    <path d="M 156 156 L 180 204 L 164 214 L 142 172 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    <Head />
    {/* flat sailor cap */}
    <ellipse cx={120} cy={40} rx={44} ry={14} fill={accent} stroke={OUT} strokeWidth={5} />
    <rect x={98} y={44} width={44} height={12} fill={accent} stroke={OUT} strokeWidth={4} />
  </svg>
);

/** CHAR-OFFICIAL-CN — Qing official: winter hat, robe, rank badge. */
export const CharOfficialCN: React.FC<PuppetProps> = ({ accent = TM.qingBlue }) => (
  <svg viewBox="0 0 240 340" width="100%" height="100%">
    {/* full-length robe (no separate legs) */}
    <path d="M 86 148 L 154 148 L 168 330 L 72 330 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    {/* wide sleeves */}
    <path d="M 86 156 L 48 214 L 66 228 L 100 176 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    <path d="M 154 156 L 192 214 L 174 228 L 140 176 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    {/* plain rank badge (schematic square, no invented insignia) */}
    <rect x={100} y={188} width={40} height={40} fill={TM.qingYellow} stroke={OUT} strokeWidth={4} />
    <Head />
    {/* official hat: shallow cone + finial */}
    <path d="M 78 58 Q 120 20 162 58 Z" fill={TM.britishRed} stroke={OUT} strokeWidth={5} />
    <circle cx={120} cy={26} r={6} fill={TM.qingYellow} stroke={OUT} strokeWidth={3} />
  </svg>
);

/** CHAR-FARMER — taxpayer with a bill: straw hat, plain tunic. */
export const CharFarmer: React.FC<PuppetProps> = ({ accent = "#8B7B54" }) => (
  <svg viewBox="0 0 240 340" width="100%" height="100%">
    <Legs color="#6B5F43" />
    <path d="M 88 150 L 152 150 L 158 246 L 82 246 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    {/* rope belt */}
    <line x1={84} y1={214} x2={156} y2={214} stroke={OUT} strokeWidth={4} strokeDasharray="10 6" />
    <path d="M 88 158 L 62 200 L 76 212 L 100 174 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    <path d="M 152 158 L 180 196 L 168 210 L 142 174 Z" fill={accent} stroke={OUT} strokeWidth={OW} />
    {/* tax bill */}
    <rect x={168} y={178} width={36} height={48} fill={TM.paperHi} stroke={OUT} strokeWidth={4} transform="rotate(8 186 202)" />
    <line x1={176} y1={192} x2={196} y2={194} stroke={TM.inkSoft} strokeWidth={3} />
    <line x1={176} y1={202} x2={196} y2={204} stroke={TM.inkSoft} strokeWidth={3} />
    <Head />
    {/* conical straw hat */}
    <path d="M 68 62 L 120 18 L 172 62 Z" fill={TM.qingYellow} stroke={OUT} strokeWidth={5} />
  </svg>
);

/**
 * CHAR-COMPANY — the Company as a door-lintel emblem, not a person
 * (scene plan: 公司拟人/门楣徽章). Generic classical pediment + monogram;
 * intentionally NOT the real EIC coat of arms.
 */
export const CharCompany: React.FC<PuppetProps & { decayed?: boolean }> = ({
  accent = TM.britishRed,
  decayed = false,
}) => (
  <svg viewBox="0 0 240 340" width="100%" height="100%">
    {/* pediment */}
    <path d="M 30 120 L 120 44 L 210 120 Z" fill={TM.paperLo} stroke={OUT} strokeWidth={OW} />
    {/* columns */}
    {[52, 106, 160].map((x) => (
      <g key={x}>
        <rect x={x} y={128} width={28} height={160} fill={TM.paperHi} stroke={OUT} strokeWidth={5} />
        <rect x={x - 6} y={120} width={40} height={12} fill={TM.paperLo} stroke={OUT} strokeWidth={4} />
        <rect x={x - 6} y={286} width={40} height={12} fill={TM.paperLo} stroke={OUT} strokeWidth={4} />
      </g>
    ))}
    {/* base */}
    <rect x={26} y={298} width={188} height={18} fill={TM.paperLo} stroke={OUT} strokeWidth={5} />
    {/* monogram shield */}
    <g transform="translate(120, 92)">
      <path d="M -34 -22 L 34 -22 L 34 8 Q 34 30 0 40 Q -34 30 -34 8 Z" fill={accent} stroke={OUT} strokeWidth={5} opacity={decayed ? 0.45 : 1} />
      <text
        x={0}
        y={14}
        textAnchor="middle"
        fontFamily={TM.fontHeading}
        fontWeight={700}
        fontSize={30}
        fill={TM.paperHi}
      >
        Co.
      </text>
    </g>
    {decayed && (
      <line x1={40} y1={60} x2={200} y2={300} stroke={OUT} strokeWidth={6} opacity={0.6} />
    )}
  </svg>
);

export type PuppetId =
  | "CHAR-MP"
  | "CHAR-MERCHANT"
  | "CHAR-CLERK"
  | "CHAR-SAILOR"
  | "CHAR-OFFICIAL-CN"
  | "CHAR-FARMER"
  | "CHAR-COMPANY";

export const PUPPETS: Record<PuppetId, React.FC<PuppetProps>> = {
  "CHAR-MP": CharMP,
  "CHAR-MERCHANT": CharMerchant,
  "CHAR-CLERK": CharClerk,
  "CHAR-SAILOR": CharSailor,
  "CHAR-OFFICIAL-CN": CharOfficialCN,
  "CHAR-FARMER": CharFarmer,
  "CHAR-COMPANY": CharCompany,
};
