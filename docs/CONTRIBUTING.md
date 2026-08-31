# Katkı Rehberi

OpenPixelFont'a katkıda bulunmak için teşekkürler! Bu rehber yeni bir karakter eklemeyi veya var olan bir karakteri geliştirmeyi anlatır.

## Karakter Dosya Formatı

Her karakter `glyphs/<ad>.json` şeklinde ayrı bir dosyadır. Örnek:

```json
{
  "unicode": 65,
  "advance": 600,
  "grid": [
    "  #  ",
    " # # ",
    "#   #",
    "#####",
    "#   #",
    "#   #",
    "#   #",
    "     "
  ]
}
```

| Alan | Açıklama |
|------|----------|
| `unicode` | Karakterin Unicode kod noktası (ondalık). Örn: `A` için `65`. |
| `advance` | Karakterin toplam genişliği (units). |
| `grid` | 5 sütun × 8 satırlık karakter tasarımı. `#` dolu hücre, boşluk boş hücredir. |

Grid kuralları:

- En üst satır en yüksek y değerindedir.
- Her hücre `cellWidth` × `cellHeight` boyutundadır (varsayılan 100×100).
- Tüm karakterler aynı 5×8 boyutunda olmalıdır.

## Adım Adım Yeni Karakter Ekleme

1. **Dallan:**

   ```bash
   git checkout -b add-turkish-g
   ```

2. **Yeni JSON dosyası oluştur:**

   Örneğin `glyphs/gbreve.json`:

   ```json
   {
     "unicode": 287,
     "advance": 600,
     "grid": [
       " ### ",
       "     ",
       " ### ",
       "#   #",
       "#   #",
       " ####",
       "    #",
       " ### "
     ]
   }
   ```

3. **Fontu derle ve kontrol et:**

   ```bash
   python builder/build_font.py
   ```

4. **Önizle:**

   ```bash
   python builder/serve_preview.py
   ```

   Tarayıcıda `http://localhost:8765/web/preview.html` aç, yeni karakteri dene.

5. **Commit ve PR:**

   ```bash
   git add glyphs/gbreve.json
   git commit -m "Add Turkish gbreve (ğ) glyph"
   git push origin add-turkish-g
   ```

   Ardından Pull Request aç. GitHub Actions otomatik olarak fontu derleyip önizleme çıktısı üretecek.

## Tasarım İlkeleri

- **Tutarlılık:** Tüm karakterler aynı grid sistemi ve kalınlıkta olmalı.
- **Okunabilirlik:** Küçük boyutlarda bile karakter tanınabilir olmalı.
- **Boşluk:** İki karakter arasındaki boşluk `advance` değeriyle ayarlanır. Gereksiz dar veya geniş yapma.
- **Türkçe:** `ı İ ç Ç ğ Ğ ö Ö ş Ş ü Ü` gibi karakterleri eklemeye öncelik ver.

## Sorular?

Bir sorunla karşılaşırsan [Issues](../../issues) bölümünden bize ulaş.
