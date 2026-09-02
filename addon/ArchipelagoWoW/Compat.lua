-- ArchipelagoWoW: Compat.lua
-- Cross-version compatibility helpers. This is the only file that should ever branch
-- on API surface.
--
-- The addon is made for World of Warcraft Classic, from Classic Era through Mists of
-- Pandaria Classic, and also runs on retail. The same files load on every one of
-- them, so nothing here branches on WOW_PROJECT_ID or client flavor; every check below
-- reads the actual API surface instead (does this global/mixin exist right now?).

local ADDON_NAME, APW = ...

APW.Compat = APW.Compat or {}
local Compat = APW.Compat

-- True when the client has the C_Map API, as every Classic client does; see
-- Map.lua/MapLegacy.lua, which pick their implementation off this flag.
Compat.HasModernMapAPI = C_Map ~= nil

-- Whether a frame needs the BackdropTemplate mixin to get SetBackdrop/backdrop methods.
-- Without the mixin, those methods are built into the base Frame widget.
Compat.NeedsBackdropTemplate = BackdropTemplateMixin ~= nil

-- Creates a frame, adding the BackdropTemplate mixin only where required.
function Compat.CreateFrame(frameType, name, parent, template)
    if Compat.NeedsBackdropTemplate then
        if template and template ~= "" then
            template = template .. ",BackdropTemplate"
        else
            template = "BackdropTemplate"
        end
    end
    return CreateFrame(frameType, name, parent, template)
end

-- Applies a backdrop table the same way on every client flavor that supports it.
function Compat.SetBackdrop(frame, backdrop)
    if frame and frame.SetBackdrop then
        frame:SetBackdrop(backdrop)
    end
end

-- Shared basic panel backdrop definition (dialog-box style border, works with or
-- without BackdropTemplate).
Compat.PANEL_BACKDROP = {
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 11, right = 12, top = 12, bottom = 11 },
}

-- Uses SetResizeBounds where it exists, and the older SetMinResize/SetMaxResize pair
-- otherwise.
function Compat.SetResizeBounds(frame, minWidth, minHeight, maxWidth, maxHeight)
    if frame.SetResizeBounds then
        frame:SetResizeBounds(minWidth, minHeight, maxWidth, maxHeight)
    else
        frame:SetMinResize(minWidth, minHeight)
        frame:SetMaxResize(maxWidth, maxHeight)
    end
end
