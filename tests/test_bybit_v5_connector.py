"""
Tests for the Bybit V5 connector
"""
import unittest
from unittest.mock import patch, MagicMock
import pytest
import json
from app.connectors.bybit.v5_connector import BybitV5Connector

class TestBybitV5Connector(unittest.TestCase):
    """Test cases for the Bybit V5 connector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test_api_key"
        self.api_secret = "test_api_secret"
        self.connector = BybitV5Connector(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=True
        )
        # Mock the HTTP client
        self.mock_client = MagicMock()
        self.connector.client = self.mock_client
        self.connector.initialized = True
    
    def test_initialization(self):
        """Test connector initialization"""
        connector = BybitV5Connector(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=True
        )
        self.assertEqual(connector.api_key, self.api_key)
        self.assertEqual(connector.api_secret, self.api_secret)
        self.assertEqual(connector.testnet, True)
        self.assertFalse(connector.initialized)
    
    @patch('pybit.unified_trading.HTTP')
    async def test_initialize(self, mock_http):
        """Test initialize method"""
        mock_instance = MagicMock()
        mock_http.return_value = mock_instance
        
        connector = BybitV5Connector(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=True
        )
        
        await connector.initialize()
        
        mock_http.assert_called_once_with(
            testnet=True,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        self.assertTrue(connector.initialized)
        self.assertEqual(connector.client, mock_instance)
    
    def test_get_balances(self):
        """Test get_balances method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    {
                        "totalEquity": "1000",
                        "accountIMRate": "0.01",
                        "totalMarginBalance": "1000",
                        "totalInitialMargin": "10",
                        "accountType": "UNIFIED",
                        "totalAvailableBalance": "990",
                        "accountMMRate": "0",
                        "totalPerpUPL": "0",
                        "totalWalletBalance": "1000",
                        "accountLTV": "0",
                        "totalMaintenanceMargin": "0",
                        "coin": [
                            {
                                "availableToBorrow": "0",
                                "bonus": "0",
                                "accruedInterest": "0",
                                "availableToWithdraw": "990",
                                "totalOrderIM": "0",
                                "equity": "1000",
                                "totalPositionMM": "0",
                                "usdValue": "1000",
                                "unrealisedPnl": "0",
                                "collateralSwitch": True,
                                "borrowAmount": "0",
                                "totalPositionIM": "10",
                                "walletBalance": "1000",
                                "cumRealisedPnl": "0",
                                "locked": "0",
                                "marginCollateral": True,
                                "coin": "USDT"
                            }
                        ]
                    }
                ]
            }
        }
        self.mock_client.get_wallet_balance.return_value = mock_response
        
        # Call the method
        result = self.connector.get_balances()
        
        # Verify the result
        self.mock_client.get_wallet_balance.assert_called_once_with(accountType="UNIFIED")
        self.assertEqual(result, mock_response["result"])
    
    def test_get_positions(self):
        """Test get_positions method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "leverage": "10",
                        "avgPrice": "30000",
                        "liqPrice": "0",
                        "riskLimitValue": "2000000",
                        "takeProfit": "0",
                        "positionValue": "300",
                        "tpslMode": "Full",
                        "riskId": 1,
                        "trailingStop": "0",
                        "unrealisedPnl": "0",
                        "markPrice": "30000",
                        "cumRealisedPnl": "0",
                        "positionMM": "0.1",
                        "createdTime": "1672376000000",
                        "positionIdx": 0,
                        "positionIM": "10",
                        "updatedTime": "1672376000000",
                        "side": "Buy",
                        "bustPrice": "0",
                        "size": "0.01",
                        "positionStatus": "Normal",
                        "stopLoss": "0",
                        "adlRankIndicator": 0
                    }
                ]
            }
        }
        self.mock_client.get_positions.return_value = mock_response
        
        # Call the method
        result = self.connector.get_positions(symbol="BTCUSDT")
        
        # Verify the result
        self.mock_client.get_positions.assert_called_once_with(category="linear", symbol="BTCUSDT")
        self.assertEqual(result, mock_response["result"])
    
    def test_get_ohlcv(self):
        """Test get_ohlcv method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "symbol": "BTCUSDT",
                "category": "linear",
                "list": [
                    ["1672376000000", "30000", "31000", "29000", "30500", "100", "3050000"],
                    ["1672375900000", "29500", "30000", "29000", "30000", "150", "4500000"]
                ]
            }
        }
        self.mock_client.get_kline.return_value = mock_response
        
        # Call the method
        result = self.connector.get_ohlcv(symbol="BTCUSDT", interval="1", limit=2)
        
        # Verify the result
        self.mock_client.get_kline.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT",
            interval="1",
            limit=2
        )
        self.assertEqual(result, mock_response["result"])
    
    def test_get_orderbook(self):
        """Test get_orderbook method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "s": "BTCUSDT",
                "b": [
                    ["30000", "1"],
                    ["29999", "2"]
                ],
                "a": [
                    ["30001", "1"],
                    ["30002", "2"]
                ],
                "ts": 1672376000000,
                "u": 123456
            }
        }
        self.mock_client.get_orderbook.return_value = mock_response
        
        # Call the method
        result = self.connector.get_orderbook(symbol="BTCUSDT", limit=2)
        
        # Verify the result
        self.mock_client.get_orderbook.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT",
            limit=2
        )
        self.assertEqual(result, mock_response["result"])
    
    def test_place_order(self):
        """Test place_order method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "orderId": "1234567890",
                "orderLinkId": "",
                "symbol": "BTCUSDT",
                "side": "Buy",
                "orderType": "Market",
                "price": "0",
                "qty": "0.01",
                "timeInForce": "GoodTillCancel",
                "orderStatus": "Created",
                "cumExecQty": "0",
                "cumExecValue": "0",
                "cumExecFee": "0",
                "reduceOnly": False,
                "closeOnTrigger": False,
                "createdTime": "1672376000000",
                "updatedTime": "1672376000000"
            }
        }
        self.mock_client.place_order.return_value = mock_response
        
        # Call the method
        result = self.connector.place_order(
            symbol="BTCUSDT",
            side="Buy",
            order_type="Market",
            qty=0.01
        )
        
        # Verify the result
        self.mock_client.place_order.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT",
            side="Buy",
            orderType="Market",
            qty="0.01",
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False,
            positionIdx=0
        )
        self.assertEqual(result, mock_response["result"])
    
    def test_modify_order(self):
        """Test modify_order method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "orderId": "1234567890",
                "orderLinkId": ""
            }
        }
        self.mock_client.amend_order.return_value = mock_response
        
        # Call the method
        result = self.connector.modify_order(
            symbol="BTCUSDT",
            order_id="1234567890",
            price=31000,
            qty=0.02
        )
        
        # Verify the result
        self.mock_client.amend_order.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT",
            orderId="1234567890",
            price="31000",
            qty="0.02"
        )
        self.assertEqual(result, mock_response["result"])
    
    def test_cancel_order(self):
        """Test cancel_order method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "orderId": "1234567890",
                "orderLinkId": ""
            }
        }
        self.mock_client.cancel_order.return_value = mock_response
        
        # Call the method
        result = self.connector.cancel_order(
            symbol="BTCUSDT",
            order_id="1234567890"
        )
        
        # Verify the result
        self.mock_client.cancel_order.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT",
            orderId="1234567890"
        )
        self.assertEqual(result, mock_response["result"])
    
    def test_cancel_all_orders(self):
        """Test cancel_all_orders method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "success": "1"
            }
        }
        self.mock_client.cancel_all_orders.return_value = mock_response
        
        # Call the method
        result = self.connector.cancel_all_orders(symbol="BTCUSDT")
        
        # Verify the result
        self.mock_client.cancel_all_orders.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT"
        )
        self.assertEqual(result, mock_response["result"])
    
    def test_close_position(self):
        """Test close_position method"""
        # Mock get_positions response
        mock_positions_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "side": "Buy",
                        "size": "0.01",
                        "positionIdx": 0
                    }
                ]
            }
        }
        
        # Mock place_order response
        mock_order_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "orderId": "1234567890"
            }
        }
        
        self.mock_client.get_positions.return_value = mock_positions_response
        self.mock_client.place_order.return_value = mock_order_response
        
        # Call the method
        result = self.connector.close_position(symbol="BTCUSDT")
        
        # Verify the result
        self.mock_client.get_positions.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT"
        )
        self.mock_client.place_order.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT",
            side="Sell",
            orderType="Market",
            qty="0.01",
            reduceOnly=True,
            timeInForce="GoodTillCancel",
            closeOnTrigger=False,
            positionIdx=0
        )
        self.assertEqual(result, mock_order_response["result"])
    
    def test_get_order_history(self):
        """Test get_order_history method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    {
                        "orderId": "1234567890",
                        "orderLinkId": "",
                        "symbol": "BTCUSDT",
                        "side": "Buy",
                        "orderType": "Market",
                        "price": "0",
                        "qty": "0.01",
                        "timeInForce": "GoodTillCancel",
                        "orderStatus": "Filled",
                        "cumExecQty": "0.01",
                        "cumExecValue": "300",
                        "cumExecFee": "0.18",
                        "reduceOnly": False,
                        "closeOnTrigger": False,
                        "createdTime": "1672376000000",
                        "updatedTime": "1672376000000"
                    }
                ]
            }
        }
        self.mock_client.get_order_history.return_value = mock_response
        
        # Call the method
        result = self.connector.get_order_history(symbol="BTCUSDT", limit=10)
        
        # Verify the result
        self.mock_client.get_order_history.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT",
            limit=10
        )
        self.assertEqual(result, mock_response["result"])
    
    def test_get_open_orders(self):
        """Test get_open_orders method"""
        # Mock response
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    {
                        "orderId": "1234567890",
                        "orderLinkId": "",
                        "symbol": "BTCUSDT",
                        "side": "Buy",
                        "orderType": "Limit",
                        "price": "29000",
                        "qty": "0.01",
                        "timeInForce": "GoodTillCancel",
                        "orderStatus": "New",
                        "cumExecQty": "0",
                        "cumExecValue": "0",
                        "cumExecFee": "0",
                        "reduceOnly": False,
                        "closeOnTrigger": False,
                        "createdTime": "1672376000000",
                        "updatedTime": "1672376000000"
                    }
                ]
            }
        }
        self.mock_client.get_open_orders.return_value = mock_response
        
        # Call the method
        result = self.connector.get_open_orders(symbol="BTCUSDT", limit=10)
        
        # Verify the result
        self.mock_client.get_open_orders.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT",
            limit=10
        )
        self.assertEqual(result, mock_response["result"])
    
    def test_get_market_data(self):
        """Test get_market_data method"""
        # Mock ticker response
        mock_ticker_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "lastPrice": "30000",
                        "indexPrice": "30005",
                        "markPrice": "30010",
                        "prevPrice24h": "29000",
                        "price24hPcnt": "0.0345",
                        "highPrice24h": "31000",
                        "lowPrice24h": "29000",
                        "volume24h": "100",
                        "turnover24h": "3000000",
                        "openInterest": "50",
                        "fundingRate": "0.0001",
                        "nextFundingTime": "1672376000000"
                    }
                ]
            }
        }
        
        # Mock OHLCV response
        mock_ohlcv_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "symbol": "BTCUSDT",
                "category": "linear",
                "list": [
                    ["1672376000000", "30000", "30100", "29900", "30050", "10", "300500"]
                ]
            }
        }
        
        self.mock_client.get_tickers.return_value = mock_ticker_response
        
        # Mock the get_ohlcv method
        self.connector.get_ohlcv = MagicMock(return_value=mock_ohlcv_response["result"])
        
        # Call the method
        result = self.connector.get_market_data(symbol="BTCUSDT")
        
        # Verify the result
        self.mock_client.get_tickers.assert_called_once_with(
            category="linear",
            symbol="BTCUSDT"
        )
        self.connector.get_ohlcv.assert_called_once_with(
            symbol="BTCUSDT",
            interval="1",
            limit=1
        )
        
        # Check the result structure
        self.assertEqual(result["pair"], "BTCUSDT")
        self.assertEqual(result["price"], 30000.0)
        self.assertEqual(result["volume_24h"], 100.0)
        self.assertEqual(result["high_24h"], 31000.0)
        self.assertEqual(result["low_24h"], 29000.0)
        self.assertEqual(result["change_24h"], 3.45)  # 0.0345 * 100
        self.assertEqual(result["open"], 30000.0)
        self.assertEqual(result["high"], 30100.0)
        self.assertEqual(result["low"], 29900.0)
        self.assertEqual(result["close"], 30050.0)
        self.assertEqual(result["volume"], 10.0)
    
    def test_get_account_balance(self):
        """Test get_account_balance method"""
        # Mock balances response
        mock_balances_response = {
            "list": [
                {
                    "accountType": "UNIFIED",
                    "totalEquity": "1000",
                    "availableBalance": "990"
                }
            ]
        }
        
        # Mock positions response
        mock_positions_response = {
            "list": [
                {
                    "symbol": "BTCUSDT",
                    "side": "Buy",
                    "size": "0.01",
                    "entryPrice": "30000",
                    "markPrice": "30500",
                    "unrealisedPnl": "5",
                    "leverage": "10"
                }
            ]
        }
        
        # Mock the methods
        self.connector.get_balances = MagicMock(return_value=mock_balances_response)
        self.connector.get_positions = MagicMock(return_value=mock_positions_response)
        
        # Call the method
        result = self.connector.get_account_balance()
        
        # Verify the result
        self.connector.get_balances.assert_called_once()
        self.connector.get_positions.assert_called_once()
        
        # Check the result structure
        self.assertEqual(result["total_equity"], 1000.0)
        self.assertEqual(result["available_balance"], 990.0)
        self.assertEqual(len(result["positions"]), 1)
        self.assertEqual(result["positions"][0]["symbol"], "BTCUSDT")
        self.assertEqual(result["positions"][0]["side"], "Buy")
        self.assertEqual(result["positions"][0]["size"], 0.01)
        self.assertEqual(result["positions"][0]["entry_price"], 30000.0)
        self.assertEqual(result["positions"][0]["mark_price"], 30500.0)
        self.assertEqual(result["positions"][0]["unrealized_pnl"], 5.0)
        self.assertEqual(result["positions"][0]["leverage"], 10.0)
    
    def test_execute_trade(self):
        """Test execute_trade method"""
        # Mock place_order response
        mock_order_response = {
            "orderId": "1234567890"
        }
        
        # Mock the place_order method
        self.connector.place_order = MagicMock(return_value=mock_order_response)
        
        # Create a signal
        signal = {
            "symbol": "BTCUSDT",
            "side": "Buy",
            "order_type": "Market",
            "qty": 0.01,
            "price": None
        }
        
        # Call the method
        result = self.connector.execute_trade(signal)
        
        # Verify the result
        self.connector.place_order.assert_called_once_with(
            symbol="BTCUSDT",
            side="Buy",
            order_type="Market",
            qty=0.01,
            price=None,
            time_in_force="GoodTillCancel",
            reduce_only=False,
            take_profit=None,
            stop_loss=None
        )
        
        # Check the result structure
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["order_id"], "1234567890")
        self.assertEqual(result["details"]["symbol"], "BTCUSDT")
        self.assertEqual(result["details"]["side"], "Buy")
        self.assertEqual(result["details"]["order_type"], "Market")
        self.assertEqual(result["details"]["qty"], 0.01)
        self.assertEqual(result["details"]["price"], None)
    
    def test_handle_rate_limit(self):
        """Test rate limit handling"""
        # Create a mock function that raises a rate limit error
        mock_function = MagicMock(side_effect=[
            Exception("Rate limit exceeded"),
            {"retCode": 0, "result": "success"}
        ])
        
        # Apply the rate limit decorator
        decorated_function = self.connector._handle_rate_limit(mock_function)
        
        # Call the decorated function
        with patch('time.sleep') as mock_sleep:
            result = decorated_function()
            
            # Verify that sleep was called
            mock_sleep.assert_called_once_with(1)
            
            # Verify that the function was called twice
            self.assertEqual(mock_function.call_count, 2)
            
            # Verify the result
            self.assertEqual(result, {"retCode": 0, "result": "success"})

if __name__ == "__main__":
    unittest.main()
