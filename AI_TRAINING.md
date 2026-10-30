# GENTAHAX AI TRAINING PACK — mr_berk edition v1.5.0

> **Paste this pack into ANY chat AI (ChatGPT, Claude, Gemini, GLM, DeepSeek...) and it
> will write VALID GENTAHAX scripts.** Everything below is generated from REAL data:
> official GENTAHAX v5.61 docs + DLL binary verification + the 6832-item items.dat
> database. There is NOT a single invented function or ID in this pack.

## 0) How to Use
- **ChatGPT (no API):** open a new chat → paste this WHOLE file as the first message
  (or put it into a Custom GPT's Instructions) → then ask: *"break all the peppers in the world"*
- **Claude:** upload to Project Knowledge or paste at the start of a chat
- Save the produced script into the GENTAHAX **Script** folder → run it with the in-game **Lua Executor**
- With the MCP connected, the AI generates via `gh_script_gen`, then `gh_auto_test`
  **runs it, reads the logs and tells you '✅ IT WORKS' or the exact error**

## 1) 7 Golden Rules
1. Use ONLY the functions listed below — **NEVER invent**. ('getPlayerList' WRONG → 'getPlayerlist' RIGHT.)
2. NEVER guess item IDs — take them from the table or resolve live via `getItemByName('X').id`.
3. Every loop MUST `sleep(math.random(200, 600))` — otherwise the client freezes + ban risk.
4. Guard the game objects: `local w = getWorld() if not w then return 'ERR|NO_WORLD' end`
5. Any packet-sending loop is ban-risky — tell the user **"⚠️ THIS HAS BAN RISK"** explicitly.
6. Do background work in `runThread(fn, 'tag')` and make it stoppable with `killThread('tag')`.
7. Auto-test markers: `doLog('AUTOTEST|START|...')` at start, `doLog('AUTOTEST|OK|...')` at end.

## 2) Auto-Test Loop (the AI's standard workflow)
```
1) write the script (following the rules)
2) RUN it in the GENTAHAX executor (MCP: gh_auto_test)
3) READ lua_logs.txt
4a) AUTOTEST|OK / FARM_RESULT / error-free progress → tell the user "✅ IT WORKS"
4b) error line → diagnose via the ERROR TABLE → fix → RUN AGAIN (max 2 retries)
   → still failing? honestly explain the error and what you tried
```
**CRITICAL:** the WORKS/ERROR verdict comes ONLY from the game's own executor and its logs.
Any external Lua editor does NOT know the in-game functions — never "fix" correct code
because an outside tool said the function is missing! A syntax (compile) check never
executes the code and CANNOT produce false errors on game functions; the only authority
on function existence is the executor itself.

## 3) Error Table (GENTAHAX executor lua_logs.txt format)
| Hata sınıfı | Executor logda nasıl görünür / neden | Ne yapılır |
|---|---|---|
| MISSING_FN | Çağrılan fonksiyon bu oyunda YOK — isim yanlış yazılmış ya da bu APK sürümünde bulunmuyor | Hata satırındaki şüpheli çağrımı gh_api_detail ile doğrula, değişkenlere nil koruması ekle |
| NIL_INDEX | Nil yerel değişken — büyük ihtimalle getWorld()/getLocal() boş döndü (dünyada değil misin?) | Script başına koruma ekle: local w = getWorld() if not w then return 'ERR|NO_WORLD' end — ve dünyada olduğunda |
| NIL_ARITH | Nil üzerinde aritmetik — değer hesaplanmamış (oyun verisi gelmeden mi kullanıldı?) | Değerlere varsayılan ver: (me.gems or 0), (w.width or 100) gibi |
| NIL_COMPARE | Nil karşılaştırma — değer hiç gelmemiş | Hata satırındaki şüpheli çağrımı gh_api_detail ile doğrula, değişkenlere nil koruması ekle |
| SYNTAX | Söz dizimi hatası — kod derlenmedi | Parantez/'end' dengesini kontrol et — gh_code_analyze'ın syntax_issues bölümü satırı işaret eder |
| LUA_ERR | Genel Lua çalışma zamanı hatası | Hata satırındaki şüpheli çağrımı gh_api_detail ile doğrula, değişkenlere nil koruması ekle |
| NOT_IN_WORLD | Executor 'ERR|NO_WORLD' döndü — dünyada değilsin | Oyunu aç, bir dünyaya gir, sonra tekrar çalıştır |
| NO_LOCAL | Executor 'ERR|NO_LOCAL' döndü — oyuncu henüz yüklenmedi | 2-3 saniye bekle ve tekrar çalıştır — oyun ekranı tam açılmamış olabilir |

## 4) ANDROID Lua API — REAL (DLL v5.61 verified)
### ANDROID — 57 fonksiyon (kaynak: OFFICIAL GENTA-HAX-DOCS (github.com/GENTA7740/GENTA-HAX-DOCS) + GENTAHAX v5.61 GTInternal....)

**ACTION**

- `void requestCollect(int x, int y, int itemID)` — risk: medium
  Verilen koordinattaki yerdeki esyayi toplama istegi gonderir. BAN RISKI: Hizli dongude kullanilirsa auto-collect bot algilanabilir.
- `void requestTileChange(int x, int y, int item_id)` — risk: medium
  Verilen koordinata blok koyma/kesme istegi gonderir (PACKET_TILE_CHANGE_REQUEST). BAN RISKI: Spam yapilirsa block spam algilanir.

**CAMERA**

- `Camera* getCamera()` — risk: low
  Kamera nesnesini dondurur.
- `Vector2f worldToScreen(float x, float y)` — risk: low
  Dunya koordinatini ekran koordinatina cevirir. ESP cizimi icin vazgecilmez.
- `void setCamera(float x, float y)` — risk: low
  Kamerayi verilen dunya koordinatina tasir (Free Camera).

**CHEAT**

- `bool getCheat(int cheat_code)` — risk: low
  Belirtilen cheat'in acik olup olmadigini dondurur. Cheat kodlari icin CheatCode enum'una bakin.
- `void toggleCheat(int cheat_code, bool state)` — risk: medium
  Cheat'i acar/kapar. BAN RISKI: Hareketi etkileyen cheatler (Mod Fly, No Clip) sunucu tarafinda anomali olarak algilanabilir.
- `void restoreMemoryByName(String cheat_name) -- Buyuk/kucuk harf duyarsiz` — risk: medium
  Isimle belirtilen bellek yamasini geri alir (or. 'Mod Fly'). DLL'de dogrulanan isimler: Mod Fly, Ghost Mode, Night Vision, Can See Ghost, Anti portal,
- `void patchMemoryByName(String cheat_name) -- Buyuk/kucuk harf duyarsiz` — risk: medium
  Isimle belirtilen bellek yamasini uygular (or. 'Mod Fly'). BAN RISKI: patch + restore hizli donusumleri hareket anomalisine yol acar.

**CONNECTION**

- `void sendWebhook(String url, DiscordWebhook)` — risk: low
  Discord webhook'una mesaj/embed gonderir. DiscordWebhook yapisi: username, avatar_url, content, useEmbeds, embeds.
- `Response makeRequest(String url, String method, std::list<String> header, String body, int connection_time_out)` — risk: low
  HTTP istegi yapar. method: 'GET'/'POST'. Donus: Response.content. DLL icinde ornek kullanim: load(makeRequest(url,'GET').content)()

**DEVICE**

- `String getMac()` — risk: low
  Cihazin MAC adresini dondurur.
- `String getGid()` — risk: low
  Cihazin Google ID (GID) degerini dondurur.
- `void randomGid()` — risk: high
  GID degerini rastgele degistirir. BAN RISKI: HWID degistirme sunucu tarafinda algilanabilir, ozellikle ban yemek icin kullaniliyorsa kalici ban riski 
- `void randomMac()` — risk: high
  MAC adresini rastgele degistirir. BAN RISKI: randomGid ile ayni risk seviyesi.
- `void setGid(String newGoogleID) -- max 37 karakter` — risk: high
  GID'i verilen degerle degistirir (max 37 karakter). BAN RISKI: HWID manipulasyonu.
- `void setMac(String newMac) -- max 18 karakter` — risk: high
  MAC adresini verilen degerle degistirir (max 18 karakter). BAN RISKI: HWID manipulasyonu.

**HOOK**

- `void AddHook(GentaHook, String HookLabel, function)` — risk: low
  Oyun olaylarina fonksiyon baglar. Hook isimleri: OnTextPacket, OnVarlist, OnTouch, OnRender, OnRawPacket, OnGameUpdatePacket, OnENetInit. HookLabel be
- `void RemoveHooks()` — risk: low
  Tum hooklari kaldirir.
- `void RemoveHook(String HookLabel)` — risk: low
  Belirtilen etiketli hook'u kaldirir.

**INVENTORY**

- `std::list<Inventory*> getInventory()` — risk: low
  Oyuncunun envanterindeki tum esyalari {id, amount} olarak dondurur.

**ITEMDB**

- `ItemInfo* getItemByID(int itemID)` — risk: low
  Esya ID'sinden esya bilgisini dondurur (name, rarity, growth, texture, collisionType, clothType, blockType). Oyunun canli items.dat'ini sorgular.
- `ItemInfo* getItemByName(String itemName)` — risk: low
  Esya adindan esya bilgisini dondurur.

**LOGGING**

- `void logToConsole(String text)` — risk: low
  GENTAHAX konsoluna yazar (lua_logs.txt'ye dusmez, sadece konsol).
- `void doLog(String text)` — risk: low
  Log dosyasina yazar (lua_logs.txt).
- `void doLogError(String text) -- Logcat seviyesi` — risk: low
  Logcat error seviyesinde loglar.
- `void doLogInfo(String text) -- Logcat seviyesi` — risk: low
  Logcat info seviyesinde loglar.

**MOVEMENT**

- `bool findPath(int x, int y)` — risk: medium
  Oyuncuyu verilen koordinata yurutur (path finding). BAN RISKI: Imkansiz noktalara yurume/sik istek hareket anomalisi.

**PACKET**

- `void sendPacket(int type, String pkt)` — risk: medium
  Sunucuya text paketi gonderir. type=2 (text), pkt ornek: 'action|input\ntext|merhaba'. BAN RISKI: Dongu icinde delaysiz kullanilirsa paket spam algila
- `void sendPacketRaw(bool send_to_client, TankPacketStruct packet)` — risk: medium
  TankPacketStruct ile ham (raw) paket gonderir. send_to_client=true olursa paketi istemciye (kendine) gonderir. BAN RISKI: Hareket/punch paketleri spam
- `void sendVariant(variantlist_t var, int netID, int delay)` — risk: medium
  Variant list paketi gonderir. var = { [0]='fonksiyon_adi', ... } seklinde 7 hucreli dizi. BAN RISKI: Sahte konsol mesaji / taklit paketleri sunucu tar

**PLAYER**

- `NetAvatar* getLocal()` — risk: low
  Yerel (kendi) oyuncunun NetAvatar nesnesini dondurur. Isim, pozisyon, gems, kuafor kiyafet ID'leri gibi tum bilgiler bu nesnede.
- `NetAvatar* getPlayerByNetID(int netid)` — risk: low
  Verilen netID'ye sahip oyuncuyu dondurur. Dunyadaki baska oyuncularin bilgisini almak icin kullanilir.
- `std::list<NetAvatar*> getPlayerlist()` — risk: low
  Dunyadaki tum oyuncularin NetAvatar listesini dondurur. ESP, oyuncu listesi, topluluk analizi icin kullanilir.

**THREAD**

- `void runThread(function(), [optional] String thread_label)` — risk: low
  Fonksiyonu ayri bir thread'de calistirir. UI donmamasi icin uzun islemler thread'de yapilmalidir.
- `void killAllThread()` — risk: low
  Tum script thread'lerini oldurur.
- `table{String} getThreadsID()` — risk: low
  Calisan thread'lerin etiketlerini dondurur.
- `void killThread(String thread_label)` — risk: low
  Belirtilen thread'i oldurur.

**TIMING**

- `unsigned long getCurrentTimeInternal()` — risk: low
  Sistem saatini milisaniye cinsinden dondurur. Auto-farm dongulerinde delay hesabi icin kullanilir.
- `void sleep(int sleep_in_ms)` — risk: low
  Script thread'ini verilen milisaniye kadar uyutur. Paket gonderen dongulerde MUTLAKA kullanilmalidir (spam/ban korumasi).

**TOUCH**

- `Vector2f getTouchAtScreenPos()` — risk: low
  Ekrandaki dokunma pozisyonunu dondurur (piksel).
- `Vector2f getTouchAtWorldPos()` — risk: low
  Dokunmanin dunya koordinatindaki karsiligini dondurur.

**UI**

- `void doToast(int toastType, int dissMissTimeInMilliSeconds, String text)` — risk: low
  ImGui toast bildirimi gosterir. toastType: 0=None, 1=Success, 2=Warning, 3=Error, 4=Info.
- `void callToast(String text, int type) -- type=1 uzun, type=0 kisa (Java Toast)` — risk: low
  Android Java Toast gosterir.
- `Vector2f getScreenSize()` — risk: low
  Ekran boyutunu dondurur.

**USEFUL**

- `void arrowToItem(bool isFloatingObject, int itemID_Target)` — risk: low
  Verilen esyaya yonelen ok gosterir.
- `std::string getDiscordID()` — risk: low
  GENTAHAX kullanicisinin Discord ID'sini dondurur.
- `bool checkPath(int x, int y)` — risk: low
  Verilen koordinata yol olup olmadigini kontrol eder.
- `int hash32(String)` — risk: low
  Verilen stringin 32-bit hash'ini dondurur.
- `int hash64(String)` — risk: low
  Verilen stringin 64-bit hash'ini dondurur.

**WORLD**

- `World* getWorld()` — risk: low
  Bulunulan dunyanin bilgilerini dondurur.
- `Tile* checkTile(int x, int y)` — risk: low
  Verilen koordinattaki tile'i dondurur (fg, bg, flags, collision). Dunya disina tasarsa nil doner.
- `std::vector<Tile*> getTile()` — risk: low
  Dunyadaki tum tile'lari dondurur. Buyuk dunyalarde cok veri icerir.
- `TileExtra* getExtraTile(int x, int y)` — risk: low
  Tile'in ekstra bilgilerini dondurur: kilit sahibi, agac buyumesi, ready (hasat) durumu, label, admin listesi.
- `void setTile(Tile*)` — risk: low
  Tile nesnesini degistirir. Dikkat: sadece istemci tarafinda gecerlidir, sunucu tarafini etkilemez.
- `std::list<WorldObject*> getWorldObject()` — risk: low
  Dunyada yerde duran tum nesneleri (dusen esyalar) dondurur. Auto-collect scriptlerinin temeli.
- `std::list<NPCList*> getNpc()` — risk: low
  Dunyadaki NPC'leri dondurur.

## 5) WINDOWS Lua API — REAL
### WINDOWS — 18 fonksiyon (kaynak: OFFICIAL GENTA-HAX-DOCS DOCS-WINDOWS.md + GENTAHAX v5.61 GTInternal.dll binary verificatio...)

**HOOK**

- `void AddHook(GentaHook, String HookLabel, function)` — risk: low
  Hook ekler. Windows hooklari: OnPacket, OnVarlist, OnProcessRaw.
- `void RemoveHooks()` — risk: low
  Tum hooklari kaldirir.
- `void RemoveHook(String HookLabel)` — risk: low
  Tek hook'u kaldirir.

**INVENTORY**

- `std::list<Inventory*> GetInventory()` — risk: low
  Envanteri (id, amount) dondurur.

**ITEMDB**

- `ItemInfo* GetItemByID(int itemID)` — risk: low
  Esya bilgisini dondurur. Windows ItemInfo: Name, ItemType, Rarity, Growth, Collision.

**LOGGING**

- `void Log(String text)` — risk: low
  GENTAHAX log konsoluna yazar.

**MOVEMENT**

- `bool FindPath(int x, int y, int delay)` — risk: medium
  Path finding ile oyuncuyu yurutur. DIKKAT: Windows surumunde ucuncu parametre delay (ms)'dir, Android'de yoktur.

**PACKET**

- `void SendPacket(int type, String pkt)` — risk: medium
  Text paketi gonderir. BAN RISKI: Spam dongulerinde algilanir.
- `void SendPacketRaw(int flags, TankPacketStruct packet)` — risk: medium
  Raw paket gonderir. DIKKAT: Windows surumunde ilk parametre send_to_client (bool) degil flags (int)'tir. ENet flagleri: 0=RELIABLE, 1=UNSEQUENCED, 2=N

**PLAYER**

- `NetAvatar* GetLocal()` — risk: low
  Yerel oyuncunun NetAvatar nesnesini dondurur. Windows surumunde NetAvatar alanlari: name, status, ances, netid, necklace, ping, skin, day, mask, face,
- `std::list<NetAvatar*> GetPlayerlist()` — risk: low
  Dunyadaki tum oyuncularin listesini dondurur.

**TIMING**

- `void sleep(int sleep_in_ms)` — risk: low
  Thread'i uyutur. Paket dongulerinde zorunlu.

**USEFUL**

- `void PlaySound(String m_sound_path)` — risk: low
  Ses dosyasi calar (Windows'a ozel).

**WORLD**

- `World* GetWorld()` — risk: low
  Dunya bilgisini dondurur (name, width, height, tilecount).
- `Tile* CheckTile(int x, int y)` — risk: low
  Koordinattaki tile'i dondurur (fg, bg, ready, x, y).
- `std::vector<Tile*> GetTile()` — risk: low
  Tum tile'lari dondurur.
- `std::list<WorldObject*> GetWorldObject()` — risk: low
  Yerdeki nesneleri dondurur (id, amount, oid, invbits, x, y).
- `std::list<NPCList*> GetNPC()` — risk: low
  NPC listesini dondurur.

## 6) Common REAL Item IDs
| Eşya | ID |
|---|---|
| Dirt | 2 |
| Dirt Seed | 3 |
| Lava | 4 |
| Main Door | 6 |
| Bedrock | 8 |
| Rock | 10 |
| Rock Seed | 11 |
| Door | 12 |
| Cave Background | 14 |
| Grass | 16 |
| Sign | 20 |
| Wooden Background | 52 |
| Wood Block | 100 |
| Gems | 112 |
| White Block | 168 |
| World Lock | 242 |
| Checkpoint | 410 |
| Growtoken | 1486 |
| Diamond Lock | 1796 |
| Cave Dirt | 3564 |
| Pepper | 4570 |
| Pepper Seed | 4571 |
| Pepper Tree | 4584 |

The full 6832-item database lives in the MCP (`gh_item_db_search`). If an item is
not in this list, do NOT guess — ask the user or resolve live.

## 7) Built-in Mods (already IN GENTAHAX — no script needed)
`toggleCheat(code, true/false)` toggles, `getCheat(code)` reads. In MCP: `gh_cheat_set('Mod Fly', true)`

| Kod | Mod |
|---|---|
| 0 | Fast Fruit |
| 1 | Ghost Mode |
| 2 | Night Vision |
| 3 | Can See Ghost |
| 4 | Anti Bounce |
| 5 | Death Anywhere |
| 6 | No Clip |
| 7 | Bypass Death |
| 8 | Show Door Label |
| 9 | Show Sign Label |
| 10 | Anti Portal |
| 11 | Dev Mode |
| 12 | Fast Wheel |
| 13 | Real Fake Bubble |
| 14 | Show Debug |
| 15 | Anti State |
| 16 | No Particle |
| 17 | Path Finder |
| 18 | Skip Update |
| 19 | Anti Tile Activation |
| 20 | Anti Respawn |
| 21 | Anti Freeze State |
| 22 | Can't Take Item |
| 23 | Can't move |
| 24 | Fast Dice |
| 25 | Auto Acc |
| 26 | Mod Fly |
| 27 | Extractor Dynamo |
| 28 | Anti OnKilled |
| 29 | No Render Image |
| 30 | Free Camera |
| 31 | Show Ready Harvest |

Bellek yaması isimleri (patchMemoryByName/restoreMemoryByName): Mod Fly, Ghost Mode, Night Vision, Can See Ghost, Anti portal, Anti Checkpoint, Anti Respawn, Anti Take Item, Dev Mode, Fast Fruits, Path Finder, Skip Update, Skip Update v2, No Block, No Clip, Ghost Ship, Anti Gravity, Auto Fishing, Auto Stop

## 8) Verified Code Patterns

**Thread + human-like delay:**
```lua
runThread(function()
  while true do
    sleep(math.random(400, 1200))
    -- work
  end
end, 'my_tag')   -- stop: killThread('my_tag')
```

**World scan + block punch:**
```lua
local w = getWorld()
if not w then return 'ERR|NO_WORLD' end
for _, t in pairs(getTile()) do
  if t and t.fg == 4570 and t.pos then  -- 4570 = Pepper (real ID)
    sendPacketRaw(false, { type = 3, state = 16, value = 18,
                           x = t.pos.x, y = t.pos.y, punchx = t.pos.x, punchy = t.pos.y })
    sleep(math.random(450, 1200))
  end
end
```

**Collecting dropped items (official helper — safer than punching):**
```lua
for _, obj in pairs(getWorldObject()) do
  requestCollect(obj.pos.x, obj.pos.y, obj.id)
  sleep(math.random(200, 500))
end
```

**Chat listening (hook):**
```lua
AddHook('OnVarlist', 'chat', function(vars, netid)
  if vars[0] == 'OnTalkBubble' then
    logToConsole('[Chat] ' .. tostring(vars[2]))
  end
end)
```

**Reading gems (NetAvatar field — real struct):**
```lua
local me = getLocal()
if me then logToConsole('Gems: ' .. tostring(me.gems)) end
```

## 9) Ban Risk Rules (first 12)
- **[HIGH] Sleep'siz sonsuz dongu** — Dongu icine sleep(300) veya daha fazla ekleyin. Auto-farm donguleri icin 250-1000ms ideal araliktir.
- **[HIGH] Dongu icinde paket gonderme** — Her paket gonderiminden sonra sleep(250+) birakin; mumsal (batch) islemlerde araligi 500ms+ yapin.
- **[HIGH] Login paketi manipulasyonu** — Login paketlerini asla otomatiklestirmayin; yalnizca oyun kendi gonderirken gozlemleyin.
- **[HIGH] Dunya giris istegi (tekrar riski)** — Dunya degistirme dongulerinde en az 2-4 saniye bekleyin; ayni dunyaya tekrar giriste 10s+ birakin.
- **[HIGH] HWID (MAC/GID) degistirme** — Bu fonksiyonlari ban kacinma icin KULLANMAYIN. Sadece arastirma amaciyla okuma (getMac/getGid) yapin.
- **[HIGH] ENet baglanti hook'u** — OnENetInit'i sadece izleme (log) icin kullanin; ip/port parametrelerini degistirmeyin.
- **[HIGH] Dongu icinde blok islemi** — Blok islemleri arasina 300ms+ delay koyun; buyuk projelerde (anit, yazı) 500ms onerilir.
- **[MEDIUM] Esya atma paketi** — Toplu drop'ta her atma arasi 400ms+ birakin.
- **[MEDIUM] Mod Fly / hareket anomalisi** — Mod Fly'i kisitli surede kullanin, insan-olmayan mesafelerde (bomba gibi) atlamayin; kalabalik dunyalarda kapali tutun.
- **[MEDIUM] No Clip** — Kisa sureli kullanin; baska oyuncularin gordugu dunyalarda kullanmamak ciddi olcude riski azaltir.
- **[MEDIUM] Otomatik balikcilik** — Insan araliklari ekleyin (rastgele 1-4s), gunde saatlerce kesintisiz calistirmayin.
- **[MEDIUM] Otomatik toplama** — Toplama araliklarina rastgelelik ekleyin (math.random ile 200-600ms), insan benzeri hareket koruyun.

## 10) Test Yourself
1. 'getPlayerList' or 'getPlayerlist'? → **getPlayerlist**
2. Pepper's ID? (from the table, not a guess) → **4570**
3. What is mandatory in infinite loops? → **sleep (random 200-600ms)**
4. How to enable a mod without writing a script? → **toggleCheat(26, true) / gh_cheat_set('Mod Fly', true)**
5. Who decides whether a script works? → **ONLY the game executor + lua_logs.txt**

## 11) mr_berk
GENTAHAX MCP v1.5.0 — Trained on real data · Ban-risk warning system · 45 tools
