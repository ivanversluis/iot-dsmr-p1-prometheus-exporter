from __future__ import annotations

import logging
import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {raw!r}") from exc


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").lower()
    if raw in ("", "0", "false", "no"):
        return default if raw == "" else False
    return True


@dataclass(frozen=True)
class DSMRConfig:
    serial_device: str
    baudrate: int
    bytesize: int
    parity: str
    stopbits: int
    metrics_port: int
    log_level: str
    log_meter_ids: bool

    @classmethod
    def from_env(cls) -> "DSMRConfig":
        return cls(
            serial_device=os.getenv("DSMR_SERIAL_DEVICE", "/dev/ttyUSB0"),
            baudrate=_int_env("DSMR_BAUDRATE", 115200),
            bytesize=_int_env("DSMR_BYTESIZE", 8),
            parity=os.getenv("DSMR_PARITY", "N"),
            stopbits=_int_env("DSMR_STOPBITS", 1),
            metrics_port=_int_env("METRICS_PORT", 9100),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_meter_ids=_bool_env("DSMR_LOG_METER_IDS", False),
        )
