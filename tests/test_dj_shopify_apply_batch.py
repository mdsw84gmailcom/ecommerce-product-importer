from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "dj_shopify_apply_batch.py"
SPEC = spec_from_file_location("dj_shopify_apply_batch", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None

MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

APPLY_CONFIRMATION = MODULE.APPLY_CONFIRMATION
MAX_APPLY_BATCH = MODULE.MAX_APPLY_BATCH
validate_apply_args = MODULE.validate_apply_args


def test_dry_run_allows_default_limit_without_confirmation() -> None:
    validate_apply_args(limit=5, apply=False, confirm="")


def test_apply_requires_exact_confirmation() -> None:
    with pytest.raises(ValueError, match="--confirm"):
        validate_apply_args(limit=5, apply=True, confirm="")

    validate_apply_args(
        limit=5,
        apply=True,
        confirm=APPLY_CONFIRMATION,
    )


def test_apply_batch_cannot_exceed_safety_limit() -> None:
    with pytest.raises(ValueError, match="limited"):
        validate_apply_args(
            limit=MAX_APPLY_BATCH + 1,
            apply=True,
            confirm=APPLY_CONFIRMATION,
        )


def test_limit_must_be_positive() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        validate_apply_args(limit=0, apply=False, confirm="")
