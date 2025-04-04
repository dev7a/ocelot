"""
GitHub Actions output utilities.

This module provides standardized methods for setting GitHub Actions outputs.
"""

import json
import os
import sys
from typing import Any


def set_github_output(
    name: str, value: Any, fail_on_error: bool = True, verbose: bool = False
) -> bool:
    """
    Sets an output variable for GitHub Actions with support for different value types.

    Handles both simple values (strings, numbers, booleans) and complex values (lists, dicts).
    Uses the appropriate GitHub Actions output syntax based on the value type.

    Args:
        name: The name of the output variable
        value: The value to set (can be str, int, bool, float, list, dict, etc.)
        fail_on_error: If True (default), exit with code 1 on error; if False, return False
        verbose: If True, print debug information about the output being set

    Returns:
        bool: True if successful, False otherwise

    Raises:
        SystemExit: With exit code 1 if fail_on_error is True and an error occurs
    """
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        error_msg = "Warning: GITHUB_OUTPUT environment variable not set"
        print(error_msg, file=sys.stderr)
        if fail_on_error:
            sys.exit(1)
        return False

    if verbose:
        print(f"Setting output '{name}'...")

    try:
        with open(github_output, "a") as f:
            # For simple values that don't need multi-line handling
            if isinstance(value, (str, int, bool, float)):
                # If it's a simple string without newlines, use simple key=value
                str_value = str(value)
                if "\n" not in str_value:
                    f.write(f"{name}={str_value}\n")
                else:
                    # For strings with newlines, use delimiter syntax
                    delimiter = f"ghadelimiter_{name}_{os.urandom(8).hex()}"
                    f.write(f"{name}<<{delimiter}\n")
                    f.write(f"{str_value}\n")
                    f.write(f"{delimiter}\n")
            else:
                # For complex values (lists, dicts, etc.), use delimiter syntax with JSON
                delimiter = f"ghadelimiter_{name}_{os.urandom(8).hex()}"
                f.write(f"{name}<<{delimiter}\n")
                f.write(f"{json.dumps(value)}\n")
                f.write(f"{delimiter}\n")

        return True

    except Exception as e:
        error_msg = f"Error writing to GITHUB_OUTPUT file {github_output}: {e}"
        print(error_msg, file=sys.stderr)
        if fail_on_error:
            sys.exit(1)
        return False
