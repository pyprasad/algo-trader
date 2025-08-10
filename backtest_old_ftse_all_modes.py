#!/usr/bin/env python3
"""
Comprehensive Backtest: Old FTSE 100 Data with All Trading Modes

Analyzes P&L performance across Conservative, Moderate, and Aggressive modes
using the historical FTSE 100 data from ftse100_old.json
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.professional_strategy_engine import ProfessionalStrategyEngine
from core.enhanced_strategy_engine import get_enhanced_strategy_engine
from utils.system_mode_manager import SystemModeManager

class ComprehensiveBacktester:
    """Backtest all trading modes against historical data"""
    
    def __init__(self):
        self.strategy_engine = ProfessionalStrategyEngine()
        self.enhanced_engine = get_enhanced_strategy_engine()
        self.mode_manager = SystemModeManager()
        
        # Trading modes to test
        self.modes = {
            'conservative': {
                'min_signal_confidence': 0.75,
                'analysis_interval_minutes': 5,
                'max_trades_per_hour': 1,
                'daily_loss_limit': 200,
                'position_size': 1
            },
            'moderate': {
                'min_signal_confidence': 0.65,
                'analysis_interval_minutes': 3,
                'max_trades_per_hour': 2,
                'daily_loss_limit': 300,
                'position_size': 1
            },
            'aggressive': {
                'min_signal_confidence': 0.60,
                'analysis_interval_minutes': 2,
                'max_trades_per_hour': 3,
                'daily_loss_limit': 500,
                'position_size': 1
            }
        }
        
        # Trading costs
        self.spread_cost = 1.0  # £1 per point spread
        self.commission = 0.0   # No commission for CFDs
        
    def load_data(self, filepath: str) -> List[Dict]:
        """Load historical data from JSON file"""
        with open(filepath, 'r') as f:
            data = []
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
        
        # Sort by timestamp
        data.sort(key=lambda x: x.get('timestamp', datetime.now()))
        return data
    
    def calculate_indicators(self, prices: List[float], window: int = 50) -> Dict:
        """Calculate technical indicators"""
        if len(prices) < window:
            return {}
        
        prices_array = np.array(prices[-window:])
        
        # Calculate RSI
        deltas = np.diff(prices_array)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
        
        if avg_loss != 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 100 if avg_gain > 0 else 50
        
        # Calculate Bollinger Bands
        sma = np.mean(prices_array[-20:])
        std = np.std(prices_array[-20:])
        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)
        
        # Calculate MACD
        ema_12 = pd.Series(prices_array).ewm(span=12, adjust=False).mean().iloc[-1]
        ema_26 = pd.Series(prices_array).ewm(span=26, adjust=False).mean().iloc[-1]
        macd = ema_12 - ema_26
        
        # Calculate momentum
        momentum = (prices_array[-1] - prices_array[-10]) / prices_array[-10] * 100 if len(prices_array) >= 10 else 0
        
        return {
            'rsi': rsi,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'sma': sma,
            'macd': macd,
            'momentum': momentum,
            'current_price': prices_array[-1]
        }
    
    def generate_signal(self, indicators: Dict, mode_config: Dict) -> Tuple[str, float]:
        """Generate trading signal based on indicators"""
        if not indicators:
            return 'HOLD', 0.0
        
        signals = []
        
        # RSI Signal
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            signals.append(('BUY', 0.7))
        elif rsi > 70:
            signals.append(('SELL', 0.7))
        else:
            signals.append(('HOLD', 0.3))
        
        # Bollinger Bands Signal
        current_price = indicators.get('current_price', 0)
        upper_band = indicators.get('upper_band', 0)
        lower_band = indicators.get('lower_band', 0)
        
        if current_price < lower_band:
            signals.append(('BUY', 0.8))
        elif current_price > upper_band:
            signals.append(('SELL', 0.8))
        else:
            signals.append(('HOLD', 0.4))
        
        # MACD Signal
        macd = indicators.get('macd', 0)
        if macd > 0:
            signals.append(('BUY', 0.6))
        elif macd < 0:
            signals.append(('SELL', 0.6))
        
        # Momentum Signal
        momentum = indicators.get('momentum', 0)
        if momentum > 1:
            signals.append(('BUY', 0.65))
        elif momentum < -1:
            signals.append(('SELL', 0.65))
        else:
            signals.append(('HOLD', 0.35))
        
        # Aggregate signals
        buy_confidence = sum(conf for sig, conf in signals if sig == 'BUY')
        sell_confidence = sum(conf for sig, conf in signals if sig == 'SELL')
        total_signals = len(signals)
        
        if total_signals > 0:
            buy_confidence /= total_signals
            sell_confidence /= total_signals
        
        # Determine final signal
        if buy_confidence > sell_confidence and buy_confidence >= mode_config['min_signal_confidence']:
            return 'BUY', buy_confidence
        elif sell_confidence > buy_confidence and sell_confidence >= mode_config['min_signal_confidence']:
            return 'SELL', sell_confidence
        else:
            return 'HOLD', max(buy_confidence, sell_confidence)
    
    def backtest_mode(self, data: List[Dict], mode_name: str, mode_config: Dict) -> Dict:
        """Run backtest for a specific mode"""
        print(f"\n{'='*60}")
        print(f"🔄 Backtesting {mode_name.upper()} Mode")
        print(f"{'='*60}")
        
        # Initialize tracking variables
        trades = []
        positions = []
        current_position = None
        daily_pnl = 0
        total_pnl = 0
        
        # Time tracking
        last_analysis_time = None
        hourly_trades = []
        
        # Price history
        price_history = []
        
        # Process each tick
        for i, tick in enumerate(data):
            timestamp = tick.get('timestamp', datetime.now())
            bid = tick.get('bid', 0)
            offer = tick.get('offer', 0)
            mid_price = (bid + offer) / 2
            
            price_history.append(mid_price)
            
            # Skip if not enough data
            if len(price_history) < 50:
                continue
            
            # Check analysis interval
            if last_analysis_time:
                time_since_last = timestamp - last_analysis_time
                if time_since_last < timedelta(minutes=mode_config['analysis_interval_minutes']):
                    continue
            
            last_analysis_time = timestamp
            
            # Check hourly trade limit
            one_hour_ago = timestamp - timedelta(hours=1)
            hourly_trades = [t for t in hourly_trades if t['timestamp'] > one_hour_ago]
            
            if len(hourly_trades) >= mode_config['max_trades_per_hour']:
                continue
            
            # Check daily loss limit
            if abs(daily_pnl) >= mode_config['daily_loss_limit']:
                continue
            
            # Calculate indicators
            indicators = self.calculate_indicators(price_history)
            
            # Generate signal
            signal, confidence = self.generate_signal(indicators, mode_config)
            
            # Execute trades based on signal
            if signal != 'HOLD' and not current_position:
                # Open new position
                entry_price = offer if signal == 'BUY' else bid
                
                current_position = {
                    'type': signal,
                    'entry_price': entry_price,
                    'entry_time': timestamp,
                    'size': mode_config['position_size'],
                    'confidence': confidence
                }
                
                trade = {
                    'timestamp': timestamp,
                    'type': signal,
                    'price': entry_price,
                    'confidence': confidence,
                    'action': 'OPEN'
                }
                
                trades.append(trade)
                hourly_trades.append(trade)
                
                print(f"⚡ {timestamp.strftime('%H:%M:%S')} - {signal} @ {entry_price:.1f} (conf: {confidence:.2%})")
                
            elif current_position:
                # Check for exit conditions
                current_price = bid if current_position['type'] == 'BUY' else offer
                pnl = (current_price - current_position['entry_price']) * current_position['size']
                if current_position['type'] == 'SELL':
                    pnl = -pnl
                
                # Exit if opposite signal or stop/target hit
                should_exit = False
                exit_reason = ""
                
                if signal != 'HOLD' and signal != current_position['type'] and confidence >= mode_config['min_signal_confidence']:
                    should_exit = True
                    exit_reason = "opposite signal"
                elif pnl >= 20:  # Take profit at £20
                    should_exit = True
                    exit_reason = "take profit"
                elif pnl <= -10:  # Stop loss at £10
                    should_exit = True
                    exit_reason = "stop loss"
                
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
                    
                    print(f"💰 {timestamp.strftime('%H:%M:%S')} - CLOSE {current_position['type']} @ {exit_price:.1f} | P&L: £{trade_pnl:.2f} ({exit_reason})")
                    
                    current_position = None
                    
                    # Reset daily P&L at day boundary
                    if i > 0 and data[i-1].get('timestamp').date() != timestamp.date():
                        daily_pnl = 0
        
        # Close any open position at end
        if current_position and len(data) > 0:
            last_tick = data[-1]
            exit_price = last_tick.get('bid' if current_position['type'] == 'BUY' else 'offer', 0)
            trade_pnl = (exit_price - current_position['entry_price']) * current_position['size']
            if current_position['type'] == 'SELL':
                trade_pnl = -trade_pnl
            trade_pnl -= self.spread_cost * current_position['size']
            
            total_pnl += trade_pnl
            
            position = {
                'entry_time': current_position['entry_time'],
                'exit_time': last_tick.get('timestamp', datetime.now()),
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
        
        stats = {
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
        
        return stats
    
    def run_comprehensive_backtest(self, filepath: str):
        """Run backtest for all modes"""
        print("\n" + "="*60)
        print("🎯 COMPREHENSIVE BACKTEST: OLD FTSE 100 DATA")
        print("="*60)
        
        # Load data
        print("\n📊 Loading historical data...")
        data = self.load_data(filepath)
        print(f"✅ Loaded {len(data)} ticks")
        
        if data:
            first_tick = data[0]
            last_tick = data[-1]
            print(f"📅 Period: {first_tick.get('timestamp', 'Unknown')} to {last_tick.get('timestamp', 'Unknown')}")
            
            # Calculate data span
            if 'timestamp' in first_tick and 'timestamp' in last_tick:
                duration = last_tick['timestamp'] - first_tick['timestamp']
                print(f"⏱️ Duration: {duration}")
        
        # Run backtest for each mode
        results = {}
        for mode_name, mode_config in self.modes.items():
            results[mode_name] = self.backtest_mode(data, mode_name, mode_config)
        
        # Print comprehensive summary
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE P&L SUMMARY")
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
        print("📈 DETAILED MODE ANALYSIS")
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
            print(f"   Risk/Reward: {abs(stats['average_win']/stats['average_loss']) if stats['average_loss'] != 0 else 0:.2f}")
        
        # Winner announcement
        print("\n" + "="*60)
        print("🏆 BEST PERFORMING MODE")
        print("="*60)
        
        best_mode = max(results.keys(), key=lambda x: results[x]['total_pnl'])
        best_stats = results[best_mode]
        
        print(f"\n🥇 {best_mode.upper()} MODE wins with £{best_stats['total_pnl']:.2f} profit!")
        print(f"   • {best_stats['total_trades']} trades executed")
        print(f"   • {best_stats['win_rate']:.1%} win rate")
        print(f"   • £{best_stats['average_win']:.2f} average win")
        
        # Risk assessment
        print("\n" + "="*60)
        print("⚠️ RISK ASSESSMENT")
        print("="*60)
        
        for mode_name in ['conservative', 'moderate', 'aggressive']:
            stats = results[mode_name]
            mode_config = self.modes[mode_name]
            
            # Calculate max drawdown
            cumulative_pnl = 0
            max_cumulative = 0
            max_drawdown = 0
            
            for position in stats['positions']:
                cumulative_pnl += position['pnl']
                max_cumulative = max(max_cumulative, cumulative_pnl)
                drawdown = max_cumulative - cumulative_pnl
                max_drawdown = max(max_drawdown, drawdown)
            
            print(f"\n{mode_name.upper()}:")
            print(f"   Max Drawdown: £{max_drawdown:.2f}")
            print(f"   Daily Loss Limit: £{mode_config['daily_loss_limit']}")
            print(f"   Risk Level: {'✅ SAFE' if max_drawdown < mode_config['daily_loss_limit'] else '⚠️ EXCEEDED'}")
        
        return results

def main():
    """Main execution"""
    backtester = ComprehensiveBacktester()
    
    # Run comprehensive backtest
    results = backtester.run_comprehensive_backtest('ftse100_old.json')
    
    print("\n" + "="*60)
    print("✅ BACKTEST COMPLETE")
    print("="*60)
    print("\n💡 Key Insights:")
    print("   • All modes include bulletproof position checking")
    print("   • Conservative mode: Safest with lowest frequency")
    print("   • Moderate mode: Balanced risk/reward")
    print("   • Aggressive mode: Higher frequency, higher risk")
    print("\n📌 Note: These results assume perfect execution and include spread costs")

if __name__ == "__main__":
    main()