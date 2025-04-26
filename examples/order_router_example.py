"""
Example script demonstrating how to use the OrderRouter.
"""
import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Import the OrderRouter
from app.core.order_router import OrderRouter

async def main():
    """Main function demonstrating OrderRouter usage"""
    # Create OrderRouter with Bybit V5 as primary and OKX and Binance as failovers
    router = OrderRouter(
        primary_exchange="bybit_v5",
        failover_exchanges=["okx", "binance"],
        health_check_interval=30,  # Check exchange health every 30 seconds
        max_retry_attempts=3,      # Try 3 times before failing over
        retry_delay=5,             # Wait 5 seconds between retries
        auto_failover=True         # Automatically failover when primary is down
    )
    
    # Initialize the router
    await router.initialize()
    
    try:
        # Get router status
        status = router.get_status()
        print(f"Router Status: {status}")
        
        # Get account balance
        balance = router.get_account_balance()
        print(f"Account Balance: {balance}")
        
        # Get market data for BTC/USDT
        market_data = router.get_market_data("BTCUSDT")
        print(f"BTC/USDT Market Data: {market_data}")
        
        # Place a limit order
        order = router.place_order(
            symbol="BTCUSDT",
            side="Buy",
            order_type="Limit",
            qty="0.001",
            price="25000",  # Limit price
            time_in_force="GoodTillCancel",
            reduce_only=False,
            take_profit="30000",
            stop_loss="24000"
        )
        print(f"Placed Order: {order}")
        
        # Get open orders
        open_orders = router.get_open_orders(symbol="BTCUSDT")
        print(f"Open Orders: {open_orders}")
        
        # Cancel the order
        if "orderId" in order:
            cancel_result = router.cancel_order(
                symbol="BTCUSDT",
                order_id=order["orderId"]
            )
            print(f"Cancel Result: {cancel_result}")
        
        # Manually failover to OKX
        print("Manually failing over to OKX...")
        router.manual_failover("okx")
        
        # Get router status after failover
        status = router.get_status()
        print(f"Router Status after failover: {status}")
        
        # Get failover history
        history = router.get_failover_history()
        print(f"Failover History: {history}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        # Clean up
        router.stop_health_check_thread()
        print("OrderRouter example completed")

if __name__ == "__main__":
    asyncio.run(main())
