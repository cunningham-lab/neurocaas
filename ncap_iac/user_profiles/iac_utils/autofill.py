import json 
import csv
## Tools to automatically fill in user stack templates from csvs. 
## We need a tool to parse excel files -> dictionary. 
## We need a tool to validate and separate out users into valid and invalid entries, and reprint that. 
## We need a tool to take dictionary, and append it to an existing user template. 
## We need a tool to look at that appended template and make sure it's okay.

def parse_userfile(path):
    """
    Take the path to the user file, and crete a two dictionaries: 1. valid users, with usernames, emails, and affiliations. 
    2. invalidated users, who should be sent an email requesting id confirmation. 
    """
    with open(path,"r",newline='') as datafile: 
        datareader = csv.reader(datafile,dialect="excel")
        for row in datareader:
            print(row)


