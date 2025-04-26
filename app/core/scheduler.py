"""
Scheduler for periodic tasks in the DeepAgent Kraken trading bot.

This module provides functionality to schedule periodic tasks such as checking
if the environment should be switched based on performance criteria.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, Coroutine
import threading

from app.core.env_manager import get_env_manager, Environment

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Scheduler for periodic tasks.
    """
    
    def __init__(self):
        """Initialize the task scheduler."""
        self.tasks = {}
        self.running = False
        self.scheduler_thread = None
        self.loop = None
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._run_scheduler,
            daemon=True
        )
        self.scheduler_thread.start()
        logger.info("Task scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Task scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            for task_name, task_info in self.tasks.items():
                self.loop.create_task(self._run_periodic_task(
                    task_name,
                    task_info['func'],
                    task_info['interval'],
                    task_info['args'],
                    task_info['kwargs']
                ))
            
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
        finally:
            self.loop.close()
    
    async def _run_periodic_task(self, task_name: str, func: Callable, interval: int,
                                args: tuple, kwargs: Dict[str, Any]):
        """
        Run a periodic task.
        
        Args:
            task_name: Name of the task
            func: Function to run
            interval: Interval in seconds
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        """
        while self.running:
            try:
                logger.debug(f"Running scheduled task: {task_name}")
                await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error running scheduled task {task_name}: {e}")
            
            await asyncio.sleep(interval)
    
    def add_task(self, task_name: str, func: Callable, interval: int,
                args: tuple = (), kwargs: Dict[str, Any] = None):
        """
        Add a task to the scheduler.
        
        Args:
            task_name: Name of the task
            func: Function to run
            interval: Interval in seconds
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        """
        if kwargs is None:
            kwargs = {}
        
        self.tasks[task_name] = {
            'func': func,
            'interval': interval,
            'args': args,
            'kwargs': kwargs
        }
        
        logger.info(f"Added scheduled task: {task_name} (interval: {interval}s)")
    
    def remove_task(self, task_name: str):
        """
        Remove a task from the scheduler.
        
        Args:
            task_name: Name of the task to remove
        """
        if task_name in self.tasks:
            del self.tasks[task_name]
            logger.info(f"Removed scheduled task: {task_name}")


# Global scheduler instance
_scheduler = None


def get_scheduler() -> TaskScheduler:
    """
    Get the global scheduler instance.
    
    Returns:
        Global scheduler instance
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = TaskScheduler()
    
    return _scheduler


async def check_environment_switch(order_router):
    """
    Check if the environment should be switched based on performance criteria.
    
    Args:
        order_router: Order router instance
    """
    # Update performance metrics
    order_router.update_performance_metrics()
    
    # Check if we should switch environment
    env_manager = get_env_manager()
    if env_manager.should_switch_to_mainnet():
        logger.info("Performance criteria met for switching to MAINNET")
        await order_router.handle_env_change(Environment.MAINNET)


def setup_environment_check_task(order_router, interval: int = 300):
    """
    Set up a periodic task to check if the environment should be switched.
    
    Args:
        order_router: Order router instance
        interval: Check interval in seconds (default: 5 minutes)
    """
    scheduler = get_scheduler()
    scheduler.add_task(
        task_name="check_environment_switch",
        func=check_environment_switch,
        interval=interval,
        args=(order_router,)
    )
    scheduler.start()
