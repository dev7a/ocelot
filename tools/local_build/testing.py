"""Testing utilities for local build process."""

import os
import functools
from typing import Optional, Any, Callable

from .exceptions import TerminateApp


def inject_error(step_index: Optional[int] = None, step_message: Optional[str] = None):
    """
    Decorator that injects a controlled failure based on environment variable.

    Args:
        step_index: The step tracker index to associate with the error
        step_message: The message to display in the tracker

    The actual error injection is controlled by setting an environment variable:
    LOCAL_BUILD_INJECT_ERROR=function_name

    Example:
        To test a failure in clone_repository:
        $ LOCAL_BUILD_INJECT_ERROR=clone_repository uv run tools/ocelot.py
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the function name
            func_name = func.__name__

            # Check if error injection is enabled for this function
            error_target = os.environ.get("LOCAL_BUILD_INJECT_ERROR")
            if error_target and error_target == func_name:
                # Generate clear error message that indicates this is a simulated error
                error_msg = f"SIMULATED ERROR: Injected test failure in '{func_name}'"

                # Log information about the simulated error
                from scripts.otel_layer_utils.ui_utils import warning

                warning(f"Injecting simulated error in '{func_name}' function")

                # Raise the error with the appropriate step information
                raise TerminateApp(
                    error_msg,
                    step_index=step_index,
                    step_message=f"Simulated failure in {func_name}",
                )

            # Normal execution if not injecting error
            return func(*args, **kwargs)

        return wrapper

    return decorator
