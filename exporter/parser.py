from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# DSMR timestamp format: YYMMDDhhmmssX where X is S(ummer) or W(inter)
_TS_RE = re.compile(r"(\d{12})[SW]?")

# OBIS code mapping: code -> (field_name, unit_strip)
_OBIS_MAP: dict[str, str] = {
    "1-3:0.2.8": "version",
    "0-0:1.0.0": "timestamp",
    "0-0:96.1.1": "meter_id_electricity",
    "0-0:96.14.0": "active_tariff",
    "1-0:1.8.1": "electricity_import_tariff_1",
    "1-0:1.8.2": "electricity_import_tariff_2",
    "1-0:2.8.1": "electricity_export_tariff_1",
    "1-0:2.8.2": "electricity_export_tariff_2",
    "1-0:1.7.0": "power_import",
    "1-0:2.7.0": "power_export",
    "1-0:32.7.0": "voltage_l1",
    "1-0:52.7.0": "voltage_l2",
    "1-0:72.7.0": "voltage_l3",
    "1-0:31.7.0": "current_l1",
    "1-0:51.7.0": "current_l2",
    "1-0:71.7.0": "current_l3",
    "1-0:21.7.0": "power_import_l1",
    "1-0:41.7.0": "power_import_l2",
    "1-0:61.7.0": "power_import_l3",
    "1-0:22.7.0": "power_export_l1",
    "1-0:42.7.0": "power_export_l2",
    "1-0:62.7.0": "power_export_l3",
    "1-0:96.7.21": "power_failures_short",
    "1-0:96.7.9": "power_failures_long",
    "1-0:32.32.0": "voltage_sags_l1",
    "1-0:52.32.0": "voltage_sags_l2",
    "1-0:72.32.0": "voltage_sags_l3",
    "1-0:32.36.0": "voltage_swells_l1",
    "1-0:52.36.0": "voltage_swells_l2",
    "1-0:72.36.0": "voltage_swells_l3",
    "0-1:96.1.0": "meter_id_gas",
    "0-1:24.2.1": "gas_total",
}

# Regex to extract value(s) from an OBIS line: code(val1)(val2)...
_VALUE_RE = re.compile(r"\(([^)]*)\)")


def _parse_timestamp(ts_str: str) -> float | None:
    """Parse a DSMR timestamp string to Unix time."""
    m = _TS_RE.match(ts_str)
    if not m:
        return None
    digits = m.group(1)
    try:
        # DSMR timestamps are in local time (CET/CEST indicated by S/W suffix)
        # We parse as naive and assume CET offset for simplicity.
        # In practice the S/W suffix distinguishes summer/winter.
        dt = datetime.strptime(digits, "%y%m%d%H%M%S")
        # Determine offset from suffix
        if ts_str.endswith("S"):
            # Summer time = CEST = UTC+2
            from datetime import timedelta

            dt = dt.replace(tzinfo=timezone(timedelta(hours=2)))
        else:
            # Winter time = CET = UTC+1
            from datetime import timedelta

            dt = dt.replace(tzinfo=timezone(timedelta(hours=1)))
        return dt.timestamp()
    except (ValueError, OverflowError):
        return None


def _strip_unit(value: str) -> str:
    """Strip unit suffix like *kWh, *m3, *kW, *V, *A."""
    idx = value.find("*")
    if idx != -1:
        return value[:idx]
    return value


@dataclass
class DSMRTelegram:
    """Parsed DSMR telegram data."""

    version: str | None = None
    timestamp: float | None = None
    meter_id_electricity: str | None = None
    meter_id_gas: str | None = None
    active_tariff: float | None = None
    electricity_import_tariff_1: float | None = None
    electricity_import_tariff_2: float | None = None
    electricity_export_tariff_1: float | None = None
    electricity_export_tariff_2: float | None = None
    power_import: float | None = None
    power_export: float | None = None
    voltage_l1: float | None = None
    voltage_l2: float | None = None
    voltage_l3: float | None = None
    current_l1: float | None = None
    current_l2: float | None = None
    current_l3: float | None = None
    power_import_l1: float | None = None
    power_import_l2: float | None = None
    power_import_l3: float | None = None
    power_export_l1: float | None = None
    power_export_l2: float | None = None
    power_export_l3: float | None = None
    power_failures_short: float | None = None
    power_failures_long: float | None = None
    voltage_sags_l1: float | None = None
    voltage_sags_l2: float | None = None
    voltage_sags_l3: float | None = None
    voltage_swells_l1: float | None = None
    voltage_swells_l2: float | None = None
    voltage_swells_l3: float | None = None
    gas_total: float | None = None
    gas_timestamp: float | None = None


def parse_telegram(raw: str) -> DSMRTelegram:
    """Parse a raw DSMR telegram string into structured data.

    Tolerant of missing OBIS fields (L2/L3 may not be present on single-phase meters).
    """
    result = DSMRTelegram()

    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("/") or line.startswith("!"):
            continue

        # Find the OBIS code (everything before the first parenthesis)
        paren_idx = line.find("(")
        if paren_idx == -1:
            continue

        obis_code = line[:paren_idx]
        field_name = _OBIS_MAP.get(obis_code)
        if field_name is None:
            continue

        # Extract all parenthesized values
        values = _VALUE_RE.findall(line)
        if not values:
            continue

        # Special handling for gas: has timestamp in first value, reading in second
        if field_name == "gas_total" and len(values) >= 2:
            result.gas_timestamp = _parse_timestamp(values[0])
            raw_val = _strip_unit(values[1])
            try:
                result.gas_total = float(raw_val)
            except (ValueError, TypeError):
                pass
            continue

        # Special handling for timestamp field
        if field_name == "timestamp":
            result.timestamp = _parse_timestamp(values[0])
            continue

        # Special handling for version (string, not numeric)
        if field_name == "version":
            result.version = values[0]
            continue

        # Meter IDs (string)
        if field_name in ("meter_id_electricity", "meter_id_gas"):
            setattr(result, field_name, values[0])
            continue

        # Numeric fields
        raw_val = _strip_unit(values[0])
        try:
            setattr(result, field_name, float(raw_val))
        except (ValueError, TypeError):
            log.debug("Could not parse %s value: %r", field_name, raw_val)

    return result
