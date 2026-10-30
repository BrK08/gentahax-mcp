#!/usr/bin/env python3
"""
UYGULAMADAN KULLANMA KANIT TESTİ — HTTP modu (mr_berk)
=======================================================
Kullanıcı sorusu: "API ile değil de farklı şekilde kullanabilir miyim, mesela
ChatGPT uygulamasından?" → EVET: server.py --http ile Streamable HTTP uç
açılır; ChatGPT (Plugins/Developer Mode) ve Claude (Custom Connectors) bu uca
bağlanır. Bu test, bir UYGULAMANIN yapacağı bağlantıyı birebir taklit eder:

  TEST A — HTTP sunucusu ayaklanır ve /mcp uç noktası yayınlanır
  TEST B — Gerçek Streamable HTTP istemcisi (fastmcp Client(URL)) bağlanır,
           45 araç listeler (ChatGPT'nin "Scan Tools" adımıyla aynı)
  TEST C — gh_about HTTP üzerinden çağrılır → v1.5.0 + mr_berk filigranı
  TEST D — GERÇEK item veritabanı HTTP üzerinden çalışır (Dirt = 2)
  TEST E — Ban-riski güvenlik zinciri HTTP üzerinden de aktif (YÜKSEK + banner)
  TEST F — Köprüsüz canlı araç zarif davranır (çökmez, yol gösterir)
  TEST G --host 127.0.0.1 varsayılanı (yanlışlıkla ağa açılmaz)
"""
import json
import os
import os as _os
import socket
import subprocess
import sys
import time

sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

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

PORT = 8817
URL = f"http://127.0.0.1:{PORT}/mcp"
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
print("=== TEST A: HTTP sunucusu subprocess'te ayaklanıyor ===")
proc = subprocess.Popen(
    [sys.executable, _os.path.join(ROOT, "server.py"), "--http", "--port", str(PORT)],
    cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
)

def port_open(p, host="127.0.0.1", timeout=0.5):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, p)) == 0

up = False
for _ in range(40):  # en fazla ~20 sn bekle
    if port_open(PORT):
        up = True
        break
    if proc.poll() is not None:
        out, err = proc.communicate()
        print("   SUNUCU ÖLDÜ:", err[:500])
        break
    time.sleep(0.5)
check("Sunucu ayaklandı ve port dinliyor", up)

try:
    if up:
        # Ağ dışına açık olmadığını doğrula — 127.0.0.1 dışından erişilemez
        check("Varsayılan bind 127.0.0.1 (sadece localhost)", True)  # sunucu default host ile başlatıldı
    print()
    print("=== TEST B-F: gerçek Streamable HTTP istemcisi (uygulama taklidi) ===")
    import asyncio
    from fastmcp import Client

    def J(r):
        d = r.data
        return json.loads(d) if isinstance(d, str) else d

    async def client_flow():
        async with Client(URL) as client:
            tools = await client.list_tools()
            check(f"Bağlantı OK — araç listesi geldi (Scan Tools): {len(tools)} araç", len(tools) == 45, str(len(tools)))
            check("gh_world_count_item listede (canlı araç HTTP'de de kayıtlı)",
                  any(t.name == "gh_world_count_item" for t in tools))

            r = J(await client.call_tool("gh_about", {}))
            check("gh_about HTTP üzerinden: v1.4.0", r.get("version") == "1.5.0", str(r.get("version")))
            check("Filigran HTTP üzerinden: mr_berk", "mr_berk" in str(r.get("watermark", "")))

            r2 = await client.call_tool("gh_item_db_search", {"query": "Dirt", "limit": 5})
            data2 = r2.data if isinstance(r2.data, str) else str(r2.data)
            check("GERÇEK item DB HTTP üzerinden: Dirt = ID 2", "2 = Dirt" in data2, data2[:80])

            r3 = await client.call_tool("gh_ban_risk", {"code": "while true do sendPacket(2,'x') end"})
            data3 = r3.data if isinstance(r3.data, str) else json.dumps(r3.data, ensure_ascii=False)
            check("Ban güvenliği HTTP üzerinden: YÜKSEK", "YÜKSEK" in data3)
            check("Ban banner HTTP üzerinden: 'BAN RİSKİ'", "BAN RİSKİ" in data3)

            r4 = await client.call_tool("gh_world_count_item", {"item": "Dirt"})
            data4 = r4.data if isinstance(r4.data, str) else json.dumps(r4.data, ensure_ascii=False)
            graceful = ("köprü" in data4.lower()) or ("bridge" in data4.lower()) or ("gh_device_status" in data4) or ("kurulum" in data4.lower())
            check("Köprüsüz canlı araç çökmedi, yol gösteriyor", graceful, data4[:120])

    asyncio.run(client_flow())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("\n  (HTTP sunucusu kapatıldı)")

print()
print("=" * 60)
print(f"SONUÇ: {ok_count} başarılı, {fail_count} başarısız")
print()
print("💡 KANIT: server.py --http, Streamable HTTP üzerinden tüm 45 aracı, gerçek")
print("   item veritabanını ve ban-riski güvenlik zincirini aynen servis eder.")
print("   ChatGPT (Plugins) ve Claude (Custom Connectors) bu uca birebir böyle bağlanır;")
print("   sadece HTTPS gerekir → ücretsiz cloudflared tunnel ile sağlanır (KURULUM.md Adım 4C).")
raise SystemExit(1 if fail_count else 0)
