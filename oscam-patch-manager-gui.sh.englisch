#!/bin/bash
# oscam-patch-manager-gui.sh – Clean modern GUI for OSCam Patch Management

PATCH_DIR=/opt/patch/oscam-patching
PATCH_FILE="$PATCH_DIR/oscam-emu.patch"
ZIP_FILE="$PATCH_DIR/oscam-emu.zip"

# Flexible Old Patch Path
OLD_PATCH_DIR_DEFAULT="/opt/s3_neu/support/patches"
OLD_PATCH_DIR="$OLD_PATCH_DIR_DEFAULT"
OLD_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.patch"
ALT_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.altpatch"

EMUREPO="https://github.com/oscam-mirror/oscam-emu"
STREAMREPO="https://git.streamboard.tv/common/oscam"
export NO_AT_BRIDGE=1

ICON_DIR="$PATCH_DIR/icons"
ICON_SIZE=64

# --- Check required tools ---
REQUIRED_TOOLS=(zenity git zip convert)
check_tools() {
    MISSING=()
    for tool in "${REQUIRED_TOOLS[@]}"; do
        command -v $tool >/dev/null 2>&1 || MISSING+=($tool)
    done
    if [ ${#MISSING[@]} -gt 0 ]; then
        zenity --question --width=400 --height=200 \
            --text="The following tools are missing: ${MISSING[*]}\nInstall them?" \
            --ok-label="Yes" --cancel-label="No"
        [ $? -eq 0 ] && sudo apt update && sudo apt install -y "${MISSING[@]}" || { zenity --error --text="Aborting: tools missing"; exit 1; }
    fi
}
check_tools

# --- Automatically create icons ---
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
    echo "patch version: 2.26.01-11920-802 ($(git rev-parse --short HEAD 2>/dev/null))
patch date: $(date -u '+%Y-%m-%d %H:%M:%S UTC (%z)')
patch modified by speedy005 ($(date '+%d/%m/%Y'))"
}

# --- Functions ---
create_patch() {
    cd "$PATCH_DIR" || return
    git fetch origin
    git fetch emu-repo

    # Check differences
    DIFF_CONTENT=$(git diff origin/master..emu-repo/master)
    if [ -z "$DIFF_CONTENT" ]; then
        PATCH_HEADER=$(generate_patch_header)
        echo -e "$PATCH_HEADER\n" > "$PATCH_FILE"
        chmod 644 "$PATCH_FILE"
        zenity --info --title="Create Patch" --text="No changes found. Patch contains only header."
        return
    fi

    # Write patch
    echo "$DIFF_CONTENT" > "$PATCH_FILE"
    PATCH_HEADER=$(generate_patch_header)
    TMP_FILE=$(mktemp)
    printf "%s\n\n" "$PATCH_HEADER" > "$TMP_FILE"
    cat "$PATCH_FILE" >> "$TMP_FILE"
    mv "$TMP_FILE" "$PATCH_FILE"
    chmod 644 "$PATCH_FILE"
    zenity --info --title="Create Patch ✅" --text="Patch created with changes."
}

renew_patch() { create_patch; }
check_patch() { git apply --check "$PATCH_FILE"; zenity --info --title="Patch Check ✅" --text="Patch check completed."; }
apply_patch() { git apply "$PATCH_FILE"; zenity --info --title="Patch Applied ✅" --text="Patch has been applied."; }
show_status() { git status | zenity --text-info --width=900 --height=600 --title="Git Status"; }
zip_patch() { [ -f "$PATCH_FILE" ] && zip -r "$ZIP_FILE" "$PATCH_FILE"; zenity --info --title="ZIP ✅" --text="Patch packed into ZIP file."; }

overwrite_old_patch() {
    [ ! -f "$PATCH_FILE" ] && zenity --error --text="New patch does not exist!" && return
    [ ! -d "$OLD_PATCH_DIR" ] && sudo mkdir -p "$OLD_PATCH_DIR" && sudo chown $USER:$USER "$OLD_PATCH_DIR"
    [ -f "$OLD_PATCH_FILE" ] && sudo mv "$OLD_PATCH_FILE" "$ALT_PATCH_FILE" && sudo chown $USER:$USER "$ALT_PATCH_FILE" && chmod 644 "$ALT_PATCH_FILE"
    sudo cp "$PATCH_FILE" "$OLD_PATCH_FILE" && sudo chown $USER:$USER "$OLD_PATCH_FILE" && chmod 644 "$OLD_PATCH_FILE"
    zenity --info --title="Patch Saved ✅" --text="Old patch backed up, new patch copied."
}

change_old_patch_dir() {
    NEW_DIR=$(zenity --file-selection --directory --title="Select folder for old patch" --filename="$OLD_PATCH_DIR/")
    if [ -n "$NEW_DIR" ]; then
        OLD_PATCH_DIR="$NEW_DIR"
        OLD_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.patch"
        ALT_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.altpatch"
        zenity --info --title="Path Updated ✅" --text="Old patch folder changed to:\n$OLD_PATCH_DIR"
    else
        zenity --warning --title="Cancelled ⚠️" --text="Path change cancelled."
    fi
}

clean_patch_folder() {
    FILES=$(find "$PATCH_DIR" -mindepth 1 \
        ! -name "oscam-patch-manager.sh" \
        ! -name "oscam-patch-manager-gui.sh" \
        ! -name "icons" \
        ! -path "$PATCH_DIR/.git*")
    [ -z "$FILES" ] && zenity --info --text="No files to delete." && return
    echo "$FILES" | zenity --text-info --width=900 --height=600 --title="Files to delete"
    zenity --question --text="Delete all files (scripts, icons and git folders will remain)?" --ok-label="Yes" --cancel-label="No"
    [ $? -eq 0 ] && echo "$FILES" | xargs -d '\n' rm -rf && zenity --info --text="Folder cleaned!" || zenity --info --text="Cancelled."
}

# --- Menu ---
while true; do
    CHOICE=$(zenity --list --radiolist \
        --title="🛠 OSCam Patch Manager" \
        --text="<b>Select an action:</b>" \
        --width=900 --height=650 \
        --column="Select" --column="Action" \
        TRUE "🟢 Create Patch" \
        FALSE "♻️ Renew Patch" \
        FALSE "🔍 Check Patch" \
        FALSE "⚡ Apply Patch" \
        FALSE "📄 Show Git Status" \
        FALSE "📦 Pack Patch to ZIP" \
        FALSE "💾 Backup Old Patch" \
        FALSE "🗑️ Clean Folder" \
        FALSE "🔧 Change Old Patch Folder" \
        FALSE "❌ Exit" \
        --hide-header)
    [ $? -ne 0 ] && exit 0

    case "$CHOICE" in
        "🟢 Create Patch") create_patch ;;
        "♻️ Renew Patch") renew_patch ;;
        "🔍 Check Patch") check_patch ;;
        "⚡ Apply Patch") apply_patch ;;
        "📄 Show Git Status") show_status ;;
        "📦 Pack Patch to ZIP") zip_patch ;;
        "💾 Backup Old Patch") overwrite_old_patch ;;
        "🗑️ Clean Folder") clean_patch_folder ;;
        "🔧 Change Old Patch Folder") change_old_patch_dir ;;
        "❌ Exit") exit 0 ;;
    esac
done

# --- Set Permissions ---
find "$PATCH_DIR" -mindepth 1 ! -path "$PATCH_DIR/.git*" \
    ! -name "oscam-patch-manager.sh" \
    ! -name "oscam-patch-manager-gui.sh" \
    ! -name "icons" \
    ! -name "oscam-emu.patch" -exec chmod -R 755 {} +
chmod 644 "$PATCH_FILE"

