import os
from pathlib import Path

bin_target = Path('/usr/local/bin/notify-at')
with open(bin_target, 'w') as f:
    f.write('#!/usr/bin/env bash\n')
    f.write('/opt/homebrew/bin/python3 "$HOME"/projects/notify-at/notify-at.py $@')
os.chmod(bin_target, 0o777)