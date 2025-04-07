//go:build lambdacomponents.custom && (lambdacomponents.all || lambdacomponents.exporter.all || lambdacomponents.exporter.clickhouse)

package exporter

import (
	"github.com/open-telemetry/opentelemetry-collector-contrib/exporter/clickhouseexporter"
	"go.opentelemetry.io/collector/exporter"
)

func init() {
	Factories = append(Factories, func(extensionId string) exporter.Factory {
		return clickhouseexporter.NewFactory()
	})
}
