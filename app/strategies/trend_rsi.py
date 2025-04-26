"""
Trend-following strategy with RSI counter for the DeepAgent Kraken trading bot.

This strategy implements the following rules:
- SMA-50 / SMA-200 cross determines direction
- LONG position only when SMA50 > SMA200 and RSI-14 < 65
- SHORT position (on perpetual) when SMA50 < SMA200 and RSI-14 > 35

Risk management:
- Position sizing = equity × 1% / (ATR14 × 1.5)
- Stop-Loss = 1.5 × ATR (server-side)
- Trailing-stop = move to breakeven after +1 ATR, then step 0.5 ATR
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum

from app.strategies.indicators import prepare_dataframe, calculate_all_indicators

logger = logging.getLogger(__name__)

class SignalType(str, Enum):
    """Signal types for the strategy."""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class TrendRSIStrategy:
    """
    Trend-following strategy with RSI counter.
    
    This strategy uses SMA-50/SMA-200 crossover to determine trend direction
    and RSI-14 as a counter-trend filter.
    """
    
    def __init__(self, order_router, config: Dict):
        """
        Initialize the strategy.
        
        Args:
            order_router: OrderRouter instance for exchange interactions
            config: Strategy configuration
        """
        self.order_router = order_router
        self.config = config
        self.symbol = config['symbol']
        self.interval = config.get('interval', '1h')
        
        # Strategy parameters
        self.sma_fast_period = config.get('sma_fast_period', 50)
        self.sma_slow_period = config.get('sma_slow_period', 200)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_overbought = config.get('rsi_overbought', 65)
        self.rsi_oversold = config.get('rsi_oversold', 35)
        self.atr_period = config.get('atr_period', 14)
        
        # Risk management parameters
        self.risk_per_trade = config.get('risk_per_trade', 0.01)  # 1% of equity
        self.atr_multiplier = config.get('atr_multiplier', 1.5)
        self.trailing_stop_trigger = config.get('trailing_stop_trigger', 1.0)  # Move to breakeven after +1 ATR
        self.trailing_stop_step = config.get('trailing_stop_step', 0.5)  # Step 0.5 ATR
        
        # State variables
        self.current_position = None
        self.entry_price = None
        self.stop_loss_price = None
        self.take_profit_price = None
        self.trailing_stop_price = None
        self.position_size = None
        
        logger.info(f"Initialized TrendRSIStrategy for {self.symbol} on {self.interval} timeframe")
    
    def fetch_candles(self, limit: int = 250) -> pd.DataFrame:
        """
        Fetch candlestick data from the exchange.
        
        Args:
            limit: Number of candles to fetch (default: 250 to ensure enough data for SMA-200)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Get candles from the exchange via order router
            candles = self.order_router.get_klines(
                symbol=self.symbol,
                interval=self.interval,
                limit=limit
            )
            
            # Prepare DataFrame
            df = prepare_dataframe(candles)
            
            logger.debug(f"Fetched {len(df)} candles for {self.symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            raise
    
    def compute_indicators(self, df: pd.DataFrame) -> Dict:
        """
        Compute all indicators needed for the strategy.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Dictionary with calculated indicators
        """
        try:
            indicators = calculate_all_indicators(df, self.config)
            
            # Log current indicator values
            logger.debug(f"SMA-{self.sma_fast_period}: {indicators['sma_fast']['value']:.2f}")
            logger.debug(f"SMA-{self.sma_slow_period}: {indicators['sma_slow']['value']:.2f}")
            logger.debug(f"RSI-{self.rsi_period}: {indicators['rsi']['value']:.2f}")
            logger.debug(f"ATR-{self.atr_period}: {indicators['atr']['value']:.2f}")
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error computing indicators: {e}")
            raise
    
    def generate_signal(self, indicators: Dict) -> SignalType:
        """
        Generate trading signal based on indicators.
        
        Args:
            indicators: Dictionary with calculated indicators
            
        Returns:
            Signal type (LONG, SHORT, or FLAT)
        """
        try:
            # Extract indicator values
            sma_fast = indicators['sma_fast']['value']
            sma_slow = indicators['sma_slow']['value']
            rsi_value = indicators['rsi']['value']
            
            # Check for NaN values
            if pd.isna(sma_fast) or pd.isna(sma_slow) or pd.isna(rsi_value):
                logger.warning("NaN values in indicators, returning FLAT signal")
                return SignalType.FLAT
            
            # Determine trend direction
            trend_up = sma_fast > sma_slow
            trend_down = sma_fast < sma_slow
            
            # Apply RSI filter
            if trend_up and rsi_value < self.rsi_overbought:
                logger.info(f"LONG signal: SMA-{self.sma_fast_period}({sma_fast:.2f}) > SMA-{self.sma_slow_period}({sma_slow:.2f}) and RSI({rsi_value:.2f}) < {self.rsi_overbought}")
                return SignalType.LONG
            
            elif trend_down and rsi_value > self.rsi_oversold:
                logger.info(f"SHORT signal: SMA-{self.sma_fast_period}({sma_fast:.2f}) < SMA-{self.sma_slow_period}({sma_slow:.2f}) and RSI({rsi_value:.2f}) > {self.rsi_oversold}")
                return SignalType.SHORT
            
            else:
                # Check for exit signals
                if self.current_position == SignalType.LONG:
                    if trend_down or rsi_value >= self.rsi_overbought:
                        logger.info(f"CLOSE_LONG signal: Trend reversed or RSI overbought")
                        return SignalType.CLOSE_LONG
                
                elif self.current_position == SignalType.SHORT:
                    if trend_up or rsi_value <= self.rsi_oversold:
                        logger.info(f"CLOSE_SHORT signal: Trend reversed or RSI oversold")
                        return SignalType.CLOSE_SHORT
                
                logger.debug("No clear signal, maintaining current position")
                return SignalType.FLAT
                
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return SignalType.FLAT
    
    def calculate_position_size(self, equity: float, atr: float) -> float:
        """
        Calculate position size based on risk parameters.
        
        Formula: Position size = equity × risk_per_trade / (ATR × atr_multiplier)
        
        Args:
            equity: Account equity
            atr: Current ATR value
            
        Returns:
            Position size in base currency
        """
        try:
            # Get current market price
            ticker = self.order_router.current_exchange.get_ticker(self.symbol)
            current_price = float(ticker['last'])
            
            # Calculate risk amount in quote currency
            risk_amount = equity * self.risk_per_trade
            
            # Calculate stop loss distance in quote currency
            stop_loss_distance = atr * self.atr_multiplier
            
            # Calculate position size in base currency
            position_size = risk_amount / stop_loss_distance
            
            # Convert to contract size for perpetual futures
            contract_size = position_size / current_price
            
            logger.info(f"Position size calculation: {equity} × {self.risk_per_trade} / ({atr} × {self.atr_multiplier}) = {contract_size:.6f} contracts")
            
            return contract_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            # Return a safe default
            return 0.0
    
    def calculate_stop_loss(self, entry_price: float, atr: float, side: SignalType) -> float:
        """
        Calculate stop loss price based on ATR.
        
        Args:
            entry_price: Entry price
            atr: Current ATR value
            side: Position side (LONG or SHORT)
            
        Returns:
            Stop loss price
        """
        stop_distance = atr * self.atr_multiplier
        
        if side == SignalType.LONG:
            stop_loss = entry_price - stop_distance
        else:  # SHORT
            stop_loss = entry_price + stop_distance
        
        logger.info(f"Stop loss calculation for {side}: {entry_price} ± ({atr} × {self.atr_multiplier}) = {stop_loss:.2f}")
        
        return stop_loss
    
    def calculate_trailing_stop(self, entry_price: float, current_price: float, atr: float, side: SignalType) -> Optional[float]:
        """
        Calculate trailing stop price based on ATR and current price.
        
        Args:
            entry_price: Entry price
            current_price: Current market price
            atr: Current ATR value
            side: Position side (LONG or SHORT)
            
        Returns:
            Trailing stop price or None if not triggered
        """
        # Calculate profit in ATR units
        if side == SignalType.LONG:
            profit_atr = (current_price - entry_price) / atr
            
            # Check if profit exceeds trigger threshold
            if profit_atr >= self.trailing_stop_trigger:
                # Calculate number of steps beyond trigger
                steps_beyond_trigger = (profit_atr - self.trailing_stop_trigger) // self.trailing_stop_step
                
                # Calculate trailing stop price
                if steps_beyond_trigger == 0:
                    # Move to breakeven
                    trailing_stop = entry_price
                else:
                    # Move up by steps
                    trailing_stop = entry_price + (steps_beyond_trigger * self.trailing_stop_step * atr)
                
                logger.info(f"Trailing stop for LONG: {trailing_stop:.2f} (profit: {profit_atr:.2f} ATR, steps: {steps_beyond_trigger})")
                return trailing_stop
            
        else:  # SHORT
            profit_atr = (entry_price - current_price) / atr
            
            # Check if profit exceeds trigger threshold
            if profit_atr >= self.trailing_stop_trigger:
                # Calculate number of steps beyond trigger
                steps_beyond_trigger = (profit_atr - self.trailing_stop_trigger) // self.trailing_stop_step
                
                # Calculate trailing stop price
                if steps_beyond_trigger == 0:
                    # Move to breakeven
                    trailing_stop = entry_price
                else:
                    # Move down by steps
                    trailing_stop = entry_price - (steps_beyond_trigger * self.trailing_stop_step * atr)
                
                logger.info(f"Trailing stop for SHORT: {trailing_stop:.2f} (profit: {profit_atr:.2f} ATR, steps: {steps_beyond_trigger})")
                return trailing_stop
        
        # Not enough profit to trigger trailing stop
        return None
    
    def update_trailing_stop(self) -> Optional[Dict]:
        """
        Update trailing stop order if needed.
        
        Returns:
            Updated order information or None if no update needed
        """
        if not self.current_position or not self.entry_price or not self.stop_loss_price:
            return None
        
        try:
            # Get current market price and position
            ticker = self.order_router.current_exchange.get_ticker(self.symbol)
            current_price = float(ticker['last'])
            
            # Get current ATR
            df = self.fetch_candles()
            indicators = self.compute_indicators(df)
            atr = indicators['atr']['value']
            
            # Calculate new trailing stop
            new_trailing_stop = self.calculate_trailing_stop(
                self.entry_price,
                current_price,
                atr,
                self.current_position
            )
            
            # Check if trailing stop should be updated
            if new_trailing_stop and (not self.trailing_stop_price or 
                                     (self.current_position == SignalType.LONG and new_trailing_stop > self.trailing_stop_price) or
                                     (self.current_position == SignalType.SHORT and new_trailing_stop < self.trailing_stop_price)):
                
                # Update trailing stop order
                # Note: Implementation depends on exchange API
                # This is a simplified example
                from app.core.order_router import OrderType, OrderSide, PositionSide
                
                # Determine order parameters based on position side
                if self.current_position == SignalType.LONG:
                    order_side = OrderSide.SELL
                    position_side = PositionSide.LONG
                else:  # SHORT
                    order_side = OrderSide.BUY
                    position_side = PositionSide.SHORT
                
                # Update stop loss order
                updated_order = self.order_router.update_order(
                    order_id=self.stop_loss_order_id,
                    symbol=self.symbol,
                    price=new_trailing_stop
                )
                
                # Update state
                self.trailing_stop_price = new_trailing_stop
                
                logger.info(f"Updated trailing stop to {new_trailing_stop:.2f}")
                
                return updated_order
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")
            return None
    
    def run(self) -> Dict:
        """
        Run the strategy once.
        
        Returns:
            Dictionary with strategy results
        """
        try:
            # Fetch candles
            df = self.fetch_candles()
            
            # Compute indicators
            indicators = self.compute_indicators(df)
            
            # Generate signal
            signal = self.generate_signal(indicators)
            
            # Update trailing stop if in position
            if self.current_position in [SignalType.LONG, SignalType.SHORT]:
                self.update_trailing_stop()
            
            # Return strategy results
            return {
                'timestamp': pd.Timestamp.now(),
                'symbol': self.symbol,
                'signal': signal,
                'indicators': {
                    'sma_fast': indicators['sma_fast']['value'],
                    'sma_slow': indicators['sma_slow']['value'],
                    'rsi': indicators['rsi']['value'],
                    'atr': indicators['atr']['value']
                },
                'current_position': self.current_position,
                'entry_price': self.entry_price,
                'stop_loss_price': self.stop_loss_price,
                'trailing_stop_price': self.trailing_stop_price
            }
            
        except Exception as e:
            logger.error(f"Error running strategy: {e}")
            return {
                'timestamp': pd.Timestamp.now(),
                'symbol': self.symbol,
                'signal': SignalType.FLAT,
                'error': str(e)
            }
