import sys
import tempfile
from pathlib import Path

# Add main tools directory to path for local_build modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Add scripts directory to path so otel_layer_utils is importable as a top-level package
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir.resolve()))

import pytest  # noqa: E402

from local_build.context import BuildContext  # noqa: E402


@pytest.fixture
def temp_test_dir():
    """Provide a temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_build_context(temp_test_dir):
    """Create a BuildContext with fake but valid settings."""
    ctx = BuildContext(
        distribution="test-dist",
        architecture="x86_64",
        upstream_repo="opentelemetry/mock-repo",
        upstream_ref="main",
        layer_name="test-layer",
        runtimes="python3.9",
        skip_publish=True,
        verbose=True,
        public=False,
        keep_temp=False,
    )
    build_dir = temp_test_dir / "build"
    build_dir.mkdir()
    ctx.build_dir = build_dir
    ctx.scripts_dir = Path(__file__).parent.parent / "scripts"
    return ctx


@pytest.fixture
def mock_tracker():
    from unittest.mock import MagicMock

    tracker = MagicMock()
    tracker.start_step = MagicMock()
    tracker.complete_step = MagicMock()
    return tracker


@pytest.fixture
def mock_upstream_repo(temp_test_dir):
    repo_dir = temp_test_dir / "upstream"
    repo_dir.mkdir()
    collector_dir = repo_dir / "collector"
    collector_dir.mkdir()
    (collector_dir / "Makefile").write_text("# Mock Makefile\n")
    (collector_dir / "VERSION").write_text("v0.42.0\n")
    return repo_dir


@pytest.fixture
def mock_layer_zip(temp_test_dir):
    build_dir = temp_test_dir / "build"
    build_dir.mkdir(exist_ok=True)
    zip_file = build_dir / "collector-x86_64-test-dist.zip"
    zip_file.write_text("Mock ZIP content")
    return zip_file
