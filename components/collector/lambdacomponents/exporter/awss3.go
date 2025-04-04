//go:build lambdacomponents.custom && (lambdacomponents.all || lambdacomponents.exporter.all || lambdacomponents.exporter.awss3)

package exporter

import (
	"github.com/open-telemetry/opentelemetry-collector-contrib/exporter/awss3exporter"
	"go.opentelemetry.io/collector/exporter"
)

func init() {
	Factories = append(Factories, func(extensionId string) exporter.Factory {
		return awss3exporter.NewFactory()
	})
}
