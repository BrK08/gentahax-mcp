#!/usr/bin/env python3
"""
GENTAHAX MCP — AI Eğitim Paketi Üretici (mr_berk edition)
=========================================================
AI_EGITIM.md (TR) + AI_TRAINING.md (EN) üretir — YALNIZ GERÇEK veri dosyalarından:

  • Her fonksiyon imzası  → data/api_android.json + data/api_windows.json
  • Her item ID           → data/items.json (6832 eşya, items.dat tabanlı)
  • Hata tablosu          → autotest.py ERROR_PATTERNS (oyun executor'ı formatı)
  • Cheat kodları         → data/structs_hooks_enums.json (CheatCode enum)
  • Ban kuralları         → data/ban_rules.json

Bu dosyayı elle DÜZENLEME — değişiklik gerekirse yeniden üret:
    python scripts/gen_training_pack.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import knowledge as K          # noqa: E402
import autotest as AT          # noqa: E402

VERSION = "1.5.0"
WATERMARK = "mr_berk"

# Eğitim paketinde yer alacak sık kullanılan eşyalar — SADECE gerçek DB'den çözülenler girer
COMMON_ITEM_NAMES = [
    "Dirt", "Rock", "Cave Background", "Bedrock", "Door", "Main Door", "Sign",
    "Grass", "Lava", "Cave Dirt", "Pepper", "Pepper Tree", "Wooden Block",
    "Wood Block", "Wooden Background", "Checkpoint", "Bouncy Block", "White Block",
    "Dirt Seed", "Rock Seed", "Pepper Seed", "Gems", "World Lock",
    "Diamond Lock", "Blue Gem Lock", "Growtoken",
    "Chandelier", "Laser Grid", "High Tech Block", "Magic Bell",
    "Sugar Cane", "Steel Block", "Bathtub", "Fish Tank",
]


def _common_items():
    seen, out = set(), []
    for name in COMMON_ITEM_NAMES:
        r = K.item_resolve(name)
        if r.get("resolved") and r["id"] not in seen:
            seen.add(r["id"])
            out.append((r["id"], r["name"]))
    return sorted(out)


def _api_section(platform):
    api = K.get_api(platform)
    cats = {}
    for fn in api["functions"]:
        cats.setdefault(fn["category"], []).append(fn)
    lines = [f"### {platform.upper()} — {len(api['functions'])} fonksiyon "
             f"(kaynak: {api['source'][:90]}...)"]
    for cat in sorted(cats):
        lines.append(f"\n**{cat.upper()}**\n")
        for fn in cats[cat]:
            risk = fn.get("risk", "?")
            lines.append(f"- `{fn['signature']}` — risk: {risk}")
            if fn.get("description"):
                lines.append(f"  {fn['description'][:150]}")
    return "\n".join(lines)


def _cheats_section():
    e = K.get_enums()["CheatCode"]
    lines = ["| Kod | Mod |", "|---|---|"]
    for code in sorted(int(k) for k in e):
        lines.append(f"| {code} | {e[str(code)]} |")
    mp = K.get_enums()["MemoryPatchNames"]
    lines.append(f"\nBellek yaması isimleri (patchMemoryByName/restoreMemoryByName): "
                 f"{', '.join(mp['names'])}")
    return "\n".join(lines)


def _error_table():
    seen, rows = set(), []
    for cls, pat, desc in AT.ERROR_PATTERNS:
        if cls in seen:
            continue
        seen.add(cls)
        fix = AT.suggest_fix({"sinif": cls, "hedef": None})
        rows.append((cls, desc, fix["cozum"][:110]))
    # parse_execution'ın özel durum kodları da öğretilir (executor dönüş formatı)
    for cls, desc in (("NOT_IN_WORLD", "Executor 'ERR|NO_WORLD' döndü — dünyada değilsin"),
                      ("NO_LOCAL", "Executor 'ERR|NO_LOCAL' döndü — oyuncu henüz yüklenmedi")):
        fix = AT.suggest_fix({"sinif": cls, "hedef": None})
        rows.append((cls, desc, fix["cozum"][:110]))
    out = ["| Hata sınıfı | Executor logda nasıl görünür / neden | Ne yapılır |", "|---|---|---|"]
    for cls, desc, fix in rows:
        out.append(f"| {cls} | {desc} | {fix} |")
    return "\n".join(out)


def _ban_rules_section(limit=12):
    br = K.get_ban_rules()
    out = []
    for r in br["rules"][:limit]:
        out.append(f"- **[{r['level'].upper()}] {r['title']}** — {r['advice'][:120]}")
    return "\n".join(out)


def _items_section():
    rows = ["| Eşya | ID |", "|---|---|"]
    for iid, name in _common_items():
        rows.append(f"| {name} | {iid} |")
    return "\n".join(rows)


def build_pack(lang="tr"):
    """Eğitim paketi metnini üretir (lang: 'tr' | 'en')."""
    items = _items_section()
    cheats = _cheats_section()
    errors = _error_table()
    bans = _ban_rules_section()
    android_api = _api_section("android")
    windows_api = _api_section("windows")
    n_items = K.items_count()

    if lang == "tr":
        return f"""# GENTAHAX AI EĞİTİM PAKETİ — {WATERMARK} edition v{VERSION}

> **Bu paketi herhangi bir sohbet AI'na (ChatGPT, Claude, Gemini, GLM, DeepSeek...) yapıştır —
> o AI bu kurallarla GEÇERLİ GENTAHAX scripti yazar.** Paketin tamamı GERÇEK verilerden
> üretilmiştir: GENTAHAX v5.61 resmi dokümantasyon + Resmi Discord paylaşımları + DLL binary doğrulaması +
> items.dat tabanlı {n_items} eşyalık veritabanı. İçinde TEK BİR uydurma fonksiyon/ID yoktur.

## 0) Nasıl Kullanılır
- **ChatGPT / Gemini / Claude (MCP ile):** `python start_mcp.py` çalıştır → çıkan `https://xxxx.trycloudflare.com/mcp` adresini bağla → AI canlı dünyanı görür, script yazar ve test eder.
- **ChatGPT / Claude (API'siz / MCP'siz):** yeni sohbet aç → bu dosyanın TAMAMINI ilk mesaj olarak yapıştır
  (veya Custom GPT / Project Knowledge'a koy) → sonra iste: *"dünyadaki pepperları kır"*
- Çıkan scripti GENTAHAX **Script** klasörüne kaydet → oyun içinde **Lua Executor** ile çalıştır
- MCP bağlıysa: AI `gh_script_gen` ile üretir, `gh_auto_test` ile **çalıştırır, logları okur ve sana '✅ ÇALIŞIYOR' ya da hatayı söyler**

## 1) 7 Altın Kural (+ 2 Ek ZORUNLU Kural)
1. **SADECE** aşağıdaki API listesindeki fonksiyonları kullan — **UYDURMA**. Emin değilsen
   üretme, kullanıcıya sor. ('getPlayerList' YANLIŞ → 'getPlayerlist' DOĞRU gibi.)
2. Item ID'lerini **ASLA tahmin etme** — tablodan al ya da script içinde
   `getItemByName('X').id` ile canlı çöz.
3. Her döngüye `sleep(math.random(200, 600))` **KOY** — yoksa istemci kilitlenir + ban riski.
4. `getWorld()` / `getLocal()` dönmüş mü kontrol et:
   `local w = getWorld() if not w then return 'ERR|NO_WORLD' end`
5. Paket gönderen her döngü ban risklidir — kullanıcıya açıkça **"⚠️ BUNDA BAN RİSKİ VAR"** de.
6. Arka plan işini `runThread(fn, 'etiket')` ile yap, `killThread('etiket')` ile durdurulabilir olsun.
7. Otomatik test işaretleri: başta `doLog('AUTOTEST|START|...')`, bitişte `doLog('AUTOTEST|OK|...')`
8. **VARSAYILAN IMGUI ARAYÜZÜ:** Kullanıcı açıkça *"ImGui olmasın / menüsüz olsun"* demedikçe, ürettiğin **HER scriptte varsayılan olarak `AddHook('OnRender', ...)` ile bir ImGui kontrol penceresi (`ImGui.Begin` / `ImGui.End`)** bulunsun (Durdur/Başlat butonu, durum bilgisi vb.).
9. **GROWTOPIA KARAKTER KURALI (TÜRKÇE KARAKTER YOK):** Growtopia'nın oyun içi fontunda Türkçe karakterler (`ğ, ü, ş, ı, ö, ç, İ, Ğ, Ü, Ş, Ö, Ç`) **YOKTUR** ve bozuk görünür! Oyun içinde görünen metinlerde (`ImGui`, `logToConsole`, `doToast`, `sendPacket`, `sendVariant`) **ASLA Türkçe karakter kullanma**; her zaman ASCII karşılıklarını (`g, u, s, i, o, c, I`) yaz (ör. `'Baslat'`, `'Koyulan'`, `'Calisiyor'`). Kullanıcıyla sohbet ederken düzgün Türkçe konuşmaya devam et.
10. **ZORUNLU REPO AÇIKLAMA SATIRI & IMGUI WATERMARK:** Ürettiğin **HER Lua scriptinin** en başına mutlaka şu açıklama satırını ekle:
    `-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp`
    Ayrıca ImGui olan her şeyde, GUI'yi bozmayacak bir yere (`ImGui.End()` hemen öncesine) mutlaka `ImGui.Separator()` ve `ImGui.TextUnformatted('By BrK | Discord : mr_berk.')` watermark satırını ekle!

## 2) Otomatik Test Döngüsü (AI'nın standart iş akışı)
```
1) scripti yaz (9 altın kurala uy, ImGui panel ekle, oyun içi stringlerde ASCII kullan)
2) GENTAHAX executor'ında ÇALIŞTIR (MCP: gh_auto_test)
3) lua_logs.txt'yi OKU
4a) AUTOTEST|OK / FARM_RESULT / hatasız ilerleme → kullanıcıya "✅ ÇALIŞIYOR" de
4b) hata satırı → HATA TABLOSU'ndan teşhis et → düzelt → TEKRAR çalıştır (en fazla 2 kez)
   → hâlâ hatalıysa: hatayı + denediğin düzeltmeleri kullanıcıya dürüstçe anlat
```
**KRİTİK:** ÇALIŞIYOR/HATA kararı **YALNIZCA oyunun executor'ından ve loglarından** gelir.
Herhangi bir dış Lua editörü/coding app oyun fonksiyonlarını tanımaz — "fonksiyon yok"
sanıp doğru kodu yanlış düzeltme! Söz dizimi kontrolü (derleme) çalıştırmaz ve oyun
fonksiyonlarından false hata VERMEZ; varlık kontrolü tek yetkili kaynak executor'dır.

## 3) Hata Tablosu (GENTAHAX executor'ının lua_logs.txt formatı)
{errors}

## 4) ANDROID Lua API — GERÇEK (DLL v5.61 + Resmi Discord doğrulamalı)
{android_api}

## 5) WINDOWS Lua API — GERÇEK
{windows_api}

## 6) Sık Kullanılan GERÇEK Item ID'leri
{items}

Tam {n_items} eşyalık veritabanı MCP'dedir (`gh_item_db_search`). Buradaki liste sık
kullanılanlardır; olmayanı **tahmin etme** — kullanıcıya sor veya canlı çöz.

## 7) Hazır Modlar (GENTAHAX'ta zaten VAR OLANLAR — script yazmadan kullan)
`toggleCheat(kod, true/false)` açar/kapar, `getCheat(kod)` okur. MCP'de: `gh_cheat_set('Mod Fly', true)`

{cheats}

## 8) Doğrulanmış Kod Kalıpları (Resmi Discord + GENTA-HAX-DOCS)

**1. ImGui Kontrol Paneli + `runThread` Tetikleme (Varsayılan Şablon):**
```lua
-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp
-- By BrK | Discord : mr_berk.
local calisiyor = false
AddHook('OnRender', 'mr_berk_ui', function(dt)
  ImGui.Begin('mr_berk Kontrol Paneli')
  ImGui.TextUnformatted('Durum: ' .. (calisiyor and 'AKTIF' or 'BEKLEMEDE'))
  if ImGui.Button('Baslat') and not calisiyor then
    calisiyor = true
    runThread(function()
      while calisiyor do
        sleep(math.random(400, 900))
      end
    end, 'ana_is')
  end
  ImGui.SameLine()
  if ImGui.Button('Durdur') then
    calisiyor = false
    killThread('ana_is')
  end
  ImGui.Separator()
  ImGui.TextUnformatted('By BrK | Discord : mr_berk.')
  ImGui.End()
end)
```

**2. Better PNB (`requestTileChange` + `requestCollectByRange`):**
```lua
local id = 340 -- Chandelier=340, Laser Grid=5666, Pepper Tree=4584, High Tech Block=324, Magic Bell=5990
local XCoords = 2
local YCoords = -1
runThread(function()
  while true do
    sleep(180)
    requestCollectByRange(4)
    sleep(500)
    local me = getLocal()
    if me then
      local px, py = me.pos.x // 32, me.pos.y // 32
      for ox = -XCoords, XCoords do
        local c = checkTile(px + ox, py + YCoords)
        if c ~= nil and c.fg == 0 then
          requestTileChange(c.pos.x, c.pos.y, id)
          sleep(200)
        end
      end
      sleep(200)
      for ox = -XCoords, XCoords do
        local tries = 0
        local c = checkTile(px + ox, py + YCoords)
        while c ~= nil and c.fg ~= 0 and tries < 10 do
          requestTileChange(c.pos.x, c.pos.y, 18)
          sleep(180)
          c = checkTile(c.pos.x, c.pos.y)
          tries = tries + 1
        end
      end
    end
  end
end, 'better_pnb')
```

**3. `setTile(x, y, Tile*)` ile İstemci Tarafı (Görsel) Tile & Flag Değiştirme:**
```lua
local me = getLocal()
if me then
  setTile(me.pos.x // 32, (me.pos.y // 32) + 1, {{
    fg = 8,
    bg = 14,
    setFlags = {{
      tileExtra = false,
      locked = false,
      wasSpliced = false,
      willSpawnSeedToo = false,
      flipped = false,
      enabled = false,
      public = false,
      silenced = false,
      water = true,
      glue = false,
      burn = false,
      red = true,
      green = false,
      blue = false
    }}
  }})
end
```

**4. `ImGui.FG:AddLine` ile Hazır Ağaç & NPC ESP Çizimi (`worldToScreen`):**
```lua
AddHook('OnRender', 'esp_line', function(delta)
  local p_local = getLocal()
  if not p_local then return end
  local _p = worldToScreen(p_local.pos.x, p_local.pos.y)
  for _, v in pairs(getTile()) do
    local _e = getExtraTile(v.pos.x, v.pos.y)
    if _e.valid == true and _e.ready == true then
      if _e.type == 4 or _e.type == 9 then
        local _b = worldToScreen(v.pos.x * 32, v.pos.y * 32)
        ImGui.FG:AddLine(_p, _b, 0xFFFFFFFF, 1.0)
      end
    end
  end
  for _, n in pairs(getNpc()) do
    local _n = worldToScreen(n.current.x, n.current.y)
    ImGui.FG:AddLine(_p, _n, 0xFF00FF00, 2.0)
  end
  collectgarbage('collect')
end)
```

**5. `getTile()` & `getExtraTile(x, y).label` Okuma:**
```lua
for _, i in pairs(getTile()) do
  if getExtraTile(i.pos.x, i.pos.y).valid == true then
    doLog('Label: ' .. tostring(getExtraTile(i.pos.x, i.pos.y).label))
  end
end
```

**6. `Json.encode` / `Json.decode` ve `runParallel`:**
```lua
local str = Json.encode({{ name = 'Genta', cool = true, age = 21, hobbies = {{ 'coding', 'modding' }} }})
logToConsole(str)
local data = Json.decode(str)
logToConsole(tostring(data.name))

-- runParallel: ayni oyun tick'inde paralel calistirir (ASLA sonsuz dongu koyma!)
local results = runParallel({{
  function() return 1 + 1 end,
  function() return 'done' end
}})
logToConsole(tostring(results[1]) .. ' / ' .. tostring(results[2]))
```

**7. VPN'siz GTPS Bağlantısı (`OnENetInit` + `setENetInformation`):**
```lua
AddHook('OnENetInit', 'gtps_redirect', function(ip, port)
  logToConsole('IP: ' .. tostring(ip) .. ' Port: ' .. tostring(port))
  setENetInformation('127.0.0.1', 17091)
  return true -- Yeni ENet bilgisini kullanmak icin true dondur!
end)
```

**8. Tüm `AddHook` Türleri ve Paket Engelleme (`return true`):**
```lua
-- OnVarlist: true dondurursen varlist istemci tarafindan islenmez (bloklanir)
AddHook('onvarlist', 'vl_hook', function(vlist, netid)
  logToConsole('VAR [1]: ' .. tostring(vlist[1]))
  return false
end)

-- OnGameUpdatePacket: true dondurursen gelen update paketi bloklanir
AddHook('ongameupdatepacket', 'gup_hook', function(raw)
  logToConsole('Packet Type: ' .. tostring(raw.type))
  return false
end)

-- OnRawPacket: true dondurursen giden raw paket bloklanir
AddHook('onrawpacket', 'raw_hook', function(raw)
  logToConsole('Raw Type: ' .. tostring(raw.type))
  return false
end)

-- OnTouch ve OnTextPacket
AddHook('ontouch', 'touch_hook', function(x, y)
  logToConsole('Touch X: ' .. tostring(x) .. ' Y: ' .. tostring(y))
end)
AddHook('ontextpacket', 'txt_hook', function(pkt)
  logToConsole('Packet: ' .. tostring(pkt))
end)
-- UYARI: OnRender icinde ASLA logToConsole kullanma (FPS cokertir); gerekirse doLog kullan!
```

**9. Discord Webhook Gönderimi (`sendWebhook`) ve Uzaktan Extender Yükleme (`makeRequest`):**
```lua
local Webhook = {{
  username = 'mr_berk Webhook',
  content = 'Bildirim mesaji - ASCII',
  useEmbeds = true,
  embeds = {{ {{ title = 'Rapor', description = 'Islem tamamlandi', color = 15258703 }} }}
}}
sendWebhook('https://discord.com/api/webhooks/ID/TOKEN', Webhook)

-- Uzaktan script calistirma (Windows + Android uyumlu):
load(makeRequest('https://raw.githubusercontent.com/GENTA7740/GENTA-HAX-DOCS/refs/heads/main/example/ImGui/extender.lua', 'GET').content)()
```

**10. GFuscator `#region _EXPOSED_` Direktifi & Custom Shaders:**
- **GFuscator:** Script şifrelenirken açık metin (düzenlenebilir) kalmasını istediğin ayar bloğunu `#region _EXPOSED_` ve `#endregion` arasına al (Not: Raw Lua modunda çalışmaz, sadece GFuscator içindir).
- **Custom Shaders:** Özel GLSL shader dosyalarını (`main.vert` ve `main.frag`) Android'de `/android/media/GENTAHAX/Shaders/` klasörüne koy (`gh_example_get('main.vert')` ve `gh_example_get('main.frag')` ile Fake Chams örneğini alabilirsin).

## 9) Ban Riski Kuralları (ilk 12)
{bans}

## 10) Kendini Test Et
1. 'getPlayerList' mi doğru yoksa 'getPlayerlist' mi? → **getPlayerlist**
2. Pepper'nun ID'si kaç? (tahmin DEĞİL, tablodan) → **4570**
3. Sonsuz döngüde ne şart? → **sleep (rastgele 200-600ms)**
4. Bir modu açmanın script yazmadan yolu? → **toggleCheat(26, true) / gh_cheat_set('Mod Fly', true)**
5. Çalışıp çalışmadığına kim karar verir? → **SADECE oyunun executor'ı + lua_logs.txt**
6. Oyun içi metinlerde (`ImGui`, `logToConsole`, `doToast`) Türkçe karakter (`ğ, ü, ş, ı, ö, ç, İ`) kullanılır mı? → **HAYIR, sadece ASCII (`g, u, s, i, o, c, I`)**
7. Kullanıcı aksini belirtmedikçe her scriptte hangi arayüz olmalı? → **`OnRender` + `ImGui.Begin` kontrol paneli**

## 11) {WATERMARK}
GENTAHAX MCP v{VERSION} — Gerçek verilerle eğitildi · Ban riski uyarı sistemli · 45 araç
"""
    return f"""# GENTAHAX AI TRAINING PACK — {WATERMARK} edition v{VERSION}

> **Paste this pack into ANY chat AI (ChatGPT, Claude, Gemini, GLM, DeepSeek...) and it
> will write VALID GENTAHAX scripts.** Everything below is generated from REAL data:
> official GENTAHAX v5.61 docs + Official Discord snippets + DLL binary verification + the {n_items}-item items.dat
> database. There is NOT a single invented function or ID in this pack.

## 0) How to Use
- **ChatGPT / Gemini / Claude (with MCP):** run `python start_mcp.py` → connect the printed `https://xxxx.trycloudflare.com/mcp` URL → the AI sees your live world, writes scripts, and tests them automatically.
- **ChatGPT / Claude (no API / no MCP):** open a new chat → paste this WHOLE file as the first message
  (or put it into a Custom GPT / Project Knowledge) → then ask: *"break all the peppers in the world"*
- Save the produced script into the GENTAHAX **Script** folder → run it with the in-game **Lua Executor**
- With the MCP connected, the AI generates via `gh_script_gen`, then `gh_auto_test`
  **runs it, reads the logs and tells you '✅ IT WORKS' or the exact error**

## 1) 7 Golden Rules (+ 2 Mandatory Rules)
1. Use ONLY the functions listed below — **NEVER invent**. ('getPlayerList' WRONG → 'getPlayerlist' RIGHT.)
2. NEVER guess item IDs — take them from the table or resolve live via `getItemByName('X').id`.
3. Every loop MUST `sleep(math.random(200, 600))` — otherwise the client freezes + ban risk.
4. Guard the game objects: `local w = getWorld() if not w then return 'ERR|NO_WORLD' end`
5. Any packet-sending loop is ban-risky — tell the user **"⚠️ THIS HAS BAN RISK"** explicitly.
6. Do background work in `runThread(fn, 'tag')` and make it stoppable with `killThread('tag')`.
7. Auto-test markers: `doLog('AUTOTEST|START|...')` at start, `doLog('AUTOTEST|OK|...')` at end.
8. **IMGUI UI BY DEFAULT:** Unless the user explicitly asks for *"no ImGui / headless"*, **EVERY script you generate MUST include an `OnRender` ImGui control window (`ImGui.Begin` / `ImGui.End`)** with status info and Start/Stop buttons.
9. **GROWTOPIA ASCII-ONLY RULE (NO TURKISH CHARACTERS IN-GAME):** Growtopia's in-game font does NOT support Turkish characters (`ğ, ü, ş, ı, ö, ç, İ, Ğ, Ü, Ş, Ö, Ç`) and renders them as garbage. NEVER use Turkish characters inside in-game Lua strings (`ImGui`, `logToConsole`, `doToast`, `sendPacket`, `sendVariant`); always use ASCII equivalents (`g, u, s, i, o, c, I`).
10. **MANDATORY REPO COMMENT & IMGUI WATERMARK:** At the very top of **EVERY Lua script** you generate, ALWAYS include:
    `-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp`
    And in EVERY ImGui window (right before `ImGui.End()`, without breaking the GUI layout), ALWAYS include:
    `ImGui.Separator()` and `ImGui.TextUnformatted('By BrK | Discord : mr_berk.')`!

## 2) Auto-Test Loop (the AI's standard workflow)
```
1) write the script (follow the 9 golden rules, include ImGui panel, use ASCII in-game strings)
2) RUN it in the GENTAHAX executor (MCP: gh_auto_test)
3) READ lua_logs.txt
4a) AUTOTEST|OK / FARM_RESULT / error-free progress → tell the user "✅ IT WORKS"
4b) error line → diagnose via the ERROR TABLE → fix → RUN AGAIN (max 2 retries)
   → still failing? honestly explain the error and what you tried
```
**CRITICAL:** the WORKS/ERROR verdict comes ONLY from the game's own executor and its logs.
Any external Lua editor does NOT know the in-game functions — never "fix" correct code
because an outside tool said the function is missing! A syntax (compile) check never
executes the code and CANNOT produce false errors on game functions; the only authority
on function existence is the executor itself.

## 3) Error Table (GENTAHAX executor lua_logs.txt format)
{errors}

## 4) ANDROID Lua API — REAL (DLL v5.61 + Official Discord verified)
{android_api}

## 5) WINDOWS Lua API — REAL
{windows_api}

## 6) Common REAL Item IDs
{items}

The full {n_items}-item database lives in the MCP (`gh_item_db_search`). If an item is
not in this list, do NOT guess — ask the user or resolve live.

## 7) Built-in Mods (already IN GENTAHAX — no script needed)
`toggleCheat(code, true/false)` toggles, `getCheat(code)` reads. In MCP: `gh_cheat_set('Mod Fly', true)`

{cheats}

## 8) Verified Code Patterns (Official Discord + GENTA-HAX-DOCS)

**1. ImGui Control Panel + `runThread` Trigger (Default Pattern):**
```lua
-- Made by Berk (GentaHAX-MCP repo) -> https://github.com/BrK08/gentahax-mcp
-- By BrK | Discord : mr_berk.
local running = false
AddHook('OnRender', 'mr_berk_ui', function(dt)
  ImGui.Begin('mr_berk Control Panel')
  ImGui.TextUnformatted('Status: ' .. (running and 'ACTIVE' or 'IDLE'))
  if ImGui.Button('Start') and not running then
    running = true
    runThread(function()
      while running do
        sleep(math.random(400, 900))
      end
    end, 'main_job')
  end
  ImGui.SameLine()
  if ImGui.Button('Stop') then
    running = false
    killThread('main_job')
  end
  ImGui.Separator()
  ImGui.TextUnformatted('By BrK | Discord : mr_berk.')
  ImGui.End()
end)
```

**2. Better PNB (`requestTileChange` + `requestCollectByRange`):**
```lua
local id = 340 -- Chandelier=340, Laser Grid=5666, Pepper Tree=4584, High Tech Block=324, Magic Bell=5990
local XCoords = 2
local YCoords = -1
runThread(function()
  while true do
    sleep(180)
    requestCollectByRange(4)
    sleep(500)
    local me = getLocal()
    if me then
      local px, py = me.pos.x // 32, me.pos.y // 32
      for ox = -XCoords, XCoords do
        local c = checkTile(px + ox, py + YCoords)
        if c ~= nil and c.fg == 0 then
          requestTileChange(c.pos.x, c.pos.y, id)
          sleep(200)
        end
      end
      sleep(200)
      for ox = -XCoords, XCoords do
        local tries = 0
        local c = checkTile(px + ox, py + YCoords)
        while c ~= nil and c.fg ~= 0 and tries < 10 do
          requestTileChange(c.pos.x, c.pos.y, 18)
          sleep(180)
          c = checkTile(c.pos.x, c.pos.y)
          tries = tries + 1
        end
      end
    end
  end
end, 'better_pnb')
```

**3. Client-Side `setTile(x, y, Tile*)` with `setFlags`:**
```lua
local me = getLocal()
if me then
  setTile(me.pos.x // 32, (me.pos.y // 32) + 1, {{
    fg = 8,
    bg = 14,
    setFlags = {{
      tileExtra = false,
      locked = false,
      wasSpliced = false,
      willSpawnSeedToo = false,
      flipped = false,
      enabled = false,
      public = false,
      silenced = false,
      water = true,
      glue = false,
      burn = false,
      red = true,
      green = false,
      blue = false
    }}
  }})
end
```

**4. `ImGui.FG:AddLine` Tree & NPC ESP (`worldToScreen`):**
```lua
AddHook('OnRender', 'esp_line', function(delta)
  local p_local = getLocal()
  if not p_local then return end
  local _p = worldToScreen(p_local.pos.x, p_local.pos.y)
  for _, v in pairs(getTile()) do
    local _e = getExtraTile(v.pos.x, v.pos.y)
    if _e.valid == true and _e.ready == true then
      if _e.type == 4 or _e.type == 9 then
        local _b = worldToScreen(v.pos.x * 32, v.pos.y * 32)
        ImGui.FG:AddLine(_p, _b, 0xFFFFFFFF, 1.0)
      end
    end
  end
  for _, n in pairs(getNpc()) do
    local _n = worldToScreen(n.current.x, n.current.y)
    ImGui.FG:AddLine(_p, _n, 0xFF00FF00, 2.0)
  end
  collectgarbage('collect')
end)
```

**5. `Json.encode` / `Json.decode`, `runParallel`, and GTPS Redirect (`OnENetInit`):**
```lua
local str = Json.encode({{ name = 'Genta', cool = true, age = 21 }})
local data = Json.decode(str)
logToConsole(tostring(data.name))

local results = runParallel({{
  function() return 1 + 1 end,
  function() return 'done' end
}})
logToConsole(tostring(results[1]))

AddHook('OnENetInit', 'gtps_redirect', function(ip, port)
  setENetInformation('127.0.0.1', 17091)
  return true
end)
```

## 9) Ban Risk Rules (first 12)
{bans}

## 10) Test Yourself
1. 'getPlayerList' or 'getPlayerlist'? → **getPlayerlist**
2. Pepper's ID? (from the table, not a guess) → **4570**
3. What is mandatory in infinite loops? → **sleep (random 200-600ms)**
4. How to enable a mod without writing a script? → **toggleCheat(26, true) / gh_cheat_set('Mod Fly', true)**
5. Who decides whether a script works? → **ONLY the game executor + lua_logs.txt**
6. Are Turkish characters (`ğ, ü, ş, ı, ö, ç, İ`) allowed in in-game strings? → **NO, ASCII only (`g, u, s, i, o, c, I`)**
7. What UI must be included by default unless told otherwise? → **`OnRender` + `ImGui.Begin` control panel**

## 11) {WATERMARK}
GENTAHAX MCP v{VERSION} — Trained on real data · Ban-risk warning system · 45 tools
"""


def main():
    tr = ROOT / "AI_EGITIM.md"
    en = ROOT / "AI_TRAINING.md"
    tr.write_text(build_pack("tr"), encoding="utf-8")
    en.write_text(build_pack("en"), encoding="utf-8")
    print(f"OK {tr} ({tr.stat().st_size:,} bayt)")
    print(f"OK {en} ({en.stat().st_size:,} bayt)")
    print(f"   Uretim: yalniz GERCEK veri dosyalari — {K.items_count()} esya, "
          f"{len(K.api_names('android'))}+{len(K.api_names('windows'))} API fonksiyonu")


if __name__ == "__main__":
    main()
