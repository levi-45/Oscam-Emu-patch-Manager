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
import os, sys, subprocess, shutil, json, zipfile, time
from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QDialog,
    QLabel,
    QPushButton,
    QLineEdit,
    
QTextEdit,
    QProgressBar,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QMessageBox,
    QDialogButtonBox
)

from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtCore import Qt, QTimer
from PIL import Image, ImageDraw, ImageFont
# ===================== APP CONFIG =====================
APP_VERSION = "1.3.7"
# =====================
# Pfade & Plugin-Konstanten
# =====================
# Aktueller Plugin-Ordner (von dem das Plugin gestartet wird)
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PLUGIN_DIR, "config.json")
GITHUB_CONF_FILE = os.path.join(PLUGIN_DIR, "github_upload_config.json")
PATCH_FILE = os.path.join(PLUGIN_DIR, "oscam-emu.patch")
ICON_DIR = os.path.join(PLUGIN_DIR, "icons")
TEMP_REPO = os.path.join(PLUGIN_DIR, "temp_repo")
PATCH_EMU_GIT_DIR = os.path.join(PLUGIN_DIR, "oscam-emu-git")
ZIP_FILE = os.path.join(PLUGIN_DIR, "oscam-emu.zip")
OLD_PATCH_DIR_DEFAULT = "/opt/s3_neu/support/patches"
OLD__DEFAULT = os.path.join(PLUGIN_DIR, "old_patches")
OLD_ = OLD__DEFAULT
OLD_PATCH_FILE = os.path.join(OLD_, "oscam-emu.patch")
ALT_PATCH_FILE = os.path.join(OLD_, "oscam-emu.altpatch")
PATCH_MANAGER_OLD = os.path.join(OLD_, "oscam_patch_manager_old.py")
CONFIG_OLD = os.path.join(OLD_, "config_old.json")
GITHUB_CONFIG_OLD = os.path.join(OLD_, "github_upload_config_old.json")
CHECK_TOOLS_SCRIPT = os.path.join(PLUGIN_DIR, "check_tools.sh")
# Patch Modifier / Repos (unverändert)
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
    "NeonInferno":      {"bg": "#FF073A", "text": "#FFFFFF"},  
    "LaserLime":        {"bg": "#00FF00", "text": "#000000"},  
    "ElectricSky":      {"bg": "#00FFFF", "text": "#000033"},  
    "CyberOrange":      {"bg": "#FF6F00", "text": "#FFFFFF"},  
    "VividViolet":      {"bg": "#8A2BE2", "text": "#FFFFFF"},  
    "HotPinkBlaze":     {"bg": "#FF1493", "text": "#000000"},  
    "NeonTeal":         {"bg": "#00FFD5", "text": "#001F1F"},  
    "SolarFlare":       {"bg": "#FF4500", "text": "#FFFFFF"},  
    "RadicalRed":       {"bg": "#FF004F", "text": "#FFFFFF"},  
    "LimeShock":        {"bg": "#CCFF00", "text": "#000000"},  
    "ElectricPurple":   {"bg": "#BF00FF", "text": "#FFFFFF"},  
    "AquaPulse":        {"bg": "#00BFFF", "text": "#FFFFFF"},  
    "FlamingMagenta":   {"bg": "#FF00AA", "text": "#FFFFFF"},  
    "HyperOrange":      {"bg": "#FF8800", "text": "#000000"},  
    "GlacialCyan":      {"bg": "#00FFFF", "text": "#003333"},   
    "TurquoiseDream":{"bg": "#002222", "text": "#40E0D0"}
}

current_diff_colors = DIFF_COLORS["Classic"]
current_color_name = "Classic"

# ===================== LANGUAGE =====================
LANG = "de"

TEXTS = {
    "en": {
        "patch_create": "Create Patch",
        "patch_renew": "Renew Patch",
        "patch_check": "Check Patch",
        "patch_apply": "Apply Patch",
        "patch_zip": "Zip Patch",
        "backup_old": "Backup/Renew Patch",
        "clean_folder": "Clean Patch Folder",
        "change_old_dir": "Select S3 Patch Folder",
        "exit": "Exit",
        "exit_question": "Do you really want to close the tool?",
        "yes": "Yes",
        "no": "No",
        "info_tooltip": "Info / Help",
        "info_title": "Information",
        "info_text": "This tool is a complete OSCam Emu Patch Manager.\n\nFeatures: ...",
        "git_status": "View Commits",
        "clean_emu_git": "Clean OSCam Emu Git",
        "patch_emu_git": "Patch OSCam Emu Git",
        "patch_applied_success": "✅ OSCam Emu Git patched successfully ({commit_msg})",
        "patch_created_success": "✅ Patch created: {patch_file}",
        "patch_zipped_success": "📦 Patch zipped: {zip_file}",
        "backup_done": "💾 Patch backed up: {old_}",
        "patch_failed": "❌ Patch failed – base mismatch",
        "not_installed": "is not installed",
        "all_tools_installed": "✅ All required tools installed",
        "cleaning_patch_folder": "🧹 Cleaning folder …",
        "patch_folder_cleaned": "✅ Patch folder cleaned",
        "oscam_emu_git_cleaning": "🧹 Cleaning OSCam Emu Git …",
        "oscam_emu_git_cleaned": "✅ OSCam Emu Git folder cleaned",
        "showing_commits": "🔄 Showing last commits …",
        "commits_done": "✅ Done",
        "github_config_button": "GitHub Configuration",
        "language_label": "Language:",
        "color_label": "Color",
        "patch_check_ok": "Patch fits – everything ok",
        "patch_check_fail": "Patch does not fit – check failed",
        "info_text": "This tool is a complete OSCam Emu Patch Manager.\n\n"
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
                     "⚠️ Note: Only `oscam-emu.patch` is overwritten during patch upload; all other files remain untouched. "
                     "All functions are fully compatible with the GUI progress bar.",
        "patch_apply_success_msg": "Patch successfully applied",
        "patch_apply_fail_msg": "Error applying the patch",
        "github_emu_credentials_missing": "GitHub Emu credentials missing!",
        "old_patch_path_changed": "Path changed: {OLD_}",
        "old_patch_path_cancelled": "Path change cancelled",
        "github_config_saved": "✔ GitHub configuration saved.",
        "patch_repo_label": "Patch Repo URL:",
        "patch_branch_label": "Patch Branch:",
        "emu_repo_label": "Emu Repo URL:",
        "emu_branch_label": "Emu Branch:",
        "github_username_label": "GitHub Username:",
        "github_token_label": "GitHub Token:",
        "github_user_name_label": "Git Username:",
        "github_user_email_label": "Git User Email:",
        "tool_check_title": "Tool Check",
        "tool_ok": "✅ {name}: {version}",
        "tool_missing": "⚠️ {name}: {error}",
        "tool_all_ok": "✅ All required tools installed",
        "tool_debug": "ℹ️ DEBUG: tools_ok loaded (Tool check skipped)",
        "tool_saved": "ℹ️ DEBUG: tools_ok saved",
        "save": "Save",
        "cancel": "Cancel",
        "github_dialog_title": "GitHub Credentials / Repos",
        "old_patch_removed": "Old oscam-emu.patch removed",
        "new_patch_copied": "New oscam-emu.patch copied",
        "patch_uploaded_success": "✅ oscam-emu.patch successfully updated and pushed",
        "patch_emu_git_missing": "Git folder missing!",
        "github_emu_git_uploaded": "✅ OSCam-Emu Git successfully uploaded",
        "github_patch_credentials_missing": "GitHub patch credentials missing!",
        "github_upload_success": "✅ Upload successful",
        "github_upload_patch_button": "Upload Patch File",
        "github_upload_emu_button": "Upload OSCam-Emu Git",
        "github_upload_failed": "❌ Upload failed",
        "github_upload_patch": "Upload Patch File",
        "github_upload_emu": "Upload OSCam-Emu-Git",
        "old_patch_deleted": "Alte Patch-Datei gelöscht",
        "new_patch_copied": "Neue Patch-Datei kopiert",
        "github_patch_uploaded": "Patch erfolgreich hochgeladen",
        "update_check_start": "Checking for plugin updates...",
        "update_available_title": "Update available",
        "update_available_msg": "A new plugin update is available. Do you want to install it now?",
        "update_started": "Update started...",
        "update_success": "Update successful! Please restart the plugin.",
        "update_fail": "Update failed: {error}",
        "update_not_available": "No new version available.",
        "plugin_update": "Plugin Update",
        "restart_required_title": "Restart required",
        "restart_required_msg": "The update was installed successfully.\n\nThe tool must be restarted.\n\nRestart now?",
        "update_success_banner": "✅ Update successful! Version {version} is now running.",
        "rollback_info": "🔄 Backup restored from backup_old.",
        "backup_cleanup_done": "🗑️ Old backups (older than 7 days) deleted.",
        "rollback_no_backup": "⚠️ No backup found to restore!",
        "rollback_success": "🔄 Rollback completed: {files}",
        "rollback_prompt_restart": "Rollback done.\n\nThe tool must be restarted.\n\nRestart now?",
        "patch_file_missing": "Patch file does not exist!"
    },
    "de": {
        "patch_create": "Patch erstellen",
        "patch_renew": "Patch erneuern",
        "patch_check": "Patch prüfen",
        "patch_apply": "Patch anwenden",
        "patch_zip": "Patch zippen",
        "backup_old": "Patch sichern/erneuern",
        "clean_folder": "Patch-Ordner leeren",
        "change_old_dir": "S3 Patch-Ordner auswählen",
        "exit": "Beenden",
        "exit_question": "Möchten Sie das Tool wirklich schließen?",
        "yes": "Ja",
        "no": "Nein",
        "info_tooltip": "Info / Hilfe",
        "info_title": "Information",
        "info_text": "Dieses Tool ist ein umfassender OSCam Emu Patch Manager.\n\nFunktionen: ...",
        "git_status": "Commits anzeigen",
        "clean_emu_git": "OSCam Emu Git bereinigen",
        "patch_emu_git": "OSCam Emu Git patchen",
        "patch_applied_success": "✅ OSCam Emu Git erfolgreich gepatcht ({commit_msg})",
        "patch_created_success": "✅ Patch erstellt: {patch_file}",
        "patch_zipped_success": "📦 Patch gezippt: {zip_file}",
        "backup_done": "💾 Patch gesichert: {old_}",
        "patch_failed": "❌ Patch fehlgeschlagen – Basis stimmt nicht",
        "not_installed": "nicht installiert",
        "all_tools_installed": "✅ Alle benötigten Tools installiert",
        "cleaning_patch_folder": "🧹 Patch-Ordner wird geleert …",
        "patch_folder_cleaned": "✅ Patch-Ordner geleert",
        "oscam_emu_git_cleaning": "🧹 OSCam Emu Git wird bereinigt …",
        "oscam_emu_git_cleaned": "✅ OSCam Emu Git Ordner bereinigt",
        "showing_commits": "🔄 Letzte Commits werden angezeigt …",
        "commits_done": "✅ Fertig",
        "github_config_button": "GitHub Konfiguration",
        "language_label": "Sprache:",
        "color_label": "Farbe",
        "patch_check_ok": "Patch passt – alles ok",
        "patch_check_fail": "Patch passt nicht – Fehler beim Prüfen",
        "patch_apply_success_msg": "Patch erfolgreich angewendet",
        "patch_apply_fail_msg": "Fehler beim Anwenden des Patches",
        "github_emu_credentials_missing": "GitHub-Emu-Zugangsdaten fehlen!",
        "old_patch_path_changed": "Pfad geändert: {OLD_}",
        "old_patch_path_cancelled": "Pfadänderung abgebrochen",
        "github_config_saved": "✔ GitHub-Konfiguration gespeichert.",
        "info_text": "Dieses Tool ist ein umfassender OSCam Emu Patch Manager.\n\n"
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
                     "⚠️ Hinweis: Beim Patch-Upload wird nur `oscam-emu.patch` überschrieben; andere Dateien bleiben unverändert. "
                     "Alle Funktionen sind kompatibel mit der GUI-Progressbar.",
        "patch_repo_label": "Patch Repo URL:",
        "patch_branch_label": "Patch Branch:",
        "emu_repo_label": "Emu Repo URL:",
        "emu_branch_label": "Emu Branch:",
        "github_username_label": "GitHub Benutzername:",
        "github_token_label": "GitHub Token:",
        "github_user_name_label": "Git Benutzername:",
        "github_user_email_label": "Git Benutzer Email:",
        "tool_check_title": "Tool-Check",
        "tool_ok": "✅ {name}: {version}",
        "tool_missing": "⚠️ {name}: {error}",
        "tool_all_ok": "✅ Alle benötigten Tools installiert",
        "tool_debug": "ℹ️ DEBUG: tools_ok geladen (Toolsprüfung übersprungen)",
        "tool_saved": "ℹ️ DEBUG: tools_ok wurde gespeichert",
        "save": "Speichern",
        "cancel": "Abbrechen",
        "github_dialog_title": "GitHub Zugangsdaten / Repos",
        "old_patch_removed": "Alte oscam-emu.patch gelöscht",
        "new_patch_copied": "Neue oscam-emu.patch kopiert",
        "patch_uploaded_success": "✅ oscam-emu.patch erfolgreich erneuert und gepusht",
        "patch_emu_git_missing": "Git-Ordner fehlt!",
        "github_emu_git_uploaded": "✅ OSCam-Emu Git erfolgreich hochgeladen",
        "github_patch_credentials_missing": "GitHub Patch-Zugangsdaten fehlen!",
        "github_upload_success": "✅ Upload erfolgreich",
        "github_upload_failed": "❌ Upload fehlgeschlagen",
        "github_upload_patch_button": "Patch-Datei hochladen",
        "github_upload_emu_button": "OSCam-Emu Git hochladen",
        "old_patch_deleted": "Old patch file deleted",
        "new_patch_copied": "New patch file copied",
        "github_patch_uploaded": "Patch uploaded successfully",
        "github_upload_patch": "Patch hochladen",
        "github_upload_emu": "OSCam-Emu-Git hochladen",
        "update_check_start": "Prüfe auf Plugin Updates...",
        "update_available_title": "Update verfügbar",
        "update_available_msg": "Ein neues Plugin-Update ist verfügbar. Möchten Sie es jetzt installieren?",
        "update_started": "Update wird gestartet...",
        "update_success": "Update erfolgreich! Bitte Plugin neu starten.",
        "update_fail": "Update fehlgeschlagen: {error}",
        "update_not_available": "Keine neue Version verfügbar.",
        "plugin_update": "Plugin Update",
        "restart_required_title": "Neustart erforderlich",
        "update_success_banner": "✅ Update erfolgreich! Version {version} läuft jetzt.",
        "rollback_info": "🔄 Backup aus backup_old wiederhergestellt.",
        "backup_cleanup_done": "🗑️ Alte Backups (älter als 7 Tage) gelöscht.",
        "rollback_no_backup": "⚠️ Kein Backup gefunden zum Wiederherstellen!",
        "rollback_success": "🔄 Rollback erfolgreich: {files}",
        "rollback_prompt_restart": "Rollback durchgeführt.\n\nDas Tool muss neu gestartet werden.\n\nJetzt neu starten?",
        "restart_required_msg": "Das Update wurde erfolgreich installiert.\n\nDas Tool muss neu gestartet werden.\n\nJetzt neu starten?",
        "patch_file_missing": "Patch-Datei existiert nicht!"
    }
}

LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".oscam_patch_manager.lock")

def check_single_instance():
    if os.path.exists(LOCK_FILE):
        QMessageBox.critical(
            None,
            "Already running",
            "The OSCam Patch Manager is already running."
        )
        sys.exit(0)

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def ensure_dir(path):
    """Stellt sicher, dass das Verzeichnis `path` existiert."""
    if not os.path.exists(path):
        os.makedirs(path)


def save_config(self, commit_count_value=None):
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            cfg = json.load(open(CONFIG_FILE, "r"))
        except:
            cfg = {}

    cfg["language"] = LANG
    cfg["color"] = current_color_name
    cfg["commit_count"] = commit_count_value if commit_count_value else commit_count
    cfg["old_patch_dir"] = getattr(self, "old_patch_dir", "/opt/s3_neu/support/patches")  # Fallback

    try:
        json.dump(cfg, open(CONFIG_FILE, "w"), indent=2)
    except:
        pass

# ===================== CONFIG =====================
def load_config():
    global LANG, current_color_name, current_diff_colors, commit_count, old_patch_dir
    commit_count = 10
    old_patch_dir = "/opt/s3_neu/support/patches"  # Standardwert

    if os.path.exists(CONFIG_FILE):
        try:
            cfg = json.load(open(CONFIG_FILE, "r"))
            LANG = cfg.get("language", LANG)
            current_color_name = cfg.get("color", "Classic")
            current_diff_colors = DIFF_COLORS.get(current_color_name, DIFF_COLORS["Classic"])
            commit_count = cfg.get("commit_count", commit_count)
            old_patch_dir = cfg.get("old_patch_dir", old_patch_dir)
        except:
            pass

# ===================== INFOSCREEN =====================
def append_info(info_widget, text, status="info"):
    if not info_widget: return
    symbols = {"info":"ℹ️", "success":"✅", "error":"❌", "warning":"⚠️"}
    colors = {"info":"white","success":"lime","error":"red","warning":"yellow"}
    symbol = symbols.get(status,"")
    color = colors.get(status,"white")
    if not text.startswith(tuple(symbols.values())):
        text = f"{symbol} [{datetime.now().strftime('%H:%M:%S')}] {text}"
    info_widget.setTextColor(QColor(color))
    info_widget.append(text)
    info_widget.moveCursor(QTextCursor.MoveOperation.End)

# ===================== BASH RUNNER =====================
def run_bash(cmd, cwd=None, info_widget=None):
    if info_widget: append_info(info_widget,f"▶ {cmd}","info")
    if cwd: ensure_dir(cwd)
    process = subprocess.Popen(cmd, shell=True, cwd=cwd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        if info_widget: append_info(info_widget, line.strip(), "info")
    process.wait()
    return process.returncode

# ===================== PATCH HEADER =====================
from datetime import datetime
import subprocess
import os

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

    # Patch modified date (festgelegt auf heutiges lokales Datum)
    modified_date = datetime.now().strftime("%d/%m/%Y")

    # Patch date = aktuelles UTC-Datum und Zeit (dynamisch beim Patch-Build)
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
            append_info(info_widget, f"{tool} {TEXTS[LANG]['not_installed']}, versuche zu installieren...", "warning")

            # Installation versuchen (Debian/Ubuntu)
            install_cmd = f"sudo apt update && sudo apt install -y {package}"
            code = run_bash(install_cmd, info_widget=info_widget)

            # Prüfen, ob Installation erfolgreich war
            if shutil.which(tool) is None:
                append_info(info_widget, f"{tool} konnte nicht installiert werden!", "error")
                all_ok = False
            else:
                append_info(info_widget, f"{tool} erfolgreich installiert.", "success")

    # Finaler Check
    missing = [t for t in tools if shutil.which(t) is None]
    if missing:
        append_info(info_widget, f"❌ Folgende Tools fehlen immer noch: {', '.join(missing)}", "error")
    else:
        append_info(info_widget, TEXTS[LANG]['all_tools_installed'], "success")

# ===================== PATCH FUNCTIONS =====================
def create_patch(info_widget=None, progress_callback=None):
    # TEMP_REPO vorbereiten
    os.makedirs(TEMP_REPO, exist_ok=True)
    append_info(info_widget, "🔄 Patch wird erstellt…", "info")
    
    try:
        # Repo clonen falls nicht vorhanden
        if not os.path.exists(os.path.join(TEMP_REPO, ".git")):
            append_info(info_widget, "⚠️ TEMP_REPO existiert noch nicht. Clone wird gestartet…", "warning")
            code = run_bash(f"git clone {STREAMREPO} .", cwd=TEMP_REPO, info_widget=info_widget)
            if code != 0:
                append_info(info_widget, "Clone fehlgeschlagen", "error")
                return
            run_bash(f"git remote add emu-repo {EMUREPO}", cwd=TEMP_REPO, info_widget=info_widget)

        # Repos aktualisieren
        run_bash("git fetch origin", cwd=TEMP_REPO, info_widget=info_widget)
        run_bash("git fetch emu-repo", cwd=TEMP_REPO, info_widget=info_widget)
        run_bash("git checkout master", cwd=TEMP_REPO, info_widget=info_widget)
        run_bash("git reset --hard origin/master", cwd=TEMP_REPO, info_widget=info_widget)

        # Patch-Header erzeugen
        header = get_patch_header()

        # Diff erzeugen
        diff = subprocess.getoutput(f"git -C {TEMP_REPO} diff origin/master..emu-repo/master -- . ':!.github'")
        if not diff.strip():
            diff = "# Keine Änderungen gefunden"

        # Patch-Datei schreiben
        with open(PATCH_FILE, "w") as f:
            f.write(header + "\n" + diff + "\n")

        append_info(info_widget, f"✅ Patch erfolgreich erstellt: {PATCH_FILE}", "success")
    except Exception as e:
        append_info(info_widget, f"❌ Patch-Erstellung fehlgeschlagen: {str(e)}", "error")
    
    if progress_callback:
        progress_callback(100)

# ===================== PATCH BACKUP =====================
def backup_old_patch(info_widget=None, progress_callback=None):
    ensure_dir(OLD_)
    try:
        if os.path.exists(OLD_PATCH_FILE):
            shutil.copy2(OLD_PATCH_FILE, ALT_PATCH_FILE)
        shutil.copy2(PATCH_FILE, OLD_PATCH_FILE)
        append_info(info_widget, TEXTS[LANG]["backup_done"].format(old_=OLD_), "success")
    except Exception as e:
        append_info(info_widget, f"Fehler beim Sichern des Patches: {str(e)}", "error")
    if progress_callback:
        progress_callback(100)

# ===================== ZIP PATCH =====================
def zip_patch(info_widget=None, progress_callback=None):
    try:
        with zipfile.ZipFile(ZIP_FILE,'w') as zipf:
            zipf.write(PATCH_FILE, os.path.basename(PATCH_FILE))
        append_info(info_widget, TEXTS[LANG]["patch_zipped_success"].format(zip_file=ZIP_FILE), "success")
    except Exception as e:
        append_info(info_widget, f"Fehler beim Zippen: {str(e)}", "error")
    if progress_callback:
        progress_callback(100)

# ===================== CLEAN PATCH FOLDER =====================
def clean_patch_folder(info_widget=None, progress_callback=None):
    append_info(info_widget, TEXTS[LANG]["cleaning_patch_folder"], "warning")

    # Nur diese Ordner/Dateien im Plugin-Ordner löschen
    targets = ["temp_repo", "oscam-emu-git", "oscam-emu.zip"]

    for f in targets:
        path = os.path.join(PLUGIN_DIR, f)
        if not os.path.exists(path):
            continue
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except Exception as e:
            append_info(info_widget, f"Fehler beim Löschen {f}: {str(e)}", "error")

    append_info(info_widget, TEXTS[LANG]["patch_folder_cleaned"], "success")
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
def clean_oscam_emu_git(info_widget=None, progress_callback=None):
    append_info(info_widget, TEXTS[LANG]["oscam_emu_git_cleaning"], "warning")
    if os.path.exists(PATCH_EMU_GIT_DIR): shutil.rmtree(PATCH_EMU_GIT_DIR)
    append_info(info_widget, TEXTS[LANG]["oscam_emu_git_cleaned"], "success")
    if progress_callback:
        progress_callback(100)

def patch_oscam_emu_git(info_widget=None, progress_callback=None):
    append_info(info_widget, TEXTS[LANG]["patch_emu_git"] + " …", "info")
    if os.path.exists(PATCH_EMU_GIT_DIR): shutil.rmtree(PATCH_EMU_GIT_DIR)
    ensure_dir(PATCH_EMU_GIT_DIR)
    run_bash(f"git clone {EMUREPO} .", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    run_bash(f"git remote add streamboard {STREAMREPO}", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    run_bash("git fetch --all", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    run_bash("git checkout -B streamboard-master streamboard/master", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    code = run_bash(f"git apply --whitespace=fix {PATCH_FILE}", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    if code != 0:
        append_info(info_widget, TEXTS[LANG]["patch_failed"], "error")
        return
    cfg = load_github_config()
    run_bash(f'git config user.name "{cfg.get("user_name","speedy005")}"', cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    run_bash(f'git config user.email "{cfg.get("user_email","patch@oscam.local")}"', cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    commit_msg=f"Sync patch {get_patch_header().splitlines()[0]}"
    run_bash(f'git commit -am "{commit_msg}" --allow-empty', cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    append_info(info_widget, TEXTS[LANG]["patch_applied_success"].format(commit_msg=commit_msg), "success")
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
    cfg = load_github_config()
    username, token = cfg.get("username"), cfg.get("token")
    user_name = cfg.get("user_name", "").strip()
    user_email = cfg.get("user_email", "").strip()

    # Prüfen ob alles vorhanden
    if not all([username, token, user_name, user_email]):
        append_info(info_widget, TEXTS[LANG]["github_emu_credentials_missing"], "error")
        return

    if not os.path.exists(dir_path):
        append_info(info_widget, TEXTS[LANG]["patch_emu_git_missing"], "error")
        return

    # Token in URL einfügen
    token_url = repo_url.replace("https://", f"https://{username}:{token}@")

    # Alte .git löschen
    git_dir = os.path.join(dir_path, ".git")
    if os.path.exists(git_dir):
        shutil.rmtree(git_dir)

    run_bash("git init", cwd=dir_path, info_widget=info_widget)
    run_bash(f"git remote add origin {token_url}", cwd=dir_path, info_widget=info_widget)
    run_bash(f"git checkout -b {branch}", cwd=dir_path, info_widget=info_widget)

    # Git Config setzen
    run_bash(f'git config user.name "{user_name}"', cwd=dir_path, info_widget=info_widget)
    run_bash(f'git config user.email "{user_email}"', cwd=dir_path, info_widget=info_widget)

    # Alles committen
    run_bash("git add -A", cwd=dir_path, info_widget=info_widget)
    run_bash(f'git commit -m "{commit_msg}" --allow-empty', cwd=dir_path, info_widget=info_widget)

    # Push erzwingen
    code = run_bash(f"git push origin {branch} --force", cwd=dir_path, info_widget=info_widget)

    # Meldung über TEXTS
    append_info(info_widget, 
                TEXTS[LANG]["github_upload_success"] if code==0 else TEXTS[LANG]["github_upload_failed"],
                "success" if code==0 else "error")

# ===================== GITHUB UPLOAD PATCH FILE =====================
def github_upload_patch_file(info_widget=None, progress_callback=None):
    cfg = load_github_config()
    repo_url, branch = cfg.get("repo_url"), cfg.get("branch", "master")
    username, token = cfg.get("username"), cfg.get("token")
    user_name, user_email = cfg.get("user_name"), cfg.get("user_email")

    # Prüfen, ob Zugangsdaten vorhanden sind
    if not all([repo_url, username, token, user_name, user_email]):
        append_info(info_widget, TEXTS[LANG]["github_patch_credentials_missing"], "error")
        if progress_callback:
            progress_callback(0)
        return

    # Prüfen, ob Patch-Datei existiert
    if not os.path.exists(PATCH_FILE):
        append_info(info_widget, TEXTS[LANG]["patch_file_missing"], "error")
        if progress_callback:
            progress_callback(0)
        return

    # Temp-Verzeichnis vorbereiten
    temp_repo = os.path.join(PLUGIN_DIR, "temp_patch_git")
    os.makedirs(temp_repo, exist_ok=True)

    token_url = repo_url.replace("https://", f"https://{username}:{token}@")

    # Repo klonen oder aktualisieren
    if not os.path.exists(os.path.join(temp_repo, ".git")):
        run_bash(f"git clone --branch {branch} {token_url} {temp_repo}", info_widget=info_widget)
    else:
        run_bash("git reset --hard", cwd=temp_repo, info_widget=info_widget)
        run_bash(f"git pull {token_url} {branch}", cwd=temp_repo, info_widget=info_widget)

    # Alte Patch-Datei löschen
    patch_path = os.path.join(temp_repo, "oscam-emu.patch")
    if os.path.exists(patch_path):
        os.remove(patch_path)
        append_info(info_widget, TEXTS[LANG]["old_patch_deleted"], "info")

    # Neue Patch-Datei kopieren
    shutil.copy2(PATCH_FILE, patch_path)
    append_info(info_widget, TEXTS[LANG]["new_patch_copied"], "info")

    # Git Username & Email setzen
    run_bash(f'git config user.name "{user_name}"', cwd=temp_repo, info_widget=info_widget)
    run_bash(f'git config user.email "{user_email}"', cwd=temp_repo, info_widget=info_widget)

    # Git add
    run_bash("git add oscam-emu.patch", cwd=temp_repo, info_widget=info_widget)

    # Commit aus erster Zeile der Patch-Datei
    with open(PATCH_FILE, "r") as f:
        commit_msg = f.readline().strip()
    if commit_msg.lower().startswith("patch version:"):
        commit_msg = commit_msg[len("patch version:"):].strip()

    run_bash(f'git commit -m "{commit_msg}" --allow-empty', cwd=temp_repo, info_widget=info_widget)

    # Push erzwingen
    run_bash(f"git push --force origin {branch}", cwd=temp_repo, info_widget=info_widget)

    append_info(info_widget, TEXTS[LANG]["github_patch_uploaded"], "success")

    if progress_callback:
        progress_callback(100)

# ===================== GITHUB UPLOAD OSCAM-EMU FOLDER =====================
def github_upload_oscam_emu_folder(info_widget=None, progress_callback=None):
    cfg = load_github_config()
    repo_url, branch = cfg.get("emu_repo_url"), cfg.get("emu_branch", "master")
    username, token = cfg.get("username"), cfg.get("token")
    user_name, user_email = cfg.get("user_name"), cfg.get("user_email")

    if not all([repo_url, username, token, user_name, user_email]):
        append_info(info_widget, TEXTS[LANG]["github_emu_git_missing"], "error")
        if progress_callback:
            progress_callback(0)
        return

    if not os.path.exists(PATCH_EMU_GIT_DIR):
        append_info(info_widget, TEXTS[LANG]["patch_emu_git_missing"], "error")
        if progress_callback:
            progress_callback(0)
        return

    # Saubere Commit-Nachricht aus Patch-Header
    header_line = get_patch_header().splitlines()[0]
    if "oscam-emu-patch" in header_line:
        commit_msg = "Sync OSCam-Emu " + header_line.split("oscam-emu-patch", 1)[1].strip()
    else:
        commit_msg = "Sync OSCam-Emu patch"

    # Upload-Funktion, Git Config wird innerhalb gesetzt
    _github_upload(PATCH_EMU_GIT_DIR, repo_url, info_widget, branch, commit_msg)

    append_info(info_widget, TEXTS[LANG]["github_emu_git_uploaded"], "success")

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

    @staticmethod
    def append_info(info_widget, text, level="info"):
        colors = {
            "success": "green",
            "warning": "orange",
            "error": "red",
            "info": "gray"
        }
        color = colors.get(level, "gray")
        info_widget.append(f'<span style="color:{color}">{text}</span>')
    
    # =====================
    # PATCH MANAGER GUI
    # =====================
class PatchManagerGUI(QWidget):
    BUTTON_HEIGHT = 60
    BUTTON_RADIUS = 10

    def __init__(self):
        super().__init__()
        self.active_button_key = ""
        self.init_ui()
        self.check_for_updates_on_start()  # 🔹 automatische Update-Prüfung beim Start
        # 🔹 Wenn das Tool gerade aktualisiert wurde, Banner direkt zeigen
        if "--updated" in sys.argv:
            # latest_version_from_config z.B. aus config.json oder APP_VERSION
            latest_version_from_config = APP_VERSION
            self.show_update_success_banner(latest_version_from_config)
    # ---------------------
    # PATCH HEADER BEARBEITEN
    # ---------------------
    def update_progressbar(self, value):
        if self.update_progress:
            # value muss INT sein
            self.update_progress.setValue(int(value))
    
    def show_update_success_banner(self, version=None):
        """
        Zeigt ein kleines Banner am oberen Fensterrand an, dass die neue Version läuft.
        """
        version = version or APP_VERSION
        banner_text = f"✅ Update erfolgreich – Version {version} läuft"

        # Banner einmalig erstellen
        if not hasattr(self, "update_banner"):
            self.update_banner = QLabel(banner_text, self)
            self.update_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.update_banner.setStyleSheet(
                "background-color: #28a745; color: white; font-weight: bold; padding: 5px; border-radius: 5px;"
            )
            self.update_banner.setFixedHeight(30)

            if self.layout() is not None:
                self.layout().insertWidget(0, self.update_banner)
            else:
                # Fallback: falls init_ui kein Layout gesetzt hat
                layout = QVBoxLayout(self)
                layout.insertWidget(0, self.update_banner)
                self.setLayout(layout)

        else:
            self.update_banner.setText(banner_text)
            self.update_banner.show()

        # Automatisch ausblenden
        QTimer.singleShot(5000, self.update_banner.hide)


    
    def restart_application(self, updated=False):
        """
        Neustart des Tools.
        Wenn `updated=True`, wird das Flag --updated angehängt,
        damit nach dem Neustart das Update-Banner angezeigt wird.
        """
        import subprocess, sys, os
        from PyQt6.QtWidgets import QApplication

        python = sys.executable
        script = os.path.abspath(__file__)
        args_list = sys.argv[1:]  # alle bisherigen Argumente übernehmen

        # 🔹 Falls Update, Flag hinzufügen
        if updated:
            args_list.append("--updated")

        # 1️⃣ Aktuelles Fenster schließen (sanft)
        self.hide()  # self.close() geht auch, hide wirkt sanfter

        # 2️⃣ Neues Plugin sofort starten
        subprocess.Popen([python, script] + args_list)

        # 3️⃣ Aktuelles Tool komplett beenden
        QApplication.quit()


    def restart_application(self, updated=False):
        import subprocess, sys, os
        from PyQt6.QtWidgets import QApplication

        python = sys.executable
        script = os.path.abspath(__file__)
        args_list = sys.argv[1:]

        if updated:
            args_list.append("--updated")

        self.hide()
        subprocess.Popen([python, script] + args_list)
        QApplication.quit()


        # -------------------
        # CLOSE EVENT (Lock entfernen)
        # -------------------
    def closeEvent(self, event):
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except:
            pass
        event.accept()
    
    def edit_patch_header(self):
        try:
            with open(PATCH_FILE, "r", encoding="utf-8") as f:
                patch_content = f.read()
        except Exception as e:
            GithubConfigDialog.append_info(self.info_text, f"Fehler beim Öffnen der Patch-Datei: {e}", "error")
            return

        editor = QDialog(self)
        editor.setWindowTitle("Patch Header bearbeiten")
        editor.resize(800, 600)
        layout = QVBoxLayout(editor)

        text_edit = QTextEdit()
        text_edit.setText(patch_content)
        text_edit.setFont(QFont("Courier", 12))
        layout.addWidget(text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        # lokale Speichern-Funktion
        def save_patch():
            try:
                with open(PATCH_FILE, "w", encoding="utf-8") as f:
                    f.write(text_edit.toPlainText())
                GithubConfigDialog.append_info(self.info_text, "Patch-Datei gespeichert", "success")
                editor.accept()
            except Exception as e:
                GithubConfigDialog.append_info(self.info_text, f"Fehler beim Speichern: {e}", "error")

        buttons.accepted.connect(save_patch)
        buttons.rejected.connect(editor.reject)
        editor.exec()

    # ---------------------
    # PLUGIN UPDATE
    # ---------------------
    def plugin_update_action(self, latest_version=None):
        """
        Führt das Plugin-Update durch:
        - Backup der alten Dateien (.py, config, github config, patch)
        - Download der neuen oscam_patch_manager.py
        - Fortschrittsanzeige in der Progressbar
        - Anzeige eines Success-Banners
        - Update-Log schreiben
        - Optional Neustart des Tools
        """
        try:
            GithubConfigDialog.append_info(self.info_text, TEXTS[LANG]["update_started"], "info")
            plugin_dir = os.path.dirname(os.path.abspath(__file__))

            # -------------------
            # Backup-Ordner erstellen
            # -------------------
            backup_dir = os.path.join(plugin_dir, "backup_old")
            os.makedirs(backup_dir, exist_ok=True)

            # -------------------
            # Alte Dateien sichern
            # -------------------
            backup_files = ["oscam_patch_manager.py", "config.json", "github_upload_config.json", "oscam-emu.patch"]
            total_files = len(backup_files)
            for i, fname in enumerate(backup_files, start=1):
                src = os.path.join(plugin_dir, fname)
                if os.path.exists(src):
                    shutil.copy(src, os.path.join(backup_dir, fname))
                    GithubConfigDialog.append_info(self.info_text, f"Backup erstellt: {fname}", "success")
                # Progressbar aktualisieren (0-30%)
                if hasattr(self, "update_progress"):
                    self.update_progress.setValue(int((i / total_files) * 30))

            # -------------------
            # Alte Backups automatisch bereinigen (>7 Tage)
            # -------------------
            backup_files_list = os.listdir(backup_dir)
            total_old = max(len(backup_files_list), 1)
            for i, f in enumerate(backup_files_list, start=1):
                path = os.path.join(backup_dir, f)
                if os.path.isfile(path):
                    age_days = (time.time() - os.path.getmtime(path)) / 86400
                    if age_days > 7:
                        os.remove(path)
                        GithubConfigDialog.append_info(self.info_text, f"Altes Backup gelöscht: {f}", "info")
                if hasattr(self, "update_progress"):
                    self.update_progress.setValue(30 + int((i / total_old) * 10))  # 30-40%

            # -------------------
            # Neue Plugin-Datei herunterladen
            # -------------------
            import requests
            url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/oscam_patch_manager.py"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
 
            plugin_file = os.path.join(plugin_dir, "oscam_patch_manager.py")
            new_file = plugin_file + ".new"
            with open(new_file, "w", encoding="utf-8") as f:
                f.write(resp.text)

            if hasattr(self, "update_progress"):
                self.update_progress.setValue(50)  # Download abgeschlossen

            # -------------------
            # Update erfolgreich – Banner
            # -------------------
            GithubConfigDialog.append_info(
                self.info_text,
                TEXTS[LANG]["update_success"] + (f" (v{latest_version})" if latest_version else ""),
                "success"
            )
            self.show_update_success_banner(latest_version)

            # -------------------
            # Update-Log
            # -------------------
            GithubConfigDialog.append_info(
                self.info_text,
                f"Update Log: Alte Version gesichert, neue Version v{latest_version} installiert",
                "info"
            )

            # -------------------
            # Rollback Hinweis
            # -------------------
            GithubConfigDialog.append_info(
                self.info_text,
                f"Rollback verfügbar im Backup-Ordner: {backup_dir}",
                "warning"
            )

            if hasattr(self, "update_progress"):
                self.update_progress.setValue(80)  # Update fast fertig

            # -------------------
            # Neustart-Abfrage
            # -------------------
            reply = QMessageBox.question(
                self,
                TEXTS[LANG]["restart_required_title"],
                TEXTS[LANG]["restart_required_msg"],
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.restart_application(updated=True)

            if hasattr(self, "update_progress"):
                self.update_progress.setValue(100)  # Fertig

        except Exception as e:
            GithubConfigDialog.append_info(
                self.info_text,
                TEXTS[LANG]["update_fail"].format(error=str(e)),
                "error"
            )
            if hasattr(self, "update_progress"):
                self.update_progress.setValue(0)  # Fehler -> zurücksetzen




    def rollback_plugin_action(self):
        """
        Rollback des Plugins aus dem Backup-Ordner.
        Stellt die alte .py, config und Patch-Datei wieder her.
        """
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(plugin_dir, "backup_old")

        if not os.path.exists(backup_dir):
            GithubConfigDialog.append_info(self.info_text, "⚠️ Kein Backup gefunden!", "warning")
            return

        # Dateien zurückkopieren
        files_to_restore = ["oscam_patch_manager.py", "config.json", "github_upload_config.json", "oscam-emu.patch"]
        restored_files = []

        for fname in files_to_restore:
            backup_file = os.path.join(backup_dir, fname)
            target_file = os.path.join(plugin_dir, fname)
            if os.path.exists(backup_file):
                shutil.copy(backup_file, target_file)
                restored_files.append(fname)

        if restored_files:
            GithubConfigDialog.append_info(
                self.info_text, f"🔄 Rollback erfolgreich: {', '.join(restored_files)}", "success"
            )
            # Optional: Neustart direkt anbieten
            reply = QMessageBox.question(
                self,
                "Neustart erforderlich",
                "Rollback durchgeführt.\n\nDas Tool muss neu gestartet werden.\n\nJetzt neu starten?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.restart_application()
        else:
            GithubConfigDialog.append_info(self.info_text, "⚠️ Keine Dateien zum Wiederherstellen gefunden!", "warning")

    # ---------------------
    # UPDATE CHECK
    # ---------------------
    def check_for_updates_on_start(self):
        """
        Prüft beim Start die GitHub-Version und bietet Update an, wenn nötig.
        """
        GithubConfigDialog.append_info(self.info_text, TEXTS[LANG]["update_check_start"], "info")

        try:
            import requests

            # URL zur version.txt im GitHub
            version_url = "https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/main/version.txt"
            resp = requests.get(version_url, timeout=10)
            resp.raise_for_status()
            latest_version = resp.text.strip()  # aktuelle Version auf GitHub

            # Lokale Version aus APP_VERSION
            if APP_VERSION != latest_version:
                # Update verfügbar
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle(TEXTS[LANG]["update_available_title"])
                msg_box.setText(TEXTS[LANG]["update_available_msg"])
                yes_button = msg_box.addButton(TEXTS[LANG].get("yes", "Ja"), QMessageBox.ButtonRole.YesRole)
                no_button = msg_box.addButton(TEXTS[LANG].get("no", "Nein"), QMessageBox.ButtonRole.NoRole)
                msg_box.exec()

                if msg_box.clickedButton() == yes_button:
                    self.plugin_update_action(latest_version=latest_version)
                else:
                    GithubConfigDialog.append_info(self.info_text, TEXTS[LANG]["update_not_available"], "info")
            else:
                # keine neue Version
                GithubConfigDialog.append_info(self.info_text, TEXTS[LANG]["update_not_available"], "info")

        except Exception as e:
            GithubConfigDialog.append_info(
                self.info_text,
                TEXTS[LANG]["update_fail"].format(error=str(e)),
                "error"
            )

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
                GithubConfigDialog.append_info(self.info_text, f"⚠️ Config konnte nicht gelesen werden: {e}", "warning")

        tools_ok = cfg.get("tools_ok", False)
        if tools_ok:
            GithubConfigDialog.append_info(self.info_text, "DEBUG: tools_ok geladen (Toolsprüfung übersprungen)", "info")
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
                    GithubConfigDialog.append_info(self.info_text, f"⚠️ {name}: {result}", "warning")
                    all_ok = False
                else:
                    GithubConfigDialog.append_info(self.info_text, f"✅ {name}: {result}", "success")
            except Exception:
                GithubConfigDialog.append_info(self.info_text, f"⚠️ {name}: Fehler", "warning")
                all_ok = False

        if all_ok:
            GithubConfigDialog.append_info(self.info_text, TEXTS[LANG]["all_tools_installed"], "success")
            cfg["tools_ok"] = True
            with open(CONFIG_FILE, "w") as f:
                json.dump(cfg, f, indent=2)
            GithubConfigDialog.append_info(self.info_text, TEXTS[LANG]["tool_saved"], "info")
        else:
            GithubConfigDialog.append_info(self.info_text, "❌ Einige Tools fehlen oder Fehler aufgetreten", "error")

        # =====================
        # INIT UI
        # =====================
    def init_ui(self):
        TITLE_HEIGHT = 60

        # -------------------
        # Haupt-Layout
        # -------------------
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        self.all_buttons = []
        self.active_button_key = None
        # 🔹 Progressbar für Plugin-Update
        self.update_progress = QProgressBar()
        self.update_progress.setMinimum(0)
        self.update_progress.setMaximum(100)
        self.update_progress.setValue(0)
        self.update_progress.setTextVisible(True)
        self.update_progress.setFormat("Update Fortschritt: %p%")
        layout.addWidget(self.update_progress)
        
        # -------------------
        # HEADER
        # -------------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        # Hier ggf. Header-Label oder Titel einfügen
        self.header_label = QLabel("OSCam Emu Patch Manager")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(self.header_label)
        layout.addLayout(header_layout)

        # Linke Widgets: Info + digitale Uhr
        self.info_button = QPushButton("ℹ️")
        self.info_button.setFixedSize(60, TITLE_HEIGHT)
        self.info_button.setToolTip(TEXTS[LANG]["info_tooltip"])
        self.info_button.clicked.connect(self.show_info)

        self.digital_clock = QLabel()
        self.digital_clock.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.digital_clock.setFixedHeight(TITLE_HEIGHT)
        self.digital_clock.setMinimumWidth(120)
        self.digital_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left_layout = QHBoxLayout()
        left_layout.setSpacing(5)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.info_button)
        left_layout.addWidget(self.digital_clock, stretch=1)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        header_layout.addWidget(left_widget, 1, Qt.AlignmentFlag.AlignLeft)

        # Titel in der Mitte
        title = QLabel("OSCam Emu Toolkit – by speedy005")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setStyleSheet("color:red;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(TITLE_HEIGHT)
        header_layout.addWidget(title, 1)

        # Version rechts
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        version_label.setStyleSheet("color:red;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        version_label.setFixedHeight(TITLE_HEIGHT)
        header_layout.addWidget(version_label, 1, Qt.AlignmentFlag.AlignRight)

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
        # OPTIONS LEISTE (Controls)
        # -------------------
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # 🔹 Patch Header bearbeiten
        self.edit_header_button = QPushButton("Patch Header bearbeiten")
        self.edit_header_button.setFixedHeight(self.BUTTON_HEIGHT)
        self.edit_header_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.edit_header_button.clicked.connect(self.edit_patch_header)
        controls_layout.addWidget(self.edit_header_button)

        # 🔹 Sprache
        self.lang_label = QLabel(TEXTS[LANG]["language_label"])
        self.lang_label.setMinimumHeight(self.BUTTON_HEIGHT)
        controls_layout.addWidget(self.lang_label)

        self.language_box = QComboBox()
        self.language_box.addItems(["EN", "DE"])
        self.language_box.setCurrentText("DE" if LANG == "de" else "EN")
        self.language_box.setFixedHeight(self.BUTTON_HEIGHT)
        self.language_box.setFixedWidth(60)
        self.language_box.currentIndexChanged.connect(self.change_language)
        self.language_box.currentIndexChanged.connect(self.change_language)
        controls_layout.addWidget(self.language_box)

        # 🔹 Farbe
        self.color_label = QLabel(TEXTS[LANG]["color_label"])
        self.color_label.setMinimumHeight(self.BUTTON_HEIGHT)
        controls_layout.addWidget(self.color_label)

        self.color_box = QComboBox()
        self.color_box.addItems(list(DIFF_COLORS.keys()))
        self.color_box.setCurrentText(current_color_name)
        self.color_box.setFixedHeight(self.BUTTON_HEIGHT)
        self.color_box.setFixedWidth(120)
        self.color_box.currentIndexChanged.connect(self.change_colors)
        controls_layout.addWidget(self.color_box)

        # 🔹 Commit-Spinbox
        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1, 20)
        self.commit_spin.setValue(commit_count)  # aus load_config()
        self.commit_spin.setFixedHeight(self.BUTTON_HEIGHT)
        self.commit_spin.setFixedWidth(50)
        controls_layout.addWidget(self.commit_spin)

        # 🔹 Commits ansehen Button
        self.commits_button = self.create_option_button(
            key="git_status",
            text=TEXTS[LANG]["git_status"],
            color="#1E90FF",
            callback=self.show_commits
        )
        self.commits_button.setFixedHeight(self.BUTTON_HEIGHT)
        controls_layout.addWidget(self.commits_button)

        # 🔹 Plugin Update Button
        self.plugin_update_button = self.create_option_button(
            key="plugin_update",
            text=TEXTS[LANG]["plugin_update"],
            color=current_diff_colors['bg'],
            fg=current_diff_colors['text'],
            callback=lambda: self.plugin_update_action(progress_callback=self.update_progressbar)
        )
        self.plugin_update_button.setFixedHeight(self.BUTTON_HEIGHT)
        controls_layout.addWidget(self.plugin_update_button)
        
        from PyQt6.QtWidgets import QProgressBar

        # 🔹 Progressbar für Plugin-Update
        self.update_progress = QProgressBar()
        self.update_progress.setMinimum(0)
        self.update_progress.setMaximum(100)
        self.update_progress.setValue(0)
        self.update_progress.setTextVisible(True)
        self.update_progress.setFormat("Update Fortschritt: %p%")
        controls_layout.addWidget(self.update_progress)
        
        # 🔹 Rollback Button
        self.rollback_button = self.create_option_button(
            key="rollback_plugin",
            text="Rollback Plugin",
            color="#FF8C00",  # orange
            fg="#FFFFFF",
            callback=self.rollback_plugin_action
        )
        self.rollback_button.setFixedHeight(self.BUTTON_HEIGHT)
        controls_layout.addWidget(self.rollback_button)

        
        # 🔹 Tool Neustarten Button
        self.restart_tool_button = self.create_option_button(
            key="restart_tool",
            text=TEXTS[LANG].get("restart_tool", "Tool Neustarten"),
            color=current_diff_colors['bg'],
            fg=current_diff_colors['text'],
            callback=self.restart_application
        )
        self.restart_tool_button.setFixedHeight(self.BUTTON_HEIGHT)
        controls_layout.addWidget(self.restart_tool_button)
     
        # Container-Widget für die Controls (vermeidet Doppel-Layouts)
        controls_container = QWidget()
        controls_container.setLayout(controls_layout)
        layout.addWidget(controls_container)

        # -------------------
        # OPTION BUTTONS (Patch & Git)
        # -------------------
        buttons_list = [
            ("clean_emu_git", TEXTS[LANG]["clean_emu_git"], "#8B4513", clean_oscam_emu_git),
            ("patch_emu_git", TEXTS[LANG]["patch_emu_git"], "#006400", patch_oscam_emu_git),
            ("github_upload_patch", TEXTS[LANG]["github_upload_patch"], "#1E90FF", github_upload_patch_file),
            ("github_upload_emu", TEXTS[LANG]["github_upload_emu"], "#1E90FF", github_upload_oscam_emu_folder),
            ("github_config", TEXTS[LANG]["github_config_button"], "#FFA500", self.edit_emu_github_config, "black")
        ]

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for btn_data in buttons_list:
            key, text, color, callback = btn_data[:4]
            fg = btn_data[4] if len(btn_data) == 5 else current_diff_colors['text']
            btn = self.create_option_button(key=key, text=text, color=color, callback=callback, fg=fg)
            btn.setMinimumHeight(self.BUTTON_HEIGHT)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            buttons_layout.addWidget(btn)

        layout.addLayout(buttons_layout)

        # -------------------
        # GRID BUTTONS
        # -------------------
        grid_layout = QGridLayout()
        actions = [
            ("patch_create", lambda: self.run_action(create_patch)),
            ("patch_renew", lambda: self.run_action(create_patch)),
            ("patch_check", lambda: self.run_action(self.check_patch)),
            ("patch_apply", lambda: self.run_action(self.apply_patch)),
            ("patch_zip", lambda: self.run_action(zip_patch)),
            ("backup_old", lambda: self.run_action(backup_old_patch)),
            ("clean_folder", lambda: self.run_action(clean_patch_folder)),
            ("change_old_dir", lambda: self.run_action(self.change_old_)),
            ("exit", self.close_with_confirm)
        ]
        self.buttons = {}
        for idx, (key, func) in enumerate(actions):
            btn = QPushButton(TEXTS[LANG][key])
            btn.setIcon(get_icon_for(TEXTS[LANG][key]))
            btn.setFont(QFont("Arial", 16))
            btn.setMinimumHeight(self.BUTTON_HEIGHT)
            btn.clicked.connect(lambda checked=False, k=key, f=func: self.set_active_button(k) or f())
            self.buttons[key] = btn
            row, col = divmod(idx, 3)
            grid_layout.addWidget(btn, row, col)

        layout.addLayout(grid_layout)

        # -------------------
        # PROGRESS BAR
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
        current_time = now.toString("HH:mm:ss dd.MM.yyyy")  # 14:35:10 20.01.2026  # Datum + Uhrzeit
        if hasattr(self, "digital_clock"):
            self.digital_clock.setText(current_time)


    
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
            f"background-color:{color}; color:{fg}; border-radius:{self.BUTTON_RADIUS}px;"
        )
        btn.clicked.connect(lambda: self.on_button_clicked(key, callback))
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

    def change_colors(self):
        """
        Update UI colors based on the selected theme (from color_box)
        Applies to labels, buttons, info text, digital clock, grid buttons, and progress bar.
        Saves the current commit count to config.
        """
        global current_diff_colors, current_color_name

        # Aktuelle Farbe aus ComboBox laden
        current_color_name = self.color_box.currentText()
        current_diff_colors = DIFF_COLORS.get(current_color_name, DIFF_COLORS["Classic"])

        # ---------- Labels & ComboBoxes ----------
        for w in [
            getattr(self, "lang_label", None),
            getattr(self, "color_label", None),
            getattr(self, "language_box", None),
            getattr(self, "color_box", None),
        ]:
            if w:
                w.setStyleSheet(
                f"background-color:{current_diff_colors['bg']}; "
                f"color:{current_diff_colors['text']};"
                )

        # ---------- Patch Header Button ----------
        if hasattr(self, "edit_header_button"):
            self.edit_header_button.setStyleSheet(
                f"background-color:{current_diff_colors['bg']}; "
                f"color:{current_diff_colors['text']}; "
                f"border-radius:10px;"
            )

        # ---------- Option Buttons ----------
        for btn in [
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
                    f"background-color:{current_diff_colors['bg']}; "
                    f"color:{current_diff_colors['text']}; "
                    f"border-radius:10px;"
                )

        # ---------- Digitale Uhr ----------
        if hasattr(self, "digital_clock"):
            self.digital_clock.setStyleSheet(
                f"color:{current_diff_colors['text']}; "
                f"background-color:{current_diff_colors['bg']}; "
                f"border-radius:10px;"
            )

        # ---------- Info-Textfeld ----------
        if hasattr(self, "info_text"):
            self.info_text.setStyleSheet(
                f"background-color:black; color:{current_diff_colors['text']};"
            )

        # ---------- Grid Buttons ----------
        for btn in getattr(self, "buttons", {}).values():
            btn.setStyleSheet(
                f"background-color:{current_diff_colors['bg']}; "
                f"color:{current_diff_colors['text']}; "
                f"border-radius:10px;"
            )

        # ---------- Active Button ----------
        if hasattr(self, "set_active_button"):
            self.set_active_button(getattr(self, "active_button_key", ""))

        # ---------- Progress Bar ----------
        if hasattr(self, "progress"):
            self.progress.setStyleSheet(
                f"QProgressBar::chunk {{background-color:{current_diff_colors['bg']};}}"
            ) 

        # ---------- Repaint UI ----------
        self.repaint()
        QApplication.processEvents()

        # ---------- Commit Count speichern ----------
        save_config(self.commit_spin.value())

    def change_language(self):
        """
        Called when the language dropdown changes.
        Updates the global LANG variable and refreshes all text labels.
        """
        global LANG
        selected = self.language_box.currentText()
        LANG = "de" if selected == "DE" else "en"

        # Update all text labels that depend on LANG
        self.lang_label.setText(TEXTS[LANG]["language_label"])
        self.color_label.setText(TEXTS[LANG]["color_label"])
        self.edit_header_button.setText(TEXTS[LANG].get("edit_patch_header", "Patch Header bearbeiten"))
        self.plugin_update_button.setText(TEXTS[LANG]["plugin_update"])
        self.restart_tool_button.setText(TEXTS[LANG].get("restart_tool", "Tool Neustarten"))
        self.commits_button.setText(TEXTS[LANG]["git_status"])

        # Update all grid buttons
        for key, btn in self.buttons.items():
            if key in TEXTS[LANG]:
                btn.setText(TEXTS[LANG][key])

        # Optional: update any other dynamic texts
        append_info(self.info_text, f"Language changed to {selected}", "info")

        # =====================
        # GITHUB EMU CREDENTIALS
        # =====================
    def check_emu_credentials(self):
        cfg = load_github_config()
        if not all([cfg.get("emu_repo_url"), cfg.get("username"), cfg.get("token")]):
            append_info(self.info_text, "GitHub-Emu-Zugangsdaten fehlen!", "warning")

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
            append_info(self.info_text, TEXTS[LANG]["github_config_saved"])

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
        try:
            self.progress.setValue(0)
            self.progress.setStyleSheet(f"QProgressBar::chunk {{background-color:{current_diff_colors['bg']};}}")
            action_func(self.info_text, progress_callback=self.progress.setValue)
            self.progress.setValue(100)
        except Exception as e:
            append_info(self.info_text, f"Fehler: {str(e)}", "error")
            self.progress.setValue(0)

        # =====================
        # BUTTON CALLBACKS
        # =====================
    def show_commits(self, info_widget=None, progress_callback=None):
        append_info(self.info_text, TEXTS[LANG]["showing_commits"], "info")
        run_bash(f"git -C {TEMP_REPO} log -n {self.commit_spin.value()} --oneline", info_widget=self.info_text)
        if progress_callback:
            progress_callback(100)


    def check_patch(self, info_widget=None, progress_callback=None):
        if not os.path.exists(PATCH_FILE):
            append_info(info_widget, TEXTS[LANG]["patch_file_missing"], "error")
            return
        code = run_bash(f"git apply --check {PATCH_FILE}", cwd=TEMP_REPO, info_widget=info_widget)
        if code == 0:
            append_info(info_widget, TEXTS[LANG]["patch_check_ok"], "success")
        else:
            append_info(info_widget, TEXTS[LANG]["patch_check_fail"], "error")
        if progress_callback:
            progress_callback(100)


    def apply_patch(self, info_widget=None, progress_callback=None):
        if not os.path.exists(PATCH_FILE):
            append_info(info_widget, TEXTS[LANG]["patch_file_missing"], "error")
            return
        code = run_bash(f"git apply {PATCH_FILE}", cwd=TEMP_REPO, info_widget=info_widget)
        if code == 0:
            append_info(info_widget, TEXTS[LANG]["patch_apply_success_msg"], "success")
        else:
            append_info(info_widget, TEXTS[LANG]["patch_apply_fail_msg"], "error")
        if progress_callback:
            progress_callback(100)

    def change_old_(self, info_widget=None, progress_callback=None):
        global OLD_, OLD_PATCH_FILE, ALT_PATCH_FILE
        new_dir = QFileDialog.getExistingDirectory(self, TEXTS[LANG]["change_old_dir"], OLD_)
        if new_dir:
            OLD_ = new_dir
            self.old_patch_dir = OLD_  # 🔹 Wichtig: für save_config()
            OLD_PATCH_FILE = os.path.join(OLD_, "oscam-emu.patch")
            ALT_PATCH_FILE = os.path.join(OLD_, "oscam-emu.altpatch")
            append_info(self.info_text, TEXTS[LANG]["old_patch_path_changed"].format(OLD_=OLD_), "success")
        else:
            append_info(self.info_text, TEXTS[LANG]["old_patch_path_cancelled"], "info")
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
            save_config(self.commit_spin.value())
            QApplication.quit()

if __name__ == "__main__":
    import sys
    import os

    os.environ["NO_AT_BRIDGE"] = "1"

    app = QApplication(sys.argv)   # 🔴 MUSS ALS ERSTES KOMMEN

    check_single_instance()        # darf JETZT QMessageBox benutzen
    ensure_dir(PLUGIN_DIR)
    ensure_dir(ICON_DIR)
    ensure_dir(TEMP_REPO)
    load_config()

    window = PatchManagerGUI()
    window.showMaximized()

    sys.exit(app.exec())

