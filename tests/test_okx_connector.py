"""
Tests for the OKX connector implementation.
"""
import pytest
import os
from unittest.mock import patch, MagicMock

from app.connectors.okx.connector import OKXConnector
from app.core.config import ExchangePriority

# Skip tests if API credentials are not available
pytestmark = pytest.mark.skipif(
    not os.getenv("OKX_API_KEY") or not os.getenv("OKX_API_SECRET") or not os.getenv("OKX_PASSPHRASE"),
    reason="OKX API credentials not available"
)

class TestOKXConnector:
    """Test suite for OKX connector"""
    
    @pytest.fixture
    def mock_ccxt(self):
        """Mock CCXT library"""
        with patch("app.connectors.okx.connector.ccxt") as mock_ccxt:
            # Mock OKX exchange
            mock_exchange = MagicMock()
            mock_ccxt.okx.return_value = mock_exchange
            
            # Mock fetch_time
            mock_exchange.fetch_time.return_value = 1619712000000
            
            # Mock fetch_balance
            mock_exchange.fetch_balance.return_value = {
                'info': {},
                'total': {'USDT': 1000.0, 'BTC': 0.1},
                'free': {'USDT': 900.0, 'BTC': 0.09},
                'used': {'USDT': 100.0, 'BTC': 0.01}
            }
            
            # Mock fetch_positions
            mock_exchange.fetch_positions.return_value = [
                {
                    'symbol': 'BTC/USDT',
                    'side': 'long',
                    'contracts': 0.01,
                    'entryPrice': 50000.0,
                    'markPrice': 51000.0,
                    'unrealizedPnl': 10.0,
                    'leverage': 10.0
                }
            ]
            
            # Mock fetch_ohlcv
            mock_exchange.fetch_ohlcv.return_value = [
                [1619712000000, 50000.0, 51000.0, 49000.0, 50500.0, 10.0],
                [1619712060000, 50500.0, 51500.0, 50000.0, 51000.0, 15.0]
            ]
            
            # Mock fetch_order_book
            mock_exchange.fetch_order_book.return_value = {
                'symbol': 'BTC/USDT',
                'timestamp': 1619712000000,
                'bids': [[50000.0, 1.0], [49900.0, 2.0]],
                'asks': [[50100.0, 1.0], [50200.0, 2.0]]
            }
            
            # Mock create_order
            mock_exchange.create_order.return_value = {
                'id': '12345',
                'symbol': 'BTC/USDT',
                'price': 50000.0,
                'amount': 0.01,
                'timestamp': 1619712000000,
                'side': 'buy',
                'type': 'limit'
            }
            
            # Mock fetch_ticker
            mock_exchange.fetch_ticker.return_value = {
                'symbol': 'BTC/USDT',
                'timestamp': 1619712000000,
                'last': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'quoteVolume': 1000000.0,
                'percentage': 0.05
            }
            
            yield mock_ccxt
    
    @pytest.fixture
    def connector(self, mock_ccxt):
        """Create OKX connector instance with mocked CCXT"""
        connector = OKXConnector(
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase",
            testnet=True,
            priority=ExchangePriority.FAILOVER
        )
        connector.initialize()
        return connector
    
    def test_initialization(self, connector, mock_ccxt):
        """Test connector initialization"""
        assert connector.initialized is True
        assert connector.api_key == "test_key"
        assert connector.api_secret == "test_secret"
        assert connector.passphrase == "test_passphrase"
        assert connector.testnet is True
        assert connector.priority == ExchangePriority.FAILOVER
        
        # Verify CCXT client was initialized correctly
        mock_ccxt.okx.assert_called_once()
        connector.client.set_sandbox_mode.assert_called_once_with(True)
    
    def test_get_balances(self, connector):
        """Test get_balances method"""
        balances = connector.get_balances()
        assert balances['total']['USDT'] == 1000.0
        assert balances['free']['BTC'] == 0.09
        
        # Test with specific coin
        usdt_balance = connector.get_balances(coin='USDT')
        assert usdt_balance['total']['USDT'] == 1000.0
    
    def test_get_positions(self, connector):
        """Test get_positions method"""
        positions = connector.get_positions()
        assert len(positions['list']) == 1
        assert positions['list'][0]['symbol'] == 'BTC/USDT'
        assert positions['list'][0]['side'] == 'Buy'
        assert positions['list'][0]['size'] == 0.01
    
    def test_get_ohlcv(self, connector):
        """Test get_ohlcv method"""
        ohlcv = connector.get_ohlcv(symbol='BTC/USDT', interval='1m', limit=2)
        assert len(ohlcv['list']) == 2
        assert float(ohlcv['list'][0][4]) == 50500.0  # Close price
    
    def test_get_orderbook(self, connector):
        """Test get_orderbook method"""
        orderbook = connector.get_orderbook(symbol='BTC/USDT', limit=2)
        assert orderbook['symbol'] == 'BTC/USDT'
        assert len(orderbook['bids']) == 2
        assert len(orderbook['asks']) == 2
    
    def test_place_order(self, connector):
        """Test place_order method"""
        order = connector.place_order(
            symbol='BTC/USDT',
            side='Buy',
            order_type='Limit',
            qty=0.01,
            price=50000.0
        )
        assert order['orderId'] == '12345'
        assert order['symbol'] == 'BTC/USDT'
        assert order['side'] == 'Buy'
    
    def test_get_market_data(self, connector):
        """Test get_market_data method"""
        market_data = connector.get_market_data(symbol='BTC/USDT')
        assert market_data['pair'] == 'BTC/USDT'
        assert market_data['price'] == 50000.0
        assert market_data['change_24h'] == 5.0  # 0.05 * 100
    
    def test_get_account_balance(self, connector):
        """Test get_account_balance method"""
        account_balance = connector.get_account_balance()
        assert account_balance['total_equity'] == 1000.0
        assert account_balance['available_balance'] == 900.0
        assert len(account_balance['positions']) == 1
    
    def test_execute_trade(self, connector):
        """Test execute_trade method"""
        signal = {
            'symbol': 'BTC/USDT',
            'side': 'Buy',
            'order_type': 'Market',
            'qty': 0.01
        }
        trade_result = connector.execute_trade(signal)
        assert trade_result['status'] == 'success'
        assert trade_result['order_id'] == '12345'
        assert trade_result['details']['symbol'] == 'BTC/USDT'
