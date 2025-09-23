from .market_order import MarketOrderStrategy
from .limit_order import LimitOrderStrategy
from .base import OrderStrategy
from typing import List


class OrderStrategyFactory:
    """
    Factory to create the right strategy based on order type.
    """
    
    _strategies = {
        'market': MarketOrderStrategy,
        'limit': LimitOrderStrategy,
    }

    @classmethod
    def create_strategy(cls, order_type: str) -> OrderStrategy:
        """
        Create appropriate strategy instance.
        
        Args:
            order_type: 'market', 'limit', etc.    
        Returns:
            OrderStrategy instance
        Raises:
            ValueError: If order_type not supported
        """
        order_type = order_type.lower().strip()

        if order_type not in cls._strategies:
            supported_types = ', '.join(cls._strategies.keys())
            raise ValueError(f"Unsupported order type '{order_type}'. Supported types: {supported_types}")
        
        return cls._strategies[order_type]()
    
    @classmethod
    def get_supported_types(cls) -> List:
        """Return list of supported order types."""
        return list(cls._strategies.keys())