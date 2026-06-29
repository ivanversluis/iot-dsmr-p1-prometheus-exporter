# DSMR P1 Prometheus Exporter — Design

## Fit with homelabs

The homelabs repository deploys home IoT exporters under `infra/home-exporters/`. The DSMR P1 exporter is deployed as:

```text
infra/home-exporters/dsmr-p1-prometheus-exporter/
```

It is added to `infra/kustomization.yaml` next to the existing GoodWe and Daikin exporters.

## Hardware requirements

- **P1 cable**: Connected to USB on `k8s-master01`.
- **Serial device**: `/dev/serial/by-id/...` (stable path, not `/dev/ttyUSB0`).
- **Node pinning**: Deployment must use `nodeSelector: kubernetes.io/hostname: k8s-master01`.
- **Device mount**: hostPath volume for the serial device.

## Serial settings (Kaifa DSMR 5.0)

| Setting  | Value   |
|----------|---------|
| Baudrate | 115200  |
| Bytesize | 8       |
| Parity   | None    |
| Stopbits | 1       |

## Security and privacy

- Meter serial numbers (OBIS `0-0:96.1.1` and `0-1:96.1.0`) are **never logged** unless `DSMR_LOG_METER_IDS=true`.
- No secrets are required — only serial device access.
- The container runs as non-root (UID 1000).
- The Kubernetes pod needs `privileged: false` but requires the device path mounted.

## Network access

The exporter requires:

- **Ingress** from the `observability` namespace to TCP/9100 for Prometheus scraping.
- **No egress** — reads from a local serial device only.

## Metrics design

All metrics are low-cardinality (no labels by default). This avoids cardinality explosion from meter IDs or per-telegram labels.

Key design choices:
- Counters (totals) are exposed as Gauges because the meter provides absolute readings.
- `dsmr_up` indicates the exporter is healthy and receiving telegrams.
- `dsmr_telegram_parse_errors_total` is a Counter for monitoring parse failures.
- L2/L3 metrics are only populated on three-phase installations.

## Energy loop with GoodWe

```
Estimated house load = goodwe_power_watts / 1000
                     + dsmr_electricity_power_import_kw
                     - dsmr_electricity_power_export_kw
```

This formula works because:
- GoodWe reports solar production.
- DSMR reports net grid exchange.
- Sum gives total consumption (house + EV charger + etc).

## Kubernetes manifests (homelabs)

```text
infra/home-exporters/dsmr-p1-prometheus-exporter/
  kustomization.yaml
  configmap.yaml
  deployment.yaml
  service.yaml
  networkpolicy.yaml
```

The Deployment uses:
- `nodeSelector` for `k8s-master01`.
- `hostPath` volume for the serial device (by-id path).
- `securityContext.privileged: false` (device access via group or supplementalGroups).
