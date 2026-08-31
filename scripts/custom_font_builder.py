#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
custom_font_builder.py
======================

Programmatically designs and compiles a complete, functional TrueType font
from scratch using only fontTools (fontTools.fontBuilder + TTGlyphPen).

Design: minimalist geometric sans-serif built from clean straight lines and
quadratic Bézier circle/ellipse segments.

Metrics:
    UPM 1000 | ascender 800 | descender -200 | cap height 700 | x-height 500

Glyph set (84 glyphs):
    .notdef, space, NBSP, A-Z, a-z, 0-9,  . , ! ? - / :
    Turkish: ı İ ç Ç ğ Ğ ö Ö ş Ş ü Ü

Run:
    pip install fonttools
    python custom_font_builder.py      # writes ./custom_font.ttf
"""

import math

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


# ---------------------------------------------------------------------------
# Global design constants
# ---------------------------------------------------------------------------
UPM        = 1000
ASCENDER   = 800
DESCENDER  = -200
CAP_HEIGHT = 700
X_HEIGHT   = 500

# Control-point radius factor for a 90° quadratic Bézier circle segment.
# Derived so the curve passes exactly through the 45° point of the arc.
ARC_F = 2.0 - math.sqrt(2.0) / 2.0          # ≈ 1.29289


def pt(x, y):
    """TrueType glyf coordinates are integers."""
    return (int(round(x)), int(round(y)))


def rad(deg):
    return deg * math.pi / 180.0


# ---------------------------------------------------------------------------
# Bounding-box recorder (exact curve extrema, not just control points)
# ---------------------------------------------------------------------------
class BboxRecorder(object):
    """Wraps a target pen, forwards every drawing operator to it, and
    computes the exact outline bounding box (sampling true quadratic
    extrema).  Needed for correct hmtx sidebearings and head bounds."""

    def __init__(self, target):
        self.target = target
        self.minx = self.miny = self.maxx = self.maxy = None
        self._cur = (0, 0)

    def _update(self, x, y):
        if self.minx is None:
            self.minx = self.maxx = x
            self.miny = self.maxy = y
        else:
            self.minx = min(self.minx, x)
            self.maxx = max(self.maxx, x)
            self.miny = min(self.miny, y)
            self.maxy = max(self.maxy, y)

    def moveTo(self, p):
        self._cur = p
        self._update(p[0], p[1])
        self.target.moveTo(p)

    def lineTo(self, p):
        self._cur = p
        self._update(p[0], p[1])
        self.target.lineTo(p)

    def qCurveTo(self, *points):
        pts = list(points)
        offs, on = pts[:-1], pts[-1]
        prev = self._cur
        for i, off in enumerate(offs):
            if i < len(offs) - 1:  # implied on-curve point
                nxt = ((off[0] + offs[i + 1][0]) / 2.0,
                       (off[1] + offs[i + 1][1]) / 2.0)
            else:
                nxt = on
            self._quad_bounds(prev, off, nxt)
            prev = nxt
        self._cur = on
        self.target.qCurveTo(*points)

    def _quad_bounds(self, p0, p1, p2):
        self._update(p0[0], p0[1])
        self._update(p2[0], p2[1])
        for i in (0, 1):
            a, b, c = p0[i], p1[i], p2[i]
            denom = a - 2.0 * b + c
            if denom != 0.0:
                t = (a - b) / denom
                if 0.0 < t < 1.0:
                    mt = 1.0 - t
                    x = mt * mt * p0[0] + 2.0 * mt * t * p1[0] + t * t * p2[0]
                    y = mt * mt * p0[1] + 2.0 * mt * t * p1[1] + t * t * p2[1]
                    self._update(x, y)

    def closePath(self):
        self.target.closePath()

    def endPath(self):
        self.target.endPath()

    @property
    def bounds(self):
        if self.minx is None:
            return None
        return (int(math.floor(self.minx)), int(math.floor(self.miny)),
                int(math.ceil(self.maxx)), int(math.ceil(self.maxy)))


# ---------------------------------------------------------------------------
# Drawing primitives (all solid shapes CCW, all holes CW -> nonzero fill)
# ---------------------------------------------------------------------------
def rect(pen, x0, y0, x1, y1):
    """Filled rectangle (counter-clockwise)."""
    pen.moveTo(pt(x0, y0))
    pen.lineTo(pt(x0, y1))
    pen.lineTo(pt(x1, y1))
    pen.lineTo(pt(x1, y0))
    pen.closePath()


def _signed_area2(pts):
    s = 0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return s


def polygon(pen, pts, ccw=True):
    """Filled polygon with guaranteed winding direction."""
    pts = [pt(x, y) for (x, y) in pts]
    if (_signed_area2(pts) > 0) != ccw:
        pts = pts[::-1]
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()


def arc_to(pen, cx, cy, rx, ry, a0, a1):
    """Emit quadratic Bézier segments approximating an elliptical arc from
    angle a0 to a1 (degrees).  The span must be a non-zero multiple of 90;
    its sign sets the direction.  The pen must already sit at the start."""
    span = a1 - a0
    assert span != 0 and span % 90 == 0, "arc span must be a multiple of 90"
    step = 90 if span > 0 else -90
    a = a0
    for _ in range(abs(span) // 90):
        mid = rad(a + step / 2.0)
        a += step
        end = rad(a)
        pen.qCurveTo(
            pt(cx + rx * math.cos(mid) * ARC_F, cy + ry * math.sin(mid) * ARC_F),
            pt(cx + rx * math.cos(end), cy + ry * math.sin(end)),
        )


def ellipse(pen, cx, cy, rx, ry, hole=False):
    """Full ellipse; CCW for solids, CW for holes."""
    pen.moveTo(pt(cx + rx, cy))
    arc_to(pen, cx, cy, rx, ry, 0, -360 if hole else 360)
    pen.closePath()


def ring(pen, cx, cy, rxo, ryo, rxi, ryi):
    """Elliptical ring (O, o, 0, 8 ...)."""
    ellipse(pen, cx, cy, rxo, ryo, hole=False)
    ellipse(pen, cx, cy, rxi, ryi, hole=True)


def c_shape(pen, cx, cy, rxo, ryo, rxi, ryi, g0, g1):
    """Ring with an angular gap [g0, g1] and flat radial terminals (C, c, e)."""
    pen.moveTo(pt(cx + rxo * math.cos(rad(g1)), cy + ryo * math.sin(rad(g1))))
    arc_to(pen, cx, cy, rxo, ryo, g1, g0 + 360)
    pen.lineTo(pt(cx + rxi * math.cos(rad(g0)), cy + ryi * math.sin(rad(g0))))
    arc_to(pen, cx, cy, rxi, ryi, g0 + 360, g1)
    pen.closePath()


def arch_up(pen, cx, cy, rxo, ryo, rxi, ryi, base=0):
    """'n' shaped arch: half ring whose legs run down to `base`."""
    pen.moveTo(pt(cx - rxo, base))
    pen.lineTo(pt(cx - rxo, cy))
    arc_to(pen, cx, cy, rxo, ryo, 180, 0)
    pen.lineTo(pt(cx + rxo, base))
    pen.lineTo(pt(cx + rxi, base))
    pen.lineTo(pt(cx + rxi, cy))
    arc_to(pen, cx, cy, rxi, ryi, 0, 180)
    pen.lineTo(pt(cx - rxi, base))
    pen.closePath()


def arch_down(pen, cx, cy, rxo, ryo, rxi, ryi, top):
    """'u' shaped inverted arch."""
    pen.moveTo(pt(cx - rxo, top))
    pen.lineTo(pt(cx - rxo, cy))
    arc_to(pen, cx, cy, rxo, ryo, 180, 360)
    pen.lineTo(pt(cx + rxo, top))
    pen.lineTo(pt(cx + rxi, top))
    pen.lineTo(pt(cx + rxi, cy))
    arc_to(pen, cx, cy, rxi, ryi, 360, 180)
    pen.lineTo(pt(cx - rxi, top))
    pen.closePath()


def dot(pen, cx, cy, r):
    ellipse(pen, cx, cy, r, r, hole=False)


def breve(pen, cx, yb):
    """Breve accent (upward-opening cup), centered on cx, baseline yb."""
    pen.moveTo(pt(cx - 120, yb))
    arc_to(pen, cx, yb, 120, 70, 180, 360)
    pen.lineTo(pt(cx + 60, yb))
    arc_to(pen, cx, yb, 60, 20, 360, 180)
    pen.closePath()


def cedilla(pen, cx):
    """Minimal geometric cedilla hook below the baseline, centered on cx."""
    rect(pen, cx - 32, -80, cx + 33, 10)
    rect(pen, cx - 92, -140, cx + 33, -80)


# ---------------------------------------------------------------------------
# Glyph builders:  name -> (advanceWidth, drawFunction)
# Cap box:   x 70..630 (width 560), y 0..700, advance 700 (unless noted)
# Lower box: x 70..550 (width 480), y 0..500, advance 620 (unless noted)
# Stroke width: 80 units everywhere.
# ---------------------------------------------------------------------------
BUILDERS = {}


def glyph(name, advance):
    def register(fn):
        BUILDERS[name] = (advance, fn)
        return fn
    return register


# ---------------------------- whitespace / .notdef -------------------------
@glyph("space", 260)
def _space(p):
    pass


@glyph("uni00A0", 260)
def _nbspace(p):
    pass


@glyph(".notdef", 500)
def _notdef(p):
    rect(p, 40, 0, 460, 700)
    polygon(p, [(100, 60), (400, 60), (400, 640), (100, 640)], ccw=False)


# ------------------------------ UPPERCASE A-Z ------------------------------
@glyph("A", 700)
def _A(p):
    polygon(p, [(70, 0), (160, 0), (350, 475), (540, 0), (630, 0), (350, 700)])
    polygon(p, [(264, 260), (436, 260), (350, 475)], ccw=False)   # counter
    rect(p, 200, 180, 500, 260)                                    # crossbar


@glyph("B", 700)
def _B(p):
    p.moveTo(pt(70, 0))
    p.lineTo(pt(350, 0))
    arc_to(p, 350, 175, 280, 175, -90, 90)
    arc_to(p, 350, 525, 280, 175, -90, 90)
    p.lineTo(pt(70, 700))
    p.closePath()
    p.moveTo(pt(150, 430)); p.lineTo(pt(150, 620)); p.lineTo(pt(350, 620))
    arc_to(p, 350, 525, 200, 95, 90, -90)
    p.closePath()
    p.moveTo(pt(150, 80)); p.lineTo(pt(150, 270)); p.lineTo(pt(350, 270))
    arc_to(p, 350, 175, 200, 95, 90, -90)
    p.closePath()


@glyph("C", 700)
def _C(p):
    c_shape(p, 350, 350, 280, 350, 200, 270, -45, 45)


@glyph("D", 700)
def _D(p):
    p.moveTo(pt(70, 0))
    p.lineTo(pt(350, 0))
    arc_to(p, 350, 350, 280, 350, -90, 90)
    p.lineTo(pt(70, 700))
    p.closePath()
    p.moveTo(pt(150, 80)); p.lineTo(pt(150, 620)); p.lineTo(pt(350, 620))
    arc_to(p, 350, 350, 200, 270, 90, -90)
    p.closePath()


@glyph("E", 640)
def _E(p):
    rect(p, 70, 0, 150, 700)
    rect(p, 150, 620, 570, 700)
    rect(p, 150, 310, 520, 390)
    rect(p, 150, 0, 570, 80)


@glyph("F", 620)
def _F(p):
    rect(p, 70, 0, 150, 700)
    rect(p, 150, 620, 550, 700)
    rect(p, 150, 310, 500, 390)


@glyph("G", 700)
def _G(p):
    c_shape(p, 350, 350, 280, 350, 200, 270, -45, 45)
    rect(p, 350, 310, 630, 390)     # crossbar
    rect(p, 500, 0, 630, 390)       # lower right stem


@glyph("H", 700)
def _H(p):
    rect(p, 70, 0, 150, 700)
    rect(p, 550, 0, 630, 700)
    rect(p, 150, 310, 550, 390)


@glyph("I", 220)
def _I(p):
    rect(p, 70, 0, 150, 700)


@glyph("J", 600)
def _J(p):
    rect(p, 380, 0, 460, 700)
    rect(p, 60, 0, 460, 80)
    rect(p, 60, 80, 140, 220)


@glyph("K", 700)
def _K(p):
    rect(p, 70, 0, 150, 700)
    polygon(p, [(130, 220), (130, 340), (510, 700), (630, 700)])
    polygon(p, [(130, 260), (130, 380), (510, 0), (630, 0)])


@glyph("L", 580)
def _L(p):
    rect(p, 70, 0, 150, 700)
    rect(p, 150, 0, 510, 80)


@glyph("M", 760)
def _M(p):
    rect(p, 70, 0, 150, 700)
    rect(p, 610, 0, 690, 700)
    polygon(p, [(90, 700), (190, 700), (410, 150), (310, 150)])
    polygon(p, [(670, 700), (570, 700), (350, 150), (450, 150)])


@glyph("N", 700)
def _N(p):
    rect(p, 70, 0, 150, 700)
    rect(p, 550, 0, 630, 700)
    polygon(p, [(70, 700), (180, 700), (630, 0), (520, 0)])


@glyph("O", 700)
def _O(p):
    ring(p, 350, 350, 280, 350, 200, 270)


@glyph("P", 700)
def _P(p):
    p.moveTo(pt(70, 0))
    p.lineTo(pt(150, 0))
    p.lineTo(pt(150, 350))
    p.lineTo(pt(350, 350))
    arc_to(p, 350, 525, 280, 175, -90, 90)
    p.lineTo(pt(70, 700))
    p.closePath()
    p.moveTo(pt(150, 430)); p.lineTo(pt(150, 620)); p.lineTo(pt(350, 620))
    arc_to(p, 350, 525, 200, 95, 90, -90)
    p.closePath()


@glyph("Q", 700)
def _Q(p):
    ring(p, 350, 350, 280, 350, 200, 270)
    polygon(p, [(380, 190), (460, 270), (650, 60), (570, -20)])


@glyph("R", 700)
def _R(p):
    _P(p)
    polygon(p, [(300, 350), (420, 350), (630, 0), (510, 0)])


@glyph("S", 700)
def _S(p):
    rect(p, 70, 620, 630, 700)
    rect(p, 70, 350, 150, 700)
    rect(p, 70, 270, 630, 350)
    rect(p, 550, 0, 630, 350)
    rect(p, 70, 0, 630, 80)


@glyph("T", 640)
def _T(p):
    rect(p, 70, 620, 570, 700)
    rect(p, 280, 0, 360, 620)


@glyph("U", 700)
def _U(p):
    p.moveTo(pt(70, 700))
    p.lineTo(pt(70, 280))
    arc_to(p, 350, 280, 280, 280, 180, 360)
    p.lineTo(pt(630, 700))
    p.lineTo(pt(550, 700))
    p.lineTo(pt(550, 280))
    arc_to(p, 350, 280, 200, 200, 360, 180)
    p.lineTo(pt(150, 700))
    p.closePath()


@glyph("V", 700)
def _V(p):
    polygon(p, [(70, 700), (180, 700), (400, 0), (290, 0)])
    polygon(p, [(630, 700), (520, 700), (300, 0), (410, 0)])


@glyph("W", 940)
def _W(p):
    polygon(p, [(70, 700), (170, 700), (350, 0), (250, 0)])
    polygon(p, [(250, 0), (350, 0), (520, 380), (420, 380)])
    polygon(p, [(420, 380), (520, 380), (690, 0), (590, 0)])
    polygon(p, [(590, 0), (690, 0), (870, 700), (770, 700)])


@glyph("X", 700)
def _X(p):
    polygon(p, [(70, 0), (190, 0), (630, 700), (510, 700)])
    polygon(p, [(510, 0), (630, 0), (190, 700), (70, 700)])


@glyph("Y", 700)
def _Y(p):
    polygon(p, [(70, 700), (190, 700), (390, 400), (390, 220)])
    polygon(p, [(630, 700), (510, 700), (310, 400), (310, 220)])
    rect(p, 310, 0, 390, 310)


@glyph("Z", 700)
def _Z(p):
    rect(p, 70, 620, 630, 700)
    rect(p, 70, 0, 630, 80)
    polygon(p, [(490, 620), (630, 620), (210, 80), (70, 80)])


# ------------------------------ lowercase a-z ------------------------------
@glyph("a", 620)
def _a(p):
    ring(p, 280, 250, 210, 250, 130, 170)
    rect(p, 470, 0, 550, 500)


@glyph("b", 620)
def _b(p):
    rect(p, 70, 0, 150, 700)
    ring(p, 345, 250, 205, 250, 125, 170)


@glyph("c", 620)
def _c(p):
    c_shape(p, 310, 250, 240, 250, 160, 170, -45, 45)


@glyph("d", 620)
def _d(p):
    ring(p, 280, 250, 210, 250, 130, 170)
    rect(p, 470, 0, 550, 700)


@glyph("e", 620)
def _e(p):
    c_shape(p, 310, 250, 240, 250, 160, 170, -90, 0)
    rect(p, 70, 210, 550, 290)


@glyph("f", 500)
def _f(p):
    rect(p, 190, 0, 270, 620)
    rect(p, 190, 620, 430, 700)
    rect(p, 70, 420, 390, 500)


@glyph("g", 620)
def _g(p):
    ring(p, 280, 250, 210, 250, 130, 170)
    rect(p, 470, -180, 550, 500)
    rect(p, 230, -180, 550, -100)


@glyph("h", 620)
def _h(p):
    rect(p, 70, 0, 150, 700)
    arch_up(p, 310, 250, 240, 250, 160, 170, base=0)


@glyph("i", 400)
def _i(p):
    rect(p, 160, 0, 240, 500)
    dot(p, 200, 650, 60)


@glyph("j", 400)
def _j(p):
    rect(p, 160, -180, 240, 500)
    rect(p, 60, -180, 240, -100)
    dot(p, 200, 650, 60)


@glyph("k", 620)
def _k(p):
    rect(p, 70, 0, 150, 700)
    polygon(p, [(130, 180), (130, 320), (375, 500), (550, 500)])
    polygon(p, [(130, 240), (130, 360), (430, 0), (570, 0)])


@glyph("l", 400)
def _l(p):
    rect(p, 160, 0, 240, 700)


@glyph("m", 900)
def _m(p):
    rect(p, 70, 0, 150, 500)
    arch_up(p, 280, 250, 210, 250, 130, 170, base=0)
    arch_up(p, 620, 250, 210, 250, 130, 170, base=0)


@glyph("n", 620)
def _n(p):
    rect(p, 70, 0, 150, 500)
    arch_up(p, 310, 250, 240, 250, 160, 170, base=0)


@glyph("o", 620)
def _o(p):
    ring(p, 310, 250, 240, 250, 160, 170)


@glyph("p", 620)
def _p(p):
    rect(p, 70, -180, 150, 500)
    ring(p, 345, 250, 205, 250, 125, 170)


@glyph("q", 620)
def _q(p):
    ring(p, 280, 250, 210, 250, 130, 170)
    rect(p, 470, -180, 550, 500)


@glyph("r", 480)
def _r(p):
    rect(p, 70, 0, 150, 500)
    p.moveTo(pt(130, 500))
    p.lineTo(pt(210, 500))
    arc_to(p, 210, 250, 200, 250, 90, 0)
    p.lineTo(pt(330, 250))
    arc_to(p, 210, 250, 120, 170, 0, 90)
    p.lineTo(pt(130, 420))
    p.closePath()


@glyph("s", 620)
def _s(p):
    rect(p, 70, 420, 550, 500)
    rect(p, 70, 250, 150, 500)
    rect(p, 70, 170, 550, 250)
    rect(p, 470, 0, 550, 250)
    rect(p, 70, 0, 550, 80)


@glyph("t", 500)
def _t(p):
    rect(p, 190, 0, 270, 650)
    rect(p, 70, 420, 430, 500)
    rect(p, 190, 0, 390, 80)


@glyph("u", 620)
def _u(p):
    arch_down(p, 310, 250, 240, 250, 160, 170, top=500)


@glyph("v", 600)
def _v(p):
    polygon(p, [(70, 500), (160, 500), (340, 0), (250, 0)])
    polygon(p, [(530, 500), (440, 500), (260, 0), (350, 0)])


@glyph("w", 820)
def _w(p):
    polygon(p, [(70, 500), (155, 500), (305, 0), (220, 0)])
    polygon(p, [(220, 0), (305, 0), (430, 300), (345, 300)])
    polygon(p, [(345, 300), (430, 300), (555, 0), (470, 0)])
    polygon(p, [(470, 0), (555, 0), (750, 500), (665, 500)])


@glyph("x", 600)
def _x(p):
    polygon(p, [(70, 0), (160, 0), (530, 500), (440, 500)])
    polygon(p, [(440, 0), (530, 0), (160, 500), (70, 500)])


@glyph("y", 600)
def _y(p):
    polygon(p, [(70, 500), (160, 500), (400, -180), (310, -180)])
    polygon(p, [(530, 500), (440, 500), (200, -180), (290, -180)])


@glyph("z", 600)
def _z(p):
    rect(p, 70, 420, 530, 500)
    rect(p, 70, 0, 530, 80)
    polygon(p, [(400, 420), (530, 420), (200, 80), (70, 80)])


# -------------------------------- digits -----------------------------------
@glyph("zero", 700)
def _zero(p):
    ring(p, 350, 350, 280, 350, 200, 270)


@glyph("one", 440)
def _one(p):
    rect(p, 180, 0, 260, 700)


@glyph("two", 700)
def _two(p):
    rect(p, 70, 620, 630, 700)
    rect(p, 550, 350, 630, 700)
    rect(p, 70, 270, 630, 350)
    rect(p, 70, 0, 150, 350)
    rect(p, 70, 0, 630, 80)


@glyph("three", 700)
def _three(p):
    rect(p, 70, 620, 630, 700)
    rect(p, 550, 0, 630, 700)
    rect(p, 150, 310, 630, 390)
    rect(p, 70, 0, 630, 80)


@glyph("four", 700)
def _four(p):
    rect(p, 70, 280, 150, 700)
    rect(p, 70, 200, 630, 280)
    rect(p, 470, 0, 550, 700)


@glyph("five", 700)
def _five(p):
    rect(p, 70, 620, 630, 700)
    rect(p, 70, 350, 150, 700)
    rect(p, 70, 270, 630, 350)
    rect(p, 550, 0, 630, 350)
    rect(p, 70, 0, 630, 80)


@glyph("six", 700)
def _six(p):
    ring(p, 350, 280, 280, 280, 200, 200)
    rect(p, 70, 280, 150, 700)


@glyph("seven", 700)
def _seven(p):
    rect(p, 70, 620, 630, 700)
    polygon(p, [(490, 620), (630, 620), (390, 0), (270, 0)])


@glyph("eight", 700)
def _eight(p):
    ring(p, 350, 515, 230, 185, 150, 105)
    ring(p, 350, 185, 260, 185, 180, 105)


@glyph("nine", 700)
def _nine(p):
    ring(p, 350, 420, 280, 280, 200, 200)
    rect(p, 550, 0, 630, 420)


# ------------------------------ punctuation --------------------------------
@glyph("period", 340)
def _period(p):
    dot(p, 170, 70, 60)


@glyph("comma", 340)
def _comma(p):
    dot(p, 170, 90, 70)
    polygon(p, [(115, 100), (225, 100), (185, -130), (125, -130)])


@glyph("exclam", 340)
def _exclam(p):
    rect(p, 130, 220, 210, 700)
    dot(p, 170, 70, 60)


@glyph("question", 500)
def _question(p):
    rect(p, 60, 620, 440, 700)
    rect(p, 360, 390, 440, 700)
    rect(p, 200, 310, 440, 390)
    rect(p, 200, 180, 280, 390)
    dot(p, 240, 70, 60)


@glyph("hyphen", 500)
def _hyphen(p):
    rect(p, 70, 260, 430, 340)


@glyph("slash", 440)
def _slash(p):
    polygon(p, [(250, 750), (340, 750), (190, -50), (100, -50)])


@glyph("colon", 340)
def _colon(p):
    dot(p, 170, 110, 60)
    dot(p, 170, 390, 60)


# -------------------------- Turkish extended set ---------------------------
@glyph("dotlessi", 400)
def _dotlessi(p):          # ı
    rect(p, 160, 0, 240, 500)


@glyph("Idotaccent", 220)
def _Idotaccent(p):        # İ
    rect(p, 70, 0, 150, 700)
    dot(p, 110, 780, 55)


@glyph("ccedilla", 620)
def _ccedilla(p):          # ç
    _c(p)
    cedilla(p, 310)


@glyph("Ccedilla", 700)
def _Ccedilla(p):          # Ç
    _C(p)
    cedilla(p, 350)


@glyph("gbreve", 620)
def _gbreve(p):            # ğ
    _g(p)
    breve(p, 310, 640)


@glyph("Gbreve", 700)
def _Gbreve(p):            # Ğ
    _G(p)
    breve(p, 350, 840)


@glyph("odieresis", 620)
def _odieresis(p):         # ö
    _o(p)
    dot(p, 200, 610, 55)
    dot(p, 420, 610, 55)


@glyph("Odieresis", 700)
def _Odieresis(p):         # Ö
    _O(p)
    dot(p, 240, 780, 55)
    dot(p, 460, 780, 55)


@glyph("scedilla", 620)
def _scedilla(p):          # ş
    _s(p)
    cedilla(p, 310)


@glyph("Scedilla", 700)
def _Scedilla(p):          # Ş
    _S(p)
    cedilla(p, 350)


@glyph("udieresis", 620)
def _udieresis(p):         # ü
    _u(p)
    dot(p, 200, 610, 55)
    dot(p, 420, 610, 55)


@glyph("Udieresis", 700)
def _Udieresis(p):         # Ü
    _U(p)
    dot(p, 240, 780, 55)
    dot(p, 460, 780, 55)


# ---------------------------------------------------------------------------
# Glyph order + Unicode cmap
# ---------------------------------------------------------------------------
UPPER = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
LOWER = list("abcdefghijklmnopqrstuvwxyz")
DIGIT_NAMES = ["zero", "one", "two", "three", "four",
               "five", "six", "seven", "eight", "nine"]
PUNCT = ["period", "comma", "exclam", "question", "hyphen", "slash", "colon"]
TURKISH = ["dotlessi", "Idotaccent", "ccedilla", "Ccedilla",
           "gbreve", "Gbreve", "odieresis", "Odieresis",
           "scedilla", "Scedilla", "udieresis", "Udieresis"]

GLYPH_ORDER = ([".notdef", "space", "uni00A0"] + UPPER + LOWER +
               DIGIT_NAMES + PUNCT + TURKISH)

CMAP = {0x0020: "space", 0x00A0: "uni00A0"}
CMAP.update({ord(ch): ch for ch in UPPER})
CMAP.update({ord(ch): ch for ch in LOWER})
CMAP.update({ord(d): n for d, n in zip("0123456789", DIGIT_NAMES)})
CMAP.update({0x2E: "period", 0x2C: "comma", 0x21: "exclam",
             0x3F: "question", 0x2D: "hyphen", 0x2F: "slash", 0x3A: "colon"})
CMAP.update({0x0131: "dotlessi", 0x0130: "Idotaccent",
             0x00E7: "ccedilla", 0x00C7: "Ccedilla",
             0x011F: "gbreve",   0x011E: "Gbreve",
             0x00F6: "odieresis", 0x00D6: "Odieresis",
             0x015F: "scedilla",  0x015E: "Scedilla",
             0x00FC: "udieresis", 0x00DC: "Udieresis"})

assert set(GLYPH_ORDER) == set(BUILDERS), "glyph order / builder mismatch"
assert len(GLYPH_ORDER) == len(set(GLYPH_ORDER))


# ---------------------------------------------------------------------------
# Draw every glyph, capture exact bounds, build metrics
# ---------------------------------------------------------------------------
def build_all_glyphs():
    glyphs, metrics, bounds = {}, {}, {}
    for name in GLYPH_ORDER:
        advance, fn = BUILDERS[name]
        ttpen = TTGlyphPen(None)
        rec = BboxRecorder(ttpen)
        fn(rec)
        g = ttpen.glyph()
        b = rec.bounds
        if b is not None:
            g.xMin, g.yMin, g.xMax, g.yMax = b
            metrics[name] = (advance, b[0])     # (advanceWidth, lsb)
            bounds[name] = b
        else:                                    # empty glyph (spaces)
            metrics[name] = (advance, 0)
        glyphs[name] = g
    return glyphs, metrics, bounds


# ---------------------------------------------------------------------------
# Assemble all tables with FontBuilder and save
# ---------------------------------------------------------------------------
def build_font(path="custom_font.ttf"):
    glyphs, metrics, bounds = build_all_glyphs()

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(GLYPH_ORDER)
    fb.setupCharacterMap(CMAP)

    # glyf (+ loca at compile time) and maxp
    fb.setupGlyf(glyphs)
    glyf_table = fb.font["glyf"]
    for name, b in bounds.items():               # enforce exact curve bounds
        g = glyf_table[name]
        g.xMin, g.yMin, g.xMax, g.yMax = b

    # hmtx
    fb.setupHorizontalMetrics(metrics)

    # hhea
    fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER)

    # name table -> Windows (3,1,0x409) AND Macintosh (1,0,0) records
    fb.setupNameTable({
        "familyName": "Custom Geometric Sans",
        "styleName": "Regular",
        "fullName": "Custom Geometric Sans Regular",
        "psName": "CustomGeometricSans-Regular",
        "uniqueFontIdentifier": "CustomGeometricSans-Regular;CSTM;2026",
        "version": "Version 1.000",
        "manufacturer": "Custom Foundry",
        "designer": "Typography Engineer",
        "description": "A minimalist geometric sans-serif designed and "
                       "compiled programmatically with fontTools.",
        "vendorURL": "",
        "licenseDescription": "Free to use, modify and embed.",
        "sampleText": "The quick brown fox jumps over the lazy dog.",
    })

    # OS/2 (v4 fields sxHeight/sCapHeight included)
    fb.setupOS2(
        sTypoAscender=ASCENDER,
        sTypoDescender=DESCENDER,
        usWinAscent=880,
        usWinDescent=220,
        sxHeight=X_HEIGHT,
        sCapHeight=CAP_HEIGHT,
        usWeightClass=400,
        usWidthClass=5,
        achVendID="CSTM",
        fsSelection=0x0040,                      # REGULAR
    )

    # post (format 2.0 keeps glyph names)
    fb.setupPost()

    # head overall bounding box
    head = fb.font["head"]
    all_b = list(bounds.values())
    head.xMin = min(b[0] for b in all_b)
    head.yMin = min(b[1] for b in all_b)
    head.xMax = max(b[2] for b in all_b)
    head.xMax = max(b[2] for b in all_b)
    head.yMax = max(b[3] for b in all_b)

    fb.save(path)
    return path


# ---------------------------------------------------------------------------
# Self-verification: reopen the file and check tables + cmap coverage
# ---------------------------------------------------------------------------
def verify(path):
    f = TTFont(path)
    for tag in ("cmap", "head", "hhea", "hmtx", "maxp",
                "name", "OS/2", "post", "glyf", "loca"):
        assert tag in f, "missing table: %s" % tag

    best = f.getBestCmap()
    for cp, gname in CMAP.items():
        assert best.get(cp) == gname, "cmap mismatch at U+%04X" % cp

    hmtx = f["hmtx"].metrics
    for gname in f.getGlyphOrder():
        adv, lsb = hmtx[gname]
        assert adv >= 0, gname

    os2 = f["OS/2"]
    head = f["head"]
    print("Saved            :", path)
    print("Tables           :", ", ".join(sorted(f.keys())))
    print("Glyphs           :", f["maxp"].numGlyphs)
    print("UPM / asc / desc : %d / %d / %d" %
          (head.unitsPerEm, f["hhea"].ascent, f["hhea"].descent))
    print("cap / x-height   : %d / %d" % (os2.sCapHeight, os2.sxHeight))
    print("Mapped codepoints:", len(best))
    print("Turkish test     : Pijamalı hasta yağız şoföre çabucak güvendi. İĞÇÖŞÜ ığçöşü")
    print("OK: font is valid and complete.")


if __name__ == "__main__":
    out = build_font("output/CustomGeometricSans-Regular.ttf")
    verify(out)
