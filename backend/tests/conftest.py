"""Shared test configuration. Environment defaults match deploy/compose defaults."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_SARIF = REPO_ROOT / "deploy" / "sample-data" / "semgrep-example.sarif"

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
