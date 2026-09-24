# Contact Card Generator 📞

Try it out: **https://nafi-contact-card-generator.vercel.app**

## Inspiration

Every semester, in multiple of my student organizations, we are constantly recruiting new members to be a part of great projects. One problem that new members run into is that they have no idea who is who in our org. group chat. It's a major hassle to save each contact, one by one.

## What It Does

Upload a spreadsheet (`.xlsx` or `.csv`) of your members and get back one contact file (`.vcf`) that anyone can open on their phone to save everyone at once. Make life easier for everyone, why not!

- **Review first:** you see every contact before anything gets converted. Problems are highlighted, and you can fix them right in the table.
- **Combine files:** under **Advanced**, mix spreadsheets and existing `.vcf` files into one. Duplicates are left out for you.
- **Private:** files are only read in memory and never stored.

The sheet needs a `Name` and `Phone Number` column, and can also have `Email` and `Birthday`. Any other fields such as Instagram or "Fun Facts" will be ignored. There are templates in [`public/`](public/) if you want a starting point.

## Development Thought Process

Whenever I hear the term automate, I immediately jump to Python. The first version was a single Pandas script. For the web version I wanted to learn a Python web framework, so I went with Flask since it's lightweight. The original script's logic lives in `vcfcore/`, and the Flask app in `webapp/` sits on top of it.

## 💻 Running Locally

Make sure you have Python 3.10 or newer, then:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask run --debug
```

Open http://127.0.0.1:5000. You can also skip the browser and run `python3 vcf.py`, which turns `contacts.xlsx` into `contacts.vcf` like always. Run the tests with `pytest`.

Pushing to `main` deploys to Vercel automatically.

## Notes

- On iPhone, tap **Add All Contacts** once, then tap **Done**. Tapping it again adds everyone a second time.
- Keep real contact data out of the repo. The `.gitignore` already covers `contacts.xlsx`, `contacts.csv`, and `*.vcf`.
