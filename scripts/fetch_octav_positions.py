"""Diagnostic script: Fetch portfolio positions via Octav.fi API."""

import os
import sys

from crypto_portfolio_tracker.integrations.octav import OctavAPIError, OctavClient

TARGET_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth


def main() -> None:
    """Fetch and display portfolio positions from Octav.fi API."""
    api_key = os.getenv("OCTAV_API_KEY")
    if not api_key:
        print("ERROR: OCTAV_API_KEY environment variable not set.")
        print("  export OCTAV_API_KEY='your_api_key_here'")
        sys.exit(1)

    address = sys.argv[1] if len(sys.argv) > 1 else TARGET_ADDRESS
    print(f"Fetching Octav.fi portfolio for: {address}")
    print(f"{'='*60}")

    with OctavClient(api_key=api_key) as client:
        # Check credits (free call)
        try:
            credits = client.check_credits()
            print(f"  API Credits remaining: {credits}")
        except OctavAPIError as e:
            print(f"  Credits check failed: {e}")

        # Fetch NAV
        print(f"\n{'='*60}")
        print("  Net Asset Value")
        print(f"{'='*60}")
        try:
            nav = client.get_nav(address)
            print(f"  NAV: ${nav:,.2f}")
        except OctavAPIError as e:
            print(f"  NAV fetch failed: {e}")

        # Fetch positions
        print(f"\n{'='*60}")
        print("  Portfolio Positions")
        print(f"{'='*60}")
        try:
            positions = client.get_positions(address)
            if not positions:
                print("  No positions found.")
            else:
                # Group by protocol
                by_protocol: dict[str, list] = {}
                for pos in positions:
                    by_protocol.setdefault(pos.protocol, []).append(pos)

                for protocol, proto_positions in sorted(by_protocol.items()):
                    total_usd = sum(
                        p.usd_value for p in proto_positions if p.usd_value
                    )
                    print(f"\n  Protocol: {protocol} (${total_usd:,.2f})")
                    print(f"  {'-'*50}")
                    for pos in proto_positions:
                        chain_tag = f"[{pos.chain}]"
                        print(
                            f"    {chain_tag:<12} {pos.token.symbol:<10} "
                            f"Balance: {pos.balance:>14,.6f}  "
                            f"Value: ${pos.usd_value or 0:>12,.2f}  "
                            f"Type: {pos.position_type}"
                        )

                print(f"\n  Total positions: {len(positions)}")

        except OctavAPIError as e:
            print(f"  Position fetch failed: {e}")

    print(f"\n{'='*60}")
    print("  Done.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
