import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class Config:
    """
    Configuration management for the trading bot.
    Loads settings from environment variables and provides defaults.
    """
    
    def __init__(self):
        # Load .env file
        self._load_environment()
        
        # API Configuration
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        
        if not self.api_key or not self.api_secret:
            raise ValueError(
                "API credentials not found. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
            )
        
        # Trading Configuration
        self.testnet = True  # Always use testnet for safety
        self.base_url = 'https://testnet.binancefuture.com'
        
        # Logging Configuration
        self.log_directory = "logs"
        self.console_log_level = "INFO"
        self.file_log_level = "DEBUG"
        
    def _load_environment(self):
        """Load environment variables from .env file."""
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Also try looking in parent directory
            parent_env = Path('..') / '.env'
            if parent_env.exists():
                load_dotenv(parent_env)
    
    def get_api_credentials(self) -> Dict[str, str]:
        """Get API credentials."""
        return {
            'api_key': self.api_key,
            'api_secret': self.api_secret
        }
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration."""
        return {
            'testnet': self.testnet,
            'base_url': self.base_url
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            'log_directory': self.log_directory,
            'console_level': self.console_log_level,
            'file_level': self.file_log_level
        }