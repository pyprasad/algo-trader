#!/usr/bin/env python3
"""
Comprehensive Backtesting Engine for Multi-Market Algorithm
Processes CSV tick data through the same strategy logic used in live trading
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings("ignore")

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import strategy modules
from models.rsi import compute_rsi
from models.atr import compute_atr
from models.ema import compute_ema

@dataclass
class BacktestTrade:
    """Individual backtest trade record"""
    timestamp: datetime
    market: str
    signal: str
    entry_price: float
    exit_price: float
    pnl: float
    cumulative_pnl: float
    duration_minutes: int
    rsi_entry: float
    atr_entry: float
    spread_cost: float
    win: bool

class TickDataProcessor:
    """Processes CSV tick data for backtesting"""
    
    def __init__(self):
        self.ftse_data = None
        self.dax_data = None
    
    def load_tick_data(self):
        """Load both FTSE 100 and DAX tick data"""
        print("Loading tick data...")
        
        # Load FTSE 100 data
        self.ftse_data = pd.read_csv('ticks_ftse_100.csv')
        self.ftse_data['timestamp'] = pd.to_datetime(self.ftse_data['timestamp'])
        self.ftse_data = self.ftse_data.sort_values('timestamp')
        print(f"FTSE 100: {len(self.ftse_data)} ticks loaded")
        
        # Load DAX data
        self.dax_data = pd.read_csv('ticks_dax.csv')
        self.dax_data['timestamp'] = pd.to_datetime(self.dax_data['timestamp'])
        self.dax_data = self.dax_data.sort_values('timestamp')
        print(f"DAX: {len(self.dax_data)} ticks loaded")
        
        return True
    
    def get_price_series(self, market: str, lookback: int = 50) -> Tuple[List[float], datetime]:
        """Get recent price series for analysis"""
        if market == 'FTSE 100':
            data = self.ftse_data
        elif market == 'DAX':
            data = self.dax_data
        else:
            return [], None
        
        if len(data) < lookback:
            return [], None
        
        # Use bid prices for analysis (more conservative)
        prices = data['bid'].tail(lookback).tolist()
        latest_timestamp = data['timestamp'].iloc[-1]
        
        return prices, latest_timestamp
    
    def get_current_spread(self, market: str) -> float:
        """Get current bid-offer spread"""
        if market == 'FTSE 100':
            data = self.ftse_data
        elif market == 'DAX':
            data = self.dax_data
        else:
            return 4.0  # Default spread
        
        if len(data) == 0:
            return 4.0
        
        latest = data.iloc[-1]
        return latest['offer'] - latest['bid']

class SimplifiedStrategyEngine:
    """Simplified version of the enhanced strategy engine for backtesting"""
    
    def __init__(self):
        # Market-specific parameters based on your live system
        self.market_params = {
            'FTSE 100': {
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'min_confidence': 0.6,
                'atr_multiplier': 2.0
            },
            'DAX': {
                'rsi_oversold': 25,  # More conservative for DAX
                'rsi_overbought': 75,
                'min_confidence': 0.7,  # Higher confidence required
                'atr_multiplier': 2.5
            }
        }
    
    def analyze_market_conditions(self, prices: List[float], market: str) -> Optional[Dict]:
        """Analyze market conditions and generate trading signals"""
        if len(prices) < 20:
            return None
        
        try:
            # Calculate technical indicators
            rsi = compute_rsi(prices, period=14)
            atr = compute_atr(prices, period=14)
            ema_20 = compute_ema(prices, period=20)
            
            if any(x is None or (isinstance(x, list) and len(x) == 0) for x in [rsi, atr, ema_20]):
                return None
            
            current_price = prices[-1]
            params = self.market_params.get(market, self.market_params['FTSE 100'])
            
            # Generate signals based on RSI and trend
            signal = 'HOLD'
            confidence = 0.0
            
            # RSI-based signals
            if isinstance(rsi, list) and len(rsi) > 0:
                current_rsi = rsi[-1]
            else:
                current_rsi = rsi
            
            if isinstance(ema_20, list) and len(ema_20) > 0:
                current_ema = ema_20[-1]
            else:
                current_ema = ema_20
            
            # Trend direction
            trend_up = current_price > current_ema
            
            # Generate buy/sell signals
            if current_rsi < params['rsi_oversold'] and trend_up:
                signal = 'BUY'
                confidence = (params['rsi_oversold'] - current_rsi) / params['rsi_oversold']
            elif current_rsi > params['rsi_overbought'] and not trend_up:
                signal = 'SELL'
                confidence = (current_rsi - params['rsi_overbought']) / (100 - params['rsi_overbought'])
            
            # Apply minimum confidence filter
            if confidence < params['min_confidence']:
                signal = 'HOLD'
            
            return {
                'signal': signal,
                'confidence': confidence,
                'rsi': current_rsi,
                'atr': atr[-1] if isinstance(atr, list) else atr,
                'price': current_price,
                'ema': current_ema
            }
            
        except Exception as e:
            print(f"Error in strategy analysis: {e}")
            return None

class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self):
        self.data_processor = TickDataProcessor()
        self.strategy = SimplifiedStrategyEngine()
        self.trades = []
        self.positions = {}  # Current positions by market
        self.cumulative_pnl = 0.0
        
        # Backtesting parameters
        self.commission = 0.5  # £0.50 per trade
        self.position_size = 1.0  # 1 unit per trade
        self.max_trade_duration = 60  # Max 60 minutes per trade
        
    def run_backtest(self) -> Dict:
        """Run comprehensive backtest on historical data"""
        print("=== STARTING COMPREHENSIVE BACKTEST ===")
        
        # Load data
        if not self.data_processor.load_tick_data():
            print("Failed to load tick data!")
            return {}
        
        # Process each market
        results = {}
        
        for market in ['FTSE 100', 'DAX']:
            print(f"\n--- Backtesting {market} ---")
            market_results = self._backtest_market(market)
            results[market] = market_results
        
        # Combine results
        combined_results = self._combine_results(results)
        
        return combined_results
    
    def _backtest_market(self, market: str) -> Dict:
        """Backtest a specific market"""
        market_trades = []
        current_position = None
        lookback_window = 50
        analysis_interval = 20  # Analyze every 20 ticks
        
        # Get market data
        if market == 'FTSE 100':
            data = self.data_processor.ftse_data
        else:
            data = self.data_processor.dax_data
        
        print(f"Processing {len(data)} ticks for {market}")
        
        # Iterate through data with analysis intervals
        for i in range(lookback_window, len(data), analysis_interval):
            try:
                # Get price series for analysis
                prices = data['bid'].iloc[i-lookback_window:i].tolist()
                current_time = data['timestamp'].iloc[i]
                current_bid = data['bid'].iloc[i]
                current_offer = data['offer'].iloc[i]
                
                # Analyze market conditions
                analysis = self.strategy.analyze_market_conditions(prices, market)
                
                if not analysis:
                    continue
                
                # Check for position exit first
                if current_position:
                    exit_signal = self._check_exit_conditions(current_position, current_time, current_bid, current_offer, analysis)
                    if exit_signal:
                        trade = self._close_position(current_position, current_time, current_bid, current_offer, exit_signal['reason'])
                        if trade:
                            market_trades.append(trade)
                        current_position = None
                
                # Check for new entry signals
                if not current_position and analysis['signal'] in ['BUY', 'SELL']:
                    current_position = self._open_position(market, analysis, current_time, current_bid, current_offer)
                
            except Exception as e:
                print(f"Error processing tick {i}: {e}")
                continue
        
        # Close any remaining position
        if current_position:
            final_data = data.iloc[-1]
            trade = self._close_position(current_position, final_data['timestamp'], final_data['bid'], final_data['offer'], 'end_of_data')
            if trade:
                market_trades.append(trade)
        
        # Calculate market-specific metrics
        return self._calculate_market_metrics(market, market_trades)
    
    def _open_position(self, market: str, analysis: Dict, timestamp: datetime, bid: float, offer: float) -> Dict:
        """Open a new trading position"""
        signal = analysis['signal']
        
        # Determine entry price based on signal direction
        if signal == 'BUY':
            entry_price = offer  # Buy at offer price
        else:  # SELL
            entry_price = bid   # Sell at bid price
        
        position = {
            'market': market,
            'signal': signal,
            'entry_time': timestamp,
            'entry_price': entry_price,
            'entry_rsi': analysis['rsi'],
            'entry_atr': analysis['atr'],
            'confidence': analysis['confidence']
        }
        
        return position
    
    def _check_exit_conditions(self, position: Dict, current_time: datetime, bid: float, offer: float, analysis: Dict) -> Optional[Dict]:
        """Check if position should be closed"""
        # Time-based exit (max duration)
        duration = (current_time - position['entry_time']).total_seconds() / 60
        if duration >= self.max_trade_duration:
            return {'reason': 'time_limit'}
        
        # Signal reversal exit
        if position['signal'] == 'BUY' and analysis['signal'] == 'SELL':
            return {'reason': 'signal_reversal'}
        elif position['signal'] == 'SELL' and analysis['signal'] == 'BUY':
            return {'reason': 'signal_reversal'}
        
        # Simple profit target / stop loss (using ATR)
        atr = position['entry_atr']
        entry_price = position['entry_price']
        
        if position['signal'] == 'BUY':
            current_price = bid  # Exit at bid when closing long
            profit_target = entry_price + (atr * 2)
            stop_loss = entry_price - (atr * 1)
            
            if current_price >= profit_target:
                return {'reason': 'profit_target'}
            elif current_price <= stop_loss:
                return {'reason': 'stop_loss'}
        else:  # SELL
            current_price = offer  # Exit at offer when closing short
            profit_target = entry_price - (atr * 2)
            stop_loss = entry_price + (atr * 1)
            
            if current_price <= profit_target:
                return {'reason': 'profit_target'}
            elif current_price >= stop_loss:
                return {'reason': 'stop_loss'}
        
        return None
    
    def _close_position(self, position: Dict, timestamp: datetime, bid: float, offer: float, reason: str) -> Optional[BacktestTrade]:
        """Close a trading position and calculate P&L"""
        signal = position['signal']
        entry_price = position['entry_price']
        
        # Determine exit price based on position direction
        if signal == 'BUY':
            exit_price = bid  # Close long at bid price
        else:  # SELL
            exit_price = offer  # Close short at offer price
        
        # Calculate P&L
        if signal == 'BUY':
            pnl = (exit_price - entry_price) * self.position_size
        else:  # SELL
            pnl = (entry_price - exit_price) * self.position_size
        
        # Subtract commission
        pnl -= self.commission
        
        # Calculate spread cost
        spread_cost = abs(offer - bid)
        
        # Update cumulative P&L
        self.cumulative_pnl += pnl
        
        # Calculate duration
        duration_minutes = (timestamp - position['entry_time']).total_seconds() / 60
        
        trade = BacktestTrade(
            timestamp=timestamp,
            market=position['market'],
            signal=signal,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            cumulative_pnl=self.cumulative_pnl,
            duration_minutes=int(duration_minutes),
            rsi_entry=position['entry_rsi'],
            atr_entry=position['entry_atr'],
            spread_cost=spread_cost,
            win=pnl > 0
        )
        
        return trade
    
    def _calculate_market_metrics(self, market: str, trades: List[BacktestTrade]) -> Dict:
        """Calculate performance metrics for a market"""
        if not trades:
            return {
                'market': market,
                'total_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_pnl': 0.0
            }
        
        total_trades = len(trades)
        total_pnl = sum(t.pnl for t in trades)
        winning_trades = [t for t in trades if t.win]
        losing_trades = [t for t in trades if not t.win]
        
        win_rate = len(winning_trades) / total_trades * 100
        avg_pnl = total_pnl / total_trades
        
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        profit_factor = abs(sum(t.pnl for t in winning_trades) / sum(t.pnl for t in losing_trades)) if losing_trades else float('inf')
        
        return {
            'market': market,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_win': max(t.pnl for t in trades),
            'max_loss': min(t.pnl for t in trades),
            'avg_duration': sum(t.duration_minutes for t in trades) / total_trades,
            'trades': trades
        }
    
    def _combine_results(self, market_results: Dict) -> Dict:
        """Combine results from all markets"""
        all_trades = []
        total_pnl = 0.0
        
        print("\n=== BACKTEST RESULTS BY MARKET ===")
        
        for market, results in market_results.items():
            print(f"\n{market}:")
            print(f"  Trades: {results['total_trades']}")
            print(f"  P&L: £{results['total_pnl']:.2f}")
            print(f"  Win Rate: {results['win_rate']:.1f}%")
            print(f"  Avg P&L: £{results['avg_pnl']:.2f}")
            print(f"  Profit Factor: {results['profit_factor']:.2f}")
            
            all_trades.extend(results.get('trades', []))
            total_pnl += results['total_pnl']
        
        # Overall metrics
        if all_trades:
            total_trades = len(all_trades)
            winning_trades = len([t for t in all_trades if t.win])
            overall_win_rate = winning_trades / total_trades * 100
            
            print(f"\n=== OVERALL BACKTEST RESULTS ===")
            print(f"Total Trades: {total_trades}")
            print(f"Total P&L: £{total_pnl:.2f}")
            print(f"Win Rate: {overall_win_rate:.1f}%")
            print(f"Avg P&L per trade: £{total_pnl/total_trades:.2f}")
            
            return {
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'win_rate': overall_win_rate,
                'market_results': market_results,
                'all_trades': all_trades
            }
        
        return {'total_trades': 0, 'total_pnl': 0.0, 'win_rate': 0.0, 'market_results': market_results}

def main():
    """Run the comprehensive backtest"""
    engine = BacktestEngine()
    results = engine.run_backtest()
    
    if results.get('total_trades', 0) > 0:
        print(f"\n=== BACKTEST VS DEMO COMPARISON ===")
        print(f"Demo Account: £51.66 across 17 trades (64.7% win rate)")
        print(f"Backtest: £{results['total_pnl']:.2f} across {results['total_trades']} trades ({results['win_rate']:.1f}% win rate)")
        
        if results['total_pnl'] > 51.66:
            print("✅ Backtest OUTPERFORMED demo account!")
        else:
            print("⚠️ Backtest underperformed demo account")
    
    return results

if __name__ == "__main__":
    results = main()