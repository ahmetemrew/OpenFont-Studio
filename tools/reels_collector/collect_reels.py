#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/reels_collector/collect_reels.py
======================================
Instagram profilindeki tüm Reels linklerini otomatik toplayıcı.
Kimi WebBridge üzerinden gerçek tarayıcınızın oturumunu kullanarak
engellere ve giriş duvarlarına takılmadan tüm Reels linklerini çeker.
"""

import sys
import json
import time
import re
from pathlib import Path
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding='utf-8')

DAEMON_URL = "http://127.0.0.1:10086/command"
SESSION_NAME = "instagram-reels-collector"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def send_webbridge_cmd(action: str, args: dict = None):
    payload = {
        "action": action,
        "args": args or {},
        "session": SESSION_NAME
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DAEMON_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"[HATA] WebBridge sunucusuna bağlanılamadı: {e}")
        print("Lütfen tarayıcınızın ve Kimi WebBridge eklentisinin açık olduğundan emin olun.")
        sys.exit(1)

def normalize_instagram_url(user_input: str) -> tuple[str, str]:
    """Kullanıcı adını veya linki temizleyip (reels_url, username) döndürür."""
    user_input = user_input.strip().rstrip('/')
    
    # URL mi kullanıcı adı mı kontrol et
    match = re.search(r"instagram\.com/([^/?#]+)", user_input)
    if match:
        username = match.group(1)
    else:
        # Doğrudan kullanıcı adı girilmiş olabilir (@kullanici_adi veya kullanici_adi)
        username = user_input.lstrip('@')
    
    # Temiz reels linki
    reels_url = f"https://www.instagram.com/{username}/reels/"
    return reels_url, username

def collect_reels(target_input: str, max_idle_scrolls: int = 8, scroll_delay_sec: float = 1.2):
    reels_url, username = normalize_instagram_url(target_input)
    
    print("\n" + "="*60)
    print("🎬 INSTAGRAM REELS TOPLAYICI BAŞLATILIYOR")
    print(f"👤 Hedef Kullanıcı: @{username}")
    print(f"🔗 Sayfa URL: {reels_url}")
    print("="*60 + "\n")
    
    print("[1/3] Tarayıcıda Reels sayfası açılıyor...")
    nav_res = send_webbridge_cmd("navigate", {"url": reels_url, "newTab": True})
    if not nav_res.get("ok"):
        print(f"[HATA] Sayfa açılamadı: {nav_res}")
        return []
    
    print("[2/3] Sayfa yükleniyor, 4 saniye bekleniyor...")
    time.sleep(4)
    
    # Sayfadaki Reels linklerini toplayan ve kaydıran JS döngüsü
    print("[3/3] Reels linkleri taranıyor ve aşağı kaydırılıyor...")
    
    # JS tarafında toplayıcı state'ini başlat
    init_js = """
    (() => {
        window.__reels_set = window.__reels_set || new Set();
        const links = document.querySelectorAll('a[href*="/reel/"]');
        links.forEach(a => {
            const clean = a.href.split('?')[0];
            if (clean.includes('/reel/')) window.__reels_set.add(clean);
        });
        return window.__reels_set.size;
    })()
    """
    
    res = send_webbridge_cmd("evaluate", {"code": init_js})
    current_count = res.get("data", {}).get("value", 0)
    print(f"  -> Başlangıçta {current_count} adet Reels linki bulundu.")
    
    idle_count = 0
    last_count = current_count
    scroll_round = 1
    
    while idle_count < max_idle_scrolls:
        # Aşağı kaydır ve yeni gelen linkleri Set'e ekle
        step_js = f"""
        (() => {{
            window.scrollTo(0, document.body.scrollHeight);
            const links = document.querySelectorAll('a[href*="/reel/"]');
            links.forEach(a => {{
                const clean = a.href.split('?')[0];
                if (clean.includes('/reel/')) window.__reels_set.add(clean);
            }});
            return {{
                count: window.__reels_set.size,
                scrollHeight: document.body.scrollHeight
            }};
        }})()
        """
        
        step_res = send_webbridge_cmd("evaluate", {"code": step_js})
        data = step_res.get("data", {}).get("value", {})
        count = data.get("count", current_count)
        
        if count > last_count:
            diff = count - last_count
            print(f"  [Tur {scroll_round}] +{diff} yeni Reels bulundu! (Toplam: {count})")
            last_count = count
            idle_count = 0
        else:
            idle_count += 1
            print(f"  [Tur {scroll_round}] Yeni link bekleniyor... ({idle_count}/{max_idle_scrolls})")
        
        scroll_round += 1
        time.sleep(scroll_delay_sec)
    
    # Tüm linkleri çek
    fetch_all_js = """
    (() => {
        return Array.from(window.__reels_set || []);
    })()
    """
    final_res = send_webbridge_cmd("evaluate", {"code": fetch_all_js})
    reels_list = final_res.get("data", {}).get("value", [])
    
    print("\n" + "="*60)
    print(f"🎉 TARAMA TAMAMLANDI! Toplam {len(reels_list)} adet Reels linki toplandı.")
    print("="*60 + "\n")
    
    # Dosyalara kaydet
    txt_file = OUTPUT_DIR / f"{username}_reels.txt"
    json_file = OUTPUT_DIR / f"{username}_reels.json"
    
    with open(txt_file, "w", encoding="utf-8") as f:
        for link in reels_list:
            f.write(link + "\n")
            
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({
            "username": username,
            "profile_url": reels_url,
            "total_reels": len(reels_list),
            "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reels": reels_list
        }, f, ensure_ascii=False, indent=2)
        
    print(f"💾 Linkler TXT olarak kaydedildi: {txt_file}")
    print(f"💾 Linkler JSON olarak kaydedildi: {json_file}\n")
    
    if reels_list:
        print("📌 İlk 3 Link:")
        for l in reels_list[:3]:
            print(f"   - {l}")
        if len(reels_list) > 3:
            print(f"   ... ve {len(reels_list) - 3} link daha dosyada.")
            
    return reels_list

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = input("Instagram profil linkini veya kullanıcı adını girin: ").strip()
    
    if not target:
        print("Lütfen geçerli bir kullanıcı adı veya profil linki girin!")
        sys.exit(1)
        
    collect_reels(target)
