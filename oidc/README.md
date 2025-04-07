## Setting Up Your Fork for Automated Publishing

To enable GitHub Actions in your fork to publish layers to your own AWS account, you need to configure AWS resources and GitHub secrets.

**1. Deploy AWS Resources:**

Set up an IAM Role assumable by GitHub Actions via OIDC and a DynamoDB table for layer metadata using the [CloudFormation template](./template.yaml).

*   Save this template (e.g., `ocelot-gha-setup.yaml`).
*   Deploy it via the AWS Console or CLI:
    ```bash
    aws cloudformation deploy \
      --template-file ocelot-gha-setup.yaml \
      --stack-name ocelot-github-setup \
      --parameter-overrides GitHubOrg=YOUR_GITHUB_USERNAME GitHubRepo=YOUR_FORK_NAME \
      --capabilities CAPABILITY_NAMED_IAM
    ```
    Replace the placeholder values for `GitHubOrg` and `GitHubRepo`.
*   Record the `CustomCollectorExtensionLayersRoleArn` output value.

**2. Configure GitHub Secrets:**

*   In your fork on GitHub, navigate to `Settings` > `Secrets and variables` > `Actions`.
*   Click `New repository secret`.
*   Name it `OTEL_LAMBDA_LAYER_PUBLISH_ROLE_ARN`.
*   Paste the ARN recorded from the CloudFormation output as the value.

**3. Configure GitHub Variables:**

*   In your fork on GitHub, navigate to `Settings` > `Secrets and variables` > `Actions`.
*   Select `Variables`.
*   Click `New repository variable`.
*   Name it `DYNAMODB_REGION`.
*   Set it to the region of the DynamoDB table you created in step 1.

**4. Verify GitHub Actions Workflow:**

*   Check the `.github/workflows/publish-custom-layer-collector.yml` file in your fork.
*   Confirm that the AWS authentication step uses the `OTEL_LAMBDA_LAYER_PUBLISH_ROLE_ARN` secret, typically via the `aws-actions/configure-aws-credentials` action:
    ```yaml
    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v4 # Or appropriate version
      with:
        role-to-assume: ${{ secrets.OTEL_LAMBDA_LAYER_PUBLISH_ROLE_ARN }}
        aws-region: ${{ env.AWS_REGION }} # Ensure AWS_REGION is set
    ```
*   Commit any necessary adjustments to the workflow file in your fork.

With this setup, running the "Publish Custom Collector Lambda layer" workflow in your fork will securely authenticate to your AWS account and manage layers and metadata accordingly.

