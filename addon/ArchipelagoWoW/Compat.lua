-- ArchipelagoWoW: Compat.lua
-- Cross-version compatibility helpers. This is the only file that should ever branch
-- on API surface.
--
-- Supported scope is the original, live-service client patches for Vanilla through
-- Mists of Pandaria (2004-2013), meaning the actual old game as it's still run today
-- via private-server emulation (AzerothCore, TrinityCore, and similar), not Blizzard's
-- 2019+ "WoW Classic" rerelease product line. The shipped .toc files are the real
-- scope boundary, since each is pinned to that expansion's original final-patch
-- Interface number (see addon/README.md's table) rather than a modern Classic-rerelease
-- one.
--
-- That distinction matters here because WOW_PROJECT_ID (and every WOW_PROJECT_*
-- named global) was only added for WoW Classic's 2019 launch (patch 8.1.5), so it does
-- not exist at all on a genuine original-era client, or on a private server emulating
-- one, which is every client this addon actually targets. So this file deliberately
-- does not branch on WOW_PROJECT_ID or client flavor anywhere; every check below reads
-- the actual API surface instead (does this global/mixin exist right now?), which gives
-- the correct answer both for the real target (nothing beyond what an original client
-- ever exposed) and, harmlessly, for anyone who loads this out of scope on a modern
-- client anyway.

local ADDON_NAME, APW = ...

APW.Compat = APW.Compat or {}
local Compat = APW.Compat

-- True on a genuine original-era client, and false on any modern client, in or out of
-- scope; see Map.lua/MapLegacy.lua, which pick their implementation off this flag.
Compat.HasModernMapAPI = C_Map ~= nil

-- Whether a frame needs the BackdropTemplate mixin to get SetBackdrop/backdrop methods
-- at all. It's absent entirely on the original clients this addon targets, since those
-- already have those methods built into the base Frame widget.
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

-- Shared basic panel backdrop definition (dialog-box style border, works via the
-- original client's native backdrop methods without needing BackdropTemplate).
Compat.PANEL_BACKDROP = {
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 11, right = 12, top = 12, bottom = 11 },
}

-- SetMinResize/SetMaxResize were replaced by a single SetResizeBounds call in much
-- later (10.0+) clients; every original-era client this addon targets only has the
-- older pair.
function Compat.SetResizeBounds(frame, minWidth, minHeight, maxWidth, maxHeight)
    if frame.SetResizeBounds then
        frame:SetResizeBounds(minWidth, minHeight, maxWidth, maxHeight)
    else
        frame:SetMinResize(minWidth, minHeight)
        frame:SetMaxResize(maxWidth, maxHeight)
    end
end
