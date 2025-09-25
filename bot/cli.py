import argparse
import sys
from typing import Any, Dict, Optional
from strategies import OrderStrategyFactory
from .logger import ContextLogger


class TradingBotCLI:
    """
    Command Line Interface for the trading bot.
    """
    
    def __init__(self) -> None:
        self.parser = self._create_parser()
        self.logger = ContextLogger('bot.cli')
        self.logger.info("CLI initialized")

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the command line argument parser."""
        parser = argparse.ArgumentParser(
            description='Simplified Trading Bot for Binance Futures Testnet',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Market order
  python main.py --symbol BTCUSDT --side buy --quantity 0.001 --type market
  
  # Limit order  
  python main.py --symbol ETHUSDT --side sell --quantity 0.1 --type limit --price 2500.50
  
  # Interactive mode
  python main.py
            """
        )

        # Trading parameters
        parser.add_argument('--symbol', type=str, help='Trading pair (e.g., BTCUSDT)')
        parser.add_argument('--side', choices=['buy', 'sell'], help='Order side')
        parser.add_argument('--quantity', type=float, help='Order Quantity')
        parser.add_argument('--type', choices=OrderStrategyFactory.get_supported_types(), 
                          help='Order type')
        parser.add_argument('--price', type=float, help='Price for limit orders')
        
        # Optional parameters
        parser.add_argument('--interactive', action='store_true',
                          help='Force interactive mode')
        
        return parser
    
    def parse_arguments(self) -> Dict[str, Any]:
        """
        Parse command line arguments and return trading parameters.
        
        Returns:
            Dict with all trading parameters
        """
        args = self.parser.parse_args()
        self.logger.info("Parsing arguments", {'args': vars(args)})

        # If no arguments provided or interactive flag set, use interactive mode
        if self._should_use_interactive_mode(args):
            self.logger.info("Entering interactive mode")
            return self._interactive_mode()
        else:
            self.logger.info("Entering batch mode")
            return self._batch_mode(args)
        
    def _should_use_interactive_mode(self, args) -> bool:
        """Determine if we should use interactive mode."""
        # Force interactive if flag is set
        if args.interactive:
            return True
        
        # Use interactive if essential parameters are missing
        essential_params = [args.symbol,  args.side, args.quantity, args.type]
        return any(param is None for param in essential_params)
    
    def _batch_mode(self, args) -> Dict[str, Any]:
        """Process batch mode arguments"""
        # Validate required parameters are present
        required_params = ['symbol', 'side', 'quantity', 'type']
        missing_params = [param for param in required_params if getattr(args, param) is None]

        if missing_params:
            self.logger.error("Missing required parameters in batch mode", {'missing': missing_params})
            self.parser.error(f"Missing required parameters: {', '.join(missing_params)}")

        # Build parameters dict
        params = {
            'symbol': args.symbol.upper(),
            'side': args.side.lower(),
            'quantity': args.quantity,
            'order_type': args.type.lower(),
        }
        
        # Add optional parameters
        if args.price is not None:
            params['price'] = args.price
        
        return params
    
    def _interactive_mode(self) -> Dict[str, Any]:
        """Interactive mode - ask user for input step by step."""
        print("=== Binance Trading Bot (Interactive Mode) ===\n")

        try:
            # Get basic parameters
            symbol = self._get_symbol()
            side = self._get_side()
            quantity = self._get_quantity()
            order_type = self._get_order_type()
            
            params = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'order_type': order_type,
            }

            # Get order-type specific parameters
            if order_type == 'limit':
                params['price'] = self._get_price()
            
            return params
        
        except KeyboardInterrupt:
            self.logger.warning("Operation cancelled by user (KeyboardInterrupt)")
            print("\n\nOperation cancelled by user.")
            sys.exit(0)
        except EOFError:
            self.logger.error("Unexpected end of input (EOFError)")
            print("\n\nUnexpected end of input.")
            sys.exit(1)

    def _get_symbol(self) -> str:
        """Get trading symbol from user."""
        while True:
            symbol = input("Enter trading symbol (e.g., BTCUSDT): ").strip().upper()
            if symbol:
                return symbol
            print("Symbol cannot be empty. Please try again.")

    def _get_side(self) -> str:
        """Get order side from user."""
        while True:
            side = input("Enter side (buy/sell): ").strip().lower()
            if side in ['buy', 'sell']:
                return side
            print("Please enter 'buy' or 'sell'.")
    
    def _get_quantity(self) -> float:
        """Get order quantity from user."""
        while True:
            try:
                quantity = float(input("Enter quantity: ").strip())
                if quantity > 0:
                    return quantity
                else:
                    print("Quantity must be positive.")
            except ValueError:
                print("Please enter a valid number.")
    
    def _get_order_type(self) -> str:
        """Get order type from user."""
        supported_types = OrderStrategyFactory.get_supported_types()
        print(f"Supported order types: {', '.join(supported_types)}")
        
        while True:
            order_type = input("Enter order type: ").strip().lower()
            if order_type in supported_types:
                return order_type
            print(f"Please enter one of: {', '.join(supported_types)}")
    
    def _get_price(self) -> float:
        """Get price for limit orders."""
        while True:
            try:
                price = float(input("Enter limit price: ").strip())
                if price > 0:
                    return price
                else:
                    print("Price must be positive.")
            except ValueError:
                print("Please enter a valid price.")

    def display_order_summary(self, params: Dict[str, Any]) -> bool:
        """
        Display order summary and ask for confirmation.
        
        Returns:
            True if user confirms, False if they cancel
        """
        print("\n=== Order Summary ===")
        print(f"Symbol: {params['symbol']}")
        print(f"Side: {params['side'].upper()}")
        print(f"Quantity: {params['quantity']}")
        print(f"Order Type: {params['order_type'].upper()}")
        
        if 'price' in params:
            print(f"Price: {params['price']}")
        
        print(f"Environment: {'TESTNET' if params.get('testnet', True) else 'LIVE'}")
        
        while True:
            confirm = input("\nConfirm order? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                self.logger.info("User confirmed order", {'params': params})
                return True
            elif confirm in ['n', 'no']:
                self.logger.warning("User cancelled order", {'params': params})
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")