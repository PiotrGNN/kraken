"""
Exchange connector factory.

This module provides a factory function to create exchange connectors based on the exchange name.
"""

from typing import Dict, Any, Optional
import logging
import json
import os

# Import connectors
from app.connectors.bybit.v5_connector import BybitV5Connector
from app.connectors.okx.connector import OKXConnector
from app.connectors.binance.connector import BinanceConnector

# Import environment manager
from app.core.env_manager import get_env_manager, Environment
from app.utils.exchange_urls import get_exchange_url

logger = logging.getLogger(__name__)


def create_connector(exchange_name: str, config: Dict[str, Any]) -> Optional[Any]:
    """
    Factory function to create an exchange connector based on the exchange name.
    
    Args:
        exchange_name: Name of the exchange to create a connector for
        config: Configuration dictionary for the connector
        
    Returns:
        Exchange connector instance or None if the exchange is not supported
    """
    exchange_name = exchange_name.lower()
    
    # Get environment manager
    env_manager = get_env_manager()
    current_env = env_manager.get_environment()
    
    # Check if we should load config from environment-specific file
    env_config_path = env_manager.get_config_path(exchange_name)
    if os.path.exists(env_config_path):
        try:
            with open(env_config_path, 'r') as f:
                env_config = json.load(f)
                # Merge with provided config, with env_config taking precedence
                for key, value in env_config.items():
                    config[key] = value
            logger.info(f"Loaded {current_env} configuration for {exchange_name} from {env_config_path}")
        except Exception as e:
            logger.error(f"Failed to load {current_env} configuration for {exchange_name}: {str(e)}")
    
    # Set testnet flag based on current environment
    testnet = current_env == Environment.TESTNET
    
    # Create connector based on exchange name
    if exchange_name == 'bybit':
        api_key = config.get('api_key', '')
        api_secret = config.get('api_secret', '')
        
        # Get base URLs for the current environment
        rest_url = get_exchange_url('bybit', current_env, 'rest')
        ws_url = get_exchange_url('bybit', current_env, 'ws')
        
        logger.info(f"Creating Bybit V5 connector (environment: {current_env})")
        return BybitV5Connector(
            api_key=api_key, 
            api_secret=api_secret, 
            testnet=testnet,
            base_url=rest_url,
            ws_url=ws_url
        )
    
    elif exchange_name == 'okx':
        api_key = config.get('api_key', '')
        api_secret = config.get('api_secret', '')
        passphrase = config.get('passphrase', '')
        
        # Get base URLs for the current environment
        rest_url = get_exchange_url('okx', current_env, 'rest')
        ws_url = get_exchange_url('okx', current_env, 'ws')
        
        logger.info(f"Creating OKX connector (environment: {current_env})")
        return OKXConnector(
            api_key=api_key, 
            api_secret=api_secret, 
            passphrase=passphrase, 
            testnet=testnet,
            base_url=rest_url,
            ws_url=ws_url
        )
    
    elif exchange_name == 'binance':
        api_key = config.get('api_key', '')
        api_secret = config.get('api_secret', '')
        
        # Get base URLs for the current environment
        rest_url = get_exchange_url('binance', current_env, 'rest')
        ws_url = get_exchange_url('binance', current_env, 'ws')
        
        logger.info(f"Creating Binance connector (environment: {current_env})")
        return BinanceConnector(
            api_key=api_key, 
            api_secret=api_secret, 
            testnet=testnet,
            base_url=rest_url,
            ws_url=ws_url
        )
    
    logger.error(f"Exchange '{exchange_name}' not supported")
    return None
