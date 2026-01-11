"""CLI for crypto portfolio tracker."""

import json
from decimal import Decimal
from enum import StrEnum

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.traceback import install

# Import all protocol handlers to trigger auto-registration
from crypto_portfolio_tracker import protocols  # noqa: F401
from crypto_portfolio_tracker.core import ChainScanner, PositionAggregator
from crypto_portfolio_tracker.core.models import PortfolioSummary
from crypto_portfolio_tracker.core.registry import ProtocolRegistry
from crypto_portfolio_tracker.data import get_all_supported_chains
from crypto_portfolio_tracker.pricing import ChainlinkPricing, DeFiLlamaPricing
from crypto_portfolio_tracker.rpc import ApeRPCProvider

# Install rich traceback handler
install(show_locals=True)

# Global debug flag
DEBUG = False

app = typer.Typer(
    name="crypto-portfolio-tracker",
    help="Fetch DeFi staking/lending positions across multiple chains using pure RPC calls",
    add_completion=False,
)

console = Console()


class OutputFormat(StrEnum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"


def _connect_to_chain(chain: str, console: Console, debug: bool = False) -> ApeRPCProvider:
    """
    Connect to a specific chain.

    Parameters
    ----------
    chain : str
        Chain name
    console : Console
        Rich console for output
    debug : bool
        Enable debug output

    Returns
    -------
    ApeRPCProvider
        Connected RPC provider

    Raises
    ------
    typer.Exit
        If connection fails

    """
    rpc_provider = ApeRPCProvider(chain=chain)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Connecting to {chain} network...", total=None)
        try:
            rpc_provider.connect()
            progress.update(task, description=f"✓ Connected to {chain}")
            progress.stop()
            return rpc_provider
        except Exception as e:
            progress.stop()
            console.print(f"[bold red]Failed to connect to {chain}:[/bold red] {e}")
            console.print("[yellow]Make sure you have set WEB3_INFURA_PROJECT_ID environment variable[/yellow]")
            console.print("[dim]  Add to ~/.zshrc: export WEB3_INFURA_PROJECT_ID='your_project_id'[/dim]")
            raise typer.Exit(code=1)


@app.command()
def positions(
    address: str = typer.Argument(..., help="Wallet address to query"),
    chain: str | None = typer.Option(None, "--chain", "-c", help="Specific chain to query"),
    protocol: str | None = typer.Option(None, "--protocol", "-p", help="Specific protocol to query"),
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output"),
) -> None:
    """
    Get all DeFi positions for a wallet address.

    Examples:

        # Get all positions
        crypto-portfolio-tracker positions 0xABC...

        # Get positions on specific chain
        crypto-portfolio-tracker positions 0xABC... --chain ethereum

        # Get positions for specific protocol
        crypto-portfolio-tracker positions 0xABC... --protocol aave_v3

        # Output as JSON
        crypto-portfolio-tracker positions 0xABC... --format json
    """
    # Set global debug flag
    global DEBUG
    DEBUG = debug

    console.print(f"\n[bold cyan]Fetching positions for:[/bold cyan] {address}")
    if debug:
        console.print("[dim]Debug mode enabled[/dim]")

    # Initialize fallback pricing service
    defillama_pricing = DeFiLlamaPricing()

    rpc_providers = {}  # Track providers for cleanup

    try:
        # Fetch positions based on filters
        if protocol:
            # Protocol filter - scan specific protocol across specified chain(s)
            target_chain = chain or "ethereum"

            # Connect to network
            rpc_provider = _connect_to_chain(target_chain, console, debug)
            rpc_providers[target_chain] = rpc_provider

            # Create Chainlink pricing with DeFiLlama fallback
            pricing = ChainlinkPricing(rpc_provider=rpc_provider, fallback_pricing=defillama_pricing)

            scanner = ChainScanner(rpc_provider=rpc_provider, debug=debug)
            aggregator = PositionAggregator(
                scanner=scanner, pricing_service=pricing, rpc_provider=rpc_provider, debug=debug
            )

            if debug:
                console.print(f"[dim]Filtering by protocol: {protocol} on {target_chain}[/dim]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Fetching {protocol} positions...", total=None)
                portfolio = aggregator.get_positions_for_protocol(address, protocol, target_chain)
                progress.update(task, description=f"✓ Fetched {len(portfolio)} positions")

            # Convert to summary format
            summary = PortfolioSummary(
                address=address,
                positions=portfolio,
                total_usd_value=sum((p.usd_value or Decimal("0") for p in portfolio), Decimal("0")),
            )
        elif chain:
            # Single chain scan
            rpc_provider = _connect_to_chain(chain, console, debug)
            rpc_providers[chain] = rpc_provider

            # Create Chainlink pricing with DeFiLlama fallback
            pricing = ChainlinkPricing(rpc_provider=rpc_provider, fallback_pricing=defillama_pricing)

            scanner = ChainScanner(rpc_provider=rpc_provider, debug=debug)
            aggregator = PositionAggregator(
                scanner=scanner, pricing_service=pricing, rpc_provider=rpc_provider, debug=debug
            )

            if debug:
                console.print(f"[dim]Scanning chain: {chain}[/dim]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Scanning {chain} for positions...", total=None)
                positions_list = aggregator.get_positions_for_chain(address, chain)
                progress.update(task, description=f"✓ Found {len(positions_list)} positions")

            summary = PortfolioSummary(
                address=address,
                positions=positions_list,
                total_usd_value=sum((p.usd_value or Decimal("0") for p in positions_list), Decimal("0")),
            )
        else:
            # Multi-chain scan - scan all supported chains
            supported_chains = get_all_supported_chains()
            all_positions = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                main_task = progress.add_task(
                    f"Scanning {len(supported_chains)} chains...",
                    total=len(supported_chains),
                )

                for i, chain_name in enumerate(supported_chains):
                    progress.update(
                        main_task,
                        description=f"Scanning {chain_name}...",
                        completed=i,
                    )

                    try:
                        # Connect to this chain
                        rpc_provider = ApeRPCProvider(chain=chain_name)
                        rpc_provider.connect()
                        rpc_providers[chain_name] = rpc_provider

                        # Create Chainlink pricing with DeFiLlama fallback for this chain
                        pricing = ChainlinkPricing(rpc_provider=rpc_provider, fallback_pricing=defillama_pricing)

                        # Scan this chain
                        scanner = ChainScanner(rpc_provider=rpc_provider, debug=debug)
                        aggregator = PositionAggregator(
                            scanner=scanner,
                            pricing_service=pricing,
                            rpc_provider=rpc_provider,
                            debug=debug,
                        )

                        positions = aggregator.get_positions_for_chain(address, chain_name)
                        all_positions.extend(positions)

                        if debug:
                            console.print(f"[dim]Found {len(positions)} positions on {chain_name}[/dim]")

                    except Exception as e:
                        if debug:
                            console.print(f"[dim]Error scanning {chain_name}: {e}[/dim]")
                        continue

                progress.update(main_task, description="✓ Scan complete", completed=len(supported_chains))

            # Build summary
            summary = PortfolioSummary(
                address=address,
                positions=all_positions,
                total_usd_value=sum((p.usd_value or Decimal("0") for p in all_positions), Decimal("0")),
            )

        # Output results
        if format == OutputFormat.JSON:
            _output_json(summary)
        else:
            _output_table(summary)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if debug:
            # Rich traceback will automatically handle this
            raise
        raise typer.Exit(1)
    finally:
        # Cleanup all RPC provider connections
        for provider in rpc_providers.values():
            try:
                provider.disconnect()
            except Exception:
                pass
        pricing.close()


@app.command()
def list_protocols() -> None:
    """List all supported protocols."""
    protocol_handlers = ProtocolRegistry.get_all_handlers()

    table = Table(title="Supported Protocols", show_header=True, header_style="bold magenta")
    table.add_column("Protocol", style="cyan")
    table.add_column("Supported Chains", style="green")
    table.add_column("Position Types", style="yellow")

    for handler_class in protocol_handlers:
        # No RPC provider needed for listing metadata
        handler = handler_class(rpc_provider=None)
        chains = ", ".join(handler.supported_chains)
        table.add_row(handler.name, chains, "All types")

    console.print(table)


@app.command()
def list_chains() -> None:
    """List all supported chains."""
    chains = get_all_supported_chains()

    table = Table(title="Supported Chains", show_header=True, header_style="bold magenta")
    table.add_column("Chain", style="cyan")
    table.add_column("Status", style="green")

    for chain in chains:
        table.add_row(chain, "✓ Active")

    console.print(table)


def _output_table(summary) -> None:
    """Output portfolio as rich table."""
    if not summary.positions:
        console.print("\n[yellow]No positions found[/yellow]")
        return

    # Main positions table
    table = Table(
        title=f"Portfolio for {summary.address[:10]}...{summary.address[-8:]}",
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Protocol", style="cyan")
    table.add_column("Chain", style="blue")
    table.add_column("Type", style="yellow")
    table.add_column("Token", style="green")
    table.add_column("Balance", style="white", justify="right")
    table.add_column("USD Value", style="bold green", justify="right")

    for position in summary.positions:
        balance_str = f"{position.balance:,.4f}"
        usd_str = f"${position.usd_value:,.2f}" if position.usd_value else "-"

        table.add_row(
            position.protocol,
            position.chain,
            position.position_type.value,
            position.token.symbol,
            balance_str,
            usd_str,
        )

    console.print("\n")
    console.print(table)

    # Summary table
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Label", style="bold")
    summary_table.add_column("Value", style="bold green")

    summary_table.add_row("Total Value:", f"${summary.total_usd_value:,.2f}")
    summary_table.add_row("Total Positions:", str(len(summary.positions)))

    if summary.by_chain:
        summary_table.add_row("", "")
        summary_table.add_row("[bold]By Chain:[/bold]", "")
        for chain, value in summary.by_chain.items():
            summary_table.add_row(f"  {chain}", f"${value:,.2f}")

    if summary.by_protocol:
        summary_table.add_row("", "")
        summary_table.add_row("[bold]By Protocol:[/bold]", "")
        for protocol, value in summary.by_protocol.items():
            summary_table.add_row(f"  {protocol}", f"${value:,.2f}")

    console.print("\n")
    console.print(summary_table)
    console.print("\n")


def _output_json(summary) -> None:
    """Output portfolio as JSON."""

    def decimal_default(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        raise TypeError

    # Convert Pydantic model to dict
    data = summary.model_dump(mode="json")

    # Pretty print JSON
    json_str = json.dumps(data, indent=2, default=decimal_default)
    console.print(json_str)


if __name__ == "__main__":
    app()
