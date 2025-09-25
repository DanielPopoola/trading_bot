
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from bot.validator import InputValidator, ValidationError

@pytest.fixture
def validator():
    """Fixture for a validator without a real API client."""
    return InputValidator(api_client=None)

@pytest.fixture
def mocked_validator():
    """Fixture for a validator with a mocked API client."""
    mock_api_client = MagicMock()
    # Mock the API client methods to avoid real network calls
    mock_api_client.get_exchange_info.return_value = {
        'symbols': [
            {'symbol': 'BTCUSDT', 'status': 'TRADING'},
            {'symbol': 'ETHUSDT', 'status': 'TRADING'},
        ]
    }
    mock_api_client.get_account_balance.return_value = [
        {'asset': 'USDT', 'availableBalance': '1000.00'}
    ]
    return InputValidator(api_client=mock_api_client)

# Tests for _validate_symbol_format
def test_validate_symbol_format_valid(validator):
    assert validator._validate_symbol_format("BTCUSDT") == "BTCUSDT"
    assert validator._validate_symbol_format("  ethusdt  ") == "ETHUSDT"

def test_validate_symbol_format_invalid_type(validator):
    with pytest.raises(ValidationError, match="Symbol must be a string"):
        validator._validate_symbol_format(123)

def test_validate_symbol_format_empty(validator):
    with pytest.raises(ValidationError, match="Symbol cannot be empty"):
        validator._validate_symbol_format("   ")

def test_validate_symbol_format_invalid_format(validator):
    with pytest.raises(ValidationError, match="Invalid symbol format"):
        validator._validate_symbol_format("BTC-USDT")
    with pytest.raises(ValidationError, match="Invalid symbol format"):
        validator._validate_symbol_format("BT")

# Tests for _validate_side
def test_validate_side_valid(validator):
    assert validator._validate_side("buy") == "buy"
    assert validator._validate_side("  SELL  ") == "sell"

def test_validate_side_invalid_type(validator):
    with pytest.raises(ValidationError, match="Side must be a string"):
        validator._validate_side(None)

def test_validate_side_invalid_value(validator):
    with pytest.raises(ValidationError, match="Side must be 'buy' or 'sell'"):
        validator._validate_side("hold")

# Tests for _validate_quantity
def test_validate_quantity_valid(validator):
    assert validator._validate_quantity("0.1") == Decimal("0.1")
    assert validator._validate_quantity(0.005) == Decimal("0.005")
    assert validator._validate_quantity(Decimal("10")) == Decimal("10")

def test_validate_quantity_invalid_type(validator):
    with pytest.raises(ValidationError, match="Quantity must be a valid number"):
        validator._validate_quantity("abc")

def test_validate_quantity_zero_or_negative(validator):
    with pytest.raises(ValidationError, match="Quantity must be positive"):
        validator._validate_quantity(0)
    with pytest.raises(ValidationError, match="Quantity must be positive"):
        validator._validate_quantity("-1")

def test_validate_quantity_too_large(validator):
    with pytest.raises(ValidationError, match="Quantity too large"):
        validator._validate_quantity("1000001")

def test_validate_quantity_too_small(validator):
    with pytest.raises(ValidationError, match="Quantity too small"):
        validator._validate_quantity("0.0000001")

def test_validate_quantity_rounding(validator):
    # This will be rounded down
    assert validator._validate_quantity("0.123456789") == Decimal("0.12345678")

# Tests for _validate_order_type
@patch('strategies.OrderStrategyFactory.get_supported_types', return_value={'market', 'limit'})
def test_validate_order_type_valid(mock_get_types, validator):
    assert validator._validate_order_type("market") == "market"
    assert validator._validate_order_type("  LIMIT  ") == "limit"

@patch('strategies.OrderStrategyFactory.get_supported_types', return_value={'market', 'limit'})
def test_validate_order_type_invalid(mock_get_types, validator):
    with pytest.raises(ValidationError, match="Unsupported order type"):
        validator._validate_order_type("stop_loss")

# Tests for _validate_price
def test_validate_price_valid(validator):
    assert validator._validate_price("50000.50") == Decimal("50000.50")
    assert validator._validate_price(2500) == Decimal("2500")

def test_validate_price_invalid_type(validator):
    with pytest.raises(ValidationError, match="Price must be a valid number"):
        validator._validate_price("high")

def test_validate_price_zero_or_negative(validator):
    with pytest.raises(ValidationError, match="Price must be positive"):
        validator._validate_price("-100")

def test_validate_price_too_high(validator):
    with pytest.raises(ValidationError, match="Price too high"):
        validator._validate_price("10000001")

# Tests for the main validation function with mocked API calls
def test_validate_order_parameters_market_buy_success(mocked_validator):
    params = mocked_validator.validate_order_parameters(
        symbol="BTCUSDT",
        side="buy",
        quantity="0.01",
        order_type="market"
    )
    assert params['symbol'] == 'BTCUSDT'
    assert params['quantity'] == Decimal('0.01')

def test_validate_order_parameters_limit_sell_success(mocked_validator):
    params = mocked_validator.validate_order_parameters(
        symbol="ETHUSDT",
        side="sell",
        quantity="0.5",
        order_type="limit",
        price="3000"
    )
    assert params['symbol'] == 'ETHUSDT'
    assert params['price'] == Decimal('3000')

def test_validate_order_parameters_symbol_not_exists(mocked_validator):
    with pytest.raises(ValidationError, match="Symbol 'DOGEUSDT' is not available"):
        mocked_validator.validate_order_parameters(
            symbol="DOGEUSDT",
            side="buy",
            quantity="100",
            order_type="market"
        )

def test_validate_order_parameters_insufficient_balance(mocked_validator):
    # This will require a large balance that the mock doesn't have
    with pytest.raises(ValidationError, match="Insufficient balance"):
        mocked_validator.validate_order_parameters(
            symbol="BTCUSDT",
            side="buy",
            quantity="100", # Large quantity
            order_type="limit",
            price="50000"
        )
