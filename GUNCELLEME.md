# 🔄 APK Güncellemesi Gelirse Ne Olur? — GENTAHAX MCP

> **Kısa cevap:** Çoğu güncellemede **hiçbir şey olmaz, her şey çalışmaya devam eder.**
> Emin olmak için 5 dakikalık kontrol listesini uygula (aşağıda). Kırıcı büyük
> değişikliklerde bile MCP **kod değil, düz veri dosyası** güncellenerek uyum sağlanır.

<div align="center">
👑 <b>mr_berk</b> edition — v1.5.0 · 45 araç · 6832 gerçek item ID
</div>

---

## 📊 3 Senaryo

| Senaryo | Ne olur | Olasılık | Ne yapacaksın |
|---|---|---|---|
| **A — Küçük güncelleme** (Lua API aynı kalmış) | **Her şey çalışmaya devam eder.** MCP, APK'nın içinde çalışmaz — köprü (bridge) dosyaları üzerinden konuşur; Lua seviyesindeki bu iletişim sürüm numarasından bağımsızdır | En sık | 5 dk kontrol listesi → hepsi yeşilse tamam |
| **B — Bazı fonksiyonlar değişmiş/yok olmuş** | O fonksiyonu kullanan şablonlar/scriptler hata verir; **geri kalan her şey çalışır** | Ara sıra (büyük sürümlerde) | `gh_compat_check` çağır → eksikler ve etkilenen şablonlar listelenir → `data/api_*.json` dosyaları güncellenir |
| **C — Köprü mekanizması kırıldı** (enjeksiyon/dosya yapısı değişti) | Scriptler cihaza ulaşamaz (`gh_device_status` → PONG gelmez) | Nadir | Yeni APK yeniden analiz edilir → `data/*.json` güncellenir → köprü yeniden kurulur |

**Mimarlik garantisi:** MCP'nin tüm bilgisi (57 Android + 18 Windows API imzası, 32 cheat
kodları, 6832 item ID, şablonlar, ban kuralları) **kodun içine gömülü değildir** —
`data/` klasöründeki **düz JSON dosyalarında** durur. APK değişince uyum sağlamak
**kod yazmayı değil, dosya değiştirmeyi** gerektirir.

**Item veritabanı APK'dan bağımsızdır:** 6832'lik eşya listesi Growtopia'ın kendi
`items.dat`'inden derlenmiştir — GENTAHAX sürümü değişse bile geçerlidir (oyun kendi
eşyalarını değiştirirse tablo yenilenir, o kadar).

---

## ✅ 5 Dakikalık Kontrol Listesi (her güncellemeden sonra)

```
1) Oyunu aç, bir dünyaya gir, gentahax_bridge.lua'yı Lua Executor'dan çalıştır
2) gh_device_status        → "PONG" geliyor mu?        → geliyorsa Senaryo A ✓
3) gh_compat_check         → kaç fonksiyon bulundu?     → 57/57 ise TAM UYUMLU ✓
4) gh_auto_test ile mini test (istersen):
   gh_run_lua("return getWorld() and getWorld().name or 'ERR|NO_WORLD'")
   → dünya adı dönüyorsa canlı zincir tam çalışıyor ✓
```

Hepsi yeşil → **hiçbir şey yapmana gerek yok.**

---

## 🗂️ Veri Dosyası Haritası (hangi dosya ne tutar, nasıl yenilenir)

| Dosya | İçerik | Nasıl yenilenir |
|---|---|---|
| `data/api_android.json` | 57 Android Lua API fonksiyonu (imza, açıklama, örnek, risk) | Yeni APK/DLL analiziyle (gh_code_analyze akışı) |
| `data/api_windows.json` | 18 Windows Lua API fonksiyonu | Aynı |
| `data/structs_hooks_enums.json` | Struct'lar (NetAvatar...), 10 hook, 32 CheatCode, 19 bellek yaması, 39 paket tipi | Aynı |
| `data/items.json` | 6832 gerçek item ID (items.dat tabanlı) | Oyun eşya eklerse listeden yeniden çekilir |
| `data/protocol.json` | Text paket protokolü + doğrulanmış variant fonksiyonları | Yeni DLL analiziyle |
| `data/ban_rules.json` | Ban riski sınıflandırma kuralları | Gerektikçe elle |
| `data/templates.json` | 9 doğrulanmış script şablonu | Fonksiyonlar değişirse güncellenir |
| `AI_EGITIM.md` / `AI_TRAINING.md` | AI eğitim paketi | `python scripts/gen_training_pack.py` (data dosyalarından OTOMATİK yeniden üretilir) |

> 🔁 **Önemli döngü:** `data/` dosyalarını güncelledikten sonra eğitim paketini
> yeniden üretmeyi unutma — paket o dosyalardan otomatik kurulur:
> ```bat
> python scripts\gen_training_pack.py
> ```

---

## 🧪 Senaryo B örneği: fonksiyon değişmişse

1. `gh_compat_check` çağır → örn. çıktı: `KISMİ UYUM — 2/57 fonksiyon yok: eskiFn, digerFn`
   + "etkilenen şablonlar: dirt_farm, auto_collect"
2. Yeni APK'da o işi yapan **yeni fonksiyonun adını** bul (resmi GENTA-HAX-DOCS /
   DLL string analizi) → `data/api_android.json`'a ekle/eskiyi düzelt
3. Etkilenen şablonları `data/templates.json` içinde yeni isimle güncelle
4. `python scripts/gen_training_pack.py` → eğitim paketi tazelenir
5. `gh_compat_check` tekrar → TAM UYUMLU ✓

---

## ⬆️ MCP'in kendisi güncellenirse (git pull)

```bat
cd C:\gentahax-mcp
git pull
```
GitHub deposu güncelse bu komutla son sürümü alırsın; veri dosyaları + araçlar birlikte
gelir. Kendi `data/` değişikliklerin varsa önce yedekle (`git stash` çakışmaları saklar).

## 📜 Sürüm Geçmişi

| Sürüm | Ne geldi |
|---|---|
| v1.5.0 | Hazır mod kontrolü (gh_cheat_set/gh_cheat_status) · otomatik test döngüsü (gh_auto_test) · APK uyum testi (gh_compat_check) · genel script üreteci (gh_script_gen) · AI eğitim paketi |
| v1.4.0 | Uygulamadan bağlantı: `server.py --http` + ChatGPT Plugins / Claude Connectors |
| v1.3.0 | `chat.py` — herhangi bir AI ile sohbet (10 sağlayıcı, API'siz lokal dahil) |
| v1.2.0 | `gh_farm_script_gen` — şablon dışı istek üreteci |
| v1.1.0 | Gerçek item ID veritabanı (6832 eşya) + dünya eşya sayımı |

## 👑 mr_berk

`GENTAHAX MCP v1.5.0` — Gerçek verilerle eğitildi · Ban riski uyarı sistemli · 45 araç

*Veri: OFFICIAL GENTA-HAX-DOCS + GENTAHAX v5.61 DLL doğrulaması (Lua 5.4.6) + items.dat tabanlı gerçek item ID listesi*
