# HomeAssistant

Fully offline voice assistant built in Python, designed for Raspberry Pi.

**Stack:** `sounddevice` (mic) → `vosk` (STT) → custom commands

## Setup

### 2. Python dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Download the Vosk model

```bash
mkdir -p models && cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip
unzip vosk-model-small-fr-0.22.zip
mv vosk-model-small-fr-0.22 vosk-model
cd ..
```

### 4. Run

```bash
python main.py
```

## Wake word

**"blanco"**

## Commands

### Music

"musique {playlist}" - play the playlist. Playlists are listed in config.py

"musique stop" or "musique arrête" - stop the playback

"musique suivant" - play the next track
