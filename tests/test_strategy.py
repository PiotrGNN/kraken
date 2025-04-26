"""
Unit tests for the trading strategy.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.strategies.indicators import TechnicalIndicators
from app.strategies.trend_rsi_strategy import TrendRSIStrategy
from app.risk.atr_risk import ATRRiskManager


class TestTechnicalIndicators(unittest.TestCase):
    """
    Test case for technical indicators.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        # Create sample price data
        dates = [datetime.now() - timedelta(days=i) for i in range(250, 0, -1)]
        
        # Create a dataframe with sample price data
        self.data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.normal(100, 5, 250),
            'high': np.random.normal(105, 5, 250),
            'low': np.random.normal(95, 5, 250),
            'close': np.random.normal(100, 5, 250),
            'volume': np.random.normal(1000, 200, 250)
        })
        
        # Ensure high is always higher than low
        self.data['high'] = self.data[['open', 'close']].max(axis=1) + abs(np.random.normal(2, 1, 250))
        self.data['low'] = self.data[['open', 'close']].min(axis=1) - abs(np.random.normal(2, 1, 250))
        
        # Create indicators instance
        self.indicators = TechnicalIndicators()
    
    def test_sma_calculation(self):
        """
        Test SMA calculation.
        """
        # Calculate SMA-50
        sma_50 = self.indicators.sma(self.data, period=50)
        
        # Check that SMA has the correct length
        self.assertEqual(len(sma_50), len(self.data))
        
        # Check that the first 49 values are NaN
        self.assertTrue(sma_50.iloc[:49].isna().all())
        
        # Check that the rest are not NaN
        self.assertTrue(sma_50.iloc[49:].notna().all())
        
        # Manually calculate SMA for a specific point and compare
        manual_sma = self.data['close'].iloc[100:150].mean()
        self.assertAlmostEqual(sma_50.iloc[149], manual_sma, places=10)
    
    def test_rsi_calculation(self):
        """
        Test RSI calculation.
        """
        # Calculate RSI-14
        rsi_14 = self.indicators.rsi(self.data, period=14)
        
        # Check that RSI has the correct length
        self.assertEqual(len(rsi_14), len(self.data))
        
        # Check that the first 14 values are NaN
        self.assertTrue(rsi_14.iloc[:14].isna().all())
        
        # Check that the rest are not NaN
        self.assertTrue(rsi_14.iloc[14:].notna().all())
        
        # Check that RSI values are between 0 and 100
        self.assertTrue((rsi_14.iloc[14:] >= 0).all() and (rsi_14.iloc[14:] <= 100).all())
    
    def test_atr_calculation(self):
        """
        Test ATR calculation.
        """
        # Calculate ATR-14
        atr_14 = self.indicators.atr(self.data, period=14)
        
        # Check that ATR has the correct length
        self.assertEqual(len(atr_14), len(self.data))
        
        # Check that the first 14 values are NaN
        self.assertTrue(atr_14.iloc[:14].isna().all())
        
        # Check that the rest are not NaN
        self.assertTrue(atr_14.iloc[14:].notna().all())
        
        # Check that ATR values are positive
        self.assertTrue((atr_14.iloc[14:] > 0).all())
    
    def test_calculate_all(self):
        """
        Test calculate_all method.
        """
        # Calculate all indicators
        result = self.indicators.calculate_all(self.data)
        
        # Check that the result has all the expected columns
        expected_columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp', 
                           'sma_50', 'sma_200', 'rsi_14', 'atr_14']
        for col in expected_columns:
            self.assertIn(col, result.columns)
        
        # Check that the result has the same length as the input
        self.assertEqual(len(result), len(self.data))


class TestTrendRSIStrategy(unittest.TestCase):
    """
    Test case for the trend-follower strategy with RSI counter.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        # Create sample price data for a bullish trend
        dates = [datetime.now() - timedelta(days=i) for i in range(250, 0, -1)]
        
        # Create a dataframe with sample price data for a bullish trend
        self.bullish_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.linspace(90, 110, 250) + np.random.normal(0, 1, 250),
            'high': np.linspace(92, 112, 250) + np.random.normal(0, 1, 250),
            'low': np.linspace(88, 108, 250) + np.random.normal(0, 1, 250),
            'close': np.linspace(90, 110, 250) + np.random.normal(0, 1, 250),
            'volume': np.random.normal(1000, 200, 250)
        })
        
        # Ensure high is always higher than low
        self.bullish_data['high'] = self.bullish_data[['open', 'close']].max(axis=1) + abs(np.random.normal(1, 0.5, 250))
        self.bullish_data['low'] = self.bullish_data[['open', 'close']].min(axis=1) - abs(np.random.normal(1, 0.5, 250))
        
        # Create sample price data for a bearish trend
        self.bearish_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.linspace(110, 90, 250) + np.random.normal(0, 1, 250),
            'high': np.linspace(112, 92, 250) + np.random.normal(0, 1, 250),
            'low': np.linspace(108, 88, 250) + np.random.normal(0, 1, 250),
            'close': np.linspace(110, 90, 250) + np.random.normal(0, 1, 250),
            'volume': np.random.normal(1000, 200, 250)
        })
        
        # Ensure high is always higher than low
        self.bearish_data['high'] = self.bearish_data[['open', 'close']].max(axis=1) + abs(np.random.normal(1, 0.5, 250))
        self.bearish_data['low'] = self.bearish_data[['open', 'close']].min(axis=1) - abs(np.random.normal(1, 0.5, 250))
        
        # Create strategy instance
        self.strategy = TrendRSIStrategy(symbol='BTCUSDT', timeframe='1h', equity=10000.0, risk_pct=0.01)
        
        # Create indicators instance
        self.indicators = TechnicalIndicators()
    
    def test_should_open_long(self):
        """
        Test should_open_long method.
        """
        # Calculate indicators for bullish data
        bullish_with_indicators = self.indicators.calculate_all(self.bullish_data)
        
        # Manipulate RSI to be below 65 for the last candle
        bullish_with_indicators.loc[bullish_with_indicators.index[-1], 'rsi_14'] = 60
        
        # Update strategy with bullish data
        self.strategy.data = bullish_with_indicators
        
        # Check that should_open_long returns True
        self.assertTrue(self.strategy.should_open_long())
        
        # Now manipulate RSI to be above 65 for the last candle
        bullish_with_indicators.loc[bullish_with_indicators.index[-1], 'rsi_14'] = 70
        
        # Update strategy with modified data
        self.strategy.data = bullish_with_indicators
        
        # Check that should_open_long returns False due to high RSI
        self.assertFalse(self.strategy.should_open_long())
    
    def test_should_open_short(self):
        """
        Test should_open_short method.
        """
        # Calculate indicators for bearish data
        bearish_with_indicators = self.indicators.calculate_all(self.bearish_data)
        
        # Manipulate RSI to be above 35 for the last candle
        bearish_with_indicators.loc[bearish_with_indicators.index[-1], 'rsi_14'] = 40
        
        # Update strategy with bearish data
        self.strategy.data = bearish_with_indicators
        
        # Check that should_open_short returns True
        self.assertTrue(self.strategy.should_open_short())
        
        # Now manipulate RSI to be below 35 for the last candle
        bearish_with_indicators.loc[bearish_with_indicators.index[-1], 'rsi_14'] = 30
        
        # Update strategy with modified data
        self.strategy.data = bearish_with_indicators
        
        # Check that should_open_short returns False due to low RSI
        self.assertFalse(self.strategy.should_open_short())
    
    def test_calculate_position_size(self):
        """
        Test calculate_position_size method.
        """
        # Calculate indicators for bullish data
        bullish_with_indicators = self.indicators.calculate_all(self.bullish_data)
        
        # Set a known ATR value for testing
        known_atr = 5.0
        bullish_with_indicators.loc[bullish_with_indicators.index[-1], 'atr_14'] = known_atr
        
        # Update strategy with bullish data
        self.strategy.data = bullish_with_indicators
        self.strategy.equity = 10000.0
        self.strategy.risk_pct = 0.01
        
        # Calculate expected position size
        expected_size = 10000.0 * 0.01 / (known_atr * 1.5)
        
        # Check that calculate_position_size returns the expected value
        self.assertAlmostEqual(self.strategy.calculate_position_size(), expected_size, places=10)
    
    def test_calculate_stop_loss(self):
        """
        Test calculate_stop_loss method.
        """
        # Calculate indicators for bullish data
        bullish_with_indicators = self.indicators.calculate_all(self.bullish_data)
        
        # Set a known ATR value for testing
        known_atr = 5.0
        bullish_with_indicators.loc[bullish_with_indicators.index[-1], 'atr_14'] = known_atr
        
        # Update strategy with bullish data
        self.strategy.data = bullish_with_indicators
        
        # Test stop loss for long position
        entry_price = 100.0
        expected_stop_long = entry_price - (known_atr * 1.5)
        self.assertAlmostEqual(self.strategy.calculate_stop_loss(entry_price, 'long'), expected_stop_long, places=10)
        
        # Test stop loss for short position
        expected_stop_short = entry_price + (known_atr * 1.5)
        self.assertAlmostEqual(self.strategy.calculate_stop_loss(entry_price, 'short'), expected_stop_short, places=10)


class TestATRRiskManager(unittest.TestCase):
    """
    Test case for the ATR risk manager.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        # Create risk manager instance
        self.risk_manager = ATRRiskManager(risk_pct=0.01, atr_multiplier=1.5, 
                                          trailing_breakeven_atr=1.0, trailing_step_atr=0.5)
    
    def test_calculate_position_size(self):
        """
        Test calculate_position_size method.
        """
        # Test with known values
        equity = 10000.0
        atr = 5.0
        price = 100.0
        
        # Calculate expected position size in base currency units
        risk_amount = equity * 0.01
        risk_per_unit = atr * 1.5
        position_size_usd = risk_amount / risk_per_unit
        expected_size = position_size_usd / price
        
        # Check that calculate_position_size returns the expected value
        self.assertAlmostEqual(self.risk_manager.calculate_position_size(equity, atr, price), expected_size, places=10)
    
    def test_calculate_stop_loss(self):
        """
        Test calculate_stop_loss method.
        """
        # Test with known values
        entry_price = 100.0
        atr = 5.0
        
        # Calculate expected stop loss for long position
        expected_stop_long = entry_price - (atr * 1.5)
        
        # Check that calculate_stop_loss returns the expected value for long position
        self.assertAlmostEqual(self.risk_manager.calculate_stop_loss(entry_price, atr, 'long'), expected_stop_long, places=10)
        
        # Calculate expected stop loss for short position
        expected_stop_short = entry_price + (atr * 1.5)
        
        # Check that calculate_stop_loss returns the expected value for short position
        self.assertAlmostEqual(self.risk_manager.calculate_stop_loss(entry_price, atr, 'short'), expected_stop_short, places=10)
    
    def test_update_trailing_stop(self):
        """
        Test update_trailing_stop method.
        """
        # Test with known values for long position
        entry_price = 100.0
        current_price = 105.0  # Profit of 5.0
        current_stop = 95.0    # Initial stop loss
        atr = 5.0              # ATR value
        
        # Profit in ATR units = 5.0 / 5.0 = 1.0, which is exactly at the breakeven threshold
        # So the stop should move to breakeven (entry_price)
        expected_stop = entry_price
        
        # Check that update_trailing_stop returns the expected value for long position
        self.assertAlmostEqual(self.risk_manager.update_trailing_stop(entry_price, current_price, current_stop, atr, 'long'), expected_stop, places=10)
        
        # Test with more profit for long position
        current_price = 110.0  # Profit of 10.0
        current_stop = 100.0   # Stop at breakeven
        
        # Profit in ATR units = 10.0 / 5.0 = 2.0, which is 1.0 ATR above the breakeven threshold
        # So the stop should move to entry_price + (profit - breakeven_threshold * atr) * trailing_step
        # = 100.0 + (10.0 - 5.0) * 0.5 = 100.0 + 2.5 = 102.5
        expected_stop = 102.5
        
        # Check that update_trailing_stop returns the expected value for long position with more profit
        self.assertAlmostEqual(self.risk_manager.update_trailing_stop(entry_price, current_price, current_stop, atr, 'long'), expected_stop, places=10)
        
        # Test with known values for short position
        entry_price = 100.0
        current_price = 95.0   # Profit of 5.0
        current_stop = 105.0   # Initial stop loss
        atr = 5.0              # ATR value
        
        # Profit in ATR units = 5.0 / 5.0 = 1.0, which is exactly at the breakeven threshold
        # So the stop should move to breakeven (entry_price)
        expected_stop = entry_price
        
        # Check that update_trailing_stop returns the expected value for short position
        self.assertAlmostEqual(self.risk_manager.update_trailing_stop(entry_price, current_price, current_stop, atr, 'short'), expected_stop, places=10)
        
        # Test with more profit for short position
        current_price = 90.0   # Profit of 10.0
        current_stop = 100.0   # Stop at breakeven
        
        # Profit in ATR units = 10.0 / 5.0 = 2.0, which is 1.0 ATR above the breakeven threshold
        # So the stop should move to entry_price - (profit - breakeven_threshold * atr) * trailing_step
        # = 100.0 - (10.0 - 5.0) * 0.5 = 100.0 - 2.5 = 97.5
        expected_stop = 97.5
        
        # Check that update_trailing_stop returns the expected value for short position with more profit
        self.assertAlmostEqual(self.risk_manager.update_trailing_stop(entry_price, current_price, current_stop, atr, 'short'), expected_stop, places=10)


if __name__ == '__main__':
    unittest.main()
