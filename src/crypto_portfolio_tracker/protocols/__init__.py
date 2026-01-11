"""Protocol handlers for various DeFi protocols."""

# Import all handlers to trigger auto-registration
from crypto_portfolio_tracker.protocols.aave import AaveHandler
from crypto_portfolio_tracker.protocols.base import BaseProtocolHandler
from crypto_portfolio_tracker.protocols.beefy import BeefyHandler
from crypto_portfolio_tracker.protocols.etherfi import EtherfiHandler
from crypto_portfolio_tracker.protocols.lido import LidoHandler
from crypto_portfolio_tracker.protocols.morpho import MorphoHandler

__all__ = [
    "AaveHandler",
    "BaseProtocolHandler",
    "BeefyHandler",
    "EtherfiHandler",
    "LidoHandler",
    "MorphoHandler",
]
