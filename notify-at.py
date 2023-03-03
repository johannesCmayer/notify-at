#!/usr/bin/env python3

import time
import os
import subprocess
from datetime import datetime as dt, timedelta
import argparse
from pathlib import Path
import pickle
from dateutil import parser as dparser

# Config
notification_interval = timedelta(hours=2)
project_dir = os.path.dirname(os.path.realpath(__file__)) 
state_dir = Path(f"{project_dir}/state")
wakeup_time_path = Path(f"{state_dir}/wakeup_time")
reflected_flag_path = Path(f"{state_dir}/reflected")
next_notification_time_sp = Path(f"{state_dir}/next_notification_time")
bedtime_sp = Path(f"{state_dir}/bedtime")
miku_url = "https://i.pinimg.com/originals/fc/60/62/fc60622ac3c047ba90d9adaba24325bd.jpg"

state_dir.mkdir(parents=True, exist_ok=True)

# Args
parser = argparse.ArgumentParser()
parser.add_argument('--wakeup', action='store_true', 
                    help="Set the wakeup time to the current time, and set the next reflection to now")
parser.add_argument('--set-wakeup', help="Set the wakeup time.")
parser.add_argument('--set-reflection', help="Set the next time to reflect at.")
parser.add_argument('--set-eod', help="Set the end of day time.")
parser.add_argument('--get-state', action='store_true', help='Querry the current state. Useful for displaying it in a widged.')
parser.add_argument('--use-voice', action='store_true', help='Use TTS to announce when it is time to reflect.')
parser.add_argument('--loop', action='store_true', help="Run the program in notification mode continuously. This should be run as a system service.")
parser.add_argument('--reflected', action='store_true', help="Declare that you are finished with the current reflection. Resets")
args = parser.parse_args()

def format_time_delta(td, seconds=True):
    a,b,c = str(td).split(".")[0].split(':')
    if seconds:
        return f"{a.zfill(2)}:{b};{c}"
    else:
        return f"{a.zfill(2)}:{b}"

def fmt_time_diff(td1, td2, seconds=True):
    val = max([td1, td2]) - min([td1, td2])
    if td2 > td1:
        return f"-{str(format_time_delta(val, seconds))}"
    else:
        return f"{str(format_time_delta(val, seconds))}"

def main():
    # Setup first time trigger
    if not next_notification_time_sp.exists():
        with next_notification_time_sp.open('wb') as f:
            pickle.dump(dt.now(), f)

    if args.set_reflection:
        next_notification_time = dparser.parse(args.set_reflection)
        with next_notification_time_sp.open('wb') as f:
            pickle.dump(next_notification_time, f)

    if args.wakeup or not wakeup_time_path.exists():
        wakeup_time = dt.now()
        with wakeup_time_path.open('wb') as f:
            pickle.dump(wakeup_time, f)
        with next_notification_time_sp.open('wb') as f:
            pickle.dump(dt.now(), f)
        bedtime = wakeup_time + timedelta(hours=12)
        with bedtime_sp.open('wb') as f:
            pickle.dump(dt.now(), f)

    with next_notification_time_sp.open('rb') as f:
        next_notification_time = pickle.load(f)

    if args.reflected:
        reflected_flag_path.touch(exist_ok=True)

    if args.set_wakeup:
        wakeup_time = dparser.parse(args.set_wakeup)
        with wakeup_time_path.open('wb') as f:
            pickle.dump(wakeup_time, f)
    with wakeup_time_path.open('rb') as f:
        wakeup_time = pickle.load(f)

    if args.set_eod:
        bedtime = dparser.parse(args.set_eod)
        with bedtime_sp.open('wb') as f:
            pickle.dump(bedtime, f)
    if not bedtime_sp.exists():
        with bedtime_sp.open('wb') as f:
            pickle.dump(dt.now(), f)
    with bedtime_sp.open('rb') as f:
        bedtime = pickle.load(f)

    def eod(seconds=True):
        return fmt_time_diff(bedtime, dt.now(), seconds)
    def j_time(seconds=True):
        return fmt_time_diff(dt.now(), wakeup_time, seconds)

    if args.get_state:
        print("         J-Time:", j_time())
        print("     End of Day:", eod(), bedtime.strftime("%H:%M"))
        print("Next Reflection:", ("NOW! " if next_notification_time < dt.now()else "") + \
              fmt_time_diff(next_notification_time, dt.now()), next_notification_time.strftime("%H:%M"))
        print("         Wakeup:", wakeup_time.strftime("%H:%M  %a"))
        print("        Bedtime:", bedtime.strftime("%H:%M"))
    elif args.loop:
        while True:
            with next_notification_time_sp.open('rb') as f:
                next_notification_time = pickle.load(f)
            print(dt.now(), "<>", next_notification_time, end="\r")
            if dt.now() >= next_notification_time:
                print("Time to reflect")
                last_announce = None
                while not reflected_flag_path.exists():
                    if last_announce and dt.now() - last_announce < timedelta(minutes=5):
                        time.sleep(1)
                        continue
                    if args.use_voice:
                        subprocess.run(["say", "reflect now"])
                    subprocess.run(["terminal-notifier", 
                        "-title", f"Reflect now ({fmt_time_diff(next_notification_time, dt.now(), False)})",
                        "-message", f"It's {j_time(False)} / {dt.now().strftime('%H:%M')}. EOD in \
                            {eod(False)} (at {bedtime.strftime('%H:%M')}).",
                        "-contentImage", miku_url])
                    last_announce = dt.now()
                reflected_flag_path.unlink()
                next_notification_time = dt.now() + notification_interval
                with next_notification_time_sp.open('wb') as f:
                    pickle.dump(next_notification_time, f)
            time.sleep(1)

if __name__ == "__main__":
    main()