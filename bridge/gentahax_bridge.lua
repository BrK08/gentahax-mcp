--[[
  GENTAHAX MCP BRIDGE — mr_berk edition
  =====================================
  Bu script GENTAHAX Lua motorunun İÇİNDE sürekli çalışan bir bekçi thread'idir.
  Python (MCP) tarafı bridge_in.txt yazar, bu köprü okuyup çalıştırır ve
  sonucu bridge_out.txt'ye yazar. Böylece AI gerçek zamanlı oyun verisi
  okuyabilir ve kod çalıştırabilir.

  KURULUM:
    1) Bu dosyayı GENTAHAX Script klasörüne koyun
       (Windows: GENTAHAX kurulu dizin/Script/ — Android: Android/media/GENTAHAX/Script/)
    2) GENTAHAX menüde Lua Executor → gentahax_bridge.lua → Execute
    3) Hepsi bu! MCP tarafı gh_device_status ile doğrulayabilir.

  NOT: io kütüphanesi kapalı bir build'de çalışmaz; bu durumda
       bridge_out.txt oluşmaz ve MCP tarafı zaman aşımı verir.
]]

local IN_FILE  = "bridge_in.txt"
local OUT_FILE = "bridge_out.txt"
local BRIDGE_ID = "mcp_bridge_mr_berk"

-- Güvenli dosya yazma (append)
local function bridge_append(text)
    local f = io.open(OUT_FILE, "a")
    if not f then return false end
    f:write(text, "\n")
    f:close()
    return true
end

-- Komut işleyici: ID|EXEC\n<lua kodu>
local function handle_command(content)
    local cmd_id, action, code = content:match("^(%x+)|(%a+)\n(.*)$")
    if not cmd_id then
        -- eski uyumsuz format
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

-- Ana bekçi thread
runThread(function()
    -- başlangıç sinyali
    bridge_append("0|OK|BRIDGE_READY mr_berk")
    logToConsole("[MCP BRIDGE] mr_berk köprüsü hazır — Python tarafını bekliyor")

    while true do
        sleep(250)
        local ok, err = pcall(function()
            local f = io.open(IN_FILE, "r")
            if not f then return end
            local content = f:read("*a")
            f:close()
            os.remove(IN_FILE)
            if content and #content > 0 then
                handle_command(content)
            end
        end)
        if not ok then
            -- hata durumunda çökme değil, bildirim
            pcall(function()
                bridge_append("0|ERR|bridge_loop:" .. tostring(err))
            end)
        end
    end
end, BRIDGE_ID)

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
        out[#out + 1] = string.format("%s[netID=%s,country=%s,gems=%s,pos=%s,%s]",
            tostring(p.name), tostring(p.netId), tostring(p.country),
            tostring(p.gems), tostring(p.pos.x) .. "," .. tostring(p.pos.y),
            tostring(p.ping) .. "ms")
    end
    return table.concat(out, " ; ")
end

function mcp_inventory_dump()
    local out = {}
    for _, item in pairs(getInventory()) do
        local info = getItemByID(item.id)
        out[#out + 1] = string.format("%s(id=%d) x%d",
            info and info.name or "?", item.id, item.amount)
    end
    return table.concat(out, ", ")
end

logToConsole("[MCP BRIDGE] kurulum tamam — mr_berk")
