# DeepAgent Kraken Trading Bot

A robust cryptocurrency trading bot with multi-exchange support and failover capabilities.

## Features

- **Multi-Exchange Support**: Integrated with Bybit V5, OKX, and Binance
- **Failover Logic**: Automatically switches to backup exchanges if the primary exchange fails
- **Trend-Following Strategy**: Uses SMA-50/SMA-200 cross for trend direction with RSI filter
- **Risk Management**: ATR-based position sizing and stop-loss calculation
- **Trailing Stop**: Moves stop-loss to breakeven after +1 ATR, then trails by 0.5 ATR

## Strategy Details

The implemented trading strategy is a trend-follower with RSI counter:

- **Direction**: SMA-50 / SMA-200 cross determines trend direction
- **Long Entry**: Only when SMA50 > SMA200 and RSI-14 < 65
- **Short Entry**: Only when SMA50 < SMA200 and RSI-14 > 35

### Risk Management

1. **Position Sizing**: equity × 1% / (ATR14 × 1.5)
2. **Stop-Loss**: 1.5 × ATR (server-side)
3. **Trailing-stop**: Move to breakeven after +1 ATR, then step by 0.5 ATR

## Project Structure

```
deepagent_kraken/
├── app/                  # Main application code
│   ├── api/              # FastAPI routes
│   ├── connectors/       # Exchange connectors
│   │   ├── bybit/        # Bybit connector implementation
│   │   ├── okx/          # OKX connector implementation
│   │   ├── binance/      # Binance connector implementation
│   │   └── connector_factory.py  # Factory for creating exchange connectors
│   ├── core/             # Core bot functionality
│   │   └── order_router.py  # Order router with failover logic
│   ├── models/           # Data models
│   ├── strategies/       # Trading strategies
│   │   ├── indicators.py  # Technical indicators implementation
│   │   └── trend_rsi_strategy.py  # Trend-follower strategy with RSI counter
│   ├── risk/             # Risk management components
│   │   └── atr_risk.py   # ATR-based risk management
│   ├── utils/            # Utility functions
│   └── monitoring/       # Monitoring configuration
├── config/               # Configuration files
│   └── config.json       # Sample configuration
├── docs/                 # Documentation
├── tests/                # Test files
│   └── test_strategy.py  # Unit tests for the strategy
├── main.py               # Main entry point
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
└── requirements.txt      # Python dependencies
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/PiotrGNN/kraken.git
   cd kraken
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure the bot:
   - Copy `config/config.json` to `config/config_local.json`
   - Edit `config_local.json` with your API keys and settings

## Usage

Run the bot with default settings:
```
python main.py
```

Specify a custom configuration file:
```
python main.py --config config/config_local.json
```

Set a custom execution interval (in seconds):
```
python main.py --interval 300
```

## Testing

Run the unit tests:
```
pytest
```

## Docker Deployment

Build and run with Docker Compose:
```
docker-compose up -d
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
