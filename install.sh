bash

#!/bin/bash
set -e

# Farben für das Terminal
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

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

# 3. DOWNLOAD (KORRIGIERTE URL)
echo -e "${GREEN}📥 Downloading Toolkit from GitHub...${NC}"
# Ersetze den Link durch den echten Download-Link deiner Release-Zip
curl -L "https://github.com" -o toolkit.tar.gz

# 4. ENTPACKEN
if command -v tar &> /dev/null; then
    tar -xzf toolkit.tar.gz --strip-components=1
    rm toolkit.tar.gz
else
    echo -e "${RED}❌ Error: 'tar' is not installed.${NC}"
    exit 1
fi

# 5. PYTHON DEPENDENCIES
echo -e "${GREEN}📦 Installing Python requirements...${NC}"
python3 -m pip install PyQt6 requests packaging --break-system-packages || python3 -m pip install PyQt6 requests packaging

# 6. RECHTE SETZEN
chmod +x oscam_patch_manager.py

echo -e "${GREEN}✅ Installation erfolgreich in $INSTALL_DIR!${NC}"
echo -e "Start mit: ${CYAN}python3 $INSTALL_DIR/oscam_patch_manager.py${NC
