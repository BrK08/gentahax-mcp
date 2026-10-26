#!/usr/bin/env python3
"""
'Kac tane dirt var?' UC TAN UCA GERCEKLIK TESTI — mr_berk
=========================================================
Kullanici sorusu: "AI'ya 'dunyada kac tane dirt var' diye sorunca gercek ve dogru
cevap veriyor mu?"  Bu test 3 katmani kanitlar:

  KATMAN 1 (Lua mantigi) : server.py'nin urettigi _WC_LUA kodu GERCEK Lua 5.x
                          runtime'inda (lupa) calisir; simule edilmis 100x60
                          dunyada (6000 tile, 214 fg Dirt + 50 bg Dirt) dogru sayar.
  KATMAN 2 (Kopru IPC)   : bridge_in.txt / bridge_out.txt dosya koprusu uzerinden
                          exec_lua() tam veri alisverisi yapar (sahte oyun responder'i ile).
  KATMAN 3 (MCP protokolu): Kullanici senaryosu birebir — Client gh_world_count_item('Dirt')
                          cagirir, arac cevabi JSON olarak doner: "264 adet Dirt".
"""
import asyncio
import json
import os
import sys
import tempfile
import threading
import time

import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

ok_count = 0
fail_count = 0

def check(name, cond, detail=""):
    global ok_count, fail_count
    if cond:
        ok_count += 1
        print(f"  ✅ {name}")
    else:
        fail_count += 1
        print(f"  ❌ {name}  {detail}")

# ---------------------------------------------------------------------------
# Simule edilmis dunya (lupa icinde GERCEK Lua tablolari)
# ---------------------------------------------------------------------------
import lupa
lua = lupa.LuaRuntime()

# Simulasyon parametreleri — beklenen kesin degerler:
W, H = 100, 60              # 6000 tile
FG_DIRT_EXPECT = 214        # on plan Dirt (ID 2)
BG_DIRT_EXPECT = 50         # arka plan Dirt (ID 2)
BG_BEDROCK_EXPECT = 6000 - BG_DIRT_EXPECT  # geri kalan arka plan Bedrock (ID 8)
FG_ROCK_EXPECT = 100        # on plan Rock (ID 10)

lua.execute("""
ID_NAMES = { [2]='Dirt', [3]='Dirt Seed', [8]='Bedrock', [10]='Rock', [16]='Grass', [0]='Blank' }
function getWorld() return { name = 'BUYDIRT', width = 100, height = 60 } end
function getItemByID(id) return { name = ID_NAMES[id] or '?', id = id } end
TILES = {}
for y = 0, 59 do
    for x = 0, 99 do
        TILES[#TILES + 1] = { pos = { x = x, y = y }, fg = 0, bg = 8 }
    end
end
-- on plan Dirt: ilk 214 tile
for i = 1, 214 do TILES[i].fg = 2 end
-- on plan Rock: sonraki 100 tile
for i = 215, 314 do TILES[i].fg = 10 end
-- arka plan Dirt: 50 tile (7,14,21,...350)
for i = 1, 50 do TILES[i * 7].bg = 2 end
function getTile() return TILES end
""")
print(f"Simülasyon dünyası: {W}x{H} = {W*H} tile")
print(f"Beklenen: Dirt fg={FG_DIRT_EXPECT}, bg={BG_DIRT_EXPECT} → toplam {FG_DIRT_EXPECT+BG_DIRT_EXPECT}")
print()

# ---------------------------------------------------------------------------
# KATMAN 1 — Lua mantık doğrulaması
# ---------------------------------------------------------------------------
print("=== KATMAN 1: LUA MANTIĞI (gerçek Lua runtime, lupa) ===")
import knowledge as K
import server as S  # _WC_LUA buradan gelir — aracın ÜRETTİĞİ kod test edilir

check("Dirt veritabanı çözümü: ID 2", K.item_resolve("Dirt") == {"resolved": True, "id": 2, "name": "Dirt"},
      str(K.item_resolve("Dirt")))

lua_code = S._WC_LUA.replace("{target_id}", "2").strip()
res1 = lua.execute(lua_code)
print(f"  Lua çıktı: {res1}")
check("Lua kodu hatasız çalıştı", isinstance(res1, str) and "WORLD:" in str(res1))
check("Dünya adı doğru", "WORLD:BUYDIRT" in str(res1))
check("Boyut doğru", "SIZE:100x60" in str(res1))
check("6000 tile tarandı", "SCANNED:6000" in str(res1), str(res1))
check(f"Ön plan Dirt = {FG_DIRT_EXPECT}", f"FG:{FG_DIRT_EXPECT}" in str(res1))
check(f"Arka plan Dirt = {BG_DIRT_EXPECT}", f"BG:{BG_DIRT_EXPECT}" in str(res1))
check(f"TOPLAM = {FG_DIRT_EXPECT+BG_DIRT_EXPECT}", f"TOTAL:{FG_DIRT_EXPECT+BG_DIRT_EXPECT}" in str(res1))
check("Canlı items.dat adı = Dirt (çapraz doğrulama)", "LIVE_NAME:Dirt" in str(res1))

# Katman 1 parse testi — aracın parse etmesiyle aynı mantık
parts = {}
for kv in str(res1).split("|"):
    if ":" in kv:
        k, v = kv.split(":", 1)
        parts[k] = v
check("Parse: FG/BG/TOPLAM doğru", int(parts["FG"]) == 214 and int(parts["BG"]) == 50 and int(parts["TOTAL"]) == 264)
check("Örnek konumlar geliyor", len(parts.get("SAMPLES", "").split(";")) >= 1)

# Sayım kodu ban riski — sadece okuma → DÜŞÜK olmalı
r = K.analyze_code(lua_code)
check("Sayım kodu ban riski: DÜŞÜK", r["risk_level"] == "low", f"= {r['risk_level']} ({r['risk_score']})")

# ---------------------------------------------------------------------------
# KATMAN 2 — Köprü IPC (bridge_in.txt → sahte oyun → bridge_out.txt)
# ---------------------------------------------------------------------------
print("\n=== KATMAN 2: KÖPRÜ IPC (dosya köprüsü uçtan uca) ===")
import bridge as B

tmpdir = tempfile.mkdtemp(prefix="gh_fake_game_")
os.environ["GENTAHAX_SCRIPT_DIR"] = tmpdir
import importlib
importlib.reload(B)  # ortam değişkeni sonrası taze yükle

IN_FILE = os.path.join(tmpdir, "bridge_in.txt")
OUT_FILE = os.path.join(tmpdir, "bridge_out.txt")

def fake_game_responder():
    """Sahte 'oyun': köprü thread'inin yaptığını yapar — bridge_in.txt okur,
    kodu lupa dünyasında ÇALIŞTIRIR, sonucu bridge_out.txt'ye yazar."""
    while not stop_flag.is_set():
        if os.path.exists(IN_FILE):
            try:
                content = open(IN_FILE, encoding="utf-8").read()
                os.remove(IN_FILE)
                head, code = content.split("\n", 1)
                cid, action = head.split("|", 1)
                if action.strip() == "EXEC":
                    result = lua.execute(code)
                    with open(OUT_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{cid}|OK|{result}\n")
            except Exception as e:
                try:
                    with open(OUT_FILE, "a", encoding="utf-8") as f:
                        f.write(f"0|ERR|{e}\n")
                except Exception:
                    pass
        time.sleep(0.05)

stop_flag = threading.Event()
th = threading.Thread(target=fake_game_responder, daemon=True)
th.start()

code_to_send = lua_code  # aracın göndereceği kod
result2 = B.exec_lua(code_to_send, timeout=10)
print(f"  IPC sonucu: {result2}")
check("exec_lua IPC üzerinden gerçek sayı döndü", f"FG:{FG_DIRT_EXPECT}" in str(result2) and f"TOTAL:{FG_DIRT_EXPECT+BG_DIRT_EXPECT}" in str(result2))
check("IPC sonucu Katman 1 ile birebir aynı", str(result2) == str(res1))

# ---------------------------------------------------------------------------
# KATMAN 3 — MCP protokolü: kullanıcı senaryosu birebir
# ---------------------------------------------------------------------------
print("\n=== KATMAN 3: MCP PROTOKOLÜ (kullanıcı senaryosu) ===")
from fastmcp import Client

def J(r):
    d = r.data
    return json.loads(d) if isinstance(d, str) else d

async def protocol_test():
    from server import mcp
    async with Client(mcp) as client:
        # Senaryo 1: "Dünyada kaç tane Dirt var?"
        r = J(await client.call_tool("gh_world_count_item", {"item": "Dirt"}))
        print("  gh_world_count_item('Dirt') cevabı:")
        print(f"    soru   : {r['soru']}")
        print(f"    cevap  : {r['cevap']}")
        print(f"    tarama : {r['taranan_tile']} tile | doğrulama: oyun={r['canli_dogrulama']['oyun_dedi']}, uyusuyor={r['canli_dogrulama']['uyusuyor']}")
        check("Cevap: 264 adet Dirt", "264 adet Dirt" in r["cevap"], r["cevap"])
        check("Ön plan 214, arka plan 50", r["on_plan_fg"] == 214 and r["arka_plan_bg"] == 50)
        check("Dünya: BUYDIRT 100x60", r["dunya"] == "BUYDIRT" and r["dunya_boyutu"] == "100x60")
        check("Taranan tile: 6000", r["taranan_tile"] == 6000)
        check("Canlı doğrulama uyumlu", r["canli_dogrulama"]["uyusuyor"] is True)
        check("Ban riski: YOK", "YOK" in r["ban_riski"])
        check("mr_berk filigranı", r["watermark"] == "mr_berk")

        # Senaryo 2: ID ile sorgulama — "kaç tane item 2 var"
        r = J(await client.call_tool("gh_world_count_item", {"item": "2"}))
        check("ID sorgusu ('2') da çalışıyor", "264 adet Dirt" in r["cevap"], r["cevap"])

        # Senaryo 3: Dünya sayımı (census)
        r = J(await client.call_tool("gh_world_census", {}))
        top_fg = r["en_cok_on_plan"]
        print(f"    census: {r['toplam_tile']} tile | en çok ön plan: {top_fg[0]['isim']} x{top_fg[0]['adet']}")
        check("Census: 6000 tile", r["toplam_tile"] == 6000)
        check("Census: en çok fg = Dirt x214", top_fg[0]["isim"] == "Dirt" and top_fg[0]["adet"] == 214)
        check("Census: en çok bg = Bedrock", r["en_cok_arka_plan"][0]["isim"] == "Bedrock"
              and r["en_cok_arka_plan"][0]["adet"] == BG_BEDROCK_EXPECT)
        check("Census: Rock x100 da listede", any(x["isim"] == "Rock" and x["adet"] == 100 for x in top_fg))

        # Senaryo 4: item DB araçları
        r = await client.call_tool("gh_item_db_search", {"query": "dirt", "limit": 5})
        check("gh_item_db_search('dirt') çalışıyor", "2 = Dirt" in str(r.data))
        r = J(await client.call_tool("gh_item_db_info", {"item_id": 2}))
        check("gh_item_db_info(2) → Dirt, seed 3", r["isim"] == "Dirt" and r["seed_id"] == 3, str(r))
        r = await client.call_tool("gh_item_lookup", {"query": "Dirt"})
        check("gh_item_lookup hâlâ çalışıyor (yeni DB ile)", "2" in str(r.data) and "Dirt" in str(r.data))

        # Senaryo 5: belirsiz isim — AI asla tahmin etmez, aday listeler
        r = await client.call_tool("gh_world_count_item", {"item": "bu"})
        check("Belirsiz isim → aday listesi (tahmin YOK)", "belirsiz" in str(r.data), str(r.data)[:120])

asyncio.run(protocol_test())

stop_flag.set()
th.join(timeout=2)

print(f"\n{'='*50}")
print(f"SONUÇ: {ok_count} başarılı, {fail_count} başarısız")
print("\n💡 KANIT: Kullanıcı AI'sına 'dünyada kaç tane dirt var?' diye sorarsa,")
print("   MCP köprüden canlı tarar ve GERÇEK sayıyı döndürür — bu testte tam 264 bulundu.")
sys.exit(1 if fail_count else 0)
