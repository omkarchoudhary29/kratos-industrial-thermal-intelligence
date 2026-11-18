"""backend/services/artifact_resolver.py
---------------------------------------
KRATOS V3.1 — Unified Production Artifact Path Resolver.

Provides robust, fail-fast path resolution for immutable presentation artifacts
and machine learning models across local development, Docker containers, and
Railway deployments with mounted persistent volumes.

Resolution Priority:
  1. KRATOS_ARTIFACTS_DIR environment variable override
  2. Project / container runtime_artifacts directory (preserves artifacts when /app/data volume is mounted)
  3. Container root /app/runtime_artifacts (if running in Docker)
  4. Local project data/processed or models directories
  5. Container root /app/models

Raises FileNotFoundError immediately if a required artifact cannot be found.
Never silently returns an empty dataframe or dummy object.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("artifact_resolver")

PROJECT_DIR = Path(__file__).resolve().parents[2]

# Standard artifact identifiers
EVENTS_PARQUET_NAME = "final_fused_events.parquet"
SOURCES_PARQUET_NAME = "thermal_sources.parquet"
FACILITY_SUMMARY_NAME = "facility_association_summary.json"
IFOREST_MODEL_NAME = "industrial_iforest_train_2021_2024.joblib"


def resolve_artifact_path(artifact_name: str, extra_candidates: Optional[List[Path]] = None) -> Path:
    """Resolve the absolute path to a required artifact file with strict fail-fast validation.

    Args:
        artifact_name: File basename (e.g., 'final_fused_events.parquet')
        extra_candidates: Optional additional paths to check before defaults

    Returns:
        Path: Verified existing file path

    Raises:
        FileNotFoundError: If the file is missing from all candidate locations.
    """
    candidates: List[Path] = []

    # 1. Environment variable override
    env_dir = os.getenv("KRATOS_ARTIFACTS_DIR", "").strip()
    if env_dir:
        candidates.append(Path(env_dir) / artifact_name)

    # 2. Extra caller-specified candidates
    if extra_candidates:
        candidates.extend(extra_candidates)

    # 3. Project runtime_artifacts directory (standard container copy location)
    candidates.append(PROJECT_DIR / "runtime_artifacts" / artifact_name)

    # 4. Standard Linux container path
    candidates.append(Path("/app/runtime_artifacts") / artifact_name)

    # 5. Domain-specific fallbacks (data/processed or models/)
    if artifact_name.endswith((".joblib", ".pkl", ".pt", ".onnx")):
        candidates.append(PROJECT_DIR / "models" / artifact_name)
        candidates.append(Path("/app/models") / artifact_name)
    else:
        candidates.append(PROJECT_DIR / "data" / "processed" / artifact_name)
        candidates.append(Path("/app/data/processed") / artifact_name)

    # Check existence
    checked_paths: List[str] = []
    for candidate in candidates:
        candidate_str = str(candidate)
        if candidate_str in checked_paths:
            continue
        checked_paths.append(candidate_str)
        try:
            if candidate.is_file():
                log.debug("Resolved artifact '%s' at: %s", artifact_name, candidate)
                return candidate.resolve()
        except OSError:
            continue

    checked_msg = "\n  - " + "\n  - ".join(checked_paths)
    error_msg = (
        f"CRITICAL: Required presentation artifact '{artifact_name}' could not be resolved.\n"
        f"Checked candidate locations:{checked_msg}\n\n"
        f"If running on Railway with a volume mounted at /app/data, ensure runtime_artifacts are bundled "
        f"in the Docker image or set KRATOS_ARTIFACTS_DIR."
    )
    log.error(error_msg)
    raise FileNotFoundError(error_msg)


def get_events_parquet_path() -> Path:
    """Get verified path to final_fused_events.parquet."""
    return resolve_artifact_path(EVENTS_PARQUET_NAME)


def get_sources_parquet_path() -> Path:
    """Get verified path to thermal_sources.parquet."""
    return resolve_artifact_path(SOURCES_PARQUET_NAME)


def get_facility_summary_path() -> Path:
    """Get verified path to facility_association_summary.json."""
    return resolve_artifact_path(FACILITY_SUMMARY_NAME)


def get_iforest_model_path() -> Path:
    """Get verified path to industrial_iforest_train_2021_2024.joblib."""
    return resolve_artifact_path(IFOREST_MODEL_NAME)


def load_events_df(**kwargs) -> Any:
    """Load the immutable fused events DataFrame."""
    import pandas as pd
    path = get_events_parquet_path()
    return pd.read_parquet(path, **kwargs)


def load_sources_df(**kwargs) -> Any:
    """Load the immutable thermal sources DataFrame."""
    import pandas as pd
    path = get_sources_parquet_path()
    return pd.read_parquet(path, **kwargs)


def load_facility_summary_json() -> Dict[str, Any]:
    """Load the facility association summary dictionary."""
    path = get_facility_summary_path()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_iforest_model() -> Any:
    """Load the serialized Isolation Forest model."""
    import joblib
    path = get_iforest_model_path()
    return joblib.load(path)
