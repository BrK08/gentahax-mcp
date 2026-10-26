#!/usr/bin/env python3
"""MCP protokol katmanı uçtan uca test (mr_berk)"""
import asyncio
import json
import sys
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

def J(r):
    d = r.data
    return json.loads(d) if isinstance(d, str) else d
from fastmcp import Client

async def main():
    from server import mcp
    async with Client(mcp) as client:
        # 1. Bilgi aracı
        r = J(await client.call_tool("gh_about", {}))
        print("gh_about →", r["name"], "|", r["knowledge_stats"]["android_functions"], "android fonksiyonu")
        assert "mr_berk" in r["watermark"]

        # 2. Arama
        r = await client.call_tool("gh_api_search", {"query": "variant", "platform": "both"})
        print("gh_api_search('variant') →", len(str(r.data)), "karakter sonuç")

        # 3. Risk analizi — yüksek riskli kod
        r = J(await client.call_tool("gh_ban_risk", {"code": "while true do sendPacket(2, 'action|drop\\nitemID|2|n|1') end"}))
        print("gh_ban_risk →", r["risk"])
        assert "YÜKSEK" in r["risk"]
        assert r["banner"] and "BAN RİSKİ" in r["banner"]
        print("  ⚠️ Banner doğru döndü:", r["banner"][:60], "...")

        # 4. Variant rehberi
        r = await client.call_tool("gh_variant_guide", {})
        print("gh_variant_guide →", len(r.data), "karakter; DLL doğrulamalı:", "verified_from_dll_v561" in r.data)

        # 5. run_lua — köprü yok → bilgilendirme; köprü olsa bile yüksek risk reddi
        r = await client.call_tool("gh_run_lua", {"code": "while true do sendPacket(2,'x') end"})
        print("gh_run_lua (yüksek risk) →", str(r.data)[:100])

        # 6. Şablon
        r = J(await client.call_tool("gh_template_get", {"template_id": "varlist_logger"}))
        print("gh_template_get →", r["name"])

        # 7. Eğitim rehberi
        r = await client.call_tool("gh_learn_lua_gentahax", {"topic": "farming"})
        print("gh_learn_lua_gentahax('farming') →", len(r.data), "karakter")

        # 8. Filigran
        r = J(await client.call_tool("gh_watermark", {}))
        assert "mr_berk" in r["imza_bloku"]
        print("gh_watermark → imza bloğu OK")

    print("\n✅ MCP PROTOKOL TESTİ: TÜM ÇAĞRILAR BAŞARILI")

asyncio.run(main())
