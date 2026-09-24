"""Command line version: python3 vcf.py [input.xlsx|input.csv] [output.vcf]

With no arguments it reads contacts.xlsx and writes contacts.vcf, like the original script.
Rows with errors are skipped and reported, since there is no review page here.
"""

import argparse
import sys
from pathlib import Path

from vcfcore import ERROR, TableError, build_vcf, load_contacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a contacts spreadsheet into a single .vcf file.")
    parser.add_argument("input", nargs="?", default="contacts.xlsx", help="a .xlsx or .csv file (default: contacts.xlsx)")
    parser.add_argument("output", nargs="?", default="contacts.vcf", help="where to write the vCards (default: contacts.vcf)")
    args = parser.parse_args()

    path = Path(args.input)
    try:
        with path.open("rb") as f:
            contacts, _ = load_contacts(f, path.name)
    except FileNotFoundError:
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    except TableError as exc:
        print(f"Cannot convert {path}: {exc}", file=sys.stderr)
        return 1

    for contact in contacts:
        for issue in contact.issues:
            print(f"Row {contact.row} [{issue.level}] {issue.message}", file=sys.stderr)

    usable = [c for c in contacts if not c.has_errors]
    Path(args.output).write_text(build_vcf(usable), encoding="utf-8")

    skipped = len(contacts) - len(usable)
    print(f"Wrote {len(usable)} contacts to {args.output}" + (f" ({skipped} rows with errors skipped)" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
