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
> üretilmiştir: GENTAHAX v5.61 resmi dokümantasyon + DLL binary doğrulaması +
> items.dat tabanlı {n_items} eşyalık veritabanı. İçinde TEK BİR uydurma fonksiyon/ID yoktur.

## 0) Nasıl Kullanılır
- **ChatGPT (API'siz):** yeni sohbet aç → bu dosyanın TAMAMINI ilk mesaj olarak yapıştır
  (veya Custom GPT → Instructions'a koy) → sonra iste: *"dünyadaki pepperları kır"*
- **Claude:** Project → Knowledge'a yükle ya da sohbet başına yapıştır
- Çıkan scripti GENTAHAX **Script** klasörüne kaydet → oyun içinde **Lua Executor** ile çalıştır
- MCP bağlıysa (chat.py / Claude Desktop / uygulama): AI `gh_script_gen` ile üretir,
  `gh_auto_test` ile **çalıştırır, logları okur ve sana '✅ ÇALIŞIYOR' ya da hatayı söyler**

## 1) 7 Altın Kural
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

## 2) Otomatik Test Döngüsü (AI'nın standart iş akışı)
```
1) scripti yaz (kurallara uy)
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

## 4) ANDROID Lua API — GERÇEK (DLL v5.61 doğrulamalı)
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

## 8) Doğrulanmış Kod Kalıpları

**Thread + insan benzeri delay:**
```lua
runThread(function()
  while true do
    sleep(math.random(400, 1200))
    -- iş
  end
end, 'benim_etiket')   -- durdur: killThread('benim_etiket')
```

**Dünya tarama + blok kırma (punch):**
```lua
local w = getWorld()
if not w then return 'ERR|NO_WORLD' end
for _, t in pairs(getTile()) do
  if t and t.fg == 4570 and t.pos then  -- 4570 = Pepper (gerçek ID)
    sendPacketRaw(false, {{ type = 3, state = 16, value = 18,
                           x = t.pos.x, y = t.pos.y, punchx = t.pos.x, punchy = t.pos.y }})
    sleep(math.random(450, 1200))
  end
end
```

**Yerdeki eşya toplama (resmi yardımcı — punch'tan güvenli):**
```lua
for _, obj in pairs(getWorldObject()) do
  requestCollect(obj.pos.x, obj.pos.y, obj.id)
  sleep(math.random(200, 500))
end
```

**Sohbet dinleme (hook):**
```lua
AddHook('OnVarlist', 'chat', function(vars, netid)
  if vars[0] == 'OnTalkBubble' then
    logToConsole('[Sohbet] ' .. tostring(vars[2]))
  end
end)
```

**Gems okuma (NetAvatar alanı — gerçek struct):**
```lua
local me = getLocal()
if me then logToConsole('Gems: ' .. tostring(me.gems)) end
```

## 9) Ban Riski Kuralları (ilk 12)
{bans}

## 10) Kendini Test Et
1. 'getPlayerList' mi doğru yoksa 'getPlayerlist' mi? → **getPlayerlist**
2. Pepper'nun ID'si kaç? (tahmin DEĞİL, tablodan) → **4570**
3. Sonsuz döngüde ne şart? → **sleep (rastgele 200-600ms)**
4. Bir modu açmanın script yazmadan yolu? → **toggleCheat(26, true) / gh_cheat_set('Mod Fly', true)**
5. Çalışıp çalışmadığına kim karar verir? → **SADECE oyunun executor'ı + lua_logs.txt**

## 11) {WATERMARK}
GENTAHAX MCP v{VERSION} — Gerçek verilerle eğitildi · Ban riski uyarı sistemli · 45 araç
"""
    return f"""# GENTAHAX AI TRAINING PACK — {WATERMARK} edition v{VERSION}

> **Paste this pack into ANY chat AI (ChatGPT, Claude, Gemini, GLM, DeepSeek...) and it
> will write VALID GENTAHAX scripts.** Everything below is generated from REAL data:
> official GENTAHAX v5.61 docs + DLL binary verification + the {n_items}-item items.dat
> database. There is NOT a single invented function or ID in this pack.

## 0) How to Use
- **ChatGPT (no API):** open a new chat → paste this WHOLE file as the first message
  (or put it into a Custom GPT's Instructions) → then ask: *"break all the peppers in the world"*
- **Claude:** upload to Project Knowledge or paste at the start of a chat
- Save the produced script into the GENTAHAX **Script** folder → run it with the in-game **Lua Executor**
- With the MCP connected, the AI generates via `gh_script_gen`, then `gh_auto_test`
  **runs it, reads the logs and tells you '✅ IT WORKS' or the exact error**

## 1) 7 Golden Rules
1. Use ONLY the functions listed below — **NEVER invent**. ('getPlayerList' WRONG → 'getPlayerlist' RIGHT.)
2. NEVER guess item IDs — take them from the table or resolve live via `getItemByName('X').id`.
3. Every loop MUST `sleep(math.random(200, 600))` — otherwise the client freezes + ban risk.
4. Guard the game objects: `local w = getWorld() if not w then return 'ERR|NO_WORLD' end`
5. Any packet-sending loop is ban-risky — tell the user **"⚠️ THIS HAS BAN RISK"** explicitly.
6. Do background work in `runThread(fn, 'tag')` and make it stoppable with `killThread('tag')`.
7. Auto-test markers: `doLog('AUTOTEST|START|...')` at start, `doLog('AUTOTEST|OK|...')` at end.

## 2) Auto-Test Loop (the AI's standard workflow)
```
1) write the script (following the rules)
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

## 4) ANDROID Lua API — REAL (DLL v5.61 verified)
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

## 8) Verified Code Patterns

**Thread + human-like delay:**
```lua
runThread(function()
  while true do
    sleep(math.random(400, 1200))
    -- work
  end
end, 'my_tag')   -- stop: killThread('my_tag')
```

**World scan + block punch:**
```lua
local w = getWorld()
if not w then return 'ERR|NO_WORLD' end
for _, t in pairs(getTile()) do
  if t and t.fg == 4570 and t.pos then  -- 4570 = Pepper (real ID)
    sendPacketRaw(false, {{ type = 3, state = 16, value = 18,
                           x = t.pos.x, y = t.pos.y, punchx = t.pos.x, punchy = t.pos.y }})
    sleep(math.random(450, 1200))
  end
end
```

**Collecting dropped items (official helper — safer than punching):**
```lua
for _, obj in pairs(getWorldObject()) do
  requestCollect(obj.pos.x, obj.pos.y, obj.id)
  sleep(math.random(200, 500))
end
```

**Chat listening (hook):**
```lua
AddHook('OnVarlist', 'chat', function(vars, netid)
  if vars[0] == 'OnTalkBubble' then
    logToConsole('[Chat] ' .. tostring(vars[2]))
  end
end)
```

**Reading gems (NetAvatar field — real struct):**
```lua
local me = getLocal()
if me then logToConsole('Gems: ' .. tostring(me.gems)) end
```

## 9) Ban Risk Rules (first 12)
{bans}

## 10) Test Yourself
1. 'getPlayerList' or 'getPlayerlist'? → **getPlayerlist**
2. Pepper's ID? (from the table, not a guess) → **4570**
3. What is mandatory in infinite loops? → **sleep (random 200-600ms)**
4. How to enable a mod without writing a script? → **toggleCheat(26, true) / gh_cheat_set('Mod Fly', true)**
5. Who decides whether a script works? → **ONLY the game executor + lua_logs.txt**

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
