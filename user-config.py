# user-config.py
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Set up credentials for pywikibot
username = os.getenv('WIKIDATA_USERNAME')
password = os.getenv('WIKIDATA_PASSWORD')

# Configure usernames for Wikidata
usernames['wikidata']['wikidata'] = username

# Optional: Set password for Wikidata
password_file = "passwordfile"
with open(password_file, 'w') as f:
    f.write(f"('wikidata', '{username}', '{password}')")