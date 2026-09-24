# Contact Card Generator 📞

Try it out: **https://contact-card-generator-nine.vercel.app**

## Inspiration

Every semester, in multiple of my student organizations, we are constantly recruiting new members to be a part of great projects. One problem that new members run into is that they have no idea who is who in our org. group chat. It's a major hassle to save each contact, one by one.

## What It Does

You upload a spreadsheet (`.xlsx` or `.csv`) of your members and get back one contact file (`.vcf`) that anyone can open on their phone to save everyone at once. The sheet needs a `Name` and `Phone Number` column, and it can also have `Email` and `Birthday`. Any other fields such as Instagram or "Fun Facts" will be ignored. New members who need to add 20+ new contacts will definitely benefit from this and the same goes for current members who only need to add a couple contacts. Make life easier for everyone, why not!

Before anything gets converted, you see every contact in a review table so you can spot check it:

- **Things that need fixing** (a missing name or phone number, a birthday I can't read) are highlighted in red. You can fix them right in the table and hit Re-check, or untick the row to leave it out. Nothing gets dropped unless you decide to drop it.
- **Warnings** (a phone number with too few or too many digits, a possible duplicate) show up in yellow, but your data is kept exactly as typed.
- **Small automatic fixes** (like Excel turning a phone number into `2125550123.0`) are noted so nothing changes behind your back.

Your files are only read in memory and never stored anywhere.

### Combining files

Every semester I end up with last semester's contact file plus a brand new sign-up sheet. Under **Advanced** on the upload page, you can combine up to 10 files at once, mixing spreadsheets and existing `.vcf` files. Everything shows up in one review table with the file each contact came from. If a contact has the same phone or email as one that already showed up, it starts out unticked as a likely duplicate, so the final file has no repeats unless you want them.

From `.vcf` files, I only keep the name, phone, email, and birthday. If a card has more than that (an address, a photo, a second phone number), the review table tells you what didn't come along.

### What the sheet needs

| Column | Notes |
| --- | --- |
| `Name` (required) | Or separate `First Name` and `Last Name` columns. A single name is split into the first word and the rest, just like the original script. |
| `Phone Number` (required) | Any format works: `123-456-7890`, `(123)-456-7890`, `123.456.7890`, `+1 123 456 7890`. No country code means US. |
| `Email` | |
| `Birthday` | With or without a year: `July 15`, `15-Jul`, `7/15`, `7/15/2003`, or an Excel date. |

Similar headers like `Mobile`, `E-mail`, or `DOB` work too, and it's fine if there's a title row above the headers. There are templates in [`public/`](public/) if you want a starting point.

## Development Thought Process

Whenever I hear the term automate, I immediately jump to Python. Python is one of my favorite languages with a ton of developer support. The first version was a single script that used Pandas to read the Excel file and write out the contact cards.

For the web version I wanted to learn a Python web framework, and I went with Flask since it's lightweight and the app only needs a couple of pages. The original script's logic now lives in its own small package (`vcfcore`) with no web code in it, and Flask sits on top and just passes files in and contact cards out. That also means the command line version still works.

I ended up swapping Pandas for Python's built-in `csv` module and `openpyxl`. Pandas' automatic type guessing is what turned phone numbers into floats, and it's a pretty heavy dependency for something that runs as a serverless function.

The app doesn't keep anything between requests. The review page holds the contacts in its own form, and every time you hit Re-check or Download, the server checks everything again.

```
vcfcore/            the conversion logic, no Flask in here
  reader.py         .csv/.xlsx -> rows of cells (encodings, Excel dates, numeric phones)
  columns.py        finds the header row and matches column names
  validate.py       cleans each field and flags problems per row
  vcards.py         reads existing .vcf files (iPhone, Google, vCard 2.1-4.0)
  builder.py        writes the contact cards with vobject (the original script's loop)
webapp/             the Flask app
  __init__.py       create_app(): config and error pages
  routes.py         /, /review, /download
  templates/        Jinja pages, styled with Pico.css
public/             static files (spreadsheet templates)
app.py              entry point for `flask run` and Vercel
vcf.py              command line version
tests/              pytest
```

## 🔧 Prerequisites

Make sure you have Python 3.10 or newer installed.

## 💻 Installation

1. Clone this repo.
2. Set up a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

3. Run the web app, then open http://127.0.0.1:5000:

```bash
flask run --debug
```

4. Or skip the browser and use the command line version. With no arguments it reads `contacts.xlsx` and writes `contacts.vcf`, same as always:

```bash
python3 vcf.py
python3 vcf.py bookclub.csv bookclub.vcf
```

There's no review step on the command line, so rows with problems are skipped and listed for you.

5. Run the tests:

```bash
pytest
```

## 🚀 Deploying

The app deploys to Vercel with no extra configuration. Vercel finds the `app` object in `app.py` and serves `public/` from its CDN. Uploads are capped at 3 MB, which keeps them under Vercel's 4.5 MB request limit.

## Notes

- Birthdays without a year are saved the same way Apple Contacts does it (`BDAY;X-APPLE-OMIT-YEAR=1604:1604-03-15`), so iPhones hide the year. Some other apps might show 1604 as the year.
- Keep real contact data out of the repo. The `.gitignore` already covers `contacts.xlsx`, `contacts.csv`, and `*.vcf`.
