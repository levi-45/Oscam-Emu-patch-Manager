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

import os, sys, subprocess, shutil, json, zipfile
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PIL import Image, ImageDraw, ImageFont

# =====================
# APP VERSION
# =====================
APP_VERSION = "1.0.0"

# ===================== PATHS & CONFIG =====================
PATCH_DIR = "/opt/patch/oscam-patching"
CONFIG_FILE = os.path.join(PATCH_DIR, "config.json")
ICON_DIR = os.path.join(PATCH_DIR, "icons")
ICON_SIZE = 64
TEMP_REPO = os.path.join(PATCH_DIR, "temp_repo")
PATCH_FILE = os.path.join(PATCH_DIR, "oscam-emu.patch")
PATCH_EMU_GIT_DIR = os.path.join(PATCH_DIR, "oscam-emu-git")
ZIP_FILE = os.path.join(PATCH_DIR, "oscam-emu.zip")
OLD_PATCH_DIR_DEFAULT = "/opt/s3_neu/support/patches"
OLD_PATCH_DIR = OLD_PATCH_DIR_DEFAULT
OLD_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.patch")
ALT_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.altpatch")
PATCH_MODIFIER = "speedy005"
EMUREPO = "https://github.com/oscam-mirror/oscam-emu.git"
STREAMREPO = "https://git.streamboard.tv/common/oscam.git"
REQUIRED_TOOLS = ["git", "zip", "unzip", "python3", "pip3"]

NEVER_DELETE = [
    "oscam_patch_manager.py", 
    "oscam-patch-manager.sh", 
    "oscam-patch-manager-gui.sh",
    "oscam-emu-patch.sh", 
    "oscam-patch-manager-gui-eng.sh", 
    "github_upload_config.json",
    "oscam-patch.sh", 
    "config.json", "icons"
]

# ===================== LANGUAGE & TEXT =====================
LANG = "en"
TEXTS = {
    "de": {
        "info_tooltip": "Info / Hilfe",
        "info_title": "Information",
        "info_text": "Dieses Tool erstellt OSCam-Emu-Patches und verwaltet GitHub-Uploads.\n\nAnleitung:\n- Sprache und Farbe wählen\n- Patch erstellen oder hochladen\n- OSCam-Emu Git updaten...",
        "language_label": "Sprache:",
        "color_label": "Farbe:",
        "git_status": "Commits ansehen",
        "clean_emu_git": "Oscam Emu Git leeren",
        "patch_emu_git": "Oscam Emu Git erstellen",
        "patch_create": "Patch erstellen",
        "patch_renew": "Patch erneuern",
        "patch_check": "Patch prüfen",
        "patch_apply": "Patch anwenden",
        "patch_zip": "Patch packen",
        "backup_old": "Patch sichern/erneuern",
        "clean_folder": "Oscam-Patch leeren",
        "change_old_dir": "Pfad zu s3 ändern",
        "exit": "Beenden",
        "exit_question": "Willst du das Programm wirklich beenden?",
        "yes": "Ja",
        "no": "Nein"
    },
    "en": {
        "info_tooltip": "Info / Help",
        "info_title": "Information",
        "info_text": "This tool creates OSCam-Emu patches and manages GitHub uploads.\n\nInstructions:\n- Choose language and color\n- Create or upload patch\n- Update OSCam-Emu Git...",
        "language_label": "Language:",
        "color_label": "Color:",
        "git_status": "View Commits",
        "clean_emu_git": "Clean OSCam Emu Git",
        "patch_emu_git": "Patch OSCam Emu Git",
        "patch_create": "Create Patch",
        "patch_renew": "Renew Patch",
        "patch_check": "Check Patch",
        "patch_apply": "Apply Patch",
        "patch_zip": "Zip Patch",
        "backup_old": "Backup/Renew Patch",
        "clean_folder": "Clean Patch Folder",
        "change_old_dir": "Change Old Patch Dir",
        "exit": "Exit",
        "exit_question": "Do you really want to close the tool?",
        "yes": "Yes",
        "no": "No"
    }
}

# =====================
# COLORS
# =====================
DIFF_COLORS = {
    "Classic":       {"bg": "#1E1E1E", "text": "#FFFFFF"},  # Dunkles Terminal
    "Ocean":         {"bg": "#2B3A67", "text": "#A8D0E6"},  # Blau-Töne
    "Sunset":        {"bg": "#FF6B6B", "text": "#FFE66D"},  # Warmes Orange/Rot
    "Forest":        {"bg": "#2E8B57", "text": "#E0F2F1"},  # Grün/Türkis
    "Candy":         {"bg": "#FFB6C1", "text": "#4B0082"},  # Rosa/Lila Kontrast
    "Cyberpunk":     {"bg": "#0D0D0D", "text": "#FF00FF"},  # Schwarz mit Neonpink
    "CoolMint":      {"bg": "#A8FFF0", "text": "#003F3F"},  # Hellmint mit dunklem Text
    "Sunrise":       {"bg": "#FFD580", "text": "#B22222"},  # Gelb-orange mit dunkelrot
    "DeepSea":       {"bg": "#001F3F", "text": "#7FDBFF"},  # Sehr dunkelblau mit hellblau
    "Lavender":      {"bg": "#E6E6FA", "text": "#4B0082"},  # Helles Lila mit dunklem Lila
    "Blue-Orange":   {"bg": "#FF8C00", "text": "#FFFFFF"},  # Orange Hintergrund, weiße Schrift
    "Yellow-Purple": {"bg": "#800080", "text": "#FFFF00"},  # Lila Hintergrund, gelbe Schrift
    "Green-Red":     {"bg": "#228B22", "text": "#FFFFFF"},  # Dunkelgrün Hintergrund, weiße Schrift
    "Midnight":      {"bg": "#121212", "text": "#BB86FC"},  # Dunkles Lila/Schwarz
    "Solarized":     {"bg": "#002B36", "text": "#839496"},  # Solarized Dark
    "Neon":          {"bg": "#0B0C10", "text": "#66FCF1"},  # Neonblau auf Schwarz
    "Fire":          {"bg": "#7F0000", "text": "#FF4500"},  # Dunkelrot + Orange
    "Moss":          {"bg": "#2E3A23", "text": "#A9BA9D"},  # Grün-Töne
    "Peach":         {"bg": "#FFDAB9", "text": "#8B4513"},  # Hellorange + Braun
    "Galaxy":        {"bg": "#1B1B2F", "text": "#E94560"},  # Dunkelblau + Pink
    "Aqua":          {"bg": "#004D4D", "text": "#00FFFF"},  # Dunkles Aqua + Cyan
    "Lavish":        {"bg": "#3D2B56", "text": "#F1C40F"},  # Lila + Gold
    "Tech":          {"bg": "#0F0F0F", "text": "#00FF00"},  # Schwarz + Neon Grün
    "NeonPink":      {"bg": "#1A1A1D", "text": "#FF6EC7"},  # Dunkel + knallpink
    "ElectricBlue":  {"bg": "#0B0C10", "text": "#00FFFF"},  # Schwarz + Cyan
    "CyberGreen":    {"bg": "#050A05", "text": "#39FF14"},  # Dunkel + Neongrün
    "SunsetVibes":   {"bg": "#FF4500", "text": "#FFF8DC"},  # Orange + Creme
    "PurpleHaze":    {"bg": "#2E004F", "text": "#D580FF"},  # Dunkellila + Lila
    "MintyFresh":    {"bg": "#002B2B", "text": "#7FFFD4"},  # Dunkeltürkis + Mint
    "HotMagenta":    {"bg": "#1B0B1B", "text": "#FF00FF"},  # Sehr dunkel + Magenta
    "GoldenHour":    {"bg": "#2F1E00", "text": "#FFD700"},  # Dunkelbraun + Gold
    "OceanDeep":     {"bg": "#001F3F", "text": "#00BFFF"},  # Tiefblau + Hellblau
    "Tropical":      {"bg": "#003300", "text": "#FFDD00"},  # Dunkelgrün + Gelb
    "MagentaGlow":   {"bg": "#1C001C", "text": "#FF00FF"},  # Dunkel + Neonmagenta
    "CyanWave":      {"bg": "#001F1F", "text": "#00FFFF"},  # Tiefes Cyan + Hellcyan
    "SunriseGold":   {"bg": "#2B1A00", "text": "#FFD700"},  # Dunkelbraun + Gold
    "CoralReef":     {"bg": "#2F0A0A", "text": "#FF7F50"},  # Dunkelrot + Korall
    "LimePunch":     {"bg": "#0A1F00", "text": "#BFFF00"},  # Dunkelgrün + Neonlime
    "VioletStorm":   {"bg": "#1E003F", "text": "#D580FF"},  # Dunkelviolett + Lila
    "OceanMist":     {"bg": "#002B3A", "text": "#7FDBFF"},  # Dunkelblau + Hellblau
    "PeachySun":     {"bg": "#3F1E00", "text": "#FFA07A"},  # Dunkelbraun + Peach
    "NeonOrange":    {"bg": "#1A0A00", "text": "#FF8C00"},  # Schwarz + Neonorange
    "TurquoiseDream":{"bg": "#002222", "text": "#40E0D0"},  # Tiefes Türkis + Cyan
}

current_diff_colors = DIFF_COLORS["Classic"]
current_color_name = "Classic"

# ===================== CONFIG UTIL =====================
def load_config():
    global LANG, current_diff_colors, current_color_name
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE,"r") as f:
                cfg = json.load(f)
                LANG = cfg.get("language", LANG)
                current_color_name = cfg.get("color", "Classic")
                current_diff_colors = DIFF_COLORS.get(current_color_name, DIFF_COLORS["Classic"])
        except: pass

def save_config():
    cfg = {"language": LANG,"color": current_color_name}
    try:
        with open(CONFIG_FILE,"w") as f: json.dump(cfg,f)
    except: pass

def ensure_dir(path):
    if not os.path.exists(path): os.makedirs(path)

def append_info(info_widget, text):
    if info_widget:
        info_widget.append(text)
        info_widget.moveCursor(QTextCursor.MoveOperation.End)

def run_bash(cmd, cwd=None, info_widget=None):
    if info_widget: append_info(info_widget,f"▶ {cmd}")
    if cwd: ensure_dir(cwd)
    process = subprocess.Popen(cmd, shell=True, cwd=cwd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        line = line.rstrip()
        if info_widget: append_info(info_widget,line)
    process.wait()
    return process.returncode

def copy_file(src,dst):
    try: shutil.copy2(src,dst); return True
    except Exception as e: return str(e)

def check_tools(info_widget=None):
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing: append_info(info_widget,f"❌ Missing tools: {', '.join(missing)}")
    else: append_info(info_widget,"✅ All required tools installed")
    return missing

# ===================== ICONS =====================
def create_icons():
    ensure_dir(ICON_DIR)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ICON_ACTIONS = {text:"green" for text in TEXTS[LANG].values()}
    for name,color in ICON_ACTIONS.items():
        safe_name = name.replace(" ","_").replace("/","_").replace("\\","_")
        file_name = os.path.join(ICON_DIR,safe_name+".png")
        if not os.path.exists(file_name):
            img = Image.new("RGBA",(ICON_SIZE,ICON_SIZE),color)
            draw = ImageDraw.Draw(img)
            try: fnt = ImageFont.truetype(font_path,16)
            except: fnt = ImageFont.load_default()
            text = name.split()[0]
            if hasattr(draw,"textbbox"):
                bbox = draw.textbbox((0,0), text,font=fnt)
                w,h = bbox[2]-bbox[0], bbox[3]-bbox[1]
            else: w,h = draw.textsize(text,font=fnt)
            draw.text(((ICON_SIZE-w)/2,(ICON_SIZE-h)/2), text,font=fnt,fill="white")
            img.save(file_name)

def get_icon_for(name):
    safe_name = name.replace(" ","_").replace("/","_").replace("\\","_")
    path = os.path.join(ICON_DIR,safe_name+".png")
    return QIcon(path) if os.path.exists(path) else QIcon()

GITHUB_CONF_FILE = os.path.join(PATCH_DIR, "github_upload_config.json")

def load_github_config():
    if os.path.exists(GITHUB_CONF_FILE):
        try:
            cfg = json.load(open(GITHUB_CONF_FILE))
            cfg.setdefault("repo_url","")
            cfg.setdefault("branch","master")
            cfg.setdefault("emu_repo_url","")
            cfg.setdefault("emu_branch","master")
            cfg.setdefault("username","")
            cfg.setdefault("token","")
            cfg.setdefault("user_name","speedy005")
            cfg.setdefault("user_email","patch@oscam.local")
            return cfg
        except: return {}
    return {}

def save_github_config(cfg):
    try:
        with open(GITHUB_CONF_FILE,"w") as f: json.dump(cfg,f)
    except: pass


# ============================================================================
# OSCam Emu Patch & Git Funktionen
# ============================================================================

# ===================== OSCAM VERSION & PATCH HEADER =====================
def get_oscam_version_from_globals(repo_dir=None):
    if repo_dir is None: repo_dir = TEMP_REPO
    globals_path = os.path.join(repo_dir, "globals.h")
    if not os.path.exists(globals_path): return None
    with open(globals_path,"r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#define CS_VERSION"):
                parts = line.split('"')
                if len(parts)>=2: return parts[1].strip()
    return None

def get_patch_header(repo_dir=None):
    if repo_dir is None: repo_dir = TEMP_REPO
    globals_path = os.path.join(repo_dir,"globals.h")
    osc_version, build_number = "2.26.01","0"
    if os.path.exists(globals_path):
        with open(globals_path,"r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#define CS_VERSION"):
                    ver_str = line.split('"')[1].strip()
                    if "-" in ver_str: osc_version, build_number = ver_str.split("-",1)
                    else: osc_version = ver_str
    commit_hash = "N/A"
    git_dir = os.path.join(repo_dir,".git")
    if os.path.exists(git_dir):
        try: commit_hash = subprocess.getoutput(f"git -C {repo_dir} rev-parse --short HEAD").strip()
        except: pass
    patch_date = subprocess.getoutput("date -u '+%Y-%m-%d %H:%M:%S UTC (%z)'")
    modified_date = datetime.now().strftime("%d/%m/%Y")
    version_str = f"{osc_version}-{build_number}-802-({commit_hash})"
    return f"patch version: oscam-emu-patch {version_str}\npatch date: {patch_date}\npatch modified by {PATCH_MODIFIER} ({modified_date})\n"

# ===================== PATCH FUNCTIONS =====================
def create_patch(info_widget=None):
    ensure_dir(TEMP_REPO)
    if not os.path.exists(os.path.join(TEMP_REPO,".git")):
        append_info(info_widget,"🔄 Cloning OSCam Repo …")
        code = run_bash(f"git clone {STREAMREPO} .", cwd=TEMP_REPO, info_widget=info_widget)
        if code!=0: append_info(info_widget,"❌ Clone failed"); return
        run_bash(f"git remote add emu-repo {EMUREPO}", cwd=TEMP_REPO, info_widget=info_widget)
    append_info(info_widget,"🔄 Fetching updates …")
    run_bash("git fetch origin", cwd=TEMP_REPO, info_widget=info_widget)
    run_bash("git fetch emu-repo", cwd=TEMP_REPO, info_widget=info_widget)
    run_bash("git checkout master", cwd=TEMP_REPO, info_widget=info_widget)
    run_bash("git reset --hard origin/master", cwd=TEMP_REPO, info_widget=info_widget)

    header = get_patch_header()
    append_info(info_widget,"🔄 Generating patch …")
    diff = subprocess.getoutput(f"git -C {TEMP_REPO} diff origin/master..emu-repo/master -- . ':!.github'")
    if not diff.strip(): diff = "# No changes found"
    with open(PATCH_FILE,"w") as f: f.write(header+"\n"+diff+"\n")
    append_info(info_widget,f"✅ Patch created: {PATCH_FILE}")

# ===================== OSCAM-EMU-GIT FUNCTIONS =====================
def clean_oscam_emu_git(info_widget=None):
    if os.path.exists(PATCH_EMU_GIT_DIR): shutil.rmtree(PATCH_EMU_GIT_DIR)
    append_info(info_widget,"✅ OSCam Emu Git folder cleaned")

def patch_oscam_emu_git(info_widget=None):
    append_info(info_widget,"🔄 Patching OSCam Emu Git …")
    if os.path.exists(PATCH_EMU_GIT_DIR): shutil.rmtree(PATCH_EMU_GIT_DIR)
    ensure_dir(PATCH_EMU_GIT_DIR)
    run_bash(f"git clone {EMUREPO} .", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    run_bash(f"git remote add streamboard {STREAMREPO}", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    run_bash("git fetch --all", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    run_bash("git checkout -B streamboard-master streamboard/master", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    code = run_bash(f"git apply --whitespace=fix {PATCH_FILE}", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    if code != 0:
        append_info(info_widget,"❌ Patch failed – base mismatch")
        return
    cfg = load_github_config()
    run_bash(f'git config user.name "{cfg.get("user_name","speedy005")}"', cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    run_bash(f'git config user.email "noreply@users.noreply.github.com"', cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    osc_version_build = get_oscam_version_from_globals(TEMP_REPO) or "unknown"
    commit_msg = f"Sync patch with {osc_version_build}"
    run_bash(f'git commit -am "{commit_msg}" --allow-empty', cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    append_info(info_widget,f"✅ Patch applied locally ({commit_msg})")

# ===================== BACKUP & ZIP =====================
def backup_old_patch(info_widget=None):
    ensure_dir(OLD_PATCH_DIR)
    if os.path.exists(OLD_PATCH_FILE): shutil.copy2(OLD_PATCH_FILE, ALT_PATCH_FILE)
    shutil.copy2(PATCH_FILE, OLD_PATCH_FILE)
    append_info(info_widget,f"💾 Patch backed up: {OLD_PATCH_DIR}")

def zip_patch(info_widget=None):
    try:
        with zipfile.ZipFile(ZIP_FILE,'w') as zipf: zipf.write(PATCH_FILE, os.path.basename(PATCH_FILE))
        append_info(info_widget,f"📦 Patch zipped: {ZIP_FILE}")
    except Exception as e: append_info(info_widget,f"❌ Error zipping patch: {str(e)}")

# ===================== GITHUB UPLOAD =====================
def github_upload_patch_file(info_widget=None):
    cfg = load_github_config()
    patch_repo_url = cfg.get("repo_url")
    branch = cfg.get("branch","master")
    if not all([patch_repo_url, cfg.get("username"), cfg.get("token")]):
        append_info(info_widget, "❌ GitHub patch credentials missing!")
        return
    append_info(info_widget, "🔄 Uploading oscam-emu.patch …")
    if not os.path.exists(PATCH_FILE):
        append_info(info_widget, "❌ Patch file does not exist!")
        return
    temp_patch_repo = os.path.join(PATCH_DIR, "temp_patch_git")
    if os.path.exists(temp_patch_repo): shutil.rmtree(temp_patch_repo)
    token_url = patch_repo_url.replace("https://", f"https://{cfg['username']}:{cfg['token']}@")
    run_bash(f"git clone --branch {branch} {token_url} {temp_patch_repo}", info_widget=info_widget)
    shutil.copy2(PATCH_FILE, os.path.join(temp_patch_repo, "oscam-emu.patch"))
    run_bash(f'git config user.name "{cfg.get("user_name","patcher")}"', cwd=temp_patch_repo, info_widget=info_widget)
    run_bash(f'git config user.email "anon@patch.local"', cwd=temp_patch_repo, info_widget=info_widget)
    run_bash("git add oscam-emu.patch", cwd=temp_patch_repo, info_widget=info_widget)
    osc_version_build = get_oscam_version_from_globals(TEMP_REPO) or "unknown"
    run_bash(f'git commit -m "Update patch {osc_version_build}" --allow-empty', cwd=temp_patch_repo, info_widget=info_widget)
    code = run_bash(f"git push origin {branch}", cwd=temp_patch_repo, info_widget=info_widget)
    append_info(info_widget,"✅ Patch uploaded" if code==0 else "❌ Upload failed")
    shutil.rmtree(temp_patch_repo)

def _github_upload(dir_path, repo_url, info_widget=None, branch="master", commit_msg="Apply OSCam Emu Patch"):
    cfg = load_github_config()
    username, token = cfg.get("username"), cfg.get("token")
    user_name, user_email = cfg.get("user_name","speedy005"), cfg.get("user_email","patch@oscam.local")
    if not os.path.exists(dir_path): append_info(info_widget,"❌ Git folder missing!"); return
    token_url = repo_url.replace("https://", f"https://{username}:{token}@")
    git_dir = os.path.join(dir_path,".git")
    if os.path.exists(git_dir): shutil.rmtree(git_dir)
    run_bash("git init", cwd=dir_path, info_widget=info_widget)
    run_bash(f"git remote add origin {token_url}", cwd=dir_path, info_widget=info_widget)
    run_bash(f"git checkout -b {branch}", cwd=dir_path, info_widget=info_widget)
    run_bash(f'git config user.name "{user_name}"', cwd=dir_path, info_widget=info_widget)
    run_bash(f'git config user.email "{user_email}"', cwd=dir_path, info_widget=info_widget)
    run_bash("git add -A", cwd=dir_path, info_widget=info_widget)
    run_bash(f'git commit -m "{commit_msg}" --allow-empty', cwd=dir_path, info_widget=info_widget)
    code = run_bash(f"git push origin {branch} --force", cwd=dir_path, info_widget=info_widget)
    append_info(info_widget,"✅ Emu Git uploaded" if code==0 else "❌ Upload failed")

def github_upload_oscam_emu_folder(info_widget=None):
    cfg = load_github_config()
    repo_url = cfg.get("emu_repo_url")
    branch = cfg.get("emu_branch","master")
    if not all([repo_url, cfg.get("username"), cfg.get("token")]):
        append_info(info_widget, "❌ GitHub Emu credentials missing!")
        return
    if not os.path.exists(PATCH_EMU_GIT_DIR):
        append_info(info_widget, "❌ OSCam-Emu Git folder missing! Run patch_oscam_emu_git first.")
        return
    commit_msg = f"Sync OSCam-Emu patch {get_oscam_version_from_globals(TEMP_REPO)}"
    _github_upload(PATCH_EMU_GIT_DIR, repo_url, info_widget=info_widget, branch=branch, commit_msg=commit_msg)


# ============================================================================
# OSCam Emu Patch Generator – GUI + Main
# ============================================================================

import sys
import os
import shutil
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

# -----------------------------
# GITHUB CONFIG DIALOG
# -----------------------------
class GithubConfigDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Zugangsdaten / Repos")
        self.setMinimumWidth(520)
        layout = QFormLayout(self)

        self.patch_repo = QLineEdit()
        self.patch_branch = QLineEdit("master")
        self.emu_repo = QLineEdit()
        self.emu_branch = QLineEdit("master")
        self.username = QLineEdit()
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.user_name = QLineEdit("speedy005")
        self.user_email = QLineEdit("patch@oscam.local")

        cfg = load_github_config()
        self.patch_repo.setText(cfg.get("repo_url",""))
        self.patch_branch.setText(cfg.get("branch","master"))
        self.emu_repo.setText(cfg.get("emu_repo_url",""))
        self.emu_branch.setText(cfg.get("emu_branch","master"))
        self.username.setText(cfg.get("username",""))
        self.token.setText(cfg.get("token",""))
        self.user_name.setText(cfg.get("user_name","speedy005"))
        self.user_email.setText(cfg.get("user_email","patch@oscam.local"))

        layout.addRow("Patch Repo URL:", self.patch_repo)
        layout.addRow("Patch Branch:", self.patch_branch)
        layout.addRow("Emu Repo URL:", self.emu_repo)
        layout.addRow("Emu Branch:", self.emu_branch)
        layout.addRow("GitHub Username:", self.username)
        layout.addRow("GitHub Token:", self.token)
        layout.addRow("Git User Name:", self.user_name)
        layout.addRow("Git User Email:", self.user_email)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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

# -----------------------------
# PATCH MANAGER GUI
# -----------------------------
class PatchManagerGUI(QWidget):
    BUTTON_HEIGHT = 60
    BUTTON_RADIUS = 10

    def __init__(self):
        super().__init__()
        load_config()
        self.setWindowTitle("OSCam Emu Toolkit – by speedy005")
        self.setGeometry(50, 50, 1600, 900)
        create_icons()
        
        self.init_ui()
        self.change_colors()
        self.change_language()

    # -----------------------------
    # INFO BUTTON CALLBACK
    # -----------------------------
    def show_info(self):
        text = TEXTS[LANG].get("info_text", "Keine Info verfügbar.")
        dlg = QMessageBox(self)
        dlg.setWindowTitle(TEXTS[LANG].get("info_title", "Info"))
        dlg.setText(text)
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        dlg.exec()



    # =====================
    # INIT UI
    # =====================
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # -----------------------------
        # TITEL + VERSION + INFO BUTTON
        # -----------------------------
        title_layout = QHBoxLayout()

        # Info-Button links außen
        self.info_button = QPushButton("ℹ️")
        self.info_button.setFixedSize(40, 40)
        self.info_button.setToolTip(TEXTS[LANG]["info_tooltip"])
        self.info_button.clicked.connect(self.show_info)
        title_layout.addWidget(self.info_button)

        # Spacer vor Titel
        title_layout.addStretch()

        # Titel zentriert
        title = QLabel("OSCam Emu Toolkit – by speedy005")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setStyleSheet("color:red;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title, stretch=2)

        # Spacer nach Titel
        title_layout.addStretch()

        # Versionsnummer rechts außen
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        version_label.setStyleSheet("color:red;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title_layout.addWidget(version_label)

        layout.addLayout(title_layout)

        # -----------------------------
        # INFO TEXT
        # -----------------------------
        self.info_text = QTextEdit()
        self.info_text.setFont(QFont("Courier", 14))
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(500)
        self.info_text.setStyleSheet("background-color:black; color:white;")
        layout.addWidget(self.info_text)

        # … restlicher Code bleibt wie zuvor …
        self.setLayout(layout)


        # -----------------------------
        # OPTIONSLEISTE (Sprache, Farbe, Commit-Anzahl, Buttons)
        # -----------------------------
        options_layout = QHBoxLayout()
        options_layout.setSpacing(10)
        options_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)


        # Sprache
        self.lang_label = QLabel(TEXTS[LANG]["language_label"])
        self.lang_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lang_label.setMinimumHeight(self.BUTTON_HEIGHT)
        options_layout.addWidget(self.lang_label)

        self.language_box = QComboBox()
        self.language_box.addItems(["EN","DE"])
        self.language_box.setCurrentText("DE" if LANG=="de" else "EN")
        self.language_box.setFixedHeight(self.BUTTON_HEIGHT)
        self.language_box.currentIndexChanged.connect(self.change_language)
        options_layout.addWidget(self.language_box)

        # Farbe
        self.color_label = QLabel(TEXTS[LANG]["color_label"])
        self.color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_label.setMinimumHeight(self.BUTTON_HEIGHT)
        options_layout.addWidget(self.color_label)

        self.color_box = QComboBox()
        self.color_box.addItems(list(DIFF_COLORS.keys()))
        self.color_box.setCurrentText(current_color_name)
        self.color_box.setFixedHeight(self.BUTTON_HEIGHT)
        self.color_box.currentIndexChanged.connect(self.change_colors)
        options_layout.addWidget(self.color_box)

        # Commit-Anzahl
        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1, 20)
        self.commit_spin.setValue(5)
        self.commit_spin.setFixedHeight(self.BUTTON_HEIGHT)
        options_layout.addWidget(self.commit_spin)

        # Option Buttons
        def create_option_button(text, color, callback, fg="white"):
            btn = QPushButton(text)
            btn.setMinimumHeight(self.BUTTON_HEIGHT)
            btn.setStyleSheet(f"background-color:{color}; color:{fg}; border-radius:{self.BUTTON_RADIUS}px;")
            btn.clicked.connect(callback)
            return btn

        self.commits_button = create_option_button(TEXTS[LANG]["git_status"], "#1E90FF",
                                                   lambda: self.show_commits())
        self.clean_emu_button = create_option_button(TEXTS[LANG]["clean_emu_git"], "#8B4513",
                                                     lambda: self.set_active_button("clean_emu_git") or clean_oscam_emu_git(self.info_text))
        self.patch_emu_git_button = create_option_button(TEXTS[LANG]["patch_emu_git"], "#006400",
                                                         lambda: self.set_active_button("patch_emu_git") or patch_oscam_emu_git(self.info_text))
        self.github_upload_patch_button = create_option_button("Upload Patch File", "#1E90FF",
                                                               lambda: self.github_upload_patch())
        self.github_upload_emu_button = create_option_button("Upload OSCam-Emu-Git", "#1E90FF",
                                                             lambda: self.github_upload_emu())
        self.github_emu_config_button = create_option_button("Zugangsdaten/URL", "#FFA500",
                                                             self.edit_emu_github_config, fg="black")

        for btn in [self.commits_button,self.clean_emu_button,self.patch_emu_git_button,
                    self.github_upload_patch_button,self.github_upload_emu_button,self.github_emu_config_button]:
            options_layout.addWidget(btn)

        layout.addLayout(options_layout)

        # PROGRESS BAR
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)

        # GRID BUTTONS
        grid_layout = QGridLayout()
        actions = [
            ("patch_create", lambda: create_patch(self.info_text)),
            ("patch_renew", lambda: create_patch(self.info_text)),
            ("patch_check", self.check_patch),
            ("patch_apply", self.apply_patch),
            ("patch_zip", lambda: zip_patch(self.info_text)),
            ("backup_old", lambda: backup_old_patch(self.info_text)),
            ("clean_folder", self.clean_patch_folder),
            ("change_old_dir", self.change_old_patch_dir),
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
        self.setLayout(layout)
        self.check_emu_credentials()

    # =====================
    # BUTTON & COLOR HANDLING
    # =====================
    def set_active_button(self, active_key):
        for key, btn in self.buttons.items():
            if key == active_key:
                btn.setStyleSheet(f"background-color:#FFD700; color:black; border-radius:{self.BUTTON_RADIUS}px; min-height:{self.BUTTON_HEIGHT}px;")
            else:
                btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:{self.BUTTON_RADIUS}px; min-height:{self.BUTTON_HEIGHT}px;")

    def change_colors(self):
        global current_diff_colors, current_color_name
        current_color_name = self.color_box.currentText()
        current_diff_colors = DIFF_COLORS[current_color_name]
        self.set_active_button("")  # reset
        self.lang_label.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:{self.BUTTON_RADIUS}px;")
        self.color_label.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:{self.BUTTON_RADIUS}px;")
        self.language_box.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:{self.BUTTON_RADIUS}px;")
        self.color_box.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:{self.BUTTON_RADIUS}px;")
        save_config()

    def change_language(self):
        global LANG
        LANG = "de" if self.language_box.currentText() == "DE" else "en"
        save_config()
        self.lang_label.setText(TEXTS[LANG]["language_label"])
        self.color_label.setText(TEXTS[LANG]["color_label"])
        for key, btn in self.buttons.items():
            btn.setText(TEXTS[LANG][key])
        self.clean_emu_button.setText(TEXTS[LANG]["clean_emu_git"])
        self.patch_emu_git_button.setText(TEXTS[LANG]["patch_emu_git"])
        self.commits_button.setText(TEXTS[LANG]["git_status"])

    # =====================
    # EMU CREDENTIALS
    # =====================
    def check_emu_credentials(self):
        cfg = load_github_config()
        if not all([cfg.get("emu_repo_url"), cfg.get("username"), cfg.get("token")]):
            append_info(self.info_text,"⚠️ GitHub-Emu-Zugangsdaten fehlen!")

    def edit_emu_github_config(self):
        dialog = GithubConfigDialog()
        if dialog.exec(): self.check_emu_credentials()

    # =====================
    # BUTTON CALLBACKS
    # =====================
    def github_upload_patch(self):
        github_upload_patch_file(self.info_text)

    def github_upload_emu(self):
        cfg = load_github_config()
        if not all([cfg.get("emu_repo_url"), cfg.get("username"), cfg.get("token")]):
            append_info(self.info_text,"⚠️ GitHub-Emu-Zugangsdaten fehlen!")
            self.edit_emu_github_config()
            return
        github_upload_oscam_emu_folder(self.info_text)

    def show_commits(self):
        append_info(self.info_text,"🔄 Showing last commits …")
        run_bash(f"git -C {TEMP_REPO} log -n {self.commit_spin.value()} --oneline", info_widget=self.info_text)

    def check_patch(self):
        if not os.path.exists(PATCH_FILE):
            append_info(self.info_text,"❌ Patch file does not exist!"); return
        run_bash(f"git apply --check {PATCH_FILE}", cwd=TEMP_REPO, info_widget=self.info_text)

    def apply_patch(self):
        if not os.path.exists(PATCH_FILE):
            append_info(self.info_text,"❌ Patch file does not exist!"); return
        run_bash(f"git apply {PATCH_FILE}", cwd=TEMP_REPO, info_widget=self.info_text)

    def clean_patch_folder(self):
        append_info(self.info_text,"🧹 Cleaning folder …")
        for f in os.listdir(PATCH_DIR):
            if f in NEVER_DELETE: continue
            path = os.path.join(PATCH_DIR,f)
            try: shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
            except: pass
        append_info(self.info_text,"✅ Patch folder cleaned")

    def change_old_patch_dir(self):
        global OLD_PATCH_DIR, OLD_PATCH_FILE, ALT_PATCH_FILE
        new_dir = QFileDialog.getExistingDirectory(self,"Select folder for old patch",OLD_PATCH_DIR)
        if new_dir:
            OLD_PATCH_DIR = new_dir
            OLD_PATCH_FILE = os.path.join(OLD_PATCH_DIR,"oscam-emu.patch")
            ALT_PATCH_FILE = os.path.join(OLD_PATCH_DIR,"oscam-emu.altpatch")
            append_info(self.info_text,f"✅ Path changed: {OLD_PATCH_DIR}")

    def close_with_confirm(self):
        msg = QMessageBox(self)
        msg.setWindowTitle(TEXTS[LANG]["exit"])
        msg.setText(TEXTS[LANG]["exit_question"])
        yes_button = msg.addButton(TEXTS[LANG]["yes"], QMessageBox.ButtonRole.YesRole)
        no_button = msg.addButton(TEXTS[LANG]["no"], QMessageBox.ButtonRole.NoRole)
        msg.exec()
        if msg.clickedButton() == yes_button:
            save_config()
            QApplication.quit()

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    os.environ["NO_AT_BRIDGE"] = "1"
    ensure_dir(ICON_DIR); ensure_dir(PATCH_DIR); ensure_dir(TEMP_REPO)
    load_config()
    app = QApplication(sys.argv)
    window = PatchManagerGUI()
    window.show()
    
    # Jetzt existiert info_text
    check_tools(window.info_text)

    sys.exit(app.exec())



