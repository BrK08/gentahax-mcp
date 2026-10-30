"""
GENTAHAX MCP — Auto-Test Engine (mr_berk edition)
==================================================
Kullanıcı isteği: "Scripti hazırla → GENTAHAX executor'ında çalıştır → loglarına bak
→ çalışıyorsa 'çalışıyor' de → hata varsa AI ona göre hareket etsin."

Bu modül SAF yürütme mantığıdır (fastmcp bağımlılığı YOK — test edilebilir):

  • classify_line()      : GENTAHAX executor'ının lua_logs.txt'ye düştüğü hata
                           satırlarını sınıflandırır (MISSING_FN, NIL_INDEX, ...)
  • parse_execution()    : senkron sonuç + yeni log satırları → KARAR
                           (CALISIYOR / DEVAM_EDIYOR / HATA / CIHAZ_YOK)
  • suggest_fix()        : hata sınıfına göre teşhis + çözüm + sonraki araç
  • closest_function()   : 'getPlayerList' yazıldıysa gerçek API'den 'getPlayerlist' önerir
  • patch_missing_fn()   : yanlış ismin geçtiği kodu YAMALAR (yeni script üretir)

ÖNEMLİ TASARIM KURALI (kullanıcının haklı itirazı üzerine):
  ÇALIŞIYOR/HATA kararı YALNIZCA oyunun kendi executor'ından ve lua_logs.txt'den
  gelir. Bu modül asla "bu fonksiyon oyun dışı Lua'da yok" gerekçesiyle hata ÜRETMEZ
  — oyun içi fonksiyonların varlığı sadece executor'ın kendi hata mesajından okunur.
"""
import difflib
import re

WATERMARK = "mr_berk"

# Üretilen scriptlerin doLog() ile bıraktığı otomatik-test işaretleri
MARKER_START = "AUTOTEST|START"
MARKER_OK = "AUTOTEST|OK"

# ---------------------------------------------------------------------------
# Hata desenleri — GENTAHAX executor'ının lua_logs.txt / dönüş formatındandır
# (sınıf, regex, insan açıklaması)
# ---------------------------------------------------------------------------
ERROR_PATTERNS = [
    ("MISSING_FN",
     r"attempt to call a nil value \(global '([A-Za-z_][A-Za-z0-9_]*)'\)",
     "Çağrılan fonksiyon bu oyunda YOK — isim yanlış yazılmış ya da bu APK sürümünde bulunmuyor"),
    ("MISSING_FN",
     r"attempt to call a nil value \(field '([A-Za-z_][A-Za-z0-9_]*)'\)",
     "Tablo üyesi fonksiyon değil — yanlış üye adı veya yanlış kullanım"),
    ("NIL_INDEX",
     r"attempt to index a nil value \(local '([A-Za-z_][A-Za-z0-9_]*)'\)",
     "Nil yerel değişken — büyük ihtimalle getWorld()/getLocal() boş döndü (dünyada değil misin?)"),
    ("NIL_INDEX",
     r"attempt to index a nil value \(field '([A-Za-z_][A-Za-z0-9_]*)'\)",
     "Nil tablo alanı — dönen nesne boş ya da alan adı yanlış"),
    ("NIL_INDEX",
     r"attempt to index a nil value \(global '([A-Za-z_][A-Za-z0-9_]*)'\)",
     "Nil global — tanımsız isim kullanılmış"),
    ("NIL_ARITH",
     r"attempt to perform arithmetic on a nil value",
     "Nil üzerinde aritmetik — değer hesaplanmamış (oyun verisi gelmeden mi kullanıldı?)"),
    ("NIL_COMPARE",
     r"attempt to compare .+ with nil",
     "Nil karşılaştırma — değer hiç gelmemiş"),
    ("SYNTAX",
     r"(syntax error|unexpected symbol|expected near|<eof>|unexpected token|'\w+' expected)",
     "Söz dizimi hatası — kod derlenmedi"),
    ("LUA_ERR",
     r"(runtime error|error:[^ ]|Error:|luaL_error)",
     "Genel Lua çalışma zamanı hatası"),
]


def classify_line(line):
    """Bir log/sonuç satırını sınıflandırır. Hata yoksa None döner."""
    line = str(line)
    for cls, pat, desc in ERROR_PATTERNS:
        m = re.search(pat, line)
        if m:
            return {"sinif": cls, "satir": line.strip()[:300],
                    "hedef": (m.group(1) if m.groups() else None), "aciklama": desc}
    return None


def _verdict(sonuc, kanit, hata=None):
    return {"sonuc": sonuc, "kanit": [str(k).strip()[:200] for k in (kanit or [])][:6],
            "hata": hata}


def parse_execution(sync_result, log_lines, api_names=None):
    """Senkron executor sonucu + çalıştırmadan SONRAKI yeni log satırları → karar.

    Karar sırası (öncelik):
      1. köprü hataları (zaman aşımı / ulaşılamadı)      → CIHAZ_YOK
      2. ERR|NO_WORLD / ERR|NO_LOCAL                     → HATA (kullanıcı eylemi gerek)
      3. executor/log hata desenleri                     → HATA (sınıflandırılmış)
      4. AUTOTEST|OK veya FARM_RESULT işareti            → CALISIYOR (kesin)
      5. AUTOTEST|START / QUEUED + hata yok              → DEVAM_EDIYOR
      6. hatasız senkron dönüş                           → CALISIYOR
    """
    sync = str(sync_result or "")
    lines = [str(l) for l in (log_lines or [])]
    sync_low = sync.lower()

    # 1) köprü/cihaz hataları
    if any(k in sync_low for k in ("timeout", "zaman aşımı", "zaman asimi", "ulaşılamadı",
                                   "bağlanılamadı", "baglanilamadi")):
        return _verdict("CIHAZ_YOK", [sync],
                        {"sinif": "BRIDGE_DOWN", "satir": sync[:300], "hedef": None,
                         "aciklama": "Köprü yanıt vermedi — gentahax_bridge.lua oyunda açık değil"})

    # 2) önceden tanımlı durum kodları
    for src in [sync] + lines:
        if "ERR|NO_WORLD" in src:
            return _verdict("HATA", [src.strip()], {
                "sinif": "NOT_IN_WORLD", "satir": src.strip()[:200], "hedef": None,
                "aciklama": "Dünyada değilsin — getWorld() boş döndü"})
        if "ERR|NO_LOCAL" in src:
            return _verdict("HATA", [src.strip()], {
                "sinif": "NO_LOCAL", "satir": src.strip()[:200], "hedef": None,
                "aciklama": "Yerel oyuncu henüz yüklenmedi (getLocal() boş)"})

    # 3) lua hata desenleri (önce loglar, sonra senkron metin)
    for src in lines + [sync]:
        if not src:
            continue
        err = classify_line(src)
        if err:
            return _verdict("HATA", [l for l in lines if l.strip()][-4:] or [sync], err)

    # 4) kesin başarı işaretleri
    for l in lines:
        if MARKER_OK in l or "FARM_RESULT" in l:
            return _verdict("CALISIYOR", [l])

    # 5) başladı ama bitmedi
    started = any(MARKER_START in l for l in lines) or sync.startswith("QUEUED")
    if started:
        prog = [l for l in lines if l.strip()]
        return _verdict("DEVAM_EDIYOR", prog[-4:] or [sync])

    # 6) hatasız senkron dönüş
    if sync.strip() and not sync.startswith("HATA"):
        return _verdict("CALISIYOR", [sync])

    return _verdict("DEVAM_EDIYOR", lines[-4:] or ["(log henüz boş — biraz bekle)"])


# ---------------------------------------------------------------------------
# İsim düzeltme + yama
# ---------------------------------------------------------------------------

def closest_function(bad_name, candidates):
    """Yanlış fonksiyon adına en yakın GERÇEK adayları döner (difflib)."""
    if not bad_name or not candidates:
        return []
    cands = list(candidates)
    low = bad_name.lower()
    # birebir (büyük/küçük harf) eşleşme
    for c in cands:
        if c.lower() == low:
            return [c]
    out = difflib.get_close_matches(bad_name, cands, n=3, cutoff=0.55)
    # büyük/küçük harf farkı en yaygın hata: 'getPlayerList' vs 'getPlayerlist'
    if not out:
        for c in cands:
            if c.lower() == low.replace("_", ""):
                return [c]
    return out


def patch_missing_fn(code, old_name, new_name):
    """Koddaki yanlış çağrıları yamalar: old_name( → new_name(
    Dönen: (yamalı_kod, değişiklik_sayısı). Eşleşme yoksa (orijinal, 0)."""
    if not old_name or not new_name or old_name == new_name:
        return code, 0
    patched = re.sub(r"\b" + re.escape(old_name) + r"\s*\(", new_name + "(", code)
    n = len(re.findall(r"\b" + re.escape(old_name) + r"\s*\(", code))
    return patched, n


def suggest_fix(err, api_names=None):
    """Hata sözlüğüne göre {teshis, cozum, sonraki_arac} döner."""
    cls = (err or {}).get("sinif", "LUA_ERR")
    hedef = (err or {}).get("hedef")

    if cls == "MISSING_FN" and hedef:
        adaylar = closest_function(hedef, api_names or [])
        tes = f"'{hedef}' bu oyunda yok (gerçek GENTAHAX API'sinde bulunamadı)"
        coz = f"Fonksiyon adını düzelt: '{hedef}' → doğrusu"
        if len(adaylar) == 1:
            coz += f" büyük ihtimalle '{adaylar[0]}'"
        elif adaylar:
            coz += " adaylar: " + ", ".join(f"'{a}'" for a in adaylar)
        else:
            coz += " bilinmiyor — gh_api_search ile doğru ismi bul"
        return {"teshis": tes, "cozum": coz,
                "sonraki_arac": f"gh_api_detail('{adaylar[0]}') ile imzayı doğrula, "
                                "yamalı scripti gh_auto_test ile TEKRAR çalıştır" if adaylar
                                else "gh_api_search('<anahtar>') ile gerçek ismi bul"}

    if cls == "NOT_IN_WORLD":
        return {"teshis": "Script dünyada olmadığın için durdu (getWorld() boş)",
                "cozum": "Oyunu aç, bir dünyaya gir, sonra tekrar çalıştır",
                "sonraki_arac": "gh_auto_test (yeniden)"}
    if cls == "NO_LOCAL":
        return {"teshis": "Yerel oyuncu henüz yüklenmedi (getLocal() boş)",
                "cozum": "2-3 saniye bekle ve tekrar çalıştır — oyun ekranı tam açılmamış olabilir",
                "sonraki_arac": "gh_auto_test (yeniden)"}
    if cls == "NIL_INDEX":
        return {"teshis": "Boş (nil) nesne kullanılmış — " + str((err or {}).get("aciklama", "")),
                "cozum": "Script başına koruma ekle: local w = getWorld() if not w then "
                         "return 'ERR|NO_WORLD' end — ve dünyada olduğundan emin ol",
                "sonraki_arac": "gh_code_analyze (düzeltilmiş hâl için)"}
    if cls == "NIL_ARITH":
        return {"teshis": "Hesapta nil değer kullanılmış",
                "cozum": "Değerlere varsayılan ver: (me.gems or 0), (w.width or 100) gibi",
                "sonraki_arac": "gh_code_analyze"}
    if cls == "SYNTAX":
        return {"teshis": "Kod derlenmedi (söz dizimi hatası)",
                "cozum": "Parantez/'end' dengesini kontrol et — gh_code_analyze'ın "
                         "syntax_issues bölümü satırı işaret eder",
                "sonraki_arac": "gh_code_analyze"}
    if cls == "BRIDGE_DOWN":
        return {"teshis": "Köprü (bridge) yanıt vermiyor",
                "cozum": "gh_device_status ile duruma bak; gentahax_bridge.lua'yı oyunda "
                         "Lua Executor'dan tekrar çalıştır (gh_bridge_deploy yazar)",
                "sonraki_arac": "gh_device_status → gh_bridge_deploy"}
    return {"teshis": "Genel Lua hatası: " + str((err or {}).get("satir", ""))[:120],
            "cozum": "Hata satırındaki şüpheli çağrımı gh_api_detail ile doğrula, "
                     "değişkenlere nil koruması ekle",
            "sonraki_arac": "gh_code_analyze"}


def new_log_lines(before_text, after_text):
    """Çalıştırma öncesi/sonrası log metninden YENİ satırları çıkarır."""
    before = set((before_text or "").splitlines())
    out = []
    for line in str(after_text or "").splitlines():
        if line not in before:
            out.append(line)
    return out
