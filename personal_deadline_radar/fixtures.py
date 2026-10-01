"""Labelled fixtures with independent, hand-computed expectations. No randomness."""
import json
from pathlib import Path


def generate(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(200):
        record = {"id": f"record-{i:03}", "kind": ("email", "file", "calendar")[i % 3],
                  "synthetic": True, "provenance": "synthetic-fixture", "text": "Routine note. No action required."}
        if i < 40:
            record["deadline"] = "2026-10-15"
        elif i < 80:
            record["text"] = "Application instructions.\nSubmit by: 2026-10-20"
        elif i < 120:
            record["text"] = "Meeting mentioned 2026-10-22. This is not a deadline."
        elif i < 160:
            record["text"] = "No deadline: 2026-10-25\nDue: tomorrow"
        else:
            record["text"] = "Henry's café note, 学校. File C:\\Users\\henry\\notes.md"
        records.append(record)
    payload = {"_comment": "SYNTHETIC fixture, not Henry's real data", "synthetic": True, "records": records}
    # Hand calculation: first 80 IDs are deadlines; 200 - 80 = 120 negatives.
    # Round-robin kinds across 200: 67 emails, 67 files, 66 calendar entries.
    expected = {"_comment": "SYNTHETIC planted ground truth, independently specified", "synthetic": True,
                "record_count": 200, "deadline_count": 80, "records_without_detected_deadline": 120,
                "counts_by_kind": {"email": 67, "file": 67, "calendar": 66},
                "deadlines": [{"id": f"record-{i:03}", "deadline": "2026-10-15" if i < 40 else "2026-10-20"} for i in range(80)]}
    for name, content in (("records.json", payload), ("expectations.json", expected)):
        (out / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return expected
