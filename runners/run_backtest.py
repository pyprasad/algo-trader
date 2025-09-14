#!/usr/bin/env python3.12
# runners/run_backtest.py

import os
import sys
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the exact same components used in run_multi_market.py
from core.enhanced_strategy_engine import get_enhanced_strategy_engine
from core.trade_executor import execute_trade
from data.db import log_trade, get_account_balance, update_account_balance
from utils.market_config_loader import MarketConfigLoader
from utils.trading_safety import get_trading_safety_manager
from core.dynamic_position_manager import get_dynamic_position_manager

class HistoricalDataBacktester:
    """
    Backtesting system that uses the exact same methods as run_multi_market.py
    but feeds historical tick data instead of live streaming data
    """
    
    def __init__(self, tick_data_files: List[str], config_loader: MarketConfigLoader = None):
        """
        Initialize backtester with historical tick data files
        
        Args:
            tick_data_files: List of paths to JSON tick data files
            config_loader: Configuration loader instance
        """
        self.tick_data_files = tick_data_files
        self.config_loader = config_loader or MarketConfigLoader()
        
        # Use the same components as run_multi_market.py
        self.enhanced_strategy_engine = get_enhanced_strategy_engine()
        self.safety_manager = get_trading_safety_manager()
        self.dynamic_position_manager = get_dynamic_position_manager()
        
        # Load configuration - same as live system
        valid_markets, invalid_markets = self.config_loader.validate_active_markets()
        self.markets = valid_markets
        self.risk_config = self.config_loader.get_risk_config()
        
        # Initialize tracking
        self.trades = []
        self.pnl_list = []
        self.positions = {}  # Track open positions
        self.initial_balance = get_account_balance()
        self.current_balance = self.initial_balance
        
        print(f"🔄 Backtester initialized")
        print(f"📊 Markets: {', '.join(self.markets)}")
        print(f"📁 Data files: {len(tick_data_files)}")
        print(f"💰 Initial balance: £{self.initial_balance:.2f}")
    
    def load_tick_data(self, file_path: str) -> pd.DataFrame:
        """
        Load tick data from JSON file - same format as MongoDB
        
        Args:
            file_path: Path to JSON tick data file
            
        Returns:
            DataFrame with tick data
        """
        print(f"📁 Loading tick data from {os.path.basename(file_path)}")
        
        ticks = []
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    tick = json.loads(line.strip())
                    # Convert MongoDB timestamp format to datetime
                    if 'timestamp' in tick and '$date' in tick['timestamp']:
                        tick['timestamp'] = datetime.fromisoformat(
                            tick['timestamp']['$date'].replace('Z', '+00:00')
                        )
                    ticks.append(tick)
        
        df = pd.DataFrame(ticks)
        df = df.sort_values('timestamp')  # Ensure chronological order
        
        print(f"✅ Loaded {len(df)} ticks from {tick['market']} ({df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']})")
        return df
    
    def simulate_trade_execution(self, market_name: str, direction: str, current_tick: Dict, 
                               strategy_sl: float, strategy_tp: float, strategy_signals: Dict) -> Dict:
        """
        Simulate trade execution - mimics execute_trade() but for backtesting
        
        Args:
            market_name: Market to trade
            direction: 'BUY' or 'SELL'
            current_tick: Current tick data
            strategy_sl: Stop loss value
            strategy_tp: Take profit value
            strategy_signals: Strategy analysis results
            
        Returns:
            Trade execution result
        """
        
        # Use same pricing logic as live system
        if direction == 'BUY':
            entry_price = current_tick['offer']  # Pay the spread when buying
            stop_loss_price = entry_price - strategy_sl
            take_profit_price = entry_price + strategy_tp
        else:  # SELL
            entry_price = current_tick['bid']    # Pay the spread when selling
            stop_loss_price = entry_price + strategy_sl
            take_profit_price = entry_price - strategy_tp
        
        # Use same position sizing logic as live system
        position_size = 1.0  # Default from config
        
        # Create trade record - same format as live system
        trade = {
            'trade_id': len(self.trades) + 1,
            'timestamp': current_tick['timestamp'],
            'market': market_name,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'position_size': position_size,
            'strategy_signals': strategy_signals,
            'status': 'OPEN'
        }
        
        # Track open position
        self.positions[market_name] = trade
        self.trades.append(trade)
        
        print(f"📈 {market_name} {direction} @ £{entry_price:.2f} | SL: £{stop_loss_price:.2f} | TP: £{take_profit_price:.2f}")
        
        return {'dealStatus': 'ACCEPTED', 'deal_id': trade['trade_id']}
    
    def check_position_exits(self, market_name: str, current_tick: Dict):
        """
        Check if open positions should be closed (stop loss or take profit hit)
        
        Args:
            market_name: Market name
            current_tick: Current tick data
        """
        if market_name not in self.positions:
            return
        
        position = self.positions[market_name]
        current_price = current_tick['midprice']
        
        exit_triggered = False
        exit_reason = None
        exit_price = None
        
        if position['direction'] == 'BUY':
            # Check stop loss (price fell below SL)
            if current_price <= position['stop_loss_price']:
                exit_triggered = True
                exit_reason = 'STOP_LOSS'
                exit_price = current_tick['bid']  # Sell at bid when closing long
            
            # Check take profit (price rose above TP)
            elif current_price >= position['take_profit_price']:
                exit_triggered = True
                exit_reason = 'TAKE_PROFIT'
                exit_price = current_tick['bid']  # Sell at bid when closing long
        
        else:  # SELL position
            # Check stop loss (price rose above SL)
            if current_price >= position['stop_loss_price']:
                exit_triggered = True
                exit_reason = 'STOP_LOSS'
                exit_price = current_tick['offer']  # Buy at offer when closing short
            
            # Check take profit (price fell below TP)
            elif current_price <= position['take_profit_price']:
                exit_triggered = True
                exit_reason = 'TAKE_PROFIT'
                exit_price = current_tick['offer']  # Buy at offer when closing short
        
        if exit_triggered:
            # Calculate P&L
            if position['direction'] == 'BUY':
                pnl = (exit_price - position['entry_price']) * position['position_size']
            else:  # SELL
                pnl = (position['entry_price'] - exit_price) * position['position_size']
            
            # Update trade record
            position['exit_price'] = exit_price
            position['exit_timestamp'] = current_tick['timestamp']
            position['exit_reason'] = exit_reason
            position['pnl'] = pnl
            position['status'] = 'CLOSED'
            
            # Add to P&L list
            pnl_record = {
                'trade_id': position['trade_id'],
                'timestamp': current_tick['timestamp'],
                'market': market_name,
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'position_size': position['position_size'],
                'pnl': pnl,
                'exit_reason': exit_reason,
                'duration_minutes': int((current_tick['timestamp'] - position['timestamp']).total_seconds() / 60)
            }
            self.pnl_list.append(pnl_record)
            
            # Update balance
            self.current_balance += pnl
            
            # Remove from open positions
            del self.positions[market_name]
            
            print(f"🔚 {market_name} {position['direction']} closed @ £{exit_price:.2f} | {exit_reason} | P&L: £{pnl:.2f}")
    
    def run_backtest(self):
        """
        Run the backtest using the same logic as run_multi_market.py
        """
        print("🚀 Starting Historical Backtest...")
        print("=" * 60)
        
        # Process each tick data file
        for file_path in self.tick_data_files:
            tick_data = self.load_tick_data(file_path)
            market_name = tick_data.iloc[0]['market']
            
            print(f"📊 Processing {market_name}...")
            
            # Process ticks in chronological order - same as live system
            for i, (_, current_tick) in enumerate(tick_data.iterrows()):
                
                # Check for position exits first
                self.check_position_exits(market_name, current_tick.to_dict())
                
                # Only analyze for new signals if we have enough historical data
                if i < 50:  # Need minimum data like live system
                    continue
                
                # Skip if already have position in this market
                if market_name in self.positions:
                    continue
                
                # Get recent tick data for analysis - same as live system  
                recent_ticks = tick_data.iloc[max(0, i-50):i+1]
                prices = recent_ticks['bid'].tolist()  # Same as live system
                
                if len(prices) < 20:  # Same minimum as live system
                    continue
                
                # Run enhanced strategy analysis - EXACT SAME METHOD
                signals = self.enhanced_strategy_engine.analyze_market_conditions(prices, market_name)
                
                if signals and signals.get('signal') in ['BUY', 'SELL']:
                    print(f"🎯 {market_name} TRADING SIGNAL: {signals['signal']}")
                    
                    # SAFETY CHECK - same as live system
                    can_trade, safety_reason = self.safety_manager.validate_trade(market_name, signals['signal'])
                    
                    if not can_trade:
                        print(f"🛡️ {market_name} Trade blocked by safety manager: {safety_reason}")
                        continue
                    
                    # Execute trade - simulate instead of real execution
                    trade_result = self.simulate_trade_execution(
                        market_name=market_name,
                        direction=signals['signal'],
                        current_tick=current_tick.to_dict(),
                        strategy_sl=signals.get('atr', 10),
                        strategy_tp=signals.get('atr', 20) * 2,
                        strategy_signals=signals
                    )
                    
                    if 'error' not in trade_result:
                        print(f"✅ {market_name} Trade executed: {trade_result.get('dealStatus', 'Unknown')}")
        
        # Close any remaining open positions at end of data
        print("🔄 Closing remaining open positions...")
        for market_name, position in list(self.positions.items()):
            # Find last tick for this market
            for file_path in self.tick_data_files:
                tick_data = self.load_tick_data(file_path)
                if tick_data.iloc[0]['market'] == market_name:
                    last_tick = tick_data.iloc[-1]
                    exit_price = last_tick['midprice']
                    
                    # Calculate final P&L
                    if position['direction'] == 'BUY':
                        pnl = (exit_price - position['entry_price']) * position['position_size']
                    else:
                        pnl = (position['entry_price'] - exit_price) * position['position_size']
                    
                    # Add to P&L list
                    pnl_record = {
                        'trade_id': position['trade_id'],
                        'timestamp': last_tick['timestamp'],
                        'market': market_name,
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'position_size': position['position_size'],
                        'pnl': pnl,
                        'exit_reason': 'END_OF_DATA',
                        'duration_minutes': int((last_tick['timestamp'] - position['timestamp']).total_seconds() / 60)
                    }
                    self.pnl_list.append(pnl_record)
                    self.current_balance += pnl
                    break
        
        self.positions.clear()
        
        print("✅ Backtest completed!")
        self.generate_results()
    
    def generate_results(self):
        """Generate and display backtest results"""
        print("=" * 60)
        print("📊 BACKTEST RESULTS")
        print("=" * 60)
        
        if not self.pnl_list:
            print("❌ No trades executed during backtest")
            return
        
        # Calculate performance metrics
        total_trades = len(self.pnl_list)
        winning_trades = len([t for t in self.pnl_list if t['pnl'] > 0])
        losing_trades = len([t for t in self.pnl_list if t['pnl'] < 0])
        
        total_pnl = sum([t['pnl'] for t in self.pnl_list])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        avg_win = sum([t['pnl'] for t in self.pnl_list if t['pnl'] > 0]) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum([t['pnl'] for t in self.pnl_list if t['pnl'] < 0]) / losing_trades if losing_trades > 0 else 0
        
        print(f"💰 Total P&L: £{total_pnl:.2f}")
        print(f"📈 Initial Balance: £{self.initial_balance:.2f}")
        print(f"💵 Final Balance: £{self.current_balance:.2f}")
        print(f"📊 Total Trades: {total_trades}")
        print(f"✅ Winning Trades: {winning_trades}")
        print(f"❌ Losing Trades: {losing_trades}")
        print(f"🎯 Win Rate: {win_rate:.1f}%")
        print(f"📊 Average Win: £{avg_win:.2f}")
        print(f"📊 Average Loss: £{avg_loss:.2f}")
        
        # Display detailed P&L list
        print("\n" + "=" * 80)
        print("📋 DETAILED P&L LIST")
        print("=" * 80)
        print(f"{'ID':<4} {'Timestamp':<20} {'Market':<12} {'Dir':<4} {'Entry':<8} {'Exit':<8} {'P&L':<10} {'Reason':<12}")
        print("-" * 80)
        
        for trade in self.pnl_list:
            print(f"{trade['trade_id']:<4} {trade['timestamp'].strftime('%Y-%m-%d %H:%M'):<20} "
                  f"{trade['market']:<12} {trade['direction']:<4} £{trade['entry_price']:<7.2f} "
                  f"£{trade['exit_price']:<7.2f} £{trade['pnl']:<9.2f} {trade['exit_reason']:<12}")
        
        return self.pnl_list


def main():
    """Main function to run backtest"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run backtest using historical tick data')
    parser.add_argument('tick_files', nargs='+', help='Paths to tick data JSON files')
    args = parser.parse_args()
    
    # Validate files exist
    for file_path in args.tick_files:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
    
    print("🔄 Initializing backtest system...")
    config_loader = MarketConfigLoader()
    
    # Create backtester and run
    backtester = HistoricalDataBacktester(args.tick_files, config_loader)
    backtester.run_backtest()


if __name__ == "__main__":
    main()