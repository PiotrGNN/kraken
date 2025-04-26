"""
Order router with failover logic.

This module provides functionality to route orders to different exchanges with failover logic.
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

from app.connectors.connector_factory import create_connector
from app.strategies import create_strategy
from app.risk.atr_risk import ATRRiskManager
from app.core.env_manager import get_env_manager, Environment

logger = logging.getLogger(__name__)


class OrderRouter:
    """
    Order router with failover logic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the order router.
        
        Args:
            config: Configuration dictionary for the order router
        """
        self.config = config
        self.env_manager = get_env_manager()
        self.exchanges = self._setup_exchanges(config.get('exchanges', []))
        self.primary_exchange = config.get('primary_exchange', '')
        self.strategy = self._setup_strategy(config.get('strategy', {}))
        self.risk_manager = self._setup_risk_manager(config.get('risk', {}))
        self.active_positions = {}
        self.order_history = []
        self.total_trades = 0
        self.current_equity = 0.0
        self.peak_equity = 0.0
        self.max_drawdown_pct = 0.0
        
        # Update environment manager with initial performance metrics
        self.env_manager.update_performance_metrics(
            equity=self.current_equity,
            trade_count=self.total_trades,
            max_drawdown_pct=self.max_drawdown_pct
        )
        
    def _setup_exchanges(self, exchange_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Set up exchange connectors.
        
        Args:
            exchange_configs: List of exchange configurations
            
        Returns:
            Dictionary of exchange connectors
        """
        exchanges = {}
        
        for exchange_config in exchange_configs:
            exchange_name = exchange_config.get('name', '')
            if not exchange_name:
                logger.error("Exchange name not provided in config")
                continue
            
            connector = create_connector(exchange_name, exchange_config)
            if connector:
                exchanges[exchange_name] = connector
        
        if not exchanges:
            logger.error("No valid exchanges configured")
        
        return exchanges
    
    def _setup_strategy(self, strategy_config: Dict[str, Any]) -> Optional[Any]:
        """
        Set up trading strategy.
        
        Args:
            strategy_config: Strategy configuration
            
        Returns:
            Strategy instance or None if setup fails
        """
        strategy_name = strategy_config.get('name', '')
        if not strategy_name:
            logger.error("Strategy name not provided in config")
            return None
        
        return create_strategy(strategy_name, strategy_config)
    
    def _setup_risk_manager(self, risk_config: Dict[str, Any]) -> ATRRiskManager:
        """
        Set up risk manager.
        
        Args:
            risk_config: Risk management configuration
            
        Returns:
            Risk manager instance
        """
        risk_pct = risk_config.get('risk_pct', 0.01)
        atr_multiplier = risk_config.get('atr_multiplier', 1.5)
        trailing_breakeven_atr = risk_config.get('trailing_breakeven_atr', 1.0)
        trailing_step_atr = risk_config.get('trailing_step_atr', 0.5)
        
        return ATRRiskManager(
            risk_pct=risk_pct,
            atr_multiplier=atr_multiplier,
            trailing_breakeven_atr=trailing_breakeven_atr,
            trailing_step_atr=trailing_step_atr
        )
    
    def get_exchange(self, exchange_name: Optional[str] = None) -> Optional[Any]:
        """
        Get exchange connector by name or primary exchange if name not provided.
        
        Args:
            exchange_name: Name of the exchange to get
            
        Returns:
            Exchange connector or None if not found
        """
        if not exchange_name:
            exchange_name = self.primary_exchange
        
        if exchange_name in self.exchanges:
            return self.exchanges[exchange_name]
        
        logger.error(f"Exchange '{exchange_name}' not found")
        return None
    
    def update_market_data(self, symbol: str, timeframe: str = '1h', limit: int = 500) -> bool:
        """
        Update market data for the strategy.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            limit: Number of candles to fetch
            
        Returns:
            True if update successful, False otherwise
        """
        if not self.strategy:
            logger.error("Strategy not initialized")
            return False
        
        # Try to get market data from primary exchange first
        exchange = self.get_exchange()
        if not exchange:
            logger.error("No valid exchange available")
            return False
        
        try:
            # Fetch candles from exchange
            candles = exchange.get_klines(symbol=symbol, interval=timeframe, limit=limit)
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert string values to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Update strategy with new data
            self.strategy.update_data(df)
            
            logger.info(f"Updated market data for {symbol} on {timeframe} timeframe")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update market data: {str(e)}")
            
            # Try failover exchanges
            for name, ex in self.exchanges.items():
                if name != self.primary_exchange:
                    try:
                        candles = ex.get_klines(symbol=symbol, interval=timeframe, limit=limit)
                        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            df[col] = df[col].astype(float)
                        self.strategy.update_data(df)
                        logger.info(f"Updated market data from failover exchange {name}")
                        return True
                    except Exception as e2:
                        logger.error(f"Failover exchange {name} also failed: {str(e2)}")
            
            return False
    
    def update_account_equity(self) -> bool:
        """
        Update account equity for position sizing.
        
        Returns:
            True if update successful, False otherwise
        """
        if not self.strategy:
            logger.error("Strategy not initialized")
            return False
        
        exchange = self.get_exchange()
        if not exchange:
            logger.error("No valid exchange available")
            return False
        
        try:
            # Get account balance
            balance = exchange.get_account_balance()
            equity = balance.get('equity', 0.0)
            
            # Update strategy with new equity
            self.strategy.update_equity(equity)
            
            logger.info(f"Updated account equity: {equity}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update account equity: {str(e)}")
            
            # Try failover exchanges
            for name, ex in self.exchanges.items():
                if name != self.primary_exchange:
                    try:
                        balance = ex.get_account_balance()
                        equity = balance.get('equity', 0.0)
                        self.strategy.update_equity(equity)
                        logger.info(f"Updated account equity from failover exchange {name}: {equity}")
                        return True
                    except Exception as e2:
                        logger.error(f"Failover exchange {name} also failed: {str(e2)}")
            
            return False
    
    def place_order(self, order_params: Dict[str, Any], exchange_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Place an order on the specified exchange with failover logic.
        
        Args:
            order_params: Order parameters
            exchange_name: Name of the exchange to place the order on
            
        Returns:
            Order response
        """
        if not exchange_name:
            exchange_name = self.primary_exchange
        
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            logger.error(f"Exchange '{exchange_name}' not found, trying failover exchanges")
            
            # Try failover exchanges
            for name, ex in self.exchanges.items():
                if name != exchange_name:
                    try:
                        logger.info(f"Trying failover exchange {name}")
                        response = ex.place_order(order_params)
                        logger.info(f"Order placed on failover exchange {name}")
                        
                        # Record order in history
                        order_record = {
                            'timestamp': time.time(),
                            'exchange': name,
                            'params': order_params,
                            'response': response,
                            'status': 'success',
                            'failover': True
                        }
                        self.order_history.append(order_record)
                        
                        return response
                    except Exception as e:
                        logger.error(f"Failover exchange {name} failed: {str(e)}")
            
            logger.error("All exchanges failed to place order")
            
            # Record failed order
            order_record = {
                'timestamp': time.time(),
                'exchange': exchange_name,
                'params': order_params,
                'response': None,
                'status': 'failed',
                'failover': False,
                'error': 'All exchanges failed'
            }
            self.order_history.append(order_record)
            
            return {'status': 'error', 'message': 'All exchanges failed to place order'}
        
        try:
            # Place order on primary exchange
            response = exchange.place_order(order_params)
            logger.info(f"Order placed on exchange {exchange_name}")
            
            # Record order in history
            order_record = {
                'timestamp': time.time(),
                'exchange': exchange_name,
                'params': order_params,
                'response': response,
                'status': 'success',
                'failover': False
            }
            self.order_history.append(order_record)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to place order on {exchange_name}: {str(e)}")
            
            # Try failover exchanges
            for name, ex in self.exchanges.items():
                if name != exchange_name:
                    try:
                        logger.info(f"Trying failover exchange {name}")
                        response = ex.place_order(order_params)
                        logger.info(f"Order placed on failover exchange {name}")
                        
                        # Record order in history
                        order_record = {
                            'timestamp': time.time(),
                            'exchange': name,
                            'params': order_params,
                            'response': response,
                            'status': 'success',
                            'failover': True
                        }
                        self.order_history.append(order_record)
                        
                        return response
                    except Exception as e2:
                        logger.error(f"Failover exchange {name} failed: {str(e2)}")
            
            logger.error("All exchanges failed to place order")
            
            # Record failed order
            order_record = {
                'timestamp': time.time(),
                'exchange': exchange_name,
                'params': order_params,
                'response': None,
                'status': 'failed',
                'failover': False,
                'error': str(e)
            }
            self.order_history.append(order_record)
            
            return {'status': 'error', 'message': str(e)}
    
    def update_order(self, order_id: str, update_params: Dict[str, Any], 
                    exchange_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing order on the specified exchange with failover logic.
        
        Args:
            order_id: ID of the order to update
            update_params: Parameters to update
            exchange_name: Name of the exchange where the order was placed
            
        Returns:
            Order update response
        """
        if not exchange_name:
            exchange_name = self.primary_exchange
        
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            logger.error(f"Exchange '{exchange_name}' not found")
            return {'status': 'error', 'message': f"Exchange '{exchange_name}' not found"}
        
        try:
            # Update order on exchange
            response = exchange.update_order(order_id, update_params)
            logger.info(f"Order {order_id} updated on exchange {exchange_name}")
            
            # Record order update in history
            order_record = {
                'timestamp': time.time(),
                'exchange': exchange_name,
                'order_id': order_id,
                'params': update_params,
                'response': response,
                'status': 'success',
                'type': 'update'
            }
            self.order_history.append(order_record)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to update order on {exchange_name}: {str(e)}")
            
            # Record failed update
            order_record = {
                'timestamp': time.time(),
                'exchange': exchange_name,
                'order_id': order_id,
                'params': update_params,
                'response': None,
                'status': 'failed',
                'type': 'update',
                'error': str(e)
            }
            self.order_history.append(order_record)
            
            return {'status': 'error', 'message': str(e)}
    
    def cancel_order(self, order_id: str, exchange_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel an order on the specified exchange.
        
        Args:
            order_id: ID of the order to cancel
            exchange_name: Name of the exchange where the order was placed
            
        Returns:
            Order cancellation response
        """
        if not exchange_name:
            exchange_name = self.primary_exchange
        
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            logger.error(f"Exchange '{exchange_name}' not found")
            return {'status': 'error', 'message': f"Exchange '{exchange_name}' not found"}
        
        try:
            # Cancel order on exchange
            response = exchange.cancel_order(order_id)
            logger.info(f"Order {order_id} cancelled on exchange {exchange_name}")
            
            # Record order cancellation in history
            order_record = {
                'timestamp': time.time(),
                'exchange': exchange_name,
                'order_id': order_id,
                'response': response,
                'status': 'success',
                'type': 'cancel'
            }
            self.order_history.append(order_record)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to cancel order on {exchange_name}: {str(e)}")
            
            # Record failed cancellation
            order_record = {
                'timestamp': time.time(),
                'exchange': exchange_name,
                'order_id': order_id,
                'response': None,
                'status': 'failed',
                'type': 'cancel',
                'error': str(e)
            }
            self.order_history.append(order_record)
            
            return {'status': 'error', 'message': str(e)}
    
    def execute_strategy(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """
        Execute the trading strategy and place orders based on signals.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            
        Returns:
            Execution result
        """
        if not self.strategy:
            logger.error("Strategy not initialized")
            return {'status': 'error', 'message': 'Strategy not initialized'}
        
        # Update market data
        if not self.update_market_data(symbol, timeframe):
            logger.error("Failed to update market data")
            return {'status': 'error', 'message': 'Failed to update market data'}
        
        # Update account equity
        if not self.update_account_equity():
            logger.warning("Failed to update account equity, using last known value")
        
        # Generate trading signal
        signal = self.strategy.generate_signal()
        logger.info(f"Strategy signal: {signal}")
        
        # Process signal
        if signal['action'] == 'open':
            # Prepare order parameters
            side = signal['side']
            size = signal['size']
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            
            # Create order parameters
            order_params = {
                'symbol': symbol,
                'side': 'buy' if side == 'long' else 'sell',
                'type': 'market',
                'quantity': size,
                'reduce_only': False
            }
            
            # Place entry order
            entry_response = self.place_order(order_params)
            
            if entry_response.get('status') == 'error':
                logger.error(f"Failed to place entry order: {entry_response.get('message')}")
                return {'status': 'error', 'message': f"Failed to place entry order: {entry_response.get('message')}"}
            
            # Place stop loss order
            stop_params = {
                'symbol': symbol,
                'side': 'sell' if side == 'long' else 'buy',
                'type': 'stop_market',
                'quantity': size,
                'stop_price': stop_loss,
                'reduce_only': True
            }
            
            stop_response = self.place_order(stop_params)
            
            if stop_response.get('status') == 'error':
                logger.error(f"Failed to place stop loss order: {stop_response.get('message')}")
                # Try to close the position if stop loss order fails
                self.cancel_order(entry_response.get('order_id', ''))
                return {'status': 'error', 'message': f"Failed to place stop loss order: {stop_response.get('message')}"}
            
            # Record active position
            self.active_positions[symbol] = {
                'side': side,
                'size': size,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'stop_order_id': stop_response.get('order_id', ''),
                'entry_time': time.time(),
                'entry_order_id': entry_response.get('order_id', '')
            }
            
            return {
                'status': 'success',
                'action': 'open',
                'side': side,
                'size': size,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'entry_order': entry_response,
                'stop_order': stop_response
            }
            
        elif signal['action'] == 'close':
            # Check if we have an active position for this symbol
            if symbol not in self.active_positions:
                logger.warning(f"No active position found for {symbol}")
                return {'status': 'warning', 'message': f"No active position found for {symbol}"}
            
            position = self.active_positions[symbol]
            
            # Create order parameters
            order_params = {
                'symbol': symbol,
                'side': 'sell' if position['side'] == 'long' else 'buy',
                'type': 'market',
                'quantity': position['size'],
                'reduce_only': True
            }
            
            # Place exit order
            exit_response = self.place_order(order_params)
            
            if exit_response.get('status') == 'error':
                logger.error(f"Failed to close position: {exit_response.get('message')}")
                return {'status': 'error', 'message': f"Failed to close position: {exit_response.get('message')}"}
            
            # Cancel stop loss order
            if position.get('stop_order_id'):
                self.cancel_order(position['stop_order_id'])
            
            # Remove from active positions
            del self.active_positions[symbol]
            
            return {
                'status': 'success',
                'action': 'close',
                'side': position['side'],
                'size': position['size'],
                'exit_order': exit_response
            }
            
        elif signal['action'] == 'update_stop':
            # Check if we have an active position for this symbol
            if symbol not in self.active_positions:
                logger.warning(f"No active position found for {symbol}")
                return {'status': 'warning', 'message': f"No active position found for {symbol}"}
            
            position = self.active_positions[symbol]
            
            # Update stop loss
            new_stop = signal['stop_loss']
            stop_order_id = position.get('stop_order_id', '')
            
            if not stop_order_id:
                logger.warning(f"No stop order ID found for {symbol}")
                return {'status': 'warning', 'message': f"No stop order ID found for {symbol}"}
            
            # Update stop loss order
            update_params = {
                'stop_price': new_stop
            }
            
            update_response = self.update_order(stop_order_id, update_params)
            
            if update_response.get('status') == 'error':
                logger.error(f"Failed to update stop loss: {update_response.get('message')}")
                return {'status': 'error', 'message': f"Failed to update stop loss: {update_response.get('message')}"}
            
            # Update active position
            self.active_positions[symbol]['stop_loss'] = new_stop
            
            return {
                'status': 'success',
                'action': 'update_stop',
                'side': position['side'],
                'new_stop': new_stop,
                'update_response': update_response
            }
        
        # No action needed
        return {
            'status': 'success',
            'action': signal['action'],
            'reason': signal.get('reason', '')
        }


    async def handle_env_change(self, target_env: Optional[Environment] = None) -> bool:
        """
        Handle environment change by closing all positions and reinitializing connectors.
        
        Args:
            target_env: Target environment to switch to (if None, determined by env_manager)
            
        Returns:
            True if environment change was successful, False otherwise
        """
        current_env = self.env_manager.get_environment()
        
        # Determine target environment if not provided
        if target_env is None:
            if self.env_manager.should_switch_to_mainnet():
                target_env = Environment.MAINNET
            else:
                # No need to switch
                return False
        
        # No change needed if already in target environment
        if current_env == target_env:
            logger.info(f"Already in {target_env} environment, no switch needed")
            return False
        
        logger.info(f"Preparing to switch environment from {current_env} to {target_env}")
        
        # Close all open positions
        await self.close_all_positions()
        
        # Switch environment in env_manager
        self.env_manager.switch_environment(target_env)
        
        # Reinitialize exchange connectors
        self.exchanges = self._setup_exchanges(self.config.get('exchanges', []))
        
        logger.info(f"Successfully switched environment from {current_env} to {target_env}")
        return True
    
    async def close_all_positions(self) -> bool:
        """
        Close all open positions across all exchanges.
        
        Returns:
            True if all positions were closed successfully, False otherwise
        """
        if not self.active_positions:
            logger.info("No active positions to close")
            return True
        
        success = True
        positions_to_close = list(self.active_positions.items())
        
        for symbol, position in positions_to_close:
            try:
                logger.info(f"Closing position for {symbol}")
                
                # Create order parameters
                order_params = {
                    'symbol': symbol,
                    'side': 'sell' if position['side'] == 'long' else 'buy',
                    'type': 'market',
                    'quantity': position['size'],
                    'reduce_only': True
                }
                
                # Place exit order
                exchange_name = position.get('exchange', self.primary_exchange)
                exit_response = self.place_order(order_params, exchange_name)
                
                if exit_response.get('status') == 'error':
                    logger.error(f"Failed to close position for {symbol}: {exit_response.get('message')}")
                    success = False
                    continue
                
                # Cancel stop loss order if it exists
                if position.get('stop_order_id'):
                    self.cancel_order(position['stop_order_id'], exchange_name)
                
                # Remove from active positions
                del self.active_positions[symbol]
                
                logger.info(f"Successfully closed position for {symbol}")
                
            except Exception as e:
                logger.error(f"Error closing position for {symbol}: {str(e)}")
                success = False
        
        return success
    
    def update_performance_metrics(self) -> None:
        """
        Update performance metrics and check if environment switch is needed.
        """
        try:
            # Get current equity
            for exchange_name in self.exchanges:
                try:
                    exchange = self.exchanges[exchange_name]
                    account_info = exchange.get_account_info()
                    self.current_equity = float(account_info.get('equity', 0.0))
                    break
                except Exception as e:
                    logger.error(f"Failed to get account info from {exchange_name}: {str(e)}")
            
            # Update peak equity
            if self.current_equity > self.peak_equity:
                self.peak_equity = self.current_equity
            
            # Calculate drawdown
            if self.peak_equity > 0:
                self.max_drawdown_pct = max(
                    self.max_drawdown_pct,
                    (self.peak_equity - self.current_equity) / self.peak_equity * 100
                )
            
            # Update environment manager with performance metrics
            self.env_manager.update_performance_metrics(
                equity=self.current_equity,
                trade_count=self.total_trades,
                max_drawdown_pct=self.max_drawdown_pct
            )
            
            logger.debug(f"Updated performance metrics: equity={self.current_equity}, trades={self.total_trades}, max_drawdown={self.max_drawdown_pct}%")
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {str(e)}")
    
    def get_pnl(self) -> float:
        """
        Get current profit and loss.
        
        Returns:
            Current PnL
        """
        # Simple implementation - difference between current equity and initial equity
        initial_equity = self.config.get('strategy', {}).get('equity', 0.0)
        return self.current_equity - initial_equity
    
    def get_equity(self) -> float:
        """
        Get current equity.
        
        Returns:
            Current equity
        """
        return self.current_equity
    
    def get_new_trade_count(self) -> int:
        """
        Get number of new trades since last call.
        
        Returns:
            Number of new trades
        """
        # This is a simple implementation - in a real system, you'd track this properly
        new_trades = len(self.order_history) - self.total_trades
        self.total_trades = len(self.order_history)
        return max(0, new_trades)
