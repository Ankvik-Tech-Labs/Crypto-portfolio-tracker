"""
Debug script to investigate why an address isn't returning positions.

Usage:
    python debug_address.py 0xBFbeD8717AEB318Eb7cE20913dd7563287c474bA
"""

import sys

from crypto_portfolio_tracker.core.scanner import ChainScanner
from crypto_portfolio_tracker.rpc import ApeRPCProvider


def main():
    """Debug address activity."""
    if len(sys.argv) < 2:
        print("Usage: python debug_address.py <address>")
        sys.exit(1)

    address = sys.argv[1]
    chain = "ethereum"

    print(f"Debugging address: {address}")
    print(f"Chain: {chain}")
    print("=" * 60)
    print()

    # Connect to network
    print("Connecting to Ethereum mainnet...")
    provider = ApeRPCProvider(chain=chain)

    try:
        provider.connect()
        print("✓ Connected successfully")
        print()
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print()
        print("Make sure you have set WEB3_INFURA_PROJECT_ID environment variable")
        sys.exit(1)

    # Create scanner with debug enabled
    scanner = ChainScanner(rpc_provider=provider, debug=True)

    print("=" * 60)
    print("Step 1: Checking chain activity (Transfer events)")
    print("=" * 60)
    has_activity = scanner._has_chain_activity(address, chain)
    print()
    print(f"Result: {'✓ Activity detected' if has_activity else '✗ No activity detected'}")
    print()

    if not has_activity:
        print("No Transfer events found for this address.")
        print("This could mean:")
        print("  1. Address has never received any tokens")
        print("  2. RPC node doesn't have full history")
        print("  3. eth_getLogs query is too broad")
        print()
        print("Let's try checking recent blocks only...")

        # Try a more recent block range
        try:
            print("Querying last 1000 blocks for Transfer events...")
            topics = [
                "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                None,
                scanner._pad_address(address),
            ]

            # Get latest block
            latest = provider.make_request("eth_blockNumber", [])
            latest_int = int(latest, 16)
            from_block = hex(latest_int - 1000)

            print(f"  Latest block: {latest_int}")
            print(f"  From block: {int(from_block, 16)}")

            logs = provider.make_request(
                "eth_getLogs",
                [
                    {
                        "fromBlock": from_block,
                        "toBlock": "latest",
                        "topics": topics,
                    }
                ],
            )

            print(f"  Found {len(logs)} Transfer events in last 1000 blocks")
            if len(logs) > 0:
                print("  ✓ Recent activity detected!")
            print()

        except Exception as e:
            print(f"  Error: {e}")
            print()

    if has_activity:
        print("=" * 60)
        print("Step 2: Discovering protocols")
        print("=" * 60)
        protocols = scanner.discover_protocols(address, chain)
        print()
        print(f"Result: Found {len(protocols)} protocols")
        if protocols:
            for protocol in protocols:
                print(f"  - {protocol}")
        print()

    print("=" * 60)
    print("Step 3: Checking specific Lido positions")
    print("=" * 60)

    # Get Lido contract addresses
    from crypto_portfolio_tracker.data import get_protocol_addresses

    lido_addresses = get_protocol_addresses(chain, "lido")
    print(f"Lido contracts: {lido_addresses}")
    print()

    if "steth" in lido_addresses:
        steth_address = lido_addresses["steth"]
        print(f"Checking stETH balance at {steth_address}...")

        try:
            contract = provider.get_contract(steth_address)
            balance = contract.balanceOf(address)
            print(f"  Raw balance: {balance}")
            print(f"  Formatted: {balance / 10**18:.6f} stETH")
            print()
        except Exception as e:
            print(f"  Error: {e}")
            print()

    if "wsteth" in lido_addresses:
        wsteth_address = lido_addresses["wsteth"]
        print(f"Checking wstETH balance at {wsteth_address}...")

        try:
            contract = provider.get_contract(wsteth_address)
            balance = contract.balanceOf(address)
            print(f"  Raw balance: {balance}")
            print(f"  Formatted: {balance / 10**18:.6f} wstETH")
            print()
        except Exception as e:
            print(f"  Error: {e}")
            print()

    # Cleanup
    provider.disconnect()
    print("=" * 60)
    print("Debug complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
