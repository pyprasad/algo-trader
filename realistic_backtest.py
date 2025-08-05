#!/usr/bin/env python3
"""
Realistic Backtesting Engine
Uses more practical parameters based on actual demo account trading patterns
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
    spread_cost: float
    win: bool
    exit_reason: str

class SimpleTechnicalIndicators:
    """Simplified technical indicators"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(0, change) for change in changes]
        losses = [max(0, -change) for change in changes]
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int = 20) -> float:
        if len(prices) < period:
            return sum(prices) / len(prices)
        return sum(prices[-period:]) / period
    
    @staticmethod
    def price_change_percent(prices: List[float], lookback: int = 10) -> float:
        """Calculate percentage price change over lookback period"""
        if len(prices) < lookback + 1:
            return 0.0
        
        old_price = prices[-lookback-1]
        new_price = prices[-1]
        
        if old_price == 0:
            return 0.0
        
        return ((new_price - old_price) / old_price) * 100

class RealisticStrategyEngine:
    """Strategy engine based on actual demo account trading patterns"""
    
    def __init__(self):
        self.indicators = SimpleTechnicalIndicators()
        
        # More realistic parameters based on demo account analysis
        self.market_params = {
            'FTSE 100': {
                'rsi_oversold': 45,      # More lenient
                'rsi_overbought': 55,    # More lenient
                'min_price_change': 0.02, # 0.02% minimum price movement
                'confidence_threshold': 0.1,  # Lower threshold
                'profit_target_pips': 10,  # 10 pip profit target
                'stop_loss_pips': 10      # 10 pip stop loss
            },
            'DAX': {
                'rsi_oversold': 45,
                'rsi_overbought': 55,
                'min_price_change': 0.02,
                'confidence_threshold': 0.1,
                'profit_target_pips': 10,
                'stop_loss_pips': 10
            }
        }
    
    def analyze_market_conditions(self, prices: List[float], market: str) -> Optional[Dict]:
        """Generate trading signals based on realistic market conditions"""
        if len(prices) < 20:
            return None
        
        try:
            # Calculate indicators
            rsi = self.indicators.calculate_rsi(prices, period=14)
            sma_20 = self.indicators.calculate_sma(prices, period=20)
            price_change = self.indicators.price_change_percent(prices, lookback=10)
            
            current_price = prices[-1]
            params = self.market_params.get(market, self.market_params['FTSE 100'])
            
            # More realistic signal generation
            signal = 'HOLD'
            confidence = 0.0
            
            # Momentum-based signals (similar to what appears to be working in demo)
            momentum_up = price_change > params['min_price_change']
            momentum_down = price_change < -params['min_price_change']
            
            # RSI divergence signals  
            rsi_oversold = rsi < params['rsi_oversold']
            rsi_overbought = rsi > params['rsi_overbought']
            
            # Price above/below moving average
            above_sma = current_price > sma_20
            below_sma = current_price < sma_20
            
            # Generate signals (more permissive to match demo trading frequency)
            if (rsi_oversold and momentum_up) or (above_sma and momentum_up):
                signal = 'BUY'
                confidence = 0.7  # Higher confidence for matching demo patterns
            elif (rsi_overbought and momentum_down) or (below_sma and momentum_down):
                signal = 'SELL'
                confidence = 0.7
            elif rsi_oversold and above_sma:  # Oversold + uptrend
                signal = 'BUY'
                confidence = 0.5
            elif rsi_overbought and below_sma:  # Overbought + downtrend
                signal = 'SELL'
                confidence = 0.5
            
            # Lower confidence threshold to generate more trades
            if confidence < params['confidence_threshold']:
                signal = 'HOLD'
            
            return {
                'signal': signal,
                'confidence': confidence,
                'rsi': rsi,
                'price': current_price,
                'sma': sma_20,
                'price_change': price_change,
                'momentum_up': momentum_up,
                'momentum_down': momentum_down
            }
            
        except Exception as e:
            print(f"Error in strategy analysis: {e}")
            return None

class RealisticBacktestEngine:
    """Realistic backtesting engine"""
    
    def __init__(self):
        self.strategy = RealisticStrategyEngine()
        self.trades = []
        self.cumulative_pnl = 0.0
        
        # More realistic parameters
        self.commission = 0.5  # £0.50 per trade (matches demo)
        self.position_size = 1.0
        self.max_trade_duration = 30  # 30 minutes max (shorter than demo suggests)
        
    def run_backtest(self) -> Dict:
        """Run realistic backtest"""
        print("=== REALISTIC BACKTEST BASED ON DEMO PATTERNS ===")
        
        # Load data
        try:
            ftse_data = pd.read_csv('ticks_ftse_100.csv')
            ftse_data['timestamp'] = pd.to_datetime(ftse_data['timestamp'])
            ftse_data = ftse_data.sort_values('timestamp')
            
            dax_data = pd.read_csv('ticks_dax.csv')
            dax_data['timestamp'] = pd.to_datetime(dax_data['timestamp'])
            dax_data = dax_data.sort_values('timestamp')
            
            print(f"FTSE 100: {len(ftse_data)} ticks")
            print(f"DAX: {len(dax_data)} ticks")
        except Exception as e:
            print(f"Error loading data: {e}")
            return {}
        
        results = {}
        
        # Process each market
        for market_name, data in [('FTSE 100', ftse_data), ('DAX', dax_data)]:
            print(f"\n--- Backtesting {market_name} ---")
            market_results = self._backtest_market(market_name, data)
            results[market_name] = market_results
        
        return self._combine_results(results)
    
    def _backtest_market(self, market: str, data: pd.DataFrame) -> Dict:
        """Backtest a specific market with realistic parameters"""
        market_trades = []
        current_position = None
        lookback_window = 50
        analysis_interval = 100  # Analyze every 100 ticks
        
        print(f"Processing {len(data)} ticks...")
        
        for i in range(lookback_window, len(data), analysis_interval):
            try:
                # Get price series
                prices = data['bid'].iloc[i-lookback_window:i].tolist()
                current_time = data['timestamp'].iloc[i]
                current_bid = data['bid'].iloc[i]
                current_offer = data['offer'].iloc[i]
                
                # Analyze conditions
                analysis = self.strategy.analyze_market_conditions(prices, market)
                if not analysis:
                    continue
                
                # Check exit conditions for existing position
                if current_position:
                    exit_signal = self._check_exit_conditions(current_position, current_time, current_bid, current_offer, analysis)
                    if exit_signal:
                        trade = self._close_position(current_position, current_time, current_bid, current_offer, exit_signal)
                        if trade:
                            market_trades.append(trade)
                            print(f"  {trade.signal} trade closed: {trade.exit_reason}, P&L: £{trade.pnl:.2f}")
                        current_position = None
                
                # Check for new entry
                if not current_position and analysis['signal'] in ['BUY', 'SELL']:
                    current_position = {
                        'market': market,
                        'signal': analysis['signal'],
                        'entry_time': current_time,
                        'entry_price': current_offer if analysis['signal'] == 'BUY' else current_bid,
                        'entry_rsi': analysis['rsi'],
                        'confidence': analysis['confidence']
                    }
                    print(f"  {analysis['signal']} position opened at £{current_position['entry_price']:.2f}, RSI: {analysis['rsi']:.1f}")
                
            except Exception as e:
                print(f"Error at tick {i}: {e}")
                continue
        
        # Close remaining position
        if current_position:
            final_data = data.iloc[-1]
            trade = self._close_position(current_position, final_data['timestamp'], final_data['bid'], final_data['offer'], 'end_of_data')
            if trade:
                market_trades.append(trade)
        
        print(f"Completed {market}: {len(market_trades)} trades")
        return self._calculate_metrics(market, market_trades)
    
    def _check_exit_conditions(self, position: Dict, current_time: datetime, bid: float, offer: float, analysis: Dict) -> Optional[str]:
        """Check realistic exit conditions"""
        
        # Time-based exit
        duration = (current_time - position['entry_time']).total_seconds() / 60
        if duration >= self.max_trade_duration:
            return 'time_limit'
        
        # Price-based exits (matching demo account patterns)
        entry_price = position['entry_price']
        params = self.strategy.market_params.get(position['market'], self.strategy.market_params['FTSE 100'])
        
        if position['signal'] == 'BUY':
            current_price = bid
            profit_target = entry_price + params['profit_target_pips']
            stop_loss = entry_price - params['stop_loss_pips']
            
            if current_price >= profit_target:
                return 'profit_target'
            elif current_price <= stop_loss:
                return 'stop_loss'
        else:  # SELL
            current_price = offer
            profit_target = entry_price - params['profit_target_pips']
            stop_loss = entry_price + params['stop_loss_pips']
            
            if current_price <= profit_target:
                return 'profit_target'
            elif current_price >= stop_loss:
                return 'stop_loss'
        
        # Signal reversal
        if position['signal'] == 'BUY' and analysis['signal'] == 'SELL':
            return 'signal_reversal'
        elif position['signal'] == 'SELL' and analysis['signal'] == 'BUY':
            return 'signal_reversal'
        
        return None
    
    def _close_position(self, position: Dict, timestamp: datetime, bid: float, offer: float, exit_reason: str) -> Optional[BacktestTrade]:
        """Close position and calculate P&L"""
        
        signal = position['signal']
        entry_price = position['entry_price']
        
        # Determine exit price
        if signal == 'BUY':
            exit_price = bid
        else:
            exit_price = offer
        
        # Calculate P&L
        if signal == 'BUY':
            pnl = (exit_price - entry_price) * self.position_size
        else:
            pnl = (entry_price - exit_price) * self.position_size
        
        # Subtract commission
        pnl -= self.commission
        
        # Update cumulative P&L
        self.cumulative_pnl += pnl
        
        # Calculate duration
        duration = (timestamp - position['entry_time']).total_seconds() / 60
        
        trade = BacktestTrade(
            timestamp=timestamp,
            market=position['market'],
            signal=signal,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            cumulative_pnl=self.cumulative_pnl,
            duration_minutes=int(duration),
            rsi_entry=position['entry_rsi'],
            spread_cost=abs(offer - bid),
            win=pnl > 0,
            exit_reason=exit_reason
        )
        
        return trade
    
    def _calculate_metrics(self, market: str, trades: List[BacktestTrade]) -> Dict:
        """Calculate market performance metrics"""
        if not trades:
            return {
                'market': market,
                'total_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_pnl': 0.0,
                'trades': []
            }
        
        total_trades = len(trades)
        total_pnl = sum(t.pnl for t in trades)
        winning_trades = [t for t in trades if t.win]
        losing_trades = [t for t in trades if not t.win]
        
        win_rate = len(winning_trades) / total_trades * 100
        avg_pnl = total_pnl / total_trades
        
        return {
            'market': market,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'avg_win': sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_loss': sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0,
            'max_win': max(t.pnl for t in trades),
            'max_loss': min(t.pnl for t in trades),
            'avg_duration': sum(t.duration_minutes for t in trades) / total_trades,
            'trades': trades
        }
    
    def _combine_results(self, market_results: Dict) -> Dict:
        """Combine and display results"""
        all_trades = []
        total_pnl = 0.0
        
        print("\n=== REALISTIC BACKTEST RESULTS ===")
        
        for market, results in market_results.items():
            print(f"\n{market}:")
            print(f"  Trades: {results['total_trades']}")
            print(f"  P&L: £{results['total_pnl']:.2f}")
            print(f"  Win Rate: {results['win_rate']:.1f}%")
            print(f"  Avg P&L: £{results['avg_pnl']:.2f}")
            if results['total_trades'] > 0:
                print(f"  Avg Win: £{results['avg_win']:.2f}")
                print(f"  Avg Loss: £{results['avg_loss']:.2f}")
                print(f"  Avg Duration: {results['avg_duration']:.1f} minutes")
            
            all_trades.extend(results['trades'])
            total_pnl += results['total_pnl']
        
        if all_trades:
            total_trades = len(all_trades)
            winning_trades = len([t for t in all_trades if t.win])
            overall_win_rate = winning_trades / total_trades * 100
            
            print(f"\n=== OVERALL BACKTEST RESULTS ===")
            print(f"Total Trades: {total_trades}")
            print(f"Total P&L: £{total_pnl:.2f}")
            print(f"Win Rate: {overall_win_rate:.1f}%")
            print(f"Avg P&L per trade: £{total_pnl/total_trades:.2f}")
            
            print(f"\n=== COMPARISON WITH DEMO ACCOUNT ===")
            print(f"Demo Account:")
            print(f"  17 trades, £51.66 profit, 64.7% win rate")
            print(f"Backtest:")
            print(f"  {total_trades} trades, £{total_pnl:.2f} profit, {overall_win_rate:.1f}% win rate")
            
            performance_ratio = total_pnl / 51.66 if total_pnl != 0 else 0
            trade_ratio = total_trades / 17
            
            print(f"\nPerformance Analysis:")
            print(f"  Profit ratio: {performance_ratio:.2f}x demo account")
            print(f"  Trade frequency: {trade_ratio:.2f}x demo account")
            
            if total_pnl > 51.66:
                print("✅ Backtest OUTPERFORMED demo account!")
            else:
                print("⚠️ Backtest underperformed demo account")
            
            return {
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'win_rate': overall_win_rate,
                'demo_comparison': {
                    'profit_ratio': performance_ratio,
                    'trade_ratio': trade_ratio,
                    'outperformed': total_pnl > 51.66
                }
            }
        
        return {'total_trades': 0, 'total_pnl': 0.0}

def main():
    """Run realistic backtest"""
    engine = RealisticBacktestEngine()
    results = engine.run_backtest()
    return results

if __name__ == "__main__":
    results = main()