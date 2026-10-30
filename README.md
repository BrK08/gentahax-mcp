<div align="center">

# 🎮 GENTAHAX MCP

### Growtopia GENTAHAX v5.61 için EKSİKSİZ AI Araç Seti — Model Context Protocol

**👑 Filigran: `mr_berk`**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.x-green.svg)](https://gofastmcp.com)
[![Lua](https://img.shields.io/badge/Lua-5.4.6-orange.svg)](https://lua.org)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

**40 araç** · **6832 gerçek item ID** · **57 Android API** · **18 Windows API** · **32 cheat kodu** · **39 paket tipi** · **22 DLL-doğrulamalı variant fonksiyonu** · **19 ban-risk kuralı**

*SAHTE DEĞİL — GERÇEK VERİLERLE EĞİTİLDİ*

📚 **Kurulum rehberi:** [KURULUM.md](KURULUM.md) (Türkçe) · [INSTALL.md](INSTALL.md) (English)

</div>

---

## 📡 Veri Kaynakları (Hepsi Gerçek)

Bu MCP **uydurma veri içermez**. Tüm bilgi tabanı iki doğrulanmış kaynaktan derlendi:

| Kaynak | Ne sağladı |
|---|---|
| 📖 **[GENTA-HAX-DOCS](https://github.com/GENTA7740/GENTA-HAX-DOCS)** — geliştiricinin RESMİ dokümantasyonu | 57 Android + 18 Windows Lua fonksiyon imzası, 15 struct, 10 hook, 32 CheatCode enum'u, Discord webhook yapısı |
| 🔬 **GENTAHAX v5.61 `GTInternal.dll`** binary analizi (MD5: `8f95ed4449dc4893f51d5380e31f8055`) | 19 bellek yaması ismi (Mod Fly, Ghost Ship...), 39 paket tipi, 22 variant fonksiyonu (OnTalkBubble, OnDialogRequest, OnFishStrike...), 62 ImGui fonksiyonu, gerçek protokol action'ları |
| 📜 **Resmî örnek scriptler** | `Genta_ImDemo.lua` (451 satır ImGui demosu), `extender.lua` (453 satır gerçek mod menüsü), `Genta_DiscordWebhook.lua` |
| 🆕 **[yoshinogaming/growtopia-item-id](https://github.com/yoshinogaming/growtopia-item-id)** — items.dat tabanlı GERÇEK eşya ID listesi | **6832 eşya** (ID 0–6831): `2=Dirt`, `3=Dirt Seed`, `112=Gems`, `6=Main Door` doğrulandı; 3383 gerçek seed çifti listeden türetildi |

> Engine: **Lua 5.4.6** · Script yolları: `Android/media/GENTAHAX/Script/*.lua` (Android), `Script/*.lua` (Windows)

---

## 🛠️ Araç Seti (40 araç)

### 📚 Bilgi Tabanı — offline, her zaman çalışır
| Araç | Açıklama |
|---|---|
| `gh_about` | Sürüm, veri kaynakları, istatistikler |
| `gh_api_search` | Fonksiyon/hook/struct arama (`query`, `platform`) |
| `gh_api_list` | Platformun TÜM API'si (isim+imza+risk) |
| `gh_api_detail` | Fonksiyonun tam detayı + örnek kod |
| `gh_struct_info` | Struct alanları (NetAvatar, TankPacketStruct, TileExtra...) |
| `gh_hooks_list` | 10 hook + imzaları + örnekler |
| `gh_cheats_list` | 32 CheatCode + 19 bellek yaması ismi |
| `gh_packet_types` | 39 raw paket tipi + ENet flag'leri |
| `gh_variant_guide` | ⭐ GERÇEK variant list rehberi (DLL doğrulamalı) |
| `gh_protocol_guide` | Text paket protokolü (action\|drop, action\|wrench...) |
| `gh_imgui_api` | 62 ImGui fonksiyonu |
| `gh_examples_list` / `gh_example_get` | Resmî örnek scriptler |
| `gh_templates_list` / `gh_template_get` | 9 hazır şablon (Auto Collect, ESP, Varlist Logger, **Dirt Farm**, **Human Responder**...) |
| `gh_item_lookup` | Eşya ID çözümü — 6832'lik GERÇEK veritabanı + seed eşleri |
| 🆕 `gh_item_db_search` | GERÇEK veritabanında serbest arama (isim veya ID, 6832 eşya) |
| 🆕 `gh_item_db_info` | ID'nin tam bilgisi: isim, seed eşleri, komşu ID'ler |
| `gh_snippet` | Fonksiyon için hazır kod parçası |
| `gh_learn_lua_gentahax` | 7 konulu eğitim rehberi |

### 🛡️ Güvenlik — ban riski analizi (asla çalıştırmaz)
| Araç | Açıklama |
|---|---|
| `gh_code_analyze` | ⭐ Risk + sözdizimi + uydurma fonksiyon tespiti |
| `gh_ban_risk` | Detaylı risk raporu (0-100 puan) |
| `gh_safety_rules` | 19 kuralın tam listesi + genel rehber |
| `gh_safe_mode` | Güvenli mod anahtarı |

### 🎮 Canlı Köprü — gerçek zamanlı oyun verisi
| Araç | Açıklama |
|---|---|
| `gh_device_status` | Cihaz/köprü durumu |
| `gh_bridge_deploy` | Lua köprüsünü cihaza kur |
| `gh_run_lua` | ⭐ Oyun içinde kod çalıştır (**önce risk analizi yapar!**) |
| `gh_world_snapshot` | Canlı dünya görüntüsü |
| 🆕 `gh_world_count_item` | ⭐⭐ **"Dünyada kaç tane X var?" — gerçek canlı sayım** (sadece okur, ban riski yok) |
| 🆕 `gh_world_census` | Canlı dünyanın TAM eşya sayımı (en çok kullanılanlar fg/bg) |
| 🆕 `gh_farm_script_gen` | ⭐⭐ **ŞABLON-DIŞ İSTEK ÜRETEÇ** — 'tüm X'leri kır ve gem söyle' türü istekler için hedefe özel tam script üretir (gerçek DB ID'li)
| `gh_player_info` | Dünyadaki tüm oyuncular |
| `gh_inventory_dump` | Envanter dökümü |
| `gh_stop_scripts` | Acil durdurma (killAllThread) |

### 📁 Script Yönetimi
`gh_scripts_list` · `gh_script_read` · `gh_script_write` · `gh_script_delete` · `gh_logs_read`

### ℹ️ Meta
`gh_watermark` (mr_berk imza bloğu)

---

## ⚠️ Ban Riski Sistemi

Kullanıcı güvenliği birinci önceliktir. `gh_run_lua` her çalıştırmadan **önce** kodu analiz eder:

```json
{
  "calistirildi": false,
  "uyari": "⚠️ UYARI: BUNDA BAN RİSKİ VAR! Bu kod yüksek riskli işlemler içeriyor...",
  "risk_seviyesi": "YÜKSEK (100/100)",
  "sebepler": ["Sleep'siz sonsuz döngü — dongu icine sleep(300) ekleyin", ...],
  "ne_yapmali": "Kodun bu kısmını düzeltin ya da force=true ile tekrar deneyin."
}
```

**Kural tablosu (19 kural):**
- 🔴 **YÜKSEK**: sleep'siz döngü + paket spam, `action|enter_game`, hızlı dünya gir-çık, HWID değiştirme (`randomGid`/`randomMac`/`setGid`/`setMac`), ENet yönlendirme, döngüde `requestTileChange`
- 🟡 **ORTA**: auto-collect/fishing/farm (insan aralıklarıyla düşer), Mod Fly, No Clip, toplu drop
- 🟢 **DÜŞÜK**: ESP/görsel katman, veri okuma, ImGui, webhook

Güvenli mod (varsayılan AÇIK): yüksek riskli kod `force=true` ile bile çalışmaz — `GENTAHAX_SAFE_MODE=0` gerekir.

---

## 🟤 "Dünyada Kaç Tane X Var?" — Gerçek Canlı Cevap

Kullanıcı AI'ına `dünyada kaç tane dirt var` diye sorduğunda, AI `gh_world_count_item("Dirt")` çağırır ve **oyunun canlı belleğindeki TÜM tile'lar taranır**:

```json
{
  "soru": "'BUYDIRT dünyasında kaç tane Dirt var?",
  "cevap": "264 adet Dirt (ID 2) — ön plan: 214, arka plan: 50",
  "taranan_tile": 6000,
  "on_plan_fg": 214,
  "arka_plan_bg": 50,
  "canli_dogrulama": { "oyun_dedi": "Dirt", "veritabani_dedi": "Dirt", "uyusuyor": true },
  "ban_riski": "YOK — sadece okuma (RAM taraması), sunucuya hiçbir paket gönderilmedi"
}
```

Nasıl çalışır:
1. **Eşya çözümü**: "Dirt" → ID 2 (6832'lik GERÇEK veritabanından; belirsiz isimde asla tahmin etmez, aday listeler)
2. **Canlı tarama**: köprü `getTile()` vektörünü tarar — **sadece okur**, sunucuya paket gitmez → ban riski YOK
3. **Çapraz doğrulama**: oyunun kendi `getItemByID(2).name` sonucu veritabanıyla karşılaştırılır

> Bu akış uçtan uca test edildi: gerçek Lua runtime'ında 6000 tile'lık simüle dünya, dosya-IPC köprüsü ve MCP protokolü üzerinden 30/30 test geçti (`scripts/test_world_count_e2e.py`).

---

## 🧩 Şablon-Dışı İstekler — "tüm pepperları kır ve çıkan gem'i söyle"

Hazır şablonu **olmayan** her istek de çalışır: AI bilgi tabanından (gerçek DB ID'si + gerçek API imzaları) **hedefe özel kod üretir**. `gh_farm_script_gen('Pepper')` örneği:

1. **Çözüm**: "Pepper" → **ID 4570** (6832'lik gerçek DB; belirsiz istekte asla tahmin etmez, aday listeler)
2. **Üretim**: tarama → punch (`sendPacketRaw`, docs'tan doğrulanmış gerçek paket formatı) → `getLocal().gems` önce/sonra → `FARM_RESULT` raporu `doLog` ile `lua_logs.txt`'ye
3. **Güvenlik**: üretilen kod **YÜKSEK ban riski** diye işaretlenir ("⚠️ BUNDA BAN RİSKİ VAR" — döngüde punch = farm bot paterni)
4. **Rapor**: `gh_logs_read` → `"37 pepper kırıldı, +97 gems"` — **gerçek sayılar**, uydurma değil

> Kanıt: `tests/test_adhoc_request.py` — 4 katman (bilgi gerçekliği → gerçek Lua runtime → güvenlik → MCP protokolü), **34/34 geçti**: 37 Pepper fg + 100 Rock sapor içeren simüle dünyada Faz A anında `FOUND:37`, Faz B 37'sini de kırdı, Rock'a **tek punch atılmadı**, `GEMS_GAINED:97` kesin doğru.

---

## 🤖 Hangi AI ile Çalışır? — HERHANGİ BİRİ ile

**Yol 1 — MCP destekleyen uygulama** (config dosyası yeterli, `chat.py` GEREKMEZ):
Claude Desktop · Cursor · VS Code (Copilot) · Windsurf · Zed · Cline → bkz. [KURULUM.md](KURULUM.md)

**Yol 2 — `chat.py` ile HERHANGİ BİR AI** (OpenAI-uyumlu her sağlayıcı):

```bat
python chat.py --list-ai                          # hangi AI'ler destekli? (10 sağlayıcı)
python chat.py --check                            # anahtarsız MCP self-test (ilk test komutu)
python chat.py --provider openai  --api-key sk-... --ask "dirt kaç numara?"
python chat.py --provider deepseek --api-key sk-...                 # interaktif sohbet
python chat.py --provider ollama  --model llama3.1                  # ÜCRETSİZ, lokal, anahtarsız
python chat.py --provider custom  --base-url http://localhost:1234/v1 --model benim-modelim
```

| Sağlayıcı | Varsayılan model | Anahtar |
|---|---|---|
| `openai` | gpt-4o-mini | platform.openai.com |
| `deepseek` | deepseek-chat | platform.deepseek.com (çok ucuz) |
| `glm` | glm-4-flash | bigmodel.cn — ücretsiz katmanı var |
| `gemini` | gemini-2.0-flash | Google AI Studio — ücretsiz anahtar |
| `openrouter` | 300+ model | tek anahtarla hepsi |
| `qwen` / `mistral` | qwen-plus / mistral-small | DashScope / console.mistral.ai |
| `ollama` / `lmstudio` | llama3.1 / local-model | **ANAHTAR GEREKMEZ** (lokal, ücretsiz) |
| `custom` | sen belirt | herhangi bir OpenAI-uyumlu uç |

`chat.py` arka planda AI ↔ 40 MCP aracı arasında **tool-calling döngüsü** kurar: AI istediği aracı çağırır → gerçek sonuç modele döner → nihai cevap. Güvenlik sistem prompt'a gömülü: AI yüksek riskli kodda `gh_code_analyze` yapıp **"⚠️ BUNDA BAN RİSKİ VAR"** demeden `gh_run_lua` çağıramaz. Kanıt: `tests/test_chat_agent.py` (15/15).

**Yol 3 — DOĞRUDAN UYGULAMADAN** (ChatGPT web · Claude web/**mobil** · Claude Desktop): `python server.py --http` → ücretsiz cloudflared tunnel → ChatGPT **Plugins / Developer Mode** veya Claude **Custom Connectors**'a ekle (ücretsiz Claude planında bile 1 connector). Kanıt: `tests/test_http_mode.py` (10/10). Detaylı adımlar: [KURULUM.md](KURULUM.md) Adım 4C.

---

## 🚀 Kurulum

> 📚 **Sıfırdan başlayan biri için tam rehber:** **[KURULUM.md](KURULUM.md)** (Türkçe) · [INSTALL.md](INSTALL.md) (English) — gereksinimler, adım adım kurulum, sorun giderme ve SSS dahil.
> Aşağıda hızlı özet var:

### 1) Gereksinimler
```bash
pip install fastmcp          # MCP sunucu kütüphanesi
```

### 2) Claude Desktop
`claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "gentahax": {
      "command": "python",
      "args": ["C:/yol/gentahax-mcp/server.py"],
      "env": {
        "GENTAHAX_SCRIPT_DIR": "C:/Users/KULLANICI/GENTAHAX/Script"
      }
    }
  }
}
```

### 3) Cursor / VS Code (Copilot)
`.cursor/mcp.json` veya `.vscode/mcp.json`:
```json
{
  "mcpServers": {
    "gentahax": {
      "command": "python",
      "args": ["./gentahax-mcp/server.py"]
    }
  }
}
```

### 4) Android (adb köprüsü)
```json
"env": {
  "GENTAHAX_TARGET": "adb",
  "GENTAHAX_ADB_DIR": "/storage/emulated/0/Android/media/GENTAHAX/Script"
}
```

### 5) Canlı köprü kurulumu (oyun verisi için)
1. AI'a: `gh_bridge_deploy` çağır → `gentahax_bridge.lua` cihaza yazılır
2. GENTAHAX menü → Lua Executor → `gentahax_bridge.lua` → **Execute**
3. AI'a: `gh_device_status` → `PONG` görüyorsan hazırsın 🎉

Artık AI gerçek zamanlı dünya/oyuncu/envanter verisi okuyabilir ve güvenli kod çalıştırabilir.

---

## 🏗️ Mimari

```
┌─────────────┐   MCP (stdio)   ┌──────────────┐   bridge_in.txt    ┌──────────────────┐
│  Claude /    │ ◄────────────► │  server.py   │ ─────────────────► │ gentahax_bridge  │
│  Cursor AI   │    40 araç     │  knowledge   │ ◄───────────────── │     .lua         │
└─────────────┘                 │  bridge      │   bridge_out.txt   │ (oyun içinde     │
                                └──────────────┘                    │  sürekli thread) │
                                                                    └──────────────────┘
```

- **Bilgi araçları** köprü olmadan çalışır (offline)
- **Canlı araçlar** dosya-IPC köprüsü kullanır: Python `bridge_in.txt`'ye komut yazar → Lua thread okuyup çalıştırır → sonuç `bridge_out.txt`'ye döner
- Windows: doğrudan klasör · Android: `adb push/pull`

---

## 📜 Lisans & Sorumluluk

MIT License — bkz. [LICENSE](LICENSE).

> **⚠️ SORUMLULUK REDDİ**: Bu proje eğitim ve araştırma amaçlıdır. Growtopia kullanım koşulları üçüncü parti mod/cheat kullanımını yasaklar; **hesabınız banlanabilir**. GENTAHAX MCP, yüksek riskli kodlarda sizi uyarır ancak nihai karar ve sorumluluk size aittir. Değerli eşyalarınızın olduğu hesaplarda kullanmayın.

---

<div align="center">

### 👑 mr_berk

`GENTAHAX MCP v1.4.0` — Gerçek verilerle eğitildi · Ban riski uyarı sistemli · 40 araç · 6832 gerçek eşya ID

*Veri: OFFICIAL GENTA-HAX-DOCS + GENTAHAX v5.61 DLL doğrulaması (Lua 5.4.6) + items.dat tabanlı gerçek item ID listesi*

</div>
