import requests, urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

repo = "speedy005/Oscam-Emu-patch-Manager"
headers = {"User-Agent": "Mozilla/5.0"}

total_stats = 0

# GitHub Downloads
try:
    res_git = requests.get(
        f"https://api.github.com/repos/{repo}/releases",
        headers=headers,
        timeout=10
    )
    git_count = 0
    if res_git.status_code == 200:
        for release in res_git.json():
            for asset in release.get("assets", []):
                git_count += asset.get("download_count", 0)

    print(f"DEBUG: GitHub Downloads gesamt: {git_count}")
    total_stats += git_count
except Exception as e:
    print("DEBUG: GitHub Fehler:", e)

print("USAGE COUNT (nur GitHub):", total_stats)
