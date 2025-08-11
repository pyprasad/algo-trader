# runners/run_multi_market.py

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import signal

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.multi_market_collector import MultiMarketCollector
from core.enhanced_strategy_engine import get_enhanced_strategy_engine
from core.market_adaptive_strategy import get_market_adaptive_strategy
from core.trade_executor import execute_trade
from data.db import get_market_tick_data, get_available_markets, get_account_balance, get_trade_lifecycle_status, sync_trade_statuses_with_ig
from data.account_streamer import start_account_streaming, stop_account_streaming, get_live_account_data
from data.trade_streamer import start_trade_streaming, stop_trade_streaming, get_live_active_trades
from utils.market_config_loader import MarketConfigLoader
from utils.trading_safety import get_trading_safety_manager
from core.dynamic_position_manager import get_dynamic_position_manager
from data.news_sentiment import get_sentiment_engine
from core.emergency_risk_manager import get_emergency_risk_manager
from core.professional_strategy_engine import get_professional_strategy_engine
from core.professional_monitor import get_professional_monitor
from core.economic_calendar_monitor import get_economic_calendar_monitor

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
        self.enhanced_strategy_engine = get_enhanced_strategy_engine()
        self.market_adaptive_strategy = get_market_adaptive_strategy()
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=len(valid_markets) + 1)
        
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
        
        # Initialize dynamic position manager
        self.dynamic_position_manager = get_dynamic_position_manager()
        print("🚀 Dynamic position manager initialized")
        
        # Initialize sentiment analysis engine
        self.sentiment_engine = get_sentiment_engine()
        print("📰 News sentiment analysis engine initialized")
        
        # Initialize professional risk management
        self.emergency_risk_manager = get_emergency_risk_manager()
        print("🚨 Emergency risk management initialized")
        
        # Initialize professional strategy engine
        self.professional_strategy = get_professional_strategy_engine()
        print("📈 Professional strategy engine initialized")
        
        # Initialize professional monitoring
        self.professional_monitor = get_professional_monitor()
        print("📊 Professional performance monitor initialized")
        
        # Initialize economic calendar monitoring
        self.economic_calendar_monitor = get_economic_calendar_monitor()
        print("📅 Economic calendar monitor initialized")
        
    def start_data_collection(self):
        """Start collecting tick data for all markets"""
        print("📡 Starting multi-market data collection...")
        self.collector.start_streaming()
        
    def analyze_market_signals(self, market_name):
        """
        Continuously analyze signals for a specific market using enhanced engine
        """
        
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
                
                # STEP 1: PROFESSIONAL STRATEGY ANALYSIS
                print(f"🔍 {market_name}: Professional analysis of {len(prices)} price points...")
                
                # Get professional signal first
                professional_signal = self.professional_strategy.analyze_market(prices, market_name)
                print(f"📈 Professional Signal: {professional_signal.get('signal', 'NONE')} (strength: {professional_signal.get('strength', 0):.2f})")
                
                # Use professional signal if strong enough, otherwise fallback
                if professional_signal.get('strength', 0) >= 0.6:
                    signals = professional_signal
                    signals['strategy_source'] = 'professional_engine'
                else:
                    # Fallback to market-adaptive strategy
                    print(f"⚠️ {market_name}: Professional signal too weak, using adaptive strategy")
                    signals = self.market_adaptive_strategy.analyze_market_conditions(prices, market_name)
                
                # Log signal result
                if signals:
                    print(f"📊 {market_name}: Adaptive Strategy Signal = {signals.get('signal', 'NONE')}, Confidence = {signals.get('confidence', 0):.2f}")
                else:
                    print(f"⚠️ {market_name}: No signals from adaptive strategy")
                
                # Fallback to enhanced strategy if adaptive strategy fails
                if not signals or signals.get('signal') == 'HOLD':
                    enhanced_signals = self.enhanced_strategy_engine.analyze_market_conditions(prices, market_name)
                    if enhanced_signals and enhanced_signals.get('signal') != 'HOLD':
                        # Merge adaptive constraints with enhanced signals
                        if self.market_adaptive_strategy._is_good_trading_time(market_name) and \
                           not self.market_adaptive_strategy._is_market_suspended(market_name):
                            signals = enhanced_signals
                            signals['strategy_source'] = 'enhanced_with_adaptive_filters'
                
                if signals:
                    # Enhanced strategy analysis results with more details
                    print(f"🚀 {market_name} Enhanced Strategy Analysis:")
                    print(f"   🎯 Final Signal: {signals.get('signal', 'HOLD')} (confidence: {signals.get('confidence', 0):.2f})")
                    print(f"   📊 Composite Score: {signals.get('composite_score', 0):.3f}")
                    print(f"   💪 Signal Strength: {signals.get('signal_strength', 0):.2f}")
                    print(f"   📈 Technical: RSI {signals.get('rsi', 0):.1f} | {signals.get('trend', 'N/A')} | {signals.get('regime', 'N/A')}")
                    print(f"   💰 Price: £{signals.get('price', 0):.2f} | Momentum: {signals.get('momentum', 0):.1f}%")
                    
                    # Show individual signal breakdown
                    if 'signal_breakdown' in signals:
                        print(f"   🔍 Signal Breakdown:")
                        for signal_type, details in signals['signal_breakdown'].items():
                            print(f"      {signal_type.replace('_', ' ').title()}: {details}")
                    
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
                                # Record failed trade for adaptive strategy
                                self.market_adaptive_strategy.record_trade_result(market_name, -5.0)  # Assume small loss for failed trades
                            else:
                                print(f"✅ {market_name} Trade executed: {trade_result.get('dealStatus', 'Unknown')}")
                                # Trade success will be recorded when streaming confirms P&L
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
        
        # Start dynamic position management
        if self.dynamic_position_manager.start():
            print("🚀 Dynamic position management active")
        
        # Start sentiment analysis
        print("📰 Starting news sentiment analysis...")
        try:
            self.sentiment_engine.start_continuous_monitoring(self.markets)
            print("✅ News sentiment analysis started")
        except Exception as e:
            print(f"⚠️ Sentiment analysis failed to start: {e}")
        
        # Start professional monitoring
        print("📊 Starting professional performance monitoring...")
        try:
            self.professional_monitor.start_monitoring()
            self.emergency_risk_manager.start_monitoring()
            print("✅ Professional monitoring systems started")
        except Exception as e:
            print(f"⚠️ Professional monitoring failed to start: {e}")
        
        # Start economic calendar monitoring
        print("📅 Starting economic calendar monitoring...")
        try:
            if self.economic_calendar_monitor.start_monitoring():
                print("✅ Economic calendar monitoring started")
            else:
                print("⚠️ Economic calendar monitoring disabled or failed to start")
        except Exception as e:
            print(f"⚠️ Economic calendar monitoring failed to start: {e}")
        
        print("🎯 PROFESSIONAL TRADING SYSTEM IS RUNNING!")
        print("   🛡️ Emergency risk controls: ACTIVE")
        print("   📈 Professional strategies: ACTIVE")  
        print("   📊 Performance monitoring: ACTIVE")
        print("   📅 Economic calendar monitoring: ACTIVE")
        print("   🚨 Circuit breakers: ACTIVE")
        
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
            
        # Stop dynamic position management
        self.dynamic_position_manager.stop()
        
        # Stop sentiment analysis
        try:
            self.sentiment_engine.stop_monitoring()
            print("📰 News sentiment analysis stopped")
        except Exception as e:
            print(f"⚠️ Error stopping sentiment analysis: {e}")
        
        # Stop professional monitoring systems
        try:
            self.professional_monitor.stop_monitoring()
            self.emergency_risk_manager.stop_monitoring()
            print("📊 Professional monitoring systems stopped")
        except Exception as e:
            print(f"⚠️ Error stopping professional monitoring: {e}")
        
        # Stop economic calendar monitoring
        try:
            self.economic_calendar_monitor.stop_monitoring()
            print("📅 Economic calendar monitoring stopped")
        except Exception as e:
            print(f"⚠️ Error stopping economic calendar monitoring: {e}")
        
        # Shutdown thread executor
        self.executor.shutdown(wait=True)
        
        print("✅ Multi-market trading system stopped")
    
    def add_market(self, market_name):
        """Add a new market to the trading system"""
        if market_name not in self.markets:
            # Add to collector
            self.collector.add_market(market_name)
            
            # Enhanced strategy engine is shared across all markets
            
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
        sync_counter = 0
        while True:
            time.sleep(60)
            sync_counter += 1
            
            # Sync database with IG every 5 minutes to prevent corrupted records
            if sync_counter >= 5:  # Every 5 minutes
                try:
                    print("🔄 Syncing database with IG API...")
                    sync_result = sync_trade_statuses_with_ig()
                    if sync_result["closed"] > 0:
                        print(f"🧹 Auto-closed {sync_result['closed']} stale trades")
                except Exception as e:
                    print(f"⚠️ Database sync error: {e}")
                sync_counter = 0
            
            status = trading_system.get_system_status()
            
            # Show system status with live account data
            print(f"📊 System Status: Running={status['running']} | Markets={len(status['markets'])} | DB Markets={len(status['available_markets_in_db'])}")
            
            # Show trade lifecycle status for all markets
            try:
                overall_status = get_trade_lifecycle_status()
                print(f"📈 Trade Status: Open={overall_status['open']} | Pending={overall_status['pending']} | Closed={overall_status['closed']} | Rejected={overall_status['rejected']} | Timeout={overall_status['timeout']}")
                
                # Show per-market status if there are active or pending trades
                active_markets = []
                for market in trading_system.markets:
                    market_status = get_trade_lifecycle_status(market)
                    if market_status['total_active'] > 0 or market_status['pending_unconfirmed'] > 0:
                        active_markets.append(f"{market}: {market_status['open']}O + {market_status['pending_unconfirmed']}P")
                
                if active_markets:
                    print(f"   Active Markets: {' | '.join(active_markets)}")
            except Exception as e:
                print(f"⚠️ Trade status error: {e}")
            
            # Show live account balance and safety status
            try:
                current_balance = get_account_balance()
                account_data = get_live_account_data()
                if account_data.get('last_update'):
                    print(f"💰 Live Balance: £{current_balance:.2f} | P&L: £{account_data.get('pnl', 0):.2f} | Margin: £{account_data.get('margin', 0):.2f}")
                
                # Show professional risk status  
                try:
                    risk_status = trading_system.emergency_risk_manager.get_risk_status()
                    if risk_status['trading_halted']:
                        print(f"🚨 EMERGENCY HALT: {risk_status['halt_reason']}")
                    else:
                        print(f"🛡️ Professional Risk: Daily P&L {risk_status['daily_pnl']:+.2f} | Positions {risk_status['active_positions']} | Losses {risk_status['consecutive_losses']}")
                        
                    # Show circuit breaker status
                    active_breakers = [name for name, active in risk_status['circuit_breakers'].items() if active]
                    if active_breakers:
                        print(f"🚨 Active Circuit Breakers: {', '.join(active_breakers)}")
                except:
                    # Fallback to original safety status
                    safety_status = trading_system.safety_manager.get_trading_status()
                    if safety_status['trading_suspended']:
                        print(f"🚨 TRADING SUSPENDED: {safety_status['suspension_reason']}")
                    else:
                        print(f"🛡️ Safety: Balance {safety_status['balance_percentage']:.1f}% | Open Positions: {safety_status['total_open_positions']}")
                
                # Show dynamic position management status
                dpm_status = trading_system.dynamic_position_manager.get_status()
                if dpm_status['enabled'] and dpm_status['running']:
                    adjustments = len(trading_system.dynamic_position_manager.get_adjustment_history())
                    print(f"🚀 Dynamic Limits: Managing {dpm_status['positions_managed']} positions | {adjustments} adjustments made")
                elif dpm_status['enabled']:
                    print(f"⚠️ Dynamic Limits: Enabled but not running")
                
                # Show market-adaptive strategy status
                try:
                    market_status = trading_system.market_adaptive_strategy.get_market_status()
                    status_parts = []
                    for market, status in market_status.items():
                        if status['suspended']:
                            status_parts.append(f"{market}: 🚨SUSPENDED")
                        elif status['consecutive_losses'] > 0:
                            status_parts.append(f"{market}: ⚠️{status['consecutive_losses']}L")
                        elif status['recent_performance'] > 0:
                            status_parts.append(f"{market}: ✅+£{status['recent_performance']:.0f}")
                        else:
                            status_parts.append(f"{market}: ✅OK")
                    
                    if status_parts:
                        print(f"🎯 Market Status: {' | '.join(status_parts)}")
                except Exception:
                    pass  # Don't show if not available
                    
            except Exception:
                pass  # Don't show if not available
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ System error: {e}")
    finally:
        trading_system.stop_trading()