from .base import OrderStrategy
from typing import Any, Dict


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

        # Validate price is a positive number
        try:
            price = float(price)
            if price <= 0:
                raise ValueError("Price must be positive")
        except (ValueError, TypeError):
            raise ValueError("Price must be a valid positive number")
        
        return {'price': price}
    
    def prepare_order_data(self, symbol: str, side: str, quantity: float, **kwargs) -> Dict[str, Any]:
        """
        Prepare limit order for Binance API.
        """
        validated_params = self.validate_parameters(**kwargs)

        return {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': 'LIMIT',
            'quantity': quantity,
            'price': validated_params['price'],
            'timeInForce': 'GTC',  # Good Till Cancel - stays active until filled or cancelled
        }
    
    def get_order_type(self) -> str:
        return "LIMIT"