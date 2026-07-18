import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { TM } from "../theme";
import { PaperBackground } from "../paper/PaperBackground";

/**
 * KIT-SET-* — line-frame scene shells (R1 stage).
 * Ink line drawings on paper, drawn on with a short stroke reveal.
 * These are compositional shells behind char_punch beats; W-jobs may later
 * replace them with painted boards without changing layout anchors.
 */

const useDraw = (delay = 0, duration = 30) => {
  const frame = useCurrentFrame();
  return interpolate(frame - delay, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};

const Stroke: React.FC<{
  d: string;
  progress: number;
  width?: number;
  fill?: string;
  dashed?: boolean;
}> = ({ d, progress, width = 4, fill = "none", dashed = false }) => (
  <path
    d={d}
    fill={fill === "none" ? "none" : fill}
    fillOpacity={fill === "none" ? 0 : 0.5 * progress}
    stroke={TM.inkSoft}
    strokeWidth={width}
    pathLength={100}
    strokeDasharray={dashed ? "3 3" : "100"}
    strokeDashoffset={dashed ? 0 : 100 * (1 - progress)}
    opacity={dashed ? progress : 1}
    strokeLinecap="round"
    strokeLinejoin="round"
  />
);

export type SetId =
  | "SET-COMMONS"
  | "SET-LEDGER"
  | "SET-CANTON-FACTORY"
  | "SET-CALCUTTA-AUCTION"
  | "SET-DECK"
  | "SET-MAP-TABLE";

/** SET-COMMONS — facing benches + Speaker's chair. */
const Commons: React.FC = () => {
  const p = useDraw(0, 34);
  const p2 = useDraw(12, 30);
  return (
    <svg width={1920} height={1080}>
      {/* floor line */}
      <Stroke d="M 160 900 L 1760 900" progress={p} width={5} />
      {/* left benches (3 rising rows) */}
      {[0, 1, 2].map((i) => (
        <Stroke
          key={`l${i}`}
          d={`M ${300 - i * 60} ${860 - i * 90} L ${760 - i * 30} ${860 - i * 90} L ${760 - i * 30} ${820 - i * 90} L ${300 - i * 60} ${820 - i * 90} Z`}
          progress={p}
          width={4}
          fill={TM.paperLo}
        />
      ))}
      {/* right benches (mirror of left) */}
      {[0, 1, 2].map((i) => (
        <Stroke
          key={`r${i}`}
          d={`M ${1160 + i * 30} ${860 - i * 90} L ${1620 + i * 60} ${860 - i * 90} L ${1620 + i * 60} ${820 - i * 90} L ${1160 + i * 30} ${820 - i * 90} Z`}
          progress={p}
          width={4}
          fill={TM.paperLo}
        />
      ))}
      {/* Speaker's chair, centre back */}
      <Stroke d="M 900 780 L 900 520 Q 960 460 1020 520 L 1020 780 Z" progress={p2} width={5} fill={TM.paperLo} />
      <Stroke d="M 880 780 L 1040 780 L 1040 820 L 880 820 Z" progress={p2} width={5} />
      {/* table of the House */}
      <Stroke d="M 840 880 L 1080 880 L 1068 940 L 852 940 Z" progress={p2} width={4} fill={TM.paperHi} />
      {/* gallery line */}
      <Stroke d="M 240 300 L 1680 300" progress={p2} width={3} dashed />
    </svg>
  );
};

/** SET-LEDGER — counting house: desk, ledgers, balance scale. */
const Ledger: React.FC = () => {
  const p = useDraw(0, 30);
  const p2 = useDraw(14, 28);
  return (
    <svg width={1920} height={1080}>
      <Stroke d="M 200 880 L 1720 880" progress={p} width={5} />
      {/* desk */}
      <Stroke d="M 480 880 L 520 640 L 1400 640 L 1440 880" progress={p} width={5} />
      <Stroke d="M 520 640 L 1400 640 L 1390 600 L 530 600 Z" progress={p} width={4} fill={TM.paperLo} />
      {/* ledger stack left */}
      {[0, 1, 2].map((i) => (
        <Stroke
          key={i}
          d={`M ${640 - i * 8} ${592 - i * 26} L ${800 - i * 4} ${592 - i * 26} L ${800 - i * 4} ${568 - i * 26} L ${640 - i * 8} ${568 - i * 26} Z`}
          progress={p2}
          width={4}
          fill={i === 1 ? TM.britishRed : TM.paperHi}
        />
      ))}
      {/* balance scale right */}
      <Stroke d="M 1150 600 L 1150 440" progress={p2} width={5} />
      <Stroke d="M 1010 470 L 1290 470" progress={p2} width={5} />
      <Stroke d="M 1010 470 L 990 540 M 1010 470 L 1030 540 M 968 556 Q 1010 588 1052 556" progress={p2} width={4} />
      <Stroke d="M 1290 470 L 1270 540 M 1290 470 L 1310 540 M 1248 556 Q 1290 588 1332 556" progress={p2} width={4} />
      {/* coin bag */}
      <Stroke d="M 1470 880 Q 1450 800 1500 780 Q 1490 760 1520 756 Q 1550 760 1540 780 Q 1590 800 1570 880 Z" progress={p2} width={4} fill={TM.qingYellow} />
    </svg>
  );
};

/** SET-CANTON-FACTORY — hong row on the waterfront. */
const CantonFactory: React.FC = () => {
  const p = useDraw(0, 32);
  const p2 = useDraw(14, 28);
  return (
    <svg width={1920} height={1080}>
      {/* waterfront */}
      <Stroke d="M 120 860 L 1800 860" progress={p} width={5} />
      <Stroke d="M 200 940 Q 400 920 600 940 T 1000 940 T 1400 940 T 1800 940" progress={p2} width={3} dashed />
      {/* three factory blocks */}
      {[0, 1, 2].map((i) => {
        const x = 380 + i * 400;
        return (
          <g key={i}>
            <Stroke d={`M ${x} 860 L ${x} 560 L ${x + 300} 560 L ${x + 300} 860`} progress={p} width={5} fill={TM.paperLo} />
            <Stroke d={`M ${x - 20} 560 L ${x + 150} 480 L ${x + 320} 560 Z`} progress={p} width={4} fill={TM.paperHi} />
            {/* arcade */}
            {[0, 1, 2].map((a) => (
              <Stroke
                key={a}
                d={`M ${x + 40 + a * 80} 860 L ${x + 40 + a * 80} 700 Q ${x + 70 + a * 80} 660 ${x + 100 + a * 80} 700 L ${x + 100 + a * 80} 860`}
                progress={p2}
                width={4}
              />
            ))}
            {/* flagstaff */}
            <Stroke d={`M ${x + 150} 480 L ${x + 150} 380`} progress={p2} width={4} />
            <Stroke d={`M ${x + 150} 380 L ${x + 210} 396 L ${x + 150} 412 Z`} progress={p2} width={4} fill={[TM.britishRed, TM.qingBlue, TM.opiumPurple][i]} />
          </g>
        );
      })}
      {/* sampan */}
      <Stroke d="M 200 930 Q 260 960 340 930 L 320 906 L 224 906 Z" progress={p2} width={4} fill={TM.paperLo} />
    </svg>
  );
};

/** SET-CALCUTTA-AUCTION — podium, gavel, chest stack. */
const CalcuttaAuction: React.FC = () => {
  const p = useDraw(0, 30);
  const p2 = useDraw(14, 28);
  return (
    <svg width={1920} height={1080}>
      <Stroke d="M 220 900 L 1700 900" progress={p} width={5} />
      {/* podium */}
      <Stroke d="M 660 900 L 700 620 L 940 620 L 980 900 Z" progress={p} width={5} fill={TM.paperLo} />
      <Stroke d="M 680 620 L 960 620 L 950 580 L 690 580 Z" progress={p} width={4} fill={TM.paperHi} />
      {/* gavel mid-swing */}
      <Stroke d="M 1010 500 L 1090 420" progress={p2} width={6} />
      <Stroke d="M 1064 380 L 1140 456 L 1104 492 L 1028 416 Z" progress={p2} width={5} fill={TM.inkSoft} />
      {/* chest stack (opium chests, schematic) */}
      {[
        [1260, 820],
        [1400, 820],
        [1330, 740],
      ].map(([x, y], i) => (
        <g key={i}>
          <Stroke d={`M ${x} ${y} L ${x + 130} ${y} L ${x + 130} ${y + 80} L ${x} ${y + 80} Z`} progress={p2} width={4} fill={TM.paperLo} />
          <Stroke d={`M ${x} ${y} L ${x + 65} ${y + 40} L ${x + 130} ${y}`} progress={p2} width={3} dashed />
        </g>
      ))}
      {/* bid papers */}
      <Stroke d="M 420 900 L 440 830 L 520 838 L 508 900 Z" progress={p2} width={3} fill={TM.paperHi} />
    </svg>
  );
};

/** SET-DECK — rail, mast, rigging, one schematic gun. */
const Deck: React.FC = () => {
  const p = useDraw(0, 32);
  const p2 = useDraw(16, 28);
  return (
    <svg width={1920} height={1080}>
      {/* deck line + rail */}
      <Stroke d="M 100 880 L 1820 840" progress={p} width={6} />
      <Stroke d="M 140 880 L 150 760 M 420 872 L 428 752 M 700 864 L 706 746 M 980 858 L 984 740 M 1260 850 L 1262 734 M 1540 844 L 1540 728" progress={p} width={4} />
      <Stroke d="M 140 766 L 1560 734" progress={p} width={5} />
      {/* mast + yards */}
      <Stroke d="M 1120 858 L 1120 160" progress={p2} width={7} />
      <Stroke d="M 900 300 L 1340 300" progress={p2} width={5} />
      <Stroke d="M 970 190 L 1270 190" progress={p2} width={4} />
      {/* shrouds to the rail */}
      <Stroke d="M 1120 320 L 880 760 M 1120 320 L 1360 750" progress={p2} width={3} />
      {/* furled sails under both yards */}
      <Stroke d="M 906 306 Q 1120 356 1334 306 L 1334 320 Q 1120 372 906 320 Z" progress={p2} width={4} fill={TM.paperHi} />
      <Stroke d="M 976 196 Q 1120 232 1264 196 L 1264 208 Q 1120 246 976 208 Z" progress={p2} width={4} fill={TM.paperHi} />
      {/* schematic gun (icon-grade, not a naval-battle tableau) */}
      <Stroke d="M 420 830 L 560 806 L 566 826 L 430 852 Z" progress={p2} width={4} fill={TM.inkSoft} />
      <Stroke d="M 470 852 L 452 892 M 520 842 L 540 884" progress={p2} width={4} />
      {/* horizon */}
      <Stroke d="M 60 520 L 1860 520" progress={p} width={3} dashed />
    </svg>
  );
};

/** SET-MAP-TABLE — chart table with dividers and pins. */
const MapTable: React.FC = () => {
  const p = useDraw(0, 30);
  const p2 = useDraw(14, 28);
  return (
    <svg width={1920} height={1080}>
      {/* table */}
      <Stroke d="M 360 880 L 420 560 L 1500 560 L 1560 880" progress={p} width={5} />
      <Stroke d="M 420 560 L 1500 560 L 1484 520 L 436 520 Z" progress={p} width={4} fill={TM.paperLo} />
      {/* unrolled chart */}
      <Stroke d="M 560 540 L 1360 540 L 1340 380 L 580 380 Z" progress={p} width={4} fill={TM.paperHi} />
      <Stroke d="M 560 540 Q 540 540 540 500 L 540 420 Q 540 380 580 380" progress={p2} width={4} />
      <Stroke d="M 1360 540 Q 1380 540 1380 500 L 1380 420 Q 1380 380 1340 380" progress={p2} width={4} />
      {/* schematic coast on the chart */}
      <Stroke d="M 640 500 Q 760 430 900 470 T 1180 430 T 1300 470" progress={p2} width={3} dashed />
      {/* dividers */}
      <Stroke d="M 1080 470 L 1040 380 M 1080 470 L 1120 384 M 1062 418 Q 1080 400 1098 420" progress={p2} width={4} />
      {/* pins */}
      {[
        [760, 460],
        [980, 448],
        [1220, 452],
      ].map(([x, y], i) => (
        <g key={i}>
          <Stroke d={`M ${x} ${y} L ${x} ${y - 26}`} progress={p2} width={4} />
          <circle cx={x} cy={y - 32} r={8} fill={[TM.britishRed, TM.qingBlue, TM.opiumPurple][i]} stroke={TM.ink} strokeWidth={3} opacity={p2} />
        </g>
      ))}
      {/* candle */}
      <Stroke d="M 480 520 L 480 470 M 470 520 L 490 520" progress={p2} width={4} />
      <circle cx={480} cy={458} r={7} fill={TM.qingYellow} opacity={p2} />
    </svg>
  );
};

export const SETS: Record<SetId, React.FC> = {
  "SET-COMMONS": Commons,
  "SET-LEDGER": Ledger,
  "SET-CANTON-FACTORY": CantonFactory,
  "SET-CALCUTTA-AUCTION": CalcuttaAuction,
  "SET-DECK": Deck,
  "SET-MAP-TABLE": MapTable,
};

/** Full-frame set shell on paper. */
export const SetShell: React.FC<{ set: SetId; children?: React.ReactNode }> = ({
  set,
  children,
}) => {
  const Set = SETS[set];
  return (
    <PaperBackground>
      <AbsoluteFill>
        <Set />
      </AbsoluteFill>
      <AbsoluteFill>{children}</AbsoluteFill>
    </PaperBackground>
  );
};
