"""
Cross-Platform Motherboard Buzzer Driver
Supports:
- Linux /dev/input event device (evdev pcspkr) with auto-detection
- Linux /dev/console ioctl (KIOCSOUND)
- Linux terminal bell fallback (\a)
- Windows winsound.Beep
"""

import os
import re
import sys
import time
import struct
import glob
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger("valheim-buzzer.driver")

EV_SND = 0x12
SND_TONE = 0x02
KIOCSOUND = 0x4B2F  # Linux ioctl to play tone on /dev/console

def find_linux_pcspkr_device() -> Optional[str]:
    """Auto-detect the event device associated with PC Speaker on Linux."""
    # Method 1: Check by-path symlinks
    for p in glob.glob("/dev/input/by-path/*pcspkr*"):
        try:
            return os.path.realpath(p)
        except Exception:
            pass

    # Method 2: Inspect /proc/bus/input/devices
    if os.path.exists("/proc/bus/input/devices"):
        try:
            with open("/proc/bus/input/devices", "r") as f:
                content = f.read()
            blocks = content.split("\n\n")
            for b in blocks:
                if 'Name="PC Speaker"' in b or 'pcspkr' in b.lower():
                    m = re.search(r"Handlers=.*?event(\d+)", b)
                    if m:
                        ev_num = m.group(1)
                        dev_path = f"/dev/input/event{ev_num}"
                        if os.path.exists(dev_path):
                            return dev_path
        except Exception as e:
            logger.debug(f"Failed to parse /proc/bus/input/devices: {e}")

    # Method 3: Check standard event13 or event0..event30 for SND capability
    for i in range(32):
        dev = f"/dev/input/event{i}"
        if os.path.exists(dev):
            # Check sysfs for snd capability if accessible
            cap_path = f"/sys/class/input/event{i}/device/capabilities/snd"
            if os.path.exists(cap_path):
                try:
                    with open(cap_path, "r") as cf:
                        val = cf.read().strip()
                        if val and val != "0":
                            return dev
                except Exception:
                    pass

    return None


class BaseBuzzerDriver:
    def open(self):
        pass

    def play_tone(self, freq: int, duration_sec: float):
        raise NotImplementedError

    def stop_tone(self):
        pass

    def close(self):
        pass


class WindowsBuzzerDriver(BaseBuzzerDriver):
    def __init__(self):
        import winsound
        self.winsound = winsound

    def play_tone(self, freq: int, duration_sec: float):
        if freq > 37:
            duration_ms = max(10, int(duration_sec * 1000))
            self.winsound.Beep(freq, duration_ms)
        else:
            time.sleep(duration_sec)


class LinuxEvdevBuzzerDriver(BaseBuzzerDriver):
    def __init__(self, device_path: Optional[str] = None):
        self.device_path = device_path or find_linux_pcspkr_device() or "/dev/input/event13"
        self.fd = -1

    def open(self):
        if not os.path.exists(self.device_path):
            raise FileNotFoundError(f"Evdev device '{self.device_path}' not found")
        self.fd = os.open(self.device_path, os.O_WRONLY)

    def play_tone(self, freq: int, duration_sec: float):
        if self.fd < 0:
            return
        # Write SND_TONE event
        ev = struct.pack("qqHHi", 0, 0, EV_SND, SND_TONE, freq)
        os.write(self.fd, ev)
        time.sleep(duration_sec)

    def stop_tone(self):
        if self.fd >= 0:
            ev = struct.pack("qqHHi", 0, 0, EV_SND, SND_TONE, 0)
            os.write(self.fd, ev)

    def close(self):
        if self.fd >= 0:
            try:
                self.stop_tone()
                os.close(self.fd)
            except Exception:
                pass
            self.fd = -1


class LinuxConsoleIoctlBuzzerDriver(BaseBuzzerDriver):
    def __init__(self, console_path: str = "/dev/console"):
        self.console_path = console_path
        self.fd = -1

    def open(self):
        import fcntl
        self.fcntl = fcntl
        self.fd = os.open(self.console_path, os.O_WRONLY)

    def play_tone(self, freq: int, duration_sec: float):
        if self.fd < 0:
            return
        if freq > 0:
            # 1193180 / freq is the 8254 PIT counter ticks
            pitch = int(1193180 / freq)
            self.fcntl.ioctl(self.fd, KIOCSOUND, pitch)
        else:
            self.fcntl.ioctl(self.fd, KIOCSOUND, 0)
        time.sleep(duration_sec)

    def stop_tone(self):
        if self.fd >= 0:
            try:
                self.fcntl.ioctl(self.fd, KIOCSOUND, 0)
            except Exception:
                pass

    def close(self):
        if self.fd >= 0:
            try:
                self.stop_tone()
                os.close(self.fd)
            except Exception:
                pass
            self.fd = -1


class FallbackBellDriver(BaseBuzzerDriver):
    def play_tone(self, freq: int, duration_sec: float):
        if freq > 0:
            sys.stdout.write("\a")
            sys.stdout.flush()
        time.sleep(duration_sec)


def create_driver(mode: str = "auto", device_path: str = "") -> BaseBuzzerDriver:
    """Factory to create appropriate buzzer driver based on OS and config."""
    if sys.platform == "win32" or mode == "windows_beep":
        logger.info("Initializing Windows winsound buzzer driver")
        return WindowsBuzzerDriver()

    # Linux evdev
    if mode in ("auto", "linux_evdev"):
        try:
            d = LinuxEvdevBuzzerDriver(device_path if device_path else None)
            d.open()
            logger.info(f"Initialized Linux evdev buzzer driver on {d.device_path}")
            return d
        except Exception as e:
            logger.warning(f"Could not open evdev buzzer: {e}")
            if mode == "linux_evdev":
                raise

    # Linux console ioctl
    if mode in ("auto", "linux_console"):
        for c in ("/dev/console", "/dev/tty0"):
            if os.path.exists(c):
                try:
                    d = LinuxConsoleIoctlBuzzerDriver(c)
                    d.open()
                    logger.info(f"Initialized Linux console ioctl buzzer driver on {c}")
                    return d
                except Exception as e:
                    logger.debug(f"Could not open {c}: {e}")

    logger.warning("No hardware buzzer available, falling back to terminal bell")
    return FallbackBellDriver()


def play_melody(driver: BaseBuzzerDriver, melody: List[Tuple[int, float, float]]):
    """Play a complete melody list of (freq, duration, rest)."""
    try:
        for freq, duration, pause in melody:
            driver.play_tone(freq, duration)
            driver.stop_tone()
            if pause > 0:
                time.sleep(pause)
    finally:
        driver.stop_tone()
