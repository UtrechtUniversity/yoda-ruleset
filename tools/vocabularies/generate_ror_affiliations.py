#!/usr/bin/env python
#
# Usage: python3 generate_ror_affiliations.py > affiliations.json
#
# Retrieve ROR data json from ROR data dump from https://zenodo.org/record/7926988
#
import json

with open('v1.25-2023-05-11-ror-data.json') as f:
    # Load ROR data dump file.
    ror_data = json.load(f)

    affiliations = []
    for organization in ror_data:
        # Get active organizations from NL with type Education.
        if (organization["status"] == "active"
           and organization["country"]["country_code"] == "NL"
           and "Education" in organization["types"]):
            affiliations.append({"value": organization['id'], "label": organization['name']})

    # Sort organizations on their name.
    affiliations = sorted(affiliations, key=lambda d: d['label'])

    print(json.dumps(affiliations))
