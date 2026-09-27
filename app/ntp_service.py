import socket
import struct
import time
from dataclasses import dataclass


NTP_EPOCH = 2208988800


@dataclass(frozen=True)
class NtpResult:
    offset_ms: float
    round_trip_ms: float
    server: str


def _ntp_seconds(data: bytes, offset: int) -> float:
    seconds, fraction = struct.unpack_from("!II", data, offset)
    return seconds + fraction / 2**32 - NTP_EPOCH


def query_ntp(server: str, timeout: float = 2.0) -> NtpResult:
    packet = bytearray(48)
    packet[0] = 0x1B
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        t1 = time.time()
        sock.sendto(packet, (server, 123))
        response, _ = sock.recvfrom(512)
        t4 = time.time()
    if len(response) < 48:
        raise ValueError("Malformed NTP response")
    t2, t3 = _ntp_seconds(response, 32), _ntp_seconds(response, 40)
    return NtpResult(((t2 - t1) + (t3 - t4)) * 500, (t4 - t1) * 1000, server)
