"""Data models for positions, tokens, and portfolio summaries."""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class PositionType(StrEnum):
    """Type of DeFi position."""

    LENDING_SUPPLY = "lending_supply"
    LENDING_BORROW = "lending_borrow"
    LIQUID_STAKING = "liquid_staking"
    VAULT = "vault"
    RESTAKING = "restaking"


class Token(BaseModel):
    """
    Token information.

    Attributes
    ----------
    address : str
        Token contract address
    symbol : str
        Token symbol (e.g., 'ETH', 'USDC')
    decimals : int
        Number of decimal places
    name : str, optional
        Full token name

    """

    address: str
    symbol: str
    decimals: int
    name: str | None = None


class Reward(BaseModel):
    """
    Claimable reward information.

    Attributes
    ----------
    token : Token
        Reward token
    amount : Decimal
        Claimable amount
    usd_value : Decimal | None
        USD value of reward

    """

    token: Token
    amount: Decimal
    usd_value: Decimal | None = None


class Position(BaseModel):
    """
    Universal position model across all protocols.

    Attributes
    ----------
    protocol : str
        Protocol name (e.g., 'aave_v3', 'lido')
    chain : str
        Chain name (e.g., 'ethereum', 'base')
    position_type : PositionType
        Type of position
    token : Token
        Primary token (e.g., aToken, stETH)
    balance : Decimal
        Token balance
    underlying_token : Token | None
        Underlying token if applicable (e.g., ETH for stETH)
    underlying_balance : Decimal | None
        Amount of underlying token
    usd_value : Decimal | None
        Total USD value
    claimable_rewards : list[Reward]
        List of claimable rewards
    apy : Decimal | None
        Annual percentage yield
    health_factor : Decimal | None
        Health factor for lending positions (None if not applicable)
    metadata : dict
        Protocol-specific additional data

    """

    protocol: str
    chain: str
    position_type: PositionType
    token: Token
    balance: Decimal
    underlying_token: Token | None = None
    underlying_balance: Decimal | None = None
    usd_value: Decimal | None = None
    claimable_rewards: list[Reward] = Field(default_factory=list)
    apy: Decimal | None = None
    health_factor: Decimal | None = None
    metadata: dict = Field(default_factory=dict)


class PortfolioSummary(BaseModel):
    """
    Aggregated portfolio view across all positions.

    Attributes
    ----------
    address : str
        User wallet address
    positions : list[Position]
        All detected positions
    total_usd_value : Decimal
        Total portfolio value in USD
    by_chain : dict[str, Decimal]
        USD value breakdown by chain
    by_protocol : dict[str, Decimal]
        USD value breakdown by protocol
    total_claimable_rewards_usd : Decimal
        Total value of all claimable rewards

    """

    address: str
    positions: list[Position]
    total_usd_value: Decimal
    by_chain: dict[str, Decimal] = Field(default_factory=dict)
    by_protocol: dict[str, Decimal] = Field(default_factory=dict)
    total_claimable_rewards_usd: Decimal = Decimal("0")


class ChainActivity(BaseModel):
    """
    Detected activity on a specific chain.

    Attributes
    ----------
    chain : str
        Chain name
    has_activity : bool
        Whether the address has any activity
    protocols_detected : list[str]
        List of protocols with detected positions

    """

    chain: str
    has_activity: bool
    protocols_detected: list[str] = Field(default_factory=list)
