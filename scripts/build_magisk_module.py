#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_magisk_module.py
Root'lu telefonlar için tek tıkla kurulabilir Magisk / KernelSU / APatch font modülü (.zip) üreticisi.
"""

import os
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_SOURCE = Path(r"C:\Users\yavuz\Downloads\Yavuz-El-Cizimi-Font (2).ttf")
ZIP_OUTPUT = OUTPUT_DIR / "Yavuz-El-Cizimi-Font-Magisk.zip"

MODULE_PROP = """id=yavuz_font
name=Yavuz El Çizimi Font
version=v2.0
versionCode=2
author=Yavuz
description=Özel el çizimi Türkçe TrueType sistem fontu. Android, Samsung OneUI, MIUI ve AOSP ile tam uyumlu.
"""

UPDATE_BINARY = """#!/sbin/sh

#################
# Initialization
#################

umask 022

ui_print() { echo "$1"; }

require_new_magisk() {
  ui_print "*******************************"
  ui_print " Please install Magisk v20.4+! "
  ui_print "*******************************"
  exit 1
}

#########################
# Load util_functions.sh
#########################

OUTFD=$2
ZIPFILE=$3

mount /data 2>/dev/null

[ -f /data/adb/magisk/util_functions.sh ] || require_new_magisk
. /data/adb/magisk/util_functions.sh
[ $MAGISK_VER_CODE -lt 20400 ] && require_new_magisk

install_module
exit 0
"""

UPDATER_SCRIPT = "#MAGISK\n"

CUSTOMIZE_SH = """ui_print "****************************************"
ui_print "    Yavuz El Cizimi Font Modulu (v2)    "
ui_print "****************************************"
ui_print "- Sistem fontlari yukleniyor (AOSP / Samsung / Xiaomi)..."
set_perm_recursive $MODPATH 0 0 0755 0644
ui_print "- Kurulum basarili! Lutfen telefonu yeniden baslatin."
"""

TARGET_FONT_NAMES = [
    # AOSP / Stock Android / Pixel / LineageOS / Custom ROMs
    "Roboto-Regular.ttf",
    "Roboto-Bold.ttf",
    "Roboto-Italic.ttf",
    "Roboto-BoldItalic.ttf",
    "Roboto-Medium.ttf",
    "Roboto-MediumItalic.ttf",
    "Roboto-Light.ttf",
    "Roboto-LightItalic.ttf",
    "Roboto-Thin.ttf",
    "Roboto-ThinItalic.ttf",
    "Roboto-Black.ttf",
    "Roboto-BlackItalic.ttf",
    "RobotoStatic-Regular.ttf",
    "DroidSans.ttf",
    "DroidSans-Bold.ttf",
    # Samsung One UI
    "SECRobotoLight-Regular.ttf",
    "SECRobotoLight-Bold.ttf",
    "SamsungSans-Regular.ttf",
    "SamsungOne-400.ttf",
    "SamsungOne-700.ttf",
    # Xiaomi / MIUI / HyperOS
    "MiSans-Normal.ttf",
    "MiSans-Regular.ttf",
    "MiSans-Medium.ttf",
    "MiSans-Bold.ttf",
    "MiLanProVF.ttf",
]

def build_zip():
    font_bytes = FONT_SOURCE.read_bytes()
    print(f"Font dosyası okundu: {FONT_SOURCE} ({len(font_bytes)} byte)")

    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        # module.prop
        zf.writestr("module.prop", MODULE_PROP.encode("utf-8"))
        
        # META-INF
        zf.writestr("META-INF/com/google/android/updater-script", UPDATER_SCRIPT.encode("utf-8"))
        zf.writestr("META-INF/com/google/android/update-binary", UPDATE_BINARY.replace("\r\n", "\n").encode("utf-8"))
        
        # customize.sh
        zf.writestr("customize.sh", CUSTOMIZE_SH.replace("\r\n", "\n").encode("utf-8"))
        
        # system/fonts/
        for fname in TARGET_FONT_NAMES:
            zf.writestr(f"system/fonts/{fname}", font_bytes)
            print(f"  + system/fonts/{fname}")

    print(f"\n[OK] Magisk Modülü başarıyla üretildi: {ZIP_OUTPUT}")
    print(f"     Boyut: {os.path.getsize(ZIP_OUTPUT)} byte")

if __name__ == "__main__":
    build_zip()
