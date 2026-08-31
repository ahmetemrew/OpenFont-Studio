#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
builder/build_font.py
=====================

Unified TrueType font compiler supporting:
- Multi-resolution solid pixel grids (8x8, 16x16, 32x32, 64x64, etc.)
- Vector contours (TrueType Quadratic Bézier & straight lines)
- Freehand vector strokes (expanded with stroke thickness)
- Complete Turkish alphabet, digits, symbols, and currency signs
"""

import json
import math
import sys
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


def pt(x, y):
    return (int(round(x)), int(round(y)))


def expand_polyline_to_contour(points, width):
    """Converts a sequence of 2D points into a closed ribbon contour of given stroke width."""
    if len(points) < 2:
        return []
    half_w = max(4.0, width / 2.0)
    left_pts = []
    right_pts = []

    for i in range(len(points)):
        p = points[i]
        px = p.get("x", 0)
        py = p.get("y", 0)

        if i == 0:
            p_next = points[i + 1]
            dx = p_next.get("x", 0) - px
            dy = p_next.get("y", 0) - py
        elif i == len(points) - 1:
            p_prev = points[i - 1]
            dx = px - p_prev.get("x", 0)
            dy = py - p_prev.get("y", 0)
        else:
            p_prev = points[i - 1]
            p_next = points[i + 1]
            dx = p_next.get("x", 0) - p_prev.get("x", 0)
            dy = p_next.get("y", 0) - p_prev.get("y", 0)

        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            nx, ny = 0, half_w
        else:
            nx = -dy / dist * half_w
            ny = dx / dist * half_w

        left_pts.append((px + nx, py + ny))
        right_pts.append((px - nx, py - ny))

    # CCW contour: left points forward, right points backward
    return left_pts + right_pts[::-1]


def draw_grid_to_pen(pen, grid, cell_w, cell_h):
    """Draws pixel grid cells as CCW solid rectangles."""
    rows = len(grid)
    if rows == 0:
        return
    cols = len(grid[0]) if rows > 0 else 0

    for r, row in enumerate(grid):
        # Y axis in TTF goes up from 0 to 1000. Grid row 0 is top (near capHeight 700/800)
        y = (rows - 1 - r) * cell_h
        for c, ch in enumerate(row):
            if ch == "#":
                x = c * cell_w
                # Draw CCW rectangle
                pen.moveTo(pt(x, y))
                pen.lineTo(pt(x, y + cell_h))
                pen.lineTo(pt(x + cell_w, y + cell_h))
                pen.lineTo(pt(x + cell_w, y))
                pen.closePath()


def draw_contours_to_pen(pen, contours):
    """Draws recorded vector contour commands (M, L, Q_CTRL/Q_ON, Z) to TTGlyphPen."""
    for contour in contours:
        if not contour:
            continue
        quad_ctrls = []
        for cmd in contour:
            t = cmd.get("type")
            if t == "M":
                pen.moveTo(pt(cmd["x"], cmd["y"]))
            elif t == "L":
                pen.lineTo(pt(cmd["x"], cmd["y"]))
            elif t == "Q_CTRL":
                quad_ctrls.append(pt(cmd["x"], cmd["y"]))
            elif t == "Q_ON":
                quad_ctrls.append(pt(cmd["x"], cmd["y"]))
                pen.qCurveTo(*quad_ctrls)
                quad_ctrls = []
            elif t == "Z":
                pen.closePath()


def draw_strokes_to_pen(pen, strokes):
    """Draws freehand strokes as expanded solid outline contours."""
    for stroke in strokes:
        points = stroke.get("points", [])
        width = stroke.get("width", 60)
        if len(points) >= 2:
            contour_pts = expand_polyline_to_contour(points, width)
            if len(contour_pts) >= 3:
                pen.moveTo(pt(contour_pts[0][0], contour_pts[0][1]))
                for p in contour_pts[1:]:
                    pen.lineTo(pt(p[0], p[1]))
                pen.closePath()


def compile_glyph(glyph_data, cell_w=25, cell_h=25):
    """Compiles single glyph JSON into a TrueType glyph object and bounding box."""
    mode = glyph_data.get("mode", "grid")
    contours = glyph_data.get("contours", [])
    strokes = glyph_data.get("strokes", [])
    grid = glyph_data.get("grid", [])

    pen = TTGlyphPen({})
    has_content = False

    # Prefer grid when in grid mode or when grid has pixels
    if mode == "grid" and grid and any("#" in row for row in grid):
        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 1
        cw = 1000 // cols if cols > 0 else cell_w
        ch = 1000 // rows if rows > 0 else cell_h
        draw_grid_to_pen(pen, grid, cw, ch)
        has_content = True
    elif mode == "vector" and (strokes or contours):
        if strokes:
            draw_strokes_to_pen(pen, strokes)
            has_content = True
        if contours:
            draw_contours_to_pen(pen, contours)
            has_content = True
    elif grid and any("#" in row for row in grid):
        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 1
        cw = 1000 // cols if cols > 0 else cell_w
        ch = 1000 // rows if rows > 0 else cell_h
        draw_grid_to_pen(pen, grid, cw, ch)
        has_content = True
    elif contours:
        draw_contours_to_pen(pen, contours)
        has_content = True

    if not has_content:
        # Empty glyph (space, etc.)
        return TTGlyphPen({}).glyph()

    return pen.glyph()


def load_glyph_files(glyphs_dir):
    """Reads all glyph JSON files from glyphs_dir."""
    glyphs_data = {}
    for path in sorted(glyphs_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        with open(path, "r", encoding="utf-8") as f:
            info = json.load(f)
        name = info.get("name", path.stem)
        glyphs_data[name] = info
    return glyphs_data


def build_font(glyphs_dir=None, output_path=None):
    project_root = Path(__file__).resolve().parent.parent
    if glyphs_dir is None:
        glyphs_dir = project_root / "glyphs"
    if output_path is None:
        output_path = project_root / "output" / "OpenPixelFont-Regular.ttf"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata_path = glyphs_dir / "_metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {}

    family_name = meta.get("familyName", "OpenPixelFont")
    style_name = meta.get("styleName", "Regular")
    upm = meta.get("unitsPerEm", 1000)
    ascender = meta.get("ascender", 800)
    descender = meta.get("descender", -200)
    cap_height = meta.get("capHeight", 700)
    x_height = meta.get("xHeight", 500)
    default_advance = meta.get("defaultAdvance", 700)
    cell_w = meta.get("cellWidth", 31)
    cell_h = meta.get("cellHeight", 31)

    glyphs_data = load_glyph_files(glyphs_dir)

    # Base glyph order starts with .notdef, space, uni00A0
    glyph_order = [".notdef", "space", "uni00A0"]
    glyphs = {}
    cmap = {0x0020: "space", 0x00A0: "uni00A0"}
    h_metrics = {
        ".notdef": (500, 0),
        "space": (260, 0),
        "uni00A0": (260, 0),
    }

    # .notdef fallback
    if ".notdef" in glyphs_data:
        glyphs[".notdef"] = compile_glyph(glyphs_data[".notdef"], cell_w, cell_h)
    else:
        pen = TTGlyphPen({})
        pen.moveTo((40, 0))
        pen.lineTo((40, 700))
        pen.lineTo((460, 700))
        pen.lineTo((460, 0))
        pen.closePath()
        glyphs[".notdef"] = pen.glyph()

    # Process all other glyphs
    for name, info in glyphs_data.items():
        if name in [".notdef", "space", "uni00A0"]:
            continue
        g = compile_glyph(info, cell_w, cell_h)
        glyphs[name] = g
        glyph_order.append(name)
        adv = info.get("advance", default_advance)
        h_metrics[name] = (adv, 0)
        u = info.get("unicode")
        if u is not None and isinstance(u, int):
            cmap[u] = name

    # Space glyphs
    if "space" in glyphs_data:
        glyphs["space"] = compile_glyph(glyphs_data["space"], cell_w, cell_h)
        h_metrics["space"] = (glyphs_data["space"].get("advance", 260), 0)
    else:
        glyphs["space"] = TTGlyphPen({}).glyph()

    if "uni00A0" in glyphs_data:
        glyphs["uni00A0"] = compile_glyph(glyphs_data["uni00A0"], cell_w, cell_h)
        h_metrics["uni00A0"] = (glyphs_data["uni00A0"].get("advance", 260), 0)
    else:
        glyphs["uni00A0"] = TTGlyphPen({}).glyph()

    fb = FontBuilder(upm, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(h_metrics)
    fb.setupHorizontalHeader(ascent=ascender, descent=descender)
    fb.setupOS2(
        sTypoAscender=ascender,
        sTypoDescender=descender,
        usWinAscent=ascender + 80,
        usWinDescent=abs(descender) + 20,
        sxHeight=x_height,
        sCapHeight=cap_height,
        usWeightClass=400,
        usWidthClass=5,
        achVendID="OPNF",
        fsSelection=0x0040,
    )
    fb.setupNameTable({
        "familyName": family_name,
        "styleName": style_name,
        "fullName": f"{family_name} {style_name}",
        "psName": f"{family_name}-{style_name}",
        "uniqueFontIdentifier": f"{family_name}-{style_name}:2026",
        "version": "Version 1.000",
        "manufacturer": "OpenPixel & Vector Font Project",
        "designer": "Yavuz & Contributors",
        "description": "Custom solid Turkish alphabet and symbol font.",
        "licenseDescription": "SIL Open Font License 1.1",
    })
    fb.setupPost()

    fb.save(str(output_path))
    return str(output_path)


def main():
    out = build_font()
    print(f"Font başarıyla kaydedildi: {out}")


if __name__ == "__main__":
    main()
