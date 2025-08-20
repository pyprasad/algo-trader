# Installation Guide

## Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows 10+
- **Python**: 3.8 or higher
- **MongoDB**: 4.0 or higher
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 20GB free space
- **Network**: Stable broadband connection

### Required Accounts
- **IG Markets Account**: Demo or Live trading account
- **Alpha Vantage API Key**: Free tier sufficient (optional for sentiment)
- **MongoDB Atlas** (optional): For cloud database

## Step-by-Step Installation

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/algo-trader.git
cd algo-trader

# Create a virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 2. Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt

# If requirements.txt doesn't exist, install manually:
pip install pandas numpy scikit-learn
pip install pymongo motor
pip install requests aiohttp
pip install lightstreamer-client
pip install pyyaml python-dotenv
pip install textblob nltk
pip install matplotlib seaborn
pip install pytest pytest-asyncio
```

### 3. Install MongoDB

#### Option A: Local Installation

**Linux (Ubuntu/Debian):**
```bash
# Import MongoDB public GPG key
wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | sudo apt-key add -

# Create list file
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/5.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-5.0.list

# Update and install
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

**macOS:**
```bash
# Using Homebrew
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB
brew services start mongodb-community
```

**Windows:**
1. Download MongoDB installer from https://www.mongodb.com/try/download/community
2. Run the installer with default settings
3. MongoDB will start automatically as a Windows service

#### Option B: MongoDB Atlas (Cloud)
1. Create account at https://www.mongodb.com/cloud/atlas
2. Create a free cluster
3. Get connection string
4. Update `configs/database_config.yaml` with connection string

### 4. Configure IG Markets API

#### Get API Credentials
1. Sign up for IG Markets account:
   - Demo: https://www.ig.com/uk/demo-account
   - Live: https://www.ig.com/uk/trading-account
2. Log into your account
3. Navigate to Settings → API
4. Generate API key

#### Configure Credentials
```bash
# Copy template configuration
cp configs/ig_config_template.yaml configs/ig_config.yaml

# Edit with your credentials
# Replace placeholders with your actual values
```

**configs/ig_config.yaml:**
```yaml
ig_service:
  username: "YOUR_USERNAME"
  password: "YOUR_PASSWORD"
  api_key: "YOUR_API_KEY"
  acc_type: "DEMO"  # or "LIVE" for production
  acc_number: "YOUR_ACCOUNT_NUMBER"
  
api_config:
  base_url: "https://demo-api.ig.com/gateway/deal"  # Use https://api.ig.com for LIVE
  streaming_url: "https://demo-apd.marketdatasystems.com"
  version: "3"
```

### 5. Configure Database

```bash
# Edit database configuration
cp configs/database_config_template.yaml configs/database_config.yaml
```

**configs/database_config.yaml:**
```yaml
mongodb:
  # For local MongoDB
  connection_string: "mongodb://localhost:27017/"
  # For MongoDB Atlas
  # connection_string: "mongodb+srv://username:password@cluster.mongodb.net/"
  
  database_name: "algo_trader"
  
  collections:
    tick_data: "tick_data"
    trades: "trades"
    ml_predictions: "ml_predictions"
    performance_metrics: "performance_metrics"
  
  options:
    max_pool_size: 100
    min_pool_size: 10
    connect_timeout_ms: 10000
```

### 6. Configure Markets and Assets

```bash
# Copy asset configuration templates
cp configs/assets/ftse_100_template.yaml configs/assets/ftse_100.yaml
cp configs/assets/dax_template.yaml configs/assets/dax.yaml
```

**Edit each asset configuration with correct EPIC codes:**
```yaml
# configs/assets/ftse_100.yaml
asset:
  name: "FTSE 100"
  epic: "IX.D.FTSE.DAILY.IP"  # Verify with IG Markets
  currency: "GBP"
  multiplier: 1
  min_stop_distance: 8
  min_deal_size: 0.5
  trading_hours:
    start: "08:00"
    end: "16:30"
    timezone: "Europe/London"
```

### 7. Configure Additional Services

#### Alpha Vantage (for sentiment analysis)
```bash
# Sign up at https://www.alphavantage.co/support/#api-key
# Add to configs/sentiment_config.yaml
```

```yaml
sentiment:
  alpha_vantage:
    api_key: "YOUR_ALPHA_VANTAGE_KEY"
    enabled: true
```

### 8. Initialize NLTK Data

```python
# Run Python interpreter
python

# Download NLTK data
import nltk
nltk.download('vader_lexicon')
nltk.download('punkt')
nltk.download('stopwords')
exit()
```

### 9. Set Environment Variables (Optional)

Create `.env` file for sensitive data:
```bash
# .env
IG_USERNAME=your_username
IG_PASSWORD=your_password
IG_API_KEY=your_api_key
MONGO_CONNECTION_STRING=mongodb://localhost:27017/
ALPHA_VANTAGE_KEY=your_av_key
```

Update configuration files to use environment variables:
```python
import os
from dotenv import load_dotenv
load_dotenv()

username = os.getenv('IG_USERNAME')
```

### 10. Verify Installation

```bash
# Run verification script
python scripts/verify_installation.py

# Or manually test components:
# Test MongoDB connection
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017/'); print('MongoDB connected')"

# Test IG connection (demo mode)
python -c "from core.ig_service import IGService; ig = IGService(demo=True); print('IG connection successful')"
```

### 11. Run Initial Tests

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests (requires configured services)
pytest tests/integration/

# Test with paper trading
python runners/run_multi_market.py --demo --duration 60
```

## Docker Installation (Alternative)

### Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  mongodb:
    image: mongo:5.0
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password

  algo-trader:
    build: .
    depends_on:
      - mongodb
    volumes:
      - ./configs:/app/configs
      - ./logs:/app/logs
    environment:
      - MONGO_CONNECTION_STRING=mongodb://admin:password@mongodb:27017/
    command: python runners/run_multi_market.py --demo

volumes:
  mongo_data:
```

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "runners/run_multi_market.py"]
```

```bash
# Build and run
docker-compose up --build
```

## Post-Installation Setup

### 1. Configure Strategy Parameters

Edit `configs/strategy_config.yaml`:
```yaml
strategy:
  confidence_threshold: 0.65
  max_positions: 3
  signal_weights:
    technical: 0.3
    ml: 0.25
    sentiment: 0.2
    regime: 0.25
```

### 2. Set Risk Parameters

Edit `configs/risk_config.yaml`:
```yaml
risk_management:
  max_risk_per_trade: 0.02  # 2% per trade
  max_daily_loss: 0.06      # 6% daily loss limit
  max_positions: 5
  stop_loss_multiplier: 1.5
```

### 3. Train Initial ML Models

```bash
# Collect historical data
python scripts/collect_historical_data.py --days 30

# Train models
python ml/model_trainer.py --initial-training
```

### 4. Configure Monitoring

```bash
# Set up log rotation
sudo nano /etc/logrotate.d/algo-trader

# Add configuration:
/path/to/algo-trader/logs/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
}
```

## Troubleshooting Installation

### Common Issues

#### 1. MongoDB Connection Failed
```bash
# Check MongoDB status
sudo systemctl status mongod

# Restart MongoDB
sudo systemctl restart mongod

# Check logs
sudo tail -f /var/log/mongodb/mongod.log
```

#### 2. IG API Authentication Error
- Verify API key is active in IG account settings
- Check demo vs live URL configuration
- Ensure account number is correct

#### 3. Python Package Conflicts
```bash
# Create fresh virtual environment
python -m venv venv_fresh
source venv_fresh/bin/activate
pip install -r requirements.txt
```

#### 4. Lightstreamer Connection Issues
- Check firewall settings for WebSocket connections
- Verify streaming URL in configuration
- Test with IG's connection diagnostic tool

### Getting Help

1. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
2. Review logs in `logs/` directory
3. Run diagnostic script: `python scripts/diagnose.py`
4. Contact support with diagnostic output

## Next Steps

1. Read [CONFIGURATION.md](./CONFIGURATION.md) for detailed configuration options
2. Review [OPERATIONS.md](./OPERATIONS.md) for running the system
3. Test strategies in demo mode before live trading
4. Set up monitoring and alerts
5. Configure backup and recovery procedures