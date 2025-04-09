# Secrets Manager Authenticator Extension

## Background

The OpenTelemetry Collector supports various authentication mechanisms for exporters through the authenticator extension system. This document proposes a new authenticator extension for OCELOT that leverages AWS Secrets Manager to store and retrieve complete HTTP header configurations including both header names and values.

## Problem Statement

Different observability vendors require different HTTP headers for authentication:

| Vendor | Authentication Header | Example |
|--------|----------------------|---------|
| New Relic | `Api-Key` | `Api-Key: YOUR_LICENSE_KEY` |
| Datadog | `DD-API-KEY` | `DD-API-KEY: abcdef123456` |
| Honeycomb | `X-Honeycomb-Team` | `X-Honeycomb-Team: your_api_key` |
| Dynatrace | `Authorization` | `Authorization: Api-Token dt0c01.sample.token` |
| Elastic | `Authorization` | `Authorization: ApiKey base64encodedkey` |
| Splunk | `X-Splunk-Token` | `X-Splunk-Token: your-token-here` |

Currently, OCELOT supports AWS Secrets Manager integration to securely store header values, but header names must be hardcoded in the YAML configuration:

```yaml
exporters:
  otlphttp:
    endpoint: "https://api.example.com"
    headers:
      Authorization: "${secretsmanager:otel/auth#api-key}"
      X-Tenant-ID: "${secretsmanager:otel/auth#tenant-id}"
```

This approach has limitations:

1. **Vendor Lock-in**: The configuration is tied to specific header names, requiring different configurations for different vendors
2. **Limited Flexibility**: Users can't easily switch between vendors without modifying configuration files
3. **Maintenance Overhead**: Any change to authentication headers requires deploying new configuration files

## Proposed Solution

We propose developing a custom `secretsmanagerauth` extension that implements the `configauth.ClientAuthenticator` interface. This extension will:

1. Retrieve a complete JSON object from AWS Secrets Manager
2. Parse all key-value pairs as HTTP headers
3. Apply these headers to outgoing HTTP requests

### Example Configuration

```yaml
extensions:
  secretsmanagerauth:
    secret_name: "otel/vendor/auth-headers"
    region: "us-east-1"
    # Optional fallback if secret retrieval fails
    fallback_headers:
      User-Agent: "OTel-Collector/1.0"

exporters:
  otlphttp:
    endpoint: "https://api.example.com"
    auth:
      authenticator: secretsmanagerauth

service:
  extensions: [secretsmanagerauth]
  # rest of service configuration
```

With this configuration, the extension would fetch the secret named `otel/vendor/auth-headers` from AWS Secrets Manager in the `us-east-1` region. The secret should contain a JSON object like:

```json
{
  "X-API-Key": "abcdef12345",
  "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "X-Tenant-ID": "customer-xyz-123"
}
```

The authenticator would apply all these headers to outgoing requests from the OTLP HTTP exporter.

## Benefits

1. **Increased Flexibility**: Users can seamlessly switch between observability backends by just updating the secret in AWS Secrets Manager
2. **Enhanced Security**: Authentication details remain fully managed in AWS Secrets Manager with features like automatic rotation
3. **Simplified Configuration**: No need for vendor-specific configuration templates or hardcoded header names
4. **Reduced Maintenance**: Updates to authentication headers can be made without redeploying collector configurations
5. **Best Practices**: Properly leverages OpenTelemetry's extension system for authentication concerns

## Implementation Details

The implementation will:

1. Create a new Go package under `components/collector/extension/secretsmanagerauth`
2. Implement the `configauth.ClientAuthenticator` interface
3. Use the AWS SDK for Go to interact with Secrets Manager
4. Parse the retrieved JSON into a map of header names and values
5. Apply these headers to outgoing requests

### Required Permissions

The AWS IAM role used by the Lambda function must have the `secretsmanager:GetSecretValue` permission for the specified secrets.

## Compatibility

This authenticator extension is particularly well-suited for:

- Services that use static API keys or tokens for authentication
- Multi-tenant deployments where credentials vary by customer
- Scenarios where authentication details may change without redeploying the collector

## Example: Creating a Secret with AWS CLI

```bash
# Create a secret for New Relic authentication
aws secretsmanager create-secret \
  --name otel/newrelic/auth-headers \
  --secret-string '{"Api-Key":"YOUR_LICENSE_KEY"}'

# Create a secret for Datadog authentication
aws secretsmanager create-secret \
  --name otel/datadog/auth-headers \
  --secret-string '{"DD-API-KEY":"YOUR_API_KEY"}'
```

## Future Considerations

1. Supporting secret rotation hooks
2. Adding support for extracting headers from more complex JSON structures
3. Implementing caching to reduce API calls to Secrets Manager
4. Adding support for alternate secret backends (HashiCorp Vault, GCP Secret Manager, etc.)

## Conclusion

The proposed Secrets Manager authenticator extension enhances OCELOT's flexibility when integrating with various observability platforms. It provides a clean, secure way to manage authentication headers while following OpenTelemetry best practices. 