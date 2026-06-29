from __future__ import annotations

import logging
import threading
from typing import Generator

import serial

from .config import DSMRConfig

log = logging.getLogger(__name__)


def open_serial(config: DSMRConfig) -> serial.Serial:
    """Open the serial port with DSMR P1 settings."""
    log.info(
        "Opening serial port device=%s baudrate=%d bytesize=%d parity=%s stopbits=%d",
        config.serial_device,
        config.baudrate,
        config.bytesize,
        config.parity,
        config.stopbits,
    )
    return serial.Serial(
        port=config.serial_device,
        baudrate=config.baudrate,
        bytesize=config.bytesize,
        parity=config.parity,
        stopbits=config.stopbits,
        timeout=10,
    )


def read_telegrams(config: DSMRConfig, stop_event: threading.Event | None = None) -> Generator[str, None, None]:
    """Yield complete DSMR telegram frames.

    A telegram starts with '/' and ends with '!' followed by a CRC line.
    """
    port = open_serial(config)
    try:
        buffer: list[str] = []
        in_telegram = False

        while stop_event is None or not stop_event.is_set():
            raw = port.readline()
            if not raw:
                continue

            try:
                line = raw.decode("ascii", errors="replace").rstrip("\r\n")
            except Exception:
                continue

            if line.startswith("/"):
                buffer = [line]
                in_telegram = True
                continue

            if in_telegram:
                buffer.append(line)
                if line.startswith("!"):
                    telegram = "\n".join(buffer)
                    log.debug("Read complete telegram (%d lines)", len(buffer))
                    yield telegram
                    buffer = []
                    in_telegram = False
    finally:
        port.close()
