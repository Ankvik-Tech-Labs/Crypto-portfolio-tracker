"""Lido liquid staking protocol handler."""

from decimal import Decimal

from crypto_portfolio_tracker.core.models import Position, PositionType, Token
from crypto_portfolio_tracker.core.registry import ProtocolRegistry
from crypto_portfolio_tracker.protocols.base import BaseProtocolHandler


@ProtocolRegistry.register
class LidoHandler(BaseProtocolHandler):
    """
    Handler for Lido liquid staking positions.

    Tracks stETH and wstETH balances, pending withdrawals, and staking rewards.

    """

    name = "lido"
    supported_chains = ["ethereum"]

    # Event signatures for discovery
    # Use Submitted event (user submits ETH for stETH)
    discovery_events = [
        "0x96a25c8ce0baabc1fdefd93e9ed25d8e092a3332f3aa9a41722b5697231d1d1a",  # Submitted(address indexed sender,uint256 amount,address indexed referral)
    ]

    def get_positions(self, user_address: str, chain: str) -> list[Position]:
        """
        Fetch Lido positions for a user.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name (only 'ethereum' supported)

        Returns
        -------
        list[Position]
            List of Lido positions (stETH, wstETH, withdrawals)

        """
        if chain not in self.supported_chains:
            return []

        positions = []
        addresses = self.get_contract_addresses(chain)

        # Check stETH balance
        steth_position = self._get_steth_position(user_address, addresses, chain)
        if steth_position:
            positions.append(steth_position)

        # Check wstETH balance
        wsteth_position = self._get_wsteth_position(user_address, addresses, chain)
        if wsteth_position:
            positions.append(wsteth_position)

        # Check pending withdrawals
        # TODO: Implement withdrawal queue checking

        return positions

    def _get_steth_position(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
    ) -> Position | None:
        """
        Get stETH position.

        Parameters
        ----------
        user_address : str
            User address
        addresses : dict[str, str]
            Protocol contract addresses
        chain : str
            Chain name

        Returns
        -------
        Position | None
            stETH position if balance > 0

        """
        steth_address = addresses.get("steth")
        if not steth_address:
            return None

        try:
            # Fetch stETH balance using contract call
            balance_raw = self._make_contract_call(
                steth_address,
                "balanceOf",
                [user_address],
                chain,
            )

            # Convert from wei to token amount (18 decimals)
            balance = Decimal(str(balance_raw)) / Decimal(10**18)

            if balance == 0:
                return None
        except Exception:
            # If call fails, skip this position
            return None

        steth_token = Token(
            address=steth_address,
            symbol="stETH",
            decimals=18,
            name="Lido Staked Ether",
        )

        eth_token = Token(
            address="0x0000000000000000000000000000000000000000",
            symbol="ETH",
            decimals=18,
            name="Ethereum",
        )

        # stETH is 1:1 with ETH (approximately, with small rebasing)
        return Position(
            protocol=self.name,
            chain=chain,
            position_type=PositionType.LIQUID_STAKING,
            token=steth_token,
            balance=balance,
            underlying_token=eth_token,
            underlying_balance=balance,  # 1:1 mapping
            metadata={
                "is_rebasing": True,
                "contract_address": steth_address,
            },
        )

    def _get_wsteth_position(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
    ) -> Position | None:
        """
        Get wstETH (wrapped stETH) position.

        Parameters
        ----------
        user_address : str
            User address
        addresses : dict[str, str]
            Protocol contract addresses
        chain : str
            Chain name

        Returns
        -------
        Position | None
            wstETH position if balance > 0

        """
        wsteth_address = addresses.get("wsteth")
        if not wsteth_address:
            return None

        try:
            # Fetch wstETH balance using contract call
            balance_raw = self._make_contract_call(
                wsteth_address,
                "balanceOf",
                [user_address],
                chain,
            )

            # Convert from wei to token amount (18 decimals)
            balance = Decimal(str(balance_raw)) / Decimal(10**18)

            if balance == 0:
                return None

            # Get stETH amount from wstETH (unwrapped value)
            steth_amount_raw = self._make_contract_call(
                wsteth_address,
                "getStETHByWstETH",
                [balance_raw],
                chain,
            )

            # Convert stETH amount from wei
            steth_amount = Decimal(str(steth_amount_raw)) / Decimal(10**18)

        except Exception:
            # If call fails, skip this position
            return None

        wsteth_token = Token(
            address=wsteth_address,
            symbol="wstETH",
            decimals=18,
            name="Wrapped liquid staked Ether 2.0",
        )

        steth_token = Token(
            address=addresses.get("steth", ""),
            symbol="stETH",
            decimals=18,
            name="Lido Staked Ether",
        )

        return Position(
            protocol=self.name,
            chain=chain,
            position_type=PositionType.LIQUID_STAKING,
            token=wsteth_token,
            balance=balance,
            underlying_token=steth_token,
            underlying_balance=steth_amount,
            metadata={
                "is_wrapped": True,
                "contract_address": wsteth_address,
            },
        )
