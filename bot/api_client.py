import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from binance import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import time


from .logger import ContextLogger, log_api_call, log_order_success, log_order_failure, log_order_attempt



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
        self.logger = ContextLogger('bot.api_client', {
            'testnet': testnet,
            'client_type': 'binance'
        })
        self.testnet = testnet
        
        try:
            # Initialize the python-binance client
            self.client = Client(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet
            )
            self.logger.info("Binance client object created")
            
            # Test the connection immediately
            self._test_connectivity()
            
            # This log now only happens after successful connectivity test
            self.logger.info("Binance client initialized and verified")
            
        except Exception as e:
            self.logger.error("Failed to initialize Binance client", 
                              data={'error': str(e), 'error_type': type(e).__name__}, exc_info=True)
            # Re-raise as a specific authentication error to be caught in main.py
            raise APIAuthenticationError(f"Failed to initialize API client: {e}")
        
    def _test_connectivity(self) -> None:
        """Test API connectivity and authentication"""
        try:
            # Test connectivity
            self.client.ping()
            self.logger.debug("API ping successful")

            # Test authentication by fetching account info
            self.client.futures_account()
            self.logger.info("API connectivity and authentication verified")
        
        except BinanceAPIException as e:
            self.logger.error("API connectivity test failed", data={'error': str(e), 'code': e.code}, exc_info=True)
            if e.code == -2014:
                raise APIAuthenticationError(f"Invalid API Key format: {e}")
            elif e.code == -2015:
                raise APIAuthenticationError(f"Invalid API-key, IP, or permissions for action: {e}")
            elif e.code == -1021:
                raise APIConnectionError(f"System time synchronization issue: {e}")
            else:
                raise APIAuthenticationError(f"Authentication failed: {e}")
        except Exception as e:
            self.logger.error("Unexpected error during connection test", data={'error': str(e)}, exc_info=True)
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
        start_time = time.time()
        # Prepare data for logging, renaming 'type' to 'order_type' to match logger function
        log_data = order_data.copy()
        if 'type' in log_data:
            log_data['order_type'] = log_data.pop('type')
        log_order_attempt(self.logger, **log_data)

        try:
            # Place order
            if order_data['type'] == 'MARKET':
                result = self.client.futures_create_order(**order_data)
            else: # LIMIT and other order types
                result = self.client.futures_create_order(**order_data)

            # Calculate API call duration
            duration = time.time() - start_time
            
            # Log successful order
            log_api_call(self.logger, 'futures_create_order', 'POST', duration)
            log_order_success(self.logger, self._standardize_order_response(result))

            # Return standardized response
            return self._standardize_order_response(result)
            
        except BinanceOrderException as e:
            duration = time.time() - start_time 
            # These are business logic errors (insufficient balance, invalid symbol, etc.)
            log_api_call(self.logger, 'futures_create_order', 'POST', duration)
            log_order_failure(self.logger, e, order_data)
            raise APIOrderError(f"Order rejected: {e}")
            
        except BinanceAPIException as e:
            duration = time.time() - start_time
            log_api_call(self.logger, 'futures_create_order', 'POST', duration)
            log_order_failure(self.logger, e, order_data)
            # Categorize different API exceptions
            if e.code in [-1021, -1022]:
                raise APIConnectionError(f"Time synchronization issue: {e}")
            elif e.code == -2010:
                raise APIOrderError(f"Order rejected by exchange: {e}")
            elif e.code == -4016:
                raise APIOrderError(f"Limit price is too high. {e}")
            elif e.code == -4164:
                raise APIOrderError(f"Order notional is too small. {e}")
            elif e.code == -5007:
                raise APIOrderError(f"Invalid order quantity: {e}")
            else:
                raise APIOrderError(f"API error: {e}")
                
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(self.logger, 'futures_create_order', 'POST', duration)
            log_order_failure(self.logger, e, order_data)
            raise APIConnectionError(f"Unexpected error during order placement: {e}")
        
    def get_account_balance(self) -> List[Dict[str, Any]]:
        """
        Get account balance information.
        
        Returns:
            List of balance information for each asset
        """
        start_time = time.time()
        self.logger.debug("Fetching account balance")
        try:
            account_info = self.client.futures_account()
            duration = time.time() - start_time
            log_api_call(self.logger, 'futures_account', 'GET', duration)

            # Extract balance info
            balances = account_info.get('assets', [])

            # Filter to only show assests with non-zero balance
            non_zero_balances = [
                balance for balance in balances
                if Decimal(str(balance.get('walletBalance', 0))) > 0
            ]

            self.logger.debug(f"Retrieved {len(non_zero_balances)} non-zero balances", {'count': len(non_zero_balances)})
            return non_zero_balances
        
        except BinanceAPIException as e:
            duration = time.time() - start_time
            log_api_call(self.logger, 'futures_account', 'GET', duration)
            self.logger.error("Failed to get account balance", data={'error': str(e), 'code': e.code}, exc_info=True)
            if e.code == -2015:
                raise APIAuthenticationError(f"Authentication error: {e}")
            raise APIConnectionError(f"Failed to retrieve balance: {e}")
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(self.logger, 'futures_account', 'GET', duration)
            self.logger.error("Unexpected error getting balance", data={'error': str(e)}, exc_info=True)
            raise APIConnectionError(f"Unexpected error: {e}")
        
    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information (valid symbols, etc.).
        Returns:
            Exchange information including valid trading symbols
        """
        start_time = time.time()
        self.logger.debug("Fetching exchange information")
        try:
            exchange_info = self.client.futures_exchange_info()
            duration = time.time() - start_time
            log_api_call(self.logger, 'futures_exchange_info', 'GET', duration)

            count = len(exchange_info.get('symbols', []))
            self.logger.debug(f"Retrieved info for {count} symbols", {'count': count})
            return exchange_info
                
        except BinanceAPIException as e:
            duration = time.time() - start_time
            log_api_call(self.logger, 'futures_exchange_info', 'GET', duration)
            self.logger.error("Failed to get exchange info", data={'error': str(e), 'code': e.code}, exc_info=True)
            if e.code == -2015:
                raise APIAuthenticationError(f"Authentication error: {e}")
            raise APIConnectionError(f"Failed to retrieve exchange info: {e}")
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(self.logger, 'futures_exchange_info', 'GET', duration)
            self.logger.error("Unexpected error getting exchange info", data={'error': str(e)}, exc_info=True)
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
            self.logger.error(f"Error getting symbol info for {symbol}", data={'symbol': symbol, 'error': str(e)}, exc_info=True)
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

if __name__ == '__main__':
    # This block is for demonstration and testing purposes.
    # You can run this file directly to test the BinanceAPIClient.
    
    # IMPORTANT: Replace with your actual API keys for testing.
    # It is recommended to use environment variables for security.
    import os
    from .logger import setup_logging
    from config import Config

    config = Config()
    credentials = config.get_api_credentials()
    API_KEY = credentials['api_key']
    API_SECRET = credentials['api_secret']

    print(API_KEY, API_SECRET)

    # Initialize logging to see the output
    setup_logging()

    
    print("--- Testing BinanceAPIClient --- Ctr + C to stop")

    if "YOUR_API_KEY_HERE" in API_KEY or "YOUR_API_SECRET_HERE" in API_SECRET:
        print("\nWARNING: Using placeholder API keys.")
        print("Please replace 'YOUR_API_KEY_HERE' and 'YOUR_API_SECRET_HERE'")
        print("or set BINANCE_API_KEY and BINANCE_API_SECRET environment variables.\n")

    try:
        # 1. Initialize the client
        # This will automatically test connectivity and authentication.
        print("\n1. Initializing client...")
        client = BinanceAPIClient(api_key=API_KEY, api_secret=API_SECRET, testnet=True)
        print("   ✓ Client initialized successfully.")

        # 2. Get account balance
        print("\n2. Fetching account balance...")
        balance = client.get_account_balance()
        print(f"   ✓ Found {len(balance)} assets with non-zero balance.")
        # print(balance)

        # 3. Get exchange information
        print("\n3. Fetching exchange information...")
        exchange_info = client.get_exchange_info()
        print(f"   ✓ Loaded info for {len(exchange_info.get('symbols', []))} symbols.")

        # 4. Place a test order (EXAMPLE - be careful)
        # This is commented out by default to prevent accidental orders.
        print("\n4. Placing a test order...")
        test_order = {
             'symbol': 'BTCUSDT',
             'side': 'BUY',
             'type': 'MARKET',
             'quantity': '0.001'
        }
        try:
            order_result = client.place_order(test_order)
            print("   ✓ Test order placed successfully:")
            print(order_result)
        except APIOrderError as e:
            print(f"   ✗ Order placement failed as expected (e.g. insufficient funds): {e}")

    except APIAuthenticationError as e:
        print(f"\n✗ AUTHENTICATION FAILED: {e}")
        print("   Please check your API key, secret, and IP permissions.")
    except APIConnectionError as e:
        print(f"\n✗ CONNECTION FAILED: {e}")
        print("   Please check your internet connection and system time.")
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
    

    print("\n--- Test complete ---")