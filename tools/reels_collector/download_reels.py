#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/reels_collector/download_reels.py
=======================================
Toplanan Instagram Reels linklerini yt-dlp ile tamamen ANONİM olarak
(hiçbir oturum/çerez kullanmadan) ve INSTAGRAMA YÜKLENME TARİHİNE GÖRE
(Yıl-Ay-Gün_Saat-Dakika-Saniye_ID.mp4) sırayla indirir.
"""

import sys
import subprocess
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LINKS_FILE = PROJECT_ROOT / "tools" / "reels_collector" / "output" / "atik_adamsi_reels.txt"
DEFAULT_DOWNLOAD_DIR = PROJECT_ROOT / "downloads" / "atik_adamsi"

def download_reels(links_file: Path = DEFAULT_LINKS_FILE, output_dir: Path = DEFAULT_DOWNLOAD_DIR):
    if not links_file.exists():
        print(f"[HATA] Link dosyası bulunamadı: {links_file}")
        sys.exit(1)
        
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_file = output_dir / ".download_archive.txt"
    
    with open(links_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and line.strip().startswith("http")]
        
    total_count = len(urls)
    print("\n" + "="*70)
    print("🎬 INSTAGRAM REELS TARİHE GÖRE ANONİM İNDİRİCİ (yt-dlp)")
    print(f"📁 İndirilecek Konum: {output_dir}")
    print(f"📊 Toplam Video Sayısı: {total_count}")
    print("📅 İsimlendirme Formatı: YIL-AY-GÜN_SAAT-DAKİKA-SANİYE_ID.mp4")
    print("🔒 Mod: %100 Anonim (Çerez/hesap bilgisi yok)")
    print("="*70 + "\n")
    
    # yt-dlp komutu:
    # -o: Dosya adının başına Instagram yüklenme tarihi ve saatini koyar (kronolojik sıralama sağlar)
    # --mtime: Dosyanın Windows üzerindeki değiştirilme tarihini de Instagram yüklenme tarihi yapar
    # --no-cookies: Anonim indirme
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-cookies",
        "--batch-file", str(links_file),
        "-P", str(output_dir),
        "-o", "%(upload_date>%Y-%m-%d)s_%(timestamp>%H-%M-%S)s_%(id)s.%(ext)s",
        "--mtime",
        "--download-archive", str(archive_file),
        "--ignore-errors",
        "--sleep-interval", "1",
        "--max-sleep-interval", "2",
        "--no-playlist"
    ]
    
    start_time = time.time()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )
        
        downloaded = 0
        for line in proc.stdout:
            line_str = line.strip()
            if "[download] Destination:" in line_str:
                fname = line_str.split("Destination:")[-1].strip()
                downloaded += 1
                print(f"[{downloaded}/{total_count}] 📥 İndiriliyor: {Path(fname).name}", flush=True)
            elif "has already been recorded in the archive" in line_str:
                print(f"⏩ Zaten indirilmiş, atlanıyor...", flush=True)
            elif "100% of" in line_str and "in" in line_str:
                print(f"   ✅ Tamamlandı!", flush=True)
            elif "ERROR:" in line_str:
                print(f"   ⚠️ {line_str}", flush=True)
                
        proc.wait()
    except KeyboardInterrupt:
        print("\n[BİLGİ] Kullanıcı tarafından durduruldu.")
        
    elapsed = round(time.time() - start_time, 1)
    
    files = list(output_dir.glob("*.mp4"))
    total_mb = round(sum(f.stat().st_size for f in files) / (1024 * 1024), 2)
    
    print("\n" + "="*70)
    print(f"🎉 İŞLEM BİTTİ!")
    print(f"📁 Klasör: {output_dir}")
    print(f"🎬 Toplam MP4 Dosyası: {len(files)} adet")
    print(f"💾 Toplam Boyut: {total_mb} MB")
    print(f"⏱️ Geçen Süre: {elapsed} saniye")
    print("="*70 + "\n")

if __name__ == "__main__":
    download_reels()
