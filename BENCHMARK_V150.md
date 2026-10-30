# GENTAHAX MCP v1.5.0 — GERÇEK BENCHMARK RAPORU (uydurma YOK)

- **Tarih:** 2026-10-30 19:51:31 · **Süre:** 44.7 sn
- **Ortam:** Python 3.12.15 · fastmcp 2.14.3 · lupa: kurulu (derleme kanıtları gerçek Lua motoruyla)
- **Köprü:** GENTAHAX_SCRIPT_DIR ayarlanMAMIŞ (bu makinede telefon/oyun yok) → canlı executor testi burada FİZİKSEL olarak imkânsız
- **Sonuç:** **43/43 kanıt geçti**

## Bu benchmark GERÇEK bir hata BULDU ve düzeltildi

Benchmark geliştirilirken (kanıt uydurma aşamasında değil, gerçek koşturmada) v1.5.0'daki
bir çöküş yakalandı: **lupa'ya dokunan her araç (gh_script_gen, gh_auto_test) MCP araç
çağrısı İÇİNDE LuaRuntime kuruyordu; fastmcp araç gövdelerini pydantic-core çalıştırma
çerçevesi altında koşturduğu için Lua C-API'si korunmasız hata verip SUNUCU SÜRECİNİ
ÖLDÜRÜYORDU** — stdio yolunda (Claude Desktop'ın yolu) istemci 'Connection closed'
hatası alıyordu. Mevcut 220 test bunu yakalayamamıştı çünkü `_syntax_precheck`'i
doğrudan çağırıyordu, MCP çağrı zincirinden değil.

**Düzeltme:** Lua derleme motoru artık sunucu AÇILIŞINDA (ana thread) bir kez kurulur
(`server.py` → `_LUA_RT`), araç çağrıları kilit altında yalnız KULLANIR. Regresyon
kanıtı: **A17** (aynı oturumda tekrar tekrar çağrı) + **E04/E05** (HTTP yolu) +
`tests/test_autotest_loop.py` KATMAN 5 (soğuk başlangıç MCP çağrı zinciri — kalıcı
regresyon testi).

> Aşağıdaki her kod bloğu gerçek çalıştırmanın YAKALANMIŞ çıktısıdır;
> rapor `tests/benchmark_v150.py` tarafından üretilmiştir, hiçbir satır elle yazılmamıştır.

## Kanıt özeti

| No | Kanıt | Sonuç |
|---|---|---|
| A01 | Gerçek sunucu süreci spawn edildi + initialize el sıkışması | ✅ GEÇTİ |
| A02 | Tam 45 araç (v1.5.0'in 5 yeni aracı dahil) | ✅ GEÇTİ |
| A03 | gh_about → sürüm + filigran | ✅ GEÇTİ |
| A04 | gh_item_db_search('Dirt') → GERÇEK veritabanından Dirt = 2 | ✅ GEÇTİ |
| A05 | gh_item_db_search('Pepper') → gerçek ID 4570 (tahmin değil, DB'den) | ✅ GEÇTİ |
| A06 | gh_code_analyze(yüksek riskli kod) → YÜKSEK + ⚠️ ban uyarısı | ✅ GEÇTİ |
| A07 | gh_cheat_set('mod fly', true) köprüsüz → SAHTE 'açıldı' DEĞİL, dürüst 'Köprü kapalı' | ✅ GEÇTİ |
| A08 | gh_cheat_status() köprüsüz → sahte durum tablosu YOK, dürüst bildirim | ✅ GEÇTİ |
| A09 | gh_auto_test(güvenli script) köprüsüz → CIHAZ_YOK dürüst kararı (asla 'ÇALIŞIYOR' UYDURMAZ) + derleme ön-kontrolü geçti | ✅ GEÇTİ |
| A10 | gh_auto_test(YÜKSEK riskli, force=false) → REDDEDİLDİ + ⚠️ ban uyarısı (executor'a HİÇ gönderilmez) | ✅ GEÇTİ |
| A11 | gh_auto_test(gerçek söz dizimi hatası) → SYNTAX yakalandı, executor'a GİTMEDİ | ✅ GEÇTİ |
| A12 | gh_compat_check() köprüsüz → OFFLINE mod: 3 güncelleme senaryosu + mimari | ✅ GEÇTİ |
| A13 | gh_script_gen('Pepper'ları kır') → gerçek ID'li, DERLENMİŞ, AUTOTEST işaretli script | ✅ GEÇTİ |
| A14 | gh_cheat_set('ghost') belirsiz → TAHMİN ETMEZ, adayları listeler | ✅ GEÇTİ |
| A15 | gh_cheat_set(olmayan mod) → 'listede yok' dürüst cevabı | ✅ GEÇTİ |
| A16 | gh_device_status() → köprü yapılandırılmamış gerçeğini açıkça söyler | ✅ GEÇTİ |
| A17 | GERÇEK ÇÖKÜŞ DÜZELTMESİ (regresyon): lupa'ya dokunan araçlar artık araç çağrısı İÇİNDE motor KURMAZ (önce: Lua PANIC → süreç ölüyordu, stdio'da 'Connection closed'); aynı oturumda tekrar tekrar çağrılıyor | ✅ GEÇTİ |
| B00 | Lua derleme motoru açılışta kurulmuş (çöküş düzeltmesi aktif) | ✅ GEÇTİ |
| B01 | Tüm 9 şablon gerçek Lua motorunda derleniyor (çalıştırılmadan) | ✅ GEÇTİ |
| B02 | gh_farm_script_gen çıktısı (Pepper ID 4570 yerleştirilmiş) derleniyor | ✅ GEÇTİ |
| B03 | gh_script_gen çıktısı derleniyor | ✅ GEÇTİ |
| B04 | OYUN-İÇİ fonksiyonlar (getLocal/toggleCheat/sleep/sendPacketRaw) derlemeyi BOZMAZ — kullanıcının haklı tespiti, kod yoluyla kanıt | ✅ GEÇTİ |
| B05 | GERÇEK gramer hatası (eksik 'end') yakalanır → executor'a gönderilmeden reddedilir | ✅ GEÇTİ |
| C01 | AI_EGITIM.md + AI_TRAINING.md, veri dosyalarından üretimle BİREBİR aynı (elle yazılmış/uydurma içerik karışmış olamaz) | ✅ GEÇTİ |
| C02 | Paketin KOD ALANINDAKİ (lua blokları + backtick imzaları) 75 farklı çağrılabilir ismin TAMAMI gerçek kaynaklı (71 gerçek API + 3 Lua stdlib/kelime + 1 gh_ aracı) — uydurma: SIFIR | ✅ GEÇTİ |
| C03 | Paketteki 46 item-ID satırı + kod örneklerindeki sabitler (Pepper=4570, Dirt=2, Mod Fly=26) gerçek DB/enum ile DOĞRULANDI | ✅ GEÇTİ |
| C04 | Paketteki 32 hazır mod tablosu CheatCode enum'ının BİREBİR kopyası | ✅ GEÇTİ |
| C05 | items.json gerçek boyut | ✅ GEÇTİ |
| D01 | Gerçek executor hata dizesi → MISSING_FN + hedef fonksiyon doğru ayrıştırılır | ✅ GEÇTİ |
| D02 | Yanlış 'getPlayerList' → gerçek API'den TE aday: doğru isim 'getPlayerlist' | ✅ GEÇTİ |
| D03 | Otomatik yama: yanlış çağrı kodda gerçek isimle değiştirilir | ✅ GEÇTİ |
| D04 | Sınıflandırma tablosu: nil-index / nil-aritmetik / syntax / nil-field doğru sınıf alır | ✅ GEÇTİ |
| D05 | TAM DÖNGÜ (etiketli taklit executor yanıtı): HATA kararı → teşhis → yama → yamalı kod derleniyor → döngü kapanmaya hazır | ✅ GEÇTİ |
| D06 | Executor'un yazacağı AUTOTEST|OK işaretli log → CALISIYOR kararı | ✅ GEÇTİ |
| D07 | START var OK yok → DEVAM_EDIYOR (aceleyle yanlış karar verilmez) | ✅ GEÇTİ |
| D08 | 'ERR|NO_WORLD' → HATA/NOT_IN_WORLD ('dünyada değilsin' teşhisi) | ✅ GEÇTİ |
| D09 | Köprü zaman aşımı → CIHAZ_YOK (sahte başarı YOK) | ✅ GEÇTİ |
| E01 | server.py --http gerçek süreç olarak ayaklandı ve portu dinliyor | ✅ GEÇTİ |
| E02 | Gerçek Streamable HTTP istemcisi bağlandı → 45 araç listelendi | ✅ GEÇTİ |
| E03 | HTTP üzerinden gerçek DB çağrısı (Dirt = 2) çalışır | ✅ GEÇTİ |
| E04 | HTTP üzerinden gh_auto_test → köprüsüz dürüst CIHAZ_YOK (+ lupa düzeltmesi HTTP yolunda da aktif) | ✅ GEÇTİ |
| E05 | HTTP üzerinden gh_script_gen → derleme geçti, süreç yaşıyor | ✅ GEÇTİ |
| F01 | 9 test dosyasının TAMAMI exit=0 ile geçti (sayılabilen 254 assertion + protokol/e2e çağrıları) | ✅ GEÇTİ |

## Bölüm A — Canlı MCP protokolü (gerçek süreç, stdio = Claude Desktop yolu)

### A04/A07/A09/A13 — yakalanan gerçek ham yanıtlar
```
### gh_item_db_search('Dirt')
```
GERÇEK veritabanı sonucu (6832 esya — items.dat tabanlı):
    2 = Dirt
    3 = Dirt Seed [SEED]
 2876 = BLYoshi's Free Dirt

(3/6 sonuç gösteriliyor — detay için gh_item_db_info)
```

### gh_cheat_set('mod fly', true) — köprüsüz
```
⚠️ Köprü kapalı.
1) Windows: GENTAHAX kurulu dizindeki Script klasörünün tam yolunu GENTAHAX_SCRIPT_DIR ortam değişkenine yaz. 2) Android: GENTAHAX_TARGET=adb ve adb'de cihaz bağlı olsun. Sonra gh_bridge_deploy ile köprüyü kur.

Bilgi araçları (Bölüm 1-2) her zaman çalışır; canlı veri için köprü kurun: gh_bridge_deploy
```

### gh_auto_test(güvenli script) — köprüsüz
```
{"sonuc": "CIHAZ_YOK", "calistirildi": false, "sozdizimi_on_kontrol": {"sonuc": "geçti", "detay": "derleme OK — kod ÇALIŞTIRILMADI, oyun fonksiyonları false hata vermez"}, "ipucu": "Canlı test için köprü gerekli — ⚠️ Köprü kapalı.\n1) Windows: GENTAHAX kurulu dizindeki Script klasörünün tam yolunu GENTAHAX_SCRIPT_DIR ortam değişkenine yaz. 2) Android: GENTAHAX_TARGET=adb ve adb'de cihaz bağlı olsun. Sonra gh_bri", "watermark": "mr_berk"}
```

### gh_script_gen('Pepper'ları kır') — script
```
-- mr_berk GENTAHAX ad-hoc script — 'Dunyadaki tum Pepper bloklarini kir ve cikan gem'i soyle'
-- Uretildi: gh_farm_script_gen | Hedef ID: 4570 (Pepper) — GERCEK items.dat veritabanindan
-- RISK: YUKSEK — dongude punch paketi (farm bot paterni). Insan benzeri rastgele delay'ler
--        eklendi ama sunucu farm botlarini analiz edebilir. Degerli hesapta kullanma!
pcall(function() math.randomseed(os.time()) end)

local TARGET = 4570
local NAME = 'Pepper'

-- FAZ A — hizli sayim (senkron, koprunun zaman asimina sigar)
local w = getWorld()
if not w then return 'ERR|NO_WORLD' end
local me = getLocal()
if not me then return 'ERR|NO_LOCAL' end
```
```

## Bölüm B — Gerçek derleme (lupa load, çalıştırma YOK)

### B01/B04/B05 — gerçek derleme çıktıları
```
şablonlar: auto_collect: geçti, varlist_logger: geçti, chat_command: geçti, esp_overlay: geçti, tree_harvest: geçti, imgui_panel: geçti, webhook_notify: geçti, dirt_farm: geçti, human_responder: geçti

oyun fonksiyonlu kod → {"sonuc": "geçti", "detay": "derleme OK — kod ÇALIŞTIRILMADI, oyun fonksiyonları false hata vermez"}

eksik 'end' kodu   → {"sonuc": "hata", "detay": "[string \"local x = getLocal()...\"]:2: 'end' expected near <eof>"}
```

## Bölüm C — Uydurma denetimi (paket ↔ gerçek veri)

### C02 — kod alanındaki çağrılabilir isimler (denetim özeti, gerçek çıktı)
```
denetim kapsamı: lua kod blokları + backtick imza alanları (yorumlar ayıklanmış)
toplam farklı isim: 75
gerçek API veri dosyalarında: 71
Lua stdlib/anahtar kelime: 3
gh_ MCP araçları: 1
UYDURMA: 0
```

## Bölüm D — Hata sınıflandırma + otomatik yama

### D05 — tam döngünün gerçek adımları (parser/yama gerçek çıktı, executor yanıtı taklit)
```
GİRDİ  (executor biçimi): Lua hatası: attempt to call a nil value (global 'getPlayerList')
KARAR  : HATA · sınıf=MISSING_FN hedef=getPlayerList
TEŞHİS : 'getPlayerList' bu oyunda yok (gerçek GENTAHAX API'sinde bulunamadı)
ÇÖZÜM  : Fonksiyon adını düzelt: 'getPlayerList' → doğrusu büyük ihtimalle 'getPlayerlist'
YAMA   : getPlayerList( → getPlayerlist( (1 değişiklik)
YAMALI KOD DERLEME: geçti
```

## Bölüm E — Canlı HTTP modu (gerçek süreç)

## Bölüm F — Tam regresyon

### F01 — regresyon dosya dosya (gerçek çıktı)
```
test_adhoc_request.py: GEÇTİ (34 assertion)
test_ai_training.py: GEÇTİ (38 assertion)
test_autotest_loop.py: GEÇTİ (50 assertion)
test_chat_agent.py: GEÇTİ (15 assertion)
test_cheat_compat.py: GEÇTİ (36 assertion)
test_gentahax_mcp.py: GEÇTİ (41 assertion)
test_http_mode.py: GEÇTİ (10 assertion)
test_mcp_protocol.py: GEÇTİ
test_world_count_e2e.py: GEÇTİ (30 assertion)
```

## Dürüstlük çerçevesi — ne kanıtlandı, ne kanıtlanamaz

**Bu makinede KANITLANDI (yukarıdaki gerçek çıktılarla):**

- MCP protokolü (stdio + HTTP), 45 araç, gerçek item veritabanı (6832), güvenlik/ban
  katmanı, lupa derleme (oyun fonksiyonları false hata VERMEZ — B04), script üretimi,
  hata sınıflandırma + otomatik yama mantığı, eğitim paketinin %100 gerçek veriden
  üretilmesi (C01-C04), köprüsüz durumda araçların SAHTE başarı üretmeden dürüst
  'Köprü kapalı / CIHAZ_YOK' bildirmesi (A07-A09, E04), ve v1.5.0 çöküşünün
  düzeltildiği (A17, E04-E05).

**Bu makinede KANITLANAMAZ (dürüstçe):**

- Bir scriptin GENTAHAX'ın GERÇEK executor'ında ÇALIŞIYOR olması — bu karar tasarım
  gereği YALNIZCA oyunun kendi executor'ından ve lua_logs.txt'den gelir; o da
  telefon + oyun + gentahax_bridge.lua gerektirir. Bölüm D'deki executor yanıtları
  BELGELENMİŞ formatın yeniden oynatımıdır ve açıkça etiketlenmiştir.
- toggleCheat/getCheat'in gerçek oyun üzerindeki etkisi (köprü kurulunca gh_cheat_set
  getCheat doğrulamasıyla birlikte çalışır — kod yolu B04/A07'de kanıtlı).

**Gerçek cihaz testi için:** KURULUM.md Adım 4-5 (köprüyü kur) → herhangi bir AI'dan
`gh_auto_test` ile script çalıştırmasını iste → '✅ ÇALIŞIYOR' ya da gerçek hata + yama gelir.

---
*GENTAHAX MCP v1.5.0 · benchmark: tests/benchmark_v150.py · mr_berk*