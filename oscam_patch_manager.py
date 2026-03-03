#!/usr/bin/env python3
# =====================================================================
#  OSCam Emu Patch Generator
#
#  Copyright (c) 2026 speedy005
#
#  Author: speedy005
#
#  License: MIT
#
#  IMPORTANT NOTICE:
#  This project is Open Source under the MIT License.
#  The author name "speedy005" must NOT be removed, changed,
#  or replaced in any modified or redistributed version.
#
#  Any redistribution or modification must retain this
#  copyright notice and author attribution.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# =====================================================================
import sys
import os
import json
import shutil
import subprocess
import stat
import platform
import re

HAS_SOUND_SUPPORT = False

import subprocess, os, platform, shutil, ctypes

import re

ONLINE_PATCHES = {
    "speedy005 (Master)": "https://raw.githubusercontent.com/speedy005/oscam-emu-patch/refs/heads/master/oscam-emu.patch",
    "OSCam-Mirror (Master)": "https://raw.githubusercontent.com/oscam-mirror/oscam-emu-patch/refs/heads/master/oscam-emu.patch",
}


def install_font_ubuntu():
    """Installiert Noto Color Emoji auf Ubuntu-basierten Systemen."""
    try:
        # Öffnet ein Terminal für das sudo-Passwort des Nutzers
        cmd = "sudo apt update && sudo apt install -y fonts-noto-color-emoji && fc-cache -f -v"
        subprocess.check_call(
            [
                "gnome-terminal",
                "--",
                "bash",
                "-c",
                f"{cmd}; read -p 'Fertig! Drücken Sie Enter...'",
            ]
        )
        return True
    except Exception:
        return False


def install_font_windows():
    """Installiert die Emoji-Schriftart für Windows (Admin-Rechte erforderlich)."""
    import requests

    url = "https://github.com"
    font_path = os.path.join(os.environ["WINDIR"], "Fonts", "NotoColorEmoji.ttf")
    try:
        if not os.path.exists(font_path):
            r = requests.get(url, timeout=10)
            with open(font_path, "wb") as f:
                f.write(r.content)
            # In Registry registrieren & System informieren
            ctypes.windll.gdi32.AddFontResourceW(font_path)
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
        return True
    except Exception:
        return False


CONFIG_FILE = "config.json"


def get_setting(key, default=True):
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get(key, default)
    except:
        pass
    return default


def save_setting(key, value):
    settings = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                settings = json.load(f)
        except:
            pass
    settings[key] = value
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f)


def ensure_dependencies():
    """Prüft Python, System-Tools, Sound-Support und zählt die Nutzung (wenn erlaubt)."""
    global HAS_SOUND_SUPPORT
    import importlib.util
    import shutil
    import platform
    import locale
    import subprocess
    import sys
    import os
    import json

    # Zukunftssichere Spracherkennung
    try:
        loc = locale.getlocale()[0] or locale.getdefaultlocale()[0] or "en"
        lang = loc[:2].lower()
    except:
        lang = "en"

    # Lokalisierte Texte
    if lang == "de":
        T_PY_MISSING = "Fehlende Python-Pakete:"
        T_PY_PROMPT = "Möchten Sie diese jetzt automatisch installieren? (j/n): "
        T_SYS_TITLE = "System-Anforderungen"
        T_SYS_TEXT = "Erforderliche Programme fehlen!"
        T_SYS_INFO = "Bitte installieren Sie: "
        T_LINUX_CMD = "Befehl für das Terminal:"
    else:
        T_PY_MISSING = "Missing Python packages:"
        T_PY_PROMPT = "Would you like to install them now? (y/n): "
        T_SYS_TITLE = "System Requirements"
        T_SYS_TEXT = "Required programs missing!"
        T_SYS_INFO = "Please install: "
        T_LINUX_CMD = "Terminal command:"

    # 1. PYTHON PAKETE PRÜFEN
    required_python = ["PyQt6", "requests", "packaging"]
    missing_python = [
        pkg for pkg in required_python if importlib.util.find_spec(pkg) is None
    ]

    if missing_python:
        print(f"\n[INFO] {T_PY_MISSING} {', '.join(missing_python)}")
        choice = input(T_PY_PROMPT)
        if choice.lower() in ["j", "y"]:
            for pkg in missing_python:
                print(f"Installing {pkg}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            os.execv(sys.executable, [sys.executable] + sys.argv)
        sys.exit(1)

    # --- COUNTER LOGIK MIT OPT-OUT PRÜFUNG ---
    # Prüft beim Start, ob der User in der GUI (JSON) zugestimmt hat
    if get_setting("allow_telemetry", True):
        try:
            import requests

            # Nutzt deinen spezifischen Counter-Link für präzise Statistiken
            tracking_url = "https://hits.seeyoufarm.com"

            # Kurzer Timeout (3s), damit das Tool bei fehlendem Internet nicht hängt
            requests.get(tracking_url, timeout=3)
        except Exception:
            # Lautloser Fehler: Falls offline oder Server down, startet das Tool trotzdem normal
            pass
    # -----------------------------------------------------------------

    # 2. SYSTEM TOOLS PRÜFEN (git, patch)
    required_tools = ["git", "patch"]
    missing_tools = [t for t in required_tools if shutil.which(t) is None]

    if missing_tools:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        _ = QApplication.instance() or QApplication(sys.argv)

        msg = f"{T_SYS_INFO} {', '.join(missing_tools)}\n\n"
        if platform.system() == "Linux":
            msg += f"{T_LINUX_CMD}\nsudo apt update && sudo apt install {' '.join(missing_tools)}"
        else:
            msg += f"Please install {', '.join(missing_tools)} and add it to your PATH."

        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(T_SYS_TITLE)
        box.setText(T_SYS_TEXT)
        box.setInformativeText(msg)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()
        sys.exit(1)

    # 3. SOUND-CHECK
    if platform.system() == "Linux":
        HAS_SOUND_SUPPORT = shutil.which("paplay") is not None
    else:
        HAS_SOUND_SUPPORT = True


from datetime import datetime, timezone
from PyQt6.QtGui import QFont, QColor, QTextCursor, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QSizePolicy,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize
import subprocess
import sys
import importlib.util
from PyQt6.QtWidgets import QMessageBox

from PyQt6.QtCore import QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsColorizeEffect


class OSCamUpdateWorker(QThread):
    """Prüft im Hintergrund, ob im Streamboard-Git neue Commits vorliegen."""

    status_signal = pyqtSignal(bool, str)  # (Update verfügbar?, Neuer Hash)

    def __init__(self, remote_url, local_path):
        super().__init__()
        self.remote_url = remote_url
        self.local_path = local_path

    def run(self):
        try:
            # 1. Remote HEAD Hash abrufen
            cmd_remote = ["git", "ls-remote", self.remote_url, "HEAD"]
            remote_out = subprocess.check_output(cmd_remote, text=True, stderr=subprocess.DEVNULL).split()
            if not remote_out:
                return
            remote_hash = remote_out[0]

            # 2. Lokalen Hash prüfen
            local_hash = ""
            if os.path.exists(os.path.join(self.local_path, ".git")):
                cmd_local = ["git", "-C", self.local_path, "rev-parse", "HEAD"]
                local_hash = subprocess.check_output(cmd_local, text=True, stderr=subprocess.DEVNULL).strip()

            # 3. Vergleich & Signal senden
            update_available = (remote_hash != local_hash)
            self.status_signal.emit(update_available, remote_hash)
        except Exception as e:
            print(f"Update-Check Fehler: {e}")
            self.status_signal.emit(False, "")


def check_and_install_dependencies(required_packages):
    missing_packages = []
    for pkg in required_packages:
        if importlib.util.find_spec(pkg) is None:
            missing_packages.append(pkg)

    if missing_packages:
        # Falls PyQt6 fehlt, können wir keine MessageBox zeigen!
        if "PyQt6" in missing_packages:
            print(f"\n⚠️ Fehlende Komponenten: {', '.join(missing_packages)}")
            choice = input("Möchten Sie diese jetzt via pip installieren? (j/n): ")
            if choice.lower() == "j":
                for pkg in missing_packages:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                # Neustart des Skripts
                os.execv(sys.executable, [sys.executable] + sys.argv)
                return True
            return False

        # Wenn PyQt6 vorhanden ist, aber andere (wie requests) fehlen:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        temp_app = QApplication.instance() or QApplication(sys.argv)

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Fehlende Komponenten")
        msg.setText(f"Folgende Bibliotheken fehlen: {', '.join(missing_packages)}")
        msg.setInformativeText("Möchten Sie diese jetzt installieren?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if msg.exec() == QMessageBox.StandardButton.Yes:
            for pkg in missing_packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            # Neustart des Skripts nach Installation
            os.execv(sys.executable, [sys.executable] + sys.argv)
            return True
    return False


# ===================== GLOBALE SOUND-SICHERHEIT=====================
HAS_PAPLAY = shutil.which("paplay") is not None


def safe_play(sound_name):
    """Spielt Sounds nur ab, wenn paplay existiert, sonst Beep."""
    if platform.system() == "Linux":
        # Nutzt die globale Variable HAS_PAPLAY, die oben gesetzt wurde
        s_path = f"/usr/share/sounds/freedesktop/stereo/{sound_name}"
        if HAS_PAPLAY and os.path.exists(s_path):
            try:
                subprocess.Popen(
                    ["paplay", s_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except:
                pass

    # Fallback, wenn Linux ohne paplay oder Windows/Mac
    from PyQt6.QtWidgets import QApplication

    QApplication.beep()


# ===================== VERSION HANDLING =====================
try:
    from packaging.version import Version, InvalidVersion
except (ImportError, ModuleNotFoundError):

    class Version:
        def __init__(self, vstring):
            self.v = [
                int(x) for x in re.sub(r"[^0-9.]", "", str(vstring)).split(".") if x
            ]

        def __gt__(self, other):
            return self.v > other.v

        def __lt__(self, other):
            return self.v < other.v

        def __ge__(self, other):
            return self.v >= other.v

        def __le__(self, other):
            return self.v <= other.v

        def __eq__(self, other):
            return self.v == other.v

    class InvalidVersion(Exception):
        pass


# ===================== ENV SETUP =====================
# Git Fehler unterdrücken
if platform.system() == "Windows":
    os.environ["GIT_REDIRECT_STDERR"] = "2>nul"
else:
    os.environ["GIT_REDIRECT_STDERR"] = "2>/dev/null"
# ===================== SCRIPT DIR =====================
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


def ensure_executable_self():
    """Setzt Ausführungsrechte für das eigene Skript (Linux/Unix)."""
    try:
        st = os.stat(__file__)
        if not (st.st_mode & stat.S_IXUSR):
            os.chmod(__file__, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception as e:
        print(f"[WARN] Konnte Rechte nicht setzen: {e}")


# ===================== ZEIT =====================
now = QDateTime.currentDateTime()
time_str = now.toString("HH:mm:ss")
date_str = now.toString("dd.MM.yyyy")
# ===================== APP CONFIG =====================
APP_VERSION = "4.1.0"


# ===================== PATCH DIRS =====================
def get_best_patch_dir():
    """Bestimmt den besten Patch-Ordner (S3, lokal, Home)."""
    s3_path = "/opt/s3/support/patches"
    if os.path.exists(s3_path) and os.access(s3_path, os.W_OK):
        return s3_path

    local_path = os.path.join(PLUGIN_DIR, "patches")
    home_fallback = os.path.join(os.path.expanduser("~"), ".oscam_patch_manager")

    os.makedirs(local_path, exist_ok=True)
    return local_path


def get_initial_patch_dir():
    """Wählt den sichersten Backup-Ordner je nach OS."""
    folder_name = "backup"
    if platform.system() == "Windows":
        path = os.path.join(PLUGIN_DIR, folder_name)
    else:
        s3_path = "/opt/s3/support/patches"
        if os.path.exists(s3_path) and os.access(s3_path, os.W_OK):
            path = s3_path
        else:
            path = os.path.join(PLUGIN_DIR, folder_name)

    os.makedirs(path, exist_ok=True)
    return path


# 1. Zuerst das Hauptverzeichnis definieren
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__)) 
WORK_DIR = PLUGIN_DIR

# 2. Jetzt alle Pfade definieren, die auf PLUGIN_DIR basieren
PYC_FILE = os.path.join(PLUGIN_DIR, "oscam_patch_manager.pyc")
CACHE_DIR = os.path.join(PLUGIN_DIR, "__pycache__")
CONFIG_FILE = os.path.join(PLUGIN_DIR, "config.json")
GITHUB_CONF_FILE = os.path.join(PLUGIN_DIR, "github_upload_config.json")
PATCH_FILE = os.path.join(PLUGIN_DIR, "oscam-emu.patch")
ZIP_FILE = os.path.join(PLUGIN_DIR, "oscam-emu.zip")
ICON_DIR = os.path.join(PLUGIN_DIR, "icons")

# 3. Verzeichnisse für Repos
TEMP_REPO = os.path.join(PLUGIN_DIR, "temp_repo")
PATCH_EMU_GIT_DIR = os.path.join(PLUGIN_DIR, "oscam-emu-git")

# 4. Alte/Backup Pfade (Falls get_initial_patch_dir() existiert)
OLD_PATCH_DIR = get_initial_patch_dir()
OLD_PATCH_DIR_PLUGIN_DEFAULT = OLD_PATCH_DIR
OLD_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.patch")
ALT_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.altpatch")
PATCH_MANAGER_OLD = os.path.join(OLD_PATCH_DIR, "oscam_patch_manager_old.py")
CONFIG_OLD = os.path.join(OLD_PATCH_DIR, "config_old.json")
GITHUB_CONFIG_OLD = os.path.join(OLD_PATCH_DIR, "github_upload_config_old.json")
# ===================== TOOLS & REPOS =====================                                                
CHECK_TOOLS_SCRIPT = os.path.join(PLUGIN_DIR, "check_tools.sh")
PATCH_MODIFIER = "speedy005"
EMUREPO = "https://github.com/oscam-mirror/oscam-emu.git"
STREAMREPO = "https://git.streamboard.tv/common/oscam.git"
# ===================== ORDNER-ERSTELLUNG =====================
# Sicherstellen, dass alle 4 Basis-Ordner physisch existieren
for d in [WORK_DIR, TEMP_REPO, PATCH_EMU_GIT_DIR, OLD_PATCH_DIR]:
    if d and not os.path.exists(d):
        try:
            # Erstellt den Ordner (und falls nötig Zwischenordner)
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            # Falls z.B. Schreibrechte in /opt/patch fehlen
            print(f"Fehler beim Erstellen von {d}: {e}")

from PyQt6.QtWidgets import QLayout, QSizePolicy, QWidgetItem
from PyQt6.QtCore import QRect, QSize, Qt, QPoint


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=5):
        super().__init__(parent)
        self.item_list = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self.item_list.append(item)

    def addWidget(self, widget):
        self.addItem(QWidgetItem(widget))

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            # Wir nehmen die echte MinimumSize des Widgets (deine 40px oder 60px)
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()  # Korrigiert von getContentsMargins
        size += QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )
        return size

    def do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        space = self.spacing()

        for item in self.item_list:
            # FIX: Wir holen uns die Größe, aber lassen sie NICHT dynamisch ändern
            # Wenn der Button eine feste Höhe hat (setMinimumHeight), nutzen wir diese.
            widget_size = item.sizeHint()

            # Falls der Button im Klick-Zustand versucht zu wachsen,
            # nehmen wir stattdessen die Mindestgröße (die du im Code fixiert hast).
            if item.widget():
                w = item.widget()
                # Falls eine feste Breite/Höhe gesetzt wurde, nutzen wir diese strikt
                final_width = widget_size.width()
                final_height = widget_size.height()
                widget_size = QSize(final_width, final_height)

            next_x = x + widget_size.width() + space

            # Zeilenumbruch-Logik
            if next_x - space > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + space
                next_x = x + widget_size.width() + space
                line_height = 0

            if not test_only:
                # Hier wird die Geometrie SCHREIBGESCHÜTZT gesetzt.
                # Der Button hat keine Chance mehr, sich beim Klick auszudehnen.
                item.setGeometry(QRect(QPoint(x, y), widget_size))

            x = next_x
            line_height = max(line_height, widget_size.height())

        return y + line_height - rect.y()


def ensure_dir(directory):
    """
    Erstellt das Verzeichnis, falls es noch nicht existiert.
    Optimiert für Pfadsicherheit und Fehlerhandling.
    """
    if not directory:
        return

    if not os.path.exists(directory):
        try:
            # exist_ok=True verhindert Fehler, falls ein anderer Prozess
            # das Verzeichnis im selben Moment erstellt
            os.makedirs(directory, exist_ok=True)
            print(f"[INFO] Verzeichnis erstellt: {directory}")
        except OSError as e:
            # Spezielles Handling für Berechtigungsfehler (z.B. in /opt/s3)
            print(f"[ERROR] Zugriff verweigert oder Pfad ungültig: {directory} ({e})")
        except Exception as e:
            print(f"[ERROR] Unbekannter Fehler beim Erstellen von {directory}: {e}")


from PyQt6.QtCore import QObject, pyqtSignal


class StreamToGui(QObject):
    """Sichere Weiterleitung von stdout an die GUI mittels Signalen."""

    new_text = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def write(self, text):
        if text.strip():
            self.new_text.emit(str(text))

    def flush(self):
        pass


# ===================== NEVER_DELETE =====================
NEVER_DELETE = [
    "oscam_patch_manager.py",
    "clean_texts.py",
    "def.py",
    "extract_text_keys.py",
    "texts_cleaned.py",
    "oscam-emu-patch.sh",
    "github_upload_config.json",
    "oscam-patch.sh",
    "config.json",
    "check_tools.sh",
    "icons",
]

# ===================== COLORS =====================
DIFF_COLORS = {
    "Acid": {
        "bg": "#1D1D1D",
        "fg": "#DFFF00",
        "hover": "#BFFF00",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Aero": {
        "bg": "#00B8D4",
        "fg": "#FFFFFF",
        "hover": "#00E5FF",
        "active": "#0091EA",
        "window_bg": "#2F2F2F",
    },
    "Afterglow": {
        "bg": "#2C2C2C",
        "fg": "#E57373",
        "hover": "#FF8A65",
        "active": "#D32F2F",
        "window_bg": "#2F2F2F",
    },
    "Alien": {
        "bg": "#00FF41",
        "fg": "#000000",
        "hover": "#008F11",
        "active": "#003B00",
        "window_bg": "#2F2F2F",
    },
    "Amethyst": {
        "bg": "#9C27B0",
        "fg": "#E1BEE7",
        "hover": "#BA68C8",
        "active": "#7B1FA2",
        "window_bg": "#2F2F2F",
    },
    "Anthrazit": {
        "bg": "#2F2F2F",
        "fg": "#FFFFFF",
        "hover": "#3D3D3D",
        "active": "#242424",
        "window_bg": "#2F2F2F",
    },
    "Arctic": {
        "bg": "#000000",
        "fg": "#00D2FF",
        "hover": "#0081FF",
        "active": "#00458B",
        "window_bg": "#2F2F2F",
    },
    "Asphalt": {
        "bg": "#263238",
        "fg": "#ECEFF1",
        "hover": "#37474F",
        "active": "#102027",
        "window_bg": "#2F2F2F",
    },
    "Atomic": {
        "bg": "#1A1A1A",
        "fg": "#7FFF00",
        "hover": "#32CD32",
        "active": "#006400",
        "window_bg": "#2F2F2F",
    },
    "Aurora": {
        "bg": "#004D40",
        "fg": "#80CBC4",
        "hover": "#00897B",
        "active": "#002420",
        "window_bg": "#2F2F2F",
    },
    "Biohazard": {
        "bg": "#003300",
        "fg": "#39FF14",
        "hover": "#00FF41",
        "active": "#001100",
        "window_bg": "#2F2F2F",
    },
    "Blackout": {
        "bg": "#000000",
        "fg": "#444444",
        "hover": "#222222",
        "active": "#111111",
        "window_bg": "#2F2F2F",
    },
    "Blaze": {
        "bg": "#E65100",
        "fg": "#FFCC80",
        "hover": "#EF6C00",
        "active": "#BF360C",
        "window_bg": "#2F2F2F",
    },
    "BloodMoon": {
        "bg": "#330000",
        "fg": "#FF0000",
        "hover": "#660000",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Bordeaux": {
        "bg": "#800000",
        "fg": "#FFFFFF",
        "hover": "#A52A2A",
        "active": "#5D0000",
        "window_bg": "#2F2F2F",
    },
    "Bubblegum": {
        "bg": "#F06292",
        "fg": "#F8BBD0",
        "hover": "#F48FB1",
        "active": "#C2185B",
        "window_bg": "#2F2F2F",
    },
    "Bumblebee": {
        "bg": "#FFCC00",
        "fg": "#000000",
        "hover": "#000000",
        "active": "#333300",
        "window_bg": "#2F2F2F",
    },
    "Candy": {
        "bg": "#FF80AB",
        "fg": "#FCE4EC",
        "hover": "#F06292",
        "active": "#C2185B",
        "window_bg": "#2F2F2F",
    },
    "Carbon": {
        "bg": "#232323",
        "fg": "#E0E0E0",
        "hover": "#111111",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Classics": {
        "bg": "#3a6ea5",
        "fg": "#FFFFFF",
        "hover": "#4a7eb5",
        "active": "#2a5e95",
        "window_bg": "#2F2F2F",
    },
    "Coffee": {
        "bg": "#4E342E",
        "fg": "#D7CCC8",
        "hover": "#5D4037",
        "active": "#3E2723",
        "window_bg": "#2F2F2F",
    },
    "Copper": {
        "bg": "#3E2723",
        "fg": "#D84315",
        "hover": "#BF360C",
        "active": "#260E04",
        "window_bg": "#2F2F2F",
    },
    "Cosmos": {
        "bg": "#130f40",
        "fg": "#f093fb",
        "hover": "#30336b",
        "active": "#130f40",
        "window_bg": "#2F2F2F",
    },
    "Crimson": {
        "bg": "#000000",
        "fg": "#DC143C",
        "hover": "#800000",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Cyberpunk": {
        "bg": "#000000",
        "fg": "#00FFFF",
        "hover": "#F305FF",
        "active": "#FF0055",
        "window_bg": "#2F2F2F",
    },
    "DeepBlack": {
        "bg": "#1A1A1A",
        "fg": "#FFD700",
        "hover": "#333333",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "DeepSea": {
        "bg": "#001219",
        "fg": "#94D2BD",
        "hover": "#0A9396",
        "active": "#005F73",
        "window_bg": "#2F2F2F",
    },
    "DeepSpace": {
        "bg": "#0B0D17",
        "fg": "#00D4FF",
        "hover": "#005F73",
        "active": "#001219",
        "window_bg": "#2F2F2F",
    },
    "Dracula": {
        "bg": "#282A36",
        "fg": "#BD93F9",
        "hover": "#44475A",
        "active": "#191A21",
        "window_bg": "#2F2F2F",
    },
    "Electric": {
        "bg": "#0000FF",
        "fg": "#FFFF00",
        "hover": "#00FFFF",
        "active": "#00008B",
        "window_bg": "#2F2F2F",
    },
    "Emerald": {
        "bg": "#2E7D32",
        "fg": "#FFFFFF",
        "hover": "#388E3C",
        "active": "#1B5E20",
        "window_bg": "#2F2F2F",
    },
    "Forest": {
        "bg": "#1B5E20",
        "fg": "#E8F5E9",
        "hover": "#2E7D32",
        "active": "#0D5302",
        "window_bg": "#2F2F2F",
    },
    "Frost": {
        "bg": "#000000",
        "fg": "#A5F2F3",
        "hover": "#FFFFFF",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Fusion": {
        "bg": "#2A0845",
        "fg": "#FFCC00",
        "hover": "#6441A5",
        "active": "#1A052D",
        "window_bg": "#2F2F2F",
    },
    "Galaxy": {
        "bg": "#0D001A",
        "fg": "#9D50BB",
        "hover": "#6E48AA",
        "active": "#300055",
        "window_bg": "#2F2F2F",
    },
    "Ghost": {
        "bg": "#F5F5F5",
        "fg": "#212121",
        "hover": "#E0E0E0",
        "active": "#BDBDBD",
        "window_bg": "#2F2F2F",
    },
    "Glitch": {
        "bg": "#000000",
        "fg": "#FF00FF",
        "hover": "#00FFFF",
        "active": "#FFFFFF",
        "window_bg": "#2F2F2F",
    },
    "Gold": {
        "bg": "#FFD700",
        "fg": "#000000",
        "hover": "#FFEA70",
        "active": "#DAA520",
        "window_bg": "#2F2F2F",
    },
    "Graphite": {
        "bg": "#424242",
        "fg": "#B0BEC5",
        "hover": "#616161",
        "active": "#212121",
        "window_bg": "#2F2F2F",
    },
    "Hazard": {
        "bg": "#000000",
        "fg": "#FFFF00",
        "hover": "#444400",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Horizon": {
        "bg": "#1C1C1C",
        "fg": "#FF4E50",
        "hover": "#F9D423",
        "active": "#D33030",
        "window_bg": "#2F2F2F",
    },
    "HotPink": {
        "bg": "#FF69B4",
        "fg": "#FFFFFF",
        "hover": "#FF1493",
        "active": "#C71585",
        "window_bg": "#2F2F2F",
    },
    "HyperSpace": {
        "bg": "#000000",
        "fg": "#FFFFFF",
        "hover": "#1A1A1A",
        "active": "#FFFFFF",
        "window_bg": "#2F2F2F",
    },
    "Iceberg": {
        "bg": "#E1F5FE",
        "fg": "#01579B",
        "hover": "#FFFFFF",
        "active": "#B3E5FC",
        "window_bg": "#2F2F2F",
    },
    "Inferno": {
        "bg": "#212121",
        "fg": "#FF4500",
        "hover": "#FF8C00",
        "active": "#8B0000",
        "window_bg": "#2F2F2F",
    },
    "Iridium": {
        "bg": "#101010",
        "fg": "#E0E0E0",
        "hover": "#FF0055",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Jungle": {
        "bg": "#1B5E20",
        "fg": "#C8E6C9",
        "hover": "#2E7D32",
        "active": "#003300",
        "window_bg": "#2F2F2F",
    },
    "Kryptonite": {
        "bg": "#0A0F0A",
        "fg": "#9DFF00",
        "hover": "#4DFF00",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Laser": {
        "bg": "#000000",
        "fg": "#FF003C",
        "hover": "#9D00FF",
        "active": "#45001A",
        "window_bg": "#2F2F2F",
    },
    "Lava": {
        "bg": "#4E0000",
        "fg": "#FF3300",
        "hover": "#FF6600",
        "active": "#220000",
        "window_bg": "#2F2F2F",
    },
    "Magma": {
        "bg": "#000000",
        "fg": "#FF0000",
        "hover": "#660000",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Matrix_Pro": {
        "bg": "#000000",
        "fg": "#00FF41",
        "hover": "#003B00",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Midnight": {
        "bg": "#1A1A1A",
        "fg": "#F7F7F7",
        "hover": "#333333",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "MidnightBlue": {
        "bg": "#1A237E",
        "fg": "#C5CAE9",
        "hover": "#283593",
        "active": "#0D1137",
        "window_bg": "#2F2F2F",
    },
    "Misty": {
        "bg": "#90A4AE",
        "fg": "#ECEFF1",
        "hover": "#B0BEC5",
        "active": "#546E7A",
        "window_bg": "#2F2F2F",
    },
    "Nebula": {
        "bg": "#1A0033",
        "fg": "#00FFD1",
        "hover": "#7000FF",
        "active": "#0D001A",
        "window_bg": "#2F2F2F",
    },
    "Neon": {
        "bg": "#000000",
        "fg": "#00FF00",
        "hover": "#003300",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Nordic": {
        "bg": "#2E3440",
        "fg": "#D8DEE9",
        "hover": "#3B4252",
        "active": "#242933",
        "window_bg": "#2F2F2F",
    },
    "Nuclear": {
        "bg": "#1A1A1A",
        "fg": "#CCFF00",
        "hover": "#333333",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Obsidian": {
        "bg": "#050505",
        "fg": "#555555",
        "hover": "#EAFF00",
        "active": "#222222",
        "window_bg": "#2F2F2F",
    },
    "Overdrive": {
        "bg": "#120000",
        "fg": "#FF8000",
        "hover": "#FF0000",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Plasma": {
        "bg": "#000022",
        "fg": "#3D5AFE",
        "hover": "#8C9EFF",
        "active": "#1A237E",
        "window_bg": "#2F2F2F",
    },
    "Riddler": {
        "bg": "#000000",
        "fg": "#19FF19",
        "hover": "#6B00B3",
        "active": "#002200",
        "window_bg": "#2F2F2F",
    },
    "Supernova": {
        "bg": "#000000",
        "fg": "#FFFFFF",
        "hover": "#FFEA00",
        "active": "#FF3D00",
        "window_bg": "#2F2F2F",
    },
    "Vaporwave": {
        "bg": "#2D004F",
        "fg": "#00FFA3",
        "hover": "#FF44CC",
        "active": "#120021",
        "window_bg": "#2F2F2F",
    },
}

current_diff_colors = DIFF_COLORS["Classics"]
current_color_name = "Classics"


def fill_missing_keys(texts):
    """
    Prüft, ob alle Keys aus 'en' auch in 'de' existieren.
    Fehlt ein Key, wird er automatisch aus 'en' übernommen.
    """
    en_keys = texts.get("en", {})
    de_keys = texts.get("de", {})

    for key, value in en_keys.items():
        if key not in de_keys:
            de_keys[key] = value  # Englische Version als Platzhalter

    texts["de"] = de_keys


# ===================== LANGUAGE =====================
LANG = "de"
TEXTS = {
    "en": {
        # Grid Buttons / Patch Aktionen
        "patch_create": "Create Patch",
        "patch_renew": "Renew Patch",
        "patch_check": "Check Patch",
        "settings_header": "Settings",
        # "patch_save_label": "Save Patch",
        "patch_apply": "Apply Patch",
        "patch_path_label": "Save Patch",
        "patch_zip": "Zip Patch",
        "backup_old": "S3-Backup/Renew Patch",
        "clean_folder": "Clean Patch Folder",
        "change_old_dir": "Select S3 Patch Folder",
        # Commits
        "loading_commits": "Loading commits...",
        "commits_loaded": "Commits successfully loaded",
        # Githup Upload
        "github_config_load": "Loading GitHub configuration...",
        "github_emu_git_missing": "Error: GitHub configuration incomplete (URL, token, or user missing).",
        "patch_emu_git_missing": "Error: Local source directory not found: {path}",
        "git_repo_init": "Initializing new git repository in target folder...",
        "git_remote_add": "Linking local repository to GitHub...",
        "git_remote_update": "Updating remote connection...",
        "git_fetching": "Fetching current data from GitHub repository...",
        "plugin_uptodate": "✅ Plugin is up to date (Version: {current})",
        "tools_ok": "✅ All required system tools are already installed.",
        "checking_tools": "Starting system tool check...",
        "git_config_user": "Setting git user data ({user_name})...",
        "git_adding_files": "Indexing files for upload...",
        "git_committing": "Creating commit...",
        "github_upload_start": "Starting upload to GitHub (push)...",
        "github_emu_git_uploaded": "Upload completed successfully!",
        "github_emu_git_revision": "Uploaded revision {sha}. Message: {commit_msg}",
        "github_upload_failed": "Failed to upload to GitHub!",
        # ... tool first start check ...
        "log_start_header": "--- OSCam Emu Patch Generator v{} ---",
        "log_sys_info": "System: {} {}",
        "log_dep_check": "Prüfung: Git ({}), Patch ({}), Sound ({})",
        "log_status_ok": "Status: Alle Abhängigkeiten geladen. Bereit.",
        "ok": "OK",
        "missing": "FEHLT",
        "active": "Aktiv",
        "inactive": "Inaktiv",
        # --- Header & GroupBoxes ---
        "settings_header": "⚙️ Settings",
        "github_config_header": "📁 GitHub Configuration",
        # --- Labels ---
        "language_label": "Language:",
        "color_label": "Style / Color:",
        "commit_count_label": "Show Commits:",
        # --- Buttons & Tooltips ---
        "modifier_button_text": "👤 Patch Author",
        "modifier_tooltip_prefix": "Created by:",
        "check_tools_button": "🛠️ Check Tools",
        # --- System-Check Log ---
        "start_check": "Starting System Check...",
        "found": "OK",
        "missing": "MISSING!",
        "net_check": "Checking connection...",
        "net_online": "Online",
        "net_offline": "Offline",
        "upd_check": "🔍 Tool Update Check...",
        "sound_active": "Active",
        "sound_inactive": "Inactive",
        # --- Status Messages ---
        "status_up_to_date": "✅ OSCam is up to date",
        "status_update_avail": "🚀 Update available!",
        "welcome_msg": "Welcome to OSCam Emu Patch Generator!",
        # ... zip_patch ...
        "patch_file_missing": "Patch file does not exist: {path}",
        "zip_success": "✅ Patch successfully zipped: {zip_file}",
        "zip_failed": "❌ Error while zipping: {error}",
        # OSCam-Emu Git Patch
        "patch_emu_git_start": "🔹 Creating OSCam-Emu Git Patch... (Path: {path})",
        "patch_emu_git_deleted": "✅ Old OSCam-Emu Git folder deleted: {path}",
        "delete_failed": "❌ Failed to delete folder: {path}",
        "patch_emu_git_clone_failed": "❌ Git clone failed",
        "patch_emu_git_apply_failed": "❌ Failed to apply patch",
        "patch_emu_git_applied": "✅ Patch successfully committed: {commit_msg}",
        "patch_emu_git_revision_failed": "⚠️ Failed to get Git revision: {error}",
        "patch_emu_git_done": "✅ Oscam Emu Git successfully patched",
        "patch_emu_git_revision": "🧾 Git revision: {sha}",
        "github_patch_uploaded": "✅ Patch successfully uploaded: {patch_version}",
        "github_upload_failed": "❌ GitHub upload failed.",
        "github_emu_git_uploaded": "✅ OSCam-Emu Git successfully uploaded!",
        "git_revision_failed": "⚠️ Git revision could not be determined: {error}",
        "github_emu_git_revision": "📊 Current Status: Revision {sha} ({commit_msg})",
        "github_upload_start": "🚀 GitHub upload started, please wait...",
        "github_emu_git_revision_failed": "⚠️ Could not retrieve revision: {error}",
        # online patch laden
        "online_patch_dl": "Get Online Patch",
        "patch_dl_title": "Patch Download",
        "patch_dl_select": "Select a patch (checking versions...):",
        "patch_dl_wait": "Checking patch versions on server...",
        "patch_dl_start": "Starting download from: ",
        "patch_dl_save": "Patch saved at: ",
        # Patch modifier
        "ok_button": "OK",
        "config_saved": "Settings updated",
        "auth_label": "Author",
        "repo_label": "Repository",
        "lang_label": "Language",
        "dir_label": "Patch Directory",
        "auto_update_label": "Auto-Update",
        "cancel_button": "Cancel",
        "mod_dialog_title": "Change Author",
        "mod_dialog_label": "Patch Author Name:",
        "mod_changed_success": "✅ Modifier changed to: {name}",
        "repo_dialog_title": "Repository Selection",
        "repo_dialog_label": "Select the desired Repo URL:",
        # Patch anwenden
        "executing_cmd": "Executing command:",
        "cmd_failed": "Command failed with exit code:",
        "executing_git_apply": "🚀 Applying patch: {patch}",
        "executing_git_check": "🔍 Checking patch compatibility: {patch}",
        # --- Patch Status ---
        # online check
        "net_check": "Checking internet connection...",
        "net_online": "Online",
        "net_offline": "Offline",
        "patch_file_missing": "❌ Patch file missing: {path}",
        "patch_emu_git_done": "✅ Patch applied successfully!",
        "patch_emu_git_apply_failed": "❌ Failed to apply patch!",
        # Tool Start
        "start": "Starting System-Check...",
        "found": "found",
        "missing": "MISSING!",
        "ready": "All required system tools are ready.",
        "upd_check": "🔍 Tooltest Update Check...",
        "up_to_date": "Plugin is up to date",
        "config": "🛠️ Active Configuration:",
        "author": "Patch Author",
        "repo": "Repository",
        "start_check": "Starting System-Check...",
        "found": "found",
        "missing": "MISSING!",
        "tools_ready": "All required system tools are ready.",
        "upd_check": "🔍 Tooltest Update Check...",
        "upd_ok": "Plugin is up to date",
        "active_conf": "🛠️ Active Configuration:",
        "patch_author": "Patch Author",
        "no_update_found": "No update available....",
        "upd_ok": "✅ Plugin is up to date",
        "upd_btn_current": "v{v} (Latest)",
        "upd_btn_new": "Update: v{v} available",
        "active_conf": "🛠️ Active Configuration:",
        "patch_author": "Patch Author",
        "repository": "Repository",
        "update_error": "Update check failed",
        "repository": "Repository",
        # change autor repo
        "config_saved": "Settings updated",
        "auth_label": "Author",
        "repo_label": "Repository",
        "start_check": "Starting system check...",
        "found": "found",
        "missing": "MISSING!",
        "upd_check": "🔍 Tooltest Update Check...",
        "info_title": "About OSCam Emu Toolkit",
        "mod_dialog_title": "Change Patch Author",
        "mod_dialog_label": "Author name:",
        # check box
        "stats_checkbox": "Stats",
        "stats_tooltip": "Allow/Disallow anonymous usage statistics (Hit-Counter).",
        # For the update check
        "new_version_available": "New version available",
        "update_title": "Update Available",
        "update_msg": "A new version was found. Do you want to update now?",
        # Exit / Confirmation
        "exit": "Exit",
        "yes": "Yes",
        "no": "No",
        "cancel": "Cancel",
        # "plugin_update": "Plugin Update",
        "btn_plugin_update": "Plugin Update",
        "state_plugin_uptodate": "Up to date",
        "check_tools_button": "🛠️ Check Tools",
        "new_version_label": "New",
        "old_version_label": "Installed",
        "upd_ok": "Plugin is up to date",
        "update_title": "Update Available",
        "update_msg": "A new version has been found. Do you want to update now?",
        "new_version_label": "New",
        "old_version_label": "Installed",
        "upd_ok": "Plugin is up to date",
        # "checking_tools": "Starting system check...",
        "state_plugin_update_available": "Update available: {current} → {latest}",
        "log_update_check_start": "Checking for updates …",
        "log_update_uptodate": "✅ Installed version: {version}",
        "log_update_declined": "Update skipped",
        "log_update_failed": "❌ Update check failed: {error}",
        "update_box_title": "Software Update",
        "update_box_msg": "A new version is available!\n\nNew: v{latest}\nCurrent: v{current}\n\nUpdate now?",
        "msg_update_available_title": "Update available",
        "msg_update_available_text": "A new version ({latest}) is available.\nCurrently installed: {current}.\nUpdate now?",
        "update_fail": "Update failed: {error}",
        "update_success": "✅ Update installed successfully! Please restart the tool.",
        "update_available_msg": "Current version: {current}\nNew version: {latest}",
        "restart_required_msg": "The update was installed successfully. The tool must be restarted.\nRestart now?",
        # "restart_tool_info": "ℹ️ Restarting application...",
        "restart_tool_cancelled": "ℹ️ Restart cancelled by user.",
        "update_started": "ℹ️ Update check started...",
        "update_backup_done": "✅ Old plugin files backed up.",
        "update_download_failed": "❌ Download failed: {error}",
        "update_extract_failed": "❌ Failed to extract new version: {error}",
        "update_done": "✅ Update to version {version} completed successfully.",
        "restart_tool": "Restart Tool",
        "update_check_done": "Done",
        "backup_created": "✅ Backup created: {file}",
        "exit_question": "Do you really want to close the tool?",
        "update_check_start": "Checking for updates ...",
        "github_version_available": "New version available: {version}",
        "github_version_fetch_failed": "Version check failed: {error}",
        # ... Log save ...
        "log_exported": "✅ Log exported to:",
        "log_save_error": "❌ Error saving log:",
        # Close Tool
        "info_title": "About this tool",
        "credits_label": "Credits / Authors",
        "close": "Close",
        # update on start
        "version_current": "Version {version} is up to date.",
        "update_check_failed": "Update check failed: {error}",
        "update_available_title": "Update Available",
        "update_no_update": "ℹ️ No update available",
        "installed_version": "Installed version is",
        "new_version_found": "New version available",
        # Option Buttons
        "git_status": "View Commits",
        "edit_patch_header": "Edit Patch Header",
        "github_emu_config_button": "Edit GitHub Config",
        "github_upload_patch": "Upload Patch File",
        "github_upload_emu": "Upload OSCam-Emu Git",
        "oscam_emu_git_patch": "OSCam EMU Git Patch",
        "oscam_emu_git_clear": "Clear OSCam EMU Git",
        "oscam_emu_patch_upload": "Upload OSCam EMU Patch",
        "version_current": "Version {version} is up to date.",
        "modifier_button_text": "👤 Patch Autor",
        "update_error": "Error checking for updates: {error}",
        "update_declined": "Update declined.",
        "update_current_version": "✅ Installed version: {version}",
        "restart_required_title": "Restart Required",
        "restart_required_msg": "The tool needs to be restarted, Restart now?",
        "yes": "Yes",
        "no": "No",
        "save": "Save",
        # patch ordner leeren
        # Statistik
        "STATS_TITLE": "TOOL STATISTICS",
        "STATS_GITHUB": "GitHub:",
        "STATS_LOCAL": "Local:",
        "STATS_TOTAL": "Total:",
        # ... deine anderen Einträge ...
        "foot_ok": "OK",
        "foot_ready": "Ready",
        "stats_title": "TOOL STATISTICS",
        "stats_github": "GitHub:",
        "stats_local": "Local:",
        "stats_total": "Total:",
        "temp_repo_deleted": "Temp repository deleted: {path}",
        "patch_file_deleted": "Patch file deleted: {path}",
        "temp_repo_already_deleted": "Temporary repository not found (already clean): {path}",
        # Labels
        "language_label": "Language:",
        "color_label": "Color",
        "commit_count_label": "Commits to show",
        "info_tooltip": "Info / Help",
        "restart_tool_question": "Do you want to restart the tool now?",
        # Info Text
        "info_text": (
            "This tool is a complete OSCam Emu Patch Manager.\n\n"
            "Features:\n"
            "- Create Patch: Generates a patch from the OSCam source code.\n"
            "- Renew Patch: Updates the existing patch.\n"
            "- Check Patch: Verifies if the patch can be applied correctly.\n"
            "- Apply Patch: Applies the patch to the local OSCam-Emu Git repository.\n"
            "- Zip Patch: Packs the patch into a ZIP file.\n"
            "- Backup Patch: Backs up the old patch and overwrites it with the new version.\n"
            "- Clean Patch Folder: Deletes temporary files in the patch folder (important files remain).\n"
            "- Patch OSCam-Emu Git: Applies the patch directly to the OSCam-Emu Git repository.\n"
            "- Clean OSCam-Emu Git: Deletes the local OSCam-Emu Git folder.\n"
            "- GitHub Upload: Uploads the patch or the OSCam-Emu Git folder to GitHub.\n"
            "- Manage GitHub Credentials: Configure username, token, repository URL, and branch.\n"
            "- Change Language and Color: Switch GUI language between English/German, change button/progressbar colors.\n"
            "- Progress Display: Shows action progress in the progress bar.\n"
            "- Show Commits: Displays the latest commits from the local repository.\n\n"
            "⚠️ Note: Only `oscam-emu.patch` is overwritten during patch upload; all other files remain untouched."
        ),
        # Patch creation
        "patch_create_start": "ℹ️ Patch creation started...",
        "patch_create_clone_start": "⚠️ Cloning git repository...",
        "patch_create_clone_failed": "❌ Failed to clone git repository",
        "patch_create_no_changes": "ℹ️ No changes found between STREAM_REPO and EMU_REPO",
        "patch_create_success": "✅ Patch successfully created: {patch_file}",
        "patch_version_from_header": "✅ Patch version from header: {patch_version}",
        "patch_create_failed": "❌ Patch creation failed: {error}",
        "plugin_update": "Update available: {current} → {latest}",
        "executing_git_apply": "🚀 Applying patch: {patch}",
        "executing_git_check": "🔍 Checking patch compatibility: {patch}",
        # Commits
        "loading_commits": "Lade Commits...",
        "commits_loaded": "Commits erfolgreich geladen",
        # Backup
        "backup_old_start": "ℹ️ Creating backup of old patch…",
        "backup_done": "✅ Backup successfully created: {path}",
        "update_downloading": "Downloading update...",
        "update_success_msg": "Update successful! The tool will now restart.",
        "no_old_patch": "ℹ️ No old patch found.",
        "new_patch_installed": "✅ New patch successfully installed: {path}",
        "patch_file_missing": "❌ Patch file missing: {path}",
        "patch_check_ok": "✅ Patch can be applied: no conflicts found",
        "github_dialog_title": "GitHub Emu Configuration",
        "patch_check_fail": "❌ Patch cannot be applied: conflicts or errors found",
        "patch_failed": "❌ Patch failed: {path}",
        # Oscam online check
        "oscam_uptodate": "OSCam Git is up to date.",
        "oscam_update_found": "Update available!",
        "oscam_check_start": "🔍 Checking OSCam Repository...",
        "oscam_server_error": "❌ Error: OSCam server not reachable.",
        # check for new commits
        "check_commit_button_short": "🔄 Check Commit",
        "check_commit_title": "OSCam Commit Check",
        "check_commit_current_hash": "Current Hash:",
        "check_commit_current": "Current Hash:",
        "check_commit_old": "Old Hash:",
        "check_commit_new": "New Hash:",
        "check_commit_no_hash": "Error: No commit hash found.",
        "check_commit_up_to_date": "No new commit found.",
        "check_commit_current": "Current status:",
        "check_commit_new_found": "New commit found!",
        "check_commit_new": "New:",
        "check_commit_old": "Old:",
        "check_commit_error": "Error during check:",
        "check_commit_button": "🔄 Check for new commit",
        "check_commit_tooltip": "Click here to check if a new commit is available in the Streamboard repository. If a new commit is found, the last commit hash will be displayed.",
        # Clean Patch Folder
        "": "ℹ️ Deleting OSCam-Emu Git folder: {path}",
        "oscam_emu_git_missing": "⚠️ Folder not found: {path}",
        "clean_done": "✅ Cleanup completed successfully!",
        "oscam_emu_git_missing": "⚠️ Folder does not exist: {path}",
        "oscam_emu_git_patch_start": "🔹 Creating OSCam-Emu Git Patch...",
        "git_patch_success": "✅ Git Patch created successfully! Revision: {rev}",
        "git_patch_success": "✅ Patch created successfully! Git Revision: {rev}",
        "patch_version_from_header": "Patch version from header: {patch_version}",
        "patch_create_success": "Patch successfully created: {patch_file}",
        "cleaning_oscam_emu_git": "🔹 Emptying OSCam-Emu Git folder...",
        "oscam_emu_git_deleted": "✅ OSCam-Emu Git folder successfully deleted.",
        "oscam_emu_git_missing": "⚠️ OSCam-Emu Git folder not found: {path}",
        "delete_failed": "❌ Failed to delete: {path}",
        "oscam_emu_git_clearing": "🔹 Emptying OSCam-Emu Git folder...",
        "oscam_emu_git_cleared": "✅ Cleanup completed successfully!",
        "patch_check_ok": "✅ Patch check successful (Patch applies)! ",
        "patch_check_fail": "❌ Patch check failed (Patch does not apply)!",
        "patch_file_missing": "❌ Patch file not found!",
        "cleanup_start": "🔹 Cleaning up work directory...",
        "cleanup_success": "✅ Cleanup completed successfully! ✨",
        "delete_failed": "❌ Deletion failed: {path} - {error}",
        "patch_create_success": "✅ Patch created successfully: {patch_file}",
        "patch_create_failed": "❌ Error creating patch: {error}",
        "showing_commits": "ℹ️ Showing latest {count} commits",
    },
    "de": {
        # Grid Buttons / Patch Aktionen
        "patch_create": "Patch erstellen",
        "patch_renew": "Patch erneuern",
        "patch_check": "Patch prüfen",
        "patch_apply": "Patch anwenden",
        "patch_zip": "Patch zippen",
        "backup_old": "S3-Patch sichern/erneuern",
        "clean_folder": "Patch-Ordner leeren",
        "patch_path_label": "Patch speichern",
        "change_old_dir": "S3 Patch-Ordner auswählen",
        # OSCam-Emu Git Patch
        "patch_emu_git_start": "🔹 OSCam-Emu Git Patch wird erstellt... (Pfad: {path})",
        "patch_emu_git_deleted": "✅ Alter OSCam-Emu Git Ordner gelöscht: {path}",
        "delete_failed": "❌ Löschen des Ordners fehlgeschlagen: {path}",
        "patch_emu_git_clone_failed": "❌ Git-Klon fehlgeschlagen",
        "patch_emu_git_apply_failed": "❌ Patch konnte nicht angewendet werden",
        "patch_emu_git_applied": "✅ Patch erfolgreich committet: {commit_msg}",
        "patch_emu_git_revision_failed": "⚠️ Git-Revision konnte nicht ermittelt werden: {error}",
        "patch_emu_git_done": "✅ Oscam Emu Git erfolgreich gepatcht",
        "edit_patch_header": "Edit Patch Header",
        "patch_emu_git_revision": "\U0001f4dd Git-Revision: {sha}",
        # Active autor repo
        "config_active_header": "🛠️ <b>Active Configuration:</b>",
        "current_author": "👤 Patch Author:",
        "current_repo": "🌐 Repository:",
        "settings_saved_info": "✅ Settings have been saved permanently.",
        # --- GitHub Dialog ---
        "github_dialog_title": "GitHub Configuration",
        "patch_repo_label": "Patch Repository:",
        "patch_branch_label": "Patch Branch:",
        "emu_repo_label": "EMU Repository:",
        "emu_branch_label": "EMU Branch:",
        "github_username_label": "GitHub User:",
        "github_token_label": "Token / PAT:",
        "github_user_name_label": "Git Name:",
        "github_user_email_label": "Git Email:",
        # Active autor repo
        "ok_button": "OK",
        "repo_dialog_title": "Repository Auswahl",
        "repo_dialog_label": "Wähle die gewünschte Repo-URL:",
        "cancel_button": "Abbrechen",
        "config_active_header": "🛠️ <b>Aktive Konfiguration:</b>",
        "current_author": "👤 Patch Autor:",
        "current_repo": "🌐 Repository:",
        "settings_saved_info": "✅ Einstellungen wurden dauerhaft gespeichert.",
        # change repo patch autor
        "config_saved": "Einstellungen aktualisiert",
        "auth_label": "Autor",
        "repo_label": "Repository",
        "start_check": "Starte System-Check...",
        "found": "gefunden",
        "missing": "FEHLT!",
        "upd_check": "🔍 Tooltest Update Check...",
        "info_title": "Über OSCam Emu Toolkit",
        "mod_dialog_title": "Patch Autor ändern",
        "mod_dialog_label": "Name des Autors:",
        # Matrix
        "matrix_system": "System",
        "matrix_engaged": "Wake up, Neo... Matrix Mode engaged. ■",
        "matrix_disabled": "Matrix Mode disabled.",
        "btn_matrix_on": "📟 MATRIX MODE",
        "btn_matrix_off": "🔙 EXIT MATRIX",
        "matrix_sys": "System",
        "matrix_on": "Wake up, Neo... Matrix Mode engaged. ■",
        "matrix_off": "Matrix Mode disabled.",
        "matrix_btn_enter": "📟 MATRIX MODE",
        "matrix_btn_exit": "🔙 EXIT MATRIX",
        # Exit / Confirmation
        "exit": "Beenden",
        "yes": "Ja",
        "no": "Nein",
        "cancel": "Abbrechen",
        "github_upload_start": "🚀 GitHub Upload gestartet, bitte warten...",
        "github_config_load": "Lade GitHub-Konfiguration...",
        "github_emu_git_missing": "Fehler: GitHub-Konfigurationsdaten unvollständig (URL, Token oder User fehlen).",
        "patch_emu_git_missing": "Fehler: Lokaler Quellordner nicht gefunden: {path}",
        "git_repo_init": "Initialisiere neues Git-Repository im Zielordner...",
        "git_remote_add": "Verknüpfe lokales Repository mit GitHub...",
        "git_remote_update": "Aktualisiere Remote-Verbindung...",
        "git_fetching": "Hole aktuelle Daten vom GitHub-Repository...",
        "git_config_user": "Setze Git-Benutzerdaten ({user_name})...",
        "git_adding_files": "Indiziere Dateien für den Upload...",
        "git_committing": "Erstelle Commit...",
        "exit_question": "Möchten Sie das Tool wirklich schließen?",
        "update_current_version": "✅ Sie nutzen bereits die aktuelle Version: {version}",
        "update_started": "ℹ️ Update gestartet…",
        "backup_created": "✅ Backup erfolgreich erstellt: {file}",
        # "restart_tool_info": "ℹ️ Tool wird neu gestartet…",
        "restart_tool_cancelled": "ℹ️ Neustart vom Benutzer abgebrochen",
        "github_emu_git_uploaded": "✅ OSCam-Emu Git erfolgreich hochgeladen!",
        "github_emu_git_revision": "📊 Aktueller Stand: Revision {sha} ({commit_msg})",
        "github_emu_git_revision_failed": "⚠️ Revision konnte nicht ausgelesen werden: {error}",
        # online check
        "net_check": "Prüfe Internetverbindung...",
        "net_online": "Online",
        "net_offline": "Offline",
        # ... check tools first start ...
        "log_start_header": "--- OSCam Emu Patch Generator v{} ---",
        "log_sys_info": "System: {} {}",
        "log_dep_check": "Check: Git ({}), Patch ({}), Sound ({})",
        "log_status_ok": "Status: All dependencies loaded. Ready.",
        "ok": "OK",
        "missing": "MISSING",
        "active": "Active",
        "inactive": "Inactive",
        # --- Header & GroupBoxes ---
        "settings_header": "⚙️ Einstellungen",
        "github_config_header": "📁 GitHub Konfiguration",
        # --- Labels ---
        "language_label": "Sprache:",
        "color_label": "Design / Farbe:",
        "commit_count_label": "Commits anzeigen:",
        # --- Buttons & Tooltips ---
        "modifier_button_text": "👤 Patch Autor",
        "modifier_tooltip_prefix": "Erstellt von:",
        "check_tools_button": "🛠️ Tools prüfen",
        # --- System-Check Log ---
        "start_check": "Starte System-Check...",
        "found": "OK",
        "missing": "FEHLT!",
        "net_check": "Prüfe Internetverbindung...",
        "net_online": "Online",
        "net_offline": "Offline",
        "upd_check": "🔍 Tool Update Check...",
        "sound_active": "Aktiv",
        "sound_inactive": "Inaktiv",
        # --- Status Meldungen ---
        "status_up_to_date": "✅ OSCam ist aktuell",
        "status_update_avail": "🚀 Update verfügbar!",
        "welcome_msg": "Willkommen beim OSCam Emu Patch Generator!",
        # Patch anwenden
        "executing_cmd": "Führe Befehl aus:",
        "cmd_failed": "Befehl fehlgeschlagen mit Code:",
        "executing_git_apply": "🚀 Wende Patch an: {patch}",
        "executing_git_check": "🔍 Prüfe Patch-Kompatibilität: {patch}",
        # Oscam update check
        "oscam_uptodate": "OSCam Git ist aktuell.",
        "oscam_update_found": "Update verfügbar!",
        "oscam_check_start": "🔍 Prüfe OSCam Repository...",
        "oscam_server_error": "❌ Fehler: OSCam Server nicht erreichbar.",
        # --- Patch Status ---
        "patch_file_missing": "❌ Patch-Datei fehlt: {path}",
        "patch_emu_git_done": "✅ Patch erfolgreich angewendet!",
        "patch_emu_git_apply_failed": "❌ Patch konnte nicht angewendet werden!",
        # ... Log save ...
        "log_exported": "✅ Log exportiert nach:",
        "log_save_error": "❌ Fehler beim Speichern des Logs:",
        # ... zip_patch ...
        "patch_file_missing": "Patch-Datei existiert nicht: {path}",
        "zip_success": "✅ Patch erfolgreich gepackt: {zip_file}",
        "zip_failed": "❌ Fehler beim Zippen: {error}",
        "zip_file_already_deleted": "Kein ZIP-Archiv zum Löschen gefunden.",
        "zip_file_deleted": "ZIP-Archiv wurde gelöscht: {path}",
        # Close Tool
        "info_title": "Über dieses Tool",
        "credits_label": "Mitwirkende / Autoren",
        "close": "Schließen",
        # Online patch laden
        "online_patch_dl": "Online Patch laden",
        "patch_dl_title": "Patch Download",
        "patch_dl_select": "Wähle einen Patch (Versionen werden geprüft...):",
        "patch_dl_wait": "Prüfe Patch-Versionen am Server...",
        "patch_dl_start": "Starte Download von: ",
        "patch_dl_save": "Patch gespeichert unter: ",
        # Tool Start
        "start": "Starte System-Check...",
        "found": "gefunden",
        "missing": "FEHLT!",
        "ready": "Alle benötigten System-Tools sind bereit.",
        "upd_check": "🔍 Tooltest Update Check...",
        "up_to_date": "Plugin ist aktuell",
        "config": "🛠️ Aktive Konfiguration:",
        "author": "Patch Autor",
        "repo": "Repository",
        "start_check": "Starte System-Check...",
        "found": "gefunden",
        "missing": "FEHLT!",
        "tools_ready": "Alle benötigten System-Tools sind bereit.",
        "upd_check": "🔍 Tooltest Update Check...",
        "upd_ok": "Plugin ist aktuell",
        "active_conf": "🛠️ Aktive Konfiguration:",
        "patch_author": "Patch Autor",
        "repository": "Repository",
        # check box
        "stats_checkbox": "Stats",
        "stats_tooltip": "Anonyme Nutzungsstatistik (Hit-Counter) erlauben/verbieten.",
        # Für den Update-Check
        "new_version_available": "Neue Version verfügbar",
        "update_title": "Update verfügbar",
        "update_msg": "Eine neue Version wurde gefunden. Möchtest du jetzt aktualisieren?",
        "update_title": "Update verfügbar",
        "update_msg": "Eine neue Version wurde gefunden. Möchtest du jetzt aktualisieren?",
        "new_version_label": "Neu",
        "no_update_found": "Kein Update vorhanden....",
        "upd_ok": "✅ Plugin ist aktuell",
        "upd_btn_current": "v{v} (Aktuell)",
        "upd_btn_new": "Update: v{v} verfügbar",
        "active_conf": "🛠️ Aktive Konfiguration:",
        "patch_author": "Patch Autor",
        "repository": "Repository",
        "update_error": "Update-Check fehlgeschlagen",
        "old_version_label": "Installiert",
        "upd_ok": "Plugin ist aktuell",
        # Matrix
        "matrix_system": "System",
        "matrix_engaged": "Wake up, Neo... Matrix-Modus aktiviert. ■",
        "matrix_disabled": "Matrix-Mode deaktiviert.",
        "btn_matrix_on": "📟 MATRIX MODE",
        "btn_matrix_off": "🔙 EXIT MATRIX",
        "matrix_sys": "System",
        "matrix_on": "Wake up, Neo... Matrix-Modus aktiviert. ■",
        "matrix_off": "Matrix-Modus deaktiviert.",
        "matrix_btn_enter": "📟 MATRIX MODE",
        "matrix_btn_exit": "🔙 EXIT MATRIX",
        # Updates
        "restart_required_msg": "Das Update wurde erfolgreich installiert. Das Tool muss neu gestartet werden.\nJetzt neu starten?",
        "restart_required_title": "Neustart erforderlich",
        "update_success": "✅ Update erfolgreich! Bitte Plugin neu starten.",
        "update_fail": "Update fehlgeschlagen: {error}",
        "update_not_available": "Keine neue Version verfügbar.",
        "update_check_start": "Prüfe auf Updates ...",
        "github_version_available": "Neue Version {version} auf GitHub verfügbar",
        "github_version_fetch_failed": "⚠️ Fehler beim Abrufen der GitHub-Version: {error}",
        "plugin_update": "Update verfügbar: {current} → {latest}",
        "btn_plugin_update": "Plugin Update",
        "update_check_done": "Fertig",
        "state_plugin_uptodate": "Bereits aktuell",
        "state_plugin_update_available": "Update verfügbar: {current} → {latest}",
        "log_update_check_start": "Prüfe auf Updates …",
        "log_update_uptodate": "✅ Installierte Version: {version}",
        "log_update_declined": "Update übersprungen",
        "log_update_failed": "❌ Update-Prüfung fehlgeschlagen: {error}",
        "msg_update_available_title": "Update verfügbar",
        "new_version_label": "Neu",
        "old_version_label": "Installiert",
        "upd_ok": "Plugin ist aktuell",
        "update_done": "✅ Update auf Version {version} erfolgreich abgeschlossen.",
        "update_backup_done": "✅ Backup der alten Plugin-Dateien erstellt.",
        "msg_update_available_text": "Eine neue Version ({latest}) ist verfügbar.\nAktuell installiert: {current}.\nJetzt updaten?",
        # check for new commits
        "check_commit_button_short": "🔄 Commit Check",
        "check_commit_current_hash": "Aktueller Hash:",
        "check_commit_current": "Aktueller Hash:",
        "check_commit_new": "Neuer Hash:",
        "check_commit_title": "OSCam Commit-Check",
        "check_commit_no_hash": "Fehler: Kein Commit-Hash gefunden.",
        "check_commit_up_to_date": "Kein neuer Commit vorhanden.",
        "check_commit_current": "Aktueller Stand:",
        "check_commit_new_found": "Neuer Commit gefunden!",
        "check_commit_new": "Neu:",
        "check_commit_old": "Alt:",
        "check_commit_error": "Fehler beim Check:",
        "check_commit_button": "🔄 Prüfe auf neuen Commit",
        "check_commit_tooltip": "Klicke hier, um zu prüfen, ob ein neuer Commit im Streamboard-Repository vorhanden ist. Falls ein neuer Commit vorhanden ist, wird der Hash des letzten Commits angezeigt.",
        # Option Buttons
        "git_status": "Commits anzeigen",
        "restart_tool": "Tool Neustarten",
        "edit_patch_header": "Patch Header bearbeiten",
        "github_emu_config_button": "GitHub-Konfiguration",
        "github_upload_patch": "Patch hochladen",
        "github_upload_emu": "EMU Git hochladen",
        "oscam_emu_git_patch": "OSCam EMU Git Patch",
        "oscam_emu_git_clear": "OSCam EMU Git leeren",
        "update_available_title": "Update verfügbar",
        "modifier_button_text": "👤 Patch Autor",
        "update_current_version": "✅ Installierte Version: {version}",
        "update_check_failed": "Fehler bei Updateprüfung: {error}",
        "update_available_msg": "Aktuelle Version: {current}\nNeue Version: {latest}",
        "update_success": "✅ Update erfolgreich installiert! Bitte Tool neu starten.",
        "version_current": "Version {version} ist aktuell.",
        "update_error": "Fehler bei Updateprüfung: {error}",
        "update_box_title": "Software Update",
        "update_box_msg": "Eine neue Version ist verfügbar!\n\nNeu: v{latest}\nAktuell: v{current}\n\nJetzt aktualisieren?",
        "update_declined": "Update abgebrochen.",
        "update_no_update": "ℹ️ Kein Update vorhanden",
        "tools_ok": "✅ Alle benötigten System-Tools sind bereits installiert.",
        "tools_missing": "⚠️ Folgende Tools fehlen: {tools}. Installation wird vorbereitet...",
        "check_tools_button": "🛠️ Tools prüfen",
        "checking_tools": "Starte System-Check...",
        "restart_required_title": "Neustart erforderlich",
        "restart_tool_question": "Möchten Sie das Tool jetzt neu starten?",
        "patch_emu_git_success": "✅ OSCam Emu Git successfully patched",
        "restart_required_msg": "Das Tool muss neu gestartet werden. Jetzt neu starten?",
        "yes": "Ja",
        "no": "Nein",
        "installed_version": "Installierte Version ist",
        "new_version_found": "Neue Version verfügbar",
        "oscam_emu_patch_upload": "OSCam EMU Patch hochladen",
        # Labels
        "mod_dialog_title": "Modifier ändern",
        "mod_dialog_label": "Name des Patch-Erstellers:",
        "mod_changed_success": "✅ Modifier geändert zu: {name}",
        # "language_label": "Sprache:",
        "language_label": "Sprache:",
        "color_label": "Style:",
        "commit_count_label": "Anzahl Commits",
        "settings_header": "Einstellungen",
        "info_tooltip": "Info / Hilfe",
        # Info Text
        "info_text": (
            "Dieses Tool ist ein umfassender OSCam Emu Patch Manager.\n\n"
            "Funktionen:\n"
            "- Patch erstellen: Erstellt den Patch aus OSCam-Quellcode.\n"
            "- Patch erneuern: Aktualisiert den bestehenden Patch.\n"
            "- Patch prüfen: Überprüft, ob der Patch korrekt angewendet werden kann.\n"
            "- Patch anwenden: Wendet den Patch auf das lokale OSCam-Emu Git-Repository an.\n"
            "- Patch zippen: Packt den Patch in eine ZIP-Datei.\n"
            "- Patch sichern: Sichert die alte Patch-Datei und überschreibt sie mit der neuen Version.\n"
            "- Patch-Ordner leeren: Löscht temporäre Dateien im Patch-Ordner (wichtige Dateien bleiben erhalten).\n"
            "- OSCam-Emu Git patchen: Wendet den Patch direkt auf das OSCam-Emu Git-Repository an.\n"
            "- OSCam-Emu Git bereinigen: Löscht das lokale OSCam-Emu Git-Verzeichnis.\n"
            "- GitHub Upload: Upload des Patches oder des OSCam-Emu Git-Ordners auf GitHub.\n"
            "- GitHub Konfiguration verwalten: Benutzername, Token, Repository-URL und Branch anpassen.\n"
            "- Sprache und Farbe anpassen: GUI-Sprache zwischen Deutsch/Englisch wechseln, Farben für Buttons/Progressbar ändern.\n"
            "- Fortschrittsanzeige: Fortschritt von Aktionen in der Progressbar sichtbar.\n"
            "- Commit-Anzeige: Zeigt die letzten Commits aus dem lokalen Repository an.\n\n"
            "⚠️ Hinweis: Beim Patch-Upload wird nur `oscam-emu.patch` überschrieben; andere Dateien bleiben unverändert."
        ),
        # Patch creation
        "patch_create_start": "ℹ️ Patch-Erstellung gestartet...",
        "patch_create_clone_start": "⚠️ TEMP_REPO existiert nicht, Repository wird geklont...",
        "patch_create_clone_failed": "❌ Klonen fehlgeschlagen, Patch-Erstellung abgebrochen.",
        "patch_create_no_changes": "ℹ️ Keine Änderungen zwischen STREAM_REPO und EMU_REPO gefunden",
        "patch_create_success": "✅ Patch erfolgreich erstellt: {patch_file}",
        "patch_version_from_header": "✅ Patch-Version aus Header: {patch_version}",
        "patch_create_failed": "❌ Patch-Erstellung fehlgeschlagen: {error}",
        "git_patch_success": "✅ Git Patch erfolgreich erstellt! Revision: {rev}",
        # Statistik
        "STATS_TITLE": "TOOL STATISTIK",
        "STATS_GITHUB": "GitHub:",
        "STATS_LOCAL": "Lokal:",
        "STATS_TOTAL": "Gesamt:",
        "foot_ok": "OK",
        "foot_ready": "Bereit",
        "stats_title": "TOOL STATISTIK",
        "stats_github": "GitHub:",
        "stats_local": "Lokal:",
        "stats_total": "Gesamt:",
        # Patch ordner leeren
        "temp_patch_git_already_deleted": "Patch-Git-Ordner war bereits gelöscht oder nicht vorhanden.",
        "patch_file_deleted": "Patch-Datei wurde erfolgreich entfernt: {path}",
        "patch_file_already_deleted": "Keine Patch-Datei zum Löschen gefunden: {path}",
        "clean_done": "Bereinigung des Patch Temp Ordners erfolgreich abgeschlossen! ✨",
        "oscam_emu_git_missing": "⚠️ Ordner nicht gefunden: {path}",
        "temp_repo_deleted": "Temporäres Repository erfolgreich gelöscht: {path}",
        "oscam_emu_git_patch_start": "🔹 OSCam-Emu Git Patch wird erstellt...",
        "patch_file_deleted": "Patch-Datei gelöscht: {path}",
        "cleaning_oscam_emu_git": "🔹 OSCam-Emu Git Ordner wird geleert...",
        "oscam_emu_git_deleted": "✅ OSCam-Emu Git Ordner erfolgreich gelöscht.",
        "oscam_emu_git_missing": "⚠️ OSCam-Emu Git Ordner nicht gefunden: {path}",
        "delete_failed": "❌ Fehler beim Löschen: {path}",
        "patch_emu_git_success": "✅ OSCam Emu Git erfolgreich gepatcht",
        # "zip_file_deleted": "ZIP-Archiv entfernt: {path}",
        # Backup
        "backup_old_start": "ℹ️ Erstelle Backup des alten Patches…",
        "backup_done": "✅ Backup erfolgreich erstellt: {path}",
        "tools_missing": "⚠️ Folgende Tools fehlen: {tools}. Installation wird vorbereitet...",
        "checking_tools": "Starte System-Check...",
        "no_old_patch": "ℹ️ Keine alte Patch-Datei gefunden.",
        "new_patch_installed": "✅ Neuer Patch erfolgreich installiert: {path}",
        "patch_file_missing": "❌ Patch-Datei fehlt: {path}",
        "update_downloading": "Lade Update herunter...",
        "update_success_msg": "Update erfolgreich! Das Tool wird nun neu gestartet.",
        "github_dialog_title": "GitHub Emu Konfiguration",
        "patch_check_ok": "✅ Patch kann angewendet werden: keine Konflikte gefunden",
        "patch_check_fail": "❌ Patch kann nicht angewendet werden: Konflikte vorhanden oder Fehler",
        "patch_failed": "❌ Patch fehlgeschlagen: {path}",
        # Github config
        "github_dialog_title": "GitHub Konfiguration",
        "patch_repo_label": "Patch Repository:",
        "patch_branch_label": "Patch Branch:",
        "emu_repo_label": "EMU Repository:",
        "emu_branch_label": "EMU Branch:",
        "github_username_label": "GitHub Benutzer:",
        "github_token_label": "GitHub Token:",
        "github_user_name_label": "Git Name:",
        "github_user_email_label": "Git E-Mail:",
        "save": "Speichern",
        "github_config_saved": "✅ GitHub Konfiguration gespeichert.",
        "executing_git_apply": "🚀 Wende Patch an: {patch}",
        "executing_git_check": "🔍 Prüfe Patch-Kompatibilität: {patch}",
        # Clean Patch Folder
        "oscam_emu_git_missing": "⚠️ Ordner nicht gefunden: {path}",
        "delete_failed": "❌ Fehler: Konnte {path} nicht löschen. Fehler: {error}",
        "git_patch_success": "✅ Patch erfolgreich erstellt! Git Revision: {rev}",
        "oscam_emu_git_missing": "⚠️ Ordner existiert nicht: {path}",
        "delete_failed": "❌ Löschen fehlgeschlagen: {path} (Fehler: {error})",
        "github_patch_uploaded": "✅ Patch erfolgreich hochgeladen: {patch_version}",
        "github_upload_failed": "❌ Fehler beim Hochladen auf GitHub.",
        "patch_version_from_header": "Patch-Version aus Header: {patch_version}",
        "patch_create_success": "Patch erfolgreich erstellt: {patch_file}",
        "oscam_emu_git_clearing": "🔹 OSCam-Emu Git Ordner wird geleert...",
        "oscam_emu_git_cleared": "✅ Bereinigung erfolgreich abgeschlossen!",
        "patch_check_ok": "✅ Patch-Check erfolgreich (Patch passt)! ",
        "patch_check_fail": "❌ Patch-Check fehlgeschlagen (Patch passt nicht)!",
        "patch_file_missing": "❌ Patch-Datei nicht gefunden!",
        "cleanup_start": "🔹 Bereinigung des Arbeitsverzeichnisses...",
        "cleanup_success": "✅ Bereinigung erfolgreich abgeschlossen! ✨",
        "delete_failed": "❌ Löschen fehlgeschlagen: {path} - {error}",
        "patch_create_success": "✅ Patch erfolgreich erstellt: {patch_file}",
        "patch_create_failed": "❌ Fehler beim Erstellen des Patches: {error}",
        "showing_commits": "ℹ️ Zeige die letzten {count} Commits",
    },
}

# Ergänze fehlende Keys aus EN nach DE
for key, value in TEXTS["en"].items():
    if key not in TEXTS["de"]:
        TEXTS["de"][key] = value

# 4️⃣ **Unbedingt einmalig vor GUI-Start aufrufen**
fill_missing_keys(TEXTS)


def save_config(cfg_updates, gui_instance=None, silent=False):
    """
    Speichert Config-Updates und synchronisiert Timer, ProgressBar sowie Sounds.
    Verhindert die Anzeige beim Toolstart (Laden) und zeigt Status beim Beenden/Speichern.
    """
    try:
        # 1. Bestehende Config laden
        current_cfg = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    current_cfg = json.load(f)
            except:
                current_cfg = {}

        # 2. Mergen der neuen Updates
        current_cfg.update(cfg_updates)

        # 3. System-Werte & Timer synchronisieren
        blink_speed = current_cfg.get("blink_speed", 500)
        led_globally_on = current_cfg.get("led_enabled", True)

        if gui_instance:
            timer = getattr(
                gui_instance, "master_timer", getattr(gui_instance, "blink_timer", None)
            )
            if timer:
                # Stoppen wenn: Laden läuft, Speed statisch oder global AUS
                if (
                    getattr(gui_instance, "is_loading", False)
                    or blink_speed >= 950
                    or not led_globally_on
                ):
                    timer.stop()
                    if hasattr(gui_instance, "force_user_leds_static"):
                        gui_instance.force_user_leds_static()
                    elif hasattr(gui_instance, "force_leds_static"):
                        gui_instance.force_leds_static()
                else:
                    timer.setInterval(max(10, blink_speed))
                    if not timer.isActive():
                        timer.start()

        # 4. Speichern in die Datei
        with open(os.path.abspath(CONFIG_FILE), "w", encoding="utf-8") as f:
            json.dump(current_cfg, f, indent=4, ensure_ascii=False)

        # 5. UI & Feedback Logik
        if gui_instance:
            gui_instance.current_config = current_cfg

            is_loading = getattr(gui_instance, "is_loading", False)
            is_closing = getattr(gui_instance, "is_closing", False)

            # WICHTIG: Feedback nur wenn NICHT im Lademodus (Start)
            if not is_loading and not silent:
                # --- SOUND ABSPIELEN ---
                if (
                    "safe_play" in globals() and not is_closing
                ):  # Beim Beenden übernimmt closeEvent den Sound
                    safe_play("dialog-information.oga")

                # --- TEXT & FARBE BESTIMMEN ---
                lang = getattr(gui_instance, "LANG", "de").lower()
                is_matrix = current_cfg.get("theme_mode") == "matrix"

                if is_closing:
                    msg = (
                        "✅ Beendet & Gespeichert"
                        if lang == "de"
                        else "✅ Exit & Saved"
                    )
                    log_color = "#FB0A2A"  # Gold-Gelb im Log beim Beenden
                    pbar_color = "#0e0701"  # Orangefarbener Balken beim Beenden
                else:
                    msg = (
                        "✅ Einstellungen gespeichert"
                        if lang == "de"
                        else "✅ Settings saved"
                    )
                    # Matrix-Grün im Matrix-Mode, sonst Cyan
                    log_color = "#00FF41" if is_matrix else "cyan"
                    pbar_color = "#2ecc71"  # Standard-Grün

                # --- PROGRESSBAR AKTUALISIEREN ---
                pbar = getattr(gui_instance, "progress_bar", None)
                if pbar:
                    pbar.setValue(100)
                    pbar.setFormat(msg)
                    # Setzt die Farbe des Balkens passend zum Status (Grün oder Orange)
                    pbar.setStyleSheet(
                        f"QProgressBar::chunk {{ background-color: {pbar_color}; border-radius: 2px; }}"
                    )

                    # Nach 3 Sekunden zurück zum Idle (nur wenn nicht beim Beenden)
                    if not is_closing and hasattr(gui_instance, "pbar_idle"):
                        from PyQt6.QtCore import QTimer

                        QTimer.singleShot(3000, gui_instance.pbar_idle)

                # --- LOG MESSAGE (INFOSCREEN) ---
                if hasattr(gui_instance, "log_message"):
                    gui_instance.log_message(
                        f"<span style='color:{log_color}; font-weight:700;'><b>{msg}</b></span>"
                    )

    except Exception as e:
        if gui_instance and hasattr(gui_instance, "log_message"):
            gui_instance.log_message(
                f"<span style='color:orange;'>❌ Fehler beim Speichern: {e}</span>"
            )


# ===================== CONFIG =====================
def load_config():
    """Lädt Config, erlaubt eigene URLs und repariert die Datei bei fehlenden Keys (inkl. Matrix & Blink-Speed)."""
    import os, json

    CORRECT_URL = "https://github.com/oscam-mirror/oscam-emu.git"
    base_patch_dir = globals().get(
        "OLD_PATCH_DIR", os.path.dirname(os.path.abspath(__file__))
    )

    # 1. Standard-Konfiguration (Erweitert um Theme und Blink-Speed)
    default_cfg = {
        "commit_count": 5,
        "color": "Classics",
        "language": "de",
        "s3_patch_path": base_patch_dir,
        "patch_modifier": "speedy005",
        "EMUREPO": CORRECT_URL,
        "theme_mode": "standard",  # NEU: Standard-Look
        "blink_speed": 0,  # NEU: Standard-Blinken (500ms)
    }

    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_cfg, f, indent=4, ensure_ascii=False)
        except:
            pass
        return default_cfg.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        if not isinstance(cfg, dict):
            return default_cfg.copy()

        # 3. Fehlende Keys ergänzen (Fügt theme_mode und blink_speed hinzu, falls sie fehlen)
        needs_save = False
        for key, value in default_cfg.items():
            if key not in cfg:
                cfg[key] = value
                needs_save = True

        # 4. KORREKTUR DER URL
        current_repo = str(cfg.get("EMUREPO", "")).strip()
        if len(current_repo) < 8:
            cfg["EMUREPO"] = CORRECT_URL
            needs_save = True

        # Datei bei Änderungen aktualisieren
        if needs_save:
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4, ensure_ascii=False)
            except:
                pass

        # 5. Globale Variablen synchronisieren
        globals()["EMUREPO"] = cfg["EMUREPO"]
        globals()["PATCH_MODIFIER"] = cfg["patch_modifier"]

        # NEU: Auch die neuen Werte global verfügbar machen (optional)
        globals()["THEME_MODE"] = cfg.get("theme_mode", "standard")
        globals()["BLINK_SPEED"] = cfg.get("blink_speed", 0)

        return cfg

    except Exception as e:
        print(f"⚠️ Kritischer Config Fehler: {e}")
        return default_cfg.copy()


# ===================== INFOSCREEN =====================
def github_upload_patch_file(
    gui_instance=None, info_widget=None, progress_callback=None
):
    """
    Lädt die Patch-Datei auf GitHub hoch mit Regenbogen-Progressbar.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import shutil, os, datetime

    # 1. Widget und Sprache
    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(gui_instance, "info_text", None)
    )
    pbar = getattr(gui_instance, "progress_bar", None)
    lang = getattr(gui_instance, "LANG", "de").lower()

    # --- REGENBOGEN STYLES ---
    rainbow = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
        "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
    )
    style_rb = f"""
        QProgressBar {{ 
            text-align: center; font-weight: 900; border: 2px solid #222;
            border-radius: 6px; background-color: #111; color: black; font-size: 14pt; 
        }}
        QProgressBar::chunk {{ background-color: {rainbow} border-radius: 4px; }}
    """
    style_err = "QProgressBar { text-align: center; font-weight: 900; border: 2px solid #500; border-radius: 6px; background-color: #111; color: #FF0000; font-size: 12pt; } QProgressBar::chunk { background-color: #800; }"

    def set_progress(val, is_err=False):
        if pbar:
            pbar.setStyleSheet(style_err if is_err else style_rb)
            pbar.setValue(val)
            pbar.setFormat("%p%")
            pbar.show()
        if progress_callback:
            try:
                progress_callback(val)
            except:
                pass
        QApplication.processEvents()

    def play_sound(success=True):
        if "safe_play" in globals():
            safe_play("complete.oga" if success else "dialog-error.oga")

    def log(text_key, level="info", **kwargs):
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        text_template = lang_dict.get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_template

        if gui_instance and hasattr(gui_instance, "append_info"):
            gui_instance.append_info(widget, text, level)
        QApplication.processEvents()

    # --- Start ---
    set_progress(5)

    cfg = load_github_config()
    if not all([cfg.get("repo_url"), cfg.get("username"), cfg.get("token")]):
        log("github_patch_credentials_missing", "error")
        play_sound(False)
        set_progress(100, is_err=True)
        return

    # 2. Temp Verzeichnis vorbereiten
    set_progress(15)
    temp_repo = os.path.join(PLUGIN_DIR, "temp_patch_git")
    if os.path.exists(temp_repo):
        shutil.rmtree(temp_repo, ignore_errors=True)
    os.makedirs(temp_repo, exist_ok=True)

    # 3. Klonen
    set_progress(20)
    token_url = cfg["repo_url"].replace(
        "https://", f"https://{cfg['username']}:{cfg['token']}@"
    )
    code = run_bash(
        f"git clone --branch {cfg.get('branch', 'master')} {token_url} {temp_repo}",
        cwd=temp_repo,
        info_widget=widget,
    )

    if code != 0:
        log("github_clone_failed", "error")
        play_sound(False)
        set_progress(100, is_err=True)
        return

    # 4. Patch kopieren & Config
    set_progress(50)
    try:
        shutil.copy2(PATCH_FILE, os.path.join(temp_repo, "oscam-emu.patch"))
        run_bash(f'git config user.name "{cfg.get("user_name")}"', cwd=temp_repo)
        run_bash(f'git config user.email "{cfg.get("user_email")}"', cwd=temp_repo)
    except Exception as e:
        log("patch_failed", "error", path=str(e))
        set_progress(100, is_err=True)
        return

    # 5. Commit Vorbereitung
    set_progress(70)
    run_bash("git add -A", cwd=temp_repo)

    # Version aus Header lesen
    try:
        with open(PATCH_FILE, "r", encoding="utf-8") as f:
            patch_version = f.readline().strip() or "Update"
    except:
        patch_version = "Patch Update"

    commit_msg = (
        f"{patch_version} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    run_bash(f'git commit -m "{commit_msg}" --allow-empty', cwd=temp_repo)

    # 6. Push
    set_progress(85)
    push_code = run_bash(
        f"git push --force origin {cfg.get('branch', 'master')}", cwd=temp_repo
    )

    if push_code == 0:
        log("github_patch_uploaded", "success", patch_version=patch_version)
        play_sound(True)
        set_progress(100)
        if pbar:
            pbar.setFormat(
                "✅ Patch Uploaded" if lang != "de" else "✅ Patch hochgeladen"
            )
    else:
        log("github_upload_failed", "error")
        play_sound(False)
        set_progress(100, is_err=True)

    # 7. Cleanup
    shutil.rmtree(temp_repo, ignore_errors=True)


from datetime import datetime, timezone
import subprocess
import os
import shutil  # wird unten benötigt


def get_patch_header(repo_dir=None, lang="de", modifier=None):
    """
    Erzeugt den Patch-Header im exakten Format untereinander:
    1. patch version: ...
    2. patch date: ...
    3. patch modified by: ...
    """
    import os, subprocess, re
    from datetime import datetime, timezone

    if repo_dir is None:
        repo_dir = TEMP_REPO

    # 1. Namen und Sprache sicherstellen
    active_modifier = modifier or PATCH_MODIFIER
    lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))

    # Standardwerte
    version, build, emu_rev, commit = "2.26.01", "11938", "802", "N/A"

    # 2. Daten extrahieren
    globals_path = os.path.join(repo_dir, "globals.h")
    if os.path.exists(globals_path):
        try:
            with open(globals_path, "r", encoding="utf-8") as f:
                content = f.read()
                v_match = re.search(r'#define CS_VERSION\s+"([^"]+)"', content)
                if v_match:
                    v_parts = v_match.group(1).split("-")
                    version = v_parts[0]
                    build = v_parts[1] if len(v_parts) > 1 else build
        except:
            pass

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_dir,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except:
        pass

    # 3. Zeitstempel
    mod_date_str = datetime.now().strftime("%d/%m/%Y")
    patch_date_utc = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC (+00:00)"
    )

    # 4. Labels übersetzen
    label_version = lang_dict.get("patch_version_header", "patch version")
    label_date = lang_dict.get("patch_date", "patch date")
    label_modified = lang_dict.get("patch_modified_by", "patch modified by")

    # 5. Finaler String-Zusammenbau in DREI Zeilen (mit \n)
    # WICHTIG: Das \n nach dem Datum erzwingt die neue Zeile für den Modifier
    header = (
        f"{label_version}: {version}-{build}-{emu_rev} ({commit})\n"
        f"{label_date}: {patch_date_utc}\n"
        f"{label_modified} {active_modifier} ({mod_date_str})"
    )

    return header


# ===================== PATCH FUNCTIONS =====================
from PyQt6.QtWidgets import QTextEdit, QApplication
import os, subprocess, shutil


def create_patch(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Erstellt den Patch im TEMP_REPO mit Regenbogen-ProgressBar und Error-Feedback.
    Löscht statische Texte wie 'Einsatzbereit' beim Start.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtGui import QTextCursor
    import subprocess, os, shutil, platform, re

    # 1. Widget & Sprache & Modifier sicherstellen
    widget = info_widget
    if not isinstance(widget, QTextEdit) and gui_instance:
        widget = getattr(gui_instance, "info_text", None)

    lang = str(getattr(gui_instance, "LANG", "de")).lower()[:2]
    active_modifier = getattr(gui_instance, "patch_modifier", PATCH_MODIFIER)
    active_emu_repo = getattr(gui_instance, "EMUREPO", EMUREPO)

    # --- ZENTRALE PROGRESS LOGIK (KORRIGIERT) ---
    def set_progress(val, is_error=False):
        if gui_instance:
            pbar = getattr(gui_instance, "progress_bar", None)
            if pbar:
                # WICHTIG: Setzt das Format zurück auf Prozent (%)
                # Damit verschwindet "Tool einsatzbereit" sofort!
                pbar.setFormat("%p%")
                pbar.setTextVisible(True)

                if is_error:
                    # Roter Style bei Fehler
                    pbar.setStyleSheet(
                        """
                        QProgressBar { text-align: center; font-weight: 900; border: 2px solid #500; 
                        border-radius: 6px; background-color: #111; color: #FF0000; font-size: 12pt; }
                        QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #800, stop:1 #F00); border-radius: 4px; }
                    """
                    )
                elif val <= 15:
                    # Regenbogen Style bei Start
                    rainbow = (
                        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                        "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                        "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
                    )
                    pbar.setStyleSheet(
                        f"""
                        QProgressBar {{ text-align: center; font-weight: 900; border: 2px solid #222; 
                        border-radius: 6px; background-color: #111; color: black; font-size: 14pt; }}
                        QProgressBar::chunk {{ background-color: {rainbow} border-radius: 4px; }}
                    """
                    )
                    pbar.show()
                pbar.setValue(val)

        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    def log(text_key, level="info", **kwargs):
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        text_template = lang_dict.get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_template

        if isinstance(widget, QTextEdit):
            color = {"success": "green", "warning": "orange", "error": "red"}.get(
                level, "yellow"
            )
            widget.append(f'<span style="color:{color}"><b>{text}</b></span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()

    def play_sound(sound_name):
        safe_func = globals().get("safe_play")
        if safe_func:
            safe_func(sound_name)

    # --- START ---
    play_sound("dialog-information.oga")
    log("patch_create_start", "info")
    set_progress(10)  # Hier springt die Anzeige jetzt sofort wieder auf Prozent um

    # ... [Rest des Codes bleibt gleich] ...
    if not os.path.exists(TEMP_REPO):
        os.makedirs(TEMP_REPO, exist_ok=True)

    git_dir = os.path.join(TEMP_REPO, ".git")

    if os.path.exists(TEMP_REPO) and not os.path.exists(git_dir):
        log("patch_create_clone_start", "warning")
        try:
            shutil.rmtree(TEMP_REPO)
            os.makedirs(TEMP_REPO, exist_ok=True)
        except:
            log("delete_failed", "error", path=TEMP_REPO)

    try:
        # 2. Git Synchronisierung
        if not os.path.exists(git_dir):
            set_progress(20)
            subprocess.run(
                f"git clone {STREAMREPO} .",
                shell=True,
                cwd=TEMP_REPO,
                capture_output=True,
            )

        subprocess.run(
            ["git", "remote", "remove", "emu-repo"], cwd=TEMP_REPO, capture_output=True
        )
        subprocess.run(
            ["git", "remote", "add", "emu-repo", active_emu_repo],
            cwd=TEMP_REPO,
            capture_output=True,
        )

        set_progress(40)
        for cmd in [
            "git fetch --all",
            "git checkout -B master origin/master",
            "git reset --hard origin/master",
        ]:
            subprocess.run(cmd, shell=True, cwd=TEMP_REPO, capture_output=True)

        set_progress(70)

        # 3. HEADER & DIFF GENERIEREN
        header = get_patch_header(
            repo_dir=TEMP_REPO, lang=lang, modifier=active_modifier
        )
        diff = subprocess.check_output(
            ["git", "diff", "origin/master..emu-repo/master", "--", ".", ":!.github"],
            cwd=TEMP_REPO,
            text=True,
        )

        if not diff.strip():
            log("patch_create_no_changes", "warning")
            diff = "# No changes detected"

        # 4. DATEI SCHREIBEN
        with open(PATCH_FILE, "w", encoding="utf-8") as f:
            f.write(header + "\n" + diff + "\n")

        # --- REVISION EXTRAHIEREN ---
        try:
            rev_match = re.search(r"-(\d{5,6})-", header)
            if not rev_match:
                rev_log = subprocess.check_output(
                    ["git", "log", "origin/master", "-n", "10", "--pretty=format:%s"],
                    cwd=TEMP_REPO,
                    text=True,
                )
                rev_match = re.search(r"(?:r)?(\d{5,6})", rev_log)

            if rev_match:
                new_rev_found = rev_match.group(1)
                script_dir = os.path.dirname(os.path.realpath(__file__))
                rev_storage_path = os.path.join(script_dir, "oscam_rev.txt")
                with open(rev_storage_path, "w", encoding="utf-8") as f:
                    f.write(new_rev_found)

                if gui_instance:
                    gui_instance.current_rev = new_rev_found
                    if hasattr(gui_instance, "on_update_check_finished"):
                        gui_instance.on_update_check_finished(False, new_rev_found)

                if isinstance(widget, QTextEdit):
                    widget.append(
                        f'<br><span style="color:#FF0000; font-size:24px;"><b>[System]</b> Revision <b>{new_rev_found}</b> erfolgreich gespeichert.</span>'
                    )
            else:
                if isinstance(widget, QTextEdit):
                    widget.append(
                        '<br><span style="color:orange;">[Info] Revision nicht gefunden.</span>'
                    )
        except Exception as rev_err:
            if isinstance(widget, QTextEdit):
                widget.append(
                    f'<br><span style="color:red; font-size:11px;">[Debug] Rev-Save Fehler: {rev_err}</span>'
                )

        set_progress(90)
        log("patch_create_success", "success", patch_file=PATCH_FILE)

        if header.strip():
            header_lines = header.splitlines()
            if header_lines:
                log(
                    "patch_version_from_header",
                    "success",
                    patch_version=header_lines[0].strip(),
                )

        play_sound("complete.oga")

    except Exception as e:
        log("patch_create_failed", "error", error=str(e))
        set_progress(100, is_error=True)  # Bar rot färben
        play_sound("dialog-error.oga")
        return

    set_progress(100)


# ===================== backup_old_patch=====================
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QTextCursor
import shutil, os, re


def backup_old_patch(self, make_backup=True, info_widget=None, progress_callback=None):
    """
    Sichert den alten Patch und aktualisiert ihn mit Fortschrittsanzeige.
    Verhalten identisch zu zip_patch:
    - Regenbogen nur während des Vorgangs
    - Am Ende bleibt Text 3 Sekunden stehen, Chunk wird transparent
    """
    import os
    import shutil
    import re
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtCore import QTimer

    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(self, "info_text", None)
    )

    lang = getattr(self, "LANG", "de").lower()
    is_de = lang == "de"
    pbar = getattr(self, "progress_bar", None)

    # -------------------------------------------------
    # Helper
    # -------------------------------------------------

    def play_backup_sound(success=True):
        safe_play("complete.oga" if success else "dialog-error.oga")

    def set_progress(val, text=None):
        if not pbar:
            return

        # Regenbogen-Gradient in einer Zeile für Qt-kompatibles StyleSheet
        rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"

        pbar.setStyleSheet(
            f"""
            QProgressBar {{
                text-align: center;
                font-weight: 700;
                border: 2px solid #222;
                border-radius: 6px;
                background-color: #111;
                color: black;
                font-size: 11pt;
            }}
            QProgressBar::chunk {{
                background-color: {rainbow};
                border-radius: 4px;
            }}
            """
        )
        pbar.show()
        pbar.setValue(val)
        if text:
            pbar.setFormat(text)

        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except Exception:
                pass

    def finalize_pbar(text, visible_seconds=3):
        if not pbar:
            return

        # Finale Anzeige: Text schwarz, Chunk noch Regenbogen
        rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"
        pbar.setStyleSheet(
            f"""
            QProgressBar {{
                text-align: center;
                font-weight: 700;
                border: 2px solid #222;
                border-radius: 6px;
                background-color: #111;
                color: black;
                font-size: 15pt;
            }}
            QProgressBar::chunk {{
                background-color: {rainbow};
                border-radius: 4px;
            }}
            """
        )
        pbar.setValue(100)
        pbar.setFormat(text)

        # Nach 3 Sekunden Chunk transparent machen und Value auf 0
        QTimer.singleShot(
            visible_seconds * 1000,
            lambda: pbar.setStyleSheet(
                """
            QProgressBar {
                text-align: center;
                font-weight: 700;
                border: 2px solid #222;
                border-radius: 6px;
                background-color: #111;
                color: orange;
                font-size: 15pt;
            }
            QProgressBar::chunk {
                background-color: transparent;
            }
            """
            ),
        )
        QTimer.singleShot(visible_seconds * 1000, lambda: pbar.setValue(0))

    def log(text_key, level="info", **kwargs):
        template = TEXTS.get(lang, {}).get(text_key, text_key)
        try:
            text = template.format(**kwargs)
        except Exception:
            text = text_key
        if isinstance(widget, QTextEdit):
            self.append_info(widget, text, level)

    # -------------------------------------------------
    # START
    # -------------------------------------------------

    set_progress(10, "Vorbereiten..." if is_de else "Preparing...")
    log("backup_old_start", "info")

    old_patch = getattr(self, "OLD_PATCH_FILE", OLD_PATCH_FILE)
    alt_patch = getattr(self, "ALT_PATCH_FILE", ALT_PATCH_FILE)
    new_patch = PATCH_FILE

    dir_path = os.path.dirname(old_patch)
    if dir_path and not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            log("patch_failed", "error", path=str(e))
            play_backup_sound(False)
            finalize_pbar("❌ Fehler!" if is_de else "❌ Error!")
            return

    # Backup
    set_progress(30, "Sichere alten Patch..." if is_de else "Backing up old patch...")
    if os.path.exists(old_patch) and make_backup:
        try:
            shutil.copy2(old_patch, alt_patch)
            log("backup_done", "success", path=alt_patch)
        except Exception as e:
            log("patch_failed", "error", path=str(e))
            play_backup_sound(False)
            finalize_pbar("❌ Fehler!" if is_de else "❌ Error!")
            return
    else:
        log("no_old_patch", "info")

    # Patch vorhanden?
    set_progress(
        60, "Installiere neuen Patch..." if is_de else "Installing new patch..."
    )
    if not os.path.exists(new_patch):
        log("patch_file_missing", "error", path=new_patch)
        play_backup_sound(False)
        finalize_pbar("❌ Fehler!" if is_de else "❌ Error!")
        return

    # -------------------------------------------------
    # HAUPT-VORGANG
    # -------------------------------------------------

    try:
        shutil.copy2(new_patch, old_patch)
        set_progress(90)

        patch_version = "unbekannt"
        with open(old_patch, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(1000)
            match = re.search(r"(?i)patch[- ]version:\s*(.+)", content)
            if match:
                patch_version = match.group(1).strip()

        log(
            "new_patch_installed",
            "success",
            path=f"{old_patch} (v: {patch_version})",
        )
        play_backup_sound(True)

        # Finale Anzeige 3 Sekunden
        finalize_pbar("✅ Patch erfolgreich!" if is_de else "✅ Patch successful!")

        return

    except Exception as e:
        log("patch_failed", "error", path=str(e))
        play_backup_sound(False)
        finalize_pbar(f"❌ Fehler: {str(e)}" if is_de else f"❌ Error: {str(e)}")
        return


# ===================== CLEAN PATCH FOLDER =====================
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QTextCursor
import shutil, os


def clean_patch_folder(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Löscht temporäre Repos und Dateien mit Regenbogen-ProgressBar,
    schwarzer Schrift und zweisprachigem Abschluss.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import os, shutil, stat, subprocess, platform

    # ---------- 1) WIDGET & SPRACHE ----------
    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(gui_instance, "info_text", None)
    )

    lang = str(getattr(gui_instance, "LANG", "de")).lower()
    is_de = lang.startswith("de")

    # --- ZENTRALE PROGRESS LOGIK (Regenbogen & Schwarze Schrift) ---
    def set_p(val, is_error=False):
        if gui_instance:
            pbar = getattr(gui_instance, "progress_bar", None)
            if pbar:
                pbar.setFormat("%p%")  # Reset Text vom System-Check
                if is_error:
                    pbar.setStyleSheet(
                        """
                        QProgressBar { text-align: center; font-weight: 900; border: 2px solid #500; 
                        border-radius: 6px; background-color: #111; color: #FF0000; font-size: 12pt; }
                        QProgressBar::chunk { background-color: #800; border-radius: 4px; }
                    """
                    )
                else:
                    rainbow = (
                        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                        "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                        "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
                    )
                    # color: black für Kontrast auf Regenbogen
                    pbar.setStyleSheet(
                        f"""
                        QProgressBar {{ text-align: center; font-weight: 900; border: 2px solid #222; 
                        border-radius: 6px; background-color: #111; color: black; font-size: 14pt; }}
                        QProgressBar::chunk {{ background-color: {rainbow} border-radius: 4px; }}
                    """
                    )
                pbar.setValue(val)
                pbar.show()

        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    def log(text_key, level="info", **kwargs):
        lang_key = "de" if is_de else "en"
        lang_data = TEXTS.get(lang_key, TEXTS.get("en", {}))
        text_template = lang_data.get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except Exception:
            text = text_template

        if gui_instance and hasattr(gui_instance, "append_info"):
            gui_instance.append_info(widget, text, level)
        elif isinstance(widget, QTextEdit):
            color = {"success": "green", "warning": "orange", "error": "red"}.get(
                level, "gray"
            )
            widget.append(f'<span style="color:{color}">{text}</span>')
        QApplication.processEvents()

    def play_sound(sound_type="success"):
        sound = "complete.oga" if sound_type == "success" else "dialog-error.oga"
        if "safe_play" in globals():
            safe_play(sound)

    def on_rm_error(func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except:
            pass

    # ---------- 2) ABLAUF ----------
    set_p(5)
    log("cleanup_start", "info")

    targets = []
    # Sammle existierende Ziele (Ordner & Dateien)
    for var_name in ["TEMP_REPO", "TEMP_PATCH_GIT"]:
        path = globals().get(var_name)
        if path and os.path.exists(path):
            targets.append((path, "folder"))

    for var_name in ["PATCH_FILE", "ZIP_FILE"]:
        path = globals().get(var_name)
        if path and os.path.exists(path):
            targets.append((path, "file"))

    if not targets:
        set_p(100)
        log("cleanup_success", "success")
        bar_txt = "✅ Already empty" if not is_de else "✅ Bereits leer"
        if gui_instance and hasattr(gui_instance, "progress_bar"):
            gui_instance.progress_bar.setFormat(bar_txt)
        play_sound("success")
        return

    all_cleaned = True
    for i, (path, p_type) in enumerate(targets):
        try:
            if p_type == "folder":
                shutil.rmtree(path, onerror=on_rm_error)
            else:
                if os.path.exists(path):
                    os.chmod(path, stat.S_IWRITE)
                    os.remove(path)
        except Exception as e:
            log("delete_failed", "error", path=os.path.basename(path), error=str(e))
            all_cleaned = False

        set_p(10 + (i + 1) * (90 // len(targets)))

    # ---------- 3) ABSCHLUSS ----------
    set_p(100, is_error=not all_cleaned)
    log("cleanup_success", "success" if all_cleaned else "warning")

    # Zweisprachiger Bar-Text setzen
    if all_cleaned:
        bar_txt = "✅ Cleanup Done" if not is_de else "✅ Bereinigung fertig"
    else:
        bar_txt = "⚠️ Cleanup Partial" if not is_de else "⚠️ Teilweise bereinigt"

    if gui_instance and hasattr(gui_instance, "progress_bar"):
        gui_instance.progress_bar.setFormat(bar_txt)

    play_sound("success" if all_cleaned else "error")
    QApplication.processEvents()


# ===================== ICONS =====================
ICON_SIZE = 64


def create_icons():
    """
    Erstellt Icons für die GUI. Die Dateinamen sind kurz, damit
    keine Probleme mit zu langen Namen auftreten.
    """
    from PIL import Image, ImageDraw, ImageFont

    ensure_dir(ICON_DIR)

    icons = {"patch": "Patch", "info": "Info", "git": "Git"}

    for key, text in icons.items():
        # Icon-Größe
        img = Image.new("RGBA", (64, 64), (30, 30, 30, 255))
        draw = ImageDraw.Draw(img)

        # Schriftart
        try:
            fnt = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14
            )
        except:
            fnt = ImageFont.load_default()

        # Textgröße berechnen (textbbox statt textsize)
        bbox = draw.textbbox((0, 0), text, font=fnt)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = (64 - w) // 2, (64 - h) // 2

        draw.text((x, y), text, font=fnt, fill=(255, 255, 255, 255))

        # Kurzer, eindeutiger Dateiname
        file_name = os.path.join(ICON_DIR, f"{key}.png")
        img.save(file_name)


def get_icon_for(name):
    safe_name = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    path = os.path.join(ICON_DIR, safe_name + ".png")
    return QIcon(path) if os.path.exists(path) else QIcon()


# ===================== OSCAM-EMU GIT FUNCTIONS =====================
def clean_oscam_emu_git(progress_callback=None):
    """Löscht den Emu-Git Ordner stumm im Log, aber mit Sound-Feedback (Absturzsicher)."""
    import os, shutil, stat, platform, subprocess

    path = globals().get("PATCH_EMU_GIT_DIR") or globals().get("TEMP_PATCH_GIT")

    if progress_callback:
        progress_callback(30)

    if path and os.path.exists(path):
        try:

            def on_error(func, p, exc):
                try:
                    os.chmod(p, stat.S_IWRITE)
                    func(p)
                except:
                    pass

            # Ordner rekursiv löschen
            shutil.rmtree(path, onerror=on_error)

            # --- SICHERER SOUND BEI ERFOLG ---
            # safe_play übernimmt den Linux-Check und den paplay-Check automatisch
            safe_play("trash-empty.oga")

            if progress_callback:
                progress_callback(100)
            return "success"

        except Exception:
            # --- SICHERER SOUND BEI FEHLER ---
            safe_play("dialog-error.oga")
            return "error"

    if progress_callback:
        progress_callback(100)
    return "not_found"


# ===================== patch_oscam_emu_git=====================
def patch_oscam_emu_git(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Klont das Streamboard Git, wendet oscam-emu.patch an und zeigt Regenbogen-Progress.
    Formatiert die Revision sauber: Version (Neuer-Hash) ohne Duplikate.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import os, shutil, subprocess

    # --- Start-Sound sofort abspielen ---
    if "safe_play" in globals():
        safe_play("dialog-information.oga")

    # 1. Referenzen & Sprache sicherstellen
    gui = gui_instance
    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(gui, "info_text", None)
    )
    pbar = getattr(gui, "progress_bar", None)
    lang = getattr(gui, "LANG", "de").lower()

    # --- 2. STYLES (Regenbogen + Schwarze Schrift) ---
    rainbow = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
        "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
    )

    # WICHTIG: {{ }} für CSS-Klammern innerhalb von f-strings
    style_rb = f"""
        QProgressBar {{ 
            text-align: center; font-weight: 900; border: 2px solid #222;
            border-radius: 6px; background-color: #111; color: black; font-size: 12pt; 
        }}
        QProgressBar::chunk {{ background-color: {rainbow} border-radius: 4px; }}
    """
    style_err = "QProgressBar { text-align: center; font-weight: 900; border: 2px solid #500; border-radius: 6px; background-color: #111; color: #FF0000; font-size: 14pt; } QProgressBar::chunk { background-color: #800; }"

    def set_progress(val, txt=None, is_err=False):
        if pbar:
            pbar.setStyleSheet(style_err if is_err else style_rb)
            pbar.setValue(val)
            pbar.setFormat(txt if txt else "%p%")
            pbar.show()
            pbar.repaint()
        if progress_callback:
            try:
                progress_callback(val)
            except:
                pass
        QApplication.processEvents()

    def log(text_key, level="info", **kwargs):
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        text_template = lang_dict.get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_key
        if gui and hasattr(gui, "append_info"):
            gui.append_info(widget, text, level)
        QApplication.processEvents()

    # --- 3. START ABLAUF ---
    start_txt = "📂 Vorbereiten..." if lang == "de" else "📂 Preparing..."
    set_progress(5, start_txt)
    log("patch_emu_git_start", "info", path=PATCH_EMU_GIT_DIR)

    # Ordner bereinigen
    if os.path.exists(PATCH_EMU_GIT_DIR):
        shutil.rmtree(PATCH_EMU_GIT_DIR, ignore_errors=True)
    os.makedirs(PATCH_EMU_GIT_DIR, exist_ok=True)

    # --- 4. GIT CLONE ---
    clone_txt = "🌐 Streamboard Clone..." if lang == "de" else "🌐 Cloning..."
    set_progress(20, clone_txt)
    clone = subprocess.run(
        ["git", "clone", "-c", "http.sslVerify=false", STREAMREPO, "."],
        cwd=PATCH_EMU_GIT_DIR,
        capture_output=True,
        text=True,
    )

    if clone.returncode != 0:
        log("patch_emu_git_clone_failed", "error")
        set_progress(100, "❌ Clone Error", is_err=True)
        if "safe_play" in globals():
            safe_play("dialog-error.oga")
        return

    # --- 5. PATCH ANWENDEN ---
    patch_txt = "🔧 Patch anwenden..." if lang == "de" else "🔧 Applying Patch..."
    set_progress(50, patch_txt)
    if not os.path.exists(PATCH_FILE):
        log("patch_file_missing", "error")
        set_progress(100, "❌ No Patch File", is_err=True)
        return

    abs_patch_path = os.path.abspath(PATCH_FILE)
    apply_patch = subprocess.run(
        ["git", "apply", "--whitespace=fix", abs_patch_path],
        cwd=PATCH_EMU_GIT_DIR,
        capture_output=True,
        text=True,
    )

    if apply_patch.returncode != 0:
        log("patch_emu_git_apply_failed", "error")
        set_progress(100, "❌ Patch Failed", is_err=True)
        if "safe_play" in globals():
            safe_play("dialog-error.oga")
        return

    # --- 6. CONFIG & COMMIT ---
    set_progress(80, "💾 Committing...")
    cfg = load_github_config()
    user = cfg.get("user_name", "speedy005")
    mail = cfg.get("user_email", "patch@oscam.local")

    subprocess.run(
        ["git", "config", "user.name", user], cwd=PATCH_EMU_GIT_DIR, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", mail],
        cwd=PATCH_EMU_GIT_DIR,
        capture_output=True,
    )

    # Saubere Extraktion der Patch-Version ohne alte Hashes oder Präfixe
    clean_version = "Update"
    try:
        if os.path.exists(PATCH_FILE):
            with open(PATCH_FILE, "r", encoding="utf-8") as f:
                line = f.readline().strip()
                # 1. Präfixe entfernen
                v = line.replace("### ", "").replace("patch version: ", "").strip()
                # 2. Alles ab der ersten Klammer wegwerfen (alter Hash/Text)
                clean_version = v.split(" (")[0].strip()
    except:
        pass

    # Lokaler Commit mit der sauberen Version
    commit_msg = f"Sync patch {clean_version}"
    subprocess.run(["git", "add", "."], cwd=PATCH_EMU_GIT_DIR, capture_output=True)
    subprocess.run(
        ["git", "commit", "-am", commit_msg, "--allow-empty"],
        cwd=PATCH_EMU_GIT_DIR,
        capture_output=True,
    )

    # Den ECHTEN neuen Kurz-Hash auslesen
    rev_hash = "N/A"
    try:
        rev_res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PATCH_EMU_GIT_DIR,
            capture_output=True,
            text=True,
        )
        if rev_res.returncode == 0:
            rev_hash = rev_res.stdout.strip()
    except:
        pass

    # --- 7. FINALE ---
    # Erstellt das gewünschte Format: 2.26.02-11943-802 (7b6371d1)
    full_revision = f"{clean_version} ({rev_hash})"

    done_txt = "✅ Fertig!" if lang == "de" else "✅ Done!"
    set_progress(100, done_txt)
    log("patch_emu_git_done", "success")

    # Detaillierte Meldung im Info-Screen (Deutsch / Englisch)
    rev_label = "📝 Git-Revision:" if lang == "de" else "📝 Git Revision:"
    if gui:
        gui.append_info(widget, f"{rev_label} {full_revision}", "success")

    if "safe_play" in globals():
        safe_play("complete.oga")


def load_github_config():
    if os.path.exists(GITHUB_CONF_FILE):
        try:
            cfg = json.load(open(GITHUB_CONF_FILE))
            cfg.setdefault("repo_url", "")
            cfg.setdefault("branch", "master")
            cfg.setdefault("emu_repo_url", "")
            cfg.setdefault("emu_branch", "master")
            cfg.setdefault("username", "")
            cfg.setdefault("token", "")
            cfg.setdefault("user_name", "speedy005")
            cfg.setdefault("user_email", "patch@oscam.local")
            return cfg
        except:
            return {}
    return {}


def save_github_config(cfg):
    try:
        json.dump(cfg, open(GITHUB_CONF_FILE, "w"))
    except:
        pass


# ===================== GITHUB UPLOAD =====================
def _github_upload(
    dir_path,
    repo_url,
    gui_instance=None,
    info_widget=None,
    branch="master",
    commit_msg="Apply OSCam Emu Patch",
):
    from PyQt6.QtWidgets import QApplication
    import os, shutil

    # 1. Sicherstellen, dass wir die Progressbar finden
    # Falls gui_instance nicht übergeben wurde, versuchen wir es über info_widget.parent()
    pbar = None
    if gui_instance:
        pbar = getattr(gui_instance, "progress_bar", None)
    elif info_widget and hasattr(info_widget, "parentWidget"):
        # Notfall-Suche: Schauen ob das Parent-Fenster die Bar hat
        pbar = getattr(info_widget.parentWidget(), "progress_bar", None)

    lang = getattr(gui_instance, "LANG", "de").lower()

    # --- REGENBOGEN STYLE (Mit doppelten Klammern {{ }} für f-strings!) ---
    rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f00, stop:0.2 #f70, stop:0.4 #ff0, stop:0.6 #0f0, stop:0.8 #00f, stop:1 #80f);"

    style_rb = f"""
        QProgressBar {{ 
            text-align: center; 
            font-weight: 700; 
            border: 2px solid #222; 
            border-radius: 6px; 
            background-color: #111; 
            color: black; 
            font-size: 14pt; 
        }}
        QProgressBar::chunk {{ 
            background-color: {rainbow} 
            border-radius: 4px; 
        }}
    """

    def update_p(val, txt=None):
        if pbar:
            pbar.setStyleSheet(style_rb)
            pbar.setValue(val)
            if txt:
                pbar.setFormat(f"{val}% - {txt}")
            else:
                pbar.setFormat("%p%")
            pbar.show()
            pbar.repaint()
        QApplication.processEvents()

    # Logger Setup
    logger = lambda text, level="info": PatchManagerGUI.append_info(
        info_widget, text, level
    )

    # --- ABLAUF ---
    update_p(45, "Check Config...")
    cfg = load_github_config()

    # 2. Pfad & Git Init
    update_p(50, "Git Init...")
    if os.path.exists(os.path.join(dir_path, ".git")):
        shutil.rmtree(os.path.join(dir_path, ".git"), ignore_errors=True)

    token_url = repo_url.replace(
        "https://", f"https://{cfg.get('username')}:{cfg.get('token')}@"
    )

    run_bash("git init", cwd=dir_path, logger=logger)
    update_p(60, "Remote Add...")
    run_bash(f"git remote add origin {token_url}", cwd=dir_path, logger=logger)
    run_bash(f"git checkout -b {branch}", cwd=dir_path, logger=logger)

    # 3. Config & Commit
    update_p(75, "Committing...")
    run_bash(
        f'git config user.name "{cfg.get("user_name")}"', cwd=dir_path, logger=logger
    )
    run_bash(
        f'git config user.email "{cfg.get("user_email")}"', cwd=dir_path, logger=logger
    )
    run_bash("git add -A", cwd=dir_path, logger=logger)
    run_bash(f'git commit -m "{commit_msg}" --allow-empty', cwd=dir_path, logger=logger)

    # 4. Push
    update_p(90, "Pushing...")
    code = run_bash(f"git push origin {branch} --force", cwd=dir_path, logger=logger)

    # 5. Finale
    if code == 0:
        update_p(100, "✅ Success")
    else:
        update_p(100, "❌ Failed")


# ===================== GITHUB UPLOAD PATCH FILE =====================
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QTextCursor
import shutil, os


def run_bash(cmd, cwd=None, info_widget=None, lang="DE", logger=None):
    """
    Führt einen Bash-Befehl aus und schreibt jede Zeile live ins Info-Widget.
    Optimiert für Sprachunterstützung und ohne Terminal-Leaks.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtGui import QTextCursor
    import os, subprocess

    # 1. Widget-Suche (behalten)
    if not isinstance(info_widget, QTextEdit):
        active_win = QApplication.activeWindow()
        if active_win and hasattr(active_win, "info_text"):
            info_widget = active_win.info_text

    # Sprach-Dictionary laden
    current_lang = lang.lower()
    t = TEXTS.get(current_lang, TEXTS.get("en", {}))

    def log(text, level="info"):
        colors = {
            "success": "#27ae60",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "info": "#7f8c8d",
        }
        color = colors.get(level, "#7f8c8d")

        # Falls der Text ein Key ist, übersetzen, sonst Original behalten
        translated = t.get(text, text)

        if isinstance(info_widget, QTextEdit):
            info_widget.append(
                f'<span style="color:{color}; font-family: monospace;">{translated}</span>'
            )
            info_widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()
        else:
            # Falls kein GUI-Widget da ist (Notfall), schreibe ins Terminal
            print(f"[{level.upper()}] {translated}")

    # 2. Arbeitsverzeichnis validieren
    if cwd and not os.path.exists(cwd):
        try:
            os.makedirs(cwd, exist_ok=True)
        except Exception as e:
            log(f"Fehler: Verzeichnis konnte nicht erstellt werden {cwd}: {e}", "error")
            return -1

    # --- ÜBERSETZTER START-LOG (ERSETZT DAS ALTE 'Executing:...') ---
    exec_msg = t.get("executing_cmd", "Führe Befehl aus:")
    log(f"🚀 {exec_msg} {cmd}", "warning")

    try:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        # 3. Live-Ausgabe
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                line = line.strip()
                if line:
                    log(line, "info")
            process.stdout.close()

        return_code = process.wait()

        if return_code != 0:
            # Fehlermeldung übersetzen
            err_msg = t.get("cmd_failed", "Befehl fehlgeschlagen mit Code")
            log(f"❌ {err_msg} {return_code}", "error")

        return return_code

    except Exception as e:
        log(f"run_bash error: {e}", "error")
        return -1


# ===================== GITHUB UPLOAD OSCAM-EMU FOLDER =====================
def github_upload_oscam_emu_folder(
    gui_instance=None, info_widget=None, progress_callback=None
):
    """
    Lädt den gesamten Inhalt des OSCam-EMU-Git-Ordners auf GitHub hoch.
    Mit Regenbogen-Progressbar, schwarzer Schrift und DE/EN Support.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import os, subprocess, shutil

    # 1. Instanzen & Widgets
    gui = gui_instance
    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(gui, "info_text", None)
    )
    pbar = getattr(gui, "progress_bar", None)
    lang = getattr(gui, "LANG", "de").lower()

    # --- REGENBOGEN STYLES ---
    rainbow = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
        "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
    )

    # WICHTIG: Doppelte {{ }} damit CSS in f-strings funktioniert
    style_rb = f"""
        QProgressBar {{ 
            text-align: center; font-weight: 900; border: 2px solid #222;
            border-radius: 6px; background-color: #111; color: black; font-size: 14pt; 
        }}
        QProgressBar::chunk {{ background-color: {rainbow} border-radius: 4px; }}
    """
    style_err = "QProgressBar { text-align: center; font-weight: 900; border: 2px solid #500; border-radius: 6px; background-color: #111; color: #FF0000; font-size: 12pt; } QProgressBar::chunk { background-color: #800; }"

    def set_progress(val, txt=None, is_err=False):
        if pbar:
            pbar.setStyleSheet(style_err if is_err else style_rb)
            pbar.setValue(val)
            # Wenn kein Text übergeben wurde, zeige Prozent
            if txt:
                pbar.setFormat(txt)
            else:
                pbar.setFormat("%p%")
            pbar.show()
            pbar.repaint()
        if progress_callback:
            try:
                progress_callback(val)
            except:
                pass
        QApplication.processEvents()

    def play_sound(success=True):
        if "safe_play" in globals():
            safe_play("complete.oga" if success else "dialog-error.oga")

    def log(text_key, level="info", **kwargs):
        lang_dict = (
            globals()
            .get("TEXTS", {})
            .get(lang, globals().get("TEXTS", {}).get("en", {}))
        )
        fallback = text_key.replace("_", " ").capitalize()
        text_template = lang_dict.get(text_key, fallback)
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_template

        if gui and hasattr(gui, "append_info"):
            gui.append_info(widget, text, level)
        QApplication.processEvents()

    # --- Start der Logik ---
    # Zweisprachiger Start-Text für die Bar
    start_txt = "⏳ Start..." if lang == "de" else "⏳ Starting..."
    set_progress(5, start_txt)
    log("github_config_load", "info")

    cfg_func = globals().get("load_github_config")
    if not cfg_func:
        err_txt = "❌ Fehler" if lang == "de" else "❌ Error"
        log("Konfigurations-Ladefunktion fehlt!", "error")
        set_progress(100, err_txt, is_err=True)
        play_sound(False)
        return

    cfg = cfg_func()
    repo_url = cfg.get("emu_repo_url")
    branch = cfg.get("emu_branch", "master")
    username, token = cfg.get("username"), cfg.get("token")
    user_name, user_email = cfg.get("user_name"), cfg.get("user_email")

    if not all([repo_url, branch, username, token, user_name, user_email]):
        err_txt = "❌ Credentials" if lang == "de" else "❌ Auth Error"
        log("github_emu_git_missing", "error")
        set_progress(100, err_txt, is_err=True)
        play_sound(False)
        return

    target_dir = globals().get("PATCH_EMU_GIT_DIR")
    if not target_dir or not os.path.exists(target_dir):
        log("patch_emu_git_missing", "error", path=str(target_dir))
        set_progress(100, "❌ Folder", is_err=True)
        play_sound(False)
        return

    # Git Setup Phase
    init_txt = "🔧 Git Init..." if lang == "de" else "🔧 Setup Git..."
    set_progress(15, init_txt)
    token_url = repo_url.replace("https://", f"https://{username}:{token}@")
    git_dir = os.path.join(target_dir, ".git")
    silent_env = os.environ.copy()
    silent_env["GIT_TERMINAL_PROMPT"] = "0"

    try:
        if not os.path.exists(git_dir):
            log("git_repo_init", "warning")
            subprocess.run(["git", "init"], cwd=target_dir, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", token_url],
                cwd=target_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "-b", branch], cwd=target_dir, capture_output=True
            )
        else:
            log("git_remote_update", "info")
            subprocess.run(
                ["git", "remote", "remove", "origin"],
                cwd=target_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", token_url],
                cwd=target_dir,
                capture_output=True,
            )

        set_progress(40, "📝 Config...")
        subprocess.run(
            ["git", "config", "user.name", user_name],
            cwd=target_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", user_email],
            cwd=target_dir,
            capture_output=True,
        )

        # 3. Add & Commit
        add_txt = "📦 Archivieren..." if lang == "de" else "📦 Adding files..."
        set_progress(60, add_txt)
        log("git_adding_files", "info")
        subprocess.run(["git", "add", "."], cwd=target_dir, capture_output=True)

        commit_msg = "Sync OSCam-Emu folder"
        header_func = globals().get("get_patch_header")
        if header_func:
            try:
                raw = header_func()
                if raw:
                    commit_msg = raw.splitlines()[0]
            except:
                pass

        subprocess.run(
            ["git", "commit", "-m", commit_msg, "--allow-empty"],
            cwd=target_dir,
            capture_output=True,
        )

        # 4. Push
        push_txt = "🚀 Upload..." if lang == "de" else "🚀 Pushing..."
        set_progress(80, push_txt)
        log("github_upload_start", "warning")
        push = subprocess.run(
            ["git", "push", "--force", "origin", branch],
            cwd=target_dir,
            capture_output=True,
            text=True,
            env=silent_env,
        )

        if push.returncode == 0:
            log("github_emu_git_uploaded", "success")
            final_txt = (
                "✅ Ordner synchronisiert" if lang == "de" else "✅ Folder Synced"
            )
            set_progress(100, final_txt)
            play_sound(True)
        else:
            log("github_upload_failed", "error")
            fail_txt = (
                "❌ Upload fehlgeschlagen" if lang == "de" else "❌ Upload failed"
            )
            set_progress(100, fail_txt, is_err=True)
            play_sound(False)

    except Exception as e:
        log(f"Kritischer Fehler: {str(e)}", "error")
        set_progress(100, "❌ Error", is_err=True)
        play_sound(False)


# =====================
# GITHUB CONFIG DIALOG
# =====================
class GithubConfigDialog(QDialog):
    """Dialog for entering GitHub credentials - Absturzsicher"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Sprache sicher ermitteln
        self.lang = getattr(parent, "LANG", globals().get("LANG", "de"))

        # Titel sicher setzen (Fallback falls Key fehlt)
        title = TEXTS.get(self.lang, {}).get("github_dialog_title", "GitHub Config")
        self.setMinimumWidth(1100)  # Erhöht die Breite, damit Deutsch reinpasst
        self.resize(1200, 800)

        layout = QFormLayout(self)

        # Eingabefelder initialisieren
        self.patch_repo = QLineEdit()
        self.patch_branch = QLineEdit("master")
        self.emu_repo = QLineEdit()
        self.emu_branch = QLineEdit("master")
        self.username = QLineEdit()
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.user_name = QLineEdit("speedy005")
        self.user_email = QLineEdit("patch@oscam.local")

        # Bestehende Konfiguration laden
        try:
            cfg = load_github_config()
            self.patch_repo.setText(cfg.get("repo_url", ""))
            self.patch_branch.setText(cfg.get("branch", "master"))
            self.emu_repo.setText(cfg.get("emu_repo_url", ""))
            self.emu_branch.setText(cfg.get("emu_branch", "master"))
            self.username.setText(cfg.get("username", ""))
            self.token.setText(cfg.get("token", ""))
            self.user_name.setText(cfg.get("user_name", "speedy005"))
            self.user_email.setText(cfg.get("user_email", "patch@oscam.local"))
        except Exception as e:
            print(f"Fehler beim Laden der GitHub-Config: {e}")

        # Hilfsfunktion für sichere Texte
        def get_t(key, default):
            return TEXTS.get(self.lang, {}).get(key, default)

        # Layout Labels + Felder (Kein KeyError mehr möglich)
        layout.addRow(get_t("patch_repo_label", "Patch Repo:"), self.patch_repo)
        layout.addRow(get_t("patch_branch_label", "Patch Branch:"), self.patch_branch)
        layout.addRow(get_t("emu_repo_label", "EMU Repo:"), self.emu_repo)
        layout.addRow(get_t("emu_branch_label", "EMU Branch:"), self.emu_branch)
        layout.addRow(get_t("github_username_label", "GitHub User:"), self.username)
        layout.addRow(get_t("github_token_label", "GitHub Token:"), self.token)
        layout.addRow(get_t("github_user_name_label", "Git Name:"), self.user_name)
        layout.addRow(get_t("github_user_email_label", "Git Email:"), self.user_email)

        # Buttons erstellen
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)

        if self.save_button:
            self.save_button.setText(get_t("save", "Speichern"))
        if self.cancel_button:
            self.cancel_button.setText(get_t("cancel", "Abbrechen"))

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        """Speichert die eingegebenen Daten"""
        cfg = {
            "repo_url": self.patch_repo.text().strip(),
            "branch": self.patch_branch.text().strip(),
            "emu_repo_url": self.emu_repo.text().strip(),
            "emu_branch": self.emu_branch.text().strip(),
            "username": self.username.text().strip(),
            "token": self.token.text().strip(),
            "user_name": self.user_name.text().strip(),
            "user_email": self.user_email.text().strip(),
        }
        try:
            save_github_config(cfg)
            self.accept()
        except Exception as e:
            print(f"Fehler beim Speichern der GitHub-Config: {e}")
            self.reject()


from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize, QThread, pyqtSignal, QUrl


class TaskWorker(QThread):
    progress = pyqtSignal(int)
    info = pyqtSignal(str, str)
    finished = pyqtSignal(object)

    def __init__(self, target_fn, *args, **kwargs):
        super().__init__()
        self.target_fn = target_fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            # Übergibt den progress-Slot als 'progress_callback' an deine Funktionen
            result = self.target_fn(
                *self.args, progress_callback=self.progress.emit, **self.kwargs
            )
            self.finished.emit(result)
        except Exception as e:
            self.info.emit(f"Fehler: {str(e)}", "error")
            self.progress.emit(100)


# =====================
# PATCH MANAGER GUI
# =====================
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QSizePolicy,
    QFrame,
    QProgressBar,
    QSlider,
)

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, QTime, Qt, QPoint
from PyQt6.QtGui import QPainter, QPolygon, QColor


class AnalogClock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)
        self.setMinimumSize(100, 100)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QPolygon
        from PyQt6.QtCore import Qt, QPoint, QTime

        side = min(self.width(), self.height())
        time = QTime.currentTime()

        # --- MATRIX CHECK ---
        # Wir schauen im Hauptfenster nach, ob der Modus aktiv ist
        main_win = self.window()
        is_matrix = (
            getattr(main_win, "current_config", {}).get("theme_mode") == "matrix"
        )

        # Farben definieren
        color_accent = (
            QColor("#00FF41") if is_matrix else QColor("#EAFF00")
        )  # Grün oder Gelb
        color_bg = (
            QColor("#000000") if is_matrix else QColor("#1A1A1A")
        )  # Schwarz oder Dunkelgrau
        color_hour = (
            QColor("#008F11") if is_matrix else QColor(255, 0, 0)
        )  # Dunkelgrün oder Rot
        color_min = (
            QColor("#00FF41") if is_matrix else QColor(200, 200, 200)
        )  # Hellgrün oder Grau

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # In die Mitte des Widgets schieben
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        # --- Zifferblatt (Hintergrund) ---
        painter.setPen(color_accent)
        painter.setBrush(color_bg)
        painter.drawEllipse(-95, -95, 190, 190)

        # --- Markierungen (Stunden) ---
        painter.setPen(color_accent)
        for i in range(12):
            painter.drawLine(80, 0, 90, 0)
            painter.rotate(30.0)

        # --- Stundenzeiger ---
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color_hour)
        painter.save()
        painter.rotate(30.0 * ((time.hour() + time.minute() / 60.0)))
        painter.drawConvexPolygon(
            QPolygon([QPoint(6, 10), QPoint(-6, 10), QPoint(0, -50)])
        )
        painter.restore()

        # --- Minutenzeiger ---
        painter.setBrush(color_min)
        painter.save()
        painter.rotate(6.0 * (time.minute() + time.second() / 60.0))
        painter.drawConvexPolygon(
            QPolygon([QPoint(4, 10), QPoint(-4, 10), QPoint(0, -80)])
        )
        painter.restore()

        # --- Sekundenzeiger ---
        painter.setBrush(color_accent)
        painter.save()
        painter.rotate(6.0 * time.second())
        painter.drawConvexPolygon(
            QPolygon([QPoint(2, 10), QPoint(-2, 10), QPoint(0, -90)])
        )
        painter.restore()

        # Mittelpunkt abdecken
        painter.setBrush(color_accent)
        painter.drawEllipse(-5, -5, 10, 10)


class PatchManagerGUI(QWidget):
    def __init__(self):
        # 1. IMPORTS & INITIALER SCHUTZ
        from PyQt6.QtGui import QColor, QFont, QTextCursor, QIcon
        from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize, QUrl
        from PyQt6.QtWidgets import QLabel, QTextEdit, QVBoxLayout
        import subprocess, platform, shutil, os, re, sys

        self.is_loading = True  # Schutz vor Timer während Setup
        if "safe_play" in globals():
            safe_play("service-login.oga")

        # 2. ATTR-BOOTSTRAP
        self.btn_matrix = None
        self.slider_speed = None
        self.color_box = None
        self.status_leds = []  # System-Status LEDs
        self.user_leds = []  # User-Blink-LEDs
        self.all_buttons = []
        self.option_buttons = {}
        self.buttons = {}
        self._blink_state = True

        super().__init__()

        # --- TIMER-SEKTION ---
        # 3. INFOSCREEN & REDIRECTOR FIX
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        try:
            self.stdout_redir = StreamToGui()
            self.stdout_redir.callback = lambda msg: self.append_info(
                self.info_text, msg, "info"
            )
            sys.stdout = self.stdout_redir
            self.stderr_redir = StreamToGui()
            self.stderr_redir.callback = lambda msg: self.append_info(
                self.info_text, msg, "error"
            )
            sys.stderr = self.stderr_redir
        except Exception:
            pass

        # 4. KONFIGURATION LADEN
        try:
            self.current_config = load_config()
        except:
            self.current_config = {}
        self.cfg = self.current_config

        stored_lang = str(self.current_config.get("language", "de")).lower()
        self.LANG = stored_lang if stored_lang in ["en", "de"] else "de"
        self.patch_modifier = self.current_config.get("patch_modifier", "Default")
        self.base_dir = os.path.dirname(os.path.abspath(__file__))        
        self.PLUGIN_DIR = self.base_dir            # Arbeitsordner
        self.WORK_DIR = self.base_dir 
        self.TEMP_REPO = os.path.join(self.base_dir, "temp_repo")         # Temp-Repo Ordner
        self.PATCH_EMU_GIT_DIR = os.path.join(self.base_dir, "oscam-emu-git") # Emu-Git Ordner
        current_path = self.current_config.get(
            "s3_patch_path", globals().get("OLD_PATCH_DIR", "./")
        )
        self.OLD_PATCH_DIR = os.path.normpath(current_path)
        self.OLD_PATCH_FILE = os.path.join(self.OLD_PATCH_DIR, "oscam-emu.patch")
        self.ALT_PATCH_FILE = os.path.join(self.OLD_PATCH_DIR, "oscam-emu.altpatch")
        # --- Direkt nach ALT_PATCH_FILE einfügen ---
        target_dirs = [self.PLUGIN_DIR, self.TEMP_REPO, self.PATCH_EMU_GIT_DIR, self.OLD_PATCH_DIR]

        for d in target_dirs:
            if d and not os.path.exists(d):
                try:
                    os.makedirs(d, exist_ok=True)
                except:
                    pass

        # Basis-Variablen
        self.active_button_key = ""
        self.main_grid_layout = None
        self.latest_version = (
            globals().get("APP_VERSION", "1.0.0").replace("v", "").strip()
        )
        self.BUTTON_RADIUS = 5

        # 5. HAUPT-UI AUFBAUEN
        self.live_indicator = QLabel()
        # Initialer Text
        self.live_indicator.setText(
            "<span style='color:#ff0000;'>●</span> <span style='color:#ffffff;'>LIVE | System Monitor</span>"
        )
        self.live_indicator.setStyleSheet(
            """
            font-weight: bold; 
            font-family: 'Courier New', monospace;
            font-size: 22px;
            background: transparent;
        """
        )

        self.init_ui()

        # 6. TIMER VORBEREITEN (Nur für User-LEDs, nicht starten)
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.animate_status_bar)

        # 7. THEME & FARBEN
        saved_color = self.current_config.get("color", "Classics")
        if hasattr(self, "color_box") and self.color_box:
            self.color_box.blockSignals(True)
            index = self.color_box.findText(saved_color)
            if index != -1:
                self.color_box.setCurrentIndex(index)
            self.color_box.blockSignals(False)
            self.color_box.currentIndexChanged.connect(self.change_colors)

        self.update_language()
        self.change_colors()

        # Theme-Status ohne Blinken anwenden
        target_theme = self.current_config.get("theme_mode", "standard")
        if hasattr(self, "toggle_matrix"):
            self.toggle_matrix(force_state=target_theme)

        # ----------------------------
        # 8. FINALER SLIDER- & LED-FIX
        # ----------------------------
        current_speed = self.current_config.get("blink_speed", 0)

        if hasattr(self, "slider_speed") and self.slider_speed:
            self.slider_speed.blockSignals(True)
            self.slider_speed.setValue(current_speed)
            self.slider_speed.blockSignals(False)

            if hasattr(self, "update_label_only"):
                self.update_label_only(current_speed)

            if hasattr(self, "update_blink_speed"):
                self.slider_speed.valueChanged.connect(self.update_blink_speed)

        # System-Status LEDs immer statisch setzen
        if hasattr(self, "set_system_leds_static"):
            self.set_system_leds_static()

        # User-LED Timer beim Start stoppen
        if hasattr(self, "blink_timer"):
            self.blink_timer.stop()

        if hasattr(self, "update_blink_speed"):
            self.update_blink_speed(current_speed)

        if hasattr(self, "update_plugin_button_state"):
            self.update_plugin_button_state()

        # --- LED STATUS WIEDERHERSTELLEN ---
        # 1. Den Wert aus der geladenen Config holen (Standard: True)
        saved_led_enabled = self.current_config.get("led_enabled", True)

        # 2. Die Checkbox visuell synchronisieren (ohne Signale zu feuern)
        if hasattr(self, "led_checkbox"):
            self.led_checkbox.blockSignals(True)
            self.led_checkbox.setChecked(saved_led_enabled)
            self.led_checkbox.blockSignals(False)

        # 3. Die tatsächliche Blink-Logik/Timer starten oder stoppen
        self.toggle_leds(saved_led_enabled)
        # -----------------------------------

        lang = getattr(self, "LANG", "de").lower()
        init_msg = (
            "Initialisiere Generator..."
            if lang == "de"
            else "Initializing Generator..."
        )

        # Styling: Rot (#FF0000), Schriftstärke 900 (Extra Bold)
        self.info_text.setHtml(
            f"<div style='margin: 20px; font-family: sans-serif; text-align: center;'>"
            f"<b style='color:#FF0000; font-size:22pt; font-weight:900;'>{init_msg}</b>"
            f"</div>"
        )
        # Ganz am Ende der __init__ einfügen:

        # 1. Wert aus Config holen
        saved_led_enabled = self.current_config.get("led_enabled", True)

        # 2. Checkbox finden und setzen (WICHTIG: Name prüfen!)
        # Falls die Checkbox bei dir anders heißt, hier anpassen:
        target_cb = getattr(self, "led_checkbox", None)
        if target_cb:
            target_cb.blockSignals(True)
            target_cb.setChecked(saved_led_enabled)
            target_cb.blockSignals(False)

        # 3. Die Logik final erzwingen
        self.toggle_leds(saved_led_enabled)

        # 4. Falls der Timer trotzdem läuft, obwohl er aus sein soll:
        if not saved_led_enabled and hasattr(self, "blink_timer"):
            self.blink_timer.stop()
            if hasattr(self, "force_user_leds_static"):
                self.force_user_leds_static()

        # 1. Willkommens-Info (500ms)
        # QTimer.singleShot(500, self.show_welcome_info)

        # 2. System-Check (2000ms) - Injiziert sich in den Anker
        QTimer.singleShot(2000, lambda: self.run_full_system_check(clear_log=False))

        # 3. Update-Check (6000ms) - Wartet, bis der Check oben fertig "eingezogen" ist
        QTimer.singleShot(4000, self.check_for_update_on_start)

        # 4. OSCam Monitor (8500ms)
        QTimer.singleShot(6500, self.start_oscam_update_check)
        self.init_button_signals()
        
        self.is_loading = False  # Initialisierung abgeschlossen
    # =====================================================================
    # ANIMATIONS-LOGIK (Verhindert AttributeError)
    # =====================================================================
    def animate_status_bar(self):
        """Wechselt den Zustand der User-LEDs für den Blink-Effekt mit Theme-Support.
        System-Status LEDs bleiben immer statisch.
        """
        # --- 0. NOTBREMSE: Verhindert Blinken beim Start ---
        if getattr(self, "is_loading", False):
            return

        if not hasattr(self, "user_leds") or not self.user_leds:
            return

        # Blink-Status umschalten
        self._blink_state = getattr(self, "_blink_state", False)
        self._blink_state = not self._blink_state

        # 1️⃣ Theme-Check
        is_matrix = self.current_config.get("theme_mode") == "matrix"

        # 2️⃣ Farben & Rahmen definieren
        if self._blink_state:
            # AN-Zustand
            color = "#00FF41" if is_matrix else "cyan"
            border = "1px solid #008F11" if is_matrix else "1px solid white"
        else:
            # AUS-Zustand
            color = "#002200" if is_matrix else "#222"
            border = "1px solid #004400" if is_matrix else "1px solid #444"

        # 3️⃣ Stylesheet auf User-LEDs anwenden
        style = f"background-color: {color}; border-radius: 5px; border: {border};"
        for led in self.user_leds:
            try:
                led.setStyleSheet(style)
            except:
                continue

    def open_custom_folder(self, path):
        """Öffnet Ordner mit Regenbogen-Progress und Sound beim Start & Ende."""
        import os, platform, subprocess
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        # --- 1. SOUND BEIM ÖFFNEN (Start) ---
        if "safe_play" in globals():
            safe_play("service-login.oga")

        # Setup & Sprach-Check
        pbar = getattr(self, "progress_bar", None)
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = lang == "de"
        
        T_OPEN = "Öffne Ordner..." if is_de else "Opening folder..."
        T_DONE = "Ordner offen!" if is_de else "Folder opened!"

        if pbar:
            # REGENBOGEN-PROGRESS Setup
            rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                       "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                       "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    text-align: center; font-weight: 700; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """)
            pbar.setFormat(f"📂 {T_OPEN} %p%")
            pbar.setValue(20)
            pbar.show()
            QApplication.processEvents()

        # 2. Ordner-Logik
        try:
            if not path or not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

            if pbar: pbar.setValue(60)

            # Explorer starten
            if platform.system() == "Windows":
                os.startfile(os.path.normpath(path))
            else:
                cmd = "xdg-open" if platform.system() == "Linux" else "open"
                subprocess.Popen([cmd, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # --- 2. SOUND NACH DEM ÖFFNEN (Abschluss) ---
            if "safe_play" in globals():
                # Signalisiert, dass der Befehl durch ist
                safe_play("complete.oga") 

            if pbar:
                pbar.setValue(100)
                pbar.setFormat(f"✅ {T_DONE} 100%")

        except Exception:
            if "safe_play" in globals():
                safe_play("dialog-error.oga")
            if pbar: pbar.setValue(0)

        # 3. AUTO-RESET (3 Sekunden) -> Zurück zu Orange/Gold
        if pbar:
            def restore_pbar():
                pbar.setValue(0)
                pbar.setFormat("%p%")
                pbar.setStyleSheet("""
                    QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; 
                    color: white; text-align: center; font-weight: bold; }
                    QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }
                """)
            QTimer.singleShot(3000, restore_pbar)

    def on_telemetry_changed(self, state):
        """Bestätigungs-Dialog für Datenschutz mit Sound und Theme-Anpassung."""
        from PyQt6.QtWidgets import QMessageBox

        is_de = getattr(self, "LANG", "en") == "de"
        new_status = state == 2

        # --- A) SOUND EFFEKT (Frage-Sound) ---
        safe_play_func = globals().get("safe_play")
        if safe_play_func:
            safe_play_func("dialog-question.oga")

        # --- B) TEXTE ---
        if is_de:
            title = "Datenschutz-Einstellungen"
            msg = (
                "<b>Möchten Sie die anonyme Nutzungsstatistik {}?</b><br><br>"
                "Es werden keine privaten Daten gesendet. Es zählt lediglich "
                "den Start des Tools, um die Weiterentwicklung zu unterstützen."
            )
            btn_yes, btn_no = "Ja", "Nein"
            status_log = "aktiviert" if new_status else "deaktiviert"
        else:
            title = "Privacy Settings"
            msg = (
                "<b>Would you like to {} anonymous usage statistics?</b><br><br>"
                "No private data is sent. It only counts the start of the tool "
                "to support further development."
            )
            btn_yes, btn_no = "Yes", "No"
            status_log = "enabled" if new_status else "disabled"

        action = (
            ("aktivieren" if is_de else "enable")
            if new_status
            else ("deaktivieren" if is_de else "disable")
        )

        # --- C) MESSAGEBOX KONFIGURIEREN ---
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(msg.format(action))
        box.setIcon(QMessageBox.Icon.Question)

        # Theme-Anpassung (Dark Style für die Box erzwingen)
        box.setStyleSheet(
            "QLabel{ color: white; font-size: 10pt; } QPushButton{ width: 80px; height: 25px; }"
        )

        y_btn = box.addButton(btn_yes, QMessageBox.ButtonRole.YesRole)
        n_btn = box.addButton(btn_no, QMessageBox.ButtonRole.NoRole)
        box.setDefaultButton(n_btn)

        box.exec()

        # --- D) AUSWERTUNG ---
        if box.clickedButton() == y_btn:
            save_setting("allow_telemetry", new_status)
            if hasattr(self, "log_message"):
                prefix = "[EINSTELLUNGEN]" if is_de else "[SETTINGS]"
                log_msg = "Nutzungsstatistik" if is_de else "Usage statistics"
                self.log_message(f"{prefix} {log_msg} {status_log}.")

            # Sound für Erfolg
            if safe_play_func:
                safe_play_func("dialog-information.oga")
        else:
            # Checkbox ohne Trigger zurückdrehen
            self.telemetry_cb.blockSignals(True)
            self.telemetry_cb.setChecked(not new_status)
            self.telemetry_cb.blockSignals(False)

    def start_s3_menu(self):
        """Sucht s3 und startet das Terminal mit 'sudo ./s3 menu'."""
        import os, shutil

        s3_exec = None
        search_list = [
            "/opt/s3_neu/s3",
            "/opt/s3/s3",
            os.path.expanduser("~/s3/s3"),
            shutil.which("s3"),
        ]

        for path in search_list:
            if path and os.path.exists(path) and os.access(path, os.X_OK):
                s3_exec = path
                break

        if s3_exec:
            # Hier zwingen wir den Sudo-Modus für Simplebuild 3
            self.open_terminal(s3_path=s3_exec, use_sudo=True)
        else:
            if hasattr(self, "info_text"):
                self.info_text.append(
                    '<br><span style="color:red;"><b>❌ Fehler:</b> s3 Startdatei nicht gefunden!</span>'
                )
            self.open_terminal()

    def find_s3_executable(self):
        """Sucht automatisch nach der s3-Startdatei an bekannten Orten."""
        import os, shutil

        # 1. Prüfen, ob s3 global im System-PATH bekannt ist
        system_path = shutil.which("s3")
        if system_path:
            return system_path

        # 2. Liste der wahrscheinlichsten Verzeichnisse (wird nacheinander abgeklappert)
        search_dirs = [
            "/opt/s3_neu",
            "/opt/s3",
            os.path.expanduser("~/s3"),
            os.path.expanduser("~/simplebuild"),
            "/var/lib/s3",
        ]

        for d in search_dirs:
            full_path = os.path.join(d, "s3")
            if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                return full_path

        return None  # Nichts gefunden

    def apply_global_button_style(self, text_color="#EAFF00"):
        """Setzt die Schriftfarbe für ALLE Buttons in der GUI zentral."""
        style = f"""
            QPushButton {{
                color: {text_color};
                font-weight: bold;
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: #4d4d4d;
                border: 1px solid #00ADFF;
            }}
        """
        # Dies überschreibt die Button-Styles im gesamten Fenster
        self.setStyleSheet(self.styleSheet() + style)

    def pbar_idle(self):
        """
        Setzt die ProgressBar auf den lockeren 'Was bauen wir heute?'-Modus zurück.
        Berücksichtigt das aktuell gewählte Farbschema (Matrix, Light oder Gold).
        """
        pbar = getattr(self, "progress_bar", None)
        if not pbar:
            return

        # 1. Sprache & Text ermitteln
        is_de = getattr(self, "LANG", "de").lower() == "de"
        idle_msg = (
            "🛠️ Was bauen wir heute?" if is_de else "🛠️ What are we building today?"
        )

        # 2. Aktuellen Mode erkennen (Matrix, Light oder Standard)
        # Wir prüfen das Stylesheet des Hauptfensters oder die aktuelle Farbbox
        current_style = self.styleSheet()
        is_matrix = (
            "Matrix" in str(getattr(self, "current_color_name", ""))
            or "#00FF00" in current_style
        )
        is_light = "#F5F5F5" in current_style or not current_style

        # 3. Stylesheets definieren
        if is_matrix:
            # --- MATRIX MODE (Grüner Scanner) ---
            style = """
                QProgressBar { 
                    border: 2px solid #00FF00; border-radius: 8px; background-color: #001100; 
                    color: #00FF00; text-align: center; font-weight: 700; font-size: 18px; 
                    min-height: 35px; padding: 2px;
                }  
                QProgressBar::chunk { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #003300, stop:0.5 #00FF00, stop:1 #003300); 
                    border-radius: 6px; 
                }
            """
        elif is_light:
            # --- LIGHT MODE (Dezent Blau/Grau) ---
            style = """
                QProgressBar { 
                    border: 2px solid #BBB; border-radius: 8px; background-color: #EEE; 
                    color: #222; text-align: center; font-weight: 700; font-size: 18px; 
                    min-height: 35px; padding: 2px;
                }
                QProgressBar::chunk { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3498db, stop:1 #2980b9); 
                    border-radius: 6px; 
                } 
            """
        else:
            # --- EDLER GOLD/ORANGE STYLE (Dein Standard) ---
            style = """
                QProgressBar { 
                    border: 2px solid #444; border-radius: 8px; background-color: #1A1A1A; 
                    color: #FFD700; text-align: center; font-weight: 700; font-size: 20px; 
                    min-height: 35px; padding: 2px;
                }
                QProgressBar::chunk { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F37804, stop:1 #FFD700); 
                    border-radius: 6px; 
                }
            """

        # 4. Werte anwenden
        pbar.setStyleSheet(style)
        pbar.setValue(0)
        pbar.setFormat(idle_msg)
        pbar.setTextVisible(True)

    def export_log(self):
        """Speichert Log als Textdatei mit Sound beim Start und beim Erfolg."""
        import shutil, subprocess, os
        from datetime import datetime
        from PyQt6.QtWidgets import QFileDialog

        # --- 1. SOUND BEIM STARTEN (Klick auf Button) ---
        for player in ["paplay", "pw-play", "aplay"]:
            if shutil.which(player):
                # Ein dezenter Sound für den Klick/Start (Beispielpfad)
                start_sound = (
                    "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"
                )
                if os.path.exists(start_sound):
                    subprocess.Popen(
                        [player, start_sound],
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                    )
                break

        text = self.info_text.toPlainText()
        if not text.strip():
            return

        lang = getattr(self, "LANG", "de").lower()
        is_de = lang == "de"

        # Texte & Titel
        t_title = "Log speichern" if is_de else "Save Log"
        t_filter = "Textdateien (*.txt)" if is_de else "Text Files (*.txt)"
        t_success = "Log exportiert nach" if is_de else "Log exported to"
        t_error = "Fehler beim Speichern" if is_de else "Error saving file"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t_title,
            f"oscam_patch_manager_log_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            t_filter,
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)

                # Erfolgsmeldung im Log
                self.append_info(
                    self.info_text, f"✅ {t_success}: {file_path}", "success"
                )

                # --- 2. SOUND BEIM ERFOLGREICHEN SPEICHERN ---
                for player in ["paplay", "pw-play", "aplay"]:
                    if shutil.which(player):
                        success_sound = (
                            "/usr/share/sounds/freedesktop/stereo/complete.oga"
                        )
                        if os.path.exists(success_sound):
                            subprocess.Popen(
                                [player, success_sound],
                                stderr=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL,
                            )
                        break

            except Exception as e:
                self.append_info(self.info_text, f"❌ {t_error}: {e}", "error")

    def copy_to_clipboard(self):
        """Kopiert den Log in die Zwischenablage."""
        QApplication.clipboard().setText(self.info_text.toPlainText())
        # Kleiner visueller Effekt (Sound oder kurze Meldung)
        if globals().get("HAS_SOUND_SUPPORT"):
            # Nutzt deinen vorhandenen Beep
            import winsound

            winsound.MessageBeep()

    def _play_sys_sound(self, sound_type="standard"):
        """Spielt System-Sounds für Windows und Linux ohne externe Dateien."""
        import platform, subprocess, shutil

        try:
            if platform.system() == "Windows":
                import winsound

                # Asterisk für Standard, Exclamation für Web/Aktion
                alias = (
                    "SystemAsterisk"
                    if sound_type == "standard"
                    else "SystemExclamation"
                )
                winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
            else:
                # Linux Freedesktop Standards
                snd = (
                    "button-pressed.oga"
                    if sound_type == "standard"
                    else "dialog-information.oga"
                )
                for cmd in ["paplay", "canberra-gtk-play", "aplay"]:
                    if shutil.which(cmd):
                        path = f"/usr/share/sounds/freedesktop/stereo/{snd}"
                        subprocess.Popen([cmd, path], stderr=subprocess.DEVNULL)
                        break
        except:
            pass

    def init_button_signals(self):
        """Verknüpft die 3 Ordner-Buttons und alle anderen Funktionen sicher."""
        import os, platform, subprocess

        # 1. PRÄZISE ORDNER-ZUWEISUNG (Gemäß deiner Vorgabe)
        # Wir holen die Pfade sicher von self oder nutzen den Fallback auf das Tool-Verzeichnis
        # 1. PRÄZISE ORDNER-ZUWEISUNG (Korrektur der Variablennamen)
        path_map = {
            # Nutzt jetzt direkt self.WORK_DIR (das Plugin-Verzeichnis)
            "btn_open_work": getattr(self, "WORK_DIR", os.getcwd()),
            
            # Nutzt self.TEMP_REPO (oscam-svn)
            "btn_open_temp": getattr(self, "TEMP_REPO", os.path.join(os.getcwd(), "oscam-svn")),
            
            # Nutzt self.PATCH_EMU_GIT_DIR (oscam-emu-patch)
            "btn_open_emu":  getattr(self, "PATCH_EMU_GIT_DIR", os.path.join(os.getcwd(), "oscam-emu-patch")),
        }


        # 2. Die Ordner-Buttons scharf schalten
        for btn_name, path in path_map.items():
            btn = getattr(self, btn_name, None)
            if btn:
                try:
                    btn.clicked.disconnect() 
                except:
                    pass
                
                # Der Pfad 'p' wird hier fest an den Klick gebunden (Lambda-Freeze)
                btn.clicked.connect(lambda checked=False, p=path: self.open_custom_folder(p))
                
                if hasattr(self, "_play_sys_sound"):
                    btn.clicked.connect(lambda checked=False: self._play_sys_sound("standard"))

        # 3. FUNKTIONS-BUTTONS (Jetzt inklusive Header-Editor!)
        func_names = {
            "btn_check_tools": "run_full_system_check",
            "restart_tool_button": "restart_app",
            "clean_emu_button": "clean_emu_data",
            "patch_emu_git_button": "run_patch_process",
            # HIER DEN EDITOR HINZUFÜGEN:
            "btn_edit_patch": "edit_patch_header", 
        }

        for btn_attr, method_name in func_names.items():
            btn = getattr(self, btn_attr, None)
            method = getattr(self, method_name, None) # Holt die Methode nur, wenn sie existiert
            
            if btn and method:
                try:
                    btn.clicked.disconnect()
                except:
                    pass
                btn.clicked.connect(method)
            elif btn:
                # Schutz: Button deaktivieren statt Absturz, falls Methode fehlt
                btn.setEnabled(False)
                btn.setToolTip(f"Fehler: Methode '{method_name}' fehlt!")

    def setup_online_patch_ui(self, parent_layout):
        """Erstellt die UI für den Online-Download inklusive Sound-Feedback."""
        from PyQt6.QtWidgets import (
            QGroupBox,
            QVBoxLayout,
            QComboBox,
            QPushButton,
            QLabel,
        )
        import locale

        # Spracherkennung
        try:
            loc = locale.getlocale()[0] or locale.getdefaultlocale()[0] or "en"
            lang = loc[:2].lower()
        except:
            lang = "en"
        self.lang = lang  # Speichern für handle_online_patch_button

        # Lokalisierung
        if lang == "de":
            self.T_PATCH_TITLE = "🌐 Online Patch-Downloader"
            self.T_PATCH_SEL = "Quelle wählen:"
            self.T_PATCH_BTN = "Patch laden & prüfen"
        else:
            self.T_PATCH_TITLE = "🌐 Online Patch-Downloader"
            self.T_PATCH_SEL = "Select Source:"
            self.T_PATCH_BTN = "Download & Verify Patch"

        # UI Komponenten
        self.group_online = QGroupBox(self.T_PATCH_TITLE)
        layout_online = QVBoxLayout()

        self.combo_source = QComboBox()
        self.combo_source.addItems(ONLINE_PATCHES.keys())
        self.combo_source.setMinimumHeight(35)

        self.btn_online = QPushButton(self.T_PATCH_BTN)
        self.btn_online.setMinimumHeight(40)
        self.btn_online.setStyleSheet(
            "font-weight: bold; background-color: #2c3e50; color: white;"
        )

        # FIX: Hier wurde der Funktionsname korrigiert von download_and_apply... zu handle_online_patch_button
        self.btn_online.clicked.connect(self.handle_online_patch_button)

        layout_online.addWidget(QLabel(self.T_PATCH_SEL))
        layout_online.addWidget(self.combo_source)
        layout_online.addWidget(self.btn_online)
        self.group_online.setLayout(layout_online)
        parent_layout.addWidget(self.group_online)

        # Sound-Feedback
        safe_play_func = globals().get("safe_play")
        if safe_play_func:
            safe_play_func("dialog-information.oga")

    def handle_online_patch_button(self):
        """Download mit Regenbogen-Progress: 100% -> Reset -> Meldung (DE/EN)."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox, QApplication
        from PyQt6.QtCore import QTimer
        import os, requests, re

        # Hilfsfunktionen
        def _(k, d): return getattr(self, "get_t", lambda x, y: y)(k, d)
        
        lang = str(getattr(self, "lang", getattr(self, "LANG", "en"))).lower()[:2]
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)
        safe_play_func = globals().get("safe_play")

        # Texte
        T_WAIT = "🔍 " + _("patch_dl_wait", "Prüfe Versionen...")
        T_START = "🌐 " + _("patch_dl_start", "Download: ")
        T_SAVE = "💾 " + _("patch_dl_save", "Gespeichert: ")
        T_DONE = "Fertig!" if is_de else "Done!"
        T_CANCEL_MSG = "Abgebrochen" if is_de else "Cancelled"

        def restore_style():
            if pbar:
                pbar.setValue(0)
                pbar.setFormat("%p%")
                pbar.setStyleSheet("""
                    QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; 
                    color: white; text-align: center; font-weight: bold; }
                    QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }
                """)

        # 1. REGENBOGEN START (Schwarz, 15pt)
        if pbar:
            rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                       "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                       "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    text-align: center; font-weight: 900; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """)
            pbar.setFormat(f"{T_WAIT} %p%")
            pbar.setValue(15)
            pbar.show()
            QApplication.processEvents()

        # Versionen laden
        display_items = {}
        patch_list = globals().get("ONLINE_PATCHES", getattr(self, "ONLINE_PATCHES", {}))
        for name, url in patch_list.items():
            try:
                res = requests.get(url, headers={"Range": "bytes=0-511"}, timeout=3)
                v = re.search(r"patch version:\s*([\d\.-]+)", res.text)
                version = v.group(1) if v else "unknown"
                display_items[f"{name} [{version}]"] = (url, version, name)
            except: display_items[f"{name} [Offline]"] = (url, "unknown", name)

        if safe_play_func: safe_play_func("dialog-information.oga")

        dialog = QInputDialog(self)
        dialog.setWindowTitle(_("patch_dl_title", "Patch Download"))
        dialog.setLabelText(_("patch_dl_select", "Wähle einen Patch:"))
        dialog.setComboBoxItems(list(display_items.keys()))
        dialog.setOkButtonText("OK")
        dialog.setCancelButtonText("Abbrechen" if is_de else "Cancel")

        if dialog.exec():
            item = dialog.textValue()
            url, version, original_name = display_items[item]
            if pbar: pbar.setFormat(f"{T_START} %p%"); pbar.setValue(60)

            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                
                file_name = f"{original_name.split()[0].replace('(', '').lower()}_v{version}.patch"
                with open(file_name, "w", encoding="utf-8") as f: f.write(response.text)

                # --- ERFOLGS-ABLAUF: 100% -> Reset -> Meldung ---
                if safe_play_func: safe_play_func("complete.oga")
                if pbar:
                    pbar.setValue(100) # Erst voll
                    pbar.setFormat("100%")
                    pbar.repaint()
                    
                    def show_success():
                        pbar.setValue(0) # Dann ausblenden (0%)
                        pbar.setFormat(f"✅ {T_DONE}")
                        pbar.repaint()
                        QTimer.singleShot(3000, restore_style)
                    QTimer.singleShot(500, show_success)

            except Exception as e:
                if safe_play_func: safe_play_func("dialog-error.oga")
                if pbar: pbar.setStyleSheet("QProgressBar { color: red; font-weight: 900; }")

        else:
            # --- ABBRUCH-ABLAUF: 100% -> Reset -> Meldung ---
            if safe_play_func: safe_play_func("dialog-warning.oga")
            if pbar:
                pbar.setValue(100) # 1. Auf 100% (Regenbogen voll)
                pbar.setFormat("100%")
                pbar.repaint()
                QApplication.processEvents()
                
                def show_cancel_final():
                    pbar.setValue(0) # 2. Ausblenden (Reset auf 0)
                    pbar.setFormat(f"❌ {T_CANCEL_MSG}") # 3. Meldung in Rot
                    pbar.setStyleSheet("QProgressBar { text-align: center; color: red; font-weight: 900; border: 2px solid red; background: #111; font-size: 15pt; }")
                    pbar.repaint()
                    QTimer.singleShot(2500, restore_style)

                QTimer.singleShot(500, show_cancel_final)


    def run_patch_process(self, patch_data, is_dry_run=True):
        """Führt den Patch-Befehl per Pipe aus (Simulation oder echt)."""
        import subprocess

        cmd = ["patch", "-p1"]
        if is_dry_run:
            cmd.append("--dry-run")

        target_dir = getattr(self, "local_oscam_path", os.getcwd())

        try:
            process = subprocess.Popen(
                cmd,
                cwd=target_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=patch_data)

            if process.returncode != 0 and not is_dry_run:
                self.log(f"❌ Patch-Fehler:\n{stderr}")
            return process.returncode == 0
        except Exception as e:
            self.log(f"🚨 Subprocess Fehler: {e}")
            return False

    def log(self, message):
        """Hilfsfunktion für die Log-Ausgabe (falls nicht vorhanden)."""
        # Hier deine TextEdit-Logik einfügen, z.B.:
        # self.log_window.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        print(message)

    def get_language_flag(self):
        """Gibt die passende Flagge zur Systemsprache zurück."""
        try:
            import locale

            # Holen der Sprache (z.B. 'de_DE' oder 'en_US')
            loc = locale.getlocale()[0] or locale.getdefaultlocale()[0] or "en"
            lang = loc[:2].lower()
        except:
            lang = "en"

        # Mapping von Sprachcode zu Flaggen-Emoji
        flags = {
            "de": "🇩🇪",
            "en": "🇺🇸",
            "fr": "🇫🇷",
            "it": "🇮🇹",
            "es": "🇪🇸",
            "ru": "🇷🇺",
            "tr": "🇹🇷",
        }
        return flags.get(lang, "🌐")  # Weltkugel als Fallback

    def force_user_leds_static(self):
        """User-LEDs statisch setzen (NUR User-LEDs, Farbe Orange!)"""
        # Wir nutzen eine spezifische Farbe für User-LEDs,
        # damit sie sich von den grünen System-LEDs abheben.
        for led in getattr(self, "user_leds", []):
            # Nutze hier die Farbe deiner GUI (z.B. Orange #F37804)
            led.setStyleSheet(
                "background-color: #F37804; border-radius: 4px; border: 1px solid #555;"
            )

    def toggle_leds(self, enable: bool):
        """
        User-LEDs an/aus, Timer starten/stoppen, Config speichern.
        System-LEDs bleiben statisch.
        """
        # 1. Zuerst den Status in der geladenen Config setzen!
        # Das ist wichtig, damit update_blink_speed den neuen Wert sofort sieht.
        self.current_config["led_enabled"] = enable

        # 2. Timer-Logik
        if hasattr(self, "blink_timer") and self.blink_timer:
            if enable:
                # Falls ein Slider da ist, dessen Wert nutzen
                speed = (
                    self.slider_speed.value() if hasattr(self, "slider_speed") else 500
                )

                # Nur starten, wenn der Speed-Wert auch Blinken zulässt (>0 und <950)
                if 0 < speed < 950:
                    self.blink_timer.start(speed)
                else:
                    # Falls Slider auf STATIC oder OFF steht, trotz "Enable" nicht blinken
                    self.blink_timer.stop()
                    self.force_user_leds_static()
            else:
                # Global aus -> Timer stoppen
                self.blink_timer.stop()
                if hasattr(self, "force_user_leds_static"):
                    self.force_user_leds_static()

        # 3. Permanent speichern
        save_config({"led_enabled": enable}, gui_instance=self)

    def show_language_animation(self, lang_code):
        """Animation mit automatischem Fallback für fehlende Emoji-Fonts."""
        from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation, QRect, QEasingCurve, QTimer, Qt
        from PyQt6.QtGui import QFont, QFontInfo

        # 1. PRÜFUNG: Ist ein Emoji-Font installiert?
        emoji_font = QFont("Noto Color Emoji", 65)
        # Wir prüfen, ob das System den Font wirklich geladen hat
        has_emoji = QFontInfo(emoji_font).family().lower() == "noto color emoji"

        # 2. STYLING & TEXT-WEICHE
        if has_emoji:
            # EMOJI MODUS (Wenn Schriftart vorhanden)
            display_text = "🇩🇪" if lang_code == "de" else "🇺🇸"
            style = "background: transparent; border: none;"
            emoji_font.setFamilies(
                ["Noto Color Emoji", "Segoe UI Emoji", "Apple Color Emoji"]
            )
        else:
            # TEXT MODUS (Fallback für saubere Optik ohne Vierecke)
            if lang_code == "de":
                display_text = " DE "
                style = """
                    color: #FFCC00; 
                    background-color: #000000; 
                    border: 3px solid #FF0000; 
                    border-radius: 12px; 
                    font-size: 45px; 
                    font-weight: bold; 
                    padding: 8px;
                """
            else:
                display_text = " EN "
                style = """
                    color: #FFFFFF; 
                    background-color: #00247D; 
                    border: 3px solid #CF142B; 
                    border-radius: 12px; 
                    font-size: 45px; 
                    font-weight: bold; 
                    padding: 8px;
                """
            emoji_font = QFont("Segoe UI", 45, QFont.Weight.Bold)

        # 3. LABEL ERSTELLEN
        self.flag_label = QLabel(display_text, self)
        self.flag_label.setFont(emoji_font)
        self.flag_label.setStyleSheet(style)
        self.flag_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.flag_label.adjustSize()

        # 4. POSITIONIERUNG (Zentriert)
        start_x = (self.width() - self.flag_label.width()) // 2
        start_y = (self.height() - self.flag_label.height()) // 2

        # Opacity Effekt für sanftes Ausblenden
        op = QGraphicsOpacityEffect(self.flag_label)
        self.flag_label.setGraphicsEffect(op)

        # 5. ANIMATIONEN (Dauer: 1.2 Sekunden)
        # Bewegung nach oben
        self.anim = QPropertyAnimation(self.flag_label, b"geometry")
        self.anim.setDuration(1200)
        self.anim.setStartValue(
            QRect(
                start_x, start_y + 50, self.flag_label.width(), self.flag_label.height()
            )
        )
        self.anim.setEndValue(
            QRect(
                start_x, start_y - 70, self.flag_label.width(), self.flag_label.height()
            )
        )
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Fade Out (Verschwinden)
        self.op_anim = QPropertyAnimation(op, b"opacity")
        self.op_anim.setDuration(1200)
        self.op_anim.setStartValue(1.0)
        self.op_anim.setEndValue(0.0)

        # 6. START & CLEANUP
        self.flag_label.show()
        self.anim.start()
        self.op_anim.start()

        # Nach Abschluss das Label aus dem Speicher löschen
        QTimer.singleShot(1300, self.flag_label.deleteLater)

    def show_tool_help(self, tool_id):
        """Zeigt Status-Infos (Grün) oder Hilfe (Rot) für System-Tools an."""
        from PyQt6.QtWidgets import QMessageBox, QApplication
        import platform
        import shutil

        lang = getattr(self, "LANG", "de").lower()

        # 1. LIVE-CHECK: Ist das Tool installiert?
        path = shutil.which(tool_id)
        # Spezialfälle für PY und QT6, die nicht als binärer Pfad gesucht werden
        is_installed = path is not None or tool_id in ["py", "qt6"]

        # Mapping der Installations-Befehle
        commands = {
            "snd": "sudo apt update && sudo apt install pulseaudio-utils",
            "git": "sudo apt update && sudo apt install git",
            "patch": "sudo apt update && sudo apt install patch",
            "zip": "sudo apt update && sudo apt install zip",
            "gcc": "sudo apt update && sudo apt install build-essential",
            "make": "sudo apt update && sudo apt install make",
            "ssl": "sudo apt update && sudo apt install libssl-dev",
            "usb": "sudo apt update && sudo apt install libusb-1.0-0-dev",
        }

        cmd = commands.get(tool_id, "N/A")
        title = "Tool Status" if lang == "de" else "Tool Status"

        # 2. TEXT-ZUSAMMENSTELLUNG (WEICHE)
        if is_installed:
            # FALL: TOOL IST INSTALLIERT (GRÜN)
            tool_path = path if path else "System / Python"
            if lang == "de":
                msg = f"Das Tool <b style='color:#00FF00;'>{tool_id.upper()}</b> ist bereits installiert.<br><br>"
                msg += f"Pfad: <code style='background-color:#222; color:#00ADFF; padding:3px;'>{tool_path}</code>"
            else:
                msg = f"Tool <b style='color:#00FF00;'>{tool_id.upper()}</b> is already installed.<br><br>"
                msg += f"Path: <code style='background-color:#222; color:#00ADFF; padding:3px;'>{tool_path}</code>"
        else:
            # FALL: TOOL FEHLT (ROT)
            if lang == "de":
                msg = f"Das Tool <b style='color:#F37804;'>{tool_id.upper()}</b> wurde nicht im System gefunden.<br><br>"
                if platform.system() == "Linux" and cmd != "N/A":
                    msg += f"Installieren Sie es über das Terminal mit:<br><br><code style='background-color:#222; color:#00FF00; padding:5px;'>{cmd}</code>"
                else:
                    msg += "Bitte installieren Sie das erforderliche Paket manuell."
            else:
                msg = f"Tool <b style='color:#F37804;'>{tool_id.upper()}</b> not found in system.<br><br>"
                if platform.system() == "Linux" and cmd != "N/A":
                    msg += f"Install it via terminal using:<br><br><code style='background-color:#222; color:#00FF00; padding:5px;'>{cmd}</code>"
                else:
                    msg += "Please install the required package manually."

        # 3. MESSAGEBOX KONFIGURIEREN
        box = QMessageBox(self)
        box.setWindowTitle(title)
        # Icon-Weiche: Information bei Grün, Warnung bei Rot
        box.setIcon(
            QMessageBox.Icon.Information if is_installed else QMessageBox.Icon.Warning
        )
        box.setText(msg)

        # Buttons: Kopieren nur anzeigen, wenn das Tool fehlt
        copy_btn = None
        if not is_installed and cmd != "N/A":
            copy_btn = box.addButton(
                "Befehl kopieren" if lang == "de" else "Copy Command",
                QMessageBox.ButtonRole.ActionRole,
            )

        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()

        # 4. LOGIK FÜR DEN KOPIER-BUTTON
        if copy_btn and box.clickedButton() == copy_btn:
            QApplication.clipboard().setText(cmd)
            if hasattr(self, "append_info"):
                log_msg = f"📋 {tool_id.upper()} " + (
                    "Befehl kopiert" if lang == "de" else "Command copied"
                )
                self.append_info(getattr(self, "info_text", None), log_msg, "status")

    def update_label_only(self, value):
        """
        Aktualisiert Text und Farbe des Speed-Labels beim Programmstart.
        Optimiert für das dunkle UI-Design.
        """
        if not hasattr(self, "lbl_speed_val") or not self.lbl_speed_val:
            return

        # Farbcodes passend zum System-Check
        C_GREEN, C_RED, C_GRAY = "#2ecc71", "#FF0000", "#AAAAAA"

        if value >= 950:
            txt = "STATIC"
            style = f"color: {C_GREEN}; font-weight: bold; font-size: 18px; font-family: 'Segoe UI', sans-serif;"
        elif value <= 50:
            txt = "TURBO"
            style = f"color: {C_RED}; font-weight: bold; font-size: 18px; font-family: 'Segoe UI', sans-serif;"
        else:
            # Zeigt die Millisekunden an, falls kein Extremwert vorliegt
            txt = f"{value}ms"
            style = f"color: {C_GRAY}; font-weight: bold; font-size: 18px; font-family: 'Segoe UI', sans-serif;"

        self.lbl_speed_val.setText(txt)
        self.lbl_speed_val.setStyleSheet(style)

    def force_leds_static(self):
        """Kombinierte LED-Steuerung: Setzt Status-Farben und Design-Stile ohne Blinken."""
        # 1. Sicherheitscheck
        if not hasattr(self, "status_leds") or not self.status_leds:
            return

        # 2. Design-Modus ermitteln (Matrix oder Standard)
        is_matrix = False
        try:
            # Prüft erst den Button-Text, falls vorhanden, sonst die Config
            if hasattr(self, "btn_matrix") and self.btn_matrix:
                is_matrix = "EXIT" in self.btn_matrix.text()
            else:
                is_matrix = self.cfg.get("theme_mode") == "matrix"
        except:
            is_matrix = False

        # 3. LEDs aktualisieren
        for led in self.status_leds:
            try:
                led.show()  # Sicherstellen, dass sie sichtbar sind

                # Tool-Status ermitteln (Grün wenn vorhanden, sonst Rot)
                exists = getattr(led, "tool_exists", False)

                if is_matrix:
                    # Im Matrix-Modus: Hellgrün für OK, Dunkelgrün/Grau für Fehlend
                    color = "#00FF41" if exists else "#003311"
                    border = "1px solid #00FF41"
                else:
                    # Im Standard-Modus: Kräftiges Rot/Grün
                    color = "#27ae60" if exists else "#c0392b"
                    border = "2px solid #555"

                led.setStyleSheet(
                    f"""
                    background-color: {color}; 
                    border-radius: 6px; 
                    border: {border};
                """
                )
            except:
                continue

    def load_config_from_file(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}  # Fallback

    def update_blink_speed(self, value):
        """
        Nur User-LEDs blinken lassen, System-LEDs bleiben statisch.
        0=OFF, >=950=STATIC, sonst blinkend (nur wenn led_enabled in Config).
        """
        timer = getattr(self, "blink_timer", None)
        if not timer or getattr(self, "is_loading", False):
            return

        # 1. UI Feedback (Texte & Farben des Labels)
        if hasattr(self, "lbl_speed_val"):
            if value <= 0:
                self.lbl_speed_val.setText("OFF")
                self.lbl_speed_val.setStyleSheet(
                    "color: #777; font-weight: bold; font-size: 12px;"
                )
            elif value >= 950:
                self.lbl_speed_val.setText("STATIC")
                self.lbl_speed_val.setStyleSheet(
                    "color: #2ecc71; font-weight: bold; font-size: 12px;"
                )
            elif value <= 50:
                self.lbl_speed_val.setText("TURBO")
                self.lbl_speed_val.setStyleSheet(
                    "color: #FF0000; font-weight: bold; font-size: 12px;"
                )
            else:
                self.lbl_speed_val.setText(f"{value}ms")
                self.lbl_speed_val.setStyleSheet(
                    "color: #aaa; font-weight: bold; font-size: 12px;"
                )

        # 2. Logik: Soll überhaupt geblinkt werden?
        # Wir prüfen den globalen "An/Aus"-Schalter aus der Config
        is_led_globally_enabled = self.current_config.get("led_enabled", True)
        config_updates = {"blink_speed": value}

        # Bedingung zum STOPPEN:
        # Slider auf 0 ODER Slider auf Max ODER User hat Blinken global deaktiviert
        if value <= 0 or value >= 950 or not is_led_globally_enabled:
            timer.stop()
            if hasattr(self, "force_user_leds_static"):
                self.force_user_leds_static()

            # Nur wenn der Slider selbst auf 0/Max steht, ändern wir led_enabled in der Config
            if value <= 0 or value >= 950:
                config_updates["led_enabled"] = value > 0
        else:
            # Bedingung zum STARTEN/AKTUALISIEREN:
            timer.setInterval(max(10, value))
            if not timer.isActive():
                timer.start()
            config_updates["led_enabled"] = True

        # 3. Speichern & System-Status
        # Falls du die Checkbox in der UI hast, hier ggf. synchronisieren:
        # if hasattr(self, "led_checkbox"): self.led_checkbox.setChecked(config_updates.get("led_enabled", is_led_globally_enabled))

        save_config(config_updates, gui_instance=self, silent=True)

    def set_system_leds_static(self):
        """System-LEDs immer statisch lassen"""
        for led in getattr(self, "status_leds", []):
            led.setStyleSheet("background-color: green; border-radius: 4px;")

    def get_matrix_style(self):
        return """
            QWidget { background-color: #0D0D0D; color: #00FF41; font-family: 'Segoe UI', 'Ubuntu', sans-serif; }
            QGroupBox { border: 2px solid #008F11; border-radius: 8px; margin-top: 1ex; font-weight: bold; }
            QTextEdit { background-color: #000000; border: 1px solid #00FF41; color: #00FF41; font-family: 'Consolas', monospace; font-size: 20px; }
            QPushButton { background-color: #1A1A1A; color: #00FF41; border: 1px solid #008F11; border-radius: 4px; padding: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #008F11; color: #000000; }
            QLabel { color: #00FF41; }
            QLineEdit { background-color: #1A1A1A; border: 1px solid #008F11; color: #FFFFFF; }
            QProgressBar { border: 1px solid #008F11; border-radius: 5px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #008F11; }
        """

    def toggle_matrix(self, force_state=None):
        """
        Schaltet das neon-grüne Matrix-Theme um.
        Inklusive Sofort-Update für die Analog-Uhr und Header-Elemente.
        """
        if not hasattr(self, "btn_matrix") or not self.btn_matrix:
            return

        # 1. Sprache und Texte laden
        lang_code = getattr(self, "LANG", "de").lower()
        t = TEXTS.get(lang_code, TEXTS.get("en", {}))

        # 2. Aktuelle Konfiguration und Ziel-Modus bestimmen
        cfg = getattr(self, "current_config", {})
        current_mode = cfg.get("theme_mode", "standard")
        target_mode = (
            force_state
            if force_state
            else ("matrix" if current_mode != "matrix" else "standard")
        )

        if target_mode == "matrix":
            # --- MATRIX STYLE (Neon-Grün auf Schwarz) ---
            matrix_qss = """
                QWidget { background-color: #000000; color: #00FF41; font-family: 'Segoe UI', 'Consolas'; }
                QGroupBox { border: 2px solid #008F11; border-radius: 8px; margin-top: 1ex; font-weight: bold; color: #00FF41; }
                QTextEdit { background-color: #050505; border: 1px solid #00FF41; color: #00FF41; font-family: 'Consolas'; font-size: 20px; }
                QPushButton { background-color: #111; color: #00FF41; border: 1px solid #008F11; border-radius: 5px; padding: 5px; font-weight: bold; }
                QPushButton:hover { background-color: #008F11; color: #000; border: 1px solid #00FF41; }
                QLabel { color: #00FF41; background: transparent; border: none; }
                QProgressBar { border: 1px solid #008F11; border-radius: 5px; text-align: center; color: white; background-color: #111; }
                QProgressBar::chunk { background-color: #008F11; }
                QLineEdit { background-color: #111; border: 1px solid #008F11; color: #00FF41; padding: 2px; }
                
                /* Matrix-Style für Slider */
                QSlider::groove:horizontal { border: 1px solid #008F11; height: 6px; background: #000; border-radius: 3px; }
                QSlider::handle:horizontal { background: #00FF41; border: 1px solid #008F11; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
            """
            self.setStyleSheet(matrix_qss)
            self.btn_matrix.setText(t.get("matrix_btn_exit", "🔙 EXIT MATRIX"))
            cfg["theme_mode"] = "matrix"

            # Header-Logos/Frames anpassen falls vorhanden
            if hasattr(self, "header_widget"):
                self.header_widget.setStyleSheet(
                    "background-color: #000; border: 1px solid #008F11;"
                )

            # Log-Ausgabe
            if hasattr(self, "info_text") and not getattr(self, "is_loading", False):
                sys_tag = f"<b>[{t.get('matrix_sys', 'System')}]</b>"
                msg = f'<br><span style="color:#00FF41; font-family:Consolas, monospace;">{sys_tag} {t.get("matrix_on", "Wake up, Neo... Matrix Mode engaged. ■")}</span>'
                self.info_text.append(msg)

            if "safe_play" in globals() and not getattr(self, "is_loading", False):
                safe_play("dialog-information.oga")

        else:
            # --- STANDARD STYLE ---
            self.setStyleSheet("")  # Setzt alles auf die Standard-Werte zurück

            # WICHTIG: Falls du in init_ui ein spezielles Grau-Gelb-Design hast,
            # musst du es hier ggf. wieder zuweisen oder leer lassen für System-Farben.

            # Slider-Style zurücksetzen
            target_slider = getattr(
                self, "blink_slider", getattr(self, "slider_speed", None)
            )
            if target_slider:
                target_slider.setStyleSheet(
                    """
                    QSlider::groove:horizontal { border: 1px solid #666; height: 6px; background: #222; border-radius: 3px; }
                    QSlider::handle:horizontal { background: #F37804; border: 1px solid #444; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
                """
                )

            self.btn_matrix.setText(t.get("matrix_btn_enter", "📟 MATRIX MODE"))
            cfg["theme_mode"] = "standard"

            # Log-Ausgabe
            if hasattr(self, "info_text") and not getattr(self, "is_loading", False):
                sys_tag = f"<b>[{t.get('matrix_sys', 'System')}]</b>"
                msg = f'<br><span style="color:orange; font-family:Consolas, monospace;">{sys_tag} {t.get("matrix_off", "Matrix Mode disabled.")}</span>'
                self.info_text.append(msg)

        # 3. Uhr-Update (Zwingt die AnalogClock zum Farbwechsel)
        if hasattr(self, "analog_clock"):
            self.analog_clock.update()

        # 4. Synchronisierung & Speicherung
        if hasattr(self, "force_leds_static"):
            self.force_leds_static()

        # Dauerhaft in Konfiguration sichern
        if not getattr(self, "is_loading", False):
            if "save_config" in globals():
                save_config(cfg, gui_instance=self, silent=True)

    def toggle_theme(self):
        """Schaltet zwischen Matrix-Mode (Dark) und System-Style (Light) um."""
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication

        lang = getattr(self, "LANG", "de").lower()
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)
        btn_online = getattr(self, "btn_patch_online", None)  # Dein neuer Button

        # Prüfen, ob wir gerade im System-Style (Light) sind
        if not self.styleSheet():
            # --- WECHSEL ZU MATRIX MODE (DARK) ---
            self.setStyleSheet(self.get_matrix_style())
            self.theme_button.setText("☀️ Light Mode")

            # 1. STYLE FÜR ONLINE-BUTTON (Orange/Gold Schema)
            if btn_online:
                btn_online.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F37804, stop:1 #8B4513);
                        color: white; font-weight: 700; border: 1px solid #444; border-radius: 10px;
                        font-size: {getattr(self, 'font_size_buttons', 12)}px;
                    }}
                    QPushButton:hover {{ background-color: #FFA500; border: 1px solid #ffffff; }}
                """
                )

            # 2. PROGRESSBAR (Regenbogen + Schwarze Schrift)
            if pbar:
                rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"
                pbar.setStyleSheet(
                    f"""
                    QProgressBar {{ text-align: center; font-weight: 700; border: 2px solid #222; border-radius: 6px; background-color: #111; color: black; font-size: 11pt; }}
                    QProgressBar::chunk {{ background: {rainbow}; border-radius: 4px; }}
                """
                )
                msg = "Matrix Mode aktiviert" if is_de else "Matrix Mode activated"
                pbar.setValue(100)
                pbar.setFormat(msg)
                if hasattr(self, "pbar_idle"):
                    QTimer.singleShot(3000, self.pbar_idle)

        else:
            # --- WECHSEL ZU SYSTEM STYLE (LIGHT) ---
            self.setStyleSheet("")  # Reset
            self.theme_button.setText("📟 Matrix Mode")

            # 1. STYLE FÜR ONLINE-BUTTON (Blau Schema)
            if btn_online:
                btn_online.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3498db, stop:1 #2980b9);
                        color: white; font-weight: 700; border: 1px solid #1c5980; border-radius: 10px;
                        font-size: {getattr(self, 'font_size_buttons', 12)}px;
                    }}
                    QPushButton:hover {{ background-color: #5dade2; border: 1px solid #ffffff; }}
                """
                )

            # 2. PROGRESSBAR (Schlicht)
            if pbar:
                pbar.setStyleSheet(
                    "QProgressBar { text-align: center; font-weight: 700; border: 1px solid #AAA; border-radius: 5px; background-color: #DDD; color: black; } QProgressBar::chunk { background-color: #4CAF50; }"
                )
                msg = "System Style aktiviert" if is_de else "System Style activated"
                pbar.setValue(100)
                pbar.setFormat(msg)
                if hasattr(self, "pbar_idle"):
                    QTimer.singleShot(3000, self.pbar_idle)

        if "safe_play" in globals():
            safe_play("dialog-information.oga")
        QApplication.processEvents()

    def animate_everything(self):
        """Steuert das Blinken von Text und LEDs."""
        self._blink_state = not self._blink_state
        # 2. LEDs blinken lassen (Matrix-Check inklusive)
        is_matrix = "EXIT" in self.btn_matrix.text()

        for led in self.status_leds:
            if self._blink_state:
                # AN-Phase
                color = led.base_color if not is_matrix else "#00FF41"
                border = "#FFF" if not is_matrix else "#00FF41"
            else:
                # AUS-Phase (Abgedunkelt)
                color = "#1a532d" if led.tool_exists else "#5a1a14"
                border = "#333"

            led.setStyleSheet(
                f"background-color: {color}; border-radius: 7px; border: 2px solid {border};"
            )

    def get_status_indicator(self, tool_name):
        """Erzeugt ein Widget mit LED-Punkt und Label für den Systemcheck."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(6)

        # Die LED (ein Kreis)
        led = QLabel()
        led.setFixedSize(10, 10)

        # Prüfung ob Tool (git, patch, etc.) im Systempfad ist
        exists = shutil.which(tool_name) is not None
        color = "#27ae60" if exists else "#c0392b"  # Grün wenn da, Rot wenn fehlt

        led.setStyleSheet(
            f"""
            background-color: {color}; 
            border-radius: 5px; 
            border: 1px solid rgba(255,255,255,0.3);
        """
        )

        # Das Text-Label daneben
        label = QLabel(tool_name.lower())
        label.setFont(QFont("Monospace", 9))

        layout.addWidget(led)
        layout.addWidget(label)
        return container

    def toggle_theme(self):
        """
        Schaltet zwischen Light, Dark und Matrix Mode um, aktualisiert die UI
        und speichert die Auswahl dauerhaft in der Config-Datei.
        """
        import json

        # Aktuellen Modus aus den globalen Variablen holen (geladen durch load_config)
        current_mode = globals().get("THEME_MODE", "standard")
        lang = getattr(self, "LANG", "de").lower()

        # 1. Logik für den Wechsel (Rotation: Standard -> Dark -> Matrix -> zurück)
        if current_mode == "standard":
            new_mode = "dark"
        elif current_mode == "dark":
            new_mode = "matrix"
        else:
            new_mode = "standard"

        # 2. Globale Variable sofort aktualisieren
        globals()["THEME_MODE"] = new_mode

        # 3. THEMEN ANWENDEN
        if new_mode == "standard":
            # --- LIGHT MODE ---
            self.setStyleSheet("background-color: #F5F5F5; color: #222;")
            self.info_text.setStyleSheet(
                "background-color: #FFFFFF; color: #222; border: 1px solid #CCC; border-radius: 5px;"
            )
            if hasattr(self, "header_widget"):
                self.header_widget.setStyleSheet(
                    "background-color: #E0E0E0; border: 1px solid #BBB; border-radius: 10px;"
                )
            self.btn_theme.setStyleSheet(
                "background-color: #DDD; color: #222; border: 1px solid #BBB; border-radius: 4px; font-size: 10px;"
            )
            self.btn_theme.setText("☀️ Light Mode")

            pbar = getattr(self, "progress_bar", None)
            if pbar:
                pbar.setStyleSheet(
                    "QProgressBar { text-align: center; border: 1px solid #BBB; border-radius: 5px; background-color: #EEE; color: #222; }"
                )
                pbar.setFormat("Helles Design" if lang == "de" else "Light Mode")

        elif new_mode == "dark":
            # --- DARK MODE ---
            self.setStyleSheet("background-color: #2F2F2F; color: #EEE;")
            self.info_text.setStyleSheet(
                "background-color: #000000; color: #FFFFFF; border: 1px solid #444; border-radius: 5px;"
            )
            if hasattr(self, "header_widget"):
                self.header_widget.setStyleSheet(
                    "background-color: #2F2F2F; border: 1px solid #444; border-radius: 10px;"
                )
            self.btn_theme.setStyleSheet(
                "background-color: #3D3D3D; color: #EEE; border: 1px solid #555; border-radius: 4px; font-size: 10px;"
            )
            self.btn_theme.setText("🌓 Dark Mode")

            pbar = getattr(self, "progress_bar", None)
            if pbar:
                rainbow = (
                    "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                    "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                    "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF)"
                )
                pbar.setStyleSheet(
                    f"QProgressBar {{ text-align: center; border: 2px solid #222; border-radius: 6px; background-color: #111; color: black; font-weight: bold; }}"
                    f"QProgressBar::chunk {{ background: {rainbow}; border-radius: 4px; }}"
                )
                pbar.setFormat("Dunkles Design" if lang == "de" else "Dark Mode")

        elif new_mode == "matrix":
            # --- MATRIX MODE ---
            # Klassisches Hacker-Grün auf Schwarz
            self.setStyleSheet("background-color: #000000; color: #00FF00;")
            self.info_text.setStyleSheet(
                "background-color: #000000; color: #00FF00; border: 1px solid #00FF00; border-radius: 5px; font-family: 'Courier New';"
            )
            if hasattr(self, "header_widget"):
                self.header_widget.setStyleSheet(
                    "background-color: #000000; border: 1px solid #00FF00; border-radius: 10px;"
                )
            self.btn_theme.setStyleSheet(
                "background-color: #000000; color: #00FF00; border: 1px solid #00FF00; border-radius: 4px; font-size: 10px;"
            )
            self.btn_theme.setText("📟 Matrix Mode")

            pbar = getattr(self, "progress_bar", None)
            if pbar:
                pbar.setStyleSheet(
                    "QProgressBar { text-align: center; border: 1px solid #00FF00; border-radius: 5px; background-color: #000; color: #00FF00; }"
                    "QProgressBar::chunk { background-color: #008800; }"
                )
                pbar.setFormat("SYSTEM MATRIX..." if lang == "de" else "MATRIX ACTIVE")

        # 4. SPEICHERN IN DATEI (Persistenz)
        try:
            # Nutzt die CONFIG_FILE Konstante aus dem globalen Scope
            config_path = globals().get("CONFIG_FILE", "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)

                cfg["theme_mode"] = new_mode

                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Fehler beim Speichern des Themes: {e}")

    import os
    import re
    import requests
    from datetime import datetime

    # --- Hilfsfunktionen innerhalb der Klasse ---

    def get_local_revision(self):
        """Liest die gespeicherte Revision aus der Datei oscam_rev.txt im Skript-Ordner."""
        import os

        # realpath löst auch Symlinks korrekt auf – konsistent mit create_patch
        script_dir = os.path.dirname(os.path.realpath(__file__))
        rev_file = os.path.join(script_dir, "oscam_rev.txt")

        if os.path.exists(rev_file):
            try:
                with open(rev_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # Sicherheitscheck: Inhalt muss eine Zahl sein
                    if content and content.isdigit():
                        return content
            except:
                pass

        # Fallback, falls Datei fehlt oder ungültig ist
        return "11943"

    def get_latest_remote_revision(self):
        """Holt die aktuellste r-Nummer direkt aus dem Streamboard-Log."""
        import requests, re

        # Der direkte Link zum OSCam-Repository Log
        url = "https://git.streamboard.tv"
        headers = {"User-Agent": "Mozilla/5.0"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Sucht nach 'r' gefolgt von 5 oder mehr Ziffern
                # Der erste Treffer im HTML ist bei Streamboard immer der aktuellste Commit
                matches = re.findall(r"r(\d{5,7})", response.text)
                if matches:
                    return matches[0]
        except Exception as e:
            print(f"Fehler: {e}")
        return None

    def save_local_revision(self, revision):
        """Speichert die neue Revision in die Datei, damit sie lokal bekannt ist."""
        rev_file = os.path.join(os.getcwd(), "oscam_rev.txt")
        try:
            with open(rev_file, "w") as f:
                f.write(str(revision))
        except Exception as e:
            print(f"Fehler beim Speichern der Revision: {e}")

    def start_oscam_update_check(self):
        """Wird aufgerufen, um den Vergleich zu starten."""
        # 1. Lokale Rev holen (aus Datei oder Fallback)
        self.current_rev = self.get_local_revision()

        # 2. Remote Rev von Streamboard holen
        remote_rev = self.get_latest_remote_revision()

        if remote_rev:
            try:
                # Prüfen ob die Online-Nummer größer als die lokale ist
                update_available = int(remote_rev) > int(self.current_rev)
                self.on_update_check_finished(update_available, remote_rev)
            except ValueError:
                self.on_update_check_finished(False, self.current_rev)
        else:
            # Fehlerfall: Nur lokalen Stand zeigen
            self.on_update_check_finished(False, self.current_rev)

    def on_update_check_finished(self, update_available, new_rev):
        """Aktualisiert das UI: Icons, Neon-Branding, Scanner-Effekt + neongrünes Revisions-Blinken."""
        from datetime import datetime
        import os
        from PyQt6.QtCore import QVariantAnimation, QTimer

        # --- ZENTRALE STYLING EINSTELLUNGEN ---
        F_SIZE = "24px"
        C_NEON_YELLOW = "#EAFF00"  # Erfolg / Aktuell
        C_NEON_PINK = "#FF00FF"  # Update gefunden
        C_NEON_GREEN = "#00FF00"  # Blink-Farbe für Revision
        C_WHITE = "#FFFFFF"
        F_EMOJI = (
            "'Noto Color Emoji', 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif"
        )
        # --------------------------------------

        txt = getattr(self, "TEXT", {})
        timestamp = datetime.now().strftime("%H:%M:%S")
        old_rev = getattr(self, "current_rev", "11943")
        self.last_remote_rev = new_rev

        def play_system_sound(sound_type="info"):
            safe_play = globals().get("safe_play")
            if safe_play:
                sounds = {
                    "update": "dialog-information.oga",
                    "uptodate": "complete.oga",
                    "beep": "bell.oga",
                }
                safe_play(sounds.get(sound_type, "complete.oga"))
            else:
                import subprocess, shutil

                player = next(
                    (p for p in ["paplay", "pw-play", "aplay"] if shutil.which(p)), None
                )
                if player:
                    s_path = (
                        "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"
                    )
                    subprocess.Popen(
                        [player, s_path],
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                    )

        if update_available:
            # --- FALL: UPDATE GEFUNDEN ---
            upd_title = txt.get("oscam_update_found", "UPDATE VERFÜGBAR")
            status_html = (
                f'<span style="font-family:{F_EMOJI}; font-size:{F_SIZE}; vertical-align: middle;">🚀</span> '
                f'<span style="font-size:{F_SIZE}; color:{C_NEON_PINK}; vertical-align: middle;"><b>[{timestamp}]</b></span> '
                f'<span style="font-size:{F_SIZE}; color:{C_WHITE}; vertical-align: middle;"><b> {upd_title}</b></span> '
                f'<span style="font-size:{F_SIZE}; color:#AAAAAA; vertical-align: middle;"> (r{old_rev} ➔ r{new_rev})</span>'
            )
            if hasattr(self, "status_label"):
                self.status_label.setText(status_html)
            play_system_sound("update")
        else:
            # --- FALL: AKTUELL (Mit Neongrün-Blinken für Revision) ---
            success_msg = txt.get("oscam_uptodate", "OSCam ist aktuell.")

            def set_status_ui(rev_color, opacity=1.0):
                html = (
                    f'<span style="font-family:{F_EMOJI}; font-size:{F_SIZE}; vertical-align: middle;">✅</span> '
                    f'<span style="font-size:{F_SIZE}; color:{C_NEON_YELLOW}; vertical-align: middle;"><b>[{timestamp}]</b></span> '
                    f'<span style="font-size:{F_SIZE}; color:{C_NEON_YELLOW}; vertical-align: middle;"><b> {success_msg}</b></span> '
                    f'<span style="font-size:{F_SIZE}; color:{rev_color}; opacity:{opacity}; vertical-align: middle;"><b> (r{old_rev})</b></span>'
                )
                if hasattr(self, "status_label"):
                    self.status_label.setText(html)

            # Initialer Zustand & Sounds
            set_status_ui(C_NEON_GREEN)
            if hasattr(self, "status_label"):
                self.status_label.show()
            play_system_sound("uptodate" if new_rev else "error")

            # Blink-Sequenz (3 Mal blinken)
            # Delays: 300(Aus), 600(An), 900(Aus), 1200(An), 1500(Aus), 1800(Finale)
            for i, delay in enumerate([300, 600, 900, 1200, 1500, 1800]):
                if i == 5:  # Letzter Schritt: Finales dezentes Gelb
                    QTimer.singleShot(
                        delay, lambda: set_status_ui(C_NEON_YELLOW, opacity=0.7)
                    )
                else:
                    color = "transparent" if i % 2 == 0 else C_NEON_GREEN
                    QTimer.singleShot(delay, lambda c=color: set_status_ui(c))

        # --- PROGRESSBAR FINALE ---
        pbar = getattr(self, "progress_bar", None)
        if pbar:
            pbar.setValue(100)
            if hasattr(self, "pbar_idle"):
                QTimer.singleShot(4000, self.pbar_idle)

            lang = getattr(self, "LANG", "de").lower()
            f_text = "Tool einsatzbereit" if lang == "de" else "Tool ready for use"
            pbar.setFormat(f_text)
            pbar.setTextVisible(True)

            base_style = (
                "QProgressBar { text-align: center; font-weight: 900; border: 2px solid #222; "
                "border-radius: 6px; background-color: #111; font-size: 15pt; color: black; }"
            )

            self._scanner_anim = QVariantAnimation(self)
            self._scanner_anim.setDuration(1000)
            self._scanner_anim.setStartValue(0.0)
            self._scanner_anim.setEndValue(1.0)
            self._scanner_anim.setLoopCount(3)

            def update_scanner(val):
                pos = val if val <= 0.5 else 1.0 - val
                pos *= 2
                p1, p2, p3 = max(0, pos - 0.3), pos, min(1, pos + 0.3)
                gradient = (
                    f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                    f"stop:0 #111, stop:{p1} {C_NEON_PINK}, stop:{p2} {C_NEON_YELLOW}, stop:{p3} #00FFFF, stop:1 #111);"
                )
                txt_color = "black" if 0.2 < val < 0.8 else "transparent"
                pbar.setStyleSheet(
                    base_style + f"QProgressBar {{ color: {txt_color}; }} "
                    f"QProgressBar::chunk {{ background-color: {gradient}; border-radius: 4px; }}"
                )

            self._scanner_anim.valueChanged.connect(update_scanner)
            self._scanner_anim.currentLoopChanged.connect(
                lambda: play_system_sound("beep")
            )

            def on_done():
                final_rainbow = (
                    "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                    "stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                    "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"
                )
                pbar.setStyleSheet(
                    base_style + "QProgressBar { color: black; } "
                    f"QProgressBar::chunk {{ background-color: {final_rainbow}; border-radius: 4px; }}"
                )

            self._scanner_anim.finished.connect(on_done)
            play_system_sound("beep")
            self._scanner_anim.start()

    def trigger_alert_animation(self, widget):
        """Lässt ein Widget dezent rot pulsieren."""
        effect = QGraphicsColorizeEffect(widget)
        widget.setGraphicsEffect(effect)

        self.pulse_anim = QPropertyAnimation(effect, b"color")
        self.pulse_anim.setDuration(1200)
        self.pulse_anim.setStartValue(QColor(Qt.GlobalColor.transparent))
        self.pulse_anim.setEndValue(QColor(255, 50, 50))  # Softes Rot
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.pulse_anim.setLoopCount(-1)  # Unendlich
        self.pulse_anim.start()

    def upload_progress_with_speed(self, current, total):
        """Aktualisiert Progressbar und zeigt Live-Speed im Log an."""
        import time

        # Initialisierung beim ersten Aufruf
        if not hasattr(self, "_upload_start_time") or current <= 0:
            self._upload_start_time = time.time()
            self._last_printed_second = 0

        # Progressbar füllen
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)

        # Geschwindigkeit berechnen (alle 0.5 Sekunden aktualisieren)
        elapsed = time.time() - self._upload_start_time
        if elapsed > 0.5:
            speed_kb = (current / 1024) / elapsed
            speed_text = (
                f"🚀 Upload: {speed_kb:.2f} KB/s ({current/1024:.1f} KB übertragen)"
            )

            # Schreibt die Info in das Log-Fenster (überschreibt die letzte Zeile nicht,
            # aber wir können eine Status-Zeile im GUI-Label nutzen oder im Log-Anhängen)
            if int(elapsed) > self._last_printed_second:
                self.append_info(self.info_text, speed_text, "info")
                self._last_printed_second = int(elapsed)

    def change_colors(self):
        """Aktualisiert das Farbschema, passt alle GUI-Buttons an und speichert via save_config."""
        global current_diff_colors, current_color_name

        # 1️⃣ Aktuelle Farbe ermitteln
        if hasattr(self, "color_box") and self.color_box.currentText():
            current_color_name = self.color_box.currentText()
        else:
            current_color_name = getattr(self, "cfg", {}).get("color", "Classics")

        # 2️⃣ Basis-Farben holen
        base_colors = DIFF_COLORS.get(
            current_color_name,
            DIFF_COLORS.get("Classics", {"bg": "#2F2F2F", "fg": "#FFFFFF"}),
        )
        bg = base_colors.get("bg", "#2F2F2F")
        fg = base_colors.get("fg", "#EAFF00")  # Dein Akzent (z.B. Neon-Gelb)

        # 3️⃣ Farben vorbereiten
        current_diff_colors = {
            **base_colors,
            "hover": base_colors.get(
                "hover",
                self.adjust_color(bg, 1.2) if hasattr(self, "adjust_color") else bg,
            ),
            "active": base_colors.get(
                "active",
                self.adjust_color(bg, 0.8) if hasattr(self, "adjust_color") else bg,
            ),
        }

        if "safe_play" in globals():
            safe_play("dialog-information.oga")

        # 4️⃣ FARBEN IM UI ANWENDEN
        button_style = f"""
            QPushButton {{
                color: {fg} !important;
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 6px;
                font-weight: 700;
                font-size: 13pt;
            }}
            QPushButton:hover {{
                background-color: #4d4d4d;
                border: 1px solid {fg};
                color: white !important;
            }}
        """
        self.setStyleSheet(self.styleSheet() + button_style)

        # --- NEU: STATS-CHECKBOX AN DAS SCHEMA ANPASSEN ---
        # --- STATS-CHECKBOX AN DAS SCHEMA ANPASSEN (Hintergrund & Akzent) ---
        if hasattr(self, "telemetry_cb") and self.telemetry_cb:
            # Wir nutzen hier 'bg' für den Kasten und 'fg' für den Text/Rahmen
            self.telemetry_cb.setStyleSheet(
                f"""
                QCheckBox {{
                    color: {fg};
                    background-color: {bg}; 
                    border: 1px solid {fg};
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-weight: 700;
                }}
                /* Vollflächiger Hover-Effekt wie bei deinen Buttons */
                QCheckBox:hover {{
                    background-color: {fg};
                    color: {bg} !important; /* Textfarbe wechselt auf Hintergrundfarbe für Kontrast */
                    border: 1px solid white;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 1px solid {fg};
                    border-radius: 3px;
                    background: transparent;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {fg};
                    border: 1px solid white;
                }}
                /* Indikator-Farbe invertieren wenn der Button gehovert wird */
                QCheckBox:hover::indicator {{
                    border: 1px solid {bg};
                    background-color: rgba(0, 0, 0, 0.1);
                }}
            """
            )

        # Zusätzliche UI-Elemente
        if hasattr(self, "repaint_ui_colors"):
            self.repaint_ui_colors()

        if hasattr(self, "header_container"):
            self.header_container.setStyleSheet(
                f"background-color: {bg}; border-radius: 8px; border: 1px solid #444;"
            )

        if hasattr(self, "header_label"):
            self.header_label.setStyleSheet(
                f"color: {fg}; font-weight: 700; font-size: 20px; background: transparent;"
            )

        # 5️⃣ ZENTRAL SPEICHERN
        if not getattr(self, "is_loading", False):
            config = getattr(self, "cfg", {})
            if config.get("color") != current_color_name:
                config["color"] = current_color_name
                if "save_config" in globals():
                    save_config(config, gui_instance=self, silent=True)

    def log_message(self, message):
        """Zentrale Funktion: Zeit in ROT, Inhalt in CYAN - sauber untereinander."""
        from datetime import datetime

        now = datetime.now().strftime("%H:%M:%S")

        # 1. Sicherstellen, dass wir eine neue Zeile haben
        self.info_text.append("")

        # 2. HTML-Zeile bauen (Zeit ROT, Nachricht CYAN/Inhalt)
        full_html = f"<span style='color:red;'>[{now}]</span> {message}"

        # 3. Cursor ans Ende und HTML einfügen
        self.info_text.moveCursor(QTextCursor.MoveOperation.End)
        self.info_text.insertHtml(full_html)

        # 4. Scrollen
        self.info_text.moveCursor(QTextCursor.MoveOperation.End)

    def scroll_to_bottom_smooth(self):
        """Scrollt das Info-Fenster sanft nach unten."""
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

        if not hasattr(self, "info_text") or not self.info_text:
            return

        scrollbar = self.info_text.verticalScrollBar()

        # Animation für die Eigenschaft 'value' der Scrollbar
        self.scroll_anim = QPropertyAnimation(scrollbar, b"value")
        self.scroll_anim.setDuration(300)  # Dauer in ms
        self.scroll_anim.setStartValue(scrollbar.value())
        self.scroll_anim.setEndValue(scrollbar.maximum())

        # Eine sanfte Kurve (beschleunigt und bremst ab)
        self.scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.scroll_anim.start()

    def show_info(self):
        """Zeigt das Info-Fenster mit spezifischen Farben für Status-Texte."""
        lang = str(getattr(self, "LANG", "de")).lower()
        t = TEXTS.get(lang, TEXTS.get("en", {}))

        info_dialog = QDialog(self)
        info_dialog.setWindowTitle(t.get("info_title", "About OSCam Emu Toolkit"))
        info_dialog.setFixedSize(450, 320)

        # Farben aus dem aktuellen Theme laden
        global current_diff_colors
        bg_color = current_diff_colors.get("bg", "#FFFFFF")
        text_color = current_diff_colors.get("text", "#000000")
        border_col = current_diff_colors.get("border", "#888888")

        info_dialog.setStyleSheet(f"background-color: {bg_color};")

        layout = QVBoxLayout(info_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon = self.style().standardIcon(
            QApplication.style().StandardPixmap.SP_MessageBoxInformation
        )
        icon_label.setPixmap(icon.pixmap(64, 64))

        title_vbox = QVBoxLayout()
        # TITEL in BLAU (Information)
        title_label = QLabel("OSCam Emu Patch Manager")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #0000FF;")  # Blau

        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setStyleSheet("color: #666666;")

        title_vbox.addWidget(title_label)
        title_vbox.addWidget(version_label)
        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Credits GroupBox
        credits_group = QGroupBox(t.get("credits_label", "Credits / Authors"))
        credits_group.setStyleSheet(
            f"QGroupBox {{ color: {text_color}; border: 1px solid {border_col}; margin-top: 10px; font-weight: bold; }}"
        )
        credits_layout = QFormLayout(credits_group)

        # AUTOR in GRÜN (Erfolg/Ersteller)
        author_val = QLabel("<b>speedy005</b>")
        author_val.setStyleSheet("color: #008000;")  # Grün

        # PATCH in BLAU
        emu_val = QLabel("OSCam-Emu Team")
        emu_val.setStyleSheet("color: #0000FF;")  # Blau

        # LIZENZ in ROT (Wichtige Einschränkung)
        lic_val = QLabel("MIT License")
        lic_val.setStyleSheet("color: #FF0000;")  # Rot

        credits_layout.addRow(QLabel("Main Author:"), author_val)
        credits_layout.addRow(QLabel("Emu Patch:"), emu_val)
        credits_layout.addRow(QLabel("License:"), lic_val)
        layout.addWidget(credits_group)

        # Copyright
        copy_label = QLabel(f"© 2026 speedy005 - All rights reserved.")
        copy_label.setFont(QFont("Arial", 8))
        copy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy_label.setStyleSheet(f"color: {text_color};")
        layout.addWidget(copy_label)

        # Schließen Button
        close_btn = QPushButton(t.get("close", "Close"))
        close_btn.setMinimumHeight(35)
        # Button Text in BLAU
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                border-radius: {self.BUTTON_RADIUS}px;
                background-color: {current_diff_colors.get('active', '#e0e0e0')};
                color: #0000FF; 
                font-weight: bold;
                border: 1px solid {border_col};
            }}
        """
        )
        close_btn.clicked.connect(info_dialog.accept)
        layout.addWidget(close_btn)

        info_dialog.exec()

    def get_t(self, key, default=None):
        """Zentrale Methode zur Textübersetzung."""
        lang = str(getattr(self, "LANG", "de")).lower()
        # Dictionary für die aktuelle Sprache holen, Fallback auf Englisch
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))

        if key in lang_dict:
            return lang_dict[key]

        # Falls Key fehlt, technischen Namen schön machen
        if default:
            return default

        return str(key).replace("_", " ").title()

    def get_gui_settings(self):
        """Sammelt alle aktuellen Einstellungen aus der UI für die Config."""
        return {
            # Falls du ein Eingabefeld/Spinbox für Commits hast:
            "commit_count": (
                self.commit_spin.value()
                if hasattr(self, "commit_spin")
                else getattr(self, "commit_count", 5)
            ),
            # Falls du eine Color-Box (QComboBox) hast:
            "color": (
                self.color_box.currentText()
                if hasattr(self, "color_box")
                else getattr(self, "current_color", "")
            ),
            # Sprache (Wichtig: "language" muss klein geschrieben sein wie in load_config!)
            "language": str(getattr(self, "LANG", "DE")).upper(),
            # Pfad
            "s3_patch_path": getattr(self, "OLD_PATCH_DIR", OLD_PATCH_DIR),
        }

    def show_update_dialog(self, latest_version, current_version):
        """Öffnet das Pop-up Fenster für das verfügbare Update."""
        from PyQt6.QtWidgets import QMessageBox

        txt = getattr(self, "TEXT", {})
        lang = getattr(self, "LANG", "de").lower()

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(txt.get("update_title", "Update"))

        # Text-Inhalt
        msg_text = (
            f"{txt.get('update_msg', 'Update verfügbar')}\n\n"
            f"{txt.get('new_version_label', 'Neu')}: v{latest_version}\n"
            f"{txt.get('old_version_label', 'Installiert')}: v{current_version}"
        )
        msg_box.setText(msg_text)

        # Buttons übersetzen
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        btn_yes = msg_box.button(QMessageBox.StandardButton.Yes)
        if btn_yes:
            btn_yes.setText(txt.get("yes", "Ja"))
        btn_no = msg_box.button(QMessageBox.StandardButton.No)
        if btn_no:
            btn_no.setText(txt.get("no", "Nein"))

        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            if hasattr(self, "plugin_update_action"):
                self.plugin_update_action(latest_version=latest_version)

    def change_emu_repo(self):
        """Repository-Auswahl mit Regenbogen-Progress, Sound und DE/EN Support."""
        from PyQt6.QtWidgets import QInputDialog, QApplication
        from PyQt6.QtCore import QTimer

        # 1. SETUP
        REPO_1 = "https://github.com/oscam-mirror/oscam-emu.git"
        REPO_2 = "https://github.com/speedy005/Oscam-emu.git"
        REPO_OPTIONS = [REPO_1, REPO_2]

        current_repo = getattr(self, "EMUREPO", REPO_1)
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)

        # TEXTE
        T_TITLE   = "Repository Auswahl" if is_de else "Repository Selection"
        T_LABEL   = "Wähle die gewünschte Repo-URL:" if is_de else "Select Repo-URL:"
        T_SAVING  = "Speichere Repo..." if is_de else "Saving Repo..."
        T_DONE    = "Repo geändert!" if is_de else "Repo changed!"
        T_CANCEL  = "Abgebrochen" if is_de else "Cancelled"

        # RESET-FUNKTION (Standard Orange/Gold)
        def restore_style():
            if pbar:
                pbar.setValue(0)
                pbar.setFormat("%p%")
                pbar.setStyleSheet("""
                    QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; 
                    color: white; text-align: center; font-weight: bold; }
                    QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }
                """)

        if "safe_play" in globals(): safe_play("dialog-information.oga")

        # 2. REGENBOGEN VORBEREITEN
        if pbar:
            rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                       "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                       "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    text-align: center; font-weight: 900; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """)
            pbar.setFormat(f"⚙️ {T_SAVING} %p%")
            pbar.setValue(20)
            pbar.show()
            QApplication.processEvents()

        # 3. DIALOG
        dialog = QInputDialog(self)
        dialog.setWindowTitle(T_TITLE)
        dialog.setLabelText(T_LABEL)
        dialog.setComboBoxItems(REPO_OPTIONS)
        dialog.setComboBoxEditable(False)
        dialog.setTextValue(current_repo)
        dialog.setOkButtonText("OK")
        dialog.setCancelButtonText("Abbrechen" if is_de else "Cancel")

        if dialog.exec():
            new_url = dialog.textValue()
            if new_url:
                if pbar: pbar.setValue(60)
                self.EMUREPO = new_url
                globals()["EMUREPO"] = new_url
                
                if hasattr(self, "cfg"):
                    self.cfg["EMUREPO"] = self.EMUREPO
                    try:
                        if "save_config" in globals():
                            globals()["save_config"](self.cfg, gui_instance=self)
                        if hasattr(self, "update_language"): self.update_language()

                        if "safe_play" in globals(): safe_play("complete.oga")
                        if pbar:
                            pbar.setValue(100)
                            pbar.setFormat(f"✅ {T_DONE}")
                            QApplication.processEvents()
                    except Exception as e:
                        if "safe_play" in globals(): safe_play("dialog-error.oga")
                        if pbar: pbar.setStyleSheet("QProgressBar { color: red; font-weight: 700; }")
                
                QTimer.singleShot(3000, restore_style)
        else:
            # --- 4. SPEZIELLER ABBRUCH-ABLAUF ---
            if "safe_play" in globals(): safe_play("dialog-warning.oga") 
            
            if pbar:
                # Erst auf 100% füllen
                pbar.setValue(100)
                pbar.setFormat("100%")
                pbar.repaint()
                QApplication.processEvents()
                
                # Nach 400ms: Ausblenden (Reset auf 0) und rote Meldung zeigen
                def show_cancel_msg():
                    pbar.setValue(0)
                    pbar.setFormat(f"❌ {T_CANCEL}")
                    # Kurzes rotes Highlight für den Abbruch
                    pbar.setStyleSheet(f"QProgressBar {{ text-align: center; color: red; font-weight: 900; font-size: 15pt; border: 2px solid red; background: #111; }}")
                    pbar.repaint()
                    # Nach weiteren 2 Sekunden endgültiger Reset zu Orange
                    QTimer.singleShot(2000, restore_style)

                QTimer.singleShot(400, show_cancel_msg)



    def change_modifier_name(self):
        """Öffnet Autor-Dialog mit Regenbogen-Progress, Sound und DE/EN Support."""
        from PyQt6.QtWidgets import QInputDialog, QLineEdit, QApplication
        from PyQt6.QtCore import QTimer

        # 1. SETUP & SPRACHE
        current_author = getattr(self, "patch_modifier", "speedy005")
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)

        # Lokalisierte Texte
        T_TITLE   = "Patch Autor" if is_de else "Patch Author"
        T_LABEL   = "Name des Autors:" if is_de else "Author Name:"
        T_SAVING  = "Speichere Autor..." if is_de else "Saving Author..."
        T_DONE    = "Autor geändert!" if is_de else "Author changed!"
        T_CANCEL  = "Abgebrochen" if is_de else "Cancelled"

        # RESET-FUNKTION (Zurück zu Orange/Gold)
        def restore_style():
            if pbar:
                pbar.setValue(0)
                pbar.setFormat("%p%")
                pbar.setStyleSheet("""
                    QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; 
                    color: white; text-align: center; font-weight: bold; }
                    QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }
                """)

        # --- SOUND BEIM ÖFFNEN ---
        if "safe_play" in globals():
            safe_play("dialog-information.oga")

        # 2. REGENBOGEN-PROGRESS STARTEN
        if pbar:
            rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                       "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                       "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    text-align: center; font-weight: 900; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """)
            pbar.setFormat(f"👤 {T_SAVING} %p%")
            pbar.setValue(20)
            pbar.show()
            QApplication.processEvents()

        # 3. DIALOG KONFIGURIEREN
        dialog = QInputDialog(self)
        dialog.setWindowTitle(T_TITLE)
        dialog.setLabelText(T_LABEL)
        dialog.setTextValue(current_author)
        dialog.setOkButtonText("OK")
        dialog.setCancelButtonText("Abbrechen" if is_de else "Cancel")

        if dialog.exec():
            new_name = dialog.textValue().strip()
            if new_name:
                if pbar: pbar.setValue(60)
                self.patch_modifier = new_name
                
                if hasattr(self, "cfg"):
                    self.cfg["patch_modifier"] = self.patch_modifier
                    try:
                        if "save_config" in globals():
                            globals()["save_config"](self.cfg, gui_instance=self)
                        
                        if hasattr(self, "update_language"):
                            self.update_language()

                        # --- ERFOLG ---
                        if "safe_play" in globals(): safe_play("complete.oga")
                        if pbar:
                            pbar.setValue(100)
                            pbar.setFormat(f"✅ {T_DONE}")
                            QApplication.processEvents()
                    
                    except Exception as e:
                        if "safe_play" in globals(): safe_play("dialog-error.oga")
                        if pbar: pbar.setStyleSheet("QProgressBar { color: red; font-weight: 900; }")
                
                # Auto-Reset nach Erfolg
                QTimer.singleShot(3000, restore_style)
        else:
            # --- 4. SPEZIELLER ABBRUCH-ABLAUF ---
            if "safe_play" in globals(): 
                safe_play("dialog-warning.oga") 
            
            if pbar:
                # Erst auf 100% füllen (Regenbogen)
                pbar.setValue(100)
                pbar.setFormat("100%")
                pbar.repaint()
                QApplication.processEvents()
                
                # Nach 400ms: Auf 0 setzen und rote Meldung zeigen
                def show_cancel_msg():
                    pbar.setValue(0)
                    pbar.setFormat(f"❌ {T_CANCEL}")
                    # Rotes Highlight für den Fehler/Abbruch
                    pbar.setStyleSheet(f"""
                        QProgressBar {{ 
                            text-align: center; color: red; font-weight: 900; 
                            font-size: 15pt; border: 2px solid red; background: #111; 
                        }}
                    """)
                    pbar.repaint()
                    QApplication.processEvents()
                    # Nach weiteren 2 Sekunden endgültiger Reset zu Orange/Gold
                    QTimer.singleShot(2000, restore_style)

                QTimer.singleShot(400, show_cancel_msg)

    def collect_and_save(self):
        """Speichert leise und aktualisiert die Farben sofort."""
        try:
            theme_name = self.color_box.currentText()

            # Globale Farbe aktualisieren, damit repaint_ui_colors sie findet
            global current_diff_colors
            if theme_name in DIFF_COLORS:
                current_diff_colors = DIFF_COLORS[theme_name]

            new_cfg = {
                "theme": theme_name,
                "commit_count": int(self.commit_spin.value()),
                "language": self.language_box.currentText(),
                "work_dir": "/opt/s3_neu/support/patches",
                "s3_patch_path": "/opt/s3_neu/support/patches",
                "tools_ok": True,
            }

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_cfg, f, indent=4, ensure_ascii=False)

            # UI sofort neu färben
            self.repaint_ui_colors()

            # Log nur in der GUI (kein print!)
            self.info_text.append(f"💾 Konfiguration gespeichert: {theme_name}")

        except Exception as e:
            self.info_text.append(f"❌ Fehler beim Speichern: {e}")

    def manual_tool_check(self):
        """System-Check mit Regenbogen-Progress, Sound und DE/EN Support."""
        import time, shutil, os, platform
        from datetime import datetime
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        # 1. Doppelklick-Sperre & Setup
        now_ts = time.time()
        if hasattr(self, "_last_check_run") and (now_ts - self._last_check_run) < 0.5:
            return
        self._last_check_run = now_ts

        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Lokalisierte Texte
        T_START = "System-Check..." if is_de else "System Check..."
        T_DONE  = "Check bereit!" if is_de else "Check ready!"
        T_ERR   = "Fehler!" if is_de else "Error!"

        # --- SOUND BEIM ÖFFNEN (Start) ---
        if "safe_play" in globals():
            safe_play("service-login.oga")

        # 2. REGENBOGEN-PROGRESS AKTIVIEREN
        if pbar:
            rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                       "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                       "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    text-align: center; font-weight: 700; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """)
            pbar.setFormat(f"🛠️ {T_START} %p%")
            pbar.setValue(20)
            pbar.show()
            QApplication.processEvents()

        try:
            self.info_text.clear()
            msg_init = f"Starte System-Check... [{timestamp}]" if is_de else f"Starting system check... [{timestamp}]"
            self.append_info(msg_init, "info")

            if pbar: pbar.setValue(50)

            # 3. Tools prüfen
            required_tools = ["git", "python3"]
            if platform.system() != "Windows":
                required_tools.extend(["patch", "zip"])

            missing = [t for t in required_tools if shutil.which(t) is None]

            if not missing:
                self.append_info("✅ Alle benötigten System-Tools sind bereit." if is_de else "✅ All required tools are ready.", "success")
                
                # --- SOUND BEI ERFOLG ---
                if "safe_play" in globals(): safe_play("complete.oga")
                
                if pbar:
                    pbar.setValue(100)
                    pbar.setFormat(f"✅ {T_DONE} 100%")

                # Folgeschritte ausführen
                if hasattr(self, "check_for_plugin_update"): self.check_for_plugin_update()
                if hasattr(self, "show_start_config"): self.show_start_config()
            else:
                # --- SOUND BEI WARNUNG ---
                if "safe_play" in globals(): safe_play("dialog-error.oga")
                missing_str = ", ".join(missing)
                self.append_info(f"⚠️ Fehlende Tools: {missing_str}" if is_de else f"⚠️ Missing tools: {missing_str}", "warning")
                if pbar: pbar.setValue(0)

        except Exception as e:
            if "safe_play" in globals(): safe_play("dialog-error.oga")
            self.append_info(f"❌ Check-Fehler: {str(e)}", "error")
            if pbar: pbar.setStyleSheet("QProgressBar { color: red; font-weight: 700; }")

        # 4. AUTO-RESET (3 Sekunden) -> Zurück zu Orange/Gold Style
        if pbar:
            def restore_style():
                pbar.setValue(0)
                pbar.setFormat("%p%")
                pbar.setStyleSheet("""
                    QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; 
                    color: white; text-align: center; font-weight: bold; }
                    QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }
                """)
            QTimer.singleShot(3000, restore_style)

    def show_start_config(self):
        """Entfernt alle Textanzeigen und setzt nur noch den ProgressBar-Abschluss."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        # --- 1. PROGRESSBAR ABSCHLUSS-TEXT ---
        pbar = getattr(self, "progress_bar", None)
        if pbar:
            lang = getattr(self, "LANG", "de").lower()
            is_de = lang == "de"
            ready_txt = "✅ System bereit" if is_de else "✅ System ready"

            pbar.setValue(100)
            pbar.setFormat(f"{ready_txt}")

            # CSS für gute Lesbarkeit auf dem Regenbogen-Balken
            pbar.setStyleSheet(
                pbar.styleSheet() + " QProgressBar { color: black; font-weight: bold; }"
            )

        QApplication.processEvents()

        # --- 2. SOUND & TIMER ---
        if "safe_play" in globals():
            safe_play("complete.oga")

        # Nach 3 Sek. wird der Balken durch pbar_idle geleert/versteckt
        if hasattr(self, "pbar_idle"):
            QTimer.singleShot(500, self.pbar_idle)

    def resizeEvent(self, event):
        """
        Zentrale Steuerung für die UI-Skalierung bei Auflösungsänderung.
        Erweitert: Automatische Anpassung des Sprachwechsel-Overlays.
        """
        super().resizeEvent(event)

        # 1. Basis-Schriftgröße berechnen (Faktor 90 statt 75 für kompaktere Schriften)
        dynamic_size = max(10, int(self.width() / 90))

        # Schriftarten erstellen
        button_font = QFont("Arial", dynamic_size, QFont.Weight.Bold)
        label_font = QFont("Arial", max(9, dynamic_size - 1))

        # UHR-FIX: Faktor auf 1.1 reduziert (statt 1.5) und Basis auf 12 (statt 14)
        clock_font = QFont("Arial", max(12, int(dynamic_size * 1.1)), QFont.Weight.Bold)

        # 2. Alle Buttons in 'all_buttons' aktualisieren
        for btn in self.all_buttons:
            btn.setFont(button_font)
            if not btn.icon().isNull():
                # Icons etwas kleiner (2.0 statt 2.5)
                icon_dim = int(dynamic_size * 2.0)
                btn.setIconSize(QSize(icon_dim, icon_dim))

        # 3. Buttons im Dictionary 'buttons' (Aktions-Grid)
        for key in self.buttons:
            self.buttons[key].setFont(button_font)

        # 4. Spezifische GUI-Elemente anpassen
        if hasattr(self, "digital_clock"):
            self.digital_clock.setFont(clock_font)

        if hasattr(self, "lang_label"):
            self.lang_label.setFont(label_font)
            self.color_label.setFont(label_font)
            self.commit_label.setFont(label_font)

        # 5. Logo-Skalierung (Proportional zur Fensterhöhe begrenzen)
        if hasattr(self, "original_pixmap") and self.original_pixmap:
            # Breite auf 40% reduzieren, damit Header schmal bleibt
            logo_width = min(500, int(self.width() * 0.4))
            logo_height = int(logo_width / 6.3)
            self.update_logo(width=logo_width, height=logo_height)

        # 6. Info-Text-Skalierung (Courier braucht oft etwas mehr Platz)
        if hasattr(self, "info_text"):
            text_font = QFont("Courier", max(10, dynamic_size))
            self.info_text.setFont(text_font)

        # --- 7. NEU: OVERLAY SKALIERUNG ---
        # Stellt sicher, dass der Lade-Schleier immer das gesamte Fenster füllt
        if hasattr(self, "loading_overlay") and self.loading_overlay:
            # Setzt die Geometrie des Overlays exakt auf die neue Fenstergröße
            self.loading_overlay.setGeometry(self.rect())

    def open_terminal(self, **kwargs):
        """Öffnet Terminal (S3 oder leer) mit Regenbogen-Progress, Sound und DE/EN Support."""
        import subprocess, platform, shutil, os
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        # 1. SETUP & SPRACHE
        s3_path = kwargs.get("s3_path")
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)

        # Lokalisierte Texte
        if s3_path:
            T_LOAD = "S3 Menü wird geladen..." if is_de else "Loading S3 Menu..."
        else:
            T_LOAD = "Terminal wird geöffnet..." if is_de else "Opening Terminal..."
        T_DONE = "Terminal bereit!" if is_de else "Terminal ready!"

        # --- SOUND BEIM ÖFFNEN (Start) ---
        if "safe_play" in globals():
            safe_play("service-login.oga")

        # 2. REGENBOGEN-PROGRESS AKTIVIEREN (Schwarze Schrift, 15pt)
        if pbar:
            rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                       "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                       "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    text-align: center; font-weight: 700; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """)
            pbar.setFormat(f"💻 {T_LOAD} %p%")
            pbar.setValue(20)
            pbar.show()
            QApplication.processEvents()

        try:
            if pbar: pbar.setValue(50)

            # 3. TERMINAL LOGIK
            system = platform.system()
            terminal_opened = False
            exec_cmd = f"cd {os.path.dirname(s3_path)} && ./s3 menu" if s3_path else ""

            if system == "Windows":
                cmd_args = ["cmd", "/K", exec_cmd] if exec_cmd else ["cmd"]
                subprocess.Popen(cmd_args, creationflags=subprocess.CREATE_NEW_CONSOLE)
                terminal_opened = True

            elif system == "Linux":
                terminals = ["gnome-terminal", "konsole", "xfce4-terminal", "xterm", "lxterminal"]
                for term in terminals:
                    if shutil.which(term):
                        if exec_cmd:
                            # Ubuntu/Gnome Spezial-Handling
                            if term == "gnome-terminal":
                                subprocess.Popen([term, "--", "bash", "-c", f"{exec_cmd}; exec bash"])
                            else:
                                subprocess.Popen([term, "-e", f"bash -c '{exec_cmd}; exec bash'"])
                        else:
                            subprocess.Popen([term])
                        terminal_opened = True
                        break

            if not terminal_opened:
                raise FileNotFoundError("No terminal emulator found!")

            # --- SOUND & PROGRESS BEI ERFOLG ---
            if "safe_play" in globals(): safe_play("complete.oga")
            if pbar:
                pbar.setValue(100)
                pbar.setFormat(f"✅ {T_DONE} 100%")

        except Exception as e:
            if "safe_play" in globals(): safe_play("dialog-error.oga")
            if pbar:
                pbar.setStyleSheet("QProgressBar { color: red; font-weight: 700; }")
                pbar.setFormat("❌ Error!")
            if hasattr(self, "append_info"):
                self.append_info(f"❌ Fehler: {str(e)}", "error")

        # 4. AUTO-RESET (3 Sekunden) -> Zurück zu Orange/Gold Style
        if pbar:
            def restore_style():
                pbar.setValue(0)
                pbar.setFormat("%p%")
                pbar.setStyleSheet("""
                    QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; 
                    color: white; text-align: center; font-weight: bold; }
                    QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }
                """)
            QTimer.singleShot(3000, restore_style)


    def select_patch_path(self):
        """Öffnet Verzeichnis-Dialog mit Regenbogen-Progress, Sound und DE/EN Support."""
        import os, json
        from PyQt6.QtWidgets import QFileDialog, QApplication
        from PyQt6.QtCore import QTimer

        # 1. SETUP & SPRACHE
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)

        # Lokalisierte Texte
        T_TITLE = "Patch-Ordner auswählen" if is_de else "Select Patch Folder"
        T_LOAD  = "Ordner wird gewählt..." if is_de else "Selecting folder..."
        T_DONE  = "Pfad gespeichert!" if is_de else "Path saved!"
        T_ERR   = "Fehler!" if is_de else "Error!"

        # --- SOUND BEIM ÖFFNEN (Start) ---
        if "safe_play" in globals():
            safe_play("service-login.oga")

        # 2. REGENBOGEN-PROGRESS AKTIVIEREN (Schwarze Schrift, 15pt)
        if pbar:
            rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                       "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                       "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    text-align: center; font-weight: 700; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """)
            pbar.setFormat(f"📁 {T_LOAD} %p%")
            pbar.setValue(20)
            pbar.show()
            QApplication.processEvents()

        # 3. DIALOG ÖFFNEN
        start_path = getattr(self, "OLD_PATCH_DIR", os.getcwd())
        directory = QFileDialog.getExistingDirectory(self, T_TITLE, start_path)

        if directory:
            directory = os.path.normpath(directory)
            if pbar: pbar.setValue(60)

            # Interne Variablen updaten
            self.cfg["s3_patch_path"] = directory
            self.OLD_PATCH_DIR = directory
            self.OLD_PATCH_FILE = os.path.join(directory, "oscam-emu.patch")
            self.ALT_PATCH_FILE = os.path.join(directory, "oscam-emu.altpatch")

            # In config.json speichern (Nutzt deine globale CONFIG_FILE)
            try:
                conf_path = globals().get("CONFIG_FILE", "config.json")
                with open(conf_path, "w", encoding="utf-8") as f:
                    json.dump(self.cfg, f, indent=4)

                # --- SOUND & PROGRESS BEI ERFOLG ---
                if "safe_play" in globals(): safe_play("complete.oga")
                
                if pbar:
                    pbar.setValue(100)
                    pbar.setFormat(f"✅ {T_DONE} 100%")

                if hasattr(self, "append_info"):
                    self.append_info(self.info_text, f"✅ Speicherort geändert: <b>{directory}</b>" if is_de else f"✅ Path changed: <b>{directory}</b>", "success")
            
            except Exception as e:
                if "safe_play" in globals(): safe_play("dialog-error.oga")
                if pbar: pbar.setStyleSheet("QProgressBar { color: red; font-weight: 700; }")
                if hasattr(self, "append_info"):
                    self.append_info(self.info_text, f"❌ {T_ERR}: {e}", "error")
        else:
            # Abgebrochen
            if "safe_play" in globals(): safe_play("dialog-error.oga")
            if pbar: pbar.setValue(0)

        # 4. AUTO-RESET (3 Sekunden) -> Zurück zu Orange/Gold Style
        if pbar:
            def restore_style():
                pbar.setValue(0)
                pbar.setFormat("%p%")
                pbar.setStyleSheet("""
                    QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; 
                    color: white; text-align: center; font-weight: bold; }
                    QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }
                """)
            QTimer.singleShot(3000, restore_style)

    def plugin_update_action(self, latest_version=None, progress_callback=None):
        """Installiert Update: Prüft Schreibrechte, macht Backup und erzwingt Disk-Sync."""
        import requests, os, shutil, sys, stat
        from PyQt6.QtWidgets import QMessageBox, QApplication
        from PyQt6.QtCore import QTimer
        from datetime import datetime

        # 1. SETUP & ECHTE PFADE ERMITTELN
        current_lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = current_lang == "de"
        
        # sys.argv[0] ist unter Linux der sicherste Weg zum echten Skript-Pfad
        current_file = os.path.abspath(sys.argv[0])
        tool_dir = os.path.dirname(current_file)
        
        backup_dir = os.path.join(tool_dir, "backup")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        v_str = str(globals().get("APP_VERSION", "old")).replace(".", "_")
        backup_file = os.path.join(backup_dir, f"backup_v{v_str}_{timestamp}.py")
        
        pbar = getattr(self, "progress_bar", None)

        # --- BERECHTIGUNGS-CHECK (Der wichtigste Teil!) ---
        if not os.access(tool_dir, os.W_OK) or (os.path.exists(current_file) and not os.access(current_file, os.W_OK)):
            error_msg = (f"❌ KEINE SCHREIBRECHTE!\n\nDas Tool darf in {tool_dir} nichts ändern.\n"
                         "Bitte starte das Tool mit 'sudo' oder ändere die Rechte:\n"
                         f"sudo chmod -R 777 {tool_dir}") if is_de else \
                        (f"❌ NO WRITE PERMISSIONS!\n\nCannot write to {tool_dir}.\n"
                         "Please start with 'sudo' or fix permissions.")
            QMessageBox.critical(self, "Permission Error", error_msg)
            return

        if "safe_play" in globals(): safe_play("service-login.oga")

        # 2. REGENBOGEN-PROGRESS STARTEN
        if pbar:
            rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                       "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                       "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
            pbar.setStyleSheet(f"QProgressBar {{ text-align: center; font-weight: 900; color: black; font-size: 15pt; background: #111; border: 2px solid #222; }} QProgressBar::chunk {{ background: {rainbow}; }}")
            pbar.setFormat("🚀 Update: Backup..." if is_de else "🚀 Update: Backup...")
            pbar.setValue(10)
            pbar.show()
            pbar.raise_()
            QApplication.processEvents()

        try:
            # --- Schritt 1: Backup ---
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
            shutil.copy2(current_file, backup_file)
            if pbar: pbar.setValue(30); QApplication.processEvents()

            # --- Schritt 2: Download (RAW URL FIX) ---
            # WICHTIG: Hier 'master' statt 'main' nutzen!
            download_url = ("https://raw.githubusercontent.com")

            # Diese Zeile MUSS vor resp = requests.get stehen:
            headers = {"Cache-Control": "no-cache", "User-Agent": "Mozilla/5.0"} 

            resp = requests.get(download_url, headers=headers, timeout=30)
        
            try:
                resp = requests.get(download_url, headers=headers, timeout=30)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Download fehlgeschlagen: {e}")

            # HTML-Schutz (Falls GitHub eine 404-Seite sendet)
            if "<!DOCTYPE html>" in resp.text or "<html>" in resp.text:
                raise ValueError("Fehler: URL ungültig (GitHub liefert HTML statt Code).")
            
            # Validierung: Ist die Datei groß genug?
            if len(resp.text) < 2000: # Etwas niedrigerer Schwellenwert als Sicherheit
                raise ValueError("Download korrupt: Datei zu klein.")


            # --- Schritt 3: Datei ersetzen (Atomic Write) ---
            temp_file = current_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(resp.text)
                f.flush()
                os.fsync(f.fileno())

            # Alte Datei löschen, neue umbenennen (umgeht File-Locks)
            if os.path.exists(current_file):
                os.remove(current_file)
            os.rename(temp_file, current_file)
            
            # Ausführbar machen für Linux
            os.chmod(current_file, os.stat(current_file).st_mode | stat.S_IEXEC)

            # --- Schritt 4: Erfolg & Neustart ---
            if pbar:
                pbar.setValue(100)
                pbar.setFormat("✅ Fertig!" if is_de else "✅ Done!")
                QApplication.processEvents()

            if "safe_play" in globals(): safe_play("complete.oga")
            
            msg = "Update erfolgreich! Jetzt neu starten?" if is_de else "Update successful! Restart now?"
            if QMessageBox.question(self, "Restart", msg) == QMessageBox.StandardButton.Yes:
                os.execl(sys.executable, sys.executable, *sys.argv)

        except Exception as e:
            if "safe_play" in globals(): safe_play("dialog-error.oga")
            QMessageBox.critical(self, "Update Error", f"Fehler: {str(e)}")
            if pbar:
                pbar.setStyleSheet("QProgressBar { color: red; font-weight: 900; }")
                pbar.setFormat("❌ Fehler!")

    def ask_for_update(self, latest_version):
        """Fragt nach Update und startet Installation entkoppelt für flüssige GUI."""
        lang = getattr(self, "LANG", "de").lower()[:2]
        lang_texts = globals().get("TEXTS", {}).get(lang, globals().get("TEXTS", {}).get("en", {}))

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(lang_texts.get("update_available_title", "Update"))
        
        message = lang_texts.get("update_available_msg", "Update {latest} verfügbar?").format(latest=latest_version)
        msg_box.setText(message)

        yes_btn = msg_box.addButton(lang_texts.get("yes", "Ja"), QMessageBox.ButtonRole.YesRole)
        no_btn = msg_box.addButton(lang_texts.get("no", "Nein"), QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(yes_btn)

        msg_box.exec()

        if msg_box.clickedButton() == yes_btn:
            # FIX: Erst Fenster weg, dann UI aktualisieren, dann mit Timer die Action rufen
            msg_box.close()
            QApplication.processEvents() 
            
            if hasattr(self, "plugin_update_action"):
                # 200ms Verzögerung entkoppelt den schweren Download-Prozess vom Dialog-Thread
                QTimer.singleShot(200, lambda: self.plugin_update_action(latest_version))



    # ======= HIER EINSETZEN =======
    def create_action_button(self, parent, text, color, callback, all_buttons_list, 
                             fg="white", factor_hover=1.15, factor_pressed=0.85, 
                             min_height=42, radius=8, icon_name=None):
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize, Qt
        from PyQt6.QtWidgets import QStyle, QSizePolicy, QPushButton

        # Text-Formatierung: Bei mehr als 12 Zeichen Umbruch für Icons
        display_text = text.replace(" ", "\n") if len(text) > 12 else text
        btn = QPushButton(display_text, parent)

        # --- ICON LOGIK (WINDOWS & LINUX SAFE) ---
        if icon_name:
            icon = QIcon()
            if str(icon_name).startswith("SP_"):
                p_enum = getattr(QStyle.StandardPixmap, icon_name, None)
                if p_enum: icon = self.style().standardIcon(p_enum)
            elif os.path.exists(str(icon_name)):
                icon = QIcon(icon_name)
            
            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(22, 22))

        # Farben für Effekte berechnen
        hover_color = self.adjust_color(color, factor_hover) if hasattr(self, "adjust_color") else color
        pressed_color = self.adjust_color(color, factor_pressed) if hasattr(self, "adjust_color") else color

        # --- STYLESHEET MIT GLOW-EFFEKT ---
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: {fg}; border-radius: {radius}px;
                border: 1px solid rgba(255,255,255,0.1); padding: 5px;
                font-weight: bold; font-size: 12px; min-height: {min_height}px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid white;
                color: #FFFFFF;
                /* Glow-Effekt Simulation durch Border */
            }} 
            QPushButton:pressed {{
                background-color: {pressed_color};
                padding-top: 7px; padding-left: 7px; /* Klick-Animation */
            }} 
        """)

        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # --- DER AUTOMATISCHE REGENBOGEN-TRIGGER ---
        def enhanced_callback():
            # 1. Regenbogen-Progress sofort starten
            pbar = getattr(self, "progress_bar", None)
            if pbar:
                rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                           "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                           "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
                pbar.setStyleSheet(f"QProgressBar {{ text-align: center; font-weight: 700; border: 2px solid #222; "
                                   f"border-radius: 6px; background: #111; color: black; font-size: 15pt; }} "
                                   f"QProgressBar::chunk {{ background: {rainbow}; }}")
                pbar.setValue(15)
                pbar.show()
            
            # 2. Original-Funktion ausführen
            if callback: callback()

        if callback:
            btn.clicked.connect(enhanced_callback)

        all_buttons_list.append(btn)
        return btn

    def generate_buttons(self, parent, button_definitions, all_buttons_list, info_widget=None):
        """Erzeugt Buttons basierend auf Dictionary-Listen (DE/EN tauglich)."""
        buttons = {}
        def_height = getattr(self, "BUTTON_HEIGHT", 42)
        def_radius = getattr(self, "BUTTON_RADIUS", 8)

        for bd in button_definitions:
            # Falls Name "work", "temp" oder "emu" -> Nutze open_custom_folder
            key = bd.get("key", "unknown")
            callback = bd.get("callback", lambda: None)
            
            # Icons übersetzen (SP_ Pfade)
            icon = bd.get("icon")
            if not icon and "open" in key: icon = "SP_DirIcon"

            btn = self.create_action_button(
                parent=parent,
                text=bd.get("text", "Button"),
                color=bd.get("color", "#444444"),
                callback=callback,
                all_buttons_list=all_buttons_list,
                fg=bd.get("fg", "white"),
                icon_name=icon,
                min_height=bd.get("min_height", def_height),
                radius=bd.get("radius", def_radius),
            )
            buttons[key] = btn
        return buttons

    def update_logo(self, width=None, height=None):
        """
        Skaliert das Logo auf die angegebene Breite und Höhe.
        Wenn width oder height None ist, werden Standardwerte verwendet.
        """
        if not hasattr(self, "original_pixmap") or self.original_pixmap is None:
            return

        # Nutze die übergebenen Werte direkt, sonst Standard
        if width is None:
            width = self.TITLE_HEIGHT * 3
        if height is None:
            height = self.TITLE_HEIGHT

        # Pixmap skalieren
        scaled_pixmap = self.original_pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.IgnoreAspectRatio,  # exakt width x height
            Qt.TransformationMode.SmoothTransformation,
        )

        self.logo_label.setPixmap(scaled_pixmap)
        self.logo_label.setFixedSize(width, height)

    # 🔹 HIER EINSETZEN 🔹
    def adjust_color(self, hex_color, factor):
        """
        Passt die Helligkeit einer Farbe an.
        factor > 1.0 = heller (Hover), factor < 1.0 = dunkler (Pressed).
        """
        hex_color = hex_color.lstrip("#")

        # Support für 3-stellige Hex-Codes (z.B. #F00 -> #FF0000)
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])

        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except ValueError:
            # Fallback falls der Hex-Code ungültig ist
            return "#1E90FF"

        # Farbberechnung mit Clamp (0-255)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))

        return f"#{r:02X}{g:02X}{b:02X}"

    def setup_option_buttons(self, parent_layout):
        """Erstellt die mittleren Buttons mit Regenbogen-Progress, Sound und DE/EN Support."""
        from PyQt6.QtWidgets import QGridLayout, QWidget, QSizePolicy, QApplication
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import Qt, QTimer

        # Sprache abrufen
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = lang == "de"

        # Button-Definitionen (Key, Text_Key, Farbe, Callback, FG, Icon)
        button_defs = [
            ("git_status", "git_status", "#1E90FF", self.show_commits, "white", "SP_FileDialogContentsView"),
            ("plugin_update", "plugin_update", "#FF8C00", self.plugin_update_button_clicked, "white", "SP_ArrowDown"),
            ("restart_tool", "restart_tool", "#FF4500", self.restart_application_with_info, "white", "SP_BrowserReload"),
            ("edit_patch_header", "edit_patch_header", "#32CD32", self.edit_patch_header, "white", "SP_FileDialogDetailedView"),
            ("github_emu_config", "github_emu_config_button", "#FFA500", self.edit_emu_github_config, "black", "SP_ComputerIcon"),
            ("github_upload_patch", "github_upload_patch", "#1E90FF", github_upload_patch_file, "white", "SP_ArrowUp"),
            ("github_upload_emu", "github_upload_emu", "#1E90FF", github_upload_oscam_emu_folder, "white", "SP_ArrowUp"),
            ("oscam_emu_git_patch", "oscam_emu_git_patch", "#32CD32", patch_oscam_emu_git, "white", "SP_DialogApplyButton"),
            ("oscam_emu_git_clear", "oscam_emu_git_clear", "#FF4500", self.oscam_emu_git_clear, "white", "SP_TrashIcon"),
            ("s3_menu", " s3_simplebuild", "#EAFF00", self.start_s3_menu, "black", "SP_FileDialogDetailedView"),
        ]

        container = QWidget()
        options_grid = QGridLayout(container)
        options_grid.setSpacing(6)
        options_grid.setContentsMargins(0, 5, 0, 5)

        if not hasattr(self, "all_buttons"): self.all_buttons = []
        self.option_buttons = getattr(self, "option_buttons", {})
        
        cols_per_row = 5
        FLACH_HEIGHT = 35

        for idx, (key, text_key, color, callback, *rest) in enumerate(button_defs):
            current_fg = rest[0] if len(rest) > 0 else "white"
            current_icon = rest[1] if len(rest) > 1 else None

            # Sprach-Übersetzung
            raw_text = self.get_t(text_key, text_key) if hasattr(self, "get_t") else text_key

            def create_cb(c, k=key):
                def wrapper():
                    # --- 1. SOUND STARTEN ---
                    if "safe_play" in globals():
                        safe_play("service-login.oga")

                    # --- 2. REGENBOGEN-PROGRESS (15pt, Schwarze Schrift) ---
                    pbar = getattr(self, "progress_bar", None)
                    if pbar:
                        rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                                   "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                                   "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
                        pbar.setStyleSheet(f"""
                            QProgressBar {{
                                text-align: center; font-weight: 700; border: 2px solid #222;
                                border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                            }}
                            QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
                        """)
                        msg = "Verarbeite..." if is_de else "Processing..."
                        pbar.setFormat(f"⚙️ {msg} %p%")
                        pbar.setValue(15)
                        pbar.show()
                        QApplication.processEvents()

                    # --- 3. FUNKTIONS-AUFRUF ---
                    try:
                        if hasattr(c, "__self__") or k == "online_patch_dl":
                            c()
                        else:
                            # Externe Funktionen (z.B. GitHub Upload)
                            callback_func = getattr(self, "upload_progress_with_speed", pbar.setValue if pbar else None)
                            c(gui_instance=self, info_widget=self.info_text, progress_callback=callback_func)
                        
                        # --- 4. ERFOLGS-SOUND & RESET ---
                        if "safe_play" in globals(): safe_play("complete.oga")
                        if pbar:
                            pbar.setValue(100)
                            pbar.setFormat("✅ OK!" if is_de else "✅ Done!")

                    except Exception as e:
                        if "safe_play" in globals(): safe_play("dialog-error.oga")
                        if pbar: pbar.setStyleSheet("QProgressBar { color: red; font-weight: 700; }")
                        print(f"Fehler bei {k}: {e}")

                    # --- 5. AUTO-RESET NACH 3 SEKUNDEN ---
                    if pbar:
                        QTimer.singleShot(3000, self.pbar_idle if hasattr(self, "pbar_idle") else lambda: pbar.setValue(0))

                return wrapper

            # Button erstellen
            btn = self.create_action_button(
                parent=self,
                text=raw_text,
                color=color,
                callback=create_cb(callback),
                all_buttons_list=self.all_buttons,
                fg=current_fg,
                icon_name=current_icon,
                min_height=FLACH_HEIGHT,
                radius=getattr(self, "BUTTON_RADIUS", 10),
            )

            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
            btn.setMinimumHeight(FLACH_HEIGHT)
            btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

            row = idx // cols_per_row
            col = idx % cols_per_row
            options_grid.addWidget(btn, row, col)
            self.option_buttons[key] = (btn, text_key)

        for i in range(cols_per_row):
            options_grid.setColumnStretch(i, 1)

        parent_layout.addWidget(container)

    def update_all_texts(self):
        # Labels
        self.lang_label.setText(TEXTS[self.LANG]["ui.language"])
        self.color_label.setText(TEXTS[self.LANG]["color_label"])
        self.commit_label.setText(TEXTS[self.LANG]["commit_count_label"])
        self.info_button.setToolTip(TEXTS[self.LANG]["ui.info"])

        # Option Buttons
        for btn, text_key in self.option_buttons.values():
            if text_key in TEXTS[self.LANG]:
                btn.setText(TEXTS[self.LANG][text_key])

        # Grid Buttons (Patch Aktionen)
        for key, btn in getattr(self, "buttons", {}).items():
            if key in TEXTS[self.LANG]:
                btn.setText(TEXTS[self.LANG][key])

        # Info Text
        if hasattr(self, "info_text") and "info_text" in TEXTS[self.LANG]:
            self.info_text.setPlainText(TEXTS[self.LANG]["info_text"])

    # ---------------------
    @staticmethod
    def start_update(self):
        print("Update starten …")
        # hier später:
        # - git pull
        # - zip download + entpacken
        # - oder installer starten

    def append_info(self, *args, **kwargs):
        from PyQt6.QtGui import QTextCursor
        from PyQt6.QtWidgets import QApplication, QTextEdit
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QAbstractAnimation

        # 1. Argumente sicher entpacken
        try:
            if len(args) == 3:
                widget, text, level = args[0], args[1], args[2]
            elif len(args) == 2:
                widget = getattr(self, "info_text", None)
                text, level = args[0], args[1]
            else:
                return
        except:
            return

        if not isinstance(widget, QTextEdit) or widget is None:
            return

        # 2. Farben & Variablen
        colors = {
            "success": "#00FF00",
            "warning": "orange",
            "error": "red",
            "info": "yellow",
            "white": "white",
            "raw": "transparent",
        }
        lvl_str = str(level).lower()
        current_color = colors.get(lvl_str, "white")
        do_newline = kwargs.get("newline", True)

        # 3. HTML vorbereiten
        safe_text = str(text).replace("\n", "<br>")
        html_output = ""
        if do_newline and widget.toPlainText().strip() != "":
            html_output += "<br>"

        if lvl_str == "raw":
            html_output += f'<div style="display:inline;">{safe_text}</div>'
        else:
            html_output += (
                f'<div style="color:{current_color}; display:inline;">{safe_text}</div>'
            )

        # 4. Am Ende einfügen
        cursor = widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        widget.setTextCursor(cursor)
        cursor.insertHtml(html_output)

        # 5. FIX FÜR DIE FEHLERMELDUNG (MINGW64)
        QApplication.processEvents()
        scrollbar = widget.verticalScrollBar()

        if scrollbar:
            # Animation instanziieren, falls nicht vorhanden
            if not hasattr(self, "_scroll_anim") or self._scroll_anim is None:
                self._scroll_anim = QPropertyAnimation()
                self._scroll_anim.setPropertyName(b"value")

            # WICHTIG: Erst STOPPEN, dann Ziel prüfen/setzen
            # Das verhindert die Meldung "can't change the target of a running animation"
            if self._scroll_anim.state() == QAbstractAnimation.State.Running:
                self._scroll_anim.stop()

            # Zielobjekt neu binden
            if self._scroll_anim.targetObject() != scrollbar:
                self._scroll_anim.setTargetObject(scrollbar)

            # Animation nur starten, wenn wir nicht schon am Ende sind
            if scrollbar.value() < scrollbar.maximum():
                self._scroll_anim.setDuration(300)
                self._scroll_anim.setStartValue(scrollbar.value())
                self._scroll_anim.setEndValue(scrollbar.maximum())
                self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self._scroll_anim.start()

        widget.ensureCursorVisible()

    def run_background_task(self, fn, *args, **kwargs):
        """Startet eine Funktion im Hintergrund und steuert die Progressbar"""
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.worker = TaskWorker(fn, *args, **kwargs)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.info.connect(
            lambda txt, lvl: self.append_info(self.info_text, txt, lvl)
        )
        self.worker.start()

    def restart_application_with_info(
        self, checked=False, progress_callback=None, info_widget=None
    ):
        """
        Sichert alle Daten und startet das Tool plattformübergreifend neu.
        """
        from PyQt6.QtWidgets import QMessageBox, QApplication
        import sys
        import os
        import subprocess

        # 1. Sprache & Texte sicherstellen
        lang_key = getattr(self, "LANG", "de").lower()
        lang_pack = (
            globals()
            .get("TEXTS", {})
            .get(lang_key, globals().get("TEXTS", {}).get("en", {}))
        )

        # 2. Dialog aufbauen
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(lang_pack.get("restart_tool", "Neustart"))
        msg.setText(
            lang_pack.get(
                "restart_tool_question", "Möchten Sie das Tool jetzt neu starten?"
            )
        )

        yes_btn = msg.addButton(
            lang_pack.get("yes", "Ja"), QMessageBox.ButtonRole.YesRole
        )
        no_btn = msg.addButton(
            lang_pack.get("no", "Nein"), QMessageBox.ButtonRole.NoRole
        )

        msg.exec()

        if msg.clickedButton() == yes_btn:
            # Sound abspielen
            if "safe_play" in globals():
                safe_play("service-logout.oga")

            # --- KRITISCHES SPEICHERN VOR NEUSTART ---
            try:
                # Falls self.cfg existiert, stellen wir sicher, dass die aktuellen UI-Werte drin sind
                if hasattr(self, "cfg"):
                    # Manuelle Synchronisation der wichtigsten Felder (Sicherheitsnetz)
                    if hasattr(self, "patch_modifier"):
                        self.cfg["patch_modifier"] = self.patch_modifier
                    if hasattr(self, "EMUREPO"):
                        self.cfg["EMUREPO"] = self.EMUREPO
                    if hasattr(self, "LANG"):
                        self.cfg["language"] = self.LANG.upper()

                    # Speichern (Silent=True, da wir eh beenden)
                    if "save_config" in globals():
                        globals()["save_config"](
                            self.cfg, gui_instance=self, silent=True
                        )

                # WICHTIG: Gib dem OS kurz Zeit, die Datei physisch zu schreiben
                QApplication.processEvents()

            except Exception as e:
                print(f"⚠️ Save error before restart: {e}")

            # --- PLATTFORMÜBERGREIFENDER NEUSTART ---
            try:
                python_exe = sys.executable
                script_path = os.path.abspath(__file__)
                cmd_args = sys.argv[1:]

                # Starte neuen Prozess
                if os.name == "nt":
                    subprocess.Popen(
                        [python_exe, script_path] + cmd_args,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                        close_fds=True,
                        shell=False,
                    )
                else:
                    subprocess.Popen([python_exe, script_path] + cmd_args)

                # Beende aktuelle Instanz sauber
                QApplication.instance().quit()
                sys.exit(0)
            except Exception as e:
                print(f"❌ Kritischer Fehler beim Neustart: {e}")
                QApplication.quit()
        else:
            # Bei "Nein" Fortschrittsbalken (falls vorhanden) auf 100 setzen
            if progress_callback:
                try:
                    progress_callback(100)
                except:
                    pass

    def restart_application(self, *args, **kwargs):
        import subprocess
        import sys
        import os
        from PyQt6.QtWidgets import QApplication

        # Speichern vor dem Exit
        try:
            if hasattr(self, "cfg"):
                self.cfg["language"] = getattr(self, "LANG", "DE").upper()
                if "save_config" in globals():
                    save_config(self.cfg)
        except:
            pass

        safe_play("service-logout.oga")

        # PFAD-FIX für Windows (Leerzeichen in 'Program Files')
        python = sys.executable
        script = os.path.abspath(__file__)

        # Subprocess mit Liste verhindert das Abschneiden des Pfades
        subprocess.Popen([python, script] + sys.argv[1:])

        QApplication.quit()
        sys.exit(0)

    # ===================== ZIP PATCH =====================
    def zip_patch(self, info_widget=None, progress_callback=None):
        """Erstellt ein ZIP des Patches mit Regenbogen-Progress und Auto-Reset."""
        from PyQt6.QtWidgets import QTextEdit, QApplication
        from PyQt6.QtCore import QTimer
        import zipfile
        import os

        # 1. Widget & ProgressBar Setup
        widget = (
            info_widget
            if isinstance(info_widget, QTextEdit)
            else getattr(self, "info_text", None)
        )
        lang = getattr(self, "LANG", "de").lower()
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)

        if pbar:
            # Regenbogen-Style mit SCHWARZER Schrift
            rainbow = (
                "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
            )
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center; font-weight: 700; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """
            )
            msg_zip = "Erstelle ZIP-Archiv..." if is_de else "Creating ZIP archive..."
            pbar.setFormat(f"{msg_zip} %p%")
            pbar.setValue(10)
            pbar.show()
            QApplication.processEvents()

        # Hilfsfunktionen
        def get_msg(key, default, **kwargs):
            template = TEXTS.get(lang, {}).get(key, default)
            try:
                return template.format(**kwargs)
            except:
                return template

        def play_zip_sound(success=True):
            safe_play("complete.oga" if success else "dialog-error.oga")

        # --- Eigentliche ZIP-Logik ---
        try:
            if pbar:
                pbar.setValue(30)

            if not os.path.exists(PATCH_FILE):
                msg = get_msg(
                    "patch_file_missing",
                    "Datei nicht gefunden: {path}",
                    path=PATCH_FILE,
                )
                self.append_info(widget, msg, "error")
                play_zip_sound(False)
                if pbar:
                    pbar.setValue(100)
                return

            if pbar:
                pbar.setValue(60)

            # Zippen
            with zipfile.ZipFile(
                ZIP_FILE, "w", compression=zipfile.ZIP_DEFLATED
            ) as zipf:
                zipf.write(PATCH_FILE, os.path.basename(PATCH_FILE))

            if pbar:
                pbar.setValue(90)

            # Erfolgsmeldung
            msg = get_msg(
                "zip_success",
                "✅ Patch erfolgreich gepackt: {zip_file}",
                zip_file=ZIP_FILE,
            )
            self.append_info(widget, msg, "success")
            play_zip_sound(True)

            if pbar:
                done_msg = "ZIP erstellt!" if is_de else "ZIP created!"
                pbar.setFormat(f"📦 {done_msg} 100%")

        except Exception as e:
            if pbar:
                pbar.setStyleSheet("QProgressBar { color: red; font-weight: 700; }")
            msg = get_msg("zip_failed", "❌ Fehler beim Zippen: {error}", error=str(e))
            self.append_info(widget, msg, "error")
            play_zip_sound(False)

        # --- ABSCHLUSS & AUTO-RESET ---
        if pbar:
            pbar.setValue(100)
            # Nach 3 Sekunden zurücksetzen (Style und Werte)
            QTimer.singleShot(3000, lambda: pbar.setValue(0))
            # QTimer.singleShot(3000, lambda: pbar.setFormat("%p%"))
            # Optional: Original-Style (Orange/Gold) wiederherstellen
            default_style = """
                QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; color: orange; text-align: center; font-weight: bold; }
                QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }
            """
            QTimer.singleShot(3000, lambda: pbar.setStyleSheet(default_style))

        if progress_callback:
            try:
                progress_callback(100)
            except:
                pass

        QApplication.processEvents()

    def run_command(self, cmd, cwd=None):
        """Führt Befehle aus und gibt das Ergebnis als String zurück."""
        import subprocess

        try:
            # shell=True ist für komplexe git-Befehle oft notwendig
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                shell=True,
                check=False,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown Error"
                # Wir loggen den Fehler direkt in den Infoscreen statt nur in die Konsole
                self.log(f"❌ Befehlsfehler: {error_msg}", "error")
                return ""

            return result.stdout.strip()
        except Exception as e:
            self.log(f"❌ Systemfehler: {str(e)}", "error")
            return ""

    def log(self, msg, level="info"):
        """
        Gibt Nachrichten im Infoscreen aus.
        Nutzt die vorhandene append_info Logik, um den THEME-Fehler zu vermeiden.
        """
        from PyQt6.QtGui import QTextCursor
        from PyQt6.QtWidgets import QApplication

        # Wir nutzen deine funktionierende append_info statt dem kaputten THEME-Dictionary
        if hasattr(self, "append_info") and hasattr(self, "info_text"):
            self.append_info(self.info_text, msg, level)
        else:
            # Notfall-Fallback falls append_info nicht erreichbar ist
            self.info_text.append(msg)

        # Sicherstellen, dass das Fenster zum Ende scrollt
        self.info_text.moveCursor(QTextCursor.MoveOperation.End)

        # GUI aktualisieren, damit der Text sofort erscheint (wichtig bei Prozessen)
        QApplication.processEvents()

    def commit_value_changed(self, value):
        # 1. Im Dict speichern (hast du bereits)
        self.cfg["commit_count"] = value

        # 2. In die Datei schreiben (WICHTIG!)
        if hasattr(self, "save_config"):
            self.save_config()

        # 3. Rückmeldung geben
        self.append_info(
            self.info_text,
            f"Commit-Anzahl auf {value} gesetzt (gespeichert)",
            "success",
        )

    def change_old_patch_dir(self, info_widget=None, progress_callback=None):
        """
        Ändert den Speicherort des alten Patch-Ordners mit Regenbogen-Progress.
        Text während des Vorgangs sichtbar, am Ende 3 Sekunden stehen lassen.
        """
        from PyQt6.QtWidgets import QFileDialog, QApplication
        from PyQt6.QtCore import QTimer
        import json, os

        widget = info_widget or getattr(self, "info_text", None)
        lang = getattr(self, "LANG", "de").lower()
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)

        # -------------------------------
        # Helper-Funktionen
        # -------------------------------
        def log(text, level="info"):
            if widget and hasattr(self, "append_info"):
                self.append_info(widget, text, level)
            else:
                print(f"[{level.upper()}] {text}")

        def set_progress(val, text=None):
            if not pbar:
                return
            rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{
                    background-color: {rainbow};
                    border-radius: 4px;
                }}
                """
            )
            pbar.show()
            pbar.setValue(val)
            if text:
                pbar.setFormat(text)
            QApplication.processEvents()
            if progress_callback:
                try:
                    progress_callback(val)
                except Exception:
                    pass

        def finalize_pbar(text, visible_seconds=3):
            if not pbar:
                return
            rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{
                    background-color: {rainbow};
                    border-radius: 4px;
                }}
                """
            )
            pbar.setValue(100)
            pbar.setFormat(text)
            # Nach 3 Sekunden Chunk transparent, Value auf 0
            QTimer.singleShot(
                visible_seconds * 1000,
                lambda: pbar.setStyleSheet(
                    """
                QProgressBar {
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: orange; font-size: 15pt;
                }
                QProgressBar::chunk {
                    background-color: transparent;
                }
                """
                ),
            )
            QTimer.singleShot(visible_seconds * 1000, lambda: pbar.setValue(0))
            if progress_callback:
                QTimer.singleShot(visible_seconds * 1000, lambda: progress_callback(0))

        # -------------------------------
        # START
        # -------------------------------
        if pbar:
            set_progress(
                10, "📂 " + ("Ordner auswählen..." if is_de else "Select folder...")
            )

        start_dir = getattr(self, "OLD_PATCH_DIR", OLD_PATCH_DIR_PLUGIN_DEFAULT)
        new_dir = QFileDialog.getExistingDirectory(
            self, "Select S3 Patch Folder", start_dir
        )

        if new_dir:
            if pbar:
                set_progress(
                    50, "🔄 Pfade aktualisieren..." if is_de else "Updating paths..."
                )
            # Pfade aktualisieren
            self.OLD_PATCH_DIR = new_dir
            self.OLD_PATCH_FILE = os.path.join(new_dir, "oscam-emu.patch")
            self.ALT_PATCH_FILE = os.path.join(new_dir, "oscam-emu.altpatch")
            self.PATCH_MANAGER_OLD = os.path.join(new_dir, "oscam_patch_manager_old.py")
            self.CONFIG_OLD = os.path.join(new_dir, "config_old.json")
            self.GITHUB_CONFIG_OLD = os.path.join(
                new_dir, "github_upload_config_old.json"
            )

            # Config speichern
            self.cfg["s3_patch_path"] = new_dir
            try:
                with open("config.json", "w") as f:
                    json.dump(self.cfg, f, indent=2)

                success_msg = (
                    f"✅ Ordner geändert: {new_dir}"
                    if is_de
                    else f"✅ Folder changed: {new_dir}"
                )
                log(success_msg, "success")
                if pbar:
                    finalize_pbar("✅ " + ("Gespeichert!" if is_de else "Saved!"))

            except Exception as e:
                log(f"❌ Fehler: {e}", "error")
                if pbar:
                    finalize_pbar(f"❌ {str(e)}")

        else:
            log("ℹ️ Abgebrochen" if is_de else "ℹ️ Cancelled", "info")
            if pbar:
                finalize_pbar("ℹ️ " + ("Abgebrochen" if is_de else "Cancelled"))

    def update_ui_texts(self):
        """Zentrale Text- und Icon-Aktualisierung mit Regenbogen-Progress."""
        from PyQt6.QtWidgets import QApplication, QStyle
        from PyQt6.QtCore import QSize, QTimer
        import re

        # 1. Sprache & Progress Setup
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)

        if pbar:
            rainbow = (
                "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
            )
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 11pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """
            )
            msg_ui = "UI wird aktualisiert..." if is_de else "Updating UI..."
            pbar.setFormat(f"{msg_ui} %p%")
            pbar.setValue(10)
            pbar.show()
            QApplication.processEvents()

        def apply_final_style(btn, text, standard_pixmap):
            if not btn:
                return
            clean_text = re.sub(
                r"[^\x00-\x7F\xc0-\xff\s\.\,\:\-\_\!\?]+", "", str(text)
            ).strip()
            if len(clean_text) > 18 and " " in clean_text:
                clean_text = clean_text.replace(" ", "\n", 1)
            btn.setText(clean_text)
            btn.setIcon(QApplication.style().standardIcon(standard_pixmap))
            btn.setIconSize(QSize(20, 20))
            btn.setMinimumSize(185, 48)
            btn.setStyleSheet("text-align: left; padding-left: 8px; font-weight: bold;")

        # --- LABELS AKTUALISIEREN ---
        if pbar:
            pbar.setValue(40)

        if hasattr(self, "commit_label"):
            self.commit_label.setText("Commits:")
            self.commit_label.setFixedWidth(self.commit_label.sizeHint().width() + 10)

        if hasattr(self, "color_label"):
            self.color_label.setText("Farbe:" if is_de else "Color:")
            self.color_label.setFixedWidth(self.color_label.sizeHint().width() + 10)

        if hasattr(self, "lang_label"):
            label_text = "Sprache:" if is_de else "Language:"
            self.lang_label.setText(f"🌐 {label_text}")

        # --- BUTTONS AKTUALISIEREN ---
        if pbar:
            pbar.setValue(70)

        apply_final_style(
            self.btn_open_work,
            "Arbeitsordner" if is_de else "WORK_DIR",
            QStyle.StandardPixmap.SP_DirIcon,
        )
        apply_final_style(
            self.btn_open_temp, "Temp-Repo", QStyle.StandardPixmap.SP_DirIcon
        )
        apply_final_style(
            self.btn_open_emu, "Emu-Git", QStyle.StandardPixmap.SP_DirIcon
        )
        apply_final_style(
            self.btn_check_tools,
            "Tools prüfen" if is_de else "Check Tools",
            QStyle.StandardPixmap.SP_ComputerIcon,
        )
        apply_final_style(
            self.btn_modifier,
            "Patch Autor" if is_de else "Patch Author",
            QStyle.StandardPixmap.SP_FileDialogDetailedView,
        )
        apply_final_style(
            self.btn_repo_url, "Repo URL", QStyle.StandardPixmap.SP_DriveNetIcon
        )
        apply_final_style(
            self.btn_check_commit,
            "Commit Check" if is_de else "Check Commit",
            QStyle.StandardPixmap.SP_BrowserReload,
        )

        # REIHE 3: Dynamische Buttons
        if hasattr(self, "buttons"):
            grid_icons = {
                "patch_create": QStyle.StandardPixmap.SP_FileIcon,
                "patch_renew": QStyle.StandardPixmap.SP_BrowserReload,
                "patch_check": QStyle.StandardPixmap.SP_DialogApplyButton,
                "patch_apply": QStyle.StandardPixmap.SP_MediaPlay,
                "patch_zip": QStyle.StandardPixmap.SP_DriveFDIcon,
                "backup_old": QStyle.StandardPixmap.SP_DialogSaveButton,
                "clean_folder": QStyle.StandardPixmap.SP_TrashIcon,
                "change_old_dir": QStyle.StandardPixmap.SP_DirOpenIcon,
                "exit": QStyle.StandardPixmap.SP_DialogCloseButton,
            }
            for key, btn in self.buttons.items():
                text = self.get_t(key, key)
                if key in grid_icons:
                    apply_final_style(btn, text, grid_icons[key])

        # --- ABSCHLUSS ---
        if pbar:
            pbar.setValue(100)
            done_msg = "UI bereit!" if is_de else "UI ready!"
            pbar.setFormat(f"✅ {done_msg} 100%")
            # Auto-Reset nach 2 Sekunden
            QTimer.singleShot(3000, self.pbar_idle)
            # Zurück zum Standard-Style (Orange)
            def_style = "QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; color: white; text-align: center; font-weight: bold; } QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }"
            QTimer.singleShot(2000, lambda: pbar.setStyleSheet(def_style))

        QApplication.processEvents()

    def edit_patch_header(self, info_widget=None, progress_callback=None):
        """Öffnet den Header-Editor mit Regenbogen-Progress, Sound und Sprach-Support."""
        import os
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QApplication
        from PyQt6.QtCore import QTimer

        # 1. Sprache & Progress Setup
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)

        # Lokalisierte Texte
        T_LOADING = "Editor wird geladen..." if is_de else "Loading editor..."
        T_SAVED   = "Patch gespeichert!" if is_de else "Patch saved!"
        T_CANCEL  = "Abgebrochen" if is_de else "Cancelled"
        T_TITLE   = "Patch-Header Editor"

        # --- SOUND BEIM ÖFFNEN ---
        if "safe_play" in globals():
            safe_play("service-login.oga")

        if pbar:
            # Regenbogen-Style mit SCHWARZER Schrift (font-size 15pt wie im ZIP-Code)
            rainbow = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                       "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                       "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);")
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    text-align: center; font-weight: 700; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
            """)
            pbar.setFormat(f"📝 {T_LOADING} %p%")
            pbar.setValue(20)
            pbar.show()
            QApplication.processEvents()

        # Pfad zur Datei sicherstellen (base_dir aus __init__)
        base = getattr(self, "base_dir", os.getcwd())
        p_file = os.path.join(base, "oscam-emu.patch")

        if not os.path.exists(p_file):
            if pbar: pbar.setValue(0)
            if "safe_play" in globals(): safe_play("dialog-error.oga")
            return

        # 2. Dialog erstellen
        dlg = QDialog(self)
        dlg.setWindowTitle(T_TITLE)
        dlg.resize(900, 700)
        ly = QVBoxLayout(dlg)
        
        edit = QTextEdit()
        # Matrix-Style: Schwarz mit grüner Schrift
        edit.setStyleSheet("background-color: #000; color: #0F0; font-family: monospace; font-size: 11pt; border: 1px solid #333;")

        try:
            with open(p_file, "r", encoding="utf-8", errors="ignore") as f:
                edit.setPlainText(f.read())
            if pbar: pbar.setValue(60)
        except Exception:
            if pbar: pbar.setValue(0)
            return

        ly.addWidget(edit)
        
        # --- BUTTONS ÜBERSETZEN ---
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_save = bb.button(QDialogButtonBox.StandardButton.Save)
        if btn_save: btn_save.setText("Speichern" if is_de else "Save")
        btn_cancel = bb.button(QDialogButtonBox.StandardButton.Cancel)
        if btn_cancel: btn_cancel.setText("Abbrechen" if is_de else "Cancel")

        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        ly.addWidget(bb)

        if pbar: pbar.setValue(90)

        # 3. Dialog ausführen
        result = dlg.exec()

        if result == QDialog.DialogCode.Accepted:
            try:
                # --- SOUND BEIM SPEICHERN ---
                if "safe_play" in globals():
                    safe_play("complete.oga") # Erfolgs-Sound

                content = edit.toPlainText()
                with open(p_file, "w", encoding="utf-8") as f:
                    f.write(content)

                if pbar:
                    pbar.setValue(100)
                    pbar.setFormat(f"✅ {T_SAVED} 100%")
            except Exception:
                if "safe_play" in globals(): safe_play("dialog-error.oga")
                if pbar: pbar.setStyleSheet("QProgressBar { color: red; }")
        else:
            # --- SOUND BEIM ABBRECHEN ---
            if "safe_play" in globals():
                safe_play("dialog-error.oga")
            
            if pbar:
                pbar.setValue(0)
                pbar.setFormat(f"↩️ {T_CANCEL}")

        # 4. AUTO-RESET (nach 3 Sekunden zurück zum Standard Orange/Gold)
        def restore_pbar():
            if pbar:
                pbar.setValue(0)
                pbar.setFormat("%p%")
                pbar.setStyleSheet("""
                    QProgressBar { border: 1px solid #444; border-radius: 8px; background-color: #1A1A1A; 
                    color: white; text-align: center; font-weight: bold; }
                    QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #F37804, stop:1 #FFD700); border-radius: 8px; }
                """)
        
        QTimer.singleShot(3000, restore_pbar)

        if progress_callback:
            progress_callback(100)

        # ---------------------
        # PLUGIN UPDATE
        # ---------------------

    def update_plugin_button_state(self):
        """Aktualisiert den Text und die Farbe des Update-Buttons."""
        btn_data = self.option_buttons.get("plugin_update")
        if not btn_data:
            return
        btn = btn_data[0]

        lang = str(getattr(self, "LANG", "de")).lower()
        t = TEXTS.get(lang, TEXTS.get("de", {}))

        cv = APP_VERSION.lstrip("v")
        lv = getattr(self, "latest_version", cv)

        if Version(lv) > Version(cv):
            txt = t.get("state_plugin_update_available", "Update: {current} → {latest}")
            btn.setText(txt.format(current=cv, latest=lv))
            btn.setStyleSheet(
                "background-color: #d35400; color: white; font-weight: bold;"
            )
        else:
            txt = t.get("state_plugin_uptodate", "v{version} aktuell")
            btn.setText(txt.format(version=cv))
            btn.setStyleSheet(
                "background-color: #1E90FF; color: white; font-weight: bold;"
            )

    def fetch_latest_version(self):
        """Vergleicht lokale APP_VERSION mit version.txt auf GitHub"""
        import requests
        from packaging.version import Version

        widget = getattr(self, "info_text", None)

        def log(text_key, level="info", **kwargs):
            colors = {
                "success": "green",
                "warning": "orange",
                "error": "red",
                "info": "gray",
            }
            color = colors.get(level, "gray")
            text_template = TEXTS[LANG].get(text_key, text_key)
            text = text_template.format(**kwargs)

            if isinstance(widget, QTextEdit):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.MoveOperation.End)
                QApplication.processEvents()
            else:
                print(f"[{level.upper()}] {text}")

        try:
            url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/version.txt"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()

            latest = resp.text.strip()
            self.latest_version = latest

            if Version(latest) > Version(APP_VERSION):
                log("github_version_available", "info", version=latest)
                self.ask_for_update(latest)  # 👈 wichtig
            else:
                log("update_current_version", "success", version=APP_VERSION)

        except Exception as e:
            log("github_version_fetch_failed", "warning", error=str(e))

    def fetch_latest_github_version(self):
        """
        Holt die neueste Version von GitHub (version.txt) und aktualisiert self.latest_version.
        """
        try:
            import requests

            url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/version.txt"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            version = resp.text.strip().lstrip("v")  # "v1.4.7" → "1.4.7"
            self.latest_version = version

            self.append_info(
                self.info_text, f"Verfügbare GitHub-Version: v{version}", "info"
            )

            # Button-Zustand aktualisieren
            self.update_plugin_button_state()
            return version

        except Exception as e:
            self.append_info(
                self.info_text,
                f"❌ Fehler beim Abrufen der GitHub-Version: {e}",
                "error",
            )
            self.latest_version = None
            self.update_plugin_button_state()
            return None

    def plugin_update_button_clicked(
        self, checked=False, info_widget=None, progress_callback=None
    ):
        """
        Geprüfter Update-Callback mit Regenbogen-Progress und schwarzem Text (DE/EN).
        Zentrierte Log-Ausgabe und korrekte URL-Verarbeitung.
        Erzwingt Ja/Nein Buttons passend zur gewählten Sprache.
        """
        from PyQt6.QtWidgets import QTextEdit, QApplication, QMessageBox
        from PyQt6.QtGui import QTextCursor
        import requests, time, re

        # --- 1. SPRACHE & PROGRESSBAR SETUP ---
        lang_key = getattr(self, "LANG", "de").lower()
        is_de = lang_key == "de"
        widget = info_widget or getattr(self, "info_text", None)
        pbar = getattr(self, "progress_bar", None)

        if pbar:
            rainbow = (
                "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
            )
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 11pt;
                }}
                QProgressBar::chunk {{ background-color: {rainbow}; border-radius: 4px; }}
                """
            )
            msg_check = "Prüfe auf Updates..." if is_de else "Checking for updates..."
            pbar.setFormat(f"{msg_check} %p%")
            pbar.setValue(0)
            pbar.show()
            QApplication.processEvents()

        # Version-Klasse (Fallback)
        try:
            from packaging.version import Version
        except ImportError:

            class Version:
                def __init__(self, v):
                    self.v = [int(x) for x in re.findall(r"\d+", str(v))]

                def __gt__(self, other):
                    return self.v > other.v

                def __lt__(self, other):
                    return self.v < other.v

                def __eq__(self, other):
                    return self.v == other.v

        def log(text_key, level="info", **kwargs):
            colors = {
                "success": "#00FF00",
                "warning": "orange",
                "error": "red",
                "info": "#00ADFF",
            }
            color = colors.get(level, "gray")
            lang_dict = (
                globals()
                .get("TEXTS", {})
                .get(lang_key, globals().get("TEXTS", {}).get("en", {}))
            )
            text_template = lang_dict.get(text_key, text_key)

            try:
                safe_kwargs = {
                    "current": globals().get("APP_VERSION", "3.3.7"),
                    "latest": getattr(self, "latest_version", "???"),
                }
                safe_kwargs.update(kwargs)
                text = text_template.format(**safe_kwargs)
            except:
                text = text_template

            if isinstance(widget, QTextEdit):
                widget.append(
                    f'<div style="text-align:center;"><span style="color:{color}"><b>{text}</b></span></div>'
                )
                widget.moveCursor(QTextCursor.MoveOperation.End)
                QApplication.processEvents()

        log("update_check_start", "info")
        if pbar:
            pbar.setValue(20)

        # --- 2. URL & CHECK ---
        version_url_base = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/refs/heads/master/version.txt"

        try:
            v_url = f"{version_url_base}?nocache={int(time.time())}"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(v_url, headers=headers, timeout=10)
            resp.raise_for_status()

            latest_str = resp.text.strip().lower().replace("v", "").strip()
            current_str = (
                globals()
                .get("APP_VERSION", "3.3.7")
                .strip()
                .lower()
                .replace("v", "")
                .strip()
            )

            self.latest_version = latest_str
            v_latest = Version(latest_str)
            v_current = Version(current_str)

            if pbar:
                pbar.setValue(60)

            # --- 3. VERGLEICH & MESSAGEBOX ---
            if v_latest > v_current:
                log("update_found", "warning", latest=latest_str, current=current_str)

                if pbar:
                    pbar.setValue(80)
                    msg_up = "Update verfügbar!" if is_de else "Update available!"
                    pbar.setFormat(f"✨ {msg_up} (v{latest_str})")

                lang_dict = globals().get("TEXTS", {}).get(lang_key, {})
                msg_title = lang_dict.get("update_box_title", "Update")
                msg_body = lang_dict.get("update_box_msg", "Update?").format(
                    latest=latest_str, current=current_str
                )

                msg_box = QMessageBox(self)
                msg_box.setWindowTitle(msg_title)
                msg_box.setText(msg_body)

                # Buttons manuell setzen um "Yes/No" (Systemsprache) zu umgehen
                yes_text, no_text = ("Ja", "Nein") if is_de else ("Yes", "No")
                yes_button = msg_box.addButton(yes_text, QMessageBox.ButtonRole.YesRole)
                no_button = msg_box.addButton(no_text, QMessageBox.ButtonRole.NoRole)

                msg_box.setDefaultButton(yes_button)
                msg_box.setEscapeButton(no_button)

                msg_box.exec()

                if msg_box.clickedButton() == yes_button:
                    if hasattr(self, "plugin_update_action"):
                        self.plugin_update_action(latest_version=latest_str)
                else:
                    log("update_declined", "info")
                    if pbar:
                        pbar.setValue(100)
            else:
                # Aktuell
                if pbar:
                    pbar.setFormat(
                        f"✅ v{current_str} aktuell 100%"
                        if is_de
                        else f"✅ v{current_str} up-to-date 100%"
                    )
                    pbar.setValue(100)
                log("update_no_update", "success")

        except Exception as e:
            error_label = "Fehler" if is_de else "Error"
            log("update_fail", "error", error=str(e))
            if pbar:
                pbar.setStyleSheet("QProgressBar { color: red; font-weight: bold; }")
                pbar.setFormat(f"❌ {error_label}: {str(e)[:40]}")
                pbar.setValue(100)

        # Timer zum Aufräumen
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(
            4000,
            lambda: (
                self.pbar_idle()
                if hasattr(self, "pbar_idle")
                else (pbar.hide() if pbar else None)
            ),
        )

        # UI Color Fix für Hover-Effekte
        if hasattr(self, "repaint_ui_colors"):
            self.repaint_ui_colors()

    # ---------------------
    # UPDATE CHECK
    # ---------------------
    def check_for_update_on_start(self):
        """
        Vervollständigt den Log voll übersetzbar.
        Finalisiert den System-Check mit der korrekten Konfiguration aus der JSON.
        """
        if getattr(self, "_update_dialog_active", False):
            return
        self._update_dialog_active = True

        import requests
        import time

        # Nutzen der im Skript definierten Version-Klasse als Fallback
        try:
            from packaging.version import Version
        except ImportError:
            Version = globals().get("Version")

        txt = getattr(self, "TEXT", {})

        # --- ZENTRALE FORMATIERUNG ---
        SZ_BIG = "26px"  # Orange Titel
        SZ_NORM = "21px"  # Standard-Inhalte
        F_FAMILY = "'Segoe UI', Tahoma, sans-serif"

        C_ORANGE = "#F37804"
        C_GREEN = "#00FF00"
        C_BLUE = "#00ADFF"
        C_LINE = "#808080"

        v_url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/master/version.txt"

        try:
            # Cache-Busting durch Timestamp
            resp = requests.get(f"{v_url}?t={int(time.time())}", timeout=5)
            resp.raise_for_status()

            latest_v = resp.text.strip().lstrip("v")
            current_v = APP_VERSION.strip().lstrip("v")

            output = []

            # --- LOGIK: VERSION VERGLEICHEN ---
            is_new = False
            try:
                is_new = Version(latest_v) > Version(current_v)
            except Exception:
                is_new = latest_v != current_v

            if is_new:
                # --- FALL: UPDATE VERFÜGBAR ---
                label = txt.get("new_version_available", "Update verfügbar")
                output.append(
                    f'<span style="font-family:{F_FAMILY}; font-size:{SZ_BIG}; color:{C_ORANGE}"><b>➔ {label}: v{latest_v}</b></span>'
                )

                if hasattr(self, "btn_update"):
                    btn_tpl = txt.get("upd_btn_new", "Update verfügbar: v{v}")
                    btn_txt = btn_tpl.format(v=latest_v, latest=latest_v)
                    self.btn_update.setText(btn_txt)
                    # WICHTIG: Farbe setzen, aber Größe stabil halten (Fixed-Policy vorausgesetzt)
                    self.btn_update.setStyleSheet(
                        f"color: {C_ORANGE}; font-weight: bold; border: 1px solid {C_ORANGE}; border-radius: 5px;"
                    )
            else:
                # --- FALL: KEIN UPDATE ---
                output.append(
                    f'<span style="font-family:{F_FAMILY}; font-size:{SZ_NORM}; color:{C_GREEN}"><b>{txt.get("no_update_found", "Kein Update vorhanden....")}</b></span>'
                )

                upd_ok_msg = txt.get("upd_ok", "Plugin ist aktuell")
                output.append(
                    f'<span style="font-family:{F_FAMILY}; font-size:{SZ_NORM}; color:{C_BLUE}"><b>✅ {upd_ok_msg} (Version: {current_v})</b></span>'
                )

                if hasattr(self, "btn_update"):
                    btn_curr_tpl = txt.get("upd_btn_current", "v{v} (Aktuell)")
                    # FIX: Benutze current_v statt der undefinierten current_version
                    btn_curr_txt = btn_curr_tpl.format(v=current_v, current=current_v)
                    self.btn_update.setText(btn_curr_txt)
                    self.btn_update.setStyleSheet(
                        "color: #00FF00; font-weight: bold; border: 1px solid #00FF00; border-radius: 5px;"
                    )

            # --- KONFIGURATIONS-BLOCK ---
            output.append(f'<span style="color:{C_LINE}">{"-" * 45}</span>')
            output.append(
                f'<span style="font-family:{F_FAMILY}; font-size:{SZ_BIG}; color:{C_ORANGE}"><b>{txt.get("active_conf", "🛠️ Aktive Konfiguration:")}</b></span>'
            )

            # Sicherer Zugriff auf Config
            cfg_obj = getattr(self, "cfg", {})
            author = cfg_obj.get(
                "patch_modifier", getattr(self, "patch_modifier", "speedy005")
            )
            repo_url = cfg_obj.get(
                "EMUREPO",
                getattr(self, "EMUREPO", "https://github.com/speedy005/Oscam-emu.git"),
            )

            output.append(
                f'<span style="font-family:{F_FAMILY}; font-size:{SZ_NORM}; color:{C_GREEN}"><b>  👤 {txt.get("patch_author", "Patch Autor")}: {author}</b></span>'
            )
            output.append(
                f'<span style="font-family:{F_FAMILY}; font-size:{SZ_NORM}; color:{C_BLUE}"><b>  🌐 {txt.get("repository", "Repository")}: {repo_url}</b></span>'
            )
            output.append(f'<span style="color:{C_LINE}">{"-" * 45}</span>')

            # Log ausgeben
            if hasattr(self, "append_info") and hasattr(self, "info_text"):
                self.append_info(self.info_text, "\n".join(output), "raw")

            # Abschluss-Sound
            if "safe_play" in globals():
                safe_play("complete.oga")

            if is_new:
                self.show_update_dialog(latest_v, current_v)

        except Exception as e:
            if "safe_play" in globals():
                safe_play("dialog-error.oga")
            err_lbl = txt.get("update_error", "Update-Check fehlgeschlagen")
            if hasattr(self, "append_info"):
                self.append_info(
                    self.info_text,
                    f'<span style="font-family:{F_FAMILY}; font-size:{SZ_NORM}; color:red"><b>➔ {err_lbl}: {str(e)}</b></span>',
                    "raw",
                )
        finally:
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(
                1000, lambda: setattr(self, "_update_dialog_active", False)
            )

    # ---------------------
    # TOOLS CHECK
    # ---------------------

    def run_full_system_check(self, clear_log=True):
        import shutil, platform, socket, importlib.util, time, os
        import urllib3
        from datetime import datetime
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QTextCursor
        import subprocess, re, requests

        if getattr(self, "_checking_active", False):
            return
        self.is_loading = True
        self._checking_active = True

        # --- ProgressBar Initialisierung & Reset ---
        pbar = getattr(self, "progress_bar", None)
        if pbar:
            rainbow_style = (
                "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
            )
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center;
                    font-weight: 900;
                    border: 2px solid #222;
                    border-radius: 6px;
                    background-color: #111;
                   color: black;
                   font-size: 14pt;
                }}
                QProgressBar::chunk {{
                    background-color: {rainbow_style}
                    border-radius: 4px;
               }}
            """
            )
            pbar.setFormat("%p%")
            pbar.setTextVisible(True)
            pbar.setRange(0, 100)
            pbar.setValue(0)
            pbar.show()
            if pbar:
                pbar.setValue(0)  # Start
        try:
            # === ZENTRALE GRÖSSEN & Farben ===
            S_TITEL, S_HEADER, S_NORM, S_EMOJI, S_FEAT, S_FOOTER = (
                "32pt",
                "20pt",
                "20pt",
                "20pt",
                "20pt",
                "20pt",
            )
            C_GREEN, C_BLUE, C_YELLOW, C_RED, C_LINE, C_ORANGE = (
                "#00FF00",
                "#00ADFF",
                "#FFFF00",
                "#FF0000",
                "#444444",
                "#F57A08",
            )
            C_START_TEXT, C_START_TIME = C_ORANGE, C_RED
            S_AV_SIZE, F_AV_STYLE, F_AV_WEIGHT = "22pt", "'Bold', sans-serif", "bold"
            C_AV_LABEL_AUTOR, C_AV_VALUE_AUTOR = C_RED, C_YELLOW
            C_AV_LABEL_VER, C_AV_VALUE_VER = C_ORANGE, C_BLUE
            F_FEAT_STYLE, F_FEAT_WEIGHT = "'Bold', sans-serif", "bold"
            S_REPO, C_REPO_NAME, C_REPO_VAL = "20pt", C_GREEN, C_BLUE
            F_MONO = "'Arial Black', 'Segoe UI', sans-serif"
            F_EMOJI = (
                "'Noto Color Emoji', 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif"
            )

            app_ver = globals().get("APP_VERSION", "3.1.5")
            timestamp = datetime.now().strftime("%H:%M:%S")
            lang = getattr(self, "LANG", "de").lower()
            is_de = lang == "de"

            T = {
                "live": "LIVE",
                "monitor": "System Monitor",
                "autor": "Autor" if is_de else "Author",
                "version": "Version",
                "features_head": "Hauptmerkmale:" if is_de else "Key Features:",
                "feat_1": "Erstellt .patch" if is_de else "Generates .patch",
                "feat_2": "GitHub Patches" if is_de else "GitHub patches",
                "feat_3": "DE/EN Lokalisierung" if is_de else "DE/EN Localization",
                "feat_4": "Echtzeit-Log" if is_de else "Real-time log",
                "start": (
                    "Starte System Check..." if is_de else "Starting System Check..."
                ),
                "lang_name": "Deutsch" if is_de else "English",
                "lang_label": "Sprache" if is_de else "Language",
                "kernel": "System Kern" if is_de else "System Kernel",
                "ok": "OK",
                "missing": "FEHLT" if is_de else "MISSING",
                "online": "Online",
                "offline": "Offline",
                "network": "Netzwerk" if is_de else "Network",
                "ping": "Ping Test",
                "foot_ok": "System-Check OK." if is_de else "System Check OK.",
                "foot_ready": "Bereit." if is_de else "Ready.",
            }

            widget = getattr(self, "info_text", None)
            if not widget:
                return
            if clear_log:
                widget.setHtml("")

            def make_safe_row(icon, label, status, label_col, status_col, size=S_NORM):
                return (
                    f'<div style="white-space: nowrap; margin: 0; padding: 0; line-height: 1.2; text-align: center;">'
                    f'<span style="font-family:{F_EMOJI}; font-size:{S_EMOJI};">{icon} </span>'
                    f'<span style="font-family:{F_MONO}; font-size:{size}; color:{label_col};"><b>{label.replace(" ", "&nbsp;")} :&nbsp;</b></span>'
                    f'<span style="font-family:{F_MONO}; font-size:{size}; color:{status_col};"><b>{status}</b></span></div>'
                )

            html = []

            # --- Live Header ---
            # Hier text-align: center hinzufügen
            html.append(
                f'<div style="line-height:1.0; text-align: center;">'
                f'<div style="margin-bottom:2px;">'
                f'<span style="color:{C_GREEN}; font-size:26pt; display:inline-block;">●</span>'
                f'<span style="color:{C_RED}; font-family:\'Arial Black\',\'Segoe UI Black\',sans-serif; font-size:20pt; font-weight:bold;"> {T["live"]}</span> | '
                f'<span style="color:{C_BLUE}; font-family:\'Arial Black\',\'Segoe UI Black\',sans-serif; font-size:20pt; font-weight:bold;">{T["monitor"]}</span>'
                f"</div>"
            )

            # OSCam Titel, Autor, Version
            # Auch hier text-align: center nutzen
            html.append(
                f'<div style="margin:0; text-align: center;">'
                f'<span style="font-family:{F_EMOJI}; font-size:32pt;">🚀</span> '
                f"<span style=\"color:#FF0419; font-family:'Arial Black','Segoe UI Black',sans-serif; font-size:32pt; font-weight:bold;\">OSCam Emu Patch Generator</span>"
                f"</div>"
            )

            html.append(
                f"<div style=\"font-size:{S_AV_SIZE}; font-family:'Arial Black','Segoe UI Black',sans-serif; font-weight:bold; margin:1px 0; text-align: center;\">"
                f'<span style="color:{C_AV_LABEL_AUTOR};">{T["autor"]}:</span> <span style="color:{C_AV_VALUE_AUTOR};">speedy005</span> | '
                f'<span style="color:{C_AV_LABEL_VER};">{T["version"]}:</span> <span style="color:{C_AV_VALUE_VER};">{app_ver}</span>'
                f"</div>"
            )

            html.append(
                f'<div style="border-top:1px solid {C_LINE}; margin:3px 0;"></div>'
            )

            # Features
            html.append(
                f'<div style="color:{C_ORANGE}; font-size:{S_HEADER}; margin:0; font-family:\'Arial Black\',\'Segoe UI Black\',sans-serif; font-weight:bold;"><b>{T["features_head"]}</b></div>'
                f"<div style=\"font-size:{S_FEAT}; font-family:'Arial Black','Segoe UI Black',sans-serif; font-weight:bold; line-height:1.1; margin-left:5px;\">"
                f'➤ <span style="color:{C_GREEN};">Auto-Patching:</span> <span style="color:{C_BLUE};">{T["feat_1"]}</span><br>'
                f'➤ <span style="color:{C_GREEN};">Online-Laden:</span> <span style="color:{C_BLUE};">{T["feat_2"]}</span><br>'
                f'➤ <span style="color:{C_GREEN};">Lokalisierung:</span> <span style="color:{C_BLUE};">{T["feat_3"]}</span><br>'
                f'➤ <span style="color:{C_GREEN};">Smart Logging:</span> <span style="color:{C_BLUE};">{T["feat_4"]}</span>'
                f"</div>"
            )

            html.append(
                f'<div style="border-top:1px solid {C_LINE}; margin:3px 0;"></div>'
            )

            # Startzeit
            html.append(
                f'<div style="margin:0;">'
                f'<span style="font-family:{F_EMOJI}; font-size:26pt; display:inline-block; width:42px;">⏳</span> '
                f'<span style="color:{C_START_TEXT}; font-family:\'Arial Black\',\'Segoe UI Black\',sans-serif; font-size:{S_NORM}; font-weight:bold;">{T["start"]}</span> '
                f"<span style=\"color:{C_START_TIME}; font-family:'Arial Black','Segoe UI Black',sans-serif; font-size:{S_NORM}; font-weight:bold;\">[{timestamp}]</span>"
                f"</div>"
            )

            if pbar:
                pbar.setValue(15)

            # System Infos
            l_icon = "🇩🇪" if is_de else "🇬🇧"
            html.append(
                make_safe_row(l_icon, T["lang_label"], T["lang_name"], C_GREEN, C_BLUE)
            )
            html.append(
                make_safe_row(
                    "💻",
                    T["kernel"],
                    f"{platform.system()} {platform.release()}",
                    C_GREEN,
                    C_BLUE,
                )
            )
            if pbar:
                pbar.setValue(30)

            # Tools prüfen
            for t in ["git", "patch", "zip"]:
                path = shutil.which(t)
                if path:
                    try:
                        info_raw = subprocess.getoutput(f"{t} --version").strip()
                        version = "unbekannt"
                        for line in info_raw.splitlines():
                            match = re.search(r"\d+(?:\.\d+)+|\d+", line)
                            if match:
                                version = match.group(0)
                            break
                        info = f"Version {version}"
                        ok = True
                    except Exception:
                        info = path
                        ok = True
                else:
                    info = "nicht gefunden"
                    ok = False
                html.append(
                    make_safe_row(
                        "✅" if ok else "❌",
                        t.capitalize(),
                        f"{'OK' if ok else 'FEHLT'} – {info}",
                        C_GREEN if ok else C_RED,
                        C_BLUE if ok else C_RED,
                    )
                )

            if pbar:
                pbar.setValue(45)

            # Python Pakete prüfen
            for pkg in ["PyQt6", "requests"]:
                spec = importlib.util.find_spec(pkg)
                ok = spec is not None
                if ok:
                    try:
                        module = importlib.import_module(pkg)
                        version = (
                            getattr(module, "__version__", "unknown")
                            if pkg != "PyQt6"
                            else __import__("PyQt6").QtCore.QT_VERSION_STR
                        )
                    except:
                        version = "unknown"
                    status_text = f"OK – {version}"
                else:
                    status_text = "FEHLT"
                html.append(
                    make_safe_row(
                        "📦" if ok else "❌",
                        pkg.capitalize(),
                        status_text,
                        C_GREEN if ok else C_RED,
                        C_BLUE if ok else C_RED,
                    )
                )

            if pbar:
                pbar.setValue(55)

            # Netzwerkstatus prüfen
            try:
                start_p = time.perf_counter()
                s = socket.create_connection(("8.8.8.8", 53), timeout=1.5)
                ping_ms = int((time.perf_counter() - start_p) * 1000)
                local_ip = s.getsockname()[0]
                s.close()
                network_status = T["online"]
                p_color = (
                    C_GREEN if ping_ms < 100 else (C_YELLOW if ping_ms < 250 else C_RED)
                )
            except:
                network_status = T["offline"]
                local_ip = "-"
                ping_ms = 0
                p_color = C_RED

            html.append(
                make_safe_row(
                    "🌐",
                    T["network"],
                    f"{network_status} : <span style='color:red;'>{local_ip}</span>",
                    C_GREEN if network_status == T["online"] else C_RED,
                    C_BLUE,
                )
            )
            html.append(
                make_safe_row(
                    "⚡",
                    T["ping"],
                    f"{ping_ms} ms",
                    C_GREEN if network_status == T["online"] else C_RED,
                    p_color,
                )
            )

            if pbar:
                pbar.setValue(65)

            # Repos prüfen
            repo_list = [
                ("📡", "Streamboard Oscam", "git.streamboard.tv"),
                ("🐙", "OSCam Emu Mirror", "github.com"),
                ("⭐", "speedy Oscam Emu", "github.com"),
                ("🔗", "GitHub API Server", "api.github.com"),
            ]
            for i, (icon, r_name, host) in enumerate(repo_list):
                try:
                    socket.gethostbyname(host)
                    html.append(
                        make_safe_row(
                            icon, r_name, T["online"], C_REPO_NAME, C_REPO_VAL, S_REPO
                        )
                    )
                except Exception as e:
                    print(f"Host {host} konnte nicht erreicht werden: {e}")
                    html.append(
                        make_safe_row(icon, r_name, T["offline"], C_RED, C_RED, S_REPO)
                    )
                if pbar:
                    pbar.setValue(70 + (i + 1) * 2)

            # --- TOOL STATISTIK ---
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            total_stats = 0
            git_count = 0
            repo = "speedy005/Oscam-Emu-patch-Manager"
            headers = {"User-Agent": "Python-Requests"}
            try:
                res = requests.get(
                    f"https://api.github.com/repos/{repo}/releases",
                    headers=headers,
                    timeout=10,
                )
                if res.status_code == 200:
                    releases = res.json()
                    for release in releases:
                        for asset in release.get("assets", []):
                            git_count += int(asset.get("download_count", 0))
            except Exception as e:
                print(f"DEBUG: GitHub Exception: {e}")

            # Lokaler Counter
            try:
                tool_dir = os.path.dirname(os.path.abspath(__file__))
            except NameError:
                tool_dir = os.getcwd()

            counter_file = os.path.join(tool_dir, "install_counter.txt")
            if not os.path.exists(counter_file) or os.stat(counter_file).st_size == 0:
                with open(counter_file, "w") as f:
                    f.write("0")

            with open(counter_file, "r") as f:
                try:
                    install_count = int(f.read().strip())
                except:
                    install_count = 0

            install_count += 1
            with open(counter_file, "w") as f:
                f.write(str(install_count))

            total_stats += install_count
            usage_count = str(total_stats)
            if pbar:
                pbar.setValue(85)
            # Statistik HTML
            current_lang = getattr(
                self, "LANG", self.cfg.get("language", "EN").lower()
            ).lower()
            T = TEXTS.get(
                current_lang, TEXTS["en"]
            )  # <-- HIER: current_lang statt LANG benutzen!

            html.append(
                f'<div style="border:2px solid #FF0419; border-radius:20px; padding:25px; margin-top:20px; '
                f'background:transparent; text-align:center; font-family:sans-serif;">'
                f'<div style="font-size:28pt; font-weight:bold; margin-bottom:20px;">'
                f"<span style=\"font-family:'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji',sans-serif;\">📊</span> "
                f'<span style="color:#FF0419;">{T.get("stats_title", "STATISTICS")}</span>'
                f"</div>"
                f'<div style="font-size:24pt; margin:10px 0;">'
                f"<span style=\"font-family:'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji',sans-serif;\">🐙</span> "
                f'<span style="color:#00FF00; font-weight:bold;">{T.get("stats_github", "GitHub:")}</span> '
                f'<span style="color:{C_BLUE}; font-weight:bold;">{git_count}</span>'
                f"</div>"
                f'<div style="font-size:24pt; margin:10px 0;">'
                f"<span style=\"font-family:'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji',sans-serif;\">💾</span> "
                f'<span style="color:#F57A08; font-weight:bold;">{T.get("stats_local", "Local:")}</span> '
                f'<span style="color:{C_BLUE}; font-weight:bold;">{install_count}</span>'
                f"</div>"
                f'<div style="height:1px; background:#444; margin:15px auto; width:60%;"></div>'
                f'<div style="font-size:26pt; font-weight:bold;">'
                f"<span style=\"font-family:'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji',sans-serif;\">📊</span> "
                f'<span style="color:#FFFF00;">{T.get("stats_total", "Total:")}</span> '  # <--- HIER WAR DER FEHLER
                f'<span style="color:{C_BLUE}; font-weight:900;">{usage_count}</span>'
                f"</div>"
                f"</div>"
            )

            # Footer
            html.append(
                f'<div style="border-top:1px solid {C_LINE}; margin:3px 0;"></div>'
            )
            footer_html = (
                f'<div style="white-space: nowrap; margin: 0; padding: 0; line-height: 1.0; text-align: center;">'
                f'<span style="font-family:{F_EMOJI}; font-size:{S_EMOJI};">✅ </span>'
                f'<span style="font-family:{F_MONO}; font-size:{S_FOOTER}; color:{C_GREEN};"><b>{T["foot_ok"]}&nbsp;</b></span>'
                f'<span style="font-family:{F_MONO}; font-size:{S_FOOTER}; color:{C_BLUE};"><b>{T["foot_ready"]}</b></span>'
                f"</div>"
            )
            html.append(footer_html)
            html.append("</div>")

            widget.setHtml("".join(html))
            widget.moveCursor(QTextCursor.MoveOperation.End)

            if pbar:
                pbar.setValue(90)

        except Exception as e:
            if widget:
                widget.append(f"<br><b style='color:red;'>Check Error: {e}</b>")

        finally:
            self.is_loading = False
            self._checking_active = False
            if pbar:
                pbar.setValue(100)
            QApplication.processEvents()

        # =====================
        # INIT UI
        # =====================

    def init_ui(self):
        from PyQt6.QtWidgets import (
            QVBoxLayout,
            QHBoxLayout,
            QGridLayout,
            QLabel,
            QPushButton,
            QWidget,
            QTextEdit,
            QComboBox,
            QSpinBox,
            QProgressBar,
            QApplication,
            QFrame,
            QFileDialog,
        )
        from PyQt6.QtGui import QPixmap, QFont
        from PyQt6.QtCore import Qt, QSize, QTimer, QDateTime
        import subprocess
        import os
        import requests

        # ---------------------------------------------------------
        # 1. Grundwerte & Hauptlayout
        # ---------------------------------------------------------
        self.TITLE_HEIGHT = 35
        self.BUTTON_HEIGHT = 35
        self.BUTTON_RADIUS = 10

        B_HEIGHT = self.BUTTON_HEIGHT
        B_WIDTH = 240
        CONTROL_HEIGHT = self.BUTTON_HEIGHT

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(5, 0, 20, 10)
        self.setStyleSheet("background-color: #2F2F2F;")

        # ---------------------------------------------------------
        # Header-Bereich
        # ---------------------------------------------------------
        header_widget = QFrame()
        header_widget.setMinimumHeight(110)
        header_widget.setStyleSheet(
            """
            QFrame { background-color: #2F2F2F; border: 1px solid #444; border-radius: 10px; }
            QLabel { background-color: transparent; border: none; font-weight: bold; }
            QPushButton {
                color: #EAFF00 !important;
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4d4d4d; border: 1px solid #EAFF00; color: white !important; }
        """
        )

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 5, 15, 5)
        header_layout.setSpacing(10)

        # --- LEFT: Info + Uhr/Daten ---
        left_header_container = QWidget()
        left_header_layout = QHBoxLayout(left_header_container)
        left_header_layout.setContentsMargins(0, 0, 0, 0)
        left_header_layout.setSpacing(10)

        self.info_button = QPushButton()
        self.info_button.setFixedSize(45, 45)
        icon_info = self.style().standardIcon(
            QApplication.style().StandardPixmap.SP_MessageBoxInformation
        )
        self.info_button.setIcon(icon_info)
        self.info_button.setIconSize(QSize(28, 28))
        self.info_button.clicked.connect(self.show_info)
        left_header_layout.addWidget(self.info_button)

        time_date_container = QWidget()
        main_h_layout = QHBoxLayout(time_date_container)
        main_h_layout.setContentsMargins(5, 0, 0, 0)
        main_h_layout.setSpacing(15)

        self.analog_clock = AnalogClock()
        self.analog_clock.setFixedSize(80, 80)
        main_h_layout.addWidget(self.analog_clock)

        labels_v_container = QWidget()
        labels_v_layout = QVBoxLayout(labels_v_container)
        labels_v_layout.setContentsMargins(0, 0, 0, 0)
        labels_v_layout.setSpacing(0)

        bold_font_time = QFont("Segoe UI", 22, QFont.Weight.Bold)
        bold_font_date = QFont("Segoe UI", 24, QFont.Weight.Bold)

        # self.digital_clock = QLabel("--:--:--")
        # self.digital_clock.setFont(bold_font_time)
        # self.digital_clock.setStyleSheet("color: red;")
        # labels_v_layout.addWidget(self.digital_clock)

        self.date_label = QLabel("--.--.----")
        self.date_label.setFont(bold_font_date)
        self.date_label.setStyleSheet("color: orange;")
        labels_v_layout.addWidget(self.date_label)

        main_h_layout.addWidget(labels_v_container)
        left_header_layout.addWidget(time_date_container)
        header_layout.addWidget(left_header_container, 1)

        # --- MIDDLE: Logo ---
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setMinimumWidth(300)
        header_layout.addWidget(self.logo_label, 2)

        try:
            url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/oscam_emu_toolkit2.png"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            self.original_pixmap = QPixmap()
            self.original_pixmap.loadFromData(resp.content)
            self.update_logo(width=300, height=35)
        except Exception:
            self.logo_label.setText("OSCAM TOOLKIT")
            self.logo_label.setStyleSheet("color: white; font-size: 18px;")
            self.original_pixmap = None

        # --- RIGHT: Log-Button + Version & Autor (OPTIMIERT) ---
        right_header_container = QWidget()
        right_header_layout = QHBoxLayout(right_header_container)
        right_header_layout.setContentsMargins(0, 0, 0, 0)
        right_header_layout.setSpacing(15)
        right_header_layout.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )

        # 1. Log-Button
        lang = getattr(self, "LANG", "de").lower()
        log_text = "Log speichern" if lang == "de" else "Save Log"
        self.log_button = QPushButton(f" {log_text}")
        self.log_button.setMinimumHeight(45)
        self.log_button.setMinimumWidth(150)
        self.log_button.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        icon_log = self.style().standardIcon(
            QApplication.style().StandardPixmap.SP_DriveHDIcon
        )
        self.log_button.setIcon(icon_log)
        if hasattr(self, "export_log"):
            self.log_button.clicked.connect(self.export_log)
        right_header_layout.addWidget(self.log_button)

        # 2. Stats Checkbox (VOLLSTÄNDIG MIT FUNKTION)
        self.telemetry_cb = QCheckBox("Stats")

        # FUNKTION WIEDERHERSTELLEN:
        self.telemetry_cb.setChecked(get_setting("allow_telemetry", True))
        self.telemetry_cb.stateChanged.connect(self.on_telemetry_changed)

        # Tooltip & Cursor
        is_de = getattr(self, "LANG", "de") == "de"
        self.telemetry_cb.setToolTip(
            "Anonyme Nutzungsstatistik (Hit-Counter) erlauben/verbieten."
            if is_de
            else "Allow/Disallow anonymous usage statistics (Hit-Counter)."
        )
        self.telemetry_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.telemetry_cb.setMinimumHeight(35)
        self.telemetry_cb.setMinimumWidth(90)
        self.telemetry_cb.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        # Akzentfarbe für Hover-Effekt (z.B. Rot oder Gelb)
        accent = (
            "#FF0000"  # Hier kannst du deine Wunschfarbe für den Hover-Effekt setzen
        )

        # STYLE (Wieder eingefügt)
        self.telemetry_cb.setStyleSheet(
            f"""
            QCheckBox {{
                color: white;
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                padding-left: 8px;
                padding-right: 5px;
            }}
            QCheckBox:hover {{
                background-color: {accent};
                border: 1px solid white;
                color: white !important;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid white;
                border-radius: 2px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: white;
                border: 1px solid white;
            }}
        """
        )

        right_header_layout.addWidget(self.telemetry_cb)

        # Fonts definieren, BEVOR sie benutzt werden (löst NameError)
        bold_font_header = QFont("Segoe UI", 24, QFont.Weight.Bold)
        bold_font_version = QFont("Segoe UI", 22, QFont.Weight.Bold)

        # Container für die Labels rechts oben
        version_text_container = QWidget()
        version_text_layout = QVBoxLayout(version_text_container)
        version_text_layout.setContentsMargins(10, 0, 15, 0)
        version_text_layout.setSpacing(2)
        version_text_layout.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )

        # Farben und Version holen
        current_diff_colors = getattr(self, "current_diff_colors", {"fg": "#FF0000"})
        text_color = current_diff_colors.get("fg", "#EAFF00")
        app_v = getattr(self, "APP_VERSION", globals().get("APP_VERSION", "4.0.0"))

        # Das Haupt-Versionslabel (Das farbige)
        # WICHTIG: Wir weisen es self.version_label zu, damit es später aktualisierbar ist
        self.version_label = QLabel(f"v{app_v}")
        self.version_label.setFont(bold_font_version)
        self.version_label.setStyleSheet(
            f"color: {text_color}; background: transparent; margin-bottom: 5px;"
        )

        # Autor Label (Blau im Screenshot)
        self.by_label = QLabel("by speedy005")
        self.by_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.by_label.setStyleSheet("color: #0055ff; background: transparent;")

        # In den kleinen Container packen
        version_text_layout.addWidget(self.version_label)
        version_text_layout.addWidget(self.by_label)

        # Den Container zum Header-Layout hinzufügen
        right_header_layout.addWidget(version_text_container)

        # Zum Haupt-Header hinzufügen
        header_layout.addWidget(right_header_container, 1)

        main_layout.addWidget(header_widget)
        self.apply_global_button_style("#EAFF00")
        # ---------------------------------------------------------
        # INFO + PROGRESS
        # ---------------------------------------------------------
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFont(QFont("Consolas", 12))
        self.info_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #000000;
                color: #FFFFFF;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """
        )
        main_layout.addWidget(self.info_text, 10)

        # --- AUTO-SCROLL LOGIK HIER EINFÜGEN ---
        # Timer erstellen, der alle 50 Millisekunden feuert
        self.scroll_timer = QTimer(self)

        def auto_scroll():
            v_bar = self.info_text.verticalScrollBar()
            # Nur scrollen, wenn wir noch nicht am Ende sind
            if v_bar.value() < v_bar.maximum():
                v_bar.setValue(v_bar.value() + 1)  # +1 ist ein sanfter Schritt
            else:
                # Optional: Stoppen, wenn Ende erreicht
                # self.scroll_timer.stop()
                pass

        self.scroll_timer.timeout.connect(auto_scroll)
        self.scroll_timer.start(50)  # Intervall in ms (kleiner = schneller)
        # ---------------------------------------

        main_layout.addSpacing(12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(35)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setStyleSheet(
            """
        QProgressBar {
            border: 1px solid #444;
            border-radius: 8px;
            background-color: #1A1A1A;
            color: white;
            text-align: center;
            font-weight: bold;
            font-size: 14px;
        }
        QProgressBar::chunk {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 #F37804, stop:1 #FFD700);
            border-radius: 8px;
        }
        """
        )
        main_layout.addWidget(self.progress_bar)
        self.pbar_idle()
        # ---------------------------------------------------------
        # STATUS-BAR (MAXIMALER AUSBAU: GROSSE ANZEIGEN & ZIP)
        # ---------------------------------------------------------
        status_bar_container = QFrame()
        status_bar_container.setFixedHeight(55)
        status_bar_container.setStyleSheet(
            "QFrame { background-color: rgba(0,0,0,0.4); border: 1px solid #444; border-radius: 10px; }"
        )

        status_bar_layout = QHBoxLayout(status_bar_container)
        status_bar_layout.setContentsMargins(15, 0, 15, 0)
        status_bar_layout.setSpacing(12)

        # FIX 1: Feste Breite und statische Attribute verhindern das "Zucken" des Textes
        self.status_info_label = QLabel("SYSTEM STATUS:")
        self.status_info_label.setFixedWidth(180)  # Reserviert festen Platz
        self.status_info_label.setAttribute(Qt.WidgetAttribute.WA_StaticContents)
        self.status_info_label.setStyleSheet(
            "color: #FF0000; font-size: 22px; font-weight: bold; border: none; background: transparent;"
        )
        status_bar_layout.addWidget(self.status_info_label)

        # Listen-Trennung für Stabilität
        self.status_leds = []  # Bleiben immer statisch (Grün/Rot)
        self.user_leds = []  # Nur für Slider-Blinken

        tools_to_check = [
            "py",
            "qt6",
            "snd",
            "git",
            "patch",
            "zip",
            "gcc",
            "make",
            "ssl",
            "usb",
        ]
        label_colors = {
            "py": "#3776AB",
            "qt6": "#41CD52",
            "snd": "#FF0000",
            "git": "#2ecc71",
            "patch": "#3498db",
            "zip": "#E24A39",
            "gcc": "#f1c40f",
            "make": "#e67e22",
            "ssl": "#9b59b6",
            "usb": "#1abc9c",
        }

        for tool in tools_to_check:
            exists = False
            display_name = tool.upper()

            # --- SYSTEM CHECK ---
            if tool == "py":
                exists = True
                display_name = f"PY {sys.version_info.major}.{sys.version_info.minor}"
            elif tool == "qt6":
                exists = importlib.util.find_spec("PyQt6") is not None
            elif tool == "snd":
                exists = (
                    any(shutil.which(c) for c in ["paplay", "pw-play", "aplay"])
                    or platform.system() == "Windows"
                )
                display_name = "SOUND"
            elif tool in ["ssl", "usb"]:
                if platform.system() == "Linux" and shutil.which("dpkg"):
                    pkg = "libssl-dev" if tool == "ssl" else "libusb-1.0-0-dev"
                    exists = (
                        subprocess.run(
                            ["dpkg-query", "-W", "-f='${Status}'", pkg],
                            capture_output=True,
                            text=True,
                        ).returncode
                        == 0
                    )
                else:
                    exists = True
            else:
                exists = shutil.which(tool) is not None

            # Tool Container
            t_widget = QWidget()
            # FIX 2: Feste Breite für Container verhindert Layout-Verschiebungen in der Zeile
            t_widget.setMinimumWidth(80)
            t_lay = QHBoxLayout(t_widget)
            t_lay.setContentsMargins(0, 0, 0, 0)
            t_lay.setSpacing(6)

            # SYSTEM LED (Wird nur EINMAL gefärbt)
            led = QLabel()
            led.setFixedSize(16, 16)
            led.tool_exists = exists
            led.base_color = "#27ae60" if exists else "#c0392b"
            led.setStyleSheet(
                f"background-color: {led.base_color}; border-radius: 8px; border: 2px solid #555;"
            )
            led.setCursor(Qt.CursorShape.PointingHandCursor)
            led.mousePressEvent = lambda e, t=tool: self.show_tool_help(t)

            self.status_leds.append(led)

            # Text
            c = label_colors.get(tool, "#FFF")
            lbl = QLabel(display_name)
            lbl.setStyleSheet(
                f"color: {c}; font-size: 20px; font-weight: bold; font-family: 'Segoe UI';"
            )

            t_lay.addWidget(led)
            t_lay.addWidget(lbl)
            status_bar_layout.addWidget(t_widget)

        status_bar_layout.addStretch()

        # ---------------------------------------------------------
        # USER-LED entfernt (Punkt gelöscht)
        self.user_leds = []

        # ---------------------------------------------------------
        # SPEED REGLER
        # ---------------------------------------------------------
        speed_icon = QLabel("⚡")
        speed_icon.setStyleSheet(
            "font-size: 20px; border: none; background: transparent;"
        )
        status_bar_layout.addWidget(speed_icon)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setFixedWidth(110)
        self.slider_speed.setRange(50, 1000)
        self.slider_speed.setInvertedAppearance(True)

        current_speed = self.current_config.get("blink_speed", 500)
        self.slider_speed.setValue(current_speed)
        self.slider_speed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_speed.setStyleSheet(
            "QSlider::groove:horizontal { border: 1px solid #666; height: 6px; background: #222; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #F37804; border: 1px solid #444; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }"
        )

        if hasattr(self, "update_blink_speed"):
            self.slider_speed.valueChanged.connect(self.update_blink_speed)

        status_bar_layout.addWidget(self.slider_speed)

        self.lbl_speed_val = QLabel("")
        self.lbl_speed_val.setStyleSheet(
            "color: #aaa; font-size: 12px; font-weight: bold; border: none;"
        )
        self.lbl_speed_val.setFixedWidth(55)
        status_bar_layout.addWidget(self.lbl_speed_val)

        # ---------------------------------------------------------
        # BUTTONS
        # ---------------------------------------------------------
        self.btn_matrix = QPushButton("📟 MATRIX MODE")
        self.btn_matrix.setFixedSize(130, 35)
        self.btn_matrix.setStyleSheet(
            "QPushButton { background-color: #000; color: #00FF41; border: 1px solid #008F11; border-radius: 6px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #008F11; color: black; }"
        )
        if hasattr(self, "toggle_matrix"):
            self.btn_matrix.clicked.connect(self.toggle_matrix)
        status_bar_layout.addWidget(self.btn_matrix)

        self.btn_theme = QPushButton("🌓 THEME")
        self.btn_theme.setFixedSize(100, 35)
        self.btn_theme.setStyleSheet(
            "QPushButton { background-color: #444; color: red; border: 1px solid #666; border-radius: 6px; font-size: 18px; font-weight: bold; } QPushButton:hover { background-color: #555; border: 1px solid #F37804; }"
        )
        self.btn_theme.clicked.connect(self.toggle_theme)
        status_bar_layout.addWidget(self.btn_theme)

        main_layout.addWidget(status_bar_container)

        # --- ANIMATIONS-TIMER STARTEN ---
        self._blink_state = True
        self.master_timer = QTimer(self)
        self.master_timer.timeout.connect(self.animate_everything)
        self.master_timer.start(500)  # 500ms Takt für das Blinken
        # ---------------------------------------------------------
        # KONTROLL-BLOCK MIT HEADER
        # ---------------------------------------------------------

        controls_group = QFrame()
        # FIX: Wir setzen eine feste Mindesthöhe für den gesamten Block,
        # damit er beim Start nicht zusammenfällt.
        controls_group.setMinimumHeight(150)

        controls_group.setStyleSheet(
            f"""
        QFrame {{
            border: 1px solid #bbb;
            border-radius: 10px;
            background-color: #2F2F2F;
        }}
        /* FIX: Wir erzwingen hier im Stylesheet, dass alle Buttons 
           im Kasten sofort ihre Zielhöhe einnehmen */
        QPushButton {{
            min-height: {self.BUTTON_HEIGHT}px;
            max-height: {self.BUTTON_HEIGHT}px;
        }}
        """
        )
        controls_group_layout = QVBoxLayout(controls_group)

        # OPTIMIERUNG: Mehr Abstand nach oben (20) und unten (20) macht den Kasten höher
        controls_group_layout.setContentsMargins(0, 20, 15, 20)
        # Mehr Abstand zwischen Header und den Reglern
        controls_group_layout.setSpacing(0)

        translated_text = self.get_t("settings_header", "Einstellungen")
        self.controls_header = QLabel(translated_text)

        self.controls_header.setMinimumWidth(220)
        # OPTIMIERUNG: Header-Höhe von 28 auf 45 erhöht für mehr Präsenz
        self.controls_header.setMinimumHeight(35)
        self.controls_header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bg = current_diff_colors.get("bg", "#2F2F2F")  # Dunkelgrauer Hintergrund
        fg = current_diff_colors.get("fg", "#EAFF00")  # NEONGELBE SCHRIFT

        self.controls_header.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                font-size: 20px;          /* Schrift im Header vergrößert */
                font-weight: bold;
                padding-left: 15px;
                padding-right: 15px;
                border-radius: 8px;
            }}
            """
        )

        controls_group_layout.addWidget(
            self.controls_header, alignment=Qt.AlignmentFlag.AlignLeft
        )

        controls_row = QWidget()
        controls_layout = QHBoxLayout(controls_row)
        # OPTIMIERUNG: Auch hier mehr Innenabstand für die Zeile
        controls_layout.setContentsMargins(0, 0, 5, 5)
        controls_layout.setSpacing(0)

        # Nutze hier deine neue B_HEIGHT (z.B. 60), falls definiert, sonst BUTTON_HEIGHT
        CONTROL_HEIGHT = getattr(self, "B_HEIGHT", 35)
        controls_layout.addStretch(0)
        control_style = f"""
        QComboBox, QSpinBox {{
            font-size: 18px;
            border-radius: {self.BUTTON_RADIUS}px;
            border: 2px solid #555;
            padding: 4px 8px;
            color: white;
            background-color: #444;
            height: {CONTROL_HEIGHT}px;
            margin-left: -2px;   /* Schiebt die Box näher an den Doppelpunkt des Labels */
        }}
        """

        def make_label(text):
            lbl = QLabel(text)
            lbl.setMinimumHeight(CONTROL_HEIGHT)

            # FIX: Von 85 auf 65 verringert, damit die Boxen näher am Wort kleben
            lbl.setFixedWidth(65)

            lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            lbl.setStyleSheet(
                f"""
                color: {fg}; 
                font-weight: bold; 
                font-size: 18px;
                background: transparent;
                padding-left: 0px;
            """
            )
            return lbl

        # --- 1. Sprache-Dropdown (Kompakt) ---
        self.lang_label = make_label(self.get_t("language_label", "Sprache:"))
        self.lang_label.setFixedWidth(85)  # Platz für "Sprache:" ohne Lücke

        self.language_box = QComboBox()
        self.language_box.addItems(["EN", "DE"])
        self.language_box.setFixedSize(80, B_HEIGHT)
        self.language_box.setStyleSheet(
            f"""
            QComboBox {{
                background-color: #444444; color: white; font-weight: bold; font-size: 20px;
                border: 2px solid #555555; border-radius: 6px; padding-left: 5px;
            }}
            QComboBox::drop-down {{ border: none; width: 0px; }}
            QComboBox::down-arrow {{
                image: none; border-left: 5px solid transparent; border-right: 5px solid transparent;
                border-top: 5px solid #FF0000;
            }}
        """
        )

        # Sprach-Logik (Einmalig)
        saved_lang = self.cfg.get("language", "de").lower()
        (
            self.language_box.setCurrentIndex(0)
            if saved_lang == "en"
            else self.language_box.setCurrentIndex(1)
        )
        self.language_box.currentIndexChanged.connect(self.change_language)

        # --- 2. Farbe/Style (Kompakt) ---
        self.color_label = make_label(self.get_t("color_label", "Farbe:"))
        self.color_label.setFixedWidth(150)
        self.color_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.color_box = QComboBox()
        self.color_box.addItems(list(DIFF_COLORS.keys()))
        saved_color = self.cfg.get("theme_color", "Classics")
        index = self.color_box.findText(saved_color)
        self.color_box.setCurrentIndex(index if index >= 0 else 0)
        self.color_box.setFixedSize(150, CONTROL_HEIGHT)
        self.color_box.setStyleSheet(control_style)
        self.color_box.currentIndexChanged.connect(self.change_colors)

        # --- 3. Commits (Kompakt) ---
        self.commit_label = make_label(self.get_t("commit_count_label", "Commits:"))

        # Breite festlegen (sizeHint + Puffer)
        self.commit_label.setFixedWidth(self.commit_label.sizeHint().width() + 10)

        # HÖHE festlegen (z.B. 35 Pixel, passend zu deinen CONTROL_HEIGHT Werten)
        self.commit_label.setFixedSize(140, 35)

        self.commit_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1, 20)
        self.commit_spin.setFixedSize(75, CONTROL_HEIGHT)
        self.commit_spin.setValue(self.cfg.get("commit_count", 10))
        self.commit_spin.valueChanged.connect(self.commit_value_changed)

        self.commit_spin.setStyleSheet(
            """
            QSpinBox {
                background-color: #222222; color: #FFFFFF; font-size: 20px; font-weight: bold;
                border: 2px solid #555555; border-radius: 6px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #333333; width: 25px; border-left: 1px solid #555555;
            }
            QSpinBox::up-arrow { border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 6px solid #FF0000; }
            QSpinBox::down-arrow { border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 6px solid #FF0000; }
        """
        )

        saved_commits = self.cfg.get("commit_count", 10)
        self.commit_spin.setValue(saved_commits)
        self.commit_spin.valueChanged.connect(self.commit_value_changed)

        self.btn_check_tools = QPushButton(
            self.get_t("check_tools_button", "🛠️ Tools prüfen")
        )
        self.btn_check_tools.setFixedSize(220, 35)

        # --- 0. Container Erstellung (Korrektur: QGroupBox statt QFrame) ---
        controls_group = QGroupBox("")
        controls_group_layout = QVBoxLayout(controls_group)

        # Stylesheet: Macht den Kasten extrem flach und rückt den Titel bündig
        controls_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 8px;
                margin-top: 10px; 
                background-color: transparent;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 3px;
                color: #00FF00;
            }
        """
        )
        # Erzwingt eine geringe Höhe für den gesamten Block
        # controls_group.setMaximumHeight(140)

        button_style = """
            QPushButton {
                background-color: #444444;
                color: white;
                font-weight: bold; 
                font-size: 24px;          /* Ein kleiner Schritt zurück auf 28px wirkt oft Wunder */
                font-family: sans-serif;
                
                border-radius: 6px;
                border: 3px solid #555555;

                /* ZENTRIERUNG ERZWINGEN */
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover { 
                background-color: #333333; 
                color: #FFD700; 
                border: 3px solid #FFD700;
            }
        """
        # --- Deine neuen Maße (Jetzt auch im Code genutzt!) ---
        B_WIDTH = 170
        B_HEIGHT = 35
        I_SIZE = 25

        # --- 2. Ordner-Buttons (Mit korrekter Höhe und Icon-Größe) ---
        f_icon = self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon)

        # --- 2. Ordner-Buttons (Oben) ---
        f_icon = self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon)

        self.btn_open_work = QPushButton(" Arbeitsordner")
        self.btn_open_work.setIcon(f_icon)
        self.btn_open_work.setIconSize(QSize(I_SIZE, I_SIZE))
        self.btn_open_work.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_open_work.setStyleSheet(button_style)
        self.btn_open_work.clicked.connect(lambda checked=False: self.open_custom_folder(getattr(self, "PLUGIN_DIR", ".")))

        self.btn_open_temp = QPushButton(" Temp-Repo")
        self.btn_open_temp.setIcon(f_icon)
        self.btn_open_temp.setIconSize(QSize(I_SIZE, I_SIZE))
        self.btn_open_temp.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_open_temp.setStyleSheet(button_style)
        self.btn_open_temp.clicked.connect(lambda checked=False: self.open_custom_folder(getattr(self, "TEMP_REPO", ".")))

        self.btn_open_emu = QPushButton(" Emu-Git")
        self.btn_open_emu.setIcon(f_icon)
        self.btn_open_emu.setIconSize(QSize(I_SIZE, I_SIZE))
        self.btn_open_emu.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_open_emu.setStyleSheet(button_style)
        self.btn_open_emu.clicked.connect(lambda checked=False: self.open_custom_folder(getattr(self, "PATCH_EMU_GIT_DIR", ".")))

        # --- 3. Funktions-Buttons (Unten) ---
        self.btn_check_tools = QPushButton("🛠️ Tools prüfen")
        self.btn_check_tools.setIconSize(QSize(I_SIZE, I_SIZE))  # Icon-Größe für Emojis
        self.btn_check_tools.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_check_tools.setStyleSheet(button_style)
        self.btn_check_tools.clicked.connect(self.run_full_system_check)

        self.btn_modifier = QPushButton("👤 Patch Autor")
        self.btn_modifier.setIconSize(QSize(I_SIZE, I_SIZE))
        self.btn_modifier.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_modifier.setStyleSheet(button_style)
        self.btn_modifier.clicked.connect(self.change_modifier_name)

        self.btn_repo_url = QPushButton("🌐 Repo URL")
        self.btn_repo_url.setIconSize(QSize(I_SIZE, I_SIZE))
        self.btn_repo_url.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_repo_url.setStyleSheet(button_style)
        self.btn_repo_url.clicked.connect(self.change_emu_repo)

        # --- Konfiguration (kannst du zentral anpassen) ---
        self.font_size_buttons = 12  # Hier die gewünschte Schriftgröße in Pixeln ändern
        current_lang = getattr(self, "lang", "de")  # Erkennt deine gewählte Sprache

        # 1. FARBSCHEMA ERMITTELN (Passend zu deinem toggle_theme)
        is_dark = "#2F2F2F" in self.styleSheet() or not self.styleSheet()

        if is_dark:
            # MATRIX / DARK COLORS (Orange/Gold)
            c1, c2, b_color = "#F37804", "#8B4513", "#444"
        else:
            # LIGHT / SYSTEM COLORS (Blau)
            c1, c2, b_color = "#3498db", "#2980b9", "#1c5980"

        # 2. TEXTE FÜR MEHRSPRACHIGKEIT
        lang = getattr(self, "LANG", "de").lower()
        text_patch_online = "🌐 Patch Online " if lang == "de" else "🌐 Load Patch "

        # 3. BUTTON ERSTELLEN
        self.btn_patch_online = QPushButton(text_patch_online)
        self.btn_patch_online.setFixedSize(B_WIDTH, B_HEIGHT)

        # 4. DYNAMISCHES STYLESHEET (Mit Variablen und Font-Fix 700)
        self.btn_patch_online.setStyleSheet(
            f"""
            QPushButton {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                                  stop:0 {c1}, stop:1 {c2});
                color: white; 
                font-weight: 700; 
                font-size: {self.font_size_buttons}px;
                border: 1px solid {b_color};
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                                  stop:0 {c2}, stop:1 {c1});
                border: 1px solid #ffffff;
            }}
            QPushButton:pressed {{
                background-color: {b_color};
                padding-top: 2px;
                border-radius: 10px;
            }}
        """
        )

        # 5. VERKNÜPFUNG
        if hasattr(self, "handle_online_patch_button"):
            self.btn_patch_online.clicked.connect(self.handle_online_patch_button)

        # --- Bestehender Button: Commit Check ---
        self.btn_check_commit = QPushButton("🔄 Commit Check")
        self.btn_check_commit.setIconSize(QSize(I_SIZE, I_SIZE))
        self.btn_check_commit.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_check_commit.setStyleSheet(button_style)
        self.btn_check_commit.clicked.connect(self.check_for_new_commit)

        # --- 4. GRID-LAYOUT (Header-Fix: Badge 220px, Lücke 5px, Badge 280px, Weißer Text) ---
        from PyQt6.QtWidgets import QFrame

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(10, 0, 10, 10)
        grid_layout.setVerticalSpacing(5)
        grid_layout.setHorizontalSpacing(8)

        # Farben: Basis transparent (Neon weg), Hover nutzt System-Style
        base_bg = "transparent"
        hover_bg = current_diff_colors.get("btn_hover", "#2a4a6a")

        # Haupt-Container (Gesamtbreite: 220 + 5 + 280 = 505px)
        self.header_container = QWidget()
        self.header_container.setFixedSize(950, 45)
        self.header_container.mousePressEvent = self.on_header_clicked

        h_layout = QHBoxLayout(self.header_container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(10)  # EXAKT 5 Pixel Lücke zwischen den Badges

        # --- A) LINKER BADGE (Einstellungen - Länge 220) ---
        self.left_badge = QFrame()
        self.left_badge.setFixedSize(220, 45)
        self.left_badge.setStyleSheet(
            f"""
            QFrame {{
                background-color: {base_bg};
                border: 1px solid #444444;
                border-radius: 6px;
            }}
            QFrame:hover {{
                background-color: {hover_bg};
                border: 1px solid #777777;
            }}
        """
        )

        left_layout = QHBoxLayout(self.left_badge)
        left_layout.setContentsMargins(10, 0, 10, 0)

        # Icon links
        icon_label = QLabel()
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        icon_label.setPixmap(icon.pixmap(20, 20))
        left_layout.addWidget(icon_label)

        # Titel (Zwingend WEISSE Schrift)
        title_text = " Einstellungen" if self.LANG == "de" else " Settings"
        self.header_label = QLabel(title_text)
        self.header_label.setStyleSheet(
            "color: white; font-weight: bold; font-size: 15px; background: transparent; border: none;"
        )
        left_layout.addWidget(self.header_label)
        left_layout.addStretch()
        h_layout.addWidget(self.left_badge)

        # --- B) RECHTER BADGE (OSCam Status - Länge 280) ---
        self.right_badge = QFrame()
        self.right_badge.setFixedSize(750, 35)
        self.right_badge.setStyleSheet(
            f"""
            QFrame {{
                background-color: {base_bg};
                border: 1px solid #444444;
                border-radius: 6px;
            }}
            QFrame:hover {{
                background-color: {hover_bg};
                border: 1px solid #777777;
            }}
        """
        )

        right_layout = QHBoxLayout(self.right_badge)
        right_layout.setContentsMargins(
            10, 0, 10, 0
        )  # Margins setzen, um Platz für Text zu schaffen

        # Status-Label (Zwingend WEISSE Schrift)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color: white; font-weight: bold; font-size: 18px; background: transparent; border: none;"
        )

        # Füge das Label ohne Stretch hin
        right_layout.addWidget(self.status_label)

        # Keine weiteren Strecken mehr erforderlich
        h_layout.addWidget(self.right_badge)

        # --- Integration ins Grid (Zeile 0) ---
        grid_layout.addWidget(self.header_container, 0, 0, 1, 4)

        grid_layout.addWidget(self.btn_open_work, 0, 6)
        grid_layout.addWidget(self.btn_open_temp, 0, 7)
        grid_layout.addWidget(self.btn_open_emu, 0, 8)

        # --- ZEILE 1: Einstellungen ---
        grid_layout.addWidget(self.lang_label, 1, 0)
        self.language_box.setFixedWidth(70)
        grid_layout.addWidget(self.language_box, 1, 1)

        self.color_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        grid_layout.addWidget(self.color_label, 1, 2)
        self.color_box.setFixedWidth(130)
        grid_layout.addWidget(self.color_box, 1, 3)

        self.commit_label.setMinimumWidth(160)
        self.commit_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        grid_layout.addWidget(self.commit_label, 1, 4)

        grid_layout.addWidget(self.commit_spin, 1, 5)
        grid_layout.setColumnStretch(5, 1)

        grid_layout.addWidget(self.btn_patch_online, 0, 9)
        grid_layout.addWidget(self.btn_check_tools, 1, 6)
        grid_layout.addWidget(self.btn_modifier, 1, 7)
        grid_layout.addWidget(self.btn_repo_url, 1, 8)
        grid_layout.addWidget(self.btn_check_commit, 1, 9)

        for btn in [
            self.btn_open_work,
            self.btn_open_temp,
            self.btn_open_emu,
            self.btn_check_tools,
            self.btn_modifier,
            self.btn_repo_url,
            self.btn_check_commit,
        ]:
            btn.setMinimumWidth(145)

        # --- 1. SPALTEN-STRETCH REINIGEN & FIXIEREN ---

        # Zuerst ALLE Spalten auf 0 setzen (kein automatisches Ausdehnen)
        for i in range(grid_layout.columnCount()):
            grid_layout.setColumnStretch(i, 0)

        # DER TRICK: Nur Spalte 6 (die Lücke zwischen Boxen und Buttons) bekommt Stretch 1.
        # Das schiebt alles links (0-5) nach LINKS und alles rechts (7-10) nach RECHTS.
        grid_layout.setColumnStretch(6, 1)

        # --- 2. KOMPAKTHEIT DER BOXEN ERZWINGEN ---
        # Damit die Boxen nicht breiter werden als nötig
        self.language_box.setFixedWidth(70)
        self.color_box.setFixedWidth(130)
        self.commit_spin.setFixedWidth(70)

        # --- 3. LABEL-ABSTÄNDE KORRIGIEREN ---
        # Wir begrenzen die Breite der Labels, damit die Boxen näher am Text kleben
        self.lang_label.setFixedWidth(90)  # Platz für "Sprache:"
        self.color_label.setFixedWidth(65)  # Platz für "Style:"
        self.commit_label.setFixedWidth(145)  # Platz für "Anzahl Commits:"

        # --- 4. FINALE INTEGRATION ---
        # Gitter-Abstände minimieren
        grid_layout.setSpacing(10)

        # Layout zum Kasten hinzufügen
        controls_group_layout.addLayout(grid_layout)
        main_layout.addWidget(controls_group)

        # --- UNTERE SEKTION (Dein restlicher Code) ---
        self.setup_option_buttons(main_layout)
        self.grid_container = QWidget()
        self.layout_grid_buttons = QGridLayout(self.grid_container)
        self.layout_grid_buttons.setSpacing(10)
        self.setup_grid_buttons()
        main_layout.addWidget(self.grid_container)

        # ---------------------------------------------------------
        # TIMER & DIGITAL CLOCK
        # ---------------------------------------------------------
        def update_digital_clock():
            now = QDateTime.currentDateTime()
            # self.digital_clock.setText(now.toString("HH:mm:ss"))
            self.date_label.setText(now.toString("dd.MM.yyyy"))

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(update_digital_clock)
        self.clock_timer.start(1000)
        update_digital_clock()

        # ---------------------------------------------------------
        # FINAL SETTINGS
        # ---------------------------------------------------------
        self.change_colors()
        self.update_language()

        # 2. Fenster-Eigenschaften festlegen
        self.setMinimumSize(1200, 850)
        self.setWindowTitle(
            f"OSCam Toolkit v{APP_VERSION} | {getattr(self, 'patch_modifier', 'speedy005')}"
        )

        # 3. FIX: Initialisierung der Button-Größen erzwingen
        # Wir zeigen das Fenster maximiert und zwingen Qt SOFORT zur Berechnung
        self.showMaximized()
        QApplication.processEvents()  # WICHTIG: Berechnet die 60px Höhe vor dem ersten Klick
        self.updateGeometry()  # Stabilisiert das FlowLayout

        # 4. Signale verbinden
        self.color_box.currentTextChanged.connect(self.collect_and_save)
        self.commit_spin.valueChanged.connect(self.collect_and_save)

        # 5. System-Check mit kleiner Verzögerung starten
        # Wir definieren das Design zentral für ALLE Buttons der App
        neon_style = """
            QPushButton {
                background-color: #3d3d3d !important;
                color: #EAFF00 !important;
                border: 1px solid #555 !important;
                border-radius: 8px !important;
                padding: 5px !important;
                font-weight: bold !important;
                font-size: 12pt !important;
            }
            QPushButton:hover {
                background-color: #4d4d4d !important;
                border: 1px solid #EAFF00 !important;
                color: white !important;
            }
        """

        # --- THEME BEIM START LADEN (Matrix-Check) ---
        # 1. Sicherstellen, dass wir die aktuellsten Daten haben
        # Falls self.current_config noch leer ist, laden wir sie hier kurz manuell
        if not hasattr(self, "current_config") or not self.current_config:
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        self.current_config = json.load(f)
                except:
                    self.current_config = {}

        cfg = getattr(self, "current_config", {})
        saved_theme = cfg.get("theme_mode", "standard")

        # 2. Matrix erzwingen
        if saved_theme == "matrix":
            # Wir setzen is_loading auf True, um Sounds/Logs beim Start zu blockieren
            was_loading = getattr(self, "is_loading", False)
            self.is_loading = True

            # WICHTIG: Erst das normale Stylesheet löschen, dann Matrix setzen
            self.setStyleSheet("")
            self.toggle_matrix(force_state="matrix")

            # Uhr-Update
            if hasattr(self, "analog_clock"):
                self.analog_clock.update()

            self.is_loading = was_loading
        else:
            # Falls nicht Matrix, Standard-Neon setzen
            self.setStyleSheet(self.styleSheet() + neon_style)

    # =====================
    # BUTTON & COLOR HANDLING
    # =====================
    def update_buttons_language(self):
        self.github_upload_patch_button.setText(TEXTS[LANG]["github_upload_patch"])
        self.github_upload_emu_button.setText(TEXTS[LANG]["github_upload_emu"])

    # =====================
    # BUTTON & COLOR HANDLING
    # =====================
    def create_option_button(
        self, key, text, color="#FFFFFF", fg="black", callback=None
    ):
        """
        Erstellt einen stylischen Option-Button für die GUI.
        - key: eindeutiger Button-Key
        - text: Anzeige-Text
        - color: Hintergrundfarbe (Hex)
        - fg: Textfarbe (Hex)
        - callback: Funktion beim Klick, bekommt info_widget + progress_callback übergeben
        """
        btn = QPushButton(text)
        btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(self.BUTTON_HEIGHT)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {color};
                color: {fg};
                border-radius: {self.BUTTON_RADIUS}px;
            }}
            QPushButton:hover {{
                background-color: {self.adjust_color(color, 1.2)};
            }}
            QPushButton:pressed {{
                background-color: {self.adjust_color(color, 0.85)};
            }}
        """
        )

        # Click Event mit info_widget & progress_callback
        if callback:
            btn.clicked.connect(
                lambda checked=False: callback(
                    info_widget=self.info_text, progress_callback=None
                )
            )

        return btn

    def on_header_clicked(self, event):
        """Wird aufgerufen, wenn man auf den blinkenden Balken klickt."""
        if (
            hasattr(self, "pulse_anim")
            and self.pulse_anim.state() == QPropertyAnimation.State.Running
        ):

            # Sofortiges Feedback im Log (Nutzt deine append_info)
            self.append_info("Update-Prozess gestartet...", "info")

            self.pulse_anim.stop()
            if self.header_container.graphicsEffect():
                self.header_container.setGraphicsEffect(None)

            self.header_label.setText(" Aktualisierung läuft...")

            # Start des Pulls
            self.run_git_pull()

    def run_git_pull(self):
        """Führt das Git-Update aus und nutzt die vorhandene append_info Logik."""
        try:
            # Git Pull ausführen und Output abfangen
            process = subprocess.run(
                ["git", "-C", TEMP_REPO, "pull"],
                capture_output=True,
                text=True,
                check=True,
            )

            self.header_label.setText(" System aktuell")

            # Erfolgsmeldung in den Infoscreen (Level 'success' für Grün)
            self.append_info("OSCam Repo wurde erfolgreich aktualisiert!", "success")

            # Falls Git Änderungen meldet, diese als 'white' oder 'raw' anzeigen
            if process.stdout and "Already up to date" not in process.stdout:
                self.append_info(process.stdout.strip(), "white")

        except subprocess.CalledProcessError as e:
            self.header_label.setText(" Update Fehler!")
            # Fehlermeldung in den Infoscreen (Level 'error' für Rot)
            self.append_info(f"Git Fehler: {e.stderr.strip()}", "error")

        except Exception as e:
            self.header_label.setText(" Fehler!")
            self.append_info(f"Unerwarteter Fehler: {str(e)}", "error")

    def log_to_info(self, message, color="white"):
        """Hilfsmethode zum Schreiben in den Infoscreen (QTextEdit)."""
        # Falls dein QTextEdit 'infoscreen' heißt:
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        html_text = f'<span style="color:gray;">[{timestamp}]</span> <span style="color:{color};">{message}</span>'
        self.infoscreen.append(html_text)
        # Automatisch nach unten scrollen
        self.infoscreen.moveCursor(QTextCursor.MoveOperation.End)

    def check_for_new_commit(self):
        import requests
        import re
        from PyQt6.QtWidgets import QMessageBox, QApplication
        from PyQt6.QtCore import QTimer

        # --- 1. Sprache & ProgressBar Setup ---
        lang = getattr(self, "LANG", "de").lower()
        self.TEXT = globals().get("TEXTS", {}).get(lang, {})
        is_de = lang == "de"

        pbar = getattr(self, "progress_bar", None)

        def set_progress(val, text=None):
            if not pbar:
                return
            rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{
                    background-color: {rainbow}; border-radius: 4px;
                }}
                """
            )
            pbar.setValue(val)
            if text:
                pbar.setFormat(text)
            pbar.show()
            QApplication.processEvents()

        def finalize_pbar(text, visible_seconds=3):
            if not pbar:
                return
            rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{
                    background-color: {rainbow}; border-radius: 4px;
                }}
                """
            )
            pbar.setValue(100)
            pbar.setFormat(text)
            QTimer.singleShot(
                visible_seconds * 1000,
                lambda: pbar.setStyleSheet(
                    """
                QProgressBar {
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: orange; font-size: 15pt;
                }
                QProgressBar::chunk {
                    background-color: transparent;
                }
                """
                ),
            )
            QTimer.singleShot(visible_seconds * 1000, lambda: pbar.setValue(0))

        # -------------------------------
        # START
        # -------------------------------
        if pbar:
            set_progress(
                10, "🔍 Prüfe Streamboard..." if is_de else "Checking Streamboard..."
            )

        cyan, end = "<span style='color:cyan;'>", "</span>"
        mb_title = self.TEXT.get("check_commit_title", "OSCam Commit-Check")

        try:
            if pbar:
                set_progress(30)
            url = "https://git.streamboard.tv/common/oscam/-/commits/master"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()

            if pbar:
                set_progress(60)

            # Commit-Hash suchen
            m = re.search(r'data-commit-id="([a-f0-9]{40})"', resp.text)
            if not m:
                m = re.search(r"commit/([a-f0-9]{40})", resp.text)

            if not m:
                safe_play("dialog-error.oga")
                msg = self.TEXT.get(
                    "check_commit_no_hash", "Fehler: Kein Commit-Hash gefunden."
                )
                self.log_message(f"<span style='color:orange;'>⚠️ {msg}</span>")
                QMessageBox.warning(self, mb_title, msg)
                finalize_pbar("❌ Fehler")
                return

            if pbar:
                set_progress(85)

            newest_hash = m.group(1)
            last_known = self.cfg.get("last_stream_commit", "")

            # --- ALLES AKTUELL ---
            if newest_hash == last_known:
                safe_play("dialog-information.oga")
                msg_up = self.TEXT.get(
                    "check_commit_up_to_date", "Kein neuer Commit vorhanden."
                )
                lbl_curr = self.TEXT.get("check_commit_current_hash", "Aktueller Hash:")

                # Log in Info-Box
                self.log_message(f"{cyan}ℹ️ {msg_up} ({newest_hash[:7]}){end}")
                QMessageBox.information(
                    self, mb_title, f"{msg_up}\n\n{lbl_curr} {newest_hash[:8]}"
                )

                if pbar:
                    # Orange-Chunk für „Alles aktuell“
                    pbar.setStyleSheet(
                        """
                        QProgressBar {
                            text-align: center; font-weight: bold; border: 2px solid #222;
                            border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                        }
                        QProgressBar::chunk {
                            background-color: orange; border-radius: 4px;
                        }
                    """
                    )
                    finalize_pbar(f"✅ {msg_up}", visible_seconds=3)

            # --- NEUER COMMIT ---
            else:
                safe_play("complete.oga")
                msg_new = self.TEXT.get(
                    "check_commit_new_found", "Neuer Commit gefunden!"
                )
                lbl_new = self.TEXT.get("check_commit_new_hash", "Neu:")
                lbl_old = self.TEXT.get("check_commit_old_hash", "Alt:")
                self.log_message(f"{cyan}🆕 {msg_new} ({newest_hash[:7]}){end}")
                info_text = f"{msg_new}\n\n{lbl_new} {newest_hash[:8]}\n{lbl_old} {last_known[:8] if last_known else '---'}"
                QMessageBox.information(self, mb_title, info_text)

                # Speichern
                self.cfg["last_stream_commit"] = newest_hash
                if "save_config" in globals():
                    globals()["save_config"](self.cfg, gui_instance=self, silent=True)

                if pbar:
                    finalize_pbar(f"🆕 {msg_new}")

        except Exception as e:
            safe_play("dialog-error.oga")
            err_lbl = self.TEXT.get("check_commit_error", "Fehler beim Check:")
            self.log_message(f"<span style='color:red;'>❌ {err_lbl} {str(e)}</span>")
            QMessageBox.critical(self, mb_title, f"{err_lbl}\n{str(e)}")
            if pbar:
                finalize_pbar(f"❌ Fehler: {str(e)}")

    def on_clean_emu_clicked(self):
        """Sorgt dafür, dass das Log vor der Bereinigung englisch wird."""
        # 1. Sprache/UI synchronisieren (löscht alte deutsche Texte im Log)
        self.update_language()
        # 2. Bereinigung starten (schreibt jetzt ins leere, englische Log)
        from oscam_patch_manager import (
            clean_oscam_emu_git,
        )  # oder wo die Funktion liegt

        clean_oscam_emu_git(gui_instance=self)

    def on_button_clicked(self, key, func):
        self.set_active_button(key)
        self.run_action(func)

    def set_active_button(self, active_key):
        self.active_button_key = active_key

        # 1. Sicherstellen, dass wir die richtige Textfarbe aus dem aktuellen Theme haben
        # Wir probieren 'fg', falls das fehlt 'text', sonst weiß als Notlösung.
        text_color = current_diff_colors.get(
            "fg", current_diff_colors.get("text", "#FFFFFF")
        )

        # 2. Die Hover-Farbe für den inaktiven Zustand holen
        hover_color = current_diff_colors.get("hover", current_diff_colors["bg"])

        for key, btn in self.buttons.items():
            if key == active_key:
                # AKTIVER BUTTON: Giftgrün (wie in deinem Original)
                # Tipp: Du könntest hier auch current_diff_colors['active'] nutzen!
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: #00FF00; 
                        color: #000000; 
                        border-radius: {self.BUTTON_RADIUS}px; 
                        min-height: {self.BUTTON_HEIGHT}px;
                        font-weight: bold;
                        border: 2px solid white;
                    }}
                """
                )
            else:
                # INAKTIVE BUTTONS: Nutzen das aktuelle Farbschema (Theme)
                # Wir bauen hier auch den Hover-Effekt wieder ein, damit er nicht verloren geht!
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {current_diff_colors['bg']}; 
                        color: {text_color}; 
                        border-radius: {self.BUTTON_RADIUS}px; 
                        min-height: {self.BUTTON_HEIGHT}px;
                    }}
                    QPushButton:hover {{
                        background-color: {hover_color};
                    }}
                """
                )

    def repaint_ui_colors(self):
        """Aktualisiert ALLE GUI-Elemente basierend auf dem gewählten Farbschema."""
        global current_diff_colors

        # Farben zentral definieren
        text_color = current_diff_colors.get("fg", "#FFFFFF")
        bg_color = current_diff_colors.get("bg", "#2F2F2F")
        hover_color = current_diff_colors.get("hover", "#444444")
        active_color = current_diff_colors.get("active", "#666666")

        # A) ALLE Buttons im Fenster automatisch finden und stylen
        all_widgets = self.findChildren(QPushButton)
        for btn in all_widgets:
            try:
                btn.setGraphicsEffect(None)
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {bg_color};
                        color: {text_color};
                        border-radius: 10px;
                        font-weight: 700; 
                        padding: 2px 6px;
                        font-size: 13px;
                        border: 1px solid #444;
                        height: 35px;
                        min-height: 35px;
                    }}
                    QPushButton:hover {{
                        background-color: {hover_color};
                        border: 1px solid {text_color};
                    }}
                    QPushButton:pressed {{
                        background-color: {active_color};
                        padding-top: 2px;
                    }}
                """
                )
            except RuntimeError:
                continue

        # --- NEU: STATS-CHECKBOX (TELEMETRIE) AN DAS SCHEMA ANPASSEN ---
        cb = getattr(self, "telemetry_cb", None)
        if cb:
            try:
                # Wir stylen die Checkbox exakt wie die Buttons oben
                cb.setStyleSheet(
                    f"""
                    QCheckBox {{
                        background-color: {bg_color};
                        color: {text_color};
                        border-radius: 10px;
                        font-weight: 700;
                        padding: 2px 10px;
                        font-size: 13px;
                        border: 1px solid #444;
                        height: 35px;
                        min-height: 35px;
                    }}
                    QCheckBox:hover {{
                        background-color: {hover_color};
                        border: 1px solid {text_color};
                    }}
                    QCheckBox::indicator {{
                        width: 16px;
                        height: 16px;
                        border: 1px solid {text_color};
                        border-radius: 3px;
                        background: transparent;
                    }}
                    QCheckBox::indicator:checked {{
                        background-color: {text_color};
                        border: 1px solid white;
                    }}
                """
                )
            except RuntimeError:
                pass

        # B) ProgressBar Style (Standard-Zustand)
        pb = getattr(self, "progress_bar", None)
        if pb:
            try:
                if pb.value() == 0 or pb.value() == 100:
                    pb.setStyleSheet(
                        f"QProgressBar {{ border: 1px solid {bg_color}; border-radius: 7px; background-color: #1a1a1a; text-align: center; color: {text_color}; font-weight: 700; }}"
                        f"QProgressBar::chunk {{ background-color: {bg_color}; border-radius: 6px; }}"
                    )
            except RuntimeError:
                pass

        # C) Labels & Header
        for lbl_name in [
            "lang_label",
            "color_label",
            "commit_label",
            "controls_header",
        ]:
            lbl = getattr(self, lbl_name, None)
            if lbl:
                try:
                    bg = bg_color if lbl_name == "controls_header" else "transparent"
                    lbl.setStyleSheet(
                        f"color: {text_color}; font-weight: 700; font-size: 18px; background: {bg}; border-radius: 6px;"
                    )
                except RuntimeError:
                    pass

        # 5. Hauptfenster Hintergrund
        try:
            self.setStyleSheet("background-color: #2F2F2F;")
            if hasattr(self, "pbar_idle") and (not pb or pb.value() == 0):
                self.pbar_idle()
        except RuntimeError:
            pass

    def setup_grid_buttons(self):
        """
        Erstellt die unteren Aktions-Buttons mit nativen System-Icons (Windows + Linux).
        Fix: Verhindert Text-Umbrüche durch CSS und sorgt für korrekte Icon-Platzierung.
        """
        from PyQt6.QtWidgets import (
            QGridLayout,
            QWidget,
            QSizePolicy,
            QApplication,
            QStyle,
        )
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize, Qt

        # ---------- Hilfsfunktion: Plattformübergreifende Icons ----------
        def get_system_icon(theme_name: str, fallback: QStyle.StandardPixmap):
            icon = QIcon.fromTheme(theme_name)
            if not icon.isNull():  # Linux / KDE / Gnome
                return icon
            return QApplication.style().standardIcon(fallback)  # Windows fallback

        # ---------- Icon Mapping ----------
        ICON_MAP = {
            "patch_create": ("document-new", QStyle.StandardPixmap.SP_FileIcon),
            "patch_renew": ("view-refresh", QStyle.StandardPixmap.SP_BrowserReload),
            "patch_check": ("dialog-ok", QStyle.StandardPixmap.SP_DialogApplyButton),
            "patch_apply": ("system-run", QStyle.StandardPixmap.SP_MediaPlay),
            "patch_zip": ("package-x-generic", QStyle.StandardPixmap.SP_DriveFDIcon),
            "backup_old": ("document-save", QStyle.StandardPixmap.SP_DialogSaveButton),
            "clean_folder": ("edit-clear", QStyle.StandardPixmap.SP_TrashIcon),
            "change_old_dir": ("folder-open", QStyle.StandardPixmap.SP_DirOpenIcon),
            "exit": ("application-exit", QStyle.StandardPixmap.SP_DialogCloseButton),
        }

        # ---------- Layout holen ----------
        if hasattr(self, "layout_grid_buttons"):
            grid_layout = self.layout_grid_buttons
        else:
            grid_layout = QGridLayout()
            grid_container = QWidget()
            grid_container.setLayout(grid_layout)
            if self.layout():
                self.layout().addWidget(grid_container)

        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(0, 5, 0, 5)

        # ---------- Aktionen ----------
        grid_actions = [
            (
                "patch_create",
                lambda: create_patch(self, self.info_text, self.progress_bar.setValue),
            ),
            (
                "patch_renew",
                lambda: create_patch(self, self.info_text, self.progress_bar.setValue),
            ),
            (
                "patch_check",
                lambda: self.check_patch(self.info_text, self.progress_bar.setValue),
            ),
            (
                "patch_apply",
                lambda: (
                    (
                        self.progress_bar.setValue(0)
                        if hasattr(self, "progress_bar")
                        else None
                    ),
                    self.apply_patch(self.info_text, self.progress_bar.setValue),
                ),
            ),
            (
                "patch_zip",
                lambda: self.zip_patch(self.info_text, self.progress_bar.setValue),
            ),
            (
                "backup_old",
                lambda: backup_old_patch(
                    self, self.info_text, self.progress_bar.setValue
                ),
            ),
            (
                "clean_folder",
                lambda: clean_patch_folder(
                    self, self.info_text, self.progress_bar.setValue
                ),
            ),
            (
                "change_old_dir",
                lambda: self.change_old_patch_dir(
                    self.info_text, self.progress_bar.setValue
                ),
            ),
            ("exit", self.close_with_confirm),
        ]

        self.buttons = {}
        cols = 3
        FIXED_HEIGHT = 35

        # ---------- Buttons erzeugen ----------
        for idx, (key, func) in enumerate(grid_actions):
            btn_text = self.get_t(key, key)

            btn = self.create_action_button(
                parent=self,
                text=btn_text,
                color="#1E90FF",
                fg="white",
                callback=lambda checked=False, f=func, k=key: (
                    self.set_active_button(k),
                    f(),
                ),
                all_buttons_list=self.all_buttons,
                min_height=FIXED_HEIGHT,
                radius=self.BUTTON_RADIUS,
            )

            # ---- System Icon setzen ----
            theme_name, fallback = ICON_MAP.get(
                key, ("application-x-executable", QStyle.StandardPixmap.SP_FileIcon)
            )
            btn.setIcon(get_system_icon(theme_name, fallback))
            btn.setIconSize(QSize(20, 20))

            # ---- Layout & Text-Verhalten FIX ----
            # 'white-space: nowrap' erzwingt Einzeiligkeit (Alternative zu setWordWrap)
            # 'text-align: left' sorgt für einheitliche Optik mit Icon links
            btn.setStyleSheet(
                btn.styleSheet()
                + """
                padding-left: 12px; 
                padding-right: 12px; 
                text-align: left; 
                white-space: nowrap;
            """
            )

            # Layout-Policy: Stabil halten
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(170)
            btn.setMaximumHeight(FIXED_HEIGHT)

            row, col = divmod(idx, cols)
            grid_layout.addWidget(btn, row, col)
            self.buttons[key] = btn

        # Gleichmäßige Spaltenbreite erzwingen
        for i in range(cols):
            grid_layout.setColumnStretch(i, 1)

    def update_language(self):
        """
        Übersetzt alle Buttons, Labels und Header zentral.
        Verhindert 'RuntimeError: wrapped C/C++ object has been deleted'.
        """
        from PyQt6.QtWidgets import QApplication

        # 1. Aktuelle Sprache ermitteln
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        self.TEXT = lang_dict

        # Helferfunktion für Übersetzungen
        def get_t(key, default=None):
            if key in lang_dict:
                return lang_dict[key]
            return (
                default if default is not None else str(key).replace("_", " ").title()
            )

        # Sicherheits-Check Funktion
        def safe_ui(attr_name, func_name, *args, **kwargs):
            widget = getattr(self, attr_name, None)
            if widget is not None:
                try:
                    # Prüfen ob das Widget noch "lebt"
                    method = getattr(widget, func_name)
                    method(*args, **kwargs)
                except (RuntimeError, AttributeError):
                    pass

        # --- A) GRID & OPTION BUTTONS ---
        if hasattr(self, "buttons") and self.buttons:
            for key, btn in self.buttons.items():
                try:
                    btn.setText(get_t(key))
                except RuntimeError:
                    pass

        if hasattr(self, "option_buttons") and self.option_buttons:
            for key, val in self.option_buttons.items():
                if isinstance(val, (list, tuple)) and len(val) >= 2:
                    try:
                        prefix = "💻 " if "terminal" in str(key).lower() else ""
                        val[0].setText(f"{prefix}{get_t(val[1])}")
                    except RuntimeError:
                        pass

        # --- B) HEADER (Die Haupt-Fehlerquelle) ---
        safe_ui("controls_header", "setText", get_t("settings_header", "Einstellungen"))
        safe_ui(
            "github_header",
            "setText",
            get_t("github_config_header", "GitHub Konfiguration"),
        )

        # --- C) DIE 3 NEUEN ORDNER-BUTTONS ---
        safe_ui(
            "btn_open_work",
            "setText",
            " Arbeitsordner" if lang == "de" else " WORK_DIR",
        )
        safe_ui(
            "btn_open_temp", "setText", " Temp-Repo" if lang == "de" else " Temp Repo"
        )
        safe_ui("btn_open_emu", "setText", " Emu Git" if lang == "de" else " Emu Git")

        # --- D) FUNKTIONS-BUTTONS ---
        safe_ui(
            "btn_check_tools", "setText", get_t("check_tools_button", "🛠️ Check Tools")
        )
        safe_ui("btn_check_commit", "setText", "🔄 Check Commit")

        # Patch Autor
        if hasattr(self, "btn_modifier"):
            auth_text = "👤 Patch Autor" if lang == "de" else "👤 Patch Author"
            current_name = getattr(self, "patch_modifier", "speedy005")
            tip = (
                f"Autor: {current_name}" if lang == "de" else f"Author: {current_name}"
            )
            safe_ui("btn_modifier", "setText", auth_text)
            safe_ui("btn_modifier", "setToolTip", tip)

        # Repo URL
        if hasattr(self, "btn_repo_url"):
            safe_ui("btn_repo_url", "setText", get_t("repo_url_button", "🌐 Repo URL"))
            repo_tip = "Emu-Repo URL ändern" if lang == "de" else "Change Emu-Repo URL"
            safe_ui("btn_repo_url", "setToolTip", repo_tip)

        # --- E) LABELS & SYSTEM ---
        safe_ui("lang_label", "setText", get_t("language_label", "Sprache:"))
        safe_ui("color_label", "setText", get_t("color_label", "Farbe:"))
        safe_ui("commit_label", "setText", get_t("commit_count_label", "Commits:"))

        safe_ui(
            "patch_emu_git_button",
            "setText",
            get_t("patch_emu_git_button", "Patch OSCam Emu"),
        )
        safe_ui(
            "github_upload_patch_button",
            "setText",
            get_t("github_upload_button", "GitHub Upload"),
        )
        safe_ui("clean_emu_button", "setText", get_t("clean_emu_button", "Bereinigen"))

        # --- F) FINISH ---
        if hasattr(self, "repaint_ui_colors"):
            try:
                self.repaint_ui_colors()
            except RuntimeError:
                pass

        QApplication.processEvents()

    def change_language(self):
        """
        Zentrale Steuerung für den Sprachwechsel.
        Kombiniert: Overlay -> Flaggen-Animation -> Sound -> UI Update -> System Monitor Restart.
        """
        from PyQt6.QtWidgets import QApplication, QGroupBox
        from PyQt6.QtCore import QTimer
        import re

        # 1. SICHERHEITS-CHECK
        if not hasattr(self, "language_box") or self.language_box is None:
            return
        if getattr(self, "_block_language_change", False):
            return
        self._block_language_change = True

        # --- A) SPRACHE & OVERLAY ERMITTELN ---
        selected = self.language_box.currentText().upper()
        target_is_de = any(x in selected for x in ["DE", "DEU", "DEUTSCH"])

        # Intern setzen
        self.LANG = "de" if target_is_de else "en"
        # Globale Variable LANG ebenfalls synchronisieren, falls vorhanden
        if "LANG" in globals():
            globals()["LANG"] = self.LANG

        is_de = self.LANG == "de"

        # TEXTS Dictionary laden
        all_texts = globals().get("TEXTS", {})
        # Wir setzen self.TEXT als Referenz auf das aktuelle Sprachpaket
        self.TEXT = all_texts.get(self.LANG, all_texts.get("en", {}))
        lang_dict = self.TEXT

        # Texte für Overlays und Progressbar (Sicherer Zugriff via .get)
        wait_text = lang_dict.get(
            "loading_commits",
            "Sprache wird angepasst..." if is_de else "Switching language...",
        )
        ok_text = f"✅ {lang_dict.get('foot_ok', 'OK')}"

        if hasattr(self, "loading_overlay"):
            self.loading_overlay.setGeometry(self.rect())
            self.loading_label.setText(f"⏳ {wait_text}")
            self.loading_overlay.show()
            self.loading_overlay.raise_()
            QApplication.processEvents()

        try:
            # --- B) RESSOURCEN & SOUND ---
            safe_play_func = globals().get("safe_play")
            if safe_play_func:
                safe_play_func("service-logout.oga")

            def strip_icons(text):
                return re.sub(r"^[^\w\s]+", "", str(text)).strip()

            # Flaggen-Animation starten
            if hasattr(self, "show_language_animation"):
                self.show_language_animation(self.LANG)

            # --- C) PROGRESSBAR START ---
            if hasattr(self, "progress_bar") and self.progress_bar:
                self.progress_bar.setValue(20)
                self.progress_bar.setFormat(f"⏳ {wait_text} %p%")

            # --- D) UI AKTUALISIEREN (BUTTONS, LABELS) ---
            if hasattr(self, "update_language"):
                self.update_language()

            # Dynamische Anpassung der Einstellungs-Labels
            if hasattr(self, "commit_label") and self.commit_label:
                self.commit_label.setText(
                    lang_dict.get("commit_count_label", "Commits:")
                )
                self.commit_label.setFixedWidth(
                    self.commit_label.sizeHint().width() + 10
                )

            if hasattr(self, "color_label") and self.color_label:
                self.color_label.setText(
                    lang_dict.get("color_label", "Farbe:" if is_de else "Color:")
                )
                self.color_label.setFixedWidth(self.color_label.sizeHint().width() + 10)

            if hasattr(self, "log_button") and self.log_button:
                self.log_button.setText(
                    lang_dict.get(
                        "log_button_text", " Log speichern" if is_de else " Save Log"
                    )
                )

            # Innerhalb von change_language(self):
            if hasattr(self, "telemetry_cb") and self.telemetry_cb:
                # 1. Texte aus dem Dictionary oder Fallback holen
                cb_text = lang_dict.get("stats_checkbox", "Stats")
                cb_tip = lang_dict.get(
                    "stats_tooltip",
                    (
                        "Anonyme Nutzungsstatistik (Hit-Counter) erlauben/verbieten."
                        if is_de
                        else "Allow/Disallow anonymous usage statistics (Hit-Counter)."
                    ),
                )

                # 2. Tooltip erst leeren (Force Refresh), dann neu setzen
                self.telemetry_cb.setToolTip("")
                self.telemetry_cb.setText(cb_text)
                self.telemetry_cb.setToolTip(cb_tip)

                # 3. Widget zur Neudarstellung zwingen
                self.telemetry_cb.update()

            if hasattr(self, "header_label") and self.header_label:
                new_title = lang_dict.get(
                    "settings_header", "Einstellungen" if is_de else "Settings"
                )
                self.header_label.setText(f" {strip_icons(new_title)}")

            # Buttons im Hauptmenü
            if hasattr(self, "btn_modifier") and self.btn_modifier:
                label = strip_icons(
                    lang_dict.get(
                        "modifier_button_text",
                        "Patch Autor" if is_de else "Patch Author",
                    )
                )
                self.btn_modifier.setText(f"👤 {label}")

            if hasattr(self, "btn_patch_online") and self.btn_patch_online:
                p_label = strip_icons(
                    lang_dict.get(
                        "online_patch_dl", "Patch Online" if is_de else "Load Patch"
                    )
                )
                self.btn_patch_online.setText(f"🌐 {p_label}")

            # Groupboxen
            for box in self.findChildren(QGroupBox):
                title = box.title()
                if any(word in title for word in ["Einstellungen", "Settings"]):
                    box.setTitle(lang_dict.get("settings_header", "Settings"))
                elif any(
                    word in title
                    for word in ["GitHub", "Configuration", "Konfiguration"]
                ):
                    box.setTitle(
                        lang_dict.get("github_config_header", "GitHub Configuration")
                    )

            # --- E) CONFIG SPEICHERN ---
            if hasattr(self, "cfg"):
                self.cfg["language"] = self.LANG.upper()
                save_func = globals().get("save_config")
                if save_func:
                    save_func(self.cfg, gui_instance=self, silent=True)

            # --- F) INFO TEXT RESET (MITTIG) ---
            if hasattr(self, "info_text") and self.info_text:
                self.info_text.clear()
                wait_msg = lang_dict.get(
                    "restarting_check",
                    (
                        "System-Check wird neu gestartet..."
                        if is_de
                        else "Restarting system check..."
                    ),
                )
                # Zentrierung eingebaut:
                self.info_text.setHtml(
                    f"<div style='margin-top:50px; text-align: center; color:#F37804; font-family:sans-serif;'>"
                    f"<b style='font-size:18pt;'>⏳ {wait_msg}</b>"
                    f"</div>"
                )

            # --- G) TIMER-KETTE FÜR FINALE ---
            if safe_play_func:
                QTimer.singleShot(400, lambda: safe_play_func("dialog-information.oga"))

            # System Check Neustart (Das schreibt Autor & Version bereits neu!)
            QTimer.singleShot(1000, lambda: self.run_full_system_check(clear_log=True))

            # Overlay entfernen
            QTimer.singleShot(1800, self.hide_language_overlay)

            # Progressbar Abschluss
            if hasattr(self, "progress_bar") and self.progress_bar:
                QTimer.singleShot(1200, lambda: self.progress_bar.setValue(100))
                QTimer.singleShot(1400, lambda: self.progress_bar.setFormat(ok_text))

                if hasattr(self, "pbar_idle"):
                    QTimer.singleShot(3000, self.pbar_idle)
                else:
                    QTimer.singleShot(3000, lambda: self.progress_bar.setFormat("%p%"))
                    QTimer.singleShot(3100, lambda: self.progress_bar.setValue(0))

        except Exception as e:
            print(f"❌ Fehler beim Sprachwechsel: {e}")
        finally:
            # Blockierung zeitverzögert lösen
            QTimer.singleShot(
                2000, lambda: setattr(self, "_block_language_change", False)
            )
            QApplication.processEvents()

    # =====================
    # GITHUB EMU CREDENTIALS
    # =====================
    def check_emu_credentials(self):
        cfg = load_github_config()
        if not all([cfg.get("emu_repo_url"), cfg.get("username"), cfg.get("token")]):
            lang = getattr(self, "LANG", LANG)
            self.append_info(
                self.info_text,
                TEXTS[lang].get(
                    "github_emu_credentials_missing", "GitHub-Emu-Zugangsdaten fehlen!"
                ),
                "warning",
            )

    def edit_emu_github_config(self, info_widget=None, progress_callback=None):
        """Öffnet den GitHub-Konfigurationsdialog mit Regenbogen-ProgressBar und Sound."""
        import os, subprocess, platform
        from PyQt6.QtWidgets import QFormLayout, QLabel, QDialogButtonBox, QApplication

        # 1. Sprache & ProgressBar sicherstellen
        current_lang = str(getattr(self, "LANG", "de")).lower()[:2]
        is_de = current_lang == "de"
        pbar = getattr(self, "progress_bar", None)

        if pbar:
            # Regenbogen Style mit schwarzer Schrift
            rainbow = (
                "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
            )
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center;
                    font-weight: bold;
                    border: 2px solid #222;
                    border-radius: 6px;
                    background-color: #111;
                    color: black;
                    font-size: 11pt;
                }}
                QProgressBar::chunk {{
                    background-color: {rainbow};
                    border-radius: 4px;
                }}
            """
            )
            msg = (
                "Konfiguration wird geladen..." if is_de else "Loading configuration..."
            )
            pbar.setFormat(f"{msg} %p%")
            pbar.setValue(20)
            pbar.show()
            QApplication.processEvents()

        def play_config_sound(sound_type="open"):
            sound = "dialog-information.oga" if sound_type == "open" else "complete.oga"
            safe_play(sound)

        play_config_sound("open")
        dialog = GithubConfigDialog(self)
        if pbar:
            pbar.setValue(50)

        # 2. Hilfsfunktion für Texte
        def get_txt(key, default=""):
            try:
                lang_pkg = TEXTS.get(current_lang, TEXTS.get("de", {}))
                return lang_pkg.get(key, default)
            except:
                return default

        # 3. UI Texte anpassen
        dialog.setWindowTitle(get_txt("github_dialog_title", "GitHub Configuration"))
        form_layout = dialog.layout()
        if isinstance(form_layout, QFormLayout):
            mapping = [
                (dialog.patch_repo, "patch_repo_label", "Patch Repo:"),
                (dialog.patch_branch, "patch_branch_label", "Patch Branch:"),
                (dialog.emu_repo, "emu_repo_label", "EMU Repo:"),
                (dialog.emu_branch, "emu_branch_label", "EMU Branch:"),
                (dialog.username, "github_username_label", "GitHub User:"),
                (dialog.token, "github_token_label", "Token:"),
                (dialog.user_name, "github_user_name_label", "Git Name:"),
                (dialog.user_email, "github_user_email_label", "Git Email:"),
            ]
            for field, key, default_text in mapping:
                label = form_layout.labelForField(field)
                if label and isinstance(label, QLabel):
                    label.setText(get_txt(key, default_text))

        # Buttons
        button_box = dialog.findChild(QDialogButtonBox)
        if button_box:
            save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
            cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
            if save_btn:
                save_btn.setText(get_txt("save", "Speichern"))
            if cancel_btn:
                cancel_btn.setText(get_txt("cancel", "Abbrechen"))

        if pbar:
            pbar.setValue(80)

        # 4. Dialog ausführen
        if dialog.exec():
            msg_save = get_txt(
                "github_config_saved", "GitHub Konfiguration gespeichert."
            )
            self.append_info(info_widget or self.info_text, msg_save, "success")
            play_config_sound("save")
            if pbar:
                finish_msg = "Gespeichert!" if is_de else "Saved!"
                pbar.setFormat(f"✅ {finish_msg} 100%")
        else:
            if pbar:
                pbar.setFormat("%p%")

        # 5. Abschluss
        if pbar:
            pbar.setValue(100)
        from PyQt6.QtCore import QTimer

        # Nach 3 Sekunden (3000ms) zurücksetzen
        QTimer.singleShot(3000, self.pbar_idle)
        if progress_callback:
            progress_callback(100)

    # =====================
    # RUN ACTION WRAPPER
    # =====================
    def run_action(self, action_func):
        """
        Führt eine Aktion aus, zeigt Fortschritt in der ProgressBar und Meldungen im Info-Widget.
        action_func: Funktion, die (info_widget, progress_callback) als Parameter akzeptiert
        """
        lang = getattr(self, "LANG", LANG)  # aktuelle GUI-Sprache

        try:
            # Progress starten
            self.progress.setValue(0)
            self.progress.setStyleSheet(
                f"QProgressBar::chunk {{background-color:{current_diff_colors['bg']};}}"
            )

            # Aktion ausführen
            action_func(
                info_widget=self.info_text, progress_callback=self.progress.setValue
            )

            # Fortschritt abschließen
            self.progress.setValue(100)

        except Exception as e:
            # Fehler im Info-Widget ausgeben, sprachabhängig
            error_text = (
                TEXTS[lang]
                .get("generic_error", "❌ Fehler: {error}")
                .format(error=str(e))
            )
            self.append_info(self.info_text, error_text, "error")
            self.progress.setValue(0)

    # =====================
    # BUTTON CALLBACKS
    # =====================
    def show_commits(self, info_widget=None, progress_callback=None):
        """
        Zeigt die letzten Commits an mit Regenbogen-ProgressBar und Sound.
        Text während des Vorgangs sichtbar, am Ende 3 Sekunden stehen lassen.
        """
        from PyQt6.QtWidgets import QTextEdit, QApplication
        from PyQt6.QtCore import QTimer
        import os

        if not isinstance(info_widget, QTextEdit):
            info_widget = getattr(self, "info_text", None)
            if info_widget is None:
                return

        lang = getattr(self, "LANG", "de").lower()
        is_de = lang == "de"
        pbar = getattr(self, "progress_bar", None)

        # -------------------------------
        # Helper-Funktionen
        # -------------------------------
        def log(text, level="info"):
            if widget := info_widget:
                self.append_info(widget, text, level)
            else:
                print(f"[{level.upper()}] {text}")

        def set_progress(val, text=None):
            if not pbar:
                return
            rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{
                   background-color: {rainbow}; border-radius: 4px;
                }}
                """
            )
            pbar.setValue(val)
            if text:
                pbar.setFormat(text)
            pbar.show()
            QApplication.processEvents()
            if progress_callback:
                try:
                    progress_callback(val)
                except Exception:
                    pass

        def finalize_pbar(text, visible_seconds=3):
            if not pbar:
                return
            rainbow = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1 #8B00FF)"
            pbar.setStyleSheet(
                f"""
                QProgressBar {{
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: black; font-size: 15pt;
                }}
                QProgressBar::chunk {{
                    background-color: {rainbow}; border-radius: 4px;
                }}
                """
            )
            pbar.setValue(100)
            pbar.setFormat(text)

            # Nach 3 Sekunden Chunk transparent, Value auf 0
            QTimer.singleShot(
                visible_seconds * 1000,
                lambda: pbar.setStyleSheet(
                    """
                QProgressBar {
                    text-align: center; font-weight: bold; border: 2px solid #222;
                    border-radius: 6px; background-color: #111; color: orange; font-size: 15pt;
                }
                QProgressBar::chunk {
                    background-color: transparent;
                }
                """
                ),
            )
            QTimer.singleShot(visible_seconds * 1000, lambda: pbar.setValue(0))
            if progress_callback:
                QTimer.singleShot(visible_seconds * 1000, lambda: progress_callback(0))

        def play_commit_sound(success=True):
            safe_play("message-new-instant.oga" if success else "dialog-error.oga")

        # -------------------------------
        # START
        # -------------------------------
        set_progress(10, "Lade Commits..." if is_de else "Loading commits...")
        log(TEXTS.get(lang, {}).get("loading_commits", "Lade Commits..."), "warning")

        try:
            if not os.path.exists(TEMP_REPO):
                log(f"❌ Ordner nicht gefunden: {TEMP_REPO}", "error")
                play_commit_sound(False)
                finalize_pbar("❌ Fehler: Ordner fehlt")
                return

            num_commits = getattr(self, "commit_spin", None)
            num_commits = num_commits.value() if num_commits else 10
            cmd = f"git log -n {num_commits} --oneline"

            set_progress(60, "Lese Commits..." if is_de else "Reading commits...")
            output = self.run_command(cmd, cwd=TEMP_REPO)

            if output:
                lines = output.splitlines()
                for line in lines:
                    log(f"• {line}", "info")
                set_progress(90, "✅ Commits geladen" if is_de else "✅ Commits loaded")
                log(
                    f"✅ {TEXTS.get(lang, {}).get('commits_loaded', 'Commits erfolgreich geladen')} ({len(lines)})",
                    "success",
                )
                play_commit_sound(True)
                finalize_pbar("✅ Fertig!" if is_de else "✅ Done!")
            else:
                log("⚠ Keine Commits gefunden.", "warning")
                play_commit_sound(False)
                finalize_pbar("⚠ Keine Commits")

        except Exception as e:
            log(f"❌ Fehler: {str(e)}", "error")
            play_commit_sound(False)
            finalize_pbar(f"❌ Fehler: {str(e)}")

    # ===================== OSCam-EMU BUTTON WRAPPERS =====================
    def oscam_emu_git_patch(self, info_widget=None, progress_callback=None):
        """Zentraler Fix: Übernimmt die funktionierende Logik der Clear-Methode."""
        from PyQt6.QtWidgets import QApplication

        # 1. Referenzen
        widget = info_widget or getattr(self, "info_text", None)
        pbar = getattr(self, "progress_bar", None)
        lang = getattr(self, "LANG", "de").lower()

        # --- 2. STYLES (Vorher definieren, nicht in der Schleife) ---
        rainbow = (
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
            "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
        )

        style_rainbow = f"""
            QProgressBar {{ 
                text-align: center; font-weight: 900; border: 2px solid #222;
                border-radius: 6px; background-color: #111; color: black; font-size: 14pt; 
            }}
            QProgressBar::chunk {{ background-color: {rainbow} border-radius: 4px; }}
        """
        style_error = """
            QProgressBar { 
                text-align: center; font-weight: 900; border: 2px solid #500; 
                border-radius: 6px; background-color: #111; color: #FF0000; font-size: 14pt; 
            }
            QProgressBar::chunk { background-color: #800; border-radius: 4px; }
        """

        def update_now(val, is_err=False):
            if pbar:
                pbar.setFormat("%p%")
                pbar.setStyleSheet(style_error if is_err else style_rainbow)
                pbar.setValue(val)
                pbar.show()
            if progress_callback:
                try:
                    progress_callback(val)
                except:
                    pass
            QApplication.processEvents()

        # --- 3. ABLAUF ---
        update_now(10)
        txt = (
            globals()
            .get("TEXTS", {})
            .get(lang, {})
            .get("oscam_emu_git_patch_start", "🔹 Patch wird erstellt...")
        )
        self.append_info(widget, txt, "info")

        try:
            update_now(40)

            # Der eigentliche Upload/Patch-Prozess
            if "_github_upload" in globals() or hasattr(self, "_github_upload"):
                _github_upload(
                    PATCH_EMU_GIT_DIR,
                    load_github_config().get("emu_repo_url"),
                    info_widget=widget,
                )

            # --- ERFOLG ---
            update_now(100)
            if "safe_play" in globals():
                safe_play("complete.oga")

            bar_txt = (
                "✅ GitHub Upload OK" if lang == "de" else "✅ GitHub Upload Success"
            )
            if pbar:
                pbar.setFormat(bar_txt)

        except Exception as e:
            self.append_info(widget, f"❌ Fehler: {e}", "error")
            update_now(100, is_err=True)
            if "safe_play" in globals():
                safe_play("dialog-error.oga")
            if pbar:
                pbar.setFormat("❌ Error")

    def oscam_emu_git_clear(self, info_widget=None, progress_callback=None):
        """Zentrales Logging für die Emu-Git Bereinigung mit schwarzer Schrift & Regenbogen."""
        from PyQt6.QtWidgets import QApplication

        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", "de").lower()
        pbar = getattr(self, "progress_bar", None)

        # --- 1. REGENBOGEN STYLES (Schwarze Schrift für Lesbarkeit) ---
        rainbow = (
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
            "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
        )

        # color: black sorgt für den Kontrast auf dem bunten Hintergrund
        style_rainbow = f"""
            QProgressBar {{ 
                text-align: center; font-weight: 900; border: 2px solid #222;
                border-radius: 6px; background-color: #111; color: black; font-size: 14pt; 
            }}
            QProgressBar::chunk {{ background-color: {rainbow} border-radius: 4px; }}
        """
        style_error = """
            QProgressBar { 
                text-align: center; font-weight: 900; border: 2px solid #500; 
                border-radius: 6px; background-color: #111; color: #FF0000; font-size: 14pt; 
            }
            QProgressBar::chunk { background-color: #800; border-radius: 4px; }
        """

        # Hilfsfunktion für Updates
        def update_p(val, is_err=False):
            if pbar:
                pbar.setFormat("%p%")
                pbar.setStyleSheet(style_error if is_err else style_rainbow)
                pbar.setValue(val)
                pbar.show()
            if progress_callback:
                try:
                    progress_callback(val)
                except:
                    pass
            QApplication.processEvents()

        # --- 2. START ---
        update_p(10)
        start_msg = TEXTS.get(lang, {}).get(
            "oscam_emu_git_clearing", "🔹 OSCam-Emu Git Ordner wird geleert..."
        )
        self.append_info(info_widget, start_msg, "info")

        try:
            # 3. Ausführung (Bereinigung)
            update_p(50)
            result = clean_oscam_emu_git(progress_callback=progress_callback)

            # 4. Ergebnis-Auswertung (Zweisprachig für die Bar)
            if result == "success":
                msg = TEXTS.get(lang, {}).get(
                    "oscam_emu_git_cleared", "✅ Bereinigung erfolgreich!"
                )
                self.append_info(info_widget, msg, "success")
                update_p(100)
                if "safe_play" in globals():
                    safe_play("complete.oga")

                # Bar-Text zweisprachig
                bar_txt = "✅ Folder cleared" if lang != "de" else "✅ Ordner geleert"
                if pbar:
                    pbar.setFormat(bar_txt)

            elif result == "not_found":
                msg = "ℹ️ " + (
                    "Ordner bereits leer." if lang == "de" else "Folder already empty."
                )
                self.append_info(info_widget, msg, "info")
                update_p(100)
                if "safe_play" in globals():
                    safe_play("dialog-information.oga")

                # Bar-Text zweisprachig
                bar_txt = "ℹ️ Already empty" if lang != "de" else "ℹ️ Bereits leer"
                if pbar:
                    pbar.setFormat(bar_txt)

            else:
                raise Exception("Deletion failed")

        except Exception as e:
            self.append_info(info_widget, f"❌ Fehler: {e}", "error")
            update_p(100, is_err=True)
            if "safe_play" in globals():
                safe_play("dialog-error.oga")

            # Bar-Text zweisprachig bei Fehler
            bar_txt = "❌ Error" if lang != "de" else "❌ Fehler"
            if pbar:
                pbar.setFormat(bar_txt)

        finally:
            QApplication.processEvents()

    def check_patch(self, info_widget=None, progress_callback=None):
        """
        Prüft den Patch-Status sauber mit Regenbogen-ProgressBar und Sound-Feedback.
        """
        import os, subprocess, platform
        from PyQt6.QtWidgets import QApplication

        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", "de").lower()
        pbar = getattr(self, "progress_bar", None)

        # --- 1. REGENBOGEN STYLES DEFINIEREN ---
        rainbow = (
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
            "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
        )
        style_rainbow = f"""
            QProgressBar {{ text-align: center; font-weight: 900; border: 2px solid #222;
            border-radius: 6px; background-color: #111; color: black; font-size: 14pt; }}
            QProgressBar::chunk {{ background-color: {rainbow} border-radius: 4px; }}
        """
        style_error = """
            QProgressBar { text-align: center; font-weight: 900; border: 2px solid #500; 
            border-radius: 6px; background-color: #111; color: #FF0000; font-size: 14pt; }
            QProgressBar::chunk { background-color: #800; border-radius: 4px; }
        """

        # Hilfsfunktion für ProgressBar-Updates
        def update_p(val, is_err=False):
            if pbar:
                pbar.setFormat("%p%")  # Löscht statische Texte wie "Einsatzbereit"
                pbar.setStyleSheet(style_error if is_err else style_rainbow)
                pbar.setValue(val)
                pbar.show()
            if progress_callback:
                try:
                    progress_callback(val)
                except:
                    pass
            QApplication.processEvents()

        def play_check_sound(success=True):
            sound = "complete.oga" if success else "dialog-error.oga"
            if "safe_play" in globals():
                safe_play(sound)

        # --- 2. START ---
        update_p(10)

        # 1. Existenzprüfung der Datei
        if not os.path.exists(PATCH_FILE):
            err_msg = TEXTS.get(lang, {}).get(
                "patch_file_missing", "❌ Patch-Datei nicht gefunden!"
            )
            self.append_info(info_widget, err_msg, "error")
            update_p(100, is_err=True)
            play_check_sound(False)
            if pbar:
                pbar.setFormat("❌ Datei fehlt")
            return

        update_p(40)

        # 2. Ausführung des Git-Checks
        # info_widget=None unterdrückt interne Logs von run_bash für saubere Ausgabe
        code = run_bash(
            f"git apply --check {PATCH_FILE}",
            cwd=TEMP_REPO,
            info_widget=None,
            lang=lang,
        )

        # 3. Ergebnis-Log basierend auf dem Return-Code
        if code == 0:
            ok_msg = TEXTS.get(lang, {}).get(
                "patch_check_ok", "✅ Patch-Check erfolgreich!"
            )
            self.append_info(info_widget, ok_msg, "success")
            update_p(100)
            play_check_sound(True)
            if pbar:
                pbar.setFormat("✅ Patch OK")
        else:
            fail_msg = TEXTS.get(lang, {}).get(
                "patch_check_fail", "❌ Patch-Check fehlgeschlagen!"
            )
            self.append_info(info_widget, fail_msg, "error")
            update_p(100, is_err=True)
            play_check_sound(False)
            if pbar:
                pbar.setFormat("❌ Patch Fehler")

        QApplication.processEvents()

        def apply_patch(self, info_widget=None, progress_callback=None):
            """Wendet den Patch an mit Regenbogen-ProgressBar und Sound-Feedback."""
            import os, subprocess, platform
            from PyQt6.QtWidgets import QApplication

            info_widget = info_widget or self.info_text
            lang = getattr(self, "LANG", "de").lower()
            pbar = getattr(self, "progress_bar", None)

            # --- 1. REGENBOGEN STYLES DEFINIEREN ---
            rainbow = (
                "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                "stop:0.0 #FF0000, stop:0.2 #FF7F00, stop:0.4 #FFFF00, "
                "stop:0.6 #00FF00, stop:0.8 #0000FF, stop:1.0 #8B00FF);"
            )
            style_rainbow = f"""
                QProgressBar {{ text-align: center; font-weight: 900; border: 2px solid #222;
                border-radius: 6px; background-color: #111; color: black; font-size: 14pt; }}
                QProgressBar::chunk {{ background-color: {rainbow} border-radius: 4px; }}
            """
            style_error = """
                QProgressBar { text-align: center; font-weight: 900; border: 2px solid #500; 
                border-radius: 6px; background-color: #111; color: #FF0000; font-size: 14pt; }
                QProgressBar::chunk { background-color: #800; border-radius: 4px; }
            """

            # Hilfsfunktion für ProgressBar-Updates

        def update_p(val, is_err=False):
            if pbar:
                pbar.setFormat("%p%")  # Löscht "Einsatzbereit"
                pbar.setStyleSheet(style_error if is_err else style_rainbow)
                pbar.setValue(val)
                pbar.show()
            if progress_callback:
                try:
                    progress_callback(val)
                except:
                    pass
            QApplication.processEvents()

        def play_apply_sound(success=True):
            if "safe_play" in globals():
                safe_play("complete.oga" if success else "dialog-error.oga")

        # --- 2. START ---
        update_p(10)

        # 1. Check ob Patch-Datei existiert
        if not os.path.exists(PATCH_FILE):
            msg = self.get_t("patch_file_missing", "❌ Patch-Datei fehlt!").format(
                path=PATCH_FILE
            )
            self.append_info(info_widget, msg, "error")
            update_p(100, is_err=True)
            play_apply_sound(False)
            if pbar:
                pbar.setFormat("❌ Datei fehlt")
            return

        # Logger definieren für run_bash
        logger = lambda text, level="info": self.append_info(info_widget, text, level)

        # 2. Start-Meldung
        start_msg = self.get_t("executing_git_apply", "🚀 Wende Patch an...").format(
            patch="oscam-emu.patch"
        )
        self.append_info(info_widget, start_msg, "warning")
        update_p(40)

        # 3. Patch ausführen
        try:
            code = run_bash(f"git apply {PATCH_FILE}", cwd=TEMP_REPO, logger=logger)

            if code == 0:
                self.append_info(
                    info_widget,
                    self.get_t("patch_emu_git_done", "✅ Patch erfolgreich angewendet"),
                    "success",
                )
                update_p(100)
                play_apply_sound(True)
                if pbar:
                    pbar.setFormat("✅ Patch angewendet")
            else:
                self.append_info(
                    info_widget,
                    self.get_t("patch_emu_git_apply_failed", "❌ Patch fehlgeschlagen"),
                    "error",
                )
                update_p(100, is_err=True)
                play_apply_sound(False)
                if pbar:
                    pbar.setFormat("❌ Fehler beim Patchen")
        except Exception as e:
            self.append_info(
                info_widget, f"❌ Schwerer Fehler beim Patchen: {str(e)}", "error"
            )
            update_p(100, is_err=True)
            play_apply_sound(False)

        QApplication.processEvents()

    def change_old_(self, info_widget=None, progress_callback=None):
        global OLD_, OLD_PATCH_FILE, ALT_PATCH_FILE

        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", LANG)  # aktuelle GUI-Sprache

        new_dir = QFileDialog.getExistingDirectory(
            self, TEXTS[lang]["change_old_dir"], OLD_
        )

        if new_dir:
            OLD_ = new_dir
            OLD_PATCH_FILE = os.path.join(OLD_, "oscam-emu.patch")
            ALT_PATCH_FILE = os.path.join(OLD_, "oscam-emu.altpatch")

            save_config(self.commit_spin.value())  # 🔹 GENAU WIE FARBE

            self.append_info(
                info_widget,
                TEXTS[lang]["old_patch_path_changed"].format(OLD_=OLD_),
                "success",
            )
        else:
            self.append_info(
                info_widget, TEXTS[lang]["old_patch_path_cancelled"], "info"
            )

        if progress_callback:
            progress_callback(100)

    def close_with_confirm(self):
        # 1. Sprache abrufen und normieren (KLEINGESCHRIEBEN passend zum Dictionary)
        lang = str(getattr(self, "LANG", "de")).lower()

        # 2. Sicherer Zugriff auf das Dictionary (Fallback auf ENGLISCH statt DE)
        t = TEXTS.get(lang, TEXTS.get("en", {}))

        # 3. GUI mit Fallback-Texten aufbauen
        msg = QMessageBox(self)
        # Fallbacks hinter dem Komma jetzt auf Englisch
        msg.setWindowTitle(t.get("exit", "Exit"))
        msg.setText(t.get("exit_question", "Do you really want to exit?"))

        # Buttons mit Fallbacks beschriften
        yes_text = t.get("yes", "Yes")
        no_text = t.get("no", "No")

        yes_button = msg.addButton(yes_text, QMessageBox.ButtonRole.YesRole)
        no_button = msg.addButton(no_text, QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(no_button)

        msg.exec()

        if msg.clickedButton() == yes_button:
            # 4. Config speichern und beenden
            if hasattr(self, "cfg"):
                try:
                    # Nutzt die globale save_config Funktion
                    if "save_config" in globals():
                        save_config(self.cfg)
                except Exception as e:
                    print(f"[WARN] Config save failed: {e}")

            QApplication.quit()

    def closeEvent(self, event):
        """
        Wird beim Schließen aufgerufen. Zeigt kurz die 'Beendet'-Meldung,
        spielt den Sound ab und schließt dann zeitverzögert das Fenster.
        """
        try:
            # 1. Status für die UI-Logik setzen
            self.is_closing = True

            # 2. Letztes Speichern triggern
            # Dies zeigt jetzt die goldene Nachricht im Log & den orangefarbenen Balken
            save_config({"last_session_exit": "success"}, gui_instance=self)

            # 3. Sound-Logik (Windows / Linux)
            import platform

            if platform.system() == "Windows":
                import winsound

                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            else:
                import shutil, subprocess

                for cmd in ["paplay", "canberra-gtk-play", "aplay"]:
                    if shutil.which(cmd):
                        sound_path = (
                            "/usr/share/sounds/freedesktop/stereo/service-logout.oga"
                        )
                        subprocess.Popen([cmd, sound_path], stderr=subprocess.DEVNULL)
                        break

            # 4. Kurze Verzögerung (700ms), damit der User die Meldung noch sieht
            # Wir ignorieren das Event zuerst und schließen dann per QTimer
            from PyQt6.QtCore import QTimer

            event.ignore()  # Fenster bleibt noch kurz offen
            QTimer.singleShot(
                1000, self.close_final
            )  # Ruft nach 700ms das endgültige Schließen auf

        except Exception as e:
            # Falls etwas schiefgeht, Fenster sofort schließen
            print(f"Fehler im closeEvent: {e}")
            event.accept()

    def close_final(self):
        """Hilfsfunktion für das endgültige Beenden nach der Verzögerung."""
        import sys

        # Beendet das komplette Programm sauber
        sys.exit(0)


# ===================== __main__ =====================
if __name__ == "__main__":
    # --- 1. UMGEBUNG & DPI (ABSOLUT ZUERST) ---
    import os
    import sys

    # High-DPI Skalierung für 4K Monitore & Laptops aktivieren
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["NO_AT_BRIDGE"] = "1"

    # Importe erst nach den Umgebungsvariablen
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import Qt

    # Skalierungs-Richtlinie festlegen, BEVOR die App-Instanz erstellt wird
    # Dies verhindert den "must be called before QGuiApplication" Fehler
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # --- 2. QAPPLICATION ERSTELLEN ---
    app = QApplication(sys.argv)

    # --- 3. START-SEQUENZ MIT FEHLER-ABFANG ---
    try:
        # Hier deine System-Prüfungen (ohne GUI-Elemente zu triggern)
        # ensure_executable_self()
        # ensure_dependencies()

        # 4. DAS HAUPTFENSTER LADEN
        # WICHTIG: Die Klasse PatchManagerGUI muss im Code darüber definiert sein
        window = PatchManagerGUI()

        # 5. ANZEIGEMODUS
        # showMaximized() für Vollbild, show() für Standardgröße
        window.showMaximized()

        # 6. EVENT-LOOP STARTEN
        sys.exit(app.exec())

    except Exception as e:
        # Falls es hier zu einer "Unhandled Exception" kommt, fangen wir sie ab
        import traceback

        error_details = traceback.format_exc()  # Erstellt den kompletten Fehler-Bericht

        print(f"KRITISCHER STARTFEHLER:\n{error_details}")

        # Fehlermeldung für den User anzeigen
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setWindowTitle("OSCam Patch Manager - Startup Error")
        error_box.setText("Ein kritischer Fehler ist beim Start aufgetreten.")
        error_box.setInformativeText(f"Fehler: {str(e)}\n\nDas Programm wird beendet.")
        error_box.setDetailedText(
            error_details
        )  # Zeigt die genaue Zeilennummer bei 'Details'
        error_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        error_box.exec()

        sys.exit(1)
