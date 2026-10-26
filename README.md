<div align="center">

# 🎮 GENTAHAX MCP

### Growtopia GENTAHAX v5.61 için EKSİKSİZ AI Araç Seti — Model Context Protocol

**👑 Filigran: `mr_berk`**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.x-green.svg)](https://gofastmcp.com)
[![Lua](https://img.shields.io/badge/Lua-5.4.6-orange.svg)](https://lua.org)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

**35 araç** · **57 Android API** · **18 Windows API** · **32 cheat kodu** · **39 paket tipi** · **22 DLL-doğrulamalı variant fonksiyonu** · **19 ban-risk kuralı**

*SAHTE DEĞİL — GERÇEK VERİLERLE EĞİTİLDİ*

</div>

---

## 📡 Veri Kaynakları (Hepsi Gerçek)

Bu MCP **uydurma veri içermez**. Tüm bilgi tabanı iki doğrulanmış kaynaktan derlendi:

| Kaynak | Ne sağladı |
|---|---|
| 📖 **[GENTA-HAX-DOCS](https://github.com/GENTA7740/GENTA-HAX-DOCS)** — geliştiricinin RESMİ dokümantasyonu | 57 Android + 18 Windows Lua fonksiyon imzası, 15 struct, 10 hook, 32 CheatCode enum'u, Discord webhook yapısı |
| 🔬 **GENTAHAX v5.61 `GTInternal.dll`** binary analizi (MD5: `8f95ed4449dc4893f51d5380e31f8055`) | 19 bellek yaması ismi (Mod Fly, Ghost Ship...), 39 paket tipi, 22 variant fonksiyonu (OnTalkBubble, OnDialogRequest, OnFishStrike...), 62 ImGui fonksiyonu, gerçek protokol action'ları |
| 📜 **Resmî örnek scriptler** | `Genta_ImDemo.lua` (451 satır ImGui demosu), `extender.lua` (453 satır gerçek mod menüsü), `Genta_DiscordWebhook.lua` |

> Engine: **Lua 5.4.6** · Script yolları: `Android/media/GENTAHAX/Script/*.lua` (Android), `Script/*.lua` (Windows)

---

## 🛠️ Araç Seti (35 araç)

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
| `gh_templates_list` / `gh_template_get` | 7 hazır şablon (Auto Collect, ESP, Varlist Logger...) |
| `gh_item_lookup` | Eşya ID çerçevesi + `getItemByName` önerisi |
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

## 🚀 Kurulum

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
│  Cursor AI   │    35 araç     │  knowledge   │ ◄───────────────── │     .lua         │
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

`GENTAHAX MCP v1.0.0` — Gerçek verilerle eğitildi · Ban riski uyarı sistemli · 35 araç

*Veri: OFFICIAL GENTA-HAX-DOCS + GENTAHAX v5.61 DLL doğrulaması (Lua 5.4.6)*

</div>
