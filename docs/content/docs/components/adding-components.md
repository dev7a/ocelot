---
title: "Adding New Components"
weight: 2
---

The primary purpose of Ocelot is to simplify the addition of custom components to the OpenTelemetry Collector for Lambda. This guide outlines the process.

## The Wrapper Approach

Instead of placing the full source code of a component into this repository, Ocelot uses a "wrapper" approach. You create a simple Go file that acts as a bridge to the actual component's source code, which is fetched as a Go module dependency.

This keeps the Ocelot repository lean and focused only on the integration logic.

## Steps to Add a Component

Let's assume you want to add a new exporter called `myexporter`.

### 1. Create the Component Directory

Create a new directory for your component under the appropriate type in `components/collector/lambdacomponents/`.

```bash
mkdir -p components/collector/lambdacomponents/exporter/myexporter
```

### 2. Create the Wrapper Go File

Inside the new directory, create a Go file (e.g., `myexporter.go`). This file will contain:
1.  A **build tag** that includes the proper conditions for inclusion.
2.  An `init()` function that registers the factory.
3.  An import statement that references the *actual* component package.

Here is the template:

```go
//go:build lambdacomponents.custom && (lambdacomponents.all || lambdacomponents.exporter.all || lambdacomponents.exporter.myexporter)

package exporter

import (
	"github.com/actual-repo/my-exporter-component" // The real component package
	"go.opentelemetry.io/collector/exporter"
)

func init() {
	Factories = append(Factories, func(extensionId string) exporter.Factory {
		return myexporter.NewFactory() // Call the actual component's factory
	})
}
```

> [!TIP]
> The build tag includes multiple conditions to ensure the component is included when building `all` components, all `exporter` components, or specifically `myexporter`.

### 3. Add the Go Dependency

Add the Go module dependency to the `config/component_dependencies.yaml` file. This maps your build tag to the required Go module:

```yaml
dependencies:
  # ... existing dependencies
  lambdacomponents.exporter.myexporter:
    - github.com/actual-repo/my-exporter-component
    # Or with a specific version:
    # - github.com/actual-repo/my-exporter-component@v1.2.3
```

The build script will automatically run `go get` and `go tidy` for these dependencies when your component is included in a build.

### 4. Define a Distribution

Add your new component's build tag to a distribution in `config/distributions.yaml`. You can add it to an existing distribution or create a new one.

```yaml
distributions:
  # ...
  minimal-my-exporter:
    description: "Minimal + My Exporter"
    base: minimal
    build-tags:
      - "lambdacomponents.exporter.myexporter"
```

### 5. Build and Test

You can now build a layer with your new component!

```bash
uv run tools/ocelot.py --distribution minimal-my-exporter
``` 