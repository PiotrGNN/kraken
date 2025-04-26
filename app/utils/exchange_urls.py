"""
Exchange URL configurations for different environments.

This module provides base URLs for different exchanges in TESTNET and MAINNET environments.
"""

from typing import Dict, Any
from app.core.env_manager import Environment

# Exchange base URLs for REST API and WebSocket
EXCHANGE_URLS = {
    # Bybit URLs
    "bybit": {
        Environment.TESTNET: {
            "rest": "https://api-testnet.bybit.com",
            "ws": "wss://stream-testnet.bybit.com"
        },
        Environment.MAINNET: {
            "rest": "https://api.bybit.com",
            "ws": "wss://stream.bybit.com"
        }
    },
    
    # OKX URLs
    "okx": {
        Environment.TESTNET: {
            "rest": "https://www.okx.com/api/v5/mock",
            "ws": "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"
        },
        Environment.MAINNET: {
            "rest": "https://www.okx.com/api/v5",
            "ws": "wss://ws.okx.com:8443/ws/v5/public"
        }
    },
    
    # Binance URLs
    "binance": {
        Environment.TESTNET: {
            "rest": "https://testnet.binance.vision/api",
            "ws": "wss://testnet.binance.vision/ws"
        },
        Environment.MAINNET: {
            "rest": "https://api.binance.com/api",
            "ws": "wss://stream.binance.com:9443/ws"
        }
    }
}


def get_exchange_url(exchange_name: str, environment: Environment, url_type: str = "rest") -> str:
    """
    Get the base URL for an exchange in a specific environment.
    
    Args:
        exchange_name: Name of the exchange
        environment: Environment (TESTNET or MAINNET)
        url_type: Type of URL (rest or ws)
        
    Returns:
        Base URL for the exchange in the specified environment
    """
    exchange_name = exchange_name.lower()
    
    if exchange_name not in EXCHANGE_URLS:
        raise ValueError(f"Exchange '{exchange_name}' not supported")
    
    if environment not in EXCHANGE_URLS[exchange_name]:
        raise ValueError(f"Environment '{environment}' not supported for exchange '{exchange_name}'")
    
    if url_type not in EXCHANGE_URLS[exchange_name][environment]:
        raise ValueError(f"URL type '{url_type}' not supported for exchange '{exchange_name}' in environment '{environment}'")
    
    return EXCHANGE_URLS[exchange_name][environment][url_type]
