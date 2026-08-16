from typing import Any

from BaseClasses import ItemClassification, Region, Tutorial
from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import set_rule
from worlds.LauncherComponents import Component, Type, components, icon_paths, launch_subprocess

from .Items import (
    ALLIANCE_ITEM_NAME,
    CATEGORY_YAML_GATES,
    FILLER_ITEM_NAME,
    GOLD_ITEM_NAME,
    HORDE_ITEM_NAME,
    PROGRESSIVE_LEVELS_ITEM_NAME,
    SEQUENTIAL_LEVEL_ITEMS,
    VICTORY_ITEM_NAME,
    WoWLevelingItem,
    item_name_groups,
    item_table,
)
from .Locations import (
    GOLD_HUNT_LOCATION_NAME,
    LEVELING_LOCATION_NAME,
    VICTORY_EVENT_LOCATION_NAME,
    WoWLevelingLocation,
    location_table,
)
from .Options import EXPANSION_CATACLYSM, EXPANSION_NAMES, WoWLevelingOptions
from .Regions import BRACKET_MAX_LEVEL, GOLD_HUNT_REGION, LEVEL_BRACKETS, LEVELING_REGION
from .Rules import make_bracket_rule, make_gold_hunt_rule, make_leveling_rule


def launch_client(*args) -> None:
    # *args exists only so this matches the signature Component.run() always calls
    # (self.func(*args) -- args is non-empty when the Launcher is invoked with extra CLI
    # tokens after "--", e.g. a url). Not forwarded further: the client reads sys.argv
    # itself (see WoWLevelingClient.launch), same as Northgard's own launch_client.
    from CommonClient import gui_enabled
    from .WoWLevelingClient import launch as Main

    if gui_enabled:
        launch_subprocess(Main, name="WoW Leveling Client")
    else:
        Main()


icon_paths["wow_leveling"] = f"ap:{__name__}/data/wow_icon.png"
components.append(Component("WoW Leveling Client", func=launch_client, component_type=Type.CLIENT, icon="wow_leveling"))


def _bracket_count_for_expansion(expansion: int) -> int:
    # Vanilla (0) needs brackets through "Levels 51-60" (6 brackets); each further
    # expansion value unlocks exactly one more bracket, up to all 10 for Mists of
    # Pandaria (4) -- see Regions.BRACKET_MAX_LEVEL / Options.Expansion's own doc. Shared
    # by create_regions and fill_slot_data (the bridge client needs the same max_level to
    # know when the Leveling goal has actually been reached in-game) so the formula only
    # lives in one place.
    return 6 + expansion


class WoWLevelingWeb(WebWorld):
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up World of Warcraft Leveling for Archipelago multiworld play.",
        "English",
        "setup_en.md",
        "setup/en",
        ["Chakraa"],
    )]
    theme = "dirt"


class WoWLevelingWorld(World):
    """Level a World of Warcraft character from 1 up to the level cap of your chosen
    expansion -- or race to dig up a stash of Gold instead. Level-ups send checks; the
    zones you can quest in and the level caps you can cross are gated behind items found
    in the multiworld."""

    game = "World of Warcraft Leveling"
    author: str = "Chakraa"
    web = WoWLevelingWeb()

    options_dataclass = WoWLevelingOptions
    options: WoWLevelingOptions

    item_name_to_id = {name: data.code for name, data in item_table.items()}
    location_name_to_id = {name: data.id for name, data in location_table.items()}

    item_name_groups = item_name_groups

    def create_item(self, name: str) -> WoWLevelingItem:
        data = item_table[name]
        return WoWLevelingItem(name, data.classification, data.code, self.player)

    def create_regions(self) -> None:
        player = self.player
        multiworld = self.multiworld

        menu = Region("Menu", player, multiworld)
        multiworld.regions.append(menu)

        expansion = self.options.expansion.value
        bracket_count = _bracket_count_for_expansion(expansion)
        brackets = LEVEL_BRACKETS[:bracket_count]
        max_level = BRACKET_MAX_LEVEL[bracket_count - 1]

        regions: dict[str, Region] = {}
        for bracket in brackets:
            region = Region(bracket, player, multiworld)
            multiworld.regions.append(region)
            regions[bracket] = region

        gold_hunt_region = Region(GOLD_HUNT_REGION, player, multiworld)
        leveling_region = Region(LEVELING_REGION, player, multiworld)
        multiworld.regions += [gold_hunt_region, leveling_region]

        # The level-bracket chain: Menu -> Levels 01-10 -> Levels 11-20 -> ... -> the last
        # bracket this expansion reaches. "Levels 01-10" has no requirement of its own.
        menu.connect(regions[brackets[0]])
        for previous_name, next_name in zip(brackets, brackets[1:]):
            entrance = regions[previous_name].connect(regions[next_name])
            set_rule(entrance, make_bracket_rule(self, next_name))

        # The two always-reachable ("starting") goal regions, gated directly off Menu.
        gold_hunt_entrance = menu.connect(gold_hunt_region)
        set_rule(gold_hunt_entrance, make_gold_hunt_rule(self))

        leveling_entrance = menu.connect(leveling_region)
        set_rule(leveling_entrance, make_leveling_rule(self, brackets[-1]))

        # Level-up locations, trimmed to this expansion's max level.
        for name, data in location_table.items():
            if name in (LEVELING_LOCATION_NAME, GOLD_HUNT_LOCATION_NAME):
                continue
            level = int(name.split(" ")[1])
            if level > max_level:
                continue
            region = regions[data.region]
            region.locations.append(WoWLevelingLocation(player, name, data.id, region))

        # The two goal locations always exist, regardless of which `goal` was chosen --
        # only the completion condition (set_rules(), below) depends on that choice.
        leveling_data = location_table[LEVELING_LOCATION_NAME]
        leveling_region.locations.append(
            WoWLevelingLocation(player, LEVELING_LOCATION_NAME, leveling_data.id, leveling_region)
        )

        gold_hunt_data = location_table[GOLD_HUNT_LOCATION_NAME]
        gold_hunt_region.locations.append(
            WoWLevelingLocation(player, GOLD_HUNT_LOCATION_NAME, gold_hunt_data.id, gold_hunt_region)
        )

        # A locked "Victory" event, placed in whichever goal region matches the chosen
        # `goal` option -- reachable exactly when that region's own entrance rule is
        # satisfied, so it needs no additional access_rule of its own.
        victory_region = (
            leveling_region if self.options.goal.value == self.options.goal.option_leveling else gold_hunt_region
        )
        victory_location = WoWLevelingLocation(player, VICTORY_EVENT_LOCATION_NAME, None, victory_region)
        victory_location.place_locked_item(
            WoWLevelingItem(VICTORY_ITEM_NAME, ItemClassification.progression, None, player)
        )
        victory_region.locations.append(victory_location)

    def create_items(self) -> None:
        options = self.options

        expansion = options.expansion.value
        allowed_expansion_names = EXPANSION_NAMES[: expansion + 1]
        skipped_expansions = len(EXPANSION_NAMES) - len(allowed_expansion_names)

        cata_state_tag = (
            "Pre-Cataclysm"
            if options.pre_or_post_cataclysm.value == options.pre_or_post_cataclysm.option_pre_cataclysm
            else "Post-Cataclysm"
        )
        if expansion >= EXPANSION_CATACLYSM:  # Cataclysm/MoP always assume a changed world
            cata_state_tag = "Post-Cataclysm"

        goal_is_gold_hunt = options.goal.value == options.goal.option_gold_hunt
        gold_amount = options.gold_hunt_amount.value

        pool: list[WoWLevelingItem] = []
        class_candidates: list[str] = []

        for name, data in item_table.items():
            categories = data.category

            # Gold only exists for the Gold Hunt goal, trimmed to gold_hunt_amount; for the
            # Leveling goal none of it is placed at all.
            if name == GOLD_ITEM_NAME:
                if goal_is_gold_hunt:
                    pool.extend(self.create_item(name) for _ in range(gold_amount))
                continue

            # Class items never go in the pool. If randomize_class is on, exactly one
            # eligible class (respecting Monk's Post-Cataclysm-only restriction) is
            # precollected once the whole table has been scanned, below.
            if "Class" in categories:
                if options.randomize_class.value:
                    if "Post-Cataclysm" in categories and cata_state_tag != "Post-Cataclysm":
                        continue
                    class_candidates.append(name)
                continue

            # Faction items: the matching one is precollected instead of pooled; the
            # opposing one is dropped entirely.
            if name == ALLIANCE_ITEM_NAME:
                if options.faction.value == options.faction.option_alliance:
                    self.multiworld.push_precollected(self.create_item(name))
                continue
            if name == HORDE_ITEM_NAME:
                if options.faction.value == options.faction.option_horde:
                    self.multiworld.push_precollected(self.create_item(name))
                continue

            count = data.count
            if name == PROGRESSIVE_LEVELS_ITEM_NAME:
                if options.level_items.value == options.level_items.option_sequential:
                    continue
                # One copy per bracket boundary for expansions beyond the chosen one is
                # simply never needed (nothing requires "Progressive Levels" past the
                # bracket that reaches this expansion's max level).
                count = max(count - skipped_expansions, 0)
            elif name in SEQUENTIAL_LEVEL_ITEMS:
                if options.level_items.value == options.level_items.option_progressive:
                    continue
                if not any(expansion_name in categories for expansion_name in allowed_expansion_names):
                    continue

            # Zones and Dungeons are both restricted to the chosen expansion's content, and
            # (for the zones the Cataclysm reshaped) to the chosen Pre/Post-Cataclysm state.
            if "Zones" in categories or "Dungeons" in categories:
                if not any(expansion_name in categories for expansion_name in allowed_expansion_names):
                    continue
                if ("Pre-Cataclysm" in categories or "Post-Cataclysm" in categories) and cata_state_tag not in categories:
                    continue
                # And to the chosen faction, for the zones/dungeons that are faction-locked
                # in-game -- otherwise bracket_reachable() (Rules.py) could be satisfied by
                # zone items the player can never actually quest in, since it only checks
                # for *any* N unique zone items in the bracket's category, not that they're
                # actually enterable by this faction. Every bracket retains at least 3
                # same-faction-or-neutral zone items after this filter (verified across all
                # expansion/cataclysm-state/faction combinations), comfortably above the
                # max zones_needed of 2 (Easier Transitions).
                if "Alliance" in categories and options.faction.value != options.faction.option_alliance:
                    continue
                if "Horde" in categories and options.faction.value != options.faction.option_horde:
                    continue

            # Generic category -> yaml-option gating (currently just Dungeons -> include_dungeons).
            gated_options = [option for category in categories for option in CATEGORY_YAML_GATES.get(category, [])]
            if gated_options and not all(getattr(options, option_name).value for option_name in gated_options):
                continue

            pool.extend(self.create_item(name) for _ in range(count))

        if options.randomize_class.value and class_candidates:
            chosen_class = self.random.choice(class_candidates)
            self.multiworld.push_precollected(self.create_item(chosen_class))

        total_locations = len(self.multiworld.get_unfilled_locations(self.player))

        if len(pool) > total_locations:
            # Trim trailing filler-classified items first (e.g. dungeons, if included) to
            # fit -- progression/useful items are never trimmed. Built as a single reversed
            # pass instead of repeated del(pool[index]) (each an O(n) shift) so this stays
            # O(n) instead of O(n * excess).
            excess = len(pool) - total_locations
            trimmed: list[WoWLevelingItem] = []
            for item in reversed(pool):
                if excess > 0 and item.classification == ItemClassification.filler:
                    excess -= 1
                    continue
                trimmed.append(item)
            trimmed.reverse()
            pool = trimmed

        while len(pool) < total_locations:
            pool.append(self.create_item(FILLER_ITEM_NAME))

        self.multiworld.itempool += pool

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has(VICTORY_ITEM_NAME, self.player)

    def fill_slot_data(self) -> dict[str, Any]:
        bracket_count = _bracket_count_for_expansion(self.options.expansion.value)
        return {
            "expansion": self.options.expansion.value,
            "goal": self.options.goal.value,
            "faction": self.options.faction.value,
            "gold_hunt_amount": self.options.gold_hunt_amount.value,
            # The Leveling goal's actual win condition, for the client to check against
            # (see WoWLevelingClient._maybe_send_goal): reaching this level in-game --
            # i.e. the "Level NN" location for it getting checked -- means the goal is
            # met. Same bracket_count formula create_regions uses, so this always matches
            # the real max level for whichever expansion was chosen.
            "max_level": BRACKET_MAX_LEVEL[bracket_count - 1],
        }
