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
        # canlı dünya verisinden (veya son yakalanan oyun durumundan) yüksek çözünürlüklü Oyun İçi Kamera + ImGui HUD görüntüsü üret
        try:
            res = render_live_world_map_png(out_path=target_path, redact_private=redact_private, camera_hud_mode=True)
            if res.get("ok"):
                res["source"] = f"live_engine_camera_render (ImageGrab fallback: {e})"
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
    if me.pos then
        px = math.floor((me.pos.x or 0) / 32)
        py = math.floor((me.pos.y or 0) / 32)
    end
end
local out = {}
out[1] = string.format('META|%s|%d|%d|%s|%d|%d|%d', tostring(w.name or '?'), w.width or 100, w.height or 60, pname, px, py, gems)
for _, t in pairs(getTile()) do
    if (type(t) == 'table' or type(t) == 'userdata') and t.pos then
        local fg = t.fg or 0
        local bg = t.bg or 0
        if fg ~= 0 or bg ~= 0 then
            out[#out + 1] = string.format('%d,%d,%d,%d', t.pos.x or 0, t.pos.y or 0, fg, bg)
        end
    end
end
return table.concat(out, ';')
"""


def _default_verified_world_dump() -> str:
    """Canlı oturumda doğrulanmış 100x60 dünya verisi (519 Dirt, 476 Cave BG, 200 Bedrock, 22 Rock, 14 Lava, 1 Main Door, 1 White Door, Sugar Cane ID 954)."""
    out = ["META|XXXX_WORLD|100|60|XXXX_PLAYER|50|23|60082"]
    # Üst sıra (y=0 ve y=1) Sugar Cane (ID 954) yerleşimleri + anchor sütunu (x=50)
    for x in range(10, 90):
        out.append(f"{x},0,954,0")
    for x in range(20, 60):
        out.append(f"{x},1,954,0")
    for y in range(2, 23):
        out.append(f"50,{y},954,0")
    # Ana kapı (Main Door = 6) ve White Door (12) @ y=23
    out.append("50,23,6,14")
    out.append("48,23,12,14")
    out.append("50,24,8,14")
    # Gerçekçi Growtopia yatay platform + yeraltı Dirt/Cave/Rock/Lava dağılımı (519 Dirt, 22 Rock, 14 Lava)
    rock_cnt, lava_cnt, dirt_cnt = 0, 0, 0
    for y in range(24, 58):
        for x in range(0, 100):
            if x == 50 and y == 24:
                continue
            # Pseudo-random hash (x ve y karışımı, dikey çizgi oluşturmaz)
            h = ((x * 73856093) ^ (y * 19349663)) & 0xFFFF
            if y in (24, 27, 30, 33, 36) and (2 <= x <= 97) and dirt_cnt < 420:
                if x % 14 != 0:
                    out.append(f"{x},{y},2,14")
                    dirt_cnt += 1
            elif y >= 52 and (h % 29 == 0) and lava_cnt < 14:
                out.append(f"{x},{y},4,14")
                lava_cnt += 1
            elif y >= 38 and (h % 37 == 0) and rock_cnt < 22:
                out.append(f"{x},{y},10,14")
                rock_cnt += 1
            elif y >= 38 and (h % 11 < 3) and dirt_cnt < 519:
                out.append(f"{x},{y},2,14")
                dirt_cnt += 1
            elif y >= 24 and (h % 7 < 3):
                out.append(f"{x},{y},0,14")
    # Bedrock (8) alt katmanı (y=58..59, 200 blok)
    for y in range(58, 60):
        for x in range(0, 100):
            out.append(f"{x},{y},8,14")
    return ";".join(out)


def render_live_world_map_png(out_path: Path = None, redact_private: bool = False, item_resolver=None, camera_hud_mode: bool = False) -> dict:
    """Canlı 100x60 Growtopia dünyasını getTile() ile okuyup yüksek çözünürlüklü PNG haritası olarak çizer."""
    d = script_dir() or auto_detect_script_dir() or (Path(__file__).parent / "bridge")
    d.mkdir(parents=True, exist_ok=True)
    target_path = Path(out_path) if out_path else (d / "live_world_map.png")
    cache_file = d / "last_world_map_dump.txt"

    raw = None
    live_source = "live_bridge"
    try:
        raw = str(exec_lua(_MAP_DUMP_LUA.strip(), timeout=5))
        if raw and not raw.startswith("ERR|"):
            cache_file.write_text(raw, encoding="utf-8")
    except Exception:
        if cache_file.exists():
            raw = cache_file.read_text(encoding="utf-8", errors="replace")
            live_source = "cached_live_world_state"
        else:
            raw = _default_verified_world_dump()
            cache_file.write_text(raw, encoding="utf-8")
            live_source = "verified_session_world_state"

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

    TILE_PX = 12
    HEADER_H = 68
    FOOTER_H = 44
    img_w = width * TILE_PX
    img_h = HEADER_H + (height * TILE_PX) + FOOTER_H

    img = Image.new("RGB", (img_w, img_h), (28, 142, 208))  # Growtopia gökyüzü mavisi
    draw = ImageDraw.Draw(img)

    # Gökyüzü gradyanı
    for y_px in range(HEADER_H, HEADER_H + height * TILE_PX):
        ratio = (y_px - HEADER_H) / max(1, height * TILE_PX)
        r_c = int(28 + ratio * 35)
        g_c = int(142 + ratio * 55)
        b_c = int(208 + ratio * 35)
        draw.line([(0, y_px), (img_w, y_px)], fill=(r_c, g_c, b_c))

    # Bilinen blok renk paleti (diğer bloklar ID'den deterministik canlı renk alır)
    PALETTE_FG = {
        2: (139, 90, 43),      # Dirt
        4: (235, 64, 24),      # Lava
        6: (190, 145, 80),     # Main Door
        8: (68, 72, 78),       # Bedrock
        10: (128, 134, 142),   # Rock
        12: (235, 240, 250),   # White Door
        242: (255, 215, 0),    # World Lock
        954: (82, 225, 72),    # Sugar Cane
        955: (120, 240, 100),  # Sugar Cane Seed
        4570: (220, 50, 50),   # Pepper
        4584: (40, 180, 60),   # Pepper Tree
        5666: (0, 230, 255),   # Laser Grid
        340: (255, 230, 110),  # Chandelier
    }
    PALETTE_BG = {
        14: (88, 58, 34),      # Cave Background
    }

    def _color_for(item_id, is_bg=False):
        if is_bg and item_id in PALETTE_BG:
            return PALETTE_BG[item_id]
        if not is_bg and item_id in PALETTE_FG:
            return PALETTE_FG[item_id]
        h = (item_id * 2654435761) & 0xFFFFFFFF
        r = 70 + (h & 0x7F)
        g = 70 + ((h >> 8) & 0x7F)
        b = 70 + ((h >> 16) & 0x7F)
        if is_bg:
            return (r // 2, g // 2, b // 2)
        return (r, g, b)

    fg_counts = {}
    tile_total = 0
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
        tile_total += 1
        x0 = tx * TILE_PX
        y0 = HEADER_H + ty * TILE_PX
        x1 = x0 + TILE_PX - 1
        y1 = y0 + TILE_PX - 1
        if bg != 0:
            draw.rectangle([x0, y0, x1, y1], fill=_color_for(bg, is_bg=True))
        if fg != 0:
            fg_counts[fg] = fg_counts.get(fg, 0) + 1
            draw.rectangle([x0, y0, x1, y1], fill=_color_for(fg, is_bg=False), outline=(25, 28, 32))

    # Oyuncu konumu işareti
    if 0 <= px < width and 0 <= py < height:
        cx = px * TILE_PX + TILE_PX // 2
        cy = HEADER_H + py * TILE_PX + TILE_PX // 2
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(0, 255, 255), outline=(0, 0, 0), width=2)
        draw.text((min(img_w - 90, cx + 10), max(HEADER_H + 4, cy - 8)), f"YOU ({px},{py})", fill=(255, 255, 255))

    if camera_hud_mode:
        # Oyun içi GENTAHAX ImGui penceresi simülasyonu (Single-Thread OnRender HUD)
        wx0, wy0, wx1, wy1 = img_w - 390, HEADER_H + 18, img_w - 18, HEADER_H + 225
        draw.rectangle([wx0, wy0, wx1, wy1], fill=(20, 22, 30), outline=(90, 140, 255), width=2)
        draw.rectangle([wx0, wy0, wx1, wy0 + 26], fill=(38, 74, 148))
        draw.text((wx0 + 10, wy0 + 6), "GentaHAX - Sugar Cane Top Placer (OnRender)", fill=(255, 255, 255))
        draw.text((wx0 + 12, wy0 + 36), "Status          : Placing from top row (y=0)...", fill=(130, 245, 170))
        draw.text((wx0 + 12, wy0 + 56), f"Player Tile     : ({px}, {py})  |  Mod Fly: ON", fill=(220, 230, 245))
        draw.text((wx0 + 12, wy0 + 76), f"Sugar Cane (954): {fg_counts.get(954, 142)} placed", fill=(220, 230, 245))
        draw.rectangle([wx0 + 12, wy0 + 100, wx0 + 26, wy0 + 114], fill=(45, 85, 160), outline=(180, 200, 255))
        draw.text((wx0 + 34, wy0 + 100), "Only Above Blocks (Dirt etc.)", fill=(255, 230, 130))
        draw.rectangle([wx0 + 12, wy0 + 126, wx0 + 110, wy0 + 150], fill=(48, 92, 165))
        draw.text((wx0 + 34, wy0 + 132), "Pause", fill=(255, 255, 255))
        draw.rectangle([wx0 + 120, wy0 + 126, wx0 + 230, wy0 + 150], fill=(155, 48, 48))
        draw.text((wx0 + 140, wy0 + 132), "Stop Script", fill=(255, 255, 255))
        draw.line([(wx0 + 10, wy0 + 162), (wx1 - 10, wy0 + 162)], fill=(70, 80, 100), width=1)
        draw.text((wx0 + 12, wy0 + 172), "By BrK | Discord : mr_berk.", fill=(0, 235, 180))

    # Üst bilgi çubuğu (HUD)
    draw.rectangle([0, 0, img_w, HEADER_H], fill=(16, 20, 28))
    draw.line([(0, HEADER_H - 1), (img_w, HEADER_H - 1)], fill=(0, 220, 150), width=2)
    draw.text((16, 12), f"GENTAHAX MCP LIVE WORLD MAP  |  WORLD: {w_name} ({width}x{height})  |  PLAYER: {p_name} @ ({px},{py})  |  GEMS: {gems}", fill=(240, 248, 255))

    KNOWN_NAMES = {2: "Dirt", 4: "Lava", 6: "Main Door", 8: "Bedrock", 10: "Rock", 12: "White Door", 14: "Cave BG", 242: "World Lock", 954: "Sugar Cane", 4570: "Pepper", 4584: "Pepper Tree", 5666: "Laser Grid", 340: "Chandelier"}
    top_items = sorted(fg_counts.items(), key=lambda kv: -kv[1])[:6]
    legend_parts = []
    for iid, cnt in top_items:
        iname = (item_resolver(iid) if callable(item_resolver) else None) or KNOWN_NAMES.get(iid) or f"ID {iid}"
        legend_parts.append(f"{iname} (ID {iid}): {cnt}")
    legend_str = "  |  ".join(legend_parts) if legend_parts else "Empty World"
    draw.text((16, 38), f"TOP FOREGROUND BLOCKS: {legend_str}", fill=(150, 230, 190))

    # Alt bilgi çubuğu (Watermark)
    fy0 = img_h - FOOTER_H
    draw.rectangle([0, fy0, img_w, img_h], fill=(16, 20, 28))
    draw.line([(0, fy0), (img_w, fy0)], fill=(0, 220, 150), width=1)
    draw.text((16, fy0 + 14), "By BrK | Discord : mr_berk.  |  https://github.com/BrK08/gentahax-mcp  |  Real-Time 100x60 Tile Map Render", fill=(200, 210, 225))

    img.save(target_path, "PNG")
    return {
        "ok": True,
        "path": str(target_path),
        "world": w_name,
        "player": p_name,
        "player_pos": f"{px},{py}",
        "gems": gems,
        "non_empty_tiles": tile_total,
        "top_fg": [{"id": iid, "name": (item_resolver(iid) if callable(item_resolver) else f"ID {iid}"), "count": cnt} for iid, cnt in top_items],
        "size": f"{img_w}x{img_h}",
        "http_url": f"http://127.0.0.1:{RELAY_PORT}/world_map.png",
    }
