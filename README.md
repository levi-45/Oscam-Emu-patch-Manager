OSCam Emu Patch Generator – Overview


The OSCam Emu Patch Generator is a comprehensive, GUI-based tool for managing, creating, and applying patches for OSCam Emu. It is designed to simplify patching workflows while providing advanced Git integration, backup options, and GitHub deployment.


Key Features:


1. Patch Creation & Management

- Automatically generate patches by comparing the OSCam Emu repository with a streaming OSCam source.

- Supports creating, renewing, and checking patches.

- Includes automatic patch headers with version, commit hash, and patch modifier information.


2. Git Integration

- Clone and manage OSCam and OSCam Emu repositories.

- Apply patches directly to the Git repository.

- Check patch compatibility using Git’s `apply --check`.

- View the latest commits directly in the GUI.

- Manage OSCam Emu Git folder with one-click cleanup and patching.


3. Backup & Version Control

- Backup existing patches to a configurable location.

- Automatically create alternative backups to prevent accidental overwrites.

- Maintain patch history with clear date and version metadata.


4. GitHub Deployment

- Upload patches to a GitHub repository using credentials stored in a secure configuration file.

- Supports forcing commits and pushing all changes to a selected branch.

- No private credentials are stored in the code; all user info comes from a secure JSON configuration.


5. Patch Distribution

- Export patches as ZIP files for easy distribution.

- Includes optional icons for quick identification of actions.


6. Customizable GUI

- Modern PyQt6-based interface with a dynamic info log window.

- Supports multiple languages (English and German) and customizable color themes.

- Includes progress bars, active button highlighting, and an easy-to-use layout for patch actions.


7. Safety & Convenience

- Never deletes critical files from the patch folder.

- Provides user confirmations for destructive actions (cleaning folder, exiting, etc.).

- Ensures all required tools (git, zip, Python3, pip3) are installed.


Technical Notes:

- Developed in Python 3 with PyQt6 and PIL for icons.

- Fully open-source under the MIT license.

- Designed for Linux-based systems with OSCam Emu installed.


https://raw.githubusercontent.com/speedy005/Oscam-Emu-patch-Manager/master/oscam-patch-generator.png
