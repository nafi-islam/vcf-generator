# Contact Card Generator 📞

## Inspiration

Every semester, in multiple of my student organizations, we are constantly recruiting new members to be a part of great projects. One problem that new members run into is that they have no idea who is who in our org. group chat. It's a major hassle to save each contact, one by one.

## What It Does

Upload a spreadsheet (`.xlsx` or `.csv`) of contacts and get back one `.vcf` file that anyone can open on their phone to save every contact at once.

Before anything is converted, the app shows every contact in a review table:

- **Problems that block the download** (a blank name or phone number, a birthday it cannot read) are highlighted. Fix them right in the table and click Re-check, or untick the row to leave it out. Nothing is dropped unless you choose to drop it.
- **Warnings** (a phone that does not look valid, a possible duplicate) are shown but kept as typed.
- **Automatic fixes** (a phone Excel stored as `2125550123.0`) are noted.

Files are read in memory and never stored.

### Combining files

Under **Advanced** on the upload page, you can combine up to 10 files at once, mixing spreadsheets and existing `.vcf` files (for example, last semester's contact file plus this semester's sign-up sheet). Everything lands in one review table with each row's source file shown. A contact with the same phone or email as an earlier one starts out unticked as a likely duplicate, so the combined file has no repeats unless you choose to keep them.

From `.vcf` files, only the name, phone, email, and birthday are kept. When a card has more (an address, a photo, a second phone number), the review table notes what was not carried over.

### What the sheet needs

| Column | Notes |
| --- | --- |
| `Name` (required) | Or separate `First Name` and `Last Name` columns. A single name is split into first word and the rest, like the original script. |
| `Phone Number` (required) | Any format. Numbers without a country code are treated as US. |
| `Email` | |
| `Birthday` | With or without a year: `15-Mar`, `Mar 15`, `03/15/2002`, or an Excel date. |

Similar headers such as `Mobile`, `E-mail`, or `DOB` work too, and a title row above the header is fine. Other columns (Instagram, Fun Facts) are ignored. Templates are in [`public/`](public/).

## Development Thought Process

Whenever I hear the term automate, I immediately jump to Python. The first version was a pandas script. Turning it into a web app, the conversion logic moved into a small package with no web code in it, and a Flask app sits on top:

```
vcfcore/            conversion logic, no Flask imports
  reader.py         .csv/.xlsx -> rows of cells (handles encodings, Excel dates, numeric phones)
  columns.py        finds the header row and matches column names
  validate.py       cleans each field and records per-row issues
  vcards.py         reads existing .vcf files (iPhone, Google, vCard 2.1-4.0)
  builder.py        writes vCard 3.0 with vobject (the original script's loop)
webapp/             Flask app
  __init__.py       create_app(): config and error handlers
  routes.py         /, /review, /download
  templates/        Jinja pages, styled with Pico.css
public/             static files (spreadsheet templates)
app.py              entry point for `flask run` and Vercel
vcf.py              command line version
tests/              pytest, spreadsheets generated in code
```

pandas was replaced with the standard `csv` module and `openpyxl`: its automatic type guessing turned phone numbers into floats, and it is a heavy dependency for a serverless function.

The app keeps no state between requests. The review page holds the contacts in its own form, and every submit (Re-check or Download) is validated again on the server.

## 🔧 Prerequisites

Python 3.10 or newer.

## 💻 Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Run the web app

```bash
flask run --debug
```

Then open http://127.0.0.1:5000.

### Run from the command line

```bash
python3 vcf.py                          # contacts.xlsx -> contacts.vcf
python3 vcf.py bookclub.csv bookclub.vcf
```

Rows with errors are skipped and listed, since there is no review step.

### Run the tests

```bash
pytest
```

## Deploying

The app deploys to Vercel with no extra configuration: Vercel finds the `app` object in `app.py` and serves `public/` from its CDN. Uploads are capped at 3 MB, under Vercel's 4.5 MB request limit.

## Notes

- Birthdays without a year are written the way Apple Contacts exports them (`BDAY;X-APPLE-OMIT-YEAR=1604:1604-03-15`), so iPhones hide the year. Other apps may show 1604 as the year.
- Keep real contact data out of the repo. `.gitignore` covers `contacts.xlsx`, `contacts.csv`, and `*.vcf`.
