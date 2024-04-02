# VCF Generator 📞

## Inspiration

Every semester, in multiple of my student organizations, we are constantly recruiting new members to be a part of great projects. One problem that new members run into is that they have no idea who is who in our org. group chat. It's a major hassle to save each contact, one by one.

## What It Does

This is a fairly straight forward process. The script takes an Excel file in and outputs a VCF or contact card. The Excel file must have fields such as `Name`, `Phone Number`, `Email`, and `Birthday`. The script will go through the Excel file and add these fields to each respective contact. Then, I make a mass contact list of all contact cards to be sent out. Any additional fields such as Instagram or "Fun Facts" will be ignored. New members who need to add 20+ new contacts will definitely benefit from this and the same goes for current members who only need to add a couple contacts. Make life easier for everyone, why not!

## Development Thought Process

Whenever I hear the term automate, I immediately jump to Python. Python is one of my favorite languages with a ton of developer support. In this project, I used Pandas because it allows me to directly manipulate Excel files out of the box. Also, the flexibility that Pandas offers such as, filtering data or handling missing values, makes my life much easier when writing code.

## What's next?

- I have tested the VCF generator locally and it works for a live audience! It'd be fun to release this to the public on some sort of web application which could be the next phase for this project 👀
