"""Diagnostic script: Fetch AAVE v3 positions for a wallet across all supported chains."""

import sys
import traceback

from crypto_portfolio_tracker.data import get_protocol_addresses
from crypto_portfolio_tracker.rpc.provider import ApeRPCProvider

TARGET_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth

# Chains with ape ecosystem plugins installed (polygon excluded due to dep conflict)
CHAINS = ["ethereum", "base", "arbitrum", "optimism"]

# getUserAccountData(address) selector
GET_USER_ACCOUNT_DATA_SELECTOR = "0xbf92857c"


def encode_address(address: str) -> str:
    """Encode address as 32-byte ABI parameter."""
    return address.lower().replace("0x", "").zfill(64)


def decode_uint256(hex_str: str, offset: int) -> int:
    """Decode a uint256 from hex response at word offset."""
    start = 2 + (offset * 64)  # skip 0x prefix
    return int(hex_str[start:start + 64], 16)


def fetch_positions_for_chain(chain: str, user_address: str) -> None:
    """Fetch and print AAVE positions for a single chain using raw eth_call."""
    print(f"\n{'='*60}")
    print(f"  Chain: {chain}")
    print(f"{'='*60}")

    addresses = get_protocol_addresses(chain, "aave_v3")
    pool = addresses.get("pool")
    if not pool:
        print("  No pool address configured — skipping.")
        return

    print(f"  Pool: {pool}")

    provider = ApeRPCProvider(chain=chain, debug=True)
    try:
        provider.connect()
        print(f"  Connected to {chain}:mainnet")

        # Build calldata: getUserAccountData(address)
        calldata = GET_USER_ACCOUNT_DATA_SELECTOR + encode_address(user_address)

        result = provider.make_request(
            "eth_call",
            [{"to": pool, "data": calldata}, "latest"],
        )

        if not result or result == "0x":
            print("\n  Empty response — user has no AAVE positions on this chain.")
            return

        # Decode the 6 uint256 return values
        total_collateral_base = decode_uint256(result, 0)
        total_debt_base = decode_uint256(result, 1)
        available_borrows_base = decode_uint256(result, 2)
        current_liq_threshold = decode_uint256(result, 3)
        ltv = decode_uint256(result, 4)
        health_factor = decode_uint256(result, 5)

        # Base currency has 8 decimals, health factor has 18
        collateral_usd = total_collateral_base / 10**8
        debt_usd = total_debt_base / 10**8
        available_usd = available_borrows_base / 10**8
        hf = health_factor / 10**18 if total_debt_base > 0 else None

        if total_collateral_base == 0 and total_debt_base == 0:
            print("\n  No AAVE positions on this chain (zero collateral & debt).")
        else:
            print(f"\n  AAVE v3 Account Data:")
            print(f"    Total Collateral:  ${collateral_usd:,.2f}")
            print(f"    Total Debt:        ${debt_usd:,.2f}")
            print(f"    Available Borrows: ${available_usd:,.2f}")
            print(f"    Liq. Threshold:    {current_liq_threshold / 10**4:.2%}")
            print(f"    LTV:               {ltv / 10**4:.2%}")
            if hf is not None:
                print(f"    Health Factor:     {hf:.4f}")
            else:
                print(f"    Health Factor:     N/A (no debt)")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        traceback.print_exc()
    finally:
        provider.disconnect()
        print(f"  Disconnected from {chain}")


def main() -> None:
    """Fetch AAVE positions across all chains."""
    address = sys.argv[1] if len(sys.argv) > 1 else TARGET_ADDRESS
    print(f"Fetching AAVE v3 positions for: {address}")
    print(f"Chains to scan: {', '.join(CHAINS)}")

    for chain in CHAINS:
        fetch_positions_for_chain(chain, address)

    print(f"\n{'='*60}")
    print("  Scan complete.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
