import re
from pathlib import PurePath

from flask import Blueprint, Response, render_template, request

from vcfcore import TableError, build_vcf, clean, load_files

# "converter" is the blueprint's name; url_for("converter.index") builds a link to index()
bp = Blueprint("converter", __name__)

# the review table posts these fields once per row, as parallel lists. "origin" is
# the file the row came from, which matters when several files are combined
ROW_FIELDS = ("row", "origin", "first", "last", "phone", "email", "birthday")
COMBINED_NAME = "combined contacts"


@bp.get("/")
def index():
    # render_template looks in webapp/templates/ and fills in the jinja placeholders
    return render_template("index.html")


@bp.post("/review")
def review():
    # the same url handles two cases: a fresh upload, or the review table sent back
    # after edits (the "re-check" button). either way the server validates everything
    # again, because anything coming from the browser can be changed by the user
    if "file" in request.files:
        # getlist returns every file sent under one input name; the advanced form's
        # <input multiple> sends several, the simple form sends one
        uploads = [f for f in request.files.getlist("file") if f.filename]
        advanced = request.form.get("mode") == "combine"
        if not uploads:
            return render_template("index.html", error="Choose a file to upload.", advanced=advanced), 400
        try:
            # each upload's stream is file-like, so it is read straight from memory;
            # nothing is saved to disk, which also suits vercel's read-only filesystem
            contacts, ignored = load_files((f.stream, f.filename) for f in uploads)
        except TableError as exc:
            # a status code other than 200 is returned by adding it after the body
            return render_template("index.html", error=str(exc), advanced=advanced), 422
        source = uploads[0].filename if len(uploads) == 1 else COMBINED_NAME
        return _render_review(contacts, source=source, ignored=ignored)

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
        file_count=len({c.source for c in contacts}),
        included_count=len(chosen),
        blocking_count=len(blocking),
        issue_count=sum(1 for c in contacts if c.issues),
        left_out_duplicates=sum(1 for c in contacts if c.duplicate_of and not c.include),
    )


def _records_from_form() -> list[dict]:
    # request.form.getlist returns every value sent under one input name, in page order
    columns = {name: request.form.getlist(name) for name in ROW_FIELDS}
    # unticked checkboxes are not sent at all, so each include box carries its row's
    # position as its value and we check membership instead of position
    included = set(request.form.getlist("include"))
    records = []
    for position, values in enumerate(zip(*(columns[name] for name in ROW_FIELDS))):
        record = dict(zip(ROW_FIELDS, values))
        if not record["row"].isdigit():
            continue
        record["source"] = record.pop("origin")
        record["include"] = str(position) in included
        records.append(record)
    return records


def _vcf_name(source: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", PurePath(source).stem).strip("-")
    return f"{stem or 'contacts'}.vcf"
