"""
Risk management system implementation
"""
import logging
from typing import Dict, Optional
from app.core.config import settings
from app.risk.position_sizing.manager import PositionSizingManager
from app.risk.drawdown_protection.manager import DrawdownProtectionManager
from app.risk.exposure_management.manager import ExposureManager

logger = logging.getLogger(__name__)

class RiskManager:
    """Risk management system for the trading bot"""
    
    def __init__(self):
        self.position_sizing = PositionSizingManager()
        self.drawdown_protection = DrawdownProtectionManager()
        self.exposure_management = ExposureManager()
    
    async def initialize(self):
        """Initialize the risk management components"""
        logger.info("Initializing risk management system")
        await self.position_sizing.initialize()
        await self.drawdown_protection.initialize()
        await self.exposure_management.initialize()
    
    async def validate_signal(self, signal: Dict, trading_pair: str) -> Optional[Dict]:
        """
        Validate a trading signal against risk management rules
        
        Args:
            signal: The trading signal to validate
            trading_pair: The trading pair the signal is for
            
        Returns:
            Modified signal with appropriate position size or None if rejected
        """
        if signal["action"] == "none":
            return None
        
        try:
            # Check if we're in drawdown protection mode
            if await self.drawdown_protection.should_prevent_trading():
                logger.warning("Trade rejected due to drawdown protection")
                return None
            
            # Check if we have too much exposure
            if await self.exposure_management.is_max_exposure_reached():
                logger.warning("Trade rejected due to maximum exposure reached")
                return None
            
            # Calculate appropriate position size
            position_size = await self.position_sizing.calculate_position_size(
                signal["price"],
                trading_pair
            )
            
            if position_size <= 0:
                logger.warning("Trade rejected due to zero position size")
                return None
            
            # Update the signal with the calculated position size
            validated_signal = signal.copy()
            validated_signal["size"] = position_size
            
            logger.info(f"Signal validated: {validated_signal}")
            return validated_signal
            
        except Exception as e:
            logger.error(f"Error in risk validation: {str(e)}")
            return None
