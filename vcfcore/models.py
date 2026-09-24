"""Plain data types shared by every step of the pipeline."""

from dataclasses import dataclass, field
from datetime import date

# issue levels, from most to least severe
ERROR = "error"      # blocks the download until fixed or the row is excluded
WARNING = "warning"  # kept as typed, but worth a look
ADJUSTED = "adjusted"  # we changed the value automatically


@dataclass(frozen=True)
class MonthDay:
    """A birthday without a year, e.g. a cell that only says "15-Mar"."""

    month: int
    day: int


@dataclass
class Issue:
    level: str
    message: str
    field: str | None = None


@dataclass
class Contact:
    """One spreadsheet row after cleaning.

    The *_text fields are what the user sees and edits: the cleaned value when we
    could parse it, otherwise their original input so nothing is lost.
    """

    row: int
    source: str = ""  # the file this contact came from
    first: str = ""
    last: str = ""
    phone: str = ""
    email: str = ""
    birthday_text: str = ""
    birthday: date | MonthDay | None = None
    include: bool = True
    duplicate_of: str | None = None  # where the earlier copy is, e.g. "row 4"
    issues: list[Issue] = field(default_factory=list)

    @property
    def where(self) -> str:
        """"row 4" for a spreadsheet, "card 4" for a .vcf file."""
        kind = "card" if self.source.lower().endswith(".vcf") else "row"
        return f"{kind} {self.row}"

    @property
    def full_name(self) -> str:
        return f"{self.first} {self.last}".strip()

    @property
    def has_errors(self) -> bool:
        return any(issue.level == ERROR for issue in self.issues)

    @property
    def status(self) -> str:
        """The most severe issue level on this row, or "ok"."""
        levels = {issue.level for issue in self.issues}
        for level in (ERROR, WARNING, ADJUSTED):
            if level in levels:
                return level
        return "ok"

    def add(self, level: str, message: str, field: str | None = None) -> None:
        self.issues.append(Issue(level, message, field))

    def field_level(self, name: str) -> str | None:
        """The most severe issue level attached to one field, used to highlight inputs."""
        levels = {issue.level for issue in self.issues if issue.field == name}
        for level in (ERROR, WARNING, ADJUSTED):
            if level in levels:
                return level
        return None


class TableError(Exception):
    """A problem with the whole file, such as an unreadable file or a missing Name or Phone Number column."""
