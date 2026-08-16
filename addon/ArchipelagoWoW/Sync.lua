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

-- Called by Core's PLAYER_LEVEL_UP handler. A single quest turn-in can grant more than
-- one level at once (e.g. 36 -> 38 in one event) -- PLAYER_LEVEL_UP only ever fires with
-- the level actually landed on, so without this, the skipped level(s) in between would
-- only ever get sent via the manual "Send All Previous Levels" button, same as Level 01.
-- Safe to back-queue automatically here (unlike QueueAllPreviousLevels): this is always
-- the actual character live in this session actually crossing these levels right now, not
-- a stale/wrong-slot's history, so there's no flood-send risk -- db.session.lastKnownLevel
-- (seeded at login by Sync.OnLogin) bounds the backfill to only the levels genuinely
-- skipped since the last level this addon actually saw.
function Sync.OnLevelUp(newLevel)
    newLevel = tonumber(newLevel)
    if not newLevel then return end

    local db = ArchipelagoWoWDB
    if not db then return end

    local from = (db.session.lastKnownLevel or (newLevel - 1)) + 1
    for level = from, newLevel do
        Sync.QueueLevel(level)
    end
    db.session.lastKnownLevel = newLevel
end

-- Called once at every login/reload (Core's PLAYER_LOGIN handler), before
-- QueueStartingLevel. Seeds session.lastKnownLevel from the character's current level so
-- OnLevelUp's skip-detection has a baseline to compare the next level-up against.
-- Deliberately does NOT back-queue anything for a gap found here (e.g. this addon was only
-- just installed on an already-level-40 character) -- that's pre-existing history, exactly
-- what "Send All Previous Levels" exists to handle manually; only forward progress *after*
-- this baseline is ever auto-queued.
function Sync.OnLogin()
    local db = ArchipelagoWoWDB
    if not db then return end

    local currentLevel = UnitLevel("player") or 1
    if not db.session.lastKnownLevel or db.session.lastKnownLevel < currentLevel then
        db.session.lastKnownLevel = currentLevel
    end
end

-- Called once at every login/reload (Core's PLAYER_LOGIN handler). Level 1 has
-- no PLAYER_LEVEL_UP event to react to -- every character simply starts there,
-- with no "ding" -- so without this, "Level 01" could only ever be sent via
-- the manual "Send All Previous Levels" button, unlike every other level.
-- Safe to queue unconditionally on every login (unlike QueueAllPreviousLevels,
-- which is deliberately manual-only to avoid flood-sending the wrong
-- character's whole history): every character on every slot is always at
-- least level 1, so this can never queue a check that doesn't actually apply.
-- QueueLevel's own acked/pending guard keeps this idempotent after the first
-- login.
function Sync.QueueStartingLevel()
    Sync.QueueLevel(1)
end
