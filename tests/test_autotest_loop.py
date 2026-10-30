#!/usr/bin/env python3
"""
OTOMATİK TEST DÖNGÜSÜ KANIT TESTİ (mr_berk)
=============================================
Kullanıcı isteği: "Scripti hazırla → GENTAHAX'ın KENDİ executor'ında çalıştır →
loglarına bak → çalışıyorsa 'çalışıyor' de → logda hata varsa AI'a göre hareket etsin."

Bu test döngünün HER halkasını gerçek olarak doğrular:

  KATMAN 0 — Hata sınıflandırıcı birimleri (gerçek Lua hata mesaj formatlarıyla)
  KATMAN 1 — Farm scripti GERÇEK Lua'da (lupa) koşar → doLog çıktıları
             (AUTOTEST|START/OK + FARM_RESULT) yakalanır → karar: CALISIYOR
  KATMAN 2 — HATA YOLU: yanlış fonksiyon adı GERÇEK Lua'da patlar → gerçek hata
             mesajı sınıflandırılır (MISSING_FN) → YAMA üretilir → yamalı kod
             gerçek Lua'da ÇALIŞIR (döngü kapanır)
  KATMAN 3 — gh_auto_test ARACI uçtan uca (sahte köprü üzerinden):
             executor çağrılır, lua_logs.txt okunur, kullaniciya_soz üretilir;
             HATA → yama → TEKRAR çağrı → CALISIYOR (kullanıcının istediği kapalı döngü)
  KATMAN 4 — Güvenlik: yüksek riskli kod force'suz çalıştırılmaz; bozuk söz dizimi
             executor'a HİÇ gönderilmez (ve oyun fonksiyonları derleme kontrolünde
             false hata VERMEZ — kullanıcının haklı itirazının kanıtı)
  KATMAN 5 — SOĞUK BAŞLANGIÇ MCP çağrı zinciri (v1.5.0 çöküş düzeltmesi): taze
             python sürecinde (Claude Desktop'ın gerçek yolu) lupa'lı araçlar
             çağrılır — sunucu süreci ölmez, dürüst karar döner
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

import autotest as AT
import knowledge as K
import server as S

API_NAMES = K.api_names("android") + K.api_names("windows")

# ===========================================================================
print("=== KATMAN 0: HATA SINIFLANDIRICI (gerçek executor formatları) ===")
e = AT.classify_line("[string \"x\"]:3: attempt to call a nil value (global 'getPlayerList')")
check("MISSING_FN yakalanır + hedef isim çıkar", e and e["sinif"] == "MISSING_FN" and e["hedef"] == "getPlayerList", str(e))

e = AT.classify_line("attempt to index a nil value (local 'w')")
check("NIL_INDEX yakalanır (getWorld boş durumu)", e and e["sinif"] == "NIL_INDEX", str(e))

e = AT.classify_line("[string \"y\"]:1: 'end' expected near <eof>")
check("SYNTAX yakalanır", e and e["sinif"] == "SYNTAX", str(e))

e = AT.classify_line("Normal ilerleme satırı — 10/37 pepper kırıldı")
check("Normal satır hata SAYILMAZ", e is None)

v = AT.parse_execution("Köprü zaman aşımı (25s) — yanıt yok", [])
check("Köprü zaman aşımı → CIHAZ_YOK", v["sonuc"] == "CIHAZ_YOK", v["sonuc"])

v = AT.parse_execution("ERR|NO_WORLD", [])
check("Dünyada değil → HATA/NOT_IN_WORLD", v["sonuc"] == "HATA" and v["hata"]["sinif"] == "NOT_IN_WORLD")

v = AT.parse_execution("QUEUED|WORLD:X|FOUND:5", ["AUTOTEST|START|farm|hedef:5", "r_berk farm] 5/5 kirildi"])
check("Başladı, bitmedi → DEVAM_EDIYOR", v["sonuc"] == "DEVAM_EDIYOR", v["sonuc"])

v = AT.parse_execution("QUEUED|WORLD:X", ["AUTOTEST|OK|farm_4570|kirilan:37|gems_kazanc:97"])
check("AUTOTEST|OK işareti → CALISIYOR", v["sonuc"] == "CALISIYOR", v["sonuc"])

v = AT.parse_execution("Lua hatası: attempt to call a nil value (global 'getPlayerList')", [])
check("Executor hata dönüşü → HATA + sınıf", v["sonuc"] == "HATA" and v["hata"]["sinif"] == "MISSING_FN")

check("closest: 'getPlayerList' → ['getPlayerlist'] (tek aday)",
      AT.closest_function("getPlayerList", API_NAMES) == ["getPlayerlist"])
check("closest: saçma isim → aday YOK (asla tahmin etmez)",
      AT.patch_missing_fn("x", "a", "b") == ("x", 0) and AT.closest_function("xyzzyq", API_NAMES) == [])

patched, n = AT.patch_missing_fn("local p = getPlayerList() return getPlayerList()[1]", "getPlayerList", "getPlayerlist")
check("Yama: yanlış isim doğruyla değişir (2 çağrı)", n == 2 and "getPlayerlist()" in patched and "getPlayerList" not in patched)
print()

# ===========================================================================
print("=== KATMAN 1: FARM SCRIPTİ GERÇEK LUA'DA → LOG → CALISIYOR ===")
import lupa
lua = lupa.LuaRuntime()

W, H, PEPPER, GEMS0 = 30, 20, 4570, 500
peppers = [(i * 7 % W, (i * 11) % H) for i in range(11)]
EXPECTED = sum((x + y) % 4 + 1 for x, y in peppers)

lua.execute(f"""
ID_NAMES = {{ [{PEPPER}]='Pepper', [10]='Rock', [0]='Blank' }}
GEMS, LOGS, PUNCHES = {GEMS0}, {{}}, {{}}
function getWorld() return {{ name='OTOTEST', width={W}, height={H} }} end
function getItemByID(id) return {{ name=ID_NAMES[id] or '?', id=id }} end
function getLocal() return {{ name='mr_berk', gems=GEMS }} end
function doLog(s) LOGS[#LOGS+1] = tostring(s) end
function logToConsole(s) end
function doToast(a,b,c) end
function sleep(ms) end
function runThread(fn, label) fn() end
TILES = {{}}
for y=0,{H}-1 do for x=0,{W}-1 do TILES[y*{W}+x+1] = {{ pos={{x=x,y=y}}, fg=0 }} end end
function tileAt(x,y) return TILES[y*{W}+x+1] end
function getTile() return TILES end
function checkTile(x,y) return tileAt(x,y) end
function sendPacketRaw(c, pkt)
  if pkt.state == 16 then
    local t = tileAt(pkt.punchx, pkt.punchy)
    if t.fg == {PEPPER} then t.fg = 0 PUNCHES[#PUNCHES+1] = 1 GEMS = GEMS + (pkt.punchx + pkt.punchy) % 4 + 1 end
  end
end
""")
for x, y in peppers:
    lua.eval(f"tileAt({x},{y})").fg = PEPPER

code = S._FARM_LUA.replace("{ID}", "4570").replace("{NAME}", "Pepper").strip()
check("Script AUTOTEST işaretleri taşıyor", "AUTOTEST|START" in code and "AUTOTEST|OK" in code)
sync = lua.execute(code)
check("Senkron dönüş QUEUED", str(sync).startswith("QUEUED"), str(sync)[:60])

n_logs = lua.eval("#LOGS")
logs = [str(lua.eval(f"tostring(LOGS[{i}])")) for i in range(1, n_logs + 1)]
ok_marker = [l for l in logs if "AUTOTEST|OK" in l]
check(f"lua_logs'a AUTOTEST|OK düştü ({len(logs)} satır log)", bool(ok_marker), str(logs[-3:]))
farm_line = [l for l in logs if l.startswith("FARM_RESULT")]
check("FARM_RESULT raporu düştü", bool(farm_line))
if farm_line:
    parts = dict(kv.split(":", 1) for kv in farm_line[0].split("|") if ":" in kv)
    check(f"Rapor sayıları doğru: 11 kırıldı, +{EXPECTED} gems",
          parts.get("BROKEN") == "11" and parts.get("GEMS_GAINED") == str(EXPECTED), farm_line[0])

v = AT.parse_execution(str(sync), logs)
check("DÖNGÜ KARARI: CALISIYOR", v["sonuc"] == "CALISIYOR", v["sonuc"])
check("Kanıt satırı AUTOTEST|OK içeriyor", any("AUTOTEST|OK" in k for k in v["kanit"]), str(v["kanit"]))

new = AT.new_log_lines("", "\n".join(logs))
check("new_log_lines: tüm yeni satırları ayırır", len(new) == len(logs))
print()

# ===========================================================================
print("=== KATMAN 2: HATA YOLU — gerçek Lua patlar → teşhis → yama → ÇALIŞIR ===")
lua.execute("function getPlayerlist() return { { name='Oyuncu1' }, { name='mr_berk' } } end")
bad_code = "local p = getPlayerList() return p[1].name"
try:
    lua.execute(bad_code)
    check("Gerçek Lua yanlış fonksiyonda HATA VERDİ", False, "hata beklenmişti")
except lupa.LuaError as le:
    errline = str(le)
    check("Gerçek Lua hata fırlattı (executor'ın yapdığı gibi)", "getPlayerList" in errline, errline[:80])
    err = AT.classify_line(errline)
    check("Hata gerçek mesajdan sınıflandırıldı: MISSING_FN/getPlayerList",
          err and err["sinif"] == "MISSING_FN" and err["hedef"] == "getPlayerList", str(err))
    fix = AT.suggest_fix(err, API_NAMES)
    check("Çözüm önerisi doğru ismi söylüyor", "getPlayerlist" in fix["cozum"], fix["cozum"])
    aday = AT.closest_function("getPlayerList", API_NAMES)
    patched, n = AT.patch_missing_fn(bad_code, "getPlayerList", aday[0])
    result = lua.execute(patched)
    check("YAMALI kod gerçek Lua'da ÇALIŞTI → döngü kapandı", str(result) == "Oyuncu1", str(result))
print()

# ===========================================================================
print("=== KATMAN 3: gh_auto_test ARACI uçtan uca (sahte köprü = executor taklidi) ===")
import bridge as B

_orig_exec, _orig_logs, _orig_status = B.exec_lua, B.read_logs, B.status
CALLS = {"exec": [], "logs": 0}
FAIL_NEXT = [False]
LOG_TEXT = {"before": "", "after": ""}
SYNC_RESULT = {"value": "ok"}

def fake_exec_lua(code, timeout=10, risk_level="low"):
    CALLS["exec"].append(code)
    if FAIL_NEXT[0]:
        FAIL_NEXT[0] = False
        raise RuntimeError("Lua hatası: attempt to call a nil value (global 'getPlayerList')")
    return SYNC_RESULT["value"]

def fake_read_logs(tail=80):
    CALLS["logs"] += 1
    # executor çağrılmadan ÖNCE 'before' (baz), çağrıldıktan SONRA 'after' (yeni loglar)
    return LOG_TEXT["after"] if CALLS["exec"] else LOG_TEXT["before"]

def fake_status():
    return {"configured": True, "mode": "local", "script_dir": "/tmp/fake_script_dir",
            "bridge_responding": True, "safe_mode": True}

B.exec_lua, B.read_logs, B.status = fake_exec_lua, fake_read_logs, fake_status

from fastmcp import Client

async def call_tool(name, args):
    async with Client(S.mcp) as client:
        r = await client.call_tool(name, args)
        d = r.data
        return json.loads(d) if isinstance(d, str) else d

import asyncio

# --- 3a) başarılı yol: executor OK + loglarda AUTOTEST|OK → kullanıcıya ÇALIŞIYOR
LOG_TEXT["before"] = "eski log satırı"
LOG_TEXT["after"] = "eski log satırı\nAUTOTEST|START|farm_4570|hedef:5\nAUTOTEST|OK|farm_4570|kirilan:5"
SYNC_RESULT["value"] = "ok"
CALLS["exec"].clear()
r = asyncio.run(call_tool("gh_auto_test", {"script": "return 'ok'", "watch": 3}))
check("gh_auto_test → sonuc CALISIYOR", r["sonuc"] == "CALISIYOR", r.get("sonuc"))
check("kullaniciya_soz: '✅ Script ÇALIŞIYOR'", "ÇALIŞIYOR" in r["kullaniciya_soz"], r.get("kullaniciya_soz"))
check("kanıt: AUTOTEST|OK satırı", any("AUTOTEST|OK" in k for k in r["kanit"]))
check("sözdizimi ön-kontrol: geçti (derleme — oyun fns false hata vermez)",
      r["sozdizimi_on_kontrol"]["sonuc"] == "geçti", str(r.get("sozdizimi_on_kontrol")))
check("executor (GENTAHAX içi) GERÇEKTEN çağrıldı", len(CALLS["exec"]) == 1)
check("loglar gerçekten okundu", CALLS["logs"] >= 1)

# --- 3b) KULLANICININ İSTEDİĞİ KAPALI DÖNGÜ: HATA → teşhis → YAMA → tekrar → ÇALIŞIYOR
hatali_script = ("local me = getLocal()\nif not me then return 'ERR|NO_LOCAL' end\n"
                 "doLog('oyuncu: ' .. getPlayerList()[1].name)\nreturn 'ok'")
FAIL_NEXT[0] = True
LOG_TEXT["before"], LOG_TEXT["after"] = "", ""
SYNC_RESULT["value"] = "ok"
CALLS["exec"].clear()
r1 = asyncio.run(call_tool("gh_auto_test", {"script": hatali_script, "watch": 3}))
check("1. deneme → sonuc HATA", r1["sonuc"] == "HATA", r1.get("sonuc"))
check("1. deneme → hata sınıfı MISSING_FN", r1["hata"]["sinif"] == "MISSING_FN", str(r1.get("hata")))
check("1. deneme → kullaniciya_soz hatayı söylüyor", "HATA verdi" in r1["kullaniciya_soz"])
check("YAMA üretildi: getPlayerList → getPlayerlist",
      r1.get("yama") and r1["yama"]["yeni_fonksiyon"] == "getPlayerlist", str(r1.get("yama"))[:120])

yama_script = r1["yama"]["script"]
r2 = asyncio.run(call_tool("gh_auto_test", {"script": yama_script, "watch": 3}))
check("2. deneme (yamayla) → ✅ ÇALIŞIYOR — döngü kapandı",
      r2["sonuc"] == "CALISIYOR", r2.get("sonuc"))
check("Yamalı scriptte yanlış isim kalmadı", "getPlayerList" not in yama_script)

# --- 3c) devam ediyor yolu
LOG_TEXT["before"], LOG_TEXT["after"] = "", "AUTOTEST|START|farm|hedef:50"
SYNC_RESULT["value"] = "QUEUED|devam"
CALLS["exec"].clear()
r = asyncio.run(call_tool("gh_auto_test", {"script": "return 'QUEUED|devam'", "watch": 3}))
check("Başladı-bitti yok → DEVAM_EDIYOR", r["sonuc"] == "DEVAM_EDIYOR", r.get("sonuc"))
check("kullaniciya_soz: çalışıyor + devam ediyor", "devam ediyor" in r["kullaniciya_soz"].lower())

# --- 3d) dünyada değil
LOG_TEXT["before"], LOG_TEXT["after"] = "", ""
SYNC_RESULT["value"] = "ERR|NO_WORLD"
CALLS["exec"].clear()
r = asyncio.run(call_tool("gh_auto_test", {"script": "return 'ERR|NO_WORLD'", "watch": 3}))
check("ERR|NO_WORLD → HATA + 'dünyaya gir' çözümü",
      r["sonuc"] == "HATA" and "Dünyada değilsin" in r["hata"]["aciklama"], str(r.get("hata")))

B.exec_lua, B.read_logs, B.status = _orig_exec, _orig_logs, _orig_status
print()

# ===========================================================================
print("=== KATMAN 4: GÜVENLİK + SÖZ DİZİMİ ÖN-KONTROLÜ (kullanıcının itirazı) ===")
# Yüksek riskli kod force'suz reddedilir — executor'a HİÇ gitmez
CALLS["exec"].clear()
B.exec_lua, B.read_logs, B.status = fake_exec_lua, fake_read_logs, fake_status
risky = "while true do sendPacket(2, 'action|input') end"
r = asyncio.run(call_tool("gh_auto_test", {"script": risky}))
check("Yüksek risk → REDDEDİLDİ", r["sonuc"] == "REDDEDİLDİ", r.get("sonuc"))
check("'⚠️ BUNDA BAN RİSKİ VAR' uyarısı", "BAN RİSKİ" in (r.get("uyari") or ""))
check("Executor'a HİÇ gönderilmedi", len(CALLS["exec"]) == 0, str(len(CALLS["exec"])))

# Bozuk söz dizimi → executor'a hiç gitmeden yakalanır
r = asyncio.run(call_tool("gh_auto_test", {"script": "if true then"}))
check("Bozuk söz dizimi → HATA/SYNTAX", r["sonuc"] == "HATA" and r["hata"]["sinif"] == "SYNTAX")
check("Söz dizimi hatasında executor çağrılmadı", len(CALLS["exec"]) == 0)

# OYUN FONKSİYONLARI derleme kontrolünde false hata VERMEZ (kullanıcının itirazı)
pre_ok = S._syntax_precheck("toggleCheat(26, true) sendPacket(2,'x') local me = getLocal()")
check("toggleCheat/sendPacket/getLocal DERLEMEDE hata VERMEZ (kod çalıştırılmıyor)",
      pre_ok["sonuc"] == "geçti", str(pre_ok))
pre_bad = S._syntax_precheck("if true then")
check("Eksik 'end' yakalanır", pre_bad["sonuc"] == "hata")

B.exec_lua, B.read_logs, B.status = _orig_exec, _orig_logs, _orig_status

# ===========================================================================
print("=== KATMAN 5: SOĞUK BAŞLANGIÇ MCP ÇAĞRI ZİNCİRİ (v1.5.0 çöküş düzeltmesi) ===")
# v1.5.0'da lupa LuaRuntime'ı araç çağrısının İÇİNDE kuruluyordu; fastmcp araç
# gövdelerini pydantic-core çerçevesi altında koşturduğu için SOĞUK süreçte ilk
# çağrıda Lua PANIC ile sunucu süreci ÖLÜYORDU (stdio yolunda 'Connection closed'
# — benchmark'ın yakaladığı gerçek hata). Düzeltme: motor açılışta kurulur.
# Bu katman taze süreci (Claude Desktop yolu) gerçek istemciyle yoklar.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

async def cold_start_test():
    async with Client(os.path.join(ROOT_DIR, "server.py")) as client:
        r1 = await client.call_tool("gh_script_gen", {"goal": "pepperları kır"})
        j1 = json.loads(r1.data)
        r2 = await client.call_tool(
            "gh_auto_test",
            {"script": "local me = getLocal() return 'FARM_RESULT|OK'", "watch": 3})
        j2 = json.loads(r2.data)
        return j1, j2

j1, j2 = asyncio.run(cold_start_test())
check("SOĞUK süreç: gh_script_gen sunucuyu öldürmüyor (lupa motoru açılışta kurulur)",
      j1.get("sozdizimi", {}).get("sonuc") in ("geçti", "atıldı"),
      str(j1.get("sozdizimi")))
check("SOĞUK süreç: üretilen script gerçek Pepper ID 4570 içeriyor",
      "4570" in j1.get("script", ""))
check("SOĞUK süreç: gh_auto_test dürüst karar veriyor (köprüsüz → CIHAZ_YOK)",
      j2.get("sonuc") == "CIHAZ_YOK", str(j2.get("sonuc")))
check("SOĞUK süreç: derleme ön-kontrolü çalıştı", j2.get("calistirildi") is False)

# ===========================================================================
print()
print("=" * 60)
print(f"SONUÇ: {ok_count} başarılı, {fail_count} başarısız")
print()
print("💡 KANIT: gh_auto_test scripti GENTAHAX executor'ında çalıştırır, loglarını")
print("   okur, '✅ ÇALIŞIYOR' der; hata görürse sınıflandırır + YAMA üretir; yamayla")
print("   tekrar deneyince döngü kapanır. Karar YALNIZCA executor + loglardan gelir.")
raise SystemExit(1 if fail_count else 0)
