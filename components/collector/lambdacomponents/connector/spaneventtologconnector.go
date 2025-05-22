//go:build lambdacomponents.custom && (lambdacomponents.all || lambdacomponents.connector.all || lambdacomponents.connector.spaneventtolog)

package connector

import (
	"github.com/dev7a/otelcol-con-spaneventtolog/spaneventtologconnector"
	"go.opentelemetry.io/collector/connector"
)

func init() {
	Factories = append(Factories, func(extensionId string) connector.Factory {
		return spaneventtologconnector.NewFactory()
	})
}
