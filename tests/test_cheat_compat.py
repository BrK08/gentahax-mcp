#!/usr/bin/env python3
"""
HAZIR MOD KONTROLÜ + APK UYUM TESTİ KANIT TESTİ (mr_berk)
==========================================================
Kullanıcı isteği: "AI GENTAHAX'ta var olan şeyleri de kullanabilsin — mesela
Mod Fly açıp kapatabilsin. Hazır olan şeyleri de kullanabilsin."

  KATMAN 0 — Cheat isim çözümü: 'mod fly'/'fly'/'26' → kod 26; belirsiz isimde
             ASLA tahmin edilmez, adaylar listelenir ('ghost' → 2 aday)
  KATMAN 1 — gh_cheat_set: toggleCheat uygular + getCheat ile DOĞRULAR
             (sahte köprü = executor taklidi; gönderilen Lua kodu da doğrulanır)
  KATMAN 2 — gh_cheat_status: 32 modun tamamının durum tablosu tek çağrıda
  KATMAN 3 — gh_compat_check (APK güncellemesi senaryoları):
             offline rapor · TAM UYUMLU · KISMİ (eksikler + etkilenen şablonlar)
             · KÖPRÜ KIRIK
"""
import asyncio
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

import knowledge as K
import server as S

# ===========================================================================
print("=== KATMAN 0: CHEAT İSİM ÇÖZÜMÜ (DLL doğrulamalı 32 mod listesi) ===")
r = S._resolve_cheat("Mod Fly")
check("'Mod Fly' → kod 26", r.get("resolved") and r["code"] == 26, str(r))
r = S._resolve_cheat("modfly")
check("'modfly' → kod 26 (yazım esnek)", r.get("resolved") and r["code"] == 26, str(r))
r = S._resolve_cheat("fly")
check("'fly' → kod 26 (kısa isim)", r.get("resolved") and r["code"] == 26, str(r))
r = S._resolve_cheat("26")
check("'26' (kod ile) → Mod Fly", r.get("resolved") and r["label"] == "Mod Fly", str(r))
r = S._resolve_cheat("ghost")
check("'ghost' belirsiz → 2 aday LİSTELENİR, tahmin YOK",
      r.get("reason") == "ambiguous" and len(r["candidates"]) >= 2, str(r))
r = S._resolve_cheat("olmayanmodxyz")
check("Bilinmeyen isim → not_found (uydurma YOK)", r.get("reason") in ("not_found", "did_you_mean"), str(r))
r = S._resolve_cheat("no clip")
check("'no clip' → No Clip (6)", r.get("resolved") and r["label"] == "No Clip", str(r))
print()

# ===========================================================================
print("=== KATMAN 1-2: gh_cheat_set / gh_cheat_status (sahte köprü = executor taklidi) ===")
import bridge as B
_orig_exec, _orig_logs, _orig_status = B.exec_lua, B.read_logs, B.status
SENT_LUA = []
RET = {"value": "false"}
FAIL = [False]

def fake_exec_lua(code, timeout=10, risk_level="low"):
    SENT_LUA.append(code)
    if FAIL[0]:
        raise TimeoutError("Köprü zaman aşımı (8s)")
    return RET["value"]

def fake_read_logs(tail=80):
    return ""

def fake_status():
    return {"configured": True, "mode": "local", "script_dir": "/tmp/fake",
            "bridge_responding": True}

B.exec_lua, B.read_logs, B.status = fake_exec_lua, fake_read_logs, fake_status

from fastmcp import Client

async def call_tool(name, args):
    async with Client(S.mcp) as client:
        r = await client.call_tool(name, args)
        d = r.data
        return json.loads(d) if isinstance(d, str) else d

# durum okuma
SENT_LUA.clear()
r = asyncio.run(call_tool("gh_cheat_set", {"cheat": "Mod Fly"}))
check("'Mod Fly durumu?' → KAPALI (getCheat okudu)", r.get("durum") == "KAPALI", str(r)[:120])
check("Okuma getCheat(26) ile yapıldı", "getCheat(26)" in (SENT_LUA[0] if SENT_LUA else ""), str(SENT_LUA[:1]))

# açma + doğrulama
RET["value"] = "true"
SENT_LUA.clear()
r = asyncio.run(call_tool("gh_cheat_set", {"cheat": "mod fly", "state": True}))
check("'mod fly aç' → AÇIK ✓ doğrulandı", "AÇIK ✓" in r.get("sonuc", ""), str(r)[:140])
check("toggleCheat(26, true) GÖNDERİLDİ", any("toggleCheat(26, true)" in c for c in SENT_LUA), str(SENT_LUA[:1]))
check("getCheat ile DOĞRULANDI", any("getCheat(26)" in c for c in SENT_LUA))
check("Ban notu: davranış dünyada görünür uyarısı", "GÖRÜNÜR" in r.get("ban_notu", ""), r.get("ban_notu", "")[:80])

# kapatma
RET["value"] = "false"
SENT_LUA.clear()
r = asyncio.run(call_tool("gh_cheat_set", {"cheat": "fly", "state": False}))
check("'fly kapat' → KAPALI ✓", "KAPALI ✓" in r.get("sonuc", ""), str(r)[:140])

# görsel mod → düşük risk notu
RET["value"] = "true"
r = asyncio.run(call_tool("gh_cheat_set", {"cheat": "Night Vision", "state": True}))
check("Night Vision (görsel mod) → 'ban riski düşük' notu", "düşük" in r.get("ban_notu", ""), r.get("ban_notu", "")[:80])

# belirsiz isim → executor HİÇ çağrılmaz
SENT_LUA.clear()
r = asyncio.run(call_tool("gh_cheat_set", {"cheat": "ghost", "state": True}))
check("'ghost' belirsiz → adaylar listelendi", r.get("adaylar") and len(r["adaylar"]) >= 2, str(r)[:150])
check("Belirsiz istekte executor çağrılmadi", len(SENT_LUA) == 0)

# doğrulama başarısız yolu
RET["value"] = "false"
r = asyncio.run(call_tool("gh_cheat_set", {"cheat": "Mod Fly", "state": True}))
check("Oyun açmadıysa → '⚠️ UYGULANAMADI' dürüst raporu", "UYGULANAMADI" in r.get("sonuc", ""), str(r)[:140])

# köprü hatası
FAIL[0] = True
r = asyncio.run(call_tool("gh_cheat_set", {"cheat": "Mod Fly", "state": True}))
check("Köprü ölüyse → hata + yol gösterme (çökmez)", "hata" in r, str(r)[:100])
FAIL[0] = False

# durum tablosu: 32 mod tek çağrıda
e = K.get_enums()["CheatCode"]
codes = sorted(int(k) for k in e)
RET["value"] = "|".join(f"{c}={'true' if c in (1, 26) else 'false'}" for c in codes)
r = asyncio.run(call_tool("gh_cheat_status", {}))
check(f"Durum tablosu: {len(codes)} modun hepsi okundu", r.get("okunabildi") == len(codes), str(r)[:100])
check("Açık olanlar listelendi: Ghost Mode + Mod Fly",
      "Ghost Mode" in str(r.get("acik_olanlar")) and "Mod Fly" in str(r.get("acik_olanlar")), str(r.get("acik_olanlar")))
check("Tablo satırları kod+isim+durum içeriyor",
      isinstance(r.get("tablo"), list) and len(r["tablo"]) == len(codes)
      and {"kod": 26, "mod": "Mod Fly", "durum": "AÇIK"} in r["tablo"], str(r.get("tablo", [])[:2]))
print()

# ===========================================================================
print("=== KATMAN 3: gh_compat_check — APK GÜNCELLEMESİ SENARYOLARI ===")
B.exec_lua, B.read_logs, B.status = _orig_exec, _orig_logs, _orig_status

# 3a) offline (köprü kapalı — gerçek ortam değişkeni yok)
r = asyncio.run(call_tool("gh_compat_check", {}))
check("Köprü kapalı → OFFLINE rapor (çökmez)", "OFFLINE" in r.get("sonuc", ""), str(r)[:80])
check("3 senaryo (A/B/C) anlatılıyor", len(r.get("apk_guncellemesi_olursa_3_senaryo", [])) == 3)
check("Bilgi tabanı rakamları: 57 Android + 18 Windows + v5.61",
      r["bilgi_tabani"]["bilinen_android_fonksiyon"] == 57
      and r["bilgi_tabani"]["bilinen_windows_fonksiyon"] == 18
      and "v5.61" in r["bilgi_tabani"]["analiz_edilen_surum"])
check("Item veritabanı APK'dan bağımsız notu", "BAĞIMSIZ" in r["bilgi_tabani"]["item_veritabani"])
check("GUNCELLEME.md rehberine yönlendiriyor", "GUNCELLEME.md" in str(r.get("detayli_rehber", "")))

# 3b) TAM UYUMLU: android 57/57, windows istemcisi değil
B.exec_lua, B.read_logs, B.status = fake_exec_lua, fake_read_logs, fake_status
PROBE = {"android": "OK:57|MISSING:", "windows": "OK:0|MISSING:" + ",".join(K.api_names("windows"))}
def fake_exec_probe(code, timeout=10, risk_level="low"):
    SENT_LUA.append(code)
    if FAIL[0]:
        raise TimeoutError("Köprü zaman aşımı (15s)")
    # windows yoklaması 'GetLocal' (büyük G) içerir — android yoklaması asla içermez
    if "GetLocal" in code:
        return PROBE["windows"]
    return PROBE["android"]
B.exec_lua = fake_exec_probe
SENT_LUA.clear()
r = asyncio.run(call_tool("gh_compat_check", {}))
check("Canlı yoklama → TAM UYUMLU (57/57)", "TAM UYUMLU" in r.get("sonuc", ""), str(r)[:80])
check("Bağlı istemci ANDROID tespit edildi", r.get("bagli_istemci") == "ANDROID")
check("Yoklama gerçekten type(_G[...]) kontrolü gönderdi", any("type(_G[n])" in c for c in SENT_LUA), str(SENT_LUA[:1])[:100])

# 3c) KISMİ: bir fonksiyon eksik → etkilenen şablonlar listelenir
PROBE["android"] = "OK:56|MISSING:getLocal"
SENT_LUA.clear()
r = asyncio.run(call_tool("gh_compat_check", {}))
check("Eksik fonksiyon → KISMİ UYUM", "KISMİ" in r.get("sonuc", ""), str(r)[:90])
check("Eksikler listelendi: getLocal", "getLocal" in r["canli_yoklama"]["eksikler"])
etk = str(r.get("etkilenen_sablonlar"))
check("Etkilenen şablonlar listelendi (getLocal kullananlar)", "auto_collect" in etk or "dirt_farm" in etk, etk[:120])
check("Çözüm yolu: data/api_*.json güncellemesi önerilir", "api_android.json" in str(r.get("ne_yapmali")))

# 3d) KÖPRÜ KIRIK (Senaryo C)
FAIL[0] = True
SENT_LUA.clear()
r = asyncio.run(call_tool("gh_compat_check", {}))
check("Köprü yanıt vermiyor → KÖPRÜ KIRIK (Senaryo C)", "KÖPRÜ KIRIK" in r.get("sonuc", ""), str(r)[:80])
check("Senaryo C adımları anlatılıyor", "gh_bridge_deploy" in str(r.get("ne_yapmali")) and "GUNCELLEME.md" in str(r.get("ne_yapmali")))
FAIL[0] = False

B.exec_lua, B.read_logs, B.status = _orig_exec, _orig_logs, _orig_status

# ===========================================================================
print()
print("=" * 60)
print(f"SONUÇ: {ok_count} başarılı, {fail_count} başarısız")
print()
print("💡 KANIT: AI artık GENTAHAX'ın HAZIR modlarını da kontrol ediyor — 'mod fly aç'")
print("   → toggleCheat(26,true) + getCheat doğrulaması; 'hangi modlar açık?' → 32'lik")
print("   durum tablosu. APK güncellemesinde gh_compat_check 57 fonksiyonu canlı yoklar.")
raise SystemExit(1 if fail_count else 0)
