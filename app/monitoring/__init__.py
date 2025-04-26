"""
Monitoring module for the DeepAgent Kraken trading bot.
"""

import logging
from typing import Dict, Any, Optional
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# Define metrics
ORDERS_TOTAL = Counter('orders_total', 'Total number of orders placed', ['exchange', 'symbol', 'side', 'status'])
POSITION_SIZE = Gauge('position_size', 'Current position size', ['symbol', 'side'])
EQUITY = Gauge('account_equity', 'Current account equity', ['exchange'])
STRATEGY_SIGNALS = Counter('strategy_signals', 'Strategy signals generated', ['symbol', 'action', 'reason'])
ORDER_LATENCY = Histogram('order_latency_seconds', 'Order placement latency in seconds', ['exchange'])
STOP_LOSS_UPDATES = Counter('stop_loss_updates', 'Number of stop loss updates', ['symbol', 'side'])


def setup_monitoring(config: Dict[str, Any]) -> None:
    """
    Set up monitoring based on configuration.
    
    Args:
        config: Monitoring configuration
    """
    if not config.get('enabled', False):
        logger.info("Monitoring is disabled")
        return
    
    port = config.get('metrics_port', 8000)
    
    try:
        start_http_server(port)
        logger.info(f"Started metrics server on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {str(e)}")


def record_order(exchange: str, symbol: str, side: str, status: str) -> None:
    """
    Record an order in metrics.
    
    Args:
        exchange: Exchange name
        symbol: Trading symbol
        side: Order side ('buy' or 'sell')
        status: Order status ('success' or 'failed')
    """
    ORDERS_TOTAL.labels(exchange=exchange, symbol=symbol, side=side, status=status).inc()


def update_position_size(symbol: str, side: str, size: float) -> None:
    """
    Update position size metric.
    
    Args:
        symbol: Trading symbol
        side: Position side ('long' or 'short')
        size: Position size
    """
    POSITION_SIZE.labels(symbol=symbol, side=side).set(size)


def update_equity(exchange: str, equity: float) -> None:
    """
    Update account equity metric.
    
    Args:
        exchange: Exchange name
        equity: Account equity
    """
    EQUITY.labels(exchange=exchange).set(equity)


def record_strategy_signal(symbol: str, action: str, reason: str) -> None:
    """
    Record a strategy signal in metrics.
    
    Args:
        symbol: Trading symbol
        action: Signal action ('open', 'close', 'update_stop', etc.)
        reason: Signal reason
    """
    STRATEGY_SIGNALS.labels(symbol=symbol, action=action, reason=reason).inc()


def record_order_latency(exchange: str, latency: float) -> None:
    """
    Record order placement latency.
    
    Args:
        exchange: Exchange name
        latency: Latency in seconds
    """
    ORDER_LATENCY.labels(exchange=exchange).observe(latency)


def record_stop_loss_update(symbol: str, side: str) -> None:
    """
    Record a stop loss update.
    
    Args:
        symbol: Trading symbol
        side: Position side ('long' or 'short')
    """
    STOP_LOSS_UPDATES.labels(symbol=symbol, side=side).inc()
