"""Aave v3 lending protocol handler."""

from decimal import Decimal

from crypto_portfolio_tracker.core.models import Position, PositionType, Reward, Token
from crypto_portfolio_tracker.core.registry import ProtocolRegistry
from crypto_portfolio_tracker.protocols.base import BaseProtocolHandler


@ProtocolRegistry.register
class AaveHandler(BaseProtocolHandler):
    """
    Handler for Aave v3 lending positions.

    Tracks supplied assets, borrowed assets, health factor, and rewards.

    """

    name = "aave_v3"
    supported_chains = ["ethereum", "base"]

    # Event signatures for discovery
    discovery_events = [
        "0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61",  # Supply
        "0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0",  # Borrow
    ]

    def get_positions(self, user_address: str, chain: str) -> list[Position]:
        """
        Fetch Aave positions for a user.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name

        Returns
        -------
        list[Position]
            List of Aave positions (supplies and borrows)

        """
        if chain not in self.supported_chains:
            return []

        positions = []
        addresses = self.get_contract_addresses(chain)

        # Get user account data
        account_data = self._get_user_account_data(user_address, addresses, chain)

        if not account_data:
            return []

        # Get supplied positions
        supply_positions = self._get_supply_positions(user_address, addresses, chain, account_data)
        positions.extend(supply_positions)

        # Get borrow positions
        borrow_positions = self._get_borrow_positions(user_address, addresses, chain, account_data)
        positions.extend(borrow_positions)

        return positions

    def _get_user_account_data(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
    ) -> dict | None:
        """
        Get user account summary from Aave.

        Parameters
        ----------
        user_address : str
            User address
        addresses : dict[str, str]
            Protocol addresses
        chain : str
            Chain name

        Returns
        -------
        dict | None
            Account data including total collateral, debt, health factor

        """
        pool_address = addresses.get("pool")
        if not pool_address:
            return None

        try:
            # Call getUserAccountData to get account summary
            result = self._make_contract_call(
                pool_address,
                "getUserAccountData",
                [user_address],
                chain,
            )
            # Returns tuple: (totalCollateralBase, totalDebtBase, availableBorrowsBase,
            #                 currentLiquidationThreshold, ltv, healthFactor)

            total_collateral_base = Decimal(str(result[0])) / Decimal(10**8)  # Base currency has 8 decimals
            total_debt_base = Decimal(str(result[1])) / Decimal(10**8)
            available_borrows_base = Decimal(str(result[2])) / Decimal(10**8)
            health_factor_raw = result[5]

            # Health factor is in WAD (10^18), but 0 means infinite (no debt)
            if total_debt_base == 0:
                health_factor = None
            else:
                health_factor = Decimal(str(health_factor_raw)) / Decimal(10**18)

            return {
                "total_collateral": total_collateral_base,
                "total_debt": total_debt_base,
                "available_borrows": available_borrows_base,
                "health_factor": health_factor,
                "ltv": Decimal(str(result[4])) / Decimal(10**4),  # LTV in basis points
            }

        except Exception:
            return None

    def _get_supply_positions(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
        account_data: dict,
    ) -> list[Position]:
        """
        Get all supply positions from Aave.

        Parameters
        ----------
        user_address : str
            User address
        addresses : dict[str, str]
            Protocol addresses
        chain : str
            Chain name
        account_data : dict
            User account summary data

        Returns
        -------
        list[Position]
            List of supply positions

        """
        positions = []

        # If user has collateral, they have supply positions
        if account_data.get("total_collateral", 0) == 0:
            return positions

        # Create a summary position showing total collateral value
        # TODO: Implement detailed per-asset positions by querying pool_data_provider
        summary_token = Token(
            address="",
            symbol="USD",
            decimals=8,
            name="USD Base Currency",
        )

        summary_position = Position(
            protocol=self.name,
            chain=chain,
            position_type=PositionType.LENDING_SUPPLY,
            token=summary_token,
            balance=account_data["total_collateral"],
            underlying_token=None,
            underlying_balance=None,
            usd_value=account_data["total_collateral"],
            health_factor=account_data.get("health_factor"),
            metadata={
                "is_summary": True,
                "total_collateral_usd": float(account_data["total_collateral"]),
                "total_debt_usd": float(account_data.get("total_debt", 0)),
                "ltv": float(account_data.get("ltv", 0)),
                "note": "Summary position - individual assets not yet fetched",
            },
        )

        positions.append(summary_position)
        return positions

    def _get_borrow_positions(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
        account_data: dict,
    ) -> list[Position]:
        """
        Get all borrow positions from Aave.

        Parameters
        ----------
        user_address : str
            User address
        addresses : dict[str, str]
            Protocol addresses
        chain : str
            Chain name
        account_data : dict
            User account summary data

        Returns
        -------
        list[Position]
            List of borrow positions

        """
        positions = []

        # TODO: Similar to supply positions, query debt tokens
        # Borrow positions will have negative USD values or be marked differently

        return positions

    def _get_rewards(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
    ) -> list[Reward]:
        """
        Get claimable rewards from Aave incentives.

        Parameters
        ----------
        user_address : str
            User address
        addresses : dict[str, str]
            Protocol addresses
        chain : str
            Chain name

        Returns
        -------
        list[Reward]
            List of claimable rewards

        """
        rewards = []
        incentives_controller = addresses.get("incentives_controller")

        if not incentives_controller:
            return rewards

        # TODO: Implement rewards fetching
        # rewards_balance = self._make_contract_call(
        #     incentives_controller,
        #     "getRewardsBalance(address[],address)",
        #     [asset_addresses, user_address],
        #     chain,
        # )

        return rewards

    def _create_supply_position(
        self,
        reserve_token: Token,
        atoken_address: str,
        balance: Decimal,
        chain: str,
        account_data: dict,
        is_collateral: bool,
        apy: Decimal | None = None,
    ) -> Position:
        """
        Create a supply position object.

        Parameters
        ----------
        reserve_token : Token
            Underlying reserve token
        atoken_address : str
            aToken contract address
        balance : Decimal
            aToken balance
        chain : str
            Chain name
        account_data : dict
            User account data
        is_collateral : bool
            Whether asset is used as collateral
        apy : Decimal | None
            Supply APY

        Returns
        -------
        Position
            Formatted supply position

        """
        atoken = Token(
            address=atoken_address,
            symbol=f"a{reserve_token.symbol}",
            decimals=reserve_token.decimals,
            name=f"Aave {reserve_token.symbol}",
        )

        return Position(
            protocol=self.name,
            chain=chain,
            position_type=PositionType.LENDING_SUPPLY,
            token=atoken,
            balance=balance,
            underlying_token=reserve_token,
            underlying_balance=balance,  # aToken is 1:1 with underlying
            apy=apy,
            health_factor=account_data.get("health_factor"),
            metadata={
                "is_collateral": is_collateral,
                "contract_address": atoken_address,
            },
        )
