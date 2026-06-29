"""Tests for the DSMR P1 telegram parser."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from exporter.parser import DSMRTelegram, parse_telegram

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


@pytest.fixture
def kaifa_telegram() -> str:
    return _load_fixture("kaifa_dsmr5_telegram.txt")


class TestParserBasic:
    """Test parsing of a complete Kaifa DSMR 5.0 telegram."""

    def test_version(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.version == "50"

    def test_timestamp(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        # 2021-06-05 12:00:00 CEST (UTC+2) = 2021-06-05 10:00:00 UTC
        assert result.timestamp is not None
        assert abs(result.timestamp - 1622887200.0) < 2

    def test_electricity_import_tariff_1(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.electricity_import_tariff_1 == pytest.approx(2345.678)

    def test_electricity_import_tariff_2(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.electricity_import_tariff_2 == pytest.approx(1234.567)

    def test_electricity_export_tariff_1(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.electricity_export_tariff_1 == pytest.approx(123.456)

    def test_electricity_export_tariff_2(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.electricity_export_tariff_2 == pytest.approx(56.789)

    def test_active_tariff(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.active_tariff == 1.0

    def test_power_import(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.power_import == pytest.approx(1.234)

    def test_power_export(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.power_export == pytest.approx(0.0)

    def test_voltage_l1(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.voltage_l1 == pytest.approx(230.0)

    def test_current_l1(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.current_l1 == pytest.approx(3.0)

    def test_power_import_l1(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.power_import_l1 == pytest.approx(1.234)

    def test_power_export_l1(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.power_export_l1 == pytest.approx(0.0)

    def test_power_failures_short(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.power_failures_short == 5.0

    def test_power_failures_long(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.power_failures_long == 2.0

    def test_voltage_sags_l1(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.voltage_sags_l1 == 3.0

    def test_voltage_swells_l1(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.voltage_swells_l1 == 1.0

    def test_gas_total(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.gas_total == pytest.approx(1234.567)

    def test_gas_timestamp(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        # 2021-06-05 11:55:00 CEST (UTC+2) = 2021-06-05 09:55:00 UTC
        assert result.gas_timestamp is not None
        assert abs(result.gas_timestamp - 1622886900.0) < 2

    def test_meter_id_electricity(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.meter_id_electricity is not None

    def test_meter_id_gas(self, kaifa_telegram: str) -> None:
        result = parse_telegram(kaifa_telegram)
        assert result.meter_id_gas is not None


class TestMissingOptionalFields:
    """Test that missing L2/L3 fields do not cause failures."""

    SINGLE_PHASE_TELEGRAM = """\
/KFM5KAIFA-METER

1-3:0.2.8(50)
0-0:1.0.0(210605120000S)
1-0:1.8.1(001000.000*kWh)
1-0:1.8.2(000500.000*kWh)
1-0:2.8.1(000100.000*kWh)
1-0:2.8.2(000050.000*kWh)
0-0:96.14.0(0002)
1-0:1.7.0(00.500*kW)
1-0:2.7.0(00.100*kW)
1-0:32.7.0(229.5*V)
1-0:31.7.0(002*A)
1-0:21.7.0(00.500*kW)
1-0:22.7.0(00.100*kW)
1-0:96.7.21(00010)
1-0:96.7.9(00001)
1-0:32.32.0(00002)
1-0:32.36.0(00000)
0-1:24.2.1(210605115500S)(00500.000*m3)
!ABCD
"""

    def test_l2_fields_are_none(self) -> None:
        result = parse_telegram(self.SINGLE_PHASE_TELEGRAM)
        assert result.voltage_l2 is None
        assert result.current_l2 is None
        assert result.power_import_l2 is None
        assert result.power_export_l2 is None

    def test_l3_fields_are_none(self) -> None:
        result = parse_telegram(self.SINGLE_PHASE_TELEGRAM)
        assert result.voltage_l3 is None
        assert result.current_l3 is None
        assert result.power_import_l3 is None
        assert result.power_export_l3 is None

    def test_l1_fields_still_parsed(self) -> None:
        result = parse_telegram(self.SINGLE_PHASE_TELEGRAM)
        assert result.voltage_l1 == pytest.approx(229.5)
        assert result.current_l1 == pytest.approx(2.0)

    def test_does_not_raise(self) -> None:
        # Should not raise any exception
        result = parse_telegram(self.SINGLE_PHASE_TELEGRAM)
        assert result.electricity_import_tariff_1 == pytest.approx(1000.0)


class TestGasTimestamp:
    """Test gas timestamp parsing with different timezone suffixes."""

    WINTER_TELEGRAM = """\
/KFM5KAIFA-METER

1-3:0.2.8(50)
0-0:1.0.0(211215100000W)
1-0:1.8.1(003000.000*kWh)
1-0:1.8.2(001500.000*kWh)
1-0:2.8.1(000200.000*kWh)
1-0:2.8.2(000100.000*kWh)
0-0:96.14.0(0001)
1-0:1.7.0(02.000*kW)
1-0:2.7.0(00.000*kW)
1-0:32.7.0(231.0*V)
1-0:31.7.0(009*A)
1-0:21.7.0(02.000*kW)
1-0:22.7.0(00.000*kW)
1-0:96.7.21(00008)
1-0:96.7.9(00003)
1-0:32.32.0(00004)
1-0:32.36.0(00001)
0-1:24.2.1(211215095500W)(02000.000*m3)
!1234
"""

    def test_winter_gas_timestamp(self) -> None:
        result = parse_telegram(self.WINTER_TELEGRAM)
        # 2021-12-15 09:55:00 CET (UTC+1) = 2021-12-15 08:55:00 UTC
        assert result.gas_timestamp is not None
        assert abs(result.gas_timestamp - 1639558500.0) < 2

    def test_winter_telegram_timestamp(self) -> None:
        result = parse_telegram(self.WINTER_TELEGRAM)
        # 2021-12-15 10:00:00 CET (UTC+1) = 2021-12-15 09:00:00 UTC
        assert result.timestamp is not None
        assert abs(result.timestamp - 1639558800.0) < 2

    def test_gas_value_parsed(self) -> None:
        result = parse_telegram(self.WINTER_TELEGRAM)
        assert result.gas_total == pytest.approx(2000.0)


class TestEmptyTelegram:
    """Edge cases with minimal or empty content."""

    def test_empty_string(self) -> None:
        result = parse_telegram("")
        assert result.version is None
        assert result.timestamp is None

    def test_header_only(self) -> None:
        result = parse_telegram("/KFM5KAIFA-METER\n!1234")
        assert result.version is None

    def test_garbage_lines_ignored(self) -> None:
        raw = "/KFM5KAIFA-METER\nsome garbage\n1-3:0.2.8(50)\n!ABCD"
        result = parse_telegram(raw)
        assert result.version == "50"
