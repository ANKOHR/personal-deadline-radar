# Personal Deadline Radar

A deterministic Python CLI for detecting explicit deadlines in local email, file and calendar records. Built for Henry's school, applications, outreach and builds. CPU only, standard library runtime, no network calls, no language models, no database. Inputs are hand-entered records, not direct integrations with inboxes or calendars.

## Quickstart

Python 3.10+ and setuptools 68+ are required. Install from this checkout without contacting package indexes:

```powershell
python -m pip install -e . --no-build-isolation --no-deps --disable-pip-version-check
pdr fixtures --out demo
pdr run --input demo
pdr report --format md
python -m pytest -q
```

If the user scripts directory is absent from PATH, use `python -m personal_deadline_radar.cli` wherever an example uses `pdr`. Alternatively install into a virtual environment and activate it. pytest is a development prerequisite, not a runtime dependency.

The fixture demo contains 200 synthetic records, 80 planted deadlines and 120 negative cases. `examples/tiny/records.json` is a hand-written five-record synthetic example: three deadlines and two negatives. Try `pdr scan --input examples/tiny`.

## Input format reference

Use a dedicated input directory. Every file is processed recursively, sorted by relative filename. Supported formats: UTF-8 JSON, JSONL and CSV. Unsupported formats, including YAML and raw Markdown, produce a named schema error. Normalize raw emails, file contents and calendar events into these formats by hand. `expectations.json` is reserved for test ground truth and never processed. Keep reports and other files outside the input directory. The CLI refuses a run result path inside it.

JSON envelope:

```json
{
  "_comment": "Henry-entered real data, not a synthetic fixture",
  "synthetic": false,
  "records": [
    {
      "id": "application-1",
      "kind": "email",
      "text": "Submit by: 2026-10-15",
      "synthetic": false,
      "provenance": "henry-entered"
    }
  ]
}
```

This snippet is illustrative format documentation, not a measured real-data trial. No real records ship in the repository.

Each record requires a unique `id` (1 to 256 characters), `kind` (`email`, `file`, `calendar`), `text` (up to 1,000,000 characters), and boolean `synthetic`. Real records require `provenance: "henry-entered"`; synthetic provenance may be absent or `synthetic-fixture`. The envelope flag must match all records; use separate files for mixed sources. Optional fields: `deadline` (ISO YYYY-MM-DD or null), `amount` (finite nonnegative number, validated but never totalled). Unknown fields fail explicitly. Do not include personal data in a public checkout.

JSONL contains one record object per line; blank lines and `#` comment lines are allowed. CSV uses the record fields as column headers, `true` or `false` for synthetic, and ISO dates. Quote multiline text using normal CSV quoting. CSV line numbers identify the end of a logical record. Duplicate JSON keys and duplicate CSV headers are errors.

Detection accepts an explicit `deadline` field or a standalone line of the following form, case-insensitive:

```text
Deadline: 2026-10-15
Due: 2026-10-15
Submit by: 2026-10-15
Apply by: 2026-10-15
```

Whitespace and a trailing full stop or exclamation mark are accepted. Calendar events need an explicit deadline field or the same text syntax; a meeting mention alone is not classified as a deadline. Relative dates, unstructured prose, quoted phrases mid-sentence and negated phrases do not match. A standalone deadline line in pasted quoted text can still match: normalize the record to the current obligation first. Multiple occurrences of the same date count once. Conflicting dates fail; split distinct obligations into distinct IDs. Invalid matched dates fail instead of disappearing. Past and future dates are valid, including far-future dates: the tool never guesses whether they are plausible.

Windows paths and Unicode text are accepted without reinterpretation. Record IDs and report paths are not shell commands. Malformed files fail the whole run with filename and line information. JSON syntax lines are exact; JSON record validation lines locate the record's ID in ordinary formatted input. Nonstandard property ordering may make that location approximate; JSONL provides exact per-record lines.

## Subcommand catalogue

- `pdr fixtures --out demo`: generate deterministic labelled synthetic fixtures and independent expectations. Rewrites the two generated files; use a dedicated directory.
- `pdr run --input demo --out .pdr/results.json`: parse and compute, then atomically save a result snapshot. Default output is `.pdr/results.json`.
- `pdr report --format md`: render the saved snapshot. Use `--format json`, `--results <file>`, or `--out evidence/report.md` as needed. Reports reflect the saved run, not subsequent input edits.
- `pdr scan --input examples/tiny --format json`: compute directly without saving a snapshot.
- `pdr upcoming --as-of 2026-10-01 --days 30`: list saved deadlines in the inclusive window from the explicit date through 30 days later. No dependence on the current clock. `--results <file>` selects another snapshot. Negative days fail.

Every subcommand supports `--help` with an example. Success exits 0; named input, schema, result and write failures exit 2. Writes use a temporary sibling and atomic replacement; a failed write leaves existing output intact and removes temporary files.

## Architecture

```text
local JSON / JSONL / CSV
          |
          v
cli.read_inputs -> core.validate -> core.detect -> core.compute
                                                     |
                                                     v
                                              saved JSON snapshot
                                                     |
                                                     v
                                      report.render -> Markdown / JSON
fixtures.generate -> labelled records + independent expectations
```

The core contains pure functions without I/O. Adapters, persistence and argparse live in the CLI. Reports carry both a provenance banner and an inventory of every processed record. Each match carries its ID, source, line, evidence, kind and synthetic flag.

## Honesty boundary

Counts and dates are computed from explicit input. The tool cannot discover missing obligations or predict intent. Records without a detected deadline are not claimed to have no deadline in real life. Provenance is an author declaration, not independently verified. Accuracy is unmeasured on real data. Time saved and money saved remain explicitly **unmeasured**; runtime is not a savings measurement. No savings or hypothetical benefit number is generated.

The synthetic evaluation measures correctness only on the planted fixture distribution. It does not establish general inbox accuracy. See `EVIDENCE.md` for observed test and demo results. Same input and arguments produce byte-identical reports; filenames and input contents are part of the input. No random generator is used, so there is no seed. Wall-clock timing is stored separately in evidence, never in deterministic reports.

## Fixture labelling policy

Every generated JSON file includes a `_comment` synthetic header and `synthetic: true`. Every record is also labelled. JSONL synthetic examples should carry a `# SYNTHETIC` header plus per-record flags; CSV synthetic examples should carry a `synthetic` column set to `true` (comments are not CSV data). The five-record JSON example also has both labels. Report banners distinguish synthetic records and Henry-entered real records even when mixed.

The independent hand calculation is 40 explicit-field matches plus 40 standalone-text matches, with 120 negatives. Round-robin kinds across 200 records give 67 email, 67 file and 66 calendar records. Tests compare every detected ID and date, not just totals. Removing a planted deadline changes the computed result to 79; corrupting expectations never controls engine output.

## Failure modes and limits

Malformed input produces `ParseError`; missing directory produces `MissingInput` with a usage hint; unsupported fields, duplicate IDs, conflicting dates and invalid values produce `SchemaError`; invalid or missing cached results produce `ResultError`; failed report persistence produces `ReportWriteError`. There is no partial success that silently drops bad records. Input limits prevent runaway strings; ordinary long Unicode inputs are tested. Raw file extraction, timezone timestamps, recurring events, attachments and relative-date reasoning are outside this version's scope.

## Two-week improvement hook and verdict

Start the evidence window on the first actual use, not the build date. Keep Henry's real records and trial notes outside this public repository. For 14 days, record whether the CLI was used each day. Hand-check all obligations in a sample and count true positives (TP), false positives (FP), and missed deadlines (FN). The primary error metric is `(FP + FN) / (TP + FP + FN)`; report numerator and denominator. If the denominator is zero, accuracy is unmeasured, not 100 percent.

If error exceeds 10 percent, fix the most frequent failure cause and recheck the same sample plus new examples, or kill with the reason recorded. If never used, kill. If acceptance criteria fail, fix them or kill. Optional savings measurement requires paired measured manual and CLI baselines on the same inputs.

After the window, record an explicit evidence-based verdict in `VERDICT.md`: expand for daily use or revenue; integrate for substantial overlap with a sibling project; commercialise if a buyer would pay for this version; maintain as portfolio evidence otherwise; kill if unused or unable to meet criteria. No two-week use evidence is fabricated at build time.
