OSCam Emu Patch Manager – Features
1. Patch Management

    Create Patch: Generates a patch file from the OSCam repositories (streamboard + emu-repo).

    Renew Patch: Recreates the patch including the latest commits.

    Check Patch: Verifies if a patch can be applied cleanly.

    Apply Patch: Applies the patch directly to the temporary OSCam repository.

    Zip Patch: Packages the patch into a .zip file for backup or distribution.

    Backup/Renew Old Patch: Saves the current patch to a backup folder and preserves the old patch.

2. Repository & Git Support

    Maintains a temporary Git repository (temp_repo) automatically.

    Can fetch commits from upstream repositories (streamboard and emu-repo).

    Shows the last X commits for tracking changes.

    Supports Git status checking to verify patch application.

3. GUI Features

    Fully graphical interface with buttons for all operations.

    Information window displays real-time logs for all operations.

    Commit counter to specify how many commits to include in patch creation.

    Color scheme selection: change button colors in the GUI.

    Language selection: switch instantly between English and German.

    Animated buttons for better user interaction.

4. Safety & Maintenance

    Clean Patch Folder safely deletes temporary files but never deletes protected files:

        oscam_patch_manager.py

        oscam_patch_manager_gui.py

        oscam-patch-manager.sh

        oscam-patch-manager-gui.sh

        icons folder

    The icons folder is automatically created and maintained by the tool.

5. Config & Settings

    Stores user settings in a config.json file, including:

        Language (EN/DE)

        Selected color scheme

    Restores settings automatically on startup.

6. Additional Features

    Handles missing tools gracefully and informs the user (git, zip, unzip, python3, pip3).

    Provides exit confirmation with localized buttons (Yes/No in English, Ja/Nein in German).

    Fully cross-platform compatible with Python 3.

Summary:

This tool is a complete patch management solution for OSCam Emu: it lets you create, check, apply, backup, and zip patches, track commits, and safely manage the patch folder – all via a friendly GUI with language and color customization.
