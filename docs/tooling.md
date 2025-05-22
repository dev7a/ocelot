# Ocelot Build Tooling

These tools are used for both local development builds and the automated CI/CD workflows in GitHub Actions, orchestrating every step from interacting with upstream repositories to publishing your tailored Lambda layers. This guide is your key to understanding the operational mechanics of Ocelot. For definitions of common terms, please refer to the [Ocelot Glossary](./glossary.md).

For a higher-level understanding of how these tools fit into the project's structure, the [Architecture](./architecture.md) document provides essential context on the build flow.

## Table of Contents

- [Overview](#overview)
- [Key Scripts and Modules](#key-scripts-and-modules)
  - [1. `tools/ocelot.py`](#1-toolsocelotpy)
  - [2. `tools/local_build/` (Module)](#2-toolslocal_build-module)
  - [3. `tools/scripts/build_extension_layer.py`](#3-toolsscriptsbuild_extension_layerpy)
  - [4. `tools/scripts/lambda_layer_publisher.py`](#4-toolsscriptslambda_layer_publisherpy)
  - [5. `tools/scripts/otel_layer_utils/` (Module)](#5-toolsscriptsotel_layer_utils-module)
  - [6. Other Scripts (`tools/`, `tools/scripts/`)](#6-other-scripts-toolstoolsscripts)
- [Dependencies (`tools/requirements.txt`)](#dependencies-toolsrequirementstxt)
- [GitHub Actions Workflows (`.github/workflows/`)](#github-actions-workflows-githubworkflows)
  - [1. `publish-custom-layer-collector.yml`](#1-publish-custom-layer-collectoryml)
  - [2. `r_publish.yml` (Reusable Workflow)](#2-r_publishyml-reusable-workflow)

## Overview

The tooling provides a command-line interface (`ocelot.py`) to orchestrate the build process locally, mimicking the steps performed in Github Actions CI/CD workflow. It handles cloning the upstream repository, managing configurations, overlaying components, handling dependencies, invoking the build, and optionally publishing the resulting AWS Lambda layer.

## Key Scripts and Modules

### 1. `tools/ocelot.py`

-   **Purpose:** Main entry point for local builds. Provides a CLI using the `click` library.
-   **Functionality:**
    -   Parses command-line arguments (distribution, architecture, upstream repo/ref, output options, etc.).
    -   Creates a `BuildContext` object to store configuration and state throughout the process.
    -   Orchestrates the build steps by calling functions from `local_build` modules in sequence:
        1.  `load_distributions` (`config.py`) (See [Configurations](./configurations.md))
        2.  `clone_repository` (`upstream.py`) - Clones repo, calls `determine_upstream_version`. (See [Upstream Integration](./upstream.md))
        3.  `determine_build_tags` (`config.py`) - Uses `distribution_utils.py`. (See [Configurations](./configurations.md))
        4.  `build_layer` (`build.py`) - Calls `scripts/build_extension_layer.py`.
        5.  `verify_credentials` (`aws.py`) (Optional)
        6.  `publish_layer` (`publish.py`) (Optional) - Calls `scripts/lambda_layer_publisher.py`.
    -   Handles overall error management and reporting (`report.py`).
    -   Manages cleanup of temporary directories (`upstream.py`).
    -   Uses UI utilities (`scripts/otel_layer_utils/ui_utils.py`) for user feedback (spinners, status messages).

### 2. `tools/local_build/` (Module)

This module contains the core logic for the local build orchestration managed by [`ocelot.py`](#1-toolsocelotpy).

-   **`config.py`:** Handles loading [`distributions.yaml`](./configurations.md#1-configdistributionsyaml), resolving build tags for a distribution (using `distribution_utils`), and managing build context related to configuration. (See [Configurations](./configurations.md))
-   **`upstream.py`:** Manages cloning the upstream Git repository into a temporary directory, determining the upstream version via `make set-otelcol-version`, and cleaning up the temporary directory. (See [Upstream Integration](./upstream.md))
-   **`build.py`:** Prepares arguments and executes the main build script ([`scripts/build_extension_layer.py`](#3-toolsscriptsbuild_extension_layerpy)). Verifies the output layer file exists.
-   **`publish.py`:** Prepares arguments and executes the layer publishing script ([`scripts/lambda_layer_publisher.py`](#4-toolsscriptslambda_layer_publisherpy)).
-   **`aws.py`:** Contains helpers for AWS interactions, like verifying credentials (`boto3`).
-   **`context.py`:** Defines the `BuildContext` class used to pass state between build steps.
-   **`exceptions.py`:** Defines custom exceptions like `TerminateApp`.
-   **`report.py`:** Generates a summary report at the end of the build.
-   **`testing.py`:** Includes decorators (`@inject_error`) for simulating errors during testing.

### 3. `tools/scripts/build_extension_layer.py`

-   **Purpose:** Performs the core build steps within a temporary, isolated environment. Called by [`local_build/build.py`](#2-toolslocal_build-module) or directly by CI/CD workflows.
-   **Functionality:**
    -   Takes build parameters (upstream info, distribution, arch, version, tags, output dir) as command-line arguments.
    -   Clones the upstream repository into a *new* temporary directory. (See [Upstream Integration](./upstream.md))
    -   Loads [`component_dependencies.yaml`](./configurations.md#2-configcomponent_dependenciesyaml). (See [Configurations](./configurations.md))
    -   Selectively copies required Ocelot component wrappers ([`components/collector/lambdacomponents/`](./components.md)) into the cloned upstream repo's `lambdacomponents/` directory based on build tags. (See [Components](./components.md))
    -   Adds required Go dependencies to the cloned repo's `go.mod` using `go mod edit` and `go mod tidy`.
    -   Executes `make package` within the cloned repo's `collector` directory, passing `GOARCH` and `BUILDTAGS` environment variables. This compiles the collector.
    -   Renames the output zip file (`opentelemetry-collector-layer-*.zip`) to include the distribution name (`collector-<arch>-<distribution>.zip`).
    -   Copies the final zip file to the specified output directory.
    -   Cleans up its temporary directory.

### 4. `tools/scripts/lambda_layer_publisher.py`

-   **Purpose:** Publishes a pre-built Lambda layer zip file to AWS. Called by [`local_build/publish.py`](#2-toolslocal_build-module) or directly by CI/CD workflows.
-   **Functionality:** (Inferred - code not analyzed in detail)
    -   Likely takes layer file path, layer name, compatible runtimes, architecture, region(s), and public/private flag as input.
    -   Uses `boto3` to interact with the AWS Lambda API (`publish_layer_version`).
    -   May handle publishing to multiple regions.
    -   May update metadata (e.g., in DynamoDB via [`dynamodb_utils.py`](#5-toolsscriptsotel_layer_utils-module)) about published layers. (See [OIDC Setup](./oidc.md#dynamodb-table-publishedcustomcollectorcollectionlayers))

### 5. `tools/scripts/otel_layer_utils/` (Module)

This module provides shared utility functions used by various scripts.

-   **`distribution_utils.py`:** Loads [`distributions.yaml`](./configurations.md#1-configdistributionsyaml) and resolves build tags, handling inheritance and cycle detection. (See [Configurations](./configurations.md))
-   **`ui_utils.py`:** Provides functions for formatted console output (headers, status, spinners, progress tracking).
-   **`subprocess_utils.py`:** Wrapper for running external commands (`subprocess.run`) with improved error handling and optional output capturing/streaming.
-   **`github_utils.py`:** (Inferred) Helpers for interacting with the GitHub API (e.g., for release notes generation). Uses `requests`.
-   **`dynamodb_utils.py`:** (Inferred) Helpers for interacting with AWS DynamoDB (likely for storing/querying layer metadata). Uses `boto3`. (See [OIDC Setup](./oidc.md#dynamodb-table-publishedcustomcollectorcollectionlayers))
-   **`regions_utils.py`:** (Inferred) Helpers for working with AWS regions. Uses `boto3`.

### 6. Other Scripts (`tools/`, `tools/scripts/`)

-   **`delete-layers.py`:** Utility to remove Lambda layers from AWS.
-   **`generate_layers_report.py`:** Creates reports about published layers (likely uses [`dynamodb_utils.py`](#5-toolsscriptsotel_layer_utils-module)). (See [OIDC Setup](./oidc.md#dynamodb-table-publishedcustomcollectorcollectionlayers))
-   **`generate_release_notes.py`:** Automates release note creation (likely uses [`github_utils.py`](#5-toolsscriptsotel_layer_utils-module)).
-   **`get_release_info.py`:** Retrieves information about releases/distributions (uses [`distribution_utils.py`](#5-toolsscriptsotel_layer_utils-module)).
-   **`prepare_matrices.py`:** Generates matrix configurations for CI/CD pipelines (e.g., GitHub Actions).

## Dependencies ([`tools/requirements.txt`](../tools/requirements.txt))

-   `boto3`/`botocore`: AWS SDK.
-   `pyyaml`: YAML parsing.
-   `click`: CLI framework.
-   `yaspin`: Console spinner.
-   `requests`: HTTP requests (for GitHub API, etc.).

## GitHub Actions Workflows (`.github/workflows/`)

The project utilizes GitHub Actions for CI/CD, particularly for building and publishing the custom Lambda layers.

### 1. `publish-custom-layer-collector.yml`

-   **Purpose:** The main workflow for building, publishing, and creating GitHub releases for custom Ocelot layers.
-   **Trigger:** Manual (`workflow_dispatch`) with inputs to customize the build (architecture, region, distribution, upstream source, dry-run, etc.).
-   **Permissions:** Requires `id-token: write` (for AWS OIDC) and `contents: write` (for creating releases). (See [OIDC Setup](./oidc.md))
-   **Key Jobs:**
    -   **`prepare-environment`:** Checks out code, determines upstream version (`make set-otelcol-version`), resolves release info and build tags ([`get_release_info.py`](#6-other-scripts-toolstoolsscripts)), and prepares build/release matrices ([`prepare_matrices.py`](#6-other-scripts-toolstoolsscripts)).
    -   **`build-layer`:** Matrix job (per architecture). Checks out full repo, sets up Go/Python, runs [`scripts/build_extension_layer.py`](#3-toolsscriptsbuild_extension_layerpy) to build the layer, uploads the `.zip` artifact.
    -   **`release-layer`:** Matrix job (per architecture/region). Calls the reusable [`r_publish.yml`](#2-r_publishyml-reusable-workflow) workflow to publish the layer artifact to AWS. Skipped if `dry-run` is true. Inherits secrets for AWS authentication.
    -   **`generate-layers-report`:** Runs after release. Authenticates to AWS (OIDC), runs [`scripts/generate_layers_report.py`](#6-other-scripts-toolstoolsscripts) (likely queries DynamoDB), uploads Markdown reports. Skipped if `dry-run` is true.
    -   **`create-github-release`:** Runs after reports. Authenticates to AWS (OIDC), generates release notes ([`scripts/generate_release_notes.py`](#6-other-scripts-toolstoolsscripts)), downloads layer artifacts, uses `gh` CLI to create a GitHub release with notes and assets. Skipped if `dry-run` is true.

### 2. `r_publish.yml` (Reusable Workflow)

-   **Purpose:** Encapsulates the logic for publishing a single, pre-built Lambda layer artifact to a specific AWS region.
-   **Trigger:** Called by other workflows (`on: workflow_call`), specifically by the `release-layer` job in `publish-custom-layer-collector.yml`.
-   **Inputs:** Receives artifact name, layer details, AWS region, DynamoDB region, version info, metadata tags, and control flags.
-   **Permissions:** Requires `id-token: write` (for AWS OIDC). (See [OIDC Setup](./oidc.md))
-   **Process:**
    -   Checks out only necessary scripts (`tools/scripts/`, [`tools/requirements.txt`](#dependencies-toolsrequirementstxt)).
    -   Downloads the specified layer artifact.
    -   Authenticates to AWS using OIDC via inherited secrets (`OTEL_LAMBDA_LAYER_PUBLISH_ROLE_ARN`).
    -   Executes [`scripts/lambda_layer_publisher.py`](#4-toolsscriptslambda_layer_publisherpy), passing inputs as command-line arguments to perform the actual publishing and metadata update.
    -   Outputs the published layer ARN.
