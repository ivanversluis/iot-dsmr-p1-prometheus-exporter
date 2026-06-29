from __future__ import annotations

import logging
import os
import time

from prometheus_client import Counter, Gauge, start_http_server

from .config import DSMRConfig, _int_env
from .parser import DSMRTelegram, parse_telegram
from .serial_reader import read_telegrams

log = logging.getLogger(__name__)

# --- Prometheus metrics ---

DSMR_UP = Gauge(
    "dsmr_up",
    "1 when the exporter is reading telegrams successfully, 0 otherwise.",
)
DSMR_VERSION = Gauge(
    "dsmr_version",
    "DSMR protocol version as a numeric value (e.g. 50 for DSMR 5.0).",
)
DSMR_TELEGRAM_TIMESTAMP = Gauge(
    "dsmr_telegram_timestamp_unixtime",
    "Unix timestamp from the last received DSMR telegram.",
)
DSMR_LAST_TELEGRAM = Gauge(
    "dsmr_last_telegram_timestamp",
    "Unix timestamp when the exporter last processed a telegram.",
)
DSMR_PARSE_ERRORS = Counter(
    "dsmr_telegram_parse_errors_total",
    "Total number of telegram parse errors.",
)

# Electricity import/export totals
ELECTRICITY_IMPORT_T1 = Gauge(
    "dsmr_electricity_import_total_kwh_tariff_1",
    "Total imported electricity on tariff 1 in kWh.",
)
ELECTRICITY_IMPORT_T2 = Gauge(
    "dsmr_electricity_import_total_kwh_tariff_2",
    "Total imported electricity on tariff 2 in kWh.",
)
ELECTRICITY_EXPORT_T1 = Gauge(
    "dsmr_electricity_export_total_kwh_tariff_1",
    "Total exported electricity on tariff 1 in kWh.",
)
ELECTRICITY_EXPORT_T2 = Gauge(
    "dsmr_electricity_export_total_kwh_tariff_2",
    "Total exported electricity on tariff 2 in kWh.",
)

# Active tariff and power
ACTIVE_TARIFF = Gauge(
    "dsmr_electricity_active_tariff",
    "Currently active tariff (1 or 2).",
)
POWER_IMPORT = Gauge(
    "dsmr_electricity_power_import_kw",
    "Current power import from grid in kW.",
)
POWER_EXPORT = Gauge(
    "dsmr_electricity_power_export_kw",
    "Current power export to grid in kW.",
)

# Phase voltage/current/power (L1)
VOLTAGE_L1 = Gauge(
    "dsmr_phase_voltage_l1_volts",
    "Phase voltage L1 in volts.",
)
CURRENT_L1 = Gauge(
    "dsmr_phase_current_l1_amps",
    "Phase current L1 in amps.",
)
POWER_IMPORT_L1 = Gauge(
    "dsmr_phase_power_import_l1_kw",
    "Phase power import L1 in kW.",
)
POWER_EXPORT_L1 = Gauge(
    "dsmr_phase_power_export_l1_kw",
    "Phase power export L1 in kW.",
)

# Power quality
POWER_FAILURES_SHORT = Gauge(
    "dsmr_power_failures_short_total",
    "Total number of short power failures.",
)
POWER_FAILURES_LONG = Gauge(
    "dsmr_power_failures_long_total",
    "Total number of long power failures.",
)
VOLTAGE_SAGS_L1 = Gauge(
    "dsmr_voltage_sags_l1_total",
    "Total number of voltage sags on L1.",
)
VOLTAGE_SWELLS_L1 = Gauge(
    "dsmr_voltage_swells_l1_total",
    "Total number of voltage swells on L1.",
)

# Gas
GAS_TOTAL = Gauge(
    "dsmr_gas_total_m3",
    "Total gas consumption in cubic meters.",
)
GAS_TIMESTAMP = Gauge(
    "dsmr_gas_timestamp_unixtime",
    "Unix timestamp of the last gas meter reading.",
)


def _set_gauge(gauge: Gauge, value: float | None) -> None:
    """Set a gauge if value is not None."""
    if value is not None:
        gauge.set(value)


def update_metrics(telegram: DSMRTelegram) -> None:
    """Update all Prometheus metrics from a parsed telegram."""
    # Version
    if telegram.version is not None:
        try:
            DSMR_VERSION.set(float(telegram.version))
        except (ValueError, TypeError):
            pass

    # Telegram timestamp
    _set_gauge(DSMR_TELEGRAM_TIMESTAMP, telegram.timestamp)

    # Electricity totals
    _set_gauge(ELECTRICITY_IMPORT_T1, telegram.electricity_import_tariff_1)
    _set_gauge(ELECTRICITY_IMPORT_T2, telegram.electricity_import_tariff_2)
    _set_gauge(ELECTRICITY_EXPORT_T1, telegram.electricity_export_tariff_1)
    _set_gauge(ELECTRICITY_EXPORT_T2, telegram.electricity_export_tariff_2)

    # Active tariff and power
    _set_gauge(ACTIVE_TARIFF, telegram.active_tariff)
    _set_gauge(POWER_IMPORT, telegram.power_import)
    _set_gauge(POWER_EXPORT, telegram.power_export)

    # Phase L1
    _set_gauge(VOLTAGE_L1, telegram.voltage_l1)
    _set_gauge(CURRENT_L1, telegram.current_l1)
    _set_gauge(POWER_IMPORT_L1, telegram.power_import_l1)
    _set_gauge(POWER_EXPORT_L1, telegram.power_export_l1)

    # Power quality
    _set_gauge(POWER_FAILURES_SHORT, telegram.power_failures_short)
    _set_gauge(POWER_FAILURES_LONG, telegram.power_failures_long)
    _set_gauge(VOLTAGE_SAGS_L1, telegram.voltage_sags_l1)
    _set_gauge(VOLTAGE_SWELLS_L1, telegram.voltage_swells_l1)

    # Gas
    _set_gauge(GAS_TOTAL, telegram.gas_total)
    _set_gauge(GAS_TIMESTAMP, telegram.gas_timestamp)

    # Mark last processed time
    DSMR_LAST_TELEGRAM.set(time.time())
    DSMR_UP.set(1)


def poll_loop(config: DSMRConfig) -> None:
    """Main loop: read telegrams from serial and update metrics."""
    DSMR_UP.set(0)

    while True:
        try:
            log.info("Starting telegram reader on %s", config.serial_device)
            for telegram_raw in read_telegrams(config):
                try:
                    telegram = parse_telegram(telegram_raw)
                    update_metrics(telegram)
                    log.debug("Metrics updated from telegram")
                except Exception:
                    DSMR_PARSE_ERRORS.inc()
                    log.exception("Failed to parse telegram")
        except Exception:
            DSMR_UP.set(0)
            log.exception("Serial reader failed, retrying in 5s")
            time.sleep(5)


def main() -> None:
    """Entrypoint: configure logging, start HTTP server, begin polling."""
    config = DSMRConfig.from_env()

    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    start_http_server(config.metrics_port)
    log.info("DSMR P1 Prometheus exporter listening on port %d", config.metrics_port)
    poll_loop(config)
