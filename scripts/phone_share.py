#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/phone_share.py
Root'lu cihazlar için Magisk Modülü ve TTF paylaşım/kurulum sunucusu.
"""

import sys
import socket
import subprocess
import threading
import time
from pathlib import Path
from flask import Flask, send_file, render_template_string
import qrcode

sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATH = Path(r"C:\Users\yavuz\Downloads\Yavuz-El-Cizimi-Font (2).ttf")
MAGISK_ZIP_PATH = OUTPUT_DIR / "Yavuz-El-Cizimi-Font-Magisk.zip"
QR_PATH = OUTPUT_DIR / "phone_download_qr.png"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

LOCAL_IP = get_local_ip()
PORT = 8088
PAGE_URL = f"http://{LOCAL_IP}:{PORT}/"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yavuz El Çizimi Font - Root & Magisk Kurulumu</title>
    <style>
        :root {
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --success: #10b981;
            --success-hover: #059669;
            --bg: #0b0f19;
            --card: #151d30;
            --text: #f1f5f9;
            --muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 20px 16px; line-height: 1.5; }
        .container { max-width: 520px; margin: 0 auto; }
        .card { background: var(--card); border-radius: 18px; padding: 24px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.08); }
        h1 { font-size: 1.45rem; font-weight: 700; margin-bottom: 8px; color: #fff; }
        p { color: var(--muted); font-size: 0.95rem; margin-bottom: 16px; }
        .btn { display: block; width: 100%; text-align: center; color: #fff; text-decoration: none; padding: 14px 20px; border-radius: 12px; font-weight: 600; font-size: 1.05rem; transition: 0.2s; margin-bottom: 12px; }
        .btn-magisk { background: var(--success); box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4); }
        .btn-magisk:active { background: var(--success-hover); transform: scale(0.98); }
        .btn-ttf { background: #334155; border: 1px solid #475569; }
        .badge { display: inline-block; background: rgba(16, 185, 129, 0.2); color: var(--success); padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; margin-bottom: 12px; }
        h2 { font-size: 1.15rem; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; color: #e2e8f0; }
        ol { padding-left: 20px; color: #cbd5e1; font-size: 0.92rem; }
        li { margin-bottom: 10px; }
        li strong { color: #fff; }
        .highlight-box { background: rgba(99, 102, 241, 0.1); border-left: 4px solid var(--primary); padding: 12px 16px; border-radius: 8px; margin: 14px 0; font-size: 0.88rem; color: #c7d2fe; }
        .footer { text-align: center; font-size: 0.8rem; color: #64748b; margin-top: 24px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <span class="badge">ROOT ÖZEL - 1 TIKLA SİSTEM FONTU</span>
            <h1>Yavuz El Çizimi Font v2</h1>
            <p>Cihazınız root'lu olduğu için sistem dosyalarına dokunmadan (Systemless) doğrudan Magisk veya KernelSU modülü olarak kurabilirsiniz:</p>
            
            <a href="/download-magisk" class="btn btn-magisk">⚡ Magisk Modülü İndir (.zip)</a>
            <a href="/download-ttf" class="btn btn-ttf">📄 Düz Font Dosyası (.ttf)</a>
        </div>

        <div class="card">
            <h2>🔥 Magisk / KernelSU / APatch Kurulumu</h2>
            <ol>
                <li>Yukarıdaki yeşil <strong>"Magisk Modülü İndir (.zip)"</strong> butonuna dokunun.</li>
                <li>Telefonunuzda <strong>Magisk</strong> (veya KernelSU / APatch) uygulamasını açın.</li>
                <li>Alttaki menüden <strong>Modüller (Modules)</strong> sekmesine geçin.</li>
                <li><strong>"Dahili depolamadan yükle" (Install from storage)</strong> butonuna dokunun.</li>
                <li>İndirilenler klasöründeki <code>Yavuz-El-Cizimi-Font-Magisk.zip</code> dosyasını seçin.</li>
                <li>Kurulum tamamlanınca sağ alttaki <strong>"Yeniden Başlat" (Reboot)</strong> butonuna basın.</li>
            </ol>
            <div class="highlight-box">
                ✅ <strong>Avantajı:</strong> Orijinal sistem dosyalarınız bozulmaz. İstediğiniz an Magisk içinden tek tıkla kapatıp açabilirsiniz!
            </div>
        </div>

        <div class="footer">
            OpenFont Studio &bull; Root Sistem Kurulumu
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/download-magisk")
def download_magisk():
    return send_file(
        MAGISK_ZIP_PATH,
        as_attachment=True,
        download_name="Yavuz-El-Cizimi-Font-Magisk.zip",
        mimetype="application/zip"
    )

@app.route("/download-ttf")
def download_ttf():
    return send_file(
        FONT_PATH,
        as_attachment=True,
        download_name="Yavuz-El-Cizimi-Font-v2.ttf",
        mimetype="font/ttf"
    )

def generate_qr():
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(PAGE_URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(QR_PATH))
    print("\n" + "="*50)
    print("📲 TELEFONDAN MAGİSK MODÜLÜNÜ İNDİRMEK İÇİN:")
    print(f"1) Telefon tarayıcısına yazın: {PAGE_URL}")
    print("   VEYA telefon kamerasını aşağıdaki QR koda tutun:")
    print("="*50 + "\n")
    qr.print_ascii(invert=True)
    print(f"\nQR Kod görseli: {QR_PATH}")
    print("="*50 + "\n")

def adb_watcher():
    pushed = False
    while True:
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            attached = [l for l in lines[1:] if "\tdevice" in l]
            if attached and not pushed:
                dev = attached[0].split("\t")[0]
                print(f"\n[ADB] Android cihaz algılandı: {dev}!")
                print(f"[ADB] Magisk modülü telefona aktarılıyor...")
                
                # Push zip to phone
                subprocess.run([
                    "adb", "-s", dev, "push",
                    str(MAGISK_ZIP_PATH),
                    "/sdcard/Download/Yavuz-El-Cizimi-Font-Magisk.zip"
                ], capture_output=True, text=True)
                
                # Push ttf to phone
                subprocess.run([
                    "adb", "-s", dev, "push",
                    str(FONT_PATH),
                    "/sdcard/Download/Yavuz-El-Cizimi-Font-v2.ttf"
                ], capture_output=True, text=True)

                print("[ADB] BAŞARILI! /sdcard/Download/ klasörüne Magisk Modülü ve TTF aktarıldı.")
                
                # Try auto-install via root
                root_test = subprocess.run(
                    ["adb", "-s", dev, "shell", "su -c 'echo root_ok'"],
                    capture_output=True, text=True, timeout=5
                )
                if "root_ok" in root_test.stdout:
                    print("[ADB] Root (su) yetkisi onaylandı! Magisk modülü doğrudan sisteme kuruluyor...")
                    install_cmd = subprocess.run(
                        ["adb", "-s", dev, "shell", "su -c 'magisk --install-module /sdcard/Download/Yavuz-El-Cizimi-Font-Magisk.zip'"],
                        capture_output=True, text=True, timeout=15
                    )
                    print(install_cmd.stdout)
                    print("[ADB] Kurulum tamamlandı! Cihazı yeniden başlatmak için: adb reboot")
                pushed = True
            elif not attached:
                pushed = False
        except Exception:
            pass
        time.sleep(4)

if __name__ == "__main__":
    generate_qr()
    t = threading.Thread(target=adb_watcher, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=PORT, debug=False)
