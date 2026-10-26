# 📦 KURULUM & KULLANIM REHBERİ — GENTAHAX MCP

> **Bu rehber kime yazıldı?** Hiçbir şey bilmeyen, bu repo'yu yeni bulan "X kişisi"ne.
> Aşağıdaki adımları sırayla uygula — toplam süre **~10 dakika**.
> Windows görselleri esas alınmıştır; Android farkları ayrıca işaretlenmiştir.

<div align="center">
👑 <b>mr_berk</b> edition — v1.3.0 · 40 araç · 6832 gerçek item ID
</div>

---

## 🔍 Bu nedir? (30 saniyede)

GENTAHAX MCP, yapay zekânı (Claude, Cursor, VS Code Copilot...) **Growtopia GENTAHAX v5.61 script uzmanı** yapan bir köprüdür. Kurduktan sonra AI'ına normal konuşma diliyle şunları yapabilir:

- 🎮 Oyun içinde **senin adına Lua kodu yazar ve çalıştırır** (önce ban riskini analiz eder!)
- 🔢 **"Dirt kaç numara?"** → gerçek veritabanından doğru cevap (6832 eşya)
- 🌍 **"Dünyamda kaç tane dirt var?"** → oyunun canlı belleğini tarayıp **gerçek sayıyı** verir
- 📚 Tüm GENTAHAX Lua API'sini, variant list okumayı, paket protokolünü bilir — **uydurmaz**

---

## ✅ Gereksinimler (başlamadan kontrol)

| # | Ne gerekiyor? | Nasıl kontrol ederim? |
|---|---|---|
| 1 | **GENTAHAX v5.61** kurulu ve çalışıyor (Android APK veya Windows) | Growtopia'da GENTAHAX menüsü açılıyor mu? |
| 2 | **Python 3.10+** | Terminalde `python --version` yaz |
| 3 | **MCP destekleyen AI istemcisi** | Claude Desktop *(önerilen)*, Cursor veya VS Code (Copilot) |
| 4 | *(Canlı veri için)* GENTAHAX **Script klasörünün yolu** | Aşağıda "Adım 0"da yol verildi |

> ⚠️ **Önce şunu bil:** Growtopia kullanım koşulları mod/cheat kullanımını yasaklar; hesabın **banlanabilir**. Bu MCP yüksek riskli kodlarda seni uyarır ve güvenli modda engeller, ama nihai karar ve sorumluluk sende. Değerli hesabında kullanma.

---

## Adım 0 — GENTAHAX'ı hazır et

MCP, GENTAHAX'ın **üstüne** biner; GENTAHAX'sız sadece bilgi araçları çalışır.

1. **GENTAHAX'ı aç** (Windows: `GH Loader.exe` → oyuna gir · Android: GENTAHAX APK ile oyuna gir).
2. İlk açılışta **lisans key** isterse: **herhangi bir metin yazıp geç** — lisans sistemi yereldir ve her girdiyi kabul eder (bilinen çalışan key: `R0VOVEEgSEFY`). İnternete bağlanmaz, sunucu yoktur.
3. **Script klasörünün tam yolunu not al:**
   - 🪟 **Windows:** `GH Loader.exe`'nin olduğu klasördeki `Script\` alt klasörü
     *(ör. `C:\Users\Ahmet\GENTAHAX\Script` — klasör yoksa kendin oluştur)*
   - 🤖 **Android:** `/storage/emulated/0/Android/media/GENTAHAX/Script/`
4. Hızlı test: GENTAHAX menü → **Lua Executor**'ün açık ve çalışır durumda olduğundan emin ol.

---

## Adım 1 — Python kur (yoksa)

1. https://www.python.org/downloads/ → **Download Python 3.1x** → kur.
2. Kurulum penceresinde **"Add python.exe to PATH" ✅ işaretle** (bu en çok unutulan adım!).
3. Doğrula — yeni bir terminal (Win+R → `cmd`) aç:

```bat
python --version
:: Python 3.10.x veya üstü görünüyorsa tamam
```

---

## Adım 2 — Bu repo'yu indir

**Seçenek A — ZIP (en kolay):**
GitHub sayfasında yeşil **`<> Code`** → **`Download ZIP`** → bir klasöre çıkar.
Önerilen yer: `C:\gentahax-mcp`

**Seçenek B — git:**

```bat
git clone https://github.com/BrK08/gentahax-mcp.git C:\gentahax-mcp
```

---

## Adım 3 — Kütüphaneyi kur (tek paket)

```bat
cd C:\gentahax-mcp
pip install -r requirements.txt
```

> `requirements.txt` içinde yalnızca `fastmcp` vardır. Hata alırsan: `pip install fastmcp`

Doğrulama (isteğe bağlı):

```bat
python tests\test_gentahax_mcp.py
:: SONUÇ: 41 başarılı, 0 başarısız  (ayrıca: tests\test_mcp_protocol.py, tests\test_world_count_e2e.py)
```

---

## Adım 4 — AI istemcisine tanıt

### 🖥️ Claude Desktop (önerilen)

1. https://claude.ai/download → kur, bir kez aç.
2. Bu dosyayı düzenle:
   - 🪟 **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
     *(Dosya Gezgini adres çubuğuna `%APPDATA%\Claude` yazıp Enter)*
   - 🍎 **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
3. İçine **kendi yollarınla** şunu yaz:

```json
{
  "mcpServers": {
    "gentahax": {
      "command": "python",
      "args": ["C:\\gentahax-mcp\\server.py"],
      "env": {
        "GENTAHAX_SCRIPT_DIR": "C:\\Users\\AHMET\\GENTAHAX\\Script"
      }
    }
  }
}
```

> 🪟 Yollarda **çift ters eğik çizgi** (`\\`) kullan. `GENTAHAX_SCRIPT_DIR` = Adım 0'da not aldığın Script klasörü.

4. Claude Desktop'ı **tamamen kapat ve yeniden aç** (sistem tepsisinden Exit).
5. Sohbet kutusundaki **🔧/ araçlar (Tools)** simgesine tıkla → **gentahax** listesinde `gh_about`, `gh_run_lua`, `gh_world_count_item`... görünmeli. Görünüyorsa **kurulum tamam** 🎉

### 🖱️ Cursor

Proje kökünde `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "gentahax": {
      "command": "python",
      "args": ["C:\\gentahax-mcp\\server.py"],
      "env": { "GENTAHAX_SCRIPT_DIR": "C:\\Users\\AHMET\\GENTAHAX\\Script" }
    }
  }
}
```

### 🧩 VS Code (GitHub Copilot)

`.vscode/mcp.json` (aynı içerik; VS Code ≥ 1.99 MCP destekler).

### 🤖 Android kullananlar için özel bölüm

MCP sunucusu **PC'de** çalışır ve telefona **USB (adb)** ile bağlanır:

1. Telefonda **Geliştirici seçenekleri → USB hata ayıklama** ✅
2. PC'ye adb kur ([platform-tools](https://developer.android.com/tools/releases/platform-tools)), telefonu USB ile bağla.
3. Doğrula: `adb devices` → cihaz listelenmeli.
4. Config'de `env`'i değiştir:

```json
"env": {
  "GENTAHAX_TARGET": "adb",
  "GENTAHAX_ADB_DIR": "/storage/emulated/0/Android/media/GENTAHAX/Script"
}
```

> Claude Desktop **PC'de** açık kalır; telefon USB ile bağlıyken AI oyununa canlı erişir.

### 🤖 Adım 4B — Claude Desktop YOK, HERHANGİ BİR AI kullanmak istiyorum

Config dosyası filan istemiyorsan **`chat.py`** hazır: ChatGPT, Gemini, GLM, DeepSeek, Qwen, Mistral, OpenRouter — hatta **anahtarsız ücretsiz lokal AI (Ollama/LM Studio)** — hepsi bağlanır:

```bat
cd C:\gentahax-mcp

:: 1) Önce MCP tarafını test et (ANAHTAR GEREKMEZ — kurulum doğru mu gör):
python chat.py --check

:: 2) Hangi AI'ler destekli, listele:
python chat.py --list-ai

:: 3) AI'nı bağla (örnekler):
python chat.py --provider deepseek --api-key sk-... --ask "dirt kaç numara?"
python chat.py --provider gemini   --api-key AIza...                  :: interaktif sohbet
python chat.py --provider ollama   --model llama3.1                   :: ÜCRETSİZ, lokal, anahtarsız

:: 4) İstersen kalıcı ayar (her komutta --api-key yazmazsın):
set GENTAHAX_AI_PROVIDER=deepseek
set DEEPSEEK_API_KEY=sk-...
python chat.py --ask "dünyada kaç tane dirt var?"
```

| Sağlayıcı | Anahtar nereden? | Not |
|---|---|---|
| `deepseek` | platform.deepseek.com | en ucuz seçeneklerden |
| `gemini` | aistudio.google.com | **ücretsiz** anahtar |
| `glm` | bigmodel.cn | glm-4-flash ücretsiz katman |
| `openrouter` | openrouter.ai | tek anahtarla 300+ model |
| `ollama` | **anahtar YOK** | ollama.com → `ollama pull llama3.1` — tamamen lokal |
| `lmstudio` | **anahtar YOK** | lmstudio.ai → Developer → sunucuyu aç |
| `custom` | kendi uçun | `--base-url` + `--model` ile her OpenAI-uyumlu servis |

> `chat.py`'de sohbette `/tools` yazarsan 40 aracı listeler, `/exit` ile çıkarsın. Güvenlik aynı: AI yüksek riskli kodu `gh_code_analyze`'den geçirmeden çalıştıramaz.

---

## Adım 5 — Canlı köprüyü kur (dünya/envanter verisi için)

Bilgi araçları (item DB, API docs, risk analizi) **köprüsüz çalışır**.
Canlı araçlar (dünya sayımı, oyuncu listesi, kod çalıştırma) için köprü lazım — **2 dakika**:

1. AI'ın sohbetine yaz:
   > *"Köprüyü cihazıma kur"* (araç: `gh_bridge_deploy`)
   → `gentahax_bridge.lua` dosyası Script klasörüne yazılır.
2. **Oyunda:** GENTAHAX menü → **Lua Executor** → listeden `gentahax_bridge.lua` → **Execute**.
3. AI'ın sohbetine yaz:
   > *"Cihaz durumunu kontrol et"* (araç: `gh_device_status`)
   → `"bridge_responding": true` / `PONG` görüyorsan **hazırsın** 🎉

**Köprü nasıl çalışır?** Oyun içinde sürekli çalışan sessiz bir Lua thread'idir:
`bridge_in.txt`'e yazılan komutları okur → çalıştırır → sonucu `bridge_out.txt`'ye yazar.
Hiçbir sunucuya bağlanmaz, her şey **senin cihazında** kalır.

---

## 🎮 KULLANIM — AI'ına yazacağın örnekler

Kurulumdan sonra özel bir şey yapmana gerek yok; **normal konuş**:

| 👤 Sen yazarsan... | 🤖 AI ne yapar |
|---|---|
| "Growtopia'da dirt kaç numara? Tohumu ne?" | Gerçek DB: **Dirt = ID 2**, Dirt Seed = ID 3 (6832 eşya) |
| "Bana auto collect scripti yaz" | Şablondan yazar → **"⚠️ BUNDA BAN RİSKİ VAR"** uyarısı + risk puanı verir |
| **"Dünyamda kaç tane dirt var?"** | Canlı RAM taraması → *"264 adet Dirt (ID 2) — ön plan 214, arka plan 50"* — **GERÇEK sayı** |
| "Dünyamdaki herkesi listele" | `gh_player_info` → canlı oyuncu listesi |
| "Envanterimi dök, kaç slot dolu?" | `gh_inventory_dump` → canlı envanter |
| "Şu kod banlar mı: `while true do ... end`" | `gh_code_analyze` → risk puanı + hangi satır neden riskli + düzeltme önerisi |
| "Ban yemeden ESP yapabilir miyim?" | Düşük riskli ImGui tabanlı ESP yazar (görsel katman = paket gönderilmez) |
| "Variant list nasıl okunur, örnekle göster" | DLL'den doğrulanmış gerçek variant fonksiyonlarıyla rehber + kod |
| "112 neyin numarası?" | **112 = Gems** ⭐ (ID soruları da ters yönde çalışır) |
| "Scriptimi kaydet: otomatik balık" | `gh_script_write` → Script klasörüne yazar → oyunda Execute ile çalıştırırsın |

**Akıllı olduğu konular:** 57 Android + 18 Windows Lua fonksiyonu, 10 hook, 32 cheat kodu, 39 paket tipi, 22 DLL-doğrulamalı variant fonksiyonu, 15 struct, 62 ImGui fonksiyonu, 7 hazır şablon, 19 ban-risk kuralı.

---

## 🛡️ Ban riski sistemi — seni nasıl korur?

`gh_run_lua` her kodu **çalıştırmadan önce** analiz eder:

```
🔴 YÜKSEK risk  → ÇALIŞTIRMAZ. "⚠️ BUNDA BAN RİSKİ VAR" + sebepler + düzeltme döner.
🟡 ORTA risk    → Çalıştırır ama uyarır.
🟢 DÜŞÜK risk   → Sorunsuz çalıştırır.
```

- Yüksek riskli örnekler: sleep'siz sonsuz döngü, paket spam, `action|enter_game` spam, hızlı dünya gir-çık, HWID değiştirme (`randomGid`, `setMac`...), döngüde `requestTileChange`.
- **Güvenli mod varsayılan AÇIK.** Yüksek riskli kodu bilerek çalıştırmak istiyorsan:
  1. Kodu düzelt (önerilen — AI zaten nasıl düzelteceğini söyler), **veya**
  2. Config'de `"GENTAHAX_SAFE_MODE": "0"` + çağrıda `force=true` (üstüne gitmek senin kararın).
- **Okuma araçları asla paket göndermez:** `gh_world_count_item`, `gh_world_census`, `gh_world_snapshot`, `gh_player_info`, `gh_inventory_dump` → RAM'den okur → **ban riski YOK**.

---

## 🔧 Sorun giderme

| Belirti | Çözüm |
|---|---|
| `'python' bulunamadı` | Python kurulumunda "Add to PATH" unutmuşsun — Python'u yeniden kur, kutuyu işaretle. Ya da `py` komutunu dene. |
| Claude'da 🔧 araçlar görünmüyor | 1) JSON'ta yazım hatası var (virgül, tırnak) — dosyayı jsonlint.com'da doğrula. 2) Yollar gerçek mi? 3) Claude'ı sistem tepsisinden tam kapat-aç. 4) `%APPDATA%\Claude\logs\mcp*.log`'a bak. |
| `ModuleNotFoundError: fastmcp` | `pip install fastmcp` — ya da config'de `command` olarak Python'ın tam yolunu ver (`C:\\Python312\\python.exe`). |
| `gh_device_status` → `configured: false` | `GENTAHAX_SCRIPT_DIR` yanlış/eksik (Windows) veya `GENTAHAX_TARGET=adb` yok (Android). |
| `bridge_responding: false` | 1) Oyunda `gentahax_bridge.lua`'yı Execute ettin mi? 2) Oyunda dünya içinde misin (menü değil)? 3) 10 sn bekle, tekrar sor. 4) Script klasöründe `bridge_in.txt`/`bridge_out.txt` oluşmuş mu bak. |
| `adb devices` boş | USB hata ayıklama kapalı / kablo data değil / telefonda çıkan izin sorusunu onayla. |
| Yüksek riskli kod "çalışmadı" | Bilerek çalıştırmak istiyorsan: `GENTAHAX_SAFE_MODE=0` + `force=true`. Önce AI'ın önerdiği düzeltmeyi dene. |
| Cevaplar Türkçe değil | AI'a "bana Türkçe cevap ver" de — MCP Türkçe/İngilizce ikisinde de çalışır. |

---

## ❓ SSS

**Ücretli mi?** Hayır. MIT lisansı, tamamen açık kaynak.

**İnternet gerekli mi?** Bilgi araçları tamamen **offline** çalışır. Canlı köprü yerel dosya/USB ile çalışır. İnterneti yalnızca AI istemcisi (Claude vb.) kendi işi için kullanır.

**Banlenir miyim?** Mod kullanmak ToS dışıdır, risk **her zaman sende**. Bu MCP'nin işi riski **görünür kılmak**: yüksek riskli kodu çalıştırmaz, nedenini söyler, düzeltme önerir. Okuma araçları (dünya sayımı vb.) sunucuya paket göndermediği için güvenlidir.

**Başka AI'larla çalışır mı?** MCP protokolünü destekleyen her istemcide: Claude Desktop, Cursor, VS Code Copilot, Windsurf, Zed...

**Veriler nereden?** GENTAHAX geliştiricisinin resmî dokümantasyonu + GTInternal.dll binary analizi + items.dat tabanlı 6832 eşyalık gerçek liste. **Uydurma veri yok** — belirsiz sorularda AI tahmin etmez, adayları listeler.

**GENTAHAX'ı nereden bulacağım?** Bu repo yalnızca MCP aracıdır; modun kendisi dahil değildir. Modu zaten kullananlar içindir.

---

## 👑 mr_berk

```
GENTAHAX MCP v1.3.0 — mr_berk edition
Gerçek verilerle eğitildi · Ban riski uyarı sistemli · 40 araç · 6832 gerçek eşya ID
```

*Bu rehberi beğendiysen repo'ya ⭐ bırakabilirsin. Sorun yaşarsan [Issues](https://github.com/BrK08/gentahax-mcp/issues) açık.*
