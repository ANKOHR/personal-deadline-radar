import pytest
from personal_deadline_radar.core import RadarError, compute, detect, upcoming


def record(**changes):
    value = {"id": "a", "kind": "email", "text": "Due: 2026-10-15", "synthetic": True}
    value.update(changes)
    return value

@pytest.mark.parametrize("changes", [
    {"amount": -1}, {"amount": float("nan")}, {"amount": True},
    {"deadline": "2026-02-30"}, {"deadline": "10/01/2026"},
    {"synthetic": "true"}, {"synthetic": False}, {"kind": "other"},
    {"id": ""}, {"text": "x" * 1000001}, {"extra": 1},
    {"deadline": "2026-10-16"}, {"provenance": "henry-entered"},
])
def test_rejects_adversarial_values(changes):
    with pytest.raises(RadarError, match="SchemaError"):
        detect(record(**changes))

def test_duplicate_ids():
    with pytest.raises(RadarError, match="duplicate"):
        compute([(record(), "a.json", 2), (record(), "b.json", 3)])

@pytest.mark.parametrize("text", ["No deadline: 2026-10-15", "Meeting 2026-10-15", "Due: tomorrow", "Not due: 2026-10-15", "Please submit by 15 October", "The old message said Due: 2026-10-15"])
def test_no_inferred_dates(text):
    assert detect(record(text=text)) is None

def test_handles_unicode_and_long_inputs():
    text = "学校 café C:\\Users\\henry\\notes.md " + "x" * 100000 + "\nDue: 2099-12-31"
    assert detect(record(text=text))["deadline"] == "2099-12-31"

def test_upcoming_inclusive(result):
    assert len(upcoming(result, "2026-10-15", 5)) == 80
    assert len(upcoming(result, "2026-10-16", 4)) == 40
    assert upcoming(result, "2026-10-21", 0) == []
    with pytest.raises(RadarError):
        upcoming(result, "2026-10-01", -1)


def test_extreme_nonnegative_integer_does_not_overflow():
    assert detect(record(amount=10 ** 1000))["deadline"] == "2026-10-15"
