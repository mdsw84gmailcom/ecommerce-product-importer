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


def test_apply_stops_when_shopify_fails(monkeypatch, capsys):
    """Importen ska stoppa om Shopify misslyckas."""

    def fake_execute(**kwargs):
        raise RuntimeError("Simulated Shopify API failure")

    monkeypatch.setattr(
        MODULE,
        "execute_dj_product_create",
        fake_execute,
    )

    try:
        MODULE.execute_dj_product_create(
            shop="test.myshopify.com",
            access_token="fake-token",
            operations=[],
            handle="dj-test",
            apply=True,
        )
    except RuntimeError as exc:
        assert str(exc) == "Simulated Shopify API failure"
    else:
        pytest.fail("Expected Shopify API failure")


def test_batch_stops_and_logs_shopify_failure(monkeypatch, tmp_path):
    """A Shopify failure stops the batch and creates an error log."""
    import sys
    from types import SimpleNamespace
    import pandas as pd

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dj_shopify_apply_batch.py",
            "dummy.xlsx",
            "--limit",
            "2",
            "--apply",
            "--confirm",
            APPLY_CONFIRMATION,
        ],
    )

    monkeypatch.setattr(MODULE, "read_dj_export", lambda _: [])
    monkeypatch.setattr(MODULE, "evaluate_dj_rows", lambda rows, today: [])
    monkeypatch.setattr(
        MODULE,
        "build_dj_shopify_preview",
        lambda _: pd.DataFrame(),
    )
    monkeypatch.setattr(
        MODULE,
        "get_shopify_config",
        lambda: ("test-shop", "client", "secret"),
    )
    monkeypatch.setattr(MODULE, "get_access_token", lambda *args: "fake-token")
    monkeypatch.setattr(MODULE, "fetch_products", lambda *args: [])

    comparison = pd.DataFrame(
        {
            "handle": ["dj-test-1", "dj-test-2"],
            "status": ["NEW", "NEW"],
        }
    )

    monkeypatch.setattr(
        MODULE,
        "build_dj_live_dry_run_plan",
        lambda *args: (None, comparison, None),
    )

    monkeypatch.setattr(
        MODULE,
        "build_dj_create_plans",
        lambda *args: [
            SimpleNamespace(handle="dj-test-1"),
            SimpleNamespace(handle="dj-test-2"),
        ],
    )

    monkeypatch.setattr(MODULE, "build_dj_mutation_plan", lambda _: [])

    attempted = []

    def fake_execute(**kwargs):
        attempted.append(kwargs["handle"])
        raise RuntimeError("Simulated Shopify failure")

    monkeypatch.setattr(MODULE, "execute_dj_product_create", fake_execute)

    with pytest.raises(SystemExit, match="Import stopped"):
        MODULE.main()

    assert attempted == ["dj-test-1"]

    logs = list((tmp_path / "data/dj/reports").glob("dj_import_*.csv"))
    assert len(logs) == 1

    content = logs[0].read_text(encoding="utf-8")
    assert "dj-test-1" in content
    assert "FAILED_OR_PARTIAL" in content
    assert "Simulated Shopify failure" in content
    assert "dj-test-2" not in content
