from datetime import date
from pathlib import Path

from flask import Flask, render_template

from vcfcore import MAX_FILES, MAX_ROWS

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
MAX_UPLOAD_MB = 3


def create_app(test_config: dict | None = None) -> Flask:
    # the "app factory" pattern: instead of one global app object, a function builds
    # and returns a fresh app. tests call it with their own config, and app.py calls
    # it once for the real server
    app = Flask(
        __name__,
        # files in public/ are served at the site root, e.g. /contacts_template.csv.
        # on vercel the cdn serves public/ before the request ever reaches flask;
        # locally flask serves them itself
        static_folder=str(PUBLIC_DIR),
        static_url_path="",
    )

    app.config.update(
        # flask rejects any request body bigger than this with a 413 error before our
        # code runs. vercel's own limit is 4.5 MB, so stay under it
        MAX_CONTENT_LENGTH=MAX_UPLOAD_MB * 1024 * 1024,
        # werkzeug (the library under flask that parses requests) refuses forms with
        # more than 1000 fields by default. the review table sends 8 fields per row
        MAX_FORM_PARTS=MAX_ROWS * 8 + 100,
    )
    if test_config:
        app.config.update(test_config)

    # a blueprint is a named group of routes. registering it attaches its routes to
    # this app; bigger apps split features into several blueprints
    from .routes import bp
    app.register_blueprint(bp)

    # a context processor adds variables to every template, so the upload page can
    # show the real limits no matter which route renders it
    @app.context_processor
    def page_values():
        return {
            "max_upload_mb": MAX_UPLOAD_MB,
            "max_rows": MAX_ROWS,
            "max_files": MAX_FILES,
            "birthday_examples": birthday_examples(date.today()),
        }

    # error handlers run when flask raises an http error instead of showing a bare error page
    @app.errorhandler(413)
    def too_large(error):
        message = f"That file is larger than {MAX_UPLOAD_MB} MB. Please upload a smaller file."
        return render_template("index.html", error=message), 413

    return app


def birthday_examples(day: date) -> list[str]:
    """Today's date in each birthday format we accept, a small easter egg on the upload page.

    The page script redoes this with the visitor's own date, since the server may be in another time zone.
    """
    year = 2004 if (day.month, day.day) == (2, 29) else 2003  # 2003 had no Feb 29
    return [
        f"{day:%B} {day.day}",
        f"{day.day}-{day:%b}",
        f"{day.month}/{day.day}",
        f"{day.month}/{day.day}/{year}",
    ]
