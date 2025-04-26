"""
Tests for environment switching functionality.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.core.env_manager import EnvironmentManager, Environment
from app.core.order_router import OrderRouter


class TestEnvironmentSwitching(unittest.TestCase):
    """Test cases for environment switching functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock config
        self.config = {
            'exchanges': [
                {
                    'name': 'bybit',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret'
                }
            ],
            'primary_exchange': 'bybit',
            'strategy': {
                'name': 'trend_rsi',
                'equity': 10000.0
            },
            'risk': {
                'risk_pct': 0.01
            }
        }
        
        # Create environment manager with test settings
        with patch('app.core.env_manager.EnvironmentSettings') as mock_settings:
            mock_settings.return_value.environment = Environment.TESTNET
            mock_settings.return_value.auto_switch_enabled = True
            mock_settings.return_value.testnet_duration_hours = 48
            mock_settings.return_value.min_trades_for_switch = 10
            mock_settings.return_value.max_drawdown_pct_for_switch = 4.0
            
            self.env_manager = EnvironmentManager()
        
        # Mock metrics
        with patch('app.core.env_manager.ENV_SWITCH_TOTAL') as self.mock_switch_total, \
             patch('app.core.env_manager.CURRENT_ENV') as self.mock_current_env:
            self.env_manager.metrics_initialized = True
    
    def test_initial_environment(self):
        """Test initial environment is TESTNET."""
        self.assertEqual(self.env_manager.get_environment(), Environment.TESTNET)
    
    def test_manual_environment_switch(self):
        """Test manual environment switch."""
        # Switch to MAINNET
        self.env_manager.switch_environment(Environment.MAINNET)
        self.assertEqual(self.env_manager.get_environment(), Environment.MAINNET)
        self.mock_switch_total.inc.assert_called_once()
        self.mock_current_env.set.assert_called_with(1)
        
        # Switch back to TESTNET
        self.mock_switch_total.inc.reset_mock()
        self.mock_current_env.set.reset_mock()
        
        self.env_manager.switch_environment(Environment.TESTNET)
        self.assertEqual(self.env_manager.get_environment(), Environment.TESTNET)
        self.mock_switch_total.inc.assert_called_once()
        self.mock_current_env.set.assert_called_with(0)
    
    def test_should_switch_to_mainnet_criteria_not_met(self):
        """Test should_switch_to_mainnet when criteria are not met."""
        # Not enough time
        self.env_manager.start_time = datetime.now() - timedelta(hours=24)
        self.env_manager.trade_count = 20
        self.env_manager.max_drawdown_pct = 2.0
        self.assertFalse(self.env_manager.should_switch_to_mainnet())
        
        # Not enough trades
        self.env_manager.start_time = datetime.now() - timedelta(hours=72)
        self.env_manager.trade_count = 5
        self.env_manager.max_drawdown_pct = 2.0
        self.assertFalse(self.env_manager.should_switch_to_mainnet())
        
        # Drawdown too high
        self.env_manager.start_time = datetime.now() - timedelta(hours=72)
        self.env_manager.trade_count = 20
        self.env_manager.max_drawdown_pct = 5.0
        self.assertFalse(self.env_manager.should_switch_to_mainnet())
    
    def test_should_switch_to_mainnet_criteria_met(self):
        """Test should_switch_to_mainnet when all criteria are met."""
        self.env_manager.start_time = datetime.now() - timedelta(hours=72)
        self.env_manager.trade_count = 20
        self.env_manager.max_drawdown_pct = 2.0
        self.assertTrue(self.env_manager.should_switch_to_mainnet())
    
    def test_order_router_environment_switch(self):
        """Test environment switching in order router."""
        # Mock order router
        with patch('app.core.order_router.get_env_manager') as mock_get_env_manager, \
             patch('app.connectors.connector_factory.create_connector') as mock_create_connector:
            
            mock_get_env_manager.return_value = self.env_manager
            mock_connector = MagicMock()
            mock_create_connector.return_value = mock_connector
            
            # Create order router
            router = OrderRouter(self.config)
            
            # Mock close_all_positions
            router.close_all_positions = MagicMock(return_value=asyncio.Future())
            router.close_all_positions.return_value.set_result(True)
            
            # Test environment switch
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(router.handle_env_change(Environment.MAINNET))
            
            self.assertTrue(result)
            router.close_all_positions.assert_called_once()
            self.assertEqual(self.env_manager.get_environment(), Environment.MAINNET)


if __name__ == '__main__':
    unittest.main()
