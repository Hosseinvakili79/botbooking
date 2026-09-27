import asyncio
import secrets

from dbus_next.aio import MessageBus
from dbus_next import BusType


DESKTOP = "org.freedesktop.portal.Desktop"
PATH = "/org/freedesktop/portal/desktop"


async def connect() -> MessageBus:
    return await MessageBus(bus_type=BusType.SESSION).connect()


def token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


async def response(bus, request_path, callback):
    introspection = await bus.introspect(DESKTOP, request_path)
    obj = bus.get_proxy_object(DESKTOP, request_path, introspection)
    request = obj.get_interface("org.freedesktop.portal.Request")
    request.on_response(callback)
