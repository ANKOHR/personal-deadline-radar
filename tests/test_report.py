import json
from personal_deadline_radar.report import render
from personal_deadline_radar.core import compute


def test_report_matches_ground_truth_exact(result):
    report = json.loads(render(result, "json"))
    assert report["record_count"] == 200
    assert report["deadline_count"] == 80
    assert report["records_without_detected_deadline"] == 120
    assert report["counts_by_kind"] == {"email": 67, "file": 67, "calendar": 66}
    assert {d["id"] for d in report["deadlines"]} == {f"record-{i:03}" for i in range(80)}

def test_report_zero_false_positives(result):
    reported = {d["id"] for d in json.loads(render(result, "json"))["deadlines"]}
    negatives = {f"record-{i:03}" for i in range(80, 200)}
    assert not reported & negatives


def test_report_carries_provenance_banner(result):
    for format in ("md", "json"):
        output = render(result, format)
        assert "200 synthetic fixture records" in output
        assert "0 Henry-entered real records" in output


def test_hypothetical_figures_labelled(result):
    for format in ("md", "json"):
        assert "unmeasured" in render(result, format)
    assert result["honesty"]["time_saved"] == "unmeasured"
    assert result["honesty"]["money_saved"] == "unmeasured"


def test_determinism_byte_identical(result):
    for format in ("md", "json"):
        assert render(result, format).encode() == render(result, format).encode()


def test_no_em_dashes_in_outputs(result):
    for format in ("md", "json"):
        assert chr(0x2014) not in render(result, format)


def test_real_and_mixed_provenance():
    records = [({"id": "real", "kind": "calendar", "text": "", "deadline": "2026-11-01", "synthetic": False, "provenance": "henry-entered"}, "own.json", 1),
               ({"id": "fake", "kind": "file", "text": "", "synthetic": True}, "fixture.json", 1)]
    output = render(compute(records))
    assert "1 synthetic fixture records; 1 Henry-entered real records" in output
    assert "own.json" in output


def test_markdown_escapes_content():
    result = compute([({"id": "<script>|oops", "kind": "file", "text": "", "synthetic": True, "deadline": "2026-10-01"}, "a|b.json", 1)])
    assert "<script>" not in render(result)
    assert "&#124;" in render(result)
