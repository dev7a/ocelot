---
title: Build Workflows
weight: 2
---

# Build and Deployment Workflows

Ocelot supports two primary workflows for building and deploying layers: a fully automated process using GitHub Actions for production-ready releases, and a flexible local workflow for development and testing.

## Automated GitHub Actions Workflow

This workflow is designed for robust, repeatable, and secure publishing of layers. It is triggered manually and orchestrates the entire build-and-release process across multiple architectures and regions.

![CI/CD with Github Actions](https://github.com/user-attachments/assets/3d45467a-34b4-4929-9e30-9a2a309586c8)

### Workflow Steps:

1.  **Manual Trigger**: The workflow is initiated from the GitHub Actions UI.
2.  **Environment Setup**: Securely sets up AWS credentials using OIDC and configures build parameters.
3.  **Parallel Builds**: Launches multiple build jobs, each targeting a specific architecture (e.g., `amd64`, `arm64`). This significantly speeds up the process.
4.  **Parallel Releases**: After a successful build, release jobs publish the layer artifacts to all configured AWS regions in parallel.
5.  **Reporting**: Once all release jobs complete, a summary report is generated.
6.  **GitHub Release**: A GitHub Release is created or updated with the new layer ARNs, zip files, and other metadata.

This automated approach is ideal for production environments, ensuring that releases are consistent and reliable.

## Local Development Workflow

This workflow provides the flexibility needed for rapid iteration during development. It uses the `tools/ocelot.py` CLI to give developers full control over the build process on their local machine.

![Local Development](https://github.com/user-attachments/assets/1a824d39-2fcf-4bf7-9223-b706ba2502d9)

### Workflow Steps:

1.  **CLI Invocation**: The developer runs the `ocelot.py` script with desired parameters (e.g., distribution, architecture).
2.  **Configuration Loading**: The script loads `config/distributions.yaml` to determine the component set and build tags.
3.  **Upstream Clone**: Clones the `open-telemetry/opentelemetry-lambda` repository.
4.  **Tag Resolution**: Resolves the final list of Go build tags based on the selected distribution and its potential base.
5.  **Local Build**: Compiles the collector binary with the overlayed custom components.
6.  **Publish Decision**: The developer can choose to publish the layer to AWS or just build it locally using the `--skip-publish` flag.
7.  **Summary Report**: The CLI outputs a report detailing the build and publish results.
8.  **Cleanup**: Temporary files and directories are automatically removed unless `--keep-temp` is specified.

This process is perfect for testing new components, verifying configurations, and debugging before committing changes. 