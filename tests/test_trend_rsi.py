"""
Tests for the trend-following strategy with RSI counter.
"""
import unittest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.strategies.indicators import sma, rsi, atr, calculate_all_indicators
from app.strategies.trend_rsi import TrendRSIStrategy, SignalType


class TestIndicators(unittest.TestCase):
    """Test cases for technical indicators."""
    
    def setUp(self):
        """Set up test data."""
        # Create sample price data
        np.random.seed(42)  # For reproducibility
        
        # Create a price series with a clear trend
        n = 250  # Number of data points
        
        # Create price series with uptrend followed by downtrend
        uptrend = np.linspace(100, 200, n // 2)
        downtrend = np.linspace(200, 100, n // 2)
        prices = np.concatenate([uptrend, downtrend])
        
        # Add some noise
        noise = np.random.normal(0, 5, n)
        prices = prices + noise
        
        # Create DataFrame
        dates = pd.date_range(start='2023-01-01', periods=n, freq='1h')
        self.df = pd.DataFrame({
            'open': prices - 1,
            'high': prices + 2,
            'low': prices - 2,
            'close': prices,
            'volume': np.random.randint(100, 1000, n)
        }, index=dates)
    
    def test_sma(self):
        """Test SMA calculation."""
        # Calculate SMA-50
        sma_value, sma_series = sma(self.df['close'], 50)
        
        # Check that the result is not NaN
        self.assertFalse(np.isnan(sma_value))
        
        # Check that the series has the correct length
        self.assertEqual(len(sma_series), len(self.df))
        
        # Check that the first 49 values are NaN
        self.assertTrue(np.isnan(sma_series.iloc[0]))
        self.assertTrue(np.isnan(sma_series.iloc[48]))
        
        # Check that the 50th value is not NaN
        self.assertFalse(np.isnan(sma_series.iloc[49]))
        
        # Check that the SMA is the average of the last 50 prices
        expected_sma = self.df['close'].iloc[-50:].mean()
        self.assertAlmostEqual(sma_value, expected_sma, places=6)
    
    def test_rsi(self):
        """Test RSI calculation."""
        # Calculate RSI-14
        rsi_value, rsi_series = rsi(self.df['close'], 14)
        
        # Check that the result is not NaN
        self.assertFalse(np.isnan(rsi_value))
        
        # Check that the series has the correct length
        self.assertEqual(len(rsi_series), len(self.df))
        
        # Check that RSI is between 0 and 100
        self.assertTrue(0 <= rsi_value <= 100)
        
        # Check that all non-NaN values in the series are between 0 and 100
        non_nan_values = rsi_series.dropna()
        self.assertTrue(all(0 <= x <= 100 for x in non_nan_values))
    
    def test_atr(self):
        """Test ATR calculation."""
        # Calculate ATR-14
        atr_value, atr_series = atr(self.df, 14)
        
        # Check that the result is not NaN
        self.assertFalse(np.isnan(atr_value))
        
        # Check that the series has the correct length
        self.assertEqual(len(atr_series), len(self.df))
        
        # Check that ATR is positive
        self.assertTrue(atr_value > 0)
        
        # Check that all non-NaN values in the series are positive
        non_nan_values = atr_series.dropna()
        self.assertTrue(all(x > 0 for x in non_nan_values))


class TestTrendRSIStrategy(unittest.TestCase):
    """Test cases for the trend-following strategy with RSI counter."""
    
    def setUp(self):
        """Set up test data and mocks."""
        # Create sample price data
        np.random.seed(42)  # For reproducibility
        
        # Create a price series with a clear trend
        n = 250  # Number of data points
        
        # Create price series with uptrend followed by downtrend
        uptrend = np.linspace(100, 200, n // 2)
        downtrend = np.linspace(200, 100, n // 2)
        prices = np.concatenate([uptrend, downtrend])
        
        # Add some noise
        noise = np.random.normal(0, 5, n)
        prices = prices + noise
        
        # Create DataFrame
        dates = pd.date_range(start='2023-01-01', periods=n, freq='1h')
        self.df = pd.DataFrame({
            'open': prices - 1,
            'high': prices + 2,
            'low': prices - 2,
            'close': prices,
            'volume': np.random.randint(100, 1000, n)
        }, index=dates)
        
        # Create mock order router
        self.order_router = MagicMock()
        self.order_router.get_klines.return_value = [
            {
                'timestamp': int(date.timestamp() * 1000),
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            }
            for date, row in self.df.iterrows()
        ]
        
        # Create mock exchange
        self.exchange = MagicMock()
        self.exchange.get_ticker.return_value = {'last': 150.0}
        self.order_router.current_exchange = self.exchange
        
        # Create strategy config
        self.config = {
            'symbol': 'BTCUSDT',
            'interval': '1h',
            'sma_fast_period': 50,
            'sma_slow_period': 200,
            'rsi_period': 14,
            'rsi_overbought': 65,
            'rsi_oversold': 35,
            'atr_period': 14,
            'risk_per_trade': 0.01,
            'atr_multiplier': 1.5,
            'trailing_stop_trigger': 1.0,
            'trailing_stop_step': 0.5
        }
        
        # Create strategy instance
        self.strategy = TrendRSIStrategy(self.order_router, self.config)
    
    def test_fetch_candles(self):
        """Test fetching candles."""
        # Call fetch_candles
        df = self.strategy.fetch_candles()
        
        # Check that the order router's get_klines method was called
        self.order_router.get_klines.assert_called_once_with(
            symbol='BTCUSDT',
            interval='1h',
            limit=250
        )
        
        # Check that the DataFrame has the correct shape
        self.assertEqual(df.shape, (250, 5))
        
        # Check that the DataFrame has the correct columns
        self.assertTrue(all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']))
    
    def test_compute_indicators(self):
        """Test computing indicators."""
        # Call compute_indicators
        indicators = self.strategy.compute_indicators(self.df)
        
        # Check that all indicators are present
        self.assertTrue(all(key in indicators for key in ['sma_fast', 'sma_slow', 'rsi', 'atr']))
        
        # Check that each indicator has a value and series
        for key in ['sma_fast', 'sma_slow', 'rsi', 'atr']:
            self.assertTrue('value' in indicators[key])
            self.assertTrue('series' in indicators[key])
            
            # Check that the value is not NaN
            self.assertFalse(np.isnan(indicators[key]['value']))
            
            # Check that the series has the correct length
            self.assertEqual(len(indicators[key]['series']), len(self.df))
    
    def test_generate_signal_long(self):
        """Test generating LONG signal."""
        # Create indicators with SMA-50 > SMA-200 and RSI < 65
        indicators = {
            'sma_fast': {'value': 150.0, 'series': pd.Series()},
            'sma_slow': {'value': 140.0, 'series': pd.Series()},
            'rsi': {'value': 60.0, 'series': pd.Series()},
            'atr': {'value': 5.0, 'series': pd.Series()}
        }
        
        # Call generate_signal
        signal = self.strategy.generate_signal(indicators)
        
        # Check that the signal is LONG
        self.assertEqual(signal, SignalType.LONG)
    
    def test_generate_signal_short(self):
        """Test generating SHORT signal."""
        # Create indicators with SMA-50 < SMA-200 and RSI > 35
        indicators = {
            'sma_fast': {'value': 140.0, 'series': pd.Series()},
            'sma_slow': {'value': 150.0, 'series': pd.Series()},
            'rsi': {'value': 40.0, 'series': pd.Series()},
            'atr': {'value': 5.0, 'series': pd.Series()}
        }
        
        # Call generate_signal
        signal = self.strategy.generate_signal(indicators)
        
        # Check that the signal is SHORT
        self.assertEqual(signal, SignalType.SHORT)
    
    def test_generate_signal_flat_high_rsi(self):
        """Test generating FLAT signal due to high RSI."""
        # Create indicators with SMA-50 > SMA-200 but RSI > 65
        indicators = {
            'sma_fast': {'value': 150.0, 'series': pd.Series()},
            'sma_slow': {'value': 140.0, 'series': pd.Series()},
            'rsi': {'value': 70.0, 'series': pd.Series()},
            'atr': {'value': 5.0, 'series': pd.Series()}
        }
        
        # Call generate_signal
        signal = self.strategy.generate_signal(indicators)
        
        # Check that the signal is FLAT
        self.assertEqual(signal, SignalType.FLAT)
    
    def test_generate_signal_flat_low_rsi(self):
        """Test generating FLAT signal due to low RSI."""
        # Create indicators with SMA-50 < SMA-200 but RSI < 35
        indicators = {
            'sma_fast': {'value': 140.0, 'series': pd.Series()},
            'sma_slow': {'value': 150.0, 'series': pd.Series()},
            'rsi': {'value': 30.0, 'series': pd.Series()},
            'atr': {'value': 5.0, 'series': pd.Series()}
        }
        
        # Call generate_signal
        signal = self.strategy.generate_signal(indicators)
        
        # Check that the signal is FLAT
        self.assertEqual(signal, SignalType.FLAT)
    
    def test_calculate_position_size(self):
        """Test calculating position size."""
        # Set up mock account info
        self.order_router.get_account_info.return_value = {'equity': 10000.0}
        
        # Call calculate_position_size
        position_size = self.strategy.calculate_position_size(10000.0, 5.0)
        
        # Expected position size = equity * risk_per_trade / (ATR * atr_multiplier)
        # = 10000 * 0.01 / (5 * 1.5) = 100 / 7.5 = 13.33
        expected_position_size = 10000.0 * 0.01 / (5.0 * 1.5)
        
        # Convert to contract size
        expected_contract_size = expected_position_size / 150.0
        
        # Check that the position size is correct
        self.assertAlmostEqual(position_size, expected_contract_size, places=6)
    
    def test_calculate_stop_loss_long(self):
        """Test calculating stop loss for LONG position."""
        # Call calculate_stop_loss
        stop_loss = self.strategy.calculate_stop_loss(150.0, 5.0, SignalType.LONG)
        
        # Expected stop loss = entry_price - (ATR * atr_multiplier)
        # = 150 - (5 * 1.5) = 150 - 7.5 = 142.5
        expected_stop_loss = 150.0 - (5.0 * 1.5)
        
        # Check that the stop loss is correct
        self.assertAlmostEqual(stop_loss, expected_stop_loss, places=6)
    
    def test_calculate_stop_loss_short(self):
        """Test calculating stop loss for SHORT position."""
        # Call calculate_stop_loss
        stop_loss = self.strategy.calculate_stop_loss(150.0, 5.0, SignalType.SHORT)
        
        # Expected stop loss = entry_price + (ATR * atr_multiplier)
        # = 150 + (5 * 1.5) = 150 + 7.5 = 157.5
        expected_stop_loss = 150.0 + (5.0 * 1.5)
        
        # Check that the stop loss is correct
        self.assertAlmostEqual(stop_loss, expected_stop_loss, places=6)
    
    def test_calculate_trailing_stop_long(self):
        """Test calculating trailing stop for LONG position."""
        # Set up test case
        entry_price = 150.0
        current_price = 160.0  # +10 points, which is +2 ATR
        atr = 5.0
        
        # Call calculate_trailing_stop
        trailing_stop = self.strategy.calculate_trailing_stop(
            entry_price, current_price, atr, SignalType.LONG
        )
        
        # Expected trailing stop = entry_price + (steps_beyond_trigger * trailing_stop_step * atr)
        # Profit in ATR = (160 - 150) / 5 = 2 ATR
        # Steps beyond trigger = (2 - 1) // 0.5 = 2 steps
        # Trailing stop = 150 + (2 * 0.5 * 5) = 150 + 5 = 155
        expected_trailing_stop = 150.0 + (2 * 0.5 * 5.0)
        
        # Check that the trailing stop is correct
        self.assertAlmostEqual(trailing_stop, expected_trailing_stop, places=6)
    
    def test_calculate_trailing_stop_short(self):
        """Test calculating trailing stop for SHORT position."""
        # Set up test case
        entry_price = 150.0
        current_price = 140.0  # -10 points, which is -2 ATR
        atr = 5.0
        
        # Call calculate_trailing_stop
        trailing_stop = self.strategy.calculate_trailing_stop(
            entry_price, current_price, atr, SignalType.SHORT
        )
        
        # Expected trailing stop = entry_price - (steps_beyond_trigger * trailing_stop_step * atr)
        # Profit in ATR = (150 - 140) / 5 = 2 ATR
        # Steps beyond trigger = (2 - 1) // 0.5 = 2 steps
        # Trailing stop = 150 - (2 * 0.5 * 5) = 150 - 5 = 145
        expected_trailing_stop = 150.0 - (2 * 0.5 * 5.0)
        
        # Check that the trailing stop is correct
        self.assertAlmostEqual(trailing_stop, expected_trailing_stop, places=6)
    
    def test_calculate_trailing_stop_not_triggered(self):
        """Test calculating trailing stop when not triggered."""
        # Set up test case
        entry_price = 150.0
        current_price = 152.0  # +2 points, which is +0.4 ATR (less than trigger)
        atr = 5.0
        
        # Call calculate_trailing_stop
        trailing_stop = self.strategy.calculate_trailing_stop(
            entry_price, current_price, atr, SignalType.LONG
        )
        
        # Expected trailing stop = None (not triggered)
        self.assertIsNone(trailing_stop)
    
    def test_run(self):
        """Test running the strategy."""
        # Call run
        result = self.strategy.run()
        
        # Check that the result contains the expected keys
        self.assertTrue(all(key in result for key in [
            'timestamp', 'symbol', 'signal', 'indicators',
            'current_position', 'entry_price', 'stop_loss_price', 'trailing_stop_price'
        ]))
        
        # Check that the indicators contain the expected keys
        self.assertTrue(all(key in result['indicators'] for key in [
            'sma_fast', 'sma_slow', 'rsi', 'atr'
        ]))


if __name__ == '__main__':
    unittest.main()
