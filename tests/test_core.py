import io
from datetime import date

import pytest

from vcfcore import ERROR, WARNING, ADJUSTED, MonthDay, TableError, build_vcf, clean, load_contacts
from vcfcore.validate import parse_birthday

from .helpers import HEADER, SAMPLE, make_csv, make_xlsx


# reading files

def test_xlsx_matches_original_script_behavior():
    contacts, ignored = load_contacts(make_xlsx(SAMPLE, {(2, 5): "d-mmm", (3, 5): "d-mmm"}), "contacts.xlsx")
    kobe = contacts[0]
    assert (kobe.row, kobe.first, kobe.last) == (2, "Kobe", "Bryant")
    assert kobe.phone == "+1 212-555-0101"
    assert kobe.birthday == MonthDay(8, 23)  # the year Excel added is not real
    assert ignored == ["Instagram"]
    assert all(c.status == "ok" for c in contacts)


def test_xlsx_date_with_visible_year_keeps_year():
    contacts, _ = load_contacts(make_xlsx(SAMPLE, {(2, 5): "yyyy-mm-dd"}), "c.xlsx")
    assert contacts[0].birthday == date(2024, 8, 23)


def test_numeric_phone_cell_is_not_turned_into_a_float():
    rows = [HEADER, ["Sam Lee", 2125550103, "", "", ""], ["Ana Diaz", 2125550104.0, "", "", ""]]
    contacts, _ = load_contacts(make_xlsx(rows), "c.xlsx")
    assert [c.phone for c in contacts] == ["+1 212-555-0103", "+1 212-555-0104"]


def test_csv_with_excel_bom_and_semicolons():
    data = make_csv([HEADER, ["Sam Lee", "212-555-0103", "sam@example.com", "", "15-Mar"]], delimiter=";", encoding="utf-8-sig")
    contacts, _ = load_contacts(data, "c.csv")
    assert contacts[0].first == "Sam"
    assert contacts[0].birthday == MonthDay(3, 15)


def test_csv_in_windows_encoding():
    data = make_csv([["Name"], ["José Núñez"]], encoding="cp1252")
    contacts, _ = load_contacts(data, "c.csv")
    assert contacts[0].full_name == "José Núñez"


def test_title_row_above_header_and_header_aliases():
    rows = [["Book Club 2026"], [], ["First Name", "Last Name", "Mobile", "E-mail", "DOB"], ["Sam", "Lee", "2125550103", "sam@example.com", "03/15/2002"]]
    contacts, _ = load_contacts(make_csv(rows), "c.csv")
    sam = contacts[0]
    assert (sam.row, sam.first, sam.last, sam.birthday) == (4, "Sam", "Lee", date(2002, 3, 15))


@pytest.mark.parametrize("filename, data, message", [
    ("c.txt", b"x", "Please upload a .csv or .xlsx"),
    ("c.xls", b"x", "Old .xls files"),
    ("c.csv", b"", "empty"),
    ("c.xlsx", b"not a zip", "could not be opened"),
    ("c.csv", b"Phone,Email\n212-555-0103,a@b.co\n", "Could not find a Name column"),
    ("c.csv", b"Name,Phone\n", "no contacts"),
])
def test_file_level_errors(filename, data, message):
    with pytest.raises(TableError, match=message):
        load_contacts(io.BytesIO(data), filename)


def test_row_limit():
    rows = [["Name"]] + [[f"Person {i}"] for i in range(2001)]
    with pytest.raises(TableError, match="more than 2000"):
        load_contacts(make_csv(rows), "c.csv")


# cleaning rows

def record(**overrides):
    base = {"row": 2, "first": "Sam", "last": "Lee", "phone": "", "email": "", "birthday": "", "include": True}
    return base | overrides


def levels(contact):
    return [(issue.level, issue.field) for issue in contact.issues]


def test_blank_name_is_an_error_but_data_is_kept():
    [contact] = clean([record(first="", last="", phone="212-555-0103")])
    assert contact.has_errors
    assert contact.phone == "+1 212-555-0103"


def test_invalid_phone_and_email_are_warnings_kept_as_typed():
    [contact] = clean([record(phone="555-01", email="sam@@example")])
    assert levels(contact) == [(WARNING, "phone"), (WARNING, "email")]
    assert (contact.phone, contact.email) == ("555-01", "sam@@example")


def test_float_phone_is_adjusted():
    [contact] = clean([record(phone="2125550103.0")])
    assert levels(contact) == [(ADJUSTED, "phone")]
    assert contact.phone == "+1 212-555-0103"


def test_unrecognized_birthday_is_an_error_that_keeps_the_text():
    [contact] = clean([record(phone="212-555-0103", birthday="sometime in march")])
    assert levels(contact) == [(ERROR, "birthday")]
    assert contact.birthday_text == "sometime in march"


def test_name_only_contact_gets_a_warning():
    [contact] = clean([record()])
    assert levels(contact) == [(WARNING, None)]


def test_duplicates_are_flagged_on_the_later_row():
    first, second = clean([record(phone="212-555-0103"), record(row=3, first="Samuel", phone="(212) 555-0103")])
    assert first.issues == []
    assert "row 2" in second.issues[0].message


def test_edited_values_round_trip_without_new_issues():
    [contact] = clean([record(phone="2125550103.0", birthday="15-Mar")])
    [again] = clean([record(phone=contact.phone, birthday=contact.birthday_text)])
    assert again.issues == []
    assert (again.phone, again.birthday) == (contact.phone, contact.birthday)


@pytest.mark.parametrize("text, expected", [
    ("15-Mar", MonthDay(3, 15)),
    ("Mar 15", MonthDay(3, 15)),
    ("march 15", MonthDay(3, 15)),
    ("3/15", MonthDay(3, 15)),
    ("29-Feb", MonthDay(2, 29)),
    ("2002-03-15", date(2002, 3, 15)),
    ("03/15/2002", date(2002, 3, 15)),
    ("Mar 15, 2002", date(2002, 3, 15)),
    ("Mar 15,2002", date(2002, 3, 15)),
    ("2002-03-15 00:00:00", date(2002, 3, 15)),
    ("15/15", None),
    ("tomorrow", None),
])
def test_parse_birthday(text, expected):
    assert parse_birthday(text) == expected


# building vcards

def test_build_vcf():
    contacts = clean([
        record(phone="212-555-0103", email="Sam@Example.COM", birthday="Mar 15"),
        record(row=3, first="Ana", last="de la Cruz", birthday="2002-03-15"),
    ])
    text = build_vcf(contacts)
    assert text.count("BEGIN:VCARD") == 2
    assert "N:Lee;Sam;;;" in text
    assert "TEL;TYPE=CELL:+1 212-555-0103" in text
    assert "EMAIL;TYPE=INTERNET:Sam@example.com" in text
    assert "BDAY;X-APPLE-OMIT-YEAR=1604:1604-03-15" in text
    assert "N:de la Cruz;Ana;;;" in text
    assert "BDAY:2002-03-15" in text
