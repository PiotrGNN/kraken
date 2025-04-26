"""
ATR-based risk management module.

Provides functionality for:
1. Position sizing based on ATR
2. Stop-loss calculation
3. Trailing stop management
"""

import logging
from typing import Dict, Optional, Tuple, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ATRRiskManager:
    """
    Risk manager using Average True Range (ATR) for position sizing and stop-loss calculation.
    """
    
    def __init__(self, risk_pct: float = 0.01, atr_multiplier: float = 1.5, 
                 trailing_breakeven_atr: float = 1.0, trailing_step_atr: float = 0.5):
        """
        Initialize the ATR risk manager.
        
        Args:
            risk_pct: Risk percentage per trade (default: 0.01 = 1%)
            atr_multiplier: Multiplier for ATR to determine stop distance (default: 1.5)
            trailing_breakeven_atr: ATR multiple to move stop to breakeven (default: 1.0)
            trailing_step_atr: ATR multiple for trailing stop steps (default: 0.5)
        """
        self.risk_pct = risk_pct
        self.atr_multiplier = atr_multiplier
        self.trailing_breakeven_atr = trailing_breakeven_atr
        self.trailing_step_atr = trailing_step_atr
    
    def calculate_position_size(self, equity: float, atr: float, price: float) -> float:
        """
        Calculate position size based on account equity and ATR.
        Formula: Position size = (equity * risk_pct) / (ATR * atr_multiplier)
        
        Args:
            equity: Account equity in USD
            atr: Current ATR value
            price: Current market price
            
        Returns:
            Position size in base currency units
        """
        if atr <= 0:
            logger.warning("ATR value is zero or negative, cannot calculate position size")
            return 0.0
        
        # Risk amount in USD
        risk_amount = equity * self.risk_pct
        
        # Risk per unit (ATR * multiplier)
        risk_per_unit = atr * self.atr_multiplier
        
        # Position size in USD
        position_size_in_usd = risk_amount / risk_per_unit
        
        # Convert to base currency units
        position_size = position_size_in_usd / price
        
        logger.info(f"Calculated position size: {position_size:.6f} units (Equity: {equity}, ATR: {atr:.2f})")
        
        return position_size
    
    def calculate_stop_loss(self, entry_price: float, atr: float, side: str) -> float:
        """
        Calculate stop loss price based on ATR.
        
        Args:
            entry_price: Entry price of the position
            atr: Current ATR value
            side: Position side ('long' or 'short')
            
        Returns:
            Stop loss price
        """
        # Calculate stop loss distance
        stop_distance = atr * self.atr_multiplier
        
        # Calculate stop loss price based on position side
        if side.lower() == 'long':
            stop_loss = entry_price - stop_distance
        else:  # short
            stop_loss = entry_price + stop_distance
        
        logger.info(f"Calculated stop loss: {stop_loss:.2f} for {side} position (Entry: {entry_price:.2f}, ATR: {atr:.2f})")
        
        return stop_loss
    
    def update_trailing_stop(self, entry_price: float, current_price: float, 
                             current_stop: float, atr: float, side: str) -> Optional[float]:
        """
        Update trailing stop based on current price and ATR.
        
        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            current_stop: Current stop loss price
            atr: Current ATR value
            side: Position side ('long' or 'short')
            
        Returns:
            New trailing stop price or None if no update needed
        """
        # Calculate profit in ATR units
        if side.lower() == 'long':
            profit_distance = current_price - entry_price
            profit_in_atr = profit_distance / atr
            
            # If we haven't reached breakeven threshold yet
            if profit_in_atr < self.trailing_breakeven_atr:
                return None
            
            # Move to breakeven if current stop is below entry
            if current_stop < entry_price:
                new_stop = entry_price
                logger.info(f"Moving stop to breakeven: {new_stop:.2f}")
                return new_stop
            
            # Calculate potential new stop
            potential_stop = entry_price + (profit_in_atr - self.trailing_breakeven_atr) * atr * self.trailing_step_atr
            
            # Only update if the new stop is higher
            if potential_stop > current_stop:
                logger.info(f"Updated trailing stop from {current_stop:.2f} to {potential_stop:.2f}")
                return potential_stop
            
        elif side.lower() == 'short':
            profit_distance = entry_price - current_price
            profit_in_atr = profit_distance / atr
            
            # If we haven't reached breakeven threshold yet
            if profit_in_atr < self.trailing_breakeven_atr:
                return None
            
            # Move to breakeven if current stop is above entry
            if current_stop > entry_price:
                new_stop = entry_price
                logger.info(f"Moving stop to breakeven: {new_stop:.2f}")
                return new_stop
            
            # Calculate potential new stop
            potential_stop = entry_price - (profit_in_atr - self.trailing_breakeven_atr) * atr * self.trailing_step_atr
            
            # Only update if the new stop is lower
            if potential_stop < current_stop:
                logger.info(f"Updated trailing stop from {current_stop:.2f} to {potential_stop:.2f}")
                return potential_stop
        
        return None
    
    def calculate_risk_reward_ratio(self, entry_price: float, stop_loss: float, 
                                   take_profit: float, side: str) -> float:
        """
        Calculate risk-to-reward ratio for a trade.
        
        Args:
            entry_price: Entry price of the position
            stop_loss: Stop loss price
            take_profit: Take profit price
            side: Position side ('long' or 'short')
            
        Returns:
            Risk-to-reward ratio (reward/risk)
        """
        if side.lower() == 'long':
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # short
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            logger.warning("Risk is zero or negative, cannot calculate risk-reward ratio")
            return 0.0
        
        ratio = reward / risk
        
        logger.info(f"Risk-reward ratio: {ratio:.2f} (Risk: {risk:.2f}, Reward: {reward:.2f})")
        
        return ratio
