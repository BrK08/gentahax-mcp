#!/usr/bin/env python3
"""GENTAHAX MCP — fonksiyonel test paketi (mr_berk)"""
import sys, json
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import knowledge as K

ok_count = 0
fail_count = 0

def check(name, cond, detail=""):
    global ok_count, fail_count
    if cond:
        ok_count += 1
        print(f"  ✅ {name}")
    else:
        fail_count += 1
        print(f"  ❌ {name} {detail}")

print("=== 1. BİLGİ TABANI BÜTÜNLÜĞÜ ===")
s = K.stats()
print(f"  İstatistikler: {json.dumps(s, ensure_ascii=False)}")
check("Android API >= 50 fonksiyon", s["android_functions"] >= 50, f"= {s['android_functions']}")
check("Windows API >= 15 fonksiyon", s["windows_functions"] >= 15, f"= {s['windows_functions']}")
check("32 cheat kodu", s["cheat_codes"] == 32)
check("39 paket tipi", s["packet_types"] == 39)
check("10 hook", s["hooks"] == 10)
check("19 bellek yaması", s["memory_patch_names"] == 19)
check("22+ DLL doğrulamalı variant fonksiyonu", s["variant_functions_verified"] >= 22)
check("7+ şablon", s["templates"] >= 7)
check("3 resmi örnek", s["examples"] == 3)

print("\n=== 2. ARAMA ===")
r = K.search_api("tile", "android")
check("tile araması sonuç veriyor", len(r) >= 3, f"= {len(r)}")
r = K.search_api("packet", "both")
check("packet araması hem Android hem Windows", any(x["platform"] == "android" for x in r) and any(x["platform"] == "windows" for x in r))
d = K.api_detail("sendVariant", "android")
check("sendVariant detayı", d and "variantlist_t" in d["signature"])
d = K.api_detail("FindPath", "windows")
check("FindPath Windows delay parametreli", d and "delay" in d["signature"])

print("\n=== 3. BAN RİSKİ SINIFLANDIRICI ===")
high_code = """
while true do
    sendPacket(2, 'action|input\\ntext|/go START')
end
"""
r = K.analyze_code(high_code)
check("Paket spam → YÜKSEK risk", r["risk_level"] == "high", f"= {r['risk_level']}")
check("Ban uyarı banner'ı var", r["high_risk_banner"] is not None and "BAN RİSKİ" in r["high_risk_banner"])
check("Risk puanı >= 45", r["risk_score"] >= 45, f"= {r['risk_score']}")

med_code = """
while true do
    for _, obj in pairs(getWorldObject()) do
        requestCollect(obj.pos.x, obj.pos.y, obj.id)
        sleep(300)
    end
    sleep(500)
end
"""
r = K.analyze_code(med_code)
check("Sleep'li auto-collect → ORTA risk", r["risk_level"] == "medium", f"= {r['risk_level']}")

low_code = """
AddHook('OnRender', 'ui', function(dt)
    ImGui.Begin('mr_berk')
    local me = getLocal()
    ImGui.TextUnformatted(me.name)
    ImGui.End()
end)
"""
r = K.analyze_code(low_code)
check("ImGui/okuma → DÜŞÜK risk", r["risk_level"] == "low", f"= {r['risk_level']}")
check("Düşük riskte banner yok", r["high_risk_banner"] is None)

hwid_code = "randomGid() randomMac()"
r = K.analyze_code(hwid_code)
check("HWID spoof → YÜKSEK", r["risk_level"] == "high")

bad_code = "local x = getGems() local y = setgems(5)"
r = K.analyze_code(bad_code)
check("Uydurma fonksiyon tespiti", "getGems" in r["unknown_functions"], f"= {r['unknown_functions']}")

syn_code = "if true then\n  print('x')\n"
r = K.analyze_code(syn_code)
check("Eksik end tespiti", any("Blok" in i for i in r["syntax_issues"]), f"= {r['syntax_issues']}")

print("\n=== 4. GERÇEK ITEM ID VERİTABANI (6832 eşya) ===")
check("6832 gerçek eşya", K.items_count() == 6832, f"= {K.items_count()}")
check("ID 2 = Dirt", K.item_by_id(2) == "Dirt")
check("ID 112 = Gems", K.item_by_id(112) == "Gems")
check("'Dirt' çözümü → ID 2", K.item_resolve("Dirt")["id"] == 2)
check("'dirt seed' çözümü → ID 3", K.item_resolve("dirt seed")["id"] == 3)
check("Sayı sorgusu '2' → Dirt", K.item_resolve("2")["name"] == "Dirt")
check("seed_of(2) = 3", K.seed_of(2) == 3)
check("base_of(3) = 2", K.base_of(3) == 2)
check("Belirsiz sorgu çözülmez (tahmin yok)", K.item_resolve("bu")["resolved"] is False)
check("Seed çifti sayısı > 3000", K.stats()["items_db_seed_pairs"] > 3000, f"= {K.stats()['items_db_seed_pairs']}")
r = K.items_search("dirt", 10)
check("'dirt' araması Dirt ve Dirt Seed içerir", any(x["id"] == 2 for x in r) and any(x["id"] == 3 for x in r))

print("\n=== 5. ŞABLONLAR & ÖRNEKLER ===")
t = K.template_get("auto_collect")
check("auto_collect şablonu", t and "requestCollect" in t["code"])
t = K.template_get("esp_overlay")
check("esp_overlay şablonu", t and "worldToScreen" in t["code"])
ex = K.example_get("extender.lua")
check("extender.lua okunuyor", ex and "AutoCollect" in ex)

print("\n=== 6. BRIDGE MODÜLÜ ===")
import os
import bridge as B
st = B.status()
check("Köprü yapılandırılmamış durumu düzgün", st["mode"] == "disabled" and "how_to_enable" in st)
os.environ["GENTAHAX_SCRIPT_DIR"] = "/tmp/gh_test_scripts"
st = B.status()
check("Script dizini tanınınca mode=local", st["mode"] == "local")
p = B.write_script("test.lua", "-- test\nprint('x')")
check("Script yazma", p and "test.lua" in p)
c = B.read_script("test.lua")
check("Script okuma", c == "-- test\nprint('x')")
d = B.delete_script("test.lua")
check("Script silme", d is True)

print(f"\n{'='*50}")
print(f"SONUÇ: {ok_count} başarılı, {fail_count} başarısız")
sys.exit(1 if fail_count else 0)
