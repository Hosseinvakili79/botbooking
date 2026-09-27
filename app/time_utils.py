from datetime import date, datetime, timedelta

from .models import TimeOfDay


def schedule_window(day: date, start: TimeOfDay, end: TimeOfDay) -> tuple[datetime, datetime]:
    start.validate()
    end.validate()
    start_dt = datetime.combine(day, datetime.min.time()) + timedelta(milliseconds=start.milliseconds_since_midnight())
    end_day = day + timedelta(days=1) if start.milliseconds_since_midnight() > end.milliseconds_since_midnight() else day
    end_dt = datetime.combine(end_day, datetime.min.time()) + timedelta(milliseconds=end.milliseconds_since_midnight())
    if start_dt == end_dt:
        raise ValueError("Start and end times must differ")
    return start_dt, end_dt


def parse_time(text: str) -> TimeOfDay:
    parts = text.split(":")
    if len(parts) != 3:
        raise ValueError("Expected HH:MM:SS.mmm")
    seconds = parts[2].split(".")
    if len(seconds) != 2 or len(seconds[1]) != 3:
        raise ValueError("Expected exactly three millisecond digits")
    result = TimeOfDay(int(parts[0]), int(parts[1]), int(seconds[0]), int(seconds[1]))
    result.validate()
    return result
