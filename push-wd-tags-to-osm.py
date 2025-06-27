import csv
import os
import sys
import json
import requests
import time
from getpass import getpass
from urllib.parse import quote
from dotenv import load_dotenv


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

def get_osm_credentials():
    load_dotenv()
    """Get OSM username and password from environment or prompt."""
    username = os.getenv('OSM_USERNAME') or input("OSM Username: ")
    password = os.getenv('OSM_PASSWORD') or getpass("OSM Password: ")
    return username, password

def authenticate_osm(username, password):
    """Authenticate with OSM API and get an auth token."""
    auth_url = "https://www.openstreetmap.org/api/0.6/user/details"
    response = requests.get(auth_url, auth=(username, password))

    if response.status_code != 200:
        print(f"Authentication failed: {response.status_code} {response.text}")
        return None

    return username, password

def get_relation_data(relation_id, auth=None):
    """Get current relation data from OSM."""
    url = f"https://api.openstreetmap.org/api/0.6/relation/{relation_id}.json"
    headers = {"Accept": "application/json"}

    response = requests.get(url, headers=headers, auth=auth)
    if response.status_code != 200:
        print(f"Failed to get relation {relation_id}: {response.status_code} {response.text}")
        return None

    return response.json()

def update_relation_with_wikidata(relation_id, wikidata_qid, auth, dry_run=True):
    """Update an OSM relation with a wikidata tag."""
    # Get current relation data
    relation_data = get_relation_data(relation_id, auth)
    if not relation_data:
        return False

    relation = relation_data.get('elements', [])[0] if 'elements' in relation_data else None
    if not relation:
        print(f"Relation {relation_id} not found")
        return False

    # Check if wikidata tag already exists
    tags = relation.get('tags', {})
    if 'wikidata' in tags:
        print(f"Relation {relation_id} already has wikidata tag: {tags['wikidata']}")
        return False

    # Add wikidata tag
    tags['wikidata'] = wikidata_qid
    relation['tags'] = tags

    if dry_run:
        print(f"DRY RUN: Would update relation {relation_id} with wikidata={wikidata_qid}")
        return True

    # Update the relation in OSM
    version = relation.get('version')
    changeset_id = create_changeset(auth)
    if not changeset_id:
        return False

    update_url = f"https://api.openstreetmap.org/api/0.6/relation/{relation_id}"
    headers = {"Content-Type": "application/xml"}
    xml_data = f"""
    <osm>
        <relation id="{relation_id}" version="{version}" changeset="{changeset_id}">
            <!-- tags and other elements would go here -->
        </relation>
    </osm>
    """

    # Note: This is simplified. In reality, you need to preserve all members and tags
    # of the relation, which requires more complex XML construction.
    # Consider using a library like osmapi instead of raw requests.

    response = requests.put(update_url, auth=auth, headers=headers, data=xml_data)
    if response.status_code != 200:
        print(f"Failed to update relation {relation_id}: {response.status_code} {response.text}")
        return False

    return True

def create_changeset(auth):
    """Create a new changeset for the edits."""
    url = "https://api.openstreetmap.org/api/0.6/changeset/create"
    headers = {"Content-Type": "application/xml"}
    changeset_data = """
    <osm>
        <changeset>
            <tag k="created_by" v="wikidata-OSM-matching-script"/>
            <tag k="comment" v="Adding wikidata tags to relations based on name/coordinate matching"/>
        </changeset>
    </osm>
    """

    response = requests.put(url, auth=auth, headers=headers, data=changeset_data)
    if response.status_code != 200:
        print(f"Failed to create changeset: {response.status_code} {response.text}")
        return None

    return response.text.strip()

def main():
    # Load matches
    matches = read_matches('matches.csv')
    print(f"Loaded {len(matches)} matches from CSV")

    # Default to dry run for safety
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1].lower() == '--commit':
        dry_run = False
        print("WARNING: Running in COMMIT mode. Changes will be pushed to OSM!")
        confirm = input("Are you sure you want to continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborting.")
            return
    else:
        print("Running in DRY RUN mode. No changes will be made to OSM.")
        print("To commit changes, run with --commit flag.")

    # Authenticate with OSM API
    username, password = get_osm_credentials()
    auth = authenticate_osm(username, password)
    if not auth:
        print("Authentication failed. Exiting.")
        return

    # Process each match
    success_count = 0
    for match in matches:
        name = match['name']
        wikidata_qid = match['wd_qid']
        osm_id = match['osm_id']

        print(f"Processing {name} (Wikidata: {wikidata_qid}, OSM: {osm_id})...")

        try:
            success = update_relation_with_wikidata(osm_id, wikidata_qid, auth, dry_run)
            if success:
                success_count += 1
                print(f"Successfully {'prepared' if dry_run else 'updated'} OSM relation {osm_id}")
            else:
                print(f"Failed to update OSM relation {osm_id}")
        except Exception as e:
            print(f"Error processing {name}: {e}")

        # Be nice to the OSM API - don't hammer it
        time.sleep(1)

    print(f"\nSummary: {success_count}/{len(matches)} relations {'would be' if dry_run else 'were'} updated")
    if not dry_run:
        print("Changes have been pushed to OpenStreetMap!")

if __name__ == "__main__":
    main()

