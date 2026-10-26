#!/usr/bin/env python3
"""
GENTAHAX MCP Server — mr_berk edition
======================================
Growtopia GENTAHAX v5.61 için EKSİKSİZ AI araç seti.

VERİ KAYNAĞI (SAHTE DEĞİL — GERÇEK):
  • OFFICIAL GENTA-HAX-DOCS (github.com/GENTA7740/GENTA-HAX-DOCS)
  • GENTAHAX v5.61 GTInternal.dll binary string doğrulaması
    (MD5: 8f95ed4449dc4893f51d5380e31f8055)
  • Lua 5.4.6 motoru, 57 Android + 18 Windows API fonksiyonu,
    10 hook, 32 cheat kodu, 19 bellek yaması, 39 paket tipi,
    DLL'den doğrulanmış variant fonksiyonları

ÇALIŞTIRMA:
  pip install fastmcp
  python server.py            # stdio (Claude Desktop / Cursor / VS Code)
  GENTAHAX_SCRIPT_DIR="C:\\...\\Script" python server.py   # canlı köprü ile

Filigran: mr_berk
"""
import json
import os
from typing import Optional

from fastmcp import FastMCP

import knowledge as K
import bridge as B

WATERMARK = "mr_berk"
VERSION = "1.0.0"

mcp = FastMCP(
    f"GENTAHAX MCP — {WATERMARK} edition",
    instructions=(
        "Bu MCP, Growtopia GENTAHAX v5.61 Lua script geliştirmek için GERÇEK verilerle eğitilmiştir. "
        "Kural 1: Kod çalıştırmadan ÖNCE mutlaka gh_code_analyze ile ban riskini kontrol et, "
        "YÜKSEK risk varsa kullanıcıyı 'BUNDA BAN RİSKİ VAR' diye uyar. "
        "Kural 2: Fonksiyon imzaları için gh_api_detail / gh_api_search kullan, asla uydurma. "
        "Kural 3: Canlı oyun verisi için köprü gerekiyor (gh_device_status)."
    ),
)

# ===========================================================================
# BÖLÜM 1 — BİLGİ TABANI (offline, her zaman çalışır)
# ===========================================================================

@mcp.tool
def gh_about() -> str:
    """MCP hakkında: sürüm, veri kaynakları, içerdiği gerçek veri istatistikleri ve mr_berk filigranı."""
    s = K.stats()
    return json.dumps({
        "name": f"GENTAHAX MCP — {WATERMARK} edition",
        "version": VERSION,
        "watermark": WATERMARK,
        "engine": "Lua 5.4.6 (GENTAHAX v5.61)",
        "data_sources": [
            "OFFICIAL GENTA-HAX-DOCS — github.com/GENTA7740/GENTA-HAX-DOCS (geliştiricinin resmi dokümantasyonu)",
            "GENTAHAX v5.61 GTInternal.dll binary doğrulaması (MD5 8f95ed4449dc4893f51d5380e31f8055)",
        ],
        "knowledge_stats": s,
        "platforms": ["android", "windows"],
        "safety": "Ban-risk sınıflandırıcı entegre — yüksek riskli kodlarda çalıştırma öncesi zorunlu uyarı",
    }, ensure_ascii=False, indent=2)


@mcp.tool
def gh_api_search(query: str, platform: str = "both") -> str:
    """API fonksiyonu / hook / struct ara (gerçek GENTAHAX API'sinde). platform: android|windows|both.
    Örnek: query='tile' → checkTile, getTile, getExtraTile, Tile struct..."""
    if platform not in ("android", "windows", "both"):
        return "HATA: platform 'android', 'windows' veya 'both' olmalı"
    results = K.search_api(query, platform)
    if not results:
        return f"'{query}' için sonuç yok. gh_api_list ile tam listeye bakın."
    out = []
    for r in results[:30]:
        t = r.get("type", "function")
        if t == "hook":
            out.append(f"[HOOK/{r['platform']}] {r['name']}({r['params']}) — {r['description'][:120]}")
        elif t == "struct":
            out.append(f"[STRUCT] {r['name']} — alanlar için gh_struct_info")
        else:
            out.append(f"[FN/{r['platform']}] {r['signature']} — risk:{r.get('risk','?')} — {r['description'][:120]}")
    return "\n".join(out) + f"\n\n({len(results)} sonuç — detay için gh_api_detail)"


@mcp.tool
def gh_api_list(platform: str = "android") -> str:
    """Platformun TÜM gerçek Lua API fonksiyonlarını listeler (isim + imza + risk)."""
    if platform not in ("android", "windows"):
        return "HATA: platform 'android' veya 'windows' olmalı"
    api = K.get_api(platform)
    lines = [f"GENTAHAX {platform.upper()} API — {len(api['functions'])} fonksiyon (kaynak: {api['source']})",
             f"Script yolu: {api['script_path']}", ""]
    cats = {}
    for fn in api["functions"]:
        cats.setdefault(fn["category"], []).append(f"  {fn['signature']}  [risk:{fn.get('risk','?')}]")
    for cat in sorted(cats):
        lines.append(f"== {cat.upper()} ==")
        lines.extend(cats[cat])
        lines.append("")
    return "\n".join(lines)


@mcp.tool
def gh_api_detail(name: str) -> str:
    """Bir fonksiyonun TAM detayı: imza, açıklama, örnek kullanım, ban riski. Örnek: name='sendPacket'"""
    for plat in ("android", "windows"):
        fn = K.api_detail(name, plat)
        if fn:
            return json.dumps(fn, ensure_ascii=False, indent=2)
    return (f"'{name}' bulunamadı. Doğru isimler: " +
            ", ".join(K.api_names("android")[:15]) + " ... — gh_api_list ile tamamına bakın.")


@mcp.tool
def gh_struct_info(name: str) -> str:
    """Struct alanlarını göster. Örnek: name='NetAvatar', 'TankPacketStruct', 'TileExtra', 'ItemInfo'"""
    si = K.struct_info(name)
    if si:
        return json.dumps(si, ensure_ascii=False, indent=2)
    return "Struct yok. Mevcut: " + ", ".join(K.get_structs().keys())


@mcp.tool
def gh_hooks_list(platform: str = "android") -> str:
    """Tüm hook'ları (oyun olay tetikleyicileri) imzalarıyla listeler."""
    hooks = K.get_hooks(platform)
    out = [f"GENTAHAX {platform.upper()} HOOK'LARI ({len(hooks)}):", ""]
    for h in hooks:
        out.append(f"• {h['name']}({h['params']})")
        out.append(f"  {h['description']}")
        out.append(f"  Örnek: {h['example']}")
        out.append("")
    return "\n".join(out)


@mcp.tool
def gh_cheats_list() -> str:
    """32 CheatCode (toggleCheat) + 19 bellek yaması (patchMemoryByName) — DLL'den doğrulanmış isimler."""
    e = K.get_enums()
    out = ["== CheatCode (toggleCheat(code, state)) =="]
    for code, label in e["CheatCode"].items():
        out.append(f"  {code:>2} = {label}")
    out.append("")
    out.append("== Bellek Yaması (patchMemoryByName / restoreMemoryByName) — DLL v5.61 doğrulamalı ==")
    out.append("  " + ", ".join(e["MemoryPatchNames"]["names"]))
    return "\n".join(out)


@mcp.tool
def gh_packet_types() -> str:
    """39 Growtopia raw paket tipi (PACKET_*) + ENet flag tablosu."""
    e = K.get_enums()
    out = ["== Growtopia Raw Packet Type (TankPacketStruct.type) =="]
    for v, n in e["PacketType"].items():
        out.append(f"  {v:>2} = {n}")
    out.append("")
    out.append("== ENet Packet Flag (Windows SendPacketRaw ilk parametresi) ==")
    for v, n in e["ENetPacketFlag"].items():
        out.append(f"  {v} = {n}")
    return "\n".join(out)


@mcp.tool
def gh_variant_guide() -> str:
    """GERÇEK VARIANT LIST rehberi: variantlist_t yapısı, DLL'den doğrulanmış variant fonksiyonları
    (OnTalkBubble, OnDialogRequest, OnFishStrike...), sendVariant kullanımı ve OnVarlist hook'u."""
    v = K.get_protocol()["variant_list"]
    return json.dumps(v, ensure_ascii=False, indent=2)


@mcp.tool
def gh_protocol_guide() -> str:
    """Growtopia text paket protokolü: DLL'de doğrulanmış action'lar (join_request, drop, wrench...),
    paket formatları, tile_change/punch/wrench raw paket notları."""
    p = K.get_protocol()
    return json.dumps({"text_packet_protocol": p["text_packet_protocol"],
                       "raw_packet_notes": p["raw_packet_notes"]}, ensure_ascii=False, indent=2)


@mcp.tool
def gh_imgui_api() -> str:
    """GENTAHAX ImGui Lua API'si — DLL + resmi örneklerden derlenen 57 widget/çizim fonksiyonu.
    OnRender hook'u içinde GUI ve ESP çizimi için kullanılır."""
    return ("GENTAHAX ImGui API (Lua — OnRender içinde kullan):\n" +
            "\n".join(f"  {f}" for f in K.IMGUI_FUNCTIONS) +
            "\n\nDetaylı kullanım örneği için: gh_example_get('Genta_ImDemo.lua')")


@mcp.tool
def gh_examples_list() -> str:
    """Resmî örnek scriptleri listeler (GENTA-HAX-DOCS repo'sundan, gerçek)."""
    ex = K.examples_list()
    if not ex:
        return "Örnek yok"
    return json.dumps({"kaynak": "OFFICIAL GENTA-HAX-DOCS (github.com/GENTA7740/GENTA-HAX-DOCS)", "examples": ex},
                      ensure_ascii=False, indent=2)


@mcp.tool
def gh_example_get(file: str) -> str:
    """Resmî örnek scriptin tam kaynak kodu. file: 'Genta_ImDemo.lua' | 'extender.lua' | 'Genta_DiscordWebhook.lua'"""
    src = K.example_get(file)
    if src:
        return f"-- KAYNAK: OFFICIAL GENTA-HAX-DOCS — {file}\n\n{src}"
    return "Bulunamadı. Mevcut: Genta_ImDemo.lua, extender.lua, Genta_DiscordWebhook.lua"


@mcp.tool
def gh_templates_list() -> str:
    """Hazır script şablonlarını listeler (Auto Collect, ESP, Varlist Logger, ImGui Panel...)."""
    return json.dumps(K.template_list(), ensure_ascii=False, indent=2)


@mcp.tool
def gh_template_get(template_id: str) -> str:
    """Şablonun tam Lua kodunu döner. template_id: auto_collect | varlist_logger | chat_command |
    esp_overlay | tree_harvest | imgui_panel | webhook_notify"""
    t = K.template_get(template_id)
    if t:
        return json.dumps(t, ensure_ascii=False, indent=2)
    return "Şablon yok. IDs: " + ", ".join(x["id"] for x in K.template_list())


@mcp.tool
def gh_item_lookup(query: str) -> str:
    """Yaygın esya ID'lerinde arama + GERÇEK çözüm önerisi: script içinde getItemByName() kullan.
    Not: Growtopia'ın 10.000+ esyalik items.dat veritabanı OYUNUN İÇİNDEDİR;
    getItemByName/getItemByID her zaman doğru canlı sonucu verir."""
    q = query.lower()
    items = [i for i in K._TEMPLATES["verified_common_items"] if q in i["name"].lower() or q == str(i["id"])]
    if not items:
        return (f"'{query}' cerceve listede yok. SCRIPTTE ASLA ID HARDCODE ETME — şunu kullan:\n"
                f"  local item = getItemByName('{query}')\n"
                f"  if item then logToConsole(item.name .. ' | rarity: ' .. item.rarity) end\n"
                f"Bu, oyunun kendi canlı items.dat'ini sorgular: GUARANTILI gerçek sonuç.")
    out = [f"{i['id']:>5} = {i['name']} — {i['desc']}" for i in items]
    return ("Çerçeve eşleşmeleri (oyun içinde getItemByName ile doğrula):\n" + "\n".join(out) +
            "\n\nScript önerisi: getItemByName('" + items[0]["name"] + "')")


# ===========================================================================
# BÖLÜM 2 — KOD ANALİZİ & BAN RİSKİ (asla çalıştırmaz)
# ===========================================================================

@mcp.tool
def gh_code_analyze(code: str) -> str:
    """Lua kodunu ÇALIŞTIRMADAN analiz eder: ban riski (yüksek/orta/düşük + puan),
    bilinmeyen fonksiyon tespiti (gerçek API'de olmayan), sözdizimi dengesi.
    YÜKSEK riskte '⚠️ BUNDA BAN RİSKİ VAR' uyarısı döner. Her gh_run_lua öncesi otomatik çağrılır."""
    r = K.analyze_code(code)
    return json.dumps(r, ensure_ascii=False, indent=2)


@mcp.tool
def gh_ban_risk(code: str) -> str:
    """Sadece ban riski raporu: eşleşen kurallar, sebepler, düzeltme önerileri ve genel 0-100 risk puanı."""
    r = K.analyze_code(code)
    out = {
        "risk": f"{r['risk_label_tr']} ({r['risk_score']}/100)",
        "banner": r["high_risk_banner"],
        "matched_rules": r["findings"],
        "syntax_issues": r["syntax_issues"],
        "engine": r["analyzed_by"],
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


@mcp.tool
def gh_safety_rules() -> str:
    """Ban riski sınıflandırma kurallarının tam listesi ve genel güvenlik rehberi.
    Hangi davranışlar neden yasaklanır, nasıl koruna bakılır."""
    br = K.get_ban_rules()
    out = {
        "seviyeler": br["levels"],
        "kurallar": [{"id": r["id"], "level": r["level"], "title": r["title"],
                      "reason": r["reason"], "advice": r["advice"]} for r in br["rules"]],
        "genel_uyari": br["general_warnings"]["tr"],
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


@mcp.tool
def gh_snippet(name: str, platform: str = "android") -> str:
    """Bir API fonksiyonu için kullanıma hazır kod parçası + risk notu döner.
    Örnek: name='sendVariant' → gerçek imza + örnek + ban riski."""
    fn = K.api_detail(name, platform)
    if not fn:
        return f"'{name}' yok — gh_api_search kullanın"
    return (f"✅ {fn['signature']}\n\n"
            f"Açıklama: {fn['description']}\n\n"
            f"Örnek:\n```lua\n{fn['example']}\n```\n\n"
            f"Ban riski: {fn.get('risk', '?').upper()}"
            + ("\n⚠️ BUNDA BAN RİSKİ VAR — dikkatli kullan!" if fn.get("risk") == "high" else ""))


# ===========================================================================
# BÖLÜM 3 — CİHAZ KÖPRÜSÜ (canlı oyun)
# ===========================================================================

def _bridge_or_hint():
    st = B.status()
    if not st.get("configured"):
        return None, ("⚠️ Köprü kapalı.\n" + st.get("how_to_enable", "") +
                      "\n\nBilgi araçları (Bölüm 1-2) her zaman çalışır; canlı veri için köprü kurun: gh_bridge_deploy")
    return st, None


@mcp.tool
def gh_device_status() -> str:
    """Cihaz/köprü durumu: script dizini, adb, köprü canlı mı (PONG testi), kurulu scriptler."""
    return json.dumps(B.status(), ensure_ascii=False, indent=2)


@mcp.tool
def gh_bridge_deploy() -> str:
    """gentahax_bridge.lua'yı cihaza yazar (Windows: Script klasörü, Android: adb push).
    Sonra GENTAHAX menüden bir kez elle çalıştırmanız gerekir — talimat döner."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    try:
        r = B.deploy_bridge()
        return json.dumps({"ok": True, **r, "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool
def gh_run_lua(code: str, force: bool = False) -> str:
    """⭐ Lua kodunu OYUN İÇİNDE çalıştırır (canlı). ÖNCE otomatik ban-risk analizi yapar:
    • YÜKSEK risk → kullanıcıya 'BUNDA BAN RİSKİ VAR' uyarısı gösterilir; force=false ise ÇALIŞTIRILMAZ.
    • ORTA risk → uyarıyla birlikte çalıştırılır.
    Köprü gerekli (gh_bridge_deploy)."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    analysis = K.analyze_code(code)
    if analysis["risk_level"] == "high" and not force:
        return json.dumps({
            "calistirildi": False,
            "uyari": analysis["high_risk_banner"],
            "risk_seviyesi": f"{analysis['risk_label_tr']} ({analysis['risk_score']}/100)",
            "sebepler": [f["title"] + " — " + f["advice"] for f in analysis["findings"] if f["level"] == "high"],
            "ne_yapmali": "Kodun bu kısmını düzeltin (sleep ekleyin, döngü sınırlayın) ya da riski kabul ediyorsanız force=true ile tekrar deneyin.",
            "watermark": WATERMARK,
        }, ensure_ascii=False, indent=2)
    try:
        result = B.exec_lua(code, risk_level=analysis["risk_level"])
        return json.dumps({
            "calistirildi": True,
            "risk_seviyesi": f"{analysis['risk_label_tr']} ({analysis['risk_score']}/100)",
            "uyari": ("⚠️ ORTA ban riski — uzun süreli kullanımda dikkat edin." if analysis["risk_level"] == "medium"
                      else "Risk: DÜŞÜK"),
            "risk_bulgu_sayisi": len(analysis["findings"]),
            "sonuc": str(result)[:4000],
            "watermark": WATERMARK,
        }, ensure_ascii=False, indent=2)
    except PermissionError as e:
        return json.dumps({"calistirildi": False, "uyari": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"calistirildi": False, "hata": str(e),
                           "ipucu": "gentahax_bridge.lua oyunda açık mı? gh_device_status ile kontrol edin."},
                          ensure_ascii=False)


@mcp.tool
def gh_world_snapshot() -> str:
    """Canlı dünya anlık görüntüsü: dünya adı, boyut, oyuncu sayısı, yerdeki eşyalar, senin durumun."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    try:
        r = B.exec_lua("return mcp_world_snapshot()", timeout=8)
        return json.dumps({"world": str(r), "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"hata": str(e)}, ensure_ascii=False)


@mcp.tool
def gh_player_info() -> str:
    """Dünyadaki TÜM oyuncuların canlı bilgisi: isim, netID, ülke, gems, pozisyon, ping."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    try:
        r = B.exec_lua("return mcp_player_info()", timeout=8)
        return json.dumps({"players": str(r), "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"hata": str(e)}, ensure_ascii=False)


@mcp.tool
def gh_inventory_dump() -> str:
    """Envanterinin canlı dökümü: eşya adı + ID + miktar (oyunun gerçek items.dat'inden)."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    try:
        r = B.exec_lua("return mcp_inventory_dump()", timeout=10)
        return json.dumps({"inventory": str(r), "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"hata": str(e)}, ensure_ascii=False)


@mcp.tool
def gh_stop_scripts() -> str:
    """Tüm Lua thread'lerini öldürür, tüm hook'ları kaldırır (killAllThread + RemoveHooks). Acil durdurma."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    try:
        r = B.exec_lua("RemoveHooks() killAllThread() return 'durdu'", timeout=6)
        return json.dumps({"ok": True, "sonuc": str(r), "not": "Köprü thread'i de durur — yeniden çalıştırmak için gentahax_bridge.lua'yı tekrar Execute edin.",
                           "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "hata": str(e)}, ensure_ascii=False)


# ===========================================================================
# BÖLÜM 4 — SCRIPT DOSYA YÖNETİMİ
# ===========================================================================

@mcp.tool
def gh_scripts_list() -> str:
    """Cihazdaki (Windows Script klasörü / Android adb) tüm .lua scriptlerini listeler."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    scripts = B.list_scripts()
    return json.dumps({"scripts": scripts or [], "adet": len(scripts or [])}, ensure_ascii=False, indent=2)


@mcp.tool
def gh_script_read(name: str) -> str:
    """Cihazdaki bir scriptin içeriğini okur. Örnek: name='auto_collect.lua'"""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    content = B.read_script(name)
    if content is None:
        return f"'{name}' okunamadı — gh_scripts_list ile kontrol edin."
    return content[:15000]


@mcp.tool
def gh_script_write(name: str, code: str, execute: bool = False) -> str:
    """Cihaza script YAZAR. Ban-risk analizi otomatik yapılır ve uyarı döner.
    execute=true ise yazdikten sonra köprü üzerinden hemen çalıştırır (risk yüksekse reddeder)."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    analysis = K.analyze_code(code)
    path = B.write_script(name, code)
    if path is None:
        return "Yazılamadı (aynı isim var? overwrite parametresi için kodu güncelleyin)"
    out = {
        "yazildi": path,
        "risk_seviyesi": f"{analysis['risk_label_tr']} ({analysis['risk_score']}/100)",
        "uyari": analysis["high_risk_banner"] or ("⚠️ ORTA risk — dikkatli kullanın." if analysis["risk_level"] == "medium" else "Risk: DÜŞÜK"),
        "watermark": WATERMARK,
    }
    if execute:
        if analysis["risk_level"] == "high":
            out["calistirildi"] = False
            out["sebep"] = "Yüksek ban riski — önce düzeltin veya gh_run_lua force=true kullanın."
        else:
            try:
                r = B.exec_lua(f"local c=loadfile('{B.script_dir()}/{name}') return c and c() or 'dosya okunamadi'", timeout=10)
                out["calistirildi"] = True
                out["sonuc"] = str(r)[:2000]
            except Exception as e:
                out["calistirildi"] = False
                out["hata"] = str(e)
    return json.dumps(out, ensure_ascii=False, indent=2)


@mcp.tool
def gh_script_delete(name: str) -> str:
    """Cihazdan script siler."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    ok = B.delete_script(name)
    return json.dumps({"silindi": bool(ok), "name": name}, ensure_ascii=False)


@mcp.tool
def gh_logs_read(tail: int = 80) -> str:
    """GENTAHAX lua_logs.txt dosyasının son satırları — script çıktılarını ve hataları buradan izleyin."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    logs = B.read_logs(tail)
    return logs or "(log yok)"


# ===========================================================================
# BÖLÜM 5 — GÜVENLİK & META
# ===========================================================================

@mcp.tool
def gh_safe_mode(enable: Optional[bool] = None) -> str:
    """Güvenli mod anahtarı: AÇIKKEN yüksek ban-riskli kodların otomatik çalıştırılması reddedilir.
    enable vermezseniz sadece mevcut durumu döner."""
    global B_SAFE
    current = os.environ.get("GENTAHAX_SAFE_MODE", "1") == "1"
    if enable is None:
        return json.dumps({
            "safe_mode": current,
            "anlam": "AÇIK → gh_run_lua yüksek riskli kodu force=false ile ÇALIŞTIRMAZ",
            "kapatma": "Ortam değişkeni: GENTAHAX_SAFE_MODE=0",
        }, ensure_ascii=False)
    note = "Not: kalıcı değişiklik için GENTAHAX_SAFE_MODE ortam değişkenini güncelleyin."
    return json.dumps({"safe_mode": current, "istek": enable, "not": note}, ensure_ascii=False)


@mcp.tool
def gh_watermark() -> str:
    """mr_berk filigran bilgisi ve imza bloğu (scriptlere eklemek için hazır)."""
    return json.dumps({
        "watermark": WATERMARK,
        "imza_bloku": (
            "-- ============================================\n"
            "-- mr_berk — GENTAHAX MCP\n"
            f"-- Üretim: GENTAHAX MCP v{VERSION}\n"
            "-- Veri: OFFICIAL GENTA-HAX-DOCS + DLL v5.61 doğrulaması\n"
            "-- ============================================"
        ),
        "toast": "doToast(4, 3000, 'mr_berk GENTAHAX MCP')",
        "log": "logToConsole('mr_berk GENTAHAX MCP aktif')",
    }, ensure_ascii=False, indent=2)


@mcp.tool
def gh_learn_lua_gentahax(topic: str = "start") -> str:
    """Adım adım GENTAHAX Lua eğitim rehberi. topic: start | hooks | packets | cheats | imgui | threads | farming"""
    guides = {
        "start": (
            "GENTAHAX LUA — HIZLI BAŞLANGIÇ (gerçek API):\n"
            "1) Script dosyan: Android → Android/media/GENTAHAX/Script/benim.lua | Windows → Script/benim.lua\n"
            "2) İlk script:\n```lua\n"
            "local me = getLocal()\n"
            "logToConsole('Merhaba ' .. me.name .. '! Gems: ' .. me.gems)\n"
            "doToast(1, 3000, 'mr_berk ilk script çalıştı!')\n"
            "```\n"
            "3) Hook ekle (her karede çalışır):\n```lua\n"
            "AddHook('OnRender', 'ilk', function(dt) ImGui.Begin('mr_berk')\n"
            "  ImGui.TextUnformatted('Delta: ' .. dt) ImGui.End() end)\n```\n"
            "4) Thread ile arka plan döngüsü:\n```lua\n"
            "runThread(function() while true do sleep(1000)\n"
            "  logToConsole('tic') end end, 'saat')\n```\n"
            "Konu başlıkları: hooks, packets, cheats, imgui, threads, farming"
        ),
        "hooks": (
            "HOOK'lar (gerçek, DLL doğrulamalı):\n"
            "• OnTextPacket(flag, packet) — sunucu text paketleri (action|log ...)\n"
            "• OnVarlist(vars, netid) — TÜM oyun olayları; vars[0]=olay adı (OnTalkBubble, OnSpawn...)\n"
            "• OnTouch(x, y) — dokunma (dunya koordinatı)\n"
            "• OnRender(dt) — her kare; ImGui/ESP burada\n"
            "• OnRawPacket(raw) / OnGameUpdatePacket(raw) — TankPacketStruct ham paketler\n"
            "• OnENetInit(ip, port) — bağlantı kurulurken (yalnızca izle!)\n"
            "Örnek sohbet dinleyici:\n```lua\n"
            "AddHook('OnVarlist', 'chat', function(vars, netid)\n"
            "  if vars[0] == 'OnTalkBubble' then\n"
            "    logToConsole('[Sohbet] ' .. tostring(vars[2]))\n"
            "  end\n\nend)\n```"
        ),
        "packets": (
            "PAKET GÖNDERME (gerçek imzalar):\n"
            "• Text: sendPacket(2, 'action|input\\ntext|/go START')\n"
            "• Raw: sendPacketRaw(false, {type=3, state=16, value=18, x=50, y=30, punchx=50, punchy=30})\n"
            "• Variant: sendVariant({'OnConsoleMessage', 'mesaj'}, -1, 0)\n"
            "• Resmi yardımcılar (tercih et): requestTileChange(x,y,id), requestCollect(x,y,id)\n"
            "⚠️ HER PAKET DÖNGÜSÜNE sleep(250+) KOY — yoksa ban riski YÜKSEK."
        ),
        "cheats": (
            "CHEAT KONTROLÜ (gerçek kodlar):\n"
            "• toggleCheat(26, true) → Mod Fly aç\n"
            "• getCheat(26) → açık mı?\n"
            "• patchMemoryByName('Mod Fly') / restoreMemoryByName('Mod Fly')\n"
            "DLL'den doğrulanmış yama isimleri: Mod Fly, Ghost Mode, Night Vision, No Clip,\n"
            "Anti Gravity, Ghost Ship, Anti portal, Path Finder, Skip Update v2, Dev Mode, Fast Fruits...\n"
            "Tam liste: gh_cheats_list"
        ),
        "imgui": (
            "IMGUI (OnRender içinde):\n"
            "```lua\nAddHook('OnRender', 'ui', function(dt)\n"
            "  ImGui.Begin('mr_berk panel')\n"
            "  local c, v = ImGui.Checkbox('Mod Fly', fly)\n"
            "  if c then fly = v; toggleCheat(26, fly) end\n"
            "  if ImGui.Button('Kapat') then RemoveHook('ui') end\n"
            "  ImGui.End()\nend)\n```\n"
            "57 fonksiyonun tam listesi: gh_imgui_api — örnek: gh_example_get('Genta_ImDemo.lua')"
        ),
        "threads": (
            "THREAD'ler (UI donmasın):\n"
            "• runThread(fn, 'etiket') — arka plan\n"
            "• killThread('etiket') / killAllThread()\n"
            "• getThreadsID() → çalışananlar\n"
            "⚠️ Thread içinde de sleep şart — sonsuz sleep'siz döngü istemciyi kilitler."
        ),
        "farming": (
            "AUTO-FARM MANTIĞI (gerçek API ile):\n"
            "1) getWorldObject() → yerdeki eşyalar; requestCollect(x, y, id)\n"
            "2) getExtraTile(x, y).ready → hasat hazır; punch paketi type=3 state=18\n"
            "3) findPath(x, y) → yürü (Windows: FindPath(x, y, delay))\n"
            "4) En iyi şablon: gh_template_get('auto_collect') ve gh_template_get('tree_harvest')\n"
            "⚠️ Tüm adımlar arasına rastgele 200-600ms sleep → bot tespitini azaltır."
        ),
    }
    return guides.get(topic, "topic: start | hooks | packets | cheats | imgui | threads | farming")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    if "--list-tools" in sys.argv:
        # Kayıtlı araçları yazdır (test amaçlı)
        import asyncio
        async def _l():
            tools = await mcp.get_tools()
            print(f"{len(tools)} araç kayıtlı:")
            for name in sorted(tools):
                print(f"  • {name}")
        asyncio.run(_l())
    else:
        print(f"[GENTAHAX MCP — {WATERMARK} edition v{VERSION}] stdio sunucusu başlıyor...",
              file=sys.stderr)
        mcp.run()  # stdio transport (Claude Desktop vb.)
