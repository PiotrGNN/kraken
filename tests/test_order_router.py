"""
Tests for the OrderRouter class.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch

from app.core.order_router import OrderRouter, OrderRouterStatus, OrderRouterError
from app.core.config import ExchangePriority

# Mock connector class for testing
class MockConnector:
    def __init__(self, name, priority=ExchangePriority.PRIMARY, is_healthy=True):
        self.name = name
        self.priority = priority
        self._is_healthy = is_healthy
        self.initialized = False
        
        # Mock methods
        self.get_balances = MagicMock(return_value={"balance": 1000})
        self.get_positions = MagicMock(return_value={"positions": []})
        self.get_open_orders = MagicMock(return_value={"orders": []})
        self.place_order = MagicMock(return_value={"orderId": "test123"})
        self.cancel_order = MagicMock(return_value={"success": True})
        
    async def initialize(self):
        self.initialized = True
        return self
        
    async def is_healthy(self):
        return self._is_healthy
        
    def set_health(self, is_healthy):
        self._is_healthy = is_healthy

# Mock the connector factory
@pytest.fixture
def mock_get_exchange_connector():
    with patch("app.core.order_router.get_exchange_connector") as mock:
        # Create mock connectors
        bybit_connector = MockConnector("bybit_v5", ExchangePriority.PRIMARY)
        okx_connector = MockConnector("okx", ExchangePriority.FAILOVER)
        binance_connector = MockConnector("binance", ExchangePriority.FAILOVER)
        
        # Configure the mock to return different connectors based on input
        def side_effect(exchange_name, priority):
            if exchange_name == "bybit_v5":
                return bybit_connector
            elif exchange_name == "okx":
                return okx_connector
            elif exchange_name == "binance":
                return binance_connector
            else:
                raise ValueError(f"Unknown exchange: {exchange_name}")
                
        mock.side_effect = side_effect
        
        # Store connectors in the mock for test access
        mock.connectors = {
            "bybit_v5": bybit_connector,
            "okx": okx_connector,
            "binance": binance_connector
        }
        
        yield mock

@pytest.mark.asyncio
async def test_order_router_initialization(mock_get_exchange_connector):
    """Test that the OrderRouter initializes correctly."""
    # Create OrderRouter
    router = OrderRouter(
        primary_exchange="bybit_v5",
        failover_exchanges=["okx", "binance"],
        health_check_interval=1  # Short interval for testing
    )
    
    # Initialize router
    await router.initialize()
    
    # Check that connectors were created
    assert mock_get_exchange_connector.call_count == 3
    assert router.current_connector_name == "bybit_v5"
    assert router.status == OrderRouterStatus.READY
    
    # Clean up
    router.stop_health_check_thread()

@pytest.mark.asyncio
async def test_order_router_failover(mock_get_exchange_connector):
    """Test that the OrderRouter fails over to a backup exchange when the primary is unhealthy."""
    # Create OrderRouter with short health check interval
    router = OrderRouter(
        primary_exchange="bybit_v5",
        failover_exchanges=["okx", "binance"],
        health_check_interval=1,  # Short interval for testing
        max_retry_attempts=1,     # Fail quickly for testing
        retry_delay=1
    )
    
    # Initialize router
    await router.initialize()
    
    # Verify initial state
    assert router.current_connector_name == "bybit_v5"
    
    # Make primary exchange unhealthy
    bybit_connector = mock_get_exchange_connector.connectors["bybit_v5"]
    bybit_connector.set_health(False)
    
    # Wait for health check and failover
    await asyncio.sleep(3)
    
    # Verify failover occurred
    assert router.current_connector_name == "okx"
    assert len(router.failover_history) == 1
    
    # Clean up
    router.stop_health_check_thread()

@pytest.mark.asyncio
async def test_order_router_manual_failover(mock_get_exchange_connector):
    """Test manual failover to a specific exchange."""
    # Create OrderRouter
    router = OrderRouter(
        primary_exchange="bybit_v5",
        failover_exchanges=["okx", "binance"],
        health_check_interval=60  # Long interval to avoid automatic failover
    )
    
    # Initialize router
    await router.initialize()
    
    # Verify initial state
    assert router.current_connector_name == "bybit_v5"
    
    # Manually failover to binance
    router.manual_failover("binance")
    
    # Verify failover occurred
    assert router.current_connector_name == "binance"
    assert len(router.failover_history) == 1
    assert router.failover_history[0]["reason"] == "Manual failover"
    
    # Clean up
    router.stop_health_check_thread()

@pytest.mark.asyncio
async def test_order_router_method_delegation(mock_get_exchange_connector):
    """Test that methods are properly delegated to the current connector."""
    # Create OrderRouter
    router = OrderRouter(
        primary_exchange="bybit_v5",
        failover_exchanges=["okx", "binance"]
    )
    
    # Initialize router
    await router.initialize()
    
    # Get the mock connector
    bybit_connector = mock_get_exchange_connector.connectors["bybit_v5"]
    
    # Test method delegation
    router.get_balances(coin="BTC")
    bybit_connector.get_balances.assert_called_once_with(coin="BTC")
    
    router.place_order(
        symbol="BTCUSDT",
        side="Buy",
        order_type="Market",
        qty="0.001"
    )
    bybit_connector.place_order.assert_called_once()
    
    # Clean up
    router.stop_health_check_thread()

@pytest.mark.asyncio
async def test_order_router_status(mock_get_exchange_connector):
    """Test the get_status method."""
    # Create OrderRouter
    router = OrderRouter(
        primary_exchange="bybit_v5",
        failover_exchanges=["okx", "binance"]
    )
    
    # Initialize router
    await router.initialize()
    
    # Get status
    status = router.get_status()
    
    # Verify status
    assert status["status"] == "ready"
    assert status["current_exchange"] == "bybit_v5"
    assert status["primary_exchange"] == "bybit_v5"
    assert status["failover_exchanges"] == ["okx", "binance"]
    assert "exchange_health" in status
    assert "bybit_v5" in status["exchange_health"]
    
    # Clean up
    router.stop_health_check_thread()
