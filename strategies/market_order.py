from .base import OrderStrategy
from typing import Any, Dict


class MarketOrderStrategy(OrderStrategy):
    """
    Market Order: 'Buy/Sell RIGHT NOW at current market price'
    
    Characteristics:
    - Executes immediately
    - Price determined by market
    - Guaranteed execution (if valid symbol/balance)
    """
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        # Market orders shouldn't have price parameter
        if 'price' in kwargs:
            raise ValueError("Market orders don't accept price parameter. Use limit order for specific price.")
        
        return {}
    
    def prepare_order_data(self, symbol: str, side: str, quantity: float, **kwargs) -> Dict[str, Any]:
        """
        Prepare the exact format Binance API expects for market orders.
        """
        return {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': 'MARKET',
            'quantity': quantity
        }
    
    def get_order_type(self) -> str:
        return "MARKET"
    