"""Test script to see raw Zerion API responses."""

import os
import json
import httpx

# Test address with known positions
test_address = "0xBFbeD8717AEB318Eb7cE20913dd7563287c474bA"

# Get Zerion API key from environment
api_key = os.getenv("ZERION_API_KEY")
if not api_key:
    print("ERROR: ZERION_API_KEY environment variable not set")
    print("Set it with: export ZERION_API_KEY='your_key'")
    exit(1)

print(f"\nTesting Zerion API for address: {test_address}\n")

# Query Zerion API
url = f"https://api.zerion.io/v1/wallets/{test_address}/positions/"
params = {
    "filter[chain_ids]": "ethereum,base",
    "currency": "usd",
}

client = httpx.Client(timeout=30.0, auth=(api_key, ""))

print(f"Fetching from: {url}")
print(f"Params: {params}\n")

try:
    response = client.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    print(f"Response status: {response.status_code}")
    print(f"Total positions: {len(data.get('data', []))}\n")

    # Print first 3 positions in detail
    for i, item in enumerate(data.get("data", [])[:3]):
        print(f"\n{'='*80}")
        print(f"Position {i+1}:")
        print(f"{'='*80}")

        # Print item structure
        print(f"Item keys: {list(item.keys())}")
        print(f"Item ID: {item.get('id')}")
        print(f"Item type: {item.get('type')}")

        # Print attributes
        attributes = item.get("attributes", {})
        print(f"\nAttributes keys: {list(attributes.keys())}")
        print(f"  position_type: {attributes.get('position_type')}")
        print(f"  protocol: {attributes.get('protocol')}")
        print(f"  name: {attributes.get('name')}")
        print(f"  value: {attributes.get('value')}")

        # Print fungible_info
        if "fungible_info" in attributes:
            fungible = attributes["fungible_info"]
            print(f"\nFungible info:")
            print(f"  symbol: {fungible.get('symbol')}")
            print(f"  name: {fungible.get('name')}")

        # Print relationships
        relationships = item.get("relationships", {})
        print(f"\nRelationships keys: {list(relationships.keys())}")

        # Save full item to file for inspection
        with open(f"/tmp/zerion_position_{i+1}.json", "w") as f:
            json.dump(item, f, indent=2)
        print(f"\nFull position saved to: /tmp/zerion_position_{i+1}.json")

    print(f"\n{'='*80}\n")
    print(f"Check the saved files for full details:")
    for i in range(min(3, len(data.get("data", [])))):
        print(f"  /tmp/zerion_position_{i+1}.json")

except httpx.HTTPStatusError as e:
    print(f"HTTP Error: {e.response.status_code}")
    print(f"Response: {e.response.text}")
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
