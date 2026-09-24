import csv
import io
from datetime import datetime

from openpyxl import Workbook


def make_xlsx(rows, number_formats=None) -> io.BytesIO:
    """Build an .xlsx in memory. number_formats maps (row, col), 1-based, to an Excel format."""
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    for (r, c), fmt in (number_formats or {}).items():
        sheet.cell(row=r, column=c).number_format = fmt
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def make_csv(rows, delimiter=",", encoding="utf-8") -> io.BytesIO:
    text = io.StringIO()
    csv.writer(text, delimiter=delimiter).writerows(rows)
    return io.BytesIO(text.getvalue().encode(encoding))


HEADER = ["Name", "Phone Number", "Email", "Instagram", "Birthday"]
SAMPLE = [
    HEADER,
    ["Kobe Bryant", "212-555-0101", "kobe@example.com", "kobe", datetime(2024, 8, 23)],
    ["Luka Doncic", "212-555-0102", "luka@example.com", "luka", datetime(2024, 2, 28)],
]
