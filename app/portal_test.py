from .capability_service import detect_capabilities


def main() -> None:
    c = detect_capabilities()
    print("org.freedesktop.portal.Desktop")
    print(f"GlobalShortcuts: {'available (version 1)' if c.global_shortcuts else 'unavailable'}")
    print(f"RemoteDesktop: {'available' if c.remote_desktop else 'unavailable'}")
    print(f"InputCapture: {'available' if c.input_capture else 'unavailable'}")


if __name__ == "__main__":
    main()
