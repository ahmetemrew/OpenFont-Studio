/**
 * Instagram Reels Otomatik Link Toplayıcı (Tarayıcı Konsol Kodu)
 * 
 * Kullanımı:
 * 1. Tarayıcınızda istediğiniz Instagram profilinin Reels sekmesine gidin (örn: https://www.instagram.com/kullanici/reels/)
 * 2. Klavyeden F12 tuşuna basıp "Console" (Konsol) sekmesine gelin.
 * 3. Aşağıdaki kodun tamamını yapıştırıp ENTER'a basın.
 * 4. Sayfa otomatik aşağı kayacak, ekranda toplanan video sayısı görünecek ve bittiğinde otomatik .txt olarak inecektir!
 */

(async function() {
    console.log("%c🎬 Instagram Reels Toplayıcı Başlatıldı...", "color: #e1306c; font-size: 16px; font-weight: bold;");
    
    // Ekrana canlı bilgi kutucuğu (HUD) ekle
    let hud = document.getElementById("reels_hud");
    if (!hud) {
        hud = document.createElement("div");
        hud.id = "reels_hud";
        hud.style.cssText = "position:fixed; top:20px; right:20px; background:#1e293b; color:#f8fafc; padding:16px 20px; border-radius:12px; z-index:999999; box-shadow:0 10px 30px rgba(0,0,0,0.5); font-family:sans-serif; font-size:14px; border:2px solid #e1306c;";
        document.body.appendChild(hud);
    }
    
    const reelsSet = new Set();
    let idleCount = 0;
    const maxIdle = 8;
    let lastCount = 0;
    
    while (idleCount < maxIdle) {
        // Sayfadaki linkleri topla
        document.querySelectorAll('a[href*="/reel/"]').forEach(a => {
            const clean = a.href.split('?')[0];
            if (clean.includes('/reel/')) reelsSet.add(clean);
        });
        
        const count = reelsSet.size;
        hud.innerHTML = `<strong>🎬 Reels Toplayıcı</strong><br>Toplanan: <span style="color:#10b981; font-size:18px; font-weight:bold;">${count}</span> adet<br><small style="color:#94a3b8;">Aşağı kaydırılıyor (${idleCount}/${maxIdle})...</small>`;
        
        if (count > lastCount) {
            idleCount = 0;
            lastCount = count;
        } else {
            idleCount++;
        }
        
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 1200));
    }
    
    hud.innerHTML = `<strong>🎉 Bitti!</strong><br>Toplam: <span style="color:#10b981; font-size:18px;">${reelsSet.size}</span> Reels<br><small>Dosya indiriliyor...</small>`;
    
    // TXT dosyası olarak indir
    const content = Array.from(reelsSet).join("\n");
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `instagram_reels_${window.location.pathname.replace(/[^a-zA-Z0-9]/g, "_")}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    setTimeout(() => hud.remove(), 4000);
    console.log(`%c✅ Toplam ${reelsSet.size} adet link başarıyla indirildi!`, "color: #10b981; font-size: 16px; font-weight: bold;");
})();
