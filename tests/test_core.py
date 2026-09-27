from datetime import date

import pytest

from app.models import AppSettings, TimeOfDay, TimingSettings
from app.ntp_service import NTP_EPOCH
from app.time_utils import parse_time, schedule_window


def test_time_validation_and_parse():
    assert parse_time("08:44:59.300").display() == "08:44:59.300"
    with pytest.raises(ValueError): parse_time("24:00:00.000")
    with pytest.raises(ValueError): TimeOfDay(0, 0, 0, 1000).validate()


def test_midnight_window():
    start, end = schedule_window(date(2026, 1, 1), TimeOfDay(23, 59, 59, 500), TimeOfDay(0, 0, 0, 500))
    assert end.date().day == 2
    assert (end - start).total_seconds() == 1


def test_timing_validation_and_limits():
    with pytest.raises(ValueError): TimingSettings(interval_ms=0).validate()
    with pytest.raises(ValueError): TimingSettings(click_limit=-1).validate()
    with pytest.raises(ValueError): TimingSettings(start=TimeOfDay(1, 0, 0, 0), end=TimeOfDay(1, 0, 0, 0)).validate()


def test_settings_round_trip():
    original = AppSettings(x=12, y=34, button="Right", click_type="Double", user_adjustment_ms=-5)
    assert AppSettings.from_dict(original.to_dict()).to_dict() == original.to_dict()


def test_ntp_epoch_constant():
    assert NTP_EPOCH == 2208988800
