import csv
import os
import sys
import requests
import time
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
import json
from getpass import getpass
from urllib.parse import quote



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
    """Get OSM OAuth2 credentials from environment."""
    load_dotenv()
    client_id = os.getenv('OSM_CLIENT_ID')
    client_secret = os.getenv('OSM_CLIENT_SECRET')
    redirect_uri = os.getenv('OSM_REDIRECT_URI')

    if not client_id or not client_secret:
        print("Error: OSM_CLIENT_ID and OSM_CLIENT_SECRET must be set in .env file")
        return None, None

    return client_id, client_secret, redirect_uri


def authenticate_osm_oauth2(client_id, client_secret, redirect_uri):
    """Authenticate with OSM API using OAuth2 and get an access token."""
    # OAuth2 endpoints for OpenStreetMap
    authorization_base_url = 'https://www.openstreetmap.org/oauth2/authorize'
    token_url = 'https://www.openstreetmap.org/oauth2/token'

    # Redirect URI (for desktop applications, this is typically a localhost URL)
    token_string =  os.getenv('OSM_TOKEN_STRING')
    redirect_uri = os.getenv('OSM_REDIRECT_URI')

    # Create OAuth2 session
    osm = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=['read_prefs', 'write_api'])

    # Get authorization URL
    authorization_url, state = osm.authorization_url(authorization_base_url)

    print(f"Please go to {authorization_url} and authorize access.")
    authorization_response = input('Paste the full redirect URL here:')

    # Fetch the access token
    try:
        token = {"access_token": token_string, "token_type": "bearer"}

        # token = osm.fetch_token(
        #     token_url,
        #     authorization_response=authorization_response,
        #     client_secret=client_secret
        # )
        return osm, token
    except Exception as e:
        print(f"OAuth2 authentication failed: {e}")
        return None, None


def get_relation_data(relation_id, oauth_session=None):
    """Get current relation data from OSM using OAuth2."""
    url = f"https://api.openstreetmap.org/api/0.6/relation/{relation_id}.json"
    headers = {"Accept": "application/json"}

    if oauth_session:
        response = oauth_session.get(url, headers=headers)
    else:
        response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to get relation {relation_id}: {response.status_code} {response.text}")
        return None

    return response.json()


def update_relation_with_wikidata(relation_id, wikidata_qid, oauth_session, dry_run=True):
    """Update an OSM relation with a wikidata tag using OAuth2."""
    # Get current relation data
    relation_data = get_relation_data(relation_id, oauth_session)
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
    changeset_id = create_changeset(oauth_session)
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

    response = oauth_session.put(update_url, headers=headers, data=xml_data)
    if response.status_code != 200:
        print(f"Failed to update relation {relation_id}: {response.status_code} {response.text}")
        return False

    return True


def create_changeset(oauth_session):
    """Create a new changeset for the edits using OAuth2."""
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

    response = oauth_session.put(url, headers=headers, data=changeset_data)
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

    # Authenticate with OSM API using OAuth2
    client_id, client_secret, redirect_uri = get_osm_credentials()
    if not client_id or not client_secret:
        print("OAuth2 credentials not found. Exiting.")
        return

    oauth_session, token = authenticate_osm_oauth2(client_id, client_secret, redirect_uri)
    if not oauth_session:
        print("OAuth2 authentication failed. Exiting.")
        return

    print("OAuth2 authentication successful!")

    # Process each match
    success_count = 0
    for match in matches:
        name = match['name']
        wikidata_qid = match['wd_qid']
        osm_id = match['osm_id']

        print(f"Processing {name} (Wikidata: {wikidata_qid}, OSM: {osm_id})...")

        try:
            success = update_relation_with_wikidata(osm_id, wikidata_qid, oauth_session, dry_run)
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