"""
GENTAHAX MCP — Device Bridge (Hibrit: Dosya IPC + Gömülü HTTP Relay)
mr_berk edition v2.0

İletişim mimarisi:
  1) Dosya IPC (io açık olan build'ler):
     Python (MCP)  ──bridge_in.txt──▶  gentahax_bridge.lua
                                   ◀──bridge_out.txt──  sonuç / log
  2) Gömülü HTTP Relay (io kapalı olan Windows PATCH r1.0 vb. build'ler):
     127.0.0.1:8809 üzerinde otomatik arka plan HTTP sunucusu açılır;
     gentahax_bridge.lua makeRequest ile /in ve /out uçlarıyla konuşur.

Windows : GENTAHAX Script klasörü izlenir (GENTAHAX_SCRIPT_DIR veya otomatik algılama)
Android : adb push/pull ile aynı dosyalar senkronize edilir (GENTAHAX_TARGET=adb)
"""
import os
import time
import threading
import subprocess
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

WATERMARK = "mr_berk"
IN_NAME = "bridge_in.txt"
OUT_NAME = "bridge_out.txt"
BRIDGE_LUA_NAME = "gentahax_bridge.lua"
DEFAULT_TIMEOUT = float(os.environ.get("GENTAHAX_BRIDGE_TIMEOUT", "10"))
SAFE_MODE = os.environ.get("GENTAHAX_SAFE_MODE", "1") == "1"
RELAY_PORT = int(os.environ.get("GENTAHAX_RELAY_PORT", "8809"))

_RELAY_STARTED = False
_RELAY_LOCK = threading.Lock()


def auto_detect_script_dir() -> Path:
    """GENTAHAX_SCRIPT_DIR ayarlı değilse standart Windows Growtopia/GENTAHAX konumlarını arar."""
    local_app = os.environ.get("LOCALAPPDATA", "")
    user_prof = os.environ.get("USERPROFILE", "")
    candidates = []
    if local_app:
        candidates.append(Path(local_app) / "Growtopia" / "scripts")
        candidates.append(Path(local_app) / "Growtopia" / "Script")
    if user_prof:
        candidates.append(Path(user_prof) / "AppData" / "Local" / "Growtopia" / "scripts")
        candidates.append(Path(user_prof) / "AppData" / "Local" / "Growtopia" / "Script")
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    # Growtopia klasörü varsa scripts alt klasörünü otomatik oluşturabiliriz
    if local_app and (Path(local_app) / "Growtopia").exists():
        target = Path(local_app) / "Growtopia" / "scripts"
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target
        except Exception:
            pass
    return None


def script_dir() -> Path:
    d = os.environ.get("GENTAHAX_SCRIPT_DIR", "")
    if d:
        return Path(d)
    if os.environ.get("GENTAHAX_AUTO_DETECT", "0") == "1":
        return auto_detect_script_dir()
    return None


def start_http_relay(port: int = RELAY_PORT) -> bool:
    """io kütüphanesi kapalı GENTAHAX sürümleri için gömülü yerel HTTP aktarıcıyı başlatır."""
    global _RELAY_STARTED
    with _RELAY_LOCK:
        if _RELAY_STARTED:
            return True

        class _RelayHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # sessiz log (stdio protokolünü kirletmemek için)

            def _active_dir(self) -> Path:
                return script_dir() or auto_detect_script_dir() or (Path(__file__).parent / "bridge")

            def do_GET(self):
                d = self._active_dir()
                if self.path.startswith("/in"):
                    in_file = d / IN_NAME
                    resp = ""
                    if in_file.exists():
                        try:
                            resp = in_file.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
                            in_file.unlink(missing_ok=True)
                        except Exception:
                            resp = ""
                    data = resp.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                elif self.path.startswith("/bridge.lua"):
                    src = Path(__file__).parent / "bridge" / BRIDGE_LUA_NAME
                    body = src.read_text(encoding="utf-8") if src.exists() else ""
                    data = body.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                elif self.path.startswith("/screenshot.png") or self.path.startswith("/world_map.png"):
                    fname = "live_game_screenshot.png" if "screenshot" in self.path else "live_world_map.png"
                    img_file = d / fname
                    if img_file.exists():
                        data = img_file.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", "image/png")
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                    else:
                        self.send_response(404)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                d = self._active_dir()
                if self.path.startswith("/out"):
                    length = int(self.headers.get("Content-Length", "0") or "0")
                    raw = self.rfile.read(length).decode("utf-8", errors="replace") if length > 0 else ""
                    try:
                        d.mkdir(parents=True, exist_ok=True)
                        out_file = d / OUT_NAME
                        with open(out_file, "a", encoding="utf-8") as f:
                            f.write(raw + "\n")
                    except Exception:
                        pass
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", "2")
                    self.end_headers()
                    self.wfile.write(b"OK")
                else:
                    self.send_response(404)
                    self.end_headers()

        try:
            srv = HTTPServer(("127.0.0.1", port), _RelayHandler)
            th = threading.Thread(target=srv.serve_forever, daemon=True, name="gh_http_relay")
            th.start()
            _RELAY_STARTED = True
            return True
        except OSError:
            # Port zaten dinleniyor olabilir (örn. başka bir süreç veya relay.ps1 açık)
            return False


def adb_enabled() -> bool:
    return os.environ.get("GENTAHAX_TARGET", "").lower() == "adb"


def _adb(*args, timeout=15):
    cmd = ["adb"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _push(local: Path, remote: str):
    r = _adb("push", str(local), remote)
    if r.returncode != 0:
        raise RuntimeError(f"adb push hatası: {r.stderr.strip()}")


def _pull(remote: str, local: Path):
    r = _adb("pull", remote, str(local))
    if r.returncode != 0:
        raise RuntimeError(f"adb pull hatası: {r.stderr.strip()}")


def _remote_dir() -> str:
    return os.environ.get("GENTAHAX_ADB_DIR", "/storage/emulated/0/Android/media/GENTAHAX/Script")


def status():
    """Köprü durum raporu."""
    d = script_dir()
    info = {
        "mode": "adb" if adb_enabled() else ("local" if d else "disabled"),
        "script_dir": str(d) if d else None,
        "safe_mode": SAFE_MODE,
        "watermark": WATERMARK,
    }
    if not d and not adb_enabled():
        info["configured"] = False
        info["how_to_enable"] = (
            "1) Windows: GENTAHAX kurulu dizindeki Script klasörünün tam yolunu "
            "GENTAHAX_SCRIPT_DIR ortam değişkenine yaz (veya start_mcp.py ile otomatik başlat). "
            "2) Android: GENTAHAX_TARGET=adb ve adb'de cihaz bağlı olsun. "
            "Sonra gh_bridge_deploy ile köprüyü kur."
        )
        return info
    info["configured"] = True

    if adb_enabled():
        r = _adb("devices")
        info["adb_devices"] = r.stdout.strip() if r.returncode == 0 else r.stderr.strip()
        remote = _remote_dir()
        rr = _adb("shell", f"test -d {remote} && echo EXISTS")
        info["remote_script_dir"] = remote
        info["remote_dir_exists"] = rr.stdout.strip() == "EXISTS"
    else:
        info["dir_exists"] = d.exists()
        if d.exists():
            info["scripts"] = sorted(p.name for p in d.glob("*.lua"))
            info["has_bridge"] = (d / BRIDGE_LUA_NAME).exists()
            log = d / "lua_logs.txt"
            alt_log = d.parent / "lua_logs.txt"
            info["has_logs"] = log.exists() or alt_log.exists()
            info["bridge_responding"] = _bridge_alive(d)
    return info


def _bridge_alive(d: Path) -> bool:
    """Köprü canlı mı? heartbeat dener."""
    try:
        out = exec_lua("return 'PONG_' .. tostring(os and os.time and os.time() or 0)", timeout=6)
        return "PONG" in str(out)
    except Exception:
        return False


def list_scripts():
    d = script_dir()
    if d is None:
        return None
    if adb_enabled():
        r = _adb("shell", f"ls {_remote_dir()}/ 2>/dev/null")
        return sorted(l for l in r.stdout.splitlines() if l.strip().endswith(".lua"))
    if d.exists():
        return sorted(p.name for p in d.glob("*.lua"))
    return []


def read_script(name):
    d = script_dir()
    if d is None:
        return None
    safe = Path(name).name
    if adb_enabled():
        tmp = Path("/tmp") / f"gh_pull_{secrets.token_hex(4)}.lua"
        try:
            _pull(f"{_remote_dir()}/{safe}", tmp)
            return tmp.read_text(encoding="utf-8", errors="replace")
        finally:
            tmp.unlink(missing_ok=True)
    p = d / safe
    if p.exists() and p.suffix == ".lua":
        return p.read_text(encoding="utf-8", errors="replace")
    return None


def write_script(name, content, overwrite=True):
    """Script yazar (Windows: doğrudan, Android: adb push). Dönen: yazılan yol."""
    d = script_dir()
    if d is None:
        return None
    safe = Path(name).name
    if not safe.endswith(".lua"):
        safe += ".lua"
    if adb_enabled():
        tmp = Path("/tmp") / f"gh_push_{secrets.token_hex(4)}.lua"
        tmp.write_text(content, encoding="utf-8")
        try:
            _push(tmp, f"{_remote_dir()}/{safe}")
        finally:
            tmp.unlink(missing_ok=True)
        return f"adb:{_remote_dir()}/{safe}"
    d.mkdir(parents=True, exist_ok=True)
    p = d / safe
    if p.exists() and not overwrite:
        return None
    p.write_text(content, encoding="utf-8", newline="\n")
    # Windows Growtopia dizininde hem 'scripts' hem 'Script' klasörlerine senkronize et
    if d.parent.name.lower() == "growtopia":
        for alt_name in ("scripts", "Script"):
            alt_dir = d.parent / alt_name
            if alt_dir != d:
                try:
                    alt_dir.mkdir(parents=True, exist_ok=True)
                    (alt_dir / safe).write_text(content, encoding="utf-8", newline="\n")
                except Exception:
                    pass
    return str(p)


def delete_script(name):
    d = script_dir()
    if d is None:
        return None
    safe = Path(name).name
    if adb_enabled():
        _adb("shell", f"rm -f {_remote_dir()}/{safe}")
        return True
    p = d / safe
    if p.exists():
        p.unlink()
        return True
    return False


def read_logs(tail=80):
    """lua_logs.txt son satırları (hem Script klasöründe hem de Growtopia ana dizininde arar)."""
    d = script_dir()
    if d is None:
        return None
    if adb_enabled():
        r = _adb("shell", f"tail -n {int(tail)} {_remote_dir()}/lua_logs.txt 2>/dev/null")
        return r.stdout
    log = d / "lua_logs.txt"
    if not log.exists() and d.parent.exists():
        alt = d.parent / "lua_logs.txt"
        if alt.exists():
            log = alt
    if not log.exists():
        return "(lua_logs.txt yok — GENTAHAX doLog() kullanınca oluşur)"
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-int(tail):])


_EXEC_LOCK = threading.Lock()


def exec_lua(code, timeout=DEFAULT_TIMEOUT, risk_level="low"):
    """
    Lua kodunu köprü üzerinden çalıştırır ve sonucu bekler (thread-safe).
    risk_level: 'high' ise güvenli modda reddedilir (force ayrı ele alınır).
    """
    d = script_dir()
    if d is None:
        raise RuntimeError("Köprü yapılandırılmamış — GENTAHAX_SCRIPT_DIR ayarlayın ve gh_bridge_deploy çalıştırın.")
    if SAFE_MODE and risk_level == "high":
        raise PermissionError(
            "⚠️ GÜVENLİ MOD: Bu kod YÜKSEK ban riski taşıdığı için otomatik çalıştırma reddedildi. "
            "Risk analizini okuyun, kodu düzeltin ya da GENTAHAX_SAFE_MODE=0 yapıp force=true ile yeniden deneyin."
        )

    start_http_relay(RELAY_PORT)

    with _EXEC_LOCK:
        out_file = d / OUT_NAME
        in_file = d / IN_NAME
        if out_file.exists():
            out_file.unlink()

        cmd_id = secrets.token_hex(4)
        payload = f"{cmd_id}|EXEC\n{code}"
        in_file.write_text(payload, encoding="utf-8", newline="\n")
        if d.parent.name.lower() == "growtopia":
            for alt_name in ("scripts", "Script"):
                alt_dir = d.parent / alt_name
                if alt_dir != d:
                    try:
                        alt_dir.mkdir(parents=True, exist_ok=True)
                        (alt_dir / OUT_NAME).unlink(missing_ok=True)
                        (alt_dir / IN_NAME).write_text(payload, encoding="utf-8", newline="\n")
                    except Exception:
                        pass

        if adb_enabled():
            _push(in_file, f"{_remote_dir()}/{IN_NAME}")

        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.25)
            local_out = out_file
            if adb_enabled():
                try:
                    _pull(f"{_remote_dir()}/{OUT_NAME}", out_file)
                except Exception:
                    continue
            if not local_out.exists() and d.parent.name.lower() == "growtopia":
                for alt_name in ("scripts", "Script"):
                    cand_out = d.parent / alt_name / OUT_NAME
                    if cand_out.exists():
                        local_out = cand_out
                        break
            if local_out.exists():
                for line in local_out.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith(f"{cmd_id}|"):
                        _, st_code, rest = line.split("|", 2)
                        if st_code == "OK":
                            return rest if rest else "(dönüş değeri yok)"
                        raise RuntimeError(f"Lua hatası: {rest}")
        raise TimeoutError(f"Köprü zaman aşımı ({timeout}s) — gentahax_bridge.lua oyunda çalışıyor mu? gh_device_status ile kontrol edin.")


def deploy_bridge():
    """gentahax_bridge.lua'yı script dizinine yazar ve gömülü HTTP aktarıcıyı başlatır."""
    start_http_relay(RELAY_PORT)
    src = Path(__file__).parent / "bridge" / BRIDGE_LUA_NAME
    if not src.exists():
        raise RuntimeError("bridge/gentahax_bridge.lua bulunamadı")
    content = src.read_text(encoding="utf-8")
    path = write_script(BRIDGE_LUA_NAME, content, overwrite=True)
    return {
        "deployed_to": path,
        "one_liner_loader": f'load(makeRequest("http://127.0.0.1:{RELAY_PORT}/bridge.lua","GET",{{}},"",5000).content)()',
        "next_steps": [
            "1) GENTAHAX menüsünden Lua Executor'ı açın ve gentahax_bridge.lua'yı çalıştırın (Execute).",
            f"   (Alternatif tek satırlık yükleyici: load(makeRequest(\"http://127.0.0.1:{RELAY_PORT}/bridge.lua\",\"GET\",{{}},\"\",5000).content)() )",
            "2) gh_device_status ile köprünün PONG döndüğünü doğrulayın.",
            "3) Artık gh_run_lua / gh_world_snapshot / gh_player_info araçları canlı çalışır.",
        ],
    }


def capture_game_window_png(out_path: Path = None, redact_private: bool = False) -> dict:
    """Canlı Growtopia penceresinin (Windows) veya Android ekranının (adb) anlık PNG görüntüsünü yakalar."""
    d = script_dir() or auto_detect_script_dir() or (Path(__file__).parent / "bridge")
    d.mkdir(parents=True, exist_ok=True)
    target_path = Path(out_path) if out_path else (d / "live_game_screenshot.png")

    if adb_enabled():
        try:
            r = subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True, timeout=10)
            if r.returncode == 0 and r.stdout.startswith(b"\x89PNG"):
                target_path.write_bytes(r.stdout)
                return {"ok": True, "source": "android_adb_screencap", "path": str(target_path),
                        "http_url": f"http://127.0.0.1:{RELAY_PORT}/screenshot.png"}
        except Exception as e:
            return {"ok": False, "error": f"adb screencap hatası: {e}"}

    try:
        import ctypes
        from ctypes import wintypes
        from PIL import ImageGrab, ImageDraw

        user32 = ctypes.windll.user32
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

        found_hwnd = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def _enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    if "growtopia" in title.lower():
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        if w > 200 and h > 200:
                            found_hwnd.append((hwnd, title, (rect.left, rect.top, rect.right, rect.bottom)))
            return True

        user32.EnumWindows(_enum_cb, 0)
        if found_hwnd:
            hwnd, title, bbox = found_hwnd[0]
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                time.sleep(0.15)
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                bbox = (rect.left, rect.top, rect.right, rect.bottom)
            img = ImageGrab.grab(bbox=bbox, all_screens=True)
            src_label = f"windows_hwnd ({title})"
        else:
            img = ImageGrab.grab(all_screens=True)
            src_label = "windows_fullscreen_fallback"

        if redact_private:
            draw = ImageDraw.Draw(img)
            w_img, h_img = img.size
            # Sol üst oyuncu adı / dünya sohbet alanı gizleme (xxxx)
            draw.rectangle([int(w_img * 0.06), int(h_img * 0.04), int(w_img * 0.25), int(h_img * 0.09)], fill=(18, 22, 32))
            draw.text((int(w_img * 0.07), int(h_img * 0.05)), "XXXX [REDACTED]", fill=(0, 255, 180))

        img.save(target_path, "PNG")
        return {
            "ok": True,
            "source": src_label,
            "path": str(target_path),
            "size": f"{img.size[0]}x{img.size[1]}",
            "http_url": f"http://127.0.0.1:{RELAY_PORT}/screenshot.png",
        }
    except Exception as e:
        # Sandboxed / arka plan oturumlarında ImageGrab 'screen grab failed' döndürürse
        # GENTAHAX Minimap mantığıyla gerçek .rttex sprite'larından dünya görüntüsü üret
        try:
            res = render_live_world_map_png(out_path=target_path, redact_private=redact_private)
            if res.get("ok"):
                res["source"] = f"live_world_render_rttex (ImageGrab kullanılamadı: {e})"
                res["http_url"] = f"http://127.0.0.1:{RELAY_PORT}/screenshot.png"
                return res
        except Exception:
            pass
        return {"ok": False, "error": str(e)}


_MAP_DUMP_LUA = """
local w = getWorld()
if not w then return 'ERR|NO_WORLD' end
local me = getLocal()
local px, py, pname, gems = -1, -1, '?', 0
if me then
    pname = tostring(me.name or '?')
    gems = tonumber(me.gems or 0) or 0
    if me.pos and type(me.pos) ~= 'number' then
        px = math.floor((tonumber(me.pos.x) or 0) / 32)
        py = math.floor((tonumber(me.pos.y) or 0) / 32)
    elseif me.posX then
        px = math.floor((tonumber(me.posX) or 0) / 32)
        py = math.floor((tonumber(me.posY) or 0) / 32)
    end
end
local ww = tonumber(w.width) or 100
local wh = tonumber(w.height) or 60
local out = {}
out[1] = string.format('META|%s|%d|%d|%s|%d|%d|%d', tostring(w.name or '?'), ww, wh, pname, px, py, gems)
local ct = checkTile or CheckTile
if type(ct) == 'function' then
    for y = 0, wh - 1 do
        for x = 0, ww - 1 do
            local t = ct(x, y)
            if type(t) == 'table' or type(t) == 'userdata' then
                local fg = tonumber(t.fg) or 0
                local bg = tonumber(t.bg) or 0
                if fg ~= 0 or bg ~= 0 then
                    out[#out + 1] = string.format('%d,%d,%d,%d', x, y, fg, bg)
                end
            end
        end
    end
else
    for idx, t in pairs(getTile()) do
        if type(t) == 'table' or type(t) == 'userdata' then
            local fg = tonumber(t.fg) or 0
            local bg = tonumber(t.bg) or 0
            if fg ~= 0 or bg ~= 0 then
                local tx, ty = -1, -1
                if type(t.pos) == 'table' or type(t.pos) == 'userdata' then
                    tx, ty = t.pos.x, t.pos.y
                elseif t.x ~= nil and t.y ~= nil then
                    tx, ty = t.x, t.y
                elseif type(idx) == 'number' then
                    tx = (idx - 1) % ww
                    ty = math.floor((idx - 1) / ww)
                end
                if tx >= 0 and ty >= 0 then
                    out[#out + 1] = string.format('%d,%d,%d,%d', tx, ty, fg, bg)
                end
            end
        end
    end
end
return table.concat(out, ';')
"""


def render_live_world_map_png(out_path: Path = None, redact_private: bool = False, item_resolver=None, camera_hud_mode: bool = False) -> dict:
    """Canlı 100x60 Growtopia dünyasını checkTile/getTile ile okuyup yüksek çözünürlüklü gerçek PNG haritası olarak çizer (ASLA sahte veri üretmez)."""
    d = script_dir() or auto_detect_script_dir() or (Path(__file__).parent / "bridge")
    d.mkdir(parents=True, exist_ok=True)
    target_path = Path(out_path) if out_path else (d / "live_world_map.png")

    try:
        raw = str(exec_lua(_MAP_DUMP_LUA.strip(), timeout=12))
    except Exception as e:
        return {
            "ok": False,
            "error": f"Canlı dünya haritası çizilemedi çünkü oyun içi köprü yanıt vermedi ({e}). Oyunda gentahax_bridge.lua'yı (veya güncel scripti) Execute et!",
        }

    if raw.startswith("ERR|NO_WORLD"):
        return {"ok": False, "error": "Şu an bir dünyada değilsin (ERR|NO_WORLD)"}

    from PIL import Image, ImageDraw

    parts = raw.split(";")
    meta = parts[0].split("|") if parts else []
    w_name = meta[1] if len(meta) > 1 else "?"
    width = int(meta[2]) if len(meta) > 2 and meta[2].lstrip("-").isdigit() else 100
    height = int(meta[3]) if len(meta) > 3 and meta[3].lstrip("-").isdigit() else 60
    p_name = meta[4] if len(meta) > 4 else "?"
    px = int(meta[5]) if len(meta) > 5 and meta[5].lstrip("-").isdigit() else -1
    py = int(meta[6]) if len(meta) > 6 and meta[6].lstrip("-").isdigit() else -1
    gems = int(meta[7]) if len(meta) > 7 and meta[7].lstrip("-").isdigit() else 0

    if redact_private:
        w_name = "XXXX_WORLD"
        p_name = "XXXX_PLAYER"

    # Oyundan gelen GERÇEK kareler (x, y, fg, bg)
    tiles = []
    fg_counts = {}
    for entry in parts[1:]:
        vals = entry.split(",")
        if len(vals) != 4:
            continue
        try:
            tx, ty, fg, bg = int(vals[0]), int(vals[1]), int(vals[2]), int(vals[3])
        except ValueError:
            continue
        if not (0 <= tx < width and 0 <= ty < height):
            continue
        tiles.append((tx, ty, fg, bg))
        if fg != 0:
            fg_counts[fg] = fg_counts.get(fg, 0) + 1
    tile_total = len(tiles)

    # GENTAHAX Minimap mantığı: gerçek game/*.rttex sprite'ları + items.dat + Connected Texture
    import world_render
    TILE_PX = 16
    HEADER_H = 68
    FOOTER_H = 44
    world_img, render_stats = world_render.render_world(tiles, width, height, player=(px, py), tile_px=TILE_PX)
    img_w = width * TILE_PX
    img_h = HEADER_H + (height * TILE_PX) + FOOTER_H
    img = Image.new("RGB", (img_w, img_h), (16, 20, 28))
    img.paste(world_img.convert("RGB"), (0, HEADER_H))
    draw = ImageDraw.Draw(img)

    # Üst bilgi çubuğu (HUD)
    draw.rectangle([0, 0, img_w, HEADER_H], fill=(16, 20, 28))
    draw.line([(0, HEADER_H - 1), (img_w, HEADER_H - 1)], fill=(0, 220, 150), width=2)
    draw.text((16, 12), f"GENTAHAX MCP LIVE WORLD MAP  |  WORLD: {w_name} ({width}x{height})  |  PLAYER: {p_name} @ ({px},{py})  |  GEMS: {gems}", fill=(240, 248, 255))

    def _name(iid):
        vis = world_render.item_visual(iid)
        return (item_resolver(iid) if callable(item_resolver) else None) or (vis[0] if vis else None) or f"ID {iid}"

    top_items = sorted(fg_counts.items(), key=lambda kv: -kv[1])[:6]
    legend_parts = []
    for iid, cnt in top_items:
        iname = _name(iid)
        legend_parts.append(f"{iname} (ID {iid}): {cnt}")
    legend_str = "  |  ".join(legend_parts) if legend_parts else "Empty World"
    draw.text((16, 38), f"TOP FOREGROUND BLOCKS: {legend_str}", fill=(150, 230, 190))

    # Alt bilgi çubuğu (Watermark)
    fy0 = img_h - FOOTER_H
    draw.rectangle([0, fy0, img_w, img_h], fill=(16, 20, 28))
    draw.line([(0, fy0), (img_w, fy0)], fill=(0, 220, 150), width=1)
    draw.text((16, fy0 + 14), "By BrK | Discord : mr_berk.  |  https://github.com/BrK08/gentahax-mcp  |  Real .rttex sprites (GENTAHAX Minimap style)", fill=(200, 210, 225))

    img.save(target_path, "PNG")
    return {
        "ok": True,
        "path": str(target_path),
        "world": w_name,
        "player": p_name,
        "player_pos": f"{px},{py}",
        "gems": gems,
        "non_empty_tiles": tile_total,
        "top_fg": [{"id": iid, "name": _name(iid), "count": cnt} for iid, cnt in top_items],
        "missing_textures": render_stats.get("missing_textures", []),
        "size": f"{img_w}x{img_h}",
        "http_url": f"http://127.0.0.1:{RELAY_PORT}/world_map.png",
    }
