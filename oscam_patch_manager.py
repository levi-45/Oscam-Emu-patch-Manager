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
)
from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize
import subprocess
import sys
import importlib.util
from PyQt6.QtWidgets import QMessageBox


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
APP_VERSION = "2.8.6"


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


OLD_PATCH_DIR = get_initial_patch_dir()
OLD_PATCH_DIR_PLUGIN_DEFAULT = OLD_PATCH_DIR
OLD_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.patch")
ALT_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.altpatch")
PATCH_MANAGER_OLD = os.path.join(OLD_PATCH_DIR, "oscam_patch_manager_old.py")
CONFIG_OLD = os.path.join(OLD_PATCH_DIR, "config_old.json")
GITHUB_CONFIG_OLD = os.path.join(OLD_PATCH_DIR, "github_upload_config_old.json")
# ===================== CACHE & CONFIG =====================
PYC_FILE = os.path.join(PLUGIN_DIR, "oscam_patch_manager.pyc")
CACHE_DIR = os.path.join(PLUGIN_DIR, "__pycache__")
CONFIG_FILE = os.path.join(PLUGIN_DIR, "config.json")
GITHUB_CONF_FILE = os.path.join(PLUGIN_DIR, "github_upload_config.json")
PATCH_FILE = os.path.join(PLUGIN_DIR, "oscam-emu.patch")
ZIP_FILE = os.path.join(PLUGIN_DIR, "oscam-emu.zip")
ICON_DIR = os.path.join(PLUGIN_DIR, "icons")
TEMP_REPO = os.path.join(PLUGIN_DIR, "temp_repo")
PATCH_EMU_GIT_DIR = os.path.join(PLUGIN_DIR, "oscam-emu-git")
# ===================== TOOLS & REPOS =====================
CHECK_TOOLS_SCRIPT = os.path.join(PLUGIN_DIR, "check_tools.sh")
PATCH_MODIFIER = "speedy005"
EMUREPO = "https://github.com/oscam-mirror/oscam-emu.git"
STREAMREPO = "https://git.streamboard.tv/common/oscam.git"
# Sicherstellen, dass Basis-Ordner existieren
for d in [TEMP_REPO, PATCH_EMU_GIT_DIR, OLD_PATCH_DIR]:
    if not os.path.exists(d):
        try:
            os.makedirs(d, exist_ok=True)
        except:
            pass

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
    "Jungle": {
        "bg": "#1B5E20",
        "fg": "#C8E6C9",
        "hover": "#2E7D32",
        "active": "#003300",
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
        "bg": "#1B1B1B",
        "fg": "#E0E0E0",
        "hover": "#444444",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Ocean": {
        "bg": "#006064",
        "fg": "#FFFFFF",
        "hover": "#00838F",
        "active": "#004D40",
        "window_bg": "#2F2F2F",
    },
    "Olive": {
        "bg": "#556B2F",
        "fg": "#FFFFFF",
        "hover": "#6B8E23",
        "active": "#3E4E21",
        "window_bg": "#2F2F2F",
    },
    "Orange": {
        "bg": "#EF6C00",
        "fg": "#FFFFFF",
        "hover": "#F57C00",
        "active": "#E65100",
        "window_bg": "#2F2F2F",
    },
    "Phoenix": {
        "bg": "#000000",
        "fg": "#FF4E00",
        "hover": "#FFD700",
        "active": "#8B0000",
        "window_bg": "#2F2F2F",
    },
    "Plasma": {
        "bg": "#000000",
        "fg": "#7F00FF",
        "hover": "#3F007F",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Purple": {
        "bg": "#6A1B9A",
        "fg": "#FFFFFF",
        "hover": "#7B1FA2",
        "active": "#4A148C",
        "window_bg": "#2F2F2F",
    },
    "RoyalBlue": {
        "bg": "#002366",
        "fg": "#FFFFFF",
        "hover": "#003399",
        "active": "#001a4d",
        "window_bg": "#2F2F2F",
    },
    "Ruby": {
        "bg": "#C62828",
        "fg": "#FFFFFF",
        "hover": "#D32F2F",
        "active": "#B71C1C",
        "window_bg": "#2F2F2F",
    },
    "Silver": {
        "bg": "#B0B0B0",
        "fg": "#000000",
        "hover": "#C0C0C0",
        "active": "#A0A0A0",
        "window_bg": "#2F2F2F",
    },
    "SkyBlue": {
        "bg": "#0288D1",
        "fg": "#FFFFFF",
        "hover": "#039BE5",
        "active": "#01579B",
        "window_bg": "#2F2F2F",
    },
    "Solar": {
        "bg": "#FBC02D",
        "fg": "#3E2723",
        "hover": "#FDD835",
        "active": "#F57F17",
        "window_bg": "#2F2F2F",
    },
    "Standard": {
        "bg": "#444444",
        "fg": "#FFFFFF",
        "hover": "#555555",
        "active": "#333333",
        "window_bg": "#2F2F2F",
    },
    "Steel": {
        "bg": "#455A64",
        "fg": "#FFFFFF",
        "hover": "#546E7A",
        "active": "#37474F",
        "window_bg": "#2F2F2F",
    },
    "Titan": {
        "bg": "#263238",
        "fg": "#CFD8DC",
        "hover": "#546E7A",
        "active": "#102027",
        "window_bg": "#2F2F2F",
    },
    "Toxic_Glow": {
        "bg": "#0D0D0D",
        "fg": "#ADFF2F",
        "hover": "#32CD32",
        "active": "#006400",
        "window_bg": "#2F2F2F",
    },
    "Turquoise": {
        "bg": "#00CED1",
        "fg": "#FFFFFF",
        "hover": "#40E0D0",
        "active": "#008B8B",
        "window_bg": "#2F2F2F",
    },
    "Ultraviolet": {
        "bg": "#120021",
        "fg": "#BF00FF",
        "hover": "#FF00FF",
        "active": "#000000",
        "window_bg": "#2F2F2F",
    },
    "Vaporwave": {
        "bg": "#2D004B",
        "fg": "#FF71CE",
        "hover": "#01CDFE",
        "active": "#05FFA1",
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
        # Patch anwenden
        "executing_cmd": "Führe Befehl aus:",
        "cmd_failed": "Befehl fehlgeschlagen mit Code:",
        "executing_git_apply": "🚀 Wende Patch an: {patch}",
        "executing_git_check": "🔍 Prüfe Patch-Kompatibilität: {patch}",
        # --- Patch Status ---
        "patch_file_missing": "❌ Patch-Datei fehlt: {path}",
        "patch_emu_git_done": "✅ Patch erfolgreich angewendet!",
        "patch_emu_git_apply_failed": "❌ Patch konnte nicht angewendet werden!",
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


def save_config(cfg, gui_instance=None, silent=False):
    """
    Speichert die Config im Hintergrund.
    silent=True: Absolut KEIN Log im Infoscreen (ideal für den Commit-Check).
    silent=False: Volle Liste (für manuelle Änderungen am Autor/Repo).
    """
    try:
        # 1. System-Werte synchronisieren (Immer ausführen)
        patch_author = cfg.get("patch_modifier", "speedy005")
        repo_url = cfg.get("EMUREPO", "")
        globals()["PATCH_MODIFIER"] = patch_author
        globals()["EMUREPO"] = repo_url

        # 2. Pfade sicherstellen und Speichern (Immer ausführen)
        abs_config_path = os.path.abspath(CONFIG_FILE)
        config_dir = os.path.dirname(abs_config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        with open(abs_config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)

        # 3. Logging (NUR wenn NICHT silent)
        if not silent and gui_instance and hasattr(gui_instance, "log_message"):
            lang = str(cfg.get("language", "de")).lower()
            t = (
                globals()
                .get("TEXTS", {})
                .get(lang, globals().get("TEXTS", {}).get("en", {}))
            )

            cyan = "<span style='color:cyan;'>"
            end = "</span>"

            # Erfolgsmeldung
            msg_ok = t.get("config_saved", "Einstellungen aktualisiert")
            gui_instance.log_message(f"{cyan}✅ {msg_ok}{end}")

            # Blacklist für interne Werte
            skip_keys = ["color", "last_stream_commit", "s3_patch_path", "auto_update"]

            display_map = {
                "patch_modifier": t.get("auth_label", "Autor"),
                "EMUREPO": t.get("repo_label", "Repository"),
                "language": t.get("lang_label", "Sprache"),
                "commit_count": "commit_count",
            }

            for key, value in cfg.items():
                if key in skip_keys:
                    continue
                label = display_map.get(key, key)
                gui_instance.log_message(f"{cyan}➤ {label}: {value}{end}")

    except Exception as e:
        # Fehler sollten auch im silent-Mode gemeldet werden
        if gui_instance and hasattr(gui_instance, "log_message"):
            gui_instance.log_message(
                f"<span style='color:orange;'>❌ Fehler beim Speichern: {e}</span>"
            )


# ===================== CONFIG =====================
def load_config():
    """Lädt Config, erlaubt eigene URLs und repariert die Datei nur bei fehlenden Keys."""
    import os, json

    CORRECT_URL = "https://github.com/oscam-mirror/oscam-emu.git"
    base_patch_dir = globals().get(
        "OLD_PATCH_DIR", os.path.dirname(os.path.abspath(__file__))
    )

    default_cfg = {
        "commit_count": 5,
        "color": "Classics",
        "language": "de",
        "s3_patch_path": base_patch_dir,
        "patch_modifier": "speedy005",
        "EMUREPO": CORRECT_URL,
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

        # 3. Fehlende Keys ergänzen
        needs_save = False
        for key, value in default_cfg.items():
            if key not in cfg:
                cfg[key] = value
                needs_save = True

        # 4. KORREKTUR DER URL (GEÄNDERT)
        # Wir prüfen nur noch, ob die URL viel zu kurz (kaputt) oder leer ist.
        # "oscam-emu.git" wird NICHT mehr erzwungen, damit eigene URLs bleiben!
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

        # 5. Globale Variablen synchronisieren (WICHTIG für den Patch-Generator)
        globals()["EMUREPO"] = cfg["EMUREPO"]
        globals()["PATCH_MODIFIER"] = cfg["patch_modifier"]

        return cfg

    except Exception as e:
        print(f"⚠️ Kritischer Config Fehler: {e}")
        return default_cfg.copy()


# ===================== INFOSCREEN =====================
def github_upload_patch_file(
    gui_instance=None, info_widget=None, progress_callback=None
):
    """
    Lädt die Patch-Datei auf GitHub hoch und zeigt die Version aus dem Header im Infoscreen an.
    Inklusive akustischem Feedback bei Abschluss.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import shutil, os, datetime, subprocess, platform

    # 1. Widget und Sprache sicherstellen
    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(gui_instance, "info_text", None)
    )
    lang = getattr(gui_instance, "LANG", "de").lower()

    # Hilfsfunktion für Fortschritt
    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    def play_sound(success=True):
        """Spielt Sound-Effekte für den GitHub Upload-Status (Absturzsicher)."""
        # Nutzt die globale Master-Funktion safe_play
        safe_play("complete.oga" if success else "dialog-error.oga")

    # 2. Lokale Logger-Funktion
    def log(text_key, level="info", **kwargs):
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        text_template = lang_dict.get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except Exception:
            text = text_template

        if isinstance(widget, QTextEdit) and gui_instance:
            gui_instance.append_info(widget, text, level)
        elif isinstance(widget, QTextEdit):
            color = {"success": "green", "warning": "orange", "error": "red"}.get(
                level, "gray"
            )
            widget.append(f'<span style="color:{color}">{text}</span>')

        QApplication.processEvents()

    # --- Start der Ausführung ---
    set_progress(5)

    cfg = load_github_config()
    repo_url = cfg.get("repo_url")
    branch = cfg.get("branch", "master")
    username = cfg.get("username")
    token = cfg.get("token")
    user_name = cfg.get("user_name")
    user_email = cfg.get("user_email")

    if not all([repo_url, username, token, user_name, user_email]):
        log("github_patch_credentials_missing", "error")
        play_sound(False)
        set_progress(0)
        return

    if not os.path.exists(PATCH_FILE):
        log("patch_file_missing", "error")
        play_sound(False)
        set_progress(0)
        return

    set_progress(15)

    temp_repo = os.path.join(PLUGIN_DIR, "temp_patch_git")
    if os.path.exists(temp_repo):
        shutil.rmtree(temp_repo, ignore_errors=True)
    os.makedirs(temp_repo, exist_ok=True)

    # 3. Repository klonen
    set_progress(20)
    token_url = repo_url.replace("https://", f"https://{username}:{token}@")
    code = run_bash(
        f"git clone --branch {branch} {token_url} {temp_repo}",
        cwd=temp_repo,
        info_widget=widget,
        lang=lang,
    )

    if code != 0:
        log("github_clone_failed", "error")
        play_sound(False)
        set_progress(0)
        return

    set_progress(50)

    # 4. Patch-Datei kopieren
    patch_path = os.path.join(temp_repo, "oscam-emu.patch")
    try:
        shutil.copy2(PATCH_FILE, patch_path)
    except Exception as e:
        log("patch_failed", "error", path=str(e))
        play_sound(False)
        return

    run_bash(
        f'git config user.name "{user_name}"',
        cwd=temp_repo,
        info_widget=widget,
        lang=lang,
    )
    run_bash(
        f'git config user.email "{user_email}"',
        cwd=temp_repo,
        info_widget=widget,
        lang=lang,
    )

    # 5. Patch-Version ermitteln
    try:
        with open(PATCH_FILE, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        patch_version = first_line if first_line else "Unknown Version"
    except:
        patch_version = "Patch Update"

    set_progress(70)
    run_bash("git add -A", cwd=temp_repo, info_widget=widget, lang=lang)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"{patch_version} | {timestamp}"
    run_bash(
        f'git commit -m "{commit_msg}" --allow-empty',
        cwd=temp_repo,
        info_widget=widget,
        lang=lang,
    )

    # 6. Push zu GitHub
    set_progress(85)
    push_code = run_bash(
        f"git push --force origin {branch}",
        cwd=temp_repo,
        info_widget=widget,
        lang=lang,
    )

    if push_code == 0:
        log("github_patch_uploaded", "success", patch_version=patch_version)
        play_sound(True)
        set_progress(100)
    else:
        log("github_upload_failed", "error")
        play_sound(False)
        set_progress(0)

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
    Erstellt den Patch im TEMP_REPO mit dem exakten 3-Zeilen-Header.
    Inklusive akustischem Feedback bei Start und Abschluss.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtGui import QTextCursor
    import subprocess, os, shutil, platform

    # 1. Widget & Sprache & Modifier sicherstellen
    widget = info_widget
    if not isinstance(widget, QTextEdit) and gui_instance:
        widget = getattr(gui_instance, "info_text", None)

    lang = str(getattr(gui_instance, "LANG", "de")).lower()[:2]
    active_modifier = getattr(gui_instance, "patch_modifier", PATCH_MODIFIER)
    active_emu_repo = getattr(gui_instance, "EMUREPO", EMUREPO)

    def log(text_key, level="info", **kwargs):
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        text_template = lang_dict.get(
            text_key, TEXTS.get("en", {}).get(text_key, text_key)
        )
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_template

        if isinstance(widget, QTextEdit):
            color = {"success": "green", "warning": "orange", "error": "red"}.get(
                level, "gray"
            )
            widget.append(f'<span style="color:{color}">{text}</span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()

    def play_sound(sound_name):
        """Spielt den passenden Sound ab (abgesichert via safe_play)."""
        if "safe_play" in globals():
            safe_play(sound_name)

    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    # --- START ---
    # 1. START-SOUND (Signalisiert den Beginn der Arbeit)
    play_sound("dialog-information.oga")

    log("patch_create_start", "info")
    set_progress(10)

    if not os.path.exists(TEMP_REPO):
        os.makedirs(TEMP_REPO, exist_ok=True)

    git_dir = os.path.join(TEMP_REPO, ".git")

    # Repository Validierung
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

        set_progress(90)

        # --- ERFOLG ---
        log("patch_create_success", "success", patch_file=PATCH_FILE)

        # Patch-Version aus Header loggen
        if header.strip():
            header_lines = header.splitlines()
            if header_lines:
                log(
                    "patch_version_from_header",
                    "success",
                    patch_version=header_lines[0].strip(),
                )

        # 2. ERFOLGS-SOUND (Signalisiert das Ende der Arbeit)
        play_sound("complete.oga")

    except Exception as e:
        log("patch_create_failed", "error", error=str(e))
        set_progress(0)
        # 3. FEHLER-SOUND
        play_sound("dialog-error.oga")
        return

    set_progress(100)


# ===================== backup_old_patch=====================
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QTextCursor
import shutil, os, re


def backup_old_patch(self, make_backup=True, info_widget=None, progress_callback=None):
    """
    Sichert den alten Patch und aktualisiert ihn flüssig mit Fortschrittsanzeige.
    Meldungen erscheinen NUR im Infoscreen.
    """
    import os
    import shutil
    import re
    import subprocess
    import platform
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtGui import QTextCursor

    # 1. Widget & Sprache sicherstellen
    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(self, "info_text", None)
    )
    lang = getattr(self, "LANG", "de")

    # --- HILFSFUNKTIONEN ---

    def play_backup_sound(success=True):
        """Spielt Sound für Backup/Update ab (Absturzsicher via safe_play)."""
        safe_play("complete.oga" if success else "dialog-error.oga")

    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    def log(text_key, level="info", **kwargs):
        text_template = TEXTS.get(lang, {}).get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_key
        if isinstance(widget, QTextEdit):
            self.append_info(widget, text, level)

    # --- ABLAUF START ---
    set_progress(10)
    log("backup_old_start", "info")

    old_patch = getattr(self, "OLD_PATCH_FILE", OLD_PATCH_FILE)
    alt_patch = getattr(self, "ALT_PATCH_FILE", ALT_PATCH_FILE)
    new_patch = PATCH_FILE

    # Zielordner sicherstellen
    dir_path = os.path.dirname(old_patch)
    if dir_path and not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            log("patch_failed", "error", path=str(e))
            play_backup_sound(False)  # Sound bei Fehler
            set_progress(0)
            return

    set_progress(30)

    # Alte Datei sichern
    if os.path.exists(old_patch) and make_backup:
        try:
            shutil.copy2(old_patch, alt_patch)
            log("backup_done", "success", path=alt_patch)
        except Exception as e:
            log("patch_failed", "error", path=str(e))
            play_backup_sound(False)  # Sound bei Fehler
            set_progress(0)
            return
    else:
        log("no_old_patch", "info")

    set_progress(60)

    # Neue Patch-Datei kopieren
    if not os.path.exists(new_patch):
        log("patch_file_missing", "error", path=new_patch)
        play_backup_sound(False)  # Sound bei Fehler
        set_progress(0)
        return

    try:
        shutil.copy2(new_patch, old_patch)
        set_progress(80)

        # Version auslesen
        patch_version = "unbekannt"
        with open(old_patch, "r", encoding="utf-8") as f:
            for _ in range(5):
                line = f.readline()
                match = re.search(r"(?i)patch[- ]version:\s*(.+)", line)
                if match:
                    patch_version = match.group(1).strip()
                    break

        log("new_patch_installed", "success", path=f"{old_patch} (v: {patch_version})")
        play_backup_sound(True)  # ERFOLGS-SOUND

    except Exception as e:
        log("patch_failed", "error", path=str(e))
        play_backup_sound(False)  # Sound bei Fehler
        set_progress(0)
        return

    # Fertig
    set_progress(100)


# ===================== CLEAN PATCH FOLDER =====================
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QTextCursor
import shutil, os


def clean_patch_folder(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Löscht temporäre Repos und Dateien (TEMP_REPO, TEMP_PATCH_GIT, PATCH_FILE, ZIP_FILE).
    Der PATCH_EMU_GIT_DIR wird NICHT gelöscht.
    Inklusive akustischem Feedback bei Erfolg.
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
    lang = "de" if lang.startswith("de") else "en"

    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    def play_sound(sound_type="success"):
        """Spielt Sound-Effekte für den Cleanup-Prozess ab (Absturzsicher)."""
        # Sound-Datei basierend auf dem Typ wählen
        sound = (
            "dialog-information.oga" if sound_type == "success" else "dialog-error.oga"
        )

        # Die globale Sicherheits-Funktion nutzen
        if "safe_play" in globals():
            safe_play(sound)

    def log(text_key, level="info", **kwargs):
        lang_data = TEXTS.get(lang, TEXTS.get("en", {}))
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

    # ---------- 2) HELPER ----------
    def on_rm_error(func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except:
            pass

    # ---------- 3) ABLAUF ----------
    set_progress(5)
    log("cleanup_start", "info")

    targets = []
    # PATCH_EMU_GIT_DIR wurde hier entfernt, damit er nicht gelöscht wird!
    for var_name in ["TEMP_REPO", "TEMP_PATCH_GIT"]:
        path = globals().get(var_name)
        if path and os.path.exists(path):
            targets.append((path, "folder"))

    for var_name in ["PATCH_FILE", "ZIP_FILE"]:
        path = globals().get(var_name)
        if path and os.path.exists(path):
            targets.append((path, "file"))

    if not targets:
        set_progress(100)
        log("cleanup_success", "success")
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

        set_progress(10 + (i + 1) * (90 // len(targets)))

    # ---------- 4) ABSCHLUSS ----------
    set_progress(100)
    log("cleanup_success", "success")

    # Sound abspielen (Erfolg oder Fehler)
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
    Klont das Streamboard Git, wendet oscam-emu.patch an und commitet.
    Inklusive Start-Sound und Sound-Feedback bei Erfolg oder Fehlern.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtCore import QTimer
    import os, shutil, subprocess, platform

    # --- Start-Sound sofort abspielen ---
    if "safe_play" in globals():
        safe_play("dialog-information.oga")

    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(gui_instance, "info_text", None)
    )
    lang = getattr(gui_instance, "LANG", "de").lower()

    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    def play_sound(success=True):
        """Spielt Sound-Effekte für Patch-Ergebnisse ab (Absturzsicher via safe_play)."""
        sound_file = "complete.oga" if success else "dialog-error.oga"
        if "safe_play" in globals():
            safe_play(sound_file)

    def log(text_key, level="info", **kwargs):
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        text_template = lang_dict.get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except Exception:
            text = text_key

        if isinstance(widget, QTextEdit) and gui_instance:
            gui_instance.append_info(widget, text, level)
        elif isinstance(widget, QTextEdit):
            widget.append(text)
        QApplication.processEvents()

    # --- Start Ablauf ---
    set_progress(5)
    log("patch_emu_git_start", "info", path=PATCH_EMU_GIT_DIR)

    # Ordner bereinigen
    if os.path.exists(PATCH_EMU_GIT_DIR):
        try:
            shutil.rmtree(PATCH_EMU_GIT_DIR, ignore_errors=True)
            log("patch_emu_git_deleted", "success", path=PATCH_EMU_GIT_DIR)
        except Exception:
            log("delete_failed", "error", path=PATCH_EMU_GIT_DIR)

    os.makedirs(PATCH_EMU_GIT_DIR, exist_ok=True)
    set_progress(15)

    # --- Git Clone ---
    set_progress(20)
    clone = subprocess.run(
        ["git", "clone", "-c", "http.sslVerify=false", STREAMREPO, "."],
        cwd=PATCH_EMU_GIT_DIR,
        capture_output=True,
        text=True,
    )

    if clone.returncode != 0:
        log("patch_emu_git_clone_failed", "error")
        play_sound(False)  # Fehlersound
        return

    # --- Patch anwenden ---
    set_progress(50)
    if not os.path.exists(PATCH_FILE):
        log("patch_file_missing", "error")
        play_sound(False)  # Fehlersound
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
        play_sound(False)  # Fehlersound
        return

    # --- Git Config & Commit ---
    set_progress(70)
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

    # Header auslesen
    old_cwd = os.getcwd()
    try:
        os.chdir(PATCH_EMU_GIT_DIR)
        header_raw = get_patch_header()
        header = header_raw.splitlines()[0] if header_raw else "Update"
    except:
        header = "Update"
    finally:
        os.chdir(old_cwd)

    commit_msg = f"Sync patch {header}"
    subprocess.run(["git", "add", "."], cwd=PATCH_EMU_GIT_DIR, capture_output=True)
    subprocess.run(
        ["git", "commit", "-am", commit_msg, "--allow-empty"],
        cwd=PATCH_EMU_GIT_DIR,
        capture_output=True,
    )
    log("patch_emu_git_applied", "success", commit_msg=commit_msg)

    # Revision auslesen
    rev = None
    try:
        rev_res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PATCH_EMU_GIT_DIR,
            capture_output=True,
            text=True,
        )
        if rev_res.returncode == 0:
            rev = rev_res.stdout.strip()
    except:
        pass

    # --- Finale Meldungen & Sound ---
    set_progress(100)
    if gui_instance:
        log("patch_emu_git_done", "success")
        if rev:
            rev_text = (
                TEXTS[lang]
                .get("patch_emu_git_revision", "Git revision: {sha}")
                .format(sha=rev)
            )
            gui_instance.append_info(widget, rev_text, "success")

        # Erfolgssound abspielen
        play_sound(True)


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
    """
    Upload des lokalen Repo-Pfads zu GitHub.
    Meldungen erscheinen im Infoscreen oder Terminal.
    """
    widget = info_widget or (
        getattr(gui_instance, "info_text", None) if gui_instance else None
    )
    lang = getattr(gui_instance, "LANG", LANG)  # aktuelle GUI-Sprache

    logger = lambda text, level="info": PatchManagerGUI.append_info(widget, text, level)

    cfg = load_github_config()
    username, token = cfg.get("username"), cfg.get("token")
    user_name = cfg.get("user_name", "").strip()
    user_email = cfg.get("user_email", "").strip()

    # Prüfen ob alles vorhanden
    if not all([username, token, user_name, user_email]):
        PatchManagerGUI.append_info(
            widget, TEXTS[lang]["github_emu_credentials_missing"], "error"
        )
        return

    if not os.path.exists(dir_path):
        PatchManagerGUI.append_info(
            widget, TEXTS[lang]["patch_emu_git_missing"], "error"
        )
        return

    # Token in URL einfügen
    token_url = repo_url.replace("https://", f"https://{username}:{token}@")

    # Alte .git löschen
    git_dir = os.path.join(dir_path, ".git")
    if os.path.exists(git_dir):
        shutil.rmtree(git_dir)

    run_bash("git init", cwd=dir_path, logger=logger)
    run_bash(f"git remote add origin {token_url}", cwd=dir_path, logger=logger)
    run_bash(f"git checkout -b {branch}", cwd=dir_path, logger=logger)

    # Git Config setzen
    run_bash(f'git config user.name "{user_name}"', cwd=dir_path, logger=logger)
    run_bash(f'git config user.email "{user_email}"', cwd=dir_path, logger=logger)

    # Alles committen
    run_bash("git add -A", cwd=dir_path, logger=logger)
    run_bash(f'git commit -m "{commit_msg}" --allow-empty', cwd=dir_path, logger=logger)

    # Push erzwingen
    code = run_bash(f"git push origin {branch} --force", cwd=dir_path, logger=logger)

    # Meldung über TEXTS
    PatchManagerGUI.append_info(
        widget,
        (
            TEXTS[lang]["github_upload_success"]
            if code == 0
            else TEXTS[lang]["github_upload_failed"]
        ),
        "success" if code == 0 else "error",
    )


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
    Inklusive Sound-Feedback bei Erfolg oder Fehlern.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import os, subprocess, shutil, platform

    # 1. Sicherstellen, dass wir Instanzen haben
    gui = gui_instance
    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(gui, "info_text", None)
    )
    lang = getattr(gui, "LANG", "de").lower()

    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
            except:
                pass
        elif hasattr(gui, "progress_bar"):
            gui.progress_bar.setValue(val)
        QApplication.processEvents()

    def play_sound(success=True):
        """Spielt Sound-Effekte für den GitHub Upload (Absturzsicher via safe_play)."""
        # Wir wählen nur die Datei und überlassen den Rest safe_play
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

        if widget and hasattr(gui, "append_info"):
            gui.append_info(widget, text, level)
        QApplication.processEvents()

    # --- Start der Logik ---
    set_progress(5)
    log("github_config_load", "info")

    load_func = globals().get("load_github_config") or getattr(
        gui, "load_github_config", None
    )
    if not load_func:
        log("Konfigurations-Ladefunktion fehlt!", "error")
        play_sound(False)
        return

    cfg = load_func()
    repo_url = cfg.get("emu_repo_url")
    branch = cfg.get("emu_branch", "master")
    username, token = cfg.get("username"), cfg.get("token")
    user_name, user_email = cfg.get("user_name"), cfg.get("user_email")

    if not all([repo_url, branch, username, token, user_name, user_email]):
        log("github_emu_git_missing", "error")
        play_sound(False)
        return

    target_dir = globals().get("PATCH_EMU_GIT_DIR")
    if not target_dir or not os.path.exists(target_dir):
        log("patch_emu_git_missing", "error", path=str(target_dir))
        play_sound(False)
        return

    set_progress(15)
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
            subprocess.run(
                ["git", "fetch", "origin", branch], cwd=target_dir, capture_output=True
            )
            subprocess.run(
                ["git", "checkout", branch], cwd=target_dir, capture_output=True
            )

        set_progress(40)
        log("git_config_user", "info")
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

        set_progress(50)
        log("git_adding_files", "info")
        subprocess.run(["git", "add", "."], cwd=target_dir, capture_output=True)

        commit_msg = "Sync OSCam-Emu folder"
        header_func = globals().get("get_patch_header")
        if header_func:
            try:
                raw = header_func()
                commit_msg = raw.splitlines()[0] if raw else commit_msg
            except:
                pass

        log("git_committing", "info")
        subprocess.run(
            ["git", "commit", "-m", commit_msg, "--allow-empty"],
            cwd=target_dir,
            capture_output=True,
        )

        set_progress(70)
        log("github_upload_start", "warning")

        push = subprocess.run(
            ["git", "push", "--force", "origin", branch],
            cwd=target_dir,
            capture_output=True,
            text=True,
            env=silent_env,
        )

        if push.returncode == 0:
            sha = "N/A"
            try:
                sha = subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"], cwd=target_dir, text=True
                ).strip()
            except:
                pass
            log("github_emu_git_uploaded", "success")
            log("github_emu_git_revision", "success", sha=sha, commit_msg=commit_msg)
            set_progress(100)
            play_sound(True)  # ERFOLG
        else:
            log("github_upload_failed", "error")
            err = (
                push.stderr.replace(token, "***")
                if push.stderr
                else "Unknown Git Error"
            )
            log(err.strip(), "error")
            set_progress(0)
            play_sound(False)  # FEHLER

    except Exception as e:
        log(f"Kritischer Fehler: {str(e)}", "error")
        set_progress(0)
        play_sound(False)  # FEHLER


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
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize, QUrl


class PatchManagerGUI(QWidget):
    def __init__(self):
        from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize, QUrl
        import subprocess, platform

        safe_play("service-login.oga")

        # 2. System-Check (etwas später, damit die Sounds sich nicht "beißen")
        # Erhöhe die Zeit von 500 auf 1500 (1.5 Sekunden)
        # QTimer.singleShot(1500, self.display_startup_info)
        # 1. STATUS INITIALISIEREN
        self.is_loading = True  # Verhindert ungewollte Event-Trigger während des Setups
        super().__init__()

        # --- 2. INFOSCREEN & REDIRECTOR ---
        # Das Widget muss existieren, bevor sys.stdout umgeleitet wird
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)

        try:
            import sys

            sys.stdout = StreamToGui(
                lambda msg: self.append_info(self.info_text, msg, "info")
            )
            sys.stderr = StreamToGui(
                lambda msg: self.append_info(self.info_text, msg, "error")
            )
        except Exception as e:
            # Falls ein Fehler auftritt, loggen wir ihn direkt ins Widget
            self.append_info(self.info_text, f"❌ Redirector Error: {e}", "error")

        # --- 3. KONFIGURATION LADEN ---
        self.cfg = load_config()

        # Sprache setzen (de/en)
        stored_lang = str(self.cfg.get("language", "de")).lower()
        self.LANG = stored_lang if stored_lang in ["en", "de"] else "de"

        # NEU: Patch-Modifier (Signatur) aus Config laden
        # Priorität: 1. config.json, 2. Globale Variable PATCH_MODIFIER
        self.patch_modifier = self.cfg.get("patch_modifier", PATCH_MODIFIER)

        # Pfad-Logik
        current_path = self.cfg.get("s3_patch_path", OLD_PATCH_DIR)
        self.OLD_PATCH_DIR = os.path.normpath(current_path)
        self.OLD_PATCH_FILE = os.path.join(self.OLD_PATCH_DIR, "oscam-emu.patch")
        self.ALT_PATCH_FILE = os.path.join(self.OLD_PATCH_DIR, "oscam-emu.altpatch")

        # Basis-Variablen für die GUI
        self.all_buttons = []
        self.option_buttons = {}
        self.buttons = {}
        self.active_button_key = ""
        self.main_grid_layout = None
        self.latest_version = APP_VERSION.replace("v", "").strip()
        self.BUTTON_RADIUS = 5

        # --- 4. HAUPT-UI AUFBAUEN ---
        # Hier werden Buttons (inkl. btn_modifier) und Layouts erstellt
        self.init_ui()

        # --- 5. FARBSCHEMA INITIALISIEREN ---
        saved_color = self.cfg.get("color", "Classics")
        global current_color_name

        if hasattr(self, "color_box"):
            # Signal blockieren, damit change_colors nicht sofort speichert
            self.color_box.blockSignals(True)

            index = self.color_box.findText(saved_color)
            if index != -1:
                self.color_box.setCurrentIndex(index)
                current_color_name = saved_color
            else:
                index = self.color_box.findText("Classics")
                if index != -1:
                    self.color_box.setCurrentIndex(index)
                current_color_name = "Classics"

        self.color_box.blockSignals(False)
        # Jetzt erst Event verbinden
        self.color_box.currentIndexChanged.connect(self.change_colors)

        # --- 6. FINALE INITIALISIERUNG ---
        if not hasattr(self, "label_patch_path"):
            self.label_patch_path = QLabel()

        # GUI-Texte gemäß Sprache befüllen (setzt auch Tooltips für btn_modifier)
        self.update_language()

        # Farben anwenden
        self.change_colors()

        # Zustand des Update-Buttons prüfen
        if hasattr(self, "update_plugin_button_state"):
            self.update_plugin_button_state()

        # Laden beendet - Events sind nun frei
        self.is_loading = False

        # --- 7. AUTOMATISCHE CHECKS (Verzögert für flüssigen Start) ---
        from PyQt6.QtCore import QTimer

        # Tool-Check nach 1 Sekunde
        # QTimer.singleShot(1000, self.manual_tool_check)

        # Update-Check nach 2 Sekunden
        # if hasattr(self, "check_for_update_on_start"):
        QTimer.singleShot(500, self.show_welcome_info)
        QTimer.singleShot(2000, self.check_for_update_on_start)

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

    def show_welcome_info(self):
        """Zeigt die Tool-Übersicht mit fettem Text und buntem Footer an."""
        lang = getattr(self, "LANG", "de").lower()
        version = globals().get("APP_VERSION", "2.8.2")

        # Farbcodes
        C_TITLE = "#E63946"  # Rot-Ton für Titel
        C_FEATURES = "#F37804"  # Orange für Hauptmerkmale
        C_GREEN = "#00FF00"  # Grün
        C_BLUE = "#00ADFF"  # Blau
        C_RED = "#FF0000"  # Reinrot
        C_YELLOW = "#FFFF00"  # Gelb
        C_GRAY = "#808080"  # Grau für Trenner

        # Helfer-Funktion für fette, zweifarbige Zeilen
        def format_line(icon_text, description):
            # Beide Teile sind fett (<b>) für gleiche Schriftstärke
            return f'<span style="color:{C_GREEN};"><b>{icon_text}</b></span> <span style="color:{C_BLUE};"><b>{description}</b></span>'

        if lang == "de":
            title = "OSCam Emu Patch Generator"
            features_label = "Hauptmerkmale:"
            f1 = format_line(
                "➤ Automatisches Patching:",
                "Erstellt .patch Dateien direkt vom Streamboard.",
            )
            f2 = format_line(
                "➤ Commit Monitor:", "Echtzeit-Tracking von neuen Änderungen."
            )
            f3 = format_line(
                "➤ Lokalisierung:", "Vollständige Unterstützung für DE/EN."
            )
            f4 = format_line("➤ Smart Logging:", "Farblich kodiertes Feedback-System.")
        else:
            title = "OSCam Emu Patch Generator"
            features_label = "Key Features:"
            f1 = format_line(
                "➤ Automated Patching:",
                "Generates .patch files directly from Streamboard.",
            )
            f2 = format_line("➤ Commit Monitor:", "Real-time tracking of new changes.")
            f3 = format_line("➤ Localization:", "Full support for DE/EN.")
            f4 = format_line("➤ Smart Logging:", "Color-coded feedback system.")

        # Bunter Footer: Jedes Element erhält explizit seine eigene Farbe
        # WICHTIG: Das umschließende div darf keine color-Eigenschaft haben!
        footer_html = f"""
        <div style="font-size: 24px; margin-top: 2px;">
            <span style="color:{C_RED};"><b>Autor:</b></span> 
            <span style="color:{C_GREEN};"><b>speedy005</b></span> 
            <span style="color:{C_GRAY};"> | </span>
            <span style="color:{C_BLUE};"><b>Version:</b></span> 
            <span style="color:{C_YELLOW};"><b>{version}</b></span> 
            <span style="color:{C_GRAY};"> | </span>
            <span style="color:{C_RED};"><b>Lizenz:</b></span> 
            <span style="color:{C_GREEN};"><b>MIT</b></span>
        </div>
        """

        welcome_html = f"""
        <div style="font-family: 'Segoe UI', Tahoma, sans-serif;">
            <h2 style="color:{C_TITLE}; margin-top:0px; margin-bottom:0px;">🚀 {title}</h2>
            <hr style="color: {C_GRAY}; margin: 2px 0px;">

            <b style="color:{C_FEATURES}; font-size: 24px;">{features_label}</b>

            <div style="font-size: 24px; line-height: 1.2; margin-top: 2px;">
                {f1}<br>
                {f2}<br>
                {f3}<br>
                {f4}
            </div>

            <hr style="color: {C_GRAY}; margin: 2px 0px;">
            {footer_html}
        </div>
        """

        if hasattr(self, "info_text"):
            from PyQt6.QtGui import QTextCursor

            self.info_text.moveCursor(QTextCursor.MoveOperation.End)
            self.info_text.insertHtml(welcome_html)
            # Kleiner Abstandshalter
            self.info_text.insertHtml("<div style='font-size:4px;'>&nbsp;</div>")
            self.info_text.moveCursor(QTextCursor.MoveOperation.End)

    def display_startup_info(self):
        """Bündelt alle Startinfos in der gewünschten Reihenfolge."""
        import shutil

        now_t = QDateTime.currentDateTime().toString("HH:mm:ss")

        output = []

        # 1. Block: System-Check
        output.append(f"Starte System-Check... [{now_t}]")
        all_ok = True
        for t in ["git", "patch", "zip"]:
            if shutil.which(t):
                output.append(f"  ✅ {t} : gefunden")
            else:
                output.append(f"  ❌ {t} : FEHLT")
                all_ok = False

        if all_ok:
            output.append("✅ Alle benötigten System-Tools sind bereit.")

        output.append("-" * 45)  # Trenner

        # 2. Block: Update Check
        output.append("🔍 Tooltest Update Check...")
        output.append(f"✅ Plugin ist aktuell (Version: {APP_VERSION})")

        output.append("-" * 45)  # Trenner

        # 3. Block: Konfiguration
        output.append("🛠️ Aktive Konfiguration:")
        output.append(f"  👤 Patch Autor: {self.patch_modifier}")
        output.append(f"  🌐 Repository: {EMUREPO}")
        output.append("-" * 45)

        # Den gesamten Block auf einmal senden
        self.append_info(self.info_text, "\n".join(output), "info")

    def open_custom_folder(self, path):
        """Öffnet den Pfad im Explorer mit dem bewährten Commit-Sound-System."""
        # 1. Sound abspielen (Nutzt die Datei, die bei dir garantiert funktioniert)
        if "safe_play" in globals():
            # Wir nehmen 'message-new-instant.oga', da diese Datei bei dir aktiv ist
            safe_play("message-new-instant.oga")
        else:
            QApplication.beep()

        # 2. Pfad-Check & Erstellung
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                if hasattr(self, "log_message"):
                    self.log_message(
                        f"<span style='color:orange;'>❌ Fehler beim Erstellen: {e}</span>"
                    )
                return

        # 3. System-Explorer öffnen
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            else:
                subprocess.Popen(
                    ["xdg-open", path],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                )
        except Exception as e:
            if hasattr(self, "log_message"):
                self.log_message(
                    f"<span style='color:orange;'>❌ Fehler beim Öffnen: {e}</span>"
                )

    def change_colors(self):
        """Aktualisiert das Farbschema und speichert es zentral über save_config."""
        global current_diff_colors, current_color_name

        # 1️⃣ Aktuelle Farbe ermitteln
        if hasattr(self, "color_box") and self.color_box.currentText():
            current_color_name = self.color_box.currentText()
        else:
            current_color_name = self.cfg.get("color", "Classics")

        # 2️⃣ Basis-Farben holen (Fallback auf Classics)
        base_colors = DIFF_COLORS.get(
            current_color_name,
            DIFF_COLORS.get("Classics", {"bg": "#FFFFFF", "fg": "#000000"}),
        )
        bg = base_colors.get("bg", "#FFFFFF")

        # 3️⃣ Farben für UI vorbereiten (Hover/Active Nuancen)
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

        # 4️⃣ Farben im UI anwenden
        if hasattr(self, "repaint_ui_colors"):
            self.repaint_ui_colors()

        # 5️⃣ Zentral Speichern über deine neue save_config
        # Wir nutzen silent=True, damit beim reinen Farbwechsel kein großer Log-Text erscheint
        if not getattr(self, "is_loading", False):
            if self.cfg.get("color") != current_color_name:
                self.cfg["color"] = current_color_name
                # Hier rufen wir deine neue globale Speicher-Funktion auf
                save_config(self.cfg, gui_instance=self, silent=True)

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
        """
        Öffnet einen Dialog zur Auswahl der Repository-URL mit lokalisierten Buttons.
        """
        from PyQt6.QtWidgets import QInputDialog, QApplication
        from PyQt6.QtCore import QTimer

        REPO_1 = "https://github.com/oscam-mirror/oscam-emu.git"
        REPO_2 = "https://github.com/speedy005/Oscam-emu.git"
        REPO_OPTIONS = [REPO_1, REPO_2]

        current_repo = getattr(self, "EMUREPO", REPO_1)
        lang = getattr(self, "LANG", "de").lower()

        # Texte laden
        lang_dict = (
            globals()
            .get("TEXTS", {})
            .get(lang, globals().get("TEXTS", {}).get("en", {}))
        )

        title = lang_dict.get("repo_dialog_title", "Repository Auswahl")
        label = lang_dict.get("repo_dialog_label", "Wähle die gewünschte Repo-URL:")
        btn_ok = lang_dict.get("ok_button", "OK")
        btn_cancel = lang_dict.get("cancel_button", "Abbrechen")

        # --- SOUND BEIM ÖFFNEN ---
        safe_play("dialog-information.oga")

        # --- Dialog als Objekt erstellen für lokalisierte Buttons ---
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setComboBoxItems(REPO_OPTIONS)
        dialog.setComboBoxEditable(False)

        # Start-Index setzen
        start_idx = 1 if current_repo == REPO_2 else 0
        dialog.setTextValue(REPO_OPTIONS[start_idx])

        # Buttons übersetzen
        dialog.setOkButtonText(btn_ok)
        dialog.setCancelButtonText(btn_cancel)

        # Dialog ausführen
        ok = dialog.exec()
        new_url = dialog.textValue()

        if ok and new_url:
            # 1. WERTE SETZEN
            self.EMUREPO = new_url
            globals()["EMUREPO"] = new_url

            # 2. CONFIG AKTUALISIEREN
            if hasattr(self, "cfg"):
                self.cfg["EMUREPO"] = self.EMUREPO
                try:
                    # Speichern (nutzt deine neue save_config mit Cyan-Log)
                    if "save_config" in globals():
                        globals()["save_config"](self.cfg, gui_instance=self)

                    # 3. UI-REFRESH
                    if hasattr(self, "update_language"):
                        self.update_language()

                    # --- SOUND BEI ERFOLG ---
                    safe_play("complete.oga")

                except Exception as e:
                    # --- SOUND BEI FEHLER ---
                    safe_play("dialog-error.oga")
                    if hasattr(self, "log_message"):
                        self.log_message(
                            f"<span style='color:orange;'>❌ Fehler: {e}</span>"
                        )

    def change_modifier_name(self):
        """
        Öffnet einen Dialog zur Eingabe des Autors mit lokalisierten Buttons.
        """
        from PyQt6.QtWidgets import QInputDialog, QLineEdit, QApplication
        from PyQt6.QtCore import QTimer

        current_author = getattr(self, "patch_modifier", "speedy005")
        lang = getattr(self, "LANG", "de").lower()

        # TEXTS laden
        lang_dict = (
            globals()
            .get("TEXTS", {})
            .get(lang, globals().get("TEXTS", {}).get("en", {}))
        )

        title_auth = lang_dict.get("mod_dialog_title", "Patch Autor")
        label_auth = lang_dict.get("mod_dialog_label", "Name des Autors:")
        btn_ok = lang_dict.get("ok_button", "OK")
        btn_cancel = lang_dict.get("cancel_button", "Abbrechen")

        # --- SOUND BEIM ÖFFNEN ---
        safe_play("dialog-information.oga")

        # --- Dialog manuell konfigurieren für lokalisierte Buttons ---
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title_auth)
        dialog.setLabelText(label_auth)
        dialog.setTextValue(current_author)
        dialog.setTextEchoMode(QLineEdit.EchoMode.Normal)

        # Hier werden die Buttons übersetzt
        dialog.setOkButtonText(btn_ok)
        dialog.setCancelButtonText(btn_cancel)

        # Dialog ausführen
        ok = dialog.exec()
        new_name = dialog.textValue()

        if ok and new_name.strip():
            new_author = new_name.strip()
            self.patch_modifier = new_author

            if hasattr(self, "cfg"):
                self.cfg["patch_modifier"] = self.patch_modifier

                try:
                    if "save_config" in globals():
                        globals()["save_config"](self.cfg, gui_instance=self)

                    if hasattr(self, "update_language"):
                        self.update_language()

                    # --- SOUND BEI ERFOLG ---
                    safe_play("complete.oga")

                except Exception as e:
                    # --- SOUND BEI FEHLER ---
                    safe_play("dialog-error.oga")
                    if hasattr(self, "log_message"):
                        self.log_message(
                            f"<span style='color:orange;'>❌ Fehler: {e}</span>"
                        )

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
        """Bereinigte Version ohne Blockaden."""
        import time, shutil, os
        from datetime import datetime
        from PyQt6.QtWidgets import QApplication

        # 1. Einfache Doppelklick-Sperre (0.5s reicht völlig)
        now_ts = time.time()
        if hasattr(self, "_last_check_run") and (now_ts - self._last_check_run) < 0.5:
            return
        self._last_check_run = now_ts

        # 2. Sperren entfernen!
        if hasattr(self, "_lock_info_screen"):
            del self._lock_info_screen

        try:
            # 3. Fenster leeren
            self.info_text.clear()
            lang = str(getattr(self, "LANG", "de")).lower()
            timestamp = datetime.now().strftime("%H:%M:%S")

            # 4. Start-Meldung (Nutze 2 Argumente, um Tupel-Fehler zu vermeiden)
            msg = (
                f"Starte System-Check... [{timestamp}]"
                if lang == "de"
                else f"Starting system check... [{timestamp}]"
            )
            self.append_info(msg, "info")

            # 5. Tools prüfen
            required_tools = ["git", "python3"]
            if os.name != "nt":
                required_tools.extend(["patch", "zip"])

            missing = [tool for tool in required_tools if shutil.which(tool) is None]

            if not missing:
                self.append_info(
                    "✅ Alle benötigten System-Tools sind bereit.", "success"
                )

                # 6. HIER NICHT ABBRECHEN! Rufe die anderen Funktionen auf:
                if hasattr(self, "check_for_plugin_update"):
                    self.check_for_plugin_update()

                if hasattr(self, "show_start_config"):
                    self.show_start_config()
            else:
                missing_str = ", ".join(missing)
                self.append_info(f"⚠️ Fehlende Tools: {missing_str}", "warning")
                # ... (hier ggf. dein Terminal-Installer) ...

        except Exception as e:
            self.append_info(f"❌ Check-Fehler: {str(e)}", "error")

    def show_start_config(self):
        """Zeigt die Konfiguration kompakt an und repariert URL-Fehler."""
        if not hasattr(self, "info_text") or not self.info_text:
            return

        lang = getattr(self, "LANG", "de").lower()
        autor = getattr(self, "patch_modifier", "speedy005")

        # URL Logik: Wir nehmen den Wert aus der Config (EMUREPO)
        repo = getattr(self, "EMUREPO", "https://github.com/oscam-mirror/oscam-emu.git")

        # RADIKALE URL-REPARATUR (verhindert https://:// und comoscam)
        if "://" in repo:
            # Extrahiert alles nach dem ersten :// und baut es sauber neu
            parts = repo.split("://")
            clean_url = parts[-1].replace("//", "/").replace("comoscam", "com/oscam")
            repo = f"https://{clean_url}"

        c_header, c_label, c_value = "#FFA500", "#FFFF00", "#00FFFF"
        h = "🛠️ Aktive Konfiguration:" if lang == "de" else "🛠️ Active Configuration:"
        a = "👤 Patch Autor:" if lang == "de" else "👤 Patch Author:"
        r = "🌐 Repository:" if lang == "de" else "🌐 Repository:"

        msg = (
            f"<span style='color:{c_header}'><b>{h}</b></span><br>"
            f"&nbsp;&nbsp;<span style='color:{c_label}'>{a}</span> <span style='color:{c_value}'>{autor}</span><br>"
            f"&nbsp;&nbsp;<span style='color:{c_label}'>{r}</span> <span style='color:{c_value}'>{repo}</span>"
        )

        # newline=True für sauberen Anschluss unter den Update-Check
        self.append_info(msg, "white", newline=True)

        if "safe_play" in globals():
            safe_play("complete.oga")

    def resizeEvent(self, event):
        """
        Zentrale Steuerung für die UI-Skalierung bei Auflösungsänderung.
        Optimiert: Uhr verkleinert, Schriftfaktoren angepasst.
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

    def open_terminal(self, **kwargs):
        """Öffnet ein leeres Terminal und spielt einen Start-Sound ab."""
        import subprocess
        import platform
        import os
        import shutil

        try:
            # --- SOUND BEIM ÖFFNEN ---
            # Nutzt die globale Sicherheits-Funktion (Absturzsicher)
            safe_play("dialog-information.oga")

            system = platform.system()
            if system == "Windows":
                # Startet eine neue Instanz der Eingabeaufforderung
                subprocess.Popen(["cmd"], creationflags=subprocess.CREATE_NEW_CONSOLE)

            elif system == "Linux":
                # Versucht das Standard-Terminal zu finden und zu starten
                terminal_opened = False
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
                    if shutil.which(term):
                        subprocess.Popen([term])
                        terminal_opened = True
                        break

                if not terminal_opened:
                    # Fallback: Versuche es über den System-Standard
                    if shutil.which("x-terminal-emulator"):
                        subprocess.Popen(["x-terminal-emulator"])
                        terminal_opened = True

                if not terminal_opened:
                    raise FileNotFoundError("Kein Terminal-Emulator gefunden.")

        except Exception as e:
            if hasattr(self, "info_text") and self.info_text:
                self.append_info(
                    self.info_text, f"❌ Terminal-Fehler: {str(e)}", "error"
                )

    def select_patch_path(self):
        """Öffnet den Verzeichnis-Dialog und speichert den Pfad Windows-sicher."""
        # Dialog öffnen (startet im aktuell gesetzten Pfad)
        directory = QFileDialog.getExistingDirectory(
            self, "Patch-Ordner auswählen", self.path_input.text() or PLUGIN_DIR
        )

        if directory:
            # WICHTIG für Windows/Bash: Pfad normalisieren (korrigiert Slashes)
            directory = os.path.normpath(directory)

            # 1. GUI-Elemente aktualisieren
            # self.path_input.setText(directory)

            # 2. Interne Variablen im laufenden Betrieb updaten
            self.cfg["s3_patch_path"] = directory
            self.OLD_PATCH_DIR = directory
            self.OLD_PATCH_FILE = os.path.join(directory, "oscam-emu.patch")
            self.ALT_PATCH_FILE = os.path.join(directory, "oscam-emu.altpatch")

            # 3. In config.json speichern
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.cfg, f, indent=4)

                # Feedback im Info-Widget (nutzt deine append_info Methode)
                if hasattr(self, "append_info"):
                    self.append_info(
                        self.info_text,
                        f"✅ Speicherort geändert: <b>{directory}</b>",
                        "success",
                    )
            except Exception as e:
                if hasattr(self, "append_info"):
                    self.append_info(
                        self.info_text, f"❌ Fehler beim Speichern: {e}", "error"
                    )

    def plugin_update_action(self, latest_version=None, progress_callback=None):
        """Sichert alle wichtigen Dateien, installiert das Update und bietet Rollback bei Fehlern."""
        import requests, os, shutil, sys
        from PyQt6.QtWidgets import QMessageBox, QApplication

        current_lang = str(getattr(self, "LANG", "de")).lower()
        lang_pack = TEXTS.get(current_lang, TEXTS.get("en", {}))
        current_file = os.path.abspath(__file__)
        # Pfad zum Backup der Hauptdatei (aus deiner Konfiguration)
        backup_file = PATCH_MANAGER_OLD

        def action_log(text_key, level="info", **kwargs):
            if hasattr(self, "info_text"):
                safe_vars = {"version": latest_version or "???", "current": APP_VERSION}
                safe_vars.update(kwargs)
                text_template = lang_pack.get(text_key, text_key)
                try:
                    text = text_template.format(**safe_vars)
                except:
                    text = text_template
                color = (
                    "green"
                    if level == "success"
                    else "red" if level == "error" else "blue"
                )
                self.info_text.append(f'<span style="color:{color}">{text}</span>')
                QApplication.processEvents()

        try:
            if progress_callback:
                progress_callback(10)

            # --- 1. BACKUP ERSTELLEN ---
            patch_dir = getattr(self, "OLD_PATCH_DIR", "patch_backup")
            os.makedirs(patch_dir, exist_ok=True)

            # Wichtigstes Backup: Die aktuelle .py Datei
            shutil.copy2(current_file, backup_file)
            action_log("update_backup_done", "success")

            if progress_callback:
                progress_callback(30)

            # --- 2. DOWNLOAD ---
            download_url = (
                "https://raw.githubusercontent.com/"
                "speedy005/Oscam-Emu-patch-Manager/main/oscam_patch_manager.py"
            )
            resp = requests.get(download_url, timeout=20)
            resp.raise_for_status()
            new_content = resp.content

            # --- 3. DATEI ERSETZEN MIT ROLLBACK-SCHUTZ ---
            try:
                if len(new_content) < 1000:  # Plausibilitätscheck: Zu kleine Datei?
                    raise ValueError(
                        "Download-Datei scheint korrupt oder zu klein zu sein."
                    )

                with open(current_file, "wb") as f:
                    f.write(new_content)

            except Exception as write_error:
                # ROLLBACK: Falls das Schreiben fehlschlägt, Backup sofort zurückspielen
                if os.path.exists(backup_file):
                    shutil.copy2(backup_file, current_file)
                    action_log(
                        "update_fail",
                        "error",
                        error=f"Rollback durchgeführt: {str(write_error)}",
                    )
                raise write_error

            if progress_callback:
                progress_callback(90)
            action_log("update_done", "success", version=latest_version)

            # --- 4. NEUSTART ---
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(lang_pack.get("restart_required_title", "Restart"))
            msg_box.setText(
                f"{lang_pack.get('update_success', 'Update OK')}\n\n{lang_pack.get('restart_tool_question', 'Restart?')}"
            )

            yes_btn = msg_box.addButton(
                lang_pack.get("yes", "Ja"), QMessageBox.ButtonRole.YesRole
            )
            msg_box.addButton(
                lang_pack.get("no", "Nein"), QMessageBox.ButtonRole.NoRole
            )
            msg_box.exec()

            if progress_callback:
                progress_callback(100)
            if msg_box.clickedButton() == yes_btn:
                os.execl(sys.executable, sys.executable, *sys.argv)

        except Exception as e:
            action_log("update_download_failed", "error", error=str(e))
            QMessageBox.critical(
                self,
                "Update Error",
                f"Update fehlgeschlagen.\nDas Tool wurde (falls möglich) wiederhergestellt.\n\nFehler: {str(e)}",
            )
            if progress_callback:
                progress_callback(0)

    def ask_for_update(self, latest_version):
        lang = getattr(self, "LANG", "DE")
        lang_texts = TEXTS.get(lang, TEXTS.get("EN", {}))

        # Dialog erstellen
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(lang_texts.get("update_available_title", "Update"))

        # Text formatieren
        msg_template = lang_texts.get("update_available_msg", "Update {latest}?")
        message = msg_template.format(current=APP_VERSION, latest=latest_version)
        msg_box.setText(message)

        # Buttons manuell hinzufügen und übersetzen
        # Wir nehmen die Texte "yes" und "no" aus deinem TEXTS-Dictionary
        yes_text = lang_texts.get("yes", "Ja")
        no_text = lang_texts.get("no", "Nein")

        yes_button = msg_box.addButton(yes_text, QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton(no_text, QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(yes_button)

        msg_box.exec()

        if msg_box.clickedButton() == yes_button:
            if hasattr(self, "plugin_update_action"):
                self.plugin_update_action(latest_version)

    # ======= HIER EINSETZEN =======
    def create_action_button(
        self,
        parent,
        text,
        color,
        callback,
        all_buttons_list,
        fg="white",
        factor_hover=1.15,
        factor_pressed=0.85,
        min_height=50,  # Erhöht auf 50 für bessere Sichtbarkeit der Icons
        radius=10,
        icon_name=None,
    ):
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize
        from PyQt6.QtWidgets import QStyle, QSizePolicy

        # Zeilenumbruch bei langen Texten für bessere Zentrierung mit Icon
        display_text = text.replace(" ", "\n") if len(text) > 12 else text
        btn = QPushButton(display_text, parent)

        # --- ICON LOGIK (WINDOWS & LINUX SAFE) ---
        if icon_name and isinstance(icon_name, str):
            icon = QIcon()
            if icon_name.startswith("SP_"):
                # Nutzt die systemeigenen Icons von Windows/Linux
                p_enum = getattr(QStyle.StandardPixmap, icon_name, None)
                if p_enum:
                    icon = self.style().standardIcon(p_enum)
            elif os.path.exists(icon_name):
                # Nutzt eigenen Pfad falls vorhanden
                icon = QIcon(icon_name)

            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(24, 24))  # Etwas größer für bessere Optik

        # --- PHYSIK & GEOMETRIE ---
        btn.setMinimumHeight(min_height)
        btn.setMinimumWidth(120)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Farben berechnen
        hover_color = self.adjust_color(color, factor_hover)
        pressed_color = self.adjust_color(color, factor_pressed)

        # --- STYLESHEET (FIXIERT HÖHE GEGEN ÜBERSCHREIBEN) ---
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {color};
                color: {fg};
                border-radius: {radius}px;
                border: none; 
                padding: 5px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                height: {min_height}px;
                min-height: {min_height}px;
                max-height: {min_height}px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid white;
            }} 
            QPushButton:pressed {{
                background-color: {pressed_color};
            }} 
        """
        )

        if callback:
            btn.clicked.connect(callback)

        all_buttons_list.append(btn)
        return btn

    def generate_buttons(
        self, parent, button_definitions, all_buttons_list, info_widget=None
    ):
        """
        Erzeugt Buttons basierend auf einer Liste von Dictionaries.
        Unterstützt Icons und erzwingt plattformübergreifend gleiche Höhen.
        """
        buttons = {}
        # Standardwerte aus der Klasse laden oder Fallbacks nutzen
        def_height = getattr(self, "BUTTON_HEIGHT", 50)
        def_radius = getattr(self, "BUTTON_RADIUS", 10)

        for bd in button_definitions:
            # Falls kein Callback definiert ist, nutzen wir eine leere Funktion
            callback = bd.get("callback", lambda: None)

            btn = self.create_action_button(
                parent=parent,
                text=bd.get("text", "Button"),
                color=bd.get("color", "#444444"),
                callback=callback,
                all_buttons_list=all_buttons_list,
                fg=bd.get("fg", "white"),
                icon_name=bd.get("icon"),  # Übergibt z.B. "SP_ArrowDown"
                min_height=bd.get("min_height", def_height),
                radius=bd.get("radius", def_radius),
            )

            # Eindeutigen Key für das Dictionary bestimmen
            key = bd.get("key", bd.get("text", "unknown"))
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
        """Erstellt die mittleren Buttons mit dynamischer Farbumschaltung der Progressbar."""
        from PyQt6.QtWidgets import QGridLayout, QWidget, QSizePolicy
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import Qt

        # Button-Definitionen (unverändert)
        button_defs = [
            (
                "git_status",
                "git_status",
                "#1E90FF",
                self.show_commits,
                "white",
                "SP_FileDialogContentsView",
            ),
            (
                "plugin_update",
                "plugin_update",
                "#FF8C00",
                self.plugin_update_button_clicked,
                "white",
                "SP_ArrowDown",
            ),
            (
                "restart_tool",
                "restart_tool",
                "#FF4500",
                self.restart_application_with_info,
                "white",
                "SP_BrowserReload",
            ),
            (
                "edit_patch_header",
                "edit_patch_header",
                "#32CD32",
                self.edit_patch_header,
                "white",
                "SP_FileDialogDetailedView",
            ),
            (
                "github_emu_config",
                "github_emu_config_button",
                "#FFA500",
                self.edit_emu_github_config,
                "black",
                "SP_ComputerIcon",
            ),
            (
                "github_upload_patch",
                "github_upload_patch",
                "#1E90FF",
                github_upload_patch_file,
                "white",
                "SP_ArrowUp",
            ),
            (
                "github_upload_emu",
                "github_upload_emu",
                "#1E90FF",
                github_upload_oscam_emu_folder,
                "white",
                "SP_ArrowUp",
            ),
            (
                "oscam_emu_git_patch",
                "oscam_emu_git_patch",
                "#32CD32",
                patch_oscam_emu_git,
                "white",
                "SP_DialogApplyButton",
            ),
            (
                "oscam_emu_git_clear",
                "oscam_emu_git_clear",
                "#FF4500",
                self.oscam_emu_git_clear,
                "white",
                "SP_TrashIcon",
            ),
            ("terminal", "Terminal", "#FFA500", self.open_terminal, "black"),
        ]

        container = QWidget()
        options_grid = QGridLayout(container)
        options_grid.setSpacing(6)
        options_grid.setContentsMargins(0, 5, 0, 5)

        self.option_buttons = getattr(self, "option_buttons", {})
        cols_per_row = 5
        FLACH_HEIGHT = 45

        for idx, (key, text_key, color, callback, *rest) in enumerate(button_defs):
            current_fg = rest[0] if len(rest) > 0 else "white"
            current_icon = rest[1] if len(rest) > 1 else None
            raw_text = self.get_t(text_key, text_key)

            # --- LOGIK: Progressbar Farbe umschalten & Funktion ausführen ---
            def create_cb(c, k=key):
                def wrapper():
                    is_upload = "github_upload" in k
                    if hasattr(self, "set_progress_style"):
                        self.set_progress_style("upload" if is_upload else "default")

                    if hasattr(c, "__self__"):
                        c()
                    else:
                        callback_func = (
                            self.upload_progress_with_speed
                            if is_upload
                            else self.progress_bar.setValue
                        )
                        c(
                            gui_instance=self,
                            info_widget=self.info_text,
                            progress_callback=callback_func,
                        )

                return wrapper

            btn = self.create_action_button(
                parent=self,
                text=raw_text,
                color=color,
                callback=create_cb(callback),
                all_buttons_list=self.all_buttons,
                fg=current_fg,
                icon_name=current_icon,
                min_height=FLACH_HEIGHT,
                radius=self.BUTTON_RADIUS if hasattr(self, "BUTTON_RADIUS") else 10,
            )

            # --- OPTIMIERUNG FÜR LESBARKEIT ---
            # Wir nutzen MinimumExpanding, damit der Button bei Bedarf höher werden darf
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding
            )
            btn.setMinimumHeight(FLACH_HEIGHT)
            # WICHTIG: setMinimumHeight entfernen, damit der Button wachsen kann!

            # Etwas kleinere Schrift (10 statt 11), damit deutsche Wörter besser passen
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
        """Erstellt ein ZIP des Patches und zeigt den Status im Infoscreen an."""
        from PyQt6.QtWidgets import QTextEdit, QApplication
        import zipfile
        import os
        import platform
        import subprocess

        # SICHERHEITS-CHECK: Widget erzwingen
        widget = info_widget
        if not isinstance(widget, QTextEdit):
            widget = getattr(self, "info_text", None)

        # Sprache sicherstellen
        lang = getattr(self, "LANG", "DE").lower()

        # Hilfsfunktion für die Texte
        def get_msg(key, default, **kwargs):
            template = TEXTS.get(lang, {}).get(key, default)
            try:
                return template.format(**kwargs)
            except:
                return template

        # Hilfsfunktion für den Sound (JETZT KORREKT EINGERÜCKT)
        def play_zip_sound(success=True):
            """Spielt Sound für das Zippen ab (Absturzsicher via safe_play)."""
            safe_play("complete.oga" if success else "dialog-error.oga")

        # --- Eigentliche ZIP-Logik ---
        try:
            # 1. Existenzprüfung
            if not os.path.exists(PATCH_FILE):
                msg = get_msg(
                    "patch_file_missing",
                    "Datei nicht gefunden: {path}",
                    path=PATCH_FILE,
                )
                self.append_info(widget, msg, "error")
                play_zip_sound(False)
                return

            # 2. Zippen
            with zipfile.ZipFile(
                ZIP_FILE, "w", compression=zipfile.ZIP_DEFLATED
            ) as zipf:
                zipf.write(PATCH_FILE, os.path.basename(PATCH_FILE))

            # 3. Erfolgsmeldung
            msg = get_msg(
                "zip_success",
                "✅ Patch erfolgreich gepackt: {zip_file}",
                zip_file=ZIP_FILE,
            )
            self.append_info(widget, msg, "success")
            play_zip_sound(True)

        except Exception as e:
            msg = get_msg("zip_failed", "❌ Fehler beim Zippen: {error}", error=str(e))
            self.append_info(widget, msg, "error")
            play_zip_sound(False)

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
        Ändert den Speicherort des alten Patch-Ordners.
        Meldungen werden ins Info-Widget geschrieben oder auf die Konsole.
        """
        # Fallback auf Widget
        widget = info_widget or getattr(self, "info_text", None)

        # Logger-Funktion
        def log(text, level="info"):
            colors = {
                "success": "green",
                "warning": "orange",
                "error": "red",
                "info": "gray",
            }
            color = colors.get(level, "gray")
            if widget and hasattr(self, "append_info"):
                self.append_info(widget, text, level)
            elif widget and hasattr(widget, "append") and hasattr(widget, "moveCursor"):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.End)
            else:
                print(f"[{level.upper()}] {text}")

        # QFileDialog öffnen, Ausgangsordner = aktueller Pfad
        start_dir = getattr(self, "OLD_PATCH_DIR", OLD_PATCH_DIR_PLUGIN_DEFAULT)
        new_dir = QFileDialog.getExistingDirectory(
            self, "Select S3 Patch Folder", start_dir
        )

        if new_dir:
            # Instanzvariablen setzen
            self.OLD_PATCH_DIR = new_dir
            self.OLD_PATCH_FILE = os.path.join(new_dir, "oscam-emu.patch")
            self.ALT_PATCH_FILE = os.path.join(new_dir, "oscam-emu.altpatch")
            self.PATCH_MANAGER_OLD = os.path.join(new_dir, "oscam_patch_manager_old.py")
            self.CONFIG_OLD = os.path.join(new_dir, "config_old.json")
            self.GITHUB_CONFIG_OLD = os.path.join(
                new_dir, "github_upload_config_old.json"
            )

            # Config aktualisieren und speichern
            self.cfg["s3_patch_path"] = new_dir
            try:
                with open("config.json", "w") as f:
                    json.dump(self.cfg, f, indent=2)
                log(f"✅ Alter Patch-Ordner geändert: {new_dir}", "success")
            except Exception as e:
                log(f"❌ Fehler beim Speichern der Config: {e}", "error")
        else:
            log("ℹ️ Änderung des Patch-Ordners abgebrochen", "info")

        if progress_callback:
            progress_callback(100)

    def update_ui_texts(self):
        """Zentrale Text- und Icon-Aktualisierung."""
        from PyQt6.QtWidgets import QApplication, QStyle
        from PyQt6.QtCore import QSize
        import re

        # Sprache sicherstellen (String-Formatierung)
        lang = str(getattr(self, "LANG", "de")).lower()[:2]

        # Diese Funktion MUSS eingerückt innerhalb von update_ui_texts stehen
        def apply_final_style(btn, text, standard_pixmap):
            if not btn: 
                return
            
            # 1. Emojis strippen
            clean_text = re.sub(r'[^\x00-\x7F\xc0-\xff\s\.\,\:\-\_\!\?]+', '', str(text)).strip()
            
            # 2. Textumbruch für FlowLayout
            if len(clean_text) > 18 and " " in clean_text:
                 clean_text = clean_text.replace(" ", "\n", 1)
            
            btn.setText(clean_text)
            
            # 3. System-Icon setzen
            btn.setIcon(QApplication.style().standardIcon(standard_pixmap))
            btn.setIconSize(QSize(20, 20))
            
            # 4. Styling & Layout
            btn.setMinimumSize(185, 48)
            btn.setStyleSheet("text-align: left; padding-left: 8px; font-weight: bold;")

        # --- Alle Aufrufe müssen exakt so weit eingerückt sein wie 'apply_final_style' ---
        
        # REIHE 1 & 2
        apply_final_style(self.btn_open_work, "Arbeitsordner" if lang == "de" else "Work Folder", QStyle.StandardPixmap.SP_DirIcon)
        apply_final_style(self.btn_open_temp, "Temp-Repo", QStyle.StandardPixmap.SP_DirIcon)
        apply_final_style(self.btn_open_emu, "Emu-Git", QStyle.StandardPixmap.SP_DirIcon)

        apply_final_style(self.btn_check_tools, "Tools prüfen" if lang == "de" else "Check Tools", QStyle.StandardPixmap.SP_ComputerIcon)
        apply_final_style(self.btn_modifier, "Patch Autor" if lang == "de" else "Patch Author", QStyle.StandardPixmap.SP_FileDialogDetailedView)
        apply_final_style(self.btn_repo_url, "Repo URL", QStyle.StandardPixmap.SP_DriveNetIcon)
        apply_final_style(self.btn_check_commit, "Commit Check" if lang == "de" else "Check Commit", QStyle.StandardPixmap.SP_BrowserReload)

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

        # Header / Labels
        if hasattr(self, "lang_label"):
            label_text = "Sprache:" if lang == "de" else "Language:"
            self.lang_label.setText(f"🌐 {label_text}")
        
        QApplication.processEvents()

    def edit_patch_header(self, info_widget=None, progress_callback=None):
        """Öffnet den Header-Editor."""
        import os
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QMessageBox
        
        p_file = getattr(self, "PATCH_FILE", "oscam-emu.patch")
        if not os.path.exists(p_file): return

        dlg = QDialog(self)
        dlg.setWindowTitle("Patch-Header")
        dlg.resize(800, 600)
        ly = QVBoxLayout(dlg)
        edit = QTextEdit()
        try:
            with open(p_file, "r", encoding="utf-8", errors="ignore") as f:
                edit.setPlainText(f.read())
        except: return
        ly.addWidget(edit)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        ly.addWidget(bb)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            with open(p_file, "w", encoding="utf-8") as f:
                f.write(edit.toPlainText())

        def handle_save():
            try:
                with open(patch_file, "w", encoding="utf-8") as f:
                    f.write(text_edit.toPlainText())
                if "safe_play" in globals():
                    globals()["safe_play"]("dialog-information.oga")
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen: {e}")

        btns.accepted.connect(handle_save)
        btns.rejected.connect(dialog.reject)
        
        if "safe_play" in globals():
            globals()["safe_play"]("dialog-information.oga")
            
        dialog.exec()

        def play_header_sound(sound_type="open"):
            """Spielt Sounds für den Editor-Dialog ab (Absturzsicher via safe_play)."""
            # Sound-Datei basierend auf dem Typ wählen
            sound = "dialog-information.oga" if sound_type == "open" else "complete.oga"

            # Die globale Sicherheits-Funktion nutzen
            safe_play(sound)

        # Get language texts
        lang_dict = TEXTS.get(getattr(self, "LANG", "en").lower(), TEXTS.get("en", {}))

        # Load patch file
        patch_content = ""
        try:
            if not os.path.exists(PATCH_FILE):
                raise FileNotFoundError(PATCH_FILE)
            with open(PATCH_FILE, "r", encoding="utf-8") as f:
                patch_content = f.read()
        except Exception as e:
            error_msg = lang_dict.get(
                "error_open_patch_file", "❌ Fehler beim Öffnen der Patch-Datei:"
            )
            log(f"{error_msg} {e}", "error")
            if progress_callback:
                progress_callback(100)
            return

        # --- EDITOR DIALOG ---
        play_header_sound("open")  # Sound beim Öffnen
        editor = QDialog(self)
        editor.setWindowTitle(
            lang_dict.get("edit_patch_header_title", "Edit Patch Header")
        )
        editor.resize(800, 600)
        layout = QVBoxLayout(editor)

        text_edit = QTextEdit()
        text_edit.setFont(QFont("Courier", 11))
        text_edit.setText(patch_content)
        layout.addWidget(text_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)

        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save_btn.setText(lang_dict.get("save", "Save"))
        cancel_btn.setText(lang_dict.get("cancel", "Cancel"))

        def save_and_close():
            try:
                with open(PATCH_FILE, "w", encoding="utf-8") as f:
                    f.write(text_edit.toPlainText())
                success_msg = lang_dict.get(
                    "patch_saved_successfully", "✅ Patch file saved successfully"
                )
                log(success_msg, "success")
                play_header_sound("save")  # Sound beim erfolgreichen Speichern
            except Exception as e:
                error_msg = lang_dict.get(
                    "error_saving_patch_file", "❌ Error saving patch file:"
                )
                log(f"{error_msg} {e}", "error")
            editor.accept()
            if progress_callback:
                progress_callback(100)

        def cancel_and_close():
            editor.reject()
            if progress_callback:
                progress_callback(100)

        save_btn.clicked.connect(save_and_close)
        cancel_btn.clicked.connect(cancel_and_close)

        editor.exec()

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
        Geprüfter Update-Callback: Vergleicht Versionen präzise und behebt den Hover-Effekt.
        """
        from PyQt6.QtWidgets import QTextEdit, QApplication, QMessageBox
        from PyQt6.QtGui import QTextCursor
        import requests, time

        # Sicherstellen, dass die Version-Klasse verfügbar ist
        try:
            from packaging.version import Version
        except ImportError:

            class Version:
                def __init__(self, v):
                    # Säubert Strings wie '2.6.5\n' zu [2, 6, 5]
                    self.v = [
                        int(x)
                        for x in str(v).replace("v", "").strip().split(".")
                        if x.strip().isdigit()
                    ]

                def __gt__(self, other):
                    return self.v > other.v

                def __lt__(self, other):
                    return self.v < other.v

                def __eq__(self, other):
                    return self.v == other.v

        lang_key = getattr(self, "LANG", "en").lower()
        widget = info_widget or getattr(self, "info_text", None)
        progress = progress_callback or (
            self.progress_bar.setValue if hasattr(self, "progress_bar") else None
        )

        if hasattr(self, "progress_bar"):
            self.progress_bar.setValue(0)
            self.progress_bar.show()

        def log(text_key, level="info", **kwargs):
            colors = {
                "success": "green",
                "warning": "orange",
                "error": "red",
                "info": "blue",
            }
            color = colors.get(level, "gray")
            # Hole Template aus globaler TEXTS Struktur
            text_template = TEXTS.get(lang_key, TEXTS.get("en", {})).get(
                text_key, text_key
            )
            try:
                safe_kwargs = {
                    "current": APP_VERSION,
                    "latest": getattr(self, "latest_version", "???"),
                }
                safe_kwargs.update(kwargs)
                text = text_template.format(**safe_kwargs)
            except:
                text = text_template

            if isinstance(widget, QTextEdit):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.MoveOperation.End)
                QApplication.processEvents()

        log("update_check_start", "info")
        if progress:
            progress(20)

        try:
            # FIX: Syntaxfehler behoben (Klammer geschlossen) und Zeitstempel für Cache-Bypass
            version_url = (
                "https://raw.githubusercontent.com/"
                "speedy005/Oscam-Emu-patch-Manager/main/version.txt"
                f"?t={int(time.time())}"
            )

            resp = requests.get(version_url, timeout=10)
            resp.raise_for_status()

            # Versionen extrem sauber strippen
            latest_str = resp.text.strip().lower().replace("v", "").strip()
            current_str = APP_VERSION.strip().lower().replace("v", "").strip()

            self.latest_version = latest_str
            v_latest = Version(latest_str)
            v_current = Version(current_str)

            if progress:
                progress(60)

            # --- PRÄZISER VERGLEICH ---
            # Nur fortfahren, wenn Online-Version ECHTE Nummer größer als Lokal
            if v_latest > v_current:
                # UPDATE VERFÜGBAR
                if progress:
                    progress(80)
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setWindowTitle(
                    TEXTS.get(lang_key, TEXTS["en"]).get(
                        "update_available_title", "Update"
                    )
                )

                raw_msg = TEXTS.get(lang_key, TEXTS["en"]).get(
                    "update_available_msg",
                    "Neu: {latest} (Aktuell: {current}). Update?",
                )
                msg_box.setText(raw_msg.format(current=APP_VERSION, latest=latest_str))
                msg_box.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                # Buttons übersetzen
                btn_y = msg_box.button(QMessageBox.StandardButton.Yes)
                if btn_y:
                    btn_y.setText(TEXTS.get(lang_key, {}).get("yes", "Ja"))
                btn_no = msg_box.button(QMessageBox.StandardButton.No)
                if btn_no:
                    btn_no.setText(TEXTS.get(lang_key, {}).get("no", "Nein"))

                if msg_box.exec() == QMessageBox.StandardButton.Yes:
                    if hasattr(self, "plugin_update_action"):
                        self.plugin_update_action(
                            latest_version=latest_str, progress_callback=progress
                        )
                else:
                    log("update_declined", "info")
                    if progress:
                        progress(100)
            else:
                # KEIN UPDATE (Version ist gleich oder lokal sogar neuer)
                msg_templ = TEXTS.get(lang_key, TEXTS["en"]).get(
                    "up_to_date", "Plugin aktuell (v{v})"
                )
                QMessageBox.information(self, "Update", msg_templ.format(v=APP_VERSION))
                log("update_no_update", "success")
                if progress:
                    progress(100)

        except Exception as e:
            log("update_fail", "error", error=str(e))
            if progress:
                progress(0)

        # --- FINALER HOVER & COLOR FIX ---
        # Stellt sicher, dass nach dem Dialog alle Buttons (auch btn_check_commit)
        # ihr korrektes Design zurückerhalten.
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

        v_url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/version.txt"

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

    def check_for_plugin_update(self):
        """Prüft auf Updates und gibt das Ergebnis aus."""
        import requests

        lang = str(getattr(self, "LANG", "de")).lower()
        t = globals().get("TEXTS", {}).get(lang, {})
        widget = getattr(self, "info_text", None)

        try:
            version_url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/version.txt"
            resp = requests.get(version_url, timeout=10)
            resp.raise_for_status()

            latest_v_str = resp.text.strip().lstrip("v")
            current_v_str = APP_VERSION.strip().lstrip("v")
            lv, cv = Version(latest_v_str), Version(current_v_str)

            if lv > cv:
                msg = t.get("update_available", "⚠️ Update verfügbar: {latest}").format(
                    latest=latest_v_str
                )
                tag = "warning"
            else:
                msg = f"✅ Plugin ist aktuell (Version: {current_v_str})"
                tag = "success"

            # Ausgabe ins Log
            self.append_info(widget, msg, tag)

        except Exception as e:
            self.append_info(widget, f"Update-Fehler: {str(e)}", "error")

    def run_full_system_check(self, clear_log=False):
        """
        Vollständiger System-Check: Fette, zweifarbige Zeilen und bunter Footer am Ende.
        """
        if getattr(self, "_checking_active", False):
            return
        self._checking_active = True
        self._update_dialog_active = False

        try:
            import shutil, platform, socket
            from datetime import datetime
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QTextCursor

            # --- STYLE KONFIGURATION ---
            SZ_BIG, SZ_NORM = "26px", "21px"
            F_FAMILY = "'Segoe UI', Tahoma, sans-serif"
            F_MONO = "'Consolas', 'Courier New', monospace"

            # Farbcodes
            C_ORANGE = "#F37804"  # Titel
            C_GREEN = "#00FF00"  # Erfolg / Namen
            C_BLUE = "#00ADFF"  # Status / Version
            C_YELLOW = "#FFFF00"  # Versions-Nummer
            C_RED = "#FF0000"  # Fehler / Autor / Lizenz
            C_LINE = "#808080"  # Trenner
            C_ERR = C_RED  # FIX: C_ERR definieren!

            # 2. LOG-FENSTER VORBEREITEN
            if hasattr(self, "info_text") and self.info_text:
                if clear_log:
                    self.info_text.clear()
                else:
                    self.info_text.moveCursor(QTextCursor.MoveOperation.End)
                    self.info_text.insertHtml(
                        "<div style='font-size:4px;'>&nbsp;</div>"
                    )
                QApplication.processEvents()

            if "safe_play" in globals():
                safe_play("dialog-information.oga")

            # Sicherer Zugriff auf Übersetzungen
            lang = getattr(self, "LANG", "de").lower()
            version = globals().get("APP_VERSION", "2.8.4")
            # FIX: Nutze self.TEXT statt globals().get("TEXTS")
            txt = getattr(self, "TEXT", {})

            timestamp = datetime.now().strftime("%H:%M:%S")
            output = []

            # --- BLOCK 1: START & TOOLS ---
            start_msg = txt.get("start_check", "Starte System-Check...")
            output.append(
                f'<div style="line-height:1.1;"><span style="font-family:{F_FAMILY}; font-size:{SZ_BIG}; color:{C_ORANGE}"><b>{start_msg} [{timestamp}]</b></span></div>'
            )

            tools = ["git"]
            if platform.system() != "Windows":
                tools += ["patch", "zip"]

            for name in tools:
                found = shutil.which(name)
                prefix_color = C_GREEN if found else C_ERR
                icon = "✅" if found else "❌"
                status = (
                    txt.get("found", "gefunden")
                    if found
                    else txt.get("missing", "FEHLT!")
                )

                line = (
                    f'<div style="line-height:1.1;">'
                    f'<span style="font-family:{F_MONO}; font-size:{SZ_NORM}; color:{prefix_color}"><b>  {icon} {name.ljust(6)} : </b></span>'
                    f'<span style="font-family:{F_MONO}; font-size:{SZ_NORM}; color:{C_BLUE}"><b>{status}</b></span>'
                    f"</div>"
                )
                output.append(line)

            # --- BLOCK 2: INTERNET-CHECK ---
            output.append(
                f'<div style="line-height:1.0; color:{C_LINE}">{"." * 45}</div>'
            )
            net_msg = txt.get("net_check", "Prüfe Internetverbindung...")
            output.append(
                f'<div style="line-height:1.1;"><span style="font-family:{F_FAMILY}; font-size:{SZ_NORM}; color:{C_BLUE}"><b>🔍 {net_msg}</b></span></div>'
            )

            net_status_key = "Offline"
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=2)
                net_status_text, net_status_key, net_prefix_col, net_icon = (
                    txt.get("net_online", "Online"),
                    "Online",
                    C_GREEN,
                    "✅",
                )
            except:
                net_status_text, net_prefix_col, net_icon = (
                    txt.get("net_offline", "Offline"),
                    C_ERR,
                    "❌",
                )

            output.append(
                f'<div style="line-height:1.1;">'
                f'<span style="font-family:{F_MONO}; font-size:{SZ_NORM}; color:{net_prefix_col}"><b>  {net_icon} Status : </b></span>'
                f'<span style="font-family:{F_MONO}; font-size:{SZ_NORM}; color:{C_BLUE}"><b>{net_status_text}</b></span>'
                f"</div>"
            )
            output.append(
                f'<div style="line-height:1.0; color:{C_LINE}">{"-" * 45}</div>'
            )

            # --- BLOCK 3: UPDATE TITEL & FOOTER ---
            upd_title = txt.get("upd_check", "🔍 Tooltest Update Check...")
            output.append(
                f'<div style="line-height:1.1;"><span style="font-family:{F_FAMILY}; font-size:{SZ_BIG}; color:{C_ORANGE}"><b>{upd_title}</b></span></div>'
            )

            footer_line = (
                f'<div style="font-family:{F_FAMILY}; font-size:{SZ_NORM}; margin-top: 4px; line-height:1.2;">'
                f'<span style="color:{C_RED};"><b>Autor:</b></span> <span style="color:{C_GREEN};"><b>speedy005</b></span> | '
                f'<span style="color:{C_BLUE};"><b>Version:</b></span> <span style="color:{C_YELLOW};"><b>{version}</b></span> | '
                f'<span style="color:{C_RED};"><b>Lizenz:</b></span> <span style="color:{C_GREEN};"><b>MIT</b></span>'
                f"</div>"
            )
            output.append(footer_line)

            # HTML-Ausgabe senden
            self.append_info(self.info_text, "".join(output), "raw")

            # --- ÜBERGABE AN UPDATE-CHECK ---
            from PyQt6.QtCore import QTimer

            if (
                hasattr(self, "check_for_update_on_start")
                and net_status_key == "Online"
            ):
                QTimer.singleShot(200, self.check_for_update_on_start)
            elif net_status_key == "Offline":
                skip_msg = (
                    "⚠️ Update-Check übersprungen (Offline)"
                    if lang == "de"
                    else "⚠️ Update check skipped (Offline)"
                )
                self.append_info(
                    self.info_text,
                    f'<br><span style="color:{C_ORANGE}"><b>{skip_msg}</b></span>',
                    "raw",
                )

        except Exception as e:
            print(f"DEBUG Error in system check: {e}")
            if hasattr(self, "append_info"):
                self.append_info(
                    getattr(self, "info_text", None), f"❌ Error: {str(e)}", "error"
                )
        finally:
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(1000, lambda: setattr(self, "_checking_active", False))

    def closeEvent(self, event):
        """Wird ausgelöst, wenn das Fenster geschlossen wird (Absturzsicher)."""
        # Die globale Funktion safe_play übernimmt alle Prüfungen
        # (Linux-Check, paplay-Check) automatisch für uns.
        safe_play("service-logout.oga")

        # Das Fenster-Event akzeptieren, um das Programm sauber zu beenden
        event.accept()

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
            QMessageBox,
        )
        from PyQt6.QtGui import QPixmap, QFont
        from PyQt6.QtCore import Qt, QSize, QTimer, QDateTime
        import subprocess
        import os
        import requests

        # ---------------------------------------------------------
        # 1. Grundwerte
        # ---------------------------------------------------------
        self.TITLE_HEIGHT = 45
        self.BUTTON_HEIGHT = 45 # <-- Von 40 auf 60 erhöhen
        self.BUTTON_RADIUS = 10

        # Hilfsvariablen für deine Buttons unten (damit die Namen stimmen)
        B_HEIGHT = self.BUTTON_HEIGHT
        B_WIDTH = 240
        CONTROL_HEIGHT = self.BUTTON_HEIGHT

        # ---------------------------------------------------------
        # Hauptlayout
        # ---------------------------------------------------------
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 0, 20, 10)

        # Setzt das gesamte Fenster auf Dunkelgrau
        self.setStyleSheet("background-color: #2F2F2F;")

        header_widget = QFrame()
        header_widget.setMinimumHeight(45)

        # Header Styles
        header_widget.setStyleSheet(
            """
            QFrame {
                background-color: #2F2F2F;
                border: 1px solid #444;
                border-radius: 10px;
            }
            QLabel {
                background-color: transparent;
                border: none;
            }
        """
        )

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 0, 15, 0)
        header_layout.setSpacing(10)

        # ---------------- LEFT: Info + Uhr/Daten ----------------
        left_header_container = QWidget()
        left_header_layout = QHBoxLayout(left_header_container)
        left_header_layout.setContentsMargins(0, 0, 0, 0)
        left_header_layout.setSpacing(10)
        left_header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Info-Button
        self.info_button = QPushButton()
        self.info_button.setFixedSize(45, 45)
        icon = self.style().standardIcon(
            QApplication.style().StandardPixmap.SP_MessageBoxInformation
        )
        self.info_button.setIcon(icon)
        self.info_button.setIconSize(QSize(28, 28))
        self.info_button.clicked.connect(self.show_info)
        left_header_layout.addWidget(self.info_button)

        # Uhr & Datum vertikal in eigenem Container
        time_date_container = QWidget()
        time_date_layout = QVBoxLayout(time_date_container)
        # 15px Abstand nach links zum Info-Button
        time_date_layout.setContentsMargins(15, 0, 0, 0)
        time_date_layout.setSpacing(2)
        # Der gesamte Block bleibt links
        time_date_layout.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        # Gemeinsame Schriftart: Fett und Größe 24
        bold_font = QFont("Segoe UI", 24)
        bold_font.setBold(True)

        # Uhrzeit-Label (Rot & Fett)
        self.digital_clock = QLabel("--:--:--")
        self.digital_clock.setFont(bold_font)
        self.digital_clock.setStyleSheet("color: red; font-weight: bold;")
        self.digital_clock.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        time_date_layout.addWidget(self.digital_clock)

        # Datum-Label (Grün & Fett)
        self.date_label = QLabel("--.--.----")
        self.date_label.setFont(bold_font)
        self.date_label.setStyleSheet("color: green; font-weight: bold;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        time_date_layout.addWidget(self.date_label)

        # Container korrekt setzen
        time_date_container.setLayout(time_date_layout)

        # Füge den Container der linken HBox hinzu
        left_header_layout.addWidget(time_date_container)

        # Linken Header dem Header-Layout hinzufügen
        header_layout.addWidget(left_header_container, 1)

        # ---------------- MIDDLE: Logo ----------------
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
            self.original_pixmap = None

        # ---------------- RIGHT: Version ----------------
        right_header_container = QWidget()
        right_header_layout = QVBoxLayout(right_header_container)
        right_header_layout.setContentsMargins(0, 0, 0, 0)
        right_header_layout.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )

        by_label = QLabel("by speedy005")
        by_label.setFont(QFont("Bold", 20, QFont.Weight.Bold))
        by_label.setStyleSheet("color: blue;")
        by_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        v_label = QLabel(f"v{APP_VERSION}")
        v_label.setFont(QFont("Bold", 20, QFont.Weight.Bold))
        v_label.setStyleSheet("color: red;")
        v_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        right_header_layout.addStretch(1)
        right_header_layout.addWidget(by_label)
        right_header_layout.addWidget(v_label)
        right_header_layout.addStretch(1)

        header_layout.addWidget(right_header_container, 1)

        # Header dem Hauptlayout hinzufügen
        main_layout.addWidget(header_widget)

        # ---------------------------------------------------------
        # INFO + PROGRESS
        # ---------------------------------------------------------
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFont(QFont("Courier", 12))

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

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)  # Höhe exakt auf 20px setzen
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Prozentanzeige in der Mitte aktivieren
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Style: Hintergrund dunkel, Fortschritt Orange/Grün, Schrift Weiß
        self.progress_bar.setStyleSheet("""
        QProgressBar {
            border: 1px solid #444;      /* kleiner Rahmen */
            border-radius: 8px;           /* kleiner Radius */
            background-color: #1A1A1A;
            color: white;
            text-align: center;
            font-weight: bold;
            font-size: 14px;
        }
        QProgressBar::chunk {
             background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 #F37804, stop:1 #FFD700);
            border-radius: 8px;           /* passt zum Bar-Radius */
        }
        """)
        main_layout.addWidget(self.progress_bar)

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
        controls_group_layout.setContentsMargins(15, 20, 15, 20)
        # Mehr Abstand zwischen Header und den Reglern
        controls_group_layout.setSpacing(15)

        translated_text = self.get_t("settings_header", "Einstellungen")
        self.controls_header = QLabel(translated_text)

        self.controls_header.setMinimumWidth(220)
        # OPTIMIERUNG: Header-Höhe von 28 auf 45 erhöht für mehr Präsenz
        self.controls_header.setMinimumHeight(45)
        self.controls_header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bg = current_diff_colors.get("bg", "#3a6ea5")
        fg = current_diff_colors.get("fg", "#FFFFFF")

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
        controls_layout.setContentsMargins(10, 10, 10, 10)
        controls_layout.setSpacing(15)

        # Nutze hier deine neue B_HEIGHT (z.B. 60), falls definiert, sonst BUTTON_HEIGHT
        CONTROL_HEIGHT = getattr(self, "B_HEIGHT", 45)

        control_style = f"""
        QComboBox, QSpinBox {{
            font-size: 18px;             /* Schrift in den Boxen vergrößert */
            border-radius: {self.BUTTON_RADIUS}px;
            border: 2px solid #555;      /* Deutlicherer Rand */
            padding: 4px 8px;
            color: white;
            background-color: #444;
            height: {CONTROL_HEIGHT}px;
        }}
        """

        def make_label(text):
            lbl = QLabel(text)
            lbl.setMinimumHeight(CONTROL_HEIGHT)

            # WICHTIG: Nutze die Variable 'fg' (Vordergrundfarbe des aktuellen Themes)
            lbl.setStyleSheet(
                f"""
                color: {fg}; 
                font-weight: bold; 
                font-size: 18px;
                background: transparent;
            """
            )

            lbl.setAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            )
            return lbl

        # --- Sprache-Dropdown Anpassung ---
        self.lang_label = make_label(self.get_t("language_label", "Sprache:"))
        self.language_box = QComboBox()
        self.language_box.addItems(["EN", "DE"])

        # WICHTIG: Höhe auf B_HEIGHT (60) setzen, Breite auf 100 erhöhen
        self.language_box.setFixedSize(60, B_HEIGHT)

        # Schriftgröße in der Box anpassen (passend zu den Buttons)
        self.language_box.setStyleSheet(
            f"""
            QComboBox {{
                background-color: #444444;
                color: white;
                font-weight: bold;
                font-size: 20px;
                border: 2px solid #555555;
                border-radius: 6px;
                padding-left: 10px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #FF0000; /* Roter Pfeil */
            }}
        """
        )

        saved_lang = self.cfg.get("language", "de").lower()
        if saved_lang == "en":
            self.language_box.setCurrentIndex(0)
        else:
            self.language_box.setCurrentIndex(1)

        self.language_box.currentIndexChanged.connect(self.change_language)

        saved_lang = self.cfg.get("language", "de").lower()

        if saved_lang == "en":
            self.language_box.setCurrentIndex(0)  # 0 ist EN
        else:
            self.language_box.setCurrentIndex(1)  # 1 ist DE

        self.language_box.currentIndexChanged.connect(self.change_language)

        self.color_label = make_label(self.get_t("color_label", "Farbe:"))
        self.color_box = QComboBox()
        self.color_box.addItems(list(DIFF_COLORS.keys()))
        saved_color = self.cfg.get("theme_color", "Classics")
        index = self.color_box.findText(saved_color)
        if index >= 0:
            self.color_box.setCurrentIndex(index)
        else:
            self.color_box.setCurrentIndex(0)
        self.color_box.setFixedSize(160, CONTROL_HEIGHT)
        self.color_box.setStyleSheet(control_style)
        self.color_box.currentIndexChanged.connect(self.change_colors)

        self.commit_label = make_label(self.get_t("commit_count_label", "Commits:"))
        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1, 20)
        self.commit_spin.setFixedSize(70, CONTROL_HEIGHT)
        saved_commits = self.cfg.get("commit_count", 10)
        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1, 20)
        # Wichtig: Breite auf 100, damit die 30px breiten Buttons Platz haben
        self.commit_spin.setFixedSize(60, CONTROL_HEIGHT)

        self.commit_spin.setStyleSheet(
            """
            QSpinBox {
                background-color: #222222;
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 6px;
            }
            /* Die seitlichen Klick-Flächen */
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #333333;
                width: 30px;
                border-left: 1px solid #555555;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #444444;
            }

            /* Der obere ROTE Pfeil */
            QSpinBox::up-arrow {
                width: 0px; height: 0px;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-bottom: 8px solid #FF0000; /* REINROT */
            }
            /* Der untere ROTE Pfeil */
            QSpinBox::down-arrow {
                width: 0px; height: 0px;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 8px solid #FF0000; /* REINROT */
            }
        """
        )

        saved_commits = self.cfg.get("commit_count", 10)
        self.commit_spin.setValue(saved_commits)
        self.commit_spin.valueChanged.connect(self.commit_value_changed)

        self.btn_check_tools = QPushButton(
            self.get_t("check_tools_button", "🛠️ Tools prüfen")
        )
        self.btn_check_tools.setFixedSize(220, 45)

        # --- 0. Container Erstellung (Korrektur: QGroupBox statt QFrame) ---
        controls_group = QGroupBox("Einstellungen")
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
        B_HEIGHT = 45
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
        self.btn_open_work.clicked.connect(lambda: self.open_custom_folder(PLUGIN_DIR))

        self.btn_open_temp = QPushButton(" Temp-Repo")
        self.btn_open_temp.setIcon(f_icon)
        self.btn_open_temp.setIconSize(QSize(I_SIZE, I_SIZE))
        self.btn_open_temp.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_open_temp.setStyleSheet(button_style)
        self.btn_open_temp.clicked.connect(lambda: self.open_custom_folder(TEMP_REPO))

        self.btn_open_emu = QPushButton(" Emu-Git")
        self.btn_open_emu.setIcon(f_icon)
        self.btn_open_emu.setIconSize(QSize(I_SIZE, I_SIZE))
        self.btn_open_emu.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_open_emu.setStyleSheet(button_style)
        self.btn_open_emu.clicked.connect(
            lambda: self.open_custom_folder(PATCH_EMU_GIT_DIR)
        )

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

        self.btn_check_commit = QPushButton("🔄 Commit Check")
        self.btn_check_commit.setIconSize(QSize(I_SIZE, I_SIZE))
        self.btn_check_commit.setFixedSize(B_WIDTH, B_HEIGHT)
        self.btn_check_commit.setStyleSheet(button_style)
        self.btn_check_commit.clicked.connect(self.check_for_new_commit)

        # --- 4. GRID-LAYOUT (Mittig optimiert) ---
        controls_group.setTitle("")
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(10, 5, 10, 5)
        grid_layout.setVerticalSpacing(10)
        grid_layout.setHorizontalSpacing(10)

        # Header für "Einstellungen" mit einem Icon
        self.controls_header = QWidget()  # Wir nutzen ein Widget, um das Label und das Icon zu halten
        header_layout = QHBoxLayout(self.controls_header)  # Layout für den Header erstellen

        # Erstelle das Label für "Einstellungen"
        self.header_label = QLabel(" Einstellungen" if self.LANG == "de" else " Settings") 
        self.controls_header.setMinimumHeight(self.BUTTON_HEIGHT)  # Setze die gleiche Höhe wie die anderen Buttons
        self.controls_header.setFixedWidth(200)  # Feste Breite für das Label
        self.header_label.setStyleSheet(
            "color: white; font-weight: bold; font-size: 20px; padding-left: 0px; background: transparent;" 
            # Hintergrundfarbe entfernt
        )

        # Erstelle das Icon (zum Beispiel ein Einstellungen-Icon)
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)  # Beispiel-Standardicon
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(28, 28))  # Setze die Größe des Icons (28x28)

        # Füge das Icon und das Label in das Layout hinzu
        header_layout.addWidget(icon_label)
        header_layout.addWidget(self.header_label)

        # Füge das Header-Widget zum Grid-Layout hinzu
        grid_layout.addWidget(self.controls_header, 0, 0, 1, 2)

        # Zeile 0: Ordner-Buttons (Oben rechts)
        grid_layout.addWidget(self.btn_open_work, 0, 6)
        grid_layout.addWidget(self.btn_open_temp, 0, 7)
        grid_layout.addWidget(self.btn_open_emu, 0, 8)

        # Zeile 1: Dropdowns & Funktions-Buttons (ALLES IN EINER ZEILE = MITTIG)
        grid_layout.addWidget(self.lang_label, 1, 0)
        grid_layout.addWidget(self.language_box, 1, 1)
        grid_layout.addWidget(self.color_label, 1, 2)
        grid_layout.addWidget(self.color_box, 1, 3)
        grid_layout.addWidget(self.commit_label, 1, 4)
        grid_layout.addWidget(self.commit_spin, 1, 5)

        # Rechte Seite (Funktionen - exakt daneben)
        grid_layout.addWidget(self.btn_check_tools, 1, 6)
        grid_layout.addWidget(self.btn_modifier, 1, 7)
        grid_layout.addWidget(self.btn_repo_url, 1, 8)
        grid_layout.addWidget(self.btn_check_commit, 1, 9)

        # Spalten-Stretch
        grid_layout.setColumnStretch(10, 1)

        # Layout dem Container zuweisen
        controls_group_layout.addLayout(grid_layout)

        # --- 5. Integration ---
        main_layout.addWidget(controls_group)

        # --- RECOVERY: Bringt die untere Sektion zurück ---
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
            self.digital_clock.setText(now.toString("HH:mm:ss"))
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
        QTimer.singleShot(1000, self.run_full_system_check)

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

    def check_for_new_commit(self):
        import requests
        import re
        from PyQt6.QtWidgets import QMessageBox

        # --- Aktuelle Sprach-Texte laden ---
        lang = getattr(self, "LANG", "de").lower()
        self.TEXT = globals().get("TEXTS", {}).get(lang, {})

        cyan, end = "<span style='color:cyan;'>", "</span>"
        mb_title = self.TEXT.get("check_commit_title", "OSCam Commit-Check")

        try:
            # 1. Seite abrufen (Master Branch)
            url = "https://git.streamboard.tv/common/oscam/-/commits/master"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()

            # 2. Den neuesten Commit-Hash finden (c656fef9...)
            m = re.search(r'data-commit-id="([a-f0-9]{40})"', resp.text)
            if not m:
                m = re.search(r"commit/([a-f0-9]{40})", resp.text)

            if not m:
                # SOUND: FEHLER
                safe_play("dialog-error.oga")
                msg = self.TEXT.get(
                    "check_commit_no_hash", "Fehler: Kein Commit-Hash gefunden."
                )
                self.log_message(f"<span style='color:orange;'>⚠️ {msg}</span>")
                QMessageBox.warning(self, mb_title, msg)
                return

            newest_hash = m.group(1)
            last_known = self.cfg.get("last_stream_commit", "")

            # --- FALL 1: ALLES AKTUELL ---
            if newest_hash == last_known:
                # SOUND: INFORMATION (wie beim Terminal öffnen)
                safe_play("dialog-information.oga")

                msg_up = self.TEXT.get(
                    "check_commit_up_to_date", "Kein neuer Commit vorhanden."
                )
                lbl_curr = self.TEXT.get("check_commit_current_hash", "Aktueller Hash:")

                self.log_message(f"{cyan}ℹ️ {msg_up} ({newest_hash[:7]}){end}")
                QMessageBox.information(
                    self, mb_title, f"{msg_up}\n\n{lbl_curr} {newest_hash[:8]}"
                )

            # --- FALL 2: NEUER COMMIT GEFUNDEN ---
            else:
                # SOUND: ERFOLG (Complete)
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

        except Exception as e:
            # SOUND: KRITISCHER FEHLER
            safe_play("dialog-error.oga")
            err_lbl = self.TEXT.get("check_commit_error", "Fehler beim Check:")
            self.log_message(f"<span style='color:red;'>❌ {err_lbl} {str(e)}</span>")
            QMessageBox.critical(self, mb_title, f"{err_lbl}\n{str(e)}")

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
        bg_color = current_diff_colors["bg"]
        hover_color = current_diff_colors.get("hover", bg_color)
        active_color = current_diff_colors.get("active", bg_color)

        # 1. Standard Button Style - JETZT MIT 45px HÖHE
        button_style = f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 10px;
                font-weight: bold;
                padding: 6px;
                font-size: 13px;
                border: none;
                height: 25px;      /* Festgelegte Höhe für Stylesheet */
                min-height: 25px;   /* Garantiert die 45px aus deinem Setup */
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid {text_color};
            }}
            QPushButton:pressed {{
                background-color: {active_color};
            }}
        """

        # A) Liste aller Funktions-Buttons
        main_buttons = [
            "edit_header_button",
            "commits_button",
            "clean_emu_button",
            "patch_emu_git_button",
            "github_upload_patch_button",
            "plugin_update_button",
            "restart_tool_button",
            "btn_check_tools",
            "btn_check_commit",
            "btn_modifier",
            "btn_repo_url",
            "btn_open_work",
            "btn_open_temp",
            "btn_open_emu",
        ]

        for btn_name in main_buttons:
            btn = getattr(self, btn_name, None)
            if btn:
                try:
                    btn.setGraphicsEffect(None)
                    btn.setStyleSheet(button_style)
                except RuntimeError:
                    continue

        # B) NEU: Speziell für die Option Buttons aus setup_option_buttons
        if hasattr(self, "option_buttons"):
            for btn_tuple in self.option_buttons.values():
                try:
                    # Da du (btn, text_key) speicherst, nehmen wir den ersten Index
                    btn_tuple[0].setStyleSheet(button_style)
                except (RuntimeError, TypeError, IndexError):
                    continue

        # C) Grid Buttons (alte Liste falls noch vorhanden)
        if hasattr(self, "buttons"):
            for btn in self.buttons.values():
                try:
                    btn.setStyleSheet(button_style)
                except RuntimeError:
                    continue

        # 2. Progressbar
        pb = getattr(self, "progress_bar", None)
        if pb:
            try:
                pb.setStyleSheet(
                    f"QProgressBar {{ border: 1px solid {bg_color}; border-radius: 7px; background-color: #1a1a1a; text-align: center; color: white; }}"
                    f"QProgressBar::chunk {{ background-color: {bg_color}; }}"
                )
            except RuntimeError:
                pass

        # 3. Header
        header = getattr(self, "controls_header", None)
        if header:
            try:
                header.setStyleSheet(
                    f"background-color: {bg_color}; color: {text_color}; font-weight: bold; border-radius: 6px; padding-left: 10px;"
                )
            except RuntimeError:
                pass

        # 5. Labels
        target_labels = ["lang_label", "color_label", "commit_label"]
        for lbl_name in target_labels:
            lbl = getattr(self, lbl_name, None)
            if lbl:
                try:
                    lbl.setStyleSheet(
                        f"color: {text_color}; font-weight: bold; font-size: 18px; background: transparent;"
                    )
                except RuntimeError:
                    pass

        # 4. Hauptfenster Style
        try:
            self.setStyleSheet("background-color: #2F2F2F;")
            self.repaint()
        except RuntimeError:
            pass

    def set_progress_style(self, mode="default"):
        """Wechselt die Farbe der Progressbar: default=Orange, upload=Blau."""
        color_chunk = "#F37804" if mode == "default" else "#00ADFF"
        color_end = "#FFD700" if mode == "default" else "#00FFFF"

        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 2px solid #444;
                border-radius: 10px;
                text-align: center;
                background-color: #1A1A1A;
                color: white;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                  stop:0 {color_chunk}, stop:1 {color_end});
                border-radius: 8px;
            }}
        """
        )

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
            ("patch_create", lambda: create_patch(self, self.info_text, self.progress_bar.setValue)),
            ("patch_renew", lambda: create_patch(self, self.info_text, self.progress_bar.setValue)),
            ("patch_check", lambda: self.check_patch(self.info_text, self.progress_bar.setValue)),
            ("patch_apply", lambda: (self.progress_bar.setValue(0) if hasattr(self, "progress_bar") else None, 
                                     self.apply_patch(self.info_text, self.progress_bar.setValue))),
            ("patch_zip", lambda: self.zip_patch(self.info_text, self.progress_bar.setValue)),
            ("backup_old", lambda: backup_old_patch(self, self.info_text, self.progress_bar.setValue)),
            ("clean_folder", lambda: clean_patch_folder(self, self.info_text, self.progress_bar.setValue)),
            ("change_old_dir", lambda: self.change_old_patch_dir(self.info_text, self.progress_bar.setValue)),
            ("exit", self.close_with_confirm),
        ]

        self.buttons = {}
        cols = 3
        FIXED_HEIGHT = 45

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
            btn.setStyleSheet(btn.styleSheet() + """
                padding-left: 12px; 
                padding-right: 12px; 
                text-align: left; 
                white-space: nowrap;
            """)

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
            " Arbeitsordner" if lang == "de" else " Work Folder",
        )
        safe_ui(
            "btn_open_temp", "setText", " Temp-Repo" if lang == "de" else " Temp Repo"
        )
        safe_ui("btn_open_emu", "setText", " Emu-Git" if lang == "de" else " Emu Git")

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
        Fix: Erzwingt Übersetzung von GroupBoxen UND dem speziellen Header-Label.
        """
        if not hasattr(self, "language_box"):
            return

        from PyQt6.QtWidgets import QApplication, QGroupBox, QLabel
        from PyQt6.QtCore import QTimer
        import re

        # Hilfsfunktion: Entfernt Emojis/Symbole am Anfang
        def strip_icons(text):
            return re.sub(r'^[^\w\s]+', '', str(text)).strip()

        # 1. SPRACHE ERMITTELN & SETZEN
        selected = self.language_box.currentText().upper()
        self.LANG = "en" if any(x in selected for x in ["EN", "ENG", "ENGLISH"]) else "de"
        
        # Globales Dictionary laden
        lang_dict = globals().get("TEXTS", {}).get(self.LANG, {})

        # 2. KONFIGURATION SPEICHERN
        if hasattr(self, "cfg"):
            self.cfg["language"] = self.LANG.upper()
            save_func = globals().get("save_config")
            if save_func:
                save_func(self.cfg, gui_instance=self, silent=True)

        # 3. BASIS-UI AKTUALISIEREN
        if hasattr(self, "update_language"):
            self.update_language()

        # --- FIX FÜR DAS SPEZIELLE HEADER-LABEL (Das mit dem Icon) ---
        if hasattr(self, "header_label"):
            new_header = lang_dict.get("settings_header", "Settings" if self.LANG == "en" else "Einstellungen")
            # Wir behalten das führende Leerzeichen für den Abstand zum Icon bei
            self.header_label.setText(f" {strip_icons(new_header)}")

        # --- UNIVERSAL-SCANNER: GroupBoxen ---
        for box in self.findChildren(QGroupBox):
            title = box.title()
            # Erkennt die Box, egal ob sie aktuell "Settings" oder "Einstellungen" heißt
            if any(word in title for word in ["Einstellungen", "Settings"]):
                box.setTitle(lang_dict.get("settings_header", "Settings" if self.LANG == "en" else "Einstellungen"))
            if any(word in title for word in ["GitHub", "Configuration", "Konfiguration"]):
                box.setTitle(lang_dict.get("github_config_header", "GitHub Configuration" if self.LANG == "en" else "GitHub Konfiguration"))

        # --- SPEZIFISCHE BUTTON-TEXTE & TOOLTIPS ---
        # A) Patch Autor Button
        if hasattr(self, "btn_modifier"):
            label = strip_icons(lang_dict.get("modifier_button_text", "Patch Author" if self.LANG == "en" else "Patch Autor"))
            self.btn_modifier.setText(f"👤 {label}")
            auth_name = getattr(self, "patch_modifier", "speedy005")
            tt_prefix = lang_dict.get("modifier_tooltip_prefix", "Author:" if self.LANG == "en" else "Autor:")
            self.btn_modifier.setToolTip(f"{tt_prefix} {auth_name}")

        # B) Repo URL Button
        if hasattr(self, "btn_repo_url"):
            label = strip_icons(lang_dict.get("repo_button_text", "Repo URL"))
            self.btn_repo_url.setText(f"🌐 {label}")
            curr_repo = getattr(self, "EMUREPO", "...")
            tt_prefix = lang_dict.get("repo_tooltip_prefix", "URL:")
            self.btn_repo_url.setToolTip(f"{tt_prefix} {curr_repo}")

        # C) Tools Prüfen Button
        if hasattr(self, "btn_check_tools"):
            label = strip_icons(lang_dict.get("check_tools_button", "Check Tools" if self.LANG == "en" else "Tools prüfen"))
            self.btn_check_tools.setText(f"🛠️ {label}")

        # 4. UI REFRESH (Farben & Sounds)
        if hasattr(self, "repaint_ui_colors"):
            self.repaint_ui_colors()

        safe_play_func = globals().get("safe_play")
        if safe_play_func:
            safe_play_func("dialog-information.oga")

        # 5. INFOSCREEN & LAYOUT SYNC
        if hasattr(self, "info_text") and self.info_text:
            self._checking_active = False
            self.info_text.clear()
        
        QApplication.processEvents()

        if hasattr(self, "show_welcome_info"):
            self.show_welcome_info()

        if hasattr(self, "run_full_system_check"):
            # 2 Sekunden Verzögerung für flüssigeres UI-Feeling
            QTimer.singleShot(2000, self.run_full_system_check)

        if self.layout():
            self.layout().activate()
    
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
        """Öffnet den GitHub-Konfigurationsdialog mit Sound-Feedback und Sicherheits-Fallbacks."""
        import os, subprocess, platform
        from PyQt6.QtWidgets import QFormLayout, QLabel, QDialogButtonBox, QApplication

        # 1. Sprache sicher abrufen
        current_lang = str(getattr(self, "LANG", "de")).lower()

        def play_config_sound(sound_type="open"):
            """Spielt Sounds für den Konfigurations-Dialog ab (Absturzsicher via safe_play)."""
            # Sound-Datei basierend auf dem Typ wählen
            sound = "dialog-information.oga" if sound_type == "open" else "complete.oga"

            # Die globale Sicherheits-Funktion nutzen
            safe_play(sound)

        # Dialog-Sound beim Öffnen
        play_config_sound("open")
        dialog = GithubConfigDialog(self)

        # 2. Hilfsfunktion für Texte
        def get_txt(key, default=""):
            try:
                lang_pkg = TEXTS.get(current_lang, TEXTS.get("de", {}))
                return lang_pkg.get(key, default)
            except:
                return default

        # 3. Titel des Dialogs setzen
        dialog.setWindowTitle(get_txt("github_dialog_title", "GitHub Configuration"))

        # 4. Labels im Dialog dynamisch übersetzen
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

        # 5. Save/Cancel Buttons übersetzen
        button_box = dialog.findChild(QDialogButtonBox)
        if button_box:
            save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
            cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
            if save_btn:
                save_btn.setText(get_txt("save", "Speichern"))
            if cancel_btn:
                cancel_btn.setText(get_txt("cancel", "Abbrechen"))

        # 6. Dialog ausführen
        if dialog.exec():
            msg = get_txt("github_config_saved", "GitHub Konfiguration gespeichert.")
            self.append_info(info_widget or self.info_text, msg, "success")
            play_config_sound("save")  # Sound beim erfolgreichen Speichern

        # 7. Progress-Bar Abschluss
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
        Zeigt die letzten Commits an.
        Nutzt run_command für sauberes Logging und spielt einen Sound bei Erfolg.
        """
        from PyQt6.QtWidgets import QTextEdit, QApplication
        import os, subprocess, platform

        # Widget absichern
        if not isinstance(info_widget, QTextEdit):
            info_widget = getattr(self, "info_text", None)
            if info_widget is None:
                return

        lang = getattr(self, "LANG", "en").lower()

        # Hilfsfunktion für den Sound (innerhalb der Methode definiert)
        def play_commit_sound(success=True):
            """Spielt Sound für Commits ab (Absturzsicher via safe_play)."""
            # Wir wählen die passende Datei und lassen safe_play den Rest machen
            safe_play("message-new-instant.oga" if success else "dialog-error.oga")

        # Texte aus dem Translation-Dictionary laden
        txt_loading = TEXTS.get(lang, {}).get("loading_commits", "Lade Commits...")
        txt_success = TEXTS.get(lang, {}).get(
            "commits_loaded", "Commits erfolgreich geladen"
        )

        # --- Startmeldung ---
        self.append_info(info_widget, txt_loading, "warning")

        try:
            if not os.path.exists(TEMP_REPO):
                self.append_info(
                    info_widget, f"❌ Ordner nicht gefunden: {TEMP_REPO}", "error"
                )
                play_commit_sound(False)
                return

            # Anzahl der Commits aus dem Spinbox-Widget lesen (falls vorhanden)
            num_commits = (
                self.commit_spin.value() if hasattr(self, "commit_spin") else 10
            )
            cmd = f"git log -n {num_commits} --oneline"

            # Befehl ausführen
            output = self.run_command(cmd, cwd=TEMP_REPO)

            if output:
                lines = output.splitlines()
                for line in lines:
                    self.append_info(info_widget, f"• {line}", "info")

                # Erfolgsmeldung & Sound
                self.append_info(
                    info_widget, f"✅ {txt_success} ({len(lines)})", "success"
                )
                play_commit_sound(True)
            else:
                self.append_info(
                    info_widget, "⚠ Keine Commits gefunden oder Git-Fehler.", "warning"
                )
                play_commit_sound(False)

        except Exception as e:
            self.append_info(
                info_widget, f"❌ Schwerer Fehler beim Commit-Abruf: {str(e)}", "error"
            )
            play_commit_sound(False)

        # Fortschrittsbalken auf 100% setzen
        if progress_callback:
            try:
                progress_callback(100)
            except:
                pass

    # ===================== OSCam-EMU BUTTON WRAPPERS =====================
    def oscam_emu_git_patch(self, info_widget=None, progress_callback=None):
        """Patch erstellen und auf GitHub hochladen mit Sound-Feedback."""
        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", "de").lower()

        self.append_info(
            info_widget,
            globals()
            .get("TEXTS", {})
            .get(lang, {})
            .get(
                "oscam_emu_git_patch_start", "🔹 OSCam-Emu Git Patch wird erstellt..."
            ),
            "info",
        )

        try:
            # Patch hochladen
            _github_upload(
                PATCH_EMU_GIT_DIR,
                load_github_config().get("emu_repo_url"),
                info_widget=info_widget,
            )

            # --- SOUND FEEDBACK BEI ERFOLG ---
            if "safe_play" in globals():
                safe_play("complete.oga")

        except Exception as e:
            self.append_info(info_widget, f"❌ Fehler beim Patch-Vorgang: {e}", "error")
            # --- SOUND FEEDBACK BEI FEHLER ---
            if "safe_play" in globals():
                safe_play("dialog-error.oga")

        if progress_callback:
            progress_callback(100)

    def oscam_emu_git_clear(self, info_widget=None, progress_callback=None):
        """Zentrales Logging für die Emu-Git Bereinigung mit Sound-Feedback."""
        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", "de")

        # 1. Start-Meldung
        start_msg = TEXTS[lang].get(
            "oscam_emu_git_clearing", "🔹 OSCam-Emu Git Ordner wird geleert..."
        )
        self.append_info(info_widget, start_msg, "info")

        # 2. Ausführung
        result = clean_oscam_emu_git(progress_callback=progress_callback)

        # 3. Ergebnis-Meldung & Sound-Trigger
        if result == "success":
            msg = TEXTS[lang].get(
                "oscam_emu_git_cleared", "✅ Bereinigung erfolgreich!"
            )
            self.append_info(info_widget, msg, "success")
            if "safe_play" in globals():
                safe_play("complete.oga")  # Erfolgssound

        elif result == "not_found":
            msg = "ℹ️ " + (
                "Ordner bereits leer." if lang == "de" else "Folder already empty."
            )
            self.append_info(info_widget, msg, "info")
            if "safe_play" in globals():
                safe_play("dialog-information.oga")  # Kurzer Info-Ton

        else:
            self.append_info(info_widget, "❌ Error during deletion", "error")
            if "safe_play" in globals():
                safe_play("dialog-error.oga")  # Fehlersound

        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()

    def check_patch(self, info_widget=None, progress_callback=None):
        """
        Prüft den Patch-Status sauber und einmalig.
        Inklusive akustischem Feedback bei Erfolg oder Fehler.
        """
        import os, subprocess, platform
        from PyQt6.QtWidgets import QApplication

        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", "de")

        def play_check_sound(success=True):
            """Spielt den passenden Sound für den Patch-Check (Absturzsicher via safe_play)."""
            # Sound-Datei basierend auf Erfolg oder Fehler wählen
            sound = "complete.oga" if success else "dialog-error.oga"

            # Die globale Sicherheits-Funktion nutzen
            safe_play(sound)

        # 1. Existenzprüfung der Datei
        if not os.path.exists(PATCH_FILE):
            err_msg = TEXTS[lang].get(
                "patch_file_missing", "❌ Patch-Datei nicht gefunden!"
            )
            self.append_info(info_widget, err_msg, "error")
            if progress_callback:
                progress_callback(0)
            play_check_sound(False)
            return

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
            ok_msg = TEXTS[lang].get("patch_check_ok", "✅ Patch-Check erfolgreich!")
            self.append_info(info_widget, ok_msg, "success")
            play_check_sound(True)
        else:
            fail_msg = TEXTS[lang].get(
                "patch_check_fail", "❌ Patch-Check fehlgeschlagen!"
            )
            self.append_info(info_widget, fail_msg, "error")
            play_check_sound(False)

        # 4. Abschluss
        if progress_callback:
            progress_callback(100)

        QApplication.processEvents()

    def apply_patch(self, info_widget=None, progress_callback=None):
        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", "de").lower()
        import os, subprocess, platform
        from PyQt6.QtWidgets import QApplication

        # Hilfsfunktion für den Sound (Absturzsicher)
        def play_apply_sound(success=True):
            """Spielt Sound nach dem Anwenden eines Patches ab (Absturzsicher via safe_play)."""
            # Bestimme die Datei und nutze die globale Sicherheits-Funktion
            safe_play("complete.oga" if success else "dialog-error.oga")

        # --- Eigentliche Patch-Logik ---

        # 1. Check ob Patch-Datei existiert
        if not os.path.exists(PATCH_FILE):
            msg = self.get_t("patch_file_missing", "❌ Patch-Datei fehlt!").format(
                path=PATCH_FILE
            )
            self.append_info(info_widget, msg, "error")
            play_apply_sound(False)
            return

        # Logger definieren für run_bash
        logger = lambda text, level="info": self.append_info(info_widget, text, level)

        # 2. Start-Meldung
        start_msg = self.get_t("executing_git_apply", "🚀 Wende Patch an...").format(
            patch="oscam-emu.patch"
        )
        self.append_info(info_widget, start_msg, "warning")

        # 3. Patch ausführen
        try:
            # Code führt den Befehl aus und gibt den Exit-Status zurück
            code = run_bash(f"git apply {PATCH_FILE}", cwd=TEMP_REPO, logger=logger)

            if code == 0:
                self.append_info(
                    info_widget,
                    self.get_t("patch_emu_git_done", "✅ Patch erfolgreich angewendet"),
                    "success",
                )
                play_apply_sound(True)
            else:
                self.append_info(
                    info_widget,
                    self.get_t("patch_emu_git_apply_failed", "❌ Patch fehlgeschlagen"),
                    "error",
                )
                play_apply_sound(False)
        except Exception as e:
            self.append_info(
                info_widget, f"❌ Schwerer Fehler beim Patchen: {str(e)}", "error"
            )
            play_apply_sound(False)

        if progress_callback:
            try:
                progress_callback(100)
            except:
                pass

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


# ===================== __main__ =====================
if __name__ == "__main__":
    # ⚡ Macht das Script ausführbar
    ensure_executable_self()

    # 1️⃣ Python-Abhängigkeiten prüfen (BEVOR die GUI-Klasse geladen wird!)
    REQUIRED_PY_PKGS = ["requests", "packaging", "PyQt6"]
    # Falls installiert wurde, startet os.execv das Skript hier bereits neu
    if check_and_install_dependencies(REQUIRED_PY_PKGS):
        sys.exit(0)

    # Standard-Imports
    import sys
    import os
    from PyQt6.QtWidgets import QApplication

    # ⚠️ Verhindert Accessibility-Warnungen unter Linux
    os.environ["NO_AT_BRIDGE"] = "1"

    # Jetzt erst die GUI-Komponenten laden
    from oscam_patch_manager import (
        PatchManagerGUI,
        TEXTS,
        fill_missing_keys,
        ensure_dir,  # War in deinem Original auskommentiert, wird aber unten genutzt
        PLUGIN_DIR,
        ICON_DIR,
        TEMP_REPO,
        load_config,
    )

    # 2️⃣ Wichtige Verzeichnisse sicherstellen
    ensure_dir(PLUGIN_DIR)
    ensure_dir(ICON_DIR)
    ensure_dir(TEMP_REPO)

    # 3️⃣ Konfiguration laden
    load_config()

    # 4️⃣ Fehlende TEXTS automatisch auffüllen
    fill_missing_keys(TEXTS)

    # 5️⃣ QApplication erstellen
    app = QApplication(sys.argv)

    # 6️⃣ GUI starten
    window = PatchManagerGUI()
    window.showMaximized()

    # 7️⃣ Event-Loop starten
    sys.exit(app.exec())
