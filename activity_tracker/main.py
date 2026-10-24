import argparse
import datetime

from . import VERSION


def format_duration(seconds):
    minutes = int(seconds // 60)
    if minutes < 1:
        return "<1m"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


def day_range(day):
    t0 = datetime.datetime.combine(day, datetime.time.min).timestamp()
    return t0, t0 + 86400


def print_report():
    from .db import Database

    rows = Database().usage_by_app(*day_range(datetime.date.today()))
    if not rows:
        print("No activity recorded today.")
    for _app_id, name, secs in rows:
        print(f"{format_duration(secs):>8}  {name}")


def main():
    parser = argparse.ArgumentParser(prog="activity-tracker", description="Track time spent in apps.")
    parser.add_argument("--daemon", action="store_true", help="run the background tracking service")
    parser.add_argument("--report", action="store_true", help="print today's usage and exit")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args()

    if args.daemon:
        from .daemon import run
        run()
    elif args.report:
        print_report()
    else:
        from .ui import run_ui
        run_ui()
