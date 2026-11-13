"""Sanity checks for config/: file maps and models.toml."""

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FILE_MAPS = sorted((ROOT / "config" / "file_maps").glob("*.v*.yaml"))
DATA_FORMATS = (ROOT / "docs" / "data-formats.md").read_text(encoding="utf-8")


def _load(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_there_is_one_map_per_mvp_file_type() -> None:
    assert [p.name for p in FILE_MAPS] == [
        "loans.v1.yaml",
        "payables.v1.yaml",
        "receivables.v1.yaml",
    ]


@pytest.mark.parametrize("path", FILE_MAPS, ids=lambda p: p.name)
def test_identity_matches_filename(path: Path) -> None:
    spec = _load(path)
    file_type, version = re.fullmatch(r"(\w+)\.v(\d+)\.yaml", path.name).groups()  # type: ignore[union-attr]
    assert spec["file_type"] == file_type
    assert spec["version"] == int(version)
    assert spec["status"] in {"proposed", "confirmed"}
    assert spec["as_of"] == {"source": "parameter"}


@pytest.mark.parametrize("path", FILE_MAPS, ids=lambda p: p.name)
def test_headers_appear_verbatim_in_data_formats(path: Path) -> None:
    table = _load(path)["table"]
    headers = list(table["header_row"]["contains_all"])
    headers += [c["header"] for c in table["columns"].values()]
    headers.append(table["end"]["total_row"]["value_column"])
    for header in headers:
        assert header in DATA_FORMATS, f"{header!r} not found in docs/data-formats.md"


@pytest.mark.parametrize("path", FILE_MAPS, ids=lambda p: p.name)
def test_field_references_resolve(path: Path) -> None:
    spec = _load(path)
    table = spec["table"]
    fields = set(table["columns"])
    headers = {c["header"] for c in table["columns"].values()}

    assert table["end"]["total_row"]["verify"]["field"] in fields
    assert set(table["duplicates"]["key"]) <= fields
    for rule in table.get("skip_rows", []):
        assert rule["when"]["field"] in fields
    label_column = table["end"]["total_row"]["label_column"]
    assert label_column == "any_column" or label_column in headers
    assert table["end"]["total_row"]["value_column"] in headers


def test_models_toml_uses_known_models() -> None:
    config = tomllib.loads((ROOT / "config" / "models.toml").read_text(encoding="utf-8"))
    features = config["features"]
    assert {
        "file_map_proposal",
        "discrepancy_classification",
        "rule_assistant",
        "forecast_qa",
        "explanation",
        "board_report",
    } <= set(features)
    allowed = {"claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"}
    for name, feature in features.items():
        assert feature["model"] in allowed, name
        assert set(feature) == {"model"}, f"{name}: only 'model' is configured for now"
