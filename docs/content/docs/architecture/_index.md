---
title: Architecture
weight: 2
cascade:
  type: docs
---

This section provides a deep dive into the technical architecture of Ocelot, covering the core "overlay" strategy, the build process, and the different development workflows.

## The Overlay Approach

Maintaining a fork of a rapidly evolving upstream project like `open-telemetry/opentelemetry-lambda` can lead to significant maintenance overhead and merge conflicts. **Ocelot** employs an **overlay** strategy to circumvent these issues.

Instead of forking, this repository contains only the custom components and the necessary build configurations. This approach is made possible by the upstream project's use of Go build tags, which allows for selective compilation of components.

### The Build Process

The build process integrates custom components seamlessly with the upstream source code:

1.  **Clone Upstream:** The build script fetches the specified version of the `open-telemetry/opentelemetry-lambda` repository into a temporary directory.
2.  **Apply Overlay:** It copies the custom Go components defined within the Ocelot repository (`components/collector/lambdacomponents/`) into the appropriate directories of the cloned upstream source.
3.  **Build Collector:** It compiles the OpenTelemetry Collector using the upstream project's build system. The build is guided by Go build tags derived from the selected Ocelot distribution, incorporating both standard and custom components.
4.  **Package Layer:** The compiled binary and any necessary configuration files are packaged into a `.zip` archive suitable for deployment as an AWS Lambda Layer.
5.  **Publish (Optional):** The script uploads the layer to specified AWS regions and can record metadata about the release.

This approach allows for seamless integration of custom functionality while staying synchronized with upstream developments, significantly reducing maintenance efforts. 