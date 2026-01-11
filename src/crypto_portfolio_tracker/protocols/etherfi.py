"""Ether.fi liquid restaking protocol handler."""

import os
from decimal import Decimal

from crypto_portfolio_tracker.core.models import Position, PositionType, Token
from crypto_portfolio_tracker.core.registry import ProtocolRegistry
from crypto_portfolio_tracker.integrations.zerion import ZerionAPIError, ZerionClient
from crypto_portfolio_tracker.protocols.base import BaseProtocolHandler
from crypto_portfolio_tracker.rpc.multicall import MulticallBatcher


@ProtocolRegistry.register
class EtherfiHandler(BaseProtocolHandler):
    """
    Handler for Ether.fi liquid restaking positions.

    Tracks eETH and weETH balances, restaking rewards, and EigenLayer points.

    """

    name = "etherfi"
    supported_chains = ["ethereum"]

    # Event signatures for discovery
    # Use Enter event from Liquid Vault (best indicator of user deposits)
    discovery_events = [
        "0xea00f88768a86184a6e515238a549c171769fe7460a011d6fd0bcd48ca078ea4",  # Enter(address indexed from,address indexed asset,address indexed to,uint256 amount,uint256 shares)
        "0xe96d7872363f475d18b2f5390caaa5eaa96b2d38e42c62afe4ac08ebd2b13c3a",  # Deposit(uint256 indexed nonce,address indexed receiver,address indexed depositAsset,...)
    ]

    def get_positions(self, user_address: str, chain: str) -> list[Position]:
        """
        Fetch Ether.fi positions for a user.

        Uses Zerion API first (includes USD values), falls back to RPC if needed.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name (only 'ethereum' supported)

        Returns
        -------
        list[Position]
            List of Ether.fi positions (eETH, weETH, liquidUSD)

        """
        if chain not in self.supported_chains:
            return []

        # Try Zerion API first
        api_key = os.getenv("ZERION_API_KEY")
        if api_key:
            try:
                with ZerionClient(api_key) as client:
                    # Fetch all positions from Zerion
                    all_positions = client.get_positions_as_models(user_address, [chain])

                    # Filter for Ether.fi positions with flexible matching
                    etherfi_keywords = ["etherfi", "ether.fi", "ether-fi"]
                    etherfi_positions = [
                        pos
                        for pos in all_positions
                        if any(keyword in pos.protocol.lower() for keyword in etherfi_keywords) and pos.chain == chain
                    ]

                    # Fallback: Check for eETH/weETH/liquidUSD tokens as proof of positions
                    if not etherfi_positions:
                        etherfi_token_symbols = ["eeth", "weeth", "liquidusd"]
                        etherfi_positions = [
                            pos
                            for pos in all_positions
                            if any(token in pos.token.symbol.lower() for token in etherfi_token_symbols)
                            and pos.chain == chain
                        ]

                    if etherfi_positions:
                        return etherfi_positions

            except (ZerionAPIError, Exception):
                # Silently fall back to RPC
                pass

        # Fallback to RPC calls with Multicall batching
        if not self.rpc_provider:
            return []

        positions = []
        addresses = self.get_contract_addresses(chain)

        # Batch all balance checks into single Multicall
        multicall = MulticallBatcher(self.rpc_provider)

        # Track call indices for balances
        eeth_idx = None
        weeth_idx = None
        vault_idx = None

        # Track call indices for decimals
        eeth_decimals_idx = None
        weeth_decimals_idx = None
        vault_decimals_idx = None

        # Track call indices for vault metadata
        vault_rate_idx = None

        if addresses.get("eeth"):
            eeth_idx = multicall.call_count
            multicall.add_call(addresses["eeth"], "balanceOf", [user_address])
            eeth_decimals_idx = multicall.call_count
            multicall.add_call(addresses["eeth"], "decimals", [])

        if addresses.get("weeth"):
            weeth_idx = multicall.call_count
            multicall.add_call(addresses["weeth"], "balanceOf", [user_address])
            weeth_decimals_idx = multicall.call_count
            multicall.add_call(addresses["weeth"], "decimals", [])

        if addresses.get("liquid_vault"):
            vault_idx = multicall.call_count
            multicall.add_call(addresses["liquid_vault"], "balanceOf", [user_address])
            vault_decimals_idx = multicall.call_count
            multicall.add_call(addresses["liquid_vault"], "decimals", [])

            # Query accountant contract for exchange rate (USDC per share)
            # Accountant: 0xc315D6e14DDCDC7407784e2Caf815d131Bc1D3E7
            accountant_address = "0xc315D6e14DDCDC7407784e2Caf815d131Bc1D3E7"
            vault_rate_idx = multicall.call_count
            multicall.add_call(accountant_address, "getRate", [])

        # Execute batched balance checks
        try:
            balance_results = multicall.execute()
        except Exception:
            return []

        # Process eETH position
        if eeth_idx is not None and balance_results[eeth_idx] and balance_results[eeth_idx] > 0:
            eeth_decimals = balance_results[eeth_decimals_idx] if eeth_decimals_idx is not None else 18
            eeth_position = self._create_eeth_position(
                user_address, addresses, chain, balance_results[eeth_idx], eeth_decimals
            )
            if eeth_position:
                positions.append(eeth_position)

        # Process weETH position
        if weeth_idx is not None and balance_results[weeth_idx] and balance_results[weeth_idx] > 0:
            weeth_decimals = balance_results[weeth_decimals_idx] if weeth_decimals_idx is not None else 18
            weeth_position = self._create_weeth_position(
                user_address, addresses, chain, balance_results[weeth_idx], weeth_decimals
            )
            if weeth_position:
                positions.append(weeth_position)

        # Process liquid vault position
        if vault_idx is not None and balance_results[vault_idx] and balance_results[vault_idx] > 0:
            vault_decimals = balance_results[vault_decimals_idx] if vault_decimals_idx is not None else 18
            vault_rate = balance_results[vault_rate_idx] if vault_rate_idx is not None else None
            vault_position = self._create_vault_position(
                user_address, addresses, chain, balance_results[vault_idx], vault_decimals, vault_rate
            )
            if vault_position:
                positions.append(vault_position)

        return positions

    def _create_eeth_position(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
        balance_raw: int,
        decimals: int = 18,
    ) -> Position | None:
        """
        Create eETH position from pre-fetched balance.

        Parameters
        ----------
        user_address : str
            User address
        addresses : dict[str, str]
            Protocol contract addresses
        chain : str
            Chain name
        balance_raw : int
            Raw balance in wei

        Returns
        -------
        Position | None
            eETH position

        """
        try:
            # Convert from wei to token amount using actual decimals
            balance = Decimal(str(balance_raw)) / Decimal(10**decimals)

            eeth_token = Token(
                address=addresses["eeth"],
                symbol="eETH",
                decimals=decimals,
                name="ether.fi Staked ETH",
            )

            eth_token = Token(
                address="0x0000000000000000000000000000000000000000",
                symbol="ETH",
                decimals=18,
                name="Ethereum",
            )

            return Position(
                protocol=self.name,
                chain=chain,
                position_type=PositionType.RESTAKING,
                token=eeth_token,
                balance=balance,
                underlying_token=eth_token,
                underlying_balance=balance,  # eETH is approximately 1:1 with ETH
                metadata={
                    "is_liquid_restaking": True,
                    "earns_eigenlayer_points": True,
                    "contract_address": addresses["eeth"],
                },
            )
        except Exception:
            return None

    def _create_weeth_position(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
        balance_raw: int,
        decimals: int = 18,
    ) -> Position | None:
        """
        Create weETH position from pre-fetched balance.

        Parameters
        ----------
        user_address : str
            User address
        addresses : dict[str, str]
            Protocol contract addresses
        chain : str
            Chain name
        balance_raw : int
            Raw balance in wei

        Returns
        -------
        Position | None
            weETH position

        """
        try:
            # Convert from wei to token amount using actual decimals
            balance = Decimal(str(balance_raw)) / Decimal(10**decimals)

            # Get underlying eETH amount
            weeth_address = addresses.get("weeth")
            if not weeth_address:
                return None

            try:
                contract = self.rpc_provider.get_contract(weeth_address)
                eeth_amount_raw = contract.getEETHByWeETH(balance_raw)
                eeth_amount = Decimal(str(eeth_amount_raw)) / Decimal(10**decimals)
            except Exception:
                # If getEETHByWeETH fails, assume 1:1
                eeth_amount = balance

            weeth_token = Token(
                address=weeth_address,
                symbol="weETH",
                decimals=decimals,
                name="Wrapped eETH",
            )

            eeth_token = Token(
                address=addresses.get("eeth", ""),
                symbol="eETH",
                decimals=18,
                name="ether.fi Staked ETH",
            )

            return Position(
                protocol=self.name,
                chain=chain,
                position_type=PositionType.RESTAKING,
                token=weeth_token,
                balance=balance,
                underlying_token=eeth_token,
                underlying_balance=eeth_amount,
                metadata={
                    "is_wrapped": True,
                    "is_liquid_restaking": True,
                    "earns_eigenlayer_points": True,
                    "contract_address": weeth_address,
                },
            )
        except Exception:
            return None

    def _create_vault_position(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
        balance_raw: int,
        decimals: int = 18,
        exchange_rate_raw: int | None = None,
    ) -> Position | None:
        """
        Create liquid vault position from pre-fetched balance.

        Parameters
        ----------
        user_address : str
            User address
        addresses : dict[str, str]
            Protocol contract addresses
        chain : str
            Chain name
        balance_raw : int
            Raw balance in wei
        decimals : int
            Token decimals
        exchange_rate_raw : int | None
            Exchange rate from accountant (USDC per liquidUSD share)

        Returns
        -------
        Position | None
            Liquid Vault position

        """
        try:
            # Convert from wei to token amount using actual decimals
            balance = Decimal(str(balance_raw)) / Decimal(10**decimals)

            vault_address = addresses.get("liquid_vault")
            if not vault_address:
                return None

            # Calculate underlying USDC value using exchange rate from accountant
            # Exchange rate is in 6 decimals (same as USDC)
            if exchange_rate_raw is not None:
                # Convert exchange rate from 6 decimals to Decimal
                # AccountantWithRateProviders returns rate in base asset decimals (USDC = 6)
                exchange_rate = Decimal(str(exchange_rate_raw)) / Decimal(10**6)
                underlying_value = balance * exchange_rate
            else:
                # Fallback if exchange rate not available
                underlying_value = balance

            vault_token = Token(
                address=vault_address,
                symbol="LiquidVault",
                decimals=decimals,
                name="Ether.fi Liquid Vault Share",
            )

            # USDC contract address on Ethereum
            usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
            underlying_token = Token(
                address=usdc_address,
                symbol="USDC",
                decimals=6,
                name="USD Coin",
            )

            return Position(
                protocol=self.name,
                chain=chain,
                position_type=PositionType.VAULT,
                token=vault_token,
                balance=balance,
                underlying_token=underlying_token,
                underlying_balance=underlying_value,
                metadata={
                    "is_liquid_vault": True,
                    "contract_address": vault_address,
                },
            )
        except Exception:
            return None

    def _get_eeth_position(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
    ) -> Position | None:
        """
        Get eETH position.

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
            eETH position if balance > 0

        """
        eeth_address = addresses.get("eeth")
        if not eeth_address:
            return None

        try:
            # Fetch eETH balance using contract call
            balance_raw = self._make_contract_call(
                eeth_address,
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

        eeth_token = Token(
            address=eeth_address,
            symbol="eETH",
            decimals=18,
            name="ether.fi Staked ETH",
        )

        eth_token = Token(
            address="0x0000000000000000000000000000000000000000",
            symbol="ETH",
            decimals=18,
            name="Ethereum",
        )

        return Position(
            protocol=self.name,
            chain=chain,
            position_type=PositionType.RESTAKING,
            token=eeth_token,
            balance=balance,
            underlying_token=eth_token,
            underlying_balance=balance,  # eETH is approximately 1:1 with ETH
            metadata={
                "is_liquid_restaking": True,
                "earns_eigenlayer_points": True,
                "contract_address": eeth_address,
            },
        )

    def _get_weeth_position(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
    ) -> Position | None:
        """
        Get weETH (wrapped eETH) position.

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
            weETH position if balance > 0

        """
        weeth_address = addresses.get("weeth")
        if not weeth_address:
            return None

        try:
            # Fetch weETH balance using contract call
            balance_raw = self._make_contract_call(
                weeth_address,
                "balanceOf",
                [user_address],
                chain,
            )

            # Convert from wei to token amount (18 decimals)
            balance = Decimal(str(balance_raw)) / Decimal(10**18)

            if balance == 0:
                return None

            # Get underlying eETH amount
            eeth_amount_raw = self._make_contract_call(
                weeth_address,
                "getEETHByWeETH",
                [balance_raw],
                chain,
            )

            # Convert eETH amount from wei
            eeth_amount = Decimal(str(eeth_amount_raw)) / Decimal(10**18)

        except Exception:
            # If call fails, skip this position
            return None

        weeth_token = Token(
            address=weeth_address,
            symbol="weETH",
            decimals=18,
            name="Wrapped eETH",
        )

        eeth_token = Token(
            address=addresses.get("eeth", ""),
            symbol="eETH",
            decimals=18,
            name="ether.fi Staked ETH",
        )

        return Position(
            protocol=self.name,
            chain=chain,
            position_type=PositionType.RESTAKING,
            token=weeth_token,
            balance=balance,
            underlying_token=eeth_token,
            underlying_balance=eeth_amount,
            metadata={
                "is_wrapped": True,
                "is_liquid_restaking": True,
                "earns_eigenlayer_points": True,
                "contract_address": weeth_address,
            },
        )

    def _get_liquid_vault_position(
        self,
        user_address: str,
        addresses: dict[str, str],
        chain: str,
    ) -> Position | None:
        """
        Get Ether.fi Liquid Vault position.

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
            Liquid Vault position if balance > 0

        """
        vault_address = addresses.get("liquid_vault")
        if not vault_address:
            return None

        try:
            # Fetch vault share balance
            balance_raw = self._make_contract_call(
                vault_address,
                "balanceOf",
                [user_address],
                chain,
            )

            # Convert from wei to token amount (18 decimals)
            balance = Decimal(str(balance_raw)) / Decimal(10**18)

            if balance == 0:
                return None

            # Try to get share price to calculate underlying value
            try:
                share_price_raw = self._make_contract_call(
                    vault_address,
                    "pricePerShare",
                    [],
                    chain,
                )
                share_price = Decimal(str(share_price_raw)) / Decimal(10**18)
                underlying_value = balance * share_price
            except Exception:
                # If pricePerShare fails, assume 1:1
                underlying_value = balance

        except Exception:
            # If call fails, skip this position
            return None

        vault_token = Token(
            address=vault_address,
            symbol="LiquidVault",
            decimals=18,
            name="Ether.fi Liquid Vault Share",
        )

        underlying_token = Token(
            address="0x0000000000000000000000000000000000000000",
            symbol="USDC",  # Vault likely accepts USDC
            decimals=6,
            name="USD Coin",
        )

        return Position(
            protocol=self.name,
            chain=chain,
            position_type=PositionType.VAULT,
            token=vault_token,
            balance=balance,
            underlying_token=underlying_token,
            underlying_balance=underlying_value,
            metadata={
                "is_liquid_vault": True,
                "contract_address": vault_address,
            },
        )
