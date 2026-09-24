import pytest

from webapp import create_app

from .helpers import SAMPLE, make_csv, make_xlsx


@pytest.fixture
def client():
    # the test client sends fake requests straight into the app, no server needed
    app = create_app({"TESTING": True})
    return app.test_client()


def upload(client, data, filename):
    return client.post("/review", data={"file": (data, filename)}, content_type="multipart/form-data")


def table_form(rows, include=None, source="club.xlsx"):
    """Build the fields the review page posts back. rows are (row, first, last, phone, email, birthday)."""
    form = {name: [] for name in ("row", "first", "last", "phone", "email", "birthday")}
    for row in rows:
        for name, value in zip(form, row):
            form[name].append(str(value))
    form["include"] = [str(r[0]) for r in rows] if include is None else [str(r) for r in include]
    form["source"] = source
    return form


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'enctype="multipart/form-data"' in response.data


def test_templates_are_served(client):
    assert client.get("/contacts_template.csv").status_code == 200
    assert client.get("/contacts_template.xlsx").status_code == 200


def test_upload_shows_every_contact_before_converting(client):
    response = upload(client, make_xlsx(SAMPLE), "club.xlsx")
    assert response.status_code == 200
    assert b"Review contacts" in response.data
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
        include=[3],
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
