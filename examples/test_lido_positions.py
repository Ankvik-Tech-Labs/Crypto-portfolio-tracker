"""
Example script to test Lido position fetching with real RPC calls.

This demonstrates the RPC integration using Ape's Infura plugin.

Requirements:
1. Set WEB3_INFURA_PROJECT_ID environment variable
   - Add to ~/.zshrc: export WEB3_INFURA_PROJECT_ID="your_project_id"
   - Or use a .env file in the project root
2. Set ETHERSCAN_API_KEY environment variable (optional but recommended)
   - Add to ~/.zshrc: export ETHERSCAN_API_KEY="your_api_key"

Usage:
    python examples/test_lido_positions.py
"""

from decimal import Decimal

from crypto_portfolio_tracker.protocols.lido import LidoHandler
from crypto_portfolio_tracker.rpc import ApeRPCProvider


def main() -> None:
    """Test Lido position fetching with a known address."""
    # Use Lido's own address as a test - it should have stETH
    # This is a well-known address that holds stETH
    test_address = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"  # stETH contract itself

    print("Testing Lido RPC Integration")
    print("=" * 50)
    print(f"Address: {test_address}")
    print()

    # Create RPC provider
    print("Connecting to Ethereum mainnet via Infura...")
    rpc_provider = ApeRPCProvider(chain="ethereum")

    try:
        rpc_provider.connect()
        print("✓ Connected successfully")
        print()

        # Create Lido handler
        handler = LidoHandler(rpc_provider=rpc_provider)

        # Fetch positions
        print("Fetching Lido positions...")
        positions = handler.get_positions(test_address, "ethereum")

        if not positions:
            print("No positions found for this address")
        else:
            print(f"Found {len(positions)} position(s):")
            print()

            for i, position in enumerate(positions, 1):
                print(f"Position {i}:")
                print(f"  Token: {position.token.symbol} ({position.token.name})")
                print(f"  Balance: {position.balance:.6f}")
                if position.underlying_token:
                    print(f"  Underlying: {position.underlying_balance:.6f} {position.underlying_token.symbol}")
                print(f"  Type: {position.position_type.value}")
                print()

    except Exception as e:
        print(f"Error: {e}")
        print()
        print("Make sure you have set environment variables:")
        print("1. WEB3_INFURA_PROJECT_ID (required)")
        print("2. ETHERSCAN_API_KEY (optional)")
        print()
        print("Add to ~/.zshrc or ~/.bashrc:")
        print('  export WEB3_INFURA_PROJECT_ID="your_project_id"')
        print('  export ETHERSCAN_API_KEY="your_api_key"')
        raise

    finally:
        rpc_provider.disconnect()
        print("Disconnected from network")


if __name__ == "__main__":
    main()
