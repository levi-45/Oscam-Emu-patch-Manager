#!/bin/bash
# oscam-patch-manager.sh
# Interaktives Skript zum Erstellen, Erneuern, Prüfen, Anwenden, Archivieren und Aufräumen von OSCam EMU-Patches
# Alles unter /opt/patch/oscam-patching
# Git intakt, Patch editierbar, andere Dateien chmod 755
# Neuer Patch immer mit Header oben, alter Patch als oscam-emu.altpatch gesichert

PATCH_DIR=/opt/patch/oscam-patching
PATCH_FILE="$PATCH_DIR/oscam-emu.patch"
ZIP_FILE="$PATCH_DIR/oscam-emu.zip"
OLD_PATCH_DIR=/opt/s3_neu/support/patches
OLD_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.patch"
ALT_PATCH_FILE="$OLD_PATCH_DIR/oscam-emu.altpatch"
EMUREPO="https://github.com/oscam-mirror/oscam-emu"
STREAMREPO="https://git.streamboard.tv/common/oscam"

# Sicherstellen, dass der Ordner existiert
sudo mkdir -p "$PATCH_DIR"
sudo chown -R $USER:$USER "$PATCH_DIR"
cd "$PATCH_DIR" || { echo "Fehler: Konnte $PATCH_DIR nicht betreten"; exit 1; }

# Prüfen, ob Git-Repo existiert
if [ ! -d ".git" ]; then
    echo "Kein Git-Repo gefunden. Klone OSCam master in temporäres Verzeichnis..."
    TMPDIR=$(mktemp -d)
    git clone "$STREAMREPO" "$TMPDIR" || exit 1
    cp -r "$TMPDIR/." "$PATCH_DIR"
    rm -rf "$TMPDIR"
    echo "OSCam master Repo erfolgreich initialisiert."
else
    echo "Git-Repository existiert bereits, kein Klonen nötig."
fi

# EMU-Repo als Remote hinzufügen, falls noch nicht vorhanden
if ! git remote | grep -q "^emu-repo$"; then
    echo "EMU-Repo als Remote hinzufügen..."
    git remote add emu-repo "$EMUREPO"
fi

git fetch emu-repo

# Header für Patch
generate_patch_header() {
    echo "patch version: 2.26.01-11920-802 (53e664fa)
patch date: $(date -u '+%Y-%m-%d %H:%M:%S UTC (%z)')
patch modified By speedy005 ($(date '+%d/%m/%Y'))"
}

# Funktionen
create_patch() {
    git checkout master
    git pull origin master
    git fetch emu-repo
    git diff master..emu-repo/master > "$PATCH_FILE"

    PATCH_HEADER=$(generate_patch_header)
    TMP_FILE=$(mktemp)
    printf "%s\n\n" "$PATCH_HEADER" > "$TMP_FILE"
    cat "$PATCH_FILE" >> "$TMP_FILE"
    mv "$TMP_FILE" "$PATCH_FILE"

    chmod 644 "$PATCH_FILE"
    echo "Patch erstellt mit Header: $PATCH_FILE"
}

renew_patch() {
    git checkout master
    git pull origin master
    git fetch emu-repo
    git diff master..emu-repo/master > "$PATCH_FILE"

    PATCH_HEADER=$(generate_patch_header)
    TMP_FILE=$(mktemp)
    printf "%s\n\n" "$PATCH_HEADER" > "$TMP_FILE"
    cat "$PATCH_FILE" >> "$TMP_FILE"
    mv "$TMP_FILE" "$PATCH_FILE"

    chmod 644 "$PATCH_FILE"
    echo "Patch erneuert mit Header: $PATCH_FILE"
}

check_patch() {
    git apply --check "$PATCH_FILE"
    echo "Patchprüfung abgeschlossen."
}

apply_patch() {
    git apply "$PATCH_FILE"
    echo "Patch angewendet."
}

show_status() {
    git status
}

zip_patch() {
    if [ -f "$PATCH_FILE" ]; then
        zip -r "$ZIP_FILE" "$PATCH_FILE"
        echo "Patch in ZIP-Datei gepackt: $ZIP_FILE"
    else
        echo "Fehler: Patch-Datei existiert nicht."
    fi
}

overwrite_old_patch() {
    if [ ! -f "$PATCH_FILE" ]; then
        echo "Fehler: Neuer Patch existiert nicht."
        return
    fi

    # Zielordner erstellen falls nicht vorhanden
    if [ ! -d "$OLD_PATCH_DIR" ]; then
        echo "Zielordner $OLD_PATCH_DIR existiert nicht, erstelle ihn..."
        sudo mkdir -p "$OLD_PATCH_DIR"
        sudo chown $USER:$USER "$OLD_PATCH_DIR"
    fi

    # Alten Patch sichern als altpatch
    if [ -f "$OLD_PATCH_FILE" ]; then
        echo "Alter Patch gefunden, sichere als oscam-emu.altpatch..."
        sudo mv "$OLD_PATCH_FILE" "$ALT_PATCH_FILE"
        sudo chown $USER:$USER "$ALT_PATCH_FILE"
        chmod 644 "$ALT_PATCH_FILE"
        echo "Alter Patch gesichert: $ALT_PATCH_FILE"
    else
        echo "Kein alter Patch gefunden, nichts gesichert."
    fi

    # Neuen Patch kopieren
    sudo cp "$PATCH_FILE" "$OLD_PATCH_FILE"
    sudo chown $USER:$USER "$OLD_PATCH_FILE"
    chmod 644 "$OLD_PATCH_FILE"
    echo "Neuer Patch kopiert: $OLD_PATCH_FILE"
}

clean_patch_folder() {
    echo "Sicher? Alle Dateien außer oscam-patch-manager.sh werden gelöscht! (j/n)"
    read -r confirm
    if [[ "$confirm" == "j" || "$confirm" == "J" ]]; then
        find "$PATCH_DIR" -mindepth 1 ! -name "oscam-patch-manager.sh" -exec rm -rf {} +
        echo "Ordner aufgeräumt, alles außer oscam-patch-manager.sh gelöscht."
    else
        echo "Abgebrochen. Keine Dateien gelöscht."
    fi
}

# Menü anzeigen
echo "Wähle, was du tun möchtest (z.B. 1,2,3,45):"
echo "1) Patch zum ersten Mal erstellen"
echo "2) Patch erneuern (immer aktuell halten)"
echo "3) Patch prüfen (--check)"
echo "4) Patch anwenden"
echo "5) Geänderte Dateien anzeigen (git status)"
echo "6) Patch in ZIP-Datei packen"
echo "7) Alten Patch sichern als oscam-emu.altpatch und neuen Patch kopieren"
echo "8) Alle Dateien im Patch-Ordner löschen außer oscam-patch-manager.sh"
read -rp "Deine Auswahl: " choice

# Aktionen ausführen
for i in $(echo "$choice" | grep -o .); do
    case "$i" in
        1) create_patch ;;
        2) renew_patch ;;
        3) check_patch ;;
        4) apply_patch ;;
        5) show_status ;;
        6) zip_patch ;;
        7) overwrite_old_patch ;;
        8) clean_patch_folder ;;
        *) echo "Ungültige Option: $i" ;;
    esac
done

# Berechtigungen setzen: .git unverändert, Patch 644, andere Dateien 755
echo "Setze Berechtigungen korrekt..."
find "$PATCH_DIR" -mindepth 1 ! -path "$PATCH_DIR/.git*" ! -name "oscam-emu.patch" ! -name "oscam-patch-manager.sh" -exec chmod -R 755 {} +
chmod 644 "$PATCH_FILE"

echo "Fertig. Git intakt, Patch editierbar, andere Dateien 755."

