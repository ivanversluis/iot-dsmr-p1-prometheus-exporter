# DSMR P1 Prometheus Exporter

Prometheus exporter for DSMR P1 smart meter telegrams. Reads complete DSMR 5.0 telegram frames from a serial device and exposes energy metrics on `:9100`.

## Quick start

```bash
# Local development
pip install -r requirements.txt
DSMR_SERIAL_DEVICE=/dev/ttyUSB0 python -m exporter

# Docker
docker build -t dsmr-p1-exporter .
docker run --rm --device=/dev/ttyUSB0:/dev/ttyUSB0 -p 9100:9100 dsmr-p1-exporter
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DSMR_SERIAL_DEVICE` | `/dev/ttyUSB0` | Path to P1 serial device |
| `DSMR_BAUDRATE` | `115200` | Serial baud rate |
| `DSMR_BYTESIZE` | `8` | Data bits |
| `DSMR_PARITY` | `N` | Parity (N/E/O) |
| `DSMR_STOPBITS` | `1` | Stop bits |
| `METRICS_PORT` | `9100` | Prometheus metrics HTTP port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DSMR_LOG_METER_IDS` | `false` | Log meter serial numbers (privacy) |

## Metrics

| Metric | Description |
|--------|-------------|
| `dsmr_up` | 1 when receiving telegrams |
| `dsmr_version` | DSMR protocol version |
| `dsmr_telegram_timestamp_unixtime` | Telegram timestamp |
| `dsmr_electricity_import_total_kwh_tariff_1` | Import tariff 1 |
| `dsmr_electricity_import_total_kwh_tariff_2` | Import tariff 2 |
| `dsmr_electricity_export_total_kwh_tariff_1` | Export tariff 1 |
| `dsmr_electricity_export_total_kwh_tariff_2` | Export tariff 2 |
| `dsmr_electricity_active_tariff` | Current tariff |
| `dsmr_electricity_power_import_kw` | Current import power |
| `dsmr_electricity_power_export_kw` | Current export power |
| `dsmr_phase_voltage_l1_volts` | L1 voltage |
| `dsmr_phase_current_l1_amps` | L1 current |
| `dsmr_phase_power_import_l1_kw` | L1 import power |
| `dsmr_phase_power_export_l1_kw` | L1 export power |
| `dsmr_power_failures_short_total` | Short power failures |
| `dsmr_power_failures_long_total` | Long power failures |
| `dsmr_voltage_sags_l1_total` | Voltage sags L1 |
| `dsmr_voltage_swells_l1_total` | Voltage swells L1 |
| `dsmr_gas_total_m3` | Gas consumption |
| `dsmr_gas_timestamp_unixtime` | Gas reading timestamp |
| `dsmr_last_telegram_timestamp` | Last processed time |
| `dsmr_telegram_parse_errors_total` | Parse error counter |

## Testing

```bash
pip install pytest
pytest tests/ -v
python -m compileall exporter
```

## Hardware

- **Meter**: Kaifa DSMR 5.0
- **Cable**: P1 USB cable on `k8s-master01`
- **Stable path**: Use `/dev/serial/by-id/...` instead of `/dev/ttyUSB0`

## Deployment

Container image is built and pushed to GHCR on every push to `main` or tag. Kubernetes manifests live in the `homelabs` repository under `infra/home-exporters/dsmr-p1-prometheus-exporter/`.

See [DESIGN.md](DESIGN.md) for architecture details.
