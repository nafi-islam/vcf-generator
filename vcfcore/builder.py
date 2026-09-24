"""Write contacts as vCard 3.0 text. This is the original vcf.py loop, moved here."""

import vobject

from .models import Contact, MonthDay

# apple's convention for a birthday without a year: a placeholder year plus a
# parameter telling the phone to hide it; other apps may show the placeholder year
OMIT_YEAR = 1604


def build_vcf(contacts: list[Contact]) -> str:
    return "".join(_vcard(contact).serialize() for contact in contacts)


def _vcard(contact: Contact) -> vobject.base.Component:
    vcard = vobject.vCard()

    vcard.add("n")
    vcard.n.value = vobject.vcard.Name(family=contact.last, given=contact.first)

    vcard.add("fn")
    vcard.fn.value = contact.full_name

    if contact.phone:
        vcard.add("tel")
        vcard.tel.value = contact.phone
        vcard.tel.type_param = "CELL"

    if contact.email:
        vcard.add("email")
        vcard.email.value = contact.email
        vcard.email.type_param = "INTERNET"

    if isinstance(contact.birthday, MonthDay):
        vcard.add("bday")
        vcard.bday.value = f"{OMIT_YEAR:04d}-{contact.birthday.month:02d}-{contact.birthday.day:02d}"
        vcard.bday.params["X-APPLE-OMIT-YEAR"] = [str(OMIT_YEAR)]
    elif contact.birthday:
        vcard.add("bday")
        vcard.bday.value = contact.birthday.isoformat()

    return vcard
