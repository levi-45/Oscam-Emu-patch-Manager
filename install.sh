bash

#!/bin/bash
# =====================================================================
#  OSCam Emu Patch Manager - Auto Installer (Linux/Unix/Windows-Bash)
#  Copyright (c) 2026 speedy005
# =====================================================================

set -e

# Farben für das Terminal
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Starting OSCam Emu Patch Manager Installer...${NC}"

# 1. PRÜFE PYTHON
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python3 is not installed.${NC}"
    exit 1
fi

# 2. INSTALLATIONSVERZEICHNIS
INSTALL_DIR="$HOME/OSCam-Toolkit"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 3. DOWNLOAD & ENTPACKEN (Version: first)
echo -e "${GREEN}📥 Downloading Toolkit from GitHub...${NC}"
curl -L https://github.com -o toolkit.zip

if command -v unzip &> /dev/null; then
    unzip -o toolkit.zip
    # Verschiebe Dateien aus dem Unterordner nach oben
    mv Oscam-Emu-patch-Manager-first/* . 2>/dev/null || true
    rm -rf Oscam-Emu-patch-Manager-first toolkit.zip
else
    echo -e "${RED}❌ Error: 'unzip' is not installed.${NC}"
    exit 1
fi

# 4. PYTHON DEPENDENCIES
echo -e "${GREEN}📦 Installing Python requirements (PyQt6, requests)...${NC}"
python3 -m pip install --upgrade pip
python3 -m pip install PyQt6 requests packaging --break-system-packages 2>/dev/null || python3 -m pip install PyQt6 requests packaging

# 5. RECHTE SETZEN
chmod +x oscam_patch_manager.py 2>/dev/null || true

echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}✅ Installation successful!${NC}"
echo -e "Location: $INSTALL_DIR"
echo -e "To start, run: ${CYAN}python3 $INSTALL_DIR/oscam_patch_manager.py${NC}"
echo -e "${CYAN}====================================================${NC}"
