import json
import time
from pathlib import Path
import pytest
from personal_deadline_radar.cli import main, read_inputs, atomic_write
from personal_deadline_radar.core import compute, RadarError


def test_run_completes_on_fixture(fixture_dir, tmp_path, capsys):
    start = time.perf_counter()
    out = tmp_path / "results" / "result.json"
    assert main(["run", "--input", str(fixture_dir), "--out", str(out)]) == 0
    assert main(["report", "--results", str(out), "--format", "md"]) == 0
    assert time.perf_counter() - start < 5
    assert "Detected deadlines: 80" in capsys.readouterr().out


def test_cli_smoke_all_subcommands(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["fixtures", "--out", "demo"]) == 0
    assert main(["run", "--input", "demo"]) == 0
    for format in ("json", "md"):
        assert main(["report", "--format", format]) == 0
        assert main(["scan", "--input", "demo", "--format", format]) == 0
    assert main(["upcoming", "--as-of", "2026-10-01", "--days", "30"]) == 0
    for command in ("fixtures", "run", "report", "scan", "upcoming"):
        with pytest.raises(SystemExit) as exc:
            main([command, "--help"])
        assert exc.value.code == 0
    assert chr(0x2014) not in capsys.readouterr().out


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    assert main(["scan", "--input", str(tmp_path)]) == 0
    assert "Detected deadlines: 0" in capsys.readouterr().out

@pytest.mark.parametrize("name,content", [("bad.json", '{\n"records": [}'), ("bad.jsonl", '# synthetic\n{"id":'), ("bad.csv", 'id,kind,text,synthetic\na,email,"unterminated,true'), ("bad.yaml", 'records: [')])
def test_malformed_input_named_error(tmp_path, capsys, name, content):
    (tmp_path / name).write_text(content)
    assert main(["scan", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert name in error and "line" in error and "Error" in error
    assert "Traceback" not in error


def test_missing_input(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "missing")]) == 2
    assert "MissingInput" in capsys.readouterr().err


def test_report_write_failure_no_partial_files(tmp_path):
    target = tmp_path / "directory"
    target.mkdir()
    with pytest.raises(RadarError, match="ReportWriteError"):
        atomic_write(target, "text")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["directory"]


def test_run_determinism(fixture_dir, tmp_path):
    a, b = tmp_path / "a.out", tmp_path / "b.out"
    assert main(["run", "--input", str(fixture_dir), "--out", str(a)]) == 0
    assert main(["run", "--input", str(fixture_dir), "--out", str(b)]) == 0
    assert a.read_bytes() == b.read_bytes()


def test_csv_and_jsonl(tmp_path):
    (tmp_path / "a.csv").write_text('id,kind,text,synthetic,deadline\na,email,note,true,2026-10-01\n')
    (tmp_path / "b.jsonl").write_text('# SYNTHETIC\n' + json.dumps({"id": "b", "kind": "calendar", "text": "Due: 2026-10-02", "synthetic": True}) + '\n')
    assert compute(read_inputs(tmp_path))["deadline_count"] == 2


def test_schema_drift_named_field(tmp_path, capsys):
    (tmp_path / "a.jsonl").write_text(json.dumps({"id": "x", "kind": "email", "text": "", "synthetic": True, "unknown": 1}))
    assert main(["scan", "--input", str(tmp_path)]) == 2
    assert "unknown" in capsys.readouterr().err


def test_invalid_results_named_error(tmp_path, capsys):
    path = tmp_path / "result.json"
    path.write_text('{"schema_version": 1}')
    assert main(["report", "--results", str(path)]) == 2
    assert "ResultError" in capsys.readouterr().err


def test_run_rejects_output_inside_inputs(fixture_dir, capsys):
    assert main(["run", "--input", str(fixture_dir), "--out", str(fixture_dir / "result.json")]) == 2
    assert "outside the input directory" in capsys.readouterr().err
    assert not (fixture_dir / "result.json").exists()


def test_tiny_hand_written_example():
    assert compute(read_inputs(Path(__file__).resolve().parents[1] / "examples" / "tiny"))["deadline_count"] == 3
