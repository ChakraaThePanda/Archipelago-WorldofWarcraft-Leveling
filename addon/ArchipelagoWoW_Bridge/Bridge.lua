-- ArchipelagoWoW_Bridge
--
-- This addon folder exists SOLELY to own a second, independent SavedVariables
-- file (ArchipelagoWoW_BridgeDB) that the external Archipelago bridge program
-- rewrites directly on disk between game sessions (it is not built by this
-- addon -- see the main project's companion Python bridge).
--
-- The ArchipelagoWoW addon only ever READS this table -- it never assigns
-- into it -- so at logout the game simply re-serializes whatever the bridge
-- last wrote back to the same file, unchanged. Two separate addon folders
-- (and therefore two separate SavedVariables files) avoid any write race
-- between this game client process and the external bridge process.
--
-- Nothing needs to run here. The one thing worth doing is seeding an empty,
-- well-shaped table on the very first login ever (before the bridge program
-- has run for the first time), purely so the SavedVariables file gets created
-- with a sane shape for the bridge to find and safely merge into later.
if ArchipelagoWoW_BridgeDB == nil then
    ArchipelagoWoW_BridgeDB = {
        connected = false,
        lastSyncEpoch = nil,
        slotData = { expansion = nil, goal = nil, faction = nil, goldHuntAmount = nil },
        ackedLevels = {},
        unlockedZones = {},
        levelItems = {},
        currentLevelCap = 10,
        goldCount = 0,
        incoming = {},
    }
end
