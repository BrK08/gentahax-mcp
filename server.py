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
import re
import time
from typing import Optional

from fastmcp import FastMCP

import knowledge as K
import bridge as B
import autotest as AT

WATERMARK = "mr_berk"
VERSION = "1.5.0"

mcp = FastMCP(
    f"GENTAHAX MCP — {WATERMARK} edition",
    instructions=(
        "Bu MCP, Growtopia GENTAHAX v5.61 Lua script geliştirmek için GERÇEK verilerle eğitilmiştir. "
        "Kural 1: Kod çalıştırmadan ÖNCE mutlaka gh_code_analyze ile ban riskini kontrol et, "
        "YÜKSEK risk varsa kullanıcıyı 'BUNDA BAN RİSKİ VAR' diye uyar. "
        "Kural 2: Fonksiyon imzaları için gh_api_detail / gh_api_search kullan, asla uydurma. "
        "Kural 3: Canlı oyun verisi için köprü gerekiyor (gh_device_status). "
        "Kural 4: Eşya ID sorularında GERÇEK 6832 esyalik veritabanı (gh_item_db_search / gh_item_db_info) "
        "+ oyunun canlı items.dat doğrulaması (getItemByName) birlikte kullan. "
        "Kural 5: 'Dünyada kaç tane X var?' gibi canlı sorularda gh_world_count_item kullan — "
        "sadece okuma yapar, gerçek sayıyı döner, ban riski yoktur. "
        "Kural 6: Hazır mod isteklerinde ('mod fly aç/kapat') gh_cheat_set kullan — script yazma. "
        "Kural 7: 'yaz/çalıştır ve çalışıyor mu bak' isteklerinde gh_auto_test kullan; dönen "
        "kullaniciya_soz alanını kullanıcıya aynen söyle, HATA'da önerilen yamayla tekrar dene."
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
            "GERÇEK Growtopia item ID veritabanı — github.com/yoshinogaming/growtopia-item-id "
            "(6832 esya, items.dat tabanlı; ID 2=Dirt, 112=Gems doğrulandı)",
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
    """Eşya ID arama — GERÇEK 6832 esyalik Growtopia veritabanında (items.dat tabanlı, GitHub'dan).
    Örnek: query='Dirt' → ID 2 (+ Dirt Seed ID 3). Canlı doğrulama önerisi: getItemByName()."""
    res = K.item_resolve(query)
    if not res["resolved"]:
        if res["reason"] == "ambiguous":
            cands = "\n".join(f"  {c['id']:>5} = {c['name']}" for c in res["candidates"])
            return (f"'{query}' belirsiz — hangisini kastettin?\n{cands}\n\n"
                    f"Daha net yaz (ör. 'Dirt' yerine tam isim).")
        return (f"'{query}' 6832 esyalik GERÇEK veritabanında yok. "
                "Script içi canlı çözüm:\n"
                "  local item = getItemByName('" + query + "')\n"
                "  if item then logToConsole(item.name .. ' | rarity: ' .. item.rarity) end")
    seed_id = K.seed_of(res["id"])
    base_id = K.base_of(res["id"])
    return json.dumps({
        "sorgu": query,
        "id": res["id"],
        "isim": res["name"],
        "seed_id": seed_id,
        "seed_isim": K.item_by_id(seed_id) if seed_id else None,
        "ana_item": (f"{base_id} = {K.item_by_id(base_id)}") if base_id else None,
        "veritabani": "6832 esya — github.com/yoshinogaming/growtopia-item-id (items.dat tabanlı, GERÇEK)",
        "canli_dogrulama": f"getItemByID({res['id']}).name veya getItemByName('{res['name']}') — "
                           "oyunun kendi items.dat'inden OKUR, her zaman doğrudur",
        "world_sayimi": f"gh_world_count_item('{res['name']}') ile dünyada kaç tane olduğunu GERÇEK sayabilirsin",
        "watermark": WATERMARK,
    }, ensure_ascii=False, indent=2)


@mcp.tool
def gh_item_db_search(query: str, limit: int = 25) -> str:
    """GERÇEK item ID veritabanında serbest arama (6832 esya: isim veya sayı sorgusu).
    Örnek: query='dirt' → Dirt(2), Dirt Seed(3), Cave Dirt... | query='2' → sadece ID 2.
    Sonuçlar: [ID] isim (SEED işaretli)."""
    limit = max(1, min(int(limit), 60))
    results = K.items_search(query, limit)
    if not results:
        return f"'{query}' için sonuç yok — yazımı kontrol et (ör. 'Dirt', 'dirt seed', '2')."
    lines = [f"{r['id']:>5} = {r['name']}{' [SEED]' if r['is_seed'] else ''}" for r in results]
    total = len(K.items_search(query, 10000))
    return ("GERÇEK veritabanı sonucu (6832 esya — items.dat tabanlı):\n" + "\n".join(lines) +
            f"\n\n({len(results)}/{total} sonuç gösteriliyor — detay için gh_item_db_info)")


@mcp.tool
def gh_item_db_info(item_id: int) -> str:
    """Item ID'nin TAM bilgisi: isim, seed eşleri, komşu ID'ler — GERÇEK veritabanından.
    Örnek: item_id=2 → Dirt | seed: 3 (Dirt Seed) | canlı doğrulama: getItemByID(2)."""
    name = K.item_by_id(item_id)
    if name is None:
        return f"ID {item_id} veritabanında yok (0..{K.items_count()-1} aralığında dene)."
    seed_id = K.seed_of(item_id)
    base_id = K.base_of(item_id)
    neighbors = {str(i): K.item_by_id(i) for i in range(max(0, item_id - 2), min(K.items_count(), item_id + 3))}
    return json.dumps({
        "id": item_id,
        "isim": name,
        "tur": "seed" if base_id else "esya",
        "seed_id": seed_id,
        "seed_isim": K.item_by_id(seed_id) if seed_id else None,
        "ana_item_id": base_id,
        "ana_item_isim": K.item_by_id(base_id) if base_id else None,
        "komsu_idler": neighbors,
        "canli_dogrulama": f"getItemByID({item_id}).name == '{name}' olmalı — değilse oyun sürümü farklıdır",
        "world_sayimi": f"gh_world_count_item('{name}') ile dünyadaki gerçek adedi say",
        "watermark": WATERMARK,
    }, ensure_ascii=False, indent=2)


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


# --------------------------- DÜNYA EŞYA SAYIMI (gerçek) ----------------------

_WC_LUA = """
local w = getWorld()
if not w then return 'ERR|NO_WORLD' end
local target = {target_id}
local tiles = getTile()
local nfg, nbg, total = 0, 0, 0
local samples = {}
for _, t in pairs(tiles) do
    if t and t.fg ~= nil then
        total = total + 1
        if t.fg == target then
            nfg = nfg + 1
            if #samples < 8 then
                local px, py = -1, -1
                if t.pos then px = t.pos.x or -1; py = t.pos.y or -1 end
                samples[#samples + 1] = tostring(px) .. ',' .. tostring(py)
            end
        end
        if t.bg == target then nbg = nbg + 1 end
    end
end
local live = getItemByID(target)
return string.format('WORLD:%s|SIZE:%dx%d|SCANNED:%d|FG:%d|BG:%d|TOTAL:%d|LIVE_NAME:%s|SAMPLES:%s',
    tostring(w.name), w.width, w.height, total, nfg, nbg, nfg + nbg,
    (live and live.name) and tostring(live.name) or '?', table.concat(samples, ';'))
"""


@mcp.tool
def gh_world_count_item(item: str) -> str:
    """⭐ 'Dünyada kaç tane X var?' sorusuna GERÇEK cevap: canlı oyundaki TÜM tile'ları tarar
    (getTile vektörü) ve itemin ön plan (fg) + arka plan (bg) adedini sayar.
    SADECE OKUR — paket gönderilmez, ban riski YOKTUR. item: isim ('Dirt') veya ID ('2').
    Oyunun canlı items.dat'i ile çapraz doğrulama yapılır (LIVE_NAME). Köprü gerekir.
    Örnek: item='Dirt' → "BUYDIRT dünyasında 214 adet Dirt var (162 fg + 52 bg, 5400 tile tarandı)"."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    res = K.item_resolve(item)
    if not res["resolved"]:
        if res["reason"] == "ambiguous":
            cands = "\n".join(f"  {c['id']:>5} = {c['name']}" for c in res["candidates"])
            return f"'{item}' belirsiz — hangisini sayayım?\n{cands}"
        return f"'{item}' GERÇEK veritabanında (6832 esya) bulunamadı. Yazımı kontrol et."
    tid, tname = res["id"], res["name"]
    lua = _WC_LUA.replace("{target_id}", str(tid))
    analysis = K.analyze_code(lua)  # okuma kodu → düşük risk olmalı; şeffaflık için raporla
    try:
        r = B.exec_lua(lua.strip(), timeout=25, risk_level=analysis["risk_level"])
    except Exception as e:
        return json.dumps({"hata": str(e), "ipucu": "gentahax_bridge.lua oyunda açık mı? gh_device_status"},
                          ensure_ascii=False)
    s = str(r)
    if s.startswith("ERR|NO_WORLD"):
        return json.dumps({"sonuc": "Şu an bir dünyada değilsin — oyunu aç, bir dünyaya gir ve tekrar dene."},
                          ensure_ascii=False)
    parts = {}
    for kv in s.split("|"):
        if ":" in kv:
            k, v = kv.split(":", 1)
            parts[k] = v
    live_name = parts.get("LIVE_NAME", "?")
    verified = (live_name.lower() == tname.lower())
    fg, bg, total = (int(parts.get("FG", 0)), int(parts.get("BG", 0)), int(parts.get("TOTAL", 0)))
    return json.dumps({
        "soru": f"'{parts.get('WORLD','?')} dünyasında kaç tane {tname} var?",
        "cevap": f"{total} adet {tname} (ID {tid}) — ön plan: {fg}, arka plan: {bg}",
        "dunya": parts.get("WORLD"),
        "dunya_boyutu": parts.get("SIZE"),
        "taranan_tile": int(parts.get("SCANNED", 0)),
        "on_plan_fg": fg,
        "arka_plan_bg": bg,
        "toplam": total,
        "ornek_konumlar": parts.get("SAMPLES", "").split(";") if parts.get("SAMPLES") else [],
        "canli_dogrulama": {
            "oyun_dedi": live_name,
            "veritabani_dedi": tname,
            "uyusuyor": verified,
            "not": "Oyunun canlı items.dat'i ile 6832'lik veritabanı çapraz doğrulandı" if verified
                   else "DİKKAT: oyunun adı farklı — oyun sürümündeki ID eşlemesi farklı olabilir",
        },
        "ban_riski": "YOK — sadece okuma (RAM taraması), sunucuya hiçbir paket gönderilmedi",
        "watermark": WATERMARK,
    }, ensure_ascii=False, indent=2)


@mcp.tool
def gh_world_census() -> str:
    """Canlı dünyanın TAM eşya sayımı: TÜM tile'lar taranır, en çok kullanılan eşyalar
    ön plan/arka plan ayrı olarak listelenir. 'Bu dünyada ne var?' sorusunun gerçek cevabı.
    SADECE OKUR — ban riski yok. Köprü gerekir."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    lua = """
local w = getWorld()
if not w then return 'ERR|NO_WORLD' end
local tiles = getTile()
local fgc, bgc, total = {}, {}, 0
for _, t in pairs(tiles) do
    if t and t.fg ~= nil then
        total = total + 1
        if t.fg and t.fg > 0 then fgc[t.fg] = (fgc[t.fg] or 0) + 1 end
        if t.bg and t.bg > 0 then bgc[t.bg] = (bgc[t.bg] or 0) + 1 end
    end
end
local function top(c)
    local a = {}
    for id, n in pairs(c) do a[#a + 1] = {id, n} end
    table.sort(a, function(x, y) return x[2] > y[2] end)
    local o = {}
    for i = 1, math.min(#a, 20) do
        local it = getItemByID(a[i][1])
        o[#o + 1] = tostring(a[i][1]) .. '=' .. tostring(it and it.name or '?') .. ' x' .. tostring(a[i][2])
    end
    return table.concat(o, ';')
end
local function n(c) local m = 0 for _ in pairs(c) do m = m + 1 end return m end
return string.format('WORLD:%s|SIZE:%dx%d|TILES:%d|DISTINCT_FG:%d|DISTINCT_BG:%d|TOP_FG:%s|TOP_BG:%s',
    tostring(w.name), w.width, w.height, total, n(fgc), n(bgc), top(fgc), top(bgc))
"""
    try:
        r = B.exec_lua(lua.strip(), timeout=25)
    except Exception as e:
        return json.dumps({"hata": str(e), "ipucu": "gentahax_bridge.lua oyunda açık mı? gh_device_status"},
                          ensure_ascii=False)
    s = str(r)
    if s.startswith("ERR|NO_WORLD"):
        return json.dumps({"sonuc": "Şu an bir dünyada değilsin — oyunu aç, bir dünyaya gir ve tekrar dene."},
                          ensure_ascii=False)
    parts = {}
    for kv in s.split("|"):
        if ":" in kv:
            k, v = kv.split(":", 1)
            parts[k] = v
    def _pairlist(x):
        if not x:
            return []
        out = []
        for p in x.split(";")[:20]:
            if "=" in p:
                i, rest = p.split("=", 1)
                nm, cnt = rest.rsplit(" x", 1)
                out.append({"id": int(i), "isim": nm, "adet": int(cnt)})
        return out
    return json.dumps({
        "dunya": parts.get("WORLD"),
        "boyut": parts.get("SIZE"),
        "toplam_tile": int(parts.get("TILES", 0)),
        "farkli_on_plan_esya": int(parts.get("DISTINCT_FG", 0)),
        "farkli_arka_plan_esya": int(parts.get("DISTINCT_BG", 0)),
        "en_cok_on_plan": _pairlist(parts.get("TOP_FG")),
        "en_cok_arka_plan": _pairlist(parts.get("TOP_BG")),
        "ban_riski": "YOK — sadece okuma, paket gönderilmedi",
        "watermark": WATERMARK,
    }, ensure_ascii=False, indent=2)


# --------------------------- ŞABLON-DIŞ İSTEK ÜRETECİ ------------------------

_FARM_LUA = """
-- mr_berk GENTAHAX ad-hoc script — 'Dunyadaki tum {NAME} bloklarini kir ve cikan gem'i soyle'
-- Uretildi: gh_farm_script_gen | Hedef ID: {ID} ({NAME}) — GERCEK items.dat veritabanindan
-- RISK: YUKSEK — dongude punch paketi (farm bot paterni). Insan benzeri rastgele delay'ler
--        eklendi ama sunucu farm botlarini analiz edebilir. Degerli hesapta kullanma!
pcall(function() math.randomseed(os.time()) end)

local TARGET = {ID}
local NAME = '{NAME}'

-- FAZ A — hizli sayim (senkron, koprunun zaman asimina sigar)
local w = getWorld()
if not w then return 'ERR|NO_WORLD' end
local me = getLocal()
if not me then return 'ERR|NO_LOCAL' end
local targets = {}
for _, t in pairs(getTile()) do
    if t and t.fg == TARGET and t.pos then
        targets[#targets + 1] = { x = t.pos.x, y = t.pos.y }
    end
end
local gems_before = me.gems or 0
if #targets == 0 then
    return string.format('FARM_RESULT|WORLD:%s|TARGET:%d|NAME:%s|FOUND:0|BROKEN:0|GEMS_BEFORE:%d|GEMS_AFTER:%d|GEMS_GAINED:0',
        tostring(w.name), TARGET, NAME, gems_before, gems_before)
end

-- FAZ B — kirma thread'i (uzun surer; ilerleme ve sonuc lua_logs.txt'ye duser)
runThread(function()
    local broken = 0
    doLog(string.format('AUTOTEST|START|farm_{ID}|hedef:%d', #targets))
    for _, p in ipairs(targets) do
        local t = checkTile(p.x, p.y)
        if t and t.fg == TARGET then
            sendPacketRaw(false, { type = 3, state = 16, value = 18,
                                   x = p.x, y = p.y, punchx = p.x, punchy = p.y })
            broken = broken + 1
            if broken % 10 == 0 then
                doLog(string.format('[mr_berk farm] %d/%d %s kirildi', broken, #targets, NAME))
            end
            sleep(math.random(450, 1200))
            if broken % 25 == 0 then sleep(math.random(2000, 4500)) end
        end
    end
    sleep(4000)  -- gem'ler sunucudan birkaç saniye icinde duser
    local me2 = getLocal()
    local gems_after = (me2 and me2.gems) or gems_before
    doLog(string.format('AUTOTEST|OK|farm_{ID}|kirilan:%d|gems_kazanc:%d', broken, gems_after - gems_before))
    doLog(string.format('FARM_RESULT|WORLD:%s|TARGET:%d|NAME:%s|FOUND:%d|BROKEN:%d|GEMS_BEFORE:%d|GEMS_AFTER:%d|GEMS_GAINED:%d',
        tostring(w.name), TARGET, NAME, #targets, broken, gems_before, gems_after, gems_after - gems_before))
    logToConsole('[mr_berk farm] tamam — rapor lua_logs.txt icinde (gh_logs_read ile oku)')
    doToast(1, 3000, 'Farm bitti (mr_berk)')
end, 'farm_{ID}')

return string.format('QUEUED|WORLD:%s|TARGET:%d|NAME:%s|FOUND:%d|GEMS_BEFORE:%d|THREAD:farm_{ID}|NOT:kirma_basladi_rapor_icin_gh_logs_read',
    tostring(w.name), TARGET, NAME, #targets, gems_before)
"""


@mcp.tool
def gh_farm_script_gen(item: str) -> str:
    """⭐ ŞABLON-DIŞ İSTEK ÜRETEÇ: 'dünyadaki tüm X'leri kır ve çıkan toplam gem'i söyle' gibi
    hazır şablonu OLMAYAN istekler için hedefe özel TAM Lua scripti üretir (kopyala-kullan hazır).
    Akış: isim → GERÇEK veritabanından ID çözümü (belirsizse adayları listeler, ASLA tahmin etmez)
    → tam script (getTile tarama → sendPacketRaw punch → getLocal().gems önce/sonra →
    FARM_RESULT raporu doLog ile lua_logs.txt'ye).
    ⚠️ Üretilen script YÜKSEK ban riski taşır (döngüde punch = farm bot paterni).
    Kullanım: 1) dönen scripti gh_script_write ile Script klasörüne kaydet veya küçük dünya için
    gh_run_lua ile çalıştır, 2) script kessin, 3) gh_logs_read ile FARM_RESULT satırını oku.
    Örnek: item='Pepper' → ID 4570 çözülür, 37 hedef bulunursa '37 pepper kırıldı, +58 gems' gibi
    GERÇEK rapor döner."""
    res = K.item_resolve(item)
    if not res.get("resolved"):
        cands = K.items_search(item, 12)
        return json.dumps({
            "hata": f"'{item}' kesin çözülemedi — tahmin ETMİYORUM, hangisini kastettin?",
            "adaylar": [{"id": c["id"], "isim": c["name"], "seed": c["is_seed"]} for c in cands],
            "ipucu": "Tam isimle tekrar çağır: örn. gh_farm_script_gen('Pepper') veya gh_farm_script_gen('Pepper Tree')",
            "watermark": WATERMARK,
        }, ensure_ascii=False, indent=2)
    tid, tname = res["id"], res["name"]
    code = _FARM_LUA.replace("{ID}", str(tid)).replace("{NAME}", tname).strip()
    risk = K.analyze_code(code)
    return json.dumps({
        "cozulen": {"id": tid, "isim": tname,
                    "not": f"ID {tid} gerçek veritabanından (6832 eşya) çözüldü — oyunun getItemByID({tid}).name'i ile çapraz doğrulanabilir"},
        "istek": f"'Dünyadaki tüm {tname} bloklarını kır ve çıkan toplam gem'i söyle'",
        "script": code,
        "ban_riski": {
            "seviye": risk["risk_label_tr"],
            "puan": f"{risk['risk_score']}/100",
            "uyari": "⚠️ BUNDA BAN RİSKİ VAR — döngüde punch paketi farm bot paternidir; "
                     "delay'ler insan benzeri ama garanti DEĞİLDİR",
            "kurallar": [f["title"] for f in risk.get("findings", [])][:5],
        },
        "kullanim": [
            f"1) gh_script_write('farm_{tid}.lua', script) ile kaydet — oyunda Lua Executor'dan çalıştır",
            "   (YA DA küçük dünyalarda doğrudan gh_run_lua ile — Faz A anında QUEUED döner)",
            "2) Faz A anında döner: kaç hedef bulunduğu + mevcut gem (QUEUED satırı)",
            "3) Faz B arka planda kırar — ilerleme her 10 blokta lua_logs.txt'ye düşer",
            "4) gh_logs_read ile FARM_RESULT|... satırını oku: FOUND/BROKEN/GEMS_GAINED gerçek sayılar",
        ],
        "durdurma": f"killThread('farm_{tid}')",
        "watermark": WATERMARK,
    }, ensure_ascii=False, indent=2)


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


# ===========================================================================
# BÖLÜM 6 — HAZIR MOD KONTROLÜ · OTOMATİK TEST DÖNGÜSÜ · APK UYUMU (v1.5.0)
# ===========================================================================

def _resolve_cheat(query):
    """Cheat adını/kodunu DLL doğrulamalı CheatCode enum'undan çözer.
    Belirsizse adayları döndürür — ASLA tahmin etmez."""
    e = K.get_enums()["CheatCode"]
    q = str(query).strip().lower()
    if q.isdigit():
        if q in e:
            return {"resolved": True, "code": int(q), "label": e[q]}
        return {"resolved": False, "reason": "not_found", "candidates": []}

    def _norm(s):
        return s.lower().replace(" ", "").replace("_", "").replace("-", "")

    exact = [(int(k), v) for k, v in e.items() if v.lower() == q or _norm(v) == _norm(q)]
    if len(exact) == 1:
        return {"resolved": True, "code": exact[0][0], "label": exact[0][1]}
    if len(exact) > 1:
        return {"resolved": False, "reason": "ambiguous",
                "candidates": sorted([{"kod": c, "mod": v} for c, v in exact], key=lambda x: x["kod"])}
    subs = [(int(k), v) for k, v in e.items() if q in v.lower()]
    if len(subs) == 1:
        return {"resolved": True, "code": subs[0][0], "label": subs[0][1]}
    if len(subs) > 1:
        return {"resolved": False, "reason": "ambiguous",
                "candidates": sorted([{"kod": c, "mod": v} for c, v in subs], key=lambda x: x["kod"])}
    close = AT.closest_function(q, list(e.values()))
    if close:
        return {"resolved": False, "reason": "did_you_mean", "suggestion": close[0]}
    return {"resolved": False, "reason": "not_found", "candidates": []}


_GORSEL_MODLAR = {"night vision", "show door label", "show sign label", "can see ghost"}


@mcp.tool
def gh_cheat_set(cheat: str, state: Optional[bool] = None) -> str:
    """⭐ HAZIR MOD AÇ/KAPAT — 'mod fly aç' gibi istekler için. GENTAHAX'ta zaten VAR OLAN
    32 hazır modu (Mod Fly, Ghost Mode, No Clip, Night Vision, Anti Gravity...) AI ile
    kontrol eder: toggleCheat uygular, getCheat ile DOĞRULAR. cheat: mod adı ('Mod Fly',
    'modfly', 'fly') veya kodu ('26'). state: True=aç, False=kapat, None=sadece durumu oku."""
    res = _resolve_cheat(cheat)
    if not res.get("resolved"):
        out = {"istek": cheat, "uygulandi": False, "watermark": WATERMARK}
        if res.get("reason") == "ambiguous":
            out["hata"] = "Birden fazla mod eşleşiyor — hangisini kastettin?"
            out["adaylar"] = res["candidates"]
        elif res.get("reason") == "did_you_mean":
            out["not"] = (f"'{res['suggestion']}' modunu mu demek istedin? "
                          "Tam adıyla tekrar çağır (ör. gh_cheat_set('{res['suggestion']}', true)).")
        else:
            out["hata"] = f"'{cheat}' DLL doğrulamalı 32 mod listesinde yok."
            out["ipucu"] = "Tam liste: gh_cheats_list — doğru adı oradan al"
        return json.dumps(out, ensure_ascii=False, indent=2)
    code, label = res["code"], res["label"]
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    try:
        if state is None:
            r = B.exec_lua(f"return tostring(getCheat({code}))", timeout=8)
            acik = "true" in str(r).lower()
            return json.dumps({
                "mod": label, "kod": code, "durum": "AÇIK" if acik else "KAPALI",
                "dogrulama_kaynagi": f"getCheat({code}) → {str(r).strip()}",
                "not": "state=true/false vererek açıp kapatabilirsin",
                "watermark": WATERMARK}, ensure_ascii=False, indent=2)
        lua = (f"toggleCheat({code}, {'true' if state else 'false'}) "
               f"sleep(150) return tostring(getCheat({code}))")
        r = B.exec_lua(lua, timeout=8)
        dogrulandi = ("true" in str(r).lower()) == bool(state)
        return json.dumps({
            "mod": label, "kod": code,
            "istenen": "AÇ" if state else "KAPAT",
            "sonuc": ("AÇIK ✓ — getCheat doğruladı" if (dogrulandi and state)
                      else "KAPALI ✓ — getCheat doğruladı" if dogrulandi
                      else f"⚠️ UYGULANAMADI — getCheat '{str(r).strip()}' döndü; oyun menüsünden elle dene"),
            "dogrulandi": dogrulandi,
            "ban_notu": ("toggleCheat istemci RAM yamasıdır (paket göndermez) AMA davranışın "
                         "dünyada GÖRÜNÜR — kalabalık dünyada uzun süre açık bırakma!"
                         if state and label.lower() not in _GORSEL_MODLAR
                         else "Görsel/bilgi modu — görünür davranış değişikliği düşük, ban riski düşük"),
            "diger": f"Durum tablosu: gh_cheat_status · bellek yaması alternatifi: patchMemoryByName('{label}')",
            "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"mod": label, "kod": code, "hata": str(e),
                           "ipucu": "gentahax_bridge.lua oyunda açık mı? gh_device_status"},
                          ensure_ascii=False)


@mcp.tool
def gh_cheat_status() -> str:
    """TÜM hazır modların (32 CheatCode) anlık AÇIK/KAPALI durum tablosu — tek köprü
    çağrısında hepsi. 'Hangi modlar açık?' sorusunun GERÇEK cevabı (getCheat ile)."""
    st, hint = _bridge_or_hint()
    if hint:
        return hint
    e = K.get_enums()["CheatCode"]
    codes = sorted(int(k) for k in e)
    arr = "{" + ",".join(str(c) for c in codes) + "}"
    lua = ("local out = {}\n"
           f"for _, c in ipairs({arr}) do out[#out + 1] = c .. '=' .. tostring(getCheat(c)) end\n"
           "return table.concat(out, '|')")
    try:
        r = B.exec_lua(lua, timeout=12)
        durum = {}
        for kv in str(r).split("|"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                try:
                    durum[int(k)] = (v.lower() == "true")
                except ValueError:
                    pass
        tbl = [{"kod": c, "mod": e[str(c)], "durum": ("AÇIK" if durum.get(c) else "KAPALI")}
               for c in codes if c in durum]
        acik = [t["mod"] for t in tbl if t["durum"] == "AÇIK"]
        return json.dumps({
            "istek": "Hangi hazır modlar açık?",
            "toplam_mod": len(codes), "okunabildi": len(tbl),
            "acik_olanlar": acik if acik else "(hiçbiri açık değil)",
            "tablo": tbl,
            "kapatma": "gh_cheat_set('<mod adı>', false)",
            "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    except Exception as ex:
        return json.dumps({"hata": str(ex), "ipucu": "gh_device_status ile köprüyü kontrol et"},
                          ensure_ascii=False)


# ------------------------- OTOMATİK TEST DÖNGÜSÜ ----------------------------

def _syntax_precheck(code):
    """Söz dizimi ön-kontrolü: kodu SADECE DERLER (load) — ASLA ÇALIŞTIRMAZ.
    Oyun içi fonksiyonlar (getLocal, toggleCheat...) DERLEMEYE takılmaz; yalnız gerçek
    gramer hatası (eksik 'end', parantez) yakalanır. Oyun fonksiyonlarının varlığına
    dair TEK yetkili kaynak GENTAHAX executor'ıdır — bu kontrol asla 'fonksiyon yok'
    HATASI ÜRETMEZ. Dönen: {'sonuc': 'geçti'|'hata'|'atıldı', 'detay': str}"""
    try:
        import lupa
    except ImportError:
        return {"sonuc": "atıldı", "detay": "lupa kurulu değil — atlandı (zaten oyun executor'ı derleyecek)"}
    try:
        lr = lupa.LuaRuntime()
        lr.globals()["__mcp_code"] = code
        lr.execute("__mcp_f, __mcp_e = load(__mcp_code)")
        ok = bool(lr.eval("__mcp_f ~= nil"))
        err = str(lr.eval("tostring(__mcp_e)"))
        if ok:
            return {"sonuc": "geçti", "detay": "derleme OK — kod ÇALIŞTIRILMADI, oyun fonksiyonları false hata vermez"}
        return {"sonuc": "hata", "detay": err[:300] if err and err != "nil" else "söz dizimi hatası"}
    except Exception as e:
        return {"sonuc": "atıldı", "detay": f"ön-kontrol atlandı: {e}"}


@mcp.tool
def gh_auto_test(script: str, watch: int = 20, force: bool = False) -> str:
    """⭐⭐ OTOMATİK TEST DÖNGÜSÜ — 'scripti ÇALIŞTIR, loglarına bak, çalışıyor mu söyle':
    scripti GENTAHAX'ın KENDİ Lua executor'ında çalıştırır, lua_logs.txt'yi izler ve
    ÇALIŞIYOR / DEVAM_EDIYOR / HATA kararını YALNIZCA executor dönüşüne + loglara göre verir.
    Hata varsa sınıflandırır + çözüm önerir + yanlış fonksiyon adıysa YAMALI script üretir
    (yamayı geri verirsin → döngü kapanır). Söz dizimi ön-kontrolü sadece DERLER
    (çalıştırmaz) — oyun içi fonksiyonlar bundan false hata VERMEZ. Yüksek riskli kod
    force=false iken çalıştırılmaz (⚠️ BUNDA BAN RİSKİ VAR uyarısı döner)."""
    watch = max(3, min(int(watch), 90))
    analysis = K.analyze_code(script)
    if analysis["risk_level"] == "high" and not force:
        return json.dumps({
            "sonuc": "REDDEDİLDİ", "calistirildi": False,
            "uyari": analysis["high_risk_banner"],
            "risk_seviyesi": f"{analysis['risk_label_tr']} ({analysis['risk_score']}/100)",
            "ne_yapmali": "Riskli kısmı düzelt (sleep ekle, döngüyü sınırla) ya da force=true ile riski kabul et.",
            "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    pre = _syntax_precheck(script)
    if pre["sonuc"] == "hata":
        return json.dumps({
            "sonuc": "HATA", "calistirildi": False,
            "sozdizimi_on_kontrol": pre,
            "hata": {"sinif": "SYNTAX", "satir": pre["detay"], "hedef": None,
                     "aciklama": "Kod derlenmedi — executor'a gönderilmedi bile"},
            "cozum": AT.suggest_fix({"sinif": "SYNTAX", "satir": pre["detay"]}),
            "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    st, hint = _bridge_or_hint()
    if hint:
        return json.dumps({"sonuc": "CIHAZ_YOK", "calistirildi": False,
                           "sozdizimi_on_kontrol": pre,
                           "ipucu": "Canlı test için köprü gerekli — " + str(hint)[:200],
                           "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    try:
        before = B.read_logs(400) or ""
    except Exception:
        before = ""
    try:
        sync = str(B.exec_lua(script.strip(), timeout=25, risk_level=analysis["risk_level"]))
        exec_err = None
    except Exception as e:
        sync, exec_err = str(e), str(e)
    sync_text = sync if exec_err is None else f"Lua hatası: {sync}"

    def _logs_now():
        try:
            return B.read_logs(400) or ""
        except Exception:
            return before
    new_lines = AT.new_log_lines(before, _logs_now())
    verdict = AT.parse_execution(sync_text, new_lines)
    t0 = time.time()
    while verdict["sonuc"] == "DEVAM_EDIYOR" and (time.time() - t0) < watch:
        time.sleep(2)
        new_lines = AT.new_log_lines(before, _logs_now())
        verdict = AT.parse_execution(sync_text, new_lines)

    api_names = K.api_names("android") + K.api_names("windows")
    hata = verdict.get("hata")
    fix = AT.suggest_fix(hata, api_names) if hata else None
    yama = None
    if hata and hata.get("sinif") == "MISSING_FN" and hata.get("hedef"):
        adaylar = AT.closest_function(hata["hedef"], api_names)
        if len(adaylar) == 1:
            patched, n = AT.patch_missing_fn(script, hata["hedef"], adaylar[0])
            if n > 0:
                yama = {"eski_fonksiyon": hata["hedef"], "yeni_fonksiyon": adaylar[0],
                        "degisiklik_sayisi": n, "script": patched}
    sonuc = verdict["sonuc"]
    if sonuc == "CALISIYOR":
        soz = "✅ Script ÇALIŞIYOR — " + (verdict["kanit"][0][:160] if verdict["kanit"] else "hatasız tamamlandı")
    elif sonuc == "DEVAM_EDIYOR":
        soz = ("⏳ Script çalışıyor, hâlâ devam ediyor — ilerlemesi kanıt satırlarında; "
               "bir süre sonra gh_logs_read ile nihai sonucu oku")
    elif sonuc == "CIHAZ_YOK":
        soz = "❌ Köprü/cihaz yanıt vermiyor — gentahax_bridge.lua'yi oyunda çalıştır, tekrar dene"
    else:
        soz = "❌ Script HATA verdi — " + (fix["teshis"][:160] if fix else "loglara bak")
    return json.dumps({
        "sonuc": sonuc,
        "kullaniciya_soz": soz,
        "kanit": verdict["kanit"],
        "sozdizimi_on_kontrol": pre,
        "risk_seviyesi": f"{analysis['risk_label_tr']} ({analysis['risk_score']}/100)",
        "hata": hata,
        "cozum": fix,
        "yama": yama,
        "yama_kullanimi": ("yama.script'i gh_auto_test'e geri ver → düzeltilmiş hâl tekrar test edilir "
                           "(AI böylece döngüyü kapatır)" if yama else
                           ("Hata düzeltildikten sonra gh_auto_test ile tekrar çağır" if hata else None)),
        "izlenen_sure_sn": round(time.time() - t0, 1),
        "watermark": WATERMARK}, ensure_ascii=False, indent=2)


# ------------------------------ APK UYUM TESTİ -------------------------------

@mcp.tool
def gh_compat_check() -> str:
    """⭐ APK GÜNCELLEMESİ sonrası uyumluluk testi: 'GENTAHAX yeni sürüme güncellendi,
    MCP bozuldu mu?' 57 Android + 18 Windows API fonksiyonunu CANLI oyunda tek tek
    yoklar (type(_G['x']) == 'function'), eksikleri ve etkilenen şablonları listeler.
    Köprü kapalıysa offline kontrol listesi + GUNCELLEME.md senaryolarını döner.
    Karar: TAM UYUMLU / KISMİ / KÖPRÜ KIRIK."""
    android_names = K.api_names("android")
    windows_names = K.api_names("windows")
    db_bilgi = {
        "analiz_edilen_surum": "GENTAHAX v5.61 (GTInternal.dll, MD5 8f95ed4449dc4893f51d5380e31f8055)",
        "bilinen_android_fonksiyon": len(android_names),
        "bilinen_windows_fonksiyon": len(windows_names),
        "item_veritabani": f"{K.items_count()} eşya — APK'dan BAĞIMSIZ (Growtopia items.dat kaynaklı, güncellenmezse de eski sürümle çalışır)",
    }

    def _probe_lua(names):
        arr = "{" + ",".join(f"'{n}'" for n in names) + "}"
        return ("local names = " + arr + "\n"
                "local okn, miss = 0, {}\n"
                "for _, n in ipairs(names) do\n"
                "  if type(_G[n]) == 'function' then okn = okn + 1 else miss[#miss + 1] = n end\n"
                "end\n"
                "return 'OK:' .. okn .. '|MISSING:' .. table.concat(miss, ',')")

    def _parse(s):
        ok_n, missing = 0, []
        for part in str(s).split("|"):
            if part.startswith("OK:"):
                try:
                    ok_n = int(part[3:] or 0)
                except ValueError:
                    ok_n = 0
            if part.startswith("MISSING:"):
                missing = [m for m in part[8:].split(",") if m]
        return ok_n, missing

    st, hint = _bridge_or_hint()
    if hint:
        return json.dumps({
            "sonuc": "OFFLINE — köprü kapalı, canlı yoklama yapılamadı",
            "bilgi_tabani": db_bilgi,
            "apk_guncellemesi_olursa_3_senaryo": [
                {"senaryo": "A — Küçük güncelleme, Lua API aynı", "olasılık": "en sık",
                 "ne_olur": "Her şey çalışmaya devam eder", "kontrol": "gh_device_status → PONG geliyorsa OK"},
                {"senaryo": "B — Bazı fonksiyonlar değişti",
                 "ne_olur": "O fonksiyonu kullanan şablonlar hata verir; geri kalanı çalışır",
                 "kontrol": "köprüyü kurup bu aracı (gh_compat_check) tekrar çağır — eksikler listelenir"},
                {"senaryo": "C — Köprü mekanizması kırıldı",
                 "ne_olur": "Scriptler cihaza ulaşamaz (PONG gelmez)",
                 "ne_yapilir": "Yeni APK yeniden analiz edilip data/api_*.json güncellenir (dosya takası)"},
            ],
            "mimarlik": "MCP bilgisi kodda gömülü DEĞİL — data/*.json düz dosyalarında; "
                        "APK değişse bile uyum veri dosyası yenilenerek sağlanır",
            "detayli_rehber": "GUNCELLEME.md (repo kökünde)",
            "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    try:
        ra = str(B.exec_lua(_probe_lua(android_names), timeout=15))
    except Exception as e:
        return json.dumps({
            "sonuc": "KÖPRÜ KIRIK (Senaryo C)",
            "bilgi_tabani": db_bilgi,
            "hata": str(e)[:200],
            "teshis": "Köprü dosyaları yapılandırılmış ama oyundan yanıt gelmiyor — "
                      "APK güncellemesi köprü mekanizmasını kırmış VEYA bridge script oyunda çalışmıyor",
            "ne_yapmali": ["1) gh_device_status → detaya bak",
                           "2) gh_bridge_deploy + oyunda gentahax_bridge.lua'yı yeniden Execute et",
                           "3) Hâlâ yoksa: yeni APK yeniden analiz edilmeli (data/api_*.json güncellenir) — GUNCELLEME.md Senaryo C"],
            "watermark": WATERMARK}, ensure_ascii=False, indent=2)
    a_ok, a_miss = _parse(ra)
    w_ok, w_miss = 0, []
    try:
        rw = str(B.exec_lua(_probe_lua(windows_names), timeout=15))
        w_ok, w_miss = _parse(rw)
    except Exception:
        w_ok, w_miss = 0, []
    client = "ANDROID" if (len(android_names) - a_ok) <= (len(windows_names) - w_ok) else "WINDOWS"
    missing = a_miss if client == "ANDROID" else w_miss
    ok_count = a_ok if client == "ANDROID" else w_ok
    total = len(android_names) if client == "ANDROID" else len(windows_names)
    affected = []
    if missing:
        codes = [K.template_get(t["id"]).get("code", "") or "" for t in K.template_list()]
        codes.append(_FARM_LUA)
        labels = [t["id"] for t in K.template_list()] + ["gh_farm_script_gen (ad-hoc üretici)"]
        for fn in missing:
            for lbl, c in zip(labels, codes):
                if fn + "(" in c:
                    affected.append({"etkilenen": lbl, "fonksiyon": fn})
    if not missing:
        verdict = "TAM UYUMLU — APK güncellemesi MCP'yi etkilememiş, tüm araçlar çalışıyor"
    else:
        verdict = (f"KISMİ UYUM — {len(missing)}/{total} fonksiyon bu sürümde yok; "
                   "etkilenenler listelendi, kalan her şey çalışır")
    return json.dumps({
        "sonuc": verdict,
        "bagli_istemci": client,
        "canli_yoklama": {"bulunan": ok_count, "toplam": total, "eksikler": missing},
        "bilgi_tabani": db_bilgi,
        "etkilenen_sablonlar": affected if affected else "(hiçbir şablon etkilenmedi)",
        "ne_yapmali": (["Eksik fonksiyonları kullanan şablonları kullanma",
                        "data/api_android.json + api_windows.json dosyalarını yeni sürüme göre güncelle "
                        "(düz JSON dosyası — kod değişikliği gerekmez)",
                        "Detay: GUNCELLEME.md Senaryo B"] if missing else
                       ["Hiçbir şey yapmana gerek yok — her şey yolunda", "Periyodik kontrol: APK güncellemesi sonrası bu aracı tekrar çağır"]),
        "watermark": WATERMARK}, ensure_ascii=False, indent=2)


# ------------------------- GENEL AMAÇLI SCRIPT ÜRETİCİ -----------------------

_PLACE_LUA = """-- mr_berk GENTAHAX — hedef: {GOAL}
-- Kalip: place (blok dose) | Uretici: gh_script_gen v1.5.0
-- Esya: {NAME} (ID {ID}) — GERCEK items.dat veritabanindan cozuldu
-- RISK: ORTA — dongude tile_change paketi; rastgele insan benzeri delay eklendi
-- Durdurma: killThread('gh_place')
local w = getWorld()
if not w then return 'ERR|NO_WORLD' end
local me = getLocal()
if not me then return 'ERR|NO_LOCAL' end
local TARGET = {ID}
local N = {COUNT}
pcall(function() math.randomseed(os.time()) end)
runThread(function()
    doLog(string.format('AUTOTEST|START|place|hedef:%d adet %s', N, '{NAME}'))
    local koyulan = 0
    local cx = math.floor(me.pos.x)
    local cy = math.floor(me.pos.y)
    for dy = -1, 2 do
        for dx = -3, 3 do
            if koyulan >= N then break end
            local t = checkTile(cx + dx, cy + dy)
            if t and (t.fg == 0 or t.fg == nil) then
                requestTileChange(cx + dx, cy + dy, TARGET)
                koyulan = koyulan + 1
                sleep(math.random(250, 700))
            end
        end
    end
    doLog(string.format('AUTOTEST|OK|place|koyulan:%d', koyulan))
    logToConsole('mr_berk] place tamam')
end, 'gh_place')
return 'QUEUED|place|esya:{NAME}|adet:' .. N
"""

_SCRIPT_PATTERNS = {
    "farm":    ("kır", "kir", "farm", "punch", "break", "smash", "kes", "kess"),
    "collect": ("topla", "collect", "yerdeki", "düşen", "dusen", "çek", "cek", "pickup"),
    "place":   ("koy", "koyul", "place", "döşe", "dose", "yerleştir", "yerlestir", "blok at"),
    "chat":    ("sohbet", "chat", "konuş", "konus", "cevap", "yanıt", "yanit", "mesaj", "insan gibi"),
    "monitor": ("izle", "monitor", "logla", "kaydet", "rapor", "dinle", "logger", "log tut"),
    "ui":      ("panel", "menü", "menu", "imgui", "arayüz", "arayuz", "overlay", "esp", "gui"),
}


def _guess_item(goal):
    """Hedef metninden eşya adı çıkarmaya çalışır (Türkçe eklerini soyarak: 'pepperları'→'pepper').
    Dönen: (resolve_sözlüğü|None, denenmiş_adaylar). ASLA tahmin etmez — sadece GERÇEK
    veritabanından kesin çözülen adı döndürür."""
    words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]{2,}", goal)
    stop = {"dünyadaki", "dünyada", "dünya", "tüm", "tum", "hepsini", "ve", "bana", "bir", "adet",
            "kır", "kir", "farm", "yap", "olsun", "script", "yaz", "modunu", "modu",
            "topla", "koy", "yerdeki", "düşen", "dusen", "sohbeti", "sohbet",
            # ödül/rapor kelimeleri — farm HEDEFİ değil, sonucu:
            "gems", "gem", "kazanç", "kazanc", "söyle", "soyle", "göster", "goster",
            "rapor", "bak", "bakalım", "kaç", "kac", "ne", "kadar", "toplam", "çıkan", "cikan"}
    tried = []
    spans = []
    for n in (3, 2, 1):
        for i in range(0, max(0, len(words) - n + 1)):
            spans.append(" ".join(words[i:i + n]))
    for cand in spans:
        if cand.lower() in stop or len(cand) < 3:
            continue
        tried.append(cand)
        r = K.item_resolve(cand)
        if r.get("resolved"):
            return r, tried
    for w in words:
        if w.lower() in stop:
            continue
        for cut in range(1, 6):
            stem = w[:-cut] if len(w) - cut >= 3 else None
            if not stem:
                break
            tried.append(stem)
            r = K.item_resolve(stem)
            if r.get("resolved"):
                return r, tried
    return None, tried


@mcp.tool
def gh_script_gen(goal: str) -> str:
    """⭐⭐ GENEL SCRIPT ÜRETİCİ — şablon dışı HER hedef için: 'pepperları kır',
    'yerdeki eşyaları topla', 'sohbeti dinle', 'etrafıma dirt koy', 'mod paneli yap'...
    Doğal dildeki hedefi kalıba ayırır (farm | collect | place | chat | monitor | ui),
    eşyayı GERÇEK 6832'lik veritabanından çözer (çözülemezse ASLA tahmin etmez, sorar),
    scripti YALNIZ GERÇEK API fonksiyonlarıyla kurar, gerçek Lua motorunda DERLER,
    ban riskini analiz eder. Üretilen script AUTOTEST işaretlidir → gh_auto_test ile
    'çalıştır + logları izle + ÇALIŞIYOR/HATA söyle' döngüsü hazırdır."""
    g = str(goal).lower()
    kalip = None
    for k in ("farm", "collect", "place", "chat", "monitor", "ui"):
        if any(w in g for w in _SCRIPT_PATTERNS[k]):
            kalip = k
            break
    if kalip is None:
        return json.dumps({
            "istek": goal,
            "hata": "Hedef tanımadım — hangi kalıp?",
            "kaliplar": {"farm": "'pepperları kır' (blok kırma + gems raporu)",
                         "collect": "'yerdeki eşyaları topla' (otomatik toplama)",
                         "place": "'etrafıma dirt koy' (blok döşeme)",
                         "chat": "'sohbeti dinle / gelenlere cevap ver'",
                         "monitor": "'dünya olaylarını izle ve logla'",
                         "ui": "'menü paneli yap' (ImGui)"},
            "ipucu": "Örnek: gh_script_gen('dünyadaki pepperları kır')",
            "watermark": WATERMARK}, ensure_ascii=False, indent=2)

    item = None
    default_notu = None
    if kalip == "farm":
        item, tried = _guess_item(goal)
        if not item:
            cand = K.items_search(tried[-1], 12) if tried else []
            return json.dumps({
                "istek": goal, "kalip": "farm",
                "hata": "Hangi eşyayı kırayım? — belirttiğin eşya GERÇEK veritabanından çözülemedi, tahmin ETMİYORUM",
                "denenmiş": tried[-8:],
                "adaylar": [{"id": c["id"], "isim": c["name"]} for c in cand[:8]],
                "ipucu": "Tam isimle tekrar dene: gh_script_gen('dünyadaki Pepper'ları kır')",
                "watermark": WATERMARK}, ensure_ascii=False, indent=2)
        code = _FARM_LUA.replace("{ID}", str(item["id"])).replace("{NAME}", item["name"]).strip()
        durdurma = f"killThread('farm_{item['id']}')"
        aciklama = f"{item['name']} (ID {item['id']}) bloklarını tara → kır → gems raporu"
    elif kalip == "place":
        item, tried = _guess_item(goal)
        if not item:
            item = {"id": 2, "name": "Dirt"}
            default_notu = "Eşya belirtilmemiş → Dirt (ID 2, gerçek DB) kullanıldı — başka istersen belirt"
        code = (_PLACE_LUA.replace("{GOAL}", goal).replace("{ID}", str(item["id"]))
                .replace("{NAME}", item["name"]).replace("{COUNT}", "10").strip())
        durdurma = "killThread('gh_place')"
        aciklama = f"Etrafına {item['name']} (ID {item['id']}) döşe"
    else:
        tpl_map = {"collect": "auto_collect", "chat": "human_responder",
                   "monitor": "varlist_logger", "ui": "imgui_panel"}
        t = K.template_get(tpl_map[kalip])
        code = (f"-- mr_berk GENTAHAX — hedef: {goal}\n"
                f"-- Kalıp: {kalip} · doğrulanmış '{t['id']}' şablonu üzerine özelleştirildi\n"
                + t["code"])
        durdurma = "killAllThread() hepsini durdurur — tek tek için gh_stop_scripts"
        aciklama = t.get("name", kalip)
    pre = _syntax_precheck(code)
    risk = K.analyze_code(code)
    return json.dumps({
        "istek": goal,
        "tespit": {"kalip": kalip, "esya": ({"id": item["id"], "isim": item["name"]} if item else None),
                   "aciklama": aciklama},
        "not": default_notu,
        "script": code,
        "sozdizimi": pre,
        "ban_riski": {"seviye": risk["risk_label_tr"], "puan": f"{risk['risk_score']}/100",
                       "uyari": risk["high_risk_banner"] or ("⚠️ ORTA — bot paterni, uzun kullanımda dikkat" if risk["risk_level"] == "medium" else "Düşük")},
        "otomatik_test": "gh_auto_test(script) → çalıştırır, lua_logs.txt'yi izler, '✅ ÇALIŞIYOR' ya da hata+yama döner",
        "kullanim": ["1) Bu scripti gh_auto_test'e ver (çalıştır + log izle + karar) — ÖNERİLEN",
                     "   ya da gh_script_write('genel_script.lua', script) ile kaydet, oyunda Execute et",
                     "2) Hata dönerse gh_auto_test'in önerdiği yamayı uygula, tekrar test et",
                     f"3) Durdurma: {durdurma}"],
        "durdurma": durdurma,
        "watermark": WATERMARK}, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(
        description=f"GENTAHAX MCP sunucusu — {WATERMARK} edition v{VERSION}")
    ap.add_argument("--list-tools", action="store_true", help="araçları listele ve çık")
    ap.add_argument("--http", action="store_true",
                    help="UZAK HTTP modu (Streamable HTTP) — ChatGPT/Claude uygulamalarından "
                         "(Plugins/Custom Connectors) bağlanmak için. stdio yerine HTTP uç verir.")
    ap.add_argument("--host", default="127.0.0.1",
                    help="HTTP dinleme adresi (varsayılan 127.0.0.1 — yalnızca bu makine; "
                         "aynı Wi-Fi'daki telefondan erişmek için 0.0.0.0 yapabilirsin ama DİKKAT)")
    ap.add_argument("--port", type=int, default=8808, help="HTTP portu (varsayılan 8808)")
    args = ap.parse_args()

    if args.list_tools:
        # Kayıtlı araçları yazdır (test amaçlı)
        import asyncio
        async def _l():
            tools = await mcp.get_tools()
            print(f"{len(tools)} araç kayıtlı:")
            for name in sorted(tools):
                print(f"  • {name}")
        asyncio.run(_l())
    elif args.http:
        print(f"[GENTAHAX MCP — {WATERMARK} edition v{VERSION}] HTTP sunucusu başlıyor...")
        print(f"  Yerel uç   : http://{args.host}:{args.port}/mcp")
        print("  Uygulamadan (ChatGPT Plugins / Claude Custom Connectors) bağlanmak için:")
        print(f"    1) Ücretsiz HTTPS tunnel aç:  cloudflared tunnel --url http://localhost:{args.port}")
        print("    2) Çıkan https://xxxx.trycloudflare.com adresinin SONUNA /mcp ekle")
        print("    3) ChatGPT: chatgpt.com/plugins → + → Add custom MCP server")
        print("       Claude  : Customize → Connectors → + Add custom connector (No sign in)")
        print("  ⚠️  Tunnel açıkken URL'yi bilen herkes araçları çağırabilir —")
        print("     işin bitince Ctrl+C ile kapat. (gh_run_lua yine güvenli mod + risk analizli)")
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        print(f"[GENTAHAX MCP — {WATERMARK} edition v{VERSION}] stdio sunucusu başlıyor...",
              file=sys.stderr)
        mcp.run()  # stdio transport (Claude Desktop vb.)
