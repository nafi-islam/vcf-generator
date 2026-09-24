import io
from datetime import date

import pytest

from vcfcore import ADJUSTED, MonthDay, TableError, build_vcf, load_files

from .helpers import HEADER, VCARDS, make_csv, make_xlsx


def vcf_file(text=VCARDS, name="phone.vcf"):
    return io.BytesIO(text.encode("utf-8")), name


def test_reads_cards_from_common_phone_exports():
    contacts, _ = load_files([vcf_file()])
    jordan, avery, jose, sam = contacts
    assert (jordan.first, jordan.last, jordan.phone, jordan.email) == ("Jordan Lee", "Rivera", "+1 212-555-0101", "jordan@example.com")
    assert jordan.birthday == MonthDay(3, 15)  # apple's hidden-year birthday
    assert avery.birthday == MonthDay(7, 24)  # google's --0724
    assert (jose.first, jose.last, jose.phone, jose.birthday) == ("José", "Núñez", "+1 212-555-0103", date(2002, 3, 15))
    assert (sam.first, sam.last, sam.phone) == ("Sam", "Patel", "+1 212-555-0104")  # name from FN, tel: uri
    assert [c.where for c in contacts] == ["card 1", "card 2", "card 3", "card 4"]


def test_notes_what_a_card_loses():
    [jordan, *_] = load_files([vcf_file()])[0]
    notes = [i.message for i in jordan.issues if i.level == ADJUSTED]
    assert "Card has 2 phone numbers; kept (212) 555-0101." in notes
    assert "Not carried over from this card: address, note, organization." in notes


def test_round_trip_through_our_own_output():
    contacts, _ = load_files([vcf_file()])
    again, _ = load_files([vcf_file(build_vcf(contacts), "ours.vcf")])
    assert [(c.full_name, c.phone, c.birthday) for c in again] == [(c.full_name, c.phone, c.birthday) for c in contacts]
    assert all(not c.issues for c in again)


def test_combining_spreadsheets_and_cards_leaves_out_duplicates():
    sheet = make_xlsx([HEADER, ["Jordan Rivera", "212-555-0101", "", "", ""], ["Riley Kim", "212-555-0105", "", "", ""]])
    csv = make_csv([["Name", "Phone"], ["Riley K", "(212) 555-0105"], ["Taylor Brooks", "212-555-0106"]])
    contacts, _ = load_files([(sheet, "club.xlsx"), (csv, "new members.csv"), vcf_file()])

    assert len(contacts) == 8
    duplicates = [c for c in contacts if c.duplicate_of]
    assert [(c.source, c.where, c.duplicate_of, c.include) for c in duplicates] == [
        ("new members.csv", "row 2", "club.xlsx row 3", False),
        ("phone.vcf", "card 1", "club.xlsx row 2", False),
    ]
    assert sum(c.include for c in contacts) == 6


def test_error_names_the_file_when_combining():
    bad = make_csv([["Name"], ["Sam Lee"]])
    with pytest.raises(TableError, match="^members.csv: Could not find a Phone Number column"):
        load_files([vcf_file(), (bad, "members.csv")])


@pytest.mark.parametrize("text, message", [
    ("hello", "does not contain any contact cards"),
    ("", "does not contain any contact cards"),
])
def test_unusable_vcf(text, message):
    with pytest.raises(TableError, match=message):
        load_files([vcf_file(text)])


def test_file_and_row_limits():
    with pytest.raises(TableError, match="at most 10 files"):
        load_files([vcf_file() for _ in range(11)])
    rows = [["Name", "Phone"]] + [[f"P {i}", f"212555{i:04d}"] for i in range(1500)]
    with pytest.raises(TableError, match="Together the files have more than 2000"):
        load_files([(make_csv(rows), "a.csv"), (make_csv(rows), "b.csv")])
