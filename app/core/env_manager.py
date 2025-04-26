"""
Environment manager for the DeepAgent Kraken trading bot.

This module provides functionality to manage and switch between TESTNET and MAINNET environments.
"""

import os
import time
import logging
import yaml
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseSettings, Field

# Configure logger
logger = logging.getLogger(__name__)

class Environment(str, Enum):
    """Trading environment enum."""
    TESTNET = "testnet"
    MAINNET = "mainnet"

class EnvironmentSettings(BaseSettings):
    """Environment settings using pydantic for validation and loading from env vars or config file."""
    
    environment: Environment = Field(
        default=Environment.TESTNET,
        env="DEEPAGENT_ENV",
        description="Trading environment (testnet or mainnet)"
    )
    
    auto_switch_enabled: bool = Field(
        default=True,
        env="DEEPAGENT_AUTO_SWITCH_ENABLED",
        description="Whether to automatically switch from TESTNET to MAINNET based on performance"
    )
    
    testnet_duration_hours: int = Field(
        default=48,
        env="DEEPAGENT_TESTNET_DURATION_HOURS",
        description="Duration in hours to run in TESTNET before considering switch to MAINNET"
    )
    
    min_trades_for_switch: int = Field(
        default=10,
        env="DEEPAGENT_MIN_TRADES_FOR_SWITCH",
        description="Minimum number of trades required before considering switch to MAINNET"
    )
    
    max_drawdown_pct_for_switch: float = Field(
        default=4.0,
        env="DEEPAGENT_MAX_DRAWDOWN_PCT_FOR_SWITCH",
        description="Maximum drawdown percentage allowed for switch to MAINNET"
    )
    
    config_path: str = Field(
        default="config/env.yaml",
        env="DEEPAGENT_ENV_CONFIG_PATH",
        description="Path to environment configuration file"
    )
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "DEEPAGENT_"
        case_sensitive = False

class EnvironmentManager:
    """
    Environment manager for handling environment switching between TESTNET and MAINNET.
    
    This class manages the trading environment and provides functionality to switch
    between TESTNET and MAINNET environments based on performance criteria.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the environment manager.
        
        Args:
            config_path: Path to the environment configuration file
        """
        # Load settings from environment variables or config file
        self.settings = EnvironmentSettings()
        
        if config_path:
            self.settings.config_path = config_path
            
        # Try to load from config file if it exists
        self._load_config()
        
        # Performance tracking
        self.start_time = datetime.now()
        self.last_switch_time = self.start_time
        self.trade_count = 0
        self.peak_equity = 0.0
        self.current_equity = 0.0
        self.max_drawdown_pct = 0.0
        
        # Initialize metrics
        from app.monitoring.metrics import ENV_SWITCH_TOTAL, CURRENT_ENV
        self.metrics_initialized = True
        
        # Set initial environment metric
        CURRENT_ENV.set(1 if self.settings.environment == Environment.MAINNET else 0)
        
        logger.info(f"Environment manager initialized with environment: {self.settings.environment}")
    
    def _load_config(self) -> None:
        """Load configuration from YAML file if it exists."""
        try:
            if os.path.exists(self.settings.config_path):
                with open(self.settings.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                if config:
                    # Update settings from config file
                    for key, value in config.items():
                        if hasattr(self.settings, key):
                            setattr(self.settings, key, value)
                
                logger.info(f"Loaded environment configuration from {self.settings.config_path}")
        except Exception as e:
            logger.error(f"Failed to load environment configuration: {str(e)}")
    
    def _save_config(self) -> None:
        """Save current configuration to YAML file."""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(self.settings.config_path), exist_ok=True)
            
            # Convert settings to dict
            config = {
                "environment": self.settings.environment,
                "auto_switch_enabled": self.settings.auto_switch_enabled,
                "testnet_duration_hours": self.settings.testnet_duration_hours,
                "min_trades_for_switch": self.settings.min_trades_for_switch,
                "max_drawdown_pct_for_switch": self.settings.max_drawdown_pct_for_switch
            }
            
            # Save to file
            with open(self.settings.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Saved environment configuration to {self.settings.config_path}")
        except Exception as e:
            logger.error(f"Failed to save environment configuration: {str(e)}")
    
    def get_environment(self) -> Environment:
        """
        Get the current trading environment.
        
        Returns:
            Current environment (TESTNET or MAINNET)
        """
        return self.settings.environment
    
    def set_environment(self, environment: Environment, save: bool = True) -> None:
        """
        Set the trading environment.
        
        Args:
            environment: Environment to set (TESTNET or MAINNET)
            save: Whether to save the configuration to file
        """
        if environment not in [Environment.TESTNET, Environment.MAINNET]:
            logger.error(f"Invalid environment: {environment}")
            return
        
        # Update environment
        self.settings.environment = environment
        self.last_switch_time = datetime.now()
        
        # Update metrics
        from app.monitoring.metrics import ENV_SWITCH_TOTAL, CURRENT_ENV
        ENV_SWITCH_TOTAL.inc()
        CURRENT_ENV.set(1 if environment == Environment.MAINNET else 0)
        
        # Save configuration if requested
        if save:
            self._save_config()
        
        logger.info(f"Environment switched to {environment}")
    
    def update_performance_metrics(self, equity: float, trade_count: int, max_drawdown_pct: float) -> None:
        """
        Update performance metrics for environment switching decisions.
        
        Args:
            equity: Current account equity
            trade_count: Total number of trades executed
            max_drawdown_pct: Maximum drawdown percentage
        """
        self.current_equity = equity
        self.trade_count = trade_count
        self.max_drawdown_pct = max_drawdown_pct
        
        # Update peak equity
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        logger.debug(f"Updated performance metrics: equity={equity}, trades={trade_count}, max_drawdown={max_drawdown_pct}%")
    
    def should_switch_to_mainnet(self) -> bool:
        """
        Check if the bot should switch from TESTNET to MAINNET based on performance criteria.
        
        Returns:
            True if the bot should switch to MAINNET, False otherwise
        """
        # Only consider switching if in TESTNET and auto-switch is enabled
        if self.settings.environment != Environment.TESTNET or not self.settings.auto_switch_enabled:
            return False
        
        # Check if enough time has passed
        time_in_testnet = datetime.now() - self.start_time
        if time_in_testnet < timedelta(hours=self.settings.testnet_duration_hours):
            logger.debug(f"Not enough time in TESTNET: {time_in_testnet.total_seconds() / 3600:.1f} hours < {self.settings.testnet_duration_hours} hours")
            return False
        
        # Check if enough trades have been executed
        if self.trade_count < self.settings.min_trades_for_switch:
            logger.debug(f"Not enough trades: {self.trade_count} < {self.settings.min_trades_for_switch}")
            return False
        
        # Check if drawdown is within acceptable limits
        if self.max_drawdown_pct > self.settings.max_drawdown_pct_for_switch:
            logger.debug(f"Drawdown too high: {self.max_drawdown_pct}% > {self.settings.max_drawdown_pct_for_switch}%")
            return False
        
        # All criteria met, should switch to MAINNET
        logger.info(f"All criteria met for switching to MAINNET: time={time_in_testnet.total_seconds() / 3600:.1f} hours, trades={self.trade_count}, drawdown={self.max_drawdown_pct}%")
        return True
    
    def switch_environment(self, target_env: Optional[Environment] = None) -> bool:
        """
        Switch the trading environment.
        
        Args:
            target_env: Target environment to switch to (if None, toggle between TESTNET and MAINNET)
            
        Returns:
            True if switch was successful, False otherwise
        """
        current_env = self.settings.environment
        
        # Determine target environment
        if target_env is None:
            target_env = Environment.MAINNET if current_env == Environment.TESTNET else Environment.TESTNET
        
        # No change needed if already in target environment
        if current_env == target_env:
            logger.info(f"Already in {target_env} environment, no switch needed")
            return False
        
        # Set new environment
        self.set_environment(target_env)
        
        return True
    
    def get_config_path(self, exchange_name: str) -> str:
        """
        Get the configuration path for the current environment.
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            Path to the configuration file for the current environment
        """
        env_dir = "testnet" if self.settings.environment == Environment.TESTNET else "mainnet"
        return f"config/{env_dir}/{exchange_name}.json"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the environment manager.
        
        Returns:
            Dictionary with environment status information
        """
        time_in_current_env = datetime.now() - self.last_switch_time
        time_since_start = datetime.now() - self.start_time
        
        return {
            "environment": self.settings.environment,
            "auto_switch_enabled": self.settings.auto_switch_enabled,
            "time_in_current_env_hours": time_in_current_env.total_seconds() / 3600,
            "time_since_start_hours": time_since_start.total_seconds() / 3600,
            "trade_count": self.trade_count,
            "current_equity": self.current_equity,
            "peak_equity": self.peak_equity,
            "max_drawdown_pct": self.max_drawdown_pct,
            "testnet_duration_hours": self.settings.testnet_duration_hours,
            "min_trades_for_switch": self.settings.min_trades_for_switch,
            "max_drawdown_pct_for_switch": self.settings.max_drawdown_pct_for_switch
        }


# Global environment manager instance
_env_manager = None


def get_env_manager() -> EnvironmentManager:
    """
    Get the global environment manager instance.
    
    Returns:
        Global environment manager instance
    """
    global _env_manager
    
    if _env_manager is None:
        _env_manager = EnvironmentManager()
    
    return _env_manager
