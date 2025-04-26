"""
Utility functions for the DeepAgent Kraken trading bot.
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from a file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing the JSON data
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to load JSON file {file_path}: {str(e)}")
        return {}


def save_json_file(file_path: str, data: Dict[str, Any]) -> bool:
    """
    Save dictionary data to a JSON file.
    
    Args:
        file_path: Path to the JSON file
        data: Dictionary data to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON file {file_path}: {str(e)}")
        return False


def format_number(value: float, precision: int = 8) -> str:
    """
    Format a number with the specified precision.
    
    Args:
        value: Number to format
        precision: Decimal precision
        
    Returns:
        Formatted number as a string
    """
    format_str = f"{{:.{precision}f}}"
    return format_str.format(value)


def round_to_tick_size(value: float, tick_size: float) -> float:
    """
    Round a value to the nearest tick size.
    
    Args:
        value: Value to round
        tick_size: Tick size
        
    Returns:
        Rounded value
    """
    return round(value / tick_size) * tick_size


def calculate_order_quantity(price: float, amount: float, precision: int = 8) -> float:
    """
    Calculate order quantity based on price and amount.
    
    Args:
        price: Current price
        amount: Amount in quote currency
        precision: Decimal precision for the quantity
        
    Returns:
        Order quantity
    """
    quantity = amount / price
    return round(quantity, precision)


def parse_timeframe(timeframe: str) -> Tuple[int, str]:
    """
    Parse a timeframe string into value and unit.
    
    Args:
        timeframe: Timeframe string (e.g., '1h', '15m', '1d')
        
    Returns:
        Tuple of (value, unit)
    """
    if timeframe.endswith('m'):
        return int(timeframe[:-1]), 'minute'
    elif timeframe.endswith('h'):
        return int(timeframe[:-1]), 'hour'
    elif timeframe.endswith('d'):
        return int(timeframe[:-1]), 'day'
    elif timeframe.endswith('w'):
        return int(timeframe[:-1]), 'week'
    else:
        raise ValueError(f"Invalid timeframe format: {timeframe}")


def timeframe_to_seconds(timeframe: str) -> int:
    """
    Convert a timeframe string to seconds.
    
    Args:
        timeframe: Timeframe string (e.g., '1h', '15m', '1d')
        
    Returns:
        Number of seconds
    """
    value, unit = parse_timeframe(timeframe)
    
    if unit == 'minute':
        return value * 60
    elif unit == 'hour':
        return value * 60 * 60
    elif unit == 'day':
        return value * 60 * 60 * 24
    elif unit == 'week':
        return value * 60 * 60 * 24 * 7
    else:
        raise ValueError(f"Invalid timeframe unit: {unit}")


def normalize_symbol(symbol: str, exchange: str) -> str:
    """
    Normalize a symbol for a specific exchange.
    
    Args:
        symbol: Symbol to normalize
        exchange: Exchange name
        
    Returns:
        Normalized symbol
    """
    symbol = symbol.upper()
    
    if exchange.lower() == 'bybit':
        # Bybit uses BTCUSDT format
        return symbol
    elif exchange.lower() == 'okx':
        # OKX uses BTC-USDT format
        if '-' not in symbol:
            base, quote = symbol[:-4], symbol[-4:]
            if quote.startswith('USD'):
                return f"{base}-{quote}"
        return symbol
    elif exchange.lower() == 'binance':
        # Binance uses BTCUSDT format
        return symbol
    
    return symbol
