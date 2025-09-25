#!/usr/bin/env python3
"""
Simplified Trading Bot for Binance Futures Testnet
"""

import sys
from typing import Dict, Any

from config import Config
from bot.logger import setup_logging, ContextLogger
from bot.cli import TradingBotCLI
from bot.api_client import BinanceAPIClient, APIError, APIConnectionError, APIAuthenticationError
from bot.validator import InputValidator, ValidationError
from bot.error_handler import ErrorHandler
from strategies import OrderStrategyFactory


class TradingBotApp:
    """
    Main trading bot application that coordinates all components.
    """
    
    def __init__(self):
        """Initialize the trading bot application."""
        self.config = None
        self.logger = None
        self.api_client = None
        self.validator = None
        self.error_handler = None
        self.cli = None
        
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load configuration
            print("Loading configuration...")
            self.config = Config()
            print("✓ Configuration loaded")
            
            # Setup logging
            logging_config = self.config.get_logging_config()
            setup_logging(**logging_config)
            self.logger = ContextLogger('trading_bot.main')
            self.logger.info("Trading bot starting up")
            print("✓ Logging initialized")
            
            # Initialize error handler
            self.error_handler = ErrorHandler()
            print("✓ Error handler initialized")
            
            # Initialize API client
            print("Connecting to Binance...")
            credentials = self.config.get_api_credentials()
            self.api_client = BinanceAPIClient(
                api_key=credentials['api_key'],
                api_secret=credentials['api_secret'],
                testnet=True
            )
            print("✓ Connected to Binance Futures Testnet")
            
            # Initialize validator
            self.validator = InputValidator(api_client=self.api_client)
            print("✓ Input validator initialized")
            
            # Initialize CLI
            self.cli = TradingBotCLI()
            print("✓ CLI initialized")
            
            self.logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize trading bot: {e}"
            print(f"✗ {error_msg}")
            if self.logger:
                self.logger.error(error_msg, data={'error': str(e)}, exc_info=True)
            return False
    
    def run(self) -> int:
        """
        Run the trading bot application.
        
        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            # Initialize components
            if not self.initialize():
                return 1
            
            print("\n" + "="*50)
            print("🤖 Trading Bot Ready - Testnet Mode")
            print("="*50 + "\n")
            
            # Get order parameters from CLI
            order_params = self.cli.parse_arguments()
            
            # Show order summary and get confirmation
            if not self.cli.display_order_summary(order_params):
                print("Order cancelled by user.")
                return 0
            
            # Process the order
            return self._process_order(order_params)
            
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            if self.logger:
                self.logger.info("Application terminated by user")
            return 0
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            if self.logger:
                self.logger.error("Unexpected application error", data={'error': str(e)}, exc_info=True)
            return 1
    
    def _process_order(self, params: Dict[str, Any]) -> int:
        """
        Process a single order through the complete pipeline.
        
        Args:
            params: Order parameters from CLI
            
        Returns:
            Exit code (0 for success, 1 for error)
        """
        self.logger.info("Starting order processing", {'params': params})
        
        try:
            # Step 1: Validate input parameters
            print("\n🔍 Validating order parameters...")
            validated_params = self.validator.validate_order_parameters(**params)
            print("✓ Parameters validated")
            
            # Step 2: Create appropriate strategy
            print(f"📋 Preparing {params['order_type']} order strategy...")
            strategy = OrderStrategyFactory.create_strategy(params['order_type'])
            
            # Step 3: Prepare order data
            order_data = strategy.prepare_order_data(
                symbol=validated_params['symbol'],
                side=validated_params['side'],
                quantity=validated_params['quantity'],
                **{k: v for k, v in validated_params.items() if k not in ['symbol', 'side', 'quantity', 'order_type']}
            )
            print("✓ Order data prepared")
            
            # Step 4: Execute order with retry logic
            print("📤 Placing order on Binance...")
            
            @self.error_handler.with_retry("place_order")
            def place_order():
                return self.api_client.place_order(order_data)
            
            result = place_order()
            
            # Step 5: Display results
            self._display_order_result(result)
            
            self.logger.info("Order processing completed successfully", {'result': result})
            return 0
            
        except ValidationError as e:
            print(f"✗ Validation Error: {e}")
            self.logger.error("Order validation failed", data={'error': str(e), 'params': params})
            return 1
            
        except APIAuthenticationError as e:
            print(f"✗ Authentication Error: {e}")
            print("Please check your API credentials in the .env file")
            self.logger.error("API authentication failed", data={'error': str(e)})
            return 1
            
        except APIConnectionError as e:
            print(f"✗ Connection Error: {e}")
            print("Please check your internet connection and try again")
            self.logger.error("API connection failed", data={'error': str(e)})
            return 1
            
        except APIError as e:
            print(f"✗ Order Failed: {e}")
            self.logger.error("Order execution failed", data={'error': str(e), 'params': params})
            return 1
            
        except Exception as e:
            print(f"✗ Unexpected Error: {e}")
            self.logger.error("Unexpected error during order processing", data={'error': str(e), 'params': params}, exc_info=True)
            return 1
    
    def _display_order_result(self, result: Dict[str, Any]) -> None:
        """Display order execution results."""
        print("\n" + "="*50)
        print("🎉 ORDER EXECUTED SUCCESSFULLY")
        print("="*50)
        
        print(f"Order ID: {result['order_id']}")
        print(f"Symbol: {result['symbol']}")
        print(f"Side: {result['side']}")
        print(f"Type: {result['type']}")
        print(f"Quantity: {result['quantity']}")
        
        if result['price']:
            print(f"Price: {result['price']}")
        
        print(f"Status: {result['status']}")
        print(f"Time: {result['time']}")
        
        print("\n✓ Order details have been logged for your records")


def main():
    """Main entry point for the trading bot."""
    app = TradingBotApp()
    exit_code = app.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()