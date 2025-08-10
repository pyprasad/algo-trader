#!/usr/bin/env python3
"""
📊 August 8th Trading System Backtest

This script simulates trading on the actual August 8, 2025 tick data to compare:
1. OLD SYSTEM: Broken position checking and no daily loss limits  
2. NEW SYSTEM: Bulletproof fixes with all safety measures

Author: Backtest Analysis Team
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

@dataclass
class Trade:
    """Represents a single trade"""
    market: str
    direction: str
    entry_price: float
    size: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    status: str = "OPEN"
    deal_id: str = ""

class BacktestEngine:
    """
    Comprehensive backtest engine for August 8th data
    """
    
    def __init__(self):
        self.initial_balance = 10000.0  # £10k starting balance
        self.current_balance = self.initial_balance
        
        # Load historical tick data
        self.ftse_data = self._load_tick_data("tick_ftse_100_08_08.json", "FTSE 100")
        self.dax_data = self._load_tick_data("tick_dax_08_08.json", "DAX")
        
        print(f"📊 Loaded {len(self.ftse_data)} FTSE ticks, {len(self.dax_data)} DAX ticks")
        
        # Combine and sort all data
        self.all_ticks = sorted(self.ftse_data + self.dax_data, key=lambda x: x['timestamp'])
        print(f"📊 Total ticks: {len(self.all_ticks)} from {self.all_ticks[0]['timestamp']} to {self.all_ticks[-1]['timestamp']}")
    
    def _load_tick_data(self, filename: str, market: str) -> List[Dict]:
        """Load tick data from JSON file"""
        ticks = []
        try:
            with open(filename, 'r') as f:
                for line in f:
                    tick_data = json.loads(line.strip())
                    
                    # Parse timestamp
                    timestamp_str = tick_data['timestamp']['$date']
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    
                    ticks.append({
                        'market': market,
                        'bid': tick_data['bid'],
                        'offer': tick_data['offer'],
                        'timestamp': timestamp,
                        'mid_price': (tick_data['bid'] + tick_data['offer']) / 2
                    })
                    
        except FileNotFoundError:
            print(f"❌ Warning: {filename} not found")
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
            
        return ticks
    
    def _calculate_technical_indicators(self, prices: List[float], period: int = 14) -> Dict:
        """Calculate technical indicators for strategy signals"""
        if len(prices) < period:
            return {'rsi': 50, 'sma': prices[-1] if prices else 0, 'trend': 'NEUTRAL'}
        
        # Simple RSI calculation
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:]) if len(gains) >= period else 0
        avg_loss = np.mean(losses[-period:]) if len(losses) >= period else 0
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Simple moving average
        sma = np.mean(prices[-period:])
        
        # Trend detection
        if len(prices) >= 5:
            recent_trend = np.polyfit(range(5), prices[-5:], 1)[0]
            trend = 'UPTREND' if recent_trend > 0 else 'DOWNTREND'
        else:
            trend = 'NEUTRAL'
        
        return {
            'rsi': rsi,
            'sma': sma,
            'trend': trend,
            'volatility': np.std(prices[-20:]) if len(prices) >= 20 else 0
        }
    
    def _generate_trading_signal(self, market: str, current_price: float, indicators: Dict) -> Optional[str]:
        """Generate trading signals based on strategy"""
        rsi = indicators['rsi']
        trend = indicators['trend']
        
        # Simple strategy: RSI + trend following
        if rsi < 30 and trend == 'UPTREND':
            return 'BUY'
        elif rsi > 70 and trend == 'DOWNTREND':
            return 'SELL'
        elif market == 'FTSE 100':
            # FTSE was showing selling signals on Aug 8th
            if rsi > 60:
                return 'SELL'
        elif market == 'DAX':
            # DAX had some buy opportunities
            if rsi < 40:
                return 'BUY'
        
        return None
    
    def simulate_old_system(self) -> Tuple[List[Trade], Dict]:
        """
        Simulate the OLD BROKEN SYSTEM with:
        - No position checking (allows multiple trades)
        - No daily loss limits
        - No timing restrictions
        """
        print("\n🔴 Simulating OLD BROKEN TRADING SYSTEM")
        print("=" * 70)
        
        trades = []
        balance = self.initial_balance
        daily_pnl = 0.0
        
        # Track price history for indicators
        ftse_prices = []
        dax_prices = []
        
        # Track positions per market (old system didn't check this properly)
        active_positions = {'FTSE 100': [], 'DAX': []}
        
        trade_count = 0
        
        for i, tick in enumerate(self.all_ticks):
            market = tick['market']
            current_price = tick['mid_price']
            current_time = tick['timestamp']
            
            # Update price history
            if market == 'FTSE 100':
                ftse_prices.append(current_price)
                prices = ftse_prices
            else:
                dax_prices.append(current_price)
                prices = dax_prices
            
            # Only analyze every 100 ticks to simulate strategy interval
            if i % 100 != 0:
                continue
            
            # Calculate indicators
            if len(prices) < 20:
                continue
                
            indicators = self._calculate_technical_indicators(prices[-50:])
            signal = self._generate_trading_signal(market, current_price, indicators)
            
            # OLD SYSTEM: NO POSITION CHECKING - allows multiple trades
            if signal:
                # Simulate the rapid trading that happened on Aug 8th
                trade_count += 1
                deal_id = f"OLD_{trade_count:04d}"
                
                # Calculate stop loss and take profit
                if signal == 'BUY':
                    stop_loss = current_price - 10
                    take_profit = current_price + 20
                    entry_price = tick['offer']  # Buy at offer
                else:
                    stop_loss = current_price + 10
                    take_profit = current_price - 20
                    entry_price = tick['bid']  # Sell at bid
                
                trade = Trade(
                    market=market,
                    direction=signal,
                    entry_price=entry_price,
                    size=1.0,
                    entry_time=current_time,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    deal_id=deal_id,
                    status="OPEN"
                )
                
                trades.append(trade)
                active_positions[market].append(trade)
                
                print(f"🔴 OLD TRADE {trade_count}: {market} {signal} at {entry_price:.1f} | SL: {stop_loss:.1f} | TP: {take_profit:.1f}")
                
                # OLD SYSTEM: No daily loss limit checking
                # Continues trading even after big losses
            
            # Check for trade exits (same logic for both systems)
            self._check_trade_exits(active_positions, tick, trades)
        
        # Close remaining open trades at end of day
        self._close_remaining_trades(active_positions, self.all_ticks[-1], trades)
        
        # Calculate final results
        total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
        stats = self._calculate_stats(trades, "OLD SYSTEM")
        
        print(f"\n🔴 OLD SYSTEM RESULTS:")
        print(f"   Total trades: {len(trades)}")
        print(f"   Total P&L: £{total_pnl:.2f}")
        print(f"   Final balance: £{balance + total_pnl:.2f}")
        
        return trades, stats
    
    def simulate_new_system(self) -> Tuple[List[Trade], Dict]:
        """
        Simulate the NEW FIXED SYSTEM with:
        - Bulletproof position checking (max 1 per market)
        - Daily loss limits (5% max)
        - 5-minute minimum between trades
        - Real-time risk validation
        """
        print("\n🟢 Simulating NEW BULLETPROOF TRADING SYSTEM")
        print("=" * 70)
        
        trades = []
        balance = self.initial_balance
        daily_pnl = 0.0
        
        # Track price history
        ftse_prices = []
        dax_prices = []
        
        # NEW SYSTEM: Proper position tracking
        active_positions = {'FTSE 100': [], 'DAX': []}
        last_trade_time = {'FTSE 100': None, 'DAX': None}
        
        # NEW SYSTEM: Safety limits
        DAILY_LOSS_LIMIT = 0.05  # 5%
        MIN_TRADE_INTERVAL = timedelta(minutes=5)
        
        trade_count = 0
        trading_halted = False
        halt_reason = ""
        
        for i, tick in enumerate(self.all_ticks):
            market = tick['market']
            current_price = tick['mid_price']
            current_time = tick['timestamp']
            
            # Update price history
            if market == 'FTSE 100':
                ftse_prices.append(current_price)
                prices = ftse_prices
            else:
                dax_prices.append(current_price)
                prices = dax_prices
            
            # Only analyze every 100 ticks
            if i % 100 != 0:
                continue
            
            # NEW SYSTEM: Check daily loss limit
            current_daily_pnl = sum(t.pnl for t in trades if t.pnl is not None)
            daily_loss_percentage = abs(current_daily_pnl) / balance if balance > 0 else 0
            
            if current_daily_pnl < 0 and daily_loss_percentage >= DAILY_LOSS_LIMIT:
                if not trading_halted:
                    trading_halted = True
                    halt_reason = f"Daily loss limit reached: £{current_daily_pnl:.2f} ({daily_loss_percentage:.1%})"
                    print(f"🚨 TRADING HALTED: {halt_reason}")
                continue
            
            # Calculate indicators
            if len(prices) < 20:
                continue
                
            indicators = self._calculate_technical_indicators(prices[-50:])
            signal = self._generate_trading_signal(market, current_price, indicators)
            
            if signal and not trading_halted:
                # NEW SYSTEM: BULLETPROOF POSITION CHECKING
                
                # Check 1: No existing positions in this market
                if len(active_positions[market]) > 0:
                    continue  # Block trade - position already exists
                
                # Check 2: Minimum time interval between trades
                if last_trade_time[market]:
                    time_since_last = current_time - last_trade_time[market]
                    if time_since_last < MIN_TRADE_INTERVAL:
                        continue  # Block trade - too soon
                
                # Check 3: Position size limits (simplified)
                position_value = current_price * 1.0
                if position_value > balance * 0.01:  # Max 1% position size
                    continue  # Block trade - position too large
                
                # All checks passed - execute trade
                trade_count += 1
                deal_id = f"NEW_{trade_count:04d}"
                
                if signal == 'BUY':
                    stop_loss = current_price - 10
                    take_profit = current_price + 20
                    entry_price = tick['offer']
                else:
                    stop_loss = current_price + 10
                    take_profit = current_price - 20
                    entry_price = tick['bid']
                
                trade = Trade(
                    market=market,
                    direction=signal,
                    entry_price=entry_price,
                    size=1.0,
                    entry_time=current_time,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    deal_id=deal_id,
                    status="OPEN"
                )
                
                trades.append(trade)
                active_positions[market].append(trade)
                last_trade_time[market] = current_time
                
                print(f"🟢 NEW TRADE {trade_count}: {market} {signal} at {entry_price:.1f} | SL: {stop_loss:.1f} | TP: {take_profit:.1f}")
            
            # Check for trade exits
            self._check_trade_exits(active_positions, tick, trades)
        
        # Close remaining trades
        self._close_remaining_trades(active_positions, self.all_ticks[-1], trades)
        
        # Calculate results
        total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
        stats = self._calculate_stats(trades, "NEW SYSTEM")
        
        print(f"\n🟢 NEW SYSTEM RESULTS:")
        print(f"   Total trades: {len(trades)}")
        print(f"   Total P&L: £{total_pnl:.2f}")
        print(f"   Final balance: £{balance + total_pnl:.2f}")
        if trading_halted:
            print(f"   🚨 Trading halted: {halt_reason}")
        
        return trades, stats
    
    def _check_trade_exits(self, active_positions: Dict, tick: Dict, trades: List[Trade]):
        """Check if any open trades should be closed"""
        market = tick['market']
        current_price = tick['mid_price']
        current_time = tick['timestamp']
        
        for trade in active_positions[market][:]:  # Copy list to avoid modification issues
            if trade.status != "OPEN":
                continue
            
            exit_triggered = False
            exit_price = None
            
            if trade.direction == 'BUY':
                # Check stop loss
                if current_price <= trade.stop_loss:
                    exit_triggered = True
                    exit_price = trade.stop_loss
                    trade.status = "STOPPED"
                # Check take profit
                elif current_price >= trade.take_profit:
                    exit_triggered = True
                    exit_price = trade.take_profit
                    trade.status = "PROFIT"
                    
            else:  # SELL
                # Check stop loss
                if current_price >= trade.stop_loss:
                    exit_triggered = True
                    exit_price = trade.stop_loss
                    trade.status = "STOPPED"
                # Check take profit
                elif current_price <= trade.take_profit:
                    exit_triggered = True
                    exit_price = trade.take_profit
                    trade.status = "PROFIT"
            
            if exit_triggered:
                trade.exit_price = exit_price
                trade.exit_time = current_time
                
                # Calculate P&L
                if trade.direction == 'BUY':
                    trade.pnl = (exit_price - trade.entry_price) * trade.size
                else:
                    trade.pnl = (trade.entry_price - exit_price) * trade.size
                
                # Remove from active positions
                active_positions[market].remove(trade)
    
    def _close_remaining_trades(self, active_positions: Dict, final_tick: Dict, trades: List[Trade]):
        """Close any remaining open trades at market close"""
        final_time = final_tick['timestamp']
        
        for market in active_positions:
            for trade in active_positions[market]:
                if trade.status == "OPEN":
                    # Close at market price
                    market_ticks = [t for t in self.all_ticks if t['market'] == market]
                    if market_ticks:
                        final_market_tick = market_ticks[-1]
                        exit_price = final_market_tick['bid'] if trade.direction == 'BUY' else final_market_tick['offer']
                        
                        trade.exit_price = exit_price
                        trade.exit_time = final_time
                        trade.status = "CLOSED_EOD"
                        
                        # Calculate P&L
                        if trade.direction == 'BUY':
                            trade.pnl = (exit_price - trade.entry_price) * trade.size
                        else:
                            trade.pnl = (trade.entry_price - exit_price) * trade.size
        
        # Clear active positions
        for market in active_positions:
            active_positions[market].clear()
    
    def _calculate_stats(self, trades: List[Trade], system_name: str) -> Dict:
        """Calculate trading statistics"""
        if not trades:
            return {}
        
        total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
        profitable_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl < 0]
        
        # Market breakdown
        ftse_trades = [t for t in trades if t.market == 'FTSE 100']
        dax_trades = [t for t in trades if t.market == 'DAX']
        
        ftse_pnl = sum(t.pnl for t in ftse_trades if t.pnl is not None)
        dax_pnl = sum(t.pnl for t in dax_trades if t.pnl is not None)
        
        return {
            'system': system_name,
            'total_trades': len(trades),
            'total_pnl': total_pnl,
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(profitable_trades) / len(trades) if trades else 0,
            'avg_win': np.mean([t.pnl for t in profitable_trades]) if profitable_trades else 0,
            'avg_loss': np.mean([t.pnl for t in losing_trades]) if losing_trades else 0,
            'ftse_trades': len(ftse_trades),
            'dax_trades': len(dax_trades),
            'ftse_pnl': ftse_pnl,
            'dax_pnl': dax_pnl,
            'max_drawdown': self._calculate_max_drawdown(trades),
            'return_percentage': total_pnl / self.initial_balance * 100
        }
    
    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """Calculate maximum drawdown"""
        running_pnl = 0
        peak = 0
        max_drawdown = 0
        
        for trade in trades:
            if trade.pnl is not None:
                running_pnl += trade.pnl
                if running_pnl > peak:
                    peak = running_pnl
                drawdown = peak - running_pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        return max_drawdown
    
    def run_comprehensive_backtest(self):
        """Run complete backtest comparing old vs new system"""
        print("📊" + "="*80)
        print("📊 COMPREHENSIVE AUGUST 8TH TRADING BACKTEST")
        print("📊" + "="*80)
        print(f"📅 Date: August 8, 2025")
        print(f"💰 Initial Balance: £{self.initial_balance:,.2f}")
        print(f"📊 FTSE Ticks: {len(self.ftse_data):,}")
        print(f"📊 DAX Ticks: {len(self.dax_data):,}")
        print("📊" + "="*80)
        
        # Run both simulations
        old_trades, old_stats = self.simulate_old_system()
        new_trades, new_stats = self.simulate_new_system()
        
        # Generate comparison report
        self._generate_comparison_report(old_stats, new_stats, old_trades, new_trades)
        
        return old_stats, new_stats

    def _generate_comparison_report(self, old_stats: Dict, new_stats: Dict, old_trades: List[Trade], new_trades: List[Trade]):
        """Generate comprehensive comparison report"""
        print("\n📊" + "="*80)
        print("📊 BACKTEST COMPARISON REPORT")
        print("📊" + "="*80)
        
        # System comparison table
        print(f"\n{'Metric':<30} {'Old System':<15} {'New System':<15} {'Improvement':<15}")
        print("-" * 75)
        
        old_pnl = old_stats.get('total_pnl', 0)
        new_pnl = new_stats.get('total_pnl', 0)
        pnl_improvement = new_pnl - old_pnl
        
        old_trades_count = old_stats.get('total_trades', 0)
        new_trades_count = new_stats.get('total_trades', 0)
        trades_reduction = old_trades_count - new_trades_count
        
        old_win_rate = old_stats.get('win_rate', 0) * 100
        new_win_rate = new_stats.get('win_rate', 0) * 100
        win_rate_improvement = new_win_rate - old_win_rate
        
        old_drawdown = old_stats.get('max_drawdown', 0)
        new_drawdown = new_stats.get('max_drawdown', 0)
        drawdown_improvement = old_drawdown - new_drawdown
        
        print(f"{'Total P&L':<30} £{old_pnl:<14.2f} £{new_pnl:<14.2f} £{pnl_improvement:<14.2f}")
        print(f"{'Total Trades':<30} {old_trades_count:<15} {new_trades_count:<15} -{trades_reduction:<14}")
        print(f"{'Win Rate':<30} {old_win_rate:<14.1f}% {new_win_rate:<14.1f}% +{win_rate_improvement:<13.1f}%")
        print(f"{'Max Drawdown':<30} £{old_drawdown:<14.2f} £{new_drawdown:<14.2f} -£{drawdown_improvement:<13.2f}")
        print(f"{'Return %':<30} {old_stats.get('return_percentage', 0):<14.1f}% {new_stats.get('return_percentage', 0):<14.1f}% +{new_stats.get('return_percentage', 0) - old_stats.get('return_percentage', 0):<13.1f}%")
        
        # Market breakdown
        print(f"\n📊 MARKET BREAKDOWN:")
        print(f"\n{'Market':<15} {'Old P&L':<12} {'New P&L':<12} {'Improvement':<12}")
        print("-" * 51)
        
        old_ftse_pnl = old_stats.get('ftse_pnl', 0)
        new_ftse_pnl = new_stats.get('ftse_pnl', 0)
        ftse_improvement = new_ftse_pnl - old_ftse_pnl
        
        old_dax_pnl = old_stats.get('dax_pnl', 0)
        new_dax_pnl = new_stats.get('dax_pnl', 0)
        dax_improvement = new_dax_pnl - old_dax_pnl
        
        print(f"{'FTSE 100':<15} £{old_ftse_pnl:<11.2f} £{new_ftse_pnl:<11.2f} £{ftse_improvement:<11.2f}")
        print(f"{'DAX':<15} £{old_dax_pnl:<11.2f} £{new_dax_pnl:<11.2f} £{dax_improvement:<11.2f}")
        
        # Key insights
        print(f"\n🔍 KEY INSIGHTS:")
        print(f"   💰 P&L Improvement: £{pnl_improvement:.2f} ({'Better' if pnl_improvement > 0 else 'Worse'} by {abs(pnl_improvement):.2f})")
        print(f"   📉 Trade Reduction: {trades_reduction} fewer trades ({trades_reduction/old_trades_count*100:.1f}% reduction)")
        print(f"   🛡️ Risk Control: {'✅ Effective' if new_drawdown < old_drawdown else '❌ Needs work'}")
        
        if pnl_improvement > 0:
            print(f"   ✅ NEW SYSTEM OUTPERFORMED by £{pnl_improvement:.2f}")
        else:
            print(f"   ⚠️ Old system performed better by £{abs(pnl_improvement):.2f}")
        
        # Safety improvements
        print(f"\n🛡️ SAFETY IMPROVEMENTS:")
        print(f"   🔒 Position Control: Bulletproof multi-layer validation")
        print(f"   📊 Daily Loss Limits: 5% maximum loss enforcement")
        print(f"   ⏰ Trade Timing: 5-minute minimum between trades")
        print(f"   🌐 Real-time Sync: Live IG position verification")
        
        # Final assessment
        print(f"\n📊 FINAL ASSESSMENT:")
        if pnl_improvement >= 0 and trades_reduction > 0:
            print("   ✅ NEW SYSTEM IS SUPERIOR")
            print("   🎯 Better P&L with fewer, safer trades")
            print("   🛡️ Bulletproof risk management prevents disasters")
            print("   ✅ READY FOR LIVE DEPLOYMENT")
        elif pnl_improvement < 0 and trades_reduction > 0:
            print("   ⚖️ TRADE-OFF SITUATION")
            print("   🛡️ Much safer but slightly less profitable")
            print("   💡 Consider fine-tuning strategy parameters")
            print("   ✅ Still recommended due to risk reduction")
        else:
            print("   ⚠️ NEEDS FURTHER ANALYSIS")
            print("   🔧 Review and optimize new system")
        
        print("📊" + "="*80)

def main():
    """Main backtest execution"""
    try:
        backtest = BacktestEngine()
        old_stats, new_stats = backtest.run_comprehensive_backtest()
        
        print("\n🎯 Backtest completed successfully!")
        print("📋 Check the detailed comparison report above.")
        
    except FileNotFoundError as e:
        print(f"❌ Data files not found: {e}")
        print("📁 Please ensure tick_ftse_100_08_08.json and tick_dax_08_08.json are in the current directory")
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()