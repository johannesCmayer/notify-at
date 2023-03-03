import os
from pathlib import Path

project_dir = os.path.dirname(os.path.realpath(__file__)) 

launchd_file_name = 'com.j.notify-at.plist'
launchd_target = Path(f'~/Library/LaunchAgents/{launchd_file_name}').expanduser()
if launchd_target.exists():
    input(f"{launchd_target} exists, to delete and continue press enter.")
    launchd_target.unlink()
os.symlink(f"{project_dir}/{launchd_file_name}", launchd_target)
os.system(f"launchctl unload {launchd_target}")
os.system(f"launchctl load {launchd_target}")