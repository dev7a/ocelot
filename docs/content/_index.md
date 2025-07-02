---
title: ocelot
toc: false
showTitle: false
---

<div class="hero-section" id="hero-parallax">
  <div class="hero-content">
    <h1 class="hero-title">OCELOT</h1>
    <div class="hero-cta">
      <a href="/ocelot/docs/quickstart" class="hero-button hero-button-primary">Get Started</a>
      <a href="/ocelot/docs/architecture" class="hero-button hero-button-secondary">Architecture</a>
    </div>
    <p class="hero-description">A fast, flexible way to build custom AWS Lambda Extension Layers for the OpenTelemetry Collector.</p>
  </div>
</div>

**Ocelot** _(OpenTelemetry Collector Extension Layer Optimization Toolkit)_ is a toolkit designed to simplify the creation of custom AWS Lambda Extension Layers for the OpenTelemetry Collector. It helps you add specific observability components or optimize your collector for particular use cases without maintaining a complex fork.

Ocelot integrates with the official [OpenTelemetry Lambda project](https://github.com/open-telemetry/opentelemetry-lambda) by leveraging its Go build tag system. This allows for the seamless inclusion of custom elements.

It functions as both a powerful CLI for local development and a CI/CD pipeline on GitHub Actions, enabling you to build, customize, and publish layers to your own AWS account or contribute them back to the community.

## Get Started

{{< cards >}}
  {{< card link="docs/quickstart" title="Quickstart" icon="play" >}}
  {{< card link="docs/architecture" title="Architecture" icon="cog" >}}
  {{< card link="docs/components" title="Components" icon="cube" >}}
{{< /cards >}}

## Key Capabilities

- **Overlay Approach:** Avoids forking the upstream repository, reducing maintenance overhead.
- **Flexible Distributions:** Build tailored collector layers with pre-defined or custom component sets.
- **Multiple Build Options:** Use pre-built layers, build locally, or set up a fully automated pipeline in your own fork.
- **Automated Publishing:** Securely publish layers to multiple AWS regions and architectures using GitHub Actions and OIDC.
- **Customizable Configurations:** Package custom OpenTelemetry Collector `config.yaml` files within your layers.

## Quick Example

Define a custom distribution in `config/distributions.yaml`:

```yaml
distributions:
  my-custom-layer:
    description: "OTLP receiver + ClickHouse exporter for data analytics"
    base: minimal
    build-tags:
      - "lambdacomponents.exporter.clickhouse"
```

Build and publish your custom layer:

```bash
uv run tools/ocelot.py --distribution my-custom-layer
```

That's it! Ocelot will:
1. Clone the upstream OpenTelemetry Lambda repository
2. Apply your custom components as an overlay
3. Build a collector binary with only the components you need
4. Package it as a Lambda layer and publish to AWS

> [!NOTE]
> This is a work in progress, and the implementation is subject to change.

For more information, visit the [documentation]({{< relref "docs" >}}). 

<script src="/ocelot/js/parallax.js"></script>
