"""
GENTAHAX MCP — Knowledge Engine
mr_berk edition

Gerçek veri kaynakları:
- OFFICIAL GENTA-HAX-DOCS (github.com/GENTA7740/GENTA-HAX-DOCS)
- GENTAHAX v5.61 GTInternal.dll binary string doğrulaması
  (MD5: 8f95ed4449dc4893f51d5380e31f8055)
"""
import json
import os
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
EXAMPLES_DIR = Path(__file__).parent / "examples"
WATERMARK = "mr_berk"
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load(name):
    with open(DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)

_API_ANDROID = _load("api_android.json")
_API_WINDOWS = _load("api_windows.json")
_SHE = _load("structs_hooks_enums.json")
_PROTOCOL = _load("protocol.json")
_BAN_RULES = _load("ban_rules.json")
_TEMPLATES = _load("templates.json")

# GERÇEK Growtopia item ID veritabanı (github.com/yoshinogaming/growtopia-item-id, items.dat tabanlı)
_ITEMS = _load("items.json")
_ITEMS_BY_ID = {int(k): v for k, v in _ITEMS["items"].items()}
_NAME_TO_ID = {}
for _iid, _nm in sorted(_ITEMS_BY_ID.items()):
    _NAME_TO_ID.setdefault(_nm.lower(), _iid)  # ilk (en düşük ID) kazanır
# Gerçek seed çiftleri — listeden TÜRETİLDİ (asla ID+1 varsayılmadı):
# 'X Seed' adlı item için ID-1 gerçekten 'X' adını taşıyorsa çift kurulur.
_SEED_OF = {}
_BASE_OF = {}
for _iid, _nm in _ITEMS_BY_ID.items():
    if _nm.endswith(" Seed") and _ITEMS_BY_ID.get(_iid - 1) == _nm[:-5]:
        _SEED_OF[_iid - 1] = _iid
        _BASE_OF[_iid] = _iid - 1


def get_api(platform="android"):
    """platform: 'android' | 'windows'"""
    return _API_ANDROID if platform == "android" else _API_WINDOWS

def get_structs():
    return _SHE["structs"]

def get_hooks(platform="android"):
    return _SHE["hooks"][platform]

def get_enums():
    return _SHE["enums"]

def get_protocol():
    return _PROTOCOL

def get_ban_rules():
    return _BAN_RULES

# ---------------------------------------------------------------------------
# Gerçek item ID veritabanı (6832 esya)
# ---------------------------------------------------------------------------

def items_count():
    return len(_ITEMS_BY_ID)


def items_source():
    return _ITEMS["source"]


def item_by_id(item_id):
    """ID -> isim (yoksa None)"""
    try:
        return _ITEMS_BY_ID.get(int(item_id))
    except (TypeError, ValueError):
        return None


def items_search(query, limit=30):
    """Isim/ID arama: önce exact eşleşme, sonra substring. Sonuç: [{'id','name','is_seed'}]"""
    q = str(query).strip().lower()
    if not q:
        return []
    # Saf sayı → exact ID araması (prefix kirliliği olmasın: '2' → 2, 20, 200 DEĞIL sadece 2)
    if q.isdigit():
        iid = int(q)
        if iid in _ITEMS_BY_ID:
            return [{"id": iid, "name": _ITEMS_BY_ID[iid], "is_seed": iid in _BASE_OF}]
    exact = []
    partial = []
    for iid, name in sorted(_ITEMS_BY_ID.items()):
        nl = name.lower()
        if nl == q:
            exact.append(iid)
        elif q in nl:
            partial.append(iid)
        if len(exact) + len(partial) >= max(limit, 60):
            break
    out_ids = exact + [i for i in partial if i not in exact]
    return [{"id": i, "name": _ITEMS_BY_ID[i], "is_seed": i in _BASE_OF}
            for i in out_ids[:limit]]


def item_resolve(query):
    """'Dirt' / '2' gibi sorguyu TEK bir (id, name) çiftine çevirir.
    Belirsizse candidates listesiyle döner (asla tahmin etmez)."""
    results = items_search(query, limit=10)
    if not results:
        return {"resolved": False, "reason": "not_found", "candidates": []}
    # exact isim eşleşmesi varsa onu al
    q = str(query).strip().lower()
    for r in results:
        if r["name"].lower() == q:
            return {"resolved": True, "id": r["id"], "name": r["name"]}
    if q.isdigit() and len(results) == 1:
        return {"resolved": True, "id": results[0]["id"], "name": results[0]["name"]}
    if len(results) == 1:
        return {"resolved": True, "id": results[0]["id"], "name": results[0]["name"]}
    return {"resolved": False, "reason": "ambiguous",
            "candidates": [{"id": r["id"], "name": r["name"]} for r in results[:10]]}


def seed_of(item_id):
    """Item'in GERÇEK seed ID'si (listedeki çiftlerden; yoksa None)."""
    return _SEED_OF.get(int(item_id))


def base_of(item_id):
    """Seed'in GERÇEK ana item ID'si (yoksa None)."""
    return _BASE_OF.get(int(item_id))


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------

def search_api(query, platform="both"):
    """API fonksiyon/struct/hook arama. platform: android|windows|both"""
    query = query.lower().strip()
    results = []
    for plat in (["android", "windows"] if platform == "both" else [platform]):
        for fn in get_api(plat)["functions"]:
            hay = (fn["name"] + " " + fn.get("signature", "") + " " + fn.get("description", "") + " " + fn.get("category", "")).lower()
            if query in hay:
                r = dict(fn)
                r["platform"] = plat
                results.append(r)
    # hooks
    for plat in (["android", "windows"] if platform == "both" else [platform]):
        for h in get_hooks(plat):
            hay = (h["name"] + " " + h.get("description", "")).lower()
            if query in hay:
                r = dict(h)
                r["platform"] = plat
                r["type"] = "hook"
                results.append(r)
    # structs
    for sname, sdata in get_structs().items():
        if query in sname.lower():
            results.append({"name": sname, "type": "struct", "platform": "both"})
    return results


def api_detail(name, platform="android"):
    name_l = name.lower()
    for plat in (["android", "windows"] if platform == "both" else [platform]):
        for fn in get_api(plat)["functions"]:
            if fn["name"].lower() == name_l:
                out = dict(fn)
                out["platform"] = plat
                return out
    return None


def api_names(platform="android"):
    return [fn["name"] for fn in get_api(platform)["functions"]]


def struct_info(name):
    for sname, sdata in get_structs().items():
        if sname.lower() == name.lower():
            return {"name": sname, "fields": sdata}
    return None


def template_list():
    return [
        {"id": t["id"], "name": t["name"], "risk": t["risk"]}
        for t in _TEMPLATES["templates"]
    ]


def template_get(tid):
    for t in _TEMPLATES["templates"]:
        if t["id"] == tid:
            return t
    return None


def examples_list():
    out = []
    if EXAMPLES_DIR.exists():
        for f in sorted(EXAMPLES_DIR.glob("*.lua")):
            out.append({
                "file": f.name,
                "size": f.stat().st_size,
                "source": "OFFICIAL GENTA-HAX-DOCS repo (gerçek, geliştiricinin kendi örnekleri)",
            })
    return out


def example_get(fname):
    safe = Path(fname).name  # path traversal koruması
    p = EXAMPLES_DIR / safe
    if p.exists() and p.suffix == ".lua":
        return p.read_text(encoding="utf-8")
    return None


# ---------------------------------------------------------------------------
# ImGui API (DLL + official examples'tan derlendi)
# ---------------------------------------------------------------------------

IMGUI_FUNCTIONS = [
    "ImGui.Begin", "ImGui.End", "ImGui.BeginChild", "ImGui.EndChild",
    "ImGui.BeginCombo", "ImGui.EndCombo", "ImGui.BeginGroupPanel", "ImGui.EndGroupPanel",
    "ImGui.BeginListBox", "ImGui.EndListBox", "ImGui.BeginTable", "ImGui.EndTable",
    "ImGui.BeginTooltip", "ImGui.EndTooltip", "ImGui.Bullet", "ImGui.Button",
    "ImGui.ButtonWithStripe", "ImGui.Checkbox", "ImGui.Columns", "ImGui.DragFloat",
    "ImGui.DragInt", "ImGui.InputInt", "ImGui.InputText", "ImGui.InputTextMultiline",
    "ImGui.InputTextWithHint", "ImGui.IsItemActive", "ImGui.NextColumn",
    "ImGui.PopID", "ImGui.PopStyleColor", "ImGui.PopTextWrapPos", "ImGui.ProgressBar",
    "ImGui.PushID", "ImGui.PushStyleColor", "ImGui.PushTextWrapPos", "ImGui.RadioButton",
    "ImGui.SameLine", "ImGui.Selectable", "ImGui.Separator", "ImGui.SetCursorPosX",
    "ImGui.SetNextItemWidth", "ImGui.SetNextWindowSize", "ImGui.SetWindowFontScale",
    "ImGui.SliderAngle", "ImGui.SliderFloat", "ImGui.SliderInt", "ImGui.TableNextColumn",
    "ImGui.TableNextRow", "ImGui.TableSetColumnIndex", "ImGui.Text", "ImGui.TextUnformatted",
    "ImGui.TreeNode", "ImGui.TreePop", "ImGui.GetWindowWidth", "ImGui.GetWindowHeight",
    "ImGui.GetContentRegionAvailWidth", "ImGui.GetFontSize",
    "ImGui.ColorConvertFloat4ToU32", "ImGui.GetBackgroundDrawList",
    "ImGui.Col.Text", "ImGui.Cond.Always", "ImGui.FG", "ImGui.BG",
]

# ---------------------------------------------------------------------------
# Ban risk engine
# ---------------------------------------------------------------------------

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
RISK_LABEL_TR = {"low": "DÜŞÜK", "medium": "ORTA", "high": "YÜKSEK"}

def _rule_matches(rule, code):
    pattern = rule.get("pattern", "")
    if not re.search(pattern, code, re.IGNORECASE | re.DOTALL):
        return False
    # context=loop → sadece dongu varsa tetiklenir
    if rule.get("context") == "loop":
        has_loop = any(re.search(lp, code, re.IGNORECASE) for lp in rule.get("loop_patterns", []))
        if not has_loop:
            return False
    # negatives → kodda koruyucu ifade varsa kural atlanır
    for neg in rule.get("negatives", []):
        if neg in code:
            return False
    return True


def analyze_code(code):
    """Lua kodunu ban-riski ve API kullanımı açısından analiz eder (ASLA çalıştırmaz)."""
    findings = []
    for rule in get_ban_rules()["rules"]:
        if _rule_matches(rule, code):
            findings.append({
                "rule_id": rule["id"],
                "level": rule["level"],
                "title": rule["title"],
                "reason": rule["reason"],
                "advice": rule["advice"],
            })

    overall = "low"
    for f in findings:
        if RISK_ORDER[f["level"]] > RISK_ORDER[overall]:
            overall = f["level"]

    # API dogrulama: kullanilan gh_ fonksiyonlari gercek mi?
    known = set()
    for plat in ("android", "windows"):
        known.update(api_names(plat))
    known.update(h["name"] for h in get_hooks("android") + get_hooks("windows"))
    known.update(IMGUI_FUNCTIONS)
    known.update({"sleep", "pairs", "ipairs", "tostring", "tonumber", "math", "string", "table", "os", "io", "print", "pcall", "load", "setmetatable", "require"})

    calls = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", code))
    calls |= set(re.findall(r"\b(ImGui\.[A-Za-z0-9_]+)", code))
    unknown = sorted(c for c in calls if c not in known and not c.startswith(("ImGui.", "gh_")) and c not in
                     {"if", "for", "while", "function", "end", "return", "and", "or", "not", "local", "then", "do", "else", "elseif", "repeat", "until", "true", "false", "nil", "in", "break"})

    # Sozdizimi denge kontrolu (heuristik — gercek dogrulama oyun icinde pcall ile yapilir)
    syntax_issues = _lua_balance_check(code)

    score = 0
    for f in findings:
        score += {"low": 5, "medium": 25, "high": 45}[f["level"]]
    score = min(100, score)
    if syntax_issues:
        score = min(100, score + 5)

    return {
        "risk_level": overall,
        "risk_label_tr": RISK_LABEL_TR[overall],
        "risk_score": score,
        "high_risk_banner": ("⚠️ UYARI: BUNDA BAN RİSKİ VAR! "
                             "Bu kod yüksek riskli işlemler içeriyor — çalıştırırsanız hesabınız kalıcı olarak banlanabilir.")
                            if overall == "high" else None,
        "findings": findings,
        "unknown_functions": unknown,
        "unknown_note": ("Bilinmeyen fonksiyon(lar) — gerçek GENTAHAX API'sinde yok, kod oyunda hata verir: "
                         + ", ".join(unknown)) if unknown else None,
        "syntax_issues": syntax_issues,
        "analyzed_by": f"{WATERMARK} GENTAHAX MCP risk engine v{VERSION}",
    }


def _lua_balance_check(code):
    """Basit Lua blok/parantez denge denetimi (heuristik)."""
    issues = []
    # yorumlari ve stringleri cikar
    stripped = re.sub(r"--\[\[.*?\]\]", "", code, flags=re.DOTALL)
    stripped = re.sub(r"--[^\n]*", "", stripped)
    stripped = re.sub(r'"(?:[^"\\]|\\.)*"', '""', stripped)
    stripped = re.sub(r"'(?:[^'\\]|\\.)*'", "''", stripped)
    for open_c, close_c in (("(", ")"), ("{", "}"), ("[", "]")):
        if stripped.count(open_c) != stripped.count(close_c):
            issues.append(f"Eşleşmeyen {open_c}{close_c} parantezleri")
    # blok anahtar kelime denge kontrolu (kabaca — satir bazli heuristik)
    openers = len(re.findall(r"\bfunction\b", stripped))
    openers += len(re.findall(r"\bif\b[^\n]*\bthen\b", stripped))
    openers += len(re.findall(r"\bfor\b[^\n]*\bdo\b", stripped))
    openers += len(re.findall(r"\bwhile\b[^\n]*\bdo\b", stripped))
    enders = len(re.findall(r"\bend\b", stripped))
    if openers != enders:
        issues.append(f"Blok dengesizliği: {openers} açıcı (function/if/for/while) vs {enders} 'end'")
    return issues


def stats():
    return {
        "android_functions": len(_API_ANDROID["functions"]),
        "windows_functions": len(_API_WINDOWS["functions"]),
        "hooks": len(get_hooks("android")) + len(get_hooks("windows")),
        "structs": len(get_structs()),
        "enums": len(get_enums()),
        "cheat_codes": len(get_enums()["CheatCode"]),
        "memory_patch_names": len(get_enums()["MemoryPatchNames"]["names"]),
        "packet_types": len(get_enums()["PacketType"]),
        "variant_functions_verified": len(_PROTOCOL["variant_list"]["verified_from_dll_v561"]["names"]),
        "ban_rules": len(get_ban_rules()["rules"]),
        "templates": len(_TEMPLATES["templates"]),
        "imgui_functions": len(IMGUI_FUNCTIONS),
        "examples": len(examples_list()),
        "items_db_count": items_count(),
        "items_db_source": _ITEMS["source"]["repo"],
        "items_db_seed_pairs": len(_SEED_OF),
    }
