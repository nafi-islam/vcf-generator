import re
from pathlib import PurePath

from flask import Blueprint, Response, render_template, request

from vcfcore import TableError, build_vcf, clean, load_contacts

# "converter" is the blueprint's name; url_for("converter.index") builds a link to index()
bp = Blueprint("converter", __name__)

# the review table posts these fields once per row, as parallel lists
ROW_FIELDS = ("row", "first", "last", "phone", "email", "birthday")


@bp.get("/")
def index():
    # render_template looks in webapp/templates/ and fills in the jinja placeholders
    return render_template("index.html")


@bp.post("/review")
def review():
    # the same url handles two cases: a fresh upload, or the review table sent back
    # after edits (the "re-check" button). either way the server validates everything
    # again, because anything coming from the browser can be changed by the user
    upload = request.files.get("file")  # request.files holds uploaded files by input name
    if upload is not None:
        if not upload.filename:
            return render_template("index.html", error="Choose a file to upload."), 400
        try:
            # upload.stream is file-like, so it is read straight from memory; nothing
            # is saved to disk, which also suits vercel's read-only filesystem
            contacts, ignored = load_contacts(upload.stream, upload.filename)
        except TableError as exc:
            # a status code other than 200 is returned by adding it after the body
            return render_template("index.html", error=str(exc)), 422
        return _render_review(contacts, source=upload.filename, ignored=ignored)

    contacts = clean(_records_from_form())
    return _render_review(contacts, source=request.form.get("source", ""), ignored=request.form.getlist("ignored"))


@bp.post("/download")
def download():
    contacts = clean(_records_from_form())
    source = request.form.get("source", "")
    chosen = [c for c in contacts if c.include]

    if any(c.has_errors for c in chosen) or not chosen:
        # never trust the disabled download button alone; check again here
        return _render_review(contacts, source=source, ignored=request.form.getlist("ignored")), 422

    # returning a Response lets us set headers ourselves. content-disposition:
    # attachment tells the browser to save the body as a file instead of showing it
    return Response(
        build_vcf(chosen),
        mimetype="text/vcard",
        headers={"Content-Disposition": f'attachment; filename="{_vcf_name(source)}"'},
    )


def _render_review(contacts, source: str, ignored: list[str]):
    chosen = [c for c in contacts if c.include]
    blocking = [c for c in chosen if c.has_errors]
    return render_template(
        "review.html",
        contacts=contacts,
        source=source,
        ignored=ignored,
        included_count=len(chosen),
        blocking_count=len(blocking),
        issue_count=sum(1 for c in contacts if c.issues),
    )


def _records_from_form() -> list[dict]:
    # request.form.getlist returns every value sent under one input name, in page order
    columns = {name: request.form.getlist(name) for name in ROW_FIELDS}
    # unticked checkboxes are not sent at all, so the include boxes carry the row
    # number as their value and we check membership instead of position
    included = set(request.form.getlist("include"))
    records = []
    for values in zip(*(columns[name] for name in ROW_FIELDS)):
        record = dict(zip(ROW_FIELDS, values))
        if not record["row"].isdigit():
            continue
        record["include"] = record["row"] in included
        records.append(record)
    return records


def _vcf_name(source: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", PurePath(source).stem).strip("-")
    return f"{stem or 'contacts'}.vcf"
