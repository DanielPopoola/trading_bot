import re
from typing import Dict, Any, Optional, Set
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from .logger import ContextLogger

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class InputValidator:
    """
    Validates all user input before processing orders.
    Uses Decimal for precise financial calculations.
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        self.logger = ContextLogger('bot.validator')
        self._valid_symbols: Optional[Set[str]] = None
        self._symbol_pattern = re.compile(r'^[A-Z0-9]{6,12}')
        
        # Decimal precision settings for financial calculations
        self.quantity_precision = 8
        self.price_precision = 8
    
    def validate_order_parameters(self, symbol: str, side: str, quantity, 
                                order_type: str, **kwargs) -> Dict[str, Any]:
        """
        Comprehensive validation with Decimal precision.
        
        Args:
            quantity: Can be float, string, or Decimal - we'll convert safely
        """
        self.logger.info(f"Validating order: {symbol} {side} {quantity} {order_type}", {
            'symbol': symbol,
            'side': side,
            'quantity': str(quantity),
            'order_type': order_type
        })
        
        validated_params = {
            'symbol': self._validate_symbol_format(symbol),
            'side': self._validate_side(side),
            'quantity': self._validate_quantity(quantity),
            'order_type': self._validate_order_type(order_type)
        }
        
        if 'price' in kwargs:
            validated_params['price'] = self._validate_price(kwargs['price'])
        
        # Business rule validation
        if self.api_client:
            self._validate_symbol_exists(validated_params['symbol'])
            self._validate_sufficient_balance(validated_params)
        
        return validated_params
    
    
    def _validate_symbol_format(self, symbol: str) -> str:
        """Validate trading symbol format."""
        if not isinstance(symbol, str):
            raise ValidationError("Symbol must be a string")
        
        symbol = symbol.strip().upper()
        
        if not symbol:
            raise ValidationError("Symbol cannot be empty")
        
        if not self._symbol_pattern.match(symbol):
            raise ValidationError(
                f"Invalid symbol format '{symbol}'. "
                f"Symbols should be 6-12 characters, letters and numbers only (e.g., BTCUSDT)"
            )
        
        return symbol
    
    def _validate_side(self, side: str) -> str:
        """Validate order side."""
        if not isinstance(side, str):
            raise ValidationError("Side must be a string")
        
        side = side.strip().lower()
        
        if side not in ['buy', 'sell']:
            raise ValidationError("Side must be 'buy' or 'sell'")
        
        return side
    

    def _validate_quantity(self, quantity) -> Decimal:
        """
        Validate and convert quantity to Decimal for precise calculations.
        
        Args:
            quantity: Input quantity (float, str, int, or Decimal)
            
        Returns:
            Decimal: Precisely represented quantity
        """
        try:
            # Convert to Decimal safely
            if isinstance(quantity, Decimal):
                decimal_quantity = quantity
            else:
                # Convert to string first to avoid float precision issues
                decimal_quantity = Decimal(str(quantity))
            
        except (InvalidOperation, ValueError, TypeError) as e:
            raise ValidationError(f"Quantity must be a valid number, got: {quantity}")
        
        # Validate positive
        if decimal_quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        # Validate reasonable bounds
        max_quantity = Decimal('1000000')  # 1 million
        min_quantity = Decimal('0.000001')  # 1 microunit
        
        if decimal_quantity > max_quantity:
            raise ValidationError(f"Quantity too large (max: {max_quantity})")
        
        if decimal_quantity < min_quantity:
            raise ValidationError(f"Quantity too small (min: {min_quantity})")
        
        # Round to appropriate precision (Binance typically uses 8 decimal places)
        rounded_quantity = decimal_quantity.quantize(
            Decimal('0.00000001'),
            rounding=ROUND_DOWN
        )
        
        if rounded_quantity != decimal_quantity:
            self.logger.info("Rounded quantity", {'from': str(decimal_quantity), 'to': str(rounded_quantity)})
        
        return rounded_quantity
    
    def _validate_order_type(self, order_type: str) -> str:
        """Validate order type against supported types."""
        if not isinstance(order_type, str):
            raise ValidationError("Order type must be a string")
        
        order_type = order_type.strip().lower()
        
        # Import here to avoid circular imports
        from strategies import OrderStrategyFactory
        
        supported_types = OrderStrategyFactory.get_supported_types()
        if order_type not in supported_types:
            raise ValidationError(
                f"Unsupported order type '{order_type}'. "
                f"Supported types: {', '.join(supported_types)}"
            )
        
        return order_type
    
    def _validate_price(self, price) -> Decimal:
        """Validate and convert price to Decimal."""
        try:
            if isinstance(price, Decimal):
                decimal_price = price
            else:
                decimal_price = Decimal(str(price))
                
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(f"Price must be a valid number, got: {price}")
        
        if decimal_price <= 0:
            raise ValidationError("Price must be positive")
        
        # Reasonable bounds check
        max_price = Decimal('10000000')  # 10 million per unit
        if decimal_price > max_price:
            raise ValidationError(f"Price too high (max: {max_price})")
        
        # Round to price precision
        rounded_price = decimal_price.quantize(
            Decimal('0.00000001'),
            rounding=ROUND_DOWN
        )
        
        return rounded_price
    
    def _validate_symbol_exists(self, symbol: str) -> None:
        """
        Validate that symbol exists on Binance.
        
        Uses caching to avoid repeated API calls.
        """
        if not self._valid_symbols:
            self._load_valid_symbols()
        
        if symbol not in self._valid_symbols:
            raise ValidationError(
                f"Symbol '{symbol}' is not available on Binance Futures. "
                f"Please check the symbol name."
            )
    
    def _load_valid_symbols(self) -> None:
        """Load valid symbols from Binance API (cached)."""
        try:
            self.logger.info("Loading valid symbols from Binance...")
            exchange_info = self.api_client.get_exchange_info()
            
            # Extract active trading symbols
            self._valid_symbols = {
                symbol['symbol'] 
                for symbol in exchange_info['symbols'] 
                if symbol['status'] == 'TRADING'
            }
            
            self.logger.info(f"Loaded {len(self._valid_symbols)} valid symbols", {'count': len(self._valid_symbols)})
            
        except Exception as e:
            self.logger.error("Failed to load valid symbols", data={'error': str(e), 'error_type': type}, exc_info=True)
            raise ValidationError(
                f"Unable to validate symbol against Binance. "
                f"Please check your internet connection. Error: {e}"
            )
    
    def _estimate_required_balance(self, params: Dict[str, Any]) -> Decimal:
        """
        Estimate required balance using Decimal arithmetic.
        
        Returns:
            Decimal: Required balance in USDT
        """
        if params['order_type'] == 'market':
            if params['side'] == 'buy':
                # Conservative estimate - in real implementation, get current price
                estimated_price = Decimal('50000')  # Conservative BTC price estimate
                return params['quantity'] * estimated_price
            else:
                return Decimal('0')
        
        elif params['order_type'] == 'limit':
            if params['side'] == 'buy':
                # Exact calculation for limit orders
                return params['quantity'] * params['price']
            else:
                return Decimal('0')
        
        return Decimal('0')
    
    def _validate_sufficient_balance(self, params: Dict[str, Any]) -> None:
        """Balance validation with Decimal precision."""
        try:
            account_info = self.api_client.get_account_balance()
            
            # Find USDT balance
            usdt_balance = Decimal('0')
            for balance in account_info:
                if balance['asset'] == 'USDT':
                    usdt_balance = Decimal(str(balance['availableBalance']))
                    break
            
            required_balance = self._estimate_required_balance(params)
            
            if usdt_balance < required_balance:
                raise ValidationError(
                    f"Insufficient balance. Required: {required_balance} USDT, "
                    f"Available: {usdt_balance} USDT"
                )
            
            self.logger.info("Balance check passed", {'available': str(usdt_balance), 'required': str(required_balance)})
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error("Failed to check balance", data={'error': str(e)}, exc_info=True)
            raise ValidationError(f"Unable to verify balance: {e}")