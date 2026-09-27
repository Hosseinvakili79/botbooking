from .capability_service import detect_capabilities


def main() -> None:
    c = detect_capabilities()
    print(f"Session: {c.session_type.title()}")
    print(f"Desktop: {c.desktop}")
    print(f"Global Shortcuts: {'SUPPORTED' if c.global_shortcuts else 'UNSUPPORTED'}")
    print(f"Remote Desktop: {'SUPPORTED' if c.remote_desktop else 'UNSUPPORTED'}")
    print(f"Pointer Injection: {'SUPPORTED' if c.pointer_injection else 'UNSUPPORTED'}")
    print(f"Cursor Position: {'SUPPORTED' if c.cursor_position else 'UNSUPPORTED'}")
    print(f"NTP: {'SUPPORTED' if c.ntp else 'UNSUPPORTED'}")
    print(f"Portal service: {'AVAILABLE' if c.portal_service else 'UNAVAILABLE'}")


if __name__ == "__main__":
    main()
