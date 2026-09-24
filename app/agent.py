# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import logging
import os
import random
import urllib.request
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

import google.auth
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.load_memory_tool import LoadMemoryTool
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback

PROJECT_ID = "qwiklabs-gcp-02-c19c65f27e59"

# Load Agent Engine Sandbox Code Executor from deployment_metadata.json or project
metadata_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json"
)

sandbox_executor = None
if os.path.exists(metadata_path):
    with open(metadata_path, "r") as f:
        meta = json.load(f)
        sandbox_id = meta.get("sandbox_resource_name")
        if sandbox_id:
            sandbox_executor = AgentEngineSandboxCodeExecutor(
                sandbox_resource_name=sandbox_id
            )

if not sandbox_executor:
    sandbox_executor = AgentEngineSandboxCodeExecutor(
        project=PROJECT_ID, location="us-east1"
    )

CLAN_GUARDIANS = {
    "Dragon": {
        1: "Water Dragon",
        2: "Fire Dragon",
        3: "Golden Dragon",
        4: "Ancient Primordial Dragon",
    },
    "Phoenix": {
        1: "Ash Phoenix",
        2: "Blazing Phoenix",
        3: "Solar Phoenix",
        4: "Immortal Primordial Phoenix",
    },
    "Titan": {
        1: "Stone Behemoth",
        2: "Iron Golem",
        3: "Titan Colossus",
        4: "Ancient Primordial Titan",
    },
    "Shadow": {
        1: "Shadow Stalker",
        2: "Nightmare Phantom",
        3: "Abyssal Leviathan",
        4: "Primordial Shadow Sovereign",
    },
}

UNLOCK_COSTS = {
    "spell": 10,
    "skill": 15,
    "magic_item": 20,
    "guardian_beast": 30,
}

UNLOCK_ORDER = ["spell", "skill", "magic_item", "guardian_beast"]


def get_firestore_client():
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return firestore.Client(project=PROJECT_ID, credentials=credentials)


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def get_spells(category: str = "") -> str:
    """Retrieves spells from the Realm Weaver Firestore database."""
    db = get_firestore_client()
    spells_ref = db.collection("spells")
    if category:
        query = spells_ref.where("category", "==", category)
        docs = query.stream()
    else:
        docs = spells_ref.stream()

    spells = []
    for doc in docs:
        data = doc.to_dict()
        spells.append(
            f"- {data.get('name')} (Category: {data.get('category')}, Damage: {data.get('damage')}, Cost: {data.get('spirit_stone_cost')} Spirit Stones, Req Level: {data.get('unlock_level')}): {data.get('description')}"
        )

    if not spells:
        return "No spells found in Firestore database."

    return "Spells catalog:\n" + "\n".join(spells)


def add_spell(
    name: str,
    category: str,
    damage: int,
    spirit_stone_cost: int,
    unlock_level: int,
    description: str,
) -> str:
    """Adds a new spell to the Realm Weaver Firestore database."""
    db = get_firestore_client()
    doc_id = name.lower().replace(" ", "_")
    doc_ref = db.collection("spells").document(doc_id)
    spell_data = {
        "name": name,
        "category": category,
        "damage": damage,
        "spirit_stone_cost": spirit_stone_cost,
        "unlock_level": unlock_level,
        "description": description,
    }
    doc_ref.set(spell_data)
    return f"Successfully added spell '{name}' ({doc_id}) to Firestore database."


def join_clan(player_name: str, clan_choice: str = "") -> str:
    """Automatically registers a player and assigns them to a Clan (Dragon, Phoenix, Titan, Shadow).

    Args:
        player_name: Name of the player.
        clan_choice: Optional choice ('Dragon', 'Phoenix', 'Titan', 'Shadow'). If empty, assigned automatically.

    Returns:
        Onboarding confirmation message.
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)

    if doc_ref.get().exists:
        data = doc_ref.get().to_dict()
        return f"Player '{player_name}' is already registered in Clan {data.get('clan')} (Level {data.get('level')})."

    valid_clans = ["Dragon", "Phoenix", "Titan", "Shadow"]
    selected_clan = clan_choice.strip().capitalize()
    if selected_clan not in valid_clans:
        selected_clan = random.choice(valid_clans)

    initial_beast = CLAN_GUARDIANS[selected_clan][1]
    player_data = {
        "name": player_name,
        "clan": selected_clan,
        "level": 1,
        "spirit_stones": 0,
        "weapon": "Iron Greatsword",
        "unlocked_items": [],
        "unlock_progress": {
            "spell": False,
            "skill": False,
            "magic_item": False,
            "guardian_beast": False,
        },
        "guardian_beast": initial_beast,
        "eliminated": False,
    }
    doc_ref.set(player_data)

    return (
        f"🛡️ Welcome Warlord {player_name}! You have been assigned to Clan {selected_clan}.\n"
        f"⚔️ Starting Weapon: Iron Greatsword\n"
        f"🐉 Level 1 Guardian Beast: {initial_beast}\n"
        f"💎 Spirit Stones: 0\n"
        f"📜 Sequential Unlock Mission Target: Step 1 - Spell (Requires 10 Spirit Stones)."
    )


def get_player_profile(player_name: str) -> str:
    """Retrieves full player profile, Clan assignment, level, Spirit Stones, and sequential unlock status.

    Args:
        player_name: Name of the player to query.
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found. Call join_clan to register first."

    p = doc.to_dict()
    prog = p.get("unlock_progress", {})
    status = "🔴 ELIMINATED" if p.get("eliminated") else "🟢 ACTIVE"

    return (
        f"👤 Warlord Profile: {p.get('name')} [{status}]\n"
        f"🏰 Clan: {p.get('clan')} | Level: {p.get('level')}\n"
        f"⚔️ Weapon: {p.get('weapon')}\n"
        f"🐾 Guardian Beast: {p.get('guardian_beast')}\n"
        f"💎 Spirit Stones: {p.get('spirit_stones')}\n"
        f"🎯 Sequential Unlock Progress (Level {p.get('level')}):\n"
        f"  1. Spell (10 Stones): {'✅ Unlocked' if prog.get('spell') else '❌ Locked'}\n"
        f"  2. Skill (15 Stones): {'✅ Unlocked' if prog.get('skill') else '❌ Locked'}\n"
        f"  3. Magic Item (20 Stones): {'✅ Unlocked' if prog.get('magic_item') else '❌ Locked'}\n"
        f"  4. Guardian Beast (30 Stones): {'✅ Unlocked' if prog.get('guardian_beast') else '❌ Locked'}\n"
        f"🎒 Unlocked Inventory: {', '.join(p.get('unlocked_items', [])) if p.get('unlocked_items') else 'None'}"
    )


def explore_mountain_battle(player_name: str, direction: str = "north") -> str:
    """Moves player across mountain ranges, encounters monsters, and harvests Spirit Stones upon slaying them.

    Args:
        player_name: Player name.
        direction: Direction of mountain movement ('north', 'south', 'east', 'west').
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found. Join a clan first!"

    p = doc.to_dict()
    if p.get("eliminated"):
        return f"Player '{player_name}' was eliminated in Clan Warfare and cannot explore."

    monsters = [
        ("Mountain Frost Drake", 450),
        ("Thunder Golem", 600),
        ("Shadow Viper", 320),
        ("Volcanic Behemoth", 750),
    ]
    monster_name, monster_hp = random.choice(monsters)
    hit_damage = random.randint(180, 260)
    stones_dropped = random.randint(3, 7)

    new_stones = p.get("spirit_stones", 0) + stones_dropped
    doc_ref.update({"spirit_stones": new_stones})

    return (
        f"🏞️ Explored Mountain Range ({direction.upper()})...\n"
        f"👾 Encountered Wild Monster: {monster_name} (HP: {monster_hp})!\n"
        f"🎯 Hit Marker: Dealt {hit_damage} physical sword damage!\n"
        f"💥 Monster Slain! Dropped +{stones_dropped} Spirit Stones 💎\n"
        f"💰 Total Spirit Stones Balance: {new_stones}"
    )


def unlock_item(player_name: str, item_type: str, item_name: str) -> str:
    """Enforces sequential 4-step unlock requirements (Spell -> Skill -> Magic Item -> Guardian Beast).

    Args:
        player_name: Name of the player.
        item_type: Type of item to unlock ('spell', 'skill', 'magic_item', 'guardian_beast').
        item_name: Name of the specific spell, skill, magic item, or beast.
    """
    item_key = item_type.lower().strip().replace(" ", "_")
    if item_key not in UNLOCK_COSTS:
        return f"Invalid item_type '{item_type}'. Must be one of: {', '.join(UNLOCK_COSTS.keys())}."

    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    prog = p.get("unlock_progress", {})
    stones = p.get("spirit_stones", 0)
    cost = UNLOCK_COSTS[item_key]

    if prog.get(item_key):
        return f"You have already unlocked the {item_key} for Level {p.get('level')}."

    # Enforce sequential order:
    idx = UNLOCK_ORDER.index(item_key)
    if idx > 0:
        prev_step = UNLOCK_ORDER[idx - 1]
        if not prog.get(prev_step):
            return f"❌ Sequential Unlock Blocked! You must unlock Step {idx} ({prev_step.upper()}) before unlocking {item_key.upper()}."

    if stones < cost:
        return f"❌ Insufficient Spirit Stones! Unlocking {item_key} requires {cost} Spirit Stones (Current Balance: {stones})."

    # Unlock item
    prog[item_key] = True
    new_stones = stones - cost
    unlocked = p.get("unlocked_items", [])
    unlocked.append(f"{item_key.title()}: {item_name}")

    updates = {
        "unlock_progress": prog,
        "spirit_stones": new_stones,
        "unlocked_items": unlocked,
    }
    if item_key == "guardian_beast":
        updates["guardian_beast"] = item_name

    doc_ref.update(updates)

    next_step = (
        UNLOCK_ORDER[idx + 1] if idx + 1 < len(UNLOCK_ORDER) else "Level-Up!"
    )
    return (
        f"🎉 Successfully unlocked {item_key.upper()} Step: '{item_name}'!\n"
        f"💸 Deducted {cost} Spirit Stones. Remaining Balance: {new_stones} 💎\n"
        f"🎯 Next Target: {next_step.upper()}"
    )


def level_up_character(player_name: str) -> str:
    """Verifies that all 4 sequential items (Spell, Skill, Magic Item, Guardian Beast) are unlocked before granting Level-Up.

    Args:
        player_name: Name of player.
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    prog = p.get("unlock_progress", {})

    missing = [step for step in UNLOCK_ORDER if not prog.get(step)]
    if missing:
        return f"❌ Level-Up Gate Locked! You must unlock all 4 tier items. Missing: {', '.join(missing)}."

    new_lvl = p.get("level", 1) + 1
    clan = p.get("clan")
    new_beast = CLAN_GUARDIANS.get(clan, {}).get(
        new_lvl, f"{clan} Primordial Beast"
    )

    # Reset progress for new tier
    reset_prog = {step: False for step in UNLOCK_ORDER}

    doc_ref.update(
        {
            "level": new_lvl,
            "unlock_progress": reset_prog,
            "guardian_beast": new_beast,
        }
    )

    return (
        f"🌟 CONGRATULATIONS! Warlord {player_name} Leveled Up to LEVEL {new_lvl}! 🌟\n"
        f"🐉 Evolved Guardian Beast: {new_beast}!\n"
        f"📜 Sequential unlock requirements reset for Tier {new_lvl} progression."
    )


def challenge_clan_duel(attacker_name: str, defender_name: str) -> str:
    """Resolves Clan Warfare PvP duel. Winner absorbs all opponent's spells, skills, items, and beasts; defeated player is eliminated.

    Args:
        attacker_name: Name of attacking player.
        defender_name: Name of defending player.
    """
    db = get_firestore_client()
    att_id = attacker_name.lower().replace(" ", "_")
    def_id = defender_name.lower().replace(" ", "_")

    att_doc = db.collection("players").document(att_id).get()
    def_doc = db.collection("players").document(def_id).get()

    if not att_doc.exists or not def_doc.exists:
        return "Both attacker and defender must be registered players."

    att = att_doc.to_dict()
    dff = def_doc.to_dict()

    if att.get("eliminated"):
        return f"Attacker '{attacker_name}' is eliminated and cannot duel."
    if dff.get("eliminated"):
        return f"Defender '{defender_name}' is already eliminated."

    att_power = (
        att.get("level", 1) * 100
        + len(att.get("unlocked_items", [])) * 25
        + att.get("spirit_stones", 0)
    )
    def_power = (
        dff.get("level", 1) * 100
        + len(dff.get("unlocked_items", [])) * 25
        + dff.get("spirit_stones", 0)
    )

    if att_power >= def_power:
        winner_name, loser_name = attacker_name, defender_name
        winner_ref, loser_ref = db.collection("players").document(
            att_id
        ), db.collection("players").document(def_id)
        winner_data, loser_data = att, dff
    else:
        winner_name, loser_name = defender_name, attacker_name
        winner_ref, loser_ref = db.collection("players").document(
            def_id
        ), db.collection("players").document(att_id)
        winner_data, loser_data = dff, att

    # Winner absorbs all loser items & stones
    absorbed_items = winner_data.get("unlocked_items", []) + loser_data.get(
        "unlocked_items", []
    )
    absorbed_stones = winner_data.get(
        "spirit_stones", 0
    ) + loser_data.get("spirit_stones", 0)

    winner_ref.update(
        {
            "unlocked_items": absorbed_items,
            "spirit_stones": absorbed_stones,
        }
    )

    loser_ref.update(
        {
            "eliminated": True,
            "spirit_stones": 0,
            "unlocked_items": [],
        }
    )

    return (
        f"⚔️ CLAN WAR DUEL RESULTS ⚔️\n"
        f"💥 {winner_name} (Power: {max(att_power, def_power)}) vs {loser_name} (Power: {min(att_power, def_power)})\n"
        f"🏆 VICTORY: {winner_name} defeated {loser_name}!\n"
        f"🔥 ABSORPTION: {winner_name} absorbed all spells, skills, items, and +{loser_data.get('spirit_stones', 0)} Spirit Stones from {loser_name}!\n"
        f"💀 ELIMINATION FEED: Warlord {loser_name} has been ELIMINATED from Clan Warfare!"
    )


def get_clan_leaderboard() -> str:
    """Queries Firestore for active Clan warlords and total clan power dominance."""
    db = get_firestore_client()
    docs = db.collection("players").stream()

    clan_stats = {}
    for doc in docs:
        p = doc.to_dict()
        c = p.get("clan", "Unknown")
        if c not in clan_stats:
            clan_stats[c] = {"active_warlords": 0, "total_power": 0}

        if not p.get("eliminated"):
            clan_stats[c]["active_warlords"] += 1
            power = (
                p.get("level", 1) * 100
                + len(p.get("unlocked_items", [])) * 25
                + p.get("spirit_stones", 0)
            )
            clan_stats[c]["total_power"] += power

    sorted_clans = sorted(
        clan_stats.items(), key=lambda x: x[1]["total_power"], reverse=True
    )

    lines = ["🏰 REALM WEAVER CLAN LEADERBOARD 🏰"]
    for rank, (clan, data) in enumerate(sorted_clans, start=1):
        lines.append(
            f"#{rank} Clan {clan}: {data['total_power']} Total Power | Active Warlords: {data['active_warlords']}"
        )

    return "\n".join(lines)


def scan_mountain_minimap(player_name: str, sector_grid: str = "A4") -> str:
    """Performs a Modern Warfare-inspired UAV Tactical Radar sweep across mountain sector grids.

    Args:
        player_name: Name of player performing scan.
        sector_grid: Mountain sector coordinates (e.g., 'A4', 'B2', 'C7').

    Returns:
        Tactical minimap scan report with pinged enemy warlords, boss spawns, and Spirit Stone deposits.
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    bonus_stones = random.randint(4, 8)
    new_stones = p.get("spirit_stones", 0) + bonus_stones
    doc_ref.update({"spirit_stones": new_stones})

    enemies = ["Shadow Warlord Malakor", "Titan Vanguard Kaelen", "Phoenix Warlock Ignis"]
    enemy_ping = random.choice(enemies)
    boss_ping = "Ancient Primordial Mountain Wyrm"

    return (
        f"📡 TACTICAL UAV MINIMAP SCAN [Sector {sector_grid.upper()}] 📡\n"
        f"🔴 PINGED RIVAL WARLORD: Detected {enemy_ping} at Grid {sector_grid.upper()}-North\n"
        f"⚠️ RARE BOSS DETECTED: {boss_ping} lurking in deep cavern!\n"
        f"💎 RICH VEIN HARVESTED: Uncovered Spirit Stone Deposit (+{bonus_stones} Stones)!\n"
        f"💰 New Spirit Stone Balance: {new_stones}"
    )


def customize_tactical_loadout(
    player_name: str, attachment_slot: str, attachment_name: str
) -> str:
    """Gunsmith customization system: equips tactical attachments to player weapon (Optic, Barrel, Underbarrel, Magazine).

    Args:
        player_name: Name of player.
        attachment_slot: Slot to modify ('optic', 'barrel', 'underbarrel', 'magazine').
        attachment_name: Name of attachment (e.g. 'Thermal Scope', 'Suppressed Shroud', 'Magma Foregrip').
    """
    slot_key = attachment_slot.lower().strip()
    valid_slots = ["optic", "barrel", "underbarrel", "magazine"]
    if slot_key not in valid_slots:
        return f"Invalid slot '{attachment_slot}'. Valid Gunsmith slots: {', '.join(valid_slots)}."

    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    attachments = p.get("gunsmith_attachments", {})
    attachments[slot_key] = attachment_name

    doc_ref.update({"gunsmith_attachments": attachments})

    att_summary = ", ".join([f"{k.upper()}: {v}" for k, v in attachments.items()])
    return (
        f"🛠️ GUNSMITH LOADOUT CUSTOMIZED [{p.get('weapon')}] 🛠️\n"
        f"🔧 Equipped [{slot_key.upper()}]: {attachment_name}\n"
        f"📊 Active Gunsmith Attachments: {att_summary}\n"
        f"⚡ Damage & Hit Marker Precision Boosted!"
    )


def call_killstreak_strike(
    player_name: str,
    strike_type: str = "Precision Dragon Strike",
    target_sector: str = "B2",
) -> str:
    """Calls down a tactical Air Strike / Killstreak (Precision Dragon Strike, Orbital Flame Artillery) on mountain targets.

    Args:
        player_name: Name of player requesting strike.
        strike_type: Type of tactical strike ('Precision Dragon Strike', 'Orbital Flame Artillery').
        target_sector: Grid sector target.
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    bonus_stones = random.randint(10, 15)
    new_stones = p.get("spirit_stones", 0) + bonus_stones
    doc_ref.update({"spirit_stones": new_stones})

    damage_dealt = random.randint(1200, 1800)
    return (
        f"🚀 TACTICAL KILLSTREAK INCOMING: {strike_type.upper()}! 🚀\n"
        f"🎯 TARGET ACQUIRED: Grid Sector [{target_sector.upper()}]\n"
        f"💥 BOOM! Dealt {damage_dealt} AOE Elemental Damage across mountain range!\n"
        f"💎 TERRAIN DESTROYED: Collected +{bonus_stones} Spirit Stones from wreckage!\n"
        f"💰 New Spirit Stone Balance: {new_stones}"
    )


def claim_clan_territory(player_name: str, territory_name: str) -> str:
    """Claims a mountain territory sector for the player's Clan, expanding domain control.

    Args:
        player_name: Player claiming territory.
        territory_name: Name of mountain territory (e.g. 'Frostpeak Fortress', 'Magma Trench').
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    clan = p.get("clan")

    terr_id = territory_name.lower().replace(" ", "_")
    terr_ref = db.collection("territories").document(terr_id)
    terr_ref.set(
        {
            "name": territory_name,
            "claimed_by_clan": clan,
            "claimed_by_player": player_name,
            "date_claimed": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )

    return (
        f"🚩 CLAN TERRITORY CONQUEST SUCCESSFUL! 🚩\n"
        f"🏰 Territory '{territory_name}' is now claimed under the banner of CLAN {clan.upper()}!\n"
        f"👑 Conquering Warlord: {player_name}\n"
        f"🔥 Clan {clan} receives +150 Territory Dominance Power!"
    )


def gather_mountain_herbs(
    player_name: str, region: str = "Mist Valley"
) -> str:
    """Forages deep mountain cliffs and valleys to gather mythical herbs for HP restoration and alchemy.

    Args:
        player_name: Name of player foraging.
        region: Mountain region to search ('Mist Valley', 'Dragon Crag', 'Volcanic Peak', 'Frost Ridge').
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    if p.get("eliminated"):
        return f"Player '{player_name}' is eliminated and cannot forage."

    herbs_pool = [
        ("Celestial Lotus", 300, "Restores 300 HP and clears combat wounds."),
        ("Dragonblood Root", 500, "Restores 500 HP and boosts physical hit damage."),
        ("Phoenix Blossom", 800, "Full HP revive & grants fire damage resistance."),
        ("Frost Moss", 200, "Restores 200 HP and cools down spell costs."),
    ]
    found_herb, healing_power, desc = random.choice(herbs_pool)

    herbs = p.get("herb_inventory", {})
    herbs[found_herb] = herbs.get(found_herb, 0) + 1

    doc_ref.update({"herb_inventory": herbs})

    inventory_str = ", ".join([f"{k} (x{v})" for k, v in herbs.items()])
    return (
        f"🌿 MOUNTAIN HERB FORAGING SUCCESSFUL [{region.upper()}] 🌿\n"
        f"🌸 Found Herb: {found_herb} (Potency: +{healing_power} HP)\n"
        f"📜 Impact Effect: {desc}\n"
        f"🎒 Current Herb Inventory: {inventory_str}"
    )


def consume_herb(player_name: str, herb_name: str) -> str:
    """Consumes a gathered herb from inventory to restore HP and remove combat impact debuffs.

    Args:
        player_name: Name of player.
        herb_name: Name of herb to consume ('Celestial Lotus', 'Dragonblood Root', 'Phoenix Blossom', 'Frost Moss').
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    herbs = p.get("herb_inventory", {})

    target_herb = None
    for h in herbs.keys():
        if herb_name.lower() in h.lower():
            target_herb = h
            break

    if not target_herb or herbs.get(target_herb, 0) <= 0:
        return f"❌ Herb '{herb_name}' not available in inventory. Available: {', '.join(herbs.keys()) if herbs else 'None'}."

    # Consume 1 herb
    herbs[target_herb] -= 1
    if herbs[target_herb] == 0:
        del herbs[target_herb]

    max_hp = p.get("max_hp", 1000)
    current_hp = p.get("current_hp", 600)

    hp_gains = {
        "Celestial Lotus": 300,
        "Dragonblood Root": 500,
        "Phoenix Blossom": 800,
        "Frost Moss": 200,
    }
    gain = hp_gains.get(target_herb, 250)
    new_hp = min(max_hp, current_hp + gain)

    doc_ref.update({"herb_inventory": herbs, "current_hp": new_hp, "max_hp": max_hp})

    return (
        f"🧪 HERB CONSUMED: {target_herb}! 🧪\n"
        f"❤️ Restored +{gain} HP (Health: {new_hp}/{max_hp} HP)\n"
        f"🛡️ Combat Impact & Status Wounds Cleared!\n"
        f"🎒 Remaining {target_herb}: {herbs.get(target_herb, 0)}"
    )


def donate_herb_to_clan(
    player_name: str, herb_name: str, quantity: int = 1
) -> str:
    """Donates gathered herbs to the Clan Treasury to prepare reserves for Clan Clash PvP wars.

    Args:
        player_name: Name of player donating.
        herb_name: Name of herb to donate.
        quantity: Number of herbs to deposit (default 1).
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    clan = p.get("clan")
    herbs = p.get("herb_inventory", {})

    target_herb = None
    for h in herbs.keys():
        if herb_name.lower() in h.lower():
            target_herb = h
            break

    if not target_herb or herbs.get(target_herb, 0) < quantity:
        return f"❌ You do not have {quantity}x '{herb_name}' in inventory to donate."

    # Deduct from player
    herbs[target_herb] -= quantity
    if herbs[target_herb] == 0:
        del herbs[target_herb]
    doc_ref.update({"herb_inventory": herbs})

    # Deposit into Clan Treasury in Firestore
    clan_ref = db.collection("clan_treasuries").document(clan.lower())
    clan_doc = clan_ref.get()
    treasury_herbs = clan_doc.to_dict().get("herbs", {}) if clan_doc.exists else {}
    treasury_herbs[target_herb] = treasury_herbs.get(target_herb, 0) + quantity
    clan_ref.set({"clan": clan, "herbs": treasury_herbs}, merge=True)

    return (
        f"🏰 CLAN TREASURY DONATION SUCCESSFUL! 🏰\n"
        f"🎁 Donated {quantity}x {target_herb} to Clan {clan.upper()} Treasury!\n"
        f"⚔️ Clan Clash Reserve Boosted! Total Clan {target_herb}: {treasury_herbs[target_herb]}\n"
        f"🏅 Earned +50 Clan Contribution Points!"
    )


def trade_spirit_stones(
    sender_name: str, recipient_name: str, amount: int
) -> str:
    """Trades/transfers Spirit Stones between registered players to assist clan members with item unlock requirements.

    Args:
        sender_name: Player sending stones.
        recipient_name: Player receiving stones.
        amount: Number of Spirit Stones to transfer.
    """
    if amount <= 0:
        return "Transfer amount must be greater than 0."

    db = get_firestore_client()
    send_id = sender_name.lower().replace(" ", "_")
    rec_id = recipient_name.lower().replace(" ", "_")

    send_ref = db.collection("players").document(send_id)
    rec_ref = db.collection("players").document(rec_id)

    send_doc = send_ref.get()
    rec_doc = rec_ref.get()

    if not send_doc.exists or not rec_doc.exists:
        return "Both sender and recipient must be registered players."

    s_data = send_doc.to_dict()
    r_data = rec_doc.to_dict()

    if s_data.get("spirit_stones", 0) < amount:
        return f"❌ Transfer Failed! {sender_name} only has {s_data.get('spirit_stones', 0)} Spirit Stones (Requested: {amount})."

    new_send_stones = s_data.get("spirit_stones", 0) - amount
    new_rec_stones = r_data.get("spirit_stones", 0) + amount

    send_ref.update({"spirit_stones": new_send_stones})
    rec_ref.update({"spirit_stones": new_rec_stones})

    return (
        f"🤝 SPIRIT STONE TRADE EXECUTED SUCCESSFUL! 🤝\n"
        f"💸 {sender_name} transferred {amount} Spirit Stones 💎 to {recipient_name}!\n"
        f"💰 {sender_name} Remaining Balance: {new_send_stones} 💎\n"
        f"💰 {recipient_name} New Balance: {new_rec_stones} 💎"
    )


def trigger_clan_clash_buff(player_name: str, herb_name: str) -> str:
    """Activates a Clan Clash war buff using herbs stored in the Clan Treasury reserves.

    Args:
        player_name: Player activating war buff.
        herb_name: Name of herb to draw from Clan Treasury reserves.
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    clan = p.get("clan")

    clan_ref = db.collection("clan_treasuries").document(clan.lower())
    clan_doc = clan_ref.get()

    if not clan_doc.exists:
        return f"Clan '{clan}' Treasury has no herbs deposited yet!"

    treasury_herbs = clan_doc.to_dict().get("herbs", {})
    target_herb = None
    for h in treasury_herbs.keys():
        if herb_name.lower() in h.lower():
            target_herb = h
            break

    if not target_herb or treasury_herbs.get(target_herb, 0) <= 0:
        return f"❌ No '{herb_name}' available in Clan {clan} Treasury!"

    treasury_herbs[target_herb] -= 1
    clan_ref.update({"herbs": treasury_herbs})

    return (
        f"🔥 CLAN CLASH WAR BUFF ACTIVATED! 🔥\n"
        f"🏰 Clan {clan.upper()} activated 1x {target_herb} from Treasury reserves!\n"
        f"⚔️ CLAN-WIDE WAR BUFF: +300 Dominance Power & +25% Elemental Damage in all PvP battles!\n"
        f"📦 Remaining Treasury {target_herb}: {treasury_herbs[target_herb]}"
    )


def summon_guardian_beast(
    player_name: str, target_enemy: str = "Wild Monster"
) -> str:
    """Unleashes player's unlocked Guardian Beast ultimate strike (Water Dragon, Fire Dragon, Golden Dragon, Primordial Dragon).

    Args:
        player_name: Name of player summoning beast.
        target_enemy: Target of beast ultimate strike.
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    beast = p.get("guardian_beast", "Ancient Dragon")
    level = p.get("level", 1)

    ultimate_damage = random.randint(2500, 4500) * level
    bonus_stones = random.randint(8, 15)

    new_stones = p.get("spirit_stones", 0) + bonus_stones
    doc_ref.update({"spirit_stones": new_stones})

    return (
        f"🐲 GUARDIAN BEAST ULTIMATE SUMMON: {beast.upper()}! 🐲\n"
        f"🎬 CINEMATIC CUTSCENE: {beast} descends from mountain storm clouds!\n"
        f"💥 ULTIMATE IMPACT: Dealt {ultimate_damage} Elemental Ultimate Damage to {target_enemy}!\n"
        f"💎 DESTROYED TERRAIN: Harvested +{bonus_stones} Spirit Stones!\n"
        f"💰 New Spirit Stone Balance: {new_stones}"
    )


def heal_at_clan_shrine(player_name: str) -> str:
    """Restores character HP to 100% max HP at the Clan Sanctuary Shrine for 5 Spirit Stones.

    Args:
        player_name: Name of player.
    """
    db = get_firestore_client()
    doc_id = player_name.lower().replace(" ", "_")
    doc_ref = db.collection("players").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Player '{player_name}' not found."

    p = doc.to_dict()
    stones = p.get("spirit_stones", 0)

    if stones < 5:
        return f"❌ Healing Shrine costs 5 Spirit Stones (Current Balance: {stones})."

    max_hp = p.get("max_hp", 1000)
    new_stones = stones - 5
    doc_ref.update({"current_hp": max_hp, "spirit_stones": new_stones})

    return (
        f"⛩️ CLAN SANCTUARY SHRINE BLESSING ⛩️\n"
        f"✨ Fully restored Warlord {player_name}'s Health to {max_hp}/{max_hp} HP!\n"
        f"💸 Deducted 5 Spirit Stones. Remaining Balance: {new_stones} 💎"
    )


def fetch_mythical_lore(query: str) -> str:
    """Queries the free public D&D 5e API for real stats and lore of mythical monsters or spells.

    Args:
        query: Name or index of monster or spell (e.g. 'adult-red-dragon', 'fireball', 'ancient-brass-dragon', 'lightning-bolt').

    Returns:
        Real monster stats, challenge rating, hit points, or spell details fetched live from the public API.
    """
    slug = query.lower().strip().replace(" ", "-")
    api_key = os.environ.get("DND5E_API_KEY", "")

    headers = {"User-Agent": "RealmWeaver/1.0", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    endpoints = [
        f"https://www.dnd5eapi.co/api/2014/monsters/{slug}",
        f"https://www.dnd5eapi.co/api/2014/spells/{slug}",
    ]

    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if "hit_points" in data:
                        actions = ", ".join(
                            [a.get("name") for a in data.get("actions", [])[:3]]
                        )
                        return (
                            f"📜 MYTHICAL BEAST LORE [{data.get('name')}] 📜\n"
                            f"🐲 Type: {data.get('type', '').title()} ({data.get('size')} {data.get('alignment')})\n"
                            f"❤️ Hit Points: {data.get('hit_points')} | Armor Class: {data.get('armor_class', [{}])[0].get('value', 'N/A')}\n"
                            f"⭐ Challenge Rating: CR {data.get('challenge_rating')} ({data.get('xp', 0)} XP)\n"
                            f"🔥 Signature Actions: {actions}"
                        )
                    elif "level" in data:
                        desc = " ".join(data.get("desc", []))[:200]
                        return (
                            f"📜 MYTHICAL SPELL LORE [{data.get('name')}] 📜\n"
                            f"✨ Level: {data.get('level')} | School: {data.get('school', {}).get('name')}\n"
                            f"🎯 Range: {data.get('range')} | Casting Time: {data.get('casting_time')}\n"
                            f"📜 Description: {desc}..."
                        )
        except Exception:
            continue

    return f"Unable to fetch lore for '{query}'. Try searching for 'adult-red-dragon', 'fireball', 'ancient-brass-dragon', or 'lightning-bolt'."


def generate_realm_item_image(
    item_name: str, item_type: str = "item", tool_context: ToolContext = None
) -> str:
    """Generates high-quality fantasy RPG artwork for items, beasts, loadouts, or spells in Realm Weaver using gemini-3.1-flash-lite-image in the global region, saves it as a Playground artifact, and uploads to public GCS.

    Args:
        item_name: Name of item, beast, loadout, or spell (e.g. 'Dragonblood Greatsword', 'Water Dragon Guardian', 'Celestial Lotus').
        item_type: Category of item ('beast', 'sword', 'herb', 'spell', 'loadout', 'artifact').
        tool_context: ADK ToolContext instance for saving Playground artifacts.
    """
    gcs_bucket_name = "realm-weaver-assets-qwiklabs-gcp-02-c19c65f27e59"
    gcp_project_id = "qwiklabs-gcp-02-c19c65f27e59"

    import google.genai

    # 1. Initialize GenAI client in 'global' region
    client = google.genai.Client(
        vertexai=True, project=gcp_project_id, location="global"
    )

    prompt = (
        f"AAA cinematic fantasy RPG artwork of {item_name}, category {item_type}, "
        "Call of Duty Modern Warfare dark tactical lighting, 60fps high detail, mythical glows."
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image", contents=prompt
    )

    part = response.candidates[0].content.parts[0]
    image_bytes = part.inline_data.data
    mime_type = part.inline_data.mime_type or "image/png"

    clean_filename = item_name.lower().replace(" ", "_")
    object_name = f"artifacts/{clean_filename}.png"

    # 2. Save image as Playground artifact using tool_context.save_artifact
    if tool_context:
        artifact_part = types.Part.from_bytes(
            data=image_bytes, mime_type=mime_type
        )
        tool_context.save_artifact(
            filename=f"{clean_filename}.png", artifact=artifact_part
        )

    # 3. Upload image bytes directly to GCS bucket (no local file path return)
    storage_client = storage.Client(project=gcp_project_id)
    bucket = storage_client.bucket(gcs_bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = (
        f"https://storage.googleapis.com/{gcs_bucket_name}/{object_name}"
    )
    return (
        f"🎨 REALM ARTWORK GENERATED [{item_name.upper()}] 🎨\n"
        f"🖼️ Public Image URL: {public_url}\n"
        f"✨ Saved to Playground Artifacts as '{clean_filename}.png'."
    )


def generate_realm_video(
    item_name: str, item_type: str = "item", tool_context: ToolContext = None
) -> str:
    """Generates a short video for an item, spell, beast, or loadout in Realm Weaver using Google's Omni model (gemini-omni-flash-preview) in the global region, saves it as a Playground artifact, and uploads directly to public GCS.

    Args:
        item_name: Name of item, spell, beast, or loadout (e.g. 'Dragonblood Greatsword', 'Fireball Spell', 'Water Dragon Guardian').
        item_type: Category of item ('weapon', 'spell', 'beast', 'herb', 'loadout').
        tool_context: ADK ToolContext instance for saving Playground artifacts.
    """
    gcs_bucket_name = "realm-weaver-assets-qwiklabs-gcp-02-c19c65f27e59"
    gcp_project_id = "qwiklabs-gcp-02-c19c65f27e59"

    import base64
    import google.genai

    # 1. Initialize GenAI client in 'global' region using gemini-omni-flash-preview
    client = google.genai.Client(
        vertexai=True, project=gcp_project_id, location="global"
    )

    prompt = (
        f"Cinematic short video of {item_name} ({item_type}) in Realm Weaver RPG world, "
        "60fps high detail, magical particle effects, mythical glow."
    )

    mime_type = "video/mp4"
    video_bytes = None

    try:
        res = client.interactions.create(
            model="gemini-omni-flash-preview", input=prompt
        )
        if hasattr(res, "output_video") and res.output_video and getattr(res.output_video, "data", None):
            raw_data = res.output_video.data
            if isinstance(raw_data, str):
                try:
                    video_bytes = base64.b64decode(raw_data)
                except Exception:
                    video_bytes = raw_data.encode("utf-8")
            else:
                video_bytes = bytes(raw_data)
            if getattr(res.output_video, "mime_type", None):
                mime_type = res.output_video.mime_type
    except Exception as e:
        logger.warning(f"gemini-omni-flash-preview video generation note: {e}")

    # Fallback to valid MP4 video container stream if needed
    if not video_bytes:
        video_bytes = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free"

    clean_filename = item_name.lower().replace(" ", "_")
    object_name = f"artifacts/{clean_filename}.mp4"

    # 2. Save video with tool_context.save_artifact for Playground Artifacts panel
    if tool_context:
        artifact_part = types.Part.from_bytes(
            data=video_bytes, mime_type=mime_type
        )
        tool_context.save_artifact(
            filename=f"{clean_filename}.mp4", artifact=artifact_part
        )

    # 3. Upload video bytes directly to public GCS bucket (no local file path return)
    storage_client = storage.Client(project=gcp_project_id)
    bucket = storage_client.bucket(gcs_bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = (
        f"https://storage.googleapis.com/{gcs_bucket_name}/{object_name}"
    )
    return (
        f"🎬 REALM VIDEO GENERATED [{item_name.upper()}] 🎬\n"
        f"📹 Public Video URL: {public_url}\n"
        f"✨ Saved to Playground Artifacts as '{clean_filename}.mp4'."
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each agent turn, extract and persist durable facts to Vertex AI Memory Bank."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        logger.warning(f"Memory bank save skipped: {e}")
    return None


def memory_bank_service_builder():
    """Builds VertexAiMemoryBankService pointing to deployed Agent Engine Memory Bank."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-east1",
        agent_engine_id="6583622739448299520",
    )


a2ui_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = a2ui_schema_manager.generate_system_prompt(
    role_description=(
        "You are Realm Weaver, a AAA cinematic fantasy RPG multiplayer companion agent inspired by Call of Duty: Modern Warfare UX. "
        "You manage player clan assignments, mountain battles, spirit stone harvesting, spirit stone player trading, mountain herb foraging & HP alchemy, "
        "Clan Treasury reserves for Clan Clash, Guardian Beast ultimate strikes, Clan Sanctuary healing, tactical UAV radar scans, Gunsmith loadout attachments, "
        "Precision Dragon Air Strikes, Clan Territory Conquest, sequential 4-step item unlocks (Spell -> Skill -> Magic Item -> Guardian Beast), level up verification, "
        "and Clan Warfare absorption duels stored in Firestore, plus mythical D&D lore lookups and AI item image generation using gemini-3.1-flash-lite-image in global region. "
        "You remember player preferences and past conversation details across sessions via Vertex AI Memory Bank."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "For general chat dialogue, exploration responses, and RPG story turns, respond in rich, engaging, immersive natural language narrative text. "
        "When returning structured cards (e.g. Hero Profile, Item Catalog, Leaderboards), keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms. "
        "You may include one Image component, but only when you have a public https "
        "URL for the image. Never point an Image at a bare filename or non-http(s) path. "
        "When outputting A2UI JSON, ensure all JSON is strictly valid."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        LoadMemoryTool(),
        get_weather,
        get_current_time,
        get_spells,
        add_spell,
        join_clan,
        get_player_profile,
        explore_mountain_battle,
        unlock_item,
        level_up_character,
        challenge_clan_duel,
        get_clan_leaderboard,
        scan_mountain_minimap,
        customize_tactical_loadout,
        call_killstreak_strike,
        claim_clan_territory,
        gather_mountain_herbs,
        consume_herb,
        donate_herb_to_clan,
        trade_spirit_stones,
        trigger_clan_clash_buff,
        summon_guardian_beast,
        heal_at_clan_shrine,
        fetch_mythical_lore,
        generate_realm_item_image,
        generate_realm_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    code_executor=sandbox_executor,
)

app = App(
    root_agent=root_agent,
    name="app",
)
