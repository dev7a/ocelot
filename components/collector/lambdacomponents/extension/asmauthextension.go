//go:build lambdacomponents.custom && (lambdacomponents.all || lambdacomponents.extension.all || lambdacomponents.extension.asmauthextension)

package extension

import (
	"github.com/dev7a/otelcol-ext-asmauth/asmauthextension"
	"go.opentelemetry.io/collector/extension"
)

func init() {
	Factories = append(Factories, func(extensionId string) extension.Factory {
		return asmauthextension.NewFactory()
	})
}
