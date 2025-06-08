---
title: Upstream Integration
weight: 3
---

# Upstream Integration

Ocelot's build system is designed to work in concert with the tooling provided by the upstream `open-telemetry/opentelemetry-lambda` project. It extends, rather than replaces, the upstream build process.

## Core Tooling Layers

The system integrates multiple layers of tooling to streamline the creation and deployment of custom layers:

1.  **Upstream Makefile**: At its core, Ocelot leverages the upstream project's `Makefile`. This orchestrates the fundamental compilation of the OpenTelemetry Collector Go binary. The Makefile handles critical tasks like:
    -   Cleaning previous builds.
    -   Embedding version and Git metadata into the binary via linker flags.
    -   Packaging the resulting binary into a Lambda-compatible zip archive.
    -   Using Go build tags to include or exclude components for serverless environments.

2.  **Ocelot Python Scripts**: Complementing the Makefile, Ocelot introduces a suite of Python scripts and libraries that automate and extend the build process. These tools are responsible for:
    -   Cloning the upstream repository to a temporary location.
    -   Applying the overlay of custom Go components.
    -   Resolving the final set of build tags based on the user-selected distribution from `config/distributions.yaml`.
    -   Managing all AWS interactions, such as publishing Lambda layers across multiple regions.
    -   Providing a flexible CLI (`tools/ocelot.py`) that abstracts away the complexity of manual Makefile invocations, environment setup, and AWS commands.

This layered approach allows developers to rapidly iterate on custom components, automate multi-region publishing, and maintain alignment with upstream changes—all without needing to directly modify the upstream build system itself. 