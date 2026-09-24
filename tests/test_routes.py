import io
from datetime import date, timedelta

import pytest

from vcfcore import MonthDay
from vcfcore.validate import parse_birthday
from webapp import birthday_examples, create_app

from .helpers import SAMPLE, make_csv, make_xlsx


@pytest.fixture
def client():
    # the test client sends fake requests straight into the app, no server needed
    app = create_app({"TESTING": True})
    return app.test_client()


def upload(client, data, filename):
    return client.post("/review", data={"file": (data, filename)}, content_type="multipart/form-data")


def table_form(rows, include=None, source="club.xlsx"):
    """Build the fields the review page posts back.

    rows are (row, first, last, phone, email, birthday); include lists row positions, default all.
    """
    form = {name: [] for name in ("row", "first", "last", "phone", "email", "birthday")}
    for row in rows:
        for name, value in zip(form, row):
            form[name].append(str(value))
    form["origin"] = [source] * len(rows)
    form["include"] = [str(i) for i in (range(len(rows)) if include is None else include)]
    form["source"] = source
    return form


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'enctype="multipart/form-data"' in response.data
    assert b'href="https://github.com/nafi-islam/vcf-generator"' in response.data


def test_templates_are_served(client):
    assert client.get("/contacts_template.csv").status_code == 200
    assert client.get("/contacts_template.xlsx").status_code == 200
    assert client.get("/favicon.svg").status_code == 200
    assert b'rel="icon" href="/favicon.svg"' in client.get("/").data


def test_upload_shows_every_contact_before_converting(client):
    response = upload(client, make_xlsx(SAMPLE), "club.xlsx")
    assert response.status_code == 200
    assert b"Review Contacts" in response.data
    assert b'<li><a href="/">Home</a></li>' in response.data
    assert b'value="Kobe"' in response.data and b'value="Luka"' in response.data
    assert b"Ignored columns: Instagram" in response.data
    assert b"disabled" not in response.data.split(b'id="download"')[1].split(b">")[0]


def test_file_problem_returns_to_upload_page(client):
    response = upload(client, make_csv([["Phone"], ["212-555-0101"]]), "c.csv")
    assert response.status_code == 422
    assert b"Could not find a Name column" in response.data


def test_missing_file(client):
    response = client.post("/review", data={"file": (b"", "")}, content_type="multipart/form-data")
    assert response.status_code == 400


def test_upload_too_large(client):
    client.application.config["MAX_CONTENT_LENGTH"] = 100
    response = upload(client, make_csv([["Name"]] + [["x" * 50]] * 10), "c.csv")
    assert response.status_code == 413
    assert b"larger than" in response.data


def test_row_errors_block_download_button(client):
    response = upload(client, make_csv([["Name", "Phone"], ["", "212-555-0101"]]), "c.csv")
    assert b"need" in response.data and b"fixing before download" in response.data
    assert b"disabled" in response.data.split(b'id="download"')[1].split(b">")[0]


def test_recheck_after_fixing_a_row(client):
    form = table_form([(2, "Sam", "Lee", "2125550101", "", "Mar 15")])
    response = client.post("/review", data=form)
    assert response.status_code == 200
    assert b"fixing before download" not in response.data
    assert b'value="+1 212-555-0101"' in response.data


def test_download_refuses_rows_with_errors(client):
    form = table_form([(2, "", "", "2125550101", "", ""), (3, "Sam", "Lee", "2125550102", "", "")])
    response = client.post("/download", data=form)
    assert response.status_code == 422
    assert response.mimetype == "text/html"


def test_download_skips_rows_the_user_unticked(client):
    form = table_form(
        [(2, "", "", "2125550101", "", ""), (3, "Sam", "Lee", "2125550102", "", "Mar 15")],
        include=[1],
        source="Book Club (Fall).xlsx",
    )
    response = client.post("/download", data=form)
    assert response.status_code == 200
    assert response.mimetype == "text/vcard"
    assert response.headers["Content-Disposition"] == 'attachment; filename="Book-Club-Fall.vcf"'
    body = response.get_data(as_text=True)
    assert body.count("BEGIN:VCARD") == 1
    assert "FN:Sam Lee" in body


def test_download_with_nothing_selected(client):
    form = table_form([(2, "Sam", "Lee", "", "", "")], include=[])
    assert client.post("/download", data=form).status_code == 422


def test_largest_allowed_table_fits_form_limits(client):
    rows = [(i, "Person", str(i), f"212555{i:04d}", "", "") for i in range(2, 2002)]
    response = client.post("/download", data=table_form(rows))
    assert response.status_code == 200
    assert response.get_data(as_text=True).count("BEGIN:VCARD") == 2000


def test_birthday_examples_are_always_accepted_formats():
    day = date(2024, 1, 1)  # a leap year, so Feb 29 is covered
    while day.year == 2024:
        examples = birthday_examples(day)
        for text in examples[:3]:
            assert parse_birthday(text) == MonthDay(day.month, day.day), text
        assert parse_birthday(examples[3]).timetuple()[1:3] == (day.month, day.day)
        day += timedelta(days=1)
    assert birthday_examples(date(2026, 9, 24)) == ["September 24", "24-Sep", "9/24", "9/24/2003"]
    assert birthday_examples(date(2024, 2, 29))[3] == "2/29/2004"


def test_upload_page_shows_todays_birthday_examples(client):
    page = client.get("/").get_data(as_text=True)
    for example in birthday_examples(date.today()):
        assert f">{example}</code>" in page


def test_combine_several_files(client):
    from .helpers import VCARDS
    sheet = make_csv([["Name", "Phone"], ["Jordan Rivera", "212-555-0101"], ["Taylor Brooks", "212-555-0106"]])
    response = client.post("/review", data={
        "mode": "combine",
        "file": [(sheet, "club.csv"), (io.BytesIO(VCARDS.encode()), "phone.vcf")],
    }, content_type="multipart/form-data")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "6 contacts found in 2 files" in page
    assert "<th>Source</th>" in page
    assert "1 likely duplicate</strong>" in page
    assert 'name="origin" value="phone.vcf"' in page


def test_combined_download_keeps_file_origins_and_name(client):
    form = table_form([(2, "Sam", "Lee", "2125550101", "", ""), (2, "Ana", "Diaz", "2125550102", "", "")], source="combined contacts")
    form["origin"] = ["a.csv", "b.vcf"]
    response = client.post("/download", data=form)
    assert response.headers["Content-Disposition"] == 'attachment; filename="combined-contacts.vcf"'
    assert response.get_data(as_text=True).count("BEGIN:VCARD") == 2


def test_combine_error_reopens_advanced_section(client):
    response = client.post("/review", data={
        "mode": "combine", "file": [(make_csv([["Name"], ["Sam"]]), "a.csv"), (make_csv([["Name"], ["Ana"]]), "b.csv")],
    }, content_type="multipart/form-data")
    assert response.status_code == 422
    assert b"a.csv: Could not find a Phone Number column" in response.data
    assert b"<details open>" in response.data


def test_analytics_script_only_on_vercel(client, monkeypatch):
    assert b"/_vercel/insights/script.js" not in client.get("/").data
    monkeypatch.setenv("VERCEL", "1")
    assert b"/_vercel/insights/script.js" in client.get("/").data
