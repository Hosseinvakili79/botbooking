from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class TimeOfDay:
    hour: int
    minute: int
    second: int
    millisecond: int

    def validate(self) -> None:
        if not 0 <= self.hour <= 23:
            raise ValueError("Hour must be between 0 and 23")
        if not 0 <= self.minute <= 59:
            raise ValueError("Minute must be between 0 and 59")
        if not 0 <= self.second <= 59:
            raise ValueError("Second must be between 0 and 59")
        if not 0 <= self.millisecond <= 999:
            raise ValueError("Millisecond must be between 0 and 999")

    def milliseconds_since_midnight(self) -> int:
        self.validate()
        return ((self.hour * 60 + self.minute) * 60 + self.second) * 1000 + self.millisecond

    def display(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}.{self.millisecond:03d}"


@dataclass
class TimingSettings:
    start: TimeOfDay = TimeOfDay(8, 44, 59, 300)
    end: TimeOfDay = TimeOfDay(8, 45, 0, 100)
    interval_ms: int = 300
    click_limit: int = 0

    def validate(self) -> None:
        self.start.validate()
        self.end.validate()
        if self.start == self.end:
            raise ValueError("Start and end times must differ")
        if self.interval_ms < 1:
            raise ValueError("Interval must be at least 1 ms")
        if self.click_limit < 0:
            raise ValueError("Click limit cannot be negative")


@dataclass
class AppSettings:
    timing: TimingSettings = field(default_factory=TimingSettings)
    x: int = 0
    y: int = 0
    button: str = "Left"
    click_type: str = "Single"
    ntp_server: str = "pool.ntp.org"
    user_adjustment_ms: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["timing"]["start"] = asdict(self.timing.start)
        data["timing"]["end"] = asdict(self.timing.end)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        timing_data = data.get("timing", {})
        timing = TimingSettings(
            start=TimeOfDay(**timing_data.get("start", asdict(TimingSettings().start))),
            end=TimeOfDay(**timing_data.get("end", asdict(TimingSettings().end))),
            interval_ms=int(timing_data.get("interval_ms", 300)),
            click_limit=int(timing_data.get("click_limit", 0)),
        )
        return cls(timing, int(data.get("x", 0)), int(data.get("y", 0)), data.get("button", "Left"),
                   data.get("click_type", "Single"), data.get("ntp_server", "pool.ntp.org"),
                   int(data.get("user_adjustment_ms", 0)))
