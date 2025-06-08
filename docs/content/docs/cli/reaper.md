---
title: "reaper.py"
weight: 2
---

The `tools/reaper.py` script helps you find and delete Lambda layers and their associated DynamoDB metadata records from your AWS account. It is a powerful cleanup utility that should be used with caution.

> [!WARNING] Use with Caution
> This tool performs destructive actions. The `reaper.py` script will delete all layer versions matching the specified pattern across the targeted regions. It is highly recommended to perform a `--dry-run` first to review what will be deleted before running the command destructively.

## Usage

```bash
uv run tools/reaper.py [OPTIONS]
```