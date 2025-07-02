---
title: Tooling & CLI
weight: 35
cascade:
  type: docs
---

# Tooling & CLI Reference

Ocelot comes with a set of command-line interface (CLI) tools to help you build, manage, and clean up Lambda layers. These tools are Python scripts located in the `tools/` directory and are designed to be run with `uv`.

## Main Tools

- **[`ocelot.py`](ocelot)**: The primary utility for building and publishing custom Lambda layers. This is the tool you will use most often.

- **[`reaper.py`](reaper)**: A cleanup utility for finding and deleting old or unused Lambda layers and their associated metadata from your AWS account. Use with caution.

## Global Options

While each script has its own set of options, some common conventions apply:

- **`--help`**: All scripts support a `--help` flag to display detailed usage information and all available options.
- **`--verbose` / `-v`**: Enables more detailed logging output, which is useful for debugging.
- **`--dry-run`**: For destructive operations like `reaper.py`, this flag allows you to preview the changes without actually executing them.
- **`--regions`**: Specifies a comma-separated list of AWS regions to target for an operation.

## Commands

### Main Commands

- [`ocelot`](ocelot) - Start the ocelot collector
- [`ocelot config`](config) - Configuration management
- [`ocelot validate`](validate) - Validate configuration files
- [`ocelot version`](version) - Show version information

### Global Options

All commands support these global options:

| Flag | Description | Default |
|------|-------------|---------|
| `--config` | Path to configuration file | `ocelot.yaml` |
| `--log-level` | Log level (debug, info, warn, error) | `info` |
| `--help` | Show help information | - |

## Examples

### Basic Usage

```bash
# Start with default configuration
ocelot

# Start with custom configuration
ocelot --config /path/to/config.yaml

# Validate configuration
ocelot validate --config config.yaml
```

### Advanced Usage

```bash
# Debug mode with verbose logging
ocelot --log-level debug

# Check configuration syntax
ocelot config validate

# Show version and build information
ocelot version --verbose
``` 