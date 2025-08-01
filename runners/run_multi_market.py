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
from data.db import get_market_tick_data, get_available_markets, get_account_balance, get_trade_lifecycle_status
from data.account_streamer import start_account_streaming, stop_account_streaming, get_live_account_data
from data.trade_streamer import start_trade_streaming, stop_trade_streaming, get_live_active_trades
from utils.market_config_loader import MarketConfigLoader
from utils.trading_safety import get_trading_safety_manager

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
        
        print(f"📊 Configured markets: {', '.join(valid_markets)}")
        
        # Load risk management settings
        self.risk_config = self.config_loader.get_risk_config()
        if self.risk_config:
            print(f"🛡️ Risk limits: {self.risk_config.get('max_margin_utilization_percent', 80)}% margin, {self.risk_config.get('max_exposure_per_market_percent', 20)}% per market")
        
        # Streaming status tracking
        self.account_streaming_started = False
        self.trade_streaming_started = False
        
        # Initialize trading safety manager
        self.safety_manager = get_trading_safety_manager()
        print("🛡️ Trading safety manager initialized")
        
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
                
                if signals:
                    # Always log strategy analysis results
                    print(f"📊 {market_name} Strategy Analysis:")
                    print(f"   Signal: {signals.get('signal', 'None')}")
                    print(f"   RSI: {signals.get('rsi', 'N/A'):.2f}" if signals.get('rsi') else f"   RSI: N/A")
                    print(f"   Trend: {signals.get('trend', 'N/A')}")
                    print(f"   Price: £{signals.get('price', 'N/A'):.2f}" if signals.get('price') else f"   Price: N/A")
                    print(f"   ATR: {signals.get('atr', 'N/A'):.2f}" if signals.get('atr') else f"   ATR: N/A")
                    print(f"   Momentum: {signals.get('momentum', 'N/A'):.2f}%" if signals.get('momentum') else f"   Momentum: N/A")
                    
                    # Check for trading signals
                    if signals.get('signal') in ['BUY', 'SELL']:
                        print(f"🎯 {market_name} TRADING SIGNAL: {signals['signal']}")
                        
                        # SAFETY CHECK: Validate trade before execution
                        can_trade, safety_reason = self.safety_manager.validate_trade(market_name, signals['signal'])
                        
                        if not can_trade:
                            print(f"🛡️ {market_name} Trade blocked by safety manager: {safety_reason}")
                        else:
                            print(f"✅ {market_name} Safety checks passed - Executing trade")
                            
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
                    else:
                        print(f"⏸️ {market_name} No trading signal - Holding position")
                else:
                    print(f"❌ {market_name} Strategy analysis failed - insufficient data")
                
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
        
        # Start account balance streaming first
        print("💰 Starting real-time account balance streaming...")
        account_success = start_account_streaming()
        if account_success:
            self.account_streaming_started = True
            print("✅ Account balance streaming started")
            
            # Wait a moment for initial account data
            time.sleep(5)
            
            # Show initial account data
            try:
                account_data = get_live_account_data()
                if account_data.get('last_update'):
                    print(f"💰 Live Account Data:")
                    print(f"   Available to Deal: £{account_data.get('available_to_deal', 0):.2f}")
                    print(f"   Available Cash: £{account_data.get('available_cash', 0):.2f}")
                    print(f"   Current P&L: £{account_data.get('pnl', 0):.2f}")
                    print(f"   Margin Used: £{account_data.get('margin', 0):.2f}")
                else:
                    print("⏳ Waiting for initial account data...")
            except Exception as e:
                print(f"⚠️ Could not retrieve account data: {e}")
        else:
            print("⚠️ Account streaming failed, using fallback balance system")
        
        # Start trade streaming
        print("📈 Starting real-time trade streaming...")
        trade_success = start_trade_streaming()
        if trade_success:
            self.trade_streaming_started = True
            print("✅ Trade streaming started")
        else:
            print("⚠️ Trade streaming failed, using database-only trade tracking")
        
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
        
        # Stop account streaming
        if self.account_streaming_started:
            print("💰 Stopping account balance streaming...")
            stop_account_streaming()
        
        # Stop trade streaming
        if self.trade_streaming_started:
            print("📈 Stopping trade streaming...")
            stop_trade_streaming()
        
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
            
            # Show system status with live account data
            print(f"📊 System Status: Running={status['running']} | Markets={len(status['markets'])} | DB Markets={len(status['available_markets_in_db'])}")
            
            # Show trade lifecycle status for all markets
            try:
                overall_status = get_trade_lifecycle_status()
                print(f"📈 Trade Status: Pending={overall_status['pending']} | Open={overall_status['open']} | Closed={overall_status['closed']} | Rejected={overall_status['rejected']}")
                
                # Show per-market status if there are active trades
                if overall_status['total_active'] > 0:
                    for market in trading_system.markets:
                        market_status = get_trade_lifecycle_status(market)
                        if market_status['total_active'] > 0:
                            print(f"   {market}: {market_status['pending']}P + {market_status['open']}O = {market_status['total_active']} active")
            except Exception as e:
                print(f"⚠️ Trade status error: {e}")
            
            # Show live account balance and safety status
            try:
                current_balance = get_account_balance()
                account_data = get_live_account_data()
                if account_data.get('last_update'):
                    print(f"💰 Live Balance: £{current_balance:.2f} | P&L: £{account_data.get('pnl', 0):.2f} | Margin: £{account_data.get('margin', 0):.2f}")
                
                # Show safety status
                safety_status = trading_system.safety_manager.get_trading_status()
                if safety_status['trading_suspended']:
                    print(f"🚨 TRADING SUSPENDED: {safety_status['suspension_reason']}")
                else:
                    print(f"🛡️ Safety: Balance {safety_status['balance_percentage']:.1f}% | Open Positions: {safety_status['total_open_positions']}")
                    
            except Exception:
                pass  # Don't show if not available
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ System error: {e}")
    finally:
        trading_system.stop_trading()