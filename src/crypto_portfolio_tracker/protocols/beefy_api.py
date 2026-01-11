"""Beefy Finance REST API client."""

from decimal import Decimal
from typing import Any

import httpx

from crypto_portfolio_tracker.core.models import Position, PositionType, Token


class BeefyAPIError(Exception):
    """Exception raised for Beefy API errors."""


class BeefyAPIClient:
    """
    Client for Beefy Finance REST API.

    Fetches vault information, prices, and APY data.

    Parameters
    ----------
    base_url : str
        API base URL
    timeout : float
        Request timeout in seconds

    """

    BASE_URL = "https://api.beefy.finance"

    # Chain name mapping (Beefy uses different chain identifiers)
    CHAIN_MAPPING = {
        "ethereum": "ethereum",
        "base": "base",
        "arbitrum": "arbitrum",
        "optimism": "optimism",
        "polygon": "polygon",
    }

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Beefy API client.

        Parameters
        ----------
        base_url : str
            API base URL
        timeout : float
            Request timeout in seconds

        """
        self.base_url = base_url
        self.client = httpx.Client(timeout=timeout)

    def get_vaults(self, chain: str) -> list[dict[str, Any]]:
        """
        Fetch all active vaults for a chain.

        Parameters
        ----------
        chain : str
            Chain name (ethereum, base, etc.)

        Returns
        -------
        list[dict[str, Any]]
            List of vault configurations

        Raises
        ------
        BeefyAPIError
            If the API request fails

        """
        beefy_chain = self.CHAIN_MAPPING.get(chain.lower())
        if not beefy_chain:
            msg = f"Unsupported chain: {chain}"
            raise BeefyAPIError(msg)

        try:
            # Fetch all vaults
            url = f"{self.base_url}/vaults"
            response = self.client.get(url)
            response.raise_for_status()
            all_vaults = response.json()

            # Filter for active vaults on this chain
            chain_vaults = [
                vault for vault in all_vaults if vault.get("chain") == beefy_chain and vault.get("status") == "active"
            ]

            return chain_vaults

        except httpx.TimeoutException as e:
            msg = f"Request timeout: {e}"
            raise BeefyAPIError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code}: {e}"
            raise BeefyAPIError(msg) from e
        except httpx.HTTPError as e:
            msg = f"HTTP request failed: {e}"
            raise BeefyAPIError(msg) from e

    def get_prices(self) -> dict[str, Decimal]:
        """
        Fetch token prices in USD.

        Returns
        -------
        dict[str, Decimal]
            Mapping of token IDs to USD prices

        Raises
        ------
        BeefyAPIError
            If the API request fails

        """
        try:
            url = f"{self.base_url}/prices"
            response = self.client.get(url)
            response.raise_for_status()
            prices_raw = response.json()

            # Convert to Decimal
            prices = {k: Decimal(str(v)) for k, v in prices_raw.items()}

            return prices

        except httpx.TimeoutException as e:
            msg = f"Request timeout: {e}"
            raise BeefyAPIError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code}: {e}"
            raise BeefyAPIError(msg) from e
        except httpx.HTTPError as e:
            msg = f"HTTP request failed: {e}"
            raise BeefyAPIError(msg) from e

    def get_apy(self) -> dict[str, dict[str, Any]]:
        """
        Fetch APY data for all vaults.

        Returns
        -------
        dict[str, dict[str, Any]]
            Mapping of vault IDs to APY information

        Raises
        ------
        BeefyAPIError
            If the API request fails

        """
        try:
            url = f"{self.base_url}/apy"
            response = self.client.get(url)
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            msg = f"Request timeout: {e}"
            raise BeefyAPIError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code}: {e}"
            raise BeefyAPIError(msg) from e
        except httpx.HTTPError as e:
            msg = f"HTTP request failed: {e}"
            raise BeefyAPIError(msg) from e

    def get_vault_positions(
        self,
        user_address: str,
        chain: str,
        rpc_provider: Any,
    ) -> list[Position]:
        """
        Fetch user positions in Beefy vaults using API + RPC hybrid approach.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name
        rpc_provider : Any
            RPC provider for contract calls

        Returns
        -------
        list[Position]
            List of Beefy vault positions with balances > 0

        """
        positions = []

        # Fetch vault list
        try:
            vaults = self.get_vaults(chain)
        except BeefyAPIError:
            return []

        # Fetch prices
        try:
            prices = self.get_prices()
        except BeefyAPIError:
            prices = {}

        # Fetch APY data
        try:
            apy_data = self.get_apy()
        except BeefyAPIError:
            apy_data = {}

        # Check each vault for user balance
        for vault in vaults:
            vault_address = vault.get("earnContractAddress")
            if not vault_address:
                continue

            try:
                # Check user balance via RPC
                contract = rpc_provider.get_contract(vault_address)
                balance_raw = contract.balanceOf(user_address)

                if balance_raw == 0:
                    continue

                # User has balance in this vault
                # Get price per full share
                try:
                    price_per_share_raw = contract.getPricePerFullShare()
                    price_per_share = Decimal(str(price_per_share_raw)) / Decimal(10**18)
                except Exception:
                    price_per_share = Decimal(1)

                # Get token decimals
                decimals = vault.get("tokenDecimals", 18)
                balance = Decimal(str(balance_raw)) / Decimal(10**decimals)

                # Calculate underlying balance
                underlying_balance = balance * price_per_share

                # Get token info
                token_address = vault.get("tokenAddress", "")
                token_symbol = vault.get("token", "UNKNOWN")

                # Get USD value from prices
                vault_id = vault.get("id", "")
                usd_value = None
                if vault_id in prices:
                    usd_value = underlying_balance * prices[vault_id]

                # Get APY
                apy = None
                if vault_id in apy_data:
                    apy_info = apy_data[vault_id]
                    if isinstance(apy_info, dict):
                        apy = Decimal(str(apy_info.get("totalApy", 0)))
                    else:
                        apy = Decimal(str(apy_info))

                # Create position
                vault_token = Token(
                    address=vault_address,
                    symbol=f"moo{token_symbol}",
                    decimals=decimals,
                    name=vault.get("name", ""),
                )

                underlying_token = Token(
                    address=token_address,
                    symbol=token_symbol,
                    decimals=decimals,
                    name=token_symbol,
                )

                position = Position(
                    protocol="beefy",
                    chain=chain,
                    position_type=PositionType.VAULT,
                    token=vault_token,
                    balance=balance,
                    underlying_token=underlying_token,
                    underlying_balance=underlying_balance,
                    usd_value=usd_value,
                    apy=apy,
                    metadata={
                        "vault_id": vault_id,
                        "vault_name": vault.get("name", ""),
                        "platform": vault.get("platform", ""),
                        "strategy": vault.get("strategy", ""),
                        "source": "beefy_api",
                    },
                )

                positions.append(position)

            except Exception:
                # Skip vaults that fail
                continue

        return positions

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "BeefyAPIClient":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: object | None,
    ) -> None:
        """Context manager exit."""
        self.close()
