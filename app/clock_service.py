import time
from datetime import datetime, timezone


class CorrectedClock:
    def __init__(self) -> None:
        self.ntp_offset_ms = 0.0
        self.user_adjustment_ms = 0.0

    def now(self) -> datetime:
        correction = (self.ntp_offset_ms + self.user_adjustment_ms) / 1000
        return datetime.fromtimestamp(time.time() + correction, timezone.utc).astimezone()

    def epoch_seconds(self) -> float:
        return time.time() + (self.ntp_offset_ms + self.user_adjustment_ms) / 1000
