---
title: Configuration
weight: 30
cascade:
  type: docs
---

Ocelot uses a central configuration file, `config/distributions.yaml`, to define "distributions"—pre-defined sets of OpenTelemetry Collector components tailored for specific use cases.

## Understanding Distributions

A distribution is essentially a named collection of Go build tags. When you build a distribution, Ocelot uses these tags to tell the Go compiler which component files to include in the final collector binary.

This mechanism allows you to create highly optimized Lambda layers that contain only the components you need, minimizing size and cold start times.

### The `distributions.yaml` File

Here is the structure of the `config/distributions.yaml` file:

```yaml
distributions:
  # The base upstream collector with standard components
  default:
    description: "Base upstream components"
    build-tags:
      - "lambdacomponents.receiver.otlp"
      - "lambdacomponents.exporter.otlp"
      # ... and other default exporters, processors, extensions
  
  # A minimal distribution for common use cases
  minimal:
    description: "OTLP receiver, Batch processor, Decouple processor, OTLP/HTTP exporter"
    build-tags:
      - "lambdacomponents.receiver.otlp"
      - "lambdacomponents.processor.batch"
      - "lambdacomponents.processor.decouple"
      - "lambdacomponents.exporter.otlphttp"

  # A distribution that builds on top of another
  minimal-clickhouse:
    description: "Minimal + ClickHouse exporter"
    base: minimal
    build-tags:
      - "lambdacomponents.exporter.clickhouse"
    
  # A distribution with a custom collector configuration file
  minimal-s3export:
    description: "Minimal + AWS S3 exporter and custom config"
    base: minimal
    config-file: "s3-export-config.yaml"
    build-tags:
      - "lambdacomponents.exporter.awss3"
```

### Key Concepts

- **`build-tags`**: A list of Go build tags. The build system combines these to select which components to compile.
- **`base`**: (Optional) A distribution can inherit all build tags from a `base` distribution. This promotes reuse and simplifies definitions. The final set of build tags used is the unique union of the base tags and the distribution-specific tags.
- **`config-file`**: (Optional) The path to a custom OpenTelemetry Collector configuration YAML file located in `config/examples/`. If provided, this file is packaged into the Lambda layer as `config.yaml`, replacing the upstream default. This is useful for creating layers with pre-configured settings.
- **`lambdacomponents.custom`**: This special build tag is **automatically included** for all distributions *except* `default`. It is the key that enables Ocelot's overlay mechanism, ensuring that the custom components in this repository are included in the build. 