"""
Trend-follower strategy with RSI counter.

Strategy rules:
- SMA-50 / SMA-200 cross = direction
- Long position only when SMA50 > SMA200 and RSI-14 < 65
- Short position (on perpetual) when SMA50 < SMA200 and RSI-14 > 35

Risk management:
1. Position sizing = equity × 1% / (ATR14 × 1.5)
2. Stop-Loss = 1.5 × ATR (server-side)
3. Trailing-stop = move to breakeven after +1 ATR, then step by 0.5 ATR
"""

import logging
from typing import Dict, Optional, Tuple, Any, List
import pandas as pd
import numpy as np

from app.strategies.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class TrendRSIStrategy:
    """
    Trend-follower strategy with RSI counter.
    """
    
    def __init__(self, symbol: str, timeframe: str = '1h', equity: float = 10000.0, risk_pct: float = 0.01):
        """
        Initialize the strategy.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Candle timeframe (default: '1h')
            equity: Account equity in USD (default: 10000.0)
            risk_pct: Risk percentage per trade (default: 0.01 = 1%)
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.equity = equity
        self.risk_pct = risk_pct
        self.indicators = TechnicalIndicators()
        self.data = None
        self.current_position = None
        self.entry_price = None
        self.stop_loss = None
        self.trailing_stop = None
        
    def update_data(self, candles: pd.DataFrame) -> None:
        """
        Update the strategy with new candle data.
        
        Args:
            candles: DataFrame containing OHLC price data
        """
        # Ensure the dataframe has the required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        for col in required_columns:
            if col not in candles.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Calculate indicators
        self.data = self.indicators.calculate_all(candles)
        logger.info(f"Updated strategy data with {len(candles)} candles")
        
    def update_equity(self, equity: float) -> None:
        """
        Update the account equity.
        
        Args:
            equity: New account equity value
        """
        self.equity = equity
        logger.info(f"Updated equity to {equity}")
        
    def should_open_long(self) -> bool:
        """
        Check if a long position should be opened.
        
        Returns:
            True if a long position should be opened, False otherwise
        """
        if self.data is None or len(self.data) < 200:
            logger.warning("Not enough data to generate signals")
            return False
        
        # Get the latest values
        latest = self.data.iloc[-1]
        
        # Check conditions: SMA50 > SMA200 and RSI-14 < 65
        sma_condition = latest['sma_50'] > latest['sma_200']
        rsi_condition = latest['rsi_14'] < 65
        
        should_long = sma_condition and rsi_condition
        
        if should_long:
            logger.info(f"Long signal generated: SMA50={latest['sma_50']:.2f}, SMA200={latest['sma_200']:.2f}, RSI14={latest['rsi_14']:.2f}")
        
        return should_long
    
    def should_open_short(self) -> bool:
        """
        Check if a short position should be opened.
        
        Returns:
            True if a short position should be opened, False otherwise
        """
        if self.data is None or len(self.data) < 200:
            logger.warning("Not enough data to generate signals")
            return False
        
        # Get the latest values
        latest = self.data.iloc[-1]
        
        # Check conditions: SMA50 < SMA200 and RSI-14 > 35
        sma_condition = latest['sma_50'] < latest['sma_200']
        rsi_condition = latest['rsi_14'] > 35
        
        should_short = sma_condition and rsi_condition
        
        if should_short:
            logger.info(f"Short signal generated: SMA50={latest['sma_50']:.2f}, SMA200={latest['sma_200']:.2f}, RSI14={latest['rsi_14']:.2f}")
        
        return should_short
    
    def calculate_position_size(self) -> float:
        """
        Calculate position size based on risk management rules.
        Position sizing = equity × 1% / (ATR14 × 1.5)
        
        Returns:
            Position size in base currency units
        """
        if self.data is None or len(self.data) < 14:
            logger.warning("Not enough data to calculate position size")
            return 0.0
        
        latest = self.data.iloc[-1]
        atr = latest['atr_14']
        
        # Risk amount in USD
        risk_amount = self.equity * self.risk_pct
        
        # Risk per unit (ATR * 1.5)
        risk_per_unit = atr * 1.5
        
        # Position size = risk amount / risk per unit
        position_size = risk_amount / risk_per_unit
        
        logger.info(f"Calculated position size: {position_size:.6f} units (Equity: {self.equity}, ATR: {atr:.2f})")
        
        return position_size
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """
        Calculate stop loss price based on ATR.
        Stop-Loss = 1.5 × ATR (server-side)
        
        Args:
            entry_price: Entry price of the position
            side: Position side ('long' or 'short')
            
        Returns:
            Stop loss price
        """
        if self.data is None or len(self.data) < 14:
            logger.warning("Not enough data to calculate stop loss")
            return 0.0
        
        latest = self.data.iloc[-1]
        atr = latest['atr_14']
        
        # Calculate stop loss distance
        stop_distance = atr * 1.5
        
        # Calculate stop loss price based on position side
        if side.lower() == 'long':
            stop_loss = entry_price - stop_distance
        else:  # short
            stop_loss = entry_price + stop_distance
        
        logger.info(f"Calculated stop loss: {stop_loss:.2f} for {side} position (Entry: {entry_price:.2f}, ATR: {atr:.2f})")
        
        return stop_loss
    
    def update_trailing_stop(self, current_price: float, side: str) -> Optional[float]:
        """
        Update trailing stop based on current price and ATR.
        Trailing-stop = move to breakeven after +1 ATR, then step by 0.5 ATR
        
        Args:
            current_price: Current market price
            side: Position side ('long' or 'short')
            
        Returns:
            New trailing stop price or None if no update needed
        """
        if self.data is None or len(self.data) < 14 or self.entry_price is None or self.stop_loss is None:
            logger.warning("Not enough data to update trailing stop")
            return None
        
        latest = self.data.iloc[-1]
        atr = latest['atr_14']
        
        # Calculate profit in ATR units
        if side.lower() == 'long':
            profit_distance = current_price - self.entry_price
            profit_in_atr = profit_distance / atr
            
            # Move to breakeven after +1 ATR
            if profit_in_atr >= 1.0 and self.trailing_stop is None:
                self.trailing_stop = self.entry_price
                logger.info(f"Moving stop to breakeven: {self.trailing_stop:.2f}")
                return self.trailing_stop
            
            # Then step by 0.5 ATR
            elif profit_in_atr >= 1.0 and self.trailing_stop is not None:
                potential_stop = self.entry_price + (profit_distance - atr) * 0.5
                if potential_stop > self.trailing_stop:
                    self.trailing_stop = potential_stop
                    logger.info(f"Updated trailing stop to: {self.trailing_stop:.2f}")
                    return self.trailing_stop
        
        elif side.lower() == 'short':
            profit_distance = self.entry_price - current_price
            profit_in_atr = profit_distance / atr
            
            # Move to breakeven after +1 ATR
            if profit_in_atr >= 1.0 and self.trailing_stop is None:
                self.trailing_stop = self.entry_price
                logger.info(f"Moving stop to breakeven: {self.trailing_stop:.2f}")
                return self.trailing_stop
            
            # Then step by 0.5 ATR
            elif profit_in_atr >= 1.0 and self.trailing_stop is not None:
                potential_stop = self.entry_price - (profit_distance - atr) * 0.5
                if potential_stop < self.trailing_stop:
                    self.trailing_stop = potential_stop
                    logger.info(f"Updated trailing stop to: {self.trailing_stop:.2f}")
                    return self.trailing_stop
        
        return None
    
    def generate_signal(self) -> Dict[str, Any]:
        """
        Generate trading signal based on current market conditions.
        
        Returns:
            Dictionary containing signal details
        """
        if self.data is None or len(self.data) < 200:
            logger.warning("Not enough data to generate signals")
            return {"action": "wait", "reason": "insufficient_data"}
        
        latest_price = self.data.iloc[-1]['close']
        
        # Check for entry signals
        if self.current_position is None:
            if self.should_open_long():
                position_size = self.calculate_position_size()
                entry_price = latest_price
                stop_loss = self.calculate_stop_loss(entry_price, 'long')
                
                self.current_position = 'long'
                self.entry_price = entry_price
                self.stop_loss = stop_loss
                self.trailing_stop = None
                
                return {
                    "action": "open",
                    "side": "long",
                    "size": position_size,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "reason": "trend_following_long"
                }
            
            elif self.should_open_short():
                position_size = self.calculate_position_size()
                entry_price = latest_price
                stop_loss = self.calculate_stop_loss(entry_price, 'short')
                
                self.current_position = 'short'
                self.entry_price = entry_price
                self.stop_loss = stop_loss
                self.trailing_stop = None
                
                return {
                    "action": "open",
                    "side": "short",
                    "size": position_size,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "reason": "trend_following_short"
                }
            
            else:
                return {"action": "wait", "reason": "no_signal"}
        
        # Check for exit signals (trend reversal)
        elif self.current_position == 'long':
            # Exit long if trend reverses
            if self.should_open_short():
                self.current_position = None
                self.entry_price = None
                self.stop_loss = None
                self.trailing_stop = None
                
                return {
                    "action": "close",
                    "side": "long",
                    "reason": "trend_reversal"
                }
            
            # Update trailing stop
            new_stop = self.update_trailing_stop(latest_price, 'long')
            if new_stop is not None:
                return {
                    "action": "update_stop",
                    "side": "long",
                    "stop_loss": new_stop,
                    "reason": "trailing_stop_update"
                }
        
        elif self.current_position == 'short':
            # Exit short if trend reverses
            if self.should_open_long():
                self.current_position = None
                self.entry_price = None
                self.stop_loss = None
                self.trailing_stop = None
                
                return {
                    "action": "close",
                    "side": "short",
                    "reason": "trend_reversal"
                }
            
            # Update trailing stop
            new_stop = self.update_trailing_stop(latest_price, 'short')
            if new_stop is not None:
                return {
                    "action": "update_stop",
                    "side": "short",
                    "stop_loss": new_stop,
                    "reason": "trailing_stop_update"
                }
        
        return {"action": "hold", "reason": "no_exit_signal"}
