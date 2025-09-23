from abc import ABC, abstractmethod
from typing import Dict, Any


class OrderStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    """

    @abstractmethod
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """
        Each strategy validates its own specific parameters.
        
        Why separate validation? Because market orders don't need price,
        but limit orders do. Each strategy knows what it needs.
        
        Returns: Dict with validated parameters or raises ValidationError
        """
        pass

    @abstractmethod
    def prepare_order_data(self, symbol: str, side: str, quantity: float, **kwargs) -> Dict[str, Any]:
        """
        Convert user input into Binance API format.
        
        Why is this abstract? Because each order type has different required fields:
        - Market: symbol, side, quantity, type='MARKET'
        - Limit: symbol, side, quantity, price, type='LIMIT', timeInForce='GTC'
        
        Returns: Dict ready to send to Binance API
        """
        pass

    @abstractmethod
    def get_order_type(self) -> str:
        """
        Return the Binance order type string.
        This helps with logging and error messages.
        """
        pass
