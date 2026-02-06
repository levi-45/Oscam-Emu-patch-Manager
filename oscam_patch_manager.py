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
APP_VERSION = "2.4.7"


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


def ensure_dir(directory):
    """Erstellt das Verzeichnis, falls es noch nicht existiert."""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            print(f"[ERROR] Konnte Verzeichnis {directory} nicht erstellen: {e}")


class StreamToGui:
    """Leitet stdout/stderr an einen Slot (Funktion) weiter."""

    def __init__(self, slot):
        self.slot = slot

    def write(self, text):
        if text.strip():
            self.slot(text.strip())

    def flush(self):
        pass  # Notwendig für die Kompatibilität


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
    # --- KLASSIKER & STANDARDS ---
    "Classics": {
        "bg": "#3a6ea5",
        "fg": "#FFFFFF",
        "hover": "#4a7eb5",
        "active": "#2a5e95",
        "window_bg": "#000000",
    },
    "Standard": {
        "bg": "#444444",
        "fg": "#FFFFFF",
        "hover": "#555555",
        "active": "#333333",
        "window_bg": "#000000",
    },
    "Silver": {
        "bg": "#B0B0B0",
        "fg": "#000000",
        "hover": "#C0C0C0",
        "active": "#A0A0A0",
        "window_bg": "#000000",
    },
    # --- DARK MODES ---
    "Midnight": {
        "bg": "#1A1A1A",
        "fg": "#F7F7F7",
        "hover": "#333333",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Anthrazit": {
        "bg": "#2F2F2F",
        "fg": "#FFFFFF",
        "hover": "#3D3D3D",
        "active": "#242424",
        "window_bg": "#000000",
    },
    "DeepBlack": {
        "bg": "#1A1A1A",
        "fg": "#FFD700",
        "hover": "#333333",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Steel": {
        "bg": "#455A64",
        "fg": "#FFFFFF",
        "hover": "#546E7A",
        "active": "#37474F",
        "window_bg": "#000000",
    },
    # --- BLAUTÖNE ---
    "RoyalBlue": {
        "bg": "#002366",
        "fg": "#FFFFFF",
        "hover": "#003399",
        "active": "#001a4d",
        "window_bg": "#000000",
    },
    "SkyBlue": {
        "bg": "#0288D1",
        "fg": "#FFFFFF",
        "hover": "#039BE5",
        "active": "#01579B",
        "window_bg": "#000000",
    },
    "Ocean": {
        "bg": "#006064",
        "fg": "#FFFFFF",
        "hover": "#00838F",
        "active": "#004D40",
        "window_bg": "#000000",
    },
    # --- NATUR & ERDE ---
    "Emerald": {
        "bg": "#2E7D32",
        "fg": "#FFFFFF",
        "hover": "#388E3C",
        "active": "#1B5E20",
        "window_bg": "#000000",
    },
    "Forest": {
        "bg": "#1B5E20",
        "fg": "#E8F5E9",
        "hover": "#2E7D32",
        "active": "#0D5302",
        "window_bg": "#000000",
    },
    "Coffee": {
        "bg": "#4E342E",
        "fg": "#D7CCC8",
        "hover": "#5D4037",
        "active": "#3E2723",
        "window_bg": "#000000",
    },
    "Olive": {
        "bg": "#556B2F",
        "fg": "#FFFFFF",
        "hover": "#6B8E23",
        "active": "#3E4E21",
        "window_bg": "#000000",
    },
    # --- WARME TÖNE ---
    "Ruby": {
        "bg": "#C62828",
        "fg": "#FFFFFF",
        "hover": "#D32F2F",
        "active": "#B71C1C",
        "window_bg": "#000000",
    },
    "Bordeaux": {
        "bg": "#800000",
        "fg": "#FFFFFF",
        "hover": "#A52A2A",
        "active": "#5D0000",
        "window_bg": "#000000",
    },
    "Orange": {
        "bg": "#EF6C00",
        "fg": "#FFFFFF",
        "hover": "#F57C00",
        "active": "#E65100",
        "window_bg": "#000000",
    },
    "Gold": {
        "bg": "#FFD700",
        "fg": "#000000",
        "hover": "#FFEA70",
        "active": "#DAA520",
        "window_bg": "#000000",
    },
    # --- LUXUS & SPEZIAL ---
    "Purple": {
        "bg": "#6A1B9A",
        "fg": "#FFFFFF",
        "hover": "#7B1FA2",
        "active": "#4A148C",
        "window_bg": "#000000",
    },
    "Neon": {
        "bg": "#000000",
        "fg": "#00FF00",
        "hover": "#003300",
        "active": "#000000",
        "window_bg": "#000000",
    },
    # --- MEGA HAMMER STYLES ---
    "Inferno": {
        "bg": "#212121",
        "fg": "#FF4500",
        "hover": "#FF8C00",
        "active": "#8B0000",
        "window_bg": "#000000",
    },
    "Electric": {
        "bg": "#0000FF",
        "fg": "#FFFF00",
        "hover": "#00FFFF",
        "active": "#00008B",
        "window_bg": "#000000",
    },
    "Lava": {
        "bg": "#4E0000",
        "fg": "#FF3300",
        "hover": "#FF6600",
        "active": "#220000",
        "window_bg": "#000000",
    },
    "Acid": {
        "bg": "#1D1D1D",
        "fg": "#DFFF00",
        "hover": "#BFFF00",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Ultraviolet": {
        "bg": "#120021",
        "fg": "#BF00FF",
        "hover": "#FF00FF",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Iceberg": {
        "bg": "#E1F5FE",
        "fg": "#01579B",
        "hover": "#FFFFFF",
        "active": "#B3E5FC",
        "window_bg": "#000000",
    },
    "Hazard": {
        "bg": "#000000",
        "fg": "#FFFF00",
        "hover": "#444400",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Alien": {
        "bg": "#00FF41",
        "fg": "#000000",
        "hover": "#008F11",
        "active": "#003B00",
        "window_bg": "#000000",
    },
    "HotPink": {
        "bg": "#FF69B4",
        "fg": "#FFFFFF",
        "hover": "#FF1493",
        "active": "#C71585",
        "window_bg": "#000000",
    },
    "DeepSea": {
        "bg": "#001219",
        "fg": "#94D2BD",
        "hover": "#0A9396",
        "active": "#005F73",
        "window_bg": "#000000",
    },
    "Magma": {
        "bg": "#000000",
        "fg": "#FF0000",
        "hover": "#660000",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Turquoise": {
        "bg": "#00CED1",
        "fg": "#FFFFFF",
        "hover": "#40E0D0",
        "active": "#008B8B",
        "window_bg": "#000000",
    },
    "Carbon": {
        "bg": "#232323",
        "fg": "#E0E0E0",
        "hover": "#111111",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Candy": {
        "bg": "#FF80AB",
        "fg": "#FCE4EC",
        "hover": "#F06292",
        "active": "#C2185B",
        "window_bg": "#000000",
    },
    "Plasma": {
        "bg": "#000000",
        "fg": "#7F00FF",
        "hover": "#3F007F",
        "active": "#000000",
        "window_bg": "#000000",
    },
    # --- TOP 50 COMPLETE (ULTRA) ---
    "Cyberpunk": {
        "bg": "#000000",
        "fg": "#00FFFF",
        "hover": "#F305FF",
        "active": "#FF0055",
        "window_bg": "#000000",
    },
    "Nuclear": {
        "bg": "#1A1A1A",
        "fg": "#CCFF00",
        "hover": "#333333",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Phoenix": {
        "bg": "#000000",
        "fg": "#FF4E00",
        "hover": "#FFD700",
        "active": "#8B0000",
        "window_bg": "#000000",
    },
    "Vaporwave": {
        "bg": "#2D004B",
        "fg": "#FF71CE",
        "hover": "#01CDFE",
        "active": "#05FFA1",
        "window_bg": "#000000",
    },
    "Matrix_Pro": {
        "bg": "#000000",
        "fg": "#00FF41",
        "hover": "#003B00",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "BloodMoon": {
        "bg": "#330000",
        "fg": "#FF0000",
        "hover": "#660000",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Arctic": {
        "bg": "#000000",
        "fg": "#00D2FF",
        "hover": "#0081FF",
        "active": "#00458B",
        "window_bg": "#000000",
    },
    "Toxic_Glow": {
        "bg": "#0D0D0D",
        "fg": "#ADFF2F",
        "hover": "#32CD32",
        "active": "#006400",
        "window_bg": "#000000",
    },
    "Obsidian": {
        "bg": "#1B1B1B",
        "fg": "#E0E0E0",
        "hover": "#444444",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Crimson": {
        "bg": "#000000",
        "fg": "#DC143C",
        "hover": "#800000",
        "active": "#000000",
        "window_bg": "#000000",
    },
    "Galaxy": {
        "bg": "#0D001A",
        "fg": "#9D50BB",
        "hover": "#6E48AA",
        "active": "#300055",
        "window_bg": "#000000",
    },
    "Titan": {
        "bg": "#263238",
        "fg": "#CFD8DC",
        "hover": "#546E7A",
        "active": "#102027",
        "window_bg": "#000000",
    },
    "Bumblebee": {
        "bg": "#FFCC00",
        "fg": "#000000",
        "hover": "#000000",
        "active": "#333300",
        "window_bg": "#000000",
    },
    "Frost": {
        "bg": "#000000",
        "fg": "#A5F2F3",
        "hover": "#2196F3",
        "active": "#0D47A1",
        "window_bg": "#000000",
    },
    "Volcano": {
        "bg": "#000000",
        "fg": "#FF3D00",
        "hover": "#DD2C00",
        "active": "#3E0000",
        "window_bg": "#000000",
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
        # Patch modifier
        "mod_dialog_title": "Change Modifier",
        "mod_dialog_label": "Patch Author Name:",
        "mod_changed_success": "✅ Modifier changed to: {name}",
        # Patch anwenden
        "executing_cmd": "Executing command:",
        "cmd_failed": "Command failed with exit code:",
        "executing_git_apply": "🚀 Applying patch: {patch}",
        "executing_git_check": "🔍 Checking patch compatibility: {patch}",
        # --- Patch Status ---
        "patch_file_missing": "❌ Patch file missing: {path}",
        "patch_emu_git_done": "✅ Patch applied successfully!",
        "patch_emu_git_apply_failed": "❌ Failed to apply patch!",
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
        "modifier_button_text": "👤 Patch Autor",
        "update_error": "Error checking for updates: {error}",
        "update_declined": "Update declined.",
        "update_current_version": "✅ Installed version: {version}",
        "restart_required_title": "Restart Required",
        "restart_required_msg": "The tool needs to be restarted. Restart now?",
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
        "edit_patch_header": "Edit Patch Header",
        "patch_emu_git_revision": "\U0001f4dd Git-Revision: {sha}",
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
        "oscam_emu_patch_upload": "OSCam EMU Patch hochladen",
        # Labels
        "mod_dialog_title": "Modifier ändern",
        "mod_dialog_label": "Name des Patch-Erstellers:",
        "mod_changed_success": "✅ Modifier geändert zu: {name}",
        # "language_label": "Sprache:",
        "language_label": "Sprache auswählen:",
        "color_label": "Farbe auswählen",
        "commit_count_label": "Anzahl der Commits",
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


def save_config(cfg):
    """
    Speichert die übergebene Config in CONFIG_FILE.
    """
    try:
        config_dir = os.path.dirname(CONFIG_FILE)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            # indent=4 macht die JSON Datei für Menschen lesbarer
            json.dump(cfg, f, indent=4, ensure_ascii=False)

        print(
            f"✅ Config erfolgreich gespeichert: {cfg.get('patch_modifier', 'default')}"
        )

    except Exception as e:
        print(f"❌ Fehler beim Speichern der Config: {e}")


# ===================== CONFIG =====================
def load_config():
    """
    Lädt die Konfigurationsdatei und gibt ein Dictionary zurück.
    Fehlende Keys werden mit Standardwerten ergänzt.
    """
    import os, json

    # 🔹 Standardwerte
    default_cfg = {
        "commit_count": 5,
        "color": "Classics",  # Standardfarbe
        "language": "DE",  # Standardsprache
        "s3_patch_path": OLD_PATCH_DIR,
    }

    # 🔹 Wenn Config-Datei nicht existiert → Standard zurückgeben
    if not os.path.exists(CONFIG_FILE):
        return default_cfg.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # 🔹 Falls kaputte Datei → Standard zurückgeben
        if not isinstance(cfg, dict):
            return default_cfg.copy()

        # 🔹 Fehlende Keys ergänzen
        for key, value in default_cfg.items():
            cfg.setdefault(key, value)

        return cfg

    except Exception as e:
        # Fehler beim Laden, Standard zurückgeben
        print(f"⚠️ Config konnte nicht geladen werden: {e}")
        return default_cfg.copy()


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
    Erstellt den Patch im TEMP_REPO mit dem exakten 3-Zeilen-Header:
    1. patch version
    2. patch date
    3. patch modified by
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtGui import QTextCursor
    import subprocess, os, shutil

    # 1. Widget & Sprache & Modifier sicherstellen
    widget = info_widget
    if not isinstance(widget, QTextEdit) and gui_instance:
        widget = getattr(gui_instance, "info_text", None)

    lang = str(getattr(gui_instance, "LANG", "de")).lower()[:2]
    # Dynamischer Name vom Button (errich, speedy005, etc.)
    active_modifier = getattr(gui_instance, "patch_modifier", PATCH_MODIFIER)

    # EMUREPO dynamisch von der GUI Instanz oder Global beziehen
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

    def set_progress(val):
        if progress_callback:
            try:
                progress_callback(val)
                QApplication.processEvents()
            except:
                pass

    # --- START ---
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
            # Nutzt STREAMREPO für das Grundgerüst
            subprocess.run(
                f"git clone {STREAMREPO} .",
                shell=True,
                cwd=TEMP_REPO,
                capture_output=True,
            )

        # Remote für Emu hinzufügen/aktualisieren (Nutzt die EMUREPO Variable)
        subprocess.run(
            ["git", "remote", "remove", "emu-repo"], cwd=TEMP_REPO, capture_output=True
        )
        subprocess.run(
            ["git", "remote", "add", "emu-repo", active_emu_repo],
            cwd=TEMP_REPO,
            capture_output=True,
        )

        set_progress(40)
        # Repository auf aktuellen Stand bringen
        for cmd in [
            "git fetch --all",
            "git checkout -B master origin/master",
            "git reset --hard origin/master",
        ]:
            subprocess.run(cmd, shell=True, cwd=TEMP_REPO, capture_output=True)

        set_progress(70)

        # 3. HEADER GENERIEREN
        header = get_patch_header(
            repo_dir=TEMP_REPO, lang=lang, modifier=active_modifier
        )

        # 4. DIFF GENERIEREN
        diff = subprocess.check_output(
            ["git", "diff", "origin/master..emu-repo/master", "--", ".", ":!.github"],
            cwd=TEMP_REPO,
            text=True,
        )

        if not diff.strip():
            log("patch_create_no_changes", "warning")
            diff = "# No changes detected"

        # 5. DATEI SCHREIBEN
        with open(PATCH_FILE, "w", encoding="utf-8") as f:
            f.write(header + "\n" + diff + "\n")

        set_progress(90)

        # --- ERFOLGSMELDUNGEN ---
        log("patch_create_success", "success", patch_file=PATCH_FILE)

        if header.strip():
            header_lines = header.splitlines()
            if header_lines:
                first_line = header_lines[0].strip()
                log("patch_version_from_header", "success", patch_version=first_line)

    except Exception as e:
        # Hier wird der Fehler abgefangen und rot ausgegeben
        log("patch_create_failed", "error", error=str(e))
        set_progress(0)
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
    Löscht temporäre Repos und Dateien (TEMP_REPO, TEMP_PATCH_GIT, PATCH_FILE, ZIP_FILE).
    Einmaliges Logging, Windows-Fix inklusive.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import os, shutil, stat

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

    # Ziele dynamisch sammeln (verhindert NameError)
    targets = []
    for var_name in ["TEMP_REPO", "TEMP_PATCH_GIT", "PATCH_EMU_GIT_DIR"]:
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
        return

    # Abarbeiten der Liste
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

        # Fortschrittsberechnung
        set_progress(10 + (i + 1) * (90 // len(targets)))

    # ---------- 4) ABSCHLUSS ----------
    set_progress(100)
    log("cleanup_success", "success")
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
    """Löscht den Emu-Git Ordner absolut stumm ohne eigene Log-Einträge."""
    import os, shutil, stat

    path = globals().get("PATCH_EMU_GIT_DIR") or globals().get("TEMP_PATCH_GIT")

    if progress_callback:
        progress_callback(30)

    if path and os.path.exists(path):
        try:

            def on_error(func, p, exc):
                os.chmod(p, stat.S_IWRITE)
                func(p)

            shutil.rmtree(path, onerror=on_error)
            if progress_callback:
                progress_callback(100)
            return "success"
        except:
            return "error"

    if progress_callback:
        progress_callback(100)
    return "not_found"


# ===================== patch_oscam_emu_git=====================
def patch_oscam_emu_git(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Klont das Streamboard Git, wendet oscam-emu.patch an und commitet.
    Optimiert für Windows 11: Keine Terminal-Ausgaben, SSL-Fix inklusive.
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    from PyQt6.QtCore import QTimer
    import os, shutil, subprocess

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
        QApplication.processEvents()

    # --- Start ---
    set_progress(5)
    log("patch_emu_git_start", "info", path=PATCH_EMU_GIT_DIR)

    # Ordner bereinigen (mit Retry für Windows-Dateisperren)
    if os.path.exists(PATCH_EMU_GIT_DIR):
        try:
            shutil.rmtree(PATCH_EMU_GIT_DIR, ignore_errors=True)
            log("patch_emu_git_deleted", "success", path=PATCH_EMU_GIT_DIR)
        except Exception:
            log("delete_failed", "error", path=PATCH_EMU_GIT_DIR)

    os.makedirs(PATCH_EMU_GIT_DIR, exist_ok=True)
    set_progress(15)

    # --- Git Clone (Informativ & Silent) ---
    set_progress(20)
    # -c http.sslVerify=false behebt Klon-Fehler auf vielen Windows-Systemen
    clone = subprocess.run(
        ["git", "clone", "-c", "http.sslVerify=false", STREAMREPO, "."],
        cwd=PATCH_EMU_GIT_DIR,
        capture_output=True,
        text=True,
    )

    if clone.returncode != 0:
        log("patch_emu_git_clone_failed", "error")
        # Fehlermeldung nur in die GUI schreiben
        if isinstance(widget, QTextEdit):
            widget.append(
                f'<span style="color:red">Git Error: {clone.stderr.strip()}</span>'
            )
        return

    # --- Patch anwenden ---
    set_progress(50)
    if not os.path.exists(PATCH_FILE):
        log("patch_file_missing", "error")
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
        if isinstance(widget, QTextEdit):
            widget.append(
                f'<span style="color:red">Patch Error: {apply_patch.stderr.strip()}</span>'
            )
        return

    # --- Git Config ---
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

    # --- Header Context Fix (Keine Terminal fatal Meldungen) ---
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

    # --- Commit ---
    subprocess.run(["git", "add", "."], cwd=PATCH_EMU_GIT_DIR, capture_output=True)
    subprocess.run(
        ["git", "commit", "-am", commit_msg, "--allow-empty"],
        cwd=PATCH_EMU_GIT_DIR,
        capture_output=True,
    )
    log("patch_emu_git_applied", "success", commit_msg=commit_msg)

    # --- Revision auslesen (Silent) ---
    rev = None
    try:
        rev_res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PATCH_EMU_GIT_DIR,
            capture_output=True,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        if rev_res.returncode == 0:
            rev = rev_res.stdout.strip()
    except:
        pass

    # --- Finale Meldungen ---
    def final_logs():
        if gui_instance:
            log("patch_emu_git_done", "success")
            if rev:
                rev_text = (
                    TEXTS[lang]
                    .get("patch_emu_git_revision", "Git revision: {sha}")
                    .format(sha=rev)
                )
                gui_instance.append_info(widget, rev_text, "success")

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
    """
    from PyQt6.QtWidgets import QTextEdit, QApplication
    import os, subprocess, shutil

    # 1. Sicherstellen, dass wir Instanzen haben
    gui = gui_instance if gui_instance else self
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

    def log(text_key, level="info", **kwargs):
        # Greift auf das globale TEXTS dictionary zu
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
        else:
            print(f"[{level.upper()}] {text}")
        QApplication.processEvents()

    # --- Start der Logik ---
    set_progress(5)
    log("github_config_load", "info")

    # Sicherer Aufruf der Ladefunktion (muss global oder in self existieren)
    load_func = globals().get("load_github_config") or getattr(
        self, "load_github_config", None
    )
    if not load_func:
        log("Konfigurations-Ladefunktion fehlt!", "error")
        return

    cfg = load_func()
    repo_url = cfg.get("emu_repo_url")
    branch = cfg.get("emu_branch", "master")
    username, token = cfg.get("username"), cfg.get("token")
    user_name, user_email = cfg.get("user_name"), cfg.get("user_email")

    # Check ob Config vollständig
    if not all([repo_url, branch, username, token, user_name, user_email]):
        log("github_emu_git_missing", "error")
        return

    # Globaler Pfad-Check
    target_dir = globals().get("PATCH_EMU_GIT_DIR")
    if not target_dir or not os.path.exists(target_dir):
        log("patch_emu_git_missing", "error", path=str(target_dir))
        return

    set_progress(15)
    token_url = repo_url.replace("https://", f"https://{username}:{token}@")
    git_dir = os.path.join(target_dir, ".git")
    silent_env = os.environ.copy()
    silent_env["GIT_TERMINAL_PROMPT"] = "0"

    # --- Git Operationen ---
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

        # Commit Message
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
        else:
            log("github_upload_failed", "error")
            err = (
                push.stderr.replace(token, "***")
                if push.stderr
                else "Unknown Git Error"
            )
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
        QTimer.singleShot(1000, self.manual_tool_check)

        # Update-Check nach 2 Sekunden
        if hasattr(self, "check_for_update_on_start"):
            QTimer.singleShot(2000, self.check_for_update_on_start)

    def change_colors(self):
        global current_diff_colors, current_color_name

        # 1️⃣ Aktuelle Farbe ermitteln
        if hasattr(self, "color_box") and self.color_box.currentText():
            current_color_name = self.color_box.currentText()
        else:
            current_color_name = self.cfg.get("color", "Classics")

        # 2️⃣ Basis-Farben holen (Fallback auf "Classics" statt leeren String)
        base_colors = DIFF_COLORS.get(current_color_name, DIFF_COLORS.get("Classics"))
        bg = base_colors.get("bg", "#FFFFFF")

        # 3️⃣ Farben für UI vorbereiten
        current_diff_colors = {
            **base_colors,
            "hover": base_colors.get("hover", self.adjust_color(bg, 1.15)),
            "active": base_colors.get("active", self.adjust_color(bg, 0.85)),
        }

        # 4️⃣ Farben im UI anwenden
        if hasattr(self, "repaint_ui_colors") and callable(self.repaint_ui_colors):
            self.repaint_ui_colors()

        # 5️⃣ Speichern NUR, wenn wir NICHT im Lademodus sind
        # Wichtig: Variable muss mit der in __init__ übereinstimmen (is_loading)
        if not getattr(self, "is_loading", False):
            if self.cfg.get("color") != current_color_name:
                self.cfg["color"] = current_color_name
                try:
                    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                        json.dump(self.cfg, f, indent=4)
                except Exception as e:
                    print(f"Fehler beim Speichern: {e}")

    def log_message(self, message):
        """Zentrale Funktion für alle Log-Ausgaben."""
        now = datetime.now().strftime("%H:%M:%S")
        # Nutze das korrekte Attribut self.info_text aus __init__
        self.info_text.append(f"<b>[{now}]</b> {message}")
        self.info_text.moveCursor(QTextCursor.MoveOperation.End)

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
        close_btn.setFixedHeight(35)
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

    def change_emu_repo(self):
        from PyQt6.QtWidgets import QInputDialog, QLineEdit
        import json
        import os

        # Aktuellen Wert holen
        current_repo = getattr(self, "EMUREPO", "https://github.com")

        title = "Repo URL" if getattr(self, "LANG", "de") == "en" else "Repo URL ändern"
        label = (
            "Neue Emu-Repository URL:"
            if getattr(self, "LANG", "de") == "de"
            else "New Emu-Repository URL:"
        )

        new_url, ok = QInputDialog.getText(
            self, title, label, QLineEdit.EchoMode.Normal, current_repo
        )

        if ok and new_url:
            self.EMUREPO = new_url.strip()

            # --- Speichern in der Config ---
            config_path = "config.json"  # Passe den Pfad an deine Struktur an
            config_data = {}

            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    try:
                        config_data = json.load(f)
                    except:
                        pass

            config_data["EMUREPO"] = self.EMUREPO

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)

            self.info_text.append(f"💾 Repo gespeichert: {self.EMUREPO}")

    def change_modifier_name(self):
        """Öffnet Dialog, speichert den Namen permanent und aktualisiert das UI."""
        from PyQt6.QtWidgets import QInputDialog, QLineEdit

        # Aktuellen Namen abrufen
        current = getattr(self, "patch_modifier", PATCH_MODIFIER)
        lang = getattr(self, "LANG", "de")

        # Texte aus TEXTS laden
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))
        
        # Titel und Label auf "Patch Autor" angepasst
        title = lang_dict.get("mod_dialog_title", "Patch Autor")
        label = lang_dict.get("mod_dialog_label", "Neuer Name des Autors:")

        new_name, ok = QInputDialog.getText(
            self, title, label, QLineEdit.EchoMode.Normal, current
        )

        if ok and new_name.strip():
            # 1. Instanz-Variable aktualisieren
            self.patch_modifier = new_name.strip()

            # 2. In das Config-Dictionary schreiben (falls vorhanden)
            if hasattr(self, "cfg"):
                self.cfg["patch_modifier"] = self.patch_modifier
                # 3. Die externe save_config Funktion aufrufen
                try:
                    save_config(self.cfg)
                except Exception as e:
                    self.append_info(self.info_text, f"❌ Config Save Error: {e}", "error")

            # 4. LIVE-UPDATE: Button-Text sofort aktualisieren
            if hasattr(self, "btn_modifier"):
                self.btn_modifier.setText(f"👤 {self.patch_modifier}")

            # 5. Feedback im Log ausgeben
            success_tpl = lang_dict.get("mod_changed_success", "✅ Patch Autor geändert: {name}")
            self.append_info(
                self.info_text, 
                success_tpl.format(name=self.patch_modifier), 
                "success"
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
        """Prüft installierte Tools und nutzt strikt die gewählte Sprache."""
        import shutil
        import subprocess

        # 1. Sprache & Texte laden
        lang = str(getattr(self, "LANG", "de")).lower()
        t = TEXTS.get(lang, TEXTS.get("en", {}))

        # 2. Start-Meldung (Nur im Infoscreen)
        self.append_info(
            self.info_text,
            t.get("checking_tools", "Starting system tool check..."),
            "info",
        )

        # 3. System-Tools prüfen
        required_tools = ["git", "patch", "zip", "python3"]
        missing = [tool for tool in required_tools if shutil.which(tool) is None]

        if not missing:
            # 4. Erfolgs-Meldung (Alles ok -> kein Terminal!)
            msg = t.get(
                "tools_ok", "✅ All required system tools are already installed."
            )
            self.append_info(self.info_text, msg, "success")
            return

        # 5. Falls Tools fehlen -> Information im Infoscreen
        missing_str = " ".join(missing)
        template = t.get(
            "tools_missing", "⚠️ Missing tools: {tools}. Starting installation..."
        )
        self.append_info(self.info_text, template.format(tools=missing_str), "warning")

        # Installations-Befehl vorbereiten
        install_cmd = f"sudo apt-get update && sudo apt-get install -y {missing_str}"
        full_cmd = (
            f"bash -c '{install_cmd}; echo; echo Done. Press Enter to close...; read'"
        )

        term = (
            shutil.which("x-terminal-emulator")
            or shutil.which("xterm")
            or "gnome-terminal"
        )

        # 6. Terminal NUR für die Installation starten
        if term:
            try:
                # Wir leiten stdout/stderr von Popen selbst nach DEVNULL,
                # damit keine GTK/System-Warnungen im Hauptterminal erscheinen.
                if "gnome" in term:
                    subprocess.Popen(
                        [term, "--", "bash", "-c", full_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    subprocess.Popen(
                        [term, "-e", full_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            except Exception as e:
                err_msg = (
                    f"Terminal Error: {e}" if lang == "en" else f"Terminal-Fehler: {e}"
                )
                self.append_info(self.info_text, err_msg, "error")
        else:
            # Fallback falls gar kein Terminal gefunden wurde
            self.append_info(self.info_text, "❌ No terminal emulator found!", "error")

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
        Verhindert doppelte Meldungen.
        """
        from PyQt6.QtWidgets import QTextEdit
        from PyQt6.QtGui import QTextCursor  # Wichtig für automatisches Scrollen

        # 1. Widget-Validierung
        if not isinstance(info_widget, QTextEdit):
            if hasattr(self, "info_text") and isinstance(self.info_text, QTextEdit):
                info_widget = self.info_text
            else:
                return  # Kein gültiges Widget vorhanden

        # 2. Prüfen, ob Text schon existiert
        if text in info_widget.toPlainText():
            return  # Nachricht bereits vorhanden, nichts tun

        # 3. Farben & Formatierung
        colors = {
            "success": "green",
            "warning": "orange",
            "error": "red",
            "info": "gray",
        }
        color = colors.get(level, "black")
        html_text = f'<span style="color:{color}">{text}</span>'

        # 4. GUI-Ausgabe
        info_widget.append(html_text)

        # 5. Automatisches Scrollen
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
        Startet das Tool neu via Button-Klick und speichert vorher die Config.
        Plattformübergreifend für Windows und Linux optimiert.
        """
        from PyQt6.QtWidgets import QMessageBox, QTextEdit, QApplication
        import sys
        import os
        import subprocess

        # 1. Widget & Sprache sicherstellen
        widget = info_widget or getattr(self, "info_text", None)
        # Wir nehmen die aktuell gesetzte Sprache der Instanz
        lang_key = str(getattr(self, "LANG", "de")).lower()

        try:
            lang_pack = TEXTS.get(lang_key, TEXTS.get("en", {}))
        except NameError:
            lang_pack = {}

        # 2. Dialog aufbauen
        msg = QMessageBox(self)
        msg.setWindowTitle(lang_pack.get("restart_tool", "Restart tool"))
        msg.setText(
            lang_pack.get("restart_tool_question", "Do you want to restart now?")
        )

        yes_text = lang_pack.get("yes", "Yes")
        no_text = lang_pack.get("no", "No")
        yes_button = msg.addButton(yes_text, QMessageBox.ButtonRole.YesRole)
        no_button = msg.addButton(no_text, QMessageBox.ButtonRole.NoRole)

        msg.exec()

        if msg.clickedButton() == yes_button:
            # --- SPEICHERN DER AKTUELLEN EINSTELLUNGEN ---
            try:
                # Nutze deine zentrale Sammel-Methode, um konsistente Keys zu haben
                if hasattr(self, "get_gui_settings"):
                    current_config = self.get_gui_settings()
                else:
                    # Fallback: Manuelles Sammeln mit den Namen aus deiner __init__
                    current_config = {
                        "commit_count": getattr(self, "commit_count", 5),
                        "color": getattr(self, "current_color", "s"),
                        "language": lang_key.upper(),
                        "s3_patch_path": getattr(self, "OLD_PATCH_DIR", OLD_PATCH_DIR),
                    }

                # Datei physisch schreiben mit deiner globalen Funktion
                if "save_config" in globals():
                    save_config(current_config)
                    print(f"✅ Config vor Neustart gesichert: {current_config}")
                else:
                    # Falls save_config nicht global ist, direkt schreiben
                    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                        json.dump(current_config, f, indent=2, ensure_ascii=False)

            except Exception as e:
                print(f"⚠️ Fehler beim Speichern vor Neustart: {e}")

            # Info im GUI-Log ausgeben
            info_msg = lang_pack.get("restart_tool_info", "Restarting...")
            if isinstance(widget, QTextEdit):
                widget.append(f'<br><span style="color:gray">{info_msg}</span>')

            # 3. Plattformübergreifende Neustart-Logik
            try:
                executable = sys.executable
                args = sys.argv[:]

                if os.name != "nt":
                    # Linux/Unix: Prozess ersetzen (sauberster Weg)
                    os.execl(executable, executable, *args)
                else:
                    # Windows: Neuen Prozess starten und aktuellen beenden
                    subprocess.Popen([executable] + args)
                    QApplication.instance().quit()
            except Exception as e:
                print(f"Kritischer Fehler beim Neustart: {e}")
                # Letzter Rettungsanker
                os.system(f"{sys.executable} {' '.join(sys.argv)}")
                QApplication.instance().quit()
        else:
            # Falls "Nein" geklickt wurde, Balken auf 100% setzen
            if progress_callback:
                progress_callback(100)

    def restart_application(self, *args, **kwargs):
        import subprocess
        import sys
        import os
        from PyQt6.QtWidgets import QApplication

        # --- SPEICHER-FIX VOR NEUSTART ---
        try:
            # Falls die globale Variable existiert, in das Dictionary schreiben
            if "current_color_name" in globals():
                self.cfg["color"] = globals()["current_color_name"]

            # Sicherstellen, dass auch andere Werte aktuell sind
            self.cfg["language"] = getattr(self, "LANG", "DE").upper()

            # Jetzt die Datei physisch schreiben
            if "save_config" in globals():
                save_config(self.cfg)
                print(f"✅ Restart-Save: {self.cfg['color']} wurde gesichert.")
        except Exception as e:
            print(f"⚠️ Fehler beim Sichern vor Restart: {e}")
        # ---------------------------------

        python = sys.executable
        script = os.path.abspath(__file__)
        args_list = sys.argv

        subprocess.Popen([python, script] + args_list[1:])
        QApplication.quit()

    # ===================== ZIP PATCH =====================
    def zip_patch(self, info_widget=None, progress_callback=None):
        """Erstellt ein ZIP des Patches und zeigt den Status im Infoscreen an."""
        from PyQt6.QtWidgets import QTextEdit
        import zipfile

        # SICHERHEITS-CHECK: Widget erzwingen
        widget = info_widget
        if not isinstance(widget, QTextEdit):
            widget = getattr(self, "info_text", None)

        # Sprache sicherstellen
        lang = getattr(self, "LANG", "DE")

        # Hilfsfunktion für die Texte (vermeidet Abstürze bei fehlenden Keys)
        def get_msg(key, default, **kwargs):
            template = TEXTS.get(lang, {}).get(key, default)
            try:
                return template.format(**kwargs)
            except:
                return template

        try:
            # 1. Existenzprüfung
            if not os.path.exists(PATCH_FILE):
                msg = get_msg(
                    "patch_file_missing",
                    "Datei nicht gefunden: {path}",
                    path=PATCH_FILE,
                )
                self.append_info(widget, msg, "error")
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

        except Exception as e:
            msg = get_msg("zip_failed", "❌ Fehler beim Zippen: {error}", error=str(e))
            self.append_info(widget, msg, "error")

        if progress_callback:
            progress_callback(100)

    def run_command(self, cmd, cwd=None):
        """Führt Befehle aus und gibt das Ergebnis als String zurück."""
        try:
            # Falls cmd ein String ist (wie in deinem git log), machen wir eine Liste daraus
            # oder nutzen shell=True. Für git log ist shell=True oft einfacher.
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                shell=True,  # Erlaubt die Übergabe als ganzer String
                check=False,
            )

            if result.returncode != 0:
                if result.stderr:
                    print(f"❌ Fehler: {result.stderr.strip()}")
                return ""  # Leerer String bei Fehler

            return result.stdout.strip()  # Gibt nur den Text zurück
        except Exception as e:
            print(f"❌ Systemfehler: {str(e)}")
            return ""

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

    # Callback nach Schließengg
    def edit_patch_header(self, info_widget=None, progress_callback=None):
        """
        Opens the patch file in a dialog to edit its header.
        Messages are written to the info widget or printed to the console.
        """
        widget = info_widget or getattr(self, "info_text", None)

        # Logger like in clean_patch_folder
        def log(text, level="info"):
            if hasattr(self, "append_info") and widget:
                self.append_info(widget, text, level)
            else:
                print(f"[{level.upper()}] {text}")

        # Get language texts
        lang_dict = TEXTS.get(getattr(self, "LANG", "en"), TEXTS.get("en", {}))

        # Load patch file
        patch_content = ""
        try:
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

        # Create dialog
        editor = QDialog(self)
        editor.setWindowTitle(
            lang_dict.get("edit_patch_header_title", "Edit Patch Header")
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

        # Set button texts with translation fallback
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save_btn.setText(lang_dict.get("save", "Save"))
        cancel_btn.setText(lang_dict.get("cancel", "Cancel"))

        # Button events
        def save_and_close():
            try:
                with open(PATCH_FILE, "w", encoding="utf-8") as f:
                    f.write(text_edit.toPlainText())
                success_msg = lang_dict.get(
                    "patch_saved_successfully", "✅ Patch file saved successfully"
                )
                log(success_msg, "success")
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
        Button-Callback: Prüft GitHub-Version und bietet Update NUR bei neuerer Version an.
        """
        from PyQt6.QtWidgets import QTextEdit, QApplication, QMessageBox
        from PyQt6.QtGui import QTextCursor
        import requests, time
        from packaging.version import Version

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
            text_template = TEXTS.get(lang_key, TEXTS.get("en", {})).get(
                text_key, text_key
            )
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
        if progress:
            progress(10)

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

            if progress:
                progress(50)

            # 1. Prüfen ob Update nötig
            if not Version(latest_version) > Version(current_version):
                msg = (
                    TEXTS.get(lang_key, TEXTS["en"])
                    .get("up_to_date", "Plugin ist aktuell (v{v})")
                    .format(v=current_version)
                )
                QMessageBox.information(self, "Update", msg)
                log("update_no_update", "success")
                if progress:
                    progress(100)
                return

            # 2. Wenn Update verfügbar
            if progress:
                progress(80)

            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle(
                TEXTS.get(lang_key, TEXTS["en"]).get(
                    "update_available_title", "Update verfügbar"
                )
            )

            raw_msg = TEXTS.get(lang_key, TEXTS["en"]).get(
                "update_available_msg",
                "Version {latest} verfügbar. Aktuell: {current}. Jetzt updaten?",
            )
            msg_box.setText(raw_msg.format(current=APP_VERSION, latest=latest_version))

            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            # Button-Texte übersetzen
            btn_yes = msg_box.button(QMessageBox.StandardButton.Yes)
            if btn_yes:
                btn_yes.setText(TEXTS.get(lang_key, {}).get("yes", "Ja"))
            btn_no = msg_box.button(QMessageBox.StandardButton.No)
            if btn_no:
                btn_no.setText(TEXTS.get(lang_key, {}).get("no", "Nein"))

            result = msg_box.exec()

            if result == QMessageBox.StandardButton.Yes:
                if hasattr(self, "plugin_update_action"):
                    self.plugin_update_action(
                        latest_version=latest_version, progress_callback=progress
                    )
            else:
                log("update_declined", "info")
                if progress:
                    progress(100)

        except Exception as e:
            log("update_fail", "error", error=str(e))
            if progress:
                progress(0)

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
            colors = {
                "success": "green",
                "warning": "orange",
                "error": "red",
                "info": "blue",
            }
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
                if progress:
                    progress.setValue(100)
                return

            # Update verfügbar
            if progress:
                progress.setValue(80)

            # MessageBox Setup
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle(
                TEXTS.get(lang, {}).get("update_available_title", "Update verfügbar")
            )

            raw_dialog_text = TEXTS.get(lang, {}).get(
                "update_available_msg",
                "Neue Version {latest} verfügbar. Jetzt updaten?",
            )
            msg_box.setText(
                raw_dialog_text.format(current=current_version, latest=latest_version)
            )

            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            # Button-Texte übersetzen
            btn_yes = msg_box.button(QMessageBox.StandardButton.Yes)
            if btn_yes:
                btn_yes.setText(TEXTS.get(lang, {}).get("yes", "Ja"))
            btn_no = msg_box.button(QMessageBox.StandardButton.No)
            if btn_no:
                btn_no.setText(TEXTS.get(lang, {}).get("no", "Nein"))

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
                if progress:
                    progress.setValue(100)

        except Exception as e:
            log("update_fail", "error", error=str(e))
            if progress:
                progress.setValue(0)

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
        self.info_text.clear()
        import shutil, os, json

        # ... (Config laden bleibt gleich) ...

        # KORREKTUR: Wir definieren, welche Tools wirklich EXTERN gebraucht werden.
        # 'zip' und 'patch' entfernen wir hier für Windows/Git-Bash.
        tools_to_check = ["git"]
        if os.name != "nt":  # Nur unter echtem Linux prüfen wir zip/patch
            tools_to_check.extend(["zip", "patch"])

        all_ok = True
        for name in tools_to_check:
            # shutil.which wirft keinen WinError 2, wenn die Datei fehlt!
            if shutil.which(name) is None:
                self.append_info(
                    self.info_text, f"⚠️ {name} fehlt im System.", "warning"
                )
                all_ok = False
            else:
                self.append_info(self.info_text, f"✅ {name} ist bereit.", "success")

        if all_ok:
            self.append_info(self.info_text, "✅ System-Check erfolgreich.", "success")
            cfg["tools_ok"] = True
            with open(CONFIG_FILE, "w") as f:
                json.dump(cfg, f, indent=2)
        else:
            # Hier den automatischen Installationsversuch löschen!
            self.append_info(
                self.info_text, "❌ Bitte fehlende Tools manuell installieren.", "error"
            )

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
        time_date_layout.setContentsMargins(0, 0, 0, 0)
        time_date_layout.setSpacing(2)
        time_date_layout.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

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
        right_header_layout.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )

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
        main_layout.addWidget(self.progress_bar)

        # ---------------------------------------------------------
        # KONTROLL-BLOCK MIT HEADER
        # ---------------------------------------------------------
        controls_group = QFrame()
        controls_group.setStyleSheet(
            """
        QFrame {
            border: 1px solid #bbb;
            border-radius: 10px;
            background-color: #2F2F2F;
        }
        """
        )
        # --- Layout für die Einstellungen-Gruppe ---
        controls_group_layout = QVBoxLayout(controls_group)
        controls_group_layout.setContentsMargins(10, 8, 10, 10)
        controls_group_layout.setSpacing(6)

        # 1. Label erstellen und an self binden (WICHTIG für Übersetzung!)
        translated_text = self.get_t("settings_header", "Einstellungen")
        self.controls_header = QLabel(translated_text)

        # 2. Dimensionen und Verhalten
        self.controls_header.setFixedHeight(28)

        # Sagt dem Label, es soll nur so breit wie der Text sein
        self.controls_header.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )

        # Textausrichtung innerhalb des blauen/farbigen Balkens
        self.controls_header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 3. Stylesheet (Hier nutzen wir bg_color und text_color aus deinem Theme)
        # Falls repaint_ui_colors noch nicht gelaufen ist, nutzen wir Fallbacks
        bg = current_diff_colors.get("bg", "#3a6ea5")
        fg = current_diff_colors.get("fg", "#FFFFFF")

        self.controls_header.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                font-size: 15px;
                font-weight: bold;
                padding-left: 15px;
                padding-right: 15px;
                border-radius: 6px;
            }}
        """
        )

        # 4. Linksbündig zum Layout hinzufügen (der Balken ist kurz, sitzt aber links)
        controls_group_layout.addWidget(
            self.controls_header, alignment=Qt.AlignmentFlag.AlignLeft
        )

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
            lbl.setAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            )
            return lbl

        self.lang_label = make_label(self.get_t("language_label", "Language:"))
        self.language_box = QComboBox()
        self.language_box.addItems(["EN", "DE"])  # Index 0=EN, 1=DE
        self.language_box.setFixedSize(80, CONTROL_HEIGHT)
        self.language_box.setStyleSheet(control_style)

        # Den Wert aus der Config laden
        saved_lang = self.cfg.get("language", "de").lower()

        # 4. Den passenden Index RICHTIG auswählen:
        if saved_lang == "en":
            self.language_box.setCurrentIndex(0)  # 0 ist EN
        else:
            self.language_box.setCurrentIndex(1)  # 1 ist DE

        # WICHTIG: Den Connect erst NACH setCurrentIndex machen,
        # damit beim Starten nicht sofort change_language ausgelöst wird!
        self.language_box.currentIndexChanged.connect(self.change_language)

        self.color_label = make_label(self.get_t("color_label", "Farbe:"))
        self.color_box = QComboBox()
        self.color_box.addItems(list(DIFF_COLORS.keys()))
        saved_color = self.cfg.get(
            "theme_color", "Classics"
        )  # oder "color", je nachdem was du jetzt nutzt
        index = self.color_box.findText(saved_color)
        if index >= 0:
            self.color_box.setCurrentIndex(index)
        else:
            # Falls er nichts findet, nimm den ersten Eintrag
            self.color_box.setCurrentIndex(0)
        self.color_box.setFixedSize(150, CONTROL_HEIGHT)
        self.color_box.setStyleSheet(control_style)
        self.color_box.currentIndexChanged.connect(self.change_colors)

        self.commit_label = make_label(self.get_t("commit_count_label", "Commits:"))
        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1, 20)
        self.commit_spin.setFixedSize(70, CONTROL_HEIGHT)
        saved_commits = self.cfg.get("commit_count", 10)
        self.commit_spin.setValue(saved_commits)
        self.commit_spin.setStyleSheet(control_style)
        self.commit_spin.valueChanged.connect(self.commit_value_changed)

        self.btn_check_tools = QPushButton(
            self.get_t("check_tools_button", "🛠️ Tools prüfen")
        )
        self.btn_check_tools.setFixedSize(160, CONTROL_HEIGHT)

        button_style = """
            QPushButton {
                background-color: #444444;
                color: white;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { 
                background-color: #333333; 
                color: #FFD700;
            }
        """
        self.btn_check_tools.setStyleSheet(button_style)
        self.btn_check_tools.clicked.connect(self.manual_tool_check)

        # --- 2. Modifier Button ---
        button_text = self.get_t("modifier_button_text", "👤 Patch Autor")
        
        # Erstellen
        self.btn_modifier = QPushButton(button_text)
        self.btn_modifier.setFixedSize(160, CONTROL_HEIGHT)
        self.btn_modifier.setStyleSheet(button_style)
        
        # Tooltip je nach Sprache
        lang = getattr(self, "LANG", "de")
        self.btn_modifier.setToolTip(
            "Namen des Patch-Autors ändern (Signatur)" if lang == "de" 
            else "Change Patch Author Name (Signature)"
        )
        
        # NUR EINMAL VERBINDEN (Damit nur ein Fenster öffnet!)
        self.btn_modifier.clicked.connect(self.change_modifier_name)

        # --- 3. Repo URL Button ---
        self.btn_repo_url = QPushButton("🌐 Repo URL")
        self.btn_repo_url.setFixedSize(160, CONTROL_HEIGHT)
        self.btn_repo_url.setStyleSheet(button_style)
        self.btn_repo_url.setToolTip(
            "Emu-Repository URL ändern" if lang == "de" else "Change Emu-Repository URL"
        )
        self.btn_repo_url.clicked.connect(self.change_emu_repo)

        # --- 4. Layout befüllen ---
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
        controls_layout.addSpacing(10)
        controls_layout.addWidget(self.btn_modifier)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(self.btn_repo_url)

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
        # Automatisch speichern bei Änderung
        self.color_box.currentTextChanged.connect(self.collect_and_save)
        self.commit_spin.valueChanged.connect(self.collect_and_save)

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
        """Aktualisiert ALLE GUI-Elemente basierend auf current_diff_colors."""
        global current_diff_colors

        # Farben und Schriftgröße zentral definieren
        text_color = current_diff_colors.get("fg", "#FFFFFF")
        bg_color = current_diff_colors["bg"]
        hover_color = current_diff_colors.get("hover", bg_color)
        active_color = current_diff_colors.get("active", bg_color)

        # 1. Gemeinsames Design für Labels, Boxen und Pfadanzeige
        common_style = f"""
            background-color: {bg_color}; 
            color: {text_color}; 
            border-radius: 4px;
            padding: 2px;
            font-weight: bold;
        """

        widgets_to_paint = [
            getattr(self, "lang_label", None),
            getattr(self, "color_label", None),
            getattr(self, "language_box", None),
            getattr(self, "color_box", None),
            getattr(self, "commit_label", None),
            getattr(self, "commit_spin", None),
            getattr(self, "label_patch_path", None),
        ]

        for w in widgets_to_paint:
            if w:
                w.setStyleSheet(common_style)

        # 2. MEGA BUTTON STYLE (Für ALLE Buttons im Tool)
        button_style = f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 10px;
                font-weight: bold;
                padding: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid {text_color};
            }}
            QPushButton:pressed {{
                background-color: {active_color};
            }}
        """

        # A) Manuelle Liste der Funktions-Buttons
        main_buttons = [
            "edit_header_button",
            "commits_button",
            "clean_emu_button",
            "patch_emu_git_button",
            "github_upload_patch_button",
            "plugin_update_button",
            "restart_tool_button",
            "btn_check_tools",
        ]

        for btn_name in main_buttons:
            btn = getattr(self, btn_name, None)
            if btn:
                btn.setStyleSheet(button_style)

        # B) ALLE dynamischen Buttons aus dem Grid (self.buttons)
        if hasattr(self, "buttons"):
            for btn in self.buttons.values():
                btn.setStyleSheet(button_style)

        # C) ALLE Buttons aus der Options-Leiste
        if hasattr(self, "option_buttons"):
            for val in self.option_buttons.values():
                if isinstance(val, (list, tuple)):
                    val[0].setStyleSheet(button_style)

        # 3. INFOSCREEN (Immer Schwarz, Schrift GROSS)
        if hasattr(self, "info_text") and self.info_text:
            self.info_text.setStyleSheet(
                f"""
                QTextEdit {{
                    background-color: #000000;
                    color: {text_color};
                    border: 1px solid {hover_color};
                    border-radius: 8px;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    font-size: 26px;  /* Vergrößerte Schrift */
                    padding: 10px;
                    line-height: 1.2;
                }}
            """
            )

            # Scrollbar passend dazu
            scrollbar_style = f"""
                QScrollBar:vertical {{ border: none; background: #000000; width: 12px; }}
                QScrollBar::handle:vertical {{ background: {hover_color}; border-radius: 6px; }}
            """
            self.info_text.verticalScrollBar().setStyleSheet(scrollbar_style)

        # 4. Header-Balken (Einstellungen)
        if hasattr(self, "controls_header") and self.controls_header:
            self.controls_header.setStyleSheet(
                f"""
                background-color: {bg_color};
                color: {text_color};
                font-weight: bold;
                border-radius: 6px;
                padding-left: 10px;
                border-bottom: 2px solid {hover_color};
            """
            )

        # 5. HAUPTFENSTER (Immer Schwarz)
        self.setStyleSheet("background-color: #000000;")
        self.repaint()

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
        """
        Übersetzt alle Buttons, Labels, Header und den Infobildschirm.
        Inklusive Patch Autor (Modifier) und Repo URL.
        """
        from PyQt6.QtWidgets import QApplication

        # 1. Aktuelle Sprache ermitteln (de/en)
        lang = str(getattr(self, "LANG", "de")).lower()[:2]
        lang_dict = TEXTS.get(lang, TEXTS.get("en", {}))

        # Helferfunktion für Übersetzungen
        def get_t(key, default=None):
            if key in lang_dict:
                return lang_dict[key]
            if default is not None:
                return default
            return str(key).replace("_", " ").title()

        # A) GRID BUTTONS (Patch Auswahl)
        if hasattr(self, "buttons") and self.buttons:
            for key, btn in self.buttons.items():
                btn.setText(get_t(key))

        # B) OPTION BUTTONS (Obere Reihe)
        if hasattr(self, "option_buttons") and self.option_buttons:
            for key, val in self.option_buttons.items():
                if isinstance(val, (list, tuple)) and len(val) >= 2:
                    btn = val[0]
                    text_key = val[1]
                    btn.setText(f"💻 {get_t(text_key)}" if "terminal" in str(key).lower() else get_t(text_key))

        # C) HEADER
        if hasattr(self, "controls_header") and self.controls_header:
            self.controls_header.setText(get_t("settings_header", "Einstellungen"))

        if hasattr(self, "github_header") and self.github_header:
            self.github_header.setText(get_t("github_config_header", "GitHub Konfiguration"))

        # D) LABELS & FUNKTIONS-BUTTONS
        if hasattr(self, "btn_check_tools") and self.btn_check_tools:
            self.btn_check_tools.setText(get_t("check_tools_button", "🛠️ Check Tools"))

        # --- Patch Autor Button (FIX: Jetzt steht hier wieder der feste Begriff) ---
        if hasattr(self, "btn_modifier") and self.btn_modifier:
            # FESTE Beschriftung statt Variablennamen
            btn_label = "👤 Patch Autor" if lang == "de" else "👤 Patch Author"
            self.btn_modifier.setText(btn_label)
            
            # Der Name (speedy005) wandert in den Tooltip
            current_name = getattr(self, "patch_modifier", "speedy005")
            self.btn_modifier.setToolTip(
                f"Aktueller Autor: {current_name}\n(Klicken zum Ändern)" if lang == "de"
                else f"Current Author: {current_name}\n(Click to change)"
            )

        # --- NEU: Repo URL Button Übersetzung ---
        if hasattr(self, "btn_repo_url") and self.btn_repo_url:
            self.btn_repo_url.setText(get_t("repo_url_button", "🌐 Repo URL"))
            self.btn_repo_url.setToolTip(
                "Emu-Repository URL ändern" if lang == "de" else "Change Emu-Repository URL"
            )

        if hasattr(self, "lang_label") and self.lang_label:
            self.lang_label.setText(get_t("language_label", "Sprache:"))

        if hasattr(self, "color_label") and self.color_label:
            self.color_label.setText(get_t("color_label", "Farbe:"))

        if hasattr(self, "commit_label") and self.commit_label:
            self.commit_label.setText(get_t("commit_count_label", "Commits:"))

        # E) GITHUB & EMU SPEZIFISCHE BUTTONS
        if hasattr(self, "patch_emu_git_button") and self.patch_emu_git_button:
            self.patch_emu_git_button.setText(get_t("patch_emu_git_button", "Patch OSCam Emu"))

        if hasattr(self, "github_upload_patch_button") and self.github_upload_patch_button:
            self.github_upload_patch_button.setText(get_t("github_upload_button", "GitHub Upload"))

        if hasattr(self, "clean_emu_button") and self.clean_emu_button:
            self.clean_emu_button.setText(get_t("clean_emu_button", "Bereinigen"))

        # G) REFRESH COLORS
        if hasattr(self, "repaint_ui_colors"):
            self.repaint_ui_colors()

        QApplication.processEvents()

    def change_language(self):
        """Wird aufgerufen, wenn die Sprach-Auswahl im Dropdown geändert wird."""
        if not hasattr(self, "language_box"):
            return

        # 1. Sprache ermitteln und normalisieren (DE/EN)
        selected = self.language_box.currentText().upper()
        self.LANG = "en" if "EN" in selected else "de"

        # 2. In Konfiguration speichern
        if hasattr(self, "cfg"):
            self.cfg["language"] = self.LANG
            if hasattr(self, "save_config"):
                self.save_config()

        # 3. UI-Texte aktualisieren (Zentrale Übersetzung aufrufen)
        self.update_language()

        # --- NEU: Patch-Autor & Repo-URL Button sofort anpassen ---
        if hasattr(self, "btn_modifier"):
            # Festgelegter Text je nach Sprache
            btn_label = "👤 Patch Autor" if self.LANG == "de" else "👤 Patch Author"
            self.btn_modifier.setText(btn_label)
            
            # Der tatsächliche Name (z.B. speedy005) kommt in den Tooltip
            current_author = getattr(self, "patch_modifier", "speedy005")
            self.btn_modifier.setToolTip(
                f"Aktueller Autor: {current_author}\n(Klicken zum Ändern)" if self.LANG == "de"
                else f"Current Author: {current_author}\n(Click to change)"
            )

        if hasattr(self, "btn_repo_url"):
            # Repo Button Übersetzung
            self.btn_repo_url.setText("🌐 Repo URL")
            self.btn_repo_url.setToolTip(
                "Emu-Repository URL ändern"
                if self.LANG == "de"
                else "Change Emu-Repository URL"
            )

        # 4. Bestätigung im Log ausgeben
        lang_dict = TEXTS.get(self.LANG, TEXTS.get("en", {}))
        lang_display = "English" if self.LANG == "en" else "Deutsch"

        # Text aus TEXTS holen, sonst Fallback
        success_msg = lang_dict.get(
            "language_changed",
            "Sprache eingestellt auf" if self.LANG == "de" else "Language set to"
        )

        if hasattr(self, "append_info") and hasattr(self, "info_text"):
            self.append_info(
                self.info_text, f"🌐 {success_msg}: {lang_display}", "success"
            )

        # 5. Status-Meldungen verzögert neu generieren (GUI-Aktualisierung)
        from PyQt6.QtCore import QTimer
        
        if hasattr(self, "check_for_plugin_update"):
            QTimer.singleShot(600, self.check_for_plugin_update)

        if hasattr(self, "manual_tool_check"):
            QTimer.singleShot(300, self.manual_tool_check)


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
        Nutzt run_command für sauberes Logging ohne Terminal-Ausgaben.
        """
        from PyQt6.QtWidgets import QTextEdit

        # Widget absichern (Fallback auf self.info_text falls info_widget nicht übergeben)
        if not isinstance(info_widget, QTextEdit):
            info_widget = getattr(self, "info_text", None)
            if info_widget is None:
                return  # Kein Ziel-Widget vorhanden

        lang = getattr(self, "LANG", "en").lower()

        # Texte aus dem Translation-Dictionary (mit Fallback)
        txt_loading = TEXTS.get(lang, {}).get("loading_commits", "Lade Commits...")
        txt_success = TEXTS.get(lang, {}).get(
            "commits_loaded", "Commits erfolgreich geladen"
        )

        # --- Startmeldung ---
        self.append_info(info_widget, txt_loading, "warning")  # Orange/Gelb

        try:
            # Pfad-Check
            if not os.path.exists(TEMP_REPO):
                self.append_info(
                    info_widget, f"❌ Ordner nicht gefunden: {TEMP_REPO}", "error"
                )
                return

            # Anzahl der Commits bestimmen
            num_commits = (
                self.commit_spin.value() if hasattr(self, "commit_spin") else 10
            )

            # Git-Befehl (vereinfacht, da wir cwd nutzen)
            cmd = f"git log -n {num_commits} --oneline"

            # Befehl ausführen (run_command liefert jetzt direkt den String)
            output = self.run_command(cmd, cwd=TEMP_REPO)

            if output:
                # Zeilen einzeln zum Widget hinzufügen
                lines = output.splitlines()
                for line in lines:
                    self.append_info(info_widget, f"• {line}", "info")

                # --- Erfolgsmeldung ---
                self.append_info(
                    info_widget, f"✅ {txt_success} ({len(lines)})", "success"
                )
            else:
                self.append_info(
                    info_widget, "⚠ Keine Commits gefunden oder Git-Fehler.", "warning"
                )

        except Exception as e:
            self.append_info(
                info_widget, f"❌ Schwerer Fehler beim Commit-Abruf: {str(e)}", "error"
            )

        # Fortschrittsbalken aktualisieren (optional)
        if progress_callback:
            try:
                progress_callback(100)
            except:
                pass

    # ===================== OSCam-EMU BUTTON WRAPPERS =====================
    def oscam_emu_git_patch(self, info_widget=None, progress_callback=None):
        """Patch erstellen und auf GitHub hochladen."""
        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", LANG)  # aktuelle GUI-Sprache

        # Info-Meldung in aktueller Sprache
        self.append_info(
            info_widget,
            TEXTS[lang].get(
                "oscam_emu_git_patch_start", "🔹 OSCam-Emu Git Patch wird erstellt..."
            ),
            "info",
        )

        # Patch hochladen
        _github_upload(
            PATCH_EMU_GIT_DIR,
            load_github_config().get("emu_repo_url"),
            info_widget=info_widget,
        )

        if progress_callback:
            progress_callback(100)

    def oscam_emu_git_clear(self, info_widget=None, progress_callback=None):
        """Zentrales Logging für die Emu-Git Bereinigung."""
        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", "de")

        # 1. Start-Meldung
        start_msg = TEXTS[lang].get(
            "oscam_emu_git_clearing", "🔹 OSCam-Emu Git Ordner wird geleert..."
        )
        self.append_info(info_widget, start_msg, "info")

        # 2. Ausführung
        result = clean_oscam_emu_git(progress_callback=progress_callback)

        # 3. Ergebnis-Meldung
        if result == "success":
            msg = TEXTS[lang].get(
                "oscam_emu_git_cleared", "✅ Bereinigung erfolgreich!"
            )
            self.append_info(info_widget, msg, "success")
        elif result == "not_found":
            msg = "ℹ️ " + (
                "Ordner bereits leer." if lang == "de" else "Folder already empty."
            )
            self.append_info(info_widget, msg, "info")
        else:
            self.append_info(info_widget, "❌ Error during deletion", "error")

        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()

    def check_patch(self, info_widget=None, progress_callback=None):
        """
        Prüft den Patch-Status sauber und einmalig.
        Verhindert Doppler-Logs und nutzt das zentrale TEXTS-System.
        """
        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", "de")

        # 1. Existenzprüfung der Datei
        if not os.path.exists(PATCH_FILE):
            err_msg = TEXTS[lang].get(
                "patch_file_missing", "❌ Patch-Datei nicht gefunden!"
            )
            self.append_info(info_widget, err_msg, "error")
            if progress_callback:
                progress_callback(0)
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
        else:
            fail_msg = TEXTS[lang].get(
                "patch_check_fail", "❌ Patch-Check fehlgeschlagen!"
            )
            self.append_info(info_widget, fail_msg, "error")

        # 4. Abschluss
        if progress_callback:
            progress_callback(100)

        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()

    def apply_patch(self, info_widget=None, progress_callback=None):
        info_widget = info_widget or self.info_text
        lang = getattr(self, "LANG", "de").lower()

        # 1. Check ob Datei existiert
        if not os.path.exists(PATCH_FILE):
            msg = self.get_t("patch_file_missing", "❌ Patch-Datei fehlt!").format(
                path=PATCH_FILE
            )
            self.append_info(info_widget, msg, "error")
            return

        # Logger definieren
        logger = lambda text, level="info": self.append_info(info_widget, text, level)

        # 2. Eigene Start-Meldung auf Deutsch (bevor run_bash loslegt)
        start_msg = self.get_t("executing_git_apply", "🚀 Wende Patch an...").format(
            patch="oscam-emu.patch"
        )
        self.append_info(info_widget, start_msg, "warning")

        # Patch ausführen
        # Hinweis: Falls run_bash selbst "Executing..." printet, musst du run_bash anpassen!
        code = run_bash(f"git apply {PATCH_FILE}", cwd=TEMP_REPO, logger=logger)

        if code == 0:
            self.append_info(
                info_widget,
                self.get_t("patch_emu_git_done", "✅ Patch erfolgreich angewendet"),
                "success",
            )
        else:
            self.append_info(
                info_widget,
                self.get_t("patch_emu_git_apply_failed", "❌ Patch fehlgeschlagen"),
                "error",
            )

        if progress_callback:
            progress_callback(100)

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

    # Standard-Imports
    import sys
    from PyQt6.QtWidgets import QApplication
    from oscam_patch_manager import (
        PatchManagerGUI,
        TEXTS,
        fill_missing_keys,
        # ensure_dir,
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
