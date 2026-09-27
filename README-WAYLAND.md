# Wayland behavior

The application detects capabilities from the current user D-Bus session. A portal interface being installed means it can be requested, not that permission has already been granted.

On this Ubuntu/GNOME session, the observed interfaces are GlobalShortcuts version 1, RemoteDesktop version 2, and InputCapture version 1. RemoteDesktop pointer injection requires the normal system permission prompt. Exact global cursor coordinates are not exposed by these interfaces, so `Get X/Y` reports that limitation and never substitutes `(0, 0)` or window-relative coordinates.

RemoteDesktop uses portal `NotifyPointerMotionAbsolute` and `NotifyPointerButton` calls. If the portal denies a session, Start remains unavailable and the denial is written to the Activity Log.

F6 is registered through the GlobalShortcuts portal when session creation and binding succeed. Space and Escape are handled only while the coordinate-capture mode is active in the application window; Space is never a global scheduler shortcut.
