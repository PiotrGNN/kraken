"""
API routes for the DeepAgent Kraken Trading Bot
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, List
from app.core.bot import TradingBot
from app.core.config import settings
from app.core.env_manager import Environment, get_env_manager
from app.api import env

router = APIRouter()
bot = TradingBot()

@router.get("/status")
async def get_status():
    """Get the current status of the trading bot"""
    return await bot.get_status()

@router.post("/start")
async def start_trading(background_tasks: BackgroundTasks):
    """Start the trading bot"""
    background_tasks.add_task(bot.start_trading)
    return {"message": "Trading started"}

@router.post("/stop")
async def stop_trading():
    """Stop the trading bot"""
    await bot.stop_trading()
    return {"message": "Trading stopped"}

@router.get("/config")
async def get_config():
    """Get the current configuration"""
    return {
        "environment": settings.ENVIRONMENT,
        "trading_pairs": settings.TRADING_PAIRS,
        "timeframes": settings.TRADING_TIMEFRAMES,
        "risk_settings": {
            "max_position_size_usd": settings.MAX_POSITION_SIZE_USD,
            "max_drawdown_percent": settings.MAX_DRAWDOWN_PERCENT,
            "max_exposure_percent": settings.MAX_EXPOSURE_PERCENT
        }
    }

@router.post("/config/environment")
async def set_environment(environment: str, background_tasks: BackgroundTasks):
    """Set the trading environment (testnet/mainnet)"""
    try:
        env_value = Environment(environment.lower())
        # Use our dedicated environment API
        return await env.switch_environment(environment, background_tasks)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment: {environment}. Must be one of: testnet, mainnet"
        )
