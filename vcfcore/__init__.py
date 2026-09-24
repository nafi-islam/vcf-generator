"""Spreadsheet and vCard to vCard conversion, with no web framework code.

Pipeline: read_table -> find_columns -> records_from_rows (or read_vcards) -> clean -> build_vcf
"""

from .builder import build_vcf
from .columns import find_columns
from .models import ADJUSTED, ERROR, WARNING, Contact, Issue, MonthDay, TableError
from .reader import MAX_ROWS, read_table
from .validate import clean, records_from_rows
from .vcards import read_vcards

MAX_FILES = 10


def load_files(files) -> tuple[list[Contact], list[str]]:
    """Read and clean one or more (stream, filename) pairs into a single list.

    Returns the contacts and the names of ignored spreadsheet columns. Contacts that
    repeat an earlier phone or email start out excluded, so combined files do not
    produce duplicates; the user can include them again on the review page.
    Raises TableError when a file itself cannot be used.
    """
    files = list(files)
    if len(files) > MAX_FILES:
        raise TableError(f"Please upload at most {MAX_FILES} files at a time.")
    several = len(files) > 1

    records, ignored = [], []
    for stream, filename in files:
        try:
            file_records, file_ignored = _read_one(stream, filename)
        except TableError as exc:
            raise TableError(f"{filename}: {exc}" if several else str(exc)) from exc
        for record in file_records:
            record["source"] = filename
        records += file_records
        ignored += [name for name in file_ignored if name not in ignored]

    if not records:
        raise TableError("The file has a header row but no contacts under it." if not several else "None of the files contain contacts.")
    if len(records) > MAX_ROWS:
        raise TableError(f"Together the files have more than {MAX_ROWS} contacts. Please combine fewer files.")

    contacts = clean(records)
    for contact in contacts:
        if contact.duplicate_of:
            contact.include = False
    return contacts, ignored


def load_contacts(stream, filename: str) -> tuple[list[Contact], list[str]]:
    """Read and clean a single file."""
    return load_files([(stream, filename)])


def _read_one(stream, filename: str) -> tuple[list[dict], list[str]]:
    if filename.lower().endswith(".vcf"):
        return read_vcards(stream.read()), []
    rows = read_table(stream, filename)
    columns = find_columns(rows)
    return records_from_rows(rows, columns), columns.ignored


__all__ = [
    "ADJUSTED", "ERROR", "WARNING", "MAX_FILES", "MAX_ROWS", "Contact", "Issue", "MonthDay", "TableError",
    "build_vcf", "clean", "find_columns", "load_contacts", "load_files", "read_table", "records_from_rows",
]
