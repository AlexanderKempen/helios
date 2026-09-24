from typer.testing import CliRunner

from helios.commands.estimate import _apply_pricing, _parse_estimate
from helios.commands.report import _short_model
from helios.main import app
from helios.services.db import init_db, insert_event

runner = CliRunner()


def test_report_runs_against_a_fresh_database():
    # Regression: the packaged db/schema.sql must be importable, otherwise every
    # command dies with FileNotFoundError on init_db().
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 0, result.output
    assert "No usage data recorded yet" in result.output


def test_report_renders_recorded_usage():
    init_db()
    insert_event(
        "csv-export", "claude-sonnet-4-5-20250929", 1000, 200, 1200, 1.23,
        timestamp="2026-01-01T00:00:00Z",
    )
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 0, result.output
    assert "csv-export" in result.output
    assert "$1.23" in result.output


def test_sync_reports_when_there_is_nothing_to_import():
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0, result.output
    assert "No new usage events" in result.output


def test_short_model_labels():
    assert _short_model("claude-sonnet-4-5-20250929") == "Sonnet 4.5"
    assert _short_model("claude-opus-5") == "Opus 5"
    assert _short_model("claude-3-5-sonnet-20241022") == "Sonnet 3.5"
    assert _short_model("claude-3-opus-20240229") == "Opus 3"
    assert _short_model(None) == "—"


def test_estimate_json_is_extracted_from_fenced_output():
    data = _parse_estimate('```json\n{"scope": "small"}\n```')
    assert data == {"scope": "small"}


def test_estimate_cost_is_repriced_for_the_model_used():
    data = {"tokens": {"min": 1_000_000, "max": 2_000_000}, "cost": {"min": 0, "max": 0}}
    _apply_pricing(data, "claude-opus-5")
    # 70% input at $5/MTok + 30% output at $25/MTok = $11/MTok
    assert data["cost"] == {"min": 11.0, "max": 22.0}
