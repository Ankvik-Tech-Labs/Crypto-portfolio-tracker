"""Tests for Octav.fi API client."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest

from crypto_portfolio_tracker.core.models import PositionType
from crypto_portfolio_tracker.integrations.octav import OctavAPIError, OctavClient

# --- Fixtures ---

MOCK_API_KEY = "test_api_key_123"

MOCK_PORTFOLIO_RESPONSE = {
    "data": {
        "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "networth": "5000.00",
        "assetByProtocols": {
            "aave_v3": {
                "key": "aave_v3",
                "name": "Aave V3",
                "value": "3296.26",
                "assets": [
                    {
                        "balance": "1.5",
                        "symbol": "WETH",
                        "price": "2197.50",
                        "value": "3296.26",
                        "contractAddress": "0x4200000000000000000000000000000000000006",
                        "chain": "base",
                    },
                    {
                        "balance": "500.0",
                        "symbol": "variableDebtUSDC",
                        "price": "1.00",
                        "value": "500.00",
                        "contractAddress": "0x1234567890abcdef1234567890abcdef12345678",
                        "chain": "base",
                    },
                ],
            },
            "wallet": {
                "key": "wallet",
                "name": "Wallet",
                "value": "1203.74",
                "assets": [
                    {
                        "balance": "0.5",
                        "symbol": "ETH",
                        "price": "2407.48",
                        "value": "1203.74",
                        "contractAddress": "",
                        "chain": "ethereum",
                    },
                ],
            },
            "lido": {
                "key": "lido",
                "name": "Lido",
                "value": "4800.00",
                "assets": [
                    {
                        "balance": "2.0",
                        "symbol": "stETH",
                        "price": "2400.00",
                        "value": "4800.00",
                        "contractAddress": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
                        "chain": "ethereum",
                    },
                ],
            },
        },
        "chains": {
            "base": {"key": "base", "name": "Base", "value": "3296.26"},
            "ethereum": {"key": "ethereum", "name": "Ethereum", "value": "6003.74"},
        },
    },
    "status": "success",
}

MOCK_NAV_RESPONSE = {"data": {"nav": 12345.67, "currency": "USD"}}

MOCK_CREDITS_RESPONSE = 19033


def _make_mock_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    if status_code >= 400:
        http_error = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=response,
        )
        response.raise_for_status.side_effect = http_error
    return response


# --- Tests ---


class TestOctavClientInit:
    """Tests for client initialization."""

    def test_client_initialization(self):
        """Verify client is created with correct API key and base URL."""
        client = OctavClient(api_key=MOCK_API_KEY)
        assert client.api_key == MOCK_API_KEY
        assert client.base_url == "https://api.octav.fi/v1"
        client.close()

    def test_client_custom_base_url(self):
        """Verify custom base URL is applied."""
        client = OctavClient(api_key=MOCK_API_KEY, base_url="https://custom.api/v1")
        assert client.base_url == "https://custom.api/v1"
        client.close()

    def test_client_auth_header(self):
        """Verify Bearer token header is set on the httpx client."""
        client = OctavClient(api_key=MOCK_API_KEY)
        assert client.client.headers["authorization"] == f"Bearer {MOCK_API_KEY}"
        client.close()


class TestGetPortfolio:
    """Tests for get_portfolio method."""

    @patch.object(httpx.Client, "get")
    def test_get_portfolio_success(self, mock_get):
        """Verify raw portfolio response is returned."""
        mock_get.return_value = _make_mock_response(MOCK_PORTFOLIO_RESPONSE)

        client = OctavClient(api_key=MOCK_API_KEY)
        result = client.get_portfolio("0xABC")

        assert result == MOCK_PORTFOLIO_RESPONSE
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "portfolio" in call_args[0][0] or "portfolio" in str(call_args)
        client.close()

    @patch.object(httpx.Client, "get")
    def test_get_portfolio_api_error(self, mock_get):
        """Verify OctavAPIError on HTTP error."""
        mock_get.return_value = _make_mock_response({}, status_code=401)

        client = OctavClient(api_key=MOCK_API_KEY)
        with pytest.raises(OctavAPIError, match="HTTP error 401"):
            client.get_portfolio("0xABC")
        client.close()

    @patch.object(httpx.Client, "get")
    def test_get_portfolio_timeout(self, mock_get):
        """Verify OctavAPIError on timeout."""
        mock_get.side_effect = httpx.TimeoutException("Connection timed out")

        client = OctavClient(api_key=MOCK_API_KEY)
        with pytest.raises(OctavAPIError, match="timeout"):
            client.get_portfolio("0xABC")
        client.close()


class TestGetPositions:
    """Tests for get_positions method."""

    @patch.object(httpx.Client, "get")
    def test_get_positions_parses_aave(self, mock_get):
        """Verify AAVE positions are parsed into Position models."""
        mock_get.return_value = _make_mock_response(MOCK_PORTFOLIO_RESPONSE)

        client = OctavClient(api_key=MOCK_API_KEY)
        positions = client.get_positions("0xABC")

        # Should have 4 positions: 2 aave_v3 + 1 wallet + 1 lido
        assert len(positions) == 4

        # Find AAVE supply position
        aave_supply = [
            p for p in positions
            if p.protocol == "aave_v3" and p.position_type == PositionType.LENDING_SUPPLY
        ]
        assert len(aave_supply) == 1
        assert aave_supply[0].token.symbol == "WETH"
        assert aave_supply[0].balance == Decimal("1.5")
        assert aave_supply[0].usd_value == Decimal("3296.26")
        assert aave_supply[0].chain == "base"

        # Find AAVE borrow position (variableDebtUSDC)
        aave_borrow = [
            p for p in positions
            if p.protocol == "aave_v3" and p.position_type == PositionType.LENDING_BORROW
        ]
        assert len(aave_borrow) == 1
        assert aave_borrow[0].token.symbol == "variableDebtUSDC"
        assert aave_borrow[0].balance == Decimal("500.0")
        client.close()

    @patch.object(httpx.Client, "get")
    def test_get_positions_filters_by_chain(self, mock_get):
        """Verify chain filtering returns only matching positions."""
        mock_get.return_value = _make_mock_response(MOCK_PORTFOLIO_RESPONSE)

        client = OctavClient(api_key=MOCK_API_KEY)
        positions = client.get_positions("0xABC", chains=["base"])

        # Only base chain positions (2 AAVE assets on base)
        assert all(p.chain == "base" for p in positions)
        assert len(positions) == 2
        client.close()

    @patch.object(httpx.Client, "get")
    def test_get_positions_empty_portfolio(self, mock_get):
        """Verify empty list for empty portfolio."""
        mock_get.return_value = _make_mock_response(
            {"data": {"assetByProtocols": {}, "chains": {}}}
        )

        client = OctavClient(api_key=MOCK_API_KEY)
        positions = client.get_positions("0xABC")
        assert positions == []
        client.close()

    @patch.object(httpx.Client, "get")
    def test_get_positions_skips_zero_balance(self, mock_get):
        """Verify positions with zero balance and zero value are skipped."""
        mock_get.return_value = _make_mock_response({
            "data": {
                "assetByProtocols": {
                    "wallet": {
                        "key": "wallet",
                        "assets": [
                            {
                                "balance": "0",
                                "symbol": "DUST",
                                "price": "0",
                                "value": "0",
                                "contractAddress": "",
                                "chain": "ethereum",
                            },
                        ],
                    },
                },
            },
        })

        client = OctavClient(api_key=MOCK_API_KEY)
        positions = client.get_positions("0xABC")
        assert positions == []
        client.close()


class TestGetNav:
    """Tests for get_nav method."""

    @patch.object(httpx.Client, "get")
    def test_get_nav_success(self, mock_get):
        """Verify NAV is returned as Decimal."""
        mock_get.return_value = _make_mock_response(MOCK_NAV_RESPONSE)

        client = OctavClient(api_key=MOCK_API_KEY)
        nav = client.get_nav("0xABC")

        assert isinstance(nav, Decimal)
        assert nav == Decimal("12345.67")
        client.close()

    @patch.object(httpx.Client, "get")
    def test_get_nav_api_error(self, mock_get):
        """Verify OctavAPIError on HTTP error."""
        mock_get.return_value = _make_mock_response({}, status_code=429)

        client = OctavClient(api_key=MOCK_API_KEY)
        with pytest.raises(OctavAPIError, match="429"):
            client.get_nav("0xABC")
        client.close()


class TestCheckCredits:
    """Tests for check_credits method."""

    @patch.object(httpx.Client, "get")
    def test_check_credits_raw_int(self, mock_get):
        """Verify credits returned when response is raw integer."""
        mock_get.return_value = _make_mock_response(MOCK_CREDITS_RESPONSE)

        client = OctavClient(api_key=MOCK_API_KEY)
        credits = client.check_credits()

        assert isinstance(credits, int)
        assert credits == 19033
        client.close()

    @patch.object(httpx.Client, "get")
    def test_check_credits_wrapped(self, mock_get):
        """Verify credits returned when response is wrapped in data key."""
        mock_get.return_value = _make_mock_response({"data": 5000})

        client = OctavClient(api_key=MOCK_API_KEY)
        credits = client.check_credits()

        assert credits == 5000
        client.close()

    @patch.object(httpx.Client, "get")
    def test_check_credits_api_error(self, mock_get):
        """Verify OctavAPIError on HTTP error."""
        mock_get.return_value = _make_mock_response({}, status_code=401)

        client = OctavClient(api_key=MOCK_API_KEY)
        with pytest.raises(OctavAPIError, match="401"):
            client.check_credits()
        client.close()


class TestPositionTypeMapping:
    """Tests for position type mapping logic."""

    def test_aave_supply_type(self):
        """Verify AAVE supply positions are mapped correctly."""
        client = OctavClient(api_key=MOCK_API_KEY)
        result = client._map_position_type("aave_v3", {"symbol": "WETH"})
        assert result == PositionType.LENDING_SUPPLY
        client.close()

    def test_aave_debt_type(self):
        """Verify AAVE debt positions are detected via symbol."""
        client = OctavClient(api_key=MOCK_API_KEY)
        result = client._map_position_type("aave_v3", {"symbol": "variableDebtUSDC"})
        assert result == PositionType.LENDING_BORROW
        client.close()

    def test_staking_type(self):
        """Verify staking protocols map to LIQUID_STAKING."""
        client = OctavClient(api_key=MOCK_API_KEY)
        result = client._map_position_type("lido", {"symbol": "stETH"})
        assert result == PositionType.LIQUID_STAKING
        client.close()

    def test_vault_default_type(self):
        """Verify unknown protocols default to VAULT."""
        client = OctavClient(api_key=MOCK_API_KEY)
        result = client._map_position_type("some_protocol", {"symbol": "TOKEN"})
        assert result == PositionType.VAULT
        client.close()

    def test_compound_supply_type(self):
        """Verify Compound positions map to LENDING_SUPPLY."""
        client = OctavClient(api_key=MOCK_API_KEY)
        result = client._map_position_type("compound", {"symbol": "cUSDC"})
        assert result == PositionType.LENDING_SUPPLY
        client.close()


class TestContextManager:
    """Tests for context manager support."""

    def test_context_manager_enter_exit(self):
        """Verify context manager returns client and closes cleanly."""
        with OctavClient(api_key=MOCK_API_KEY) as client:
            assert isinstance(client, OctavClient)
            assert client.api_key == MOCK_API_KEY

    def test_close_method(self):
        """Verify close() can be called without error."""
        client = OctavClient(api_key=MOCK_API_KEY)
        client.close()


class TestMetadata:
    """Tests for metadata in parsed positions."""

    @patch.object(httpx.Client, "get")
    def test_position_metadata_source(self, mock_get):
        """Verify positions include 'octav' source in metadata."""
        mock_get.return_value = _make_mock_response(MOCK_PORTFOLIO_RESPONSE)

        client = OctavClient(api_key=MOCK_API_KEY)
        positions = client.get_positions("0xABC")

        for pos in positions:
            assert pos.metadata.get("source") == "octav"
            assert "octav_protocol" in pos.metadata
        client.close()
