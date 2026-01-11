#!/bin/sh
# oscam-patch.sh

TAG=$1

if [ -z "${TAG}" ]; then
    TAG="master"
fi

STREAMREPO="https://git.streamboard.tv/common/oscam.git"
EMUREPO="https://github.com/oscam-mirror/oscam-emu.git"
PATCH_MODIFIER="speedy005"

# Clone if needed
if [ ! -d "oscam-patching" ]; then
    git clone $STREAMREPO oscam-patching
fi

cd oscam-patching

# Set up remotes
git remote | grep -q oscam-emu || git remote add oscam-emu $EMUREPO

# Fetch updates
git fetch origin
git fetch oscam-emu

# Checkout the specific tag
git checkout $TAG

# Get version from globals.h
if [ -f "globals.h" ]; then
    OSC_VERSION=$(grep '#define CS_VERSION' globals.h | cut -d'"' -f2)
else
    OSC_VERSION="2.26.01-$TAG"
fi

# Create patch
#git diff $TAG..oscam-emu/master > ../oscam-emu-$TAG.patch
git diff $TAG..oscam-emu/master -- . ':!.github' > ../oscam-emu-$TAG-raw.patch

# Create header
echo "patch version: ${OSC_VERSION}-802" > ../header.txt
echo "patch date: $(date -u '+%Y-%m-%d %H:%M:%S UTC (%z)')" >> ../header.txt
echo "patch modified by $PATCH_MODIFIER ($(date '+%d/%m/%Y'))" >> ../header.txt
echo "---" >> ../header.txt

# Combine header and patch
cat ../header.txt ../oscam-emu-$TAG-raw.patch > ../oscam-emu-$TAG.patch

echo "Patch created: oscam-emu-$TAG.patch"
echo "Size: $(wc -l < ../oscam-emu-$TAG.patch) lines"
