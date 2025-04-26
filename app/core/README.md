# OrderRouter for DeepAgent Kraken Trading Bot

The OrderRouter is a core component of the DeepAgent Kraken trading bot that manages exchange connectors and handles failover logic between them. It provides a unified interface for trading strategies to interact with, abstracting away the details of which exchange is being used.

## Features

- **Exchange Management**: Manages primary and failover exchange connectors
- **Health Checking**: Continuously monitors exchange health to detect issues
- **Automatic Failover**: Automatically switches to backup exchanges when the primary exchange is unavailable
- **Position Synchronization**: Synchronizes positions and orders across exchanges when switching
- **Logging and Monitoring**: Logs exchange status and failover events for monitoring

## Usage

### Initialization

```python
from app.core.order_router import OrderRouter

# Create OrderRouter with Bybit V5 as primary and OKX and Binance as failovers
router = OrderRouter(
    primary_exchange="bybit_v5",
    failover_exchanges=["okx", "binance"],
    health_check_interval=30,  # Check exchange health every 30 seconds
    max_retry_attempts=3,      # Try 3 times before failing over
    retry_delay=5,             # Wait 5 seconds between retries
    auto_failover=True         # Automatically failover when primary is down
)

# Initialize the router
await router.initialize()
```

### Trading Operations

The OrderRouter provides the same interface as the exchange connectors, so you can use it just like you would use a connector:

```python
# Get account balance
balance = router.get_account_balance()

# Get market data
market_data = router.get_market_data("BTCUSDT")

# Place an order
order = router.place_order(
    symbol="BTCUSDT",
    side="Buy",
    order_type="Limit",
    qty="0.001",
    price="25000",
    time_in_force="GoodTillCancel",
    reduce_only=False,
    take_profit="30000",
    stop_loss="24000"
)

# Get open orders
open_orders = router.get_open_orders(symbol="BTCUSDT")

# Cancel an order
cancel_result = router.cancel_order(
    symbol="BTCUSDT",
    order_id=order["orderId"]
)
```

### Failover Management

```python
# Get router status
status = router.get_status()

# Manually failover to a specific exchange
router.manual_failover("okx")

# Get failover history
history = router.get_failover_history()
```

### Cleanup

```python
# Stop the health check thread when done
router.stop_health_check_thread()
```

## Configuration

The OrderRouter can be configured with the following parameters:

- `primary_exchange`: Name of the primary exchange (e.g., "bybit_v5")
- `failover_exchanges`: List of failover exchange names in priority order
- `health_check_interval`: Interval in seconds between health checks
- `max_retry_attempts`: Maximum number of retry attempts before failover
- `retry_delay`: Delay in seconds between retry attempts
- `auto_failover`: Whether to automatically failover to backup exchanges

## Error Handling

The OrderRouter provides the `OrderRouterError` exception class for handling errors:

```python
from app.core.order_router import OrderRouterError

try:
    # Use the router
    router.place_order(...)
except OrderRouterError as e:
    # Handle router-specific errors
    print(f"OrderRouter error: {str(e)}")
except Exception as e:
    # Handle other errors
    print(f"Error: {str(e)}")
```

## Status Monitoring

The OrderRouter provides the `OrderRouterStatus` enum for monitoring the status:

```python
from app.core.order_router import OrderRouterStatus

# Get router status
status = router.get_status()

# Check if router is ready
if status["status"] == OrderRouterStatus.READY.value:
    # Router is ready
    pass
elif status["status"] == OrderRouterStatus.SWITCHING.value:
    # Router is currently switching exchanges
    pass
elif status["status"] == OrderRouterStatus.ERROR.value:
    # Router is in an error state
    pass
```

## Example

See the [order_router_example.py](../../examples/order_router_example.py) script for a complete example of how to use the OrderRouter.
