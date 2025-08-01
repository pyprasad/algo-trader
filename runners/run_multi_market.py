# runners/run_multi_market.py

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import signal

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.multi_market_collector import MultiMarketCollector
from core.strategy_engine import StrategyEngine
from core.trade_executor import execute_trade
from data.db import get_market_tick_data, get_available_markets, update_account_balance
from utils.market_config_loader import MarketConfigLoader

class MultiMarketTradingSystem:
    def __init__(self, config_loader: MarketConfigLoader = None):
        """
        Initialize multi-market trading system using configuration files
        
        Args:
            config_loader (MarketConfigLoader): Configuration loader instance
        """
        self.config_loader = config_loader or MarketConfigLoader()
        
        # Validate configuration and get valid markets
        valid_markets, invalid_markets = self.config_loader.validate_active_markets()
        
        if invalid_markets:
            print(f"⚠️ Warning: Invalid markets found: {invalid_markets}")
            print("These markets are not configured in assets_comprehensive.yaml")
        
        if not valid_markets:
            raise ValueError("❌ No valid markets configured for trading!")
        
        self.markets = valid_markets
        self.collector = MultiMarketCollector(valid_markets)
        self.strategy_engines = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=len(valid_markets) + 1)
        
        # Initialize strategy engines for each market
        for market in valid_markets:
            self.strategy_engines[market] = StrategyEngine()
        
        # Set initial balance from config
        system_config = self.config_loader.get_system_config()
        initial_balance = system_config.get('initial_balance', 10000.0)
        update_account_balance(initial_balance)
        print(f"💰 Initial balance set to: £{initial_balance}")
        
        print(f"📊 Configured markets: {', '.join(valid_markets)}")
        
        # Load risk management settings
        self.risk_config = self.config_loader.get_risk_config()
        if self.risk_config:
            print(f"🛡️ Risk limits: {self.risk_config.get('max_margin_utilization_percent', 80)}% margin, {self.risk_config.get('max_exposure_per_market_percent', 20)}% per market")
        
    def start_data_collection(self):
        """Start collecting tick data for all markets"""
        print("📡 Starting multi-market data collection...")
        self.collector.start_streaming()
        
    def analyze_market_signals(self, market_name):
        """
        Continuously analyze signals for a specific market
        """
        strategy_engine = self.strategy_engines[market_name]
        
        while self.running:
            try:
                # Get recent tick data for this market
                recent_ticks = get_market_tick_data(market_name, limit=50)
                
                if len(recent_ticks) < 20:  # Need minimum data for analysis
                    print(f"⏳ {market_name}: Waiting for more tick data...")
                    time.sleep(30)
                    continue
                
                # Extract prices for analysis
                prices = [tick['bid'] for tick in reversed(recent_ticks)]  # Reverse to get chronological order
                
                # Run strategy analysis
                signals = strategy_engine.analyze_market_conditions(prices)
                
                if signals and signals.get('signal') in ['BUY', 'SELL']:
                    print(f"🎯 {market_name} SIGNAL: {signals['signal']} | RSI: {signals.get('rsi', 'N/A')} | Trend: {signals.get('trend', 'N/A')}")
                    
                    # Execute trade with global balance checking
                    trade_result = execute_trade(
                        market_name=market_name,
                        direction=signals['signal'],
                        strategy_sl=signals.get('atr', 10),
                        strategy_tp=signals.get('atr', 20) * 2,
                        strategy_signals=signals
                    )
                    
                    if 'error' in trade_result:
                        print(f"❌ {market_name} Trade failed: {trade_result['error']}")
                    else:
                        print(f"✅ {market_name} Trade executed: {trade_result.get('dealStatus', 'Unknown')}")
                
                # Wait before next analysis (configurable)
                system_config = self.config_loader.get_system_config()
                analysis_interval = system_config.get('analysis_interval_seconds', 60)
                time.sleep(analysis_interval)
                
            except Exception as e:
                print(f"❌ Error analyzing {market_name}: {e}")
                time.sleep(30)
    
    def start_trading(self):
        """Start the complete multi-market trading system"""
        print("🚀 Starting Multi-Market Trading System...")
        print(f"📊 Trading markets: {', '.join(self.markets)}")
        
        self.running = True
        
        # Start data collection
        self.start_data_collection()
        
        # Wait for initial data collection (configurable)
        system_config = self.config_loader.get_system_config()
        data_timeout = system_config.get('data_collection_timeout_seconds', 30)
        print(f"⏳ Waiting {data_timeout}s for initial tick data...")
        time.sleep(data_timeout)
        
        # Start strategy analysis for each market in separate threads
        for market in self.markets:
            self.executor.submit(self.analyze_market_signals, market)
            print(f"🎯 Started strategy analysis for {market}")
        
        print("✅ Multi-market trading system is running!")
        
    def stop_trading(self):
        """Stop the trading system"""
        print("🛑 Stopping Multi-Market Trading System...")
        self.running = False
        
        # Stop data collection
        self.collector.stop_streaming()
        
        # Shutdown thread executor
        self.executor.shutdown(wait=True)
        
        print("✅ Multi-market trading system stopped")
    
    def add_market(self, market_name):
        """Add a new market to the trading system"""
        if market_name not in self.markets:
            # Add to collector
            self.collector.add_market(market_name)
            
            # Add strategy engine
            self.strategy_engines[market_name] = StrategyEngine()
            
            # Add to markets list
            self.markets.append(market_name)
            
            # Start analysis if system is running
            if self.running:
                self.executor.submit(self.analyze_market_signals, market_name)
            
            print(f"➕ Added {market_name} to trading system")
        else:
            print(f"⚠️ {market_name} already in trading system")
    
    def remove_market(self, market_name):
        """Remove a market from the trading system"""
        if market_name in self.markets:
            # Remove from collector
            self.collector.remove_market(market_name)
            
            # Remove strategy engine
            if market_name in self.strategy_engines:
                del self.strategy_engines[market_name]
            
            # Remove from markets list
            self.markets.remove(market_name)
            
            print(f"➖ Removed {market_name} from trading system")
        else:
            print(f"⚠️ {market_name} not in trading system")
    
    def get_system_status(self):
        """Get current system status"""
        return {
            "running": self.running,
            "markets": self.markets,
            "data_streaming": self.collector.is_running(),
            "available_markets_in_db": get_available_markets()
        }


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n⚠️ Received shutdown signal...")
    global trading_system
    if trading_system:
        trading_system.stop_trading()
    sys.exit(0)


if __name__ == "__main__":
    # Load market configuration from files
    print("📋 Loading market configuration...")
    config_loader = MarketConfigLoader()
    config_loader.print_market_summary()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize and start trading system
    trading_system = MultiMarketTradingSystem(config_loader)
    
    try:
        trading_system.start_trading()
        
        # Keep the system running
        while True:
            time.sleep(60)
            status = trading_system.get_system_status()
            print(f"📊 System Status: Running={status['running']} | Markets={len(status['markets'])} | DB Markets={len(status['available_markets_in_db'])}")
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ System error: {e}")
    finally:
        trading_system.stop_trading()