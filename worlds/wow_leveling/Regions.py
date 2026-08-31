# The linear chain of level-bracket regions (Levels 01-10 -> 11-20 -> ... -> 86-90),
# hardcoded here (not loaded from JSON/a data file). Ported faithfully from the original
# Manual-based WorldofWarcraft-Leveling project's data/regions.json -- the exact boolean logic each
# bracket's "requires" string encoded there is hand-written in Rules.py instead (see the
# note there for why); regions.json's "connects_to"/"starting" fields were never anything
# more than this same linear order, so nothing beyond the bracket names/max levels
# themselves needs to survive the port.
LEVEL_BRACKETS: list[str] = [
    "Levels 01-10",
    "Levels 11-20",
    "Levels 21-30",
    "Levels 31-40",
    "Levels 41-50",
    "Levels 51-60",
    "Levels 61-70",
    "Levels 71-80",
    "Levels 81-85",
    "Levels 86-90",
]

# The character level reached once each bracket in LEVEL_BRACKETS is fully open.
BRACKET_MAX_LEVEL: list[int] = [10, 20, 30, 40, 50, 60, 70, 80, 85, 90]

# The two always-reachable ("starting") goal regions. Both exist regardless of which
# `goal` option is chosen; only whichever one matches the chosen goal ends up holding the
# locked "Victory" event location (see Locations.py / __init__.py), gated by that region's
# own entrance rule (see Rules.py).
GOLD_HUNT_REGION = "Gold Hunt"
LEVELING_REGION = "Leveling"
