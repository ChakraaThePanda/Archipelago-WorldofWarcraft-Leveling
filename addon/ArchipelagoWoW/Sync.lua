-- ArchipelagoWoW: Sync.lua
-- Everything related to queueing level checks and flushing SavedVariables to
-- disk via ReloadUI(). There is deliberately no live/instant signaling here
-- (no chat-log tailing, no combat-log tricks) -- the only way data ever
-- reaches the external bridge program is a SavedVariables write, and the only
-- way that happens is logout or ReloadUI().
--
-- Syncing is manual-only ("Sync Now"), on purpose: an automatic ReloadUI()
-- fired mid-combat would drop your target/casting at a genuinely dangerous
-- moment (could get you killed), so this never triggers a reload on its own
-- -- only ever in direct response to the player clicking Sync Now.
--
-- IMPORTANT: ReloadUI() is a protected call -- it only works when invoked
-- synchronously, directly inside a real click handler's call stack. Routing
-- it through ANY intervening frame (a C_Timer/OnUpdate-driven timer callback,
-- even with a 0-second delay) breaks that secure chain and gets it blocked
-- with "Interface action failed because of an addon" (confirmed live). So
-- Sync.SyncNow below must call ReloadUI() directly -- no timer, no
-- indirection -- and there is deliberately no automatic combat-lockdown
-- retry: if you click it mid-combat, it just tells you to try again once
-- combat ends, rather than silently queuing a retry that would hit the same
-- taint problem anyway.

local ADDON_NAME, APW = ...

APW.Sync = APW.Sync or {}
local Sync = APW.Sync
local Core = APW.Core

-- Adds `level` to pendingChecks unless it's already pending or the bridge has
-- already confirmed (acked) it was sent to the AP server.
function Sync.QueueLevel(level)
    level = tonumber(level)
    if not level or level < 1 then
        return false
    end

    local db = ArchipelagoWoWDB
    local bridge = ArchipelagoWoW_BridgeDB
    if not db or not bridge then
        return false
    end

    if bridge.ackedLevels[level] then
        return false
    end
    if Core.IsPending(level) then
        return false
    end

    table.insert(db.pendingChecks, level)
    table.sort(db.pendingChecks)
    Core.AddLog(string.format("Queued level %d to send on next sync", level))
    return true
end

-- "Send All Previous Levels": queues every integer level from 1 up to the
-- player's current level that isn't already acked or already pending. This is
-- an explicit, user-initiated action so connecting to the wrong
-- character/slot doesn't silently flood-send a character's whole history.
function Sync.QueueAllPreviousLevels()
    local db = ArchipelagoWoWDB
    local bridge = ArchipelagoWoW_BridgeDB
    if not db or not bridge then
        return 0
    end

    local currentLevel = UnitLevel("player") or 1
    local added = 0
    for level = 1, currentLevel do
        if not bridge.ackedLevels[level] and not Core.IsPending(level) then
            table.insert(db.pendingChecks, level)
            added = added + 1
        end
    end

    if added > 0 then
        table.sort(db.pendingChecks)
        Core.AddLog(string.format("Queued %d previous level(s) (1-%d) to send on next sync", added, currentLevel))
    else
        Core.AddLog("Send All Previous Levels: nothing to queue (all already sent or acked)")
    end
    return added
end

-- Manual "Sync Now" button/action. Must call ReloadUI() directly and
-- synchronously (see file header) -- if you're in combat, this just refuses
-- and asks you to click it again once combat ends, rather than queuing an
-- automatic retry (which would hit the same taint restriction anyway).
function Sync.SyncNow()
    if InCombatLockdown() then
        Core.AddLog("Can't sync while in combat -- click Sync Now again once combat ends")
        if DEFAULT_CHAT_FRAME then
            DEFAULT_CHAT_FRAME:AddMessage("|cff33ff99ArchipelagoWoW|r: can't sync while in combat -- try again once combat ends.")
        end
        return
    end
    ReloadUI()
end

-- Called by Core's PLAYER_LEVEL_UP handler. Only queues the level for the next
-- (manual) sync -- never schedules a reload itself. See file header.
function Sync.OnLevelUp(level)
    Sync.QueueLevel(level)
end
