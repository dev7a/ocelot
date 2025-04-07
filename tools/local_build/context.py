from pathlib import Path
from typing import Dict, Optional


class BuildContext:
    """
    Central context object to manage build state between modules.
    This replaces passing many individual variables between functions.
    """

    def __init__(
        self,
        distribution: str,
        architecture: str,
        upstream_repo: str,
        upstream_ref: str,
        layer_name: str,
        runtimes: str,
        skip_publish: bool,
        verbose: bool,
        public: bool,
        keep_temp: bool,
    ):
        # CLI parameters
        self.distribution = distribution
        self.architecture = architecture
        self.upstream_repo = upstream_repo
        self.upstream_ref = upstream_ref
        self.layer_name = layer_name
        self.runtimes = runtimes
        self.skip_publish = skip_publish
        self.verbose = verbose
        self.public = public
        self.keep_temp = keep_temp

        # Paths
        self.repo_root = Path().cwd()
        self.build_dir = self.repo_root / "build"
        self.scripts_dir = self.repo_root / "tools" / "scripts"

        # Runtime state
        self.temp_upstream_dir: Optional[str] = None
        self.upstream_version: Optional[str] = None
        self.build_tags_string: Optional[str] = None
        self.distributions_data: Dict = {}
        self.layer_file: Optional[Path] = None
        self.layer_file_size: Optional[int] = None
        self.layer_arn: Optional[str] = None
        self.aws_region: Optional[str] = None
        self.dynamodb_region: Optional[str] = None
        self.start_time = None

    def set_temp_dir(self, temp_dir: str) -> None:
        """Set the temporary directory for the upstream clone."""
        self.temp_upstream_dir = temp_dir

    def set_upstream_version(self, version: str) -> None:
        """Set the upstream version."""
        self.upstream_version = version

    def set_build_tags(self, tags: str) -> None:
        """Set the build tags string."""
        self.build_tags_string = tags

    def set_distributions_data(self, data: Dict) -> None:
        """Set the distributions data."""
        self.distributions_data = data

    def set_layer_file(self, file_path: Path, size: int) -> None:
        """Set the built layer file and its size."""
        self.layer_file = file_path
        self.layer_file_size = size

    def set_layer_arn(self, arn: str) -> None:
        """Set the published layer ARN."""
        self.layer_arn = arn

    def set_aws_region(self, region: str) -> None:
        """Set the AWS region."""
        self.aws_region = region

    def set_dynamodb_region(self, region: str) -> None:
        """Set the DynamoDB region."""
        from scripts.otel_layer_utils.ui_utils import detail
        if self.verbose:
            detail("Setting DynamoDB region", f"region={region}")
        self.dynamodb_region = region
