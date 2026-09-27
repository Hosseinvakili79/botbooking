import threading
import time
from datetime import datetime

from .clock_service import CorrectedClock
from .input_backend import InputBackend
from .models import TimingSettings


class SchedulerService:
    def __init__(self, clock: CorrectedClock, input_backend: InputBackend, log):
        self.clock, self.input, self.log = clock, input_backend, log
        self._cancel = threading.Event()
        self._thread = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, timing: TimingSettings, x: int, y: int, button: str, click_type: str) -> None:
        if self.running:
            raise RuntimeError("Scheduler is already running")
        timing.validate()
        self._cancel.clear()
        self._thread = threading.Thread(target=self._run, args=(timing, x, y, button, click_type), daemon=True)
        self._thread.start()

    def stop(self, reason="user requested"):
        self._cancel.set()
        self.log(f"Scheduler stopped: {reason}.")

    def _run(self, timing, x, y, button, click_type):
        try:
            self.input.start()
            now = self.clock.epoch_seconds()
            today = datetime.now().astimezone().date()
            start_ms = timing.start.milliseconds_since_midnight()
            end_ms = timing.end.milliseconds_since_midnight()
            now_ms = (datetime.now().astimezone().hour * 3600 + datetime.now().astimezone().minute * 60 + datetime.now().astimezone().second) * 1000 + datetime.now().astimezone().microsecond // 1000
            start_offset = start_ms - now_ms
            if start_offset < 0:
                start_offset += 86400000
            end_offset = end_ms - start_ms
            if end_offset <= 0:
                end_offset += 86400000
            target = time.monotonic_ns() + int(start_offset * 1_000_000)
            deadline = target + int(end_offset * 1_000_000)
            interval = timing.interval_ms * 1_000_000
            count = 0
            self.log("Scheduler started.")
            while not self._cancel.is_set() and time.monotonic_ns() <= deadline:
                self._wait_until(target)
                if self._cancel.is_set() or time.monotonic_ns() > deadline:
                    break
                scheduled = target
                result = self.input.click(x, y, button, click_type)
                if not result.success:
                    self.log(f"Scheduler stopped: input error: {result.error}.")
                    break
                count += 1
                actual = time.monotonic_ns()
                error_ms = (actual - scheduled) / 1_000_000
                self.log(f"Click #{count} at ({x},{y}); timing error {error_ms:+.3f}ms.")
                if timing.click_limit and count >= timing.click_limit:
                    self.log("Scheduler stopped: click limit reached.")
                    break
                target += interval
            else:
                self.log("Scheduler stopped: end time reached.")
        finally:
            self.input.stop()

    def _wait_until(self, target):
        while not self._cancel.is_set():
            remaining = target - time.monotonic_ns()
            if remaining <= 0:
                return
            if remaining > 3_000_000:
                self._cancel.wait((remaining - 2_000_000) / 1_000_000_000)
            else:
                time.sleep(0.0002)
