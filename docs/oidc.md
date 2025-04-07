# OIDC Setup for GitHub Actions

This document explains the OpenID Connect (OIDC) integration used to allow GitHub Actions workflows, particularly those running in user forks, to securely publish Ocelot Lambda layers to an AWS account.

## Purpose

The primary goal of this setup is to enable automated publishing of custom Lambda layers built by GitHub Actions workflows directly to an AWS account without requiring long-lived AWS access keys to be stored as GitHub secrets. Instead, it uses OIDC to establish trust between GitHub Actions and AWS IAM, allowing workflows to assume an IAM role and obtain temporary, short-lived credentials.

This is particularly useful for users who fork the Ocelot repository and want to build and publish layers to their *own* AWS accounts using the provided workflows (e.g., `.github/workflows/publish-custom-layer-collector.yml`).

## Mechanism

The integration relies on the following components:

1.  **GitHub Actions as OIDC Provider:** GitHub Actions can issue OIDC JSON Web Tokens (JWTs) for each workflow run. These tokens contain claims about the workflow execution environment, such as the repository (`repository`), branch (`ref`), and triggering event (`event_name`).
2.  **AWS IAM OIDC Identity Provider:** An IAM resource (`AWS::IAM::OIDCProvider`) is created in the target AWS account to represent GitHub Actions (`token.actions.githubusercontent.com`) as a trusted identity provider. AWS verifies the provider's identity using a thumbprint.
3.  **AWS IAM Role:** An IAM role (`AWS::IAM::Role`) is created with a trust policy that allows the GitHub OIDC provider to assume it (`sts:AssumeRoleWithWebIdentity`). Crucially, the trust policy includes conditions that restrict *which* GitHub Actions runs can assume the role:
    -   `token.actions.githubusercontent.com:aud: 'sts.amazonaws.com'`: Ensures the token was intended for AWS STS.
    -   `token.actions.githubusercontent.com:sub: 'repo:<GitHubOrg>/<GitHubRepo>:*`: Restricts assumption to workflows running within a specific GitHub repository (e.g., the user's fork).
4.  **IAM Policy:** The IAM role is granted specific permissions via an attached policy (`OcelotLayerPublishPolicy`). These permissions allow it to:
    -   Publish and manage Lambda layers (`lambda:*Layer*`) with names matching a specific prefix (e.g., `ocel-*`).
    -   Read from and write to a specific DynamoDB table used for storing layer metadata.
5.  **GitHub Actions Workflow (`aws-actions/configure-aws-credentials`):** The workflow uses this official action, configured with the ARN of the IAM role (stored as a GitHub secret), to automatically handle the OIDC token exchange and configure the workflow environment with temporary AWS credentials.

## Setup Process ([`oidc/README.md`](../oidc/README.md) and [`ocelot-gha-setup.yaml.yaml`](../oidc/ocelot-gha-setup.yaml.yaml))

The setup for a user fork involves:

1.  **Deploying CloudFormation:** The user deploys the [`oidc/ocelot-gha-setup.yaml.yaml`](../oidc/ocelot-gha-setup.yaml.yaml) template to their AWS account. This template creates the IAM OIDC Provider, the IAM Role (scoped to their fork), and the DynamoDB metadata table (`PublishedCustomCollectorExtensionLayers`).
2.  **Configuring GitHub Secrets:** The user stores the ARN of the created IAM Role (output from CloudFormation) as a secret named `OTEL_LAMBDA_LAYER_PUBLISH_ROLE_ARN` in their GitHub fork's settings.
3.  **Configuring GitHub Variables:** The user stores the AWS region where the DynamoDB table was created as a variable named `DYNAMODB_REGION`.
4.  **Workflow Execution:** When the "Publish Custom Collector Lambda layer" workflow runs in the user's fork, the `configure-aws-credentials` action requests an OIDC token from GitHub, presents it to AWS STS along with the Role ARN, receives temporary credentials, and makes them available to subsequent steps (like [`lambda_layer_publisher.py`](./tooling.md#4-toolsscriptslambda_layer_publisherpy)) for interacting with AWS. (See [Tooling](./tooling.md))

## DynamoDB Table (`PublishedCustomCollectorExtensionLayers`)

-   **Purpose:** Stores metadata about published Lambda layers, likely used by scripts like [`generate_layers_report.py`](./tooling.md#6-other-scripts-toolstoolsscripts) and potentially by the publishing script to track existing versions. (See [Tooling](./tooling.md))
-   **Schema:** Uses a composite primary key (`pk`, `sk`) and potentially GSIs for flexible querying (e.g., finding layers by name/arch or by region/version).
-   **Permissions:** The IAM role granted to GitHub Actions has full CRUD permissions on this specific table.
