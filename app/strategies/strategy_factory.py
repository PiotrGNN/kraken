"""
Factory for creating trading strategies
"""
from typing import List, Optional

def get_trading_strategy(strategy_type: str, trading_pair: str, timeframes: List[str]):
    """
    Factory function to create and return the appropriate trading strategy
    
    Args:
        strategy_type: Type of strategy (regime_detection, technical, fundamental)
        trading_pair: Trading pair to apply the strategy to
        timeframes: List of timeframes to analyze
        
    Returns:
        An instance of the appropriate trading strategy
    """
    if strategy_type.lower() == "regime_detection":
        from app.strategies.regime_detection.strategy import RegimeDetectionStrategy
        return RegimeDetectionStrategy(trading_pair=trading_pair, timeframes=timeframes)
    elif strategy_type.lower() == "technical":
        from app.strategies.technical.strategy import TechnicalStrategy
        return TechnicalStrategy(trading_pair=trading_pair, timeframes=timeframes)
    elif strategy_type.lower() == "fundamental":
        from app.strategies.fundamental.strategy import FundamentalStrategy
        return FundamentalStrategy(trading_pair=trading_pair, timeframes=timeframes)
    else:
        raise ValueError(f"Unsupported strategy type: {strategy_type}")
