import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from binance import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import time


class APIError(Exception):
    """Base exception for API-related errors."""
    pass

class APIConnectionError(APIError):
    """Raised when there are network/connection issues."""
    pass

class APIAuthenticationError(APIError):
    """Raised when API credentials are invalid."""
    pass

class APIOrderError(APIError):
    """Raised when order placement fails due to business rules."""
    pass


class BinanceAPIClient:
    """
    Wrapper around python-binance client with error handling and logging.
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize Binance client.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (True) or live trading (False)
        """
        self.logger = logging.getLogger(__name__)
        self.testnet = testnet
        
        try:
            # Initialize the python-binance client
            self.client = Client(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet
            )
            
            # Test the connection immediately
            self._test_connectivity()
            
            self.logger.info(f"Binance client initialized (testnet: {testnet})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Binance client: {e}")
            raise APIAuthenticationError(f"Failed to initialize API client: {e}")
        
    def _test_connectivity(self) -> None:
        """Test API connectivity and authentication"""
        try:
            # Test connectivity
            self.client.ping()

            # Test authentication
            self.client.get_account()

            self.logger.info("API connectivity and authentication verified")
        
        except BinanceAPIException as e:
            if e.code == -2014:
                raise APIAuthenticationError("Invalid API key format")
            elif e.code == -1021:
                raise APIConnectionError("System time synchronization issue")
            else:
                raise APIAuthenticationError(f"Authentication failed: {e}")
        except Exception as e:
            raise APIConnectionError(f"Connection test failed: {e}")
        
    def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order on Binance.
        
        Args:
            order_data: Order parameters from strategy (already formatted)
            
        Returns:
            Dict with order result information
            
        Raises:
            APIOrderError: Business logic errors (insufficient balance, etc.)
            APIConnectionError: Network/connectivity issues
        """
        self.logger.info(f"Placing order: {order_data}")

        try:
            start_time = time.time()

            # Place order
            if order_data['type'] == 'MARKET':
                result = self.client.futures_create_order(**order_data)
            else: # LIMIT and other order types
                result = self.client.futures_create_order(**order_data)

            # Calculate API call duration
            duration = time.time() - start_time
            
            # Log successful order
            self.logger.info(
                f"Order placed successfully. OrderId: {result.get('orderId')}, "
                f"Duration: {duration:.2f}s"
            )

            # Return standardized response
            return self._standardize_order_response(result)
            
        except BinanceOrderException as e:
            # These are business logic errors (insufficient balance, invalid symbol, etc.)
            self.logger.error(f"Order failed - Business rule violation: {e}")
            raise APIOrderError(f"Order rejected: {e}")
            
        except BinanceAPIException as e:
            # Categorize different API exceptions
            if e.code in [-1021, -1022]:
                self.logger.error(f"Order failed - Timestamp issue: {e}")
                raise APIConnectionError(f"Time synchronization issue: {e}")
            elif e.code == -2010:
                self.logger.error(f"Order failed - Rejected: {e}")
                raise APIOrderError(f"Order rejected by exchange: {e}")
            elif e.code == -5007:
                self.logger.error(f"Order failed - Invalid quantity: {e}")
                raise APIOrderError(f"Invalid order quantity: {e}")
            else:
                self.logger.error(f"Order failed - API error: {e}")
                raise APIOrderError(f"API error: {e}")
                
        except Exception as e:
            # Network or other unexpected errors
            self.logger.error(f"Order failed - Unexpected error: {e}")
            raise APIConnectionError(f"Unexpected error during order placement: {e}")
        
    def get_account_balance(self) -> List[Dict[str, Any]]:
        """
        Get account balance information.
        
        Returns:
            List of balance information for each asset
        """
        try:
            self.logger.debug("Fetching account balance")

            account_info = self.client.futures_account()

            # Extract balance info
            balances = account_info.get('assets', [])

            # Filter to only show assests with non-zero balance
            non_zero_balances = [
                balance for balance in balances
                if Decimal(str(balance.get('walletBalance', 0) > 0))
            ]

            self.logger.debug(f"Retrieved {len(non_zero_balances)} non-zero balances")
            return non_zero_balances
        
        except BinanceAPIException as e:
            self.logger.error(f"Failed to get account balance: {e}")
            raise APIConnectionError(f"Failed to retrieve balance: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting balance: {e}")
            raise APIConnectionError(f"Unexpected error: {e}")
        
    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information (valid symbols, etc.).
        Returns:
            Exchange information including valid trading symbols
        """
        try:
            self.logger.debug("Fetching exchange information")

            exchange_info = self.client.futures_exchange_info()

            self.logger.debug(f"Retrieved info for {len(exchange_info.get('symbols', []))} symbols")
            return exchange_info
                
        except BinanceAPIException as e:
            self.logger.error(f"Failed to get exchange info: {e}")
            raise APIConnectionError(f"Failed to retrieve exchange info: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting exchange info: {e}")
            raise APIConnectionError(f"Unexpected error: {e}")
        
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            Symbol information dict or None if not found
        """
        try:
            exchange_info = self.get_exchange_info()
            
            for symbol_info in exchange_info.get('symbols', []):
                if symbol_info['symbol'] == symbol.upper():
                    return symbol_info
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting symbol info for {symbol}: {e}")
            raise APIConnectionError(f"Error retrieving symbol info: {e}")
        
    def _standardize_order_response(self, binance_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Binance's response format to our standardized format.
        
        This makes it easier for the rest of our code to work with responses.
        """
        return {
            'order_id': binance_response.get('orderId'),
            'symbol': binance_response.get('symbol'),
            'side': binance_response.get('side'),
            'type': binance_response.get('type'),
            'quantity': binance_response.get('origQty'),
            'price': binance_response.get('price'),
            'status': binance_response.get('status'),
            'time': binance_response.get('transactTime'),
            'raw_response': binance_response  # Keep original for debugging
        }
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get information about the client configuration."""
        return {
            'testnet': self.testnet,
            'base_url': 'https://testnet.binancefuture.com' if self.testnet else 'https://fapi.binance.com'
        }