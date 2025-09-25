

import pytest
from unittest.mock import patch, MagicMock
from binance.exceptions import BinanceAPIException, BinanceOrderException
from bot.api_client import BinanceAPIClient, APIAuthenticationError, APIConnectionError, APIOrderError

# This fixture will patch the Client for all tests in this file
@pytest.fixture(autouse=True)
def mock_binance_client_class():
    with patch('bot.api_client.Client') as mock_client_constructor:
        yield mock_client_constructor

@pytest.fixture
def mock_binance_client(mock_binance_client_class):
    mock_instance = MagicMock()
    mock_binance_client_class.return_value = mock_instance
    return mock_instance

# A mock response object for creating BinanceAPIException instances
@pytest.fixture
def mock_response():
    response = MagicMock()
    response.status_code = 400
    response.text = '{"code": -1121, "msg": "Invalid symbol."}'
    return response


def test_client_initialization_success(mock_binance_client):
    BinanceAPIClient(api_key="test_key", api_secret="test_secret")
    mock_binance_client.ping.assert_called_once()
    mock_binance_client.futures_account.assert_called_once()

def test_place_order_success(mock_binance_client):
    client = BinanceAPIClient(api_key="test_key", api_secret="test_secret")
    order_data = {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': '0.001'}
    mock_binance_client.futures_create_order.return_value = {
        'orderId': 123, 'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET',
        'origQty': '0.001', 'price': '50000', 'status': 'FILLED', 'transactTime': 123456789
    }
    result = client.place_order(order_data)
    mock_binance_client.futures_create_order.assert_called_once_with(**order_data)
    assert result['order_id'] == 123

def test_get_account_balance_success(mock_binance_client):
    client = BinanceAPIClient(api_key="test_key", api_secret="test_secret")
    mock_binance_client.futures_account.return_value = {
        'assets': [
            {'asset': 'USDT', 'walletBalance': '1000.00'},
            {'asset': 'BTC', 'walletBalance': '0.00'}
        ]
    }
    balance = client.get_account_balance()
    assert len(balance) == 1
    assert balance[0]['asset'] == 'USDT'

def test_get_exchange_info_success(mock_binance_client):
    client = BinanceAPIClient(api_key="test_key", api_secret="test_secret")
    mock_binance_client.futures_exchange_info.return_value = {'symbols': [{'symbol': 'BTCUSDT'}]}
    info = client.get_exchange_info()
    assert len(info['symbols']) == 1


def test_get_exchange_info_failure(mock_binance_client):
    client = BinanceAPIClient(api_key="test_key", api_secret="test_secret")
    mock_binance_client.futures_exchange_info.side_effect = Exception("Network error")
    with pytest.raises(APIConnectionError, match="Unexpected error"):
        client.get_exchange_info()


def test_get_symbol_info_success(mock_binance_client):
    client = BinanceAPIClient(api_key="test_key", api_secret="test_secret")
    mock_binance_client.futures_exchange_info.return_value = {
        'symbols': [{'symbol': 'BTCUSDT', 'pair': 'BTCUSDT'}, {'symbol': 'ETHUSDT'}]
    }
    info = client.get_symbol_info('BTCUSDT')
    assert info['pair'] == 'BTCUSDT'


def test_get_symbol_info_not_found(mock_binance_client):
    client = BinanceAPIClient(api_key="test_key", api_secret="test_secret")
    mock_binance_client.futures_exchange_info.return_value = {'symbols': [{'symbol': 'ETHUSDT'}]}
    info = client.get_symbol_info('BTCUSDT')
    assert info is None
