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


# cards as exported by an iPhone, Google Contacts, an old phone (vcard 2.1), and vcard 4.0
VCARDS = """BEGIN:VCARD
VERSION:3.0
PRODID:-//Apple Inc.//iPhone OS 17.0//EN
N:Rivera;Jordan;Lee;;
FN:Jordan Lee Rivera
ORG:Acme;
TEL;type=HOME;type=VOICE:(212) 555-0199
TEL;type=CELL;type=VOICE;type=pref:(212) 555-0101
EMAIL;type=INTERNET;type=HOME;type=pref:jordan@example.com
item1.ADR;type=HOME:;;1 Main St;NYC;NY;10001;USA
NOTE:met at club
BDAY;X-APPLE-OMIT-YEAR=1604:1604-03-15
END:VCARD
BEGIN:VCARD
VERSION:3.0
FN:Avery Chen
N:Chen;Avery;;;
TEL;TYPE=CELL:+1 212-555-0102
BDAY:--0724
END:VCARD
BEGIN:VCARD
VERSION:2.1
N;CHARSET=UTF-8:Núñez;José;;;
TEL;CELL:2125550103
BDAY:20020315
END:VCARD
BEGIN:VCARD
VERSION:4.0
FN:Sam Patel
TEL;VALUE=uri;TYPE=cell:tel:+1-212-555-0104
END:VCARD
"""
