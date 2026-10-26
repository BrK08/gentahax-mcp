#!/usr/bin/env python3
"""
GENTAHAX MCP — HERHANGİ BİR AI ile SOHBET MODU (mr_berk edition)
=================================================================
Claude Desktop'a ihtiyaç YOK. OpenAI-uyumlu (OpenAI-compatible) HERHANGİ bir
AI'yi GENTAHAX MCP'nin 40 aracına bağlar:

  OpenAI (ChatGPT) · DeepSeek · GLM (Z.ai) · Google Gemini (OpenAI uçları)
  OpenRouter (tek anahtarla 300+ model) · Qwen · Mistral
  Ollama (ÜCRETSİZ, lokal) · LM Studio (ÜCRETSİZ, lokal)

KULLANIM:
  python chat.py --list-ai                       # desteklenen AI'leri listele
  python chat.py --check                         # MCP tarafını anahtarsız self-test et
  python chat.py --provider openai  --ask "dirt kaç numara?"
  python chat.py --provider ollama  --model llama3.1   # ücretsiz lokal AI, interaktif
  python chat.py --ask "dünyada kaç tane dirt var?"    # env'den ayarları okur

ANAHTARLAR (ortam değişkeni ya da --api-key):
  GENTAHAX_AI_PROVIDER  : openai|deepseek|glm|gemini|openrouter|ollama|lmstudio|qwen|mistral|custom
  GENTAHAX_AI_BASE_URL  : custom sağlayıcı için API tabanı (ör. http://localhost:1234/v1)
  GENTAHAX_AI_API_KEY   : sağlayıcı anahtarı (ollama/lmstudio için gerekmez)
  GENTAHAX_AI_MODEL     : model adı (sağlayıcı varsayılanını ezer)

Köprü ayarları (server.py ile aynı): GENTAHAX_SCRIPT_DIR / GENTAHAX_TARGET=adb / ...

Filigran: mr_berk
"""
import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request

WATERMARK = "mr_berk"
MAX_TURNS = 8            # en fazla 8 tur tool-arama (sonsuz döngü koruması)
MAX_RESULT_CHARS = 4000  # araç sonucundan modele gidecek maksimum uzunluk

# ---------------------------------------------------------------------------
# Desteklenen AI sağlayıcıları (hepsi OpenAI-uyumlu /chat/completions konuşur)
# ---------------------------------------------------------------------------
PROVIDERS = {
    "openai":    {"base": "https://api.openai.com/v1",
                  "model": "gpt-4o-mini",
                  "key_env": "OPENAI_API_KEY",
                  "hint": "platform.openai.com'dan anahtar"},
    "deepseek":  {"base": "https://api.deepseek.com/v1",
                  "model": "deepseek-chat",
                  "key_env": "DEEPSEEK_API_KEY",
                  "hint": "platform.deepseek.com (çok ucuz)"},
    "glm":       {"base": "https://open.bigmodel.cn/api/paas/v4",
                  "model": "glm-4-flash",
                  "key_env": "GLM_API_KEY",
                  "hint": "Z.ai / bigmodel.cn — glm-4-flash ÜCRETSİZ katmanı var"},
    "gemini":    {"base": "https://generativelanguage.googleapis.com/v1beta/openai",
                  "model": "gemini-2.0-flash",
                  "key_env": "GEMINI_API_KEY",
                  "hint": "Google AI Studio'dan ücretsiz anahtar"},
    "openrouter": {"base": "https://openrouter.ai/api/v1",
                   "model": "openai/gpt-4o-mini",
                   "key_env": "OPENROUTER_API_KEY",
                   "hint": "tek anahtarla 300+ model"},
    "qwen":      {"base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                  "model": "qwen-plus",
                  "key_env": "DASHSCOPE_API_KEY",
                  "hint": "Alibaba Cloud DashScope"},
    "mistral":   {"base": "https://api.mistral.ai/v1",
                  "model": "mistral-small-latest",
                  "key_env": "MISTRAL_API_KEY",
                  "hint": "console.mistral.ai"},
    "ollama":    {"base": "http://localhost:11434/v1",
                  "model": "llama3.1",
                  "key_env": None,
                  "hint": "ÜCRETSİZ + LOKAL: ollama.com indir, 'ollama pull llama3.1'"},
    "lmstudio":  {"base": "http://localhost:1234/v1",
                  "model": "local-model",
                  "key_env": None,
                  "hint": "ÜCRETSİZ + LOKAL: lmstudio.ai indir, Developer sekmesinden sunucuyu aç"},
    "custom":    {"base": None,
                  "model": None,
                  "key_env": "GENTAHAX_AI_API_KEY",
                  "hint": "GENTAHAX_AI_BASE_URL + GENTAHAX_AI_MODEL ile herhangi bir uç"},
}

SYSTEM_PROMPT = f"""Sen GENTAHAX MCP'nin Growtopia script uzmanısın ({WATERMARK} edition).
Araçların bilgisi GERÇEK verilerle derlendi: GENTAHAX v5.61 resmi dokümantasyon + DLL binary analizi + 6832 eşyalık gerçek items.dat veritabanı.

KURALLAR (mutlaka uyar):
1. KOD ÇALIŞTIRMADAN ÖNCE gh_code_analyze çağır. YÜKSEK risk çıkarsa kullanıcıya '⚠️ BUNDA BAN RİSKİ VAR' diye uyar ve onay almadan gh_run_lua ÇAĞIRMA.
2. Fonksiyon imzalarını ASLA uydurma — emin değilsen gh_api_search / gh_api_detail ile doğrula.
3. Eşya ID'leri için gh_item_db_search / gh_item_db_info kullan. Belirsiz isimde tahmin etme, adayları listele.
4. Canlı oyun verisi (dünya sayımı, oyuncu, envanter) köprü gerektirir. Önce gh_device_status ile kontrol et; 'configured: false' dönerse kullanıcıya KURULUM.md Adım 5'i (gh_bridge_deploy → oyunda Execute → gh_device_status) anlat.
5. Kullanıcının dilinde cevap ver (varsayılan Türkçe). Kısa, net, SAMİMİ ol.
6. Ban riski olmayan okuma araçlarını (gh_world_count_item, gh_world_census...) rahatça kullan.
Filigran: {WATERMARK}"""


# ---------------------------------------------------------------------------
# OpenAI-uyumlu HTTP çağrısı (ek kütüphane YOK, stdlib urllib)
# ---------------------------------------------------------------------------
def ai_complete(base_url, api_key, model, messages, tools):
    """POST {base}/chat/completions — OpenAI-uyumlu yanıt döndürür."""
    payload = {"model": model, "messages": messages, "temperature": 0.3}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key or 'no-key'}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_tool_schemas(mcp_tools):
    """fastmcp araç listesini OpenAI 'function calling' şemasına çevirir."""
    out = []
    for t in mcp_tools:
        schema = dict(t.inputSchema or {"type": "object", "properties": {}})
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        out.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": (t.description or "")[:1200],
                "parameters": schema,
            },
        })
    return out


def clip(text, limit=MAX_RESULT_CHARS):
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...(kısaltıldı, tamı için gh araçlarını çağır) [{WATERMARK}]"


# ---------------------------------------------------------------------------
# Agent — aracı şirketten bağımsız yap (test edilebilirlik için)
# ---------------------------------------------------------------------------
class Agent:
    def __init__(self, client, ai_fn, verbose=True):
        self.client = client      # fastmcp Client (in-process MCP)
        self.ai_fn = ai_fn        # ai_fn(messages, tools) -> dict (OpenAI formatı)
        self.verbose = verbose
        self.trace = []           # kullanılan araçlar

    async def run(self, user_msg, history):
        history.append({"role": "user", "content": user_msg})
        tools = build_tool_schemas(await self.client.list_tools())
        for _turn in range(MAX_TURNS):
            resp = self.ai_fn(history, tools)
            msg = resp["choices"][0]["message"]
            assistant = {"role": "assistant", "content": msg.get("content") or ""}
            calls = msg.get("tool_calls") or []
            if calls:
                assistant["tool_calls"] = calls
                assistant["content"] = msg.get("content") or None
            history.append(assistant)
            if not calls:
                return msg.get("content") or "(boş yanıt)"
            for call in calls:
                fn = call["function"]
                name, args = fn["name"], {}
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                if self.verbose:
                    print(f"  🔧 {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})")
                try:
                    r = await self.client.call_tool(name, args)
                    result = r.data if hasattr(r, "data") else str(r)
                except Exception as e:
                    result = f"ARAÇ HATASI: {e}"
                self.trace.append({"tool": name, "args": args})
                history.append({"role": "tool",
                                "tool_call_id": call["id"],
                                "content": clip(result)})
        return f"⚠️ {MAX_TURNS} tur araç çağrısı limiti doldu — isteğini parçala. [{WATERMARK}]"


# ---------------------------------------------------------------------------
# Self-test: anahtarsız MCP tarafını doğrular (kullanıcının İLK test komutu)
# ---------------------------------------------------------------------------
async def self_check():
    from fastmcp import Client
    from server import mcp
    print(f"🎮 GENTAHAX MCP self-test — {WATERMARK} edition\n")
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print(f"  ✅ MCP sunucusu yüklendi: {len(tools)} araç kayıtlı")
        r = await client.call_tool("gh_about", {})
        about = r.data if isinstance(r.data, dict) else json.loads(r.data)
        ver = about.get("version", "?")
        print(f"  ✅ gh_about → v{ver} | filigran: {about.get('watermark')}")
        r2 = await client.call_tool("gh_item_db_search", {"query": "Dirt", "limit": 5})
        data2 = r2.data if isinstance(r2.data, str) else str(r2.data)
        assert "2" in data2 and "Dirt" in data2
        print(f"  ✅ Gerçek item veritabanı çalışıyor: Dirt = ID 2 ({data2.splitlines()[0].strip()[:60]}...)")
        r3 = await client.call_tool("gh_ban_risk", {"code": "while true do sendPacket(2,'x') end"})
        data3 = r3.data if isinstance(r3.data, str) else json.dumps(r3.data, ensure_ascii=False)
        assert "YÜKSEK" in data3
        print(f"  ✅ Ban-riski uyarı sistemi çalışıyor: yüksek riskli kod → YÜKSEK + 'BAN RİSKİ'")
        import bridge as B
        st = B.status()
        if st.get("configured"):
            print(f"  ✅ Köprü yapılandırıldı: {st.get('mode')} → {st.get('script_dir') or st.get('remote_script_dir')}")
            alive = st.get("bridge_responding")
            if alive:
                print("  ✅ Oyun içi köprü CANLI (PONG) — canlı araçlar hazır 🎉")
            else:
                print("  ⚠️  Köprü dosyası var ama oyun yanıt vermiyor — oyunda gentahax_bridge.lua'yı Execute et")
        else:
            print("  ℹ️  Köprü henüz ayarlanmadı (bilgi araçları yine de tam çalışır) — canlı veri için KURULUM.md Adım 5")
    print(f"\n✅ MCP TARAFI TAMAM — şimdi AI'nı bağla: python chat.py --provider <ad> --ask \"...\"")
    print("   Anahtarsız denemek için: python chat.py --provider ollama (lokal, ücretsiz)")


# ---------------------------------------------------------------------------
# Ana program
# ---------------------------------------------------------------------------
def resolve_provider(args):
    name = args.provider or os.environ.get("GENTAHAX_AI_PROVIDER", "").lower()
    if name and name not in PROVIDERS:
        sys.exit(f"Bilinmeyen sağlayıcı: '{name}' — --list-ai ile listeyi gör")
    if not name:
        name = "openai"
    p = PROVIDERS[name]
    base = (args.base_url or os.environ.get("GENTAHAX_AI_BASE_URL") or p["base"])
    model = (args.model or os.environ.get("GENTAHAX_AI_MODEL") or p["model"])
    key = (args.api_key or os.environ.get("GENTAHAX_AI_API_KEY")
           or (os.environ.get(p["key_env"]) if p.get("key_env") else None))
    if not base:
        sys.exit("custom sağlayıcı için --base-url (veya GENTAHAX_AI_BASE_URL) gerekli")
    return name, base, model, key


def main():
    ap = argparse.ArgumentParser(description=f"GENTAHAX MCP — herhangi bir AI ile sohbet ({WATERMARK})")
    ap.add_argument("--provider", help="openai|deepseek|glm|gemini|openrouter|qwen|mistral|ollama|lmstudio|custom")
    ap.add_argument("--model", help="model adı (sağlayıcı varsayılanını ezer)")
    ap.add_argument("--base-url", help="custom API tabanı (ör. http://localhost:1234/v1)")
    ap.add_argument("--api-key", help="API anahtarı (ollama/lmstudio için gerekmez)")
    ap.add_argument("--ask", help="tek soru modu: --ask \"dünyada kaç dirt var?\"")
    ap.add_argument("--list-ai", action="store_true", help="desteklenen AI'leri listele ve çık")
    ap.add_argument("--check", action="store_true", help="anahtarsız MCP self-test")
    ap.add_argument("--quiet", action="store_true", help="araç çağrılarını gösterme")
    args = ap.parse_args()

    if args.list_ai:
        print("🤖 DESTEKLENEN AI SAĞLAYICILARI — hepsi OpenAI-uyumlu uçlar üzerinden bağlanır\n")
        for name, p in PROVIDERS.items():
            model = p["model"] or "(--model ile belirt)"
            key_note = "anahtar GEREKMEZ (lokal/ücretsiz)" if p["key_env"] is None else f"anahtar: {p['key_env']}"
            print(f"  {name:<11} model={model:<22} {key_note}\n              {p['hint']}")
        print("\nMCP destekleyen uygulamalarla da kullanabilirsin (bu dosya gerekmez):")
        print("  Claude Desktop · Cursor · VS Code Copilot · Windsurf · Zed · Cline — bkz. KURULUM.md")
        return

    if args.check:
        asyncio.run(self_check())
        return

    name, base, model, key = resolve_provider(args)
    if not key and name not in ("ollama", "lmstudio", "custom"):
        key_env = PROVIDERS[name]["key_env"]
        sys.exit(f"⚠️ '{name}' için API anahtarı yok.\n"
                 f"   Ya ortam değişkeni ver:  set {key_env}=sk-...\n"
                 f"   Ya da argümanla:          python chat.py --provider {name} --api-key sk-...\n"
                 f"   Anahtarsız denemek için:  python chat.py --provider ollama  (lokal, ücretsiz)")

    from fastmcp import Client
    from server import mcp

    def real_ai(messages, tools):
        try:
            return ai_complete(base, key, model, messages, tools)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"AI sağlayıcısı hata döndürdü (HTTP {e.code}): {body}")
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"AI sağlayıcısına ulaşılamadı: {e.reason}\n"
                + ("Ollama kurulu mu? 'ollama serve' çalışıyor mu?" if name == "ollama" else "Base URL doğru mu / internet var mı?"))

    async def loop():
        async with Client(mcp) as client:
            agent = Agent(client, real_ai, verbose=not args.quiet)
            history = [{"role": "system", "content": SYSTEM_PROMPT}]
            print(f"🎮 GENTAHAX MCP + {name}/{model} — {WATERMARK} edition")
            print("   '/tools' araçları listeler · '/exit' çıkar · örnek: 'dirt kaç numara?'\n")
            if args.ask:
                answer = await agent.run(args.ask, history)
                print(f"\n🤖 {answer}")
                return
            while True:
                try:
                    user = input("👤 sen: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n👋 görüşürüz!")
                    return
                if not user:
                    continue
                if user == "/exit":
                    print("👋 görüşürüz!")
                    return
                if user == "/tools":
                    tools = await client.list_tools()
                    print("🔧", ", ".join(t.name for t in tools))
                    continue
                if user == "/temizle":
                    history[:] = [{"role": "system", "content": SYSTEM_PROMPT}]
                    print("  (geçmiş temizlendi)")
                    continue
                try:
                    answer = await agent.run(user, history)
                    print(f"\n🤖 {answer}\n")
                except RuntimeError as e:
                    print(f"\n❌ {e}\n")

    asyncio.run(loop())


if __name__ == "__main__":
    main()
