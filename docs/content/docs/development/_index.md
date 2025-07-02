---
title: Development & Testing
weight: 50
---

The project includes a comprehensive test suite covering various components, utilities, and integration scenarios. Tests use `pytest` and are designed to run in isolation without requiring AWS credentials.

## Setting Up the Test Environment

1.  **Create and activate a virtual environment**:
    ```bash
    uv venv
    source .venv/bin/activate # For Linux/macOS
    # .\.venv\Scripts\activate # For Windows
    ```

2.  **Install test dependencies**:
    This command installs all the necessary packages for running the build tools and the test suite.
    ```bash
    uv pip install -r tools/tests/requirements.txt
    ```

## Running the Tests

Once your environment is set up, you can run the test suite using `pytest`.

#### Run all tests
```bash
python -m pytest tools/tests
```

#### Run tests with coverage
To see a report of how much of the codebase is covered by tests:
```bash
python -m pytest tools/tests --cov=tools --cov-report=term-missing
```

#### Run specific test files
You can run tests for a single file to speed up the development cycle.
```bash
python -m pytest tools/tests/test_distribution_utils.py
```

#### Run tests with verbose output
For more detailed output from the test runner:
```bash
python -m pytest tools/tests -v
```

## Test Import Strategy

The test suite needs to be able to import modules from the `tools/` and `tools/scripts/` directories. This is handled gracefully using a path-manipulation approach in `tools/tests/conftest.py`.

```python
# From tools/tests/conftest.py
import sys
from pathlib import Path

# Add main tools directory to path for local_build modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Add scripts directory to path so otel_layer_utils is importable as a top-level package
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir.resolve()))
```
This strategy ensures that imports work cleanly in the test environment without requiring complex changes to the production code. 