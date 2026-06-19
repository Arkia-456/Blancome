# Blancome

Fully offline voice assistant built in Python, designed for Raspberry Pi. It listens for a wake word, recognizes spoken French commands, and controls music playback and a shopping list — all without any cloud dependency.

**Stack:** `sounddevice` (mic) → `vosk` (STT) → custom command plugins + PyQt6 touchscreen UI

> Built with AI assistance.

---

## Requirements

- Python 3.10+
- A working microphone
- [Vosk French model](https://alphacephei.com/vosk/models) (see setup below)
- _(Optional)_ Free Mobile account for SMS shopping list delivery
- _(Optional)_ Google Cloud project with Calendar API enabled (for Google Calendar)
- _(Optional)_ Azure App Registration with `Calendars.Read` permission (for Microsoft/Outlook Calendar)

---

## Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd HomeAssistant
```

### 2. Install Python dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Download the Vosk speech recognition model

```bash
mkdir -p models && cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip
unzip vosk-model-small-fr-0.22.zip
mv vosk-model-small-fr-0.22 vosk-model
cd ..
```

### 4. Configure environment variables

Copy the example and fill in your values:

```bash
cp .env.example .env
```

| Variable               | Description                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| `PLAYLIST_<NAME>`      | Path to a playlist file (`.m3u8` or `.txt`). Add one per playlist.                       |
| `SHOPPING_LIST_FILE`   | Path to the file where shopping list items are stored.                                   |
| `FREE_MOBILE_USER`     | _(Optional)_ Your Free Mobile phone number, for SMS delivery.                            |
| `FREE_MOBILE_API_KEY`  | _(Optional)_ Your Free Mobile API key.                                                   |
| `GOOGLE_CLIENT_ID`     | _(Optional)_ OAuth 2.0 Client ID from Google Cloud Console (Desktop app type).           |
| `GOOGLE_CLIENT_SECRET` | _(Optional)_ OAuth 2.0 Client Secret from Google Cloud Console.                          |
| `MICROSOFT_CLIENT_ID`  | _(Optional)_ App Registration Client ID from Azure Portal (`Calendars.Read` permission). |

On first run with calendar credentials configured, a browser window will open to complete OAuth authentication. Tokens are cached locally (`google_token.json` / `microsoft_token.json`) and refreshed automatically.

### 5. Run

```bash
python main.py
```

---

## Usage

### Wake word

Say **"blanco"** to activate the assistant before giving any command.

### Commands

All commands are in French.

#### Music

| Phrase                                         | Action                   |
| ---------------------------------------------- | ------------------------ |
| `"musique {playlist}"` or `"lance {playlist}"` | Load and play a playlist |
| `"stop"` or `"arrête"`                         | Stop playback            |
| `"suivant"`                                    | Skip to the next track   |
| `"précédent"`                                  | Play the previous track  |
| `"pause"`                                      | Pause playback           |
| `"reprend"`                                    | Resume playback          |

Playlist names in commands match the suffix of the `PLAYLIST_<NAME>` env variable (case-insensitive).

#### Shopping list

| Phrase                                       | Action                                                            |
| -------------------------------------------- | ----------------------------------------------------------------- |
| `"ajoute/rajoute/mets ... liste de courses"` | Add one or more items to the list                                 |
| `"liste de courses"`                         | Read back the current shopping list                               |
| `"envoie liste"`                             | Send the shopping list via SMS (requires Free Mobile credentials) |

### UI

The assistant launches a full-screen PyQt6 UI showing a clock, upcoming calendar events, a music player card, and a shopping list.

#### Calendar

The UI displays events from Google Calendar and/or Microsoft Outlook (whichever credentials are configured). Events are fetched on startup and refresh automatically. If neither calendar is configured the calendar panel is hidden.

---

## Project structure

```
main.py              # Entry point
config.py            # Environment variable loader
assistant/
  brain.py           # Wake word detection and command routing
  listener.py        # Audio capture and speech-to-text
  player.py          # Music playback with auto-advance
  ui.py              # PyQt6 UI
  calendar_service.py           # Google Calendar integration (OAuth 2.0)
  microsoft_calendar_service.py # Microsoft/Outlook Calendar integration (MSAL)
  shopping_service.py           # Shopping list persistence
  music_service.py              # Music library helper
commands/
  base.py            # Abstract Command class
  music/             # Music control commands
  shopping/          # Shopping list commands
assets/              # UI icons
models/
  vosk-model/        # Vosk French model (downloaded separately)
```
