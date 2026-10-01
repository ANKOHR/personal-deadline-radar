"""Reports contain computed counts and record-level provenance, never savings claims."""
import json


def banner(result):
    synthetic = sum(x["synthetic"] for x in result["inputs"])
    real = result["record_count"] - synthetic
    return f"Data provenance: {synthetic} synthetic fixture records; {real} Henry-entered real records. Provenance is declared by the input author, not independently verified."


def render(result, format="md"):
    if format == "json":
        return json.dumps(dict(result, provenance_banner=banner(result)), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if format != "md":
        raise ValueError("Unsupported report format")
    def cell(value):
        # Escape user content so it cannot create Markdown rows or HTML.
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\n", " ").replace("\r", " ")
    lines = ["# Personal Deadline Radar", "", banner(result), "",
             f"Records: {result['record_count']}", f"Detected deadlines: {result['deadline_count']}",
             f"Records without a detected deadline: {result['records_without_detected_deadline']}", "",
             "Time saved: unmeasured. Money saved: unmeasured. Real-data accuracy: unmeasured.",
             "No predictions or relative-date estimates are included.", "",
             "| ID | Kind | Deadline | Source | Line | Evidence | Provenance |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for d in result["deadlines"]:
        values = [d["id"], d["kind"], d["deadline"], d["source"], d["line"], d["evidence"],
                  "synthetic" if d["synthetic"] else "Henry-entered real"]
        lines.append("| " + " | ".join(cell(v) for v in values) + " |")
    lines += ["", "## Input inventory", "", "Every processed record is listed, including records without detected deadlines.", ""]
    for item in result["inputs"]:
        lines.append(f"- {cell(item['id'])}: {cell(item['source'])}, line {item['line']}; {cell(item['provenance'])}")
    return "\n".join(lines) + "\n"
