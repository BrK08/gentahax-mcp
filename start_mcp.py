#!/usr/bin/env python3
"""
GENTAHAX MCP — TEK KOMUTLA OTOMATİK KURULUM & BAŞLATICI (mr_berk edition)
==========================================================================
Kullanıcı veya yapay zeka (ChatGPT, Gemini, Claude, Antigravity, Cursor)
yalnızca şu komutu çalıştırır:

    python start_mcp.py

Bu betik otomatik olarak:
  1) Growtopia / GENTAHAX Script klasörünü tespit eder (veya oluşturur)
  2) gentahax_bridge.lua v2.0 (Hibrit Köprü: io.open + HTTP 8809) dosyasını
     Script klasörüne kopyalar
  3) MCP HTTP sunucusunu (127.0.0.1:8808) ve Gömülü HTTP Aktarıcısını
     (127.0.0.1:8809) başlatır
  4) cloudflared kuruluysa ücretsiz HTTPS tüneli açar ve ChatGPT / Gemini /
     Claude'a yapıştırılacak hazır `https://xxxx.trycloudflare.com/mcp`
     adresini ekrana basar!
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import bridge as B  # noqa: E402


def ensure_script_dir() -> str:
    """Growtopia Script klasörünü bulur veya Windows varsayılanını oluşturur."""
    env_dir = os.environ.get("GENTAHAX_SCRIPT_DIR", "").strip()
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    detected = B.auto_detect_script_dir()
    if detected:
        os.environ["GENTAHAX_SCRIPT_DIR"] = detected
        return detected
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        gt_dir = os.path.join(local_app, "Growtopia")
        if os.path.isdir(gt_dir):
            scr = os.path.join(gt_dir, "Script")
            os.makedirs(scr, exist_ok=True)
            os.environ["GENTAHAX_SCRIPT_DIR"] = scr
            return scr
    fallback = str(ROOT / "Script")
    os.makedirs(fallback, exist_ok=True)
    os.environ["GENTAHAX_SCRIPT_DIR"] = fallback
    return fallback


def start_cloudflared(port: int):
    """cloudflared varsa arka planda başlatır ve trycloudflare URL'sini yakalar."""
    cf_bin = shutil.which("cloudflared")
    if not cf_bin:
        return None, None
    proc = subprocess.Popen(
        [cf_bin, "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    found_url = [None]

    def _reader():
        pat = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        for line in proc.stdout:
            m = pat.search(line)
            if m and not found_url[0]:
                found_url[0] = m.group(0) + "/mcp"

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    for _ in range(30):
        if found_url[0] or proc.poll() is not None:
            break
        time.sleep(0.5)
    return proc, found_url[0]


def main():
    ap = argparse.ArgumentParser(description="GENTAHAX MCP Tek Komutla Başlatıcı (mr_berk)")
    ap.add_argument("--port", type=int, default=8808, help="MCP HTTP portu (varsayılan: 8808)")
    ap.add_argument("--host", default="127.0.0.1", help="Dinleme adresi (varsayılan: 127.0.0.1)")
    ap.add_argument("--no-tunnel", action="store_true", help="cloudflared tünelini açma")
    args = ap.parse_args()

    print("=" * 72)
    print("  GENTAHAX MCP v1.5.0 — OTOMATİK KURULUM & BAŞLATICI (mr_berk)")
    print("=" * 72)

    scr_dir = ensure_script_dir()
    print(f"[1/4] Script klasörü : {scr_dir}")

    try:
        dep = B.deploy_bridge()
        print(f"[2/4] Köprü kuruldu  : {dep.get('deployed_to')}")
    except Exception as e:
        print(f"[2/4] Köprü uyarısı  : {e}")

    relay_port = B.start_http_relay()
    print(f"[3/4] Hibrit Aktarıcı: http://127.0.0.1:{relay_port} (Windows io=nil & Android uyumlu)")

    cf_proc = None
    mcp_url = None
    if not args.no_tunnel:
        print("[4/4] Cloudflare HTTPS tüneli açılıyor...")
        cf_proc, mcp_url = start_cloudflared(args.port)
        if mcp_url:
            print(f"      Tünel hazır    : {mcp_url}")
        else:
            print("      Not: cloudflared bulunamadı veya URL alınamadı (yerel uç aktif).")
    else:
        print("[4/4] Tünel atlandı (--no-tunnel).")

    print("\n" + "=" * 72)
    print("  BAĞLANTI BİLGİLERİ (KOPYALA - YAPIŞTIR)")
    print("=" * 72)
    print(f"  • Yerel MCP URL  : http://{args.host}:{args.port}/mcp")
    if mcp_url:
        print(f"  • Uzak MCP URL   : {mcp_url}   <-- ChatGPT / Gemini / Claude'a bunu yapıştır!")
    print("-" * 72)
    print("  OYUN İÇİ KÖPRÜYÜ ÇALIŞTIRMAK İÇİN (2 YÖNTEMDEN BİRİNİ SEÇ):")
    print("  Yöntem A (Dosyadan): GENTAHAX -> Script sekmesi -> gentahax_bridge.lua -> Execute")
    print("  Yöntem B (Tek Satır — Dosyasız): Lua Executor'a şunu yapıştırıp Execute bas:")
    print(f'    load(makeRequest("http://127.0.0.1:{B.RELAY_PORT}/bridge.lua","GET",{{}},"",5000).content)()')
    print("=" * 72 + "\n")

    try:
        from server import mcp
        mcp.run(transport="http", host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n[mr_berk] Kapatılıyor...")
    finally:
        if cf_proc and cf_proc.poll() is None:
            cf_proc.terminate()


if __name__ == "__main__":
    main()
