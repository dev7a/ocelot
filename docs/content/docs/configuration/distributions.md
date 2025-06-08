---
title: Available Distributions
weight: 2
---

Ocelot provides several pre-defined distributions in `config/distributions.yaml`. You can use them as-is or as a base for your own custom distributions.

| Distribution | Description | Base | Key Build Tags / Components |
| :--- | :--- | :--- | :--- |
| `default` | Base upstream components | *none* | Includes standard upstream components like OTLP receiver, OTLP exporter, Batch processor, etc. Does **not** include the `lambdacomponents.custom` tag. |
| `full` | All available upstream and custom components | *none* | `lambdacomponents.custom`, `lambdacomponents.all` |
| `minimal` | OTLP receiver, Batch processor, Decouple processor, OTLP/HTTP exporter | *none* | `receiver.otlp`, `processor.batch`, `processor.decouple`, `exporter.otlphttp` |
| `minimal-clickhouse` | Minimal + ClickHouse exporter | `minimal` | `exporter.clickhouse` |
| `minimal-s3export` | Minimal + AWS S3 exporter | `minimal` | `exporter.awss3` |
| `minimal-asmauth` | Minimal + AWS Secrets Manager Auth extension | `minimal` | `extension.asmauthextension` |
| `minimal-signaltometrics` | Minimal + Signal to Metrics connector | `minimal` | `connector.signaltometrics` |
| `minimal-spaneventtolog` | Minimal + Span Event to Log connector | `minimal` | `connector.spaneventtolog` |
| `minimal-forwarder` | Minimal + Multiple connectors & extensions for the [Serverless OTLP forwarder](https://github.com/dev7a/serverless-otlp-forwarder) | `minimal` | `connector.signaltometrics`, `connector.spaneventtolog`, `extension.asmauthextension` |

> [!NOTE]
> The `lambdacomponents.` prefix is omitted from the "Key Build Tags" column for brevity. All tags are prefixed accordingly (e.g., `exporter.clickhouse` is actually `lambdacomponents.exporter.clickhouse`).

## How to Define a New Distribution

To define a new distribution, add an entry to the `distributions` map in `config/distributions.yaml`.

### Example: Creating a "minimal-prometheus" Distribution

Let's say you need a minimal build that can send metrics to Prometheus.

1.  **Open `config/distributions.yaml`**.
2.  **Add a new entry**. We'll use `minimal` as a `base` to inherit its components and add the `prometheusremotewrite` exporter.

```yaml
distributions:
  # ... other distributions
  minimal:
    # ...
  
  minimal-prometheus:
    description: "Minimal + Prometheus Remote Write exporter"
    base: minimal
    build-tags:
      - "lambdacomponents.exporter.prometheusremotewrite"
```

3.  **Build your new distribution**:

```bash
uv run tools/ocelot.py --distribution minimal-prometheus
```

That's it! Ocelot will combine the build tags from `minimal` with `lambdacomponents.exporter.prometheusremotewrite` to create the exact layer you need. 