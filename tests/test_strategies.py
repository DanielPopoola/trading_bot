
import pytest
from decimal import Decimal
from strategies.factory import OrderStrategyFactory
from strategies.market_order import MarketOrderStrategy
from strategies.limit_order import LimitOrderStrategy

# Tests for OrderStrategyFactory
def test_factory_creates_market_strategy():
    strategy = OrderStrategyFactory.create_strategy("market")
    assert isinstance(strategy, MarketOrderStrategy)

def test_factory_creates_limit_strategy():
    strategy = OrderStrategyFactory.create_strategy("limit")
    assert isinstance(strategy, LimitOrderStrategy)

def test_factory_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported order type"):
        OrderStrategyFactory.create_strategy("stop_loss")

def test_factory_get_supported_types():
    types = OrderStrategyFactory.get_supported_types()
    assert "market" in types
    assert "limit" in types

# Tests for MarketOrderStrategy
def test_market_strategy_validate_params():
    strategy = MarketOrderStrategy()
    # Should not raise any exception
    strategy.validate_parameters()

def test_market_strategy_validate_params_with_price():
    strategy = MarketOrderStrategy()
    with pytest.raises(ValueError, match="Market orders don't accept price parameter"):
        strategy.validate_parameters(price=50000)

def test_market_strategy_prepare_data():
    strategy = MarketOrderStrategy()
    order_data = strategy.prepare_order_data(
        symbol="BTCUSDT",
        side="buy",
        quantity=Decimal("0.001")
    )
    expected_data = {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'type': 'MARKET',
        'quantity': '0.001'
    }
    assert order_data == expected_data

def test_market_strategy_get_order_type():
    strategy = MarketOrderStrategy()
    assert strategy.get_order_type() == "MARKET"

# Tests for LimitOrderStrategy
def test_limit_strategy_validate_params():
    strategy = LimitOrderStrategy()
    validated = strategy.validate_parameters(price=50000)
    assert validated['price'] == Decimal("50000")

def test_limit_strategy_validate_params_missing_price():
    strategy = LimitOrderStrategy()
    with pytest.raises(ValueError, match="Limit orders require 'price' parameter"):
        strategy.validate_parameters()

def test_limit_strategy_validate_params_invalid_price():
    strategy = LimitOrderStrategy()
    with pytest.raises(ValueError, match="Price must be a valid number"):
        strategy.validate_parameters(price="abc")
    with pytest.raises(ValueError, match="Price must be positive"):
        strategy.validate_parameters(price=-100)

def test_limit_strategy_prepare_data():
    strategy = LimitOrderStrategy()
    order_data = strategy.prepare_order_data(
        symbol="ETHUSDT",
        side="sell",
        quantity=Decimal("0.5"),
        price=Decimal("3000.50")
    )
    expected_data = {
        'symbol': 'ETHUSDT',
        'side': 'SELL',
        'type': 'LIMIT',
        'quantity': Decimal('0.5'),
        'price': '3000.50',
        'timeInForce': 'GTC'
    }
    assert order_data == expected_data

def test_limit_strategy_get_order_type():
    strategy = LimitOrderStrategy()
    assert strategy.get_order_type() == "LIMIT"
