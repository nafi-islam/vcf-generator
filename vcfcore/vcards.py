"""Read an existing .vcf file into the same records a spreadsheet row produces.

Only the fields this app manages are kept: name, one phone, one email, birthday.
Anything else on a card is listed in a note so the user knows it was not carried over.
"""

import re
from datetime import date

import vobject

from .models import ADJUSTED, MonthDay, TableError
from .reader import decode

# properties that carry no user data, so dropping them is not worth mentioning
SILENT = {"VERSION", "PRODID", "UID", "REV", "N", "FN", "TEL", "EMAIL", "BDAY", "CATEGORIES", "SOURCE", "KIND", "CLASS"}
DROPPED_NAMES = {
    "ADR": "address", "ORG": "organization", "TITLE": "job title", "ROLE": "job title", "NOTE": "note",
    "PHOTO": "photo", "URL": "website", "NICKNAME": "nickname", "X-SOCIALPROFILE": "social profile",
    "IMPP": "messaging account", "ANNIVERSARY": "anniversary", "X-ANNIVERSARY": "anniversary",
}
MOBILE_TYPES = {"cell", "mobile", "iphone"}


def read_vcards(data: bytes) -> list[dict]:
    text = decode(data)
    if "BEGIN:VCARD" not in text.upper():
        raise TableError("This .vcf file does not contain any contact cards.")
    try:
        cards = list(vobject.readComponents(text, ignoreUnreadable=True))
    except Exception as exc:  # vobject raises several unrelated error types on bad input
        raise TableError("This .vcf file could not be read. It may be damaged.") from exc
    return [_record(card, number) for number, card in enumerate(cards, start=1) if card.name == "VCARD"]


def _record(card, number: int) -> dict:
    notes = []
    first, last = _name(card)
    phones = [_clean_tel(child.value) for child in card.contents.get("tel", [])]
    phone = _pick(card.contents.get("tel", []), phones)
    emails = [str(child.value).strip() for child in card.contents.get("email", [])]
    email = _pick(card.contents.get("email", []), emails)

    if len([p for p in phones if p]) > 1:
        notes.append((ADJUSTED, f"Card has {len(phones)} phone numbers; kept {phone}.", "phone"))
    if len([e for e in emails if e]) > 1:
        notes.append((ADJUSTED, f"Card has {len(emails)} emails; kept {email}.", "email"))

    dropped = sorted({DROPPED_NAMES[key] for key in _property_names(card) if key in DROPPED_NAMES})
    if dropped:
        notes.append((ADJUSTED, f"Not carried over from this card: {', '.join(dropped)}.", None))

    return {
        "row": number,
        "first": first,
        "last": last,
        "phone": phone,
        "email": email,
        "birthday": _birthday(card),
        "include": True,
        "notes": notes,
    }


def _name(card) -> tuple[str, str]:
    name = card.contents.get("n", [None])[0]
    if name is not None and hasattr(name.value, "given"):
        value = name.value
        first = " ".join(_join(part) for part in (value.given, value.additional) if _join(part))
        last = _join(value.family)
        if first or last:
            return first, last
    full = str(card.contents["fn"][0].value).strip() if "fn" in card.contents else ""
    parts = full.split()
    return (parts[0] if parts else ""), " ".join(parts[1:])


def _join(part) -> str:
    if isinstance(part, (list, tuple)):
        return " ".join(str(p).strip() for p in part if str(p).strip())
    return str(part or "").strip()


def _types(child) -> set[str]:
    # vcard 3.0 writes TYPE=CELL; vcard 2.1 often writes a bare ;CELL
    values = child.params.get("TYPE", []) + list(getattr(child, "singletonparams", []))
    return {t.lower() for value in values for t in str(value).split(",")}


def _pick(children, values: list[str]) -> str:
    """Prefer a mobile entry, then one marked preferred, then the first."""
    pairs = [(child, value) for child, value in zip(children, values) if value]
    for wanted in (MOBILE_TYPES, {"pref"}):
        for child, value in pairs:
            if _types(child) & wanted:
                return value
    return pairs[0][1] if pairs else ""


def _clean_tel(value) -> str:
    return re.sub(r"^tel:", "", str(value).strip(), flags=re.IGNORECASE)  # vcard 4.0 uses tel: uris


def _birthday(card) -> date | MonthDay | str:
    if "bday" not in card.contents:
        return ""
    child = card.contents["bday"][0]
    text = str(child.value).strip()
    digits = re.sub(r"[^0-9-]", "", text.split("T")[0])

    if match := re.fullmatch(r"--(\d{2})-?(\d{2})", digits):  # year-less form: --0315 or --03-15
        return _month_day(int(match[1]), int(match[2]), text)
    if match := re.fullmatch(r"(\d{4})-?(\d{2})-?(\d{2})", digits):
        year, month, day = (int(g) for g in match.groups())
        if child.params.get("X-APPLE-OMIT-YEAR") or year <= 1604:  # placeholder year, not a real one
            return _month_day(month, day, text)
        try:
            return date(year, month, day)
        except ValueError:
            return text
    return text  # left for the normal birthday check to report


def _month_day(month: int, day: int, text: str) -> MonthDay | str:
    try:
        date(2000, month, day)  # validates the day, 2000 is a leap year
    except ValueError:
        return text
    return MonthDay(month, day)


def _property_names(card) -> set[str]:
    return {child.name.upper() for child in card.getChildren()} - SILENT
