"""Test script to debug Zerion API responses."""

import os
from crypto_portfolio_tracker.integrations.zerion import ZerionClient

# Test address with known positions
test_address = "0xBFbeD8717AEB318Eb7cE20913dd7563287c474bA"

# Get Zerion API key from environment
api_key = os.getenv("ZERION_API_KEY")
if not api_key:
    print("ERROR: ZERION_API_KEY environment variable not set")
    exit(1)

print(f"\nTesting Zerion API for address: {test_address}\n")

with ZerionClient(api_key) as client:
    # Fetch positions
    positions = client.get_positions_as_models(test_address)

    print(f"\n\n=== SUMMARY ===")
    print(f"Total positions found: {len(positions)}")

    # Group by protocol
    by_protocol = {}
    for pos in positions:
        if pos.protocol not in by_protocol:
            by_protocol[pos.protocol] = []
        by_protocol[pos.protocol].append(pos)

    print(f"\nBy Protocol:")
    for protocol, pos_list in by_protocol.items():
        print(f"  {protocol}: {len(pos_list)} positions")
        for pos in pos_list:
            # Format USD value with 2 decimal places
            usd_str = f"${pos.usd_value:.2f}" if pos.usd_value else "$0.00"
            print(f"    - {pos.token.symbol} on {pos.chain}: {usd_str}")
