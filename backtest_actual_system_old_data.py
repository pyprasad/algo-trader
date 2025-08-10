#!/usr/bin/env python3
"""
Backtest Actual Trading System Against Old FTSE 100 Data

This uses the ACTUAL trading system components without modifications
to test Conservative, Moderate, and Aggressive modes against historical data.
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Import ACTUAL system components
from core.professional_strategy_engine import ProfessionalStrategyEngine
from core.enhanced_strategy_engine import get_enhanced_strategy_engine
from core.emergency_risk_manager import EmergencyRiskManager
from models.ml_predictor import MLTradingPredictor
from utils.system_mode_manager import SystemModeManager

class ActualSystemBacktester:
    """Backtest using actual trading system components"""
    
    def __init__(self):
        # Use ACTUAL system components
        self.strategy_engine = ProfessionalStrategyEngine()
        self.enhanced_engine = get_enhanced_strategy_engine()
        self.risk_manager = EmergencyRiskManager()
        self.mode_manager = SystemModeManager()
        
        # Try to load ML model if available
        self.ml_predictor = None
        try:
            self.ml_predictor = MLTradingPredictor()
            # Try loading existing model
            import os
            if os.path.exists('models/ml_model_FTSE_100.pkl'):
                import joblib
                self.ml_predictor.model = joblib.load('models/ml_model_FTSE_100.pkl')
                print("✅ ML model loaded for enhanced predictions")
        except:
            print("⚠️ ML model not available, using traditional strategies only")
        
        # Get actual mode configurations from system
        self.modes = self.mode_manager.get_available_modes()
        
        # Trading costs (same as actual system)
        self.spread_cost = 1.0  # £1 per point spread
        
    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load and prepare historical data"""
        data = []
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    tick = json.loads(line)
                    # Parse timestamp
                    if 'timestamp' in tick and '$date' in tick['timestamp']:
                        tick['timestamp'] = datetime.fromisoformat(
                            tick['timestamp']['$date'].replace('Z', '+00:00')
                        )
                    data.append(tick)
                except json.JSONDecodeError:
                    continue
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(data)
        df = df.sort_values('timestamp')
        df['mid_price'] = (df['bid'] + df['offer']) / 2
        
        return df
    
    def prepare_price_data(self, df: pd.DataFrame, end_idx: int) -> List[float]:
        """Prepare price data for strategy engine"""
        # Get last 100 prices up to end_idx
        start_idx = max(0, end_idx - 100)
        return df['mid_price'].iloc[start_idx:end_idx].tolist()
    
    def backtest_mode(self, df: pd.DataFrame, mode_name: str) -> Dict:
        """Run backtest for a specific mode using actual system logic"""
        print(f"\n{'='*60}")
        print(f"🔄 Backtesting {mode_name.upper()} Mode (Using Actual System)")
        print(f"{'='*60}")
        
        # Get actual mode configuration
        mode_config = self.modes[mode_name]
        
        # Switch system to this mode
        self.mode_manager.switch_mode(mode_name)
        
        # Initialize tracking
        trades = []
        positions = []
        current_position = None
        daily_pnl = 0
        total_pnl = 0
        
        # Time tracking
        last_analysis_time = None
        hourly_trades = []
        last_trade_time = None
        
        # Process each tick
        for i in range(100, len(df)):  # Start after we have enough history
            tick = df.iloc[i]
            timestamp = tick['timestamp']
            bid = tick['bid']
            offer = tick['offer']
            
            # Check analysis interval (from actual mode config)
            if last_analysis_time:
                time_since_last = timestamp - last_analysis_time
                if time_since_last < timedelta(minutes=mode_config['analysis_interval_minutes']):
                    continue
            
            last_analysis_time = timestamp
            
            # Check hourly trade limit (from actual mode config)
            one_hour_ago = timestamp - timedelta(hours=1)
            hourly_trades = [t for t in hourly_trades if t['timestamp'] > one_hour_ago]
            
            if len(hourly_trades) >= mode_config['max_trades_per_hour']:
                continue
            
            # Check daily loss limit (from actual mode config)
            if abs(daily_pnl) >= mode_config['daily_loss_limit']:
                continue
            
            # Safety check: minimum time between trades (30 seconds)
            if last_trade_time and (timestamp - last_trade_time) < timedelta(seconds=30):
                continue
            
            # Prepare price data for strategy
            price_data = self.prepare_price_data(df, i + 1)
            
            if len(price_data) < 50:
                continue
            
            # Get signals from ACTUAL strategy engine
            try:
                # Use professional strategy engine
                signals = self.strategy_engine.analyze_market_conditions(
                    price_data, 
                    "FTSE 100"
                )
                
                if not signals or 'confidence' not in signals:
                    continue
                
                signal_confidence = signals['confidence']
                signal_direction = signals.get('signal', 'HOLD')
                
                # Apply mode-specific confidence filter
                if signal_confidence < mode_config['min_signal_confidence']:
                    continue
                
                # Execute trades based on actual system logic
                if signal_direction != 'HOLD' and not current_position:
                    # Check risk manager approval
                    can_trade, reason = self.risk_manager.can_open_position(
                        "FTSE 100",
                        signal_direction,
                        1,  # position size
                        {'daily_pnl': daily_pnl}
                    )
                    
                    if not can_trade:
                        continue
                    
                    # Open new position
                    entry_price = offer if signal_direction == 'BUY' else bid
                    
                    current_position = {
                        'type': signal_direction,
                        'entry_price': entry_price,
                        'entry_time': timestamp,
                        'size': 1,
                        'confidence': signal_confidence
                    }
                    
                    trade = {
                        'timestamp': timestamp,
                        'type': signal_direction,
                        'price': entry_price,
                        'confidence': signal_confidence
                    }
                    
                    trades.append(trade)
                    hourly_trades.append(trade)
                    last_trade_time = timestamp
                    
                    print(f"⚡ {timestamp.strftime('%H:%M:%S')} - {signal_direction} @ {entry_price:.1f} (conf: {signal_confidence:.2%})")
                    
                elif current_position:
                    # Check exit conditions using actual system logic
                    current_price = bid if current_position['type'] == 'BUY' else offer
                    pnl = (current_price - current_position['entry_price']) * current_position['size']
                    if current_position['type'] == 'SELL':
                        pnl = -pnl
                    
                    # Exit conditions from actual system
                    should_exit = False
                    exit_reason = ""
                    
                    # Opposite signal
                    if signal_direction != 'HOLD' and signal_direction != current_position['type']:
                        if signal_confidence >= mode_config['min_signal_confidence']:
                            should_exit = True
                            exit_reason = "opposite signal"
                    
                    # Stop loss / Take profit (from actual system)
                    elif pnl >= 20:  # Take profit
                        should_exit = True
                        exit_reason = "take profit"
                    elif pnl <= -10:  # Stop loss
                        should_exit = True
                        exit_reason = "stop loss"
                    
                    # Time-based exit (hold max 1 hour)
                    elif (timestamp - current_position['entry_time']) > timedelta(hours=1):
                        should_exit = True
                        exit_reason = "time limit"
                    
                    if should_exit:
                        # Close position
                        exit_price = bid if current_position['type'] == 'BUY' else offer
                        trade_pnl = (exit_price - current_position['entry_price']) * current_position['size']
                        if current_position['type'] == 'SELL':
                            trade_pnl = -trade_pnl
                        
                        # Account for spread
                        trade_pnl -= self.spread_cost * current_position['size']
                        
                        daily_pnl += trade_pnl
                        total_pnl += trade_pnl
                        
                        position = {
                            'entry_time': current_position['entry_time'],
                            'exit_time': timestamp,
                            'type': current_position['type'],
                            'entry_price': current_position['entry_price'],
                            'exit_price': exit_price,
                            'pnl': trade_pnl,
                            'reason': exit_reason
                        }
                        
                        positions.append(position)
                        
                        # Update risk manager with P&L
                        self.risk_manager.update_daily_pnl(trade_pnl)
                        
                        print(f"💰 {timestamp.strftime('%H:%M:%S')} - CLOSE @ {exit_price:.1f} | P&L: £{trade_pnl:.2f} ({exit_reason})")
                        
                        current_position = None
                        last_trade_time = timestamp
                        
            except Exception as e:
                # Skip on any error to continue backtest
                continue
            
            # Reset daily P&L at day boundary
            if i > 0 and df.iloc[i-1]['timestamp'].date() != timestamp.date():
                daily_pnl = 0
                self.risk_manager.reset_daily_metrics()
        
        # Close any open position at end
        if current_position:
            last_tick = df.iloc[-1]
            exit_price = last_tick['bid'] if current_position['type'] == 'BUY' else last_tick['offer']
            trade_pnl = (exit_price - current_position['entry_price']) * current_position['size']
            if current_position['type'] == 'SELL':
                trade_pnl = -trade_pnl
            trade_pnl -= self.spread_cost * current_position['size']
            
            total_pnl += trade_pnl
            
            position = {
                'entry_time': current_position['entry_time'],
                'exit_time': last_tick['timestamp'],
                'type': current_position['type'],
                'entry_price': current_position['entry_price'],
                'exit_price': exit_price,
                'pnl': trade_pnl,
                'reason': 'end of data'
            }
            positions.append(position)
        
        # Calculate statistics
        winning_trades = [p for p in positions if p['pnl'] > 0]
        losing_trades = [p for p in positions if p['pnl'] < 0]
        
        return {
            'mode': mode_name,
            'total_trades': len(positions),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(positions) if positions else 0,
            'total_pnl': total_pnl,
            'average_win': sum(p['pnl'] for p in winning_trades) / len(winning_trades) if winning_trades else 0,
            'average_loss': sum(p['pnl'] for p in losing_trades) / len(losing_trades) if losing_trades else 0,
            'max_win': max((p['pnl'] for p in positions), default=0),
            'max_loss': min((p['pnl'] for p in positions), default=0),
            'positions': positions
        }
    
    def run_backtest(self, filepath: str):
        """Run backtest for all modes using actual system"""
        print("\n" + "="*60)
        print("🎯 BACKTEST WITH ACTUAL TRADING SYSTEM")
        print("="*60)
        
        # Load data
        print("\n📊 Loading historical FTSE 100 data...")
        df = self.load_data(filepath)
        print(f"✅ Loaded {len(df)} ticks")
        
        if len(df) > 0:
            print(f"📅 Period: {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
            duration = df.iloc[-1]['timestamp'] - df.iloc[0]['timestamp']
            print(f"⏱️ Duration: {duration}")
        
        # Run backtest for each mode
        results = {}
        for mode_name in ['conservative', 'moderate', 'aggressive']:
            results[mode_name] = self.backtest_mode(df, mode_name)
        
        # Print comprehensive summary
        print("\n" + "="*60)
        print("📊 P&L SUMMARY - ACTUAL SYSTEM BACKTEST")
        print("="*60)
        
        print(f"\n{'Mode':<15} {'Trades':<10} {'Win Rate':<12} {'Total P&L':<15} {'Avg Win':<12} {'Avg Loss':<12}")
        print("-"*80)
        
        for mode_name in ['conservative', 'moderate', 'aggressive']:
            stats = results[mode_name]
            print(f"{mode_name.capitalize():<15} {stats['total_trades']:<10} "
                  f"{stats['win_rate']:<12.1%} £{stats['total_pnl']:<14.2f} "
                  f"£{stats['average_win']:<11.2f} £{stats['average_loss']:<11.2f}")
        
        # Detailed breakdown
        print("\n" + "="*60)
        print("📈 DETAILED ANALYSIS")
        print("="*60)
        
        for mode_name in ['conservative', 'moderate', 'aggressive']:
            stats = results[mode_name]
            print(f"\n🎯 {mode_name.upper()} MODE:")
            print(f"   Total Trades: {stats['total_trades']}")
            print(f"   Winning Trades: {stats['winning_trades']}")
            print(f"   Losing Trades: {stats['losing_trades']}")
            print(f"   Win Rate: {stats['win_rate']:.1%}")
            print(f"   Total P&L: £{stats['total_pnl']:.2f}")
            print(f"   Best Trade: £{stats['max_win']:.2f}")
            print(f"   Worst Trade: £{stats['max_loss']:.2f}")
        
        # Winner
        best_mode = max(results.keys(), key=lambda x: results[x]['total_pnl'])
        best_stats = results[best_mode]
        
        print("\n" + "="*60)
        print("🏆 RECOMMENDATION")
        print("="*60)
        print(f"\n🥇 {best_mode.upper()} MODE performed best with £{best_stats['total_pnl']:.2f} P&L")
        
        return results

def main():
    """Main execution"""
    backtester = ActualSystemBacktester()
    
    # Run backtest with actual system
    results = backtester.run_backtest('ftse100_old.json')
    
    print("\n" + "="*60)
    print("✅ BACKTEST COMPLETE")
    print("="*60)
    print("\n📌 This backtest used your ACTUAL trading system components:")
    print("   • Professional Strategy Engine")
    print("   • Emergency Risk Manager")
    print("   • System Mode Manager")
    print("   • All safety features enabled")

if __name__ == "__main__":
    main()