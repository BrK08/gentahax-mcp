#!/usr/bin/env python3
"""
HERHANGİ BİR AI KANIT TESTİ — chat.py (mr_berk)
================================================
Kullanıcı isteği: "Yapay zekası olarak istediğim HERHANGİ BİR yapay zekayı
kullanmak istiyorum" — chat.py, OpenAI-uyumlu her sağlayıcıyı (OpenAI, Gemini,
GLM, DeepSeek, OpenRouter, Ollama...) MCP'nin 45 aracına bağlar.

Bu test GERÇEK bir API anahtarı GEREKMEZ: MockAI (OpenAI yanıt formatını birebir
taklit eden sahte sağlayıcı) ile aracın tool-calling döngüsü uçtan uca koşar.

  TEST A — Şema üretimi : 45 aracın TÜMÜ geçerli OpenAI function şemasına dönüşür
  TEST B — Tek tur      : MockAI gh_item_db_search('Dirt') çağırır → GERÇEK MCP aracı
                          çalışır → sonuç (Dirt=2) modele geri döner → nihai cevap
  TEST C — Güvenlik akışı: MockAI yüksek riskli kod için gh_code_analyze çağırır →
                          gerçek analiz 'BAN RİSKİ' döner → nihai cevap uyarı içerir
  TEST D — Sonuç akışı  : araç sonuçları history'ye 'tool' rolüyle doğru eklenir
  TEST E — Sağlayıcı çözümleme: env değişkenleri doğru okunur
"""
import asyncio
import json
import os as _os
import sys
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

# OpenAI-uyumlu yanıt yardımcıları (sahte sağlayıcının konuştuğu format)
def tool_call_msg(call_id, fn_name, args_json, text=None):
    return {"choices": [{"message": {
        "role": "assistant",
        "content": text,
        "tool_calls": [{"id": call_id, "type": "function",
                        "function": {"name": fn_name, "arguments": args_json}}],
    }}]}

def final_msg(text):
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


async def main():
    import chat as C
    from fastmcp import Client
    from server import mcp

    print("=== TEST A: 45 araç → OpenAI function şeması ===")
    async with Client(mcp) as client:
        tools = await client.list_tools()
        schemas = C.build_tool_schemas(tools)
        check("Tüm araçlar şemaya dönüştü (45)", len(schemas) == 45, str(len(schemas)))
        valid = all(s["type"] == "function" and s["function"]["name"]
                    and isinstance(s["function"]["parameters"], dict)
                    and s["function"]["parameters"].get("type") == "object"
                    for s in schemas)
        check("Her şema geçerli (name+description+parameters.type=object)", valid)
        gh_run = next(s for s in schemas if s["function"]["name"] == "gh_run_lua")
        check("gh_run_lua şeması risk açıklaması taşıyor", "BAN" in gh_run["function"]["description"].upper()
              or "risk" in gh_run["function"]["description"].lower())
        print()

        # ------------------------------------------------------------------
        print("=== TEST B: tek tur — MockAI gerçek aracı çağırıyor ===")
        # Senaryo: kullanıcı 'dirt kaç numara?' der; MockAI doğru aracı çağırır,
        # dönen GERÇEK sonuca göre cevap yazar (cevap içeriği MockAI'dan geliyor
        # ama araç SONUCU gerçek MCP katmanından).
        scripted = [
            tool_call_msg("c1", "gh_item_db_search", '{"query": "Dirt", "limit": 5}'),
            final_msg("Dirt = ID 2 (gerçek veritabanından). Tohumu: Dirt Seed = ID 3. — mr_berk"),
        ]
        state = {"i": 0, "seen_tool_result": None}

        def mock_ai(messages, tools):
            resp = scripted[state["i"]]
            state["i"] += 1
            # MockAI, history'deki tool mesajını gördü mü? (sonuç geri akışı)
            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            if tool_msgs:
                state["seen_tool_result"] = tool_msgs[-1]["content"]
            return resp

        agent = C.Agent(client, mock_ai, verbose=False)
        history = [{"role": "system", "content": C.SYSTEM_PROMPT}]
        answer = await agent.run("dirt kaç numara?", history)
        check("Nihai cevap döndü", "Dirt = ID 2" in answer, answer)
        check("Gerçek araç çağrıldı (trace)", agent.trace[0]["tool"] == "gh_item_db_search")
        check("GERÇEK sonuç (Dirt=2) modele geri aktı", state["seen_tool_result"] and "2" in state["seen_tool_result"]
              and "Dirt" in state["seen_tool_result"], str(state["seen_tool_result"])[:120])
        print(f"  → modele dönen gerçek sonuç: {str(state['seen_tool_result'])[:90]}...")
        print()

        # ------------------------------------------------------------------
        print("=== TEST C: güvenlik akışı — MockAI önce gh_code_analyze çağırır ===")
        risky_code = "while true do sendPacket(2, 'action|drop\\nitemID|2|n|1') end"
        scripted2 = [
            tool_call_msg("c2", "gh_code_analyze", json.dumps({"code": risky_code})),
            final_msg("⚠️ BUNDA BAN RİSKİ VAR! Bu kod sleep'siz paket spam içeriyor (YÜKSEK, 100/100). "
                      "Düzeltme: döngü içine sleep(500) ekle. Onaylarsan çalıştırırım. — mr_berk"),
        ]
        state2 = {"i": 0, "seen": None}

        def mock_ai2(messages, tools):
            resp = scripted2[state2["i"]]
            state2["i"] += 1
            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            if tool_msgs:
                state2["seen"] = tool_msgs[-1]["content"]
            return resp

        agent2 = C.Agent(client, mock_ai2, verbose=False)
        hist2 = [{"role": "system", "content": C.SYSTEM_PROMPT}]
        ans2 = await agent2.run("bu kodu çalıştır: " + risky_code, hist2)
        check("Nihai cevap ban uyarısı içeriyor", "BAN RİSKİ" in ans2)
        check("Gerçek analiz sonucu modele döndü (YÜKSEK görüldü)", state2["seen"] and "YÜKSEK" in state2["seen"])
        print(f"  → gerçek analiz: {str(state2['seen'])[:80]}...")
        print()

        # ------------------------------------------------------------------
        print("=== TEST D: history formatı (OpenAI standartlarına uygun) ===")
        roles = [m["role"] for m in hist2]
        check(" Roller: system → user → assistant(tool_calls) → tool → assistant",
              roles == ["system", "user", "assistant", "tool", "assistant"], str(roles))
        tc = hist2[2].get("tool_calls", [])
        check("assistant mesajı tool_calls taşıyor", tc and tc[0]["function"]["name"] == "gh_code_analyze")
        check("tool mesajı tool_call_id eşliyor", hist2[3].get("tool_call_id") == tc[0]["id"])
        print()

    # ----------------------------------------------------------------------
    print("=== TEST E: sağlayıcı çözümleme (env/arg) ===")
    os_environ = _os.environ

    class Args:
        provider = None; model = None; base_url = None; api_key = None

    a = Args(); a.provider = "ollama"
    n, base, model, key = C.resolve_provider(a)
    check("ollama → lokal uç + anahtarsız", base.startswith("http://localhost:11434") and key is None)

    a2 = Args(); a2.provider = "deepseek"; a2.api_key = "sk-test"
    n2, base2, model2, key2 = C.resolve_provider(a2)
    check("deepseek → doğru uç + anahtar", n2 == "deepseek" and "deepseek.com" in base2 and key2 == "sk-test")

    a3 = Args(); a3.provider = "custom"; a3.base_url = "http://localhost:1234/v1"; a3.model = "benim-modelim"
    n3, base3, model3, key3 = C.resolve_provider(a3)
    check("custom → kullanıcının ucu + modeli", base3 == "http://localhost:1234/v1" and model3 == "benim-modelim")

    # provider isim listesi
    check("10 sağlayıcı kayıtlı", len(C.PROVIDERS) == 10, str(len(C.PROVIDERS)))
    print()

    print("=" * 60)
    print(f"SONUÇ: {ok_count} başarılı, {fail_count} başarısız")
    print()
    print("💡 KANIT: chat.py' nin tool-calling döngüsü HERHANGİ BİR OpenAI-uyumlu AI ile")
    print("   aynı şekilde çalışır — MockAI gerçek formatı konuştı, gerçek MCP araçları")
    print("   koştu, sonuçlar modele geri aktı, güvenlik uyarısı nihai cevaba düştü.")
    raise SystemExit(1 if fail_count else 0)

asyncio.run(main())
