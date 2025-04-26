"""
Configuration module for the DeepAgent Kraken trading bot.
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class ExchangeConfig:
    """Exchange configuration settings."""
    name: str
    api_key: str
    api_secret: str
    testnet: bool = False

@dataclass
class StrategyConfig:
    """Strategy configuration settings."""
    name: str
    symbol: str
    interval: str = "1h"
    sma_fast_period: int = 50
    sma_slow_period: int = 200
    rsi_period: int = 14
    rsi_overbought: float = 65.0
    rsi_oversold: float = 35.0
    atr_period: int = 14
    risk_per_trade: float = 0.01  # 1% of equity
    atr_multiplier: float = 1.5
    trailing_stop_trigger: float = 1.0  # Move to breakeven after +1 ATR
    trailing_stop_step: float = 0.5  # Step 0.5 ATR

@dataclass
class BotConfig:
    """Main bot configuration settings."""
    primary_exchange: str = "bybit"
    failover_exchanges: List[str] = None
    strategy: str = "trend_rsi"
    symbols: List[str] = None
    intervals: List[str] = None
    log_level: str = "INFO"
    
    def __post_init__(self):
        if self.failover_exchanges is None:
            self.failover_exchanges = ["okx", "binance"]
        if self.symbols is None:
            self.symbols = ["BTCUSDT"]
        if self.intervals is None:
            self.intervals = ["1h"]

def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables and .env file.
    
    Returns:
        Dict containing configuration settings
    """
    # Load bot config
    bot_config = BotConfig(
        primary_exchange=os.getenv("PRIMARY_EXCHANGE", "bybit"),
        failover_exchanges=os.getenv("FAILOVER_EXCHANGES", "okx,binance").split(","),
        strategy=os.getenv("STRATEGY", "trend_rsi"),
        symbols=os.getenv("SYMBOLS", "BTCUSDT").split(","),
        intervals=os.getenv("INTERVALS", "1h").split(","),
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    # Load exchange configs
    exchanges = {}
    for exchange in [bot_config.primary_exchange] + bot_config.failover_exchanges:
        exchanges[exchange] = ExchangeConfig(
            name=exchange,
            api_key=os.getenv(f"{exchange.upper()}_API_KEY", ""),
            api_secret=os.getenv(f"{exchange.upper()}_API_SECRET", ""),
            testnet=os.getenv(f"{exchange.upper()}_TESTNET", "false").lower() == "true"
        )
    
    # Load strategy configs
    strategies = {}
    for symbol in bot_config.symbols:
        strategies[symbol] = StrategyConfig(
            name=bot_config.strategy,
            symbol=symbol
        )
    
    return {
        "bot": {
            "primary_exchange": bot_config.primary_exchange,
            "failover_exchanges": bot_config.failover_exchanges,
            "strategy": bot_config.strategy,
            "symbols": bot_config.symbols,
            "intervals": bot_config.intervals,
            "log_level": bot_config.log_level
        },
        "exchanges": {k: {
            "name": v.name,
            "api_key": v.api_key,
            "api_secret": v.api_secret,
            "testnet": v.testnet
        } for k, v in exchanges.items()},
        "strategies": {k: {
            "name": v.name,
            "symbol": v.symbol,
            "interval": v.interval,
            "sma_fast_period": v.sma_fast_period,
            "sma_slow_period": v.sma_slow_period,
            "rsi_period": v.rsi_period,
            "rsi_overbought": v.rsi_overbought,
            "rsi_oversold": v.rsi_oversold,
            "atr_period": v.atr_period,
            "risk_per_trade": v.risk_per_trade,
            "atr_multiplier": v.atr_multiplier,
            "trailing_stop_trigger": v.trailing_stop_trigger,
            "trailing_stop_step": v.trailing_stop_step
        } for k, v in strategies.items()}
    }
