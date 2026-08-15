from typing import Callable

from BaseClasses import CollectionState

from .Items import GOLD_ITEM_NAME, PROGRESSIVE_LEVELS_ITEM_NAME, item_table

# category name (e.g. "Zones 10-20") -> every item name tagged with it. Built off the full
# item table regardless of what a given seed's option choices actually pooled -- an item
# that was filtered out of this seed's pool simply can never be "had", so including it here
# is harmless and keeps this independent of the faction/expansion/cataclysm filtering that
# happens in __init__.py's create_items.
ZONE_ITEMS_BY_CATEGORY: dict[str, list[str]] = {}
for _name, _data in item_table.items():
    for _category in _data.category:
        if _category.startswith("Zones ") and _category != "Zones":
            ZONE_ITEMS_BY_CATEGORY.setdefault(_category, []).append(_name)

# bracket region name -> (Maximum Level item, equivalent Progressive Levels count,
#                         zone category covering that bracket, expansion-starting zone(s)
#                         required ONLY when Easier Transitions is enabled).
#
# NOTE on faithfulness: the ORIGINAL Manual-based WorldofWarcraft-Leveling project (a
# separate, sibling repo -- not anything in this one) encoded this exact same logic as a
# boolean expression in Manual's own mini-language, in ITS data/regions.json, e.g. for
# "Levels 61-70":
#   ({YamlDisabled(easier_transitions)} AND (|Maximum Level 70| OR |Progressive Levels:6|)
#       AND |@Zones 60-70:1|)
#   OR ({YamlEnabled(easier_transitions)} AND (|Maximum Level 70| OR |Progressive Levels:6|)
#       AND |@Zones 60-70:2| AND |Hellfire Peninsula (58-63)|)
# Rather than writing a generic parser for that mini-language for just 9 regions, the same
# structure is hand-encoded below (bracket_reachable()) and driven by this table -- notably,
# the specific expansion-starting zone (e.g. Hellfire Peninsula) is only ever required in the
# Easier-Transitions-enabled branch, never in the default branch. If this table ever needs
# changing, re-derive it from the original project's data/regions.json requires strings
# rather than guessing -- there is no copy of that file in this repo.
BRACKET_REQUIREMENTS: dict[str, tuple[str, int, str, list[str]]] = {
    "Levels 11-20": ("Maximum Level 20", 1, "Zones 10-20", []),
    "Levels 21-30": ("Maximum Level 30", 2, "Zones 20-30", []),
    "Levels 31-40": ("Maximum Level 40", 3, "Zones 30-40", []),
    "Levels 41-50": ("Maximum Level 50", 4, "Zones 40-50", []),
    "Levels 51-60": ("Maximum Level 60", 5, "Zones 50-60", []),
    "Levels 61-70": ("Maximum Level 70", 6, "Zones 60-70", ["Hellfire Peninsula (58-63)"]),
    "Levels 71-80": ("Maximum Level 80", 7, "Zones 70-80", ["Borean Tundra (68-72)", "Howling Fjord (68-72)"]),
    "Levels 81-85": ("Maximum Level 85", 8, "Zones 80-85", ["Mount Hyjal (80-82)", "Vashj'ir (80-82)"]),
    "Levels 86-90": ("Maximum Level 90", 9, "Zones 85-90", ["The Jade Forest (85-86)"]),
}


def bracket_reachable(state: CollectionState, world, bracket_name: str) -> bool:
    max_level_item, progressive_count, zone_category, expansion_zones = BRACKET_REQUIREMENTS[bracket_name]
    player = world.player

    if not (
        state.has(max_level_item, player)
        or state.has(PROGRESSIVE_LEVELS_ITEM_NAME, player, progressive_count)
    ):
        return False

    easier = world.options.easier_transitions.value == world.options.easier_transitions.option_true
    zones_needed = 2 if easier else 1
    zone_items = ZONE_ITEMS_BY_CATEGORY.get(zone_category, [])
    if not state.has_from_list_unique(zone_items, player, zones_needed):
        return False

    if easier and expansion_zones and not state.has_any(expansion_zones, player):
        return False

    return True


def make_bracket_rule(world, bracket_name: str) -> Callable[[CollectionState], bool]:
    return lambda state: bracket_reachable(state, world, bracket_name)


def make_leveling_rule(world, final_bracket_name: str) -> Callable[[CollectionState], bool]:
    # The "Leveling" goal region requires exactly the same condition as crossing into the
    # bracket that contains the chosen expansion's max level -- in the original Manual
    # project, its "Leveling" region's "requires" string branched per
    # {YamlCompare(expansion == N)} and duplicated that bracket's own requirement in each
    # branch; here that's just calling bracket_reachable() with the final bracket name.
    return lambda state: bracket_reachable(state, world, final_bracket_name)


def make_gold_hunt_rule(world) -> Callable[[CollectionState], bool]:
    return lambda state: state.has(GOLD_ITEM_NAME, world.player, world.options.gold_hunt_amount.value)
