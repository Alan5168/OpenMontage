"""primitives_report — 研报域原语第二批（s1/s2/s3/s5/s6 迁移件）。
导入即注册进 PRIMS；时间触发一律 beat-local（at=…）。"""
from __future__ import annotations

import math

from .draw import Ctx, back, clamp, eo
from .primitives import PRIMS


def loading_bar(cx: Ctx, lt, t, y=960, label="99%"):
    tk = cx.tk
    cx.rr((240, y, 840, y + 50), 2, outline=cx.A(tk.c("g3")), width=2)
    cx.rr((244, y + 4, 244 + 592 * 0.99, y + 46), 1, fill=cx.A(tk.c("g2"), 0.9))
    blink = 0.55 + 0.45 * math.sin(t * 6)
    cx.text((540, y + 110), label, cx.F("sub", 40), cx.A(tk.c("muted"), blink))


def duel_plates(cx: Ctx, lt, t, left_title="", left_sub="", right_title="", right_sub="",
                swap_at=2.0):
    tk = cx.tk
    if tk.plate_frame:
        left_box, right_box = (180, 760, 500, 1140), (580, 760, 900, 1140)
        lx, rx = 340, 740
    else:
        left_box, right_box = (120, 760, 500, 1140), (580, 760, 960, 1140)
        lx, rx = 310, 770
    dim = 1.0 - 0.5 * eo((lt - swap_at) / 0.6)
    cx.rr(left_box, 2, outline=cx.A(tk.c("g3"), dim), width=2)
    cx.text((lx, 920), left_title, cx.F("head", 56), cx.A(tk.c("g3"), dim))
    cx.text((lx, 1030), left_sub, cx.F("sub", 36 if tk.plate_frame else 38), cx.A(tk.c("muted"), dim))
    p = eo((lt - swap_at) / 0.5)
    if p > 0:
        cx.rr(right_box, 2, outline=cx.A(tk.c("g1"), p), width=2)
        cx.text((rx, 920), right_title, cx.F("head", 56), cx.A(tk.c("ink"), p))
        cx.text((rx, 1030), right_sub, cx.F("sub", 36 if tk.plate_frame else 38), cx.A(tk.c("muted"), p))


def scale_shift(cx: Ctx, lt, t, small="nm", small_sub="纳米 · 制程", big="mm",
                big_sub="毫米 · 打包", shift_at=3.4):
    tk = cx.tk
    cx.text((300, 900), small, cx.F("head", 80), cx.A(tk.c("g3")))
    cx.text((300, 1010), small_sub, cx.F("sub", 36), cx.A(tk.c("muted")))
    p = eo((lt - shift_at) / 0.5)
    if p > 0:
        cx.line([(430, 900), (430 + 130 * p, 900)], cx.A(tk.c("g2"), p), 3)
        cx.line([(534, 882), (560, 900), (534, 918)], cx.A(tk.c("g2"), p), 3)
        cx.text((760, 890), big, cx.F("head", int(150 * (0.8 + 0.2 * p))), cx.A(tk.c("ink"), p))
        cx.text((760, 1020), big_sub, cx.F("sub", 36), cx.A(tk.c("accent"), p))


def grow_box(cx: Ctx, lt, t, frame_label="头骨 = 封装", inner_label="大脑 = 芯片",
             grow_start=0.5, grow_dur=4.5, stamp_text="", stamp_at=5.9):
    tk = cx.tk
    c0, cy = 540, 980
    cx.rr((c0 - 260, cy - 260, c0 + 260, cy + 260), 6, outline=cx.A(tk.c("ink"), 0.9), width=3)
    cx.text((c0 + 175, cy + 300), frame_label, cx.F("sub", 34), cx.A(tk.c("muted")))
    g = 0.55 + 0.45 * eo((lt - grow_start) / grow_dur)
    hw = 250 * g
    cx.rr((c0 - hw, cy - hw, c0 + hw, cy + hw), 4, fill=cx.A(tk.c("g3")))
    cx.text((c0, cy), inner_label, cx.F("sub", 40), cx.A(tk.c("on_die")))
    if g > 0.985:
        flash = 0.5 + 0.5 * math.sin(t * 5)
        cx.rr((c0 - 262, cy - 262, c0 + 262, cy + 262), 6,
              outline=cx.A(tk.c("accent"), 0.55 * flash), width=5)
    if stamp_text and lt >= stamp_at:
        cx.badge(540, 1400, stamp_text, cx.F("num", 52), a=eo((lt - stamp_at) / 0.4))


def calendar_card(cx: Ctx, lt, t, top="2026", big="5月", sub="", sub_at=1.6):
    tk = cx.tk
    p = eo((lt - 0.25) / 0.5)
    if p > 0:
        cy = 1000 - (1 - p) * 100
        cx.rr((330, cy - 230, 750, cy - 120), 2, fill=cx.A(tk.c("accent") if not tk.lighting else tk.c("g2")))
        cx.text((540, cy - 175), top, cx.F("num", 58),
                cx.A(tk.c("card") if not tk.lighting else tk.c("on_die")))
        cx.rr((330, cy - 120, 750, cy + 230), 2,
              fill=cx.A(tk.c("card"), 0.97) if not tk.lighting else None,
              outline=cx.A(tk.c("g2")), width=2)
        cx.text((540, cy + 55), big, cx.F("head", 130), cx.A(tk.c("ink")))
    if sub and lt >= sub_at:
        cx.text((540, 1330), sub, cx.F("sub", 42), cx.A(tk.c("muted"), eo((lt - sub_at) / 0.4)))


def bar_pair(cx: Ctx, lt, t, base_y=1360, left_label="去年5月", right_label="今年5月",
             left_h=250, right_h=340, right_at=1.7, value_text="", value_at=1.85,
             badge_text="", badge_at=3.1, strike_text="", strike_note="", strike_at=3.75,
             stamp_text="", stamp_at=4.3):
    tk = cx.tk
    cx.line([(200, base_y), (880, base_y)], cx.A(tk.c("g2"), 0.6), 3)
    h1 = left_h * eo(clamp((lt - 0.15) / 0.6))
    cx.rr((270, base_y - h1, 450, base_y), 2 if tk.lighting else 12, fill=cx.A(tk.c("g3")))
    cx.text((360, base_y + 52), left_label, cx.F("sub", 38), cx.A(tk.c("muted")))
    p2 = eo(clamp((lt - right_at) / 0.8))
    h2 = right_h * p2
    if p2 > 0:
        col = tk.c("g1") if tk.lighting else tk.c("accent")
        cx.rr((630, base_y - h2, 810, base_y), 2 if tk.lighting else 12, fill=cx.A(col))
    cx.text((720, base_y + 52), right_label, cx.F("sub", 38), cx.A(tk.c("muted")))
    if value_text and lt >= value_at:            # 整值弹出（lessons #21）
        ap = eo((lt - value_at) / 0.3)
        cx.text((720, base_y - h2 - 44 - 12 * ap), value_text, cx.F("num", 50), cx.A(tk.c("ink"), ap))
    if badge_text and lt >= badge_at:
        cx.badge(720, base_y - h2 - 165, badge_text, cx.F("num", 58), a=eo((lt - badge_at) / 0.3))
    if strike_text and lt >= strike_at:
        a4 = eo((lt - strike_at) / 0.35)
        cx.text((360, base_y - left_h - 62), strike_text, cx.F("sub", 44), cx.A(tk.c("g3"), a4))
        w = cx.tw(strike_text, cx.F("sub", 44))
        cx.line([(360 - w/2 - 8, base_y - left_h - 62), (360 + w/2 + 8, base_y - left_h - 62)],
                cx.A(tk.c("alert"), a4), 4)
        cx.text((360, base_y - left_h - 112), strike_note, cx.F("sub", 32), cx.A(tk.c("muted"), a4))
    if stamp_text and lt >= stamp_at:
        a5 = eo((lt - stamp_at) / 0.3)
        cx.tracked(540, 610, stamp_text, cx.F("sub", 40), cx.A(tk.c("accent"), a5),
                   em=max(cx.tk.tracked_em * 2.5, 0.0), max_w=400)


def hero_number(cx: Ctx, lt, t, value="135.6", unit="", sub="", badge_text="", badge_at=3.1):
    tk = cx.tk
    ap = eo(clamp((lt - 0.2) / 0.35))
    cx.text((540, 930 - 14 * ap), value, cx.F("num", 170), cx.A(tk.c("accent"), ap))
    cx.text((540, 1075), unit, cx.F("sub", 50), cx.A(tk.c("ink"), ap * 0.92))
    cx.text((540, 1170), sub, cx.F("sub", 38), cx.A(tk.c("muted"), ap))
    if badge_text and lt >= badge_at:
        cx.hairbox(540, 1310, badge_text, cx.F("num", 48), col=tk.c("g2") if tk.lighting else tk.c("accent2"),
                   a=eo((lt - badge_at) / 0.3))


def kpi_duo(cx: Ctx, lt, t, items=(("量 ↑", "野村估算 ≈281亿"), ("价 ↑", "技术溢价")),
            at1=0.2, at2=0.9, stamp_text="", stamp_at=2.9, foot_text="", foot_at=4.1):
    tk = cx.tk
    # plate_frame print well is inset by ~mat; keep plaques inside cream lip
    if tk.plate_frame:
        centers, half, max_tw = (360, 720), 170, 300
    else:
        centers, half, max_tw = (315, 765), 200, 360
    for (cxp, (big, sub), at) in ((centers[0], items[0], at1), (centers[1], items[1], at2)):
        p = eo(clamp((lt - at) / 0.4))
        if p <= 0:
            continue
        cx.rr((cxp - half, 700, cxp + half, 1140), 2 if tk.lighting else 26,
              fill=None if tk.lighting else cx.A(tk.c("card"), 0.97 * p),
              outline=cx.A(tk.c("g2") if tk.lighting else tk.c("accent"), p), width=2)
        big_size = 84 if tk.plate_frame else 92
        f_big = cx.F("head", big_size)
        while cx.tw(big, f_big) > max_tw and big_size > 40:
            big_size = int(big_size * 0.88)
            f_big = cx.F("head", big_size)
        cx.text((cxp, 850), big, f_big, cx.A(tk.c("ink"), p))
        sub_size = 32 if tk.plate_frame else 36
        cx.text((cxp, 1020), sub, cx.F("sub", sub_size), cx.A(tk.c("muted"), p))
    if stamp_text and lt >= stamp_at:
        cx.tracked(540, 500, stamp_text, cx.F("head", 72),
                   cx.A(tk.c("ink"), min(1, (lt - stamp_at) / 0.3)))
    if foot_text and lt >= foot_at:
        cx.text((540, 1250), foot_text, cx.F("sub", 42), cx.A(tk.c("muted"), eo((lt - foot_at) / 0.35)))


def board_transform(cx: Ctx, lt, t, label_a="塑料板", label_b="战略资产", glow_at=4.3,
                    swap_at=8.65, tags=(("布线密度 ↑", 330, 0.15), ("大尺寸 ↑", 750, 1.8)),
                    sub_text="", sub_at=2.45, tagline="", tag_at=9.4):
    tk = cx.tk
    glow = eo(clamp((lt - glow_at) / 2.2))
    cy = 950
    if glow > 0.1:
        ga = glow * (0.30 + 0.15 * math.sin(t * 4))
        cx.rr((216, cy - 214, 864, cy + 214), 8, fill=cx.A(tk.c("warm"), ga * 0.30))
    a, b = tk.c("g4"), (tk.c("g2") if tk.lighting else tk.c("warm"))
    col = tuple(int(a[i] + (b[i] - a[i]) * glow) for i in range(3))
    cx.rr((230, cy - 200, 850, cy + 200), 4 if tk.lighting else 30, fill=cx.A(col),
          outline=cx.A(tk.c("g2"), 0.6 + 0.4 * glow), width=2)
    lbl = label_b if lt >= swap_at else label_a
    cx.text((540, cy), lbl, cx.F("head", 92),
            cx.A(tk.c("on_die") if (glow > 0.5 or not tk.lighting) else tk.c("g2")))
    for (s_, x_, at_) in tags:
        p = eo(clamp((lt - at_) / 0.4))
        if p > 0:
            cx.text((x_, cy - 270), s_, cx.F("sub", 36), cx.A(tk.c("g2") if tk.lighting else tk.c("ink"), p))
    if sub_text and lt >= sub_at:
        cx.text((540, cy + 280), sub_text, cx.F("sub", 42), cx.A(tk.c("muted"), eo((lt - sub_at) / 0.4)))
    if tagline and lt >= tag_at:
        cx.tracked(540, 1400, tagline, cx.F("head", 64), cx.A(tk.c("ink"), eo((lt - tag_at) / 0.4)), em=None)


def quad_dies(cx: Ctx, lt, t, mode="assemble", label="", label_at=1.4):
    tk = cx.tk
    c0, cy = 540, 980
    cx.rr((c0 - 300, cy - 300, c0 + 300, cy + 300), 6, outline=cx.A(tk.c("g3"), 0.9), width=2)
    fade = 1.0 - 0.75 * eo((lt - 0.4) / 0.8) if mode == "reduce" else 1.0
    for i, (dx, dy) in enumerate(((-140, -140), (140, -140), (-140, 140), (140, 140))):
        if mode == "assemble":
            p = eo(clamp((lt - 0.4 - i * 0.25) / 0.4))
            if p <= 0:
                continue
            hw = 120 * p
            cx.rr((c0 + dx - hw, cy + dy - hw, c0 + dx + hw, cy + dy + hw), 4, fill=cx.A(tk.c("die")))
        else:
            gone = i in (1, 3)
            hw = 120
            if gone and fade < 0.6:
                cx.rr((c0 + dx - hw, cy + dy - hw, c0 + dx + hw, cy + dy + hw), 4,
                      outline=cx.A(tk.c("g3"), fade), width=2)
            else:
                cx.rr((c0 + dx - hw, cy + dy - hw, c0 + dx + hw, cy + dy + hw), 4,
                      fill=cx.A(tk.c("die"), fade if gone else 1.0))
    if label and lt >= label_at:
        cx.text((540, 1360), label, cx.F("num", 54), cx.A(tk.c("accent"), eo((lt - label_at) / 0.4)))


def limit_wall(cx: Ctx, lt, t, limit_label="5.5× 掩模版", bar_label="中介层",
               lines_at=2.6, lines_label="HBM4 · 布线极密", box_text="", box_at=9.4):
    tk = cx.tk
    cy, lim_x = 880, 810
    cx.line([(lim_x, cy - 130), (lim_x, cy + 210)], cx.A(tk.c("accent"), 0.8), 3)
    cx.text((lim_x, cy - 170), limit_label, cx.F("sub", 34), cx.A(tk.c("accent"), 0.9))
    g = eo(clamp((lt - 0.3) / 2.2))
    x1 = 190 + 700 * g
    cx.rr((190, cy, min(x1, lim_x), cy + 70), 2, fill=cx.A(tk.c("g3")))
    if x1 > lim_x:
        cx.rr((lim_x, cy, x1, cy + 70), 2, fill=cx.A(tk.c("g4")), outline=cx.A(tk.c("accent"), 0.7), width=2)
    cx.text((400, cy + 36), bar_label, cx.F("sub", 36), cx.A(tk.c("on_die")))
    if lt > lines_at:
        a2 = eo((lt - lines_at) / 0.5)
        ys = cy + 150
        for k in range(9):
            xx = 220 + k * 72
            cx.line([(xx, ys), (xx + 24, ys + 34), (xx - 10, ys + 66), (xx + 30, ys + 100)],
                    cx.A(tk.c("g2"), a2 * 0.85), 2.4)
        cx.text((540, ys + 150), lines_label, cx.F("sub", 36), cx.A(tk.c("muted"), a2))
    if box_text and lt >= box_at:
        cx.hairbox(540, 1330, box_text, cx.F("sub", 42), col=tk.c("g2") if tk.lighting else tk.c("accent"),
                   a=eo((lt - box_at) / 0.4))


def city_grid(cx: Ctx, lt, t, roads_at=0.8, label="再硬塞立体高速公路"):
    tk = cx.tk
    c0, cy = 540, 990
    for gx in range(-3, 4):
        for gy in range(-2, 3):
            hh = 26 + ((gx * 7 + gy * 13) % 40)
            cx.rr((c0 + gx*110 - 36, cy + gy*90 - hh, c0 + gx*110 + 36, cy + gy*90 + 28), 2,
                  fill=cx.A(tk.c("g4")), outline=cx.A(tk.c("g3"), 0.5), width=1)
    a2 = eo((lt - roads_at) / 0.8)
    if a2 > 0:
        for row in ((150, 1060, 480, 880, 760, 1010, 930, 900), (200, 900, 500, 1080, 700, 880, 920, 1060)):
            cx.line([(row[i], row[i+1]) for i in range(0, 8, 2)],
                    cx.A(tk.c("g2") if tk.lighting else tk.c("accent"), a2 * 0.9), 4)
        cx.text((540, 1300), label, cx.F("sub", 40), cx.A(tk.c("muted"), a2))


def gauge(cx: Ctx, lt, t, label="Tokens / Watt", sub="每瓦时能吐多少 Token"):
    tk = cx.tk
    c0, cy, r = 540, 1080, 300
    for k in range(37):
        ang = math.pi + k * math.pi / 36
        ln = 30 if k % 6 == 0 else 16
        cx.line([(c0 + math.cos(ang) * (r - ln), cy + math.sin(ang) * (r - ln)),
                 (c0 + math.cos(ang) * r, cy + math.sin(ang) * r)], cx.A(tk.c("g3"), 0.9), 2.5)
    sweep = eo(clamp((lt - 0.5) / 1.6))
    ang = math.pi * (1 + 0.78 * sweep)
    cx.line([(c0, cy), (c0 + math.cos(ang) * (r - 46), cy + math.sin(ang) * (r - 46))],
            cx.A(tk.c("accent")), 5)
    cx.ellipse((c0 - 10, cy - 10, c0 + 10, cy + 10), cx.A(tk.c("accent")))
    cx.text((540, 1180), label, cx.F("num", 54), cx.A(tk.c("ink")))
    cx.text((540, 1270), sub, cx.F("sub", 38), cx.A(tk.c("muted")))


def pipe_bandwidth(cx: Ctx, lt, t, left="GPU", right="HBM", widen_at=1.6,
                   label="内存容量 · 内存-GPU 带宽", label_at=1.9):
    tk = cx.tk
    wp = 4 + 12 * eo(clamp((lt - widen_at) / 0.8))
    cx.line([(430, 980), (650, 980)], cx.A(tk.c("g2") if tk.lighting else tk.c("accent")), wp)
    for (x0, s_) in ((180, left), (650, right)):
        cx.rr((x0, 880, x0 + 250, 1080), 2 if tk.lighting else 20,
              fill=None if tk.lighting else cx.A(tk.c("card")),
              outline=cx.A(tk.c("g2") if tk.lighting else tk.c("ink")), width=2)
        cx.text((x0 + 125, 980), s_, cx.F("head", 56), cx.A(tk.c("ink")))
    if lt > label_at:
        cx.text((540, 1180), label, cx.F("sub", 40), cx.A(tk.c("muted"), eo((lt - label_at) / 0.4)))


def onchip_keep(cx: Ctx, lt, t, tiles=("权重", "KV 缓存", "HBM"), out_label="主机内存 / 硬盘",
                fade_at=6.5, keep_label="少搬运"):
    tk = cx.tk
    c0, cy = 540, 980
    cx.rr((c0 - 300, cy - 220, c0 + 300, cy + 220), 4 if tk.lighting else 22,
          outline=cx.A(tk.c("g1") if tk.lighting else tk.c("ink"), 0.95), width=3)
    for i, (dx, lab) in enumerate(zip((-150, 0, 150), tiles)):
        p = eo(clamp((lt - 0.5 - i * 0.35) / 0.4))
        if p <= 0:
            continue
        cx.rr((c0 + dx - 65, cy - 60, c0 + dx + 65, cy + 60), 3 if tk.lighting else 12,
              fill=cx.A(tk.c("g3") if i < 2 else tk.c("g2"), p) if tk.lighting
              else cx.A(tk.c("die") if i < 2 else tk.c("hbm"), p))
        cx.text((c0 + dx, cy), lab, cx.F("sub", 34), cx.A(tk.c("on_die"), p))
    fade = 1.0 - eo(clamp((lt - fade_at) / 1.0))
    if fade > 0.02:
        cx.rr((c0 - 190, cy + 320, c0 + 190, cy + 420), 2, outline=cx.A(tk.c("g4"), fade), width=2)
        cx.text((c0, cy + 370), out_label, cx.F("sub", 34), cx.A(tk.c("g4"), fade))
        cx.line([(c0, cy + 224), (c0, cy + 316)], cx.A(tk.c("g4"), fade), 3)
    else:
        cx.text((c0, cy + 370), keep_label, cx.F("sub", 40), cx.A(tk.c("accent")))


def down_arrows(cx: Ctx, lt, t, items=("功耗", "响应延迟"), tail="下来"):
    tk = cx.tk
    for i, (xc, lab) in enumerate(zip((330, 750), items)):
        p = eo(clamp((lt - 0.2 - i * 0.7) / 0.5))
        if p <= 0:
            continue
        cx.text((xc, 800), lab, cx.F("head", 60), cx.A(tk.c("ink"), p))
        ay = 900 + 160 * p
        cx.line([(xc, 900), (xc, ay)], cx.A(tk.c("accent"), p), 6)
        cx.line([(xc - 30, ay - 36), (xc, ay), (xc + 30, ay - 36)], cx.A(tk.c("accent"), p), 6)
        cx.text((xc, ay + 70), tail, cx.F("sub", 42), cx.A(tk.c("muted"), p))


def converge(cx: Ctx, lt, t):
    tk = cx.tk
    g = eo(clamp((lt - 0.3) / 1.2))
    c0, cy = 540, 1000
    for (dx, dy) in ((-260, -200), (260, -200), (-260, 200), (260, 200)):
        x, y = c0 + dx * (1 - g), cy + dy * (1 - g)
        hw = 90 - 20 * g
        cx.rr((x - hw, y - hw, x + hw, y + hw), 4 if tk.lighting else 10, fill=cx.A(tk.c("die")))
    if g > 0.9:
        cx.rr((c0 - 210, cy - 210, c0 + 210, cy + 210), 6,
              outline=cx.A(tk.c("g1") if tk.lighting else tk.c("accent"), (g - 0.9) * 10), width=3)


def quiz_row(cx: Ctx, lt, t, items=(), start_at=0.4, stagger=0.55):
    tk = cx.tk
    # stay inside cream-mat print well on dark-gallery
    base_cy = 820 if tk.plate_frame else 750
    gap = 200 if tk.plate_frame else 240
    x0, x1 = (230, 850) if tk.plate_frame else (200, 880)
    for i, (k_, q_) in enumerate(items):
        p = eo(clamp((lt - start_at - i * stagger) / 0.5))
        if p <= 0:
            continue
        cy = base_cy + i * gap
        cx.rr((x0, cy - 80, x1, cy + 80), 2 if tk.lighting else 18,
              fill=None if tk.lighting else cx.A(tk.c("card"), 0.97 * p),
              outline=cx.A(tk.c("g2") if tk.lighting else tk.c("ink"), p), width=2)
        cx.text((x0 + 100, cy), k_, cx.F("num", 44), cx.A(tk.c("accent"), p))
        cx.text(((x0 + x1) / 2 + 40, cy), q_, cx.F("sub", 38 if tk.plate_frame else 40),
                cx.A(tk.c("ink"), p))


PRIMS.update({
    "loading_bar": loading_bar, "duel_plates": duel_plates, "scale_shift": scale_shift,
    "grow_box": grow_box, "calendar_card": calendar_card, "bar_pair": bar_pair,
    "hero_number": hero_number, "kpi_duo": kpi_duo, "board_transform": board_transform,
    "quad_dies": quad_dies, "limit_wall": limit_wall, "city_grid": city_grid,
    "gauge": gauge, "pipe_bandwidth": pipe_bandwidth, "onchip_keep": onchip_keep,
    "down_arrows": down_arrows, "converge": converge, "quiz_row": quiz_row,
})
