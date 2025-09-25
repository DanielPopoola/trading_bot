from .base import OrderStrategy
from typing import Any, Dict
from decimal import Decimal, InvalidOperation


class LimitOrderStrategy(OrderStrategy):
    """
    Limit Order: 'Buy/Sell only if price reaches my target'
    
    Characteristics:
    - May not execute immediately (or ever)
    - User sets the exact price
    - Only executes at specified price or better
    """

    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """
        Limit orders REQUIRE a price parameter.
        """
        if 'price' not in kwargs:
            raise ValueError("Limit orders require 'price' parameter")
        
        price = kwargs['price']

        # Handle both Decimal and other types
        if not isinstance(price, Decimal):
            try:
                price = Decimal(str(price))
            except (ValueError, TypeError, InvalidOperation):
                raise ValueError("Price must be a valid number")
        
        if price <= 0:
            raise ValueError("Price must be positive")
        
        return {'price': price}
    
    def prepare_order_data(self, symbol: str, side: str, quantity: Decimal, **kwargs) -> Dict[str, Any]:
        """
        Prepare limit order for Binance API.
        """
        validated_params = self.validate_parameters(**kwargs)

        return {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': 'LIMIT',
            'quantity': quantity,
            'price': str(validated_params['price']),
            'timeInForce': 'GTC',  # Good Till Cancel - stays active until filled or cancelled
        }
    
    def get_order_type(self) -> str:
        return "LIMIT"