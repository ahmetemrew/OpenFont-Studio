#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_full_glyph_set.py
==================================

Generates complete, bold, solid-filled pixel grids and vector contours
for the entire Turkish character set, digits, punctuation, and currency symbols.
"""

import json
import math
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
GLYPHS_DIR = ROOT / "glyphs"
GLYPHS_DIR.mkdir(parents=True, exist_ok=True)

GRID_SIZE = 32
UPM = 1000
CELL_SIZE = UPM // GRID_SIZE  # 31.25 -> 31

# All characters to support
CHARS_MAP = [
    # Turkish Uppercase
    ("A", "A", 0x0041, "turkish_upper", 700),
    ("B", "B", 0x0042, "turkish_upper", 700),
    ("C", "C", 0x0043, "turkish_upper", 700),
    ("Ccedilla", "Ç", 0x00C7, "turkish_upper", 700),
    ("D", "D", 0x0044, "turkish_upper", 720),
    ("E", "E", 0x0045, "turkish_upper", 660),
    ("F", "F", 0x0046, "turkish_upper", 640),
    ("G", "G", 0x0047, "turkish_upper", 720),
    ("Gbreve", "Ğ", 0x011E, "turkish_upper", 720),
    ("H", "H", 0x0048, "turkish_upper", 720),
    ("I", "I", 0x0049, "turkish_upper", 300),
    ("Idotaccent", "İ", 0x0130, "turkish_upper", 300),
    ("J", "J", 0x004A, "turkish_upper", 550),
    ("K", "K", 0x004B, "turkish_upper", 700),
    ("L", "L", 0x004C, "turkish_upper", 600),
    ("M", "M", 0x004D, "turkish_upper", 850),
    ("N", "N", 0x004E, "turkish_upper", 720),
    ("O", "O", 0x004F, "turkish_upper", 740),
    ("Odieresis", "Ö", 0x00D6, "turkish_upper", 740),
    ("P", "P", 0x0050, "turkish_upper", 680),
    ("Q", "Q", 0x0051, "turkish_upper", 740),
    ("R", "R", 0x0052, "turkish_upper", 700),
    ("S", "S", 0x0053, "turkish_upper", 660),
    ("Scedilla", "Ş", 0x015E, "turkish_upper", 660),
    ("T", "T", 0x0054, "turkish_upper", 660),
    ("U", "U", 0x0055, "turkish_upper", 720),
    ("Udieresis", "Ü", 0x00DC, "turkish_upper", 720),
    ("V", "V", 0x0056, "turkish_upper", 680),
    ("W", "W", 0x0057, "turkish_upper", 950),
    ("X", "X", 0x0058, "turkish_upper", 680),
    ("Y", "Y", 0x0059, "turkish_upper", 680),
    ("Z", "Z", 0x005A, "turkish_upper", 660),

    # Turkish Lowercase
    ("a", "a", 0x0061, "turkish_lower", 600),
    ("b", "b", 0x0062, "turkish_lower", 620),
    ("c", "c", 0x0063, "turkish_lower", 580),
    ("ccedilla", "ç", 0x00E7, "turkish_lower", 580),
    ("d", "d", 0x0064, "turkish_lower", 620),
    ("e", "e", 0x0065, "turkish_lower", 600),
    ("f", "f", 0x0066, "turkish_lower", 380),
    ("g", "g", 0x0067, "turkish_lower", 620),
    ("gbreve", "ğ", 0x011F, "turkish_lower", 620),
    ("h", "h", 0x0068, "turkish_lower", 600),
    ("dotlessi", "ı", 0x0131, "turkish_lower", 280),
    ("i", "i", 0x0069, "turkish_lower", 280),
    ("j", "j", 0x006A, "turkish_lower", 300),
    ("k", "k", 0x006B, "turkish_lower", 580),
    ("l", "l", 0x006C, "turkish_lower", 280),
    ("m", "m", 0x006D, "turkish_lower", 880),
    ("n", "n", 0x006E, "turkish_lower", 600),
    ("o", "o", 0x006F, "turkish_lower", 620),
    ("odieresis", "ö", 0x00F6, "turkish_lower", 620),
    ("p", "p", 0x0070, "turkish_lower", 620),
    ("q", "q", 0x0071, "turkish_lower", 620),
    ("r", "r", 0x0072, "turkish_lower", 420),
    ("s", "s", 0x0073, "turkish_lower", 560),
    ("scedilla", "ş", 0x015F, "turkish_lower", 560),
    ("t", "t", 0x0074, "turkish_lower", 400),
    ("u", "u", 0x0075, "turkish_lower", 600),
    ("udieresis", "ü", 0x00FC, "turkish_lower", 600),
    ("v", "v", 0x0076, "turkish_lower", 560),
    ("w", "w", 0x0077, "turkish_lower", 820),
    ("x", "x", 0x0078, "turkish_lower", 560),
    ("y", "y", 0x0079, "turkish_lower", 560),
    ("z", "z", 0x007A, "turkish_lower", 560),

    # Digits
    ("zero", "0", 0x0030, "digit", 600),
    ("one", "1", 0x0031, "digit", 420),
    ("two", "2", 0x0032, "digit", 600),
    ("three", "3", 0x0033, "digit", 600),
    ("four", "4", 0x0034, "digit", 600),
    ("five", "5", 0x0035, "digit", 600),
    ("six", "6", 0x0036, "digit", 600),
    ("seven", "7", 0x0037, "digit", 600),
    ("eight", "8", 0x0038, "digit", 600),
    ("nine", "9", 0x0039, "digit", 600),

    # Punctuation & Symbols
    ("space", " ", 0x0020, "whitespace", 260),
    ("uni00A0", " ", 0x00A0, "whitespace", 260),
    ("exclam", "!", 0x0021, "symbol", 320),
    ("quotedbl", '"', 0x0022, "symbol", 420),
    ("numbersign", "#", 0x0023, "symbol", 640),
    ("dollar", "$", 0x0024, "symbol", 600),
    ("percent", "%", 0x0025, "symbol", 750),
    ("ampersand", "&", 0x0026, "symbol", 700),
    ("quotesingle", "'", 0x0027, "symbol", 260),
    ("parenleft", "(", 0x0028, "symbol", 360),
    ("parenright", ")", 0x0029, "symbol", 360),
    ("asterisk", "*", 0x002A, "symbol", 460),
    ("plus", "+", 0x002B, "symbol", 600),
    ("comma", ",", 0x002C, "symbol", 300),
    ("hyphen", "-", 0x002D, "symbol", 420),
    ("period", ".", 0x002E, "symbol", 300),
    ("slash", "/", 0x002F, "symbol", 460),
    ("colon", ":", 0x003A, "symbol", 300),
    ("semicolon", ";", 0x003B, "symbol", 300),
    ("less", "<", 0x003C, "symbol", 600),
    ("equal", "=", 0x003D, "symbol", 600),
    ("greater", ">", 0x003E, "symbol", 600),
    ("question", "?", 0x003F, "symbol", 540),
    ("at", "@", 0x0040, "symbol", 780),
    ("bracketleft", "[", 0x005B, "symbol", 360),
    ("backslash", "\\", 0x005C, "symbol", 460),
    ("bracketright", "]", 0x005D, "symbol", 360),
    ("asciicircum", "^", 0x005E, "symbol", 500),
    ("underscore", "_", 0x005F, "symbol", 560),
    ("grave", "`", 0x0060, "symbol", 320),
    ("braceleft", "{", 0x007B, "symbol", 400),
    ("bar", "|", 0x007C, "symbol", 280),
    ("braceright", "}", 0x007D, "symbol", 400),
    ("asciitilde", "~", 0x007E, "symbol", 560),

    # Currency & Special
    ("turkishlira", "₺", 0x20BA, "currency", 700),
    ("euro", "€", 0x20AC, "currency", 700),
    ("sterling", "£", 0x00A3, "currency", 640),
    ("degree", "°", 0x00B0, "symbol", 400),
]


def grid_to_vector_contours(grid, cell_w=31, cell_h=31):
    """Converts solid pixel grid blocks into CCW rectangle vector contours."""
    contours = []
    rows = len(grid)
    for r, row in enumerate(grid):
        y = (rows - 1 - r) * cell_h
        for c, ch in enumerate(row):
            if ch == "#":
                x = c * cell_w
                contours.append([
                    {"type": "M", "x": x, "y": y},
                    {"type": "L", "x": x, "y": y + cell_h},
                    {"type": "L", "x": x + cell_w, "y": y + cell_h},
                    {"type": "L", "x": x + cell_w, "y": y},
                    {"type": "Z"}
                ])
    return contours


def main():
    # Load Segoe UI Bold or Arial Bold as high-quality solid template generator
    font_path = "C:/Windows/Fonts/segoeuib.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/arialbd.ttf"
    
    base_font = ImageFont.truetype(font_path, 24)

    # Clean old files
    for p in GLYPHS_DIR.glob("*.json"):
        if p.name != "_metadata.json":
            p.unlink()

    count = 0

    for name, char, u, cat, adv in CHARS_MAP:
        grid = [[" " for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        if u and u > 32:
            img = Image.new("1", (GRID_SIZE, GRID_SIZE), 0)
            draw = ImageDraw.Draw(img)

            bbox = draw.textbbox((0, 0), char, font=base_font)
            bw = bbox[2] - bbox[0]
            bh = bbox[3] - bbox[1]

            # Center horizontally and position baseline around row 25
            ox = max(1, (GRID_SIZE - bw) // 2)
            oy = max(2, (GRID_SIZE - bh) // 2 - 2)

            draw.text((ox, oy), char, font=base_font, fill=1)

            for y in range(GRID_SIZE):
                for x in range(GRID_SIZE):
                    if img.getpixel((x, y)):
                        grid[y][x] = "#"

        grid_strings = ["".join(row) for row in grid]
        contours = grid_to_vector_contours(grid_strings, CELL_SIZE, CELL_SIZE)

        glyph_data = {
            "name": name,
            "char": char,
            "unicode": u,
            "advance": adv,
            "category": cat,
            "mode": "grid",
            "gridCols": GRID_SIZE,
            "gridRows": GRID_SIZE,
            "contours": contours,
            "strokes": [],
            "grid": grid_strings,
        }

        filename = f"U{u:04X}.json" if u is not None else f"{name}.json"
        with open(GLYPHS_DIR / filename, "w", encoding="utf-8") as f:
            json.dump(glyph_data, f, ensure_ascii=False, indent=2)
        count += 1

    # Notdef
    notdef_grid = [
        "################################",
        "################################",
        "##                            ##",
        "##  ########################  ##",
        "##  ########################  ##",
        "##  ##                    ##  ##",
        "##  ##                    ##  ##",
        "##  ##            ####    ##  ##",
        "##  ##          ######    ##  ##",
        "##  ##        ########    ##  ##",
        "##  ##      ##    ####    ##  ##",
        "##  ##            ####    ##  ##",
        "##  ##            ####    ##  ##",
        "##  ##            ####    ##  ##",
        "##  ##            ####    ##  ##",
        "##  ##            ####    ##  ##",
        "##  ##                  ##    ##",
        "##  ##                ####    ##",
        "##  ##              ######    ##",
        "##  ##            ########    ##",
        "##  ##                    ##  ##",
        "##  ##                    ##  ##",
        "##  ##                    ##  ##",
        "##  ##  ########################",
        "##  ##  ########################",
        "##  ##                    ##  ##",
        "##  ##                    ##  ##",
        "##  ########################  ##",
        "##  ########################  ##",
        "##                            ##",
        "################################",
        "################################"
    ]
    notdef_data = {
        "name": ".notdef",
        "char": "?",
        "unicode": None,
        "advance": 500,
        "category": "symbol",
        "mode": "grid",
        "gridCols": GRID_SIZE,
        "gridRows": GRID_SIZE,
        "contours": grid_to_vector_contours(notdef_grid, CELL_SIZE, CELL_SIZE),
        "strokes": [],
        "grid": notdef_grid,
    }
    with open(GLYPHS_DIR / ".notdef.json", "w", encoding="utf-8") as f:
        json.dump(notdef_data, f, ensure_ascii=False, indent=2)

    # Metadata
    meta = {
        "familyName": "OpenPixelFont",
        "styleName": "Regular",
        "unitsPerEm": 1000,
        "ascender": 800,
        "descender": -200,
        "capHeight": 700,
        "xHeight": 500,
        "cellWidth": CELL_SIZE,
        "cellHeight": CELL_SIZE,
        "gridCols": GRID_SIZE,
        "gridRows": GRID_SIZE,
        "defaultAdvance": 700,
        "glyphCount": count + 1,
    }
    with open(GLYPHS_DIR / "_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Başarıyla {count + 1} adet dolu (solid) karakter üretildi!")


if __name__ == "__main__":
    main()
