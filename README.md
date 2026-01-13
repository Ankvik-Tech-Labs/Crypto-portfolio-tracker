# Crypto Portfolio Tracker

A high-performance Python CLI tool to fetch DeFi staking/lending positions for any wallet address across multiple chains using on-chain RPC calls with accurate Chainlink pricing.

## Features

- **On-Chain Pricing**: Chainlink price feeds for accurate real-time USD values
- **Pure RPC**: Direct blockchain queries with intelligent fallbacks
- **Multi-Chain**: Ethereum, Base, Arbitrum, Optimism, Polygon (easily extensible)
- **Multi-Protocol**: Aave v3, Lido, Morpho, Ether.fi, Beefy
- **Auto-Discovery**: Event log-based position detection
- **Performance Optimized**: Parallel chain scanning + multicall batching
- **Beautiful CLI**: Rich tables and JSON output
- **Extensible**: Plugin-based protocol architecture
- **Type-Safe**: Full Pydantic models and type hints

## Architecture

```
CLI (Typer + Rich)
        ↓
 PositionAggregator
├─→ ChainScanner (parallel log-based discovery)
├─→ ProtocolRegistry (auto-registration)
│   ├─→ AaveHandler
│   ├─→ LidoHandler
│   ├─→ MorphoHandler
│   ├─→ EtherfiHandler (with AccountantWithRateProviders integration)
│   └─→ BeefyHandler
├─→ ChainlinkPricing (50+ price feeds across 5 chains)
│   └─→ DeFiLlama Fallback (for tokens without Chainlink feeds)
└─→ RPC Layer (provider, retry, cache, multicall batching)
```

## Installation

### Prerequisites

- Python 3.11+
- [Hatch](https://hatch.pypa.io/latest/) (package manager)
- [UV](https://github.com/astral-sh/uv) (fast Python package installer)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/crypto-portfolio-tracker.git
cd crypto-portfolio-tracker

# Install dependencies (UV will be used automatically)
hatch env create

# Activate the environment
hatch shell
```

## Usage

### Command Line Interface

#### Get All Positions

```bash
crypto-portfolio-tracker positions 0xYourAddressHere
```

**Example Output:**
```
                Portfolio for 0xBFbeD871...87c474bA
┏━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Protocol ┃ Chain    ┃ Type  ┃ Token       ┃  Balance ┃ USD Value ┃
┡━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━┩
│ etherfi  │ ethereum │ vault │ LiquidVault │ 440.0301 │   $500.41 │
│ lido     │ ethereum │ stake │ stETH       │  12.5000 │ $3,125.00 │
│ aave_v3  │ base     │ lend  │ aUSDC       │ 1000.000 │ $1,000.50 │
└──────────┴──────────┴───────┴─────────────┴──────────┴───────────┘

Total Portfolio Value: $4,625.91
```

#### Filter by Chain

```bash
crypto-portfolio-tracker positions 0xYourAddress --chain ethereum
```

#### Filter by Protocol

```bash
crypto-portfolio-tracker positions 0xYourAddress --protocol aave_v3
```

#### Debug Mode (Show Pricing Calculations)

```bash
crypto-portfolio-tracker positions 0xYourAddress --debug
```

**Example Debug Output:**
```
[DEBUG] Pricing etherfi: 500.550916667356 USDC × $0.99970951 = $500.40551163157329975556
[DEBUG] Exchange rate: 1.137538 USDC per share
[DEBUG] Underlying value: 500.55 USDC
```

#### JSON Output

```bash
crypto-portfolio-tracker positions 0xYourAddress --format json
```

#### List Supported Protocols

```bash
crypto-portfolio-tracker list-protocols
```

**Output:**
```
Registered Protocols:
  - aave_v3 (chains: ethereum, base, arbitrum, optimism, polygon)
  - lido (chains: ethereum)
  - morpho (chains: ethereum)
  - etherfi (chains: ethereum)
  - beefy (chains: base, arbitrum, optimism, polygon)
```

#### List Supported Chains

```bash
crypto-portfolio-tracker list-chains
```

**Output:**
```
Supported Chains:
  - ethereum (Chain ID: 1)
  - base (Chain ID: 8453)
  - arbitrum (Chain ID: 42161)
  - optimism (Chain ID: 10)
  - polygon (Chain ID: 137)
```

### Python API

```python
from crypto_portfolio_tracker.core import ChainScanner, PositionAggregator
from crypto_portfolio_tracker.pricing import ChainlinkPricing, DeFiLlamaPricing
from crypto_portfolio_tracker.rpc import MultiRPCProvider

# Initialize RPC provider
rpc_provider = MultiRPCProvider(
    chain="ethereum",
    rpc_endpoints=["https://eth.llamarpc.com", "https://rpc.ankr.com/eth"]
)

# Initialize pricing with Chainlink + DeFiLlama fallback
defillama = DeFiLlamaPricing()
pricing = ChainlinkPricing(rpc_provider=rpc_provider, fallback_pricing=defillama)

# Initialize scanner and aggregator
scanner = ChainScanner(rpc_provider=rpc_provider)
aggregator = PositionAggregator(scanner=scanner, pricing_service=pricing)

# Fetch portfolio (uses parallel chain scanning)
portfolio = aggregator.get_all_positions("0xYourAddress")

print(f"Total Value: ${portfolio.total_usd_value}")
print(f"Positions: {len(portfolio.positions)}")

for position in portfolio.positions:
    print(f"{position.protocol} - {position.token.symbol}: {position.balance}")
```

## Project Structure

```
crypto-portfolio-tracker/
├── src/crypto_portfolio_tracker/
│   ├── cli/                        # CLI interface (Typer)
│   │   └── main.py
│   ├── core/                       # Core logic
│   │   ├── aggregator.py          # Position orchestration + parallel scanning
│   │   ├── scanner.py             # Chain/protocol discovery
│   │   ├── models.py              # Pydantic data models
│   │   └── registry.py            # Protocol handler registry
│   ├── protocols/                  # Protocol handlers
│   │   ├── base.py                # Base handler class
│   │   ├── aave.py                # Aave v3
│   │   ├── lido.py                # Lido liquid staking
│   │   ├── morpho.py              # Morpho Blue
│   │   ├── etherfi.py             # Ether.fi restaking + vault
│   │   └── beefy.py               # Beefy vaults
│   ├── rpc/                        # RPC layer
│   │   ├── provider.py            # Multi-RPC provider
│   │   ├── retry.py               # Retry with backoff
│   │   ├── cache.py               # TTL cache
│   │   └── multicall.py           # Batch calls (Multicall3)
│   ├── pricing/                    # Pricing services
│   │   ├── chainlink.py           # Chainlink price feeds (primary)
│   │   └── defillama.py           # DeFiLlama integration (fallback)
│   └── data/                       # Configuration
│       ├── addresses.py           # ✨ Centralized contract addresses
│       ├── contracts.yaml         # Chain configs + RPC endpoints
│       ├── loader.py              # Config loader
│       └── __init__.py            # Exports
├── tests/                          # Test suite
├── pyproject.toml                 # Hatch config
├── ape-config.yaml                # Ape framework config
└── README.md
```

## Key Features Explained

### 1. Chainlink On-Chain Pricing

Uses Chainlink decentralized price oracles for accurate USD values:

```python
from crypto_portfolio_tracker.pricing import ChainlinkPricing

pricing = ChainlinkPricing(rpc_provider=rpc_provider)

# Automatically uses Chainlink feeds when available
# Falls back to DeFiLlama for tokens without feeds
prices = pricing.get_prices([
    ("ethereum", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"),  # USDC
    ("ethereum", "0xdAC17F958D2ee523a2206206994597C13D831ec7"),  # USDT
])
```

**Supported Price Feeds:**
- **Ethereum**: 20+ tokens (USDC, USDT, DAI, ETH, wstETH, cbETH, etc.)
- **Base**: 10+ tokens (USDC, ETH, cbBTC, etc.)
- **Arbitrum**: 15+ tokens
- **Optimism**: 10+ tokens
- **Polygon**: 10+ tokens

**Total**: 50+ Chainlink price feeds across 5 chains.

### 2. Centralized Address Management

All contract addresses in one place for easy maintenance:

```python
# src/crypto_portfolio_tracker/data/addresses.py

CHAINLINK_PRICE_FEEDS = {
    "ethereum": {
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",  # USDC/USD
        # ... 50+ more feeds
    },
}

PROTOCOL_ADDRESSES = {
    "etherfi": {
        "ethereum": {
            "eeth": "0x35fA164735182de50811E8e2E824cFb9B6118ac2",
            "weeth": "0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee",
            "liquid_vault": "0x08c6F91e2B681FaF5e17227F2a44C307b3C1364C",
            "liquid_vault_accountant": "0xc315D6e14DDCDC7407784e2Caf815d131Bc1D3E7",
        },
    },
}

MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"
```

### 3. Vault Pricing with Accountant Contracts

Handles complex vault architectures like Ether.fi's BoringVault + AccountantWithRateProviders:

```python
# Query vault shares
vault_balance = 440.030062  # LiquidVault shares (6 decimals)

# Query exchange rate from accountant contract
accountant = "0xc315D6e14DDCDC7407784e2Caf815d131Bc1D3E7"
exchange_rate = accountant.getRate()  # Returns 1.137538 USDC per share

# Calculate underlying USDC balance
underlying_usdc = vault_balance × exchange_rate  # = 500.55 USDC

# Price underlying asset using Chainlink
usdc_price = chainlink.get_price("ethereum", USDC_ADDRESS)  # $0.9997
usd_value = underlying_usdc × usdc_price  # = $500.41
```

### 4. Parallel Chain Scanning

Uses `ThreadPoolExecutor` for concurrent chain queries:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

# Scan multiple chains in parallel (2-4x speedup)
with ThreadPoolExecutor(max_workers=min(len(chains), 4)) as executor:
    futures = {
        executor.submit(fetch_chain_positions, chain): chain
        for chain in ["ethereum", "base", "arbitrum"]
    }

    for future in as_completed(futures):
        positions.extend(future.result())
```

### 5. Multicall Batching

Combines multiple contract calls into single RPC request:

```python
from crypto_portfolio_tracker.rpc.multicall import MulticallBatcher

multicall = MulticallBatcher(rpc_provider)

# Add multiple calls to batch
balance_idx = multicall.add_call(token_address, "balanceOf", [user_address])
decimals_idx = multicall.add_call(token_address, "decimals", [])
rate_idx = multicall.add_call(accountant_address, "getRate", [])

# Execute all calls in single RPC request (5-10x faster)
results = multicall.execute()

balance = results[balance_idx]
decimals = results[decimals_idx]
rate = results[rate_idx]
```

## Adding a New Protocol

### 1. Create Handler

```python
# src/crypto_portfolio_tracker/protocols/compound.py
from decimal import Decimal
from crypto_portfolio_tracker.core.models import Position, PositionType, Token
from crypto_portfolio_tracker.core.registry import ProtocolRegistry
from crypto_portfolio_tracker.protocols.base import BaseProtocolHandler
from crypto_portfolio_tracker.rpc.multicall import MulticallBatcher

@ProtocolRegistry.register
class CompoundHandler(BaseProtocolHandler):
    name = "compound_v3"
    supported_chains = ["ethereum", "base"]
    discovery_events = [
        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",  # Supply event
    ]

    def get_positions(self, user_address: str, chain: str) -> list[Position]:
        positions = []

        # 1. Get contract addresses
        addresses = self.get_contract_addresses(chain)

        # 2. Use multicall for efficient batch queries
        multicall = MulticallBatcher(self.rpc_provider)

        balance_idx = multicall.add_call(addresses["comet"], "balanceOf", [user_address])
        decimals_idx = multicall.add_call(addresses["comet"], "decimals", [])

        results = multicall.execute()

        balance_raw = results[balance_idx]
        decimals = results[decimals_idx]

        # 3. Create Position objects
        if balance_raw > 0:
            balance = Decimal(str(balance_raw)) / Decimal(10**decimals)

            positions.append(Position(
                protocol=self.name,
                chain=chain,
                position_type=PositionType.LENDING_SUPPLY,
                token=Token(
                    address=addresses["comet"],
                    symbol="cUSDC",
                    decimals=decimals,
                    name="Compound USDC",
                ),
                balance=balance,
            ))

        return positions
```

### 2. Add Contract Addresses

```python
# src/crypto_portfolio_tracker/data/addresses.py

PROTOCOL_ADDRESSES = {
    # ... existing protocols ...
    "compound_v3": {
        "ethereum": {
            "comet": "0xc3d688B66703497DAA19211EEdff47f25384cdc3",
            "rewards": "0x1B0e765F6224C21223AeA2af16c1C46E38885a40",
        },
        "base": {
            "comet": "0xb125E6687d4313864e53df431d5425969c15Eb2F",
            "rewards": "0x123...",
        },
    },
}
```

### 3. Import Handler

```python
# src/crypto_portfolio_tracker/protocols/__init__.py
from crypto_portfolio_tracker.protocols.compound import CompoundHandler

__all__ = [..., "CompoundHandler"]
```

### 4. Test

```bash
crypto-portfolio-tracker list-protocols
# Should show compound_v3

crypto-portfolio-tracker positions 0xAddress --protocol compound_v3 --debug
```

## Adding a New Chain

### 1. Update Ape Config

```yaml
# ape-config.yaml
arbitrum:
  default_network: mainnet
  mainnet:
    required_confirmations: 0
```

### 2. Add Chain Configuration

```yaml
# src/crypto_portfolio_tracker/data/contracts.yaml
chains:
  arbitrum:
    chain_id: 42161
    rpc_endpoints:
      - https://arb1.arbitrum.io/rpc
      - https://arbitrum.llamarpc.com
    protocols:
      aave_v3:
        pool: "0x794a61358D6845594F94dc1DB02A252b5b4814aD"
```

### 3. Add Chainlink Price Feeds (Optional)

```python
# src/crypto_portfolio_tracker/data/addresses.py

CHAINLINK_PRICE_FEEDS = {
    # ... existing chains ...
    "arbitrum": {
        "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8": "0x50834F3163758fcC1Df9973b6e91f0F0F0434aD3",  # USDC/USD
        "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9": "0x3f3f5dF88dC9F13eac63DF89EC16ef6e7E25DdE7",  # USDT/USD
        # ... more feeds
    },
}
```

### 4. Update Protocol Handlers

```python
class AaveHandler(BaseProtocolHandler):
    supported_chains = ["ethereum", "base", "arbitrum"]  # Add new chain
```

## Development

### Run Linting

```bash
hatch run lint:lint
```

### Run Type Checking

```bash
hatch run lint:typing
```

### Run Tests

```bash
hatch run test:test
```

### Format Code

```bash
hatch run lint:lint
```

## Configuration

### RPC Endpoints

RPC endpoints are configured in `src/crypto_portfolio_tracker/data/contracts.yaml`:

```yaml
chains:
  ethereum:
    rpc_endpoints:
      - https://eth.llamarpc.com          # Primary
      - https://rpc.ankr.com/eth           # Fallback 1
      - https://ethereum.publicnode.com    # Fallback 2
```

The system automatically falls back to the next endpoint on failure.

### Contract Addresses

All contract addresses are centralized in `src/crypto_portfolio_tracker/data/addresses.py`:

```python
PROTOCOL_ADDRESSES = {
    "aave_v3": {
        "ethereum": {
            "pool": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
            "pool_data_provider": "0x7B4EB56E7CD4b454BA8ff71E4518426369a138a3",
        },
    },
}
```

Legacy YAML config in `contracts.yaml` is still supported via loader fallback.

## Data Models

### Position

```python
class Position(BaseModel):
    protocol: str                          # e.g., "aave_v3"
    chain: str                            # e.g., "ethereum"
    position_type: PositionType           # LENDING_SUPPLY, LENDING_BORROW, STAKING, VAULT
    token: Token                          # Position token (aToken, stETH, vault share)
    balance: Decimal                      # Token balance
    underlying_token: Token | None       # Underlying asset (USDC, ETH, etc.)
    underlying_balance: Decimal | None   # Underlying amount
    usd_value: Decimal | None            # USD value (from Chainlink)
    claimable_rewards: list[Reward]      # Claimable rewards
    apy: Decimal | None                  # Current APY
    health_factor: Decimal | None        # For lending positions
    metadata: dict                        # Protocol-specific data
```

### PortfolioSummary

```python
class PortfolioSummary(BaseModel):
    address: str                          # User wallet
    positions: list[Position]             # All positions
    total_usd_value: Decimal             # Total portfolio value
    by_chain: dict[str, Decimal]         # Value per chain
    by_protocol: dict[str, Decimal]      # Value per protocol
    total_claimable_rewards_usd: Decimal # Total rewards value
```

## Performance Optimizations

### Before Optimization
- **Time**: 10-20 seconds per query
- **RPC Calls**: 50+ sequential individual calls
- **Chains**: Scanned sequentially
- **Pricing**: DeFiLlama API only

### After Optimization
- **Time**: 1-2 seconds per query (10-20x faster)
- **RPC Calls**: 5-10 batched multicalls
- **Chains**: Parallel scanning with ThreadPoolExecutor
- **Pricing**: Chainlink on-chain feeds + DeFiLlama fallback

### Optimization Techniques Applied

1. **Parallel Chain Scanning** - ThreadPoolExecutor with max 4 workers (2-4x speedup)
2. **Multicall Batching** - Combine 5-10 calls into single RPC request (5-10x speedup)
3. **Chainlink On-Chain Pricing** - Batch price queries for multiple tokens (3x faster than API)
4. **Smart Caching** - TTL cache for RPC results and chain activity
5. **Optimized Event Scanning** - Recent blocks only (30-90 days vs full history)

## Testing

### Manual Testing

Since this tool queries real blockchain data, test with known addresses:

```bash
# Test with address known to have DeFi positions
crypto-portfolio-tracker positions 0xBFbeD8717AEB318Eb7cE20913dd7563287c474bA --debug

# Test specific protocol
crypto-portfolio-tracker positions 0xBFbeD8717AEB318Eb7cE20913dd7563287c474bA --protocol etherfi --debug

# Expected output:
# [DEBUG] Pricing etherfi: 500.550916667356 USDC × $0.99970951 = $500.40551163157329975556
#
#                 Portfolio for 0xBFbeD871...87c474bA
# ┏━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┓
# ┃ Protocol ┃ Chain    ┃ Type  ┃ Token       ┃  Balance ┃ USD Value ┃
# ┡━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━┩
# │ etherfi  │ ethereum │ vault │ LiquidVault │ 440.0301 │   $500.41 │
# └──────────┴──────────┴───────┴─────────────┴──────────┴───────────┘

# Test JSON output
crypto-portfolio-tracker positions 0xBFbeD8717AEB318Eb7cE20913dd7563287c474bA --format json
```

### Example Test Addresses

Use these verified wallet addresses to test the portfolio tracker with real DeFi positions:

#### Ether.fi Testing
```bash
# Small position (~$374)
crypto-portfolio-tracker positions 0xa670ebdaaa258311a7c33a5bf795f07b97c83430 --protocol etherfi
```

![Ether.fi Demo](media/demo-etherfi.gif)

#### Lido Testing
```bash
# Large stETH holder (~$65M)
crypto-portfolio-tracker positions 0xC13ABCDEED78EFcaDE757371BEABBBdfebE0B932 --protocol lido
```

![Lido stETH Demo](media/demo-lido.gif)

```bash
# Large wstETH holder (~$92.8M) - Also active on Aave, Spark, Ether.fi
crypto-portfolio-tracker positions 0xEd0C6079229E2d407672a117c22b62064f4a4312 --protocol lido
```

![Lido wstETH Demo](media/demo-lido-wsteth.gif)

```bash
# Another large stETH holder (~$61.5M)
crypto-portfolio-tracker positions 0x1fa6D78bc5c5336164563f7e9d3f5ccABea4F5A9 --protocol lido
```

#### Multi-Chain Testing
```bash
# Full multi-chain scan (all protocols across all chains)
crypto-portfolio-tracker positions 0x293Ed38530005620e4B28600f196a97E1125dAAc
```

![Multi-Chain Demo](media/demo-multi-chain.gif)

**Note**: These are real wallet addresses with active DeFi positions. Use them to verify your installation and test protocol integrations.

### Unit Tests

```bash
# Run all tests
hatch run test:test

# Run with coverage
hatch run test:test-cov-xml
```

### Test Structure

```python
# tests/test_pricing.py
from crypto_portfolio_tracker.pricing import ChainlinkPricing

def test_chainlink_pricing():
    """Test Chainlink price feed integration."""
    pricing = ChainlinkPricing(rpc_provider=mock_provider)

    # Should fetch USDC price from Chainlink
    prices = pricing.get_prices([
        ("ethereum", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
    ])

    assert prices[("ethereum", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")] > 0
```

## Current Status

### ✅ Completed

- ✅ Project structure with Hatch + UV
- ✅ Protocol handler registry with auto-registration
- ✅ 5 protocol handlers (Aave, Lido, Morpho, Ether.fi, Beefy)
- ✅ Multi-chain support (Ethereum, Base, Arbitrum, Optimism, Polygon)
- ✅ Chain scanner with event log discovery
- ✅ Position aggregator with parallel chain scanning
- ✅ **Chainlink price integration (50+ feeds across 5 chains)**
- ✅ **DeFiLlama fallback pricing**
- ✅ CLI with table and JSON output
- ✅ RPC layer with retry, fallback, and caching
- ✅ **Multicall batching implementation**
- ✅ Type-safe Pydantic models
- ✅ **Centralized contract address registry (addresses.py)**
- ✅ **Vault pricing with accountant contracts (Ether.fi BoringVault)**
- ✅ **Performance optimizations (10-20x faster)**

### 🚧 Future Enhancements

1. **Additional Protocols**:
   - Compound v3
   - Uniswap v3 LP positions
   - Curve pools
   - Convex staking

2. **Enhanced Features**:
   - Historical position tracking
   - APY calculations for all protocols
   - Impermanent loss tracking for LP positions
   - Transaction cost tracking

3. **Advanced Optimizations**:
   - WebSocket subscriptions for real-time updates
   - GraphQL indexer integration (The Graph)
   - Local event cache database

4. **Monitoring & Alerts**:
   - Portfolio value change notifications
   - Health factor warnings for lending positions
   - Reward claiming reminders

## Troubleshooting

### "No positions found"

- Ensure the address has DeFi positions on supported protocols
- Check that RPC endpoints are accessible
- Try debug mode to see detection logs: `--debug`
- Try a known address with positions

### Balance Shows as 0

- Check if token uses non-standard decimals (not 18)
- Enable debug mode to see raw contract values
- Verify contract address in `addresses.py`
- For vaults: check if accountant contract is configured

### Incorrect USD Values

- Verify Chainlink price feed exists for the token
- Check if token needs underlying asset pricing (vaults)
- Enable debug mode to see pricing calculations
- Verify exchange rate calculation for vault shares

### RPC Connection Errors

- Check your internet connection
- Verify RPC endpoints in `contracts.yaml`
- Try different RPC providers
- Check for rate limiting (use dedicated RPC endpoint)

### Import Errors

- Ensure environment is activated: `hatch shell`
- Reinstall dependencies: `hatch env remove default && hatch env create`

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-protocol`
3. Make your changes
4. Run linting: `hatch run lint:lint`
5. Run tests: `hatch run test:test`
6. Commit changes: `git commit -m "Add Compound v3 handler"`
7. Push to branch: `git push origin feature/new-protocol`
8. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Built with [Ape](https://apeworx.io/) for Ethereum interactions
- Uses [Chainlink](https://chain.link/) for on-chain price oracles
- Uses [DeFiLlama](https://defillama.com/) for fallback price data
- Powered by [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/)
- Project management with [Hatch](https://hatch.pypa.io/)
- Fast package installation with [UV](https://github.com/astral-sh/uv)

---

**Note**: This project queries real blockchain data. RPC rate limits may apply. For production use, consider running your own RPC node or using paid RPC services.

**Performance**: Optimized for 1-2 second response times using parallel scanning, multicall batching, and on-chain Chainlink pricing.
