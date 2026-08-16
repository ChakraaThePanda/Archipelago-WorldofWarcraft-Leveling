-- ArchipelagoWoW: Core.lua
-- SavedVariables defaults/shape enforcement, activity log helper, and the
-- reconciliation pass that merges the bridge's authoritative state
-- (ArchipelagoWoW_BridgeDB) into our own display state on every reload.

local ADDON_NAME, APW = ...

APW.Core = APW.Core or {}
local Core = APW.Core

local LOG_CAP = 200

local DB_DEFAULTS = {
    ui = {
        mainPanel = { point = "CENTER", relPoint = "CENTER", x = 0, y = 0, shown = false },
        zonesPanel = { point = "CENTER", relPoint = "CENTER", x = 0, y = 0, shown = false },
    },
    -- lastKnownLevel: the character level this addon last actually saw, used by
    -- Sync.OnLevelUp to detect a multi-level jump (e.g. one quest turn-in granting 2
    -- levels at once) and back-queue the level(s) in between, not just the one landed on.
    session = { seedName = nil, lastKnownLevel = nil },
    pendingChecks = {},
    log = {},
}

-- The bridge's file is written externally; we never assign into it, but we
-- still need every read anywhere in this addon to be able to assume the full
-- shape exists, since the bridge may not have run yet (first login ever, or
-- the player connected before configuring/starting the companion program).
local BRIDGE_DEFAULTS = {
    connected = false,
    lastSyncEpoch = nil,
    slotData = { expansion = nil, goal = nil, faction = nil, goldHuntAmount = nil },
    ackedLevels = {},
    unlockedZones = {},
    -- name -> count (e.g. "Progressive Levels" = 3, or "Maximum Level 40" = 1). Class and
    -- faction items are deliberately not tracked at all -- both are a single fixed choice
    -- known from the moment you connect, not something that progressively unlocks.
    levelItems = {},
    -- Highest character level currently reachable from level-cap items alone -- always
    -- at least 10 ("Levels 01-10" needs nothing, see Rules.py), so 10 is a safe default
    -- before the bridge has ever synced.
    currentLevelCap = 10,
    -- Gold Hunt goal progress, out of slotData.goldHuntAmount.
    goldCount = 0,
    incoming = {},
}

-- Recursively fills in any key missing from `tbl` using `defaults`, without
-- overwriting anything already present. Safe to call every login even after
-- the shape has gained new fields in a later addon version.
local function applyDefaults(tbl, defaults)
    tbl = tbl or {}
    for k, v in pairs(defaults) do
        if type(v) == "table" then
            if type(tbl[k]) ~= "table" then
                tbl[k] = {}
            end
            applyDefaults(tbl[k], v)
        elseif tbl[k] == nil then
            tbl[k] = v
        end
    end
    return tbl
end

function Core.EnsureDB()
    ArchipelagoWoWDB = applyDefaults(ArchipelagoWoWDB, DB_DEFAULTS)
    -- Defensive only: never write meaningful values here, just guarantee shape.
    ArchipelagoWoW_BridgeDB = applyDefaults(ArchipelagoWoW_BridgeDB, BRIDGE_DEFAULTS)
end

-- Appends one activity-log entry (chronological, oldest first) and trims to
-- LOG_CAP by dropping the oldest entries.
function Core.AddLog(text)
    local db = ArchipelagoWoWDB
    if not db then return end
    table.insert(db.log, { ts = time(), text = text })
    while #db.log > LOG_CAP do
        table.remove(db.log, 1)
    end
end

-- Returns true if `level` is already present in the pendingChecks array.
local function isPending(db, level)
    for _, existing in ipairs(db.pendingChecks) do
        if existing == level then
            return true
        end
    end
    return false
end

Core.IsPending = function(level)
    return isPending(ArchipelagoWoWDB, level)
end

-- Runs on every login/reload, after both SavedVariables tables are guaranteed
-- loaded. Trusts ArchipelagoWoW_BridgeDB.ackedLevels as authoritative over our
-- own pendingChecks, and folds any new bridge `incoming` entries into our log.
function Core.Reconcile()
    local db = ArchipelagoWoWDB
    local bridge = ArchipelagoWoW_BridgeDB
    if not db or not bridge then return end

    -- If the bridge is now reporting a different room than last time we synced, our own
    -- pendingChecks/log are about a DIFFERENT seed and would otherwise sit there forever
    -- confusingly mixed in with the new room's activity (confirmed live: old entries from
    -- a previous room stayed visible indefinitely). Detected and reset before anything
    -- else below reads/mutates either.
    -- The bridge only ever writes seedName inside slotData (see
    -- WoWLevelingClient.py's _translate_slot_data) -- there is no top-level
    -- bridge.seedName key to fall back from.
    local bridgeSeedName = bridge.slotData and bridge.slotData.seedName
    if bridgeSeedName ~= nil and db.session.seedName ~= nil and bridgeSeedName ~= db.session.seedName then
        db.pendingChecks = {}
        db.log = {}
        Core.AddLog(string.format("Connected to a new room (seed %s) -- activity log reset", tostring(bridgeSeedName)))
    end

    -- Drop anything the bridge has confirmed it already sent to the AP server.
    local stillPending = {}
    for _, level in ipairs(db.pendingChecks) do
        if not bridge.ackedLevels[level] then
            table.insert(stillPending, level)
        else
            Core.AddLog(string.format("Level %d confirmed synced by bridge", level))
        end
    end
    table.sort(stillPending)
    db.pendingChecks = stillPending

    -- Mirror bridge-reported session info for display (and so the next Reconcile can
    -- detect a room change, above) -- bridgeSeedName already resolved whichever of
    -- bridge.seedName / bridge.slotData.seedName the bridge actually populated.
    if bridgeSeedName ~= nil then
        db.session.seedName = bridgeSeedName
    end

    -- Fold bridge "incoming" entries into our own log, skipping ones we've
    -- already recorded (matched by timestamp + item + sender).
    local known = {}
    for _, entry in ipairs(db.log) do
        if entry.incomingKey then
            known[entry.incomingKey] = true
        end
    end

    local addedAny = false
    for _, item in ipairs(bridge.incoming or {}) do
        local key = string.format("%s|%s|%s", tostring(item.ts), tostring(item.itemName), tostring(item.fromPlayer))
        if not known[key] then
            local text = string.format("Received %s from %s", tostring(item.itemName or "?"), tostring(item.fromPlayer or "Archipelago"))
            table.insert(db.log, { ts = item.ts or time(), text = text, incomingKey = key })
            known[key] = true
            addedAny = true
        end
    end

    if addedAny then
        table.sort(db.log, function(a, b) return (a.ts or 0) < (b.ts or 0) end)
    end
    while #db.log > LOG_CAP do
        table.remove(db.log, 1)
    end
end

-- Human-readable "synced Xs/Xm/Xh ago" string, computed against time() at call
-- time. Returns "never" when the bridge hasn't ever written the file.
function Core.FormatRelativeTime(epoch)
    if not epoch then
        return "never"
    end
    local diff = time() - epoch
    if diff < 0 then
        diff = 0
    end
    if diff < 60 then
        return string.format("%ds ago", diff)
    elseif diff < 3600 then
        return string.format("%dm ago", math.floor(diff / 60))
    elseif diff < 86400 then
        return string.format("%dh ago", math.floor(diff / 3600))
    else
        return string.format("%dd ago", math.floor(diff / 86400))
    end
end

-- ---------------------------------------------------------------------------
-- Event wiring
-- ---------------------------------------------------------------------------

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("ADDON_LOADED")
eventFrame:RegisterEvent("PLAYER_LOGIN")
eventFrame:RegisterEvent("PLAYER_LEVEL_UP")

eventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "ADDON_LOADED" then
        local loadedAddonName = ...
        if loadedAddonName == ADDON_NAME then
            -- Only our own two tables are guaranteed present at this point;
            -- the bridge addon may not have fired ADDON_LOADED yet. Shape-only.
            Core.EnsureDB()
        end
    elseif event == "PLAYER_LOGIN" then
        -- By PLAYER_LOGIN every enabled addon (including the bridge sidecar)
        -- has already loaded its SavedVariables, so it's safe to reconcile now.
        Core.EnsureDB()
        Core.Reconcile()
        if APW.Sync and APW.Sync.OnLogin then
            APW.Sync.OnLogin()
        end
        if APW.Sync and APW.Sync.QueueStartingLevel then
            APW.Sync.QueueStartingLevel()
        end
        if APW.UI and APW.UI.OnLogin then
            APW.UI.OnLogin()
        end
    elseif event == "PLAYER_LEVEL_UP" then
        local newLevel = ...
        newLevel = tonumber(newLevel) or UnitLevel("player")
        if APW.Sync and APW.Sync.OnLevelUp then
            APW.Sync.OnLevelUp(newLevel)
        end
        if APW.UI and APW.UI.RefreshAll then
            APW.UI.RefreshAll()
        end
    end
end)
