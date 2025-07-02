import json
from math import isclose
import unicodedata
import re
import csv

# Load OSM data
with open("osm-relations-without-wikidata.json", "r", encoding="utf-8") as osm_file:
    osm_data = json.load(osm_file)

# Load Wikidata
with open("wikidata-entities.json", "r", encoding="utf-8") as wikidata_file:
    wikidata_data = json.load(wikidata_file)

# Extract OSM elements
osm_elements = osm_data.get("elements", [])

# Prepare matches
matches = []

# Helper function to normalize text for comparison
def normalize_text(text):
    if not text:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Normalize Unicode characters (NFD normalization)
    text = unicodedata.normalize('NFD', text)
    return text

# Helper function to parse Wikidata coordinates
def parse_wikidata_coord(coord):
    try:
        lon, lat = coord.replace("Point(", "").replace(")", "").split()
        return float(lat), float(lon)
    except Exception:
        return None, None

# Helper function to extract Wikidata QID from URI
def extract_wikidata_qid(uri):
    if not uri:
        return ""
    return uri.split('/')[-1]

# Match Wikidata settlements to OSM names or coordinates
for wd_entry in wikidata_data:
    wd_label = wd_entry.get("settlementLabel")
    wd_label_normalized = normalize_text(wd_label)
    wd_lat, wd_lon = parse_wikidata_coord(wd_entry.get("coord", ""))
    wd_qid = extract_wikidata_qid(wd_entry.get("settlement"))

    for osm_element in osm_elements:
        osm_name = osm_element.get("tags", {}).get("name")
        osm_name_normalized = normalize_text(osm_name)
        osm_lat = osm_element.get("center", {}).get("lat")
        osm_lon = osm_element.get("center", {}).get("lon")
        osm_id = osm_element.get("id")

        # Match by normalized name and coordinates
        name_match = wd_label_normalized == osm_name_normalized
        coord_match = (osm_lat and osm_lon and
                      isclose(wd_lat, osm_lat, abs_tol=0.01) and
                      isclose(wd_lon, osm_lon, abs_tol=0.01))

        if name_match and coord_match:
            matches.append({
                "wikidata": wd_entry,
                "osm": osm_element,
                "match_type": "name_and_coordinates",
                "name": wd_label,
                "wikidata_qid": wd_qid,
                "osm_id": osm_id
            })

# Output matches
print("Matches found:")
for match in matches:
    print(f"Match type: {match['match_type']}")
    print(json.dumps(match, ensure_ascii=False, indent=2))

# Save matches to a file
with open("matches.json", "w", encoding="utf-8") as output_file:
    json.dump(matches, output_file, ensure_ascii=False, indent=2)

# Output to CSV file with specified headers
with open("matches.csv", "w", encoding="utf-8", newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['name', 'wd_qid', 'osm_id'])  # Write headers
    for match in matches:
        csv_writer.writerow([match['name'], match['wikidata_qid'], match['osm_id']])

print(f"Output written to matches.csv")
