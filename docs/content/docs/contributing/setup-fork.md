---
title: "Setup your fork"
weight: 10
---

To enable the GitHub Actions workflow in your fork to publish Lambda layers to your own AWS account, you need to configure a trust relationship between GitHub and AWS using OIDC (OpenID Connect). This allows the workflow to securely assume an IAM role in your account without needing long-lived access keys.

The `oidc/` directory in this repository contains detailed instructions and a CloudFormation template to help you set this up.

## High-Level Steps

1.  **Run the CloudFormation Template**: The template in `oidc/cloudformation.yaml` will create the necessary AWS resources:
    -   An **IAM OIDC Provider** for GitHub.
    -   An **IAM Role** that the GitHub Actions workflow can assume. This role has permissions to publish Lambda layers and manage the DynamoDB metadata table.
    -   A **DynamoDB Table** to store metadata about the published layers.

2.  **Configure GitHub Secrets**: After the CloudFormation stack is created, you will need to add its outputs as secrets to your forked GitHub repository. This allows the workflow to know which role to assume and which DynamoDB table to use.
    -   `AWS_ROLE_TO_ASSUME`: The ARN of the IAM role created by the template.
    -   `DYNAMODB_TABLE_NAME`: The name of the DynamoDB table.

## The Role of the DynamoDB Table

The DynamoDB table (`PublishedCustomCollectorExtensionLayers`) serves as a **metadata registry** for all Lambda layers published by your CI/CD workflow. It tracks:

- **Layer identification**: ARN, version, and distribution name
- **Build relationships**: Links between base distributions and derived layers  
- **Discovery and management**: Enables querying layers by distribution or version

### Publishing Workflow Integration

When the GitHub Actions workflow publishes a layer, it:

1. **Builds** the Lambda layer with your custom distribution
2. **Publishes** the layer to AWS Lambda (gets a layer ARN)
3. **Records metadata** in DynamoDB with details like:
   - `layer_arn`: The full ARN of the published layer
   - `distribution`: Which distribution configuration was used
   - `base_layer_arn`: If based on another layer
   - `version`: The layer version number
4. **Enables discovery**: Other processes can query the table to find layers by distribution or track version history

### Table Structure

The table includes Global Secondary Indexes that enable efficient queries:
- **`distribution-index`**: Find all layers for a specific distribution (e.g., "minimal-clickhouse")
- **`base-layer-index`**: Track relationships between base layers and derived versions

This metadata system is also used by the cleanup tool (`reaper.py`) to identify and manage layers across your AWS account.

## Detailed Instructions

For the complete, step-by-step guide, please refer to the README file within the oidc directory:

[**oidc/README.md**](https://github.com/dev7a/ocelot/blob/main/oidc/README.md)

Following this guide will fully equip your fork to act as a private, automated build and publishing system for your custom OpenTelemetry Lambda layers. 