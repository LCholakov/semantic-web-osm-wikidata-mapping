import csv
import os
import sys
import time
import requests
from getpass import getpass
from dotenv import load_dotenv
import pywikibot
from pywikibot import Site, WbTime
from pywikibot.exceptions import NoPageError

def read_matches(csv_file):
    """Read the matches from the CSV file."""
    matches = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            matches.append({
                'name': row['name'],
                'wd_qid': row['wd_qid'],
                'osm_id': row['osm_id']
            })
    return matches

def get_wikidata_credentials():
    """Get Wikidata username and password from environment or prompt."""
    load_dotenv()
    """Get Wikidata username and password from environment or prompt."""
    username = os.getenv('WIKIDATA_USERNAME') or input("Wikidata Username: ")
    password = os.getenv('WIKIDATA_PASSWORD') or getpass("Wikidata Password: ")
    return username, password

def set_up_wikidata_connection():
    """Set up connection to Wikidata."""
    username, password = get_wikidata_credentials()
    site = Site('wikidata', 'wikidata')
    site.login(username)
    return site.data_repository()

def add_p402_to_entity(repo, wd_qid, osm_id, dry_run=True):
    """Add P402 (OpenStreetMap relation ID) property to a Wikidata entity."""
    try:
        # Load the item
        item = pywikibot.ItemPage(repo, wd_qid)
        item.get()

        # Check if P402 already exists
        if 'P402' in item.claims:
            for claim in item.claims['P402']:
                if claim.getTarget() == str(osm_id):
                    print(f"Item {wd_qid} already has P402 with value {osm_id}")
                    return False
                else:
                    print(f"Item {wd_qid} already has P402 with different value: {claim.getTarget()}")
                    return False

        if dry_run:
            print(f"DRY RUN: Would add P402={osm_id} to {wd_qid}")
            return True

        # Create a new claim
        claim = pywikibot.Claim(repo, 'P402')
        claim.setTarget(str(osm_id))
        item.addClaim(claim, summary="Adding OpenStreetMap relation ID")

        # Add reference
        ref = pywikibot.Claim(repo, 'P143')  # P143 = imported from Wikimedia project
        ref.setTarget(pywikibot.ItemPage(repo, 'Q16960'))  # Q16960 = OpenStreetMap
        claim.addSource(ref, summary="Adding reference")

        print(f"Successfully added P402={osm_id} to {wd_qid}")
        return True

    except NoPageError:
        print(f"Error: Item {wd_qid} does not exist")
        return False
    except Exception as e:
        print(f"Error processing {wd_qid}: {e}")
        return False

def main():
    # Load matches
    matches = read_matches('matches.csv')
    print(f"Loaded {len(matches)} matches from CSV")

    # Default to dry run for safety
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1].lower() == '--commit':
        dry_run = False
        print("WARNING: Running in COMMIT mode. Changes will be pushed to Wikidata!")
        confirm = input("Are you sure you want to continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborting.")
            return
    else:
        print("Running in DRY RUN mode. No changes will be made to Wikidata.")
        print("To commit changes, run with --commit flag.")

    # Set up Wikidata connection
    try:
        repo = set_up_wikidata_connection()
    except Exception as e:
        print(f"Failed to connect to Wikidata: {e}")
        return

    # Process each match
    success_count = 0
    for match in matches:
        name = match['name']
        wd_qid = match['wd_qid']
        osm_id = match['osm_id']

        print(f"Processing {name} (Wikidata: {wd_qid}, OSM: {osm_id})...")

        try:
            success = add_p402_to_entity(repo, wd_qid, osm_id, dry_run)
            if success:
                success_count += 1
                print(f"Successfully {'prepared' if dry_run else 'updated'} Wikidata item {wd_qid}")
            else:
                print(f"Failed to update Wikidata item {wd_qid}")
        except Exception as e:
            print(f"Error processing {name}: {e}")

        # Be nice to the Wikidata API - don't hammer it
        time.sleep(2)

    print(f"\nSummary: {success_count}/{len(matches)} Wikidata items {'would be' if dry_run else 'were'} updated")
    if not dry_run:
        print("Changes have been pushed to Wikidata!")

if __name__ == "__main__":
    main()
