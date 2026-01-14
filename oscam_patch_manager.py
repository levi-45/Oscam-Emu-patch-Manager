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

import os, sys, subprocess, shutil, zipfile, json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QVBoxLayout, QGridLayout,
    QPushButton, QSizePolicy, QMessageBox, QFileDialog, QComboBox, QHBoxLayout,
    QSpinBox, QDialog, QDialogButtonBox
)
from PyQt6.QtGui import QFont, QTextCursor, QIcon, QPixmap
from PyQt6.QtCore import Qt
from PIL import Image, ImageDraw, ImageFont

# -----------------------------
# PATHS & VARIABLES
# -----------------------------
PATCH_DIR = "/opt/patch/oscam-patching"
CONFIG_FILE = os.path.join(PATCH_DIR, "config.json")
ICON_DIR = os.path.join(PATCH_DIR, "icons")
ICON_SIZE = 64
TEMP_REPO = os.path.join(PATCH_DIR, "temp_repo")
PATCH_FILE = os.path.join(PATCH_DIR, "oscam-emu.patch")
SH_PATCH_DIR = os.path.join(PATCH_DIR, "sh")
PATCH_OSCAM_FILE = os.path.join(SH_PATCH_DIR, "oscam-emu.patch")
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
    "oscam-patch.sh",
    "sh",
    "icons"
]

# -----------------------------
# LANGUAGE & TEXTS
# -----------------------------
LANG = "en"
TEXTS = {
    "en": {
        "patch_create": "Create Patch",
        "patch_renew": "Renew Patch",
        "patch_check": "Check Patch",
        "patch_apply": "Apply Patch",
        "git_status": "Git Status",
        "patch_zip": "Zip Patch",
        "backup_old": "Backup/Renew Patch",
        "clean_folder": "Clean Patch Folder",
        "clean_sh_folder": "Clean OSCam SH",
        "patch_emu_git": "Patch OSCam-EMU Git",
        "change_old_dir": "Change Old Patch Dir",
        "edit_patch_header": "Edit Patch Header",
        "patch_oscam_sh": "Patch OSCam SH",
        "save": "Save",
        "cancel": "Cancel",
        "exit": "Exit",
        "exit_question": "Do you really want to exit?",
        "yes": "Yes",
        "no": "No",
        "show_commits": "Show Commits",
        "language_label": "Language:",
        "color_label": "Color:",
        "missing_tools": "Missing tools: {}",
        "all_tools_ok": "All required tools installed"
    },
    "de": {
        "patch_create": "Patch erstellen",
        "patch_renew": "Patch erneuern",
        "patch_check": "Patch prüfen",
        "patch_apply": "Patch anwenden",
        "git_status": "Git Status",
        "patch_zip": "Patch packen",
        "backup_old": "Patch sichern/erneuern",
        "clean_folder": "Oscam-Patch leeren",
        "clean_sh_folder": "Oscam SH leeren",
        "patch_emu_git": "Patch OSCam-EMU Git",
        "change_old_dir": "Pfad zu s3 ändern",
        "edit_patch_header": "Patch Header bearbeiten",
        "patch_oscam_sh": "Patch OSCam SH",
        "save": "Speichern",
        "cancel": "Abbrechen",
        "exit": "Beenden",
        "exit_question": "Willst du das Programm wirklich beenden?",
        "yes": "Ja",
        "no": "Nein",
        "show_commits": "Commits anzeigen",
        "language_label": "Sprache:",
        "color_label": "Farbe:",
        "missing_tools": "Fehlende Tools: {}",
        "all_tools_ok": "Alle benötigten Tools installiert"
    }
}

# -----------------------------
# COLOR SCHEMES
# -----------------------------
DIFF_COLORS = {
    "classic":       {"bg": "#87CEEB", "text": "black"},
    "blue-orange":   {"bg": "#FF8C00", "text": "white"},
    "yellow-purple": {"bg": "#800080", "text": "yellow"},
    "green-red":     {"bg": "#228B22", "text": "white"}
}
current_diff_colors = DIFF_COLORS["classic"]
current_color_name = "classic"

# -----------------------------
# CONFIG HELPERS
# -----------------------------
def load_config():
    global LANG, current_diff_colors, current_color_name
    current_color_name = "classic"
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                LANG = cfg.get("language", LANG)
                current_color_name = cfg.get("color", "classic")
                current_diff_colors = DIFF_COLORS.get(current_color_name, DIFF_COLORS["classic"])
        except Exception:
            pass

def save_config():
    cfg = {
        "language": LANG,
        "color": current_color_name
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
    except Exception:
        pass

# -----------------------------
# UTILITY FUNCTIONS
# -----------------------------
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def append_info(info_widget, text):
    if info_widget:
        info_widget.append(text)
        info_widget.moveCursor(QTextCursor.MoveOperation.End)

def run_bash(cmd, cwd=None, info_widget=None):
    if info_widget: append_info(info_widget, f"▶ {cmd}")
    if cwd: ensure_dir(cwd)
    process = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        line = line.rstrip()
        if info_widget: append_info(info_widget, line)
    process.wait()
    return process.returncode

def copy_file(src, dst):
    try:
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        return str(e)

def check_tools(info_widget=None):
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        append_info(info_widget, TEXTS[LANG]["missing_tools"].format(", ".join(missing)))
    else:
        append_info(info_widget, TEXTS[LANG]["all_tools_ok"])
    return missing

# -----------------------------
# ICONS
# -----------------------------
def create_icons():
    ensure_dir(ICON_DIR)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ICON_ACTIONS = {
        TEXTS[LANG]["patch_create"]: "green",
        TEXTS[LANG]["patch_renew"]: "orange",
        TEXTS[LANG]["patch_check"]: "blue",
        TEXTS[LANG]["patch_apply"]: "purple",
        TEXTS[LANG]["git_status"]: "cyan",
        TEXTS[LANG]["patch_zip"]: "yellow",
        TEXTS[LANG]["backup_old"]: "magenta",
        TEXTS[LANG]["clean_folder"]: "red",
        TEXTS[LANG]["clean_sh_folder"]: "brown",
        TEXTS[LANG]["patch_oscam_sh"]: "pink",
        TEXTS[LANG]["patch_emu_git"]: "darkgreen",
        TEXTS[LANG]["change_old_dir"]: "grey",
        TEXTS[LANG]["exit"]: "grey"
    }
    for name, color in ICON_ACTIONS.items():
        safe_name = name.replace(" ", "_").replace("/","_").replace("\\","_")
        file_name = os.path.join(ICON_DIR, safe_name + ".png")
        if not os.path.exists(file_name):
            img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), color)
            draw = ImageDraw.Draw(img)
            try: fnt = ImageFont.truetype(font_path, 16)
            except: fnt = ImageFont.load_default()
            text = name.split()[0]
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0,0), text, font=fnt)
                w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
            else:
                w, h = draw.textsize(text, font=fnt)
            draw.text(((ICON_SIZE-w)/2,(ICON_SIZE-h)/2), text, font=fnt, fill="white")
            img.save(file_name)

def get_icon_for(name):
    safe_name = name.replace(" ", "_").replace("/","_").replace("\\","_")
    path = os.path.join(ICON_DIR, safe_name + ".png")
    if os.path.exists(path):
        return QIcon(QPixmap(path))
    return QIcon()

# -----------------------------
# PATCH FUNCTIONS
# -----------------------------
def get_oscam_version_from_globals():
    globals_path = os.path.join(TEMP_REPO, "globals.h")
    if not os.path.exists(globals_path):
        return None
    with open(globals_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#define CS_VERSION"):
                parts = line.split('"')
                if len(parts) >= 2:
                    return parts[1].strip()
    return None

def get_patch_header(repo_dir=TEMP_REPO):
    globals_path = os.path.join(repo_dir, "globals.h")
    osc_version = "2.26.01"
    build_number = "0"
    if os.path.exists(globals_path):
        with open(globals_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#define CS_VERSION"):
                    parts = line.split('"')
                    if len(parts) >= 2:
                        ver_str = parts[1].strip()
                        if "-" in ver_str:
                            osc_version, build_number = ver_str.split("-", 1)
                        else:
                            osc_version = ver_str

    commit_hash = "N/A"
    git_dir = os.path.join(repo_dir, ".git")
    if os.path.exists(git_dir):
        try:
            commit_hash = subprocess.getoutput(f"git -C {repo_dir} rev-parse --short HEAD").strip()
        except Exception:
            pass

    patch_date = subprocess.getoutput("date -u '+%Y-%m-%d %H:%M:%S UTC (%z)'")
    modified_date = subprocess.getoutput("date '+%d/%m/%Y'")

    version_str = f"{osc_version}-{build_number}-802-({commit_hash})"
    return f"patch version: oscam-emu-patch {version_str}\npatch date: {patch_date}\npatch modified by {PATCH_MODIFIER} ({modified_date})\n"


# -----------------------------
# CREATE / CLEAN PATCHES
# -----------------------------
def create_patch(info_widget):
    ensure_dir(TEMP_REPO)
    if not os.path.exists(os.path.join(TEMP_REPO, ".git")):
        append_info(info_widget, "🔄 Cloning OSCam Repo …")
        code = run_bash(f"git clone {STREAMREPO} .", cwd=TEMP_REPO, info_widget=info_widget)
        if code != 0:
            append_info(info_widget, "❌ Clone failed")
            return
        run_bash(f"git remote add emu-repo {EMUREPO}", cwd=TEMP_REPO, info_widget=info_widget)
    append_info(info_widget, "🔄 Fetching updates …")
    run_bash("git fetch origin", cwd=TEMP_REPO, info_widget=info_widget)
    run_bash("git fetch emu-repo", cwd=TEMP_REPO, info_widget=info_widget)
    run_bash("git checkout master", cwd=TEMP_REPO, info_widget=info_widget)
    run_bash("git reset --hard origin/master", cwd=TEMP_REPO, info_widget=info_widget)

    header = get_patch_header()
    append_info(info_widget, "🔄 Generating patch …")
    diff = subprocess.getoutput(f"git -C {TEMP_REPO} diff origin/master..emu-repo/master -- . ':!.github'")
    if not diff.strip(): diff = "# No changes found"
    with open(PATCH_FILE, "w") as f:
        f.write(header + "\n" + diff + "\n")
    append_info(info_widget, f"✅ Patch created: {PATCH_FILE}")

def clean_oscam_sh_folder(info_widget):
    ensure_dir(SH_PATCH_DIR)
    append_info(info_widget, "🧹 Cleaning OSCam SH folder …")
    for f in os.listdir(SH_PATCH_DIR):
        path = os.path.join(SH_PATCH_DIR, f)
        try:
            if os.path.isdir(path): shutil.rmtree(path)
            else: os.remove(path)
            append_info(info_widget, f"✔ Deleted: {f}")
        except Exception as e:
            append_info(info_widget, f"❌ Error deleting {f}: {str(e)}")
    append_info(info_widget, "✅ OSCam SH folder cleaned")

def create_oscam_sh_patch(info_widget=None):
    """
    Erstellt den OSCam SH Patch im eigenen SH-Ordner.
    TEMP_REPO liegt unter sh/temp_repo und wird bei Bedarf automatisch geklont.
    """
    ensure_dir(SH_PATCH_DIR)
    tmp_repo = os.path.join(SH_PATCH_DIR, "temp_repo")  # SH-eigener TEMP_REPO

    # TEMP_REPO prüfen und ggf. klonen
    if not os.path.exists(tmp_repo):
        append_info(info_widget, "🔄 TEMP_REPO für OSCam SH existiert nicht, klone OSCam Repo …")
        ensure_dir(tmp_repo)
        code = run_bash(f"git clone {STREAMREPO} .", cwd=tmp_repo, info_widget=info_widget)
        if code != 0:
            append_info(info_widget, "❌ Klonen von TEMP_REPO für SH fehlgeschlagen")
            return

        run_bash(f"git remote add emu-repo {EMUREPO}", cwd=tmp_repo, info_widget=info_widget)
        run_bash("git fetch origin", cwd=tmp_repo, info_widget=info_widget)
        run_bash("git fetch emu-repo", cwd=tmp_repo, info_widget=info_widget)
        run_bash("git checkout master", cwd=tmp_repo, info_widget=info_widget)
        run_bash("git reset --hard origin/master", cwd=tmp_repo, info_widget=info_widget)

    append_info(info_widget, "🔄 Generating OSCam SH patch …")

    # Patch Header aus SH TEMP_REPO holen (korrekter Commit!)
    header = get_patch_header(repo_dir=tmp_repo)

    # Diff generieren
    diff = subprocess.getoutput(f"git -C {tmp_repo} diff origin/master..emu-repo/master -- . ':!.github'")
    if not diff.strip():
        diff = "# No changes found"

    # Patch-Datei speichern
    with open(PATCH_OSCAM_FILE, "w") as f:
        f.write(header + "\n" + diff + "\n")
    append_info(info_widget, f"✅ OSCam SH Patch erstellt: {PATCH_OSCAM_FILE}")

    # Optional: Temporäres Verzeichnis aufräumen (wenn gewünscht)
    # shutil.rmtree(tmp_repo)
    # append_info(info_widget, "🧹 Temporary SH repo entfernt")





def patch_emu_git(info_widget):
    append_info(info_widget, "🔄 Patching OSCam-EMU Git …")
    ensure_dir(PATCH_EMU_GIT_DIR)
    run_bash(f"rm -rf {PATCH_EMU_GIT_DIR}", info_widget=info_widget)
    shutil.copytree(TEMP_REPO, PATCH_EMU_GIT_DIR)
    code = run_bash(f"git apply {PATCH_FILE}", cwd=PATCH_EMU_GIT_DIR, info_widget=info_widget)
    append_info(info_widget, "✅ OSCam-EMU Git patched" if code==0 else "❌ Error patching OSCam-EMU Git")

# -----------------------------
# GUI CLASS
# -----------------------------
class PatchManagerGUI(QWidget):
    def __init__(self):
        super().__init__()
        load_config()
        self.setWindowTitle("OSCam Emu Patch Generator – by speedy005")
        self.setGeometry(50,50,1600,900)
        self.default_font = QFont("Arial",12)
        create_icons()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20,20,20,20)

        title = QLabel("OSCam Emu Patch Generator – by speedy005")
        title.setFont(QFont("Arial",28,QFont.Weight.Bold))
        title.setStyleSheet("color:red;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.info_text = QTextEdit()
        self.info_text.setFont(QFont("Courier",14))
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(500)
        self.info_text.setStyleSheet("background-color:black; color:white;")
        layout.addWidget(self.info_text)

        # Options layout
        options_layout = QHBoxLayout()
        self.lang_label = QLabel(TEXTS[LANG]["language_label"])
        options_layout.addWidget(self.lang_label)
        self.language_box = QComboBox()
        self.language_box.addItems(["EN","DE"])
        self.language_box.setFixedWidth(60)
        self.language_box.setCurrentText("DE" if LANG=="de" else "EN")
        self.language_box.currentIndexChanged.connect(self.change_language)
        options_layout.addWidget(self.language_box)

        self.color_label = QLabel(TEXTS[LANG]["color_label"])
        options_layout.addWidget(self.color_label)
        self.color_box = QComboBox()
        self.color_box.addItems(list(DIFF_COLORS.keys()))
        self.color_box.setFixedWidth(100)
        self.color_box.setCurrentText(current_color_name)
        self.color_box.currentIndexChanged.connect(self.change_colors)
        options_layout.addWidget(self.color_box)

        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1,10)
        self.commit_spin.setValue(5)
        self.commit_spin.setPrefix("Commits: ")
        options_layout.addWidget(self.commit_spin)

        # SH Buttons
        self.show_commits_button = QPushButton(TEXTS[LANG]["show_commits"])
        self.show_commits_button.clicked.connect(lambda: self.set_active_button("show_commits") or self.show_commits())
        options_layout.addWidget(self.show_commits_button)

        self.edit_patch_header_button = QPushButton(TEXTS[LANG]["edit_patch_header"])
        self.edit_patch_header_button.clicked.connect(lambda: self.set_active_button("edit_patch_header") or self.edit_patch_header())
        options_layout.addWidget(self.edit_patch_header_button)

        self.patch_oscam_sh_button = QPushButton(TEXTS[LANG]["patch_oscam_sh"])
        self.patch_oscam_sh_button.clicked.connect(lambda: self.set_active_button("patch_oscam_sh") or create_oscam_sh_patch(self.info_text))
        options_layout.addWidget(self.patch_oscam_sh_button)

        self.clean_sh_button = QPushButton(TEXTS[LANG]["clean_sh_folder"])
        self.clean_sh_button.clicked.connect(lambda: self.set_active_button("clean_sh_folder") or clean_oscam_sh_folder(self.info_text))
        options_layout.addWidget(self.clean_sh_button)

        self.patch_emu_git_button = QPushButton(TEXTS[LANG]["patch_emu_git"])
        self.patch_emu_git_button.clicked.connect(lambda: self.set_active_button("patch_emu_git") or patch_emu_git(self.info_text))
        options_layout.addWidget(self.patch_emu_git_button)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Main Buttons Grid
        grid_layout = QGridLayout()
        actions = [
            ("patch_create", lambda: create_patch(self.info_text)),
            ("patch_renew", lambda: create_patch(self.info_text)),
            ("patch_check", self.check_patch),
            ("patch_apply", self.apply_patch),
            ("git_status", self.show_commits),
            ("patch_zip", self.zip_patch),
            ("backup_old", self.backup_old_patch),
            ("clean_folder", self.clean_patch_folder),
            ("change_old_dir", self.change_old_patch_dir),
            ("exit", self.close_with_confirm)
        ]
        self.buttons = {}
        for idx,(key,func) in enumerate(actions):
            btn = QPushButton(TEXTS[LANG][key])
            btn.setIcon(get_icon_for(TEXTS[LANG][key]))
            self.buttons[key] = btn
            btn.setFont(QFont("Arial",16))
            btn.setMinimumHeight(60)
            btn.clicked.connect(lambda checked=False, k=key, f=func: self.set_active_button(k) or f())
            btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;")
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            row,col = divmod(idx,5)
            grid_layout.addWidget(btn,row,col)
        layout.addLayout(grid_layout)
        self.setLayout(layout)

    # ----------------- ACTIVE BUTTON LOGIK ----------------
    def set_active_button(self, active_key):
        for key, btn in self.buttons.items():
            if key == active_key:
                btn.setStyleSheet(f"background-color:#FFD700; color:black; border-radius:10px;")
            else:
                btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;")
        for key, btn in [("patch_oscam_sh", self.patch_oscam_sh_button),
                         ("clean_sh_folder", self.clean_sh_button),
                         ("show_commits", self.show_commits_button),
                         ("edit_patch_header", self.edit_patch_header_button),
                         ("patch_emu_git", self.patch_emu_git_button)]:
            if key == active_key:
                btn.setStyleSheet(f"background-color:#FFD700; color:black; border-radius:10px;")
            else:
                btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;")

    # ----------------- color/language ----------------
    def change_colors(self):
        global current_diff_colors, current_color_name
        current_color_name = self.color_box.currentText()
        current_diff_colors = DIFF_COLORS[current_color_name]
        self.set_active_button(None)
        for btn in self.buttons.values():
            btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;")
        for btn in [self.patch_oscam_sh_button, self.clean_sh_button,
                    self.show_commits_button, self.edit_patch_header_button,
                    self.patch_emu_git_button]:
            btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;")
        save_config()

    def change_language(self):
        global LANG
        LANG = "de" if self.language_box.currentText()=="DE" else "en"
        save_config()
        self.lang_label.setText(TEXTS[LANG]["language_label"])
        self.color_label.setText(TEXTS[LANG]["color_label"])
        self.show_commits_button.setText(TEXTS[LANG]["show_commits"])
        self.edit_patch_header_button.setText(TEXTS[LANG]["edit_patch_header"])
        self.patch_oscam_sh_button.setText(TEXTS[LANG]["patch_oscam_sh"])
        self.clean_sh_button.setText(TEXTS[LANG]["clean_sh_folder"])
        self.patch_emu_git_button.setText(TEXTS[LANG]["patch_emu_git"])
        for key,btn in self.buttons.items(): btn.setText(TEXTS[LANG][key])

    # ----------------- PATCH OPERATIONS ----------------
    def check_patch(self):
        if not os.path.exists(PATCH_FILE):
            append_info(self.info_text,"❌ Patch file does not exist!")
            return
        code = run_bash(f"git apply --check {PATCH_FILE}", cwd=TEMP_REPO, info_widget=self.info_text)
        append_info(self.info_text,"✅ Patch is valid" if code==0 else "❌ Patch cannot be applied")

    def apply_patch(self):
        if not os.path.exists(PATCH_FILE):
            append_info(self.info_text,"❌ Patch file does not exist!")
            return
        code = run_bash(f"git apply {PATCH_FILE}", cwd=TEMP_REPO, info_widget=self.info_text)
        append_info(self.info_text,"✅ Patch applied" if code==0 else "❌ Error applying patch")

    def zip_patch(self):
        try:
            with zipfile.ZipFile(ZIP_FILE, 'w') as zipf:
                zipf.write(PATCH_FILE, os.path.basename(PATCH_FILE))
            append_info(self.info_text,f"📦 Patch zipped: {ZIP_FILE}")
        except Exception as e:
            append_info(self.info_text,f"❌ Error zipping patch: {str(e)}")

    def backup_old_patch(self):
        ensure_dir(OLD_PATCH_DIR)
        if os.path.exists(OLD_PATCH_FILE):
            copy_file(OLD_PATCH_FILE, ALT_PATCH_FILE)
        copy_file(PATCH_FILE, OLD_PATCH_FILE)
        append_info(self.info_text,f"💾 Patch backed up: {OLD_PATCH_DIR}")

    def clean_patch_folder(self):
        append_info(self.info_text, "🧹 Cleaning folder …")
        for f in os.listdir(PATCH_DIR):
            if f in NEVER_DELETE: append_info(self.info_text,f"⚠️ Skipping protected: {f}"); continue
            path = os.path.join(PATCH_DIR, f)
            try: shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
            except Exception as e: append_info(self.info_text,f"❌ Error deleting {f}: {str(e)}")
        append_info(self.info_text, "✅ Patch folder cleaned")

    def show_commits(self):
        ensure_dir(TEMP_REPO)
        if not os.path.exists(os.path.join(TEMP_REPO, ".git")):
            append_info(self.info_text, "❌ No Git repository! Create patch first.")
            return
        try:
            commits = subprocess.getoutput(f"git -C {TEMP_REPO} log -{self.commit_spin.value()} --oneline")
            append_info(self.info_text, f"📄 Last {self.commit_spin.value()} commit(s):\n{commits}" if commits else "⚠️ No commits found")
        except Exception as e:
            append_info(self.info_text, f"❌ Error fetching commits: {str(e)}")

    def edit_patch_header(self):
        if not os.path.exists(PATCH_FILE):
            append_info(self.info_text,"❌ Patch file does not exist!")
            return
        with open(PATCH_FILE,"r") as f: content = f.read()
        dialog = QDialog(self)
        dialog.setWindowTitle(TEXTS[LANG]["edit_patch_header"])
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setText(content)
        layout.addWidget(text_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(lambda: self.save_patch_header(text_edit.toPlainText(), dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        dialog.resize(800,600)
        dialog.exec()

    def save_patch_header(self, text, dialog):
        with open(PATCH_FILE,"w") as f: f.write(text)
        append_info(self.info_text,"✅ Patch header updated")
        dialog.accept()

    def change_old_patch_dir(self):
        global OLD_PATCH_DIR, OLD_PATCH_FILE, ALT_PATCH_FILE
        new_dir = QFileDialog.getExistingDirectory(self, "Select folder for old patch", OLD_PATCH_DIR)
        if new_dir:
            OLD_PATCH_DIR = new_dir
            OLD_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.patch")
            ALT_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.altpatch")
            append_info(self.info_text,f"✅ Path changed: {OLD_PATCH_DIR}")
        else:
            append_info(self.info_text,"⚠️ Change cancelled")

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
# START
# -----------------------------
if __name__=="__main__":
    ensure_dir(ICON_DIR)
    ensure_dir(PATCH_DIR)
    ensure_dir(TEMP_REPO)
    load_config()
    app = QApplication(sys.argv)
    window = PatchManagerGUI()  # GUI wie vorher
    window.show()
    check_tools(window.info_text)
    sys.exit(app.exec())

