"""draw — 绘制上下文与共享助手（字体缓存 / 圆角 / 追踪字距 / 缓动）。"""
from __future__ import annotations

import math
import os

from PIL import ImageDraw, ImageFont

from .style import FONT_DIR


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def back(t):
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


_FONT_CACHE: dict = {}


class Ctx:
    """一个 beat 的绘制上下文：d=ImageDraw, tk=Style, S=超采样, al=beat 透明度(仅 fade 风格<1)."""

    def __init__(self, d: ImageDraw.ImageDraw, tk, S: int, al: float = 1.0):
        self.d, self.tk, self.S, self.al = d, tk, S, al

    # ---- fonts（模块级缓存，跨帧复用） ----
    def F(self, role: str, size: float):
        fname = self.tk.fonts.get(role) or self.tk.fonts["body"]
        key = (fname, int(size * self.S))
        if key not in _FONT_CACHE:
            fdir = os.environ.get("OM_FONT_DIR", FONT_DIR)
            path = fdir + fname
            try:
                _FONT_CACHE[key] = ImageFont.truetype(path, int(size * self.S), index=2)
            except OSError:
                # macOS often ships single-face OTF (Source Han / Noto SC); index=2 is Linux TTC SC face
                _FONT_CACHE[key] = ImageFont.truetype(path, int(size * self.S), index=0)
        return _FONT_CACHE[key]

    # ---- shapes / text ----
    def A(self, col, a=1.0):
        return (col[0], col[1], col[2], int(255 * clamp(a * self.al)))

    def rr(self, box, r, fill=None, outline=None, width=1):
        S = self.S
        self.d.rounded_rectangle([box[0]*S, box[1]*S, box[2]*S, box[3]*S],
                                 radius=max(1, int(r*S)), fill=fill, outline=outline,
                                 width=max(1, int(width*S)))

    def line(self, pts, fill, width=2):
        S = self.S
        self.d.line([(x*S, y*S) for x, y in pts], fill=fill, width=max(1, int(width*S)))

    def ellipse(self, box, fill):
        S = self.S
        self.d.ellipse([box[0]*S, box[1]*S, box[2]*S, box[3]*S], fill=fill)

    def text(self, xy, s, font, fill, anchor="mm"):
        self.d.text((xy[0]*self.S, xy[1]*self.S), s, font=font, fill=fill, anchor=anchor)

    def tw(self, s, font):
        b = self.d.textbbox((0, 0), s, font=font)
        return (b[2] - b[0]) / self.S

    def tracked(self, cx, cy, s, font, fill, em=None, max_w=920):
        """展签式逐字加距；em=None 用风格默认；超宽自动缩号。em=0 时走普通居中。"""
        em = self.tk.tracked_em if em is None else em
        if em <= 0.001:
            self.text((cx, cy), s, font, fill)
            return
        size = font.size / self.S
        while True:
            ws = [self.tw(ch, font) for ch in s]
            gap = size * em
            total = sum(ws) + gap * (len(s) - 1)
            if total <= max_w or size < 26:
                break
            size *= 0.92
            # Linux Noto CJK TTC uses face index=2 (SC); macOS single-face packages need 0
            try:
                font = ImageFont.truetype(font.path, int(size * self.S), index=2)
            except OSError:
                font = ImageFont.truetype(font.path, int(size * self.S), index=0)
        x = cx - total / 2
        for ch, w_ in zip(s, ws):
            self.d.text(((x + w_/2)*self.S, cy*self.S), ch, font=font, fill=fill, anchor="mm")
            x += w_ + gap

    def chip(self, cx, cy, s, font, fg, bg, a=1.0, pad=36, hh=46, radius=18):
        w_ = self.tw(s, font)
        self.rr((cx - w_/2 - pad, cy - hh, cx + w_/2 + pad, cy + hh), radius, fill=self.A(bg, a))
        self.text((cx, cy), s, font, self.A(fg, a))

    def hairbox(self, cx, cy, s, font, col=None, a=1.0, pad=40, hh=48):
        col = col or self.tk.c("accent")
        w_ = self.tw(s, font)
        self.rr((cx - w_/2 - pad, cy - hh, cx + w_/2 + pad, cy + hh), 1,
                fill=self.A(self.tk.c("bg"), a * 0.9), outline=self.A(col, a * 0.9), width=2)
        self.text((cx, cy), s, font, self.A(col, a))

    def badge(self, cx, cy, s, font, a=1.0):
        """风格化重点标签：dark=hairbox 暖白；clay=墨底奶字圆角 pill。"""
        if self.tk.lighting:
            self.hairbox(cx, cy, s, font, a=a)
        else:
            self.chip(cx, cy, s, font, self.tk.c("card"), self.tk.c("ink"), a=a, radius=18)
