"""
DeepAgent Kraken Trading Bot

Main entry point for the trading bot.
"""

import os
import sys
import time
import logging
import argparse
import json
import asyncio
from typing import Dict, Any

from app.core.order_router import OrderRouter
from app.strategies import create_strategy
from app.core.env_manager import get_env_manager, Environment
from app.core.scheduler import get_scheduler, setup_environment_check_task
from app.monitoring.metrics import init_metrics, start_metrics_server


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kraken_bot.log')
    ]
)

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        sys.exit(1)


def run_bot(config: Dict[str, Any], interval: int = 60) -> None:
    """
    Run the trading bot.
    
    Args:
        config: Configuration dictionary
        interval: Execution interval in seconds
    """
    try:
        # Initialize environment manager
        env_manager = get_env_manager()
        current_env = env_manager.get_environment()
        logger.info(f"Starting in {current_env} environment")
        
        # Create order router
        router = OrderRouter(config)
        
        # Initialize metrics
        init_metrics(order_router=router, risk_manager=router.risk_manager)
        
        # Start metrics server if monitoring is enabled
        monitoring_config = config.get('monitoring', {})
        if monitoring_config.get('enabled', True):
            metrics_port = monitoring_config.get('metrics_port', 8000)
            start_metrics_server(port=metrics_port)
            logger.info(f"Started metrics server on port {metrics_port}")
        
        # Set up environment check task
        env_check_interval = config.get('env_check_interval', 300)  # 5 minutes
        setup_environment_check_task(router, env_check_interval)
        logger.info(f"Set up environment check task with interval {env_check_interval}s")
        
        # Get trading parameters
        symbol = config.get('symbol', 'BTCUSDT')
        timeframe = config.get('timeframe', '1h')
        
        logger.info(f"Starting trading bot for {symbol} on {timeframe} timeframe")
        
        # Main trading loop
        while True:
            try:
                # Execute strategy
                result = router.execute_strategy(symbol, timeframe)
                
                if result.get('status') == 'error':
                    logger.error(f"Strategy execution failed: {result.get('message')}")
                else:
                    logger.info(f"Strategy execution result: {result}")
                
                # Update performance metrics
                router.update_performance_metrics()
                
                # Wait for next execution
                logger.info(f"Waiting {interval} seconds for next execution")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {str(e)}")
                time.sleep(10)  # Wait a bit before retrying
    
    except Exception as e:
        logger.error(f"Failed to initialize bot: {str(e)}")
        sys.exit(1)


def main():
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(description='DeepAgent Kraken Trading Bot')
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to configuration file')
    parser.add_argument('--interval', type=int, default=60, help='Execution interval in seconds')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Run the bot
    run_bot(config, args.interval)


if __name__ == '__main__':
    main()
