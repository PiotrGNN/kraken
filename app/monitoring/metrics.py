"""
Metrics collector for the DeepAgent Kraken trading bot.
Exposes performance metrics to Prometheus.
"""
import logging
import time
from typing import Dict, Any, Optional
from prometheus_client import start_http_server, Counter, Gauge, Summary
import threading

# Configure logger
logger = logging.getLogger(__name__)

# Define Prometheus metrics
TRADE_COUNT = Counter('deepagent_trade_count', 'Total number of trades executed')
PNL_USD = Gauge('deepagent_pnl_usd', 'Profit and Loss in USD')
EQUITY_USD = Gauge('deepagent_equity_usd', 'Current equity in USD')
DRAWDOWN_PCT = Gauge('deepagent_drawdown_pct', 'Current drawdown percentage')
OPEN_RISK_USD = Gauge('deepagent_open_risk_usd', 'Current open risk in USD')
TRADE_EXECUTION_TIME = Summary('deepagent_trade_execution_seconds', 'Time spent executing trades')

# Environment metrics
ENV_SWITCH_TOTAL = Counter('deepagent_env_switch_total', 'Total number of environment switches')
CURRENT_ENV = Gauge('deepagent_current_env', 'Current environment (0=TESTNET, 1=MAINNET)')
TIME_IN_ENV_HOURS = Gauge('deepagent_time_in_env_hours', 'Time spent in current environment in hours')

# Reference to the order router and risk manager
_order_router = None
_risk_manager = None


class MetricsCollector:
    """Collects and updates metrics from the trading bot."""
    
    def __init__(self, order_router=None, risk_manager=None, collection_interval=5):
        """
        Initialize the metrics collector.
        
        Args:
            order_router: The order router instance
            risk_manager: The risk manager instance
            collection_interval: Interval in seconds to collect metrics
        """
        self.order_router = order_router
        self.risk_manager = risk_manager
        self.collection_interval = collection_interval
        self.running = False
        self.collection_thread = None
        
    def start(self):
        """Start the metrics collection thread."""
        if self.running:
            return
            
        self.running = True
        self.collection_thread = threading.Thread(
            target=self._collect_metrics_loop,
            daemon=True
        )
        self.collection_thread.start()
        logger.info("Metrics collection started")
        
    def stop(self):
        """Stop the metrics collection thread."""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("Metrics collection stopped")
        
    def _collect_metrics_loop(self):
        """Continuously collect metrics at the specified interval."""
        while self.running:
            try:
                self._update_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            time.sleep(self.collection_interval)
    
    def _update_metrics(self):
        """Update all Prometheus metrics with current values."""
        if not self.order_router or not self.risk_manager:
            logger.warning("Order router or risk manager not available for metrics collection")
            return
            
        try:
            # Get performance data from the order router and risk manager
            performance_data = self._get_performance_data()
            
            # Update Prometheus metrics
            if performance_data:
                PNL_USD.set(performance_data.get('pnl_usd', 0))
                EQUITY_USD.set(performance_data.get('equity_usd', 0))
                DRAWDOWN_PCT.set(performance_data.get('drawdown_pct', 0))
                OPEN_RISK_USD.set(performance_data.get('open_risk_usd', 0))
                # Trade count is a counter, so we only increment it when new trades occur
                new_trades = performance_data.get('new_trade_count', 0)
                if new_trades > 0:
                    TRADE_COUNT.inc(new_trades)
                    
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    def _get_performance_data(self) -> Dict[str, Any]:
        """
        Get performance data from the order router and risk manager.
        
        Returns:
            Dict containing performance metrics
        """
        data = {}
        
        try:
            # Get data from order router
            if self.order_router:
                # These methods would need to be implemented in the order router
                data['pnl_usd'] = self.order_router.get_pnl()
                data['equity_usd'] = self.order_router.get_equity()
                data['new_trade_count'] = self.order_router.get_new_trade_count()
            
            # Get data from risk manager
            if self.risk_manager:
                # These methods would need to be implemented in the risk manager
                data['drawdown_pct'] = self.risk_manager.get_drawdown_percentage()
                data['open_risk_usd'] = self.risk_manager.get_open_risk_usd()
                
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            
        return data


# Global metrics collector instance
_metrics_collector = None


def init_metrics(order_router=None, risk_manager=None):
    """
    Initialize the metrics collector with references to the order router and risk manager.
    
    Args:
        order_router: The order router instance
        risk_manager: The risk manager instance
    """
    global _order_router, _risk_manager, _metrics_collector
    
    _order_router = order_router
    _risk_manager = risk_manager
    
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(order_router, risk_manager)
    else:
        _metrics_collector.order_router = order_router
        _metrics_collector.risk_manager = risk_manager


def start_metrics_server(port=9000, addr=''):
    """
    Start the Prometheus metrics HTTP server and metrics collection.
    
    Args:
        port: Port to expose metrics on
        addr: Address to bind the server to
    """
    try:
        logger.info(f"Starting metrics server on port {port}")
        start_http_server(port, addr)
        
        if _metrics_collector:
            _metrics_collector.start()
        else:
            logger.warning("Metrics collector not initialized. Call init_metrics() first.")
            
        logger.info(f"Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        raise


def record_trade_execution_time(func):
    """
    Decorator to record the execution time of a trade.
    
    Args:
        func: The function to decorate
    
    Returns:
        Wrapped function that records execution time
    """
    def wrapper(*args, **kwargs):
        with TRADE_EXECUTION_TIME.time():
            return func(*args, **kwargs)
    return wrapper
