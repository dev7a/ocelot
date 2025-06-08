---
title: Quickstart
weight: 1
---

This guide walks you through building a custom OpenTelemetry Collector Lambda Layer directly from your local machine. This is the ideal starting point for testing custom components, developing new features, or managing private layers.

## Prerequisites

Before you begin, ensure you have the following installed:

1.  **Go:** The latest stable version. See the [official Go installation guide](https://go.dev/docs/install).
2.  **uv:** A fast Python package manager used to run the Ocelot build scripts. See the [Astral `uv` installation guide](https://docs.astral.sh/uv/getting-started/installation/).
3.  **AWS Credentials:** Your environment must be configured for programmatic AWS access. This can be done via `~/.aws/credentials`, environment variables, or an IAM role. The credentials need permissions to publish Lambda layers (e.g., `lambda:PublishLayerVersion`).

## Build and Publish Your First Layer

The primary tool for local builds is `tools/ocelot.py`. You can run it easily using `uv`.

The following command builds the `minimal` distribution for the `amd64` architecture, packages it into a `.zip` file, and publishes it to your default AWS region:

```bash
uv run tools/ocelot.py --distribution minimal
```

### What This Command Does

1.  **Clones Upstream:** Fetches the `open-telemetry/opentelemetry-lambda` repository.
2.  **Applies Overlay:** Copies custom components from this project into the cloned upstream source.
3.  **Builds Collector:** Compiles the OpenTelemetry Collector, including the components defined in the `minimal` distribution.
4.  **Packages Layer:** Creates a `.zip` archive in the `build/` directory.
5.  **Publishes to AWS:** Uploads the `.zip` as a new Lambda Layer version in your AWS account.

## Build Without Publishing

If you only want to build the layer locally for inspection or testing without publishing it to AWS, use the `--skip-publish` flag:

```bash
uv run tools/ocelot.py -d minimal -a arm64 --skip-publish
```
This command will build the `minimal` distribution for the `arm64` architecture and place the resulting `.zip` file in the `build/` directory.

## Exploring Other Options

The build tool has many options for customization. Use the `--help` flag to see them all:

```bash
uv run tools/ocelot.py --help
```

This will show you how to specify different architectures, upstream versions, layer names, and more.

## Next Steps

- **[Understand the Architecture]({{< relref "/docs/architecture" >}})**: Learn about the "overlay" approach and build workflows.
- **[Explore Distributions]({{< relref "/docs/configuration" >}})**: See what other component sets are available or learn how to define your own.
- **[Add a Custom Component]({{< relref "/docs/components" >}})**: Start building your own custom exporters, processors, or receivers. 