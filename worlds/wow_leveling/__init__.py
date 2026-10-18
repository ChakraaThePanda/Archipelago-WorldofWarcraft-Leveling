import logging
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
    starting_level,
)
from .Locations import (
    VICTORY_EVENT_LOCATION_NAME,
    WoWLevelingLocation,
    location_table,
)
from .Options import POST_CATACLYSM_FORCED_ABOVE_LEVEL, WoWLevelingOptions
from .Regions import BRACKET_MAX_LEVEL, GOLD_HUNT_REGION, LEVEL_BRACKETS, LEVELING_REGION
from .Rules import BRACKET_REQUIREMENTS, make_bracket_rule, make_gold_hunt_rule, make_leveling_rule


def launch_client(*args) -> None:
    # *args exists only so this matches the signature Component.run() always calls
    # (self.func(*args) -- args is non-empty when the Launcher is invoked with extra CLI
    # tokens after "--", e.g. a url). Not forwarded further: the client reads sys.argv
    # itself (see WoWLevelingClient.launch).
    from CommonClient import gui_enabled
    from .WoWLevelingClient import launch as Main

    if gui_enabled:
        launch_subprocess(Main, name="WoW Leveling Client")
    else:
        Main()


icon_paths["wow_leveling"] = f"ap:{__name__}/data/wow_icon.png"
components.append(Component("WoW Leveling Client", func=launch_client, component_type=Type.CLIENT, icon="wow_leveling"))


def _bracket_count_for_max_level(max_level: int) -> int:
    # How many brackets (from the start of Regions.LEVEL_BRACKETS) it takes to reach
    # max_level: 25 -> 3 ("Levels 01-10" through "Levels 21-30", the last one only partly
    # used), 60 -> 6, 90 -> all 10.
    for index, bracket_max in enumerate(BRACKET_MAX_LEVEL):
        if max_level <= bracket_max:
            return index + 1
    return len(BRACKET_MAX_LEVEL)


def _required_zone_categories(bracket_count: int) -> set[str]:
    # The "Zones N-M" categories bracket_reachable() (Rules.py) actually checks for this
    # seed's brackets. A zone tagged only with categories outside this set can never
    # matter to logic (e.g. a "Zones 20-30" zone in a max-level-20 seed), so it's left out.
    return {BRACKET_REQUIREMENTS[bracket][2] for bracket in LEVEL_BRACKETS[1:bracket_count]}


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
    """Level a World of Warcraft character up to the level you choose, or race to find a
    stash of Gold instead. Every level up sends a check, and the zones you can quest in and
    the level caps you can pass are unlocked by items from the multiworld."""

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

        max_level = self.options.max_level.value
        brackets = LEVEL_BRACKETS[:_bracket_count_for_max_level(max_level)]

        regions: dict[str, Region] = {}
        for bracket in brackets:
            region = Region(bracket, player, multiworld)
            multiworld.regions.append(region)
            regions[bracket] = region

        gold_hunt_region = Region(GOLD_HUNT_REGION, player, multiworld)
        leveling_region = Region(LEVELING_REGION, player, multiworld)
        multiworld.regions += [gold_hunt_region, leveling_region]

        # The level-bracket chain: Menu -> Levels 01-10 -> Levels 11-20 -> ... -> the last
        # bracket max_level falls in. "Levels 01-10" has no requirement of its own.
        menu.connect(regions[brackets[0]])
        for previous_name, next_name in zip(brackets, brackets[1:]):
            entrance = regions[previous_name].connect(regions[next_name])
            set_rule(entrance, make_bracket_rule(self, next_name))

        # The two always-reachable ("starting") goal regions, gated directly off Menu.
        gold_hunt_entrance = menu.connect(gold_hunt_region)
        set_rule(gold_hunt_entrance, make_gold_hunt_rule(self))

        leveling_entrance = menu.connect(leveling_region)
        set_rule(leveling_entrance, make_leveling_rule(self, brackets[-1]))

        # Level-up locations, trimmed to max_level, plus (with include_achievements) the
        # Statistics milestones whose bracket this seed reaches.
        include_achievements = bool(self.options.include_achievements.value)
        for name, data in location_table.items():
            if data.stat_id is None:
                if int(name.split(" ")[1]) > max_level:
                    continue
            elif not include_achievements or data.region not in regions:
                continue
            region = regions[data.region]
            region.locations.append(WoWLevelingLocation(player, name, data.id, region))

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

        max_level = options.max_level.value
        bracket_count = _bracket_count_for_max_level(max_level)
        allowed_level_items = SEQUENTIAL_LEVEL_ITEMS[: bracket_count - 1]
        required_zone_categories = _required_zone_categories(bracket_count)

        cata_state_tag = (
            "Pre-Cataclysm"
            if options.pre_or_post_cataclysm.value == options.pre_or_post_cataclysm.option_pre_cataclysm
            else "Post-Cataclysm"
        )
        if max_level > POST_CATACLYSM_FORCED_ABOVE_LEVEL:  # Cataclysm/MoP always assume a changed world
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
                # One copy per bracket boundary up to the bracket max_level falls in.
                # Nothing requires "Progressive Levels" past that.
                count = bracket_count - 1
            elif name in SEQUENTIAL_LEVEL_ITEMS:
                if options.level_items.value == options.level_items.option_progressive:
                    continue
                if name not in allowed_level_items:
                    continue

            # Zones and Dungeons are both restricted to the ones starting at or below
            # max_level, and (for the zones the Cataclysm reshaped) to the chosen
            # Pre/Post-Cataclysm state.
            if "Zones" in categories or "Dungeons" in categories:
                if starting_level(name) > max_level:
                    continue
                if "Zones" in categories and not required_zone_categories.intersection(categories):
                    continue
                if ("Pre-Cataclysm" in categories or "Post-Cataclysm" in categories) and cata_state_tag not in categories:
                    continue
                # And to the chosen faction, for the zones/dungeons that are faction-locked
                # in-game -- otherwise bracket_reachable() (Rules.py) could be satisfied by
                # zone items the player can never actually quest in, since it only checks
                # for *any* N unique zone items in the bracket's category, not that they're
                # actually enterable by this faction. Every bracket retains at least 2
                # same-faction-or-neutral zone items after this filter (verified across all
                # max_level/cataclysm-state/faction combinations), comfortably above the
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

        # Low max levels have few "Level NN" locations, so the progression items can
        # still overflow them (e.g. max_level 11 with Gold Hunt: 11 locations for 10 Gold,
        # a level item, and every 10-20 zone). Drop zones logic doesn't need first, then
        # Gold as a last resort.
        if len(pool) > total_locations:
            pool = self._trim_surplus_zones(pool, len(pool) - total_locations, bracket_count)
        if len(pool) > total_locations:
            excess = len(pool) - total_locations
            gold_items = [item for item in pool if item.name == GOLD_ITEM_NAME]
            if excess >= len(gold_items):
                raise Exception(f"{self.player_name}: max_level {max_level} is too low to fit this seed's items")
            for item in gold_items[:excess]:
                pool.remove(item)
            options.gold_hunt_amount.value -= excess
            logging.warning(
                f"{self.player_name}: lowered gold_hunt_amount to {options.gold_hunt_amount.value} "
                f"so it fits in max_level {max_level}'s locations"
            )

        while len(pool) < total_locations:
            pool.append(self.create_item(FILLER_ITEM_NAME))

        self.multiworld.itempool += pool

    def _trim_surplus_zones(
        self, pool: list[WoWLevelingItem], excess: int, bracket_count: int
    ) -> list[WoWLevelingItem]:
        """Removes up to `excess` random zone items from the pool, but never one that
        bracket_reachable() (Rules.py) still needs: each required bracket keeps
        zones_needed zones of its category, plus one of its expansion-starting zones when
        Easier Transitions is on."""
        easier = self.options.easier_transitions.value == self.options.easier_transitions.option_true
        zones_needed = 2 if easier else 1
        requirements = [BRACKET_REQUIREMENTS[bracket] for bracket in LEVEL_BRACKETS[1:bracket_count]]

        remaining_names = {item.name for item in pool}

        def still_satisfied(names: set[str]) -> bool:
            for _, _, zone_category, expansion_zones in requirements:
                if sum(1 for name in names if zone_category in item_table[name].category) < zones_needed:
                    return False
                if easier and expansion_zones and not names.intersection(expansion_zones):
                    return False
            return True

        candidates = [item for item in pool if "Zones" in item_table[item.name].category]
        self.random.shuffle(candidates)
        removed: list[WoWLevelingItem] = []
        for item in candidates:
            if len(removed) >= excess:
                break
            if still_satisfied(remaining_names - {item.name}):
                remaining_names.discard(item.name)
                removed.append(item)
        removed_ids = {id(item) for item in removed}
        return [item for item in pool if id(item) not in removed_ids]

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has(VICTORY_ITEM_NAME, self.player)

    def fill_slot_data(self) -> dict[str, Any]:
        return {
            "max_level": self.options.max_level.value,
            "goal": self.options.goal.value,
            "faction": self.options.faction.value,
            "gold_hunt_amount": self.options.gold_hunt_amount.value,
        }
