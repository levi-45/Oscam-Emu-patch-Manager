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
from pathlib import Path
from io import BytesIO
from datetime import datetime, timezone
from PyQt6.QtGui import QPixmap, QAction
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QTextEdit, QProgressBar, QLabel, QComboBox,
    QSpinBox, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QDialogButtonBox, QFileDialog, QGroupBox, QSizePolicy
)
from PyQt6.QtGui import QFont, QColor, QTextCursor, QIcon
from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize
from packaging.version import Version

now = QDateTime.currentDateTime()
time_str = now.toString("HH:mm:ss")
date_str = now.toString("dd.MM.yyyy")
# ===================== APP CONFIG =====================
APP_VERSION = "1.7.6"
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
# -----------------------------
plugin_dir = os.path.dirname(os.path.abspath(__file__))
pyc_file = os.path.join(plugin_dir, "oscam_patch_manager.pyc")
cache_dir = os.path.join(plugin_dir, "__pycache__")

# Konfigurationsdateien
# -----------------------------
CONFIG_FILE = os.path.join(PLUGIN_DIR, "config.json")
GITHUB_CONF_FILE = os.path.join(PLUGIN_DIR, "github_upload_config.json")
# -----------------------------
# Patch-Dateien im Plugin-Ordner
# -----------------------------
PATCH_FILE = os.path.join(PLUGIN_DIR, "oscam-emu.patch")
ZIP_FILE = os.path.join(PLUGIN_DIR, "oscam-emu.zip")
# -----------------------------
# Ordner
# -----------------------------
ICON_DIR = os.path.join(PLUGIN_DIR, "icons")
TEMP_REPO = os.path.join(PLUGIN_DIR, "temp_repo")            
PATCH_EMU_GIT_DIR = os.path.join(PLUGIN_DIR, "oscam-emu-git")
# -----------------------------
# Alte Patch-Ordner / Dateien
# -----------------------------
# Default-Ordner (wird genutzt, wenn noch kein anderer Pfad gewählt)
OLD_PATCH_DIR_DEFAULT = "/opt/s3/support/patches"   # angepasst
OLD_PATCH_DIR_PLUGIN_DEFAULT = os.path.join(PLUGIN_DIR, "old_patches")

# Aktueller Arbeitsordner für alte Patches (kann vom User geändert werden)
OLD_PATCH_DIR = OLD_PATCH_DIR_PLUGIN_DEFAULT
# Legacy-Variable für alte Funktionen
OLD_ = OLD_PATCH_DIR
# Alte Patch-Dateien im aktuellen Arbeitsordner
OLD_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.patch")
ALT_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.altpatch")
PATCH_MANAGER_OLD = os.path.join(OLD_PATCH_DIR, "oscam_patch_manager_old.py")
CONFIG_OLD = os.path.join(OLD_PATCH_DIR, "config_old.json")
GITHUB_CONFIG_OLD = os.path.join(OLD_PATCH_DIR, "github_upload_config_old.json")

# -----------------------------
# Tools
# -----------------------------
CHECK_TOOLS_SCRIPT = os.path.join(PLUGIN_DIR, "check_tools.sh")

# -----------------------------
# Patch Modifier / Repos
# -----------------------------
PATCH_MODIFIER = "speedy005"
EMUREPO = "https://github.com/oscam-mirror/oscam-emu.git"
STREAMREPO = "https://git.streamboard.tv/common/oscam.git"





NEVER_DELETE = [
    "oscam_patch_manager.py", 
    "oscam-patch-manager.sh", 
    "oscam-patch-manager-gui.sh",
    "oscam-emu-patch.sh", 
    "oscam-patch-manager-gui-eng.sh", 
    "github_upload_config.json",
    "oscam-patch.sh", 
    "config.json", 
    "oscam_patch_manager_test.py",
    "oscam_patch_manager_neu.py",
    "check_tools.sh",
    "versuche.py", 
    "icons"
]

# ===================== COLORS =====================
DIFF_COLORS = {
    "Classic":       {"bg": "#1E1E1E", "text": "#FFFFFF"},
    "Ocean":         {"bg": "#2B3A67", "text": "#A8D0E6"},
    "Sunset":        {"bg": "#FF6B6B", "text": "#FFE66D"},
    "Forest":        {"bg": "#2E8B57", "text": "#E0F2F1"},
    "Candy":         {"bg": "#FFB6C1", "text": "#4B0082"},
    "Cyberpunk":     {"bg": "#0D0D0D", "text": "#FF00FF"},
    "CoolMint":      {"bg": "#A8FFF0", "text": "#003F3F"},
    "Sunrise":       {"bg": "#FFD580", "text": "#B22222"},
    "DeepSea":       {"bg": "#001F3F", "text": "#7FDBFF"},
    "Lavender":      {"bg": "#E6E6FA", "text": "#4B0082"},
    "Blue-Orange":   {"bg": "#FF8C00", "text": "#FFFFFF"},
    "Yellow-Purple": {"bg": "#800080", "text": "#FFFF00"},
    "Green-Red":     {"bg": "#228B22", "text": "#FFFFFF"},
    "Midnight":      {"bg": "#121212", "text": "#BB86FC"},
    "Solarized":     {"bg": "#002B36", "text": "#839496"},
    "Neon":          {"bg": "#0B0C10", "text": "#66FCF1"},
    "Fire":          {"bg": "#7F0000", "text": "#FF4500"},
    "Moss":          {"bg": "#2E3A23", "text": "#A9BA9D"},
    "Peach":         {"bg": "#FFDAB9", "text": "#8B4513"},
    "Galaxy":        {"bg": "#1B1B2F", "text": "#E94560"},
    "Aqua":          {"bg": "#004D4D", "text": "#00FFFF"},
    "Lavish":        {"bg": "#3D2B56", "text": "#F1C40F"},
    "Tech":          {"bg": "#0F0F0F", "text": "#00FF00"},
    "NeonPink":      {"bg": "#1A1A1D", "text": "#FF6EC7"},
    "ElectricBlue":  {"bg": "#0B0C10", "text": "#00FFFF"},
    "CyberGreen":    {"bg": "#050A05", "text": "#39FF14"},
    "SunsetVibes":   {"bg": "#FF4500", "text": "#FFF8DC"},
    "PurpleHaze":    {"bg": "#2E004F", "text": "#D580FF"},
    "MintyFresh":    {"bg": "#002B2B", "text": "#7FFFD4"},
    "HotMagenta":    {"bg": "#1B0B1B", "text": "#FF00FF"},
    "GoldenHour":    {"bg": "#2F1E00", "text": "#FFD700"},
    "OceanDeep":     {"bg": "#001F3F", "text": "#00BFFF"},
    "Tropical":      {"bg": "#003300", "text": "#FFDD00"},
    "MagentaGlow":   {"bg": "#1C001C", "text": "#FF00FF"},
    "CyanWave":      {"bg": "#001F1F", "text": "#00FFFF"},
    "SunriseGold":   {"bg": "#2B1A00", "text": "#FFD700"},
    "CoralReef":     {"bg": "#2F0A0A", "text": "#FF7F50"},
    "LimePunch":     {"bg": "#0A1F00", "text": "#BFFF00"},
    "VioletStorm":   {"bg": "#1E003F", "text": "#D580FF"},
    "OceanMist":     {"bg": "#002B3A", "text": "#7FDBFF"},
    "PeachySun":     {"bg": "#3F1E00", "text": "#FFA07A"},
    "NeonOrange":    {"bg": "#1A0A00", "text": "#FF8C00"},
    "ElectricLime":      {"bg": "#00FF00", "text": "#0D0D0D"},
    "NeonCoral":         {"bg": "#FF4040", "text": "#0D0D0D"},
    "RoyalTeal":         {"bg": "#005F6B", "text": "#FFD700"},
    "MidnightPurple":    {"bg": "#1C003D", "text": "#FF77FF"},
    "SolarFlare":        {"bg": "#FFB300", "text": "#2C003E"},
    "FrostBlue":         {"bg": "#00D4FF", "text": "#1A1A2E"},
    "CandyFloss":        {"bg": "#FFB3FF", "text": "#330033"},
    "TangerineDream":    {"bg": "#FF6F3C", "text": "#1A1A1A"},
    "EmeraldNight":      {"bg": "#004D40", "text": "#A8FF60"},
    "CrimsonWave":       {"bg": "#8B0000", "text": "#FFDDFF"},
    "NeonLemon":        {"bg": "#1A1A00", "text": "#FFFF33"},
    "UltraViolet":      {"bg": "#330066", "text": "#FF99FF"},
    "AquaBlast":        {"bg": "#002233", "text": "#33FFFF"},
    "MagentaRush":      {"bg": "#2A001A", "text": "#FF33CC"},
    "GoldenEmerald":    {"bg": "#003300", "text": "#FFD700"},
    "ElectricFuchsia":  {"bg": "#1A001A", "text": "#FF33FF"},
    "IceMint":          {"bg": "#001F1A", "text": "#99FFCC"},
    "FlamingSun":       {"bg": "#4B0000", "text": "#FFCC33"},
    "CobaltSky":        {"bg": "#00114D", "text": "#66CCFF"},
    "PinkGalaxy":       {"bg": "#1A0022", "text": "#FF66FF"},
    "NeonPink":       {"bg": "#1A1A1D", "text": "#FF6EC7"},
    "ElectricBlue":   {"bg": "#1A1A1D", "text": "#00FFFF"},
    "LimeGreen":      {"bg": "#1A1A1D", "text": "#32CD32"},
    "SunsetOrange":   {"bg": "#1A1A1D", "text": "#FF4500"},
    "VioletDream":    {"bg": "#1A1A1D", "text": "#8A2BE2"},
    "GoldenYellow":   {"bg": "#1A1A1D", "text": "#FFD700"},
    "CandyRed":       {"bg": "#1A1A1D", "text": "#FF1493"},
    "AquaMarine":     {"bg": "#1A1A1D", "text": "#7FFFD4"},
    "CoralPink":      {"bg": "#1A1A1D", "text": "#FF7F50"},
    "Turquoise":      {"bg": "#1A1A1D", "text": "#40E0D0"},
    "MagentaPop":     {"bg": "#1A1A1D", "text": "#FF00FF"},
    "SkyBlue":        {"bg": "#1A1A1D", "text": "#87CEEB"},
    "LemonYellow":    {"bg": "#1A1A1D", "text": "#FFF44F"},
    "HotPink":        {"bg": "#1A1A1D", "text": "#FF69B4"},
    "BrightOrange":   {"bg": "#1A1A1D", "text": "#FFA500"},
    "MagentaPop":    {"bg": "#1A1A1D", "text": "#FF00FF"},
    "NeonCyan":      {"bg": "#0D0D0D", "text": "#00FFFF"},
    "ElectricLime":  {"bg": "#1B1B1B", "text": "#00FF00"},
    "CrimsonNight":  {"bg": "#1C1C1F", "text": "#DC143C"},
    "RoyalPurple":   {"bg": "#161618", "text": "#800080"},
    "OrangeFever":   {"bg": "#1F1F1F", "text": "#FFA500"},
    "BlueSteel":     {"bg": "#101018", "text": "#4682B4"},
    "PinkGalaxy":    {"bg": "#1A101A", "text": "#FF69B4"},
    "AmberGlow":     {"bg": "#1C1B10", "text": "#FFBF00"},
    "TealShadow":    {"bg": "#121212", "text": "#008080"},
    "VioletHaze":    {"bg": "#1A1A2E", "text": "#EE82EE"},
    "RedStorm":      {"bg": "#1B0B0B", "text": "#FF4500"},
    "CyanIce":       {"bg": "#0F1A1A", "text": "#00CED1"},
    "LimePulse":     {"bg": "#101810", "text": "#32CD32"},
    "FuchsiaDream":  {"bg": "#1A1018", "text": "#FF00FF"},
    "TurquoiseDream":{"bg": "#002222", "text": "#40E0D0"}
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
        "patch_apply": "Apply Patch",
        "patch_zip": "Zip Patch",
        "backup_old": "Backup/Renew Patch",
        "clean_folder": "Clean Patch Folder",
        "change_old_dir": "Select S3 Patch Folder",
        "patch_emu_git": "OSCam Emu Git patchen",
        "exit": "Exit",
        "no": "No",
        "yes": "Yes",
        
        # Option Buttons
        "git_status": "View Commits",
        "plugin_update": "Plugin Update",
        "restart_tool": "Restart Tool",
        "edit_patch_header": "Edit Patch Header",
        "github_emu_config_button": "Edit GitHub Config",
        "github_upload_patch": "Upload Patch File",
        "github_upload_emu": "Upload OSCam-Emu Git",
        "github_version_fetch_failed": "⚠️ Failed to fetch GitHub version: {error}",

        # Labels
        "language_label": "Language:",
        "color_label": "Color",
        "commit_count_label": "Number of commits to show",
        "info_tooltip": "Info / Help",
        "clean_emu_git": "Clean OSCam Emu Git",
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

        # Messages
        "patch_applied_success": "✅ Patch successfully applied",
        "patch_created_success": "✅ Patch created: {patch_file}",
        "patch_zipped_success": "📦 Patch zipped: {zip_file}",
        "backup_done": "💾 Patch backed up: {old_}",
        "patch_failed": "❌ Patch failed – base mismatch",
        "not_installed": "is not installed",
        "all_tools_installed": "✅ All required tools installed",
        "patch_folder_cleaned": "✅ Patch folder cleaned",
        "oscam_emu_git_cleaned": "✅ OSCam Emu Git folder cleaned",
        "showing_commits": "🔄 Showing last commits …",
        "commits_done": "✅ Done",
        "github_emu_credentials_missing": "❌ GitHub Emu credentials missing!",
        "patch_file_missing": "❌ Patch file does not exist!",
        "temp_repo_deleted": "♻️ Temp repo deleted: {path}",
        "clean_done": "✅ Clean operation completed",
        "restart_required_msg": "The update was installed successfully. The tool must be restarted.\nRestart now?",
        "restart_required_title": "Restart required",
        "update_success": "✅ Update successful! Please restart the plugin.",
        "update_fail": "❌ Update failed: {error}",
        "update_not_available": "No new version available.",
        'exit_question': 'Do you really want to close the tool?',
        "github_version_available": "New version {version} is available on GitHub",
        "update_check_start": "Checking for updates…",
        "github_version_available": "A new version {version} is available on GitHub",
        "github_version_available": "New version {version} available on GitHub",
        "update_check_start": "Checking for updates…",
        "plugin_update": "Plugin Update"
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
        "change_old_dir": "S3 Patch-Ordner auswählen",
        "clean_emu_git": "OSCam Emu Git bereinigen",
        "yes": "Ja:",
        "no": "Nein",
        "exit": "Beenden",

        # Option Buttons
        "git_status": "Commits anzeigen",
        "plugin_update": "Plugin Update",
        "restart_tool": "Tool Neustarten",
        "edit_patch_header": "Patch Header bearbeiten",
        "github_emu_config_button": "GitHub-Konfiguration bearbeiten",
        "github_upload_patch": "Patch hochladen",
        "github_upload_emu": "OSCam-Emu Git hochladen",
        "patch_emu_git": "OSCam Emu Git patchen",
        'yes': 'Ja', 
        
        "github_version_fetch_failed": "⚠️ Fehler beim Abrufen der GitHub-Version: {error}",

        # Labels
        "language_label": "Sprache:",
        "color_label": "Farbe",
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

        # Messages
        "patch_applied_success": "✅ Patch erfolgreich angewendet",
        "patch_created_success": "✅ Patch erstellt: {patch_file}",
        "patch_zipped_success": "📦 Patch gezippt: {zip_file}",
        "backup_done": "💾 Patch gesichert: {old_}",
        "patch_failed": "❌ Patch fehlgeschlagen – Basis stimmt nicht",
        "not_installed": "nicht installiert",
        "all_tools_installed": "✅ Alle benötigten Tools installiert",
        "patch_folder_cleaned": "✅ Patch-Ordner geleert",
        "oscam_emu_git_cleaned": "✅ OSCam Emu Git Ordner bereinigt",
        "showing_commits": "🔄 Letzte Commits werden angezeigt …",
        "commits_done": "✅ Fertig",
        "github_emu_credentials_missing": "❌ GitHub-Emu-Zugangsdaten fehlen!",
        "patch_file_missing": "❌ Patch-Datei existiert nicht!",
        "temp_repo_deleted": "♻️ TEMP_REPO gelöscht: {path}",
        "clean_done": "✅ Clean-Vorgang abgeschlossen",
        "restart_required_msg": "Das Update wurde erfolgreich installiert. Das Tool muss neu gestartet werden.\nJetzt neu starten?",
        "restart_required_title": "Neustart erforderlich",
        "update_success": "✅ Update erfolgreich! Bitte Plugin neu starten.",
        "update_fail": "❌ Update fehlgeschlagen: {error}",
        "update_not_available": "Keine neue Version verfügbar.",
        'exit_question': 'Möchten Sie das Tool wirklich schließen?',
        "github_version_available": "Neue Version {version} auf GitHub verfügbar",
        "update_check_start": "Prüfe auf Updates …",
        "plugin_update": "Plugin Update"
    }
}


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
                self.append_info(None, f"⚠️ Config konnte nicht gelesen werden: {e}", "warning")

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        self.append_info(None, f"Fehler beim Speichern der Config: {e}", "error")

# ===================== CONFIG =====================
def load_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # Wenn die Datei mal nur eine Zahl enthält, korrigiere es
            if not isinstance(cfg, dict):
                cfg = {"commit_count": int(cfg), "color": "Classic", "language": "DE", "s3_patch_path": ""}
        except Exception as e:
            self.append_info(None, f"⚠️ Config konnte nicht gelesen werden: {e}", "warning")
            cfg = {"commit_count": 5, "color": "Classic", "language": "DE", "s3_patch_path": ""}
    return cfg

# ===================== INFOSCREEN =====================

def run_bash(cmd, cwd=None, logger=None):
    """
    Führt einen Bash-Befehl aus und schreibt jede Zeile live ins Log.
    logger muss callable(text, level) sein.
    """
    def log(text, level="info"):
        if callable(logger):
            logger(text, level)
        else:
            print(f"[{level.upper()}] {text}")

    log(f"▶ {cmd}", "info")

    if cwd:
        ensure_dir(cwd)

    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    if process.stdout:
        for line in process.stdout:
            line = line.rstrip()
            if line:
                log(line, "info")

    process.wait()
    return process.returncode

# ===================== PATCH HEADER =====================
from datetime import datetime
import subprocess
import os

def get_patch_header(repo_dir=None):
    if repo_dir is None:
        repo_dir = TEMP_REPO  # TEMP_REPO muss vorher definiert sein

    # Standardwerte
    version = "2.26.01"
    build = "0"
    commit = "N/A"

    # globals.h auslesen
    globals_path = os.path.join(repo_dir, "globals.h")
    if os.path.exists(globals_path):
        with open(globals_path, "r") as f:
            for line in f:
                if line.startswith("#define CS_VERSION"):
                    parts = line.strip().split('"')
                    if len(parts) >= 2:
                        version = parts[1].split("-")[0]
                        build = parts[1].split("-")[1] if "-" in parts[1] and "-" in parts[1] else "0"

    # Git-Commit auslesen
    git_dir = os.path.join(repo_dir, ".git")
    if os.path.exists(git_dir):
        try:
            commit = subprocess.getoutput(f"git -C {repo_dir} rev-parse --short HEAD").strip()
        except Exception:
            pass

    # Patch modified date (heutiges lokales Datum)
    modified_date = datetime.now().strftime("%d/%m/%Y")

    # Patch date = aktuelles UTC-Datum
    patch_date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC (+00:00)")

    # Header zusammenbauen
    header = (
        f"patch version: oscam-emu-patch {version}-{build}-({commit})\n"
        f"patch modified by {PATCH_MODIFIER} ({modified_date})\n"
        f"patch date: {patch_date_utc}"
    )

    return header

# ===================== TOOL CHECK & AUTOMATISCHE INSTALLATION =====================
def check_tools(info_widget=None):
    """
    Prüft alle benötigten Tools und installiert fehlende automatisch (Debian/Ubuntu).
    """
    tools = {
        "git": "git",
        "patch": "patch",
        "zip": "zip",
        "python3": "python3",
        "pip3": "python3-pip"
    }

    all_ok = True
    for tool, package in tools.items():
        if shutil.which(tool) is None:
            self.append_info(info_widget, f"{tool} {TEXTS[LANG]['not_installed']}, versuche zu installieren...", "warning")

            # Installation versuchen (Debian/Ubuntu)
            install_cmd = f"sudo apt update && sudo apt install -y {package}"
            code = run_bash(install_cmd, info_widget=info_widget)

            # Prüfen, ob Installation erfolgreich war
            if shutil.which(tool) is None:
                self.append_info(info_widget, f"{tool} konnte nicht installiert werden!", "error")
                all_ok = False
            else:
                self.append_info(info_widget, f"{tool} erfolgreich installiert.", "success")

    # Finaler Check
    missing = [t for t in tools if shutil.which(t) is None]
    if missing:
        self.append_info(info_widget, f"❌ Folgende Tools fehlen immer noch: {', '.join(missing)}", "error")
    else:
        self.append_info(info_widget, TEXTS[LANG]['all_tools_installed'], "success")

# ===================== PATCH FUNCTIONS =====================
from PyQt6.QtWidgets import QTextEdit, QApplication
import os, subprocess

def create_patch(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Erstellt den Patch im TEMP_REPO.
    Meldungen erscheinen im Infoscreen oder Terminal.
    """
    # Widget: info_widget oder gui_instance.info_text
    widget = info_widget or (getattr(gui_instance, "info_text", None) if gui_instance else None)

    # Lokaler Logger mit Übersetzungen
    def log(text_key, level="info", **kwargs):
        colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
        color = colors.get(level, "gray")

        text_template = TEXTS[LANG].get(text_key, text_key)
        text = text_template.format(**kwargs)

        if isinstance(widget, QTextEdit):
            widget.append(f'<span style="color:{color}">{text}</span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()
        elif gui_instance and hasattr(gui_instance, "append_info"):
            gui_instance.append_info(widget, text, level)
        else:
            print(f"[{level.upper()}] {text}")

    log("patch_create_start", "info")

    os.makedirs(TEMP_REPO, exist_ok=True)

    try:
        git_dir = os.path.join(TEMP_REPO, ".git")
        if not os.path.exists(git_dir):
            log("patch_create_clone_start", "warning")
            code = run_bash(f"git clone {STREAMREPO} .", cwd=TEMP_REPO, logger=log)
            if code != 0:
                log("patch_create_clone_failed", "error")
                return
            run_bash(f"git remote add emu-repo {EMUREPO}", cwd=TEMP_REPO, logger=log)

        # Fetch & Reset
        run_bash("git fetch origin", cwd=TEMP_REPO, logger=log)
        run_bash("git fetch emu-repo", cwd=TEMP_REPO, logger=log)
        run_bash("git checkout master", cwd=TEMP_REPO, logger=log)
        run_bash("git reset --hard origin/master", cwd=TEMP_REPO, logger=log)

        # Patch erstellen
        header = get_patch_header()
        diff = subprocess.getoutput(
            f"git -C {TEMP_REPO} diff origin/master..emu-repo/master -- . ':!.github'"
        )
        if not diff.strip():
            diff = TEXTS[LANG].get("patch_create_no_changes", "# Keine Änderungen gefunden")

        with open(PATCH_FILE, "w", encoding="utf-8") as f:
            f.write(header + "\n" + diff + "\n")

        log("patch_create_success", "success", patch_file=PATCH_FILE)

    except Exception as e:
        log("patch_create_failed", "error", error=str(e))

    if progress_callback:
        progress_callback(100)

# ===================== PATCH BACKUP =====================
from PyQt6.QtWidgets import QTextEdit, QApplication, QFileDialog
import os, shutil

def change_old_patch_dir(self, info_widget=None, progress_callback=None):
    """
    Ändert den Speicherort des alten Patch-Ordners.
    Die neue oscam-emu.patch aus dem Startordner wird dort später ersetzt.
    """
    global OLD_PATCH_DIR, OLD_PATCH_FILE, ALT_PATCH_FILE, PATCH_MANAGER_OLD, CONFIG_OLD, GITHUB_CONFIG_OLD

    widget = info_widget or getattr(self, "info_text", None)

    # Logger mit Übersetzung
    def log(text_key, level="info", **kwargs):
        colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
        color = colors.get(level, "gray")

        text_template = TEXTS[LANG].get(text_key, text_key)
        text = text_template.format(**kwargs)

        if widget and hasattr(self, "append_info"):
            self.append_info(widget, text, level)
        elif widget and hasattr(widget, "append") and hasattr(widget, "moveCursor"):
            widget.append(f'<span style="color:{color}">{text}</span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()
        else:
            print(f"[{level.upper()}] {text}")

    # Ordner auswählen
    new_dir = QFileDialog.getExistingDirectory(
        self,
        TEXTS[LANG].get("select_s3_patch_folder", "Select S3 Patch Folder"),
        OLD_PATCH_DIR
    )

    if new_dir:
        OLD_PATCH_DIR = new_dir

        # Alte Dateien im neuen Pfad
        OLD_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.patch")
        ALT_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.altpatch")
        PATCH_MANAGER_OLD = os.path.join(OLD_PATCH_DIR, "oscam_patch_manager_old.py")
        CONFIG_OLD = os.path.join(OLD_PATCH_DIR, "config_old.json")
        GITHUB_CONFIG_OLD = os.path.join(OLD_PATCH_DIR, "github_upload_config_old.json")

        log("old_patch_path_changed", "success", OLD_=OLD_PATCH_DIR)
        
        # Die neue Patch-Datei im Startverzeichnis kopieren
        start_dir_patch = os.path.join(os.getcwd(), "oscam-emu.patch")
        if os.path.exists(start_dir_patch):
            try:
                # Alte Datei sichern
                if os.path.exists(OLD_PATCH_FILE):
                    shutil.move(OLD_PATCH_FILE, ALT_PATCH_FILE)
                    log("backup_done", "success", old_=ALT_PATCH_FILE)
                
                shutil.copy(start_dir_patch, OLD_PATCH_FILE)
                log("new_patch_installed", "success", path=OLD_PATCH_FILE)
            except Exception as e:
                log("patch_failed", "error", path=str(e))
        else:
            log("patch_file_missing", "warning", path=start_dir_patch)
    else:
        log("old_patch_path_cancelled", "info")

    if progress_callback:
        progress_callback(100)


def log(text, level="info"):
    colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
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
import shutil, os

def backup_old_patch(self, make_backup=True, info_widget=None, progress_callback=None):
    """
    Sichert den alten Patch:
    - optional als .altpatch
    - ersetzt ihn mit der neuen oscam-emu.patch aus dem Tool-Ordner
    Meldungen erscheinen im Infoscreen (QTextEdit) oder im Terminal.
    """

    # Infoscreen Widget
    widget = info_widget if isinstance(info_widget, QTextEdit) else getattr(self, "info_text", None)

    # Logger-Funktion, Texte aus TEXTS
    def log(text_key, level="info", **kwargs):
        colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
        color = colors.get(level, "gray")
        
        # Übersetzungs-Text aus TEXTS, falls vorhanden, sonst key selbst
        text_template = TEXTS[LANG].get(text_key, text_key)
        text = text_template.format(**kwargs)

        if isinstance(widget, QTextEdit):
            widget.append(f'<span style="color:{color}">{text}</span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()
        else:
            print(f"[{level.upper()}] {text}")

    # Alte Patch-Dateien im konfigurierten S3-Ordner
    old_patch = getattr(self, "OLD_PATCH_FILE", os.path.join(OLD_PATCH_DIR_DEFAULT, "oscam-emu.patch"))
    alt_patch = getattr(self, "ALT_PATCH_FILE", os.path.join(OLD_PATCH_DIR_DEFAULT, "oscam-emu.altpatch"))

    # Neue Patch-Datei aus dem Tool-Ordner
    tool_dir = os.path.dirname(os.path.abspath(__file__))  # Script-Ordner
    new_patch = os.path.join(tool_dir, "oscam-emu.patch")

    log("backup_old_start", "info")

    # Zielordner sicherstellen
    try:
        os.makedirs(os.path.dirname(old_patch), exist_ok=True)
    except Exception as e:
        log("patch_failed", "error", path=str(e))
        return

    # Alte Datei sichern
    if os.path.exists(old_patch) and make_backup:
        try:
            shutil.copy2(old_patch, alt_patch)
            log("backup_done", "success", path=alt_patch)
        except Exception as e:
            log("patch_failed", "error", path=str(e))
            return
    else:
        log("no_old_patch", "info")

    # Neue Patch-Datei kopieren
    if not os.path.exists(new_patch):
        log("patch_file_missing", "error", path=new_patch)
        return

    try:
        shutil.copy2(new_patch, old_patch)
        log("new_patch_installed", "success", path=old_patch)
    except Exception as e:
        log("patch_failed", "error", path=str(e))

    # Fortschritt melden
    if progress_callback:
        progress_callback(100)

# ===================== CLEAN PATCH FOLDER =====================
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QTextCursor
import shutil, os

def clean_patch_folder(gui_instance=None, info_widget=None, progress_callback=None):
    """
    Löscht TEMP_REPO, PATCH_FILE, ZIP_FILE und TEMP_PATCH_GIT komplett.
    gui_instance: Instanz von PatchManagerGUI
    info_widget: optionales QTextEdit
    progress_callback: optionaler Callback
    """

    # Infoscreen Widget
    widget = info_widget or (getattr(gui_instance, "info_text", None) if gui_instance else None)

    # Logger-Funktion mit Übersetzungen
    def log(text_key, level="info", **kwargs):
        colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
        color = colors.get(level, "gray")

        # Übersetzung aus TEXTS, fallback auf key
        text_template = TEXTS[LANG].get(text_key, text_key)
        text = text_template.format(**kwargs)

        if isinstance(widget, QTextEdit):
            widget.append(f'<span style="color:{color}">{text}</span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()
        else:
            print(f"[{level.upper()}] {text}")

    # TEMP_REPO löschen
    if os.path.exists(TEMP_REPO):
        try:
            shutil.rmtree(TEMP_REPO)
            log("temp_repo_deleted", "success", path=TEMP_REPO)
        except Exception as e:
            log("delete_failed", "error", path=f"TEMP_REPO ({e})")
    else:
        log("temp_repo_missing", "warning", path=TEMP_REPO)

    # TEMP_PATCH_GIT löschen
    temp_patch_git = os.path.join(PLUGIN_DIR, "temp_patch_git")
    if os.path.exists(temp_patch_git):
        try:
            shutil.rmtree(temp_patch_git)
            log("temp_patch_git_deleted", "success", path=temp_patch_git)
        except Exception as e:
            log("delete_failed", "error", path=f"TEMP_PATCH_GIT ({e})")
    else:
        log("temp_patch_git_missing", "warning", path=temp_patch_git)

    # PATCH_FILE löschen
    if os.path.exists(PATCH_FILE):
        try:
            os.remove(PATCH_FILE)
            log("patch_file_deleted", "success", path=PATCH_FILE)
        except Exception as e:
            log("delete_failed", "error", path=f"PATCH_FILE ({e})")
    else:
        log("patch_file_missing", "warning", path=PATCH_FILE)

    # ZIP_FILE löschen
    if os.path.exists(ZIP_FILE):
        try:
            os.remove(ZIP_FILE)
            log("zip_file_deleted", "success", path=ZIP_FILE)
        except Exception as e:
            log("delete_failed", "error", path=f"ZIP_FILE ({e})")
    else:
        log("zip_file_missing", "warning", path=ZIP_FILE)

    log("clean_done", "success")

    if progress_callback:
        progress_callback(100)

# ===================== ICONS =====================
ICON_SIZE = 64

def create_icons():
    """
    Erstellt Icons für die GUI. Die Dateinamen sind kurz, damit
    keine Probleme mit zu langen Namen auftreten.
    """
    from PIL import Image, ImageDraw, ImageFont

    ensure_dir(ICON_DIR)

    icons = {
        "patch": "Patch",
        "info": "Info",
        "git": "Git"
    }

    for key, text in icons.items():
        # Icon-Größe
        img = Image.new("RGBA", (64, 64), (30, 30, 30, 255))
        draw = ImageDraw.Draw(img)

        # Schriftart
        try:
            fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
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

def clean_oscam_emu_git(info_widget=None, progress_callback=None):
    """
    Löscht den PATCH_EMU_GIT Ordner.
    Meldungen erscheinen im Infoscreen oder Terminal.
    """
    widget = info_widget

    def log(text_key, level="info", **kwargs):
        colors = {
            "success": "green",
            "warning": "orange",
            "error": "red",
            "info": "gray"
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

    log("cleaning_oscam_emu_git", "info", path=PATCH_EMU_GIT_DIR)

    if os.path.exists(PATCH_EMU_GIT_DIR):
        try:
            shutil.rmtree(PATCH_EMU_GIT_DIR)
            log("oscam_emu_git_deleted", "success", path=PATCH_EMU_GIT_DIR)
        except Exception as e:
            log("delete_failed", "error", path=PATCH_EMU_GIT_DIR, error=str(e))
            return
    else:
        log("oscam_emu_git_missing", "warning", path=PATCH_EMU_GIT_DIR)

    if progress_callback:
        progress_callback(100)

# ===================== patch_oscam_emu_git=====================
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QTextCursor
import shutil, os

def patch_oscam_emu_git(info_widget=None, progress_callback=None):
    """
    Klont das Streamboard Git, wendet oscam-emu.patch an und commitet.
    Meldungen erscheinen im Infoscreen oder Terminal.
    """
    widget = info_widget

    # Logger mit Übersetzungen
    def log(text_key, level="info", **kwargs):
        colors = {"success":"green","warning":"orange","error":"red","info":"gray"}
        color = colors.get(level,"gray")

        # Text aus TEXTS holen, fallback auf Key
        text_template = TEXTS[LANG].get(text_key, text_key)
        text = text_template.format(**kwargs)

        if isinstance(widget, QTextEdit):
            widget.append(f'<span style="color:{color}">{text}</span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()
        else:
            print(f"[{level.upper()}] {text}")
    log("patch_emu_git_start", "info", path=PATCH_EMU_GIT_DIR)

    # Ordner löschen, falls vorhanden
    if os.path.exists(PATCH_EMU_GIT_DIR):
        try:
            shutil.rmtree(PATCH_EMU_GIT_DIR)
            log("patch_emu_git_deleted", "success", path=PATCH_EMU_GIT_DIR)
        except Exception as e:
            log("delete_failed", "error", path=f"{PATCH_EMU_GIT_DIR} ({e})")
            return

    ensure_dir(PATCH_EMU_GIT_DIR)

    # Streamboard Repo klonen
    code = run_bash(f"git clone {STREAMREPO} .", cwd=PATCH_EMU_GIT_DIR, logger=log)
    if code != 0:
        log("patch_emu_git_clone_failed", "error")
        return

    # Patch anwenden
    code = run_bash(f"git apply --whitespace=fix {PATCH_FILE}", cwd=PATCH_EMU_GIT_DIR, logger=log)
    if code != 0:
        log("patch_emu_git_apply_failed", "error")
        return

    # Git user config setzen
    cfg = load_github_config()
    run_bash(f'git config user.name "{cfg.get("user_name","speedy005")}"', cwd=PATCH_EMU_GIT_DIR, logger=log)
    run_bash(f'git config user.email "{cfg.get("user_email","patch@oscam.local")}"', cwd=PATCH_EMU_GIT_DIR, logger=log)

    # Commit erstellen
    commit_msg = f"Sync patch {get_patch_header().splitlines()[0]}"
    run_bash(f'git commit -am "{commit_msg}" --allow-empty', cwd=PATCH_EMU_GIT_DIR, logger=log)

    log("patch_emu_git_applied", "success", commit_msg=commit_msg)

    if progress_callback:
        progress_callback(100)

# ===================== GITHUB CONFIG =====================
GITHUB_CONF_FILE = os.path.join(PLUGIN_DIR, "github_upload_config.json")

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
        except: return {}
    return {}

def save_github_config(cfg):
    try: json.dump(cfg, open(GITHUB_CONF_FILE, "w"))
    except: pass

# ===================== GITHUB UPLOAD =====================
def _github_upload(dir_path, repo_url, info_widget=None, branch="master", commit_msg="Apply OSCam Emu Patch"):
    logger = lambda text, level="info": self.append_info(info_widget, text, level)

    cfg = load_github_config()
    username, token = cfg.get("username"), cfg.get("token")
    user_name = cfg.get("user_name", "").strip()
    user_email = cfg.get("user_email", "").strip()

    # Prüfen ob alles vorhanden
    if not all([username, token, user_name, user_email]):
        self.append_info(info_widget, TEXTS[LANG]["github_emu_credentials_missing"], "error")
        return

    if not os.path.exists(dir_path):
        self.append_info(info_widget, TEXTS[LANG]["patch_emu_git_missing"], "error")
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
    self.append_info(
        info_widget, 
        TEXTS[LANG]["github_upload_success"] if code == 0 else TEXTS[LANG]["github_upload_failed"],
        "success" if code == 0 else "error"
    )

# ===================== GITHUB UPLOAD PATCH FILE =====================
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QTextCursor
import shutil, os

def github_upload_patch_file(info_widget=None, progress_callback=None):
    """
    Lädt die Patch-Datei auf GitHub hoch.
    Die Patch-Datei wird immer überschrieben.
    Meldungen erscheinen im Infoscreen oder Terminal.
    """
    # Widget für Infos
    widget = info_widget

    # Logger mit Übersetzungen
    def log(text_key, level="info", **kwargs):
        colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
        color = colors.get(level, "gray")
        text_template = TEXTS[LANG].get(text_key, text_key)
        text = text_template.format(**kwargs)
        if isinstance(widget, QTextEdit):
            widget.append(f'<span style="color:{color}">{text}</span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()
        else:
            print(f"[{level.upper()}] {text}")

    cfg = load_github_config()
    repo_url, branch = cfg.get("repo_url"), cfg.get("branch", "master")
    username, token = cfg.get("username"), cfg.get("token")
    user_name, user_email = cfg.get("user_name"), cfg.get("user_email")

    # Prüfen ob Zugangsdaten vorhanden sind
    if not all([repo_url, username, token, user_name, user_email]):
        log("github_patch_credentials_missing", "error")
        if progress_callback:
            progress_callback(0)
        return

    # Prüfen ob Patch-Datei existiert
    if not os.path.exists(PATCH_FILE):
        log("patch_file_missing", "error")
        if progress_callback:
            progress_callback(0)
        return

    temp_repo = os.path.join(PLUGIN_DIR, "temp_patch_git")

    # Temp-Repo löschen, falls vorhanden
    if os.path.exists(temp_repo):
        try:
            shutil.rmtree(temp_repo)
            log("temp_repo_deleted", "info", path=temp_repo)
        except Exception as e:
            log("delete_failed", "error", path=f"{temp_repo} ({e})")
            return

    os.makedirs(temp_repo, exist_ok=True)

    # Repo klonen mit Token
    token_url = repo_url.replace("https://", f"https://{username}:{token}@")
    code = run_bash(f"git clone --branch {branch} {token_url} {temp_repo}", logger=log)
    if code != 0:
        log("github_clone_failed", "error")
        if progress_callback:
            progress_callback(0)
        return

    # Alte Patch-Datei überschreiben
    patch_path = os.path.join(temp_repo, "oscam-emu.patch")
    shutil.copy2(PATCH_FILE, patch_path)
    log("new_patch_copied", "info")

    # Git Username & Email setzen
    run_bash(f'git config user.name "{user_name}"', cwd=temp_repo, logger=log)
    run_bash(f'git config user.email "{user_email}"', cwd=temp_repo, logger=log)

    # Git add & commit
    run_bash("git add oscam-emu.patch", cwd=temp_repo, logger=log)
    with open(PATCH_FILE, "r", encoding="utf-8") as f:
        commit_msg = f.readline().strip() or TEXTS[LANG].get("default_commit_msg", "Update oscam-emu.patch")
    run_bash(f'git commit -m "{commit_msg}" --allow-empty', cwd=temp_repo, logger=log)

    # Push erzwingen
    run_bash(f"git push --force origin {branch}", cwd=temp_repo, logger=log)
    log("github_patch_uploaded", "success")

    # Temp-Repo bereinigen
    try:
        shutil.rmtree(temp_repo)
        log("temp_repo_cleaned", "info", path=temp_repo)
    except Exception as e:
        log("temp_repo_cleanup_failed", "warning", path=f"{temp_repo} ({e})")

    if progress_callback:
        progress_callback(100)

# ===================== GITHUB UPLOAD OSCAM-EMU FOLDER =====================
def github_upload_oscam_emu_folder(info_widget=None, progress_callback=None):
    """
    Lädt den gesamten Inhalt des OSCam-EMU-Git-Ordners auf GitHub hoch.
    Alte Dateien werden überschrieben.
    Meldungen werden ins Info-Widget geschrieben oder auf die Konsole.
    """
    widget = info_widget

    # Logger mit Übersetzungen
    def log(text_key, level="info", **kwargs):
        colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
        color = colors.get(level, "gray")

        text_template = TEXTS[LANG].get(text_key, text_key)
        text = text_template.format(**kwargs)

        if isinstance(widget, QTextEdit):
            widget.append(f'<span style="color:{color}">{text}</span>')
            widget.moveCursor(QTextCursor.MoveOperation.End)
            QApplication.processEvents()
        else:
            print(f"[{level.upper()}] {text}")

    cfg = load_github_config()
    repo_url, branch = cfg.get("emu_repo_url"), cfg.get("emu_branch", "master")
    username, token = cfg.get("username"), cfg.get("token")
    user_name, user_email = cfg.get("user_name"), cfg.get("user_email")

    if not all([repo_url, branch, username, token, user_name, user_email]):
        log("github_emu_git_missing", "error")
        if progress_callback: progress_callback(0)
        return

    if not os.path.exists(PATCH_EMU_GIT_DIR):
        log("patch_emu_git_missing", "error", path=PATCH_EMU_GIT_DIR)
        if progress_callback: progress_callback(0)
        return

    token_url = repo_url.replace("https://", f"https://{username}:{token}@")
    git_dir = os.path.join(PATCH_EMU_GIT_DIR, ".git")

    if not os.path.exists(git_dir):
        log("git_repo_init", "warning", path=PATCH_EMU_GIT_DIR)
        run_bash("git init", cwd=PATCH_EMU_GIT_DIR, logger=log)
        run_bash(f"git remote add origin {token_url}", cwd=PATCH_EMU_GIT_DIR, logger=log)
        run_bash(f"git checkout -b {branch}", cwd=PATCH_EMU_GIT_DIR, logger=log)
    else:
        run_bash(f"git remote remove origin || true", cwd=PATCH_EMU_GIT_DIR, logger=log)
        run_bash(f"git remote add origin {token_url}", cwd=PATCH_EMU_GIT_DIR, logger=log)
        run_bash(f"git fetch origin {branch}", cwd=PATCH_EMU_GIT_DIR, logger=log)
        run_bash(f"git checkout {branch}", cwd=PATCH_EMU_GIT_DIR, logger=log)

    run_bash(f'git config user.name "{user_name}"', cwd=PATCH_EMU_GIT_DIR, logger=log)
    run_bash(f'git config user.email "{user_email}"', cwd=PATCH_EMU_GIT_DIR, logger=log)

    run_bash("git add .", cwd=PATCH_EMU_GIT_DIR, logger=log)
    commit_msg = get_patch_header().splitlines()[0]
    run_bash(f'git commit -m "Sync OSCam-Emu folder {commit_msg}" --allow-empty', cwd=PATCH_EMU_GIT_DIR, logger=log)
    run_bash(f"git push --force origin {branch}", cwd=PATCH_EMU_GIT_DIR, logger=log)

    log("github_emu_git_uploaded", "success")
    if progress_callback:
        progress_callback(100)

# =====================
# GITHUB CONFIG DIALOG
# =====================
class GithubConfigDialog(QDialog):
    """Dialog for entering GitHub credentials"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle(TEXTS[LANG]["github_dialog_title"])
        self.setMinimumWidth(520)
        layout = QFormLayout(self)

        # Eingabefelder
        self.patch_repo = QLineEdit()
        self.patch_branch = QLineEdit("master")
        self.emu_repo = QLineEdit()
        self.emu_branch = QLineEdit("master")
        self.username = QLineEdit()
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.user_name = QLineEdit("speedy005")
        self.user_email = QLineEdit("patch@oscam.local")

        # Lade bestehende Konfiguration
        cfg = load_github_config()
        self.patch_repo.setText(cfg.get("repo_url", ""))
        self.patch_branch.setText(cfg.get("branch", "master"))
        self.emu_repo.setText(cfg.get("emu_repo_url", ""))
        self.emu_branch.setText(cfg.get("emu_branch", "master"))
        self.username.setText(cfg.get("username", ""))
        self.token.setText(cfg.get("token", ""))
        self.user_name.setText(cfg.get("user_name", "speedy005"))
        self.user_email.setText(cfg.get("user_email", "patch@oscam.local"))

        # Layout Labels + Felder
        layout.addRow(TEXTS[LANG]["patch_repo_label"], self.patch_repo)
        layout.addRow(TEXTS[LANG]["patch_branch_label"], self.patch_branch)
        layout.addRow(TEXTS[LANG]["emu_repo_label"], self.emu_repo)
        layout.addRow(TEXTS[LANG]["emu_branch_label"], self.emu_branch)
        layout.addRow(TEXTS[LANG]["github_username_label"], self.username)
        layout.addRow(TEXTS[LANG]["github_token_label"], self.token)
        layout.addRow(TEXTS[LANG]["github_user_name_label"], self.user_name)
        layout.addRow(TEXTS[LANG]["github_user_email_label"], self.user_email)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save_btn.setText(TEXTS[LANG]["save"])
        cancel_btn.setText(TEXTS[LANG]["cancel"])

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Referenzen speichern
        self.save_button = save_btn
        self.cancel_button = cancel_btn
        self.update_language()  # Sprache direkt beim Erstellen setzen

    def update_language(self):
        self.setWindowTitle(TEXTS[LANG]["github_dialog_title"])
        self.save_button.setText(TEXTS[LANG]["save"])
        self.cancel_button.setText(TEXTS[LANG]["cancel"])
        # Labels neu setzen, falls nötig

    def save(self):
        cfg = {
            "repo_url": self.patch_repo.text().strip(),
            "branch": self.patch_branch.text().strip(),
            "emu_repo_url": self.emu_repo.text().strip(),
            "emu_branch": self.emu_branch.text().strip(),
            "username": self.username.text().strip(),
            "token": self.token.text().strip(),
            "user_name": self.user_name.text().strip(),
            "user_email": self.user_email.text().strip()
        }
        save_github_config(cfg)
        self.accept()

 # =====================
# PATCH MANAGER GUI
# =====================
class PatchManagerGUI(QWidget):
    BUTTON_HEIGHT = 60
    BUTTON_WIDTH = 120   
    BUTTON_RADIUS = 10   

    def update_all_texts(self):
        # Labels
        self.lang_label.setText(TEXTS[self.LANG]["language_label"])
        self.color_label.setText(TEXTS[self.LANG]["color_label"])
        self.commit_label.setText(TEXTS[self.LANG]["commit_count_label"])
        self.info_button.setToolTip(TEXTS[self.LANG]["info_tooltip"])

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


    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.LANG = self.cfg.get("language", "DE").lower()  # "de" oder "en"
        if self.LANG not in ["en", "de"]:
            self.LANG = "en"
        # Patch-Pfade
        self.OLD_PATCH_DIR = self.cfg.get("s3_patch_path", OLD_PATCH_DIR_DEFAULT)
        self.OLD_PATCH_FILE = os.path.join(self.OLD_PATCH_DIR, "oscam-emu.patch")
        self.ALT_PATCH_FILE = os.path.join(self.OLD_PATCH_DIR, "oscam-emu.altpatch")

        # Buttons & Status
        self.all_buttons = []
        self.option_buttons = {}
        self.buttons = {}
        self.active_button_key = ""
        self.latest_version = None

        # UI einmal aufbauen
        self.init_ui()

        # GitHub / Update
        self.fetch_latest_version()
        self.update_plugin_button_state()
        QTimer.singleShot(1000, self.check_for_updates_on_start)
    # ---------------------
    @staticmethod
    def append_info(info_widget, text, level="info"):
        """
        Schreibt eine Nachricht in ein QTextEdit mit farblicher Kennzeichnung.
        Scrollt automatisch ans Ende.
        Kann auch außerhalb von GUI-Instanzen benutzt werden.
        """
        if info_widget is None:
            # Fallback, falls kein Widget übergeben wurde
            print(f"[{level.upper()}] {text}")
            return

        # Farben definieren
        colors = {
            "success": "green",
            "warning": "orange",
            "error": "red",
            "info": "gray"
       }

        # Hier unbedingt die Variable 'level' verwenden, die als Parameter übergeben wird
        color = colors.get(level, "black")

        # Nachricht als HTML formatieren (farblich)
        html_text = f'<span style="color:{color}">{text}</span>'
    
        # Text einfügen
        info_widget.append(html_text)

        # Scroll automatisch ans Ende
        scroll_bar = info_widget.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    @staticmethod
    def adjust_color(hex_color, factor):
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))  # <-- hier factor statt verticalScrollBarfactor
        b = max(0, min(255, int(b * factor)))
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def get_patch_header(repo_dir=None):
        if repo_dir is None:
            repo_dir = TEMP_REPO

        # Standardwerte
        version = "2.26.01"
        build = "0"
        commit = "N/A"

        # globals.h auslesen
        globals_path = os.path.join(repo_dir, "globals.h")
        if os.path.exists(globals_path):
            for line in open(globals_path):
                if line.startswith("#define CS_VERSION"):
                    parts = line.strip().split('"')
                    if len(parts) >= 2:
                        version = parts[1].split("-")[0]
                        build = parts[1].split("-")[1] if "-" in parts[1] else "0"

        # Git-Commit auslesen
        if os.path.exists(os.path.join(repo_dir, ".git")):
            try:
                commit = subprocess.getoutput(f"git -C {repo_dir} rev-parse --short HEAD").strip()
            except:
                pass

        modified_date = datetime.now().strftime("%d/%m/%Y")
        patch_date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC (+00:00)")

        header = (
            f"patch version: oscam-emu-patch {version}-{build}-({commit})\n"
            f"patch modified by {PATCH_MODIFIER} ({modified_date})\n"
            f"patch date: {patch_date_utc}"
        )
        return header
    
    def restart_application_with_info(self, checked=False, progress_callback=None, info_widget=None):
        """
        Startet das Tool neu mit optionaler Info-Ausgabe im Widget.
        """
        widget = info_widget or getattr(self, "info_text", None)

        msg = QMessageBox(self)
        msg.setWindowTitle(TEXTS[LANG].get("restart_tool", "Tool Neustarten"))
        msg.setText(TEXTS[LANG].get("restart_tool_question", "Möchten Sie das Tool wirklich neu starten?"))

        yes_button = msg.addButton(TEXTS[LANG].get("yes", "Ja"), QMessageBox.ButtonRole.YesRole)
        no_button = msg.addButton(TEXTS[LANG].get("no", "Nein"), QMessageBox.ButtonRole.NoRole)
        msg.exec()

        # Lokaler Logger
        def log(text_key, level="info", **kwargs):
            colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
            color = colors.get(level, "gray")

            text_template = TEXTS[LANG].get(text_key, text_key)
            text = text_template.format(**kwargs)

            if isinstance(widget, QTextEdit):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.MoveOperation.End)
                QApplication.processEvents()
            else:
                print(f"[{level.upper()}] {text}")
    
        if msg.clickedButton() == yes_button:
            log("restart_tool_info", "info")  # ⚠️ Tool wird neu gestartet...
            self.restart_application()
        else:
            log("restart_tool_cancelled", "info")  # ℹ️ Neustart abgebrochen
    
        if progress_callback:
            progress_callback(100)

    # ===================== ZIP PATCH =====================
    def zip_patch(self, info_widget=None, progress_callback=None):
        info_widget = info_widget or self.info_text
        try:
            with zipfile.ZipFile(ZIP_FILE, 'w') as zipf:
                zipf.write(PATCH_FILE, os.path.basename(PATCH_FILE))
            PatchManagerGUI.append_info(info_widget, f"✅ Patch erfolgreich gezippt: {ZIP_FILE}", "success")
        except Exception as e:
            PatchManagerGUI.append_info(info_widget, f"❌ Fehler beim Zippen: {str(e)}", "error")
        if progress_callback:
            progress_callback(100)  
    

    def run_command(self, cmd, cwd=None):
        self.append_info(self.info_text, f"▶ {cmd}", "info")

        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            self.append_info(self.info_text, line.strip(), "info")

        process.wait()
        return process.returncode


    def log(self, msg, level='info'):
        colors = {
            'info': THEME['text'],
            'success': THEME['success'],
            'warning': THEME['warning'],
            'error': THEME['error']
        }
        self.info_text.setTextColor(QColor(colors.get(level, THEME['text'])))
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

        python = sys.executable               # Python-Interpreter
        script = os.path.abspath(__file__)    # Pfad zur aktuellen .py-Datei
        args_list = sys.argv                   # alle übergebenen Args übernehmen

        # Neues Tool starten
        subprocess.Popen([python, script] + args_list[1:])

        # Aktuelles Tool sauber beenden
        QApplication.quit()

    def commit_value_changed(self, value):
        self.cfg["commit_count"] = value  # nur im Dict speichern
        self.append_info(self.info_text, f"Commit-Anzahl auf {value} gesetzt", "success")

    def change_old_patch_dir(self, info_widget=None, progress_callback=None):
        """
        Ändert den Speicherort des alten Patch-Ordners.
        Meldungen werden ins Info-Widget geschrieben oder auf die Konsole.
        """
        # Fallback auf Widget
        widget = info_widget or getattr(self, "info_text", None)

        # Logger-Funktion
        def log(text, level="info"):
            colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
            color = colors.get(level, "gray")
            if widget and hasattr(self, "append_info"):
                self.append_info(widget, text, level)
            elif widget and hasattr(widget, "append") and hasattr(widget, "moveCursor"):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.End)
            else:
                print(f"[{level.upper()}] {text}")

        # QFileDialog öffnen, Ausgangsordner = aktueller Pfad
        start_dir = getattr(self, "OLD_PATCH_DIR", OLD_PATCH_DIR_DEFAULT)
        new_dir = QFileDialog.getExistingDirectory(self, "Select S3 Patch Folder", start_dir)

        if new_dir:
            # Instanzvariablen setzen
            self.OLD_PATCH_DIR = new_dir
            self.OLD_PATCH_FILE = os.path.join(new_dir, "oscam-emu.patch")
            self.ALT_PATCH_FILE = os.path.join(new_dir, "oscam-emu.altpatch")
            self.PATCH_MANAGER_OLD = os.path.join(new_dir, "oscam_patch_manager_old.py")
            self.CONFIG_OLD = os.path.join(new_dir, "config_old.json")
            self.GITHUB_CONFIG_OLD = os.path.join(new_dir, "github_upload_config_old.json")

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
        "restart_tool_button": "restart_tool",
        "edit_header_button": "edit_patch_header",
        "commits_button": "commits_button"
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
        for w in [getattr(self, "lang_label", None),
                  getattr(self, "color_label", None),
                  getattr(self, "language_box", None),
                  getattr(self, "color_box", None)]:
            if w:
                w.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']};")

        for btn in [getattr(self, "edit_header_button", None),
                    getattr(self, "commits_button", None),
                    getattr(self, "clean_emu_button", None),
                    getattr(self, "patch_emu_git_button", None),
                    getattr(self, "github_upload_patch_button", None),
                    getattr(self, "github_upload_emu_button", None),
                    getattr(self, "github_emu_config_button", None),
                    getattr(self, "plugin_update_button", None),
                    getattr(self, "restart_tool_button", None)]:
            if btn:
                btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;")

        for btn in getattr(self, "buttons", {}).values():
            if btn:
                btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;")

        if hasattr(self, "commit_label") and self.commit_label:
            self.commit_label.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; padding:4px;")
        if hasattr(self, "commit_spin") and self.commit_spin:
            self.commit_spin.setStyleSheet(f"""
                QSpinBox {{
                    background-color:{current_diff_colors['bg']};
                    color:{current_diff_colors['text']};
                    border:1px solid {current_diff_colors['text']};
                    border-radius:6px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    background-color:{current_diff_colors['bg']};
                }}
            """)
        if hasattr(self, "progress") and self.progress:
            self.progress.setStyleSheet(f"QProgressBar::chunk {{background-color:{current_diff_colors['bg']};}}")

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
        patch_content = ""  # Variable immer definieren
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
        editor.setWindowTitle("Patch Header bearbeiten")
        editor.resize(800, 600)
        layout = QVBoxLayout(editor)

        text_edit = QTextEdit()
        text_edit.setFont(QFont("Courier", 12))
        text_edit.setText(patch_content)
        layout.addWidget(text_edit)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

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

        buttons.accepted.connect(save_and_close)
        buttons.rejected.connect(cancel_and_close)

        editor.exec()
    
        def save_patch():
            try:
               with open(PATCH_FILE, "w", encoding="utf-8") as f:
                f.write(text_edit.toPlainText())
                self.append_info(info_widget, "✅ Patch-Datei gespeichert", "success")
                editor.accept()
            except Exception as e:
             self.append_info(info_widget, f"❌ Fehler beim Speichern: {e}", "error")

        # Buttons verbinden
        buttons.accepted.connect(save_patch)
        buttons.rejected.connect(editor.reject)

        # Dialog modal anzeigen
        editor.exec()

        # Optional: Fortschritt auf 100% setzen
        if progress_callback:
            progress_callback(100)

        # ---------------------
        # PLUGIN UPDATE
        # ---------------------
    
    def update_plugin_button_state(self):
        from packaging.version import Version, InvalidVersion
        if not hasattr(self, "plugin_update_button"):
            return
        if not getattr(self, "latest_version", None):
            return

        try:
            lv = Version(self.latest_version.strip().lstrip("v"))
            cv = Version(APP_VERSION.strip().lstrip("v"))

            if lv <= cv:
                self.plugin_update_button.setEnabled(False)
                self.plugin_update_button.setText(f"{TEXTS[LANG]['plugin_update']} ✅")
            else:
                self.plugin_update_button.setEnabled(True)
                self.plugin_update_button.setText(TEXTS[LANG]['plugin_update'])

        except InvalidVersion:
            self.plugin_update_button.setEnabled(True)
            self.plugin_update_button.setText(TEXTS[LANG]['plugin_update'])



    
    def plugin_update_action(self, latest_version=None, progress_callback=None):
        """
        Prüft die Version, sichert alte Dateien, lädt das neue Plugin herunter
        und bietet einen Neustart an. Meldungen erscheinen im Info-Widget.
        """
        from packaging.version import Version, InvalidVersion
        import os, shutil, requests

        widget = getattr(self, "info_text", None)

        def log(text_key, level="info", **kwargs):
            colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
            color = colors.get(level, "gray")
            text_template = TEXTS[LANG].get(text_key, text_key)
            text = text_template.format(**kwargs)
            if isinstance(widget, QTextEdit):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.MoveOperation.End)
                QApplication.processEvents()
            else:
                print(f"[{level.upper()}] {text}")

        # 🔹 ⚡ Cache-Cleanup am Start (alte .pyc / __pycache__)
        try:
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            pyc_file = os.path.join(plugin_dir, "oscam_patch_manager.pyc")
            cache_dir = os.path.join(plugin_dir, "__pycache__")

            if os.path.exists(pyc_file):
                os.remove(pyc_file)
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
        except Exception as e:
            log("update_fail", "warning", error=f"Cache cleanup failed: {e}")

        # 🔹 Version prüfen
        if latest_version:
            try:
                lv = Version(latest_version.strip().lstrip("v"))
                cv = Version(APP_VERSION.strip().lstrip("v"))
                if lv <= cv:
                    log("update_current_version", "success", version=latest_version)
                    if progress_callback:
                        progress_callback(100)
                    return
            except InvalidVersion:
                log("update_fail", "error", error=f"Invalid version detected: '{latest_version}'")
                if progress_callback:
                    progress_callback(100)
                return

        log("update_started", "info")

        try:
            backup_dir = os.path.join(plugin_dir, "backup_old")
            os.makedirs(backup_dir, exist_ok=True)

            # 🔹 Alte Dateien sichern
            for fname in ["oscam_patch_manager.py", "config.json", "github_upload_config.json", "oscam-emu.patch"]:
                src = os.path.join(plugin_dir, fname)
                if os.path.exists(src):
                    shutil.copy(src, os.path.join(backup_dir, fname))
                    log("backup_created", "success", file=fname)

            # 🔹 Neue Plugin-Datei herunterladen
            url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/oscam_patch_manager.py"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()

            plugin_file = os.path.join(plugin_dir, "oscam_patch_manager.py")
            tmp_file = plugin_file + ".tmp"

            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(resp.text)

            os.replace(tmp_file, plugin_file)  # Atomic Write

            log("update_success", "success", version=latest_version or "")

            # 🔹 interner Status → verhindert Endlosschleife
            self.latest_version = APP_VERSION

            # 🔹 Neustart-Abfrage
            msg = QMessageBox(self)
            msg.setWindowTitle(TEXTS[LANG].get("restart_required_title", "Restart required"))
            msg.setText(TEXTS[LANG].get("restart_required_msg", "The tool must be restarted. Restart now?"))
            yes_button = msg.addButton(TEXTS[LANG].get("yes", "Yes"), QMessageBox.ButtonRole.YesRole)
            no_button = msg.addButton(TEXTS[LANG].get("no", "No"), QMessageBox.ButtonRole.NoRole)
            msg.exec()

            if msg.clickedButton() == yes_button:
                log("restart_tool_info", "info")
                self.restart_application()
            else:
                log("restart_tool_cancelled", "info")

        except Exception as e:
            log("update_fail", "error", error=str(e))

        if progress_callback:
            progress_callback(100)






    def fetch_latest_version(self):
        """Ruft die Version aus oscams_patch_manager.py auf GitHub ab und speichert sie in self.latest_version."""
        import requests, re

        widget = getattr(self, "info_text", None)

        def log(text_key, level="info", **kwargs):
            colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
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
            url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/oscam_patch_manager.py"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()

            match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', resp.text)
            if not match:
                raise RuntimeError("APP_VERSION not found on GitHub")

            latest = match.group(1)
            self.latest_version = latest

            # Versionsvergleich
            from packaging.version import Version
            if Version(latest) > Version(APP_VERSION):
             log("github_version_available", "info", version=latest)
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

            self.append_info(self.info_text, f"Verfügbare GitHub-Version: v{version}", "info")

            # Button-Zustand aktualisieren
            self.update_plugin_button_state()
            return version

        except Exception as e:
            self.append_info(self.info_text, f"❌ Fehler beim Abrufen der GitHub-Version: {e}", "error")
            self.latest_version = None
            self.update_plugin_button_state()
            return None

    def plugin_update_button_clicked(self, checked=False):
        """Button-Callback: Prüft GitHub-Version und bietet Update an."""
        from packaging.version import Version, InvalidVersion
        import requests, re

        widget = getattr(self, "info_text", None)

        def log(text_key, level="info", **kwargs):
            colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
            color = colors.get(level, "gray")
            text_template = TEXTS[LANG].get(text_key, text_key)
            text = text_template.format(**kwargs)
            if isinstance(widget, QTextEdit):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.MoveOperation.End)
                QApplication.processEvents()
            else:
                print(f"[{level.upper()}] {text}")

        log("update_check_start", "info")

        try:
            url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/oscam_patch_manager.py"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()

            match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', resp.text)
            if not match:
                raise RuntimeError("APP_VERSION not found on GitHub")

            latest_version = match.group(1)

            # 🔹 Safe-Check + Versionsvergleich
            try:
                lv = Version(latest_version.strip().lstrip("v"))
                cv = Version(APP_VERSION.strip().lstrip("v"))
                if lv <= cv:
                    log("update_current_version", "success", version=APP_VERSION)
                    return
            except InvalidVersion:
                log("update_fail", "error", error=f"Invalid version detected: '{latest_version}'")
            return

            # Update verfügbar
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(TEXTS[LANG].get("update_available_title", "Update available"))
            msg_box.setText(TEXTS[LANG].get("update_available_msg", "Version {version} is available.").format(version=latest_version))
            yes_button = msg_box.addButton(TEXTS[LANG].get("yes", "Yes"), QMessageBox.ButtonRole.YesRole)
            no_button = msg_box.addButton(TEXTS[LANG].get("no", "No"), QMessageBox.ButtonRole.NoRole)
            msg_box.exec()

            if msg_box.clickedButton() == yes_button:
                self.plugin_update_action(latest_version=latest_version)
            else:
                log("update_declined", "info")

        except Exception as e:
            log("update_fail", "error", error=str(e))




    # ---------------------
    # UPDATE CHECK
    # ---------------------
    def check_for_updates_on_start(self):
        """
        Prüft beim Start die GitHub-Version und bietet Update an, wenn nötig.
        Meldungen erscheinen im Info-Widget.
        """
        widget = getattr(self, "info_text", None)

        def log(text_key, level="info", **kwargs):
            colors = {"success": "green", "warning": "orange", "error": "red", "info": "gray"}
            color = colors.get(level, "gray")
            text_template = TEXTS[LANG].get(text_key, text_key)
            text = text_template.format(**kwargs)
            if isinstance(widget, QTextEdit):
                widget.append(f'<span style="color:{color}">{text}</span>')
                widget.moveCursor(QTextCursor.MoveOperation.End)
                QApplication.processEvents()
            else:
                print(f"[{level.upper()}] {text}")

        log("update_check_start", "info")

        try:
            import requests

            # GitHub version.txt abrufen
            version_url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/version.txt"
            resp = requests.get(version_url, timeout=10)
            resp.raise_for_status()
            latest_version = resp.text.strip().lstrip("v")  # führendes 'v' entfernen

            current_version = APP_VERSION.strip().lstrip("v")

            if current_version == latest_version:
                log("update_current_version", "success", version=current_version)
                return

            # Update verfügbar
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(TEXTS[LANG].get("update_available_title", "Update verfügbar"))
            msg_box.setText(TEXTS[LANG].get("update_available_msg", f"Neue Version verfügbar: v{latest_version}\nMöchten Sie aktualisieren?"))
            yes_button = msg_box.addButton(TEXTS[LANG].get("yes", "Ja"), QMessageBox.ButtonRole.YesRole)
            no_button = msg_box.addButton(TEXTS[LANG].get("no", "Nein"), QMessageBox.ButtonRole.NoRole)
            msg_box.exec()

            if msg_box.clickedButton() == yes_button:
                self.plugin_update_action(latest_version=latest_version)

                # Optional: Neustart direkt abfragen
                reply = QMessageBox.question(
                    self,
                    TEXTS[LANG].get("restart_required_title", "Tool Neustarten"),
                    TEXTS[LANG].get("restart_required_msg", "Das Tool muss neu gestartet werden. Jetzt neu starten?"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self.restart_application()
                else:
                    log("restart_tool_cancelled", "info")

            else:
                log("update_declined", "info")

        except Exception as e:
            log("update_fail", "error", error=str(e))

    # ---------------------
    # TOOLS CHECK
    # ---------------------
    def check_tool(self, name, cmd):
        try:
            result = subprocess.getoutput(cmd).splitlines()[0]
            if "not found" in result.lower() or "error" in result.lower():
                self.info_text.append(TEXTS[LANG]["tool_missing"].format(name=name, error=result))
            else:
                self.info_text.append(TEXTS[LANG]["tool_ok"].format(name=name, version=result))
        except Exception:
            self.info_text.append(TEXTS[LANG]["tool_missing"].format(name=name, error="Fehler"))

    def check_tools_on_start(self):
        self.info_text.clear()
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
            except Exception as e:
                self.append_info(self.info_text, f"⚠️ Fehler beim Lesen der Config: {e}", "warning")

        tools_ok = cfg.get("tools_ok", False)
        if tools_ok:
            self.append_info(self.info_text, "DEBUG: tools_ok geladen (Toolsprüfung übersprungen)", "info")
            return

        tools = {
            "git": "git --version",
            "patch": "patch --version | head -n 1",
            "zip": "zip -v | head -n 1",
            "python3": "python3 --version",
            "pip3": "pip3 --version"
        }

        all_ok = True
        for name, cmd in tools.items():
            try:
                result = subprocess.getoutput(cmd).splitlines()[0]
                if "not found" in result.lower() or "error" in result.lower():
                    self.append_info(self.info_text, f"⚠️ {name}: {result}", "warning")
                    all_ok = False
                else:
                    self.append_info(self.info_text, f"✅ {name}: {result}", "success")
            except Exception:
                self.append_info(self.info_text, f"⚠️ {name}: Fehler", "warning")
                all_ok = False

        if all_ok:
            self.append_info(self.info_text, TEXTS[LANG]["all_tools_installed"], "success")
            cfg["tools_ok"] = True
            with open(CONFIG_FILE, "w") as f:
                json.dump(cfg, f, indent=2)
            self.append_info(self.info_text, TEXTS[LANG]["tool_saved"], "info")
        else:
            self.append_info(self.info_text, "❌ Einige Tools fehlen oder Fehler aufgetreten", "error")

        # =====================
        # INIT UI
        # =====================
    def init_ui(self):
        self.all_buttons = []  # <- HIER hinzufügen!
        TITLE_HEIGHT = 105
        self.BUTTON_HEIGHT = 40
        self.BUTTON_WIDTH = 120
        self.BUTTON_RADIUS = 10

        layout = QVBoxLayout()
        self.lang_label = QLabel()
        self.color_label = QLabel()
        self.commit_label = QLabel()
        layout.addWidget(self.lang_label)
        layout.addWidget(self.color_label)
        layout.addWidget(self.commit_label)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        self.active_button_key = None

        # -------------------
        # HEADER
        # -------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        header_layout.setContentsMargins(20, 0, 20, 0)

        # Info Button + Uhr links
        self.info_button = QPushButton()
        self.info_button.setFixedSize(60, TITLE_HEIGHT)
        self.info_button.setToolTip(TEXTS[LANG]["info_tooltip"])
        self.info_button.clicked.connect(self.show_info)
        icon = get_icon_for("Info___Hilfe")
        if not icon.isNull():
            self.info_button.setIcon(icon)
            self.info_button.setIconSize(QSize(52, 52))
        else:
            self.info_button.setText("ℹ️")
        self.info_button.setStyleSheet("background-color:#222222;color:white;border:none;")

        self.digital_clock = QLabel()
        self.digital_clock.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.digital_clock.setAlignment(Qt.AlignmentFlag.AlignLeft)

        left_layout = QHBoxLayout()
        left_layout.setSpacing(5)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.info_button)
        left_layout.addSpacing(10)
        left_layout.addWidget(self.digital_clock, stretch=1)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        header_layout.addWidget(left_widget, 1, Qt.AlignmentFlag.AlignLeft)

        # Logo Mitte
        self.logo_label = QLabel()
        logo_height = TITLE_HEIGHT
        logo_width = TITLE_HEIGHT * 10
        self.logo_label.setFixedSize(logo_width, logo_height)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        try:
            url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/oscam_emu_toolkit2.png"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            image_data = BytesIO(resp.content)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data.read())
            self.logo_label.setPixmap(pixmap.scaled(
                logo_width, logo_height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        except Exception:
            self.logo_label.setText("Logo ❌")

        header_layout.addWidget(self.logo_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Version + Autor rechts
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(2)
        right_layout.setContentsMargins(0, 0, 0, 0)
        by_label = QLabel("by speedy005")
        by_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        by_label.setStyleSheet("color:blue;")
        by_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(by_label)

        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        version_label.setStyleSheet("color:red;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(version_label)

        right_widget.setLayout(right_layout)
        header_layout.addWidget(right_widget, 1, Qt.AlignmentFlag.AlignRight)

        layout.addLayout(header_layout)

        # -------------------
        # INFO TEXT
        # -------------------
        self.info_text = QTextEdit()
        self.info_text.setFont(QFont("Courier", 14))
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(400)
        self.info_text.setStyleSheet("background-color:black;color:white;")
        layout.addWidget(self.info_text)

        # -------------------
        # OPTION CONTROLS (Sprache, Farbe, Commits)
        # -------------------
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Sprache
        self.lang_label = QLabel(TEXTS[LANG]["language_label"])
        self.lang_label.setFixedHeight(self.BUTTON_HEIGHT)
        controls_layout.addWidget(self.lang_label)

        self.language_box = QComboBox()
        self.language_box.addItems(["EN", "DE"])
        self.language_box.setFixedHeight(self.BUTTON_HEIGHT)
        self.language_box.setFixedWidth(self.BUTTON_WIDTH)
        self.language_box.setCurrentText(self.cfg.get("language", "DE"))
        self.language_box.currentIndexChanged.connect(self.change_language)
        controls_layout.addWidget(self.language_box)

        # Farbe
        self.color_label = QLabel(TEXTS[LANG]["color_label"])
        self.color_label.setFixedHeight(self.BUTTON_HEIGHT)
        controls_layout.addWidget(self.color_label)

        self.color_box = QComboBox()
        self.color_box.addItems(list(DIFF_COLORS.keys()))
        self.color_box.setFixedHeight(self.BUTTON_HEIGHT)
        self.color_box.setFixedWidth(self.BUTTON_WIDTH)
        self.color_box.setCurrentText(self.cfg.get("color", "Classic"))
        self.color_box.currentIndexChanged.connect(self.change_colors)
        controls_layout.addWidget(self.color_box)

        # Commit Spinbox
        self.commit_label = QLabel(TEXTS[LANG]["commit_count_label"])
        self.commit_label.setFixedHeight(self.BUTTON_HEIGHT)
        controls_layout.addWidget(self.commit_label)

        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1, 20)
        self.commit_spin.setValue(self.cfg.get("commit_count", 5))
        self.commit_spin.setFixedHeight(self.BUTTON_HEIGHT)
        self.commit_spin.setFixedWidth(50)
        self.commit_spin.valueChanged.connect(self.commit_value_changed)
        controls_layout.addWidget(self.commit_spin)

        controls_container = QWidget()
        controls_container.setLayout(controls_layout)
        layout.addWidget(controls_container)

        # -------------------
        # OPTION BUTTONS
        # -------------------
        option_buttons_list = [
            # key, text_key in TEXTS, button color, callback, optional fg
            ("git_status", "git_status", "#1E90FF", self.show_commits),
            ("plugin_update", "plugin_update", "#000000", self.plugin_update_button_clicked, "#FFFFFF"),
            ("restart_tool", "restart_tool", "#000000", self.restart_application_with_info, "#FFFFFF"),
            ("edit_patch_header", "edit_patch_header", "#000000", self.edit_patch_header, "#FFFFFF"),
            ("github_emu_config_button", "github_emu_config_button", "#FFA500", self.edit_emu_github_config, "#000000"),
            ("github_upload_patch", "github_upload_patch", "#1E90FF", github_upload_patch_file),
            ("github_upload_emu", "github_upload_emu", "#1E90FF", github_upload_oscam_emu_folder)
        ]

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.option_buttons = {}

        for key, text_key, color, callback, *rest in option_buttons_list:
            fg = rest[0] if rest else "black"
            btn = self.create_option_button(
                key=key,
                text=TEXTS[self.LANG][text_key],
                color=color,
                fg=fg,
                callback=lambda checked=False, f=callback: f(info_widget=self.info_text, progress_callback=None)
            )
            btn.setMinimumHeight(self.BUTTON_HEIGHT)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            buttons_layout.addWidget(btn)
            self.option_buttons[key] = (btn, text_key)

        controls_container = QWidget()
        controls_container.setLayout(buttons_layout)
        layout.addWidget(controls_container)

        # -------------------
        # -------------------
        # GRID BUTTONS (Patch Aktionen)
        # -------------------
        grid_layout = QGridLayout()
        actions = [
            ("patch_create", lambda: create_patch(self, self.info_text, None)),
            ("patch_renew", lambda: create_patch(self, self.info_text, None)),
            ("patch_check", lambda: self.check_patch(self.info_text, None)),
            ("patch_apply", lambda: self.apply_patch(self.info_text, None)),
            ("patch_zip", lambda: self.zip_patch(self.info_text, None)),
            ("backup_old", lambda: backup_old_patch(self, self.info_text, None)),
            ("clean_folder", lambda: clean_patch_folder(self, self.info_text, None)),
            ("change_old_dir", lambda: self.change_old_patch_dir(self.info_text, None)),
            ("exit", self.close_with_confirm)
        ]
 
        self.buttons = {}
        for idx, (key, func) in enumerate(actions):
            btn = QPushButton(TEXTS[self.LANG][key])  # self.LANG statt global LANG
            btn.setFont(QFont("Arial", 16))
            btn.setMinimumHeight(self.BUTTON_HEIGHT)
            btn.clicked.connect(lambda checked=False, k=key, f=func: (self.set_active_button(k), f()))
            self.buttons[key] = btn
            row, col = divmod(idx, 3)
            grid_layout.addWidget(btn, row, col)

        layout.addLayout(grid_layout)

        # -------------------
        # PROGRESS
        # -------------------
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFixedHeight(22)
        self.progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress)

        # -------------------
        # FINAL
        # -------------------
        self.setLayout(layout)
        self.change_colors()
        self.check_emu_credentials()
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_digital_clock)
        self.clock_timer.start(1000)
        self.update_digital_clock()

    # =====================
    # update_buttons_
    # =====================
    def update_digital_clock(self):
        now = QDateTime.currentDateTime()
        time_str = now.toString("HH:mm:ss")       # Uhrzeit
        date_str = now.toString("dd.MM.yyyy")     # Datum

        # HTML mit Farben: Uhrzeit rot, Datum gelb
        self.digital_clock.setText(
            f'<span style="color:red;">{time_str}</span><br>'
            f'<span style="color:yellow;">{date_str}</span>'
        )

        
    def update_buttons_language(self):
        self.github_upload_patch_button.setText(TEXTS[LANG]["github_upload_patch"])
        self.github_upload_emu_button.setText(TEXTS[LANG]["github_upload_emu"])

    # =====================
    # BUTTON & COLOR HANDLING
    # =====================
    def create_option_button(self, key, text, color, callback, fg="white"):
        btn = QPushButton(text)
        btn.setMinimumHeight(self.BUTTON_HEIGHT)
        btn.setProperty("key", key)
        btn.setStyleSheet(
            f"background-color:{current_diff_colors['bg']}; "
            f"color:{current_diff_colors['text']}; "
            f"border-radius:10px;"
        )

        btn.clicked.connect(callback)  # 🔥 DAS ist der Fix

        self.all_buttons.append(btn)
        return btn

    def on_button_clicked(self, key, func):
        self.set_active_button(key)
        self.run_action(func)

    def set_active_button(self, active_key):
        self.active_button_key = active_key
        for key, btn in self.buttons.items():
            if key == active_key:
                btn.setStyleSheet(f"background-color:#00FF00; color:black; border-radius:{self.BUTTON_RADIUS}px; min-height:{self.BUTTON_HEIGHT}px;")
            else:
                btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:{self.BUTTON_RADIUS}px; min-height:{self.BUTTON_HEIGHT}px;")

    # ---------- change_colors ----------
    def change_colors(self):
        global current_diff_colors, current_color_name

        # Aktuelle Farbe aus ComboBox laden oder aus Config
        current_color_name = self.color_box.currentText() if hasattr(self, "color_box") else self.cfg.get("color", "Classic")
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

    def change_language(self):
        """
        Called when the language dropdown changes.
        Updates self.LANG, refreshes all text labels,
        and saves the choice in config.json.
        """
        selected = self.language_box.currentText()
        self.LANG = "de" if selected == "DE" else "en"  # <-- wichtig: self.LANG

        # ---------- Labels ----------
        label_map = {
            "lang_label": "language_label",
            "color_label": "color_label",
            "commit_label": "commit_count_label"
        }
        for attr, key in label_map.items():
            if hasattr(self, attr) and key in TEXTS[self.LANG]:
                getattr(self, attr).setText(TEXTS[self.LANG][key])

        # ---------- Option Buttons ----------
        for btn, text_key in self.option_buttons.values():
            if text_key in TEXTS[self.LANG]:
                btn.setText(TEXTS[self.LANG][text_key])

        # ---------- Grid Buttons ----------
        for key, btn in getattr(self, "buttons", {}).items():
            if key in TEXTS[self.LANG]:
                btn.setText(TEXTS[self.LANG][key])

        # ---------- Info Text ----------
        if hasattr(self, "info_text") and "info_text" in TEXTS[self.LANG]:
            self.info_text.setPlainText(TEXTS[self.LANG]["info_text"])

        # ---------- Config speichern ----------
        if not hasattr(self, "cfg"):
            self.cfg = load_config()
        self.cfg["language"] = selected
        save_config(self.cfg)

        # Optional: Info-Log
        if hasattr(self, "append_info"):
            self.append_info(self.info_text, f"Language changed to {selected}", "info")

    # =====================
    # GITHUB EMU CREDENTIALS
    # =====================
    def check_emu_credentials(self):
        cfg = load_github_config()
        if not all([cfg.get("emu_repo_url"), cfg.get("username"), cfg.get("token")]):
            self.append_info(self.info_text, "GitHub-Emu-Zugangsdaten fehlen!", "warning")

    def edit_emu_github_config(self, info_widget=None, progress_callback=None):
        """Öffnet den GitHub-Konfigurationsdialog mit Labels aus TEXTS"""
        dialog = GithubConfigDialog()

        # Titel des Dialogs
        dialog.setWindowTitle(TEXTS[LANG]["github_dialog_title"])

        # Labels im Dialog setzen
        form_layout = dialog.layout()
        if isinstance(form_layout, QFormLayout):
            for field, key in [
                (dialog.patch_repo, "patch_repo_label"),
                (dialog.patch_branch, "patch_branch_label"),
                (dialog.emu_repo, "emu_repo_label"),
                (dialog.emu_branch, "emu_branch_label"),
                (dialog.username, "github_username_label"),
                (dialog.token, "github_token_label"),
                (dialog.user_name, "github_user_name_label"),
                (dialog.user_email, "github_user_email_label")
            ]:
                label = form_layout.labelForField(field)
                if label:
                    label.setText(TEXTS[LANG][key])

        # Save/Cancel Buttons übersetzen
        button_box = dialog.findChild(QDialogButtonBox)
        if button_box:
            save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
            cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
            if save_btn:
                save_btn.setText(TEXTS[LANG]["save"])
            if cancel_btn:
                cancel_btn.setText(TEXTS[LANG]["cancel"])

        # Dialog öffnen
        if dialog.exec():  # modal
            self.append_info(self.info_text, TEXTS[LANG]["github_config_saved"])

        # Optional: Fortschritt auf 100%
        if progress_callback:
            progress_callback(100)

    # =====================
    # INFO BUTTON CALLBACK
    # =====================
    def show_info(self):
        text = TEXTS[LANG].get("info_text", "Keine Info verfügbar.")
        dlg = QMessageBox(self)
        dlg.setWindowTitle(TEXTS[LANG].get("info_title", "Info"))
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
        try:
            # Progress starten
            self.progress.setValue(0)
            self.progress.setStyleSheet(
                f"QProgressBar::chunk {{background-color:{current_diff_colors['bg']};}}"
            )

            # Aktion ausführen
            action_func(info_widget=self.info_text, progress_callback=self.progress.setValue)

            # Fortschritt abschließen
            self.progress.setValue(100)

        except Exception as e:
            # Fehler im Info-Widget ausgeben
            self.append_info(self.info_text, f"❌ Fehler: {e}", "error")
            self.progress.setValue(0)

    # =====================
    # BUTTON CALLBACKS
    # =====================
    def show_commits(self, info_widget=None, progress_callback=None):
        """
        Zeigt die letzten Commits an.
        """
        info_widget = info_widget or self.info_text  # Fallback falls None

        # Info-Meldung ausgeben
        self.append_info(info_widget, TEXTS[LANG]["showing_commits"], "info")

        # Git log ausführen
        try:
            cmd = f"git -C {TEMP_REPO} log -n {self.commit_spin.value()} --oneline"
            output = self.run_command(cmd, cwd=TEMP_REPO)
            # Ausgabe im Info-Widget anzeigen
            if output:
                for line in output.splitlines():
                    self.append_info(info_widget, line, "info")
        except Exception as e:
            self.append_info(info_widget, f"❌ Fehler beim Abrufen der Commits: {e}", "error")

        # Fortschrittscallback
        if progress_callback:
            progress_callback(100)

    def check_patch(self, info_widget=None, progress_callback=None):
        info_widget = info_widget or self.info_text  # Fallback falls None

        # Logger für run_bash erstellen
        logger = lambda text, level="info": self.append_info(info_widget, text, level)

        if not os.path.exists(PATCH_FILE):
            self.append_info(info_widget, TEXTS[LANG]["patch_file_missing"], "error")
            return

        # run_bash mit logger aufrufen
        code = run_bash(f"git apply --check {PATCH_FILE}", cwd=TEMP_REPO, logger=logger)

        if code == 0:
            self.append_info(info_widget, TEXTS[LANG]["patch_check_ok"], "success")
        else:
            self.append_info(info_widget, TEXTS[LANG]["patch_check_fail"], "error")

        if progress_callback:
            progress_callback(100)

    def apply_patch(self, info_widget=None, progress_callback=None):
        info_widget = info_widget or self.info_text

        if not os.path.exists(PATCH_FILE):
            self.append_info(info_widget, "❌ Patch-Datei fehlt!", "error")
            return

        # Logger für run_bash
        logger = lambda text, level="info": self.append_info(info_widget, text, level)

        # Patch anwenden
        code = run_bash(f"git apply {PATCH_FILE}", cwd=TEMP_REPO, logger=logger)

        if code == 0:
            self.append_info(info_widget, "✅ Patch erfolgreich angewendet", "success")
        else:
            self.append_info(info_widget, "❌ Patch konnte nicht angewendet werden", "error")

        if progress_callback:
            progress_callback(100)

    def change_old_(self, info_widget=None, progress_callback=None):
        global OLD_, OLD_PATCH_FILE, ALT_PATCH_FILE

        info_widget = info_widget or self.info_text

        new_dir = QFileDialog.getExistingDirectory(
            self,
            TEXTS[LANG]["change_old_dir"],
            OLD_
        )

        if new_dir:
            OLD_ = new_dir
            OLD_PATCH_FILE = os.path.join(OLD_, "oscam-emu.patch")
            ALT_PATCH_FILE = os.path.join(OLD_, "oscam-emu.altpatch")

            save_config(self.commit_spin.value())  # 🔹 GENAU WIE FARBE

            self.append_info(
                info_widget,
                TEXTS[LANG]["old_patch_path_changed"].format(OLD_=OLD_),
                "success"
            )
        else:
            self.append_info(
                info_widget,
                TEXTS[LANG]["old_patch_path_cancelled"],
                "info"
            )

        if progress_callback:
            progress_callback(100)

    def close_with_confirm(self):
        msg = QMessageBox(self)
        msg.setWindowTitle(TEXTS[LANG]["exit"])
        msg.setText(TEXTS[LANG]["exit_question"])
        yes_button = msg.addButton(TEXTS[LANG]["yes"], QMessageBox.ButtonRole.YesRole)
        no_button = msg.addButton(TEXTS[LANG]["no"], QMessageBox.ButtonRole.NoRole)
        msg.exec()
        if msg.clickedButton() == yes_button:
            save_config(self.cfg)  # jetzt sauber, nur beim Beenden
            QApplication.quit()


if __name__ == "__main__":
    import os
    import sys
    from PyQt6.QtWidgets import QApplication
    from oscam_patch_manager import PatchManagerGUI, TEXTS, fill_missing_keys, ensure_dir, PLUGIN_DIR, ICON_DIR, TEMP_REPO, load_config

    # ⚠️ Verhindert Accessibility-Warnungen unter Linux
    os.environ["NO_AT_BRIDGE"] = "1"

    # 1️⃣ Verzeichnisse sicherstellen
    ensure_dir(PLUGIN_DIR)
    ensure_dir(ICON_DIR)
    ensure_dir(TEMP_REPO)

    # 2️⃣ Konfiguration laden
    load_config()

    # 3️⃣ Fehlende TEXTS automatisch ausfüllen
    fill_missing_keys(TEXTS)  # einmalig vor GUI-Start

    # 4️⃣ QApplication erstellen
    app = QApplication(sys.argv)

    # 5️⃣ GUI starten — jetzt wird alles nur einmal initialisiert
    window = PatchManagerGUI()
    window.showMaximized()

    # 6️⃣ Event Loop starten
    sys.exit(app.exec())

    
