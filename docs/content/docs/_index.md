---
title: Documentation
cascade:
  type: docs
---

**Ocelot** (OpenTelemetry Collector Extension Layer Optimization Toolkit) is a toolkit designed to simplify the creation of custom AWS Lambda Extension Layers for the OpenTelemetry Collector. 

This documentation provides a comprehensive guide to understanding, using, and extending Ocelot. Whether you want to use pre-built layers, build your own, or contribute to the project, you'll find the necessary information here.
 
## How to Use Ocelot

There are three primary ways to get and use Ocelot layers, depending on your needs:

1.  **Use Pre-built Layers (Easiest)**
    -   Find layers for various distributions published in the [**Releases**](https://github.com/dev7a/ocelot/releases) section of the repository. This is the simplest way to get started with standard or common custom distributions.

2.  **Local Build (For Development & Testing)**
    -   Compile and publish layers directly from your local machine to your own AWS account. This is ideal for testing custom components or managing private layers. See the [**Quickstart Guide**](quickstart) to begin.

3.  **Fork and Use GitHub Actions (For Automation)**
    -   Fork the repository to create your own private build system. You can configure the CI/CD workflow to securely and automatically publish *your* custom layers to *your* AWS account. See the [**Contributing Guide**](contributing) for more.

## Main Sections

- **[Quickstart Guide](quickstart)**: Get up and running with a local build.
- **[Architecture](architecture)**: Understand how Ocelot works, from its overlay strategy to its build workflows.
- **[Configuration](configuration)**: Learn about distributions and how to define them.
- **[Components](components)**: Discover the available custom components and how to add your own.
- **[Tooling & CLI](cli)**: A detailed reference for the command-line tools.
- **[Contributing](contributing)**: Guidelines for contributing to the Ocelot project.
- **[Development](development)**: Information on running tests and setting up your environment.
- **[Glossary](glossary)**: Definitions of key terms used in Ocelot.

## Overview

ocelot provides:
- OpenTelemetry-native telemetry collection
- Optimized performance for AWS Lambda
- Flexible telemetry processing and filtering
- Multi-backend export capabilities
- Production-ready observability solutions

## Getting Started

Start with our [Quickstart Guide](quickstart) to get ocelot running in your environment.

## Architecture

Learn about ocelot's architecture and components:
- [Core Components](architecture/components)
- [Telemetry Pipeline](architecture/pipeline)
- [AWS Lambda Integration](architecture/lambda)

## Configuration

Detailed configuration guides:
- [Basic Configuration](configuration/basic)
- [Advanced Settings](configuration/advanced)
- [Performance Tuning](configuration/performance) 