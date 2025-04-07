# Ocelot Go Components

This document details the Go components defined within the Ocelot project (`components/collector/lambdacomponents/`). These components act as wrappers to selectively include functionality from the `opentelemetry-collector-contrib` repository based on Go build tags.

See [Architecture](./architecture.md) for the overall build process and how these components are integrated.

## Component Registration Pattern

All components in this directory follow a consistent pattern:

1.  **Build Tags:** Each file starts with a Go build tag directive:
    ```go
    //go:build lambdacomponents.custom && (lambdacomponents.all || lambdacomponents.<type>.all || lambdacomponents.<type>.<name>)
    ```
    -   `lambdacomponents.custom`: A master tag, likely required to include *any* custom components defined in Ocelot.
    -   `lambdacomponents.all`: Includes all custom components.
    -   `lambdacomponents.<type>.all`: Includes all custom components of a specific type (e.g., `lambdacomponents.exporter.all`).
    -   `lambdacomponents.<type>.<name>`: Includes only this specific component (e.g., `lambdacomponents.exporter.clickhouse`).
    These tags are used during the `make package` step (controlled by the `BUILDTAGS` environment variable set by [`build_extension_layer.py`](./tooling.md#3-toolsscriptsbuild_extension_layerpy)) to conditionally compile the component into the final collector binary.

2.  **Package:** Components are organized into packages based on their type (`connector`, `exporter`, etc.) within `components/collector/lambdacomponents/`.

3.  **Factory Registration:** Each file contains an `init()` function that appends the corresponding component factory function from the `opentelemetry-collector-contrib` repository to a package-level slice named `Factories`.
    ```go
    // Example from exporter/clickhouse.go
    import (
        "github.com/open-telemetry/opentelemetry-collector-contrib/exporter/clickhouseexporter"
        "go.opentelemetry.io/collector/exporter"
    )

    func init() {
        // Assumes 'Factories' is defined in the exporter package scope
        Factories = append(Factories, func(extensionId string) exporter.Factory {
            return clickhouseexporter.NewFactory()
        })
    }
    ```
    It's assumed that the upstream collector build process iterates over these `Factories` slices (likely within its `lambdacomponents/custom.go` or similar) to register the components that were compiled based on the build tags. (See [Upstream Integration](./upstream.md))

## Included Components

The following components are currently defined in Ocelot:

### 1. Signal-to-Metrics Connector

-   **File:** `components/collector/lambdacomponents/connector/signaltometricsconnector.go`
-   **Build Tag Suffix:** `connector.signaltometrics`
-   **Upstream Factory:** `github.com/open-telemetry/opentelemetry-collector-contrib/connector/signaltometricsconnector.NewFactory()`
-   **Purpose:** Converts span data into metrics, often used for generating RED (Rate, Errors, Duration) metrics from traces.

### 2. AWS S3 Exporter

-   **File:** `components/collector/lambdacomponents/exporter/awss3.go`
-   **Build Tag Suffix:** `exporter.awss3`
-   **Upstream Factory:** `github.com/open-telemetry/opentelemetry-collector-contrib/exporter/awss3exporter.NewFactory()`
-   **Purpose:** Exports telemetry data (traces, metrics, logs) to an AWS S3 bucket.

### 3. ClickHouse Exporter

-   **File:** `components/collector/lambdacomponents/exporter/clickhouse.go`
-   **Build Tag Suffix:** `exporter.clickhouse`
-   **Upstream Factory:** `github.com/open-telemetry/opentelemetry-collector-contrib/exporter/clickhouseexporter.NewFactory()`
-   **Purpose:** Exports telemetry data to a ClickHouse database.

## Adding New Components

To add a new custom component from `opentelemetry-collector-contrib`:

1.  Create a new Go file in the appropriate subdirectory (e.g., `components/collector/lambdacomponents/processor/myprocessor.go`).
2.  Add the standard build tag directive, replacing `<type>.<name>` with the specific type and name (e.g., `processor.myprocessor`).
3.  Implement the `init()` function to import the desired factory from `opentelemetry-collector-contrib` and append it to the `Factories` slice for that package type.
4.  Add an entry to [`config/component_dependencies.yaml`](./configurations.md#2-configcomponent_dependenciesyaml) mapping the new build tag (`lambdacomponents.processor.myprocessor`) to the required Go module path(s). (See [Configurations](./configurations.md))
5.  Define a new distribution in [`config/distributions.yaml`](./configurations.md#1-configdistributionsyaml) (or modify an existing one) to include the new build tag. (See [Configurations](./configurations.md))
