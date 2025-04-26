"""
Environment management API routes.

This module provides API routes for managing the trading environment.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from app.core.env_manager import get_env_manager, Environment
from app.core.order_router import OrderRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/env", tags=["environment"])

# Reference to the order router
_order_router = None


def set_order_router(order_router: OrderRouter):
    """
    Set the order router reference for the API routes.
    
    Args:
        order_router: Order router instance
    """
    global _order_router
    _order_router = order_router


def get_order_router() -> OrderRouter:
    """
    Get the order router reference.
    
    Returns:
        Order router instance
    
    Raises:
        HTTPException: If order router is not initialized
    """
    if _order_router is None:
        raise HTTPException(status_code=500, detail="Order router not initialized")
    return _order_router


@router.get("/")
async def get_environment() -> Dict[str, Any]:
    """
    Get the current environment status.
    
    Returns:
        Dictionary with environment status information
    """
    env_manager = get_env_manager()
    return env_manager.get_status()


@router.post("/{target_env}")
async def switch_environment(
    target_env: str,
    background_tasks: BackgroundTasks,
    order_router: OrderRouter = Depends(get_order_router)
) -> Dict[str, Any]:
    """
    Switch the trading environment.
    
    Args:
        target_env: Target environment to switch to (testnet or mainnet)
        background_tasks: FastAPI background tasks
        order_router: Order router instance
    
    Returns:
        Dictionary with switch status information
    
    Raises:
        HTTPException: If target environment is invalid
    """
    # Validate target environment
    try:
        target = Environment(target_env.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment: {target_env}. Must be one of: testnet, mainnet"
        )
    
    # Get current environment
    env_manager = get_env_manager()
    current_env = env_manager.get_environment()
    
    # No change needed if already in target environment
    if current_env == target:
        return {
            "status": "no_change",
            "message": f"Already in {target} environment",
            "current_environment": current_env
        }
    
    # Schedule environment switch in background
    background_tasks.add_task(order_router.handle_env_change, target)
    
    return {
        "status": "switching",
        "message": f"Switching from {current_env} to {target}",
        "from_environment": current_env,
        "to_environment": target
    }


@router.post("/toggle")
async def toggle_environment(
    background_tasks: BackgroundTasks,
    order_router: OrderRouter = Depends(get_order_router)
) -> Dict[str, Any]:
    """
    Toggle between TESTNET and MAINNET environments.
    
    Args:
        background_tasks: FastAPI background tasks
        order_router: Order router instance
    
    Returns:
        Dictionary with switch status information
    """
    # Get current environment
    env_manager = get_env_manager()
    current_env = env_manager.get_environment()
    
    # Determine target environment
    target = Environment.MAINNET if current_env == Environment.TESTNET else Environment.TESTNET
    
    # Schedule environment switch in background
    background_tasks.add_task(order_router.handle_env_change, target)
    
    return {
        "status": "switching",
        "message": f"Toggling from {current_env} to {target}",
        "from_environment": current_env,
        "to_environment": target
    }
