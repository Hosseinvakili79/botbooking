from .capability_service import detect_capabilities


def main() -> None:
    c = detect_capabilities()
    print(f"Detected backend: {'Wayland RemoteDesktop portal' if c.remote_desktop else 'unsupported'}")
    print(f"Pointer injection can be requested: {'yes' if c.pointer_injection else 'no'}")
    print("Permission required: yes" if c.remote_desktop else "Permission required: unavailable")
    print("No input was generated.")


if __name__ == "__main__":
    main()
