"""
Archipelago desktop "bridge" client for the World of Warcraft Leveling apworld.

WoW's Lua addon sandbox has never exposed sockets or live file I/O to addons (true in
every client version, Vanilla through retail) -- so the actual Archipelago connection
lives here, in this ordinary desktop Python process, and talks to the WoW addon
(ArchipelagoWoW, under addon/ in this repo) purely through two SavedVariables files on
disk:

  * ArchipelagoWoWDB (written by the game itself, at logout/ReloadUI only -- we only
    ever READ this file, see _handle_addon_file_change below). Its `pendingChecks` are
    level numbers the addon wants checked but hasn't seen confirmed yet.
  * ArchipelagoWoW_BridgeDB (written only by us, read by the game at its next login --
    see _write_bridge_file/_build_bridge_db below). Tells the addon what's connected,
    what the AP server has actually acked, and what items have arrived.

NOTE: this client connects to the Archipelago server the same way any other Archipelago
client does -- its own console/GUI (e.g. `/connect host:port`, or the GUI's connect
fields), same as Northgard's client. There is deliberately no server-address/slot/
password configuration on the addon side at all (that was tried and reverted -- see
addon/README.md) -- the two things are independent: which AP *server/slot* you're
connected to is decided here, in this process, exactly like every other AP client;
which WoW *character* this process reads/writes SavedVariables for is a completely
separate question, resolved below (see "WHICH CHARACTER").

Both are plain Lua table literals; see savedvariables_io.py for the (deliberately
restricted, no-eval) parser/serializer used on both sides of that exchange.

Since the WoW client can only flush SavedVariables to disk at logout or ReloadUI(), the
addon's own log already says outright that there's no live/instant signaling -- this
client's whole job is to poll ArchipelagoWoWDB's mtime (every POLL_INTERVAL_SECONDS) and
react whenever it changes. Do not add filesystem-event watching or chat-log tailing here;
that idea was explicitly floated and explicitly deferred to a separate future experiment.

Structure/launch() pattern and CommonClient usage cloned from the same author's working
Northgard client (worlds/northgard/NorthgardClient.py in the Archipelago-Northgard repo)
-- server_loop/CommonContext/ClientCommandProcessor/get_base_parser/gui_enabled are all
used exactly the same way. This module is loaded by worlds/wow_leveling/__init__.py via
`from .WoWLevelingClient import launch as Main`, mirroring worlds/northgard/__init__.py's
`from .NorthgardClient import launch as Main`.

WHICH CHARACTER: a WoW install can have many <Account>/<Realm>/<Character> combinations
under WTF/Account/ -- on a machine used for more than one throwaway test character (or
one used for multiple realms/servers at once), "just pick whichever SavedVariables file
changed most recently" is a real footgun: logging into an unrelated alt for two minutes
to check mail would silently steal "active" status from the character actually playing
this room. So this is explicit, not guessed:

  * If exactly one ArchipelagoWoW.lua exists under the configured install, it's used --
    no ambiguity, nothing to configure.
  * If more than one exists, /wowchar lists them (as "<Account>/<Realm>/<Character>",
    read straight from each file's own path -- SavedVariables layout already encodes
    this, no need for the addon to duplicate it) and lets you pin one explicitly by
    index; the pin is persisted in client_config.json (see _CONFIG_FILE) the same way
    wow_install_dir is, so it survives a bridge restart. Until you pin one, the most-
    recent-mtime heuristic is still used as a fallback -- but a warning is logged on
    every poll tick while more than one candidate exists and nothing is pinned, rather
    than silently guessing forever.

The bridge reply is always written into that same character's SavedVariables folder,
since SavedVariables are strictly per-character and the addon can only ever read its own
folder back.
"""
from __future__ import annotations

import asyncio
import glob
import json
import os
import re
import sys
import threading
import time
import typing

import Utils
from CommonClient import gui_enabled, logger, get_base_parser, CommonContext, ClientCommandProcessor, server_loop
from NetUtils import ClientStatus

from .savedvariables_io import LuaParseError, parse_saved_variables, dumps_lua_assignment, lua_table_to_list

# Both of these are the same package this client ships inside -- read-only imports here,
# never modified by this client. Both define `game = "World of Warcraft Leveling"` (see
# Items.py's WoWLevelingItem.game and __init__.py's WoWLevelingWorld.game / the registered
# Component("WoW Leveling Client", ...)); this constant, and the Component-name strings
# stripped in launch() below, must stay in sync with those two files if either ever
# changes the game name or Component name.
from .Items import (
    item_table as _item_table,
    GOLD_ITEM_NAME as _GOLD_ITEM_NAME,
    PROGRESSIVE_LEVELS_ITEM_NAME as _PROGRESSIVE_LEVELS_ITEM_NAME,
    SEQUENTIAL_LEVEL_ITEMS as _SEQUENTIAL_LEVEL_ITEMS,
)
from .Locations import (
    location_table as _location_table,
    GOLD_HUNT_LOCATION_NAME as _GOLD_HUNT_LOCATION_NAME,
    LEVELING_LOCATION_NAME as _LEVELING_LOCATION_NAME,
)
from .Options import Goal as _GoalOption, Faction as _FactionOption, EXPANSION_NAMES as _EXPANSION_NAMES
from .Regions import BRACKET_MAX_LEVEL as _BRACKET_MAX_LEVEL

GAME_NAME = "World of Warcraft Leveling"

ADDON_SV_FILENAME = "ArchipelagoWoW.lua"
BRIDGE_SV_FILENAME = "ArchipelagoWoW_Bridge.lua"
ADDON_DB_VAR = "ArchipelagoWoWDB"
BRIDGE_DB_VAR = "ArchipelagoWoW_BridgeDB"

# Short on purpose: sending a check and getting the resulting item back is a round trip
# (this poll tick sends LocationChecks, the server's ReceivedItems reply arrives some time
# later, handled asynchronously by on_package -- NOT within this same tick). Whatever this
# tick writes to the bridge file is only as fresh as the last completed round trip, so a
# long interval here directly means a longer window where clicking Sync Now shows stale
# data and needs a second reload to catch up (confirmed live: at 2.0s this was genuinely
# noticeable). 0.5s keeps that window well under normal human reaction time instead.
POLL_INTERVAL_SECONDS = 0.5
# How often the bridge file gets rewritten on disk even when nothing in it actually
# changed, purely so lastSyncEpoch (the addon's "synced Xs ago" display) doesn't go stale
# during an idle period. Deliberately much longer than POLL_INTERVAL_SECONDS: writing this
# file on literally every poll tick was pure overhead for no observable benefit, since
# nothing reads it that often. NOTE: this is *not* what caused the client-close hang once
# attributed to it (see SHUTDOWN_TIMEOUT_SECONDS for the actual fix) -- WoW's own
# SavedVariables flush writes ArchipelagoWoW.lua, a different file the bridge only ever
# reads, never ArchipelagoWoW_Bridge.lua, so the two processes were never actually
# contending for the same file in the first place.
MIN_BRIDGE_WRITE_INTERVAL_SECONDS = 5.0
# Absolute deadline for the entire close sequence in main() -- past this, the process is
# force-killed outright via the watchdog thread armed there, rather than kept waiting on
# whatever caused the hang. Short on purpose: everything this deadline covers (cancelling
# bridge_loop, one best-effort file write, a disconnect handshake) is normally sub-second, so
# this only ever actually elapses when something really is stuck -- at which point there's
# nothing more to gain by waiting longer.
SHUTDOWN_TIMEOUT_SECONDS = 3.0
MAX_INCOMING_LOG = 200

# Locations are declared "Level 01".."Level 90" (zero-padded to 2 digits -- see
# Locations.py's _RAW_LOCATIONS), never bare "Level 1"; _LEVEL_LOCATION_RE still matches either way
# when reading a location *name* back (int() doesn't care about leading zeros), but
# building a name to look *up* in _LOCATION_NAME_TO_ID (see _handle_addon_file_change)
# must zero-pad, or "Level 1" simply won't be a key in that table.
_LEVEL_LOCATION_RE = re.compile(r"^Level (\d+)$")

# ---------------------------------------------------------------------------
# Item -> bridge-bucket classification, and id<->name translation.
#
# This client ships inside the same apworld package as Items.py/Locations.py -- imported
# read-only here, exactly the way Northgard's own NorthgardClient.py imports its sibling
# Items.py/Locations.py for the same reason -- so translating AP's numeric item/location
# ids to/from names, and classifying an item name
# into 'zone'/'level_item', can both be done directly from this game's own local
# tables rather than round-tripping through the network DataPackage -- simpler and
# available immediately (no "hasn't arrived yet" race), and it's exactly Northgard's
# precedent. item_name_groups (Zones/Dungeons/Classes) exists on Items.py but is a
# World-authoring/generation-time concept never sent over the wire -- data.category
# tuples (also local, also authoritative) serve the same purpose here.
# ---------------------------------------------------------------------------

_ITEM_ID_TO_NAME: typing.Dict[int, str] = {data.code: name for name, data in _item_table.items()}
_LOCATION_NAME_TO_ID: typing.Dict[str, int] = {name: data.id for name, data in _location_table.items()}
_LOCATION_ID_TO_NAME: typing.Dict[int, str] = {v: k for k, v in _LOCATION_NAME_TO_ID.items()}


def _choice_option_id_to_name(choice_cls: type) -> typing.Dict[int, str]:
    """{0: 'leveling', 1: 'gold_hunt', ...} derived straight from a Options.Choice
    subclass's own `option_<name> = <id>` class attributes -- kept in sync with
    Options.py automatically rather than duplicating those id<->name pairs by hand."""
    return {
        value: key[len("option_"):]
        for key, value in vars(choice_cls).items()
        if key.startswith("option_") and isinstance(value, int) and not isinstance(value, bool)
    }


_GOAL_ID_TO_NAME = _choice_option_id_to_name(_GoalOption)
_FACTION_ID_TO_NAME = _choice_option_id_to_name(_FactionOption)


def _classify_item(item_name: str) -> typing.Optional[str]:
    """Returns 'zone', 'level_item', 'gold', or None (unrecognized/filler/class/faction/
    etc.), using Items.py's own per-item category tuples -- see module note above. Class
    and faction items are deliberately NOT tracked here: both are always a single, fixed
    choice known from the moment you connect (faction items are always precollected,
    never placed in the pool; a class item is precollected too whenever randomize_class
    is on), never something that progressively "unlocks" -- so there's nothing worth
    showing progress for in the addon's Zones/Progress panel."""
    if item_name == _GOLD_ITEM_NAME:
        return "gold"
    if item_name == _PROGRESSIVE_LEVELS_ITEM_NAME or item_name in _SEQUENTIAL_LEVEL_ITEMS:
        return "level_item"
    data = _item_table.get(item_name)
    if data is None:
        return None
    if "Zones" in data.category:
        return "zone"
    return None


_SEQUENTIAL_LEVEL_TO_INT: typing.Dict[str, int] = {
    name: int(name.rsplit(" ", 1)[-1]) for name in _SEQUENTIAL_LEVEL_ITEMS
}


def _current_level_cap(level_item_counts: typing.Dict[str, int]) -> int:
    """Highest character level currently reachable purely from level-cap items received so
    far -- ignoring whether a zone item is also available for that bracket, which the
    addon already shows separately under "Zones Unlocked". Baseline is
    BRACKET_MAX_LEVEL[0] (10): "Levels 01-10" needs no item at all (see Rules.py), so
    that's always reachable regardless of what's been received."""
    sequential_levels = [
        value for name, value in _SEQUENTIAL_LEVEL_TO_INT.items() if level_item_counts.get(name)
    ]
    if sequential_levels:
        return max(sequential_levels)

    progressive_count = level_item_counts.get(_PROGRESSIVE_LEVELS_ITEM_NAME, 0)
    index = max(0, min(progressive_count, len(_BRACKET_MAX_LEVEL) - 1))
    return _BRACKET_MAX_LEVEL[index]


def _translate_slot_data(slot_data: dict, seed_name: typing.Optional[str]) -> dict:
    """slot_data's expansion/goal/faction are raw Choice-option ints (see
    WoWLevelingWorld.fill_slot_data in __init__.py) -- translated here into the
    human-readable strings the addon actually wants to display (see the bridge DB shape
    in the file contract). Falls back to nil (None) for anything out of range/unknown
    rather than guessing, per the contract's "nil-safe" requirement."""
    expansion_id = slot_data.get("expansion")
    expansion_name = (
        _EXPANSION_NAMES[expansion_id] if isinstance(expansion_id, int) and 0 <= expansion_id < len(_EXPANSION_NAMES)
        else None
    )
    return {
        "expansion": expansion_name,
        "goal": _GOAL_ID_TO_NAME.get(slot_data.get("goal")),
        "faction": _FACTION_ID_TO_NAME.get(slot_data.get("faction")),
        # Only meaningful when goal is Gold Hunt, but harmless to always include -- see
        # WoWLevelingWorld.fill_slot_data.
        "goldHuntAmount": slot_data.get("gold_hunt_amount"),
        # Mirrored for display only (see addon/ArchipelagoWoW/Core.lua's Reconcile, which
        # copies this into its own session.seedName) -- not part of the literal slotData
        # shape in the original spec text, but the addon's own real code reads it.
        "seedName": seed_name,
    }


# ---------------------------------------------------------------------------
# Local config (per-machine WoW install path) -- modeled on Northgard's save_state.py /
# NorthgardClient.py client_config.json convention: a small JSON file under the real
# Windows "Saved Games" folder (survives a WoW reinstall/relocation, unlike anything
# stored inside the WoW install itself), resolved once via SHGetKnownFolderPath so a
# redirected Saved Games folder (another drive, etc.) is still found correctly.
# ---------------------------------------------------------------------------

def _known_folder_path(guid_str: str, fallback: str) -> str:
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_byte * 8),
            ]

        guid = GUID()
        if ctypes.windll.ole32.IIDFromString(ctypes.c_wchar_p(f"{{{guid_str}}}"), ctypes.byref(guid)) != 0:
            return fallback

        path_ptr = ctypes.c_wchar_p()
        result = ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, 0, ctypes.byref(path_ptr))
        if result != 0 or not path_ptr.value:
            return fallback
        path = path_ptr.value
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)
        return path
    except Exception:
        return fallback


_FOLDERID_SAVED_GAMES = "4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4"

_CONFIG_DIR = os.path.join(
    _known_folder_path(_FOLDERID_SAVED_GAMES, os.path.join(os.path.expanduser("~"), "Saved Games")),
    "Archipelago", "WoW Leveling",
)
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "client_config.json")


def _load_config() -> dict:
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config if isinstance(config, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_config(config: dict) -> None:
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError:
        logger.warning(f"[WoW Leveling] Couldn't persist client config to {_CONFIG_FILE}")


# Battle.net-managed installs (retail, Classic, Classic Era, PTR, ...) organize each game
# version into its own subfolder under one shared install root -- WTF lives inside that
# subfolder (e.g. ".../World of Warcraft/_retail_/WTF"), not directly in the root the way
# an unzipped-anywhere private-server client (this project's own WotLK 3.3.5a test client)
# is laid out. Checked in a fixed order so a dual retail+Classic install doesn't
# ambiguously resolve to whichever happens to be listed first.
_BATTLENET_VERSION_FOLDERS = ["_retail_", "_classic_", "_classic_era_", "_ptr_", "_classic_ptr_", "_beta_"]


def _resolve_wtf_containing_dir(path: typing.Optional[str]) -> typing.Optional[str]:
    """Returns the actual folder that directly contains WTF/Interface/Data -- either
    `path` itself (flat/private-server-style layout) or one of its known Battle.net
    version subfolders (Battle.net-managed layout), whichever actually has a WTF folder.
    None if neither -- confirmed live that a bare Battle.net root (no WTF directly inside)
    would otherwise silently fail auto-detection/validation for a retail install."""
    if not path:
        return None
    if os.path.isdir(os.path.join(path, "WTF")):
        return path
    for version_folder in _BATTLENET_VERSION_FOLDERS:
        candidate = os.path.join(path, version_folder)
        if os.path.isdir(os.path.join(candidate, "WTF")):
            return candidate
    return None


def _candidate_wow_install_dirs() -> typing.List[str]:
    """Best-effort scan of common install locations. A WOTLK-era private-server client is
    routinely just unzipped anywhere, so this scans every top-level folder under Program
    Files/Program Files (x86)/each drive root/each drive's "Games" folder whose name
    contains "world of warcraft", rather than assuming one fixed path -- this also happens
    to find a real Battle.net-managed install (which really is just named "World of
    Warcraft" under Program Files), whose actual WTF-containing subfolder is then resolved
    by _resolve_wtf_containing_dir, not assumed to be this path directly."""
    search_bases = set()
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        val = os.environ.get(env_var)
        if val:
            search_bases.add(val)

    for letter in "CDEFGH":
        drive = f"{letter}:\\"
        if os.path.isdir(drive):
            search_bases.add(drive)
            search_bases.add(os.path.join(drive, "Games"))

    candidates = []
    for base in search_bases:
        try:
            entries = os.listdir(base)
        except OSError:
            continue
        for name in entries:
            if "world of warcraft" in name.lower():
                candidates.append(os.path.join(base, name))
    return candidates


def _detect_wow_install_dir() -> typing.Optional[str]:
    for candidate in _candidate_wow_install_dirs():
        resolved = _resolve_wtf_containing_dir(candidate)
        if resolved:
            return resolved
    return None


def _resolve_wow_install_dir() -> str:
    config = _load_config()
    configured = _resolve_wtf_containing_dir(config.get("wow_install_dir"))
    if configured:
        return configured

    detected = _detect_wow_install_dir()
    if detected:
        logger.info(f"[WoW Leveling] Auto-detected WoW install folder: {detected}")
        config["wow_install_dir"] = detected
        _save_config(config)
        return detected

    logger.info(
        "[WoW Leveling] Couldn't auto-detect your WoW install -- opening a folder picker "
        "(pick either the WoW folder that directly contains WTF/Interface/Data, e.g. "
        "'...\\World of Warcraft WOTLK 3.3.5a', OR a Battle.net-managed install's root "
        "folder, e.g. '...\\World of Warcraft' -- its _retail_/_classic_/etc. subfolder "
        "is found automatically either way)."
    )
    try:
        picked = Utils.open_directory("Select your World of Warcraft install folder")
    except Exception:
        logger.exception("[WoW Leveling] Folder picker failed")
        picked = None

    resolved_picked = _resolve_wtf_containing_dir(picked)
    if resolved_picked:
        config["wow_install_dir"] = resolved_picked
        _save_config(config)
        logger.info(f"[WoW Leveling] Using {resolved_picked}. Change it later with /wowdir <path>.")
        return resolved_picked

    logger.warning(
        "[WoW Leveling] No WoW install folder configured -- checks/items can't sync until you "
        "set one. Use /wowdir <path to your WoW install folder>."
    )
    return ""


# ---------------------------------------------------------------------------
# SavedVariables file discovery
# ---------------------------------------------------------------------------

def _find_addon_sv_files(wow_install_dir: str) -> typing.List[str]:
    if not wow_install_dir:
        return []
    pattern = os.path.join(wow_install_dir, "WTF", "Account", "*", "*", "*", "SavedVariables", ADDON_SV_FILENAME)
    return glob.glob(pattern)


def _most_recent_addon_sv(wow_install_dir: str) -> typing.Optional[str]:
    """Fallback only -- see _resolve_active_addon_sv. Whichever ArchipelagoWoW.lua under
    WTF/Account/**/SavedVariables/ was written most recently, i.e. whichever character
    most recently logged out or ReloadUI()'d."""
    files = _find_addon_sv_files(wow_install_dir)
    if not files:
        return None
    try:
        return max(files, key=os.path.getmtime)
    except OSError:
        return None


def _character_identity(addon_sv_path: str) -> str:
    """"<Account>/<Realm>/<Character>", read straight from the SavedVariables path itself
    (.../WTF/Account/<Account>/<Realm>/<Character>/SavedVariables/ArchipelagoWoW.lua) --
    that layout already encodes identity, so this never has to ask the addon for it."""
    sv_dir = os.path.dirname(addon_sv_path)
    character_dir = os.path.dirname(sv_dir)
    realm_dir = os.path.dirname(character_dir)
    account_dir = os.path.dirname(realm_dir)
    return f"{os.path.basename(account_dir)}/{os.path.basename(realm_dir)}/{os.path.basename(character_dir)}"


def _resolve_active_addon_sv(ctx: "WoWLevelingContext") -> typing.Optional[str]:
    """Picks which ArchipelagoWoW.lua this bridge session reads/writes for -- see the
    module docstring's "WHICH CHARACTER" section. Explicit pin wins whenever its file
    still exists; otherwise falls back to most-recent-mtime, logging a warning (at most
    once per distinct candidate set, not every poll tick) whenever that fallback is
    ambiguous."""
    files = _find_addon_sv_files(ctx.wow_install_dir)
    if not files:
        return None
    if len(files) == 1:
        return files[0]

    if ctx.pinned_character:
        for path in files:
            if _character_identity(path) == ctx.pinned_character:
                return path
        logger.warning(
            f"[WoW Leveling] Pinned character {ctx.pinned_character!r} not found among "
            f"current candidates -- run /wowchar to re-pin. Falling back to most-recently-used."
        )

    candidates_key = frozenset(files)
    if candidates_key != ctx._warned_ambiguous_candidates:
        ctx._warned_ambiguous_candidates = candidates_key
        listing = ", ".join(_character_identity(p) for p in files)
        logger.warning(
            f"[WoW Leveling] Multiple WoW characters have ArchipelagoWoW data ({listing}) "
            f"and none is pinned -- guessing the most-recently-used one. Run /wowchar to pin "
            f"the right one explicitly."
        )
    return _most_recent_addon_sv(ctx.wow_install_dir)


def _bridge_sv_path_for(addon_sv_path: str) -> str:
    """The sidecar bridge file lives in the exact same <Character>/SavedVariables folder
    as the addon file we just read -- SavedVariables are strictly per-character, so
    writing anywhere else would mean the addon that logged out/reloaded can never read it
    back on its next login."""
    return os.path.join(os.path.dirname(addon_sv_path), BRIDGE_SV_FILENAME)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class WoWLevelingCommandProcessor(ClientCommandProcessor):
    def _cmd_wowdir(self, path: str = "") -> bool:
        """Show, pick, or set this machine's WoW install folder: /wowdir with no argument
        opens a folder picker (or shows the current path); /wowdir <path> sets it
        directly. Accepts either the folder that directly contains WTF/Interface/Data
        (a private-server-style client) or a Battle.net-managed install's root folder
        (its _retail_/_classic_/etc. subfolder is found automatically either way). Per-
        machine, not per-room -- set it once."""
        ctx: WoWLevelingContext = self.ctx
        path = path.strip().strip('"')

        if not path:
            logger.info(f"[WoW Leveling] Current WoW install folder: {ctx.wow_install_dir or '(not set)'}")
            try:
                picked = Utils.open_directory("Select your World of Warcraft install folder", suggest=ctx.wow_install_dir)
            except Exception:
                logger.exception("[WoW Leveling] Folder picker failed")
                return False
            if not picked:
                return False
            path = picked

        resolved = _resolve_wtf_containing_dir(path)
        if not resolved:
            logger.info(f"[WoW Leveling] Not a WoW install folder (no WTF subfolder found there, directly or under _retail_/_classic_/etc.): {path}")
            return False

        ctx.wow_install_dir = resolved
        config = _load_config()
        config["wow_install_dir"] = resolved
        _save_config(config)
        logger.info(f"[WoW Leveling] WoW install folder set to {resolved}")
        return True

    def _cmd_wowchar(self, selector: str = "") -> bool:
        """List every WoW character with Archipelago data under the configured install, or
        pin the one this bridge should read/write for: /wowchar with no argument lists
        candidates (numbered) and shows the current pin, if any; /wowchar <number> or
        /wowchar <text matching an Account/Realm/Character string> pins that one. Only
        matters when more than one character has ArchipelagoWoW data at once -- with just
        one, it's used automatically and there's nothing to pin."""
        ctx: WoWLevelingContext = self.ctx
        files = _find_addon_sv_files(ctx.wow_install_dir)
        if not files:
            logger.info(
                f"[WoW Leveling] No {ADDON_SV_FILENAME} found yet under the configured WoW "
                f"install -- log into WoW with the ArchipelagoWoW addon enabled at least once."
            )
            return True

        identities = [_character_identity(p) for p in files]
        selector = selector.strip()

        if not selector:
            logger.info(f"[WoW Leveling] Pinned character: {ctx.pinned_character or '(none -- using most-recently-used)'}")
            for i, identity in enumerate(identities, start=1):
                logger.info(f"  [{i}] {identity}")
            if len(files) == 1:
                logger.info("[WoW Leveling] Only one candidate -- it's used automatically, no pin needed.")
            return True

        chosen: typing.Optional[str] = None
        if selector.isdigit():
            index = int(selector) - 1
            if 0 <= index < len(identities):
                chosen = identities[index]
        else:
            matches = [identity for identity in identities if selector.lower() in identity.lower()]
            if len(matches) == 1:
                chosen = matches[0]
            elif len(matches) > 1:
                logger.info(f"[WoW Leveling] {selector!r} matches more than one candidate -- be more specific, or use a number.")
                return False

        if chosen is None:
            logger.info(f"[WoW Leveling] No candidate matched {selector!r}. Run /wowchar with no argument to list them.")
            return False

        ctx.pinned_character = chosen
        config = _load_config()
        config["pinned_character"] = chosen
        _save_config(config)
        logger.info(f"[WoW Leveling] Pinned character set to {chosen}.")
        return True

    def _cmd_synced(self) -> bool:
        """Shows which character's SavedVariables folder is currently being watched/synced."""
        ctx: WoWLevelingContext = self.ctx
        if ctx.active_addon_sv_path:
            logger.info(f"[WoW Leveling] Currently syncing: {ctx.active_addon_sv_path}")
        else:
            logger.info(
                f"[WoW Leveling] No {ADDON_SV_FILENAME} found yet under the configured WoW "
                f"install -- log into WoW with the ArchipelagoWoW addon enabled at least once."
            )
        return True


class WoWLevelingContext(CommonContext):
    game = GAME_NAME
    items_handling = 0b111  # full remote item tracking -- the AP server is the source of truth
    command_processor = WoWLevelingCommandProcessor

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.wow_install_dir: str = ""
        self.active_addon_sv_path: typing.Optional[str] = None
        self._last_addon_sv_mtime: float = 0.0

        # Explicit "<Account>/<Realm>/<Character>" pin from client_config.json, or None if
        # unset (falls back to most-recent-mtime -- see _resolve_active_addon_sv). Set via
        # /wowchar, mirroring how wow_install_dir is set via /wowdir.
        self.pinned_character: typing.Optional[str] = None
        # Suppresses re-logging the same "ambiguous, no pin set" warning every 2-second
        # poll tick -- only warns again if the actual candidate set changes.
        self._warned_ambiguous_candidates: typing.Optional[frozenset] = None

        self.slot_data: dict = {}

        self.unlocked_zones: typing.Set[str] = set()
        # Counts, not a set: unlike zones (owned or not), a Progressive Levels count of 3
        # is meaningfully different from 1 -- see _classify_item's docstring for why class/
        # faction items aren't tracked here at all.
        self.level_item_counts: typing.Dict[str, int] = {}
        # Gold Hunt goal progress -- how many "Gold" items received so far, out of
        # slot_data's gold_hunt_amount (see _translate_slot_data/_build_bridge_db).
        self.gold_count: int = 0
        self.incoming_log: typing.List[dict] = []
        # Set once _maybe_send_goal has sent StatusUpdate(CLIENT_GOAL) -- guards against
        # resending it every poll tick, mirroring Northgard's own ctx.finished_game.
        self.goal_sent: bool = False
        # How many entries of self.items_received (the base CommonContext's own complete,
        # already-deduplicated received-items list) have already been folded into
        # incoming_log -- since ReceivedItems can legitimately redeliver the full list from
        # index 0 on every reconnect, unlocked_zones/level_item_counts are recomputed from
        # scratch off the full list every time (see on_package), but incoming_log should
        # only grow by the genuinely-new tail, not replay the same history again.
        self._incoming_log_processed_count: int = 0

        # Used to skip redundant bridge-file writes -- see MIN_BRIDGE_WRITE_INTERVAL_SECONDS.
        self._last_bridge_fingerprint: typing.Optional[tuple] = None
        self._last_bridge_write_time: float = 0.0

        # Level numbers most recently read from the addon's pendingChecks -- cached here
        # (rather than only acted on inside _handle_addon_file_change) so a poll tick that
        # ISN'T a file-change tick still retries sending these until the server acks them.
        # This matters because a send attempt can race the connection itself: connecting
        # (via /connect, or the GUI) doesn't happen synchronously, so a send attempted
        # before ctx.server is actually set would otherwise silently do nothing and never
        # be retried -- confirmed live (see bridge_loop's comment below).
        self._cached_pending_levels: typing.List[int] = []

    def make_gui(self):
        ui = super().make_gui()
        ui.base_title = "Archipelago WoW Leveling Client"
        return ui

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict):
        if cmd == "RoomInfo":
            self.seed_name = args.get("seed_name")
        elif cmd == "Connected":
            self.slot_data = args.get("slot_data", {}) or {}
            # Reset on every (re)connect, not just at ctx construction: reconnecting the
            # same running client to a DIFFERENT slot/room reuses this same context
            # object, so without this, a goal already sent for a previous slot this
            # session would permanently block _maybe_send_goal from ever re-checking the
            # new slot's own goal -- confirmed live (this is exactly what happened testing
            # a 2-slot room from one client: goaled slot 1, reconnected as slot 2, slot
            # 2's Gold Hunt was fully met but never sent because goal_sent was still True
            # from slot 1).
            self.goal_sent = False
        elif cmd == "ConnectionRefused":
            logger.warning(f"[WoW Leveling] Server refused the connection: {args.get('errors')}")
        elif cmd == "ReceivedItems":
            # entry is a NetUtils.NetworkItem (NamedTuple) -- attribute access, not .get()
            # (same pattern as NorthgardClient's ReceivedItems handling). self.items_received
            # is the base CommonContext's own complete, already-deduplicated list (it can
            # legitimately be resent in full from index 0 on every reconnect) -- unlocked_zones
            # /level_item_counts are recomputed from that full list every time rather than
            # incrementally mutated off args["items"], since level_item_counts is a running
            # count, not a set: incrementing it off a possible full resend would double-count.
            self.unlocked_zones = set()
            self.level_item_counts = {}
            self.gold_count = 0
            for entry in self.items_received:
                name = _ITEM_ID_TO_NAME.get(entry.item, f"Item #{entry.item}")
                bucket = _classify_item(name)
                if bucket == "zone":
                    self.unlocked_zones.add(name)
                elif bucket == "level_item":
                    self.level_item_counts[name] = self.level_item_counts.get(name, 0) + 1
                elif bucket == "gold":
                    self.gold_count += 1

            # incoming_log is a plain activity feed though -- only append the genuinely new
            # tail of self.items_received, not the whole list again, using
            # _incoming_log_processed_count to remember how far it's already caught up to.
            # Guarded against a shorter list than last time (e.g. reconnecting to a
            # different room reset self.items_received) -- without this, a stale, too-large
            # processed_count would silently skip that new room's entire history forever.
            if len(self.items_received) < self._incoming_log_processed_count:
                self._incoming_log_processed_count = 0
            for entry in self.items_received[self._incoming_log_processed_count:]:
                name = _ITEM_ID_TO_NAME.get(entry.item, f"Item #{entry.item}")
                player_name = self.player_names.get(entry.player, f"Player {entry.player}")
                self.incoming_log.append({"ts": int(time.time()), "itemName": name, "fromPlayer": player_name})
            self._incoming_log_processed_count = len(self.items_received)
            if len(self.incoming_log) > MAX_INCOMING_LOG:
                self.incoming_log = self.incoming_log[-MAX_INCOMING_LOG:]


async def _handle_addon_file_change(ctx: WoWLevelingContext, addon_path: str) -> None:
    try:
        with open(addon_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        db = parse_saved_variables(text, ADDON_DB_VAR)
    except (OSError, LuaParseError) as e:
        logger.warning(f"[WoW Leveling] Couldn't parse {addon_path}: {e}")
        return
    if not isinstance(db, dict):
        logger.warning(f"[WoW Leveling] {addon_path} didn't contain a table for {ADDON_DB_VAR}")
        return

    # Cache pendingChecks; actually sending is done unconditionally every poll tick by
    # _flush_pending_checks (called from bridge_loop), not here -- see its docstring for why.
    pending_levels: typing.List[int] = []
    for level in lua_table_to_list(db.get("pendingChecks")):
        try:
            pending_levels.append(int(level))
        except (TypeError, ValueError):
            continue
    ctx._cached_pending_levels = pending_levels

    await _flush_pending_checks(ctx)


async def _flush_pending_checks(ctx: WoWLevelingContext) -> None:
    """Sends LocationChecks for every level in ctx._cached_pending_levels not yet in
    ctx.checked_locations. Called every bridge_loop tick (not just on a file-change tick)
    specifically so a send attempt that loses the race against an in-progress connect (see
    _cached_pending_levels' field comment) gets retried on the next tick instead of being
    silently dropped for the rest of the session -- confirmed live: without this, the very
    first sync after connecting could send zero checks even though pendingChecks was
    non-empty, because ctx.connect() had not finished establishing ctx.server yet."""
    if not ctx._cached_pending_levels or ctx.server is None:
        return

    location_ids: typing.List[int] = []
    for level_int in ctx._cached_pending_levels:
        # Location names are zero-padded ("Level 01".."Level 90", see Locations.py's
        # _RAW_LOCATIONS) -- must match exactly, or a real pending level would silently
        # never be found.
        loc_id = _LOCATION_NAME_TO_ID.get(f"Level {level_int:02d}")
        if loc_id is None:
            continue  # not a recognized location name for this game -- skip rather than guess
        if loc_id in ctx.checked_locations:
            continue  # already acked by the server -- resending is safe but pointless
        location_ids.append(loc_id)

    if location_ids:
        await ctx.send_msgs([{"cmd": "LocationChecks", "locations": location_ids}])


def _acked_levels(ctx: WoWLevelingContext) -> typing.Dict[int, bool]:
    """Every level the AP server currently reports as checked for this slot, translated
    from location ids back to level numbers via Locations.py's own table -- this is the
    authoritative truth the addon is meant to trust over its own pendingChecks bookkeeping
    (see addon/ArchipelagoWoW/Core.lua's Reconcile, which does exactly that)."""
    acked: typing.Dict[int, bool] = {}
    for loc_id in ctx.checked_locations:
        name = _LOCATION_ID_TO_NAME.get(loc_id)
        if not name:
            continue
        m = _LEVEL_LOCATION_RE.match(name)
        if m:
            acked[int(m.group(1))] = True
    return acked


async def _maybe_send_goal(ctx: WoWLevelingContext) -> None:
    """Detects whether the chosen goal has actually been met in-game and, the first time it
    has, checks the corresponding location -- "Leveling" or "Gold Hunt" (see Locations.py) --
    and sends StatusUpdate(CLIENT_GOAL), the same pattern Northgard's own client uses for its
    "Chapter 07" goal check (NorthgardClient.py's save_watcher). Unlike the World's separate
    id=None "Victory" event location (never delivered over the network to any client, so
    there is nothing to react to there), "Leveling"/"Gold Hunt" are ordinary real locations
    with real ids -- so, exactly like any other location, nothing marks them checked unless
    a client actually sends a LocationChecks for them. Without this function that never
    happens for either one, and the world could never actually be "won" in a live game even
    after truly reaching max level or collecting enough Gold -- confirmed missing entirely
    until this was added."""
    if ctx.goal_sent or ctx.server is None:
        return

    slot_data = ctx.slot_data or {}
    goal = slot_data.get("goal")

    location_name: typing.Optional[str] = None
    if goal == _GoalOption.option_leveling:
        max_level = slot_data.get("max_level")
        if isinstance(max_level, int) and _acked_levels(ctx).get(max_level):
            location_name = _LEVELING_LOCATION_NAME
    elif goal == _GoalOption.option_gold_hunt:
        amount = slot_data.get("gold_hunt_amount")
        if isinstance(amount, int) and amount > 0 and ctx.gold_count >= amount:
            location_name = _GOLD_HUNT_LOCATION_NAME

    if location_name is None:
        return  # goal not met yet

    loc_id = _LOCATION_NAME_TO_ID.get(location_name)
    if loc_id is not None and loc_id not in ctx.checked_locations:
        await ctx.send_msgs([{"cmd": "LocationChecks", "locations": [loc_id]}])

    ctx.goal_sent = True
    logger.info("[WoW Leveling] Goal complete! Sending StatusUpdate to the server.")
    await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])


def _build_bridge_db(ctx: WoWLevelingContext) -> dict:
    return {
        "connected": ctx.server is not None,
        "lastSyncEpoch": int(time.time()),
        "slotData": _translate_slot_data(ctx.slot_data or {}, ctx.seed_name),
        "ackedLevels": _acked_levels(ctx),
        "unlockedZones": {name: True for name in sorted(ctx.unlocked_zones)},
        "levelItems": dict(sorted(ctx.level_item_counts.items())),
        "currentLevelCap": _current_level_cap(ctx.level_item_counts),
        "goldCount": ctx.gold_count,
        "incoming": list(ctx.incoming_log[-MAX_INCOMING_LOG:]),
    }


def _write_bridge_file(ctx: WoWLevelingContext, addon_path: str) -> None:
    bridge_path = _bridge_sv_path_for(addon_path)
    text = dumps_lua_assignment(BRIDGE_DB_VAR, _build_bridge_db(ctx))
    try:
        os.makedirs(os.path.dirname(bridge_path), exist_ok=True)
        tmp_path = bridge_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp_path, bridge_path)  # atomic on Windows for same-volume renames
    except OSError as e:
        logger.warning(f"[WoW Leveling] Couldn't write {bridge_path}: {e}")


def _bridge_db_fingerprint(ctx: WoWLevelingContext) -> tuple:
    """Everything in _build_bridge_db that the addon actually displays, EXCLUDING
    lastSyncEpoch (which is always "different" by definition) -- used by bridge_loop to
    decide whether a write would actually change anything on disk. See
    MIN_BRIDGE_WRITE_INTERVAL_SECONDS for why avoiding a no-op write matters."""
    return (
        ctx.server is not None,
        tuple(sorted(_acked_levels(ctx).items())),
        tuple(sorted(ctx.unlocked_zones)),
        tuple(sorted(ctx.level_item_counts.items())),
        ctx.gold_count,
        len(ctx.incoming_log),
    )


def _maybe_write_bridge_file(ctx: WoWLevelingContext, addon_path: str) -> None:
    """Writes the bridge file only when its content actually changed since the last
    write, or MIN_BRIDGE_WRITE_INTERVAL_SECONDS has passed regardless (so lastSyncEpoch
    doesn't go stale during an idle period) -- rather than unconditionally on every single
    poll tick, which was pure disk-write overhead for no benefit (see
    MIN_BRIDGE_WRITE_INTERVAL_SECONDS -- this is unrelated to the client-close hang, which
    was a missing timeout on shutdown itself; see SHUTDOWN_TIMEOUT_SECONDS)."""
    fingerprint = _bridge_db_fingerprint(ctx)
    now = time.time()
    if fingerprint == ctx._last_bridge_fingerprint and (now - ctx._last_bridge_write_time) < MIN_BRIDGE_WRITE_INTERVAL_SECONDS:
        return
    ctx._last_bridge_fingerprint = fingerprint
    ctx._last_bridge_write_time = now
    _write_bridge_file(ctx, addon_path)


async def bridge_loop(ctx: WoWLevelingContext) -> None:
    while not ctx.exit_event.is_set():
        try:
            if ctx.wow_install_dir:
                addon_path = _resolve_active_addon_sv(ctx)
                if addon_path is not None:
                    ctx.active_addon_sv_path = addon_path
                    try:
                        mtime = os.path.getmtime(addon_path)
                    except OSError:
                        mtime = ctx._last_addon_sv_mtime
                    if mtime != ctx._last_addon_sv_mtime:
                        ctx._last_addon_sv_mtime = mtime
                        await _handle_addon_file_change(ctx, addon_path)
                    else:
                        # Not a file-change tick, but still retry any not-yet-acked cached
                        # pending levels -- see _flush_pending_checks' docstring.
                        await _flush_pending_checks(ctx)
                    # Every tick, not just file-change ticks: the goal can become met purely
                    # from server-side activity (a Gold item landing pushes gold_count over
                    # the Gold Hunt amount) with no addon-side file change involved at all.
                    await _maybe_send_goal(ctx)
                    # Checked every tick (cheap), but only actually writes to disk when
                    # something changed or MIN_BRIDGE_WRITE_INTERVAL_SECONDS has passed --
                    # see _maybe_write_bridge_file's docstring for why unconditional writes
                    # here were a real problem.
                    _maybe_write_bridge_file(ctx, addon_path)
        except Exception:
            logger.exception("[WoW Leveling] bridge_loop iteration failed")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def main(args) -> None:
    ctx = WoWLevelingContext(args.connect, args.password)
    ctx.wow_install_dir = _resolve_wow_install_dir()
    ctx.pinned_character = _load_config().get("pinned_character") or None
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    if gui_enabled:
        ctx.run_gui()
    ctx.run_cli()

    watcher_task = asyncio.create_task(bridge_loop(ctx), name="WoWLevelingBridgeWatcher")

    await ctx.exit_event.wait()
    ctx.server_address = None

    # Absolute backstop, armed the instant the window is asked to close: if this process is
    # still alive after SHUTDOWN_TIMEOUT_SECONDS, kill it immediately, full stop. This has to
    # be a real OS thread, not an asyncio-level timeout (asyncio.wait_for/wait were tried
    # first and confirmed live to still take the *entire* bounded duration, ~15s, and leave
    # the window "Not Responding" throughout) -- asyncio's own timers run on the very same
    # thread as the code they're timing out, so a genuinely blocking synchronous call (a
    # stuck file open(), a socket call with no async cancellation point) starves the timeout
    # callback exactly as much as it starves everything else. A watchdog on its own thread
    # keeps running regardless (blocking C calls release the GIL while they wait), so it's
    # the only way to guarantee the window actually disappears on schedule no matter what
    # kind of hang caused this. os._exit(), not sys.exit(): skips atexit/thread-join/asyncio
    # finalization entirely, which is the point -- any of those could be the very thing
    # that's stuck.
    watchdog = threading.Timer(SHUTDOWN_TIMEOUT_SECONDS, os._exit, args=(1,))
    watchdog.daemon = True
    watchdog.start()

    # Everything below is best-effort now that the watchdog guarantees an upper bound --
    # cancel() is fired and NOT awaited (awaiting it would just reintroduce the same
    # thread-starvation problem the watchdog exists to route around), and the final write and
    # disconnect are wrapped so an exception in either still lets the other run.
    watcher_task.cancel()

    # One last write on a clean shutdown so the addon shows "Not connected" on its next
    # login/reload, rather than being stuck showing whatever "connected" was true as of
    # the last poll tick before this process closed -- SavedVariables only reflect whatever
    # was last written, and nothing else will ever correct it once this process exits.
    # Explicitly force ctx.server to None (rather than assume the base client already cleared
    # it by this point) so _build_bridge_db's "connected" is unambiguously False here. NOTE:
    # this can't help on a forceful kill/crash (including the watchdog firing) -- only a
    # clean shutdown that finishes before the deadline runs this.
    if ctx.active_addon_sv_path:
        ctx.server = None
        try:
            _write_bridge_file(ctx, ctx.active_addon_sv_path)
        except Exception:
            logger.exception("[WoW Leveling] Final bridge write on shutdown failed")

    try:
        await ctx.shutdown()
    except Exception:
        logger.exception("[WoW Leveling] ctx.shutdown() failed")

    watchdog.cancel()


def launch() -> None:
    import colorama

    parser = get_base_parser(description="WoW Leveling Client")
    cli_args = sys.argv[1:]
    # The Launcher's "Component -- args" invocation prepends the component's own display
    # name and a literal "--" separator ahead of any real args (e.g. `ArchipelagoLauncher.exe
    # "WoW Leveling Client" -- --nogui host:port`); left in place, argparse would treat
    # everything after "--" as forced-positional-only and silently swallow flags like
    # --nogui. Stripped the same way NorthgardClient.launch() strips "Northgard Client"/"--".
    # The exact string below was confirmed against __init__.py's actual
    # Component("WoW Leveling Client", ...) registration, not guessed.
    if "WoW Leveling Client" in cli_args:
        cli_args.remove("WoW Leveling Client")
    if "--" in cli_args:
        cli_args.remove("--")
    parsed_args, _ = parser.parse_known_args(args=cli_args)

    colorama.init()
    asyncio.run(main(parsed_args))
    colorama.deinit()


if __name__ == "__main__":
    launch()
