# Instagram Reels Otomatik Link Toplayıcı 🎬🔗

Bu araç, herhangi bir Instagram profilindeki **tüm Reels videolarının linklerini** tek tek uğraşmadan, otomatik aşağı kaydırarak saniyeler içinde toplar ve `.txt` ile `.json` formatında kaydeder.

---

## 🚀 1. Yöntem: Python ile Otomatik Toplama (En Kolay)

Terminalden tek satır komutla çalıştırabilirsiniz:

```bash
.venv\Scripts\python tools\reels_collector\collect_reels.py https://www.instagram.com/KULLANICI_ADI/
```
*(veya sadece kullanıcı adını girin: `.venv\Scripts\python tools\reels_collector\collect_reels.py @kullanici`)*

- Tarayıcınızda otomatik olarak o sayfa açılır.
- Arka planda aşağı kaydırarak 100+ videonun tamamını tarar.
- Sonuçları `tools/reels_collector/output/<kullanici>_reels.txt` dosyasına alt alta sıralar.

---

## ⚡ 2. Yöntem: Tarayıcı Konsolu ile (F12 - Kuruluma Gerek Yok)

1. Tarayıcınızda Instagram sayfasının Reels sekmesine gidin (örn: `https://www.instagram.com/kullanici/reels/`).
2. Klavyeden **F12** tuşuna basıp **Console (Konsol)** sekmesini açın.
3. [`browser_console_script.js`](browser_console_script.js) içindeki kodu yapıştırıp **Enter**'a basın.
4. Sayfa kendiliğinden kayacak ve bittiğinde tüm linkler otomatik olarak bilgisayarınıza `.txt` olarak inecektir.
