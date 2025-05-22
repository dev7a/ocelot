# OCELOT  
#### The OpenTelemetry Collector Extension Layer Optimization Toolkit  

Ocelot is a toolkit designed to simplify the creation of custom AWS Lambda Extension Layers for the OpenTelemetry Collector. It helps users add specific observability components or optimize their collector for particular use cases. Ocelot integrates with the [OpenTelemetry Lambda project](https://github.com/open-telemetry/opentelemetry-lambda) by leveraging its Go build tag system, which facilitates the inclusion of custom elements without requiring a direct fork of the upstream repository.

![OCELOT CLI and CI/CD](https://github.com/user-attachments/assets/bdfe0908-f2f1-4a5a-b3fa-34615fe3691c)
*A fast, flexible way to build custom Lambda Extension Layers.*

`Ocelot` is both a CLI and a CI/CD pipeline on Github Action: you can use the CLI to build your own customized layers, and publish them to your own AWS account, or you can contribute to this repo providinga customized configuration that you think would be useful to share widely. 

Layer are published to differnent regions (currently North America and EU only) and available as both ARM and Intel architectures in the releases section.

This README provides an overview of Ocelot, covering setup, core concepts, customization, and contribution guidelines. For definitions of specialized terms, please consult the [Ocelot Glossary](docs/glossary.md).




## Table of Contents

- [Overview: The Overlay Approach](#overview-the-overlay-approach)
- [Build and Deployment Options](#build-and-deployment-options)
- [Getting Started: Local Build](#getting-started-local-build)
- [Understanding Distributions](#understanding-distributions)
- [Customization Guide](#customization-guide)
- [Current Custom Components](#current-custom-components)
- [Architecture](#architecture)
- [Using the Ocelot Local Build Tool](#using-the-ocelot-local-build-tool)
- [Managing and Cleaning Up Lambda Layers](#managing-and-cleaning-up-lambda-layers)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [Setting Up Your Fork for Automated Publishing](#setting-up-your-fork-for-automated-publishing)
- [Glossary](docs/glossary.md)
- [License](#license)

## Overview: The Overlay Approach

Maintaining a fork of a rapidly evolving upstream project like OpenTelemetry Lambda can lead to significant maintenance overhead and merge conflicts. **Ocelot** employs an **overlay** strategy, made possible by the upstream project's Go build tag system, to circumvent these issues. Instead of forking, this repository contains only the custom components and the necessary build configurations.

The build process works as follows:

1.  **Clone Upstream:** Fetches the specified version of the `open-telemetry/opentelemetry-lambda` repository.
2.  **Apply Overlay:** Copies the custom Go components defined within this repository (`components/collector/lambdacomponents/`) into the appropriate directories of the cloned upstream source code.
3.  **Build Collector:** Compiles the OpenTelemetry Collector using the upstream project's Go build tag system, guided by the tags derived from the selected ocelot distribution, incorporating both standard and custom components.
4.  **Package Layer:** Creates a `.zip` archive suitable for deployment as an AWS Lambda Layer.
5.  **Publish (Optional):** Uploads the layer to specified AWS regions and records metadata.

This approach allows for seamless integration of custom functionality while staying synchronized with upstream developments, significantly reducing maintenance efforts. For a detailed explanation of the overlay build process and how Ocelot integrates with the upstream repository, see [Architecture](docs/architecture.md) and [Upstream Integration](docs/upstream.md).

## Build and Deployment Options

Choose the method that best suits your workflow and requirements:

1.  **Use Pre-built Layers:** Find layers for various distributions published in the [Releases](https://github.com/dev7a/ocelot/releases) section of this repository. This is the simplest way to use standard or common custom distributions.
2.  **Local Build:** Compile and publish layers directly from your local machine to your AWS account. Ideal for testing custom components, development, or managing private layers not intended for public release.
3.  **Fork and Use GitHub Actions:** Fork this repository to create your own private build system. Configure the GitHub Actions workflow within your fork with your AWS credentials (using OIDC and secrets) for secure, automated publishing of *your* custom layers to *your* AWS account. See the "Setting Up Your Fork for Automated Publishing" section for details.

## Getting Started: Local Build

To build layers locally, ensure you have the following prerequisites installed:

1.  **Go:** The latest stable version. ([Installation Guide](https://go.dev/docs/install))
2.  **uv:** A fast Python package manager. ([Installation Guide](https://docs.astral.sh/uv/getting-started/installation/))
3.  **AWS Credentials:** Configured for programmatic access (e.g., via `~/.aws/credentials`, environment variables, or IAM role).

**Build Steps:**

```bash
uv run tools/ocelot.py --distribution minimal
```

This command performs the clone, overlay, build, and packaging steps for the `minimal` distribution and `amd64` architecture by default. It saves the resulting `.zip` file in the `build/` directory and publishes the layer to your configured default AWS region.

Use `uv run tools/ocelot.py --help` for additional options, such as specifying architecture (`--architecture`), the upstream ref from which to build your custom collector (`--upstream-ref`), or skipping publishing (`--skip-publish`). For advanced CLI options and build tooling internals, see [Tooling](docs/tooling.md).

## Understanding Distributions

**Ocelot** supports building different "distributions," which are pre-defined sets of OpenTelemetry Collector components tailored for specific use cases. These are defined in `config/distributions.yaml`.

| Distribution | Description | Base | Build Tags |
|-------------|-------------|------|------------|
| `default` | Base upstream components | *none* | `lambdacomponents.custom`, `lambdacomponents.receiver.otlp`, `lambdacomponents.exporter.*`, `lambdacomponents.processor.*`, `lambdacomponents.extension.*` |
| `full` | All available upstream and custom components | *none* | `lambdacomponents.custom`, `lambdacomponents.all` |
| `minimal` | OTLP receiver, Batch processor, Decouple processor, OTLP/HTTP exporter | *none* | `lambdacomponents.custom`, `lambdacomponents.receiver.otlp`, `lambdacomponents.processor.batch`, `lambdacomponents.processor.decouple`, `lambdacomponents.exporter.otlphttp` |
| `minimal-clickhouse` | Minimal + ClickHouse exporter | minimal | `lambdacomponents.exporter.clickhouse` |
| `minimal-s3export` | Minimal + AWS S3 exporter | minimal | `lambdacomponents.exporter.awss3` |
| `minimal-asmauth` | Minimal + AWS Secrets Manager Auth extension | minimal | `lambdacomponents.extension.asmauthextension` |
| `minimal-signaltometrics` | Minimal + Signal to Metrics connector | minimal | `lambdacomponents.connector.signaltometrics` |
| `minimal-spaneventtolog` | Minimal + Span Event to Log connector | minimal | `lambdacomponents.connector.spaneventtolog` |
| `minimal-forwarder` | Minimal + Span Event to Log connector + AWS Secrets Manager Auth + Signal to Metrics | minimal | Multiple connectors and extensions intended specifically for the [Serverless OTLP forwarder](https://github.com/dev7a/serverless-otlp-forwarder) use case |

**Build Tag Mechanism:** The `lambdacomponents.custom` build tag is automatically included for all distributions except `default`, enabling the overlay mechanism. Distributions can inherit build tags from a `base` distribution defined in the configuration, promoting reuse and simplifying definitions. The final set of build tags used during compilation is the unique union of base tags and distribution-specific tags. For full details on distribution definitions and inheritance, see [Configurations](docs/configurations.md#1-configdistributionsyaml).

**Custom Collector Configurations:**  
Optionally, a distribution can specify a `config-file` property pointing to a YAML file inside `config/examples/`. If provided, this file will be copied into the Lambda layer during the build, replacing the default upstream `config.yaml`. This allows you to customize the OpenTelemetry Collector configuration per distribution without modifying upstream sources. If omitted, the default upstream configuration is used.


### Upstream Default Components

The `default` distribution includes the following standard components from `open-telemetry/opentelemetry-lambda`:

*   **Receivers:** `otlp`, `telemetryapi`
*   **Exporters:** `debug`, `otlp`, `otlphttp`, `prometheusremotewrite`
*   **Processors:** `attributes`, `filter`, `memory_limiter`, `probabilistic_sampler`, `resource`, `span`, `coldstart`, `decouple`, `batch`
*   **Extensions:** `sigv4auth`, `basicauth`
*   **Connectors:** None.

Refer to the upstream OpenTelemetry Lambda and Collector Contrib documentation for detailed configuration of these components. For a technical breakdown of how Ocelot includes custom components using build tags, see [Components](docs/components.md).

### Component Comparison: Default vs. Full

The primary distinction between `default` and `full` lies in the inclusion of connectors and custom components in the `full` distribution.

| Component Type | Component Name        | Default | Full |
| :------------- | :-------------------- | :------: | :--: |
| **Connectors** | spanmetrics           |          |  ✓   |
|                | *Custom Connectors*   |          |  ✓   |
| **Exporters**  | *Custom Exporters*    |          |  ✓   |
|                | debug                 |    ✓     |  ✓   |
|                | otlp                  |    ✓     |  ✓   |
|                | otlphttp              |    ✓     |  ✓   |
|                | prometheusremotewrite |    ✓     |  ✓   |
| **Extensions** | basicauth             |    ✓     |  ✓   |
|                | sigv4auth             |    ✓     |  ✓   |
| **Processors** | *All Default*         |    ✓     |  ✓   |
|                | *Custom Processors*   |          |  ✓   |
| **Receivers**  | *All Default*         |    ✓     |  ✓   |
|                | *Custom Receivers*    |          |  ✓   |


## Customization Guide

Extend **ocelot** with your own components and distributions. This involves placing Go files with specific build tags, declaring dependencies, and defining distribution presets in configuration files.

For detailed step-by-step instructions, refer to:

-   [Adding Custom Components](docs/components.md#adding-new-components): Learn how to create Go wrapper files, apply build tags, and manage dependencies.
-   [Defining New Distributions](docs/configurations.md#1-configdistributionsyaml): Understand how to define new presets in `config/distributions.yaml`, including using base distributions.

## Current Custom Components

*   **ClickHouse Exporter**: Exports telemetry data to ClickHouse.
*   **AWS S3 Exporter**: Exports telemetry data to Amazon S3.
*   **SignalToMetrics Connector**: Converts signal data (e.g., spans) into metrics.

See [Components](docs/components.md) for technical details on these wrappers and how they use build tags.

## Architecture

The build system for Ocelot integrates multiple layers of tooling to streamline the creation and deployment of custom OpenTelemetry Lambda Layers. At its core, it leverages the upstream [OpenTelemetry Lambda](https://github.com/open-telemetry/opentelemetry-lambda) project's Makefile, which orchestrates the compilation of the OpenTelemetry Collector as a Go binary. This Makefile handles tasks such as cleaning previous builds, embedding version and Git metadata via linker flags, and packaging the resulting binary into a Lambda-compatible zip archive. The Go build process itself uses specific build tags to include or exclude components, enabling highly customizable collector builds tailored for serverless environments.

Complementing this, Ocelot introduces a suite of Python scripts and libraries that automate and extend the upstream build process. These Python tools handle cloning the upstream repository, applying overlays of custom Go components, resolving build tags based on user-selected distributions, and managing AWS interactions such as publishing Lambda layers across multiple regions. They provide a flexible CLI (`tools/ocelot.py`) that abstracts away the complexity of manual Makefile invocation, environment setup, and AWS CLI commands. This layered approach allows developers to rapidly iterate on custom components, automate multi-region publishing, and maintain alignment with upstream changes—all without directly modifying the upstream build system. For a deep dive into the build flow and upstream integration, see [Architecture](docs/architecture.md) and [Upstream Integration](docs/upstream.md).

### Build and Deployment Workflows

The following diagrams illustrate the system's workflow for both automated (GitHub Actions) and local builds.

### GitHub Actions Workflow

<img alt="CI/CD with Github Actions" width="50%" align="right" src="https://github.com/user-attachments/assets/3d45467a-34b4-4929-9e30-9a2a309586c8">

This diagram illustrates the **automated publishing workflow** using GitHub Actions:

- The process starts with a **manual trigger** of the workflow.
- The environment is prepared, including setting up AWS credentials and build parameters.
- Multiple **parallel build jobs** are launched, each targeting a specific architecture (e.g., `amd64`, `arm64`).
- After building, **parallel release jobs** publish the built Lambda layers to the specified AWS regions.
- All release jobs converge to a step that **generates reports** summarizing the published layers.
- Finally, a **GitHub Release** is created or updated with the new layer artifacts and metadata.

This automation enables multi-architecture, multi-region publishing with minimal manual intervention.

### Local Development Workflow

<img alt="Local Development" width="50%" align="right" src="https://github.com/user-attachments/assets/1a824d39-2fcf-4bf7-9223-b706ba2502d9">

This diagram illustrates the **local build and publish workflow** when running the Ocelot CLI tool:

- The process begins with a **local CLI command** invocation.
- The tool **loads the distribution configuration** to determine which components and build tags to use.
- It **clones the upstream OpenTelemetry Lambda repository** at the specified version or branch.
- The tool **determines the upstream version** to ensure compatibility.
- It **resolves the build tags** based on the selected distribution.
- The OpenTelemetry Collector is **built locally** with the overlayed custom components.
- The workflow then checks whether to **skip publishing**:
  - If **No**, it **publishes the built Lambda layer** to the configured AWS regions.
  - If **Yes**, it skips publishing.
- A **summary report** is generated, detailing the build and publish results.
- Finally, **temporary files and directories are cleaned up**.

This process allows rapid local iteration and testing before automating publishing via GitHub Actions.

## Using the Ocelot Local Build Tool

The `tools/ocelot.py` script is the primary CLI utility for building and optionally publishing Lambda layers.

### Usage

```bash
uv run tools/ocelot.py [OPTIONS]
```

### Options

| Option | Description | Default |
|---------|-------------|---------|
| `--distribution, -d` | Distribution preset to build (see [Understanding Distributions](#understanding-distributions)) | `default` |
| `--architecture, -a` | Target architecture (`amd64` or `arm64`) | `amd64` |
| `--upstream-repo, -r` | Upstream OpenTelemetry Lambda repo | `open-telemetry/opentelemetry-lambda` |
| `--upstream-ref, -b` | Upstream Git reference (branch, tag, SHA) | `main` |
| `--layer-name, -l` | Base name for the Lambda layer | `ocel` |
| `--runtimes` | Space-delimited list of compatible runtimes or empty| _empty_ |
| `--skip-publish` | Skip publishing to AWS, only build locally | *false* |
| `--verbose, -v` | Enable verbose output | *false* |
| `--public` | Make the published layer publicly accessible | *false* |
| `--keep-temp` | Keep temporary directories (e.g., upstream clone) | *false* |

### Examples

Build and publish the default distribution:

```bash
uv run tools/ocelot.py --distribution default
```

Build a minimal distribution for ARM64 without publishing:

```bash
uv run tools/ocelot.py -d minimal -a arm64 --skip-publish
```


---

## Managing and Cleaning Up Lambda Layers

> [!WARNING]
> The `tools/reaper.py` script helps you find and delete Lambda layers and associated DynamoDB records. You can use it to clean up old layers and associated DynamoDB records, but keep in mind that it will delete all layers matching the pattern. Use it with caution. And probably you won't need it.

### Usage

```bash
uv run tools/reaper.py [OPTIONS]
```

### Common Options

| Option | Description |
|---------|-------------|
| `--pattern` | Pattern (glob) to match layer names (required) |
| `--dry-run` | Preview deletions without making changes |
| `--force` | Skip confirmation prompts |
| `--regions` | Comma-separated list of AWS regions to target |
| `--verbose` | Enable verbose output |
| `--skip-dynamodb` | Skip deleting DynamoDB records |

### Examples

Preview layers matching "ocel-*" without deleting in all regions:

```bash
uv run tools/reaper.py --pattern "ocel-*" --dry-run
```

Delete all matching layers across `us-east-1` and `eu-west-1` without confirmation:

```bash
uv run tools/reaper.py --pattern "ocel-*" --force --regions us-east-1,eu-west-1
```

Delete layers but keep DynamoDB records:

```bash
uv run tools/reaper.py --pattern ocelot-dev --skip-dynamodb
```

**Warning:** This tool performs destructive actions. Use `--dry-run` first to review what will be deleted. For details on this and other scripts, see [Tooling](docs/tooling.md).

## Running Tests

The project includes a comprehensive test suite covering various components, utilities, and integration scenarios. Tests use `pytest` and are designed to run in isolation without requiring AWS credentials.

### Setting Up the Test Environment

```bash
# Create and activate a virtual environment
uv venv
source .venv/bin/activate # Linux/macOS
# .venv\Scripts\activate # Windows

# Install test dependencies (includes main requirements plus testing packages)
uv pip install -r tools/tests/requirements.txt
```

### Running the Tests

```bash
# Run all tests
python -m pytest tools/tests

# Run tests with coverage information
python -m pytest tools/tests --cov=tools --cov-report=term-missing

# Run specific test files
python -m pytest tools/tests/test_distribution_utils.py

# Run tests with verbose output
python -m pytest tools/tests -v
```

### Import Strategy

The test suite uses a path-manipulation approach in `conftest.py` to make imports work cleanly:

```python
# From tools/tests/conftest.py
import sys
from pathlib import Path

# Add main tools directory to path for local_build modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Add scripts directory to path so otel_layer_utils is importable as a top-level package
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir.resolve()))
```

This strategy:
1. Makes `otel_layer_utils` directly importable in both application code and tests
2. Eliminates the need for conditional imports or import fallbacks
3. Keeps the production code clean while handling import path resolution in the test environment

### Testing Individual Components

For detailed testing of specific utilities:

```bash
# Test build_extension_layer.py with coverage
python -m pytest tools/tests/test_build_extension_layer.py -v --cov=tools.scripts.build_extension_layer --cov-report=term-missing

# Test lambda_layer_publisher.py with coverage
python -m pytest tools/tests/test_lambda_layer_publisher.py -v --cov=tools.scripts.lambda_layer_publisher --cov-report=term-missing
```

---

## Contributing

Contributions are welcome! Please follow this general workflow:

1.  **Fork:** Create your personal fork of the repository on GitHub.
2.  **Clone:** Clone your fork to your local development machine.
3.  **Branch:** Create a new feature branch for your changes (`git checkout -b feature/my-cool-addition`).
4.  **Develop:**
    *   Implement your new component or distribution changes as described in the "Customization Guide".
    *   Ensure necessary documentation is added or updated.
5.  **Test Locally:** Use the local build script (`uv run tools/ocelot.py --distribution YOUR_DISTRIBUTION`) to verify that your changes build successfully and function as expected.
6.  **Commit & Push:** Commit your changes with clear, descriptive messages and push the branch to your fork (`git push origin feature/my-cool-addition`).
7.  **Pull Request:** Open a Pull Request from your feature branch to the `main` branch of the original `dev7a/ocelot` repository. Provide a detailed description of your contribution.
8.  **Review:** Engage in the review process and address any feedback.

## Setting Up Your Fork for Automated Publishing

To enable GitHub Actions in your fork to publish layers to your own AWS account, you need to configure AWS resources (IAM Role via OIDC, DynamoDB) and corresponding GitHub secrets. You can check the [oidc/README.md](oidc/README.md) file for detailed instructions on how to set it up on your fork.


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for full details.
