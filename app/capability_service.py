import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    session_type: str
    desktop: str
    portal_service: bool
    global_shortcuts: bool
    remote_desktop: bool
    input_capture: bool
    pointer_injection: bool
    cursor_position: bool
    ntp: bool


def _portal_interface(interface: str) -> bool:
    if not shutil.which("busctl"):
        return False
    result = subprocess.run(["busctl", "--user", "introspect", "org.freedesktop.portal.Desktop",
                             "/org/freedesktop/portal/desktop", interface], capture_output=True, text=True)
    return result.returncode == 0 and "method" in result.stdout


def detect_capabilities() -> Capabilities:
    session = os.environ.get("XDG_SESSION_TYPE", "unknown")
    portal = bool(shutil.which("busctl")) and subprocess.run(
        ["busctl", "--user", "status", "org.freedesktop.portal.Desktop"], capture_output=True
    ).returncode == 0
    remote = _portal_interface("org.freedesktop.portal.RemoteDesktop")
    return Capabilities(session, os.environ.get("XDG_CURRENT_DESKTOP", "unknown"), portal,
                        _portal_interface("org.freedesktop.portal.GlobalShortcuts"), remote,
                        _portal_interface("org.freedesktop.portal.InputCapture"),
                        remote, False, True)
