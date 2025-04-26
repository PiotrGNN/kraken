"""
Technical indicators for trading strategies.
Provides implementations for SMA, RSI, and ATR calculations.
"""

import numpy as np
import pandas as pd


class TechnicalIndicators:
    """
    Class for calculating technical indicators used in trading strategies.
    """
    
    @staticmethod
    def sma(data: pd.DataFrame, column: str = 'close', period: int = 50) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA).
        
        Args:
            data: DataFrame containing price data
            column: Column name to use for calculation (default: 'close')
            period: Period for SMA calculation (default: 50)
            
        Returns:
            Series containing SMA values
        """
        return data[column].rolling(window=period).mean()
    
    @staticmethod
    def rsi(data: pd.DataFrame, column: str = 'close', period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            data: DataFrame containing price data
            column: Column name to use for calculation (default: 'close')
            period: Period for RSI calculation (default: 14)
            
        Returns:
            Series containing RSI values
        """
        delta = data[column].diff()
        
        # Make two series: one for gains and one for losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and average loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS (Relative Strength)
        rs = avg_gain / avg_loss
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        # Set the first 'period' values to NaN
        rsi.iloc[:period] = np.nan
        
        return rsi
    
    @staticmethod
    def atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        Args:
            data: DataFrame containing OHLC price data
            period: Period for ATR calculation (default: 14)
            
        Returns:
            Series containing ATR values
        """
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate ATR
        atr = tr.rolling(window=period).mean()
        
        # Set the first 'period' values to NaN
        atr.iloc[:period] = np.nan
        
        return atr
    
    @staticmethod
    def calculate_all(data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all indicators and add them to the dataframe.
        
        Args:
            data: DataFrame containing OHLC price data
            
        Returns:
            DataFrame with added indicator columns
        """
        indicators = TechnicalIndicators()
        
        # Make a copy to avoid modifying the original dataframe
        result = data.copy()
        
        # Calculate indicators
        result['sma_50'] = indicators.sma(data, period=50)
        result['sma_200'] = indicators.sma(data, period=200)
        result['rsi_14'] = indicators.rsi(data, period=14)
        result['atr_14'] = indicators.atr(data, period=14)
        
        return result
