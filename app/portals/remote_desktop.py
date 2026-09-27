import asyncio
import threading

from dbus_next import Variant

from ..input_backend import ClickResult, InputBackend
from .portal_utils import DESKTOP, PATH, connect, response, token


class RemoteDesktopBackend(InputBackend):
    """RemoteDesktop portal backend. The portal owns permission and input injection."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.bus = None
        self.session = None

    def _run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result(timeout=30)

    async def _start(self):
        self.bus = await connect()
        introspection = await self.bus.introspect(DESKTOP, PATH)
        obj = self.bus.get_proxy_object(DESKTOP, PATH, introspection)
        api = obj.get_interface("org.freedesktop.portal.RemoteDesktop")
        options = {"handle_token": Variant("s", token("handle")), "session_handle_token": Variant("s", token("session"))}
        request_path = await api.call_create_session(options)
        result = {}
        event = asyncio.Event()
        async def done(response_code, values):
            result.update(code=response_code, values=values)
            event.set()
        await response(self.bus, request_path, done)
        await event.wait()
        if result["code"] != 0:
            raise PermissionError("RemoteDesktop session creation was denied")
        self.session = result["values"]["session_handle"]
        request_path = await api.call_select_devices(self.session, {"devices": Variant("u", 1), "handle_token": Variant("s", token("handle"))})
        result, event = {}, asyncio.Event()
        async def selected(code, values):
            result.update(code=code, values=values)
            event.set()
        await response(self.bus, request_path, selected)
        await event.wait()
        if result["code"] != 0:
            raise PermissionError("RemoteDesktop pointer permission was denied")
        request_path = await api.call_start(self.session, "", {"handle_token": Variant("s", token("handle"))})
        result, event = {}, asyncio.Event()
        async def started(code, values):
            result.update(code=code, values=values)
            event.set()
        await response(self.bus, request_path, started)
        await event.wait()
        if result["code"] != 0:
            raise PermissionError("RemoteDesktop start was denied")

    def start(self) -> None:
        self._run(self._start())

    def click(self, x: int, y: int, button: str, click_type: str) -> ClickResult:
        if not self.session or not self.bus:
            return ClickResult(False, "RemoteDesktop session is not started")
        try:
            self._run(self._click(x, y, button, click_type))
            return ClickResult(True)
        except Exception as exc:
            return ClickResult(False, str(exc))

    async def _click(self, x, y, button, click_type):
        introspection = await self.bus.introspect(DESKTOP, PATH)
        api = self.bus.get_proxy_object(DESKTOP, PATH, introspection).get_interface("org.freedesktop.portal.RemoteDesktop")
        await api.call_notify_pointer_motion_absolute(self.session, {}, 0, float(x), float(y))
        code = 1 if button == "Left" else 3
        presses = 2 if click_type == "Double" else 1
        for _ in range(presses):
            await api.call_notify_pointer_button(self.session, {}, code, 1)
            await api.call_notify_pointer_button(self.session, {}, code, 0)
            if presses == 2:
                await asyncio.sleep(0.05)

    def stop(self) -> None:
        self.session = None
        if self.bus:
            self.bus.disconnect()
            self.bus = None
