"""
Exchange connectors module for the DeepAgent Kraken trading bot.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class ExchangeConnector(ABC):
    """
    Abstract base class for exchange connectors.
    
    All exchange connectors should implement these methods to provide
    a consistent interface for the order router.
    """
    
    @abstractmethod
    def get_klines(self, symbol: str, interval: str, limit: int = 200) -> List[Dict]:
        """
        Get candlestick data from the exchange.
        
        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candlesticks to retrieve
            
        Returns:
            List of candlestick data
        """
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict:
        """
        Get ticker information for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Ticker information
        """
        pass
    
    @abstractmethod
    def create_order(self, **kwargs) -> Dict:
        """
        Create an order on the exchange.
        
        Args:
            **kwargs: Order parameters
            
        Returns:
            Order information
        """
        pass
    
    @abstractmethod
    def update_order(self, order_id: str, symbol: str, **kwargs) -> Dict:
        """
        Update an existing order on the exchange.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            **kwargs: Parameters to update
            
        Returns:
            Updated order information
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """
        Cancel an order on the exchange.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            Cancellation confirmation
        """
        pass
    
    @abstractmethod
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        Get information about an order.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            Order information
        """
        pass
    
    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders.
        
        Args:
            symbol: Trading pair symbol (optional)
            
        Returns:
            List of open orders
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Dict:
        """
        Get position information for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Position information
        """
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict:
        """
        Get account information from the exchange.
        
        Returns:
            Account information
        """
        pass
