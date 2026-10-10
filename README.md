# ⚡ Valheim Motherboard Buzzer

> **Bring your homelab to life!** A lightweight, zero-overhead daemon that listens to Valheim dedicated server events and plays retro 8-bit chiptune melodies directly on your server's physical motherboard buzzer (`pcspkr`).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-cyan.svg)](https://www.docker.com/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey.svg)](https://github.com/)

---

## 🎮 Why?
Because Discord webhooks are boring, and physical server beeps are legendary.  
When a friend connects to your Valheim world, your server greets them with the **Super Mario Overworld Theme**. When someone gets crushed by a falling tree or a troll, your server plays **Mario Death** or **Coffin Dance**. When a raid begins or a boss is summoned, an emergency 8-bit siren alerts everyone in the room!

> ⚠️ **Who is this for?**  
> This project is built specifically for **homelab enthusiasts, self-hosters, and server administrators who run a Valheim dedicated server on physical bare-metal hardware** (such as a local home server, spare PC, or rackmount unit) that has an actual motherboard buzzer / PC speaker (`pcspkr`).  
> **It is NOT an in-game client mod for players**, nor is it meant for cloud VPS instances that lack physical audio transducers.

---

## ✨ Features

- 🔊 **Authentic 8-Bit Chiptunes:** High-precision tuned frequencies, durations, and rests for classic retro gaming tunes.
- 🎯 **Rich Event Detection:**
  - 🚀 **Server Ready:** When the Valheim world finishes loading.
  - ⚔️ **Player Join:** Plays a triumphant entrance fanfare when a character spawns.
  - 🚪 **Player Leave:** Plays a downer chime when a socket closes.
  - 💀 **Player Death:** Detects `ZDOID 0:0` assignment when a player dies in-game.
  - 🔥 **Raid / Event Start:** Urgent alarm when raids trigger (e.g. *"The forest is moving"*).
  - 🐉 **Boss Summon:** Epic boss riff when an altar is activated (Eikthyr, The Elder, Bonemass, Moder, Yagluth, The Queen, Fader).
- 📦 **Pre-built Sound Packs:**
  - **Mario:** Iconic Nintendo theme, Game Over, and underground castle riffs.
  - **Zelda:** Secret item discovery fanfare, Triforce chimes, and dungeon alerts.
  - **Arcade:** Pac-Man intro, Tetris tension theme, and Space Invaders march.
  - **Meme:** Megalovania (Sans), Coffin Dance (Astronomia), Imperial March.
- 🎛️ **Granular Control:** Easily enable/disable any event and set per-event cooldowns in `config.yaml`.
- 🐧🪟 **Cross-Platform Driver:**
  - **Linux:** Automatic `/dev/input/event*` (`pcspkr`) detection, `/dev/console` ioctl (`KIOCSOUND`) fallback, terminal bell fallback.
  - **Windows:** Native `winsound.Beep` integration.
- 🪶 **Extremely Lightweight:** Consumes **0% CPU** and under **17 MB RAM** in Docker.

---

## 🎵 Sound Packs Overview

| Event | 🍄 Mario Pack | ⚔️ Zelda Pack | 🕹️ Arcade Pack | 💀 Meme Pack |
| :--- | :--- | :--- | :--- | :--- |
| **Server Start** | Coin Jingle | Triforce Chime | Insert Coin | Nokia Ringtone |
| **Player Join** | Overworld Main Theme | Secret Found Fanfare | Pac-Man Game Start | Megalovania Riff |
| **Player Leave** | Pipe Down Sound | Warp Chime | Invaders Down | Sad Trombone |
| **Player Death** | Mario Game Over | Link Heart Alarm | Pac-Man Death Siren | Coffin Dance |
| **Raid Start** | Fast Castle Panic | Danger Encounter | Tetris Fast Panic | High-Pitch Emergency |
| **Boss Spawn** | Bowser Battle Riff | Boss Theme Fanfare | Deep Invaders Riff | Imperial March |

---

## 🚀 Quick Start (Docker)

If you already run Valheim in Docker (e.g., `lloesche/valheim-server`):

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mr-sarsarabi/valheim-pcspkr-buzzer.git
   cd valheim-pcspkr-buzzer
   ```

2. **Verify your speaker device (Linux):**
   ```bash
   lsmod | grep pcspkr
   # Ensure the kernel module is loaded:
   sudo modprobe pcspkr
   ```

3. **Start with Docker Compose:**
   ```bash
   docker compose up -d
   ```

4. **View live logs:**
   ```bash
   docker logs -f valheim-buzzer
   ```

---

## 🛠️ Bare-Metal Setup (Linux & Windows)

### Linux (Systemd / Background)
```bash
# 1. Install requirements
pip install -r requirements.txt

# 2. Run the daemon
sudo python3 main.py config.yaml
```
*(Root or membership in the `input` group is required to write to `/dev/input/event*`).*

### Windows (Local Dedicated Server)
```cmd
pip install -r requirements.txt
python main.py config.yaml
```
*On Windows, set `driver.mode: "windows_beep"` and `server.log_source: "file"` with your `log_file_path` in `config.yaml`.*

---

## ⚙️ Configuration (`config.yaml`)

```yaml
server:
  container_name: "valheim-server"
  log_source: "docker" # "docker" or "file"
  log_file_path: ""

driver:
  mode: "auto" # "auto", "linux_evdev", "linux_console", "windows_beep"
  device_path: "" # Auto-detected on Linux if empty

sound_pack: "mario" # Choose: "mario", "zelda", "arcade", "meme"

events:
  server_start:
    enabled: true
    cooldown_seconds: 15
  player_join:
    enabled: true
    cooldown_seconds: 5
  player_leave:
    enabled: false
    cooldown_seconds: 5
  player_death:
    enabled: true
    cooldown_seconds: 5
  raid_start:
    enabled: true
    cooldown_seconds: 20
  boss_spawn:
    enabled: true
    cooldown_seconds: 20
```

To switch a sound pack or disable an event, simply edit `config.yaml` and restart the daemon:
```bash
docker restart valheim-buzzer
```

---

## 🤝 Contributing

Contributions are very welcome!
- Have an awesome 8-bit melody? Add it to `sound_packs.py`!
- Found a new event pattern in the latest Valheim update? Submit a PR!

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.
