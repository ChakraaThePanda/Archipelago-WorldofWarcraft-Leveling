from dataclasses import dataclass

from BaseClasses import Location

# Deliberately distinct from Items.BASE_ID so item and location IDs never collide.
BASE_ID = 39280000
_LOCATION_ID_OFFSET = 1000

# Every location this world can create, hardcoded here (not loaded from JSON/a data file).
# Ported from the original Manual-based WorldofWarcraft-Leveling project's
# data/locations.json, one "Level NN" check per character level -- minus that source's two
# "Leveling"/"Gold_Hunt" goal checks, which this World deliberately does not carry over:
# neither is anything the addon can detect a check for (the goal condition is inferred
# purely from addon-reported level/gold state, see WoWLevelingClient._maybe_send_goal), so
# they'd only ever be real locations that a live game can never actually complete. Goal
# completion instead fires directly off that inferred state via StatusUpdate(CLIENT_GOAL),
# independent of any location check; the locked "Victory" event location (below) still
# exists purely to drive multiworld completion logic.
_RAW_LOCATIONS: list[dict] = [
    {'name': 'Level 01', 'region': 'Levels 01-10'},
    {'name': 'Level 02', 'region': 'Levels 01-10'},
    {'name': 'Level 03', 'region': 'Levels 01-10'},
    {'name': 'Level 04', 'region': 'Levels 01-10'},
    {'name': 'Level 05', 'region': 'Levels 01-10'},
    {'name': 'Level 06', 'region': 'Levels 01-10'},
    {'name': 'Level 07', 'region': 'Levels 01-10'},
    {'name': 'Level 08', 'region': 'Levels 01-10'},
    {'name': 'Level 09', 'region': 'Levels 01-10'},
    {'name': 'Level 10', 'region': 'Levels 01-10'},
    {'name': 'Level 11', 'region': 'Levels 11-20'},
    {'name': 'Level 12', 'region': 'Levels 11-20'},
    {'name': 'Level 13', 'region': 'Levels 11-20'},
    {'name': 'Level 14', 'region': 'Levels 11-20'},
    {'name': 'Level 15', 'region': 'Levels 11-20'},
    {'name': 'Level 16', 'region': 'Levels 11-20'},
    {'name': 'Level 17', 'region': 'Levels 11-20'},
    {'name': 'Level 18', 'region': 'Levels 11-20'},
    {'name': 'Level 19', 'region': 'Levels 11-20'},
    {'name': 'Level 20', 'region': 'Levels 11-20'},
    {'name': 'Level 21', 'region': 'Levels 21-30'},
    {'name': 'Level 22', 'region': 'Levels 21-30'},
    {'name': 'Level 23', 'region': 'Levels 21-30'},
    {'name': 'Level 24', 'region': 'Levels 21-30'},
    {'name': 'Level 25', 'region': 'Levels 21-30'},
    {'name': 'Level 26', 'region': 'Levels 21-30'},
    {'name': 'Level 27', 'region': 'Levels 21-30'},
    {'name': 'Level 28', 'region': 'Levels 21-30'},
    {'name': 'Level 29', 'region': 'Levels 21-30'},
    {'name': 'Level 30', 'region': 'Levels 21-30'},
    {'name': 'Level 31', 'region': 'Levels 31-40'},
    {'name': 'Level 32', 'region': 'Levels 31-40'},
    {'name': 'Level 33', 'region': 'Levels 31-40'},
    {'name': 'Level 34', 'region': 'Levels 31-40'},
    {'name': 'Level 35', 'region': 'Levels 31-40'},
    {'name': 'Level 36', 'region': 'Levels 31-40'},
    {'name': 'Level 37', 'region': 'Levels 31-40'},
    {'name': 'Level 38', 'region': 'Levels 31-40'},
    {'name': 'Level 39', 'region': 'Levels 31-40'},
    {'name': 'Level 40', 'region': 'Levels 31-40'},
    {'name': 'Level 41', 'region': 'Levels 41-50'},
    {'name': 'Level 42', 'region': 'Levels 41-50'},
    {'name': 'Level 43', 'region': 'Levels 41-50'},
    {'name': 'Level 44', 'region': 'Levels 41-50'},
    {'name': 'Level 45', 'region': 'Levels 41-50'},
    {'name': 'Level 46', 'region': 'Levels 41-50'},
    {'name': 'Level 47', 'region': 'Levels 41-50'},
    {'name': 'Level 48', 'region': 'Levels 41-50'},
    {'name': 'Level 49', 'region': 'Levels 41-50'},
    {'name': 'Level 50', 'region': 'Levels 41-50'},
    {'name': 'Level 51', 'region': 'Levels 51-60'},
    {'name': 'Level 52', 'region': 'Levels 51-60'},
    {'name': 'Level 53', 'region': 'Levels 51-60'},
    {'name': 'Level 54', 'region': 'Levels 51-60'},
    {'name': 'Level 55', 'region': 'Levels 51-60'},
    {'name': 'Level 56', 'region': 'Levels 51-60'},
    {'name': 'Level 57', 'region': 'Levels 51-60'},
    {'name': 'Level 58', 'region': 'Levels 51-60'},
    {'name': 'Level 59', 'region': 'Levels 51-60'},
    {'name': 'Level 60', 'region': 'Levels 51-60'},
    {'name': 'Level 61', 'region': 'Levels 61-70'},
    {'name': 'Level 62', 'region': 'Levels 61-70'},
    {'name': 'Level 63', 'region': 'Levels 61-70'},
    {'name': 'Level 64', 'region': 'Levels 61-70'},
    {'name': 'Level 65', 'region': 'Levels 61-70'},
    {'name': 'Level 66', 'region': 'Levels 61-70'},
    {'name': 'Level 67', 'region': 'Levels 61-70'},
    {'name': 'Level 68', 'region': 'Levels 61-70'},
    {'name': 'Level 69', 'region': 'Levels 61-70'},
    {'name': 'Level 70', 'region': 'Levels 61-70'},
    {'name': 'Level 71', 'region': 'Levels 71-80'},
    {'name': 'Level 72', 'region': 'Levels 71-80'},
    {'name': 'Level 73', 'region': 'Levels 71-80'},
    {'name': 'Level 74', 'region': 'Levels 71-80'},
    {'name': 'Level 75', 'region': 'Levels 71-80'},
    {'name': 'Level 76', 'region': 'Levels 71-80'},
    {'name': 'Level 77', 'region': 'Levels 71-80'},
    {'name': 'Level 78', 'region': 'Levels 71-80'},
    {'name': 'Level 79', 'region': 'Levels 71-80'},
    {'name': 'Level 80', 'region': 'Levels 71-80'},
    {'name': 'Level 81', 'region': 'Levels 81-85'},
    {'name': 'Level 82', 'region': 'Levels 81-85'},
    {'name': 'Level 83', 'region': 'Levels 81-85'},
    {'name': 'Level 84', 'region': 'Levels 81-85'},
    {'name': 'Level 85', 'region': 'Levels 81-85'},
    {'name': 'Level 86', 'region': 'Levels 86-90'},
    {'name': 'Level 87', 'region': 'Levels 86-90'},
    {'name': 'Level 88', 'region': 'Levels 86-90'},
    {'name': 'Level 89', 'region': 'Levels 86-90'},
    {'name': 'Level 90', 'region': 'Levels 86-90'},
]


class WoWLevelingLocation(Location):
    game: str = "World of Warcraft Leveling"


@dataclass(frozen=True)
class LocationData:
    id: int
    region: str


# Location IDs follow _RAW_LOCATIONS' own order, same stability rationale as Items.py.
# All 90 "Level NN" locations are pre-declared here so location_name_to_id is stable
# regardless of which expansion is chosen at generation time -- only a subset is actually
# placed into regions in a given seed (see __init__.py).
location_table: dict[str, LocationData] = {
    entry["name"]: LocationData(
        BASE_ID + _LOCATION_ID_OFFSET + index,
        entry["region"],
    )
    for index, entry in enumerate(_RAW_LOCATIONS)
}

# The event location holding the locked "Victory" item. It is NOT part of location_table:
# it has no id, is never sent over the network, and only exists so
# multiworld.completion_condition has something to check (see Rules.py / __init__.py).
VICTORY_EVENT_LOCATION_NAME = "Victory"
