"""Position aggregator for orchestrating position fetching across chains and protocols."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Any

from rich.console import Console

from crypto_portfolio_tracker.core.models import PortfolioSummary, Position
from crypto_portfolio_tracker.core.registry import ProtocolRegistry
from crypto_portfolio_tracker.core.scanner import ChainScanner


class PositionAggregator:
    """
    Orchestrates position fetching across all chains and protocols.

    Workflow:
    1. Detect active chains (via ChainScanner)
    2. Discover protocols on each chain (via event logs)
    3. Fetch positions from each protocol handler
    4. Enrich positions with USD pricing
    5. Aggregate into portfolio summary

    Parameters
    ----------
    scanner : ChainScanner
        Chain scanner instance
    pricing_service : Any
        Pricing service for USD value enrichment
    rpc_provider : Any | None
        RPC provider for contract calls (optional, defaults to scanner's provider)

    """

    def __init__(
        self,
        scanner: ChainScanner,
        pricing_service: Any,
        rpc_provider: Any | None = None,
        debug: bool = False,
    ) -> None:
        self.scanner = scanner
        self.pricing_service = pricing_service
        self.rpc_provider = rpc_provider or scanner.rpc_provider
        self.debug = debug

    def get_all_positions(
        self,
        user_address: str,
        progress: Any | None = None,
        task_id: Any | None = None,
    ) -> PortfolioSummary:
        """
        Get all positions for a user across all chains and protocols.

        Parameters
        ----------
        user_address : str
            User wallet address
        progress : Any | None
            Rich progress bar instance (optional)
        task_id : Any | None
            Task ID for progress updates (optional)

        Returns
        -------
        PortfolioSummary
            Complete portfolio with all positions and aggregations

        """
        all_positions = []

        if self.debug:
            pass

        # Scan all chains for activity
        if progress and task_id:
            progress.update(task_id, description="Scanning chains for activity...", completed=20)

        chain_activities = self.scanner.scan_all_chains(user_address)

        if self.debug:
            sum(1 for a in chain_activities if a.has_activity)

        # For each active chain, fetch positions from detected protocols IN PARALLEL
        active_chains = [a for a in chain_activities if a.has_activity]

        if not active_chains:
            if self.debug:
                pass
            return PortfolioSummary(
                address=user_address,
                positions=[],
                total_usd_value=Decimal(0),
                by_chain={},
                by_protocol={},
                total_claimable_rewards_usd=Decimal(0),
            )

        if self.debug:
            pass

        # Execute chain position fetching in parallel
        with ThreadPoolExecutor(max_workers=min(len(active_chains), 4)) as executor:
            # Submit all chain scans
            future_to_chain = {
                executor.submit(
                    self._get_chain_positions_with_debug,
                    user_address,
                    activity.chain,
                    activity.protocols_detected,
                ): activity
                for activity in active_chains
            }

            # Collect results as they complete
            for i, future in enumerate(as_completed(future_to_chain)):
                activity = future_to_chain[future]

                if progress and task_id:
                    percent = 20 + (60 * (i + 1) // len(active_chains))
                    progress.update(
                        task_id,
                        description=f"Fetching positions from {activity.chain}...",
                        completed=percent,
                    )

                try:
                    chain_positions = future.result(timeout=30)
                    all_positions.extend(chain_positions)
                except Exception:
                    if self.debug:
                        pass
                    # Continue with other chains even if one fails

        if self.debug:
            pass

        # Enrich with USD pricing
        if progress and task_id:
            progress.update(task_id, description="Fetching USD prices...", completed=80)

        enriched_positions = self._enrich_positions_with_pricing(all_positions)

        # Build summary
        if progress and task_id:
            progress.update(task_id, description="Building portfolio summary...", completed=95)

        summary = self._build_portfolio_summary(user_address, enriched_positions)

        if progress and task_id:
            progress.update(task_id, description="✓ Scan complete", completed=100)

        return summary

    def get_positions_for_chain(
        self,
        user_address: str,
        chain: str,
    ) -> list[Position]:
        """
        Get all positions for a user on a specific chain.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name

        Returns
        -------
        list[Position]
            All positions on this chain

        """
        # Scan chain for protocol activity
        activity = self.scanner.scan_chain(user_address, chain)

        if not activity.has_activity:
            return []

        # Fetch positions from detected protocols
        positions = self._get_chain_positions(
            user_address,
            chain,
            activity.protocols_detected,
        )

        # Enrich with pricing
        return self._enrich_positions_with_pricing(positions)

    def get_positions_for_protocol(
        self,
        user_address: str,
        protocol_name: str,
        chain: str | None = None,
    ) -> list[Position]:
        """
        Get positions for a specific protocol.

        Parameters
        ----------
        user_address : str
            User wallet address
        protocol_name : str
            Protocol identifier
        chain : str | None
            Specific chain, or None for all chains

        Returns
        -------
        list[Position]
            Protocol positions

        """
        handler_class = ProtocolRegistry.get_handler(protocol_name)
        if not handler_class:
            return []

        positions = []

        # Determine which chains to query
        if chain:
            chains = [chain] if chain in handler_class.supported_chains else []
        else:
            chains = handler_class.supported_chains

        # Fetch from each chain
        for chain_name in chains:
            handler = handler_class(rpc_provider=self.rpc_provider)
            chain_positions = handler.get_positions(user_address, chain_name)
            positions.extend(chain_positions)

        # Enrich with pricing
        return self._enrich_positions_with_pricing(positions)

    def _get_chain_positions(
        self,
        user_address: str,
        chain: str,
        protocols: list[str],
    ) -> list[Position]:
        """
        Fetch positions from multiple protocols on a chain.

        Parameters
        ----------
        user_address : str
            User address
        chain : str
            Chain name
        protocols : list[str]
            Protocol names to query

        Returns
        -------
        list[Position]
            All positions found

        """
        positions = []

        for protocol_name in protocols:
            if self.debug:
                pass

            handler_class = ProtocolRegistry.get_handler(protocol_name)
            if not handler_class:
                if self.debug:
                    pass
                continue

            # Instantiate handler and fetch positions
            handler = handler_class(rpc_provider=self.rpc_provider)
            try:
                protocol_positions = handler.get_positions(user_address, chain)
                if self.debug:
                    pass
                positions.extend(protocol_positions)
            except Exception as e:
                # Log error but continue with other protocols
                if self.debug:
                    console = Console()
                    console.print(f"[red]Error fetching {protocol_name} positions on {chain}: {e}[/red]")
                    console.print_exception()
                continue

        return positions

    def _get_chain_positions_with_debug(self, user_address: str, chain: str, protocols: list[str]) -> list[Position]:
        """
        Get positions for a chain with debug output (thread-safe wrapper).

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name
        protocols : list[str]
            Protocols detected on this chain

        Returns
        -------
        list[Position]
            Positions found on this chain

        """
        if self.debug:
            pass

        positions = self._get_chain_positions(user_address, chain, protocols)

        if self.debug:
            pass

        return positions

    def _enrich_positions_with_pricing(
        self,
        positions: list[Position],
    ) -> list[Position]:
        """
        Add USD values to positions using pricing service.

        Parameters
        ----------
        positions : list[Position]
            Positions to enrich

        Returns
        -------
        list[Position]
            Positions with USD values

        """
        if not positions:
            return positions

        # Collect unique tokens for price lookup
        tokens_to_price = {}
        for position in positions:
            key = (position.chain, position.token.address)
            tokens_to_price[key] = position.token

            if position.underlying_token:
                key = (position.chain, position.underlying_token.address)
                tokens_to_price[key] = position.underlying_token

        # Fetch all prices in batch
        prices = self.pricing_service.get_prices(list(tokens_to_price.keys()))

        # Enrich positions
        for position in positions:
            # For vault positions with underlying tokens, price the underlying balance
            # This ensures we get USD value based on the actual underlying asset (e.g., USDC)
            if position.underlying_token and position.underlying_balance:
                underlying_key = (position.chain, position.underlying_token.address)
                underlying_price = prices.get(underlying_key, Decimal("0"))

                if underlying_price > 0:
                    position.usd_value = position.underlying_balance * underlying_price
                    if self.debug:
                        pass
                else:
                    # Fallback to pricing vault shares if underlying price not available
                    token_key = (position.chain, position.token.address)
                    token_price = prices.get(token_key, Decimal("0"))
                    if token_price > 0:
                        position.usd_value = position.balance * token_price
            else:
                # For non-vault positions, price the token directly
                token_key = (position.chain, position.token.address)
                token_price = prices.get(token_key, Decimal("0"))

                if token_price > 0:
                    position.usd_value = position.balance * token_price

            # Enrich rewards
            for reward in position.claimable_rewards:
                reward_key = (position.chain, reward.token.address)
                reward_price = prices.get(reward_key, Decimal("0"))
                if reward_price > 0:
                    reward.usd_value = reward.amount * reward_price

        return positions

    def _build_portfolio_summary(
        self,
        user_address: str,
        positions: list[Position],
    ) -> PortfolioSummary:
        """
        Build aggregated portfolio summary.

        Parameters
        ----------
        user_address : str
            User address
        positions : list[Position]
            All positions

        Returns
        -------
        PortfolioSummary
            Aggregated summary

        """
        total_usd = Decimal("0")
        by_chain: dict[str, Decimal] = {}
        by_protocol: dict[str, Decimal] = {}
        total_rewards_usd = Decimal("0")

        for position in positions:
            pos_value = position.usd_value or Decimal("0")
            total_usd += pos_value

            # Aggregate by chain
            by_chain[position.chain] = by_chain.get(position.chain, Decimal("0")) + pos_value

            # Aggregate by protocol
            by_protocol[position.protocol] = by_protocol.get(position.protocol, Decimal("0")) + pos_value

            # Sum rewards
            for reward in position.claimable_rewards:
                total_rewards_usd += reward.usd_value or Decimal("0")

        return PortfolioSummary(
            address=user_address,
            positions=positions,
            total_usd_value=total_usd,
            by_chain=by_chain,
            by_protocol=by_protocol,
            total_claimable_rewards_usd=total_rewards_usd,
        )
