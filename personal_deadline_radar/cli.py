"""Local file adapters and CLI. Only JSON, JSONL and CSV are input formats."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import RadarError, compute, upcoming
from .fixtures import generate
from .report import render, banner


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise RadarError(f"ParseError: duplicate JSON field {key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs)


def read_inputs(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise RadarError(f"MissingInput: {directory}: use pdr fixtures --out demo or provide an input directory")
    entries = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name == "expectations.json":
            continue
        source = path.relative_to(directory).as_posix()
        if path.suffix.lower() not in (".json", ".jsonl", ".csv"):
            raise RadarError(f"SchemaError: {source}: line 1: field format: supported inputs are JSON, JSONL, CSV")
        line = 1
        try:
            text = path.read_text(encoding="utf-8-sig")
            if path.suffix.lower() == ".json":
                data = strict_json(text)
                if not isinstance(data, dict) or set(data) - {"_comment", "synthetic", "records"} or not isinstance(data.get("records"), list):
                    raise RadarError("SchemaError: field records: expected envelope with records list")
                if type(data.get("synthetic")) is not bool:
                    raise RadarError("SchemaError: field synthetic: envelope requires boolean")
                # Generator writes one id per record; locate starts without changing data.
                cursor = 0
                for record in data["records"]:
                    pos = text.find('"id"', cursor)
                    line = text.count("\n", 0, pos) + 1 if pos >= 0 else 1
                    cursor = max(pos + 4, cursor)
                    if isinstance(record, dict) and record.get("synthetic") != data["synthetic"]:
                        raise RadarError("SchemaError: field synthetic: envelope and record mismatch")
                    entries.append((record, source, line))
            elif path.suffix.lower() == ".jsonl":
                for line, raw in enumerate(text.splitlines(), 1):
                    if raw.strip() and not raw.lstrip().startswith("#"):
                        entries.append((strict_json(raw), source, line))
            else:
                reader = csv.DictReader(io.StringIO(text), strict=True)
                if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                    raise RadarError("SchemaError: field CSV header: missing or duplicate columns")
                for record in reader:
                    line = reader.line_num
                    if None in record or None in record.values():
                        raise RadarError("ParseError: CSV row has wrong number of fields")
                    if record.get("synthetic") not in ("true", "false"):
                        raise RadarError("SchemaError: field synthetic: CSV expects true or false")
                    record["synthetic"] = record["synthetic"] == "true"
                    if record.get("deadline") == "":
                        record.pop("deadline")
                    if "amount" in record:
                        record["amount"] = float(record["amount"])
                    entries.append((record, source, line))
        except json.JSONDecodeError as exc:
            raise RadarError(f"ParseError: {source}: line {line + exc.lineno - 1}: {exc.msg}") from None
        except csv.Error as exc:
            raise RadarError(f"ParseError: {source}: line {reader.line_num}: {exc}") from None
        except RadarError as exc:
            raise RadarError(f"{source}: line {line}: {exc}") from None
        except (UnicodeError, ValueError, OSError) as exc:
            raise RadarError(f"ParseError: {source}: line {line}: {exc}") from None
    return entries


def atomic_write(path, text):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            f.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        raise RadarError(f"ReportWriteError: {path}: {exc}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load_result(path):
    try:
        result = strict_json(Path(path).read_text(encoding="utf-8"))
        required = {"schema_version", "record_count", "deadline_count", "records_without_detected_deadline", "counts_by_kind", "deadlines", "inputs", "honesty"}
        if not isinstance(result, dict) or not required <= result.keys() or result["schema_version"] != 1:
            raise RadarError("SchemaError: field results: unsupported result schema")
        # Validate cached counts and matches by reconstructing explicit records.
        records = []
        matches = {d["id"]: d for d in result["deadlines"]}
        for item in result["inputs"]:
            d = matches.get(item["id"])
            record = {"id": item["id"], "kind": item["kind"], "text": "", "synthetic": item["synthetic"]}
            if not record["synthetic"]:
                record["provenance"] = "henry-entered"
            if d:
                record["deadline"] = d["deadline"]
            records.append((record, item["source"], item["line"]))
        verified = compute(records)
        for key in ("record_count", "deadline_count", "records_without_detected_deadline", "counts_by_kind", "honesty"):
            if result[key] != verified[key]:
                raise RadarError(f"SchemaError: field {key}: cached counts do not reconcile")
        if len(matches) != len(result["deadlines"]) or set(matches) - {i["id"] for i in result["inputs"]}:
            raise RadarError("SchemaError: field deadlines: duplicate or unknown id")
        for d in result["deadlines"]:
            item = next(i for i in result["inputs"] if i["id"] == d["id"])
            if any(d[k] != item[k] for k in ("kind", "source", "line", "synthetic")) or not isinstance(d["evidence"], str):
                raise RadarError("SchemaError: field deadlines: match provenance conflicts with input inventory")
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RadarError(f"ResultError: {path}: line 1: {exc}; run pdr run --input <dir> first") from None


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pdr", description="Detect explicit deadlines in local, author-labelled records. No network or language models.")
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("fixtures", help="Generate 200 labelled synthetic records", epilog="Example: pdr fixtures --out demo")
    p.add_argument("--out", required=True)
    p = subs.add_parser("run", help="Detect deadlines and save computed results", epilog="Example: pdr run --input demo")
    p.add_argument("--input", required=True)
    p.add_argument("--out", default=".pdr/results.json")
    p = subs.add_parser("report", help="Render computed results with provenance", epilog="Example: pdr report --format md")
    p.add_argument("--format", choices=("md", "json"), default="md")
    p.add_argument("--results", default=".pdr/results.json")
    p.add_argument("--out")
    p = subs.add_parser("scan", help="Detect and report directly from local records", epilog="Example: pdr scan --input demo --format json")
    p.add_argument("--input", required=True)
    p.add_argument("--format", choices=("md", "json"), default="md")
    p = subs.add_parser("upcoming", help="List deadlines in an explicit inclusive date window", epilog="Example: pdr upcoming --as-of 2026-10-01 --days 30")
    p.add_argument("--as-of", required=True)
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--results", default=".pdr/results.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "fixtures":
            generate(args.out)
            print("Generated 200 synthetic fixture records with planted ground truth.")
        elif args.command == "run":
            if Path(args.out).resolve().is_relative_to(Path(args.input).resolve()):
                raise RadarError("SchemaError: field out: results must be outside the input directory")
            result = compute(read_inputs(args.input))
            atomic_write(args.out, render(result, "json"))
            print(f"Processed {result['record_count']} records; detected {result['deadline_count']} deadlines. Results: {args.out}")
            print(banner(result))
        elif args.command == "scan":
            print(render(compute(read_inputs(args.input)), args.format), end="")
        elif args.command == "report":
            output = render(load_result(args.results), args.format)
            if args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        else:
            result = load_result(args.results)
            print(json.dumps({"provenance_banner": banner(result), "as_of": args.as_of,
                              "days": args.days, "deadlines": upcoming(result, args.as_of, args.days)}, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (RadarError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
