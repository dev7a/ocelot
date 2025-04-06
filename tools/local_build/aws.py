"""AWS utilities for the local build process."""


from scripts.otel_layer_utils.ui_utils import success, warning, error, detail, subheader, info
from .context import BuildContext
from typing import Optional, Tuple
from .exceptions import TerminateApp


def check_aws_credentials() -> bool:
    """
    Check if AWS credentials are configured correctly.

    Returns:
        bool: True if credentials are properly configured, False otherwise
    """
    try:
        # Import boto3 (should be available as it's in the script requirements)
        import boto3

        # Create a boto3 STS client
        sts_client = boto3.client("sts")

        # Call get_caller_identity directly using boto3
        response = sts_client.get_caller_identity()

        # Extract account ID from response
        account_id = response.get("Account")
        if account_id:
            success("AWS credentials are configured", f"Account: {account_id}")
            return True
        else:
            warning(
                "AWS credentials are configured but account ID couldn't be determined."
            )
            return False

    except ImportError:
        error("boto3 is not installed", "Please install it: pip install boto3")
        return False
    except Exception as e:
        error("AWS credentials are not configured correctly", str(e))
        return False


def get_aws_region() -> str:
    """
    Get the current AWS region from boto3 session.

    Returns:
        str: The detected AWS region

    Raises:
        TerminateApp: If AWS region cannot be determined
    """
    try:
        import boto3

        # Get the region from the default session
        session = boto3.session.Session()
        region = session.region_name

        if region:
            return region
        else:
            # Don't fallback, require configuration
            error("Could not determine AWS region from boto3 session.")
            detail(
                "Hint", "Configure region via AWS_REGION env var or 'aws configure'."
            )
            raise TerminateApp(
                "Could not determine AWS region",
                step_index=4,
                step_message="AWS region not configured",
            )
    except Exception as e:
        error("Error getting AWS region", str(e))
        raise TerminateApp(
            f"Failed to get AWS region: {str(e)}",
            step_index=4,
            step_message="AWS region error",
        )


# Import locally to avoid circular imports
from .testing import inject_error


@inject_error(step_index=4)
def verify_credentials(context: BuildContext, tracker) -> BuildContext:
    """
    Verify AWS credentials and region before publishing.

    Args:
        context: The build context
        tracker: Step tracker for progress reporting

    Returns:
        BuildContext: Updated build context with AWS region

    Raises:
        TerminateApp: If credentials or region check fails
    """
    if context.verbose:
        info("Function call", "verify_credentials started")
    
    # Sub-step: Check AWS Credentials
    subheader("Checking AWS credentials")
    if not check_aws_credentials():
        error("AWS credentials check failed", "Skipping publish step")
        detail("Hint", "Run 'aws configure' or set AWS environment variables")
        raise TerminateApp(
            "AWS credentials check failed",
            step_index=4,
            step_message="AWS credentials check failed",
        )

    # Sub-step: Get AWS Region
    subheader("Determining AWS region")
    region = get_aws_region()
    success("Target AWS Region", region)

    # Update the context with the AWS region
    if context.verbose:
        info("Region values before update", f"aws_region={context.aws_region}, dynamodb_region={context.dynamodb_region}")
    context.set_aws_region(region)
    context.set_dynamodb_region(region)
    if context.verbose:
        info("Region values after update", f"aws_region={context.aws_region}, dynamodb_region={context.dynamodb_region}")

    return context
