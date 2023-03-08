import time
import os
import subprocess
from datetime import datetime as dt, timedelta
import datetime
import argparse
from pathlib import Path
import pickle
from dateutil import parser as dparser

# Config
notification_interval = timedelta(hours=2.5)
notification_repeat_interval = timedelta(minutes=10)
awake_per_day = timedelta(hours=14)
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
parser.add_argument('-w', '--wakeup', action='store_true', 
                    help="Set the wakeup time to the current time, and set the next reflection to now")
parser.add_argument('--set-wakeup', help="Set the wakeup time.")
parser.add_argument('--set-reflection', help="Set the next time to reflect at.")
parser.add_argument('--set-eod', help="Set the end of day time.")
parser.add_argument('--get-state', action='store_true', help='Querry the current state. Useful for displaying it in a widged.')
parser.add_argument('--use-voice', action='store_true', help='Use TTS to announce when it is time to reflect.')
parser.add_argument('--loop', action='store_true', help="Run the program in notification mode continuously. This should be run as a system service.")
parser.add_argument('-r', '--reflected', action='store_true', help="Declare that you are finished with the current reflection. Resets")
args = parser.parse_args()

def utc_now():
    return dt.now(datetime.UTC)

def now():
    return utc_now().astimezone()

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
            pickle.dump(utc_now(), f)

    if args.set_reflection:
        next_notification_time = dparser.parse(args.set_reflection).astimezone()
        with next_notification_time_sp.open('wb') as f:
            pickle.dump(next_notification_time, f)

    if args.wakeup or not wakeup_time_path.exists():
        reflected_flag_path.unlink(missing_ok=True)
        with wakeup_time_path.open('wb') as f:
            pickle.dump(utc_now(), f)
        with next_notification_time_sp.open('wb') as f:
            pickle.dump(utc_now(), f)
        with bedtime_sp.open('wb') as f:
            pickle.dump(utc_now() + awake_per_day, f)

    with next_notification_time_sp.open('rb') as f:
        next_notification_time = pickle.load(f)

    if args.reflected:
        reflected_flag_path.touch(exist_ok=True)

    if args.set_wakeup:
        wakeup_time = dparser.parse(args.set_wakeup).astimezone()
        with wakeup_time_path.open('wb') as f:
            pickle.dump(wakeup_time, f)
    with wakeup_time_path.open('rb') as f:
        wakeup_time = pickle.load(f)

    if args.set_eod:
        bedtime = dparser.parse(args.set_eod).astimezone()
        with bedtime_sp.open('wb') as f:
            pickle.dump(bedtime, f)
    if not bedtime_sp.exists():
        with bedtime_sp.open('wb') as f:
            pickle.dump(utc_now(), f)
    with bedtime_sp.open('rb') as f:
        bedtime = pickle.load(f)

    def eod(seconds=True):
        return fmt_time_diff(bedtime, utc_now(), seconds)
    def j_time(seconds=True):
        return fmt_time_diff(utc_now(), wakeup_time, seconds)

    if args.get_state:
        print("         J-Time:", j_time(), wakeup_time.astimezone().strftime("%H:%M"))
        print("     End of Day:", eod(), bedtime.astimezone().strftime("%H:%M"))
        print("Next Reflection:", ("NOW! " if next_notification_time < utc_now() else "") + \
              fmt_time_diff(next_notification_time, utc_now()), next_notification_time.astimezone().strftime("%H:%M"))
        print("         Wakeup:", wakeup_time.astimezone().strftime("%H:%M  %a"))
        print("        Bedtime:", bedtime.astimezone().strftime("%H:%M"))
    elif args.loop:
        while True:
            with next_notification_time_sp.open('rb') as f:
                next_notification_time = pickle.load(f)
            print(utc_now(), "<>", next_notification_time, end="\r")
            if utc_now() >= next_notification_time:
                print("Time to reflect")
                last_announce = None
                while not reflected_flag_path.exists() or utc_now() < next_notification_time:
                    with next_notification_time_sp.open('rb') as f:
                        next_notification_time = pickle.load(f)
                    if last_announce and utc_now() - last_announce < notification_repeat_interval:
                        time.sleep(1)
                        continue
                    if args.use_voice:
                        subprocess.run(["say", "reflect now"])
                    subprocess.run(["terminal-notifier", 
                        "-title", f"Reflect now ({fmt_time_diff(next_notification_time, utc_now(), False)})",
                        "-message", f"It's {j_time(False)} / {now().strftime('%H:%M')}. EOD in \
                            {eod(False)} (at {bedtime.astimezone().strftime('%H:%M')}).",
                        "-contentImage", miku_url])
                    last_announce = utc_now()
                reflected_flag_path.unlink()
                next_notification_time = utc_now() + notification_interval
                with next_notification_time_sp.open('wb') as f:
                    pickle.dump(next_notification_time, f)
            time.sleep(1)

if __name__ == "__main__":
    main()

#SOMEDAY
# - Use plain text as serialization format
# - make the serialization easier (use some dict object that automatically 
#   saves to file when writing to)
# - General refactoring