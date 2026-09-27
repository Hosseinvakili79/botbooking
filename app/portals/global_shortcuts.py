import asyncio
import threading

from dbus_next import Variant

from .portal_utils import DESKTOP, PATH, connect, response, token


class GlobalShortcutService:
    def __init__(self, activated):
        self.activated = activated
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.bus = None
        self.session = None

    def start(self) -> None:
        asyncio.run_coroutine_threadsafe(self._start(), self.loop).result(timeout=30)

    async def _start(self):
        self.bus = await connect()
        introspection = await self.bus.introspect(DESKTOP, PATH)
        obj = self.bus.get_proxy_object(DESKTOP, PATH, introspection)
        api = obj.get_interface("org.freedesktop.portal.GlobalShortcuts")
        path = await api.call_create_session({"handle_token": Variant("s", token("handle")), "session_handle_token": Variant("s", token("session"))})
        result, event = {}, asyncio.Event()
        async def created(code, values):
            result.update(code=code, values=values)
            event.set()
        await response(self.bus, path, created)
        await event.wait()
        if result["code"] != 0:
            raise PermissionError("Global shortcut session was denied")
        self.session = result["values"]["session_handle"]
        api.on_activated(self._on_activated)
        path = await api.call_bind_shortcuts(self.session, [("toggle", {"description": Variant("s", "Toggle Start/Stop Clicking"), "preferred_trigger": Variant("s", "F6")})], {})
        result, event = {}, asyncio.Event()
        async def bound(code, values):
            result.update(code=code)
            event.set()
        await response(self.bus, path, bound)
        await event.wait()
        if result["code"] != 0:
            raise PermissionError("F6 global shortcut binding was denied")

    def _on_activated(self, session, shortcut_id, timestamp, options):
        if session == self.session and shortcut_id == "toggle":
            self.activated()

    def stop(self) -> None:
        if self.bus:
            self.bus.disconnect()
            self.bus = None
        self.session = None
