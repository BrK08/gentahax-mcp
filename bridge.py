"""
GENTAHAX MCP — Device Bridge
mr_berk edition

İletişim mimarisi (Dosya IPC):
  Python (MCP)  ──bridge_in.txt──▶  gentahax_bridge.lua (oyun içinde thread)
                                  ◀──bridge_out.txt──  sonuç / log

Windows : GENTAHAX Script klasörü doğrudan izlenir (GENTAHAX_SCRIPT_DIR)
Android : adb push/pull ile aynı dosyalar senkronize edilir (GENTAHAX_TARGET=adb)
"""
import os
import time
import subprocess
import secrets
from pathlib import Path

WATERMARK = "mr_berk"
IN_NAME = "bridge_in.txt"
OUT_NAME = "bridge_out.txt"
BRIDGE_LUA_NAME = "gentahax_bridge.lua"
DEFAULT_TIMEOUT = float(os.environ.get("GENTAHAX_BRIDGE_TIMEOUT", "10"))
SAFE_MODE = os.environ.get("GENTAHAX_SAFE_MODE", "1") == "1"


def script_dir() -> Path:
    d = os.environ.get("GENTAHAX_SCRIPT_DIR", "")
    return Path(d) if d else None


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
            "GENTAHAX_SCRIPT_DIR ortam değişkenine yaz. "
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
            info["has_logs"] = log.exists()
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
    p.write_text(content, encoding="utf-8")
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
    """lua_logs.txt son satırları (GENTAHAX kendi log dosyası)."""
    d = script_dir()
    if d is None:
        return None
    if adb_enabled():
        r = _adb("shell", f"tail -n {int(tail)} {_remote_dir()}/lua_logs.txt 2>/dev/null")
        return r.stdout
    log = d / "lua_logs.txt"
    if not log.exists():
        return "(lua_logs.txt yok — GENTAHAX doLog() kullanınca oluşur)"
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-int(tail):])


def exec_lua(code, timeout=DEFAULT_TIMEOUT, risk_level="low"):
    """
    Lua kodunu köprü üzerinden çalıştırır ve sonucu bekler.
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

    out_file = d / OUT_NAME
    in_file = d / IN_NAME
    # önce eski çıktıları temizle
    if out_file.exists():
        out_file.unlink()

    cmd_id = secrets.token_hex(4)
    payload = f"{cmd_id}|EXEC\n{code}"
    in_file.write_text(payload, encoding="utf-8")

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
        if local_out.exists():
            for line in local_out.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith(f"{cmd_id}|"):
                    _, status, rest = line.split("|", 2)
                    if status == "OK":
                        return rest if rest else "(dönüş değeri yok)"
                    raise RuntimeError(f"Lua hatası: {rest}")
    raise TimeoutError(f"Köprü zaman aşımı ({timeout}s) — gentahax_bridge.lua oyunda çalışıyor mu? gh_device_status ile kontrol edin.")


def deploy_bridge():
    """gentahax_bridge.lua'yı script dizinine yazar."""
    src = Path(__file__).parent / "bridge" / BRIDGE_LUA_NAME
    if not src.exists():
        raise RuntimeError("bridge/gentahax_bridge.lua bulunamadı")
    content = src.read_text(encoding="utf-8")
    path = write_script(BRIDGE_LUA_NAME, content, overwrite=True)
    return {
        "deployed_to": path,
        "next_steps": [
            "1) GENTAHAX menüsünden Lua Executor'ı açın ve gentahax_bridge.lua'yı çalıştırın (Execute).",
            "2) gh_device_status ile köprünün PONG döndüğünü doğrulayın.",
            "3) Artık gh_run_lua / gh_world_snapshot / gh_player_info araçları canlı çalışır.",
        ],
    }
