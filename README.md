# OSM-Wikidata Mapping Tool

A Python toolkit for creating bidirectional mappings between OpenStreetMap (OSM) relations and Wikidata entities. This project enables semantic linking between geographical features in OSM and structured knowledge in Wikidata.

## Overview

This project provides three main scripts to:

1. **Match entities** - Find corresponding entities between OSM and Wikidata based on name similarity and coordinate proximity
2. **Update Wikidata** - Add OSM relation IDs (P402 property) to matched Wikidata entities
3. **Update OSM** - Add Wikidata tags to matched OSM relations

By establishing these bidirectional links, the project enhances data integration and enables richer semantic queries across both platforms.

## Features

- **Intelligent Matching**: Matches entities using normalized name comparison and coordinate proximity
- **Bidirectional Linking**: Creates links from OSM to Wikidata and vice versa
- **Safety First**: Dry-run mode by default to preview changes before committing
- **Rate Limited**: Implements appropriate delays to respect API rate limits
- **Robust Error Handling**: Gracefully handles missing data and API errors

## Prerequisites

- Python 3.6+
- OpenStreetMap account with API access
- Wikidata account
- Required input data files (see Data Files section)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/LCholakov/semantic-web-osm-wikidata-mapping.git
cd semantic-web-osm-wikidata-mapping
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```env
OSM_USERNAME=your_osm_username
OSM_PASSWORD=your_osm_password
WIKIDATA_USERNAME=your_wikidata_username
WIKIDATA_PASSWORD=your_wikidata_password
```

3. The `user-config.py` file will automatically load these credentials for pywikibot.

## Data Files

The project requires these input files:

- `osm-relations-without-wikidata.json` - OSM relations that need Wikidata tags
- `wikidata-hardcode-3towns-for-match-test.json` - Wikidata entities for matching

Example structure for OSM data:
```json
{
  "elements": [
    {
      "id": 123456,
      "tags": {
        "name": "City Name"
      },
      "center": {
        "lat": 42.1234,
        "lon": 23.5678
      }
    }
  ]
}
```

Example structure for Wikidata data:
```json
[
  {
    "settlement": "http://www.wikidata.org/entity/Q12345",
    "settlementLabel": "City Name",
    "coord": "Point(23.5678 42.1234)"
  }
]
```

## Usage

### Step 1: Match Entities

Find corresponding entities between OSM and Wikidata:

```bash
python match-osm-wiki-small-batch-test.py
```

This script:
- Loads OSM relations and Wikidata entities
- Matches them based on normalized names and coordinate proximity (±0.01 degrees)
- Outputs results to `matches.json` and `matches.csv`

### Step 2: Update Wikidata (Optional)

Add OSM relation IDs to Wikidata entities:

```bash
# Dry run (preview changes)
python push-p402-relation-to-wikidata.py

# Commit changes to Wikidata
python push-p402-relation-to-wikidata.py --commit
```

This adds the P402 property (OpenStreetMap relation ID) to matched Wikidata entities.

### Step 3: Update OSM (Optional)

Add Wikidata tags to OSM relations:

```bash
# Dry run (preview changes)
python push-wd-tags-to-osm.py

# Commit changes to OSM
python push-wd-tags-to-osm.py --commit
```

This adds `wikidata=Q12345` tags to matched OSM relations.

## Safety Features

- **Dry Run Mode**: All scripts run in dry-run mode by default
- **Explicit Confirmation**: Requires user confirmation before making changes
- **Duplicate Detection**: Skips entities that already have the target properties/tags
- **Rate Limiting**: Implements delays between API calls (2s for Wikidata, 1s for OSM)
- **Error Recovery**: Continues processing even if individual entities fail

## Output Files

- `matches.json` - Detailed match results with full entity data
- `matches.csv` - Simple CSV with columns: name, wd_qid, osm_id

## Example Workflow

```bash
# 1. Match entities
python match-osm-wiki-small-batch-test.py

# 2. Review matches
cat matches.csv

# 3. Update Wikidata (dry run first)
python push-p402-relation-to-wikidata.py
python push-p402-relation-to-wikidata.py --commit

# 4. Update OSM (dry run first)
python push-wd-tags-to-osm.py
python push-wd-tags-to-osm.py --commit
```

## Matching Algorithm

The matching process uses:

1. **Name Normalization**:
   - Convert to lowercase
   - Remove extra whitespace
   - Unicode normalization (NFD)

2. **Coordinate Proximity**:
   - Tolerance of ±0.01 degrees (~1km)
   - Both name and coordinates must match

## API Rate Limits

The scripts implement conservative rate limiting:
- Wikidata: 2-second delay between requests
- OSM: 1-second delay between requests

## Error Handling

Common scenarios handled:
- Missing or malformed data
- Network timeouts
- Authentication failures
- Duplicate entries
- Non-existent entities

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with dry-run mode
5. Submit a pull request

## Acknowledgements

- [OpenStreetMap](https://www.openstreetmap.org/) for geographical data
- [Wikidata](https://www.wikidata.org/) for structured knowledge
- [Pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot) for Wikidata API access

## Support

For issues or questions, please open an issue on GitHub or contact the maintainers.

