//go:build lambdacomponents.custom && (lambdacomponents.all || lambdacomponents.connector.all || lambdacomponents.connector.signaltometrics)

package connector

import (
	"github.com/open-telemetry/opentelemetry-collector-contrib/connector/signaltometricsconnector"
	"go.opentelemetry.io/collector/connector"
)

func init() {
	Factories = append(Factories, func(extensionId string) connector.Factory {
		return signaltometricsconnector.NewFactory()
	})
}
