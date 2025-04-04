#!/usr/bin/env python3
"""
prepare_matrices.py

Generates build and release job matrices for GitHub Actions based on input parameters.
Sets outputs using GitHub Actions output format.

Usage:
  python prepare_matrices.py --architecture <arch> --aws-region <region>

Where:
  <arch> can be: all, amd64, or arm64
  <region> can be: all or a specific AWS region
"""

import json
import click
from otel_layer_utils.github_utils import set_github_output


@click.command()
@click.option(
    "--architecture",
    required=True,
    type=click.Choice(["all", "amd64", "arm64"]),
    help="Architecture(s) to build for",
)
@click.option(
    "--aws-region",
    required=True,
    help='AWS region(s) to publish to ("all" for all regions)',
)
def main(architecture, aws_region):
    """Generate build and release job matrices for GitHub Actions."""

    # Determine architectures
    if architecture == "all":
        architectures = ["amd64", "arm64"]
    else:
        architectures = [architecture]

    # Build matrix is just architectures
    build_matrix = {"architecture": architectures}

    # Determine regions
    if aws_region == "all":
        regions = [
            "ca-central-1",
            "ca-west-1",
            "eu-central-1",
            "eu-central-2",
            "eu-north-1",
            "eu-south-1",
            "eu-south-2",
            "eu-west-1",
            "eu-west-2",
            "eu-west-3",
            "us-east-1",
            "us-east-2",
            "us-west-2",
        ]
    else:
        regions = [aws_region]

    # Create release matrix
    release_matrix = {"architecture": architectures, "aws_region": regions}

    # Print the matrices for debug
    click.echo(f"Build matrix: {json.dumps(build_matrix)}")
    click.echo(f"Release matrix: {json.dumps(release_matrix)}")

    # Set outputs
    set_github_output("build_jobs", build_matrix)
    set_github_output("release_jobs", release_matrix)

    click.echo("Matrix preparation complete")


if __name__ == "__main__":
    main()
