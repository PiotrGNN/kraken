"""
Unit tests for configuration settings
"""
import pytest
from app.core.config import Settings, Environment

def test_default_settings():
    """Test default settings values"""
    settings = Settings()
    assert settings.ENVIRONMENT == Environment.TESTNET
    assert settings.DEBUG is False
    assert settings.API_HOST == "0.0.0.0"
    assert settings.API_PORT == 8000

def test_environment_enum():
    """Test environment enum values"""
    assert Environment.TESTNET == "testnet"
    assert Environment.MAINNET == "mainnet"
