# Sarkhati Bourse Dackeh 4.1

Native PySide6 desktop application for Ubuntu/GNOME Wayland. It uses the XDG Desktop Portal for input injection and GlobalShortcuts. It does not use X11 input APIs, fake coordinates, or a licensing system.

## Setup

Create a virtual environment and install the Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the application:

```bash
python -m app.main
```

Useful non-invasive checks:

```bash
python -m app.diagnostics
python -m app.portal_test
python -m app.test_input
pytest
```

Settings are stored at `~/.config/sarkhati-bourse-dackeh/settings.json`. The application never changes system time. NTP correction is applied only to its application clock.

## Ubuntu packages

`xdg-desktop-portal` provides the standardized D-Bus portal API. `xdg-desktop-portal-gnome` provides the GNOME backend and permission dialogs. The running session must expose `org.freedesktop.portal.Desktop`; no `sudo` command is run by this project.
