# OCELOT  
**OpenTelemetry Collector Extension Layer Optimization Toolkit**

[![Build Status](https://img.shields.io/github/actions/workflow/status/dev7a/ocelot/ci.yml?branch=main)](https://github.com/dev7a/ocelot/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-website-blue)](https://dev7a.github.io/ocelot/)

Build custom, optimized AWS Lambda Extension Layers for the OpenTelemetry Collector with ease. Ocelot simplifies adding specific observability components, integrating with the upstream OpenTelemetry Lambda project via an "overlay" strategy to avoid forking.

> [!WARNING]
> **Alpha Software Notice**: Ocelot is currently in alpha development. While functional and actively used, the CLI, APIs, and configuration format may change between versions. We welcome feedback and contributions.

## Why Ocelot?

Building custom OpenTelemetry layers for AWS Lambda often requires forking the upstream `open-telemetry/opentelemetry-lambda` repository, leading to maintenance overhead. Ocelot solves this by allowing you to define custom "distributions" of the collector, building only what you need.

## Quick Example

Define a custom distribution in `config/distributions.yaml`:

```yaml
distributions:
  my-custom-layer:
    description: "A minimal layer with a ClickHouse exporter"
    base: minimal
    build-tags:
      - "lambdacomponents.exporter.clickhouse"
```

Build and publish your custom layer with a single command:
```bash
uv run tools/ocelot.py --distribution my-custom-layer
```

Ocelot automatically:
- ✅ Clones the upstream OpenTelemetry Lambda repository
- ✅ Applies your custom components as an overlay
- ✅ Builds a lean collector binary with only the components you need
- ✅ Packages it as a Lambda layer and publishes it to your AWS account

## Key Features

- **Overlay Strategy:** Avoid forking the upstream repository, reducing maintenance overhead.
- **Flexible Distributions:** Build tailored collector layers with pre-defined or custom component sets.
- **Multiple Build Options:** Use pre-built layers, build locally, or set up a fully automated pipeline in your own fork.
- **Automated Publishing:** Securely publish layers to multiple AWS regions and architectures using GitHub Actions and OIDC.
- **Customizable Configurations:** Package custom OpenTelemetry Collector `config.yaml` files within your layers.

## How to Get Started

There are three primary ways to get and use Ocelot layers:

1.  **Use Pre-built Layers (Easiest)**: Find layers for various distributions in the [**Releases**](https://github.com/dev7a/ocelot/releases) section.
2.  **Local Build**: Compile and publish layers directly from your local machine. See the [**Quickstart Guide**](https://dev7a.github.io/ocelot/docs/quickstart/) to begin.
3.  **Fork and Use GitHub Actions**: Set up your own automated build system. See the guide on [**Setting Up Your Fork**](https://dev7a.github.io/ocelot/docs/contributing/setup-fork/).

## Prerequisites for Local Build

- **Go (latest stable)**: For compiling the collector.
- **uv**: A fast Python package manager for running the build scripts.
- **AWS Credentials**: Configured for programmatic access to publish layers.

## Documentation

📖 **[Complete Documentation →](https://dev7a.github.io/ocelot/)**

Our comprehensive documentation includes:

- **[Quickstart Guide](https://dev7a.github.io/ocelot/docs/quickstart/)**: Build your first custom layer in minutes.
- **[Architecture Deep Dive](https://dev7a.github.io/ocelot/docs/architecture/)**: Understand the overlay strategy.
- **[Component & Distribution Guides](https://dev7a.github.io/ocelot/docs/components/)**: Learn how to add custom components.
- **[CLI Reference](https://dev7a.github.io/ocelot/docs/cli/)**: All command-line options and usage.
- **[Contributing Guide](https://dev7a.github.io/ocelot/docs/contributing/)**: Learn how to contribute to Ocelot.

## Contributing

Contributions are welcome! Please see our [Contributing Guidelines](https://dev7a.github.io/ocelot/docs/contributing/) for details on the development workflow.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for full details.
