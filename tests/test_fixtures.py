import json
from personal_deadline_radar.cli import read_inputs
from personal_deadline_radar.core import compute
from personal_deadline_radar.fixtures import generate


def test_fixtures_labelled_synthetic(fixture_dir):
    for path in fixture_dir.iterdir():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["synthetic"] is True
        assert "SYNTHETIC" in data["_comment"]
    assert all(r["synthetic"] is True for r, _, _ in read_inputs(fixture_dir))

def test_fixture_ground_truth_matches_hand_computed(fixture_dir, result):
    truth = json.loads((fixture_dir / "expectations.json").read_text())
    assert truth["record_count"] == 200
    assert truth["deadline_count"] == 80
    for field in ("record_count", "deadline_count", "counts_by_kind", "records_without_detected_deadline"):
        assert result[field] == truth[field]
    assert [{"id": d["id"], "deadline": d["deadline"]} for d in result["deadlines"]] == truth["deadlines"]

def test_corrupted_fixture_changes_computed_result(fixture_dir):
    path = fixture_dir / "records.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["records"][0]["deadline"]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert compute(read_inputs(fixture_dir))["deadline_count"] == 79
    # Expectations are not used by the engine, even if deliberately corrupted.
    (fixture_dir / "expectations.json").write_text('{"deadline_count": 999}')
    assert compute(read_inputs(fixture_dir))["deadline_count"] == 79

def test_generator_byte_identical(tmp_path):
    generate(tmp_path / "one")
    generate(tmp_path / "two")
    for path in (tmp_path / "one").iterdir():
        assert path.read_bytes() == (tmp_path / "two" / path.name).read_bytes()
