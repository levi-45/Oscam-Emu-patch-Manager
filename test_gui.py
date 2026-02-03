#!/usr/bin/env python3
# ============================================================================
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
# ============================================================================
import sys
import os
import json
import shutil
import subprocess
import zipfile
import requests
import stat
import platform
import re
from pathlib import Path
from io import BytesIO
from datetime import datetime, timezone

from PyQt6.QtGui import QPixmap, QAction, QFont, QColor, QTextCursor, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QLabel,
    QComboBox,
    QSpinBox,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QSizePolicy,
)
import os
import platform
import re
from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize

# ===================== VERSION HANDLING =====================
try:
    from packaging.version import Version, InvalidVersion
except (ImportError, ModuleNotFoundError):
    class Version:
        def __init__(self, vstring):
            self.v = [int(x) for x in re.sub(r"[^0-9.]", "", str(vstring)).split(".") if x]

        def __gt__(self, other): return self.v > other.v
        def __lt__(self, other): return self.v < other.v
        def __ge__(self, other): return self.v >= other.v
        def __le__(self, other): return self.v <= other.v
        def __eq__(self, other): return self.v == other.v

    class InvalidVersion(Exception): pass

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
APP_VERSION = "2.4.0"

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

# ===================== SUBPROCESS HELPERS =====================
def run_python_script(script_path, args=None):
    """Führt ein externes Python-Skript mit dem gleichen Interpreter aus."""
    if args is None:
        args = []
    cmd = [sys.executable, script_path] + args
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[FEHLER] Fehler beim Starten von {script_path}: {e}")

def run_command(cmd_list, cwd=None):
    """Führt einen Befehl aus und gibt (returncode, stdout, stderr) zurück."""
    try:
        result = subprocess.run(
            cmd_list,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=False,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

# ===================== BEISPIEL: GIT CLONE =====================
# erst ausführen, nachdem TEMP_REPO und STREAMREPO definiert sind
# returncode, out, err = run_command(["git", "clone", STREAMREPO, "."], cwd=TEMP_REPO)
# if returncode != 0:
#     print(f"[ERROR] Git clone failed: {err}")
# else:
#     print(out)


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
            size = size.expandedTo(item.minimumSize())
        margins = self.getContentsMargins()
        size += QSize(margins[0] + margins[2], margins[1] + margins[3])
        return size

    def do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        space = self.spacing()

        for item in self.item_list:
            widget_size = item.sizeHint()
            next_x = x + widget_size.width() + space
            if next_x - space > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + space
                next_x = x + widget_size.width() + space
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), widget_size))

            x = next_x
            line_height = max(line_height, widget_size.height())

        return y + line_height - rect.y()


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
    "Classic": {"bg": "#1E1E1E", "text": "#FFFFFF"},
    "Ocean": {"bg": "#2B3A67", "text": "#A8D0E6"},
    "Sunset": {"bg": "#FF6B6B", "text": "#FFE66D"},
    "Forest": {"bg": "#2E8B57", "text": "#E0F2F1"},
    "Candy": {"bg": "#FFB6C1", "text": "#4B0082"},
    "Cyberpunk": {"bg": "#0D0D0D", "text": "#FF00FF"},
    "CoolMint": {"bg": "#A8FFF0", "text": "#003F3F"},
    "Sunrise": {"bg": "#FFD580", "text": "#B22222"},
    "DeepSea": {"bg": "#001F3F", "text": "#7FDBFF"},
    "Lavender": {"bg": "#E6E6FA", "text": "#4B0082"},
    "Blue-Orange": {"bg": "#FF8C00", "text": "#FFFFFF"},
    "Yellow-Purple": {"bg": "#800080", "text": "#FFFF00"},
    "Green-Red": {"bg": "#228B22", "text": "#FFFFFF"},
    "Midnight": {"bg": "#121212", "text": "#BB86FC"},
    "Solarized": {"bg": "#002B36", "text": "#839496"},
    "Neon": {"bg": "#0B0C10", "text": "#66FCF1"},
    "Fire": {"bg": "#7F0000", "text": "#FF4500"},
    "Moss": {"bg": "#2E3A23", "text": "#A9BA9D"},
    "Peach": {"bg": "#FFDAB9", "text": "#8B4513"},
    "Galaxy": {"bg": "#1B1B2F", "text": "#E94560"},
    "Aqua": {"bg": "#004D4D", "text": "#00FFFF"},
    "Lavish": {"bg": "#3D2B56", "text": "#F1C40F"},
    "Tech": {"bg": "#0F0F0F", "text": "#00FF00"},
    "NeonPink": {"bg": "#1A1A1D", "text": "#FF6EC7"},
    "ElectricBlue": {"bg": "#0B0C10", "text": "#00FFFF"},
    "CyberGreen": {"bg": "#050A05", "text": "#39FF14"},
    "SunsetVibes": {"bg": "#FF4500", "text": "#FFF8DC"},
    "PurpleHaze": {"bg": "#2E004F", "text": "#D580FF"},
    "MintyFresh": {"bg": "#002B2B", "text": "#7FFFD4"},
    "HotMagenta": {"bg": "#1B0B1B", "text": "#FF00FF"},
    "GoldenHour": {"bg": "#2F1E00", "text": "#FFD700"},
    "OceanDeep": {"bg": "#001F3F", "text": "#00BFFF"},
    "Tropical": {"bg": "#003300", "text": "#FFDD00"},
    "MagentaGlow": {"bg": "#1C001C", "text": "#FF00FF"},
    "CyanWave": {"bg": "#001F1F", "text": "#00FFFF"},
    "SunriseGold": {"bg": "#2B1A00", "text": "#FFD700"},
    "CoralReef": {"bg": "#2F0A0A", "text": "#FF7F50"},
    "LimePunch": {"bg": "#0A1F00", "text": "#BFFF00"},
    "VioletStorm": {"bg": "#1E003F", "text": "#D580FF"},
    "OceanMist": {"bg": "#002B3A", "text": "#7FDBFF"},
    "PeachySun": {"bg": "#3F1E00", "text": "#FFA07A"},
    "NeonOrange": {"bg": "#1A0A00", "text": "#FF8C00"},
    "ElectricLime": {"bg": "#00FF00", "text": "#0D0D0D"},
    "NeonCoral": {"bg": "#FF4040", "text": "#0D0D0D"},
    "RoyalTeal": {"bg": "#005F6B", "text": "#FFD700"},
    "MidnightPurple": {"bg": "#1C003D", "text": "#FF77FF"},
    "SolarFlare": {"bg": "#FFB300", "text": "#2C003E"},
    "FrostBlue": {"bg": "#00D4FF", "text": "#1A1A2E"},
    "CandyFloss": {"bg": "#FFB3FF", "text": "#330033"},
    "TangerineDream": {"bg": "#FF6F3C", "text": "#1A1A1A"},
    "EmeraldNight": {"bg": "#004D40", "text": "#A8FF60"},
    "CrimsonWave": {"bg": "#8B0000", "text": "#FFDDFF"},
    "NeonLemon": {"bg": "#1A1A00", "text": "#FFFF33"},
    "UltraViolet": {"bg": "#330066", "text": "#FF99FF"},
    "AquaBlast": {"bg": "#002233", "text": "#33FFFF"},
    "MagentaRush": {"bg": "#2A001A", "text": "#FF33CC"},
    "GoldenEmerald": {"bg": "#003300", "text": "#FFD700"},
    "ElectricFuchsia": {"bg": "#1A001A", "text": "#FF33FF"},
    "IceMint": {"bg": "#001F1A", "text": "#99FFCC"},
    "FlamingSun": {"bg": "#4B0000", "text": "#FFCC33"},
    "CobaltSky": {"bg": "#00114D", "text": "#66CCFF"},
    "PinkGalaxy": {"bg": "#1A0022", "text": "#FF66FF"},
    "NeonPink": {"bg": "#1A1A1D", "text": "#FF6EC7"},
    "ElectricBlue": {"bg": "#1A1A1D", "text": "#00FFFF"},
    "LimeGreen": {"bg": "#1A1A1D", "text": "#32CD32"},
    "SunsetOrange": {"bg": "#1A1A1D", "text": "#FF4500"},
    "VioletDream": {"bg": "#1A1A1D", "text": "#8A2BE2"},
    "GoldenYellow": {"bg": "#1A1A1D", "text": "#FFD700"},
    "CandyRed": {"bg": "#1A1A1D", "text": "#FF1493"},
    "AquaMarine": {"bg": "#1A1A1D", "text": "#7FFFD4"},
    "CoralPink": {"bg": "#1A1A1D", "text": "#FF7F50"},
    "Turquoise": {"bg": "#1A1A1D", "text": "#40E0D0"},
    "MagentaPop": {"bg": "#1A1A1D", "text": "#FF00FF"},
    "SkyBlue": {"bg": "#1A1A1D", "text": "#87CEEB"},
    "LemonYellow": {"bg": "#1A1A1D", "text": "#FFF44F"},
    "HotPink": {"bg": "#1A1A1D", "text": "#FF69B4"},
    "BrightOrange": {"bg": "#1A1A1D", "text": "#FFA500"},
    "MagentaPop": {"bg": "#1A1A1D", "text": "#FF00FF"},
    "NeonCyan": {"bg": "#0D0D0D", "text": "#00FFFF"},
    "ElectricLime": {"bg": "#1B1B1B", "text": "#00FF00"},
    "CrimsonNight": {"bg": "#1C1C1F", "text": "#DC143C"},
    "RoyalPurple": {"bg": "#161618", "text": "#800080"},
    "OrangeFever": {"bg": "#1F1F1F", "text": "#FFA500"},
    "BlueSteel": {"bg": "#101018", "text": "#4682B4"},
    "PinkGalaxy": {"bg": "#1A101A", "text": "#FF69B4"},
    "AmberGlow": {"bg": "#1C1B10", "text": "#FFBF00"},
    "TealShadow": {"bg": "#121212", "text": "#008080"},
    "VioletHaze": {"bg": "#1A1A2E", "text": "#EE82EE"},
    "RedStorm": {"bg": "#1B0B0B", "text": "#FF4500"},
    "CyanIce": {"bg": "#0F1A1A", "text": "#00CED1"},
    "LimePulse": {"bg": "#101810", "text": "#32CD32"},
    "FuchsiaDream": {"bg": "#1A1018", "text": "#FF00FF"},
    "TurquoiseDream": {"bg": "#002222", "text": "#40E0D0"},
}

current_diff_colors = DIFF_COLORS["Classic"]
current_color_name = "Classic"


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
        # "patch_save_label": "Save Patch",
        "patch_apply": "Apply Patch",
        "patch_path_label": "Save Patch",
        "patch_zip": "Zip Patch",
        "backup_old": "Backup/Renew Patch",
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
        # Exit / Confirmation
        "exit": "Exit",
        "yes": "Yes",
        "no": "No",
        "cancel": "Cancel",
        # "plugin_update": "Plugin Update",
        "btn_plugin_update": "Plugin Update",
        "state_plugin_uptodate": "Up to date",
        "check_tools_button": "🛠️ Check Tools",
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
        "update_error": "Error checking for updates: {error}",
        "update_declined": "Update declined.",
        "update_current_version": "✅ Installed version: {version}",
        "restart_required_title": "Restart Required",
        "restart_required_msg": "The tool needs to be restarted. Restart now?",
        "yes": "Yes",
        "no": "No",
        # patch ordner leeren
        "temp_repo_deleted": "Temp repository deleted: {path}",
        "patch_file_deleted": "Patch file deleted: {path}",
        "temp_repo_already_deleted": "Temporary repository not found (already clean): {path}",
        "clean_done": "✅ Cleaning successfully finished!",
        # Labels
        "language_label": "Language:",
        "color_label": "Color",
        "commit_count_label": "Number of commits to show",
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
        "patch_create_start": "ℹ️ Patch creation started...",
        "patch_create_clone_start": "⚠️ TEMP_REPO does not exist, cloning repository...",
        "patch_create_clone_failed": "❌ Git clone failed!",
        "patch_git_error": "❌ Git error: {error}",
        "patch_git_exception": "❌ Exception running git command: {error}",
        "patch_create_no_changes": "⚠️ No changes found, patch is empty.",
        "patch_create_success": "✅ Patch successfully created: {patch_file}",
        "patch_version_from_header": "Patch version from header: {patch_version}",
        "patch_create_start": "ℹ️ Patch creation started...",
        "patch_create_clone_start": "⚠️ TEMP_REPO does not exist, cloning repository...",
        "patch_create_clone_failed": "❌ Git clone failed!",
        "patch_git_error": "❌ Git error: {error}",
        "patch_git_exception": "❌ Git exception: {error}",
        "patch_create_no_changes": "⚠️ No changes found to create a patch.",
        "patch_create_success": "✅ Patch successfully created: {patch_file}",
        "patch_version_from_header": "Patch version from header: {patch_version}",
        # Commits
        "loading_commits": "Lade Commits...",
        "commits_loaded": "Commits erfolgreich geladen",
        # Tool check
        "checking_tools": "Checking installed system tools...",
        "tools_ok": "✅ All required system tools are already installed.",
        "tool_missing": "⚠️ Missing tool: {tool}.",
        "tool_ok": "✅ {tool} is ready.",
        "system_check_ok": "✅ System check completed successfully.",
        "manual_install": "❌ Please manually install missing tools.",
        "checking_tools": "🔹 Checking system tools...",
        "tools_missing": "⚠️ Missing tools: {tools}. Please manually install them.",
        "patch_file_missing": "❌ Patch file not found: {path}",
        "patch_check_ok": "✅ Patch check passed successfully.",
        "patch_check_fail": "❌ Patch check failed.",
        "zip_success": "✅ Patch successfully zipped: {zip_file}",
        "oscam_emu_git_patch_start": "🔹 Creating OSCam-Emu Git Patch...",
        "oscam_emu_git_clearing": "🔹 Clearing OSCam-Emu Git folder...",
        "change_old_dir": "Select the folder for OLD patches",
        "old_patch_path_changed": "✅ OLD patch path changed to: {OLD_}",
        "old_patch_path_cancelled": "ℹ️ Changing OLD patch path cancelled",
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
        # Clean Patch Folder
        "cleaning_oscam_emu_git": "ℹ️ Deleting OSCam-Emu Git folder: {path}",
        "oscam_emu_git_deleted": "✅ OSCam-Emu Git folder successfully deleted.",
        "oscam_emu_git_missing": "⚠️ Folder not found: {path}",
        "clean_done": "✅ Cleanup completed successfully!",
        "oscam_emu_git_missing": "⚠️ Folder does not exist: {path}",
        "oscam_emu_git_patch_start": "🔹 Creating OSCam-Emu Git Patch...",
        "git_patch_success": "✅ Git Patch created successfully! Revision: {rev}",
        "git_patch_success": "✅ Patch created successfully! Git Revision: {rev}",
        "clean_done": "✅ All temporary files cleaned",
        "patch_version_from_header": "Patch version from header: {patch_version}",
        "patch_create_success": "Patch successfully created: {patch_file}",
        "showing_commits": "ℹ️ Showing latest {count} commits",
    },
    "de": {
        # Grid Buttons / Patch Aktionen
        "patch_create": "Patch erstellen",
        "patch_renew": "Patch erneuern",
        "patch_check": "Patch prüfen",
        "patch_apply": "Patch anwenden",
        "patch_zip": "Patch zippen",
        "backup_old": "Patch sichern/erneuern",
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
        "patch_emu_git_revision": "🧾 Git-Revision: {sha}",
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
        "msg_update_available_text": "Eine neue Version ({latest}) ist verfügbar.\nAktuell installiert: {current}.\nJetzt updaten?",
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
        "update_current_version": "✅ Installierte Version: {version}",
        "update_check_failed": "Fehler bei Updateprüfung: {error}",
        "update_available_msg": "Aktuelle Version: {current}\nNeue Version: {latest}",
        "update_success": "✅ Update erfolgreich installiert! Bitte Tool neu starten.",
        "version_current": "Version {version} ist aktuell.",
        "update_error": "Fehler bei Updateprüfung: {error}",
        "update_declined": "Update abgebrochen.",
        "check_tools_button": "🛠️ Tools prüfen",
        "update_no_update": "ℹ️ Kein Update vorhanden",
        "tools_missing": "⚠️ Folgende Tools fehlen: {tools}. Installation wird vorbereitet...",
        "check_tools_button": "🛠️ Tools prüfen",
        "checking_tools": "Starte System-Check...",
        "restart_required_title": "Neustart erforderlich",
        "restart_tool_question": "Möchten Sie das Tool jetzt neu starten?",
        "patch_emu_git_success": "✅ OSCam Emu Git successfully patched",
        "restart_required_msg": "Das Tool muss neu gestartet werden. Jetzt neu starten?",
        "yes": "Ja",
        "no": "Nein",
        "oscam_emu_patch_upload": "OSCam EMU Patch hochladen",
        # Labels
        # "language_label": "Sprache:",
        "language_label": "Sprache auswählen:",
        "color_label": "Farbe auswählen",
        "commit_count_label": "Anzahl der anzuzeigenden Commits",
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
        "patch_create_clone_failed": "❌ Git Clone fehlgeschlagen!",
        "patch_git_error": "❌ Git Fehler: {error}",
        "patch_git_exception": "❌ Git Exception: {error}",
        "patch_create_no_changes": "⚠️ Keine Änderungen zum Patchen gefunden.",
        "patch_create_success": "✅ Patch erfolgreich erstellt: {patch_file}",
        "patch_version_from_header": "Patch-Version aus Header: {patch_version}",
        
        "patch_create_clone_start": "⚠️ TEMP_REPO existiert nicht, Repository wird geklont...",
        "patch_create_clone_failed": "❌ Git Clone fehlgeschlagen!",
        "patch_git_error": "❌ Git Fehler: {error}",
        "patch_git_exception": "❌ Ausnahme beim Git-Befehl: {error}",
        "patch_create_no_changes": "⚠️ Keine Änderungen gefunden, Patch ist leer.",
        "patch_create_success": "✅ Patch erfolgreich erstellt: {patch_file}",
        "patch_version_from_header": "Patch-Version aus Header: {patch_version}",
        # Patch ordner leeren
        "temp_patch_git_already_deleted": "Patch-Git-Ordner war bereits gelöscht oder nicht vorhanden.",
        "patch_file_deleted": "Patch-Datei wurde erfolgreich entfernt: {path}",
        "patch_file_already_deleted": "Keine Patch-Datei zum Löschen gefunden: {path}",
        "clean_done": "Bereinigung des Arbeitsverzeichnisses erfolgreich abgeschlossen! ✨",
        "oscam_emu_git_missing": "⚠️ Ordner nicht gefunden: {path}",
        "temp_repo_deleted": "Temporäres Repository erfolgreich gelöscht: {path}",
        "oscam_emu_git_patch_start": "🔹 OSCam-Emu Git Patch wird erstellt...",
        "patch_file_deleted": "Patch-Datei gelöscht: {path}",
        "patch_emu_git_success": "✅ OSCam Emu Git erfolgreich gepatcht",
        "oscam_emu_git_deleted": "✅ OSCam-Emu Git Ordner erfolgreich gelöscht.",
        # Tool check
        "checking_tools": "Überprüfe installierte System-Tools...",
        "tools_ok": "✅ Alle erforderlichen System-Tools sind bereits installiert.",
        "tools_missing": "⚠️ Folgende Tools fehlen: {tools}. Bitte manuell installieren.",
        "patch_file_missing": "❌ Patch-Datei nicht gefunden: {path}",
        "patch_check_ok": "✅ Patchprüfung erfolgreich.",
        "patch_check_fail": "❌ Patchprüfung fehlgeschlagen.",
        "zip_success": "✅ Patch erfolgreich gepackt: {zip_file}",
        "oscam_emu_git_patch_start": "🔹 OSCam-Emu Git Patch wird erstellt...",
        "oscam_emu_git_clearing": "🔹 OSCam-Emu Git Ordner wird geleert...",
        "change_old_dir": "Ordner für OLD-Patches auswählen",
        "old_patch_path_changed": "✅ Pfad für OLD-Patch geändert auf: {OLD_}",
        "old_patch_path_cancelled": "ℹ️ Änderung des OLD-Patch-Pfads abgebrochen",
        "tool_missing": "⚠️ {tool} fehlt im System.",
        "tool_ok": "✅ {tool} ist bereit.",
        "system_check_ok": "✅ System-Check erfolgreich.",
        "manual_install": "❌ Bitte fehlende Tools manuell installieren.",
        "checking_tools": "🔹 Prüfe System-Tools...",
        # Backup
        "backup_old_start": "ℹ️ Erstelle Backup des alten Patches…",
        "backup_done": "✅ Backup erfolgreich erstellt: {path}",
        "tools_ok": "✅ Alle benötigten System-Tools sind bereits installiert.",
        "tools_missing": "⚠️ Folgende Tools fehlen: {tools}. Installation wird vorbereitet...",
        "check_tools_button": "🛠️ Tools prüfen",
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
        # Clean Patch Folder
        "cleaning_oscam_emu_git": "ℹ️ Lösche OSCam-Emu Git Ordner: {path}",
        "oscam_emu_git_deleted": "✅ OSCam-Emu Git Ordner erfolgreich gelöscht.",
        "oscam_emu_git_missing": "⚠️ Ordner nicht gefunden: {path}",
        "delete_failed": "❌ Fehler: Konnte {path} nicht löschen. Fehler: {error}",
        "clean_done": "✅ Bereinigung erfolgreich abgeschlossen!",
        "git_patch_success": "✅ Patch erfolgreich erstellt! Git Revision: {rev}",
        "oscam_emu_git_missing": "⚠️ Ordner existiert nicht: {path}",
        "delete_failed": "❌ Löschen fehlgeschlagen: {path} (Fehler: {error})",
        "github_patch_uploaded": "✅ Patch erfolgreich hochgeladen: {patch_version}",
        "github_upload_failed": "❌ Fehler beim Hochladen auf GitHub.",
        "patch_version_from_header": "Patch-Version aus Header: {patch_version}",
        "patch_create_success": "Patch erfolgreich erstellt: {patch_file}",
        "showing_commits": "ℹ️ Zeige die letzten {count} Commits",
    },
}

# Ergänze fehlende Keys aus EN nach DE
for key, value in TEXTS["en"].items():
    if key not in TEXTS["de"]:
        TEXTS["de"][key] = value

# 4️⃣ **Unbedingt einmalig vor GUI-Start aufrufen**
fill_missing_keys(TEXTS)


def ensure_dir(path):
    """Stellt sicher, dass das Verzeichnis `path` existiert."""
    if not os.path.exists(path):
        os.makedirs(path)


def save_config(cfg=None):
    """
    Speichert die Config in CONFIG_FILE.
    Wenn cfg gesetzt ist, wird die gesamte Config gespeichert.
    """
    if cfg is None:
        # Falls keine Config übergeben wird, einfach aus Datei laden
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception as e:
                self.append_info(
                    None, f"⚠️ Config konnte nicht gelesen werden: {e}", "warning"
                )

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        self.append_info(None, f"Fehler beim Speichern der Config: {e}", "error")


# ===================== CONFIG =====================
def load_config():
    # Standardwerte
    default_cfg = {
        "commit_count": 5,
        "color": "Classic",
        "language": "DE",
        "s3_patch_path": OLD_PATCH_DIR,  # Nutzt den Pfad aus Schritt 1
    }

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not isinstance(cfg, dict):
                return default_cfg

            # Fehlende Keys ergänzen
            for key, value in default_cfg.items():
                if key not in cfg:
                    cfg[key] = value
            return cfg
        except:
            return default_cfg
    return default_cfg


# ===================== INFOSCREEN =====================
def github_upload_patch_file(
    gui_instance=None, info_widget=None, progress_callback=None
):
    """
    Lädt die Patch-Datei auf GitHub hoch und zeigt die Version aus dem Header im Infoscreen an.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import shutil, os, datetime

    # 1. Widget und Sprache sicherstellen
    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(gui_instance, "info_text", None)
    )
    # Sprache vereinheitlichen (kleingeschrieben für Dictionary-Match)
    lang = getattr(gui_instance, "LANG", "de").lower()

    # Hilfsfunktion für Fortschritt
    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    # 2. Lokale Logger-Funktion mit Kwargs-Unterstützung
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
            # Fallback falls gui_instance fehlt
            color = {"success": "green", "warning": "orange", "error": "red"}.get(
                level, "gray"
            )
            widget.append(f'<span style="color:{color}">{text}</span>')

        QApplication.processEvents()

    # --- Start der Ausführung ---
    set_progress(5)

    # GitHub-Konfig laden
    cfg = load_github_config()
    repo_url = cfg.get("repo_url")
    branch = cfg.get("branch", "master")
    username = cfg.get("username")
    token = cfg.get("token")
    user_name = cfg.get("user_name")
    user_email = cfg.get("user_email")

    if not all([repo_url, username, token, user_name, user_email]):
        log("github_patch_credentials_missing", "error")
        set_progress(0)
        return

    if not os.path.exists(PATCH_FILE):
        log("patch_file_missing", "error")
        set_progress(0)
        return

    set_progress(15)

    # Temporäres Verzeichnis vorbereiten
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
        set_progress(0)
        return

    set_progress(50)

    # 4. Patch-Datei kopieren
    patch_path = os.path.join(temp_repo, "oscam-emu.patch")
    try:
        shutil.copy2(PATCH_FILE, patch_path)
    except Exception as e:
        log("patch_failed", "error", path=str(e))
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

    # 5. Patch-Version für Anzeige und Commit ermitteln
    try:
        # Liest die erste Zeile der lokalen Patch-Datei
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
        # Hier wird die Version aus der ersten Zeile des Patches im Infoscreen ausgegeben
        log("github_patch_uploaded", "success", patch_version=patch_version)
        set_progress(100)
    else:
        log("github_upload_failed", "error")
        set_progress(0)

    # 7. Cleanup
    shutil.rmtree(temp_repo, ignore_errors=True)


from datetime import datetime, timezone
import subprocess
import os
import shutil  # wird unten benötigt


def get_patch_header(repo_dir=None, lang=LANG):
    """
    Liest Versions- und Build-Information aus globals.h
    und erzeugt den Patch-Header mit Commit und Datum.
    Übersetzt die Header-Texte entsprechend der GUI-Sprache.
    """
    if repo_dir is None:
        repo_dir = TEMP_REPO

    # Standardwerte
    version = "2.26.01"
    build = "0"
    commit = "N/A"

    # globals.h auslesen
    globals_path = os.path.join(repo_dir, "globals.h")
    if os.path.exists(globals_path):
        try:
            with open(globals_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#define CS_VERSION"):
                        parts = line.strip().split('"')
                        if len(parts) >= 2:
                            version_build = parts[1].split("-")
                            version = version_build[0]
                            build = version_build[1] if len(version_build) > 1 else "0"
        except Exception:
            pass

    # Git-Commit auslesen
    git_dir = os.path.join(repo_dir, ".git")
    if os.path.exists(git_dir):
        try:
            commit = subprocess.getoutput(
                f"git -C {repo_dir} rev-parse --short HEAD"
            ).strip()
        except Exception:
            commit = "N/A"

    # Patch modified date (lokales Datum)
    modified_date = datetime.now().strftime("%d/%m/%Y")

    # Patch date = aktuelles UTC-Datum
    patch_date_utc = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC (+00:00)"
    )

    # Header mit Übersetzung
    header = (
        f"{TEXTS[lang].get('patch_version_header', 'patch version')}: "
        f"oscam-emu-patch {version}-{build}-({commit})\n"
        f"{TEXTS[lang].get('patch_modified_by', 'patch modified by')} "
        f"{PATCH_MODIFIER} ({modified_date})\n"
        f"{TEXTS[lang].get('patch_date', 'patch date')}: {patch_date_utc}"
    )

    return header


# ===================== PATCH FUNCTIONS =====================
from PyQt6.QtWidgets import QTextEdit, QApplication
import os, subprocess, shutil


def create_patch(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Erstellt den Patch im TEMP_REPO mit flüssiger Fortschrittsanzeige.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtGui import QTextCursor
    import subprocess, os, shutil

    widget = info_widget
    if not isinstance(widget, QTextEdit) and gui_instance:
        widget = getattr(gui_instance, "info_text", None)

    lang = getattr(gui_instance, "LANG", "de").lower()

    def log(text_key, level="info", **kwargs):
        text_template = TEXTS.get(lang, {}).get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except Exception:
            text = text_template

        if isinstance(widget, QTextEdit):
            color_map = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
            color = color_map.get(level, "gray")
            widget.append(f'<span style="color:{color}">{text}</span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()
        else:
            print(f"[{level.upper()}] {text}")

    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    def run_git(cmd_list, ignore_no_remote=False):
        """Führt Git Befehle robust aus und loggt Fehler."""
        try:
            result = subprocess.run(
                cmd_list,
                cwd=TEMP_REPO,
                capture_output=True,
                text=True,
                shell=False,
                check=False
            )
            if result.returncode != 0:
                # Optional: 'No such remote' ignorieren beim Entfernen
                if ignore_no_remote and "No such remote" in result.stderr:
                    return 0, result.stdout, result.stderr
                log("patch_git_error", "error", error=result.stderr.strip())
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            log("patch_git_exception", "error", error=str(e))
            return 1, "", str(e)

    # --- START DER AKTION ---
    log("patch_create_start", "info")
    set_progress(10)

    os.makedirs(TEMP_REPO, exist_ok=True)
    git_dir = os.path.join(TEMP_REPO, ".git")

    # 1️⃣ Clone falls .git fehlt
    if not os.path.exists(git_dir):
        set_progress(20)
        log("patch_create_clone_start", "info")
        # Lösche TEMP_REPO falls kaputt
        if os.listdir(TEMP_REPO):
            shutil.rmtree(TEMP_REPO)
            os.makedirs(TEMP_REPO, exist_ok=True)

        returncode, out, err = run_git(["git", "clone", STREAMREPO, "."])
        if returncode != 0:
            log("patch_create_clone_failed", "error")
            set_progress(0)
            return

    # 2️⃣ Remotes sicher setzen
    run_git(["git", "remote", "remove", "origin"], ignore_no_remote=True)
    run_git(["git", "remote", "add", "origin", STREAMREPO])
    run_git(["git", "remote", "remove", "emu-repo"], ignore_no_remote=True)
    run_git(["git", "remote", "add", "emu-repo", EMUREPO])

    set_progress(40)

    # 3️⃣ Git Befehle
    for cmd in [
        ["git", "fetch", "origin"],
        ["git", "fetch", "emu-repo"],
        ["git", "checkout", "-B", "master", "origin/master"],
        ["git", "reset", "--hard", "origin/master"],
    ]:
        run_git(cmd)

    set_progress(70)

    # 4️⃣ Patch generieren
    header = get_patch_header()
    try:
        diff = subprocess.check_output(
            ["git", "diff", "origin/master..emu-repo/master", "--", ".", ":!.github"],
            cwd=TEMP_REPO,
            text=True,
        )
    except subprocess.CalledProcessError:
        diff = "# No changes"

    if not diff.strip():
        log("patch_create_no_changes", "warning")
        diff = "# No changes"

    with open(PATCH_FILE, "w", encoding="utf-8") as f:
        f.write(header + "\n" + diff + "\n")

    set_progress(90)
    log("patch_create_success", "success", patch_file=PATCH_FILE)

    if header.strip():
        first_line = header.splitlines()[0]
        log("patch_version_from_header", "success", patch_version=first_line)

    set_progress(100)



def log(text, level="info"):
    colors = {
        "success": "green",
        "warning": "orange",
        "error": "red",
        "info": "gray",
    }
    color = colors.get(level, "gray")

    if widget is not None and isinstance(widget, QTextEdit):
        widget.append(f'<span style="color:{color}">{text}</span>')
        widget.moveCursor(QTextCursor.End)
        QApplication.processEvents()
    else:
        print(f"[{level.upper()}] {text}")


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
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtGui import QTextCursor

    # 1. Widget & Sprache sicherstellen
    widget = (
        info_widget
        if isinstance(info_widget, QTextEdit)
        else getattr(self, "info_text", None)
    )
    lang = getattr(self, "LANG", "de")

    # Hilfsfunktion für Fortschritt
    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()  # Sorgt für live Update der GUI
            except:
                pass

    # Lokaler Logger ohne Terminal-Print
    def log(text_key, level="info", **kwargs):
        text_template = TEXTS.get(lang, {}).get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_key

        if isinstance(widget, QTextEdit):
            # Nutze die zentrale append_info für einheitliche Farben
            self.append_info(widget, text, level)

    # --- Start ---
    set_progress(10)
    log("backup_old_start", "info")

    # Pfade ermitteln (Nutze die globalen Konstanten falls vorhanden)
    old_patch = getattr(self, "OLD_PATCH_FILE", OLD_PATCH_FILE)
    alt_patch = getattr(self, "ALT_PATCH_FILE", ALT_PATCH_FILE)
    new_patch = PATCH_FILE  # Nutze die globale Konstante aus deiner Config

    # Zielordner sicherstellen
    dir_path = os.path.dirname(old_patch)
    if dir_path and not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            log("patch_failed", "error", path=str(e))
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
            set_progress(0)
            return
    else:
        log("no_old_patch", "info")

    set_progress(60)

    # Neue Patch-Datei kopieren
    if not os.path.exists(new_patch):
        log("patch_file_missing", "error", path=new_patch)
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

    except Exception as e:
        log("patch_failed", "error", path=str(e))
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
    Löscht TEMP_REPO, PATCH_FILE, ZIP_FILE und TEMP_PATCH_GIT komplett.
    Windows-Fix: Entfernt Schreibschutz von Git-Dateien (stat.S_IWRITE).
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import os, shutil, stat

    # 1. Widget & Sprache sicherstellen
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

    def log(text_key, level="info", **kwargs):
        lang_data = TEXTS.get(lang, TEXTS.get("En", {}))
        text_template = lang_data.get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_key

        if gui_instance and hasattr(gui_instance, "append_info"):
            gui_instance.append_info(widget, text, level)
        elif isinstance(widget, QTextEdit):
            colors = {"success": "green", "warning": "orange", "error": "red"}
            color = colors.get(level, "gray")
            widget.append(f'<span style="color:{color}">{text}</span>')
        QApplication.processEvents()

    # --- Windows Schreibschutz-Fix ---
    def on_rm_error(func, path, exc_info):
        """Entfernt Schreibschutz und versucht das Löschen erneut (für Git-Dateien)."""
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except:
            pass  # Falls Datei wirklich gesperrt ist

    def delete_path(path, path_name):
        if path and os.path.exists(path):
            try:
                if os.path.isdir(path):
                    # Nutze on_rm_error statt ignore_errors für Windows-Kompatibilität
                    shutil.rmtree(path, onerror=on_rm_error)
                else:
                    # Vor dem Löschen von Dateien ebenfalls Schreibschutz entfernen
                    os.chmod(path, stat.S_IWRITE)
                    os.remove(path)
                log(f"{path_name}_deleted", "success", path=path)
                return True
            except Exception as e:
                log("delete_failed", "error", path=path_name)
        else:
            log(f"{path_name}_already_deleted", "info", path=path)
        return False

    # --- Ablauf ---
    set_progress(10)
    delete_path(TEMP_REPO, "temp_repo")

    set_progress(35)
    temp_patch_git = os.path.join(PLUGIN_DIR, "temp_patch_git")
    delete_path(temp_patch_git, "temp_patch_git")

    set_progress(60)
    delete_path(PATCH_FILE, "patch_file")

    set_progress(85)
    delete_path(ZIP_FILE, "zip_file")

    log("clean_done", "success")
    set_progress(100)


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
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QTextCursor
import shutil, os


def clean_oscam_emu_git(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Löscht den PATCH_EMU_GIT Ordner flüssig mit Fortschrittsanzeige.
    Windows-Fix: Entfernt Schreibschutz von Git-Dateien vor dem Löschen.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import os, shutil, stat

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

    def log(text_key, level="info", **kwargs):
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        text_template = lang_dict.get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_template

        if gui_instance and hasattr(gui_instance, "append_info"):
            gui_instance.append_info(widget, text, level)
        elif isinstance(widget, QTextEdit):
            color = {"success": "green", "warning": "orange", "error": "red"}.get(
                level, "gray"
            )
            widget.append(f'<span style="color:{color}">{text}</span>')
        QApplication.processEvents()

    # --- Windows-Spezifischer Fix für Schreibschutz ---
    def remove_readonly(func, path, excinfo):
        """Hilfsfunktion: Entfernt Schreibschutz, falls shutil.rmtree scheitert."""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    # --- Start ---
    set_progress(10)
    log("cleaning_oscam_emu_git", "info", path=PATCH_EMU_GIT_DIR)

    if os.path.exists(PATCH_EMU_GIT_DIR):
        try:
            set_progress(50)
            # onerror=remove_readonly ist der entscheidende Teil für Windows!
            shutil.rmtree(PATCH_EMU_GIT_DIR, onerror=remove_readonly)
            log("oscam_emu_git_deleted", "success", path=PATCH_EMU_GIT_DIR)
        except Exception as e:
            # Notfallplan: Falls rmtree immer noch blockiert (z.B. Datei offen)
            log("delete_failed", "error", path=PATCH_EMU_GIT_DIR)
            set_progress(0)
            return
    else:
        log("oscam_emu_git_missing", "warning", path=PATCH_EMU_GIT_DIR)

    set_progress(100)
    log("clean_done", "success")


# ===================== patch_oscam_emu_git=====================
def patch_oscam_emu_git(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Klont das Streamboard Git, wendet oscam-emu.patch an und commitet.
    Optimiert für Windows/Linux: Keine Terminal-Ausgaben, SSL-Fix inklusive.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtCore import QTimer
    import os, shutil, subprocess

    # --- GUI & Logging vorbereiten ---
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
        else:
            print(f"[{level.upper()}] {text}")
        QApplication.processEvents()

    # --- Git Wrapper ---
    def run_git(cmd_list, cwd=PATCH_EMU_GIT_DIR, check=True):
        """Führt Git Kommandos aus, loggt Fehler, gibt stdout zurück."""
        try:
            result = subprocess.run(
                cmd_list,
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            if check and result.returncode != 0:
                log("git_error", "error", cmd=" ".join(cmd_list), err=result.stderr.strip())
            return result
        except Exception as e:
            log("git_exception", "error", cmd=" ".join(cmd_list), err=str(e))
            return None

    # --- Start ---
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
    clone = run_git(["git", "clone", "-c", "http.sslVerify=false", STREAMREPO, "."], check=True)
    if not clone or clone.returncode != 0:
        log("patch_emu_git_clone_failed", "error")
        return

    set_progress(40)

    # --- Patch prüfen & anwenden ---
    if not os.path.exists(PATCH_FILE):
        log("patch_file_missing", "error")
        return

    abs_patch_path = os.path.abspath(PATCH_FILE)
    # prüfen, ob Patch bereits angewendet
    check_patch = run_git(["git", "apply", "--check", abs_patch_path], check=False)
    if check_patch.returncode != 0:
        log("patch_emu_git_already_applied", "warning")
    else:
        apply_patch = run_git(["git", "apply", "--whitespace=fix", abs_patch_path], check=True)
        if not apply_patch or apply_patch.returncode != 0:
            log("patch_emu_git_apply_failed", "error")
            return

    set_progress(70)

    # --- Git Config ---
    cfg = load_github_config()
    user = cfg.get("user_name", "speedy005")
    mail = cfg.get("user_email", "patch@oscam.local")
    run_git(["git", "config", "user.name", user], check=False)
    run_git(["git", "config", "user.email", mail], check=False)

    # --- Commit ---
    header_raw = get_patch_header() or "Update"
    header = header_raw.splitlines()[0]
    commit_msg = f"Sync patch {header}"

    run_git(["git", "add", "."], check=False)
    run_git(["git", "commit", "-am", commit_msg, "--allow-empty"], check=False)
    log("patch_emu_git_applied", "success", commit_msg=commit_msg)

    # --- Revision auslesen ---
    rev = None
    rev_res = run_git(["git", "rev-parse", "--short", "HEAD"], check=False)
    if rev_res and rev_res.returncode == 0:
        rev = rev_res.stdout.strip()

    # --- Finale Logs ---
    def final_logs():
        log("patch_emu_git_done", "success")
        if rev:
            rev_text = TEXTS[lang].get("patch_emu_git_revision", "Git revision: {sha}").format(sha=rev)
            if gui_instance:
                gui_instance.append_info(widget, rev_text, "success")
            else:
                print(rev_text)

    QTimer.singleShot(100, final_logs)
    set_progress(100)



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
    Optimiert für Git-Operationen und Thread-Sicherheit.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtGui import QTextCursor
    import os, subprocess

    # 1. Widget-Suche (Fallback)
    if not isinstance(info_widget, QTextEdit):
        active_win = QApplication.activeWindow()
        if active_win and hasattr(active_win, "info_text"):
            info_widget = active_win.info_text

    def log(text, level="info"):
        colors = {
            "success": "#27ae60",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "info": "#7f8c8d",
        }
        color = colors.get(level, "#7f8c8d")

        # Prüfen, ob der Text ein Key aus deiner TEXTS-Struktur ist
        translated = (
            TEXTS.get(lang, {}).get(text, text) if "TEXTS" in globals() else text
        )

        if isinstance(info_widget, QTextEdit):
            # Nutzt HTML für saubere Farben in der GUI
            info_widget.append(
                f'<span style="color:{color}; font-family: monospace;">{translated}</span>'
            )
            info_widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()  # Erlaubt das "Live-Update" der UI
        else:
            print(f"[{level.upper()}] {translated}")

    # 2. Arbeitsverzeichnis validieren
    if cwd and not os.path.exists(cwd):
        try:
            os.makedirs(cwd, exist_ok=True)
        except Exception as e:
            log(f"Could not create directory {cwd}: {e}", "error")
            return -1

    log(f"Executing: {cmd}", "info")

    try:
        # Popen mit Shell=True ist für "git clone ..." Ketten okay,
        # aber wir fügen env hinzu, um Git-Prompts (Passwörter) zu unterdrücken
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Leitet Fehler direkt in stdout um
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        # 3. Live-Ausgabe der Zeilen
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                line = line.strip()
                if line:
                    # Filtert unnötiges "Fetching..." Rauschen oder zeigt es dezent an
                    log(line, "info")
            process.stdout.close()

        return_code = process.wait()

        if return_code != 0:
            log(f"Command failed with exit code {return_code}", "error")

        return return_code

    except Exception as e:
        log(f"run_bash execution error: {e}", "error")
        return -1


# ===================== GITHUB UPLOAD OSCAM-EMU FOLDER =====================
def github_upload_oscam_emu_folder(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Lädt den gesamten Inhalt des OSCam-EMU-Git-Ordners auf GitHub hoch.
    Silent, robust, GUI-freundlich.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import os, subprocess

    # --- GUI & Logging vorbereiten ---
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
        elif gui and hasattr(gui, "progress_bar"):
            gui.progress_bar.setValue(val)
        QApplication.processEvents()

    def log(text_key, level="info", **kwargs):
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        text_template = lang_dict.get(text_key, text_key)
        try:
            text = text_template.format(**kwargs)
        except:
            text = text_key
        if widget and gui and hasattr(gui, "append_info"):
            gui.append_info(widget, text, level)
        else:
            print(f"[{level.upper()}] {text}")
        QApplication.processEvents()

    # --- Git Wrapper ---
    target_dir = PATCH_EMU_GIT_DIR
    if not target_dir or not os.path.exists(target_dir):
        log("patch_emu_git_missing", "error", path=str(target_dir))
        return

    cfg = load_github_config()
    repo_url = cfg.get("emu_repo_url")
    branch = cfg.get("emu_branch", "master")
    username, token = cfg.get("username"), cfg.get("token")
    user_name, user_email = cfg.get("user_name"), cfg.get("user_email")
    if not all([repo_url, branch, username, token, user_name, user_email]):
        log("github_emu_git_missing", "error")
        return

    token_url = repo_url.replace("https://", f"https://{username}:{token}@")
    silent_env = os.environ.copy()
    silent_env["GIT_TERMINAL_PROMPT"] = "0"

    def run_git(cmd_list, cwd=target_dir, check=True):
        try:
            res = subprocess.run(cmd_list, cwd=cwd, capture_output=True, text=True, env=silent_env)
            if check and res.returncode != 0:
                log("git_error", "error", cmd=" ".join(cmd_list), err=res.stderr.strip())
            return res
        except Exception as e:
            log("git_exception", "error", cmd=" ".join(cmd_list), err=str(e))
            return None

    try:
        set_progress(15)
        # --- Remote setzen ---
        git_dir = os.path.join(target_dir, ".git")
        if not os.path.exists(git_dir):
            log("git_repo_init", "warning")
            run_git(["git", "init"])
            run_git(["git", "remote", "add", "origin", token_url])
            run_git(["git", "checkout", "-b", branch])
        else:
            log("git_remote_update", "info")
            run_git(["git", "remote", "remove", "origin"], check=False)
            run_git(["git", "remote", "add", "origin", token_url])
            run_git(["git", "fetch", "origin", branch])
            run_git(["git", "checkout", branch])

        set_progress(40)
        # --- User Config ---
        run_git(["git", "config", "user.name", user_name], check=False)
        run_git(["git", "config", "user.email", user_email], check=False)

        set_progress(50)
        log("git_adding_files", "info")
        run_git(["git", "add", "."])

        # --- Commit Message ---
        commit_msg = "Sync OSCam-Emu folder"
        header_func = globals().get("get_patch_header")
        if header_func:
            try:
                raw = header_func()
                commit_msg = raw.splitlines()[0] if raw else commit_msg
            except:
                pass

        run_git(["git", "commit", "-m", commit_msg, "--allow-empty"], check=False)
        log("git_committing", "info")

        set_progress(70)
        log("github_upload_start", "warning")
        push = run_git(["git", "push", "--force", "origin", branch], check=False)

        if push and push.returncode == 0:
            try:
                sha = subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"], cwd=target_dir, text=True
                ).strip()
            except:
                sha = "N/A"
            log("github_emu_git_uploaded", "success")
            log("github_emu_git_revision", "success", sha=sha, commit_msg=commit_msg)
            set_progress(100)
        else:
            log("github_upload_failed", "error")
            err = (push.stderr.replace(token, "***") if push and push.stderr else "Unknown Git Error")
            log(err.strip(), "error")
            set_progress(0)

    except Exception as e:
        log(f"Kritischer Fehler: {str(e)}", "error")
        set_progress(0)



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
        self.setWindowTitle(title)
        self.setMinimumWidth(520)

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


from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize, QThread, pyqtSignal


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


class PatchManagerGUI(QWidget):
    def __init__(self):
        super().__init__()

        # 1. Daten laden (Einheitlich self.cfg verwenden)
        self.cfg = load_config()

        # 2. Sprache & Basis-Initialisierungen (KORRIGIERT)
        # Wir nutzen .lower(), damit es zum Dictionary TEXTS["de"] passt
        stored_lang = str(self.cfg.get("language", "de")).lower()

        # Validierung: Nur erlauben, was wir auch im Dictionary haben
        if stored_lang in ["en", "de"]:
            self.LANG = stored_lang
        else:
            self.LANG = "de"  # Sicherer Standard-Fallback

        # 3. Patch-Pfade (Windows-sicher über os.path.normpath)
        current_path = self.cfg.get("s3_patch_path", OLD_PATCH_DIR)
        self.OLD_PATCH_DIR = os.path.normpath(current_path)

        self.OLD_PATCH_FILE = os.path.join(self.OLD_PATCH_DIR, "oscam-emu.patch")
        self.ALT_PATCH_FILE = os.path.join(self.OLD_PATCH_DIR, "oscam-emu.altpatch")

        # 4. Listen & Status-Variablen
        self.all_buttons = []
        self.option_buttons = {}
        self.buttons = {}
        self.active_button_key = ""

        # Grid-Layout Referenz initialisieren
        self.main_grid_layout = None

        # --- UPDATE INITIALISIERUNG ---
        self.latest_version = APP_VERSION.replace("v", "").strip()

        # 5. Haupt-UI aufbauen
        self.init_ui()
        QTimer.singleShot(1000, self.manual_tool_check)
        # 6. Pfad-Layout sicherstellen
        if not hasattr(self, "label_patch_path"):
            self.label_patch_path = QLabel()

        # 7. SPRACHE ANWENDEN (Zuerst Anleitung setzen)
        # Dies befüllt den info_text via Teil E deiner update_language
        self.update_language()

        # 8. UPDATE-LOGIK STARTEN
        # Erst den Button-Zustand (Farbe) initialisieren
        self.update_plugin_button_state()

        # Der Timer startet den Online-Check verzögert, damit die GUI erst steht.
        # Nutzt check_for_plugin_update, da diese Methode den Status UNTER die Anleitung hängt.
        QTimer.singleShot(1500, self.check_for_update_on_start)
        
    
    def show_info(self):
        """Zeigt ein modernes Info-Fenster mit Credits und System-Icon."""
        # 1. Sprache ermitteln
        lang = str(getattr(self, "LANG", "de")).lower()
        t = TEXTS.get(lang, TEXTS.get("en", {}))

        # 2. Dialog erstellen
        info_dialog = QDialog(self)
        info_dialog.setWindowTitle(t.get("info_title", "About OSCam Emu Toolkit"))
        info_dialog.setFixedSize(450, 320)

        layout = QVBoxLayout(info_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 3. Oberer Teil: Icon & Titel
        header_layout = QHBoxLayout()

        # Das Info-Icon (das gleiche wie im Button)
        icon_label = QLabel()
        icon = self.style().standardIcon(
            QApplication.style().StandardPixmap.SP_MessageBoxInformation
        )
        icon_label.setPixmap(icon.pixmap(64, 64))

        title_vbox = QVBoxLayout()
        title_label = QLabel("OSCam Emu Patch Manager")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))

        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setStyleSheet("color: #666;")

        title_vbox.addWidget(title_label)
        title_vbox.addWidget(version_label)

        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 4. Mittlerer Teil: Credits / Mitwirkende
        credits_group = QGroupBox(t.get("credits_label", "Credits / Authors"))
        credits_layout = QFormLayout(credits_group)

        # Hier kannst du deine Liste erweitern
        credits_layout.addRow("Main Author:", QLabel("<b>speedy005</b>"))
        credits_layout.addRow("Emu Patch:", QLabel("OSCam-Emu Team"))
        credits_layout.addRow("License:", QLabel("MIT License"))

        layout.addWidget(credits_group)

        # 5. Unterer Teil: Copyright & Schließen
        copy_label = QLabel(f"© 2026 speedy005 - All rights reserved.")
        copy_label.setFont(QFont("Arial", 8))
        copy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copy_label)

        close_btn = QPushButton(t.get("close", "Close"))
        close_btn.setFixedHeight(35)
        close_btn.setStyleSheet(
            f"border-radius: {self.BUTTON_RADIUS}px; background-color: #f0f0f0; font-weight: bold;"
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

    def manual_tool_check(self):
        """Prüft installierte Tools und nutzt strikt die gewählte Sprache."""
        import shutil
        import subprocess
        import platform

        lang = str(getattr(self, "LANG", "de")).lower()
        t = TEXTS.get(lang, TEXTS.get("en", {}))

        self.append_info(
            self.info_text,
            t.get("checking_tools", "Starting system tool check..."),
            "info",
        )

        required_tools = ["git", "patch", "zip", "python3"]
        missing = [tool for tool in required_tools if shutil.which(tool) is None]

        if not missing:
            msg = t.get(
                "tools_ok", "✅ All required system tools are already installed."
            )
            self.append_info(self.info_text, msg, "success")
            return

        missing_str = ", ".join(missing)
        self.append_info(
            self.info_text,
            t.get("tools_missing", "⚠️ Missing tools: {tools}. Please install manually.")
            .format(tools=missing_str),
            "warning",
        )

        # Plattformabhängig
        system = platform.system().lower()
        if system in ["linux", "darwin"]:  # Linux / MacOS
            install_cmd = f"sudo apt-get update && sudo apt-get install -y {' '.join(missing)}"
            term = shutil.which("x-terminal-emulator") or shutil.which("xterm") or "gnome-terminal"
            try:
                if term and "gnome" in term:
                    subprocess.Popen([term, "--", "bash", "-c", install_cmd])
                else:
                    subprocess.Popen([term, "-e", install_cmd])
            except Exception as e:
                err_msg = t.get("terminal_error", f"Terminal Error: {e}")
                self.append_info(self.info_text, err_msg, "error")
        elif system == "windows":
            # Windows kann nur informieren, keine automatische Installation
            self.append_info(
                self.info_text,
                t.get(
                    "manual_install", 
                    f"Please manually install missing tools: {missing_str}"
                ),
                "info",
            )

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
        """Öffnet ein leeres Terminal ohne Verzeichniswechsel."""
        import subprocess
        import platform
        import os

        try:
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
                    # Fallback: Versuche es über xdg-open (manchmal für Apps verknüpft)
                    subprocess.Popen(["x-terminal-emulator"])
        except Exception as e:
            if hasattr(self, "info_text"):
                self.info_text.append(
                    f'<span style="color:red">Terminal-Fehler: {str(e)}</span>'
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
                color = "green" if level == "success" else "red" if level == "error" else "blue"
                self.info_text.append(f'<span style="color:{color}">{text}</span>')
                QApplication.processEvents()

        try:
            if progress_callback: progress_callback(10)

            # --- 1. BACKUP ERSTELLEN ---
            patch_dir = getattr(self, "OLD_PATCH_DIR", "patch_backup")
            os.makedirs(patch_dir, exist_ok=True)
            
            # Wichtigstes Backup: Die aktuelle .py Datei
            shutil.copy2(current_file, backup_file)
            action_log("update_backup_done", "success")

            if progress_callback: progress_callback(30)

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
                if len(new_content) < 1000: # Plausibilitätscheck: Zu kleine Datei?
                    raise ValueError("Download-Datei scheint korrupt oder zu klein zu sein.")

                with open(current_file, "wb") as f:
                    f.write(new_content)
                
            except Exception as write_error:
                # ROLLBACK: Falls das Schreiben fehlschlägt, Backup sofort zurückspielen
                if os.path.exists(backup_file):
                    shutil.copy2(backup_file, current_file)
                    action_log("update_fail", "error", error=f"Rollback durchgeführt: {str(write_error)}")
                raise write_error

            if progress_callback: progress_callback(90)
            action_log("update_done", "success", version=latest_version)

            # --- 4. NEUSTART ---
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(lang_pack.get("restart_required_title", "Restart"))
            msg_box.setText(f"{lang_pack.get('update_success', 'Update OK')}\n\n{lang_pack.get('restart_tool_question', 'Restart?')}")
            
            yes_btn = msg_box.addButton(lang_pack.get("yes", "Ja"), QMessageBox.ButtonRole.YesRole)
            msg_box.addButton(lang_pack.get("no", "Nein"), QMessageBox.ButtonRole.NoRole)
            msg_box.exec()

            if progress_callback: progress_callback(100)
            if msg_box.clickedButton() == yes_btn:
                os.execl(sys.executable, sys.executable, *sys.argv)

        except Exception as e:
            action_log("update_download_failed", "error", error=str(e))
            QMessageBox.critical(self, "Update Error", f"Update fehlgeschlagen.\nDas Tool wurde (falls möglich) wiederhergestellt.\n\nFehler: {str(e)}")
            if progress_callback: progress_callback(0)

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
        min_height=40,
        radius=10,
    ):
        # Zeilenumbruch bei langen Texten erzwingen (ersetzt Leerzeichen durch Umbruch)
        display_text = text.replace(" ", "\n") if len(text) > 12 else text

        btn = QPushButton(display_text, parent)
        btn.setMinimumHeight(min_height)
        btn.setMinimumWidth(10)  # Erlaubt extremes Schrumpfen im Grid
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Sorgt dafür, dass der Text im Button zentriert und umgebrochen wird
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        hover_color = self.adjust_color(color, factor_hover)
        pressed_color = self.adjust_color(color, factor_pressed)

        # Padding reduziert, damit Text mehr Platz hat
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {color};
                color: {fg};
                border-radius: {radius}px;
                border: none;
                padding: 4px 4px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }} 
            QPushButton:pressed {{
                background-color: {pressed_color};
            }} 
        """
        )

        btn.clicked.connect(callback)
        all_buttons_list.append(btn)
        return btn

    def generate_buttons(
        self, parent, button_definitions, all_buttons_list, info_widget=None
    ):
        """
        Erzeugt Buttons basierend auf einer Liste von Definitionen.
        WICHTIG: Muss 'self' als ersten Parameter haben, um create_action_button aufzurufen.
        """
        buttons = {}
        for bd in button_definitions:
            # Aufruf über self, da create_action_button eine Instanzmethode ist
            btn = self.create_action_button(
                parent=parent,
                text=bd["text"],
                color=bd.get("color", "#CCCCCC"),
                callback=bd["callback"],
                all_buttons_list=all_buttons_list,
                fg=bd.get("fg", "white"),
                min_height=self.BUTTON_HEIGHT if hasattr(self, "BUTTON_HEIGHT") else 40,
            )
            buttons[bd.get("key", bd["text"])] = btn
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
        from PyQt6.QtWidgets import QGridLayout, QWidget, QSizePolicy
        from PyQt6.QtGui import QFont

        button_defs = [
            ("git_status", "git_status", "#1E90FF", self.show_commits, "white"),
            (
                "plugin_update",
                "plugin_update",
                "#FF8C00",
                self.plugin_update_button_clicked,
                "white",
            ),
            (
                "restart_tool",
                "restart_tool",
                "#FF4500",
                self.restart_application_with_info,
                "white",
            ),
            (
                "edit_patch_header",
                "edit_patch_header",
                "#32CD32",
                self.edit_patch_header,
                "white",
            ),
            (
                "github_emu_config",
                "github_emu_config_button",
                "#FFA500",
                self.edit_emu_github_config,
                "black",
            ),
            (
                "github_upload_patch",
                "github_upload_patch",
                "#1E90FF",
                github_upload_patch_file,
                "white",
            ),
            (
                "github_upload_emu",
                "github_upload_emu",
                "#1E90FF",
                github_upload_oscam_emu_folder,
                "white",
            ),
            (
                "oscam_emu_git_patch",
                "oscam_emu_git_patch",
                "#32CD32",
                patch_oscam_emu_git,
                "white",
            ),
            (
                "oscam_emu_git_clear",
                "oscam_emu_git_clear",
                "#FF4500",
                self.oscam_emu_git_clear,
                "white",
            ),
            ("terminal", "Terminal", "#2E2E2E", self.open_terminal, "#39FF14"),
        ]

        container = QWidget()
        options_grid = QGridLayout(container)
        options_grid.setSpacing(6)
        options_grid.setContentsMargins(0, 0, 0, 0)

        self.option_buttons = getattr(self, "option_buttons", {})
        cols_per_row = 5

        for idx, (key, text_key, color, callback, *rest) in enumerate(button_defs):
            fg = rest[0] if rest else "white"
            raw_text = self.get_t(text_key, text_key)

            # Dieser Part regelt den Aufruf ohne 'self' Konflikt
            def create_cb(c):
                # Wenn es eine Methode der Klasse ist (self.name)
                if hasattr(c, "__self__"):
                    return lambda: c()
                # Wenn es eine externe Funktion ist
                return lambda: c(
                    gui_instance=self,
                    info_widget=self.info_text,
                    progress_callback=None,
                )

            btn = self.create_action_button(
                parent=self,
                text=raw_text,
                color=color,
                fg=fg,
                callback=create_cb(callback),
                all_buttons_list=self.all_buttons,
                min_height=35,
                radius=self.BUTTON_RADIUS,
            )

            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(self.BUTTON_HEIGHT)
            btn.setFont(QFont("Arial", 9, QFont.Weight.Bold))

            row = idx // cols_per_row
            col = idx % cols_per_row
            options_grid.addWidget(btn, row, col)
            self.option_buttons[key] = (btn, text_key)

        for i in range(cols_per_row):
            options_grid.setColumnStretch(i, 1)

        parent_layout.addWidget(container, 0)

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

    def append_info(self, info_widget, text, level="info"):
        """
        Schreibt eine Nachricht in ein QTextEdit.
        Terminal-Ausgabe ist komplett deaktiviert.
        """
        from PyQt6.QtWidgets import QTextEdit
        from PyQt6.QtGui import QTextCursor  # Wichtig für Punkt 4

        # 1. Widget-Validierung
        if not isinstance(info_widget, QTextEdit):
            if hasattr(self, "info_text") and isinstance(self.info_text, QTextEdit):
                info_widget = self.info_text
            else:
                # TERMINAL-STOP: Hier wurde das print() entfernt.
                return

        # 2. Farben & Formatierung
        colors = {
            "success": "green",
            "warning": "orange",
            "error": "red",
            "info": "gray",
        }
        color = colors.get(level, "black")
        html_text = f'<span style="color:{color}">{text}</span>'

        # 3. GUI-Ausgabe
        info_widget.append(html_text)

        # 4. Automatisches Scrollen
        info_widget.moveCursor(QTextCursor.MoveOperation.End)
        scroll_bar = info_widget.verticalScrollBar()
        if scroll_bar:
            scroll_bar.setValue(scroll_bar.maximum())

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
        Startet das Tool neu via Button-Klick.
        Plattformübergreifend für Windows und Linux optimiert.
        """
        from PyQt6.QtWidgets import QMessageBox, QTextEdit, QApplication
        import sys
        import os
        import subprocess

        # 1. Widget & Sprache sicherstellen
        widget = info_widget or getattr(self, "info_text", None)
        current_lang = str(getattr(self, "LANG", "de")).lower()

        # Falls TEXTS global definiert ist, sonst Fallback
        try:
            lang_pack = TEXTS.get(current_lang, TEXTS.get("en", {}))
        except NameError:
            lang_pack = {}

        # 2. Dialog aufbauen
        msg = QMessageBox(self)
        msg.setWindowTitle(lang_pack.get("restart_tool", "Restart tool"))
        msg.setText(
            lang_pack.get("restart_tool_question", "Do you want to restart now?")
        )

        # Buttons mit Übersetzung
        yes_text = lang_pack.get("yes", "Yes")
        no_text = lang_pack.get("no", "No")
        yes_button = msg.addButton(yes_text, QMessageBox.ButtonRole.YesRole)
        no_button = msg.addButton(no_text, QMessageBox.ButtonRole.NoRole)

        msg.exec()

        if msg.clickedButton() == yes_button:
            info_msg = lang_pack.get("restart_tool_info", "Restarting...")
            if isinstance(widget, QTextEdit):
                widget.append(f'<span style="color:gray">{info_msg}</span>')

            # 3. Plattformübergreifende Neustart-Logik
            try:
                # Aktuellen Python-Interpreter und Skriptpfad ermitteln
                executable = sys.executable
                args = sys.argv[:]

                # Unter Linux/Unix ist os.execl der sauberste Weg (ersetzt Prozess)
                # Unter Windows nutzen wir Popen, da os.execl oft GUI-Instanzen blockiert
                if os.name != "nt":
                    os.execl(executable, executable, *args)
                else:
                    subprocess.Popen([executable] + args)
                    QApplication.quit()
            except Exception as e:
                print(f"Fehler beim Neustart: {e}")
                # Letzter Rettungsanker
                os.system(f"{sys.executable} {' '.join(sys.argv)}")
                QApplication.quit()
        else:
            # Falls "Nein" geklickt wurde, Balken auf 100% setzen
            if progress_callback:
                progress_callback(100)

    def restart_application(self):
        """Interne Hilfsmethode, falls diese separat gerufen wird."""
        self.restart_application_with_info()

    # ===================== ZIP PATCH =====================
    def zip_patch(self, info_widget=None, progress_callback=None):
        """Erstellt ein ZIP des Patches und zeigt den Status im Infoscreen an."""
        from PyQt6.QtWidgets import QTextEdit
        import zipfile
        import os

        widget = info_widget
        if not isinstance(widget, QTextEdit):
            widget = getattr(self, "info_text", None)

        lang = getattr(self, "LANG", "DE")

        def get_msg(key, default, **kwargs):
            template = TEXTS.get(lang, {}).get(key, default)
            try:
                return template.format(**kwargs)
            except:
                return template

        try:
            # Fortschritt: 0% Start
            if progress_callback:
                progress_callback(0)

            # 1️⃣ Existenzprüfung
            if not os.path.exists(PATCH_FILE):
                msg = get_msg(
                    "patch_file_missing", 
                    "Datei nicht gefunden: {path}", 
                    path=PATCH_FILE
                )
                self.append_info(widget, msg, "error")
                if progress_callback:
                    progress_callback(0)
                return

            # Fortschritt: 50% Vorbereitung abgeschlossen
            if progress_callback:
                progress_callback(50)

            # 2️⃣ ZIP erstellen (nur oscam-emu.patch)
            with zipfile.ZipFile(ZIP_FILE, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(PATCH_FILE, os.path.basename(PATCH_FILE))

            # Fortschritt: 100% ZIP erstellt
            if progress_callback:
                progress_callback(100)

            # Erfolgsmeldung
            msg = get_msg(
                "zip_success", 
                "✅ Patch erfolgreich gepackt: {zip_file}", 
                zip_file=ZIP_FILE
            )
            self.append_info(widget, msg, "success")

        except Exception as e:
            self.append_info(widget, f"❌ Fehler beim ZIP: {e}", "error")
            if progress_callback:
                progress_callback(0)

    def run_command(self, cmd, cwd=None):
        self.append_info(self.info_text, f"▶ {cmd}", "info")

        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for line in process.stdout:
            self.append_info(self.info_text, line.strip(), "info")

        process.wait()
        return process.returncode

    def log(self, msg, level="info"):
        colors = {
            "info": THEME["text"],
            "success": THEME["success"],
            "warning": THEME["warning"],
            "error": THEME["error"],
        }
        self.info_text.setTextColor(QColor(colors.get(level, THEME["text"])))
        self.info_text.append(msg)
        self.info_text.moveCursor(QTextCursor.MoveOperation.End)
        QApplication.processEvents()

    def restart_application(self, *args, **kwargs):
        """
        Startet das Tool neu aus dem gleichen Ordner.
        Ignoriert alle überflüssigen Argumente, z.B. progress_callback.
        """
        import subprocess
        import sys
        from PyQt6.QtWidgets import QApplication

        python = sys.executable  # Python-Interpreter
        script = os.path.abspath(__file__)  # Pfad zur aktuellen .py-Datei
        args_list = sys.argv  # alle übergebenen Args übernehmen

        # Neues Tool starten
        subprocess.Popen([python, script] + args_list[1:])

        # Aktuelles Tool sauber beenden
        QApplication.quit()

    def commit_value_changed(self, value):
        self.cfg["commit_count"] = value  # nur im Dict speichern
        self.append_info(
            self.info_text, f"Commit-Anzahl auf {value} gesetzt", "success"
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
        """Alle Texte basierend auf aktueller Sprache aktualisieren."""
        # Labels
        if hasattr(self, "lang_label"):
            self.lang_label.setText(TEXTS[LANG]["language_label"])
        if hasattr(self, "color_label"):
            self.color_label.setText(TEXTS[LANG]["color_label"])
        if hasattr(self, "commit_label"):
            self.commit_label.setText(TEXTS[LANG]["commit_count_label"])

        # ---------- Option Buttons aktualisieren & Callback anpassen ----------
        option_buttons_map = {
            # Patch Buttons
            "patch_create_button": "patch_create",
            "patch_renew_button": "patch_renew",
            "patch_check_button": "patch_check",
            "patch_apply_button": "patch_apply",
            "patch_zip_button": "patch_zip",
            "backup_old_button": "backup_old",
            "clean_folder_button": "clean_folder",
            "change_old_dir_button": "change_old_dir",
            # OSCam Emu Git
            "clean_emu_button": "clean_emu_git",
            "patch_emu_git_button": "patch_emu_git",
            # GitHub
            "github_upload_patch_button": "github_upload_patch",
            "github_upload_emu_button": "github_upload_emu",
            "github_emu_config_button": "github_emu_config_button",
            # Tool / Sonstiges
            "plugin_update_button": "plugin_update",
            "edit_header_button": "edit_patch_header",
            "commits_button": "commits_button",
        }

        # Option Buttons aktualisieren
        for btn, text_key in self.option_buttons.values():
            if text_key in TEXTS[self.LANG]:
                btn.setText(TEXTS[self.LANG][text_key])

        # Grid Buttons aktualisieren
        for key, btn in getattr(self, "buttons", {}).items():
            if key in TEXTS[self.LANG]:
                btn.setText(TEXTS[self.LANG][key])

        # Info Text optional aktualisieren
        if hasattr(self, "info_text") and "info_text" in TEXTS[self.LANG]:
            self.info_text.setPlainText(TEXTS[self.LANG]["info_text"])

    def repaint_ui_colors(self):
        # Labels, ComboBoxes, Buttons, ProgressBar etc.
        for w in [
            getattr(self, "lang_label", None),
            getattr(self, "color_label", None),
            getattr(self, "language_box", None),
            getattr(self, "color_box", None),
        ]:
            if w:
                w.setStyleSheet(
                    f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']};"
                )

        for btn in [
            getattr(self, "edit_header_button", None),
            getattr(self, "commits_button", None),
            getattr(self, "clean_emu_button", None),
            getattr(self, "patch_emu_git_button", None),
            getattr(self, "github_upload_patch_button", None),
            getattr(self, "github_upload_emu_button", None),
            getattr(self, "github_emu_config_button", None),
            getattr(self, "plugin_update_button", None),
            getattr(self, "restart_tool_button", None),
        ]:
            if btn:
                btn.setStyleSheet(
                    f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;"
                )

        for btn in getattr(self, "buttons", {}).values():
            if btn:
                btn.setStyleSheet(
                    f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;"
                )

        if hasattr(self, "commit_label") and self.commit_label:
            self.commit_label.setStyleSheet(
                f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; padding:4px;"
            )
        if hasattr(self, "commit_spin") and self.commit_spin:
            self.commit_spin.setStyleSheet(
                f"""
                QSpinBox {{
                    background-color:{current_diff_colors['bg']};
                    color:{current_diff_colors['text']};
                    border:1px solid {current_diff_colors['text']};
                    border-radius:6px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    background-color:{current_diff_colors['bg']};
                }}
            """
            )
        if hasattr(self, "progress") and self.progress:
            self.progress.setStyleSheet(
                f"QProgressBar::chunk {{background-color:{current_diff_colors['bg']};}}"
            )

        # UI sofort updaten
        self.repaint()
        QApplication.processEvents()

    # Callback nach Schließengg
    def edit_patch_header(self, info_widget=None, progress_callback=None):
        """
        Öffnet die Patch-Datei in einem Dialog zum Bearbeiten des Headers.
        Meldungen werden ins Info-Widget geschrieben oder auf die Konsole.
        """
        widget = info_widget or getattr(self, "info_text", None)

        # Logger wie bei clean_patch_folder
        def log(text, level="info"):
            if hasattr(self, "append_info") and widget:
                self.append_info(widget, text, level)
            else:
                print(f"[{level.upper()}] {text}")

        # Patch-Datei laden
        patch_content = ""
        try:
            with open(PATCH_FILE, "r", encoding="utf-8") as f:
                patch_content = f.read()
        except Exception as e:
            log(f"❌ Fehler beim Öffnen der Patch-Datei: {e}", "error")
            if progress_callback:
                progress_callback(100)
            return

        # Dialog erstellen
        editor = QDialog(self)
        editor.setWindowTitle(
            TEXTS[LANG].get("edit_patch_header_title", "Patch Header bearbeiten")
        )
        editor.resize(800, 600)
        layout = QVBoxLayout(editor)

        text_edit = QTextEdit()
        text_edit.setFont(QFont("Courier", 12))
        text_edit.setText(patch_content)
        layout.addWidget(text_edit)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)

        # Buttons selbst abgreifen und Texte setzen
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save_btn.setText(TEXTS[LANG].get("save", "Speichern"))
        cancel_btn.setText(TEXTS[LANG].get("cancel", "Abbrechen"))

        # Button-Events verbinden
        def save_and_close():
            try:
                with open(PATCH_FILE, "w", encoding="utf-8") as f:
                    f.write(text_edit.toPlainText())
                log("✅ Patch-Datei erfolgreich gespeichert", "success")
            except Exception as e:
                log(f"❌ Fehler beim Speichern der Patch-Datei: {e}", "error")
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

    def plugin_update_button_clicked(self, checked=False, info_widget=None, progress_callback=None):
        """
        Button-Callback: Prüft GitHub-Version und bietet Update NUR bei neuerer Version an.
        """
        from PyQt6.QtWidgets import QTextEdit, QApplication, QMessageBox
        from PyQt6.QtGui import QTextCursor
        import requests, time
        from packaging.version import Version

        lang_key = getattr(self, "LANG", "en").lower()
        widget = info_widget or getattr(self, "info_text", None)
        progress = progress_callback or (self.progress_bar.setValue if hasattr(self, "progress_bar") else None)

        if hasattr(self, "progress_bar"):
            self.progress_bar.setValue(0)
            self.progress_bar.show()

        def log(text_key, level="info", **kwargs):
            colors = {"success": "green", "warning": "orange", "error": "red", "info": "blue"}
            color = colors.get(level, "gray")
            text_template = TEXTS.get(lang_key, TEXTS.get("en", {})).get(text_key, text_key)
            try:
                safe_kwargs = {
                    "current": APP_VERSION,
                    "version": APP_VERSION,
                    "latest": getattr(self, "latest_version", "???"),
                    "error": "Unknown Error",
                }
                safe_kwargs.update(kwargs)
                text = text_template.format(**safe_kwargs)
            except Exception:
                text = text_template

            if isinstance(widget, QTextEdit):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.MoveOperation.End)
                QApplication.processEvents()

        log("update_check_start", "info")
        if progress: progress(10)

        try:
            # FIX: Korrekte URL-Zusammensetzung und direkter Zeitstempel
            version_url = (
                "https://raw.githubusercontent.com/"
                "speedy005/Oscam-Emu-patch-Manager/main/version.txt"
                f"?t={int(time.time())}"
            )
            
            # FIX: Request muss ausgeführt werden, bevor resp.text genutzt wird
            resp = requests.get(version_url, timeout=10)
            resp.raise_for_status()
            
            latest_version = resp.text.strip().lstrip("v")
            self.latest_version = latest_version
            current_version = APP_VERSION.strip().lstrip("v")

            if progress: progress(50)

            # 1. Prüfen ob Update nötig
            if not Version(latest_version) > Version(current_version):
                msg = TEXTS.get(lang_key, TEXTS["en"]).get("up_to_date", "Plugin ist aktuell (v{v})").format(v=current_version)
                QMessageBox.information(self, "Update", msg)
                log("update_no_update", "success")
                if progress: progress(100)
                return

            # 2. Wenn Update verfügbar
            if progress: progress(80)
            
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle(TEXTS.get(lang_key, TEXTS["en"]).get("update_available_title", "Update verfügbar"))
            
            raw_msg = TEXTS.get(lang_key, TEXTS["en"]).get(
                "update_available_msg", 
                "Version {latest} verfügbar. Aktuell: {current}. Jetzt updaten?"
            )
            msg_box.setText(raw_msg.format(current=APP_VERSION, latest=latest_version))
            
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            # Button-Texte übersetzen
            btn_yes = msg_box.button(QMessageBox.StandardButton.Yes)
            if btn_yes: btn_yes.setText(TEXTS.get(lang_key, {}).get("yes", "Ja"))
            btn_no = msg_box.button(QMessageBox.StandardButton.No)
            if btn_no: btn_no.setText(TEXTS.get(lang_key, {}).get("no", "Nein"))
            
            result = msg_box.exec()

            if result == QMessageBox.StandardButton.Yes:
                if hasattr(self, "plugin_update_action"):
                    self.plugin_update_action(
                        latest_version=latest_version, 
                        progress_callback=progress
                    )
            else:
                log("update_declined", "info")
                if progress: progress(100)

        except Exception as e:
            log("update_fail", "error", error=str(e))
            if progress: progress(0)

    # ---------------------
    # UPDATE CHECK
    # ---------------------
    def check_for_update_on_start(self):
        """
        Prüft beim Start die GitHub-Version, aktualisiert den Update-Button
        und fragt den Nutzer, ob er direkt updaten möchte.
        """
        from PyQt6.QtWidgets import QTextEdit, QApplication, QMessageBox
        from PyQt6.QtGui import QTextCursor
        import time, requests
        from packaging.version import Version

        widget = getattr(self, "info_text", None)
        progress = getattr(self, "progress_bar", None)
        lang = getattr(self, "LANG", "de").lower()

        if progress:
            progress.setValue(0)
            progress.show()

        def log(text_key, level="info", **kwargs):
            colors = {"success": "green", "warning": "orange", "error": "red", "info": "blue"}
            color = colors.get(level, "gray")
            text_template = TEXTS.get(lang, TEXTS.get("en", {})).get(text_key, text_key)
            try:
                safe_params = {
                    "current": APP_VERSION,
                    "version": APP_VERSION,
                    "latest": getattr(self, "latest_version", "???"),
                    "error": kwargs.get("error", "Unknown Error"),
                }
                safe_params.update(kwargs)
                text = text_template.format(**safe_params)
            except Exception:
                text = text_template

            if isinstance(widget, QTextEdit):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.MoveOperation.End)
                QApplication.processEvents()

        log("update_check_start", "info")
        
        try:
            # FIX: URL-Format und Zeitstempel
            version_url = (
                "https://raw.githubusercontent.com/"
                "speedy005/Oscam-Emu-patch-Manager/main/version.txt"
                f"?t={int(time.time())}"
            )

            # FIX: Den Request auch wirklich absenden!
            resp = requests.get(version_url, timeout=10)
            resp.raise_for_status()

            latest_version = resp.text.strip().lstrip("v")
            self.latest_version = latest_version
            
            if hasattr(self, "update_plugin_button_state"):
                self.update_plugin_button_state()

            current_version = APP_VERSION.strip().lstrip("v")

            # Kein Update nötig
            if not Version(latest_version) > Version(current_version):
                log("update_current_version", "success", version=current_version)
                log("update_no_update", "info")
                if progress: progress.setValue(100)
                return

            # Update verfügbar
            if progress: progress.setValue(80)

            # MessageBox Setup
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle(TEXTS.get(lang, {}).get("update_available_title", "Update verfügbar"))
            
            raw_dialog_text = TEXTS.get(lang, {}).get(
                "update_available_msg", 
                "Neue Version {latest} verfügbar. Jetzt updaten?"
            )
            msg_box.setText(raw_dialog_text.format(current=current_version, latest=latest_version))
            
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            # Button-Texte übersetzen
            btn_yes = msg_box.button(QMessageBox.StandardButton.Yes)
            if btn_yes: btn_yes.setText(TEXTS.get(lang, {}).get("yes", "Ja"))
            btn_no = msg_box.button(QMessageBox.StandardButton.No)
            if btn_no: btn_no.setText(TEXTS.get(lang, {}).get("no", "Nein"))
            
            msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

            # Ergebnis abfangen
            result = msg_box.exec()

            if result == QMessageBox.StandardButton.Yes:
                if hasattr(self, "plugin_update_action"):
                    self.plugin_update_action(
                        latest_version=latest_version,
                        progress_callback=progress.setValue if progress else None,
                    )
            else:
                log("update_declined", "info")
                log("update_current_version", "success", version=current_version)
                if progress: progress.setValue(100)

        except Exception as e:
            log("update_fail", "error", error=str(e))
            if progress: progress.setValue(0)

    # ---------------------
    # TOOLS CHECK
    # ---------------------

    def check_for_plugin_update(self):
        """Prüft auf Updates und hängt den Status an den bestehenden Infoscreen an."""
        import requests
        from PyQt6.QtWidgets import QTextEdit

        # 1. Sprache sicher abrufen
        lang = str(getattr(self, "LANG", "de")).lower()

        # Sicherer Zugriff: Wenn 'de', dann Fallback auf 'de', sonst 'en'
        fallback_dict = TEXTS.get("de", {}) if lang == "de" else TEXTS.get("en", {})
        t = TEXTS.get(lang, fallback_dict)

        widget = getattr(self, "info_text", None)

        if hasattr(self, "append_info") and widget:
            self.append_info(widget, "\n" + "-" * 30 + "\n", "info")

        try:
            # 2. Version von GitHub holen
            version_url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/version.txt"
            resp = requests.get(version_url, timeout=10)
            resp.raise_for_status()

            latest_version_str = resp.text.strip().lstrip("v")
            current_version_str = APP_VERSION.strip().lstrip("v")
            self.latest_version = latest_version_str

            # Button Status aktualisieren
            if hasattr(self, "update_plugin_update_button_state"):
                self.update_plugin_update_button_state()
            elif hasattr(self, "update_plugin_button_state"):
                self.update_plugin_button_state()

            # 3. Versions-Vergleich (Nutzt globales Version-Objekt)
            lv = Version(latest_version_str)
            cv = Version(current_version_str)

            if lv > cv:
                # Nutzt Key aus Dictionary, Fallback-Text ist Englisch
                template = t.get(
                    "update_available",
                    "Update available: {latest} (current: {current})",
                )
                msg = template.format(
                    latest=latest_version_str, current=current_version_str
                )
                tag = "warning"
            else:
                # Nutzt Key aus Dictionary, Fallback-Text ist Englisch
                template = t.get(
                    "plugin_uptodate", "✅ Plugin is up to date (Version: {current})"
                )
                msg = template.format(current=current_version_str)
                tag = "success"

            if hasattr(self, "append_info") and widget:
                self.append_info(widget, msg, tag)

        except Exception as e:
            error_msg = t.get("update_error", "Update error: {error}").format(
                error=str(e)
            )
            if hasattr(self, "append_info") and widget:
                self.append_info(widget, error_msg, "error")

    def check_tool(self, name, cmd):
        try:
            result = subprocess.getoutput(cmd).splitlines()[0]
            if "not found" in result.lower() or "error" in result.lower():
                self.info_text.append(
                    TEXTS[LANG]["tool_missing"].format(name=name, error=result)
                )
            else:
                self.info_text.append(
                    TEXTS[LANG]["tool_ok"].format(name=name, version=result)
                )
        except Exception:
            self.info_text.append(
                TEXTS[LANG]["tool_missing"].format(name=name, error="Fehler")
            )

    def check_tools_on_start(self):
        """
        Prüft die externen Tools beim Start. 
        Unter Windows nur Git, unter Linux zusätzlich zip/patch.
        Zeigt Meldungen im GUI-Info-Widget an.
        """
        import shutil, os, json

        self.info_text.clear()

        # Config laden
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                try:
                    cfg = json.load(f)
                except Exception:
                    cfg = {}
        else:
            cfg = {}

        # Tools definieren
        tools_to_check = ["git"]
        if os.name != "nt":  # Linux/Unix: prüfe zusätzliche Tools
            tools_to_check.extend(["zip", "patch"])

        all_ok = True
        for tool in tools_to_check:
            if shutil.which(tool) is None:
                if os.name == "nt" and tool in ["zip", "patch"]:
                    # Windows: zip/patch sind nicht nötig, nur Hinweis
                    self.append_info(
                        self.info_text,
                        f"ℹ️ Windows: {tool} wird nicht benötigt, falls Python benutzt wird.",
                        "info",
                )
                else:
                    self.append_info(
                        self.info_text,
                        f"⚠️ {tool} fehlt im System!",
                        "warning",
                    )
                    all_ok = False
            else:
                self.append_info(
                    self.info_text,
                    f"✅ {tool} ist bereit.",
                    "success",
                )

        # Zusammenfassung
        if all_ok:
            self.append_info(self.info_text, "✅ System-Check erfolgreich.", "success")
            cfg["tools_ok"] = True
        else:
            self.append_info(
                self.info_text,
                "❌ Bitte fehlende Tools manuell installieren.",
                "error",
            )
            cfg["tools_ok"] = False

        # Config speichern
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        # =====================
        # INIT UI
        # =====================

    def init_ui(self):
        from PyQt6.QtWidgets import (
            QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
            QWidget, QTextEdit, QComboBox, QSpinBox, QProgressBar, QApplication, QFrame
        )
        from PyQt6.QtGui import QPixmap, QFont
        from PyQt6.QtCore import Qt, QSize, QTimer, QDateTime
        import requests

        # ---------------------------------------------------------
        # 1. Grundwerte
        # ---------------------------------------------------------
        self.TITLE_HEIGHT = 45
        self.BUTTON_HEIGHT = 40
        self.BUTTON_RADIUS = 10

        # ---------------------------------------------------------
        # Hauptlayout
        # ---------------------------------------------------------
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(20, 0, 20, 10)

        # ---------------------------------------------------------
        # HEADER-SECTION (BANNER)
        # ---------------------------------------------------------
        header_widget = QFrame()
        header_widget.setFixedHeight(90)
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
        icon = self.style().standardIcon(QApplication.style().StandardPixmap.SP_MessageBoxInformation)
        self.info_button.setIcon(icon)
        self.info_button.setIconSize(QSize(28, 28))
        self.info_button.clicked.connect(self.show_info)
        left_header_layout.addWidget(self.info_button)

        # Uhr & Datum vertikal in eigenem Container
        time_date_container = QWidget()
        time_date_layout = QVBoxLayout(time_date_container)
        time_date_layout.setContentsMargins(0, 0, 0, 0)
        time_date_layout.setSpacing(2)
        time_date_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self.digital_clock = QLabel("--:--:--")
        self.digital_clock.setFont(QFont("Bold", 22, QFont.Weight.Bold))
        self.digital_clock.setStyleSheet("color: red;")
        self.digital_clock.setAlignment(Qt.AlignmentFlag.AlignLeft)
        time_date_layout.addWidget(self.digital_clock)

        # Datum-Label
        self.date_label = QLabel("--.--.----")
        self.date_label.setFont(QFont("Bold", 22))
        self.date_label.setStyleSheet("color: green;")  # <-- hier Grün!
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
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
        right_header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        by_label = QLabel("by speedy005")
        by_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        by_label.setStyleSheet("color: blue;")
        by_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        v_label = QLabel(f"v{APP_VERSION}")
        v_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
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
        main_layout.addWidget(self.info_text, 10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")  # Zeigt nur den Prozentsatz
        main_layout.addWidget(self.progress_bar)

        # ---------------------------------------------------------
        # KONTROLL-BLOCK MIT HEADER
        # ---------------------------------------------------------
        controls_group = QFrame()
        controls_group.setStyleSheet("""
        QFrame {
            border: 1px solid #bbb;
            border-radius: 10px;
            background-color: #f7f7f7;
        }
        """)
        controls_group_layout = QVBoxLayout(controls_group)
        controls_group_layout.setContentsMargins(10, 8, 10, 10)
        controls_group_layout.setSpacing(6)

        controls_header = QLabel(self.get_t("settings_header", "Einstellungen"))
        controls_header.setFixedHeight(28)
        controls_header.setStyleSheet("""
        QLabel {
            background-color: #3a6ea5;
            color: white;
            font-size: 15px;
            font-weight: bold;
            padding-left: 10px;
            border-radius: 6px;
        }
        """)
        controls_group_layout.addWidget(controls_header)

        controls_row = QWidget()
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(10)

        CONTROL_HEIGHT = self.BUTTON_HEIGHT
        control_style = f"""
        QComboBox, QSpinBox {{
            font-size: 14px;
            border-radius: {self.BUTTON_RADIUS}px;
            border: 1px solid #ccc;
            padding: 4px 8px;
        }}
        """

        def make_label(text):
            lbl = QLabel(text)
            lbl.setFixedHeight(CONTROL_HEIGHT)
            lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            return lbl

        self.lang_label = make_label(self.get_t("language_label", "Language:"))
        self.language_box = QComboBox()
        self.language_box.addItems(["EN", "DE"])
        self.language_box.setFixedSize(80, CONTROL_HEIGHT)
        self.language_box.setStyleSheet(control_style)
        self.language_box.currentIndexChanged.connect(self.change_language)

        self.color_label = make_label(self.get_t("color_label", "Farbe:"))
        self.color_box = QComboBox()
        self.color_box.addItems(list(DIFF_COLORS.keys()))
        self.color_box.setFixedSize(150, CONTROL_HEIGHT)
        self.color_box.setStyleSheet(control_style)
        self.color_box.currentIndexChanged.connect(self.change_colors)

        self.commit_label = make_label(self.get_t("commit_count_label", "Commits:"))
        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1, 20)
        self.commit_spin.setFixedSize(70, CONTROL_HEIGHT)
        self.commit_spin.setStyleSheet(control_style)
        self.commit_spin.valueChanged.connect(self.commit_value_changed)

        self.btn_check_tools = QPushButton(self.get_t("check_tools_button", "🛠️ Tools prüfen"))
        self.btn_check_tools.setFixedSize(160, CONTROL_HEIGHT)
        self.btn_check_tools.setStyleSheet("""
        QPushButton {
            background-color: #FFD700;
            font-weight: bold;
            border-radius: 6px;
        }
        QPushButton:hover { background-color: #ffea70; }
        """)
        self.btn_check_tools.clicked.connect(self.manual_tool_check)

        controls_layout.addWidget(self.lang_label)
        controls_layout.addWidget(self.language_box)
        controls_layout.addSpacing(15)
        controls_layout.addWidget(self.color_label)
        controls_layout.addWidget(self.color_box)
        controls_layout.addSpacing(15)
        controls_layout.addWidget(self.commit_label)
        controls_layout.addWidget(self.commit_spin)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(self.btn_check_tools)
        controls_layout.addStretch(1)

        controls_group_layout.addWidget(controls_row)
        main_layout.addWidget(controls_group)

        # ---------------------------------------------------------
        # BUTTON-GRIDS
        # ---------------------------------------------------------
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
        self.setMinimumSize(1200, 850)
        self.showMaximized()


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

    def on_button_clicked(self, key, func):
        self.set_active_button(key)
        self.run_action(func)

    def set_active_button(self, active_key):
        self.active_button_key = active_key
        for key, btn in self.buttons.items():
            if key == active_key:
                btn.setStyleSheet(
                    f"background-color:#00FF00; color:black; border-radius:{self.BUTTON_RADIUS}px; min-height:{self.BUTTON_HEIGHT}px;"
                )
            else:
                btn.setStyleSheet(
                    f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:{self.BUTTON_RADIUS}px; min-height:{self.BUTTON_HEIGHT}px;"
                )

    # ---------- change_colors ----------
    def change_colors(self):
        global current_diff_colors, current_color_name

        # Aktuelle Farbe aus ComboBox laden oder aus Config
        current_color_name = (
            self.color_box.currentText()
            if hasattr(self, "color_box")
            else self.cfg.get("color", "Classic")
        )
        base_colors = DIFF_COLORS.get(current_color_name, DIFF_COLORS["Classic"])

        # Hover / Active Farben ableiten
        bg = base_colors["bg"]
        current_diff_colors = {
            **base_colors,
            "hover": self.adjust_color(bg, 1.15),
            "active": self.adjust_color(bg, 0.85),
        }

        # UI-Farben anwenden
        self.repaint_ui_colors()

        # Config aktualisieren (nur im Speicher, nicht neu laden)
        self.cfg["color"] = current_color_name

    def setup_grid_buttons(self):
        from PyQt6.QtWidgets import QGridLayout, QWidget, QSizePolicy
        from PyQt6.QtGui import QFont

        # WICHTIG: Nutze das bereits in init_ui definierte Layout
        if hasattr(self, "layout_grid_buttons"):
            grid_layout = self.layout_grid_buttons
        else:
            # Fallback falls die Referenz fehlt
            grid_layout = QGridLayout()
            grid_container = QWidget()
            grid_container.setLayout(grid_layout)
            if self.layout():
                self.layout().addWidget(grid_container, stretch=4)

        grid_layout.setSpacing(10)

        # Aktions-Buttons Definition
        grid_actions = [
            ("patch_create", lambda: create_patch(self, self.info_text, None)),
            ("patch_renew", lambda: create_patch(self, self.info_text, None)),
            ("patch_check", lambda: self.check_patch(self.info_text, None)),
            (
                "patch_apply",
                lambda: (
                    (
                        self.progress_bar.setValue(0)
                        if hasattr(self, "progress_bar")
                        else None
                    ),
                    self.apply_patch(self.info_text, None),
                ),
            ),
            ("patch_zip", lambda: self.zip_patch(self.info_text, None)),
            ("backup_old", lambda: backup_old_patch(self, self.info_text, None)),
            ("clean_folder", lambda: clean_patch_folder(self, self.info_text, None)),
            ("change_old_dir", lambda: self.change_old_patch_dir(self.info_text, None)),
            ("exit", self.close_with_confirm),
        ]

        self.buttons = {}
        cols = 3
        for idx, (key, func) in enumerate(grid_actions):
            # Erstellt den Button über deine zentrale Funktion
            btn = self.create_action_button(
                parent=self,
                text=self.get_t(key, key),
                color="#1E90FF",
                fg="white",
                callback=lambda checked=False, f=func, k=key: (
                    self.set_active_button(k),
                    f(),
                ),
                all_buttons_list=self.all_buttons,
                min_height=self.BUTTON_HEIGHT,
                radius=self.BUTTON_RADIUS,
            )

            # Layout-Verhalten: Button füllt den verfügbaren Platz im Grid
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )

            row, col = divmod(idx, cols)
            grid_layout.addWidget(btn, row, col)
            self.buttons[key] = btn

        # Erzwingt die gleichmäßige Verteilung der Spaltenbreite
        for i in range(cols):
            grid_layout.setColumnStretch(i, 1)

    def update_language(self):
        """Übersetzt alle Buttons, Labels und den großen Infoscreen."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QTextCursor

        # 1. Sprache normieren (Kürzel de/en)
        lang = str(getattr(self, "LANG", "de")).lower()

        # 2. Dictionary sicher abrufen (Fallback auf Englisch bei Fehlern)
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))

        def get_t(k, default=None):
            if k in lang_dict:
                return lang_dict[k]
            clean = str(k).replace("_", " ").title()
            mapping = {
                "Language Label": "Language:" if lang == "en" else "Sprache auswählen:",
                "Color Label": "Color:" if lang == "en" else "Farbe wählen:",
                "Commit Count Label": "Commits:" if lang == "en" else "Commits:",
                "Check Tools Button": (
                    "🛠️ Check Tools" if lang == "en" else "🛠️ Tools prüfen"
                ),
            }
            return mapping.get(clean, default if default else clean)

        # A) GRID-BUTTONS
        if hasattr(self, "buttons"):
            for key, btn in self.buttons.items():
                btn.setText(get_t(key))

        # B) OPTION-BUTTONS (Kopfzeile) - FIX: Hintergrundfarben wiederherstellen
        if hasattr(self, "option_buttons"):
            for key, val in self.option_buttons.items():
                if isinstance(val, (list, tuple)) and len(val) >= 2:
                    btn, text_key = val[0], val[1]
                    if text_key == "plugin_update":
                        continue

                    # Text setzen
                    translated = get_t(text_key)
                    btn.setText(
                        f"💻 {translated}"
                        if "terminal" in str(key).lower()
                        else translated
                    )

                    # --- FARB-FIX START ---
                    # Wir holen die Farben aus dem gespeicherten Tuple (val[2] = BG, val[4] = FG)
                    # Falls das Tuple kürzer ist, nutzen wir Fallbacks
                    bg = val[2] if len(val) >= 3 else "#1E90FF"
                    fg = val[4] if len(val) >= 5 else "white"

                    # StyleSheet zwingend neu setzen, sonst wird es grau/standard
                    btn.setStyleSheet(
                        f"background-color: {bg}; color: {fg}; font-weight: bold; border-radius: 4px;"
                    )
                    # --- FARB-FIX ENDE ---

        # C) TOOLS-BUTTON & LABELS (Commit-Zeile)
        if hasattr(self, "btn_check_tools"):
            self.btn_check_tools.setText(get_t("check_tools_button", "🛠️ Tools"))

        if hasattr(self, "lang_label"):
            self.lang_label.setText(get_t("language_label", "Language:"))

        if hasattr(self, "color_label"):
            self.color_label.setText(get_t("color_label", "Color:"))

        if hasattr(self, "commit_label"):
            self.commit_label.setText(get_t("commit_count_label", "Commits:"))

        # E) INFOSCREEN / ANLEITUNG
        if hasattr(self, "info_text"):
            full_info = get_t("info_text", None)
            if full_info:
                self.info_text.setText(full_info)
                self.info_text.moveCursor(QTextCursor.MoveOperation.Start)

        QApplication.processEvents()

    def change_language(self):
        """Wird aufgerufen, wenn die Dropdown-Box geändert wird."""
        if not hasattr(self, "language_box"):
            return

        # 1. Sprache aus GUI ermitteln & setzen
        selected = self.language_box.currentText().lower()
        # Setzt self.LANG auf "de" oder "en"
        self.LANG = "de" if "de" in selected else "en"

        # 2. In Konfiguration speichern (für Neustart)
        self.cfg["language"] = self.LANG
        # Nutzt die globale save_config Funktion
        if "save_config" in globals():
            save_config(self.cfg)
        elif hasattr(self, "save_config"):
            self.save_config()

        # 3. UI-Elemente und Anleitung (info_text) sofort übersetzen
        # Hinweis: update_language überschreibt info_text mit der Anleitung
        self.update_language()

        # 4. Status-Meldungen in der neuen Sprache neu generieren
        # Wir nutzen QTimer, damit die Meldungen sauber UNTER die Anleitung
        # im info_text angehängt werden, nachdem update_language fertig ist.

        # Plugin-Status prüfen (Version etc.)
        if hasattr(self, "check_for_plugin_update"):
            QTimer.singleShot(500, self.check_for_plugin_update)

        # System-Tools prüfen (git, patch etc.)
        if hasattr(self, "manual_tool_check"):
            QTimer.singleShot(200, self.manual_tool_check)

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
        """Öffnet den GitHub-Konfigurationsdialog mit Sicherheits-Fallbacks für TEXTS"""
        # 1. Sprache sicher abrufen (kleingeschrieben für Dictionary)
        current_lang = str(getattr(self, "LANG", "de")).lower()
        dialog = GithubConfigDialog(self)

        # 2. Hilfsfunktion für Texte (muss get_txt heißen, damit es unten passt)
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

        # 5. Save/Cancel Buttons übersetzen (Nutzt jetzt einheitlich get_txt)
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

        # 7. Progress-Bar Abschluss
        if progress_callback:
            progress_callback(100)

    # =====================
    # INFO BUTTON CALLBACK
    # =====================
    def show_info(self):
        lang = getattr(self, "LANG", LANG)  # aktuelle GUI-Sprache verwenden
        text = TEXTS[lang].get("info_text", "Keine Info verfügbar.")
        dlg = QMessageBox(self)
        dlg.setWindowTitle(TEXTS[lang].get("info_title", "Info"))
        dlg.setText(text)
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        dlg.exec()

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
        Sicherer Zugriff auf das Info-Widget, um AttributeError zu vermeiden.
        Startmeldung in Orange, Endmeldung in Grün.
        """
        from PyQt6.QtWidgets import QTextEdit

        # Widget absichern
        if not isinstance(info_widget, QTextEdit):
            info_widget = getattr(self, "info_text", None)
            if info_widget is None:
                return  # kein Widget vorhanden, abbrechen

        lang = getattr(self, "LANG", "en").lower()  # Sprache klein, für TEXTS-Dict

        # --- Startmeldung ---
        self.append_info(
            info_widget,
            TEXTS.get(lang, {}).get("loading_commits", "Lade Commits..."),
            "warning",  # Orange
        )

        # Git log ausführen
        try:
            if not os.path.exists(TEMP_REPO):
                self.append_info(info_widget, "❌ Repo-Ordner nicht gefunden.", "error")
                return

            num_commits = (
                self.commit_spin.value() if hasattr(self, "commit_spin") else 10
            )
            cmd = f"git -C {TEMP_REPO} log -n {num_commits} --oneline"

            output = self.run_command(cmd, cwd=TEMP_REPO)

            if output:
                for line in output.splitlines():
                    self.append_info(info_widget, line, "info")
            else:
                self.append_info(info_widget, "Keine Commits gefunden.", "warning")

            # --- Endmeldung ---
            self.append_info(
                info_widget,
                TEXTS.get(lang, {}).get(
                    "commits_loaded", "Commits erfolgreich geladen"
                ),
                "success",  # Grün
            )

        except Exception as e:
            self.append_info(
                info_widget,
                f"❌ Fehler beim Abrufen der Commits: {e}",
                "error",
            )

        # Fortschrittscallback am Ende
        if progress_callback:
            try:
                progress_callback(100)
            except:
                pass

    # ===================== OSCam-EMU BUTTON WRAPPERS =====================
    def oscam_emu_git_patch(self, info_widget=None, progress_callback=None):
        """Patch erstellen und auf GitHub hochladen."""
        info_widget = info_widget or getattr(self, "info_text", None)
        lang = getattr(self, "LANG", "de").lower()  # aktuelle GUI-Sprache

        # Sicherer Zugriff auf TEXTS
        lang_dict = globals().get("TEXTS", {}).get(lang, {})
        start_msg = lang_dict.get(
        "oscam_emu_git_patch_start", "🔹 OSCam-Emu Git Patch wird erstellt..."
        )

        # Info-Meldung anzeigen
        if hasattr(self, "append_info") and info_widget:
            self.append_info(info_widget, start_msg, "info")
        else:
            print(f"[INFO] {start_msg}")

        # GitHub Config laden
        load_func = globals().get("load_github_config") or getattr(self, "load_github_config", None)
        if not load_func:
            print("[ERROR] GitHub Config Funktion fehlt!")
            return
        cfg = load_func()
    
        # Upload starten
        upload_func = globals().get("_github_upload")
        if not upload_func:
            print("[ERROR] GitHub Upload Funktion fehlt!")
            return

        try:
            upload_func(
                PATCH_EMU_GIT_DIR,
                cfg.get("emu_repo_url"),
                branch=cfg.get("emu_branch", "master"),
                username=cfg.get("username"),
                token=cfg.get("token"),
                user_name=cfg.get("user_name"),
               user_email=cfg.get("user_email"),
                info_widget=info_widget,
                progress_callback=progress_callback,
            )
        except Exception as e:
            err_msg = f"[ERROR] Upload fehlgeschlagen: {e}"
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, err_msg, "error")
            else:
                print(err_msg)
            if progress_callback:
                progress_callback(0)
            return

        # Wenn erfolgreich
        if progress_callback:
            progress_callback(100)

    

    def oscam_emu_git_clear(self, info_widget=None, progress_callback=None):
        """OSCAm-EMU Git Ordner leeren."""
        info_widget = info_widget or getattr(self, "info_text", None)
        lang = getattr(self, "LANG", "de").lower()

        # Sicherer Zugriff auf TEXTS
        lang_dict = globals().get("TEXTS", {}).get(lang, {})
        clear_msg = lang_dict.get(
            "oscam_emu_git_clearing", "🔹 OSCam-Emu Git Ordner wird geleert..."
        )

        # Info-Meldung anzeigen
        if info_widget and hasattr(self, "append_info"):
            self.append_info(info_widget, clear_msg, "info")
        else:
            print(f"[INFO] {clear_msg}")

        # Git Ordner leeren
        clean_func = globals().get("clean_oscam_emu_git") or getattr(self, "clean_oscam_emu_git", None)
        if not clean_func:
            err_msg = "[ERROR] Funktion clean_oscam_emu_git fehlt!"
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, err_msg, "error")
            else:
                print(err_msg)
            if progress_callback:
                progress_callback(0)
            return

        try:
            clean_func(info_widget=info_widget, progress_callback=progress_callback)
        except Exception as e:
            err_msg = f"[ERROR] Fehler beim Leeren des Ordners: {e}"
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, err_msg, "error")
            else:
                print(err_msg)
            if progress_callback:
                progress_callback(0)
            return

        if progress_callback:
            progress_callback(100)

    def check_patch(self, info_widget=None, progress_callback=None):
        """Prüft, ob der Patch auf das TEMP_REPO angewendet werden kann."""
        info_widget = info_widget or getattr(self, "info_text", None)
        lang = getattr(self, "LANG", "de").lower()

        # Sicherer Zugriff auf TEXTS
        lang_dict = globals().get("TEXTS", {}).get(lang, {})
        patch_missing = lang_dict.get("patch_file_missing", "⚠️ Patch-Datei fehlt!")
        patch_ok = lang_dict.get("patch_check_ok", "✅ Patch kann angewendet werden.")
        patch_fail = lang_dict.get("patch_check_fail", "❌ Patch kann nicht angewendet werden.")

        if not os.path.exists(PATCH_FILE):
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, patch_missing, "error")
            else:
                 print(f"[ERROR] {patch_missing}")
            if progress_callback:
                progress_callback(0)
            return

        # run_bash prüfen
        run_func = globals().get("run_bash") or getattr(self, "run_bash", None)
        if not run_func:
            err_msg = "[ERROR] Funktion run_bash fehlt!"
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, err_msg, "error")
            else:
                print(err_msg)
            if progress_callback:
                progress_callback(0)
            return

        try:
            code = run_func(
                f"git apply --check {PATCH_FILE}",
                cwd=TEMP_REPO,
                info_widget=info_widget,
                lang=lang,
            )
        except Exception as e:
            err_msg = f"[ERROR] Fehler beim Prüfen des Patches: {e}"
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, err_msg, "error")
            else:
                print(err_msg)
            if progress_callback:
                progress_callback(0)
            return

        if code == 0:
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, patch_ok, "success")
            else:
                print(f"[SUCCESS] {patch_ok}")
        else:
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, patch_fail, "error")
            else:
                print(f"[ERROR] {patch_fail}")

        if progress_callback:
            progress_callback(100)

    def apply_patch(self, info_widget=None, progress_callback=None):
        """Wendet den Patch auf TEMP_REPO an."""
        info_widget = info_widget or getattr(self, "info_text", None)
        lang = getattr(self, "LANG", "de").lower()

        # Sicherer Zugriff auf TEXTS
        lang_dict = globals().get("TEXTS", {}).get(lang, {})
        patch_missing = lang_dict.get("patch_file_missing", "❌ Patch-Datei fehlt!")
        patch_success = lang_dict.get("patch_applied", "✅ Patch erfolgreich angewendet")
        patch_fail = lang_dict.get("patch_apply_fail", "❌ Patch konnte nicht angewendet werden")

        if not os.path.exists(PATCH_FILE):
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, patch_missing, "error")
            else:
                print(f"[ERROR] {patch_missing}")
            if progress_callback:
                progress_callback(0)
            return

        # run_bash prüfen
        run_func = globals().get("run_bash") or getattr(self, "run_bash", None)
        if not run_func:
            err_msg = "[ERROR] Funktion run_bash fehlt!"
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, err_msg, "error")
            else:
                print(err_msg)
            if progress_callback:
                progress_callback(0)
            return

        # Logger-Funktion
        logger = lambda text, level="info": (
            self.append_info(info_widget, text, level) if info_widget and hasattr(self, "append_info") else print(f"[{level.upper()}] {text}")
        )

        try:
            code = run_func(f"git apply {PATCH_FILE}", cwd=TEMP_REPO, logger=logger)
        except Exception as e:
            err_msg = f"[ERROR] Fehler beim Anwenden des Patches: {e}"
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, err_msg, "error")
            else:
                print(err_msg)
            if progress_callback:
                progress_callback(0)
            return

        if code == 0:
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, patch_success, "success")
            else:
                print(f"[SUCCESS] {patch_success}")
            if progress_callback:
                progress_callback(100)
        else:
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, patch_fail, "error")
            else:
                print(f"[ERROR] {patch_fail}")
            if progress_callback:
                progress_callback(0)

    def change_old_(self, info_widget=None, progress_callback=None):
        """Ändert den OLD_ Patch-Ordner."""
        global OLD_, OLD_PATCH_FILE, ALT_PATCH_FILE

        info_widget = info_widget or getattr(self, "info_text", None)
        lang = getattr(self, "LANG", "de").lower()
        lang_dict = globals().get("TEXTS", {}).get(lang, {})

        # Fallback-Texte
        dlg_title = lang_dict.get("change_old_dir", "📁 Wähle den OLD-Ordner")
        success_msg = lang_dict.get(
            "old_patch_path_changed", "✅ Alter Patch-Pfad geändert: {OLD_}"
        )
        cancelled_msg = lang_dict.get("old_patch_path_cancelled", "ℹ️ Aktion abgebrochen")

        # Ordnerdialog
        new_dir = QFileDialog.getExistingDirectory(self, dlg_title, OLD_)

        if new_dir:
            OLD_ = new_dir
            OLD_PATCH_FILE = os.path.join(OLD_, "oscam-emu.patch")
            ALT_PATCH_FILE = os.path.join(OLD_, "oscam-emu.altpatch")

            # Konfiguration speichern
            if hasattr(self, "commit_spin"):
                save_config(self.commit_spin.value())

            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, success_msg.format(OLD_=OLD_), "success")
            else:
                print(f"[SUCCESS] {success_msg.format(OLD_=OLD_)}")
            if progress_callback:
                progress_callback(100)
        else:
            if info_widget and hasattr(self, "append_info"):
                self.append_info(info_widget, cancelled_msg, "info")
            else:
                print(f"[INFO] {cancelled_msg}")
            if progress_callback:
                progress_callback(0)

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

    # Standard-Imports
    import sys
    from PyQt6.QtWidgets import QApplication
    from oscam_patch_manager import (
        PatchManagerGUI,
        TEXTS,
        fill_missing_keys,
        ensure_dir,
        PLUGIN_DIR,
        ICON_DIR,
        TEMP_REPO,
        load_config,
    )

    # ⚠️ Verhindert Accessibility-Warnungen unter Linux
    import os

    os.environ["NO_AT_BRIDGE"] = "1"

    # 1️⃣ Wichtige Verzeichnisse sicherstellen
    ensure_dir(PLUGIN_DIR)
    ensure_dir(ICON_DIR)
    ensure_dir(TEMP_REPO)

    # 2️⃣ Konfiguration laden
    load_config()

    # 3️⃣ Fehlende TEXTS automatisch auffüllen
    fill_missing_keys(TEXTS)  # einmalig vor GUI-Start

    # 4️⃣ QApplication erstellen
    app = QApplication(sys.argv)

    # 5️⃣ GUI starten
    window = PatchManagerGUI()
    window.showMaximized()  # optional: .show() für normale Größe

    # 6️⃣ Event-Loop starten
    sys.exit(app.exec())
