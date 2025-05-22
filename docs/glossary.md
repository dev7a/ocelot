# Ocelot Glossary

This glossary defines key terms and concepts used throughout the Ocelot project documentation. Understanding these terms will help you navigate the architecture, build process, and customization options more effectively.

## Core Concepts

-   **AWS Lambda Extension Layer (Lambda Layer):** A `.zip` file archive that can contain additional code and content, such as libraries, a custom runtime, or other dependencies. Lambda functions can be configured to use layers, making it easier to share common components and manage dependencies. Ocelot produces Lambda Layers containing custom OpenTelemetry Collectors.
-   **Build Tags (Go Build Constraints):** In Go, build tags (or build constraints) are conditions placed at the top of a `.go` file (e.g., `//go:build customtag`) that determine whether the file is included during compilation. Ocelot uses build tags extensively to select which OpenTelemetry components are compiled into a specific "distribution" of the collector.
-   **Distribution (Ocelot Distribution):** A specific variant of the OpenTelemetry Collector built by Ocelot, tailored for particular use cases. Each distribution is defined by a unique set of build tags that include or exclude specific components (receivers, processors, exporters, connectors, extensions). Distributions are defined in `config/distributions.yaml`.
-   **OpenTelemetry (OTel):** An open-source observability framework—for instrumenting, generating, collecting, and exporting telemetry data (metrics, logs, and traces) to help you analyze your software's performance and behavior.
-   **OpenTelemetry Collector (OTel Collector):** A component of OpenTelemetry that can receive, process, and export telemetry data. It's highly configurable and extensible. Ocelot builds custom versions of the OTel Collector specifically for AWS Lambda environments.
-   **Overlay Strategy:** Ocelot's approach to customization. Instead of forking the upstream `open-telemetry/opentelemetry-lambda` repository, Ocelot "overlays" its custom Go component wrappers and build configurations onto a cloned version of the upstream repository during the build process. This minimizes maintenance and merge conflicts.
-   **Upstream Repository:** The base OpenTelemetry Lambda project repository (typically `open-telemetry/opentelemetry-lambda`) that Ocelot uses as the foundation for its builds. Ocelot clones this repository, applies its overlays, and then uses the upstream's Makefile to build the final Lambda layer.

## Ocelot Components & Files

-   **`components/collector/lambdacomponents/`:** The directory within Ocelot containing Go wrapper files. These files use build tags to selectively include actual component factories from the `opentelemetry-collector-contrib` repository.
-   **`config/distributions.yaml`:** The Ocelot configuration file that defines the available distributions, their descriptions, base distributions (for inheritance), and the specific Go build tags they activate.
-   **`config/component_dependencies.yaml`:** Maps specific Ocelot component build tags to the Go module(s) they require from external repositories (primarily `opentelemetry-collector-contrib`), ensuring correct dependency resolution during the build.
-   **`tools/ocelot.py`:** The main command-line interface (CLI) script for building Ocelot distributions locally.
-   **`tools/reaper.py`:** A utility script for finding and deleting Ocelot-generated Lambda layers and their associated metadata from AWS.

## Telemetry Signals

-   **Traces:** Records of the path taken by a request as it travels through various services in an application. A trace is a tree of "spans."
-   **Metrics:** Numerical measurements aggregated over a period of time, such as request counts, error rates, or CPU utilization.
-   **Logs:** Timestamped text records, structured or unstructured, that represent discrete events within an application or system.

## Component Types (OpenTelemetry Collector)

-   **Receivers:** How data gets into the Collector (e.g., OTLP, Zipkin).
-   **Processors:** How data is manipulated within the Collector (e.g., batching, filtering, adding attributes).
-   **Exporters:** How data is sent from the Collector to one or more backends (e.g., OTLP/HTTP, Prometheus, AWS S3).
-   **Connectors:** A way to bridge two telemetry pipelines within the Collector, often used to convert signals (e.g., traces to metrics).
-   **Extensions:** Provide capabilities that don't directly involve processing telemetry data (e.g., health checks, authentication). 