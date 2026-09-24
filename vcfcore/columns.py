"""Find the header row and work out which column holds which field."""

import re
from dataclasses import dataclass, field

from .models import TableError
from .reader import Rows

# normalized header text -> field; headers are lowercased with punctuation and spaces removed
ALIASES = {
    "name": {"name", "fullname", "contactname", "contact"},
    "first": {"first", "firstname", "givenname", "fname"},
    "last": {"last", "lastname", "surname", "familyname", "lname"},
    "phone": {
        "phone", "phonenumber", "phoneno", "phonenum", "mobile", "mobilenumber", "mobilephone",
        "cell", "cellphone", "cellnumber", "telephone", "tel", "number",
    },
    "email": {"email", "emailaddress", "mail"},
    "birthday": {"birthday", "bday", "birthdate", "dateofbirth", "dob"},
}

HEADER_SEARCH_ROWS = 10  # a title or blank rows above the header are allowed


@dataclass
class ColumnMap:
    header_row: int
    index: dict[str, int]  # field -> column position
    ignored: list[str] = field(default_factory=list)


def normalize_header(text) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())


def find_columns(rows: Rows) -> ColumnMap:
    """Pick the first row that looks like a header and map its columns to fields.

    Name and Phone Number are required columns.
    """
    for number, cells in rows[:HEADER_SEARCH_ROWS]:
        mapping = _map(number, cells)
        if "name" in mapping.index or "first" in mapping.index:
            if "phone" not in mapping.index:
                raise TableError(f"Could not find a Phone Number column. {_found(cells)}")
            return mapping

    raise TableError(f"Could not find a Name column (or First Name and Last Name columns). {_found(rows[0][1])}")


def _found(cells) -> str:
    names = [str(c).strip() for c in cells if str(c or "").strip()]
    return f"Columns found: {', '.join(names) or 'none'}. Rename the column or start from the template."


def _map(number: int, cells) -> ColumnMap:
    index: dict[str, int] = {}
    ignored = []
    for position, cell in enumerate(cells):
        key = normalize_header(cell)
        if not key:
            continue
        target = next((name for name, aliases in ALIASES.items() if key in aliases), None)
        if target and target not in index:  # a repeated column keeps the first one
            index[target] = position
        else:
            ignored.append(str(cell).strip())
    return ColumnMap(header_row=number, index=index, ignored=ignored)
