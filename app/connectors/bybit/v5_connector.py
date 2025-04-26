"""
Bybit V5 API connector for the DeepAgent Kraken trading bot.
"""
import logging
import time
import hmac
import hashlib
import json
import requests
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode

from app.connectors import ExchangeConnector

logger = logging.getLogger(__name__)

class BybitV5Connector(ExchangeConnector):
    """
    Bybit V5 API connector.
    
    This connector implements the ExchangeConnector interface for the Bybit V5 API.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False, 
                 base_url: Optional[str] = None, ws_url: Optional[str] = None):
        """
        Initialize the Bybit V5 connector.
        
        Args:
            api_key: API key
            api_secret: API secret
            testnet: Whether to use testnet
            base_url: Base URL for REST API (overrides testnet flag if provided)
            ws_url: WebSocket URL (for future WebSocket implementation)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        # Set base URL based on provided URL or testnet flag
        if base_url:
            self.base_url = base_url
        else:
            # Fallback to default URLs based on testnet flag
            if testnet:
                self.base_url = "https://api-testnet.bybit.com"
            else:
                self.base_url = "https://api.bybit.com"
        
        # Store WebSocket URL for future use
        if ws_url:
            self.ws_url = ws_url
        else:
            # Fallback to default WebSocket URLs based on testnet flag
            if testnet:
                self.ws_url = "wss://stream-testnet.bybit.com"
            else:
                self.ws_url = "wss://stream.bybit.com"
        
        # Set up session
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-BAPI-API-KEY": self.api_key
        })
        
        logger.info(f"Initialized BybitV5Connector (testnet: {testnet}, base_url: {self.base_url})")
    
    def _generate_signature(self, params: Dict, timestamp: int) -> str:
        """
        Generate signature for API request.
        
        Args:
            params: Request parameters
            timestamp: Current timestamp in milliseconds
            
        Returns:
            HMAC signature
        """
        param_str = str(timestamp) + self.api_key + "5000" + urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
    
    def _send_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     signed: bool = False) -> Dict:
        """
        Send request to Bybit API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether the request needs to be signed
            
        Returns:
            API response
        """
        url = f"{self.base_url}{endpoint}"
        
        # Prepare parameters
        params = params or {}
        
        # Add signature for authenticated requests
        if signed:
            timestamp = int(time.time() * 1000)
            signature = self._generate_signature(params, timestamp)
            
            self.session.headers.update({
                "X-BAPI-SIGN": signature,
                "X-BAPI-SIGN-TYPE": "2",
                "X-BAPI-TIMESTAMP": str(timestamp),
                "X-BAPI-RECV-WINDOW": "5000"
            })
        
        # Send request
        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=params)
            elif method == "DELETE":
                response = self.session.delete(url, json=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check for errors
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            if data["retCode"] != 0:
                logger.error(f"API error: {data['retMsg']}")
                raise Exception(f"API error: {data['retMsg']}")
            
            return data["result"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise
    
    def get_klines(self, symbol: str, interval: str, limit: int = 200) -> List[Dict]:
        """
        Get candlestick data from the exchange.
        
        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candlesticks to retrieve
            
        Returns:
            List of candlestick data
        """
        # Map interval to Bybit format if needed
        interval_map = {
            "1m": "1",
            "3m": "3",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "2h": "120",
            "4h": "240",
            "6h": "360",
            "12h": "720",
            "1d": "D",
            "1w": "W",
            "1M": "M"
        }
        
        bybit_interval = interval_map.get(interval, interval)
        
        # Prepare parameters
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": bybit_interval,
            "limit": min(limit, 1000)  # Bybit has a max limit of 1000
        }
        
        # Send request
        response = self._send_request("GET", "/v5/market/kline", params)
        
        # Process response
        candles = []
        for item in response["list"]:
            candle = {
                "timestamp": int(item[0]),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5])
            }
            candles.append(candle)
        
        return candles
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        Get ticker information for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Ticker information
        """
        # Prepare parameters
        params = {
            "category": "linear",
            "symbol": symbol
        }
        
        # Send request
        response = self._send_request("GET", "/v5/market/tickers", params)
        
        # Process response
        if "list" in response and len(response["list"]) > 0:
            ticker = response["list"][0]
            return {
                "symbol": ticker["symbol"],
                "last": ticker["lastPrice"],
                "bid": ticker["bid1Price"],
                "ask": ticker["ask1Price"],
                "high": ticker["highPrice24h"],
                "low": ticker["lowPrice24h"],
                "volume": ticker["volume24h"],
                "timestamp": int(time.time() * 1000)
            }
        else:
            raise Exception(f"No ticker data found for {symbol}")
    
    def create_order(self, **kwargs) -> Dict:
        """
        Create an order on the exchange.
        
        Args:
            **kwargs: Order parameters
                - symbol: Trading pair symbol
                - side: Order side (buy/sell)
                - order_type: Order type (market, limit, etc.)
                - quantity: Order quantity
                - price: Order price (required for limit orders)
                - stop_loss: Stop loss price
                - take_profit: Take profit price
                - position_side: Position side (long/short) for hedge mode
                - reduce_only: Whether the order is reduce-only
                - time_in_force: Time in force (GTC, IOC, FOK)
                - close_on_trigger: Whether to close position on trigger
            
        Returns:
            Order information
        """
        # Map parameters to Bybit format
        order_type_map = {
            "market": "Market",
            "limit": "Limit",
            "stop": "Stop",
            "stop_market": "StopMarket",
            "take_profit": "TakeProfit",
            "take_profit_market": "TakeProfitMarket"
        }
        
        side_map = {
            "buy": "Buy",
            "sell": "Sell"
        }
        
        # Prepare parameters
        params = {
            "category": "linear",
            "symbol": kwargs["symbol"],
            "side": side_map.get(kwargs["side"].lower(), kwargs["side"]),
            "orderType": order_type_map.get(kwargs["order_type"].lower(), kwargs["order_type"]),
            "qty": str(kwargs["quantity"])
        }
        
        # Add optional parameters
        if "price" in kwargs and kwargs["price"] is not None:
            params["price"] = str(kwargs["price"])
        
        if "stop_loss" in kwargs and kwargs["stop_loss"] is not None:
            params["stopLoss"] = str(kwargs["stop_loss"])
        
        if "take_profit" in kwargs and kwargs["take_profit"] is not None:
            params["takeProfit"] = str(kwargs["take_profit"])
        
        if "position_side" in kwargs and kwargs["position_side"] is not None:
            params["positionIdx"] = "1" if kwargs["position_side"].lower() == "long" else "2"
        
        if "reduce_only" in kwargs:
            params["reduceOnly"] = kwargs["reduce_only"]
        
        if "time_in_force" in kwargs:
            params["timeInForce"] = kwargs["time_in_force"]
        else:
            params["timeInForce"] = "GTC"  # Default to Good Till Cancel
        
        if "close_on_trigger" in kwargs:
            params["closeOnTrigger"] = kwargs["close_on_trigger"]
        
        # Send request
        response = self._send_request("POST", "/v5/order/create", params, signed=True)
        
        return response
    
    def update_order(self, order_id: str, symbol: str, **kwargs) -> Dict:
        """
        Update an existing order on the exchange.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            **kwargs: Parameters to update
                - price: New price
                - quantity: New quantity
                - stop_loss: New stop loss price
                - take_profit: New take profit price
            
        Returns:
            Updated order information
        """
        # Prepare parameters
        params = {
            "category": "linear",
            "symbol": symbol,
            "orderId": order_id
        }
        
        # Add parameters to update
        if "price" in kwargs and kwargs["price"] is not None:
            params["price"] = str(kwargs["price"])
        
        if "quantity" in kwargs and kwargs["quantity"] is not None:
            params["qty"] = str(kwargs["quantity"])
        
        if "stop_loss" in kwargs and kwargs["stop_loss"] is not None:
            params["stopLoss"] = str(kwargs["stop_loss"])
        
        if "take_profit" in kwargs and kwargs["take_profit"] is not None:
            params["takeProfit"] = str(kwargs["take_profit"])
        
        # Send request
        response = self._send_request("POST", "/v5/order/amend", params, signed=True)
        
        return response
    
    def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """
        Cancel an order on the exchange.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            Cancellation confirmation
        """
        # Prepare parameters
        params = {
            "category": "linear",
            "symbol": symbol,
            "orderId": order_id
        }
        
        # Send request
        response = self._send_request("POST", "/v5/order/cancel", params, signed=True)
        
        return response
    
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        Get information about an order.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            Order information
        """
        # Prepare parameters
        params = {
            "category": "linear",
            "symbol": symbol,
            "orderId": order_id
        }
        
        # Send request
        response = self._send_request("GET", "/v5/order/realtime", params, signed=True)
        
        # Process response
        if "list" in response and len(response["list"]) > 0:
            return response["list"][0]
        else:
            raise Exception(f"Order {order_id} not found")
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders.
        
        Args:
            symbol: Trading pair symbol (optional)
            
        Returns:
            List of open orders
        """
        # Prepare parameters
        params = {
            "category": "linear"
        }
        
        if symbol:
            params["symbol"] = symbol
        
        # Send request
        response = self._send_request("GET", "/v5/order/realtime", params, signed=True)
        
        # Process response
        return response.get("list", [])
    
    def get_position(self, symbol: str) -> Dict:
        """
        Get position information for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Position information
        """
        # Prepare parameters
        params = {
            "category": "linear",
            "symbol": symbol
        }
        
        # Send request
        response = self._send_request("GET", "/v5/position/list", params, signed=True)
        
        # Process response
        if "list" in response and len(response["list"]) > 0:
            return response["list"][0]
        else:
            # Return empty position
            return {
                "symbol": symbol,
                "side": "None",
                "size": "0",
                "entryPrice": "0",
                "leverage": "0",
                "positionValue": "0",
                "unrealisedPnl": "0"
            }
    
    def get_account_info(self) -> Dict:
        """
        Get account information from the exchange.
        
        Returns:
            Account information
        """
        # Prepare parameters
        params = {
            "accountType": "CONTRACT"
        }
        
        # Send request
        response = self._send_request("GET", "/v5/account/wallet-balance", params, signed=True)
        
        # Process response
        if "list" in response and len(response["list"]) > 0:
            return response["list"][0]
        else:
            raise Exception("Failed to get account information")
