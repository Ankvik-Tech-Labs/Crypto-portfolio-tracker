"""Tests for Pydantic data models."""

from decimal import Decimal

import pytest

from crypto_portfolio_tracker.core.models import (
    ChainActivity,
    PortfolioSummary,
    Position,
    PositionType,
    Reward,
    Token,
)


def test_token_model():
    """Test Token model."""
    token = Token(
        address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        symbol="USDC",
        decimals=6,
        name="USD Coin",
    )
    
    assert token.symbol == "USDC"
    assert token.decimals == 6
    assert token.name == "USD Coin"


def test_position_model():
    """Test Position model."""
    token = Token(
        address="0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
        symbol="stETH",
        decimals=18,
    )
    
    position = Position(
        protocol="lido",
        chain="ethereum",
        position_type=PositionType.LIQUID_STAKING,
        token=token,
        balance=Decimal("10.5"),
        usd_value=Decimal("25000.50"),
    )
    
    assert position.protocol == "lido"
    assert position.chain == "ethereum"
    assert position.balance == Decimal("10.5")
    assert position.usd_value == Decimal("25000.50")
    assert position.position_type == PositionType.LIQUID_STAKING


def test_position_with_rewards():
    """Test Position with claimable rewards."""
    token = Token(address="0x...", symbol="aUSDC", decimals=6)
    reward_token = Token(address="0x...", symbol="AAVE", decimals=18)
    
    reward = Reward(
        token=reward_token,
        amount=Decimal("5.5"),
        usd_value=Decimal("500.00"),
    )
    
    position = Position(
        protocol="aave_v3",
        chain="ethereum",
        position_type=PositionType.LENDING_SUPPLY,
        token=token,
        balance=Decimal("1000"),
        claimable_rewards=[reward],
    )
    
    assert len(position.claimable_rewards) == 1
    assert position.claimable_rewards[0].amount == Decimal("5.5")


def test_portfolio_summary():
    """Test PortfolioSummary model."""
    token = Token(address="0x...", symbol="stETH", decimals=18)
    
    positions = [
        Position(
            protocol="lido",
            chain="ethereum",
            position_type=PositionType.LIQUID_STAKING,
            token=token,
            balance=Decimal("10"),
            usd_value=Decimal("25000"),
        )
    ]
    
    summary = PortfolioSummary(
        address="0xUser...",
        positions=positions,
        total_usd_value=Decimal("25000"),
        by_chain={"ethereum": Decimal("25000")},
        by_protocol={"lido": Decimal("25000")},
    )
    
    assert summary.address == "0xUser..."
    assert len(summary.positions) == 1
    assert summary.total_usd_value == Decimal("25000")
    assert summary.by_chain["ethereum"] == Decimal("25000")


def test_chain_activity():
    """Test ChainActivity model."""
    activity = ChainActivity(
        chain="ethereum",
        has_activity=True,
        protocols_detected=["lido", "aave_v3"],
    )
    
    assert activity.chain == "ethereum"
    assert activity.has_activity is True
    assert "lido" in activity.protocols_detected
    assert "aave_v3" in activity.protocols_detected


def test_position_type_enum():
    """Test PositionType enum values."""
    assert PositionType.LENDING_SUPPLY.value == "lending_supply"
    assert PositionType.LENDING_BORROW.value == "lending_borrow"
    assert PositionType.LIQUID_STAKING.value == "liquid_staking"
    assert PositionType.VAULT.value == "vault"
    assert PositionType.RESTAKING.value == "restaking"
