#!/bin/bash
# oscam-patch-manager-gui.sh – Saubere moderne GUI für OSCam Patch Management

PATCH_DIR=/opt/patch/oscam-patching
PATCH_FILE="$PATCH_DIR/oscam-emu.patch"
ZIP_FILE="$PATCH_DIR/oscam-emu.zip"

# Flexibler Alter Patch Pfad
OLD_PATCH_DIR_DEFAULT="/opt/s3_neu/support/patches"
OLD_PATCH_DIR="$OLD_PATCH_DIR_DEFAULT"
OLD_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.patch"
ALT_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.altpatch"

EMUREPO="https://github.com/oscam-mirror/oscam-emu"
STREAMREPO="https://git.streamboard.tv/common/oscam"
export NO_AT_BRIDGE=1

ICON_DIR="$PATCH_DIR/icons"
ICON_SIZE=64

# --- Prüfen, ob Tools installiert sind ---
REQUIRED_TOOLS=(zenity git zip convert)
check_tools() {
    MISSING=()
    for tool in "${REQUIRED_TOOLS[@]}"; do
        command -v $tool >/dev/null 2>&1 || MISSING+=($tool)
    done
    if [ ${#MISSING[@]} -gt 0 ]; then
        zenity --question --width=400 --height=200 \
            --text="Folgende Tools fehlen: ${MISSING[*]}\nInstallieren?" \
            --ok-label="Ja" --cancel-label="Nein"
        [ $? -eq 0 ] && sudo apt update && sudo apt install -y "${MISSING[@]}" || { zenity --error --text="Abbruch: Tools fehlen"; exit 1; }
    fi
}
check_tools

# --- Icons automatisch erstellen ---
declare -A ICONS=(
    [patch]="green" [renew]="orange" [check]="blue" [apply]="purple"
    [status]="cyan" [zip]="yellow" [save]="magenta" [clean]="red"
    [exit]="grey" [folder]="brown"
)
mkdir -p "$ICON_DIR"
sudo chown -R $USER:$USER "$ICON_DIR"
for NAME in "${!ICONS[@]}"; do
    OUTPUT="$ICON_DIR/$NAME.png"
    [ ! -f "$OUTPUT" ] && convert -size ${ICON_SIZE}x${ICON_SIZE} xc:${ICONS[$NAME]} \
        -gravity center -pointsize 20 -fill white -annotate 0 "$NAME" "$OUTPUT"
done

# --- Patch Header ---
generate_patch_header() {
    echo "patch version: 2.26.01-11920-803 ($(git rev-parse --short HEAD 2>/dev/null))
patch date: $(date -u '+%Y-%m-%d %H:%M:%S UTC (%z)')
patch modified By speedy005 ($(date '+%d/%m/%Y'))"
}

# --- Funktionen ---
create_patch() {
    cd "$PATCH_DIR" || return
    git fetch origin
    git fetch emu-repo

    # Unterschiede prüfen
    DIFF_CONTENT=$(git diff origin/master..emu-repo/master)
    if [ -z "$DIFF_CONTENT" ]; then
        PATCH_HEADER=$(generate_patch_header)
        echo -e "$PATCH_HEADER\n" > "$PATCH_FILE"
        chmod 644 "$PATCH_FILE"
        zenity --info --title="Patch erstellen" --text="Keine Änderungen gefunden. Patch enthält nur Header."
        return
    fi

    # Patch schreiben
    echo "$DIFF_CONTENT" > "$PATCH_FILE"
    PATCH_HEADER=$(generate_patch_header)
    TMP_FILE=$(mktemp)
    printf "%s\n\n" "$PATCH_HEADER" > "$TMP_FILE"
    cat "$PATCH_FILE" >> "$TMP_FILE"
    mv "$TMP_FILE" "$PATCH_FILE"
    chmod 644 "$PATCH_FILE"
    zenity --info --title="Patch erstellen ✅" --text="Patch erstellt mit Änderungen."
}
renew_patch() { create_patch; }
check_patch() { git apply --check "$PATCH_FILE"; zenity --info --title="Patch Check ✅" --text="Patchprüfung abgeschlossen."; }
apply_patch() { git apply "$PATCH_FILE"; zenity --info --title="Patch angewendet ✅" --text="Patch wurde angewendet."; }
show_status() { git status | zenity --text-info --width=900 --height=600 --title="Git Status"; }
zip_patch() { [ -f "$PATCH_FILE" ] && zip -r "$ZIP_FILE" "$PATCH_FILE"; zenity --info --title="ZIP ✅" --text="Patch in ZIP-Datei gepackt."; }

overwrite_old_patch() {
    [ ! -f "$PATCH_FILE" ] && zenity --error --text="Neuer Patch existiert nicht!" && return
    [ ! -d "$OLD_PATCH_DIR" ] && sudo mkdir -p "$OLD_PATCH_DIR" && sudo chown $USER:$USER "$OLD_PATCH_DIR"
    [ -f "$OLD_PATCH_FILE" ] && sudo mv "$OLD_PATCH_FILE" "$ALT_PATCH_FILE" && sudo chown $USER:$USER "$ALT_PATCH_FILE" && chmod 644 "$ALT_PATCH_FILE"
    sudo cp "$PATCH_FILE" "$OLD_PATCH_FILE" && sudo chown $USER:$USER "$OLD_PATCH_FILE" && chmod 644 "$OLD_PATCH_FILE"
    zenity --info --title="Patch gesichert ✅" --text="Alter Patch gesichert, neuer Patch kopiert."
}

change_old_patch_dir() {
    NEW_DIR=$(zenity --file-selection --directory --title="Wähle den Ordner für den alten Patch" --filename="$OLD_PATCH_DIR/")
    if [ -n "$NEW_DIR" ]; then
        OLD_PATCH_DIR="$NEW_DIR"
        OLD_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.patch"
        ALT_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.altpatch"
        zenity --info --title="Pfad aktualisiert ✅" --text="Alter Patch Ordner geändert nach:\n$OLD_PATCH_DIR"
    else
        zenity --warning --title="Abgebrochen ⚠️" --text="Pfadänderung abgebrochen."
    fi
}

clean_patch_folder() {
    FILES=$(find "$PATCH_DIR" -mindepth 1 \
        ! -name "oscam-patch-manager.sh" \
        ! -name "oscam-patch-manager-gui.sh" \
        ! -name "icons" \
        ! -path "$PATCH_DIR/.git*")
    [ -z "$FILES" ] && zenity --info --text="Keine Dateien zum Löschen gefunden." && return
    echo "$FILES" | zenity --text-info --width=900 --height=600 --title="Zu löschende Dateien"
    zenity --question --text="Alle Dateien löschen (Skripte, Icons und Git-Ordner bleiben erhalten)?" --ok-label="Ja" --cancel-label="Nein"
    [ $? -eq 0 ] && echo "$FILES" | xargs -d '\n' rm -rf && zenity --info --text="Ordner aufgeräumt!" || zenity --info --text="Abgebrochen."
}

# --- Menü ---
while true; do
    CHOICE=$(zenity --list --radiolist \
        --title="🛠 OSCam Patch Manager" \
        --text="<b>Wähle eine Aktion:</b>" \
        --width=900 --height=650 \
        --column="Auswahl" --column="Aktion" \
        TRUE "🟢 Patch erstellen" \
        FALSE "♻️ Patch erneuern" \
        FALSE "🔍 Patch prüfen" \
        FALSE "⚡ Patch anwenden" \
        FALSE "📄 Git Status anzeigen" \
        FALSE "📦 Patch in ZIP-Datei packen" \
        FALSE "💾 Alter Patch sichern" \
        FALSE "🗑️ Ordner aufräumen" \
        FALSE "🔧 Alten Patch Ordner ändern" \
        FALSE "❌ Beenden" \
        --hide-header)
    [ $? -ne 0 ] && exit 0

    case "$CHOICE" in
        "🟢 Patch erstellen") create_patch ;;
        "♻️ Patch erneuern") renew_patch ;;
        "🔍 Patch prüfen") check_patch ;;
        "⚡ Patch anwenden") apply_patch ;;
        "📄 Git Status anzeigen") show_status ;;
        "📦 Patch in ZIP-Datei packen") zip_patch ;;
        "💾 Alter Patch sichern") overwrite_old_patch ;;
        "🗑️ Ordner aufräumen") clean_patch_folder ;;
        "🔧 Alten Patch Ordner ändern") change_old_patch_dir ;;
        "❌ Beenden") exit 0 ;;
    esac
done

# --- Berechtigungen setzen ---
find "$PATCH_DIR" -mindepth 1 ! -path "$PATCH_DIR/.git*" \
    ! -name "oscam-patch-manager.sh" \
    ! -name "oscam-patch-manager-gui.sh" \
    ! -name "icons" \
    ! -name "oscam-emu.patch" -exec chmod -R 755 {} +
chmod 644 "$PATCH_FILE"

