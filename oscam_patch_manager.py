#!/usr/bin/env python3
import os, sys, subprocess, shutil, zipfile, json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QVBoxLayout, QGridLayout,
    QPushButton, QSizePolicy, QMessageBox, QFileDialog, QComboBox,
    QHBoxLayout, QSpinBox, QDialog, QDialogButtonBox
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
ZIP_FILE = os.path.join(PATCH_DIR, "oscam-emu.zip")
OLD_PATCH_DIR_DEFAULT = "/opt/s3_neu/support/patches"
OLD_PATCH_DIR = OLD_PATCH_DIR_DEFAULT
OLD_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.patch")
ALT_PATCH_FILE = os.path.join(OLD_PATCH_DIR, "oscam-emu.altpatch")
PATCH_MODIFIER = "speedy005"
EMUREPO = "https://github.com/oscam-mirror/oscam-emu.git"
STREAMREPO = "https://git.streamboard.tv/common/oscam.git"
REQUIRED_TOOLS = ["git", "zip", "unzip", "python3", "pip3"]

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
        "change_old_dir": "Change Old Patch Dir",
        "edit_patch_header": "Edit Patch Header",
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
        "change_old_dir": "Pfad zu s3 ändern",
        "edit_patch_header": "Patch Header bearbeiten",
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

# -----------------------------
# CONFIG HELPERS
# -----------------------------
def load_config():
    global LANG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                LANG = cfg.get("language", LANG)
        except:
            pass

def save_config():
    cfg = {"language": LANG}
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
    except:
        pass

# -----------------------------
# UTILITY FUNCTIONS
# -----------------------------
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def append_info(info_widget, text):
    info_widget.append(text)
    info_widget.moveCursor(QTextCursor.MoveOperation.End)

def run_bash(cmd, cwd=None, info_widget=None):
    if info_widget: append_info(info_widget, f"▶ {cmd}")
    ensure_dir(cwd)
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
        if info_widget: append_info(info_widget, TEXTS[LANG]["missing_tools"].format(", ".join(missing)))
    else:
        if info_widget: append_info(info_widget, TEXTS[LANG]["all_tools_ok"])
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
        TEXTS[LANG]["change_old_dir"]: "brown",
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
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0,0), name.split()[0], font=fnt)
                w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
            else:
                w, h = draw.textsize(name.split()[0], font=fnt)
            draw.text(((ICON_SIZE-w)/2,(ICON_SIZE-h)/2), name.split()[0], font=fnt, fill="white")
            img.save(file_name)

def get_icon_for(name):
    safe_name = name.replace(" ", "_").replace("/","_").replace("\\","_")
    path = os.path.join(ICON_DIR, safe_name + ".png")
    if os.path.exists(path):
        return QIcon(QPixmap(path))
    return QIcon()

# -----------------------------
# OSCAM VERSION FUNCTIONS
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

def get_patch_header():
    patch_date = subprocess.getoutput("date -u '+%Y-%m-%d %H:%M:%S UTC (%z)'")
    modified_date = subprocess.getoutput("date '+%d/%m/%Y'")
    commit_hash = "N/A"
    if os.path.exists(os.path.join(TEMP_REPO, ".git")):
        try:
            commit_hash = subprocess.getoutput(f"git -C {TEMP_REPO} rev-parse --short HEAD").strip()
        except: pass
    osc_version = get_oscam_version_from_globals()
    if not osc_version:
        osc_version = "2.26.01-0"
    patch_version = f"{osc_version}-802"
    return f"patch version: {patch_version} ({commit_hash})\npatch date: {patch_date}\npatch modified by {PATCH_MODIFIER} ({modified_date})\n"

# -----------------------------
# PATCH FUNCTIONS
# -----------------------------
def create_patch(info_widget, commit_count=10):
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
    append_info(info_widget, "🔄 Checking out master and resetting …")
    run_bash("git checkout master", cwd=TEMP_REPO, info_widget=info_widget)
    run_bash("git reset --hard origin/master", cwd=TEMP_REPO, info_widget=info_widget)

    header = get_patch_header()
    append_info(info_widget, "🔄 Generating patch diff …")
    process = subprocess.Popen(
        f"git -C {TEMP_REPO} diff origin/master..emu-repo/master",
        shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    diff_lines = []
    for line in process.stdout:
        line = line.rstrip()
        diff_lines.append(line + "\n")
        append_info(info_widget, line)
    process.wait()
    if not diff_lines:
        diff_lines = ["# No changes found\n"]
        append_info(info_widget, "# No changes found")

    with open(PATCH_FILE, "w") as f:
        f.write(header + "\n")
        f.writelines(diff_lines)
    append_info(info_widget, f"✅ Patch created: {PATCH_FILE}")

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

        # -------------------------
        # Titel
        # -------------------------
        title = QLabel("OSCam Emu Patch Generator – by speedy005")
        title.setFont(QFont("Arial",28,QFont.Weight.Bold))
        title.setStyleSheet("color:red;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # -------------------------
        # Info-Text
        # -------------------------
        self.info_text = QTextEdit()
        self.info_text.setFont(QFont("Courier",14))
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(500)
        self.info_text.setStyleSheet("background-color:black; color:white;")
        layout.addWidget(self.info_text)

        # -------------------------
        # Optionen (eine Zeile)
        # -------------------------
        options_layout = QHBoxLayout()
        options_layout.setSpacing(10)

        # Sprache
        self.lang_label = QLabel(TEXTS[LANG]["language_label"])
        options_layout.addWidget(self.lang_label)
        self.language_box = QComboBox()
        self.language_box.addItems(["EN","DE"])
        self.language_box.setFixedWidth(60)
        self.language_box.setCurrentText("DE" if LANG=="de" else "EN")
        self.language_box.currentIndexChanged.connect(self.change_language)
        options_layout.addWidget(self.language_box)

        # Farbe
        self.color_label = QLabel(TEXTS[LANG]["color_label"])
        options_layout.addWidget(self.color_label)
        self.color_box = QComboBox()
        self.color_box.addItems(list(DIFF_COLORS.keys()))
        self.color_box.setFixedWidth(100)
        self.color_box.currentIndexChanged.connect(self.change_colors)
        options_layout.addWidget(self.color_box)

        # Commit SpinBox
        self.commit_spin = QSpinBox()
        self.commit_spin.setRange(1,10)
        self.commit_spin.setValue(5)
        self.commit_spin.setPrefix("Commits: ")
        options_layout.addWidget(self.commit_spin)

        # Show Commits
        self.show_commits_button = QPushButton(TEXTS[LANG]["show_commits"])
        self.show_commits_button.clicked.connect(self.show_commits)
        options_layout.addWidget(self.show_commits_button)

        # Patch Header bearbeiten
        self.edit_patch_header_button = QPushButton(TEXTS[LANG]["edit_patch_header"])
        self.edit_patch_header_button.clicked.connect(self.edit_patch_header)
        options_layout.addWidget(self.edit_patch_header_button)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        # -------------------------
        # Action-Buttons (Grid)
        # -------------------------
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        actions = [
            ("patch_create", lambda: create_patch(self.info_text, self.commit_spin.value())),
            ("patch_renew", lambda: create_patch(self.info_text, self.commit_spin.value())),
            ("patch_check", lambda: self.check_patch()),
            ("patch_apply", lambda: self.apply_patch()),
            ("git_status", lambda: self.show_commits()),
            ("patch_zip", lambda: self.zip_patch()),
            ("backup_old", lambda: self.backup_old_patch()),
            ("clean_folder", lambda: self.clean_patch_folder()),
            ("change_old_dir", lambda: self.change_old_patch_dir()),
            ("exit", self.close_with_confirm)
        ]
        self.buttons = {}
        for idx,(key,func) in enumerate(actions):
            btn = QPushButton(TEXTS[LANG][key])
            btn.setIcon(get_icon_for(TEXTS[LANG][key]))
            self.buttons[key] = btn
            btn.setFont(QFont("Arial",16))
            btn.setMinimumHeight(60)
            btn.clicked.connect(func)
            btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;")
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            row,col = divmod(idx,5)
            grid_layout.addWidget(btn,row,col)
        layout.addLayout(grid_layout)

        self.setLayout(layout)

    # -------------------------
    # Color/Language
    # -------------------------
    def change_colors(self):
        selected = self.color_box.currentText()
        global current_diff_colors
        current_diff_colors = DIFF_COLORS[selected]
        for btn in self.buttons.values():
            btn.setStyleSheet(f"background-color:{current_diff_colors['bg']}; color:{current_diff_colors['text']}; border-radius:10px;")

    def change_language(self):
        global LANG
        LANG = "de" if self.language_box.currentText()=="DE" else "en"
        save_config()
        self.lang_label.setText(TEXTS[LANG]["language_label"])
        self.color_label.setText(TEXTS[LANG]["color_label"])
        self.show_commits_button.setText(TEXTS[LANG]["show_commits"])
        self.edit_patch_header_button.setText(TEXTS[LANG]["edit_patch_header"])
        for key,btn in self.buttons.items():
            btn.setText(TEXTS[LANG][key])

    # -------------------------
    # Patch Functions
    # -------------------------
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
        protected = [
            "oscam_patch_manager.py",
            "oscam-patch-manager.sh",
            "oscam-patch-manager-gui.sh",
            "icons"
        ]
        for f in os.listdir(PATCH_DIR):
            if f in protected:
                append_info(self.info_text, f"⚠️ Skipping protected: {f}")
                continue
            path = os.path.join(PATCH_DIR, f)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                append_info(self.info_text, f"❌ Error deleting {f}: {str(e)}")
        append_info(self.info_text, "✅ Patch folder cleaned")

    # -------------------------
    # Commit Anzeige
    # -------------------------
    def show_commits(self):
        ensure_dir(TEMP_REPO)
        if not os.path.exists(os.path.join(TEMP_REPO, ".git")):
            append_info(self.info_text, "❌ No Git repository! Create patch first.")
            return
        try:
            commits = subprocess.getoutput(f"git -C {TEMP_REPO} log -{self.commit_spin.value()} --oneline")
            if not commits.strip():
                append_info(self.info_text, "⚠️ No commits found")
            else:
                append_info(self.info_text, f"📄 Last {self.commit_spin.value()} commit(s):\n{commits}")
        except Exception as e:
            append_info(self.info_text, f"❌ Error fetching commits: {str(e)}")

    # -------------------------
    # Patch Header Editor
    # -------------------------
    def edit_patch_header(self):
        if not os.path.exists(PATCH_FILE):
            append_info(self.info_text,"❌ Patch file does not exist!")
            return
        with open(PATCH_FILE,"r") as f:
            content = f.read()
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
        with open(PATCH_FILE,"w") as f:
            f.write(text)
        append_info(self.info_text,"✅ Patch header updated")
        dialog.accept()

    # -------------------------
    # Old Patch Dir
    # -------------------------
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

    # -------------------------
    # Close
    # -------------------------
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
    window = PatchManagerGUI()
    window.show()
    missing = check_tools(window.info_text)
    sys.exit(app.exec())

