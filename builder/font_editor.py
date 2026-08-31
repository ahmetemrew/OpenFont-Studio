#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
builder/font_editor.py
======================

Backend server for OpenFont Studio (OpenPixel & Vector Font Studio).
Provides REST APIs for glyph storage, vector & grid editing, and instant TTF compilation.
"""

import json
import sys
import tempfile
from pathlib import Path
from flask import Flask, jsonify, request, send_file, Response, make_response

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GLYPHS_DIR = PROJECT_ROOT / "glyphs"
OUTPUT_DIR = PROJECT_ROOT / "output"
WEB_DIR = PROJECT_ROOT / "web"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_font as bf

app = Flask(__name__, static_folder=str(WEB_DIR))


def load_metadata():
    meta_path = GLYPHS_DIR / "_metadata.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "familyName": "OpenPixelFont",
        "styleName": "Regular",
        "unitsPerEm": 1000,
        "ascender": 800,
        "descender": -200,
        "capHeight": 700,
        "xHeight": 500,
        "cellWidth": 31,
        "cellHeight": 31,
        "gridCols": 32,
        "gridRows": 32,
        "defaultAdvance": 700,
    }


def save_metadata(meta):
    meta_path = GLYPHS_DIR / "_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    return app.send_static_file("editor.html")


@app.route("/output/<path:filename>")
def serve_output(filename):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return Response("Dosya bulunamadı", status=404)
    resp = send_file(file_path, mimetype="font/ttf")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.route("/web/<path:filename>")
def serve_web(filename):
    return send_file(WEB_DIR / filename)


@app.route("/api/metadata", methods=["GET", "POST"])
def api_metadata():
    if request.method == "POST":
        meta = request.get_json()
        save_metadata(meta)
        return jsonify({"status": "ok", "metadata": meta})
    return jsonify(load_metadata())


@app.route("/api/clear_all", methods=["POST"])
def api_clear_all():
    """Wipes all drawing contours, strokes, and pixel grids from all glyphs."""
    glyphs = bf.load_glyph_files(GLYPHS_DIR)
    for name, info in glyphs.items():
        info["contours"] = []
        info["strokes"] = []
        rows = info.get("gridRows", 32)
        cols = info.get("gridCols", 32)
        info["grid"] = [" " * cols for _ in range(rows)]
        info["mode"] = "vector"
        
        u = info.get("unicode")
        filename = f"U{u:04X}.json" if u is not None and isinstance(u, int) and u >= 0 else f"{name}.json"
        with open(GLYPHS_DIR / filename, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "cleared", "count": len(glyphs), "glyphs": glyphs})


@app.route("/api/reset_defaults", methods=["POST"])
def api_reset_defaults():
    """Forces regeneration of pristine solid glyph files on disk."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    import rebuild_all_solid_glyphs as rbg
    rbg.main()
    bf.build_font()
    glyphs = bf.load_glyph_files(GLYPHS_DIR)
    return jsonify({"status": "reset", "count": len(glyphs), "glyphs": glyphs})


@app.route("/api/glyphs", methods=["GET", "POST"])
def api_glyphs():
    if request.method == "POST":
        data = request.get_json()
        GLYPHS_DIR.mkdir(parents=True, exist_ok=True)
        count = 0
        for name, info in data.items():
            u = info.get("unicode")
            if u is not None and isinstance(u, int) and u >= 0:
                filename = f"U{u:04X}.json"
            else:
                filename = f"{name}.json"
            with open(GLYPHS_DIR / filename, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            count += 1
        return jsonify({"status": "saved", "count": count})

    glyphs = bf.load_glyph_files(GLYPHS_DIR)
    return jsonify(glyphs)


@app.route("/api/build", methods=["POST"])
def api_build():
    """Compiles provided glyphs and returns downloadable .ttf directly."""
    data = request.get_json()
    if data:
        for name, info in data.items():
            u = info.get("unicode")
            if u is not None and isinstance(u, int) and u >= 0:
                filename = f"U{u:04X}.json"
            else:
                filename = f"{name}.json"
            with open(GLYPHS_DIR / filename, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)

    meta = load_metadata()
    family_name = meta.get("familyName", "OpenPixelFont")
    style_name = meta.get("styleName", "Regular")
    out_filename = f"{family_name}-{style_name}.ttf"

    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmp:
        tmp_path = tmp.name

    bf.build_font(glyphs_dir=GLYPHS_DIR, output_path=tmp_path)
    
    permanent_out = OUTPUT_DIR / out_filename
    try:
        bf.build_font(glyphs_dir=GLYPHS_DIR, output_path=permanent_out)
    except Exception as e:
        print(f"Warning: could not write permanent font file: {e}")

    resp = send_file(
        tmp_path,
        as_attachment=True,
        download_name=out_filename,
        mimetype="font/ttf",
    )
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


if __name__ == "__main__":
    print("=======================================================")
    print(" OpenPixel & Vector Font Studio")
    print(" URL: http://localhost:5000")
    print("=======================================================")
    app.run(host="localhost", port=5000, debug=False)
