# Simplified Trading Bot

A Python-based trading bot for Binance Futures Testnet that supports market and limit orders with intelligent error handling and comprehensive logging.

## 🚀 Features

- **Order Types**: Market and limit orders for both buy and sell sides
- **Intelligent Error Handling**: Exponential backoff retry logic with error categorization
- **Decimal Precision**: Financial-grade precision using Python's Decimal library
- **Comprehensive Logging**: Structured JSON logging with multiple output destinations
- **Input Validation**: Thorough validation of symbols, quantities, prices, and account balance
- **CLI Interface**: Both interactive and batch modes supported
- **Strategy Pattern**: Extensible architecture for adding new order types
- **Testnet Safe**: Built specifically for Binance Futures Testnet environment

## 📋 Requirements

- Python 3.8+
- Binance Futures Testnet account with API credentials
- Internet connection for API calls

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd trading-bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   export BINANCE_API_KEY="your_futures_testnet_api_key"
   export BINANCE_API_SECRET="your_futures_testnet_api_secret"
   ```

   Or create a `.env` file:
   ```
   BINANCE_API_KEY=your_futures_testnet_api_key
   BINANCE_API_SECRET=your_futures_testnet_api_secret
   ```

## 🎯 Getting Testnet API Keys

1. Visit [Binance Futures Testnet](https://testnet.binancefuture.com/)
2. Register and login
3. Go to API Management
4. Create new API key with permissions:
   - ✅ **TRADE** (Can place/cancel orders)
   - ✅ **USER_DATA** (Can view account information)
   - ✅ **USER_STREAM** (Can manage listen keys)

## 🖥️ Usage

### Interactive Mode (Recommended for beginners)
```bash
python main.py
```
The bot will guide you through each step with prompts.

### Batch Mode (For automation)

**Market Order:**
```bash
python main.py --symbol BTCUSDT --side buy --quantity 0.001 --type market
```

**Limit Order:**
```bash
python main.py --symbol ETHUSDT --side sell --quantity 0.1 --type limit --price 2500.50
```

### Command Line Options

| Option | Description | Required | Example |
|--------|-------------|----------|---------|
| `--symbol` | Trading pair | Yes* | `BTCUSDT` |
| `--side` | Order side | Yes* | `buy` or `sell` |
| `--quantity` | Order quantity | Yes* | `0.001` |
| `--type` | Order type | Yes* | `market` or `limit` |
| `--price` | Price (limit orders only) | For limit | `50000.50` |
| `--interactive` | Force interactive mode | No | - |
| `--testnet` | Use testnet (default: true) | No | - |

*Required for batch mode only

## 📁 Project Structure

```
trading-bot/
├── main.py                 # Entry point
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── bot/                   # Core bot components
│   ├── __init__.py
│   ├── cli.py            # Command line interface
│   ├── validator.py      # Input validation
│   ├── api_client.py     # Binance API wrapper
│   ├── error_handler.py  # Retry logic and error handling
│   └── logger.py         # Logging configuration
│
├── strategies/           # Trading strategies (Strategy Pattern)
│   ├── __init__.py
│   ├── base.py          # Abstract base strategy
│   ├── market_order.py  # Market order implementation
│   ├── limit_order.py   # Limit order implementation
│   └── factory.py       # Strategy factory
│
├── tests/               # Unit tests
│   ├── __init__.py
│   ├── test_validator.py
│   ├── test_strategies.py
│   └── test_api_client.py
│
└── logs/                # Log files (auto-created)
    ├── trading_bot.log  # All events (JSON)
    ├── errors.log       # Errors only (JSON)
    └── api_calls.log    # API interactions (JSON)
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BINANCE_API_KEY` | Your Binance Futures Testnet API Key | None | Yes |
| `BINANCE_API_SECRET` | Your Binance Futures Testnet API Secret | None | Yes |

### Retry Configuration

The bot uses intelligent retry logic:
- **Network errors**: 3 retries with exponential backoff (1s, 2s, 4s)
- **Rate limiting**: Longer delays with max 5-minute wait
- **Business logic errors**: No retries (fail immediately)

## 📊 Logging

The bot creates comprehensive logs in multiple formats:

### Log Files

- **`trading_bot.log`**: All events in structured JSON format
- **`errors.log`**: Only warnings and errors
- **`api_calls.log`**: All API interactions with performance metrics

### Console Output

Human-readable format for development:
```
10:30:15 | INFO     | bot.api_client      | Order placed successfully
10:30:16 | WARNING  | bot.error_handler   | Retrying operation in 2.0 seconds
```

## 🛡️ Error Handling

The bot categorizes and handles errors intelligently:

| Error Type | Action | Examples |
|------------|--------|----------|
| **Network Issues** | Retry with backoff | Connection timeouts, DNS failures |
| **Rate Limiting** | Retry with longer delays | HTTP 429 errors |
| **Business Logic** | Fail immediately | Insufficient balance, invalid symbol |
| **Authentication** | Fail immediately | Invalid API keys |

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Run specific test:
```bash
python -m pytest tests/test_validator.py -v
```

## 🔍 Troubleshooting

### Common Issues

**Authentication Error (-2015)**
```
APIError(code=-2015): Invalid API-key, IP, or permissions for action
```
- ✅ Check API key and secret are correct
- ✅ Ensure keys are for Futures Testnet (not Spot)
- ✅ Verify API key permissions include TRADE and USER_DATA

**Insufficient Balance**
```
ValidationError: Insufficient balance. Required: 50.00 USDT, Available: 0.00 USDT
```
- ✅ Add funds to your Futures Testnet account
- ✅ Check you're using the correct symbol (USDT-M futures)

**Invalid Symbol**
```
ValidationError: Symbol 'INVALID' is not available on Binance Futures
```
- ✅ Use valid futures symbols (e.g., BTCUSDT, ETHUSDT)
- ✅ Check symbol exists on Binance Futures Testnet

**Network Connection Issues**
```
APIConnectionError: Connection test failed
```
- ✅ Check internet connection
- ✅ Verify testnet.binancefuture.com is accessible
- ✅ Check firewall settings

## 🔄 Architecture

The bot uses several design patterns for maintainability:

- **Strategy Pattern**: Easy to add new order types
- **Decorator Pattern**: Clean retry logic separation
- **Factory Pattern**: Centralized strategy creation
- **Observer Pattern**: Comprehensive logging throughout

## 🚀 Extending the Bot

### Adding New Order Types

1. Create new strategy class in `strategies/`:
```python
class StopLimitOrderStrategy(OrderStrategy):
    # Implement abstract methods
    pass
```

2. Register in factory:
```python
_strategies = {
    'market': MarketOrderStrategy,
    'limit': LimitOrderStrategy,
    'stop_limit': StopLimitOrderStrategy,  # Add here
}
```

### Custom Error Handling

Extend the `ErrorHandler` class:
```python
class CustomErrorHandler(ErrorHandler):
    def _categorize_error(self, error):
        # Custom error categorization logic
        return super()._categorize_error(error)
```

## 📜 License

This project is created for educational purposes as part of a take-home assignment.

## 🤝 Contributing

This is a take-home assignment project. However, if you find bugs or have suggestions:
1. Open an issue describing the problem
2. If you have a fix, create a pull request with clear description

## 📞 Support

For questions about this implementation:
- Check the troubleshooting section above
- Review the comprehensive logging in `logs/` directory
- Examine the error messages - they're designed to be helpful

## 🎯 Assignment Requirements Checklist

- ✅ **Language**: Python
- ✅ **Exchange**: Binance Futures Testnet
- ✅ **Order Types**: Market and limit orders
- ✅ **Sides**: Both buy and sell supported
- ✅ **API**: Official Binance API (python-binance library)
- ✅ **CLI**: Command-line interface with validation
- ✅ **Output**: Order details and execution status
- ✅ **Logging**: Comprehensive request/response/error logging
- ✅ **Error Handling**: Intelligent retry logic and categorization
- ✅ **Code Structure**: Reusable, clean architecture

## 📈 Future Enhancements

Potential improvements for production use:
- WebSocket integration for real-time data
- Portfolio management features
- Advanced order types (OCO, TWAP, etc.)
- Risk management rules
- Performance analytics dashboard
- Database integration for trade history