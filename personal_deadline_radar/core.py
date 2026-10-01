"""Pure parsing and detection. No predictions, network calls, or I/O."""
import re
from datetime import date

class RadarError(ValueError):
    """Named input or output failure suitable for CLI display."""

FIELDS = {"id", "kind", "text", "deadline", "synthetic", "provenance", "amount"}
PATTERN = re.compile(r"(?im)^\s*(?:deadline|due|submit by|apply by)\s*:\s*(\d{4}-\d{2}-\d{2})\s*[.!]?\s*$")


def parse_date(value, field="deadline"):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise RadarError(f"SchemaError: field {field}: expected ISO date YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RadarError(f"SchemaError: field {field}: invalid date {value}") from None


def validate(record):
    if not isinstance(record, dict):
        raise RadarError("SchemaError: field record: expected object")
    unknown = set(record) - FIELDS
    if unknown:
        raise RadarError(f"SchemaError: unknown field {sorted(unknown)[0]}")
    for field in ("id", "kind", "text", "synthetic"):
        if field not in record:
            raise RadarError(f"SchemaError: missing field {field}")
    for field in ("id", "text"):
        if not isinstance(record[field], str):
            raise RadarError(f"SchemaError: field {field}: expected string")
    if not record["id"] or len(record["id"]) > 256:
        raise RadarError("SchemaError: field id: length must be 1..256")
    if len(record["text"]) > 1000000:
        raise RadarError("SchemaError: field text: exceeds 1000000 characters")
    if record["kind"] not in ("email", "file", "calendar"):
        raise RadarError("SchemaError: field kind: expected email, file, or calendar")
    if type(record["synthetic"]) is not bool:
        raise RadarError("SchemaError: field synthetic: expected boolean")
    if not record["synthetic"] and record.get("provenance") != "henry-entered":
        raise RadarError("SchemaError: field provenance: real data requires henry-entered")
    if record.get("provenance") not in (None, "henry-entered", "synthetic-fixture"):
        raise RadarError("SchemaError: field provenance: unsupported value")
    if record["synthetic"] and record.get("provenance") == "henry-entered":
        raise RadarError("SchemaError: field provenance: conflicts with synthetic")
    if "amount" in record:
        import math
        amount = record["amount"]
        if type(amount) not in (int, float) or (type(amount) is float and not math.isfinite(amount)) or amount < 0:
            raise RadarError("SchemaError: field amount: expected finite nonnegative number")
    if record.get("deadline") is not None:
        parse_date(record["deadline"])
    return record


def detect(record):
    validate(record)
    candidates = []
    if record.get("deadline"):
        candidates.append((record["deadline"], "deadline field"))
    for match in PATTERN.finditer(record["text"]):
        parse_date(match.group(1), "text deadline")
        candidates.append((match.group(1), match.group(0).strip()))
    dates = sorted({item[0] for item in candidates})
    if len(dates) > 1:
        raise RadarError("SchemaError: field deadline: conflicting dates; split into separate records")
    if not candidates:
        return None
    return {"id": record["id"], "kind": record["kind"], "deadline": dates[0],
            "evidence": candidates[0][1], "synthetic": record["synthetic"]}


def compute(entries):
    seen = set()
    matches = []
    inputs = []
    counts = {"email": 0, "file": 0, "calendar": 0}
    for record, source, line in entries:
        try:
            validate(record)
            if record["id"] in seen:
                raise RadarError(f"SchemaError: field id: duplicate {record['id']}")
            seen.add(record["id"])
            match = detect(record)
        except RadarError as exc:
            raise RadarError(f"{source}: line {line}: {exc}") from None
        counts[record["kind"]] += 1
        inputs.append({"id": record["id"], "kind": record["kind"], "source": source, "line": line,
                       "synthetic": record["synthetic"],
                       "provenance": "synthetic fixture" if record["synthetic"] else "Henry-entered real data"})
        if match:
            matches.append(dict(match, source=source, line=line))
    matches.sort(key=lambda x: (x["deadline"], x["id"]))
    inputs.sort(key=lambda x: (x["source"], x["id"]))
    return {"schema_version": 1, "record_count": len(inputs), "deadline_count": len(matches),
            "records_without_detected_deadline": len(inputs) - len(matches),
            "counts_by_kind": counts, "deadlines": matches, "inputs": inputs,
            "honesty": {"time_saved": "unmeasured", "money_saved": "unmeasured",
                        "accuracy": "unmeasured on real data; fixture accuracy requires labelled comparison"}}


def upcoming(result, as_of, days):
    start = parse_date(as_of, "as_of")
    if days < 0:
        raise RadarError("SchemaError: field days: must be nonnegative")
    return [d for d in result["deadlines"] if 0 <= (parse_date(d["deadline"]) - start).days <= days]
