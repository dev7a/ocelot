# OCELOT  
> The **O**penTelemetry **C**ollector **E**xtension **L**ayer **O**ptimization **T**oolkit  
> *A fast, flexible way to build custom Lambda Extension Layers.*

Like its namesake, **OCELOT** is small, fast, and sharp. This project offers a customizable build system for AWS Lambda Extension Layers powered by the OpenTelemetry Collector. It leverages the excellent build tag system from the [OpenTelemetry Lambda project](https://github.com/open-telemetry/opentelemetry-lambda), making it easy to add custom observability components without forking or maintaining upstream code.


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
- [Contributing](#contributing)
- [Setting Up Your Fork for Automated Publishing](#setting-up-your-fork-for-automated-publishing)
- [License](#license)

## Overview: The Overlay Approach

Maintaining a fork of a rapidly evolving upstream project like OpenTelemetry Lambda can lead to significant maintenance overhead and merge conflicts. **Ocelot** employs an **overlay** strategy, made possible by the upstream project's Go build tag system, to circumvent these issues. Instead of forking, this repository contains only the custom components and the necessary build configurations.

The build process works as follows:

1.  **Clone Upstream:** Fetches the specified version of the `open-telemetry/opentelemetry-lambda` repository.
2.  **Apply Overlay:** Copies the custom Go components defined within this repository (`components/collector/lambdacomponents/`) into the appropriate directories of the cloned upstream source code.
3.  **Build Collector:** Compiles the OpenTelemetry Collector using the upstream project's Go build tag system, guided by the tags derived from the selected ocelot distribution, incorporating both standard and custom components.
4.  **Package Layer:** Creates a `.zip` archive suitable for deployment as an AWS Lambda Layer.
5.  **Publish (Optional):** Uploads the layer to specified AWS regions and records metadata.

This approach allows for seamless integration of custom functionality while staying synchronized with upstream developments, significantly reducing maintenance efforts.

## Build and Deployment Options

Choose the method that best suits your workflow and requirements:

1.  **Use Pre-built Layers:** Find layers for various distributions published in the [Releases](https://github.com/dev7a/ocelot/releases) section of this repository. This is the simplest way to use standard or common custom distributions.
2.  **Local Build:** Compile and publish layers directly from your local machine to your AWS account. Ideal for testing custom components, development, or managing private layers not intended for public release.
3.  **Fork and Use GitHub Actions:** Fork this repository to create your own private build system. Configure the GitHub Actions workflow within your fork with your AWS credentials (using OIDC and secrets) for secure, automated publishing of *your* custom layers to *your* AWS account. See the "Setting Up Your Fork for Automated Publishing" section for details.

## Getting Started: Local Build

To build layers locally, ensure you have the following prerequisites installed:

1.  **Go:** The latest stable version. ([Installation Guide](https://go.dev/doc/install))
2.  **uv:** A fast Python package manager. ([Installation Guide](https://docs.astral.sh/uv/getting-started/installation/))
3.  **AWS Credentials:** Configured for programmatic access (e.g., via `~/.aws/credentials`, environment variables, or IAM role).

**Build Steps:**

```bash
# Navigate to the ocelot project directory
# Set up a virtual environment and install dependencies
uv venv
source .venv/bin/activate # Linux/macOS
# .venv\Scripts\activate # Windows
uv pip install -r tools/requirements.txt

# Execute the local build script
# Specify the desired distribution (e.g., minimal, default, clickhouse, full)
uv run tools/ocelot.py --distribution minimal
```

This command performs the clone, overlay, build, and packaging steps for the `minimal` distribution and `amd64` architecture by default. It saves the resulting `.zip` file in the `build/` directory and publishes the layer to your configured default AWS region.

Use `uv run tools/ocelot.py --help` for additional options, such as specifying architecture (`--arch`), target regions (`--region`), or skipping publishing (`--skip-publish`).

## Understanding Distributions

**Ocelot** supports building different "distributions," which are pre-defined sets of OpenTelemetry Collector components tailored for specific use cases. These are defined in `config/distributions.yaml`.

| Distribution     | Description                                                      | Base     | Build Tags                                                                                      |
|------------------|------------------------------------------------------------------|----------|------------------------------------------------------------------------------------------------|
| `default`        | Standard upstream components                                     | *none*   | *(empty)*                                                                                       |
| `full`           | All available upstream and custom components                     | *none*   | `lambdacomponents.custom`, `lambdacomponents.all`                                               |
| `minimal`        | OTLP receiver, Batch processor, Decouple processor, OTLP/HTTP exporter | *none*   | `lambdacomponents.custom`, `lambdacomponents.receiver.otlp`, `lambdacomponents.processor.batch`, `lambdacomponents.processor.decouple`, `lambdacomponents.exporter.otlphttp` |
| `clickhouse`     | Minimal + ClickHouse exporter                                   | minimal  | `lambdacomponents.exporter.clickhouse`                                                          |
| `exporters`      | All exporters plus minimal components                            | minimal  | `lambdacomponents.exporter.all`                                                                 |
| `s3export`       | Minimal + AWS S3 exporter                                       | minimal  | `lambdacomponents.exporter.awss3`                                                               |
| `signaltometrics`| Minimal + Signal to Metrics connector                           | minimal  | `lambdacomponents.connector.signaltometrics`                                                    |

**Build Tag Mechanism:** The `lambdacomponents.custom` build tag is automatically included for all distributions except `default`, enabling the overlay mechanism. Distributions can inherit build tags from a `base` distribution defined in the configuration, promoting reuse and simplifying definitions. The final set of build tags used during compilation is the unique union of base tags and distribution-specific tags.

### Upstream Default Components

The `default` distribution includes the following standard components from `open-telemetry/opentelemetry-lambda`:

*   **Receivers:** `otlp`, `telemetryapi`
*   **Exporters:** `debug`, `otlp`, `otlphttp`, `prometheusremotewrite`
*   **Processors:** `attributes`, `filter`, `memory_limiter`, `probabilistic_sampler`, `resource`, `span`, `coldstart`, `decouple`, `batch`
*   **Extensions:** `sigv4auth`, `basicauth`
*   **Connectors:** None.

Refer to the upstream OpenTelemetry Lambda and Collector Contrib documentation for detailed configuration of these components.

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

Extend **ocelot** with your own components and distributions:

**Adding a New Custom Go Component (e.g., `myprocessor`):**

1.  **Place Go File:** Create your component file (`myprocessor.go`) in the corresponding directory within the overlay structure: `components/collector/lambdacomponents/processor/myprocessor.go`.
2.  **Apply Build Tags:** Add the necessary Go build constraints at the top of your file:
    ```go
    //go:build lambdacomponents.custom && (lambdacomponents.all || lambdacomponents.processor.all || lambdacomponents.processor.myprocessor)
    ```
    These tags control when your component is compiled into the collector based on the selected distribution.
3.  **Declare Go Dependencies (If Required):** If your component relies on external Go modules not present in the upstream project, declare them in `config/component_dependencies.yaml` using the component's specific build tag as the key:

    ```yaml
    dependencies:
      # ... existing entries ...
      lambdacomponents.processor.myprocessor:
        - github.com/dependency-org/dependency-repo/v1
    ```

    The build script (`tools/local_build/build.py`) will automatically fetch these dependencies using `go get`.
4.  **Add Documentation:** Create a markdown file (e.g., `docs/myprocessor.md`) detailing the configuration and usage of your component.
5.  **Update README:** List your new component in the "Current Custom Components" section below.

**Defining a New Distribution Preset (e.g., `analytics-focused`):**

1.  **Modify Configuration:** Edit `config/distributions.yaml`.
2.  **Add Definition:** Define your new distribution, potentially inheriting from a base:

    ```yaml
    base-standard:
      description: "Common components"
      buildtags:
        - lambdacomponents.custom
        - lambdacomponents.receiver.otlp
        - lambdacomponents.processor.batch

    analytics-focused:
      description: "Standard base plus my custom processor"
      base: base-standard # Inherit tags from base-standard
      buildtags:
        # Add only the additional tags needed
        - lambdacomponents.processor.myprocessor
    ```
    
3.  **Update Workflow File:** Manually add the new distribution name (`analytics-focused`) to the `options` list for the `distribution` input in the `.github/workflows/publish-custom-layer-collector.yml` file to make it selectable in the GitHub Actions UI.
4.  **Update README:** Include your new distribution in the "Understanding Distributions" table.

## Current Custom Components

*   **ClickHouse Exporter**: Enables exporting telemetry data directly to ClickHouse databases. ([docs/clickhouse.md](docs/clickhouse.md))
*   **AWS S3 Exporter**: Enables exporting telemetry data directly to Amazon S3 buckets.
*   **SignalToMetrics Connector**: Converts signal data (e.g., spans) into metrics. (`components/collector/lambdacomponents/connector/signaltometricsconnector.go`)
*   *(Your custom component could be listed here!)*

## Architecture

The build system for Ocelot integrates multiple layers of tooling to streamline the creation and deployment of custom OpenTelemetry Lambda Layers. At its core, it leverages the upstream [OpenTelemetry Lambda](https://github.com/open-telemetry/opentelemetry-lambda) project's Makefile, which orchestrates the compilation of the OpenTelemetry Collector as a Go binary. This Makefile handles tasks such as cleaning previous builds, embedding version and Git metadata via linker flags, and packaging the resulting binary into a Lambda-compatible zip archive. The Go build process itself uses specific build tags to include or exclude components, enabling highly customizable collector builds tailored for serverless environments.

Complementing this, Ocelot introduces a suite of Python scripts and libraries that automate and extend the upstream build process. These Python tools handle cloning the upstream repository, applying overlays of custom Go components, resolving build tags based on user-selected distributions, and managing AWS interactions such as publishing Lambda layers across multiple regions. They provide a flexible CLI (`tools/ocelot.py`) that abstracts away the complexity of manual Makefile invocation, environment setup, and AWS CLI commands. This layered approach allows developers to rapidly iterate on custom components, automate multi-region publishing, and maintain alignment with upstream changes—all without directly modifying the upstream build system.

### Build and Deployment Workflows

The following diagrams illustrate the system's workflow for both automated (GitHub Actions) and local builds.

### GitHub Actions Workflow

![image](https://github.com/user-attachments/assets/c1d9c276-ecea-49f3-ba61-5f19590a7402)


This diagram illustrates the **automated publishing workflow** using GitHub Actions:

- The process starts with a **manual trigger** of the workflow.
- The environment is prepared, including setting up AWS credentials and build parameters.
- Multiple **parallel build jobs** are launched, each targeting a specific architecture (e.g., `amd64`, `arm64`).
- After building, **parallel release jobs** publish the built Lambda layers to the specified AWS regions.
- All release jobs converge to a step that **generates reports** summarizing the published layers.
- Finally, a **GitHub Release** is created or updated with the new layer artifacts and metadata.

This automation enables multi-architecture, multi-region publishing with minimal manual intervention.

### Local Development Workflow

![image](https://github.com/user-attachments/assets/e9f827cb-9186-4c28-bdc6-68617b394738)

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

Inject an error for testing:

```bash
LOCAL_BUILD_INJECT_ERROR=clone_repository uv run tools/ocelot.py -d minimal
```

---

## Managing and Cleaning Up Lambda Layers

The `tools/delete-layers.py` script helps you find and delete Lambda layers and associated DynamoDB records.

### Usage

```bash
uv run tools/delete-layers.py [OPTIONS]
```

### Common Options

| Option | Description |
|---------|-------------|
| `--pattern` | Pattern to match layer names (required) |
| `--dry-run` | Preview deletions without making changes |
| `--force` | Skip confirmation prompts |
| `--regions` | Comma-separated list of AWS regions to target |
| `--verbose` | Enable verbose output |
| `--skip-dynamodb` | Skip deleting DynamoDB records |

### Examples

Preview layers matching "ocelot-dev" without deleting:

```bash
uv run tools/delete-layers.py --pattern ocelot-dev --dry-run
```

Delete all matching layers across `us-east-1` and `eu-west-1` without confirmation:

```bash
uv run tools/delete-layers.py --pattern ocelot-dev --force --regions us-east-1,eu-west-1
```

Delete layers but keep DynamoDB records:

```bash
uv run tools/delete-layers.py --pattern ocelot-dev --skip-dynamodb
```

**Warning:** This tool performs destructive actions. Use `--dry-run` first to review what will be deleted.

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

To enable GitHub Actions in your fork to publish layers to your own AWS account, you need to configure AWS resources (IAM Role via OIDC, DynamoDB) and corresponding GitHub secrets.

Detailed instructions and the necessary CloudFormation template are provided in the [**OIDC Setup Guide (oidc/README.md)**](./oidc/README.md).


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for full details.
