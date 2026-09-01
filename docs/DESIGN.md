# DSMR P1 Prometheus Exporter — Design

> Last verified against `exporter/` and the `homelabs` deployment manifests on 2026-09-01.

## Fit with homelabs

The homelabs repository deploys home IoT exporters under `infra/home-exporters/`, in the
`home-exporters` namespace. The DSMR P1 exporter is deployed as:

```text
infra/home-exporters/dsmr-p1-prometheus-exporter/
  kustomization.yaml
  dsmr-p1-prometheus-exporter-configmap.yaml
  dsmr-p1-prometheus-exporter-deployment.yaml
  dsmr-p1-prometheus-exporter-service.yaml
  dsmr-p1-prometheus-exporter-networkpolicy.yaml
```

It sits next to the existing GoodWe and Daikin exporters under `infra/home-exporters/kustomization.yaml`.

## Hardware requirements

- **P1 cable**: Connected to USB on `k8s-master01`.
- **Serial device**: currently `/dev/ttyUSB0` (hostPath, `CharDevice`), pinned via `nodeName: k8s-master01`
  (not a `nodeSelector`) plus a control-plane toleration.
- **TODO (hardening)**: switch to the stable `/dev/serial/by-id/...` path — `/dev/ttyUSB0` can shift
  if the USB device is replugged or another serial adapter is added.

## Serial settings (Kaifa DSMR 5.0)

| Setting  | Value   |
|----------|---------|
| Baudrate | 115200  |
| Bytesize | 8       |
| Parity   | None    |
| Stopbits | 1       |

## Security and privacy

**Current state:**
- The container image ([Dockerfile](../Dockerfile)) defines a non-root user (UID/GID 1000) as the default.
- The `home-exporters` Deployment **overrides this and runs as root** (`runAsUser: 0`) with
  `securityContext.privileged: true`, because `/dev/ttyUSB0` device permissions weren't reliably
  accessible otherwise.
- `DSMR_LOG_METER_IDS` (env var, default `false`) is parsed in `config.py` but **not yet wired up** —
  meter serial numbers (OBIS `0-0:96.1.1` and `0-1:96.1.0`) are parsed into `DSMRTelegram` but never
  logged anywhere today, regardless of this flag.
- No secrets are required — only serial device access.

**TODO (hardening)**: run as non-root/non-privileged using a udev rule + supplementary group for the
by-id device path, and either implement or remove the `DSMR_LOG_METER_IDS` gate.

## Network access

The NetworkPolicy allows:

- **Ingress** from the `observability` namespace to TCP/9100 for Prometheus scraping.
- **Egress** to `kube-system` on UDP/TCP 53 for DNS resolution only. There is no other egress —
  the exporter itself only reads from a local serial device and never makes outbound calls.

## Metrics design

All metrics are low-cardinality (no labels by default). This avoids cardinality explosion from meter IDs or per-telegram labels.

Key design choices:
- Counters (totals) are exposed as Gauges because the meter provides absolute readings.
- `dsmr_up` indicates the exporter is healthy and receiving telegrams.
- `dsmr_telegram_parse_errors_total` is a Counter for monitoring parse failures.
- **Only L1 metrics are currently exposed** (`dsmr_phase_*_l1_*`). `parser.py` already extracts
  L2/L3 OBIS fields (voltage, current, import/export power, sags/swells) into `DSMRTelegram`, but
  `metrics.py` does not yet define Gauges for them or set them in `update_metrics()`.
- **TODO**: expose L2/L3 gauges for three-phase installations, or drop the L2/L3 parsing if it will
  stay single-phase-only.

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

This is a Grafana/Prometheus recording-rule idea for combining the two exporters' outputs; it is not
implemented in this repository.

## Kubernetes manifests (homelabs) — current state

The Deployment (`dsmr-p1-prometheus-exporter-deployment.yaml`) actually uses:
- `nodeName: k8s-master01` (hard pin, not `nodeSelector`) with a control-plane toleration.
- `hostPath` volume of type `CharDevice` for `/dev/ttyUSB0`.
- `securityContext.privileged: true` and `runAsUser: 0` at the pod level.
- Readiness/liveness probes against `GET /metrics` on the `metrics` port (9100).
- Config supplied via `envFrom.configMapRef` (`dsmr-p1-prometheus-exporter-config`), matching the
  env vars in [README.md](../README.md#configuration).

See the hardening TODOs above (by-id device path, non-root/non-privileged) for the intended future state.
