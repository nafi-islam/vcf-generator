import pandas as pd
import vobject

# Access the Excel File
df = pd.read_excel('contacts.xlsx')

# Initialize an empty string to hold all vCard information
vcards = ""

# Iterate over the rows in the DataFrame
for index, row in df.iterrows():
    # Split the name into first and last name
    names = row['Name'].split()
    first_name = names[0]
    last_name = ' '.join(names[1:]) if len(names) > 1 else ''

    # Init VCF
    vcard = vobject.vCard()

    vcard.add('n')
    vcard.n.value = vobject.vcard.Name(family=last_name, given=first_name)

    # Add Formatted Name
    vcard.add('fn')
    vcard.fn.value = str(row['Name'])

    # Phone #
    vcard.add('tel')
    vcard.tel.value = str(row['Phone Number'])
    vcard.tel.type_param = 'CELL'

    # Email
    vcard.add('email')
    vcard.email.value = row['Email']
    vcard.email.type_param = 'INTERNET'

    # Add Birthday, convert to "YYYY-MM-DD" from "dd-MMM"
    # Year N/A -> "2000" as placeholder. Just need Calendar to recognize date. Maybe don't hard code this, oops
    # Maybe add a try/except to catch errors for NaN
    if pd.notnull(row['Birthday']):
        birthday = pd.to_datetime(row['Birthday'], format='%d-%b', errors='coerce')
        vcard.add('bday')
        vcard.bday.value = birthday.strftime('2000-%m-%d')

    # Append vCard to vcards string
    vcards += vcard.serialize()

# Write all accumulated vCards to a single file
with open('contacts.vcf', 'w') as f:
    f.write(vcards)
