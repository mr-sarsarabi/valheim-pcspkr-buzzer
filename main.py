#!/usr/bin/env python3
"""
Valheim Motherboard Buzzer Daemon
Listens to Valheim server logs and plays retro chiptune melodies on the hardware buzzer.
"""

import os
import sys
import time
import signal
import threading
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any

from driver import create_driver, play_melody, BaseBuzzerDriver
from sound_packs import get_melody, PACKS
from valheim_parser import parse_log_line

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("valheim-buzzer")

# Global stop flag
stop_event = threading.Event()
play_lock = threading.Lock()
last_event_timestamps: Dict[str, float] = {}

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load config.yaml with fallback parser if PyYAML is absent."""
    default_cfg = {
        "server": {"container_name": "valheim-server", "log_source": "docker", "log_file_path": ""},
        "driver": {"mode": "auto", "device_path": ""},
        "sound_pack": "mario",
        "events": {
            "server_start": {"enabled": True, "cooldown_seconds": 15},
            "player_join": {"enabled": True, "cooldown_seconds": 5},
            "player_leave": {"enabled": False, "cooldown_seconds": 5},
            "player_death": {"enabled": True, "cooldown_seconds": 5},
            "raid_start": {"enabled": True, "cooldown_seconds": 20},
            "boss_spawn": {"enabled": True, "cooldown_seconds": 20},
        }
    }

    if not os.path.exists(config_path):
        logger.warning(f"Config file {config_path} not found. Using defaults.")
        return default_cfg

    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            return cfg or default_cfg
    except Exception as e:
        logger.error(f"Error parsing {config_path} with yaml: {e}. Falling back to default.")
        return default_cfg


def handle_event(event_name: str, detail: str, cfg: Dict[str, Any], driver: BaseBuzzerDriver):
    """Check event rules and trigger buzzer in a background thread."""
    events_cfg = cfg.get("events", {})
    event_info = events_cfg.get(event_name, {"enabled": True, "cooldown_seconds": 5})

    if not event_info.get("enabled", True):
        logger.debug(f"Event '{event_name}' is disabled in config.")
        return

    cooldown = float(event_info.get("cooldown_seconds", 5))
    now = time.time()
    last_time = last_event_timestamps.get(event_name, 0)
    if now - last_time < cooldown:
        logger.debug(f"Event '{event_name}' is on cooldown ({cooldown}s).")
        return

    last_event_timestamps[event_name] = now
    sound_pack_name = cfg.get("sound_pack", "mario")
    melody = get_melody(sound_pack_name, event_name)

    if not melody:
        logger.warning(f"No melody found for event '{event_name}' in pack '{sound_pack_name}'")
        return

    icon_map = {
        "server_start": "🚀",
        "player_join": "⚔️",
        "player_leave": "🚪",
        "player_death": "💀",
        "raid_start": "🔥",
        "boss_spawn": "🐉",
    }
    icon = icon_map.get(event_name, "🔔")
    logger.info(f"{icon} EVENT: [{event_name.upper()}] - {detail} (Playing {sound_pack_name} melody)")

    def _worker():
        if not play_lock.acquire(blocking=False):
            logger.debug("Buzzer currently busy, skipping overlapping sound.")
            return
        try:
            play_melody(driver, melody)
        finally:
            play_lock.release()

    threading.Thread(target=_worker, daemon=True).start()


def monitor_docker_logs(container_name: str, on_line_callback):
    """Stream docker logs using docker CLI."""
    cmd = ["docker", "logs", "-f", "--tail", "0", container_name]
    logger.info(f"Connecting to Docker logs stream for '{container_name}'...")

    while not stop_event.is_set():
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            while not stop_event.is_set():
                line = proc.stdout.readline()
                if not line:
                    break
                on_line_callback(line)

            proc.terminate()
            proc.wait(timeout=2)
        except Exception as e:
            if not stop_event.is_set():
                logger.error(f"Docker logs stream error: {e}. Reconnecting in 5s...")
                time.sleep(5)


def monitor_file_logs(file_path: str, on_line_callback):
    """Tail a regular log file on disk."""
    logger.info(f"Tailing log file: {file_path}")
    if not os.path.exists(file_path):
        logger.warning(f"Log file {file_path} does not exist yet. Waiting...")
        while not os.path.exists(file_path) and not stop_event.is_set():
            time.sleep(2)

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(0, os.SEEK_END)
        while not stop_event.is_set():
            line = f.readline()
            if not line:
                time.sleep(0.2)
                continue
            on_line_callback(line)


def main():
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cfg = load_config(config_file)

    logger.info("=" * 60)
    logger.info("  ⚡ VALHEIM MOTHERBOARD BUZZER DAEMON ⚡")
    logger.info(f"  Sound Pack: {cfg.get('sound_pack', 'mario').upper()}")
    logger.info("=" * 60)

    driver_cfg = cfg.get("driver", {})
    driver = create_driver(
        mode=driver_cfg.get("mode", "auto"),
        device_path=driver_cfg.get("device_path", "")
    )

    def _sig_handler(sig, frame):
        logger.info("Shutting down buzzer daemon...")
        stop_event.set()
        driver.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    def on_line(line: str):
        parsed = parse_log_line(line)
        if parsed:
            event_name, detail = parsed
            handle_event(event_name, detail, cfg, driver)

    server_cfg = cfg.get("server", {})
    source_type = server_cfg.get("log_source", "docker")

    if source_type == "file":
        log_file = server_cfg.get("log_file_path", "")
        monitor_file_logs(log_file, on_line)
    else:
        container_name = server_cfg.get("container_name", "valheim-server")
        monitor_docker_logs(container_name, on_line)


if __name__ == "__main__":
    main()
