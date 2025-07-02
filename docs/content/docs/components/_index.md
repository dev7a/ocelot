---
title: Components
weight: 40
cascade:
  type: docs
---

Ocelot allows you to build Lambda layers with a precise set of OpenTelemetry Collector components. This includes standard components from the upstream `open-telemetry/opentelemetry-lambda` project as well as custom components unique to Ocelot.

## Component Types

The OpenTelemetry Collector is composed of the following types of components:

- **Receivers**: Get data into the Collector.
- **Processors**: Process data before it is exported.
- **Exporters**: Send data to one or more backends.
- **Connectors**: Link two pipelines together, for example, by converting spans to metrics.
- **Extensions**: Provide capabilities that do not involve processing telemetry data, such as health checks or authentication.

## Default vs. Full Distribution

The `default` distribution contains a standard set of upstream components, while the `full` distribution includes all available upstream and custom components. The primary distinction is the inclusion of connectors and custom components in the `full` build.

| Component Type | Component Name | Default | Full |
| :--- | :--- | :---: | :---: |
| **Connectors** | `spanmetrics` | | ✓ |
| | *Custom Connectors* | | ✓ |
| **Exporters** | *Custom Exporters* | | ✓ |
| | `debug` | ✓ | ✓ |
| | `otlp` | ✓ | ✓ |
| | `otlphttp` | ✓ | ✓ |
| | `prometheusremotewrite`| ✓ | ✓ |
| **Extensions** | `basicauth` | ✓ | ✓ |
| | `sigv4auth` | ✓ | ✓ |
| **Processors** | *All Default Upstream* | ✓ | ✓ |
| | *Custom Processors* | | ✓ |
| **Receivers** | *All Default Upstream* | ✓ | ✓ |
| | *Custom Receivers* | | ✓ |

For a complete list of default upstream components, see the [upstream documentation](https://github.com/open-telemetry/opentelemetry-lambda).

## Upstream Default Components

The `default` distribution includes the following standard components from the `open-telemetry/opentelemetry-lambda` project:

*   **Receivers**: `otlp`, `telemetryapi`
*   **Exporters**: `debug`, `otlp`, `otlphttp`, `prometheusremotewrite`
*   **Processors**: `attributes`, `filter`, `memory_limiter`, `probabilistic_sampler`, `resource`, `span`, `coldstart`, `decouple`, `batch`
*   **Extensions**: `sigv4auth`, `basicauth`
*   **Connectors**: None.

Refer to the upstream OpenTelemetry Lambda and Collector Contrib documentation for detailed configuration of these components.

## Current Custom Components

Ocelot currently includes the following custom components:

-   **ClickHouse Exporter**: Exports telemetry data to a ClickHouse database.
-   **AWS S3 Exporter**: Exports telemetry data to an Amazon S3 bucket.
-   **SignalToMetrics Connector**: Converts signal data (e.g., spans) into metrics.

Learn how to add your own in the [Adding New Components](adding-components) guide. 