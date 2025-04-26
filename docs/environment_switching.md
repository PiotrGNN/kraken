# Environment Switching

The DeepAgent Kraken trading bot supports switching between TESTNET and MAINNET environments. This document explains how to configure and use this functionality.

## Overview

The environment switching functionality allows the bot to:

1. Start in TESTNET mode for paper trading
2. Automatically switch to MAINNET after a specified period if performance criteria are met
3. Manually switch between environments through the API or Grafana dashboard
4. Use different API keys and configurations for each environment

## Configuration

### Environment Settings

Environment settings are configured in `config/env.yaml`:

```yaml
# Current trading environment (testnet or mainnet)
environment: testnet

# Whether to automatically switch from TESTNET to MAINNET based on performance
auto_switch_enabled: true

# Duration in hours to run in TESTNET before considering switch to MAINNET
testnet_duration_hours: 48

# Minimum number of trades required before considering switch to MAINNET
min_trades_for_switch: 10

# Maximum drawdown percentage allowed for switch to MAINNET
max_drawdown_pct_for_switch: 4.0
```

### Environment Variables

You can also configure the environment using environment variables:

- `DEEPAGENT_ENV`: Current environment (`testnet` or `mainnet`)
- `DEEPAGENT_AUTO_SWITCH_ENABLED`: Whether to enable automatic switching (`true` or `false`)
- `DEEPAGENT_TESTNET_DURATION_HOURS`: Hours to run in TESTNET before considering switch
- `DEEPAGENT_MIN_TRADES_FOR_SWITCH`: Minimum trades required for switch
- `DEEPAGENT_MAX_DRAWDOWN_PCT_FOR_SWITCH`: Maximum drawdown percentage allowed for switch

### Exchange API Keys

Exchange API keys are configured separately for each environment:

- TESTNET keys: `config/testnet/<exchange>.json`
- MAINNET keys: `config/mainnet/<exchange>.json`

Example for Bybit:

```json
// config/testnet/bybit.json
{
    "api_key": "YOUR_BYBIT_TESTNET_API_KEY",
    "api_secret": "YOUR_BYBIT_TESTNET_API_SECRET"
}

// config/mainnet/bybit.json
{
    "api_key": "YOUR_BYBIT_MAINNET_API_KEY",
    "api_secret": "YOUR_BYBIT_MAINNET_API_SECRET"
}
```

## Automatic Switching

The bot will automatically switch from TESTNET to MAINNET if all of the following criteria are met:

1. The bot has been running in TESTNET for at least `testnet_duration_hours` (default: 48 hours)
2. At least `min_trades_for_switch` trades have been executed (default: 10 trades)
3. The maximum drawdown is less than `max_drawdown_pct_for_switch` (default: 4%)

The environment check runs every 5 minutes (configurable via `env_check_interval` in the main config).

## Manual Switching

### API Endpoints

You can manually switch environments using the following API endpoints:

- `GET /api/env`: Get current environment status
- `POST /api/env/testnet`: Switch to TESTNET
- `POST /api/env/mainnet`: Switch to MAINNET
- `POST /api/env/toggle`: Toggle between TESTNET and MAINNET

### Grafana Dashboard

The environment can also be switched from the Grafana dashboard:

1. Open the "DeepAgent Environment Monitor" dashboard
2. Use the "Switch to TESTNET" or "Switch to MAINNET" links in the "Environment Control" panel

## Switching Process

When switching environments, the bot will:

1. Close all open positions on the current environment
2. Update the environment setting
3. Reinitialize exchange connectors with the new environment's API keys
4. Continue trading in the new environment

## Monitoring

Environment status and performance metrics are available in:

1. The Grafana dashboard ("DeepAgent Environment Monitor")
2. Prometheus metrics:
   - `deepagent_current_env`: Current environment (0=TESTNET, 1=MAINNET)
   - `deepagent_env_switch_total`: Total number of environment switches
   - `deepagent_time_in_env_hours`: Time spent in current environment in hours

## Docker Configuration

When running with Docker, you can set the initial environment in `docker-compose.yml`:

```yaml
services:
  bot:
    environment:
      - DEEPAGENT_ENV=testnet
      - DEEPAGENT_AUTO_SWITCH_ENABLED=true
      - DEEPAGENT_TESTNET_DURATION_HOURS=48
      - DEEPAGENT_MIN_TRADES_FOR_SWITCH=10
      - DEEPAGENT_MAX_DRAWDOWN_PCT_FOR_SWITCH=4.0
```
