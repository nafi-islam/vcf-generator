"""Clean each field and record what we found, row by row.

The same checks run on a freshly uploaded file and on the edited table the user
sends back from the review page, so the rules live in exactly one place.
"""

import re
from datetime import date, datetime

import phonenumbers

from .columns import ColumnMap
from .models import ADJUSTED, ERROR, WARNING, Contact, MonthDay
from .reader import Rows

DEFAULT_REGION = "US"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

FULL_DATE_FORMATS = [
    "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%b %d, %Y", "%B %d, %Y",
    "%b %d %Y", "%B %d %Y", "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %B %Y",
]
# formats without a year; parsed together with a leap year so Feb 29 works
MONTH_DAY_FORMATS = ["%d-%b", "%d-%B", "%b %d", "%B %d", "%d %b", "%d %B", "%m/%d", "%m-%d", "--%m-%d"]

FIELDS = ("first", "last", "phone", "email", "birthday")


def records_from_rows(rows: Rows, columns: ColumnMap) -> list[dict]:
    """Pull the mapped fields out of each data row, splitting a single Name column like the original script."""
    records = []
    for number, cells in rows:
        if number <= columns.header_row:
            continue

        def get(name):
            position = columns.index.get(name)
            if position is None or position >= len(cells):
                return None
            return cells[position]

        if "first" in columns.index or "last" in columns.index:
            first, last = _text(get("first")), _text(get("last"))
        else:
            # first word is the given name, the rest is the family name
            parts = _text(get("name")).split()
            first = parts[0] if parts else ""
            last = " ".join(parts[1:])

        record = {
            "row": number,
            "first": first,
            "last": last,
            "phone": get("phone"),
            "email": get("email"),
            "birthday": get("birthday"),
            "include": True,
        }
        if any(_filled(record[name]) for name in FIELDS):  # skip rows that only fill ignored columns
            records.append(record)
    return records


def clean(records: list[dict]) -> list[Contact]:
    contacts = [_clean_one(record) for record in records]
    _flag_duplicates(contacts)
    return contacts


def _clean_one(record: dict) -> Contact:
    contact = Contact(
        row=int(record["row"]),
        first=" ".join(_text(record.get("first")).split()),
        last=" ".join(_text(record.get("last")).split()),
        include=bool(record.get("include", True)),
    )

    if not contact.full_name:
        contact.add(ERROR, "Name is blank.", "first")

    contact.phone = _clean_phone(record.get("phone"), contact)
    if not contact.phone:
        contact.add(ERROR, "Phone number is blank.", "phone")

    contact.email = _clean_email(record.get("email"), contact)
    contact.birthday, contact.birthday_text = _clean_birthday(record.get("birthday"), contact)
    return contact


def _clean_phone(value, contact: Contact) -> str:
    raw = _text(value)
    if not raw:
        return ""
    if re.fullmatch(r"\d+\.0", raw):
        raw = raw[:-2]  # a phone saved as a number in the sheet
        contact.add(ADJUSTED, "Phone was stored as a number; the trailing .0 was removed.", "phone")
    try:
        number = phonenumbers.parse(raw, DEFAULT_REGION)
    except phonenumbers.NumberParseException:
        number = None
    if number is None or not phonenumbers.is_valid_number(number):
        contact.add(WARNING, f"Phone '{raw}' does not look like a valid number; kept as typed.", "phone")
        return raw
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)


def _clean_email(value, contact: Contact) -> str:
    raw = _text(value)
    if not raw:
        return ""
    if not EMAIL_RE.match(raw):
        contact.add(WARNING, f"Email '{raw}' does not look valid; kept as typed.", "email")
        return raw
    local, domain = raw.rsplit("@", 1)
    return f"{local}@{domain.lower()}"


def _clean_birthday(value, contact: Contact) -> tuple[date | MonthDay | None, str]:
    parsed = value if isinstance(value, (date, MonthDay)) else parse_birthday(_text(value))
    if parsed is None:
        raw = _text(value)
        if raw:
            contact.add(ERROR, f"Birthday '{raw}' was not recognized. Use a format like Mar 15 or 03/15/2002, or clear it.", "birthday")
        return None, raw
    if isinstance(parsed, date) and parsed > date.today():
        contact.add(ERROR, f"Birthday '{format_birthday(parsed)}' is in the future.", "birthday")
        return None, format_birthday(parsed)
    return parsed, format_birthday(parsed)


def parse_birthday(text: str) -> date | MonthDay | None:
    text = " ".join(text.replace(",", ", ").split()).replace(" ,", ",")
    text = re.sub(r"[ T]00:00(:00)?$", "", text)  # "2002-03-15 00:00:00" from some exports
    if not text:
        return None
    for fmt in FULL_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    for fmt in MONTH_DAY_FORMATS:
        try:
            parsed = datetime.strptime(f"{text} 2000", f"{fmt} %Y")
            return MonthDay(parsed.month, parsed.day)
        except ValueError:
            pass
    return None


def format_birthday(value: date | MonthDay) -> str:
    """How a birthday is shown and edited: "Mar 15" or "Mar 15, 2002"."""
    month = date(2000, value.month, 1).strftime("%b")
    if isinstance(value, MonthDay):
        return f"{month} {value.day}"
    return f"{month} {value.day}, {value.year}"


def _flag_duplicates(contacts: list[Contact]) -> None:
    seen: dict[tuple[str, str], int] = {}
    for contact in contacts:
        keys = []
        if contact.phone:
            keys.append(("phone", re.sub(r"\D", "", contact.phone)))
        if contact.email:
            keys.append(("email", contact.email.lower()))
        for kind, key in keys:
            if (kind, key) in seen:
                contact.add(WARNING, f"Same {kind} as row {seen[(kind, key)]}; this may be a duplicate.", kind)
            else:
                seen[(kind, key)] = contact.row


def _filled(value) -> bool:
    return isinstance(value, (date, MonthDay)) or bool(_text(value))


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()
