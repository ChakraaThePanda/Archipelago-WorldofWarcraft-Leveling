-- ArchipelagoWoW: UI.lua
-- Custom-frame UI (no reliance on any version's native Settings/Interface Options
-- API): a draggable "Archipelago" main panel, a draggable "Zones/Progress" panel,
-- and the /apwow and /archipelago slash commands. No settings frame -- there is
-- nothing left to configure in-game (see CreateMainPanel's own comment for why).
--
-- Honesty note baked into every status string below: everything shown here
-- reflects the state as of the last sync (last ReloadUI), never "live". There
-- is deliberately no "Connected"/"Not connected" indicator anywhere in this
-- file -- ArchipelagoWoW_BridgeDB.connected is only ever as fresh as your last
-- reload, and the bridge only corrects it to false on a *clean* shutdown, so a
-- crashed/force-closed bridge can leave it reading true indefinitely. A claim
-- that can silently go wrong that way and never self-corrects isn't worth
-- displaying at all; "synced Xs/Xm/Xh ago" (Core.FormatRelativeTime) plus the
-- "Sync Now (Reload UI)" button are the only trustworthy signals this addon
-- can actually offer, so that's all it shows.

local ADDON_NAME, APW = ...

APW.UI = APW.UI or {}
local UI = APW.UI
local Compat = APW.Compat
local Core = APW.Core
local Sync = APW.Sync
local Zones = APW.Zones

-- ---------------------------------------------------------------------------
-- Small shared helpers
-- ---------------------------------------------------------------------------

-- Display-only formatting for raw snake_case option values ("gold_hunt" -> "Gold Hunt",
-- "alliance" -> "Alliance"). Never applied to the values actually compared/stored --
-- only at the point of building a string to show the player.
local function DisplayCase(s)
    if not s then return s end
    s = tostring(s):gsub("_", " ")
    s = s:gsub("(%a)([%w']*)", function(first, rest) return first:upper() .. rest:lower() end)
    return s
end

-- A manually-driven scroll frame (no template dependency): base ScrollFrame
-- widget methods (SetScrollChild / SetVerticalScroll / GetVerticalScrollRange
-- / UpdateScrollChildRect) are part of the core widget type on every client
-- flavor, so this avoids depending on any scrollbar template's continued
-- existence/name across versions.
--
-- `width`/`height` are only the INITIAL size -- callers that want this to grow/shrink
-- with a resizable parent (see UI.MakeResizable) anchor scrollFrame on all 4 edges
-- afterward instead of leaving it at a fixed size; the OnSizeChanged handler below keeps
-- content/text width (and therefore word-wrap and scroll bounds) in sync whenever that
-- happens, whether from a live resize-grip drag or the panel's saved size being restored
-- at login.
function UI.CreateScrollingText(parent, width, height)
    local scrollFrame = CreateFrame("ScrollFrame", nil, parent)
    scrollFrame:SetSize(width, height)
    scrollFrame:EnableMouseWheel(true)

    local content = CreateFrame("Frame", nil, scrollFrame)
    content:SetSize(width, height)
    scrollFrame:SetScrollChild(content)

    local text = content:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
    text:SetPoint("TOPLEFT", 2, 0)
    text:SetWidth(width - 8)
    text:SetJustifyH("LEFT")
    text:SetJustifyV("TOP")

    scrollFrame:SetScript("OnMouseWheel", function(self, delta)
        local current = self:GetVerticalScroll()
        -- Older/unofficial client builds may lack GetVerticalScrollRange entirely --
        -- fall back to computing it directly rather than defaulting to 0, which would
        -- silently cap scrolling at the very top forever.
        local maxScroll
        if self.GetVerticalScrollRange then
            maxScroll = self:GetVerticalScrollRange()
        else
            maxScroll = math.max(0, content:GetHeight() - self:GetHeight())
        end
        local newScroll = current - (delta * 20)
        if newScroll < 0 then newScroll = 0 end
        if newScroll > maxScroll then newScroll = maxScroll end
        self:SetVerticalScroll(newScroll)
    end)

    scrollFrame:SetScript("OnSizeChanged", function(self, w, h)
        if w and w > 16 then
            content:SetWidth(w)
            text:SetWidth(w - 8)
        end
    end)

    return scrollFrame, content, text
end

-- ---------------------------------------------------------------------------
-- Panel position persistence (mainPanel / zonesPanel only, per SavedVariables
-- shape -- the settings frame has no persisted position).
-- ---------------------------------------------------------------------------

function UI.SavePanelPosition(frame, key)
    local point, _, relPoint, x, y = frame:GetPoint(1)
    local ui = ArchipelagoWoWDB.ui[key]
    ui.point = point or "CENTER"
    ui.relPoint = relPoint or "CENTER"
    ui.x = x or 0
    ui.y = y or 0
end

function UI.ApplyPanelPosition(frame, key)
    local ui = ArchipelagoWoWDB.ui[key]
    frame:ClearAllPoints()
    frame:SetPoint(ui.point or "CENTER", UIParent, ui.relPoint or "CENTER", ui.x or 0, ui.y or 0)
    if ui.width and ui.height then
        frame:SetSize(ui.width, ui.height)
    end
end

-- Saves the frame's current size alongside its position (same `ui[key]` entry) -- called
-- both after a drag-move (size unchanged, just re-saved) and after a resize-grip drag.
function UI.SavePanelSize(frame, key)
    local ui = ArchipelagoWoWDB.ui[key]
    ui.width = frame:GetWidth()
    ui.height = frame:GetHeight()
end

-- Adds a bottom-right drag-to-resize grip to `frame` and wires it (and the existing
-- drag-to-move handler) to persist width/height into ArchipelagoWoWDB.ui[key], the same
-- way position is already persisted. `onResize`, if given, is called after every resize
-- (drag-in-progress AND the final drop) so callers can reflow their own content (e.g. the
-- scrolling log/list needs its content width and wrapped-text height recalculated as the
-- panel grows or shrinks).
function UI.MakeResizable(frame, key, minWidth, minHeight, onResize)
    frame:SetResizable(true)
    Compat.SetResizeBounds(frame, minWidth, minHeight, 900, 900)

    local grip = CreateFrame("Button", nil, frame)
    grip:SetSize(16, 16)
    grip:SetPoint("BOTTOMRIGHT", -4, 4)
    grip:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    grip:SetHighlightTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Highlight")
    grip:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Down")
    grip:SetScript("OnMouseDown", function()
        frame:StartSizing("BOTTOMRIGHT")
    end)
    grip:SetScript("OnMouseUp", function()
        frame:StopMovingOrSizing()
        UI.SavePanelSize(frame, key)
        if onResize then onResize() end
    end)

    if onResize then
        frame:SetScript("OnSizeChanged", onResize)
    end
end

-- ---------------------------------------------------------------------------
-- Main "Archipelago" panel (the only panel -- reachable via /apwow or
-- /archipelago). No settings frame: there is nothing left to configure here
-- (no server/slot/password -- see the bridge program instead; no auto-sync --
-- see Sync.lua's file header for why).
-- ---------------------------------------------------------------------------

function UI.CreateMainPanel()
    if UI.mainPanel then return UI.mainPanel end

    local frame = Compat.CreateFrame("Frame", "ArchipelagoWoWMainPanel", UIParent)
    frame:SetSize(380, 430)
    frame:SetFrameStrata("DIALOG")
    Compat.SetBackdrop(frame, Compat.PANEL_BACKDROP)
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        UI.SavePanelPosition(self, "mainPanel")
    end)
    UI.MakeResizable(frame, "mainPanel", 320, 320, function()
        if UI.mainPanel then UI.RefreshLogText(UI.mainPanel) end
    end)
    frame:SetScript("OnShow", function(self)
        ArchipelagoWoWDB.ui.mainPanel.shown = true
        UI.RefreshMainPanel()
    end)
    frame:SetScript("OnHide", function(self)
        ArchipelagoWoWDB.ui.mainPanel.shown = false
    end)
    frame:Hide()

    local title = frame:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge")
    title:SetPoint("TOP", 0, -18)
    title:SetText("Archipelago")

    local closeBtn = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
    closeBtn:SetPoint("TOPRIGHT", -4, -4)
    closeBtn:SetScript("OnClick", function() frame:Hide() end)

    local statusText = frame:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
    statusText:SetPoint("TOP", title, "BOTTOM", 0, -10)
    statusText:SetWidth(340)
    frame.statusText = statusText

    local sendBtn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    sendBtn:SetSize(200, 22)
    sendBtn:SetPoint("TOP", statusText, "BOTTOM", 0, -16)
    sendBtn:SetText("Send All Previous Levels")
    sendBtn:SetScript("OnClick", function()
        Sync.QueueAllPreviousLevels()
        UI.RefreshAll()
    end)
    frame.sendBtn = sendBtn

    local syncBtn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    syncBtn:SetSize(200, 22)
    syncBtn:SetPoint("TOP", sendBtn, "BOTTOM", 0, -8)
    syncBtn:SetText("Sync Now (Reload UI)")
    syncBtn:SetScript("OnClick", function()
        Sync.SyncNow()
    end)

    local zonesBtn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    zonesBtn:SetSize(200, 22)
    zonesBtn:SetPoint("TOP", syncBtn, "BOTTOM", 0, -8)
    zonesBtn:SetText("View Zones / Progress")
    zonesBtn:SetScript("OnClick", function()
        UI.ToggleZonesPanel()
    end)

    local logLabel = frame:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    logLabel:SetPoint("TOP", zonesBtn, "BOTTOM", 0, -14)
    logLabel:SetText("Activity Log (newest first)")

    local scrollFrame, content, text = UI.CreateScrollingText(frame, 340, 190)
    -- Anchored on all 4 edges (rather than a fixed size) so it grows/shrinks with the
    -- panel as it's resized -- see UI.MakeResizable above and CreateScrollingText's
    -- OnSizeChanged handler, which keeps content/text width in sync with this.
    scrollFrame:SetPoint("TOP", logLabel, "BOTTOM", 0, -6)
    scrollFrame:SetPoint("BOTTOM", frame, "BOTTOM", 0, 16)
    scrollFrame:SetPoint("LEFT", frame, "LEFT", 20, 0)
    scrollFrame:SetPoint("RIGHT", frame, "RIGHT", -20, 0)
    frame.logScroll = scrollFrame
    frame.logContent = content
    frame.logText = text

    local elapsedAccum = 0
    frame:SetScript("OnUpdate", function(self, elapsed)
        elapsedAccum = elapsedAccum + elapsed
        if elapsedAccum >= 1 then
            elapsedAccum = 0
            UI.RefreshMainPanel()
        end
    end)

    UI.mainPanel = frame
    return frame
end

function UI.RefreshLogText(frame)
    local db = ArchipelagoWoWDB
    local lines = {}
    local count = #db.log
    local shown = 0
    for i = count, 1, -1 do
        local entry = db.log[i]
        local when = Core.FormatRelativeTime(entry.ts)
        table.insert(lines, string.format("|cffaaaaaa[%s]|r %s", when, entry.text))
        shown = shown + 1
        if shown >= 100 then break end
    end
    if #lines == 0 then
        table.insert(lines, "|cff999999No activity yet.|r")
    end

    frame.logText:SetText(table.concat(lines, "\n"))
    local neededHeight = frame.logText:GetStringHeight() + 8
    local minHeight = frame.logScroll:GetHeight()
    frame.logContent:SetHeight(neededHeight > minHeight and neededHeight or minHeight)
    if frame.logScroll.UpdateScrollChildRect then
        frame.logScroll:UpdateScrollChildRect()
    end
end

function UI.RefreshMainPanel()
    local frame = UI.mainPanel
    if not frame or not frame:IsShown() then return end

    local bridge = ArchipelagoWoW_BridgeDB
    local syncedStr = Core.FormatRelativeTime(bridge and bridge.lastSyncEpoch)
    -- Explicit "\n", not a single line left to word-wrap on its own: the wrap point
    -- depends on the rendered pixel width of syncedStr ("4s ago" vs "32s ago" vs "2h ago"
    -- vs "never"), so a one-line version would inconsistently break mid-sentence depending
    -- on which one happened to be current -- confirmed live, comparing screenshots seconds
    -- apart. Forcing the break here keeps it at exactly two lines every time.
    local line = string.format("Last synced %s\nClick Sync Now for the current state", syncedStr)

    local seedName = ArchipelagoWoWDB.session.seedName
    if seedName then
        line = line .. string.format("\nSeed: %s", tostring(seedName))
    end

    local slotData = bridge and bridge.slotData
    if slotData and (slotData.expansion or slotData.goal or slotData.faction) then
        local parts = {}
        -- expansion is already display-cased ("Wrath of the Lich King", see EXPANSION_NAMES
        -- in Options.py) -- only goal/faction need DisplayCase, since those come from raw
        -- snake_case option identifiers ("gold_hunt", "alliance") that are also compared
        -- against literally (e.g. the gold_hunt check just below), so the underlying
        -- slotData.goal/faction values themselves must stay untouched.
        if slotData.expansion then table.insert(parts, tostring(slotData.expansion)) end
        if slotData.faction then table.insert(parts, DisplayCase(slotData.faction)) end
        if slotData.goal then table.insert(parts, "Goal: " .. DisplayCase(slotData.goal)) end
        line = line .. "\n" .. table.concat(parts, "  -  ")
    end

    local pendingCount = #ArchipelagoWoWDB.pendingChecks
    if pendingCount > 0 then
        line = line .. string.format("\n|cffffcc00%d level(s) queued, will send on next sync|r", pendingCount)
    end

    frame.statusText:SetText(line)
    UI.RefreshLogText(frame)
end

function UI.ToggleMainPanel()
    local frame = UI.CreateMainPanel()
    if frame:IsShown() then
        frame:Hide()
    else
        UI.ApplyPanelPosition(frame, "mainPanel")
        frame:Show()
    end
end

-- ---------------------------------------------------------------------------
-- Zones / Progress panel
-- ---------------------------------------------------------------------------

function UI.CreateZonesPanel()
    if UI.zonesPanel then return UI.zonesPanel end

    local frame = Compat.CreateFrame("Frame", "ArchipelagoWoWZonesPanel", UIParent)
    frame:SetSize(380, 480)
    frame:SetFrameStrata("DIALOG")
    Compat.SetBackdrop(frame, Compat.PANEL_BACKDROP)
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        UI.SavePanelPosition(self, "zonesPanel")
    end)
    UI.MakeResizable(frame, "zonesPanel", 320, 320, function()
        if UI.zonesPanel then UI.RefreshZonesPanel() end
    end)
    frame:SetScript("OnShow", function(self)
        ArchipelagoWoWDB.ui.zonesPanel.shown = true
        UI.RefreshZonesPanel()
    end)
    frame:SetScript("OnHide", function(self)
        ArchipelagoWoWDB.ui.zonesPanel.shown = false
    end)
    frame:Hide()

    local title = frame:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge")
    title:SetPoint("TOP", 0, -18)
    title:SetText("Zones / Progress")

    local subtitle = frame:CreateFontString(nil, "ARTWORK", "GameFontDisableSmall")
    subtitle:SetPoint("TOP", title, "BOTTOM", 0, -4)
    frame.subtitle = subtitle

    local closeBtn = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
    closeBtn:SetPoint("TOPRIGHT", -4, -4)
    closeBtn:SetScript("OnClick", function() frame:Hide() end)

    -- Small Sync Now shortcut so this panel is usable without also keeping the main
    -- Archipelago panel open just to reach that button. A plain UIPanelButtonTemplate
    -- text button, not an icon-only button -- an earlier attempt using
    -- "Interface\Buttons\UI-RefreshButton" rendered invisible (texture path doesn't
    -- resolve on this client), whereas UIPanelButtonTemplate is already proven to render
    -- correctly everywhere else in this UI.
    local zonesSyncBtn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    zonesSyncBtn:SetSize(50, 20)
    -- Matches closeBtn's vertical center (a standard UIPanelCloseButton is ~32px tall,
    -- anchored at y=-4, so its center sits around y=-20; this button is 20px tall, so
    -- -10 centers it at the same height) and clears the ~12px border inset horizontally.
    zonesSyncBtn:SetPoint("TOPLEFT", 10, -10)
    zonesSyncBtn:SetText("Sync")
    zonesSyncBtn:SetScript("OnClick", function() Sync.SyncNow() end)
    zonesSyncBtn:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText("Sync Now (Reload UI)")
        GameTooltip:Show()
    end)
    zonesSyncBtn:SetScript("OnLeave", function() GameTooltip:Hide() end)

    local scrollFrame, content, text = UI.CreateScrollingText(frame, 340, 410)
    -- Anchored on all 4 edges (see CreateMainPanel's identical comment) so it grows/
    -- shrinks with the panel as it's resized.
    scrollFrame:SetPoint("TOP", subtitle, "BOTTOM", 0, -10)
    scrollFrame:SetPoint("BOTTOM", frame, "BOTTOM", 0, 16)
    scrollFrame:SetPoint("LEFT", frame, "LEFT", 20, 0)
    scrollFrame:SetPoint("RIGHT", frame, "RIGHT", -20, 0)
    frame.scroll = scrollFrame
    frame.content = content
    frame.text = text

    UI.zonesPanel = frame
    return frame
end

-- `map` is name -> count (e.g. levelItems) -- shows "xN" only when N > 1 (a Sequential
-- "Maximum Level 40" only ever has count 1; a Progressive "Progressive Levels" count is
-- meaningful).
local function AppendCountedSection(lines, headerText, map)
    table.insert(lines, string.format("|cffffd100%s|r", headerText))
    local names = {}
    for name, count in pairs(map or {}) do
        if count and count > 0 then table.insert(names, name) end
    end
    table.sort(names)
    if #names == 0 then
        table.insert(lines, "  |cff999999(none yet)|r")
    else
        for _, name in ipairs(names) do
            local count = map[name]
            if count > 1 then
                table.insert(lines, string.format("  %s x%d", name, count))
            else
                table.insert(lines, "  " .. name)
            end
        end
    end
    table.insert(lines, "")
end

function UI.RefreshZonesPanel()
    local frame = UI.zonesPanel
    if not frame or not frame:IsShown() then return end

    local bridge = ArchipelagoWoW_BridgeDB
    if not bridge then return end
    local lines = {}

    local levelCap = bridge.currentLevelCap or 10
    local subtitle = string.format("Current level cap: %d (as of last sync)", levelCap)

    local slotData = bridge.slotData
    if slotData and slotData.goal == "gold_hunt" and slotData.goldHuntAmount then
        local goldCount = bridge.goldCount or 0
        subtitle = subtitle .. string.format("\nGold: %d/%d", goldCount, slotData.goldHuntAmount)
    end
    frame.subtitle:SetText(subtitle)

    AppendCountedSection(lines, "Level Items Received", bridge.levelItems)

    table.insert(lines, "|cffffd100Zones Unlocked|r")
    local groups = Zones.GroupUnlocked(bridge.unlockedZones)
    if #groups == 0 then
        table.insert(lines, "  |cff999999(none yet)|r")
    else
        for _, group in ipairs(groups) do
            table.insert(lines, string.format("|cff66ccff%s|r", group.category))
            for _, item in ipairs(group.items) do
                table.insert(lines, "  " .. item)
            end
        end
    end

    frame.text:SetText(table.concat(lines, "\n"))
    local neededHeight = frame.text:GetStringHeight() + 8
    local minHeight = frame.scroll:GetHeight()
    frame.content:SetHeight(neededHeight > minHeight and neededHeight or minHeight)
    if frame.scroll.UpdateScrollChildRect then
        frame.scroll:UpdateScrollChildRect()
    end
end

function UI.ToggleZonesPanel()
    local frame = UI.CreateZonesPanel()
    if frame:IsShown() then
        frame:Hide()
    else
        UI.ApplyPanelPosition(frame, "zonesPanel")
        frame:Show()
    end
end

-- ---------------------------------------------------------------------------
-- Login/reload wiring + refresh-everything entry point
-- ---------------------------------------------------------------------------

function UI.RefreshAll()
    if UI.mainPanel then UI.RefreshMainPanel() end
    if UI.zonesPanel then UI.RefreshZonesPanel() end
end

-- Called once from Core's PLAYER_LOGIN handler, i.e. right after every
-- ReloadUI/login, once both SavedVariables tables are guaranteed loaded.
function UI.OnLogin()
    -- Captured BEFORE creating either frame: a freshly CreateFrame()'d frame is shown by
    -- default, so CreateMainPanel/CreateZonesPanel's own frame:Hide() call is a real
    -- shown->hidden transition that fires OnHide -- which immediately overwrites
    -- ui.mainPanel.shown/ui.zonesPanel.shown to false, clobbering the very value loaded
    -- from last session before we'd otherwise get a chance to read it below (confirmed
    -- live: panels never actually remembered being open because of this).
    local mainShouldShow = ArchipelagoWoWDB.ui.mainPanel.shown
    local zonesShouldShow = ArchipelagoWoWDB.ui.zonesPanel.shown

    local mainFrame = UI.CreateMainPanel()
    UI.ApplyPanelPosition(mainFrame, "mainPanel")
    if mainShouldShow then
        mainFrame:Show()
    else
        mainFrame:Hide()
    end

    local zonesFrame = UI.CreateZonesPanel()
    UI.ApplyPanelPosition(zonesFrame, "zonesPanel")
    if zonesShouldShow then
        zonesFrame:Show()
    else
        zonesFrame:Hide()
    end

    UI.RefreshAll()
end

-- ---------------------------------------------------------------------------
-- Slash commands
-- ---------------------------------------------------------------------------

SLASH_ARCHIPELAGOWOW1 = "/apwow"
SLASH_ARCHIPELAGOWOW2 = "/archipelago"
SlashCmdList["ARCHIPELAGOWOW"] = function(msg)
    msg = tostring(msg or "")
    msg = msg:lower():match("^%s*(.-)%s*$")
    if msg == "zones" then
        UI.ToggleZonesPanel()
    else
        UI.ToggleMainPanel()
    end
end
