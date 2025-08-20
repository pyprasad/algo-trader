# Development Guide

## Development Environment Setup

### Prerequisites
- Python 3.8+
- Git
- Virtual environment
- IDE (PyCharm, VSCode recommended)
- MongoDB (local or Docker)

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/algo-trader.git
cd algo-trader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Set up environment variables
cp .env.example .env.development
# Edit .env.development with your settings
```

### Development Dependencies

```txt
# requirements-dev.txt
-r requirements.txt

# Testing
pytest==7.4.0
pytest-asyncio==0.21.0
pytest-cov==4.1.0
pytest-mock==3.11.1

# Code Quality
black==23.7.0
flake8==6.0.0
mypy==1.4.1
pylint==2.17.4
isort==5.12.0

# Development Tools
ipython==8.14.0
jupyter==1.0.0
pre-commit==3.3.3

# Documentation
sphinx==7.0.1
sphinx-rtd-theme==1.2.2

# Profiling
memory-profiler==0.61.0
line-profiler==4.0.3
```

## Project Structure

### Directory Organization

```
algo-trader/
├── core/                   # Core trading functionality
│   ├── __init__.py
│   ├── base/              # Base classes and interfaces
│   │   ├── base_strategy.py
│   │   ├── base_indicator.py
│   │   └── base_service.py
│   ├── data_collector.py
│   ├── ig_service.py
│   ├── risk_manager.py
│   ├── signal_analyzer.py
│   ├── strategy_engine.py
│   └── trade_executor.py
│
├── ml/                     # Machine learning components
│   ├── __init__.py
│   ├── models/            # ML model implementations
│   ├── features/          # Feature engineering
│   └── training/          # Training pipelines
│
├── strategies/             # Trading strategies
│   ├── __init__.py
│   ├── base_strategy.py
│   ├── enhanced_strategy.py
│   └── custom/            # Custom strategy implementations
│
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── database_handler.py
│   ├── logger.py
│   └── helpers.py
│
├── tests/                  # Test suites
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/                # Utility scripts
│   ├── setup/
│   ├── maintenance/
│   └── analysis/
│
└── docs/                   # Documentation
    ├── api/
    ├── guides/
    └── examples/
```

## Code Standards

### Python Style Guide

Follow PEP 8 with these additions:
- Line length: 88 characters (Black default)
- Use type hints for all functions
- Docstrings for all public methods

```python
from typing import List, Dict, Optional, Tuple
import numpy as np

class SignalAnalyzer:
    """Analyzes market signals for trading decisions.
    
    This class processes technical indicators and generates
    trading signals based on configured strategies.
    """
    
    def calculate_rsi(
        self,
        prices: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """Calculate Relative Strength Index.
        
        Args:
            prices: Array of closing prices
            period: RSI period (default: 14)
            
        Returns:
            Array of RSI values
            
        Raises:
            ValueError: If prices array is too short
        """
        if len(prices) < period + 1:
            raise ValueError(f"Need at least {period + 1} prices")
            
        # Implementation here
        return rsi_values
```

### Code Formatting

Use Black for automatic formatting:
```bash
# Format single file
black core/signal_analyzer.py

# Format entire project
black .

# Check formatting without changing
black --check .
```

### Import Organization

Use isort for import organization:
```python
# Standard library imports
import os
import sys
from datetime import datetime
from typing import Dict, List

# Third-party imports
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# Local imports
from core.base import BaseStrategy
from utils.logger import get_logger
```

## Adding New Features

### Creating a New Strategy

1. **Create Strategy Class**
```python
# strategies/momentum_strategy.py
from strategies.base_strategy import BaseStrategy
from typing import Dict, Any

class MomentumStrategy(BaseStrategy):
    """Momentum-based trading strategy."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lookback_period = config.get('lookback_period', 20)
        
    def generate_signal(self, market_data: Dict) -> float:
        """Generate trading signal based on momentum.
        
        Returns:
            Signal strength between -1 (strong sell) and 1 (strong buy)
        """
        # Calculate momentum
        momentum = self._calculate_momentum(market_data)
        
        # Generate signal
        if momentum > self.config['buy_threshold']:
            return 1.0
        elif momentum < self.config['sell_threshold']:
            return -1.0
        else:
            return 0.0
            
    def _calculate_momentum(self, market_data: Dict) -> float:
        """Calculate price momentum."""
        prices = market_data['prices']
        return (prices[-1] - prices[-self.lookback_period]) / prices[-self.lookback_period]
```

2. **Register Strategy**
```python
# core/strategy_engine.py
from strategies.momentum_strategy import MomentumStrategy

AVAILABLE_STRATEGIES = {
    'enhanced_multi_signal': EnhancedStrategy,
    'momentum': MomentumStrategy,  # Add new strategy
    # ... other strategies
}
```

3. **Add Configuration**
```yaml
# configs/strategies/momentum.yaml
strategy:
  type: momentum
  lookback_period: 20
  buy_threshold: 0.05
  sell_threshold: -0.05
  position_size: 1.0
```

### Adding a New Indicator

1. **Create Indicator Module**
```python
# core/indicators/vwap.py
import numpy as np
from typing import Tuple

def calculate_vwap(
    prices: np.ndarray,
    volumes: np.ndarray,
    period: int = 20
) -> np.ndarray:
    """Calculate Volume Weighted Average Price.
    
    Args:
        prices: Array of prices
        volumes: Array of volumes
        period: Calculation period
        
    Returns:
        Array of VWAP values
    """
    cumsum_pv = np.cumsum(prices * volumes)
    cumsum_v = np.cumsum(volumes)
    
    vwap = cumsum_pv / cumsum_v
    
    # Apply rolling window
    if period:
        vwap = pd.Series(vwap).rolling(period).mean().values
        
    return vwap
```

2. **Integrate into Signal Analyzer**
```python
# core/signal_analyzer.py
from core.indicators.vwap import calculate_vwap

class SignalAnalyzer:
    def analyze(self, market_data: Dict) -> Dict[str, float]:
        signals = {}
        
        # Existing indicators
        signals['rsi'] = self.calculate_rsi(market_data['prices'])
        signals['macd'] = self.calculate_macd(market_data['prices'])
        
        # Add new indicator
        signals['vwap'] = calculate_vwap(
            market_data['prices'],
            market_data['volumes']
        )
        
        return signals
```

### Adding a New Data Source

1. **Create Data Source Adapter**
```python
# core/data_sources/binance_adapter.py
from typing import Dict, List
import ccxt

class BinanceAdapter:
    """Adapter for Binance exchange data."""
    
    def __init__(self, api_key: str, api_secret: str):
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
        })
        
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '5m',
        limit: int = 100
    ) -> List[Dict]:
        """Fetch OHLCV data from Binance."""
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        return [
            {
                'timestamp': candle[0],
                'open': candle[1],
                'high': candle[2],
                'low': candle[3],
                'close': candle[4],
                'volume': candle[5]
            }
            for candle in ohlcv
        ]
        
    def stream_ticker(self, symbol: str):
        """Stream real-time ticker data."""
        # WebSocket streaming implementation
        pass
```

2. **Register Data Source**
```python
# core/data_collector.py
from core.data_sources.binance_adapter import BinanceAdapter

class DataCollector:
    def __init__(self, config: Dict):
        self.sources = {}
        
        # Existing sources
        if config.get('ig_markets'):
            self.sources['ig'] = IGMarketsAdapter(config['ig_markets'])
            
        # Add new source
        if config.get('binance'):
            self.sources['binance'] = BinanceAdapter(
                config['binance']['api_key'],
                config['binance']['api_secret']
            )
```

## Testing

### Unit Testing

```python
# tests/unit/test_signal_analyzer.py
import pytest
import numpy as np
from core.signal_analyzer import SignalAnalyzer

class TestSignalAnalyzer:
    @pytest.fixture
    def analyzer(self):
        """Create signal analyzer instance."""
        return SignalAnalyzer()
        
    def test_calculate_rsi(self, analyzer):
        """Test RSI calculation."""
        prices = np.array([100, 102, 101, 103, 102, 104, 103, 105])
        rsi = analyzer.calculate_rsi(prices, period=3)
        
        assert len(rsi) == len(prices)
        assert 0 <= rsi[-1] <= 100
        
    def test_calculate_rsi_insufficient_data(self, analyzer):
        """Test RSI with insufficient data."""
        prices = np.array([100, 102])
        
        with pytest.raises(ValueError):
            analyzer.calculate_rsi(prices, period=14)
            
    @pytest.mark.parametrize("period,expected_range", [
        (7, (30, 70)),
        (14, (20, 80)),
        (21, (10, 90)),
    ])
    def test_rsi_periods(self, analyzer, period, expected_range):
        """Test RSI with different periods."""
        prices = np.random.uniform(90, 110, 100)
        rsi = analyzer.calculate_rsi(prices, period=period)
        
        assert expected_range[0] <= np.mean(rsi) <= expected_range[1]
```

### Integration Testing

```python
# tests/integration/test_trading_flow.py
import pytest
from unittest.mock import Mock, patch
from core.strategy_engine import StrategyEngine
from core.trade_executor import TradeExecutor

class TestTradingFlow:
    @pytest.fixture
    def mock_ig_service(self):
        """Mock IG Markets service."""
        mock = Mock()
        mock.get_market_data.return_value = {
            'bid': 7500.0,
            'ask': 7501.0,
            'status': 'TRADEABLE'
        }
        return mock
        
    def test_complete_trade_flow(self, mock_ig_service):
        """Test complete trading flow from signal to execution."""
        # Setup
        strategy = StrategyEngine(config={'type': 'test'})
        executor = TradeExecutor(ig_service=mock_ig_service)
        
        # Generate signal
        market_data = {'prices': [7500, 7502, 7505]}
        signal = strategy.generate_signal(market_data)
        
        # Execute trade
        if signal > 0.6:
            order = executor.open_position(
                market='FTSE_100',
                direction='BUY',
                size=1.0
            )
            
        # Verify
        assert order is not None
        mock_ig_service.open_position.assert_called_once()
```

### Performance Testing

```python
# tests/performance/test_throughput.py
import time
import pytest
from core.data_collector import DataCollector

def test_data_processing_throughput():
    """Test data processing throughput."""
    collector = DataCollector()
    
    # Generate test data
    test_data = generate_test_ticks(10000)
    
    start_time = time.time()
    for tick in test_data:
        collector.process_tick(tick)
    elapsed = time.time() - start_time
    
    throughput = len(test_data) / elapsed
    assert throughput > 1000  # Should process >1000 ticks/second
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov-report=html

# Run specific test file
pytest tests/unit/test_signal_analyzer.py

# Run with verbose output
pytest -v

# Run only marked tests
pytest -m "not slow"

# Run in parallel
pytest -n 4
```

## Debugging

### Debug Configuration

```python
# utils/debug.py
import logging
from functools import wraps

def debug_trace(func):
    """Decorator for debug tracing."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Entering {func.__name__}")
        logger.debug(f"Args: {args}, Kwargs: {kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
        finally:
            logger.debug(f"Exiting {func.__name__}")
            
    return wrapper
```

### Using Debugger

```python
# VSCode launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Algo Trader",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/runners/run_multi_market.py",
            "args": ["--demo", "--duration", "300"],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "LOG_LEVEL": "DEBUG"
            }
        }
    ]
}
```

### Profiling

```python
# Profile specific function
from line_profiler import LineProfiler

def profile_function():
    lp = LineProfiler()
    lp_wrapper = lp(signal_analyzer.analyze)
    lp_wrapper(market_data)
    lp.print_stats()

# Memory profiling
from memory_profiler import profile

@profile
def memory_intensive_function():
    # Function implementation
    pass
```

## API Development

### Creating REST API Endpoints

```python
# api/app.py
from flask import Flask, jsonify, request
from flask_restful import Api, Resource

app = Flask(__name__)
api = Api(app)

class PositionsResource(Resource):
    def get(self):
        """Get all open positions."""
        positions = trade_executor.get_positions()
        return jsonify(positions)
        
    def post(self):
        """Open new position."""
        data = request.get_json()
        position = trade_executor.open_position(
            market=data['market'],
            direction=data['direction'],
            size=data['size']
        )
        return jsonify(position), 201

api.add_resource(PositionsResource, '/api/positions')

if __name__ == '__main__':
    app.run(debug=True)
```

### WebSocket Implementation

```python
# api/websocket_server.py
import asyncio
import websockets
import json

async def handle_client(websocket, path):
    """Handle WebSocket client connections."""
    try:
        # Subscribe client to updates
        await register_client(websocket)
        
        # Send real-time updates
        while True:
            data = await get_market_update()
            await websocket.send(json.dumps(data))
            
    except websockets.exceptions.ConnectionClosed:
        await unregister_client(websocket)

async def start_websocket_server():
    """Start WebSocket server."""
    async with websockets.serve(handle_client, "localhost", 8765):
        await asyncio.Future()  # Run forever
```

## Documentation

### Generating Documentation

```bash
# Generate Sphinx documentation
cd docs
sphinx-quickstart
sphinx-apidoc -o source ../core
make html
```

### Docstring Format

```python
def calculate_position_size(
    account_balance: float,
    risk_percentage: float,
    stop_distance: float,
    point_value: float = 1.0
) -> float:
    """Calculate optimal position size using risk management rules.
    
    Uses the percentage risk method to determine position size
    based on account balance and stop loss distance.
    
    Args:
        account_balance: Current account balance in base currency
        risk_percentage: Maximum risk per trade (e.g., 0.02 for 2%)
        stop_distance: Distance to stop loss in points
        point_value: Value per point movement (default: 1.0)
        
    Returns:
        Calculated position size in lots
        
    Raises:
        ValueError: If any parameter is negative
        ZeroDivisionError: If stop_distance is zero
        
    Example:
        >>> size = calculate_position_size(10000, 0.02, 50, 1.0)
        >>> print(f"Position size: {size} lots")
        Position size: 4.0 lots
        
    Note:
        The calculated size is automatically rounded down to ensure
        risk doesn't exceed the specified percentage.
    """
    if account_balance < 0 or risk_percentage < 0 or stop_distance <= 0:
        raise ValueError("Parameters must be positive")
        
    risk_amount = account_balance * risk_percentage
    position_size = risk_amount / (stop_distance * point_value)
    
    return math.floor(position_size * 100) / 100  # Round down
```

## Version Control

### Git Workflow

```bash
# Feature branch workflow
git checkout -b feature/new-indicator
git add .
git commit -m "feat: Add VWAP indicator"
git push origin feature/new-indicator

# Create pull request for review
```

### Commit Message Convention

Follow Conventional Commits:
```
feat: Add new feature
fix: Fix bug
docs: Update documentation
style: Code style changes
refactor: Code refactoring
test: Add tests
chore: Maintenance tasks
```

## Deployment

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        
    - name: Run tests
      run: pytest --cov=core
      
    - name: Run linting
      run: |
        black --check .
        flake8 .
        mypy core/
        
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

### Release Process

```bash
# 1. Update version
bumpversion minor  # or major, patch

# 2. Update changelog
git add CHANGELOG.md
git commit -m "docs: Update changelog for v1.2.0"

# 3. Create tag
git tag -a v1.2.0 -m "Release version 1.2.0"

# 4. Push to repository
git push origin main --tags

# 5. Create release
gh release create v1.2.0 --title "Release v1.2.0" --notes-file CHANGELOG.md
```

## Contributing

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

### Code Review Guidelines

1. Check for correctness
2. Verify test coverage
3. Review documentation
4. Ensure code style compliance
5. Check for security issues
6. Verify performance impact