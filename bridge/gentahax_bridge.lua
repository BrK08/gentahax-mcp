--[[
  GENTAHAX MCP — Oyun İçi Köprü (Hibrit: Dosya IPC + HTTP Relay Fallback + Immortal Watchdog)
  mr_berk edition v2.1

  ÇALIŞMA MANTIĞI:
  • io kütüphanesi AÇIKSA (Android / standart build): bridge_in.txt / bridge_out.txt kullanır.
  • io kütüphanesi KAPALIYSA (Windows PATCH r1.0 vb.): makeRequest ile yerel HTTP aktarıcıyı
    (http://127.0.0.1:8809/in ve /out) kullanır. Hiçbir ek ayar gerekmez!
  • Immortal Watchdog: Herhangi bir script hata verse, RemoveHooks() veya killAllThread() çağırsa bile
    köprü asla kapanmaz; arka planda otomatik yeniden doğar.

  KURULUM:
  1) GENTAHAX menüden Lua Executor'da (</>) gentahax_bridge.lua seçip çalıştırın (▶).
  2) Veya tek satırlık yükleyiciyi yapıştırıp çalıştırın:
     load(makeRequest("http://127.0.0.1:8809/bridge.lua","GET",{},"",5000).content)()
]]

local IN_FILE   = "bridge_in.txt"
local OUT_FILE  = "bridge_out.txt"
local RELAY     = "http://127.0.0.1:8809"
local BRIDGE_ID = "mcp_bridge_mr_berk"
local WATCH_ID  = "_gh_bridge_watchdog"
local HAS_IO    = (type(io) == "table" and type(io.open) == "function")

-- Orijinal fonksiyonları yedekle (bir kez)
if not _G._GH_ORIG_SAVED then
    _G._GH_ORIG_SAVED = true
    _G._GH_RAW_ADDHOOK      = AddHook
    _G._GH_RAW_REMOVEHOOK   = RemoveHook
    _G._GH_RAW_REMOVEHOOKS  = RemoveHooks
    _G._GH_RAW_RUNTHREAD    = runThread
    _G._GH_RAW_KILLALL      = killAllThread
    _G._GH_USER_HOOKS       = {}
end

-- Güvenli AddHook sarmalayıcı: Hatalı scriptler C++ Lua state'ini veya köprüyü çökertemez
if type(_G._GH_RAW_ADDHOOK) == "function" then
    AddHook = function(ev, label, fn)
        local lbl = tostring(label or "unnamed")
        if lbl ~= WATCH_ID then
            _G._GH_USER_HOOKS[lbl] = true
        end
        if type(fn) ~= "function" then
            return _G._GH_RAW_ADDHOOK(ev, lbl, fn)
        end
        return _G._GH_RAW_ADDHOOK(ev, lbl, function(...)
            local ok, res = pcall(fn, ...)
            if not ok then
                pcall(logToConsole, "[MCP SAFE HOOK ERR] " .. lbl .. ": " .. tostring(res))
                if type(_G._GH_RAW_REMOVEHOOK) == "function" and lbl ~= WATCH_ID then
                    pcall(_G._GH_RAW_REMOVEHOOK, lbl)
                    _G._GH_USER_HOOKS[lbl] = nil
                end
                return false
            end
            return res
        end)
    end
end

-- Güvenli RemoveHooks: Köprü bekçisini (_gh_bridge_watchdog) korur, sadece kullanıcı hooklarını siler
if type(_G._GH_RAW_REMOVEHOOK) == "function" then
    RemoveHooks = function()
        for lbl, _ in pairs(_G._GH_USER_HOOKS or {}) do
            if lbl ~= WATCH_ID then
                pcall(_G._GH_RAW_REMOVEHOOK, lbl)
            end
        end
        _G._GH_USER_HOOKS = {}
    end
end

-- Güvenli killAllThread: Köprü thread'ini (mcp_bridge_mr_berk) korur
if type(getThreadsID) == "function" and type(killThread) == "function" then
    killAllThread = function()
        local ok, tids = pcall(getThreadsID)
        if ok and type(tids) == "table" then
            for _, tid in pairs(tids) do
                if tostring(tid) ~= BRIDGE_ID then
                    pcall(killThread, tid)
                end
            end
        end
    end
end

-- Güvenli çıktı gönderme (io açıksa dosyaya append, kapalıysa HTTP relay'e POST)
local function bridge_append(text)
    if HAS_IO then
        local f = io.open(OUT_FILE, "a")
        if f then
            f:write(text, "\n")
            f:close()
            return true
        end
    end
    if type(makeRequest) == "function" then
        local ok = pcall(makeRequest, RELAY .. "/out", "POST", {"Content-Type: text/plain; charset=utf-8"}, text, 4000)
        return ok
    end
    return false
end

-- Komut okuma (io açıksa dosyadan, kapalıysa HTTP relay'den GET)
local function bridge_poll_in()
    if HAS_IO then
        local f = io.open(IN_FILE, "r")
        if f then
            local content = f:read("*a")
            f:close()
            if type(os) == "table" and type(os.remove) == "function" then
                os.remove(IN_FILE)
            end
            if content and #content > 0 then
                return content:gsub("\r\n", "\n")
            end
        end
    end
    if type(makeRequest) == "function" then
        local ok, resp = pcall(makeRequest, RELAY .. "/in", "GET", {}, "", 4000)
        if ok and resp and resp.content and #resp.content > 0 then
            return resp.content:gsub("\r\n", "\n")
        end
    end
    return nil
end

-- Komut işleyici: ID|EXEC\n<lua kodu>
local function handle_command(content)
    local cmd_id, action, code = content:match("^(%x+)|(%a+)\n(.*)$")
    if not cmd_id then
        return false
    end

    if action == "EXEC" then
        local chunk, err = load(code, "mcp_chunk", "t", _G)
        if not chunk then
            bridge_append(cmd_id .. "|ERR|" .. tostring(err))
            return true
        end
        local ok, r1, r2, r3, r4 = pcall(chunk)
        if ok then
            local parts = {}
            for _, v in ipairs({r1, r2, r3, r4}) do
                if v ~= nil then parts[#parts + 1] = tostring(v) end
            end
            local out = table.concat(parts, " \t ")
            if out == "" then out = "OK" end
            bridge_append(cmd_id .. "|OK|" .. out)
        else
            bridge_append(cmd_id .. "|ERR|" .. tostring(r1))
        end
        return true
    elseif action == "STOP" then
        RemoveHooks()
        killAllThread()
        bridge_append(cmd_id .. "|OK|durduruldu")
        return true
    end
    return false
end

-- Köprü işçi thread'ini başlatan fonksiyon
local function spawn_bridge_worker()
    if _G._GH_WORKER_RUNNING then return end
    _G._GH_WORKER_RUNNING = true
    local runner = _G._GH_RAW_RUNTHREAD or runThread
    runner(function()
        bridge_append("0|OK|BRIDGE_READY mr_berk")
        while true do
            _G._GH_LAST_BEAT = getCurrentTimeInternal and getCurrentTimeInternal() or 0
            sleep(250)
            local ok, err = pcall(function()
                local content = bridge_poll_in()
                if content and #content > 0 then
                    handle_command(content)
                end
            end)
            if not ok then
                pcall(function()
                    bridge_append("0|ERR|bridge_loop:" .. tostring(err))
                end)
            end
        end
    end, BRIDGE_ID)
end

-- Immortal Watchdog: Köprü thread'i herhangi bir sebeple durursa 2 saniye içinde otomatik diriltir
local watch_elapsed = 0
if type(_G._GH_RAW_ADDHOOK) == "function" then
    pcall(_G._GH_RAW_REMOVEHOOK, WATCH_ID)
    _G._GH_RAW_ADDHOOK("OnRender", WATCH_ID, function(dt)
        watch_elapsed = watch_elapsed + (tonumber(dt) or 0.016)
        if watch_elapsed >= 2.0 then
            watch_elapsed = 0
            local alive = false
            if type(getThreadsID) == "function" then
                local ok, tids = pcall(getThreadsID)
                if ok and type(tids) == "table" then
                    for _, tid in pairs(tids) do
                        if tostring(tid) == BRIDGE_ID then
                            alive = true
                            break
                        end
                    end
                end
            else
                alive = _G._GH_WORKER_RUNNING
            end
            if not alive then
                _G._GH_WORKER_RUNNING = false
                pcall(spawn_bridge_worker)
            end
        end
    end)
end

_G._GH_WORKER_RUNNING = false
spawn_bridge_worker()
if type(doToast) == "function" then
    pcall(doToast, "GentaHAX MCP Bridge v2.1 Active (mr_berk)")
end

-- Kullanışlı hazır sorgular (MCP bunları EXEC ile çağırır)
function mcp_world_snapshot()
    local w = getWorld()
    if not w then return "Dunya yok (menude olabilirsin)" end
    local me = getLocal()
    local players = #getPlayerlist()
    local objs = #getWorldObject()
    return string.format(
        "WORLD:%s|SIZE:%dx%d|ME:%s|GEMS:%d|POS:%s|PLAYERS:%d|DROPS:%d",
        tostring(w.name), w.width, w.height,
        me and me.name or "?", me and me.gems or 0,
        me and (me.pos.x .. "," .. me.pos.y) or "?",
        players, objs
    )
end

function mcp_player_info()
    local list = getPlayerlist()
    local out = {}
    for i, p in pairs(list) do
        if type(p) == "table" or type(p) == "userdata" then
            out[#out + 1] = string.format("%s[netID=%s,country=%s,gems=%s,pos=%s,%s]",
                tostring(p.name), tostring(p.netId), tostring(p.country),
                tostring(p.gems), tostring(p.pos and p.pos.x or "?") .. "," .. tostring(p.pos and p.pos.y or "?"),
                tostring(p.ping) .. "ms")
        end
    end
    return table.concat(out, " ; ")
end

function mcp_inventory_dump()
    local out = {}
    for _, item in pairs(getInventory()) do
        if (type(item) == "table" or type(item) == "userdata") and item.id then
            local info = getItemByID(item.id)
            out[#out + 1] = string.format("%s(id=%d) x%d",
                info and info.name or "?", item.id, item.amount or 0)
        end
    end
    return table.concat(out, ", ")
end

function mcp_world_item_counts(ids_csv)
    local w = getWorld()
    if not w then return "ERR|NO_WORLD" end
    local want = {}
    for id in tostring(ids_csv):gmatch("%d+") do
        want[tonumber(id)] = { fg = 0, bg = 0 }
    end
    local total = 0
    for _, t in pairs(getTile()) do
        if (type(t) == "table" or type(t) == "userdata") and t.fg ~= nil then
            total = total + 1
            if want[t.fg] then want[t.fg].fg = want[t.fg].fg + 1 end
            if want[t.bg] then want[t.bg].bg = want[t.bg].bg + 1 end
        end
    end
    local out = {}
    for id, c in pairs(want) do
        out[#out + 1] = string.format("%d=%d/%d", id, c.fg, c.bg)
    end
    table.sort(out)
    return string.format("WORLD:%s|SIZE:%dx%d|TILES:%d|COUNTS:%s",
        tostring(w.name), w.width, w.height, total, table.concat(out, ";"))
end

function mcp_world_census()
    local w = getWorld()
    if not w then return "ERR|NO_WORLD" end
    local fgc, bgc, total = {}, {}, 0
    for _, t in pairs(getTile()) do
        if (type(t) == "table" or type(t) == "userdata") and t.fg ~= nil then
            total = total + 1
            if t.fg and t.fg > 0 then fgc[t.fg] = (fgc[t.fg] or 0) + 1 end
            if t.bg and t.bg > 0 then bgc[t.bg] = (bgc[t.bg] or 0) + 1 end
        end
    end
    local function top(c)
        local a = {}
        for id, n in pairs(c) do a[#a + 1] = { id, n } end
        table.sort(a, function(x, y) return x[2] > y[2] end)
        local o = {}
        for i = 1, math.min(#a, 20) do
            local it = getItemByID(a[i][1])
            o[#o + 1] = tostring(a[i][1]) .. "=" .. tostring(it and it.name or "?") .. " x" .. tostring(a[i][2])
        end
        return table.concat(o, ";")
    end
    local function n(c) local m = 0 for _ in pairs(c) do m = m + 1 end return m end
    return string.format("WORLD:%s|SIZE:%dx%d|TILES:%d|DISTINCT_FG:%d|DISTINCT_BG:%d|TOP_FG:%s|TOP_BG:%s",
        tostring(w.name), w.width, w.height, total, n(fgc), n(bgc), top(fgc), top(bgc))
end

logToConsole("[MCP BRIDGE] kurulum tamam - mr_berk v2.1 (Immortal Hibrit Kopru hazir)")
