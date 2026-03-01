bash

#!/bin/bash
# =====================================================================
#  OSCam Emu Patch Manager - Auto Installer
# =====================================================================

set -e

# Farben
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}🚀 Starte OSCam Emu Patch Manager Installer...${NC}"

# 1. PRÜFE PYTHON
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Fehler: Python3 ist nicht installiert.${NC}"
    exit 1
fi

# 2. VERZEICHNIS ERSTELLEN
INSTALL_DIR="$HOME/OSCam-Toolkit"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 3. DIREKTER DOWNLOAD DER .PY DATEI
echo -e "${GREEN}📥 Lade Tool von GitHub Release...${NC}"
curl -L "https://github.com/speedy005/Oscam-Emu-patch-Manager/releases/download/first/oscam_patch_manager.py" -o oscam_patch_manager.py

# --- DOWNLOAD-ZÄHLER REGISTRIEREN ---
# Dies erhöht den Zähler bei jeder Installation lautlos im Hintergrund
curl -s "https://hits.seeyoufarm.com" > /dev/null 2>&1

# 4. ABHÄNGIGKEITEN INSTALLIEREN
echo -e "${GREEN}📦 Installiere Python-Module (PyQt6, requests)...${NC}"
# Versuche normale Installation, falls nötig mit --break-system-packages
python3 -m pip install PyQt6 requests packaging --break-system-packages 2>/dev/null || python3 -m pip install PyQt6 requests packaging

# 5. RECHTE SETZEN
chmod +x oscam_patch_manager.py

echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}✅ Installation erfolgreich!${NC}"
echo -e "Ordner: $INSTALL_DIR"
echo -e "Startbefehl: ${CYAN}python3 $INSTALL_DIR/oscam_patch_manager.py${NC}"
echo -e "${CYAN}====================================================${NC}"
