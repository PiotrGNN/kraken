"""
Binance exchange connector implementation for DeepAgent Kraken trading bot.

This module provides a connector for the Binance API using the CCXT library.
It includes functionality for authentication, fetching account information,
getting market data, placing orders, and managing positions.
"""
import logging
import time
import ccxt
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from functools import wraps

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings, ExchangePriority

logger = logging.getLogger(__name__)

# Define exception types that should trigger retries
RETRY_EXCEPTIONS = (ConnectionError, TimeoutError, ccxt.NetworkError)

def handle_rate_limit(func):
    """
    Decorator to handle rate limiting errors from Binance API.
    Implements exponential backoff when rate limits are hit.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ccxt.RateLimitExceeded as e:
            # Extract retry-after header if available
            retry_after = 1  # Default to 1 second
            if hasattr(e, "response") and e.response and "retry-after" in e.response.headers:
                retry_after = int(e.response.headers["retry-after"])
            
            logger.warning(f"Rate limit hit, sleeping for {retry_after} seconds")
            time.sleep(retry_after)
            return func(*args, **kwargs)
        except Exception as e:
            raise
    return wrapper


class BinanceConnector:
    """
    Connector for the Binance API using CCXT.
    
    This class provides methods for interacting with the Binance API,
    including authentication, fetching account information, getting market data,
    placing orders, and managing positions.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        api_secret: Optional[str] = None, 
        testnet: bool = False,
        priority: ExchangePriority = ExchangePriority.FAILOVER
    ):
        """
        Initialize the Binance connector.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Whether to use the testnet API
            priority: Priority of the exchange (primary or failover)
        """
        self.api_key = api_key or settings.BINANCE_API_KEY
        self.api_secret = api_secret or settings.BINANCE_API_SECRET
        self.testnet = testnet if testnet is not None else settings.BINANCE_TESTNET
        self.priority = priority
        self.client = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize the Binance client"""
        logger.info(f"Initializing Binance connector (testnet: {self.testnet})")
        
        # Configure CCXT Binance client
        options = {
            'adjustForTimeDifference': True,
            'recvWindow': 10000,
            'defaultType': 'future',  # Use futures by default for perpetual contracts
        }
        
        # Set up the client
        self.client = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': options
        })
        
        # Set testnet if required
        if self.testnet:
            self.client.set_sandbox_mode(True)
            
        self.initialized = True
        return self
    
    def _ensure_initialized(self):
        """Ensure the client is initialized before making API calls"""
        if not self.initialized or not self.client:
            raise RuntimeError("Binance connector not initialized. Call initialize() first.")
    
    def _handle_ccxt_error(self, e: Exception):
        """
        Handle CCXT exceptions and convert them to appropriate error messages.
        
        Args:
            e: CCXT exception
            
        Raises:
            Exception: Converted exception with appropriate error message
        """
        error_msg = str(e)
        
        if isinstance(e, ccxt.AuthenticationError):
            logger.error(f"Authentication error: {error_msg}")
            raise Exception(f"Binance authentication failed: {error_msg}")
        elif isinstance(e, ccxt.InsufficientFunds):
            logger.error(f"Insufficient funds: {error_msg}")
            raise Exception(f"Insufficient funds on Binance: {error_msg}")
        elif isinstance(e, ccxt.InvalidOrder):
            logger.error(f"Invalid order: {error_msg}")
            raise Exception(f"Invalid order on Binance: {error_msg}")
        elif isinstance(e, ccxt.ExchangeError):
            logger.error(f"Exchange error: {error_msg}")
            raise Exception(f"Binance exchange error: {error_msg}")
        elif isinstance(e, ccxt.NetworkError):
            logger.error(f"Network error: {error_msg}")
            raise Exception(f"Network error connecting to Binance: {error_msg}")
        else:
            logger.error(f"Unexpected error: {error_msg}")
            raise Exception(f"Unexpected error with Binance: {error_msg}")
    
    async def is_healthy(self) -> bool:
        """
        Check if the exchange connection is healthy.
        
        Returns:
            True if the connection is healthy, False otherwise
        """
        try:
            self._ensure_initialized()
            # Use server time endpoint as a simple health check
            self.client.fetch_time()
            return True
        except Exception as e:
            logger.error(f"Binance health check failed: {str(e)}")
            return False
    
    @handle_rate_limit
    def get_balances(self, coin: Optional[str] = None) -> Dict:
        """
        Get account balance information.
        
        Args:
            coin: Optional specific coin to get balance for
            
        Returns:
            Dictionary containing balance information
        """
        self._ensure_initialized()
        
        try:
            balances = self.client.fetch_balance()
            
            if coin:
                # Filter for specific coin if requested
                if coin in balances['total']:
                    return {
                        'info': balances['info'],
                        'total': {coin: balances['total'][coin]},
                        'free': {coin: balances['free'][coin]},
                        'used': {coin: balances['used'][coin]}
                    }
                else:
                    return {'total': {}, 'free': {}, 'used': {}}
            
            return balances
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def get_positions(self, symbol: Optional[str] = None) -> Dict:
        """
        Get current positions.
        
        Args:
            symbol: Optional specific symbol to get positions for
            
        Returns:
            Dictionary containing position information
        """
        self._ensure_initialized()
        
        try:
            # Fetch positions
            positions = self.client.fetch_positions(symbol)
            
            # Format the response to match Bybit's structure
            formatted_positions = []
            for pos in positions:
                if float(pos.get('contracts', 0)) > 0:
                    formatted_positions.append({
                        'symbol': pos.get('symbol'),
                        'side': 'Buy' if pos.get('side') == 'long' else 'Sell',
                        'size': float(pos.get('contracts', 0)),
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'leverage': float(pos.get('leverage', 0))
                    })
            
            return {'list': formatted_positions}
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def get_ohlcv(
        self, 
        symbol: str, 
        interval: str = "1m", 
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Dict:
        """
        Get OHLCV (Kline) data.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            interval: Kline interval (e.g., "1m" for 1 minute, "1h" for 1 hour)
            limit: Number of candles to retrieve (max 1000)
            start_time: Optional start timestamp in milliseconds
            end_time: Optional end timestamp in milliseconds
            
        Returns:
            Dictionary containing OHLCV data
        """
        self._ensure_initialized()
        
        # Map interval to CCXT timeframe format
        timeframe_map = {
            "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
            "60": "1h", "120": "2h", "240": "4h", "360": "6h", "720": "12h",
            "D": "1d", "1D": "1d", "W": "1w", "1W": "1w", "M": "1M", "1M": "1M"
        }
        
        timeframe = timeframe_map.get(interval, interval)
        
        try:
            # Fetch OHLCV data
            params = {}
            if start_time:
                params['since'] = start_time
            if end_time:
                params['until'] = end_time
                
            ohlcv = self.client.fetch_ohlcv(symbol, timeframe, limit=limit, params=params)
            
            # Format the response to match Bybit's structure
            formatted_ohlcv = []
            for candle in ohlcv:
                formatted_ohlcv.append([
                    candle[0],  # timestamp
                    str(candle[1]),  # open
                    str(candle[2]),  # high
                    str(candle[3]),  # low
                    str(candle[4]),  # close
                    str(candle[5])   # volume
                ])
            
            return {'list': formatted_ohlcv}
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def get_orderbook(self, symbol: str, limit: int = 50) -> Dict:
        """
        Get orderbook data.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            limit: Depth of the orderbook (max 500)
            
        Returns:
            Dictionary containing orderbook data
        """
        self._ensure_initialized()
        
        try:
            # Fetch orderbook
            orderbook = self.client.fetch_order_book(symbol, limit=limit)
            
            # Format the response to match Bybit's structure
            formatted_bids = [[str(price), str(amount)] for price, amount in orderbook['bids']]
            formatted_asks = [[str(price), str(amount)] for price, amount in orderbook['asks']]
            
            return {
                'symbol': symbol,
                'timestamp': orderbook['timestamp'],
                'bids': formatted_bids,
                'asks': formatted_asks
            }
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: Union[str, float],
        price: Optional[Union[str, float]] = None,
        time_in_force: str = "GoodTillCancel",
        reduce_only: bool = False,
        close_on_trigger: bool = False,
        position_idx: int = 0,
        take_profit: Optional[Union[str, float]] = None,
        stop_loss: Optional[Union[str, float]] = None,
        tp_trigger_by: str = "LastPrice",
        sl_trigger_by: str = "LastPrice",
        order_link_id: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Place an order.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            side: Order side ("Buy" or "Sell")
            order_type: Order type ("Market" or "Limit")
            qty: Order quantity
            price: Order price (required for Limit orders)
            time_in_force: Time in force ("GoodTillCancel", "ImmediateOrCancel", "FillOrKill", "PostOnly")
            reduce_only: Whether the order should only reduce position
            close_on_trigger: Whether to close position on trigger
            position_idx: Position index (0: one-way mode, 1: hedge mode buy, 2: hedge mode sell)
            take_profit: Take profit price
            stop_loss: Stop loss price
            tp_trigger_by: Take profit trigger type
            sl_trigger_by: Stop loss trigger type
            order_link_id: Custom order ID
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing order information
        """
        self._ensure_initialized()
        
        # Convert numeric values to strings as required by the API
        if isinstance(qty, str):
            qty = float(qty)
        if price is not None and isinstance(price, str):
            price = float(price)
        
        # Map Bybit order types to CCXT order types
        order_type_map = {
            "Market": "market",
            "Limit": "limit"
        }
        
        # Map Bybit sides to CCXT sides
        side_map = {
            "Buy": "buy",
            "Sell": "sell"
        }
        
        # Map time in force to CCXT time in force
        tif_map = {
            "GoodTillCancel": "GTC",
            "ImmediateOrCancel": "IOC",
            "FillOrKill": "FOK",
            "PostOnly": "PO"
        }
        
        ccxt_order_type = order_type_map.get(order_type, order_type.lower())
        ccxt_side = side_map.get(side, side.lower())
        ccxt_tif = tif_map.get(time_in_force, time_in_force)
        
        try:
            params = {
                'timeInForce': ccxt_tif,
                'reduceOnly': reduce_only
            }
            
            # Add client order ID if provided
            if order_link_id:
                params['clientOrderId'] = order_link_id
                
            # Add take profit and stop loss if provided
            if take_profit:
                params['takeProfitPrice'] = float(take_profit) if isinstance(take_profit, str) else take_profit
            if stop_loss:
                params['stopLossPrice'] = float(stop_loss) if isinstance(stop_loss, str) else stop_loss
                
            # Add any additional parameters
            params.update(kwargs)
            
            # Place the order
            order = self.client.create_order(
                symbol=symbol,
                type=ccxt_order_type,
                side=ccxt_side,
                amount=qty,
                price=price if ccxt_order_type == 'limit' else None,
                params=params
            )
            
            # Format the response to match Bybit's structure
            return {
                'orderId': order.get('id'),
                'symbol': order.get('symbol'),
                'side': side,
                'orderType': order_type,
                'price': str(order.get('price', '')),
                'qty': str(order.get('amount', '')),
                'timeInForce': time_in_force,
                'reduceOnly': reduce_only,
                'orderLinkId': order_link_id,
                'createTime': order.get('timestamp', int(time.time() * 1000))
            }
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def modify_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
        price: Optional[Union[str, float]] = None,
        qty: Optional[Union[str, float]] = None,
        take_profit: Optional[Union[str, float]] = None,
        stop_loss: Optional[Union[str, float]] = None,
        tp_trigger_by: Optional[str] = None,
        sl_trigger_by: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Modify an existing order.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            order_id: Order ID
            order_link_id: Custom order ID
            price: New order price
            qty: New order quantity
            take_profit: New take profit price
            stop_loss: New stop loss price
            tp_trigger_by: New take profit trigger type
            sl_trigger_by: New stop loss trigger type
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing order information
        """
        self._ensure_initialized()
        
        if not order_id and not order_link_id:
            raise ValueError("Either order_id or order_link_id must be provided")
        
        # Convert numeric values to strings as required by the API
        if price is not None and isinstance(price, str):
            price = float(price)
        if qty is not None and isinstance(qty, str):
            qty = float(qty)
        
        try:
            params = {}
            
            # Use client order ID if provided
            if order_link_id:
                params['clientOrderId'] = order_link_id
                
            # Add take profit and stop loss if provided
            if take_profit:
                params['takeProfitPrice'] = float(take_profit) if isinstance(take_profit, str) else take_profit
            if stop_loss:
                params['stopLossPrice'] = float(stop_loss) if isinstance(stop_loss, str) else stop_loss
                
            # Add any additional parameters
            params.update(kwargs)
            
            # Modify the order
            order = self.client.edit_order(
                id=order_id,
                symbol=symbol,
                price=price,
                amount=qty,
                params=params
            )
            
            # Format the response to match Bybit's structure
            return {
                'orderId': order.get('id'),
                'symbol': order.get('symbol'),
                'price': str(order.get('price', '')),
                'qty': str(order.get('amount', '')),
                'orderLinkId': order_link_id
            }
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def cancel_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None
    ) -> Dict:
        """
        Cancel an order.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            order_id: Order ID
            order_link_id: Custom order ID
            
        Returns:
            Dictionary containing cancellation information
        """
        self._ensure_initialized()
        
        if not order_id and not order_link_id:
            raise ValueError("Either order_id or order_link_id must be provided")
        
        try:
            params = {}
            
            # Use client order ID if provided
            if order_link_id:
                params['clientOrderId'] = order_link_id
                
            # Cancel the order
            order = self.client.cancel_order(
                id=order_id,
                symbol=symbol,
                params=params
            )
            
            # Format the response to match Bybit's structure
            return {
                'orderId': order.get('id'),
                'symbol': order.get('symbol'),
                'orderLinkId': order_link_id
            }
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict:
        """
        Cancel all orders.
        
        Args:
            symbol: Optional trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            Dictionary containing cancellation information
        """
        self._ensure_initialized()
        
        try:
            params = {}
            
            # Cancel all orders
            if symbol:
                result = self.client.cancel_all_orders(symbol=symbol, params=params)
            else:
                # CCXT might not support canceling all orders across all symbols
                # We'll need to fetch open orders first and cancel them one by one
                open_orders = self.client.fetch_open_orders()
                result = []
                
                for order in open_orders:
                    order_symbol = order['symbol']
                    order_id = order['id']
                    canceled = self.client.cancel_order(id=order_id, symbol=order_symbol)
                    result.append(canceled)
            
            # Format the response to match Bybit's structure
            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def close_position(self, symbol: str, position_idx: int = 0) -> Dict:
        """
        Close a position.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            position_idx: Position index (0: one-way mode, 1: hedge mode buy, 2: hedge mode sell)
            
        Returns:
            Dictionary containing position closure information
        """
        self._ensure_initialized()
        
        try:
            # Get current position to determine the side and quantity
            positions = self.get_positions(symbol=symbol)
            position_data = None
            
            # Find the relevant position
            for pos in positions.get("list", []):
                if pos.get("symbol") == symbol:
                    position_data = pos
                    break
                    
            if not position_data:
                logger.warning(f"No position found for {symbol}")
                return {"success": False, "message": "No position found"}
                
            # Determine the side for closing (opposite of position side)
            position_side = position_data.get("side")
            close_side = "Sell" if position_side == "Buy" else "Buy"
            
            # Get the position size
            position_size = abs(float(position_data.get("size", 0)))
            if position_size <= 0:
                logger.warning(f"Position size is zero for {symbol}")
                return {"success": False, "message": "Position size is zero"}
                
            # Place a market order to close the position
            return self.place_order(
                symbol=symbol,
                side=close_side,
                order_type="Market",
                qty=str(position_size),
                reduce_only=True
            )
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def get_order_history(
        self,
        symbol: Optional[str] = None,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
        limit: int = 50,
        **kwargs
    ) -> Dict:
        """
        Get order history.
        
        Args:
            symbol: Optional trading pair symbol (e.g., "BTC/USDT")
            order_id: Optional order ID
            order_link_id: Optional custom order ID
            limit: Number of orders to retrieve (max 50)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing order history
        """
        self._ensure_initialized()
        
        try:
            params = {
                'limit': limit
            }
            
            # Add client order ID if provided
            if order_link_id:
                params['clientOrderId'] = order_link_id
                
            # Add any additional parameters
            params.update(kwargs)
            
            # Fetch order history
            if order_id:
                # Fetch a specific order
                orders = [self.client.fetch_order(id=order_id, symbol=symbol)]
            else:
                # Fetch order history
                orders = self.client.fetch_orders(symbol=symbol, limit=limit, params=params)
            
            # Format the response to match Bybit's structure
            formatted_orders = []
            for order in orders:
                formatted_orders.append({
                    'orderId': order.get('id'),
                    'symbol': order.get('symbol'),
                    'side': 'Buy' if order.get('side') == 'buy' else 'Sell',
                    'orderType': order.get('type').capitalize(),
                    'price': str(order.get('price', '')),
                    'qty': str(order.get('amount', '')),
                    'orderStatus': order.get('status'),
                    'createTime': order.get('timestamp'),
                    'orderLinkId': order.get('clientOrderId')
                })
            
            return {'list': formatted_orders}
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def get_open_orders(
        self,
        symbol: Optional[str] = None,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
        limit: int = 50,
        **kwargs
    ) -> Dict:
        """
        Get open orders.
        
        Args:
            symbol: Optional trading pair symbol (e.g., "BTC/USDT")
            order_id: Optional order ID
            order_link_id: Optional custom order ID
            limit: Number of orders to retrieve (max 50)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing open orders
        """
        self._ensure_initialized()
        
        try:
            params = {
                'limit': limit
            }
            
            # Add client order ID if provided
            if order_link_id:
                params['clientOrderId'] = order_link_id
                
            # Add any additional parameters
            params.update(kwargs)
            
            # Fetch open orders
            if order_id:
                # Fetch a specific order
                orders = [self.client.fetch_order(id=order_id, symbol=symbol)]
                # Filter for open orders
                orders = [order for order in orders if order['status'] in ['open', 'new', 'partially_filled']]
            else:
                # Fetch open orders
                orders = self.client.fetch_open_orders(symbol=symbol, limit=limit, params=params)
            
            # Format the response to match Bybit's structure
            formatted_orders = []
            for order in orders:
                formatted_orders.append({
                    'orderId': order.get('id'),
                    'symbol': order.get('symbol'),
                    'side': 'Buy' if order.get('side') == 'buy' else 'Sell',
                    'orderType': order.get('type').capitalize(),
                    'price': str(order.get('price', '')),
                    'qty': str(order.get('amount', '')),
                    'orderStatus': order.get('status'),
                    'createTime': order.get('timestamp'),
                    'orderLinkId': order.get('clientOrderId')
                })
            
            return {'list': formatted_orders}
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def get_market_data(self, symbol: str) -> Dict:
        """
        Get market data for a specific trading pair.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            Dictionary containing market data
        """
        self._ensure_initialized()
        
        try:
            # Get ticker data
            ticker = self.client.fetch_ticker(symbol)
            
            # Get recent OHLCV data
            ohlcv_data = self.get_ohlcv(symbol=symbol, interval="1m", limit=1)
            ohlcv = ohlcv_data.get("list", [])
            
            # Format the response
            result = {
                "pair": symbol,
                "timestamp": ticker.get('timestamp', int(time.time() * 1000)),
                "price": ticker.get('last', 0),
                "volume_24h": ticker.get('quoteVolume', 0),
                "high_24h": ticker.get('high', 0),
                "low_24h": ticker.get('low', 0),
                "change_24h": ticker.get('percentage', 0) * 100  # Convert to percentage
            }
            
            # Add OHLCV data if available
            if ohlcv:
                candle = ohlcv[0]
                result.update({
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                })
                
            return result
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def get_account_balance(self) -> Dict:
        """
        Get account balance information.
        
        Returns:
            Dictionary containing balance information
        """
        self._ensure_initialized()
        
        try:
            # Get wallet balance
            balance = self.get_balances()
            
            # Get positions
            positions = self.get_positions()
            
            # Format the response
            total_equity = 0
            available_balance = 0
            
            # Extract balance information
            if 'total' in balance and 'USDT' in balance['total']:
                total_equity = balance['total']['USDT']
                available_balance = balance['free']['USDT']
            
            # Format positions
            formatted_positions = []
            if 'list' in positions:
                formatted_positions = positions['list']
            
            return {
                "total_equity": total_equity,
                "available_balance": available_balance,
                "positions": formatted_positions
            }
        except Exception as e:
            self._handle_ccxt_error(e)
    
    @handle_rate_limit
    def execute_trade(self, signal: Dict) -> Dict:
        """
        Execute a trade based on the provided signal.
        
        Args:
            signal: Dictionary containing trade signal information
            
        Returns:
            Dictionary containing trade execution information
        """
        self._ensure_initialized()
        
        try:
            # Extract signal parameters
            symbol = signal.get("symbol")
            side = signal.get("side")
            order_type = signal.get("order_type", "Market")
            qty = signal.get("qty")
            price = signal.get("price")
            
            if not symbol or not side or not qty:
                raise ValueError("Missing required signal parameters: symbol, side, qty")
            
            # Place the order
            order_response = self.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=qty,
                price=price,
                time_in_force=signal.get("time_in_force", "GoodTillCancel"),
                reduce_only=signal.get("reduce_only", False),
                take_profit=signal.get("take_profit"),
                stop_loss=signal.get("stop_loss")
            )
            
            # Format the response
            order_id = order_response.get("orderId", "unknown")
            
            return {
                "status": "success",
                "order_id": order_id,
                "details": {
                    "symbol": symbol,
                    "side": side,
                    "order_type": order_type,
                    "qty": qty,
                    "price": price,
                    "timestamp": int(time.time() * 1000)
                }
            }
        except Exception as e:
            self._handle_ccxt_error(e)
