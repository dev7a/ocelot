#!/usr/bin/env python3
"""
subprocess_utils.py - Utilities for working with subprocesses

This module provides utility functions for subprocess execution with enhanced output handling,
error reporting, and GitHub environment variable capture.
"""

import os
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple, Union

from .ui_utils import (
    info,
    status,
    detail,
    success,
    error,
    warning,
    command_output_block,
    display_command,
)


def run_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    check: bool = True,
    capture_output: bool = False,
    capture_github_env: bool = False,
) -> Union[
    subprocess.CompletedProcess, Tuple[subprocess.CompletedProcess, Dict[str, str]]
]:
    """Run a shell command with enhanced output handling and error reporting.

    Args:
        cmd: Command to run as a list of strings
        cwd: Working directory for the command
        env: Environment variables to add
        check: Whether to raise an exception on non-zero exit
        capture_output: Whether to capture stdout/stderr instead of streaming
        capture_github_env: Whether to capture GitHub environment variables

    Returns:
        The completed process object, or a tuple of (process, github_env_vars) if
        capture_github_env is True

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit code and check is True
    """
    command_str = " ".join(cmd)

    # Display the command and directory using the improved formatter
    display_command("Command", command_str)

    if cwd:
        detail("Directory", cwd)

    # Set up environment
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    # Set up GitHub environment files if needed
    github_env_path = None
    github_output_path = None
    if capture_github_env:
        # Create temporary files
        github_env_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        github_env_path = github_env_file.name
        github_env_file.close()

        github_output_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        github_output_path = github_output_file.name
        github_output_file.close()

        # Add to environment
        full_env.update(
            {"GITHUB_ENV": github_env_path, "GITHUB_OUTPUT": github_output_path}
        )

    # Run the command
    process = subprocess.run(
        cmd,
        cwd=cwd,
        env=full_env,
        text=True,
        check=False,  # We'll handle errors ourselves
        capture_output=capture_output,
    )

    # --- BEGIN ADDED DEBUGGING ---
    if capture_output:
        if process.stdout:
            print(f"--- RAW STDOUT ---\n{process.stdout}\n--- END RAW STDOUT ---")
        if process.stderr:
            print(f"--- RAW STDERR ---\n{process.stderr}\n--- END RAW STDERR ---")
    # --- END ADDED DEBUGGING ---

    # Handle the output
    failed = process.returncode != 0

    # If we captured output, display it
    if capture_output:
        # First handle the case where the process failed
        if failed:
            # Show stdout if it exists
            if process.stdout and len(process.stdout.strip()) > 0:
                info("Output", "")
                command_output_block(process.stdout)

            # Show stderr as an error
            if process.stderr and len(process.stderr.strip()) > 0:
                error("Error", "")
                command_output_block(process.stderr, prefix="  | ", max_lines=20)
            elif not process.stderr or len(process.stderr.strip()) == 0:
                error(
                    "Error",
                    f"No error output produced, but command failed with exit code {process.returncode}",
                )

        # Process succeeded - show stdout and stderr as regular output
        else:
            has_output = False

            # Show stdout if it exists
            if process.stdout and len(process.stdout.strip()) > 0:
                info("Output", "")
                command_output_block(process.stdout)
                has_output = True

            # Show stderr as additional output
            if process.stderr and len(process.stderr.strip()) > 0:
                if has_output:
                    info("Additional output (stderr)", "")
                else:
                    info("Output (stderr)", "")
                command_output_block(process.stderr, prefix="  | ", max_lines=20)
                has_output = True

            # Indicate if there was no output at all
            if not has_output:
                info("Output", "No output produced")

    # Show success/failure
    if not failed:
        success("Command completed successfully")
    elif check:
        error("Command failed", f"Exit code {process.returncode}")
        raise subprocess.CalledProcessError(
            process.returncode,
            cmd,
            output=process.stdout if capture_output else None,
            stderr=process.stderr if capture_output else None,
        )
    else:
        warning(
            f"Command returned non-zero exit code {process.returncode}",
            "check=False, continuing",
        )

    # Parse GitHub env variables if requested
    if capture_github_env:
        github_env_vars = {}
        # Read and parse GitHub environment files
        for file_path, file_type in [
            (github_env_path, "GITHUB_ENV"),
            (github_output_path, "GITHUB_OUTPUT"),
        ]:
            try:
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    with open(file_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and "=" in line:
                                key, value = line.split("=", 1)
                                github_env_vars[key] = value
                                if value.strip():  # Only log non-empty values
                                    info("Captured", f"{file_type}: {key}={value}")
            except Exception as e:
                warning(f"Error parsing {file_type} file: {e}")
            finally:
                # Clean up
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    warning(f"Error removing temporary {file_type} file: {e}")

        return process, github_env_vars

    return process
