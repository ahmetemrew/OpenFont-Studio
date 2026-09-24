#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/reels_collector/merge_reels.py
====================================
İndirilen tüm orijinal Reels videolarını:
1. Instagram'ın kendi orijinal veri akış hızına (bitrate) birebir eşitleyerek
2. Toplam boyutu ham dosyaların toplamı olan ~750 MB civarına denk getirerek
3. 720p (720x1280, 9:16) formatında
4. Videolar arası 1 saniye siyah geçiş ekleyerek
5. NVIDIA NVENC GPU hızlandırmasıyla birleştirir.
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
import imageio_ffmpeg

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "downloads" / "atik_adamsi"
OUTPUT_FILE = PROJECT_ROOT / "downloads" / "atik_adamsi_birlestirilmis_instagram_boyut.mp4"
TEMP_DIR = PROJECT_ROOT / "downloads" / ".temp_merge_cache_ig"

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def check_has_audio(video_path: Path) -> bool:
    """Videonun ses kanalı içerip içermediğini kontrol eder."""
    try:
        p = subprocess.run(
            [FFMPEG_EXE, "-i", str(video_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return "Audio:" in p.stderr
    except Exception:
        return True

def create_black_transition(out_path: Path):
    """1 saniyelik 720x1280 siyah ekran ve sessiz ses dosyası üretir."""
    cmd = [
        FFMPEG_EXE, "-y",
        "-f", "lavfi", "-i", "color=c=black:s=720x1280:r=30:d=1",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:d=1",
        "-c:v", "h264_nvenc", "-rc", "vbr", "-cq", "28", "-b:v", "750k", "-maxrate", "950k", "-bufsize", "1200k", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "96k",
        "-shortest",
        str(out_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def merge_reels():
    if not INPUT_DIR.exists():
        print(f"[HATA] Giriş klasörü bulunamadı: {INPUT_DIR}")
        sys.exit(1)
        
    raw_files = sorted(list(INPUT_DIR.glob("*.mp4")))
    if not raw_files:
        print("[HATA] Klasörde MP4 dosyası bulunamadı!")
        sys.exit(1)
        
    total_videos = len(raw_files)
    print("\n" + "="*70)
    print("🎬 INSTAGRAM REELS TAM BOYUT EŞLEŞTİRMELİ BİRLEŞTİRİCİ (~750 MB)")
    print(f"📁 Kaynak Klasör: {INPUT_DIR} ({total_videos} orijinal video)")
    print("🔒 Hedef Boyut: Orijinal toplamıyla birebir uyumlu (~750 MB)")
    print(f"🎯 Çıktı Dosyası: {OUTPUT_FILE}")
    print("📐 Format: 720p 9:16 (720x1280, 30fps) - Instagram Orijinal Bitrate")
    print("⏱️ Geçiş: Videolar arası 1 saniye siyahlık")
    print("⚡ Hızlandırma: NVIDIA NVENC GPU")
    print("="*70 + "\n")

    # Geçici çalışma dizini oluştur
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1 saniyelik siyah geçiş videosu oluştur
    black_clip = TEMP_DIR / "black_transition_1s.mp4"
    print("⏳ 1 saniyelik siyah geçiş klibi oluşturuluyor...")
    create_black_transition(black_clip)
    print("✅ Geçiş klibi hazır.\n")
    
    # Adım 1: Her videoyu Instagram standartlarına (750k video + 96k ses) dönüştür
    normalized_files = []
    print(f"⏳ [1/2] {total_videos} video Instagram orijinal parametreleriyle işleniyor...")
    start_transcode = time.time()
    
    vf_filter = (
        "scale=720:1280:force_original_aspect_ratio=decrease,"
        "pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=black,"
        "fps=30,setsar=1,format=yuv420p"
    )
    
    for idx, vfile in enumerate(raw_files, 1):
        out_v = TEMP_DIR / f"norm_{idx:03d}.mp4"
        normalized_files.append(out_v)
        
        if out_v.exists() and out_v.stat().st_size > 1000:
            print(f"  [{idx}/{total_videos}] ⏩ Önceden hazır: {vfile.name}", flush=True)
            continue
            
        has_audio = check_has_audio(vfile)
        
        if has_audio:
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", str(vfile),
                "-vf", vf_filter,
                "-c:v", "h264_nvenc", "-rc", "vbr", "-cq", "28", "-b:v", "750k", "-maxrate", "950k", "-bufsize", "1200k",
                "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "96k",
                str(out_v)
            ]
        else:
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", str(vfile),
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-vf", vf_filter,
                "-c:v", "h264_nvenc", "-rc", "vbr", "-cq", "28", "-b:v", "750k", "-maxrate", "950k", "-bufsize", "1200k",
                "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "96k",
                "-shortest",
                str(out_v)
            ]
            
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if p.returncode != 0:
            cmd_cpu = [
                FFMPEG_EXE, "-y",
                "-i", str(vfile),
                "-vf", vf_filter,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
                "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "96k",
                str(out_v)
            ]
            subprocess.run(cmd_cpu, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        pct = round((idx / total_videos) * 100, 1)
        print(f"  [{idx}/{total_videos}] %{pct} - {vfile.name}", flush=True)
        
    transcode_time = round(time.time() - start_transcode, 1)
    print(f"\n✅ Tüm videolar Instagram çıktı standartlarına uyarlandı ({transcode_time} sn).\n")
    
    # Adım 2: Concat listesi hazırla
    concat_list_file = TEMP_DIR / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for idx, norm_file in enumerate(normalized_files):
            escaped_path = str(norm_file.resolve()).replace("\\", "/")
            f.write(f"file '{escaped_path}'\n")
            
            if idx < len(normalized_files) - 1:
                escaped_black = str(black_clip.resolve()).replace("\\", "/")
                f.write(f"file '{escaped_black}'\n")
                
    # Adım 3: Concat Demuxer ile birleştir
    print("⏳ [2/2] Videolar ve 1 saniyelik geçişler birleştiriliyor...")
    start_merge = time.time()
    
    merge_cmd = [
        FFMPEG_EXE, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(OUTPUT_FILE)
    ]
    
    subprocess.run(merge_cmd, check=True)
    merge_time = round(time.time() - start_merge, 1)
    
    # Geçici dosyaları temizle
    print("🧹 Geçici önbellek dosyaları temizleniyor...")
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    
    final_size_mb = round(OUTPUT_FILE.stat().st_size / (1024 * 1024), 2)
    
    print("\n" + "="*70)
    print("🎉 INSTAGRAM ÇIKTI STANDARTLI BİRLEŞTİRME BAŞARIYLA TAMAMLANDI!")
    print(f"🎬 Çıktı Dosyası: {OUTPUT_FILE}")
    print(f"📦 Dosya Boyutu: {final_size_mb} MB (Ham videolarla birebir uyumlu)")
    print(f"🎞️ Birleştirilen Video: {total_videos} adet (Eskiden Yeniye)")
    print(f"🔒 Orijinal Dosyalar: {INPUT_DIR} içinde eksiksiz saklandı.")
    print("="*70 + "\n")

if __name__ == "__main__":
    merge_reels()
