"""
Log parser for Valheim Dedicated Server events.
Extracts:
- server_start
- player_join
- player_leave
- player_death
- raid_start
- boss_spawn
"""

import re
from typing import Optional, Tuple

# Boss list in Valheim internal code
# Eikthyr, gd_king (The Elder), Bonemass, Dragon (Moder), GoblinKing (Yagluth), SeekerQueen (The Queen), Fader (Ashlands boss)
BOSS_PATTERN = (
    r"(?:"
    r"Spawned\s+(Eikthyr|gd_king|Bonemass|Dragon|GoblinKing|SeekerQueen|Fader|boss_.*)"
    r"|Boss summoned:\s*(.+)"
    r"|Sacrificed items at altar:\s*(.+)"
    r")"
)

EVENT_REGEXES = [
    # 1. Player Death: ZDOID 0:0 is assigned on death
    (
        "player_death",
        re.compile(r"Got character ZDOID from (.+?)\s*:\s*0:0\b", re.IGNORECASE)
    ),
    # 2. Player Join: Character ZDOID loaded (non 0:0)
    (
        "player_join",
        re.compile(r"Got character ZDOID from (.+?)\s*:\s*(?!0:0\b)[0-9]+:[0-9]+", re.IGNORECASE)
    ),
    # 3. Boss Spawn / Summoning
    (
        "boss_spawn",
        re.compile(BOSS_PATTERN, re.IGNORECASE)
    ),
    # 4. Raids / Random events (e.g. "The forest is moving", "A foul smell from the swamp")
    (
        "raid_start",
        re.compile(r"Random event set:\s*([^\r\n]+)", re.IGNORECASE)
    ),
    # 5. Player Disconnect / Socket Closed
    (
        "player_leave",
        re.compile(r"(?:Closing socket|Destroying peer)\s*([0-9]+)", re.IGNORECASE)
    ),
    # 6. Server lifecycle ready
    (
        "server_start",
        re.compile(r"(?:Game server connected|DungeonDB Start done)", re.IGNORECASE)
    ),
]


def parse_log_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Parses a single line of Valheim server logs.
    Returns (event_name, event_detail) or None.
    """
    if not line or not line.strip():
        return None

    clean_line = line.strip()

    for event_name, pattern in EVENT_REGEXES:
        match = pattern.search(clean_line)
        if match:
            # Pick first non-None captured group as detail
            groups = [g for g in match.groups() if g is not None]
            detail = groups[0].strip() if groups else event_name
            return event_name, detail

    return None
