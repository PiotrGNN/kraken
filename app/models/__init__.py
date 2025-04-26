"""
Data models for the DeepAgent Kraken trading bot.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    """Order side enum."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enum."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT_MARKET = "take_profit_market"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class OrderStatus(str, Enum):
    """Order status enum."""
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(str, Enum):
    """Position side enum."""
    LONG = "long"
    SHORT = "short"


class TimeInForce(str, Enum):
    """Time in force enum."""
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    GTX = "GTX"  # Good Till Crossing


class Order(BaseModel):
    """Order model."""
    id: str
    client_order_id: Optional[str] = None
    exchange: str
    symbol: str
    side: OrderSide
    type: OrderType
    price: Optional[float] = None
    quantity: float
    executed_quantity: float = 0
    status: OrderStatus
    time_in_force: Optional[TimeInForce] = None
    reduce_only: bool = False
    post_only: bool = False
    stop_price: Optional[float] = None
    created_at: int  # Unix timestamp in milliseconds
    updated_at: Optional[int] = None  # Unix timestamp in milliseconds


class Position(BaseModel):
    """Position model."""
    exchange: str
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    mark_price: float
    liquidation_price: Optional[float] = None
    unrealized_pnl: float
    realized_pnl: float
    margin: float
    leverage: float
    created_at: int  # Unix timestamp in milliseconds
    updated_at: int  # Unix timestamp in milliseconds


class Balance(BaseModel):
    """Balance model."""
    exchange: str
    asset: str
    free: float
    used: float
    total: float


class AccountInfo(BaseModel):
    """Account information model."""
    exchange: str
    balances: List[Balance]
    positions: List[Position]
    equity: float
    available_margin: float
    used_margin: float
    total_margin: float
    unrealized_pnl: float
    realized_pnl: float


class Candle(BaseModel):
    """Candle model."""
    timestamp: int  # Unix timestamp in milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float


class Signal(BaseModel):
    """Trading signal model."""
    symbol: str
    action: str  # 'open', 'close', 'update_stop', 'wait', 'hold'
    side: Optional[PositionSide] = None
    size: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str
    timestamp: int  # Unix timestamp in milliseconds


class OrderRequest(BaseModel):
    """Order request model."""
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: Optional[TimeInForce] = None
    reduce_only: bool = False
    post_only: bool = False
    client_order_id: Optional[str] = None


class OrderResponse(BaseModel):
    """Order response model."""
    status: str  # 'success' or 'error'
    message: Optional[str] = None
    order: Optional[Order] = None
    error_code: Optional[str] = None


class StrategyConfig(BaseModel):
    """Strategy configuration model."""
    name: str
    symbol: str
    timeframe: str
    equity: float = 10000.0
    risk_pct: float = 0.01
    parameters: Dict[str, Any] = Field(default_factory=dict)


class RiskConfig(BaseModel):
    """Risk management configuration model."""
    risk_pct: float = 0.01
    atr_multiplier: float = 1.5
    trailing_breakeven_atr: float = 1.0
    trailing_step_atr: float = 0.5
    max_drawdown_pct: float = 0.1
    max_position_size_pct: float = 0.2


class ExchangeConfig(BaseModel):
    """Exchange configuration model."""
    name: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    testnet: bool = False
    timeout: int = 10000  # Milliseconds


class MonitoringConfig(BaseModel):
    """Monitoring configuration model."""
    enabled: bool = True
    log_level: str = "INFO"
    metrics_port: int = 8000


class BotConfig(BaseModel):
    """Bot configuration model."""
    symbol: str
    timeframe: str
    primary_exchange: str
    exchanges: List[ExchangeConfig]
    strategy: StrategyConfig
    risk: RiskConfig
    monitoring: MonitoringConfig
