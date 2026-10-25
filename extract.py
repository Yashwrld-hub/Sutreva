"""
Command-line version. All real logic lives in core.py; file generation in
exports.py. This file only reads arguments and prints/writes results.

Usage:
    python extract.py <datasheet.txt|.pdf> [template.json] [--debug] [--export xlsx|pdf|csv]
"""

import sys

from core import audit_summary, extract_text_from_pdf, load_schema, run_audit
from exports import suggested_filename, to_csv_bytes, to_excel_bytes, to_pdf_bytes


EXPORTERS = {"xlsx": to_excel_bytes, "pdf": to_pdf_bytes, "csv": to_csv_bytes}


def print_report(rows):
    print(f"\n{'FIELD':<28}{'EXTRACTED VALUE':<24}{'STATUS'}")
    print("-" * 66)
    for r in rows:
        val = r["extracted_value"]
        val = "\u2014" if val in (None, "") else str(val)
        print(f"{r['field']:<28}{val:<24}{r['status']}")

    s = audit_summary(rows)
    print("-" * 66)
    print(f"{s['MATCHED']} of {s['TOTAL']} matched · "
          f"{s['MISSING']} missing · {s['MISMATCHED']} mismatched · "
          f"{s['OUT OF RANGE']} out of range\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Usage: python extract.py <datasheet.txt|.pdf> [template.json] "
              "[--debug] [--export xlsx|pdf|csv]")
        sys.exit(1)

    datasheet_path = args[0]
    template_path = args[1] if len(args) > 1 else "templates/mechanical_seal_audit.json"

    export_fmt = None
    if "--export" in sys.argv:
        idx = sys.argv.index("--export")
        if idx + 1 < len(sys.argv):
            export_fmt = sys.argv[idx + 1].lower()
        if export_fmt not in EXPORTERS:
            print(f"Unknown export format. Choose one of: {', '.join(EXPORTERS)}")
            sys.exit(1)

    try:
        schema = load_schema(template_path)
    except ValueError as e:
        print(f"Could not load the template: {e}")
        sys.exit(1)

    try:
        if datasheet_path.lower().endswith(".pdf"):
            datasheet_text = extract_text_from_pdf(datasheet_path, schema=schema)
        else:
            with open(datasheet_path, "r") as f:
                datasheet_text = f.read()
    except (OSError, ValueError) as e:
        print(f"Could not read the datasheet: {e}")
        sys.exit(1)

    print(f"Template: {schema['template_name']}")
    print(f"Datasheet: {datasheet_path}")

    try:
        rows, raw_output, _ = run_audit(datasheet_text, schema)
    except Exception as e:  # noqa: BLE001
        print(f"The audit failed: {e}")
        sys.exit(1)

    print_report(rows)

    if "--debug" in sys.argv:
        print("--- Raw model output ---")
        print(raw_output)

    if export_fmt:
        source = datasheet_path.rsplit("/", 1)[-1]
        data = EXPORTERS[export_fmt](rows, schema["template_name"], source)
        out_name = suggested_filename(schema["template_name"], export_fmt, source)
        with open(out_name, "wb") as f:
            f.write(data)
        print(f"Exported to {out_name}")


if __name__ == "__main__":
    main()
