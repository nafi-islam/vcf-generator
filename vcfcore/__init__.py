"""Spreadsheet to vCard conversion, with no web framework code.

Pipeline: read_table -> find_columns -> records_from_rows -> clean -> build_vcf
"""

from .builder import build_vcf
from .columns import find_columns
from .models import ADJUSTED, ERROR, WARNING, Contact, Issue, MonthDay, TableError
from .reader import MAX_ROWS, read_table
from .validate import clean, records_from_rows


def load_contacts(stream, filename: str) -> tuple[list[Contact], list[str]]:
    """Read and clean a whole file. Returns the contacts and the names of ignored columns.

    Raises TableError when the file itself cannot be used.
    """
    rows = read_table(stream, filename)
    columns = find_columns(rows)
    contacts = clean(records_from_rows(rows, columns))
    if not contacts:
        raise TableError("The file has a header row but no contacts under it.")
    return contacts, columns.ignored


__all__ = [
    "ADJUSTED", "ERROR", "WARNING", "MAX_ROWS", "Contact", "Issue", "MonthDay", "TableError",
    "build_vcf", "clean", "find_columns", "load_contacts", "read_table", "records_from_rows",
]
