"""
Trading strategies module.

This module provides various trading strategies that can be used with the DeepAgent Kraken trading bot.
"""

from typing import Dict, Any, Optional
import logging

from app.strategies.trend_rsi_strategy import TrendRSIStrategy

logger = logging.getLogger(__name__)


def create_strategy(strategy_name: str, config: Dict[str, Any]) -> Optional[Any]:
    """
    Factory function to create a strategy instance based on the strategy name.
    
    Args:
        strategy_name: Name of the strategy to create
        config: Configuration dictionary for the strategy
        
    Returns:
        Strategy instance or None if the strategy is not found
    """
    if strategy_name.lower() == 'trend_rsi':
        # Extract required parameters from config
        symbol = config.get('symbol', 'BTCUSDT')
        timeframe = config.get('timeframe', '1h')
        equity = config.get('equity', 10000.0)
        risk_pct = config.get('risk_pct', 0.01)
        
        logger.info(f"Creating TrendRSI strategy for {symbol} on {timeframe} timeframe")
        return TrendRSIStrategy(symbol=symbol, timeframe=timeframe, equity=equity, risk_pct=risk_pct)
    
    # Add more strategies here as they are implemented
    
    logger.error(f"Strategy '{strategy_name}' not found")
    return None


__all__ = ['create_strategy', 'TrendRSIStrategy']
