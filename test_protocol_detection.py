"""Test protocol detection from token symbols."""

# Simulated test cases based on the summary output
test_cases = [
    {
        "token_symbol": "aBasUSDC",
        "position_name": "",
        "expected_protocol": "aave",
        "description": "Aave aToken on Base",
    },
    {
        "token_symbol": "steakUSDC",
        "position_name": "",
        "expected_protocol": "morpho",
        "description": "Morpho Steakhouse vault",
    },
    {
        "token_symbol": "sparkUSDC",
        "position_name": "",
        "expected_protocol": "morpho",
        "description": "Morpho Spark vault",
    },
    {
        "token_symbol": "USDC",
        "position_name": "Spark USDC Vault",
        "expected_protocol": "morpho",
        "description": "Morpho vault from position name",
    },
    {
        "token_symbol": "mooBeefyUSDC",
        "position_name": "",
        "expected_protocol": "beefy",
        "description": "Beefy mooToken",
    },
    {
        "token_symbol": "weETH",
        "position_name": "",
        "expected_protocol": "etherfi",
        "description": "Ether.fi wrapped eETH",
    },
    {
        "token_symbol": "stETH",
        "position_name": "",
        "expected_protocol": "lido",
        "description": "Lido stETH",
    },
    {
        "token_symbol": "USDC",
        "position_name": "",
        "expected_protocol": "wallet",
        "description": "Plain USDC (wallet)",
    },
]


def detect_protocol(token_symbol: str, position_name: str) -> str:
    """Replicate the _detect_protocol logic."""
    token_symbol = token_symbol.lower()
    position_name = position_name.lower()

    protocol_patterns = {
        "aave": ["abas", "aeth", "aopt", "apol", "aarb"],
        "morpho": ["steak", "spark", "steakhouse", "morpho"],
        "beefy": ["moo"],
        "etherfi": ["eeth", "weeth"],
        "lido": ["steth", "wsteth"],
    }

    # Check token symbol
    for protocol, patterns in protocol_patterns.items():
        for pattern in patterns:
            if pattern in token_symbol:
                return protocol

    # Check position name
    for protocol, patterns in protocol_patterns.items():
        for pattern in patterns:
            if pattern in position_name:
                return protocol

    # Check for vault/pool in position name
    if "vault" in position_name or "pool" in position_name:
        words = position_name.split()
        if len(words) > 0:
            first_word = words[0].lower()
            for protocol, patterns in protocol_patterns.items():
                if first_word in patterns or first_word == protocol:
                    return protocol

    return "wallet"


print("\nProtocol Detection Tests\n" + "=" * 80)

passed = 0
failed = 0

for test in test_cases:
    detected = detect_protocol(test["token_symbol"], test["position_name"])
    status = "✓" if detected == test["expected_protocol"] else "✗"
    result = "PASS" if detected == test["expected_protocol"] else "FAIL"

    print(f"\n{status} {result}: {test['description']}")
    print(f"  Token: {test['token_symbol']}")
    if test["position_name"]:
        print(f"  Position: {test['position_name']}")
    print(f"  Expected: {test['expected_protocol']}")
    print(f"  Detected: {detected}")

    if result == "PASS":
        passed += 1
    else:
        failed += 1

print(f"\n{'=' * 80}")
print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print()
