"""Exceptions for the local build process."""
from typing import Optional


class TerminateApp(Exception):
    """Exception raised to signal application termination with an error code."""
    def __init__(
        self,
        message: str = "Application terminated",
        exit_code: int = 1,
        step_index: Optional[int] = None,
        step_message: Optional[str] = None,
    ):
        self.message = message
        self.exit_code = exit_code
        self.step_index = step_index
        self.step_message = step_message
        super().__init__(self.message) 