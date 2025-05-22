# Upstream Repository Integration

Ocelot builds upon the foundation provided by the upstream `open-telemetry/opentelemetry-lambda` repository. This document explains how Ocelot integrates with this upstream project, utilizing its source code and build system dynamically. The aim is to make it easier to create custom OpenTelemetry Collector versions for AWS Lambda without needing to maintain a separate fork of the upstream repository. Understanding this relationship is helpful for grasping how Ocelot works. For definitions of specific terms, the [Ocelot Glossary](./glossary.md) is a valuable resource.

To see how this integration fits into the broader build system, please see the [Architecture](./architecture.md) document for the overall process context.

## Role of the Upstream Repository

The Ocelot project does not contain a full OpenTelemetry Collector implementation. Instead, it relies on the official OpenTelemetry Lambda Collector repository (`open-telemetry/opentelemetry-lambda` by default) as its foundation. The Ocelot build process leverages the upstream repository's source code, build system (`Makefile`), and standard components.

## Integration Mechanism

The integration happens dynamically during the build process orchestrated by [`tools/ocelot.py`](./tooling.md#1-toolsocelotpy) and executed primarily by [`tools/scripts/build_extension_layer.py`](./tooling.md#3-toolsscriptsbuild_extension_layerpy): (See [Tooling](./tooling.md))

1.  **Cloning:** The build process starts by cloning the specified upstream repository (defined by `--upstream-repo` and `--upstream-ref` arguments, defaulting to `open-telemetry/opentelemetry-lambda`@`main`) into a temporary local directory (e.g., `/tmp/otel-upstream-*`). This ensures the build uses a clean, specific version of the upstream code.
2.  **Versioning:** The exact version of the cloned upstream code is determined by running `make set-otelcol-version` within the `collector/` subdirectory of the clone. This command is expected to generate a `VERSION` file, which is then read by the Ocelot tooling ([`tools/local_build/upstream.py`](./tooling.md#2-toolslocal_build-module)). This version is crucial for pinning dependencies correctly.
3.  **Component Overlay:** Ocelot component wrappers (from [`components/collector/lambdacomponents/`](./components.md)) selected via build tags are copied *into* the `collector/lambdacomponents/` directory of the *cloned upstream repository*. This injects the Ocelot-specific component registrations alongside the upstream ones. (See [Components](./components.md))
4.  **Dependency Management:** The `go.mod` file *within the cloned upstream repository* is modified. Dependencies required by the overlaid Ocelot components (defined in [`config/component_dependencies.yaml`](./configurations.md#2-configcomponent_dependenciesyaml)) are added using `go mod edit -require=<module>@<version>`, pinning them to the determined upstream version. `go mod tidy` is run afterwards. (See [Configurations](./configurations.md))
5.  **Building:** The build itself is performed by executing `make package` *within the `collector/` subdirectory of the cloned upstream repository*. This uses the upstream `Makefile`, which compiles the Go code (including the standard upstream components and the overlaid Ocelot components with their added dependencies) using the specified build tags (`BUILDTAGS` environment variable).

## Upstream Structure (`collector/` directory)

Based on the analysis of a temporary clone, the relevant structure within the upstream `collector/` directory includes:

-   `Makefile`, `Makefile.Common`: Used by Ocelot's build process (`make set-otelcol-version`, `make package`).
-   `go.mod`, `go.sum`: Modified by Ocelot to add dependencies.
-   `main.go`: The entry point for the collector binary being built.
-   `internal/`: Contains upstream's internal logic for Lambda integration (API clients, lifecycle).
-   `lambdacomponents/`: Contains Go files registering upstream's standard components (`default.go`, etc.). **This is the target for Ocelot's component overlay.** (See [Components](./components.md))
-   `processor/`, `receiver/`: Contain implementations of core upstream components.

## Implications

-   **Build Dependency:** Ocelot builds are directly dependent on the availability and structure of the upstream repository and its `Makefile`. Changes in the upstream `Makefile` or directory structure could break the Ocelot build process.
-   **Versioning:** The version of the final Ocelot collector layer is tied to the version determined from the upstream clone. Dependency pinning ensures that custom components use compatible versions of shared libraries.
-   **Updates:** To update the base collector used by Ocelot, the `--upstream-ref` argument (or the default) needs to point to a newer tag or commit in the `open-telemetry/opentelemetry-lambda` repository. The build process will then clone, version, and build against that newer base.

## Analysis Limitations

Direct analysis of the upstream repository's file content was limited as it only exists ephemerally during the build process within a temporary directory. The structural analysis was based on the output of `ls -R` run against such a temporary directory.
