import json
from pathlib import Path

from .models import AppSettings


class SettingsService:
    path = Path.home() / ".config" / "sarkhati-bourse-dackeh" / "settings.json"

    def load(self) -> AppSettings:
        try:
            return AppSettings.from_dict(json.loads(self.path.read_text()))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(settings.to_dict(), indent=2) + "\n")
        temporary.replace(self.path)
