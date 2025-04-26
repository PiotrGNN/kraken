"""
Core trading bot implementation
"""
import logging
import asyncio
from typing import Dict, List, Optional
from app.core.config import settings, Environment, ExchangePriority
from app.connectors.connector_factory import get_exchange_connector
from app.strategies.strategy_factory import get_trading_strategy
from app.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class TradingBot:
    """Main trading bot class that orchestrates all components"""
    
    def __init__(self):
        self.environment = settings.ENVIRONMENT
        self.connectors = {}
        self.strategies = {}
        self.risk_manager = RiskManager()
        self.is_running = False
        self.trading_tasks = []
    
    async def initialize(self):
        """Initialize exchange connectors and trading strategies"""
        logger.info(f"Initializing trading bot in {self.environment} mode")
        
        # Initialize primary exchange (Bybit)
        self.connectors["bybit"] = get_exchange_connector(
            "bybit", 
            priority=ExchangePriority.PRIMARY
        )
        
        # Initialize failover exchanges
        self.connectors["okx"] = get_exchange_connector(
            "okx", 
            priority=ExchangePriority.FAILOVER
        )
        self.connectors["binance"] = get_exchange_connector(
            "binance", 
            priority=ExchangePriority.FAILOVER
        )
        
        # Initialize trading strategies
        for pair in settings.TRADING_PAIRS:
            self.strategies[pair] = get_trading_strategy(
                strategy_type="regime_detection",
                trading_pair=pair,
                timeframes=settings.TRADING_TIMEFRAMES
            )
        
        # Initialize risk manager
        await self.risk_manager.initialize()
        
        logger.info("Trading bot initialization complete")
    
    async def start_trading(self):
        """Start the trading process"""
        if self.is_running:
            logger.warning("Trading bot is already running")
            return
        
        logger.info("Starting trading operations")
        self.is_running = True
        
        # Start trading tasks for each pair
        for pair, strategy in self.strategies.items():
            task = asyncio.create_task(self.trading_loop(pair, strategy))
            self.trading_tasks.append(task)
    
    async def stop_trading(self):
        """Stop the trading process"""
        if not self.is_running:
            logger.warning("Trading bot is not running")
            return
        
        logger.info("Stopping trading operations")
        self.is_running = False
        
        # Cancel all trading tasks
        for task in self.trading_tasks:
            task.cancel()
        
        # Wait for all tasks to complete
        if self.trading_tasks:
            await asyncio.gather(*self.trading_tasks, return_exceptions=True)
        
        self.trading_tasks = []
        logger.info("Trading operations stopped")
    
    async def trading_loop(self, pair, strategy):
        """Main trading loop for a specific pair"""
        logger.info(f"Starting trading loop for {pair}")
        
        while self.is_running:
            try:
                # Get primary exchange connector
                connector = self.connectors[settings.DEFAULT_EXCHANGE]
                
                # Check if primary exchange is available, if not switch to failover
                if not await connector.is_healthy():
                    logger.warning(f"Primary exchange {settings.DEFAULT_EXCHANGE} is not healthy, switching to failover")
                    for name, backup_connector in self.connectors.items():
                        if name != settings.DEFAULT_EXCHANGE and await backup_connector.is_healthy():
                            connector = backup_connector
                            logger.info(f"Switched to failover exchange {name}")
                            break
                
                # Get market data
                market_data = await connector.get_market_data(pair)
                
                # Analyze market regime
                regime = await strategy.detect_regime(market_data)
                
                # Generate trading signals
                signal = await strategy.generate_signal(market_data, regime)
                
                # Apply risk management
                approved_signal = await self.risk_manager.validate_signal(signal, pair)
                
                # Execute trade if signal is approved
                if approved_signal:
                    await connector.execute_trade(approved_signal)
                
                # Wait for next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in trading loop for {pair}: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def get_status(self):
        """Get the current status of the trading bot"""
        return {
            "is_running": self.is_running,
            "environment": self.environment,
            "active_pairs": list(self.strategies.keys()),
            "exchanges": {
                name: {
                    "is_healthy": await connector.is_healthy(),
                    "priority": connector.priority
                }
                for name, connector in self.connectors.items()
            }
        }
