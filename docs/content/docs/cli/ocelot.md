---
title: "ocelot.py"
weight: 1
---

# Build Tool: `ocelot.py`

The `tools/ocelot.py` script is the primary CLI utility for building and optionally publishing Lambda layers.

## Usage

```bash
uv run tools/ocelot.py [OPTIONS]
```

## Options

| Option | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--distribution` | `-d` | Distribution preset to build from `config/distributions.yaml`. | `default` |
| `--architecture` | `-a` | Target architecture (`amd64` or `arm64`). | `amd64` |
| `--upstream-repo` | `-r` | The upstream `user/repo` to clone. | `open-telemetry/opentelemetry-lambda` |
| `--upstream-ref` | `-b` | The git reference (branch, tag, or SHA) of the upstream repo to use. | `main` |
| `--layer-name` | `-l` | Base name for the Lambda layer. | `ocel` |
| `--runtimes` | | A space-delimited list of compatible runtimes for the layer (e.g., `python3.9 nodejs18.x`). | (empty) |
| `--skip-publish`| | If set, the script will only build the layer locally and not publish it to AWS. | `false` |
| `--verbose` | `-v` | Enable verbose output for debugging. | `false` |
| `--public` | | If set, the published Lambda layer will be publicly accessible. | `false` |
| `--keep-temp` | | If set, the script will not delete temporary directories (e.g., the upstream clone). | `false` |

## Examples

#### Build and publish the default distribution
This command builds the standard `default` distribution for `amd64` and publishes it to your configured AWS account and region.
```bash
uv run tools/ocelot.py --distribution default
```

#### Build a minimal distribution for ARM64 without publishing
A common development task is to build a layer for inspection without pushing it to AWS.
```bash
uv run tools/ocelot.py -d minimal -a arm64 --skip-publish
```

#### Build from a specific upstream version
You can target a specific tag or branch from the upstream repository, which is useful for ensuring reproducible builds.
```bash
uv run tools/ocelot.py -d minimal --upstream-ref v1.20.0
```

#### Build a layer with a custom name and runtimes
This example creates a layer named `my-custom-otel-layer` compatible with specific runtimes.
```bash
uv run tools/ocelot.py \
  -d minimal-clickhouse \
  -l my-custom-otel-layer \
  --runtimes "python3.10 python3.11"
``` 