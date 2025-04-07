# Ocelot Configurations

This document explains the YAML configuration files used by the Ocelot build tooling, located in the `config/` directory.

See [Architecture](./architecture.md) for how these configurations fit into the overall build process.

## 1. `config/distributions.yaml`

This file defines the different build variants, or "distributions," of the Ocelot collector. Each distribution represents a specific combination of standard upstream components and custom Ocelot components.

**Structure:**

The file is a YAML dictionary where each key is the unique name of a distribution. The value associated with each key is another dictionary containing:

-   `description` (String): A human-readable description of the distribution's purpose or contents.
-   `buildtags` (List of Strings): A list of Go build tags to be activated when building this distribution. These tags control which Go files (especially the component wrappers in [`components/collector/lambdacomponents/`](./components.md)) are included in the compilation. (See [Components](./components.md))
-   `base` (String, Optional): The name of another distribution from which to inherit `buildtags`. Tags from the `base` distribution are combined with the tags listed directly under `buildtags` for the current distribution.

**Example Entry:**

```yaml
clickhouse:
  description: "Minimal + ClickHouse exporter"
  base: minimal # Inherits tags from the 'minimal' distribution
  buildtags:
    - lambdacomponents.exporter.clickhouse # Adds the specific tag for the ClickHouse exporter
```

**Key Distributions:**

-   `default`: Represents the standard upstream build, typically with no custom Ocelot tags.
-   `full`: Includes all available custom components (uses `lambdacomponents.custom` and `lambdacomponents.all`).
-   `minimal`: Defines a base set of commonly used upstream components (e.g., OTLP receiver/exporter, batch processor). Specific Ocelot distributions often use `minimal` as their `base`.
-   Other distributions (e.g., `clickhouse`, `s3export`, `signaltometrics`): Build upon `minimal` by adding specific component tags.

**Usage:**

-   The [`tools/ocelot.py`](./tooling.md#1-toolsocelotpy) script uses this file to present choices for the `--distribution` argument.
-   [`tools/scripts/otel_layer_utils/distribution_utils.py`](./tooling.md#5-toolsscriptsotel_layer_utils-module) (`resolve_build_tags` function) parses this file to determine the final, flattened list of build tags for a given distribution name, handling inheritance and checking for errors.
-   [`tools/scripts/build_extension_layer.py`](./tooling.md#3-toolsscriptsbuild_extension_layerpy) receives the resolved build tags string and passes it via the `BUILDTAGS` environment variable to the upstream `make package` command.
-   Other scripts ([`get_release_info.py`](./tooling.md#6-other-scripts-toolstoolsscripts), GitHub workflows) also use this file to understand available distributions. (See [Tooling](./tooling.md))

## 2. `config/component_dependencies.yaml`

This file maps the specific Ocelot component build tags (defined in the Go wrapper files and used in [`distributions.yaml`](#1-configdistributionsyaml)) to the Go module(s) they require from external repositories (primarily `opentelemetry-collector-contrib`). (See [Components](./components.md))

**Structure:**

The file contains a top-level `dependencies` key, which holds a dictionary. Each key within this dictionary is a specific Ocelot component build tag (e.g., `lambdacomponents.exporter.clickhouse`). The value is a list of strings, where each string is the Go module path required by that component.

**Example Entry:**

```yaml
dependencies:
  # Build Tag: List of Go Module Paths
  lambdacomponents.exporter.clickhouse:
    - github.com/open-telemetry/opentelemetry-collector-contrib/exporter/clickhouseexporter

  lambdacomponents.connector.signaltometrics:
    - github.com/open-telemetry/opentelemetry-collector-contrib/connector/signaltometricsconnector
```

**Usage:**

-   [`tools/scripts/build_extension_layer.py`](./tooling.md#3-toolsscriptsbuild_extension_layerpy) reads this file (`load_component_dependencies`). (See [Tooling](./tooling.md))
-   When building a specific distribution, the script first determines the active build tags for that distribution (using [`distributions.yaml`](#1-configdistributionsyaml)).
-   It then looks up these active tags in the `component_dependencies.yaml` mapping to find the required Go modules.
-   The `add_dependencies` function uses this list of modules to modify the `go.mod` file within the cloned upstream repository (using `go mod edit -require=<module>@<version>`), ensuring the necessary code for the selected custom components is available during compilation. The version is typically pinned to the determined `upstream_version`. (See [Upstream Integration](./upstream.md))

**Purpose:**

This file allows the build system to manage dependencies efficiently. Instead of including all possible dependencies in the base `go.mod`, it only adds the ones explicitly needed for the components included in the target distribution, reducing download times and potential conflicts.
