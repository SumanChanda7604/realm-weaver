# Realm Weaver 🏰✨

**Realm Weaver** is a AAA cinematic fantasy RPG multiplayer companion agent built using Google's **Agent Development Kit (ADK 1.1.0+)**, **A2UI**, and **Vertex AI Agent Engine**. Inspired by Call of Duty: Modern Warfare UX, it manages player clan assignments, mountain beast battles, spirit stone harvesting, sequential item unlocks, player trading, alchemy foraging, clan warfare duels, AI artwork generation, and AI video creation.

---

## 🌟 Implemented Agent Features & Architecture

### 1. 🤖 Core Agent & AI Models (`app/agent.py`)
* **Gemini Flash (`gemini-flash-latest`)**: Core ReAct reasoning agent handling game logic, story narrative, and tool selection.
* **Vertex AI Memory Bank (`VertexAiMemoryBankService`)**: Persists player preferences, past conversation context, and durable facts across sessions using `generate_memories_callback`.
* **Gemini 3.1 Flash Lite Image (`gemini-3.1-flash-lite-image`)**: Generates custom AI item and battle artwork in the `global` region (`generate_realm_item_image`).
* **Gemini Omni Flash Preview (`gemini-omni-flash-preview`)**: Generates 60fps cinematic 5-second MP4 videos for items, weapons, and clan themes in the `global` region (`generate_realm_video`).

### 2. 📊 Google Cloud Infrastructure
* **Google Cloud Firestore**: Persists player profiles, clan stats (Titan, Dragon, Phoenix, Shadow), level progression, Spirit Stone balances, herb inventories, Clan Treasury balances, and absorption duels (`qwiklabs-gcp-02-c19c65f27e59`).
* **Google Cloud Storage (GCS)**: Stores AI-generated artwork images and item video artifacts in public bucket `realm-weaver-assets-qwiklabs-gcp-02-c19c65f27e59`.
* **Agent Engine Sandbox Code Executor (`AgentEngineSandboxCodeExecutor`)**: Executes python code securely in Vertex AI Agent Engine (`us-east1`).

### 3. 🎨 A2UI Protocol & Modern UX (`app/a2ui_utils.py` & `frontend/static/index.html`)
* **A2UI Protocol Manager (`A2uiSchemaManager` v0.8)**: Generates structured Call of Duty-inspired dark mode UI components (`Card`, `Column`, `Row`, `Text`, `Image`).
* **Streaming A2UI Callback (`a2ui_callback`)**: Automatically transforms model outputs into valid A2UI `beginRendering` and `surfaceUpdate` JSON structures.
* **Responsive Frontend Proxy (`frontend/main.py`)**: FastAPI same-origin proxy communicating with deployed Agent Engine over the A2A protocol.

---

## 🛠️ Implemented Agent Tools

| Tool | Functionality |
| :--- | :--- |
| `join_clan` | Registers a player into Titan, Dragon, Phoenix, or Shadow Clan; seeds starting profile in Firestore. |
| `get_player_profile` | Fetches player level, clan, spirit stones, HP/MP, herb inventory, and sequential unlock stage. |
| `explore_mountain_battle` | Simulates turn-based mountain battles against wild beasts yielding Spirit Stone rewards. |
| `unlock_item` | Enforces 4-step sequential item unlock (`Spell` [10 Stones] $\rightarrow$ `Skill` $\rightarrow$ `Magic Item` $\rightarrow$ `Guardian Beast`). |
| `level_up_character` | Upgrades player character level upon meeting Spirit Stone progression thresholds. |
| `gather_mountain_herbs` | Forages mountain herbs for alchemy and HP restoration. |
| `consume_herb` | Consumes herbs from inventory to restore player HP. |
| `donate_herb_to_clan` | Donates herbs to Clan Treasury to boost clan reserves. |
| `trade_spirit_stones` | Transfers Spirit Stones directly between players. |
| `challenge_clan_duel` | Initiates Clan Warfare absorption duels between rival warlords. |
| `summon_guardian_beast` | Triggers Level 1 Guardian Beast ultimate strike in battle. |
| `trigger_clan_clash_buff` | Activates clan-wide damage and defense multipliers from Treasury. |
| `heal_at_clan_shrine` | Restores full player HP and MP at Clan Sanctuary. |
| `fetch_mythical_lore` | Queries mythical D&D and fantasy lore database. |
| `generate_realm_item_image` | Generates AI item artwork via `gemini-3.1-flash-lite-image` and uploads to public GCS. |
| `generate_realm_video` | Generates 60fps AI item/clan video via `gemini-omni-flash-preview` and saves to Playground Artifacts & public GCS. |
| `scan_mountain_minimap` | Scans regional minimap for high-value targets and environmental hazards. |
| `customize_tactical_loadout` | Customizes weapon attachments and tactical gear. |
| `call_killstreak_strike` | Calls in Precision Dragon Air Strike on enemy territory. |
| `claim_clan_territory` | Captures strategic mountain sectors for the clan. |
| `get_weather` / `get_current_time` | Fetches ambient realm weather and in-game time. |
| `get_spells` / `add_spell` | Retrieves and binds elemental spells to player profile. |

---

## 🎬 Generated Media & Assets (`assets/`)

All AI-generated images (`gemini-3.1-flash-lite-image`), videos (`gemini-omni-flash-preview`), and audio tracks are committed directly in the `assets/` directory:

### 🖼️ AI Artwork
* **Spirit Stone Monster Kill**: `assets/warlord_solariss_hand_holding_a_glowing_spirit_stone_over_the_slayed_mountain_frost_drake.png`
* **Dragonblood Greatsword**: `assets/dragonblood_greatsword.png`
* **Clan Dragon Emblem**: `assets/clan_dragon_emblem.png`
* **Celestial Lotus**: `assets/celestial_lotus.png`

### 📹 AI Clan Theme & Gameplay Videos (Omni Model 60fps)
* **Phoenix Clan Demo**: `assets/phoenix_clan_warlord_solaris_demo.mp4`
* **Titan Clan Sanctuary**: `assets/titan_clan_sanctuary.mp4`
* **Dragon Clan Volcanic Rift**: `assets/dragon_clan_volcanic_rift.mp4`
* **Phoenix Clan Solar Spire**: `assets/phoenix_clan_solar_spire.mp4`
* **Shadow Clan Eclipse Citadel**: `assets/shadow_clan_eclipse_citadel.mp4`
* **Dragonblood Greatsword Item**: `assets/dragonblood_greatsword.mp4`

### 🎵 Lo-Fi Background Audio
* **Phoenix Clan Upbeat Lo-Fi Beat**: `assets/phoenix_clan_lofi_theme.wav`

---

## 📁 Directory Structure

```
realm-weaver/
├── app/                        # Core ADK Agent implementation
│   ├── agent.py                # Main agent definition, tools, memory callbacks, A2UI prompt
│   ├── a2ui_utils.py           # A2UI event payload transformer
│   └── fast_api_app.py         # FastAPI Agent Engine application entrypoint
├── frontend/                   # Web Application & Proxy
│   ├── main.py                 # FastAPI A2A proxy server
│   └── static/
│       └── index.html          # Call of Duty dark mode UI, A2UI renderer, dynamic HUD
├── assets/                     # AI-generated artwork PNGs, Omni MP4 videos, WAV audio
├── agents-cli-manifest.yaml    # ADK deployment manifest
├── pyproject.toml              # Dependencies and project metadata
├── seed_firestore.py           # Firestore database seed script
└── README.md                   # Project documentation
```

---

## 🚀 Setup & Local Execution

### Prerequisites
* **Python 3.11+**
* **uv**: `pip install uv`
* **Google Cloud SDK**: `gcloud auth application-default login`

### 1. Install Dependencies
```bash
uv sync
```

### 2. Seed Firestore Database
```bash
uv run python seed_firestore.py
```

### 3. Run Agent & Web UI Locally
Set environment variables pointing to your Google Cloud project and Agent Engine resource, then launch the FastAPI proxy server:

```bash
export AGENT_ENGINE_RESOURCE_NAME="projects/<YOUR_PROJECT_ID>/locations/us-east1/reasoningEngines/<YOUR_ENGINE_ID>"
export AGENT_DIRECTORY="app"
export PORT=8080

cd frontend
uv run python main.py
```

The web application will start on port `8080`.

---

## ☁️ Deployment Instructions

### Deploy Agent Engine Backend
```bash
agents-cli deploy agent-engine \
  --project <YOUR_PROJECT_ID> \
  --region us-east1
```

### Deploy Frontend Proxy to Cloud Run
```bash
gcloud run deploy realm-weaver-frontend \
  --source frontend \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="projects/<YOUR_PROJECT_ID>/locations/us-east1/reasoningEngines/<YOUR_ENGINE_ID>",AGENT_DIRECTORY="app"
```
