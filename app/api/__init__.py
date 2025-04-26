"""
API routes for the DeepAgent Kraken trading bot.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from typing import Dict, List, Any, Optional

from app.models import (
    OrderRequest, OrderResponse, Order, Position, AccountInfo, Signal, BotConfig
)
from app.core.order_router import OrderRouter

logger = logging.getLogger(__name__)

app = FastAPI(title="DeepAgent Kraken API", description="API for the DeepAgent Kraken trading bot")


# Dependency to get the order router
def get_order_router() -> OrderRouter:
    """
    Get the order router instance.
    
    Returns:
        OrderRouter instance
    """
    # This would typically be initialized at application startup
    # and stored in a global variable or state manager
    return app.state.order_router


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return {"status": "ok"}


@app.get("/config", tags=["Configuration"])
async def get_config() -> BotConfig:
    """
    Get the current bot configuration.
    
    Returns:
        Bot configuration
    """
    return app.state.config


@app.post("/orders", tags=["Trading"], response_model=OrderResponse)
async def place_order(
    order_request: OrderRequest,
    background_tasks: BackgroundTasks,
    order_router: OrderRouter = Depends(get_order_router)
) -> OrderResponse:
    """
    Place an order.
    
    Args:
        order_request: Order request
        background_tasks: Background tasks
        order_router: Order router
        
    Returns:
        Order response
    """
    try:
        # Convert order request to order parameters
        order_params = order_request.dict()
        
        # Place order
        response = order_router.place_order(order_params)
        
        return OrderResponse(
            status="success" if response.get("status") != "error" else "error",
            message=response.get("message"),
            order=response.get("order"),
            error_code=response.get("error_code")
        )
    except Exception as e:
        logger.error(f"Failed to place order: {str(e)}")
        return OrderResponse(
            status="error",
            message=str(e)
        )


@app.get("/orders/{order_id}", tags=["Trading"], response_model=Order)
async def get_order(
    order_id: str,
    exchange: Optional[str] = None,
    order_router: OrderRouter = Depends(get_order_router)
) -> Order:
    """
    Get order details.
    
    Args:
        order_id: Order ID
        exchange: Exchange name
        order_router: Order router
        
    Returns:
        Order details
    """
    try:
        # Get exchange connector
        exchange_connector = order_router.get_exchange(exchange)
        if not exchange_connector:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange} not found")
        
        # Get order details
        order = exchange_connector.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/orders/{order_id}", tags=["Trading"], response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    exchange: Optional[str] = None,
    order_router: OrderRouter = Depends(get_order_router)
) -> OrderResponse:
    """
    Cancel an order.
    
    Args:
        order_id: Order ID
        exchange: Exchange name
        order_router: Order router
        
    Returns:
        Order cancellation response
    """
    try:
        # Cancel order
        response = order_router.cancel_order(order_id, exchange)
        
        return OrderResponse(
            status="success" if response.get("status") != "error" else "error",
            message=response.get("message"),
            order=response.get("order"),
            error_code=response.get("error_code")
        )
    except Exception as e:
        logger.error(f"Failed to cancel order: {str(e)}")
        return OrderResponse(
            status="error",
            message=str(e)
        )


@app.get("/positions", tags=["Trading"], response_model=List[Position])
async def get_positions(
    symbol: Optional[str] = None,
    exchange: Optional[str] = None,
    order_router: OrderRouter = Depends(get_order_router)
) -> List[Position]:
    """
    Get current positions.
    
    Args:
        symbol: Trading symbol
        exchange: Exchange name
        order_router: Order router
        
    Returns:
        List of positions
    """
    try:
        # Get exchange connector
        exchange_connector = order_router.get_exchange(exchange)
        if not exchange_connector:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange} not found")
        
        # Get positions
        positions = exchange_connector.get_positions(symbol)
        
        return positions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/account", tags=["Trading"], response_model=AccountInfo)
async def get_account_info(
    exchange: Optional[str] = None,
    order_router: OrderRouter = Depends(get_order_router)
) -> AccountInfo:
    """
    Get account information.
    
    Args:
        exchange: Exchange name
        order_router: Order router
        
    Returns:
        Account information
    """
    try:
        # Get exchange connector
        exchange_connector = order_router.get_exchange(exchange)
        if not exchange_connector:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange} not found")
        
        # Get account information
        account_info = exchange_connector.get_account_info()
        
        return account_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account information: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/strategy/execute", tags=["Strategy"], response_model=Dict[str, Any])
async def execute_strategy(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    order_router: OrderRouter = Depends(get_order_router)
) -> Dict[str, Any]:
    """
    Execute the trading strategy.
    
    Args:
        symbol: Trading symbol
        timeframe: Candle timeframe
        order_router: Order router
        
    Returns:
        Strategy execution result
    """
    try:
        # Use default symbol and timeframe if not provided
        if not symbol:
            symbol = app.state.config.symbol
        if not timeframe:
            timeframe = app.state.config.timeframe
        
        # Execute strategy
        result = order_router.execute_strategy(symbol, timeframe)
        
        return result
    except Exception as e:
        logger.error(f"Failed to execute strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/strategy/signal", tags=["Strategy"], response_model=Signal)
async def get_strategy_signal(
    symbol: Optional[str] = None,
    order_router: OrderRouter = Depends(get_order_router)
) -> Signal:
    """
    Get the current strategy signal.
    
    Args:
        symbol: Trading symbol
        order_router: Order router
        
    Returns:
        Strategy signal
    """
    try:
        # Use default symbol if not provided
        if not symbol:
            symbol = app.state.config.symbol
        
        # Update market data
        order_router.update_market_data(symbol, app.state.config.timeframe)
        
        # Generate signal
        signal = order_router.strategy.generate_signal()
        
        # Convert to Signal model
        return Signal(
            symbol=symbol,
            action=signal.get("action", "wait"),
            side=signal.get("side"),
            size=signal.get("size"),
            entry_price=signal.get("entry_price"),
            stop_loss=signal.get("stop_loss"),
            take_profit=signal.get("take_profit"),
            reason=signal.get("reason", "unknown"),
            timestamp=int(time.time() * 1000)
        )
    except Exception as e:
        logger.error(f"Failed to get strategy signal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
