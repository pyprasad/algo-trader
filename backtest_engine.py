# backtest_engine.py

"""
📊 Comprehensive Backtesting Engine

Tests trading strategies against historical tick data to generate detailed P&L analysis.
Processes entire stored dataset (105,740 ticks) for both DAX and FTSE 100.

Features:
- Full tick-by-tick simulation
- Realistic spread and slippage modeling
- Multiple strategy comparison
- Comprehensive performance metrics
- Detailed trade logging

Author: Backtesting Analysis Team
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import csv
from dataclasses import dataclass, asdict
import yaml

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from data.db import db
from models.rsi import compute_rsi
from models.atr import compute_atr
from utils.config_loader import load_global_config

@dataclass
class BacktestTrade:
    """Container for individual backtest trade"""
    timestamp: datetime
    market: str
    strategy: str
    signal: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    cumulative_pnl: float
    win: bool
    duration_seconds: int
    reason: str
    entry_rsi: float
    exit_rsi: float
    spread_cost: float

@dataclass
class BacktestMetrics:
    """Container for backtest performance metrics"""
    strategy_name: str
    market: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    max_drawdown: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    avg_trade_duration: float
    total_spread_cost: float
    sharpe_ratio: float
    return_std: float

class BacktestEngine:
    """
    Core backtesting engine for strategy performance analysis
    """
    
    def __init__(self):
        """Initialize backtesting engine"""
        self.global_config = load_global_config()
        
        # Load market-specific configurations
        try:
            with open("configs/market_specific_strategy.yaml", "r") as f:
                self.market_config = yaml.safe_load(f)
        except FileNotFoundError:
            print("⚠️ Market-specific config not found, using defaults")
            self.market_config = {"market_strategies": {}}
        
        # Backtesting parameters
        self.commission_per_trade = 0.5  # £0.50 per trade (IG typical)
        self.slippage_factor = 0.1  # 0.1 pip slippage on average
        
        # Performance tracking
        self.trades = []
        self.current_positions = {}
        self.balance_history = []
        
        print("📊 Backtesting Engine initialized")
        print(f"   Commission: £{self.commission_per_trade} per trade")
        print(f"   Slippage: {self.slippage_factor} pips average")
    
    def load_tick_data(self, market: str) -> List[Dict]:
        """Load all tick data for a specific market"""
        try:
            # Get collection name
            collection_name = f"ticks_{market.lower().replace(' ', '_')}"
            collection = db[collection_name]
            
            # Load all ticks sorted by timestamp
            ticks = list(collection.find({}).sort("timestamp", 1))
            
            print(f"📈 Loaded {len(ticks):,} ticks for {market}")
            if ticks:
                print(f"   Time range: {ticks[0]['timestamp']} to {ticks[-1]['timestamp']}")
                print(f"   Price range: {min(t['bid'] for t in ticks):.1f} - {max(t['bid'] for t in ticks):.1f}")
            
            return ticks
            
        except Exception as e:
            print(f"❌ Error loading tick data for {market}: {e}")
            return []
    
    def get_original_strategy_params(self, market: str) -> Dict:
        """Get original strategy parameters (the ones that caused losses)"""
        return {
            "rsi_period": 14,
            "rsi_buy_threshold": 70,
            "rsi_sell_threshold": 30,
            "stop_loss_pips": 10,
            "take_profit_pips": 20,
            "min_confidence": 0.7,
            "strategy_name": "Original"
        }
    
    def get_adaptive_strategy_params(self, market: str) -> Dict:
        """Get market-adaptive strategy parameters"""
        market_strategies = self.market_config.get("market_strategies", {})
        
        if market in market_strategies:
            params = market_strategies[market].copy()
            params["strategy_name"] = "Adaptive"
            return params
        else:
            # Default adaptive parameters
            if market == "DAX":
                return {
                    "rsi_period": 14,
                    "rsi_buy_threshold": 75,
                    "rsi_sell_threshold": 25,
                    "stop_loss_pips": 15,
                    "take_profit_pips": 30,
                    "min_confidence": 0.8,
                    "strategy_name": "Adaptive",
                    "trading_hours": {"avoid_hours": [19, 20, 21, 22]}
                }
            else:  # FTSE 100
                return {
                    "rsi_period": 14,
                    "rsi_buy_threshold": 70,
                    "rsi_sell_threshold": 30,
                    "stop_loss_pips": 10,
                    "take_profit_pips": 20,
                    "min_confidence": 0.7,
                    "strategy_name": "Adaptive",
                    "trading_hours": {"avoid_hours": [21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7]}
                }
    
    def should_avoid_time(self, timestamp: datetime, strategy_params: Dict) -> bool:
        """Check if trading should be avoided at this time for adaptive strategy"""
        if strategy_params.get("strategy_name") != "Adaptive":
            return False
        
        trading_hours = strategy_params.get("trading_hours", {})
        avoid_hours = trading_hours.get("avoid_hours", [])
        
        return timestamp.hour in avoid_hours
    
    def generate_signal(self, prices: List[float], timestamp: datetime, strategy_params: Dict) -> Tuple[str, float, str]:
        """Generate trading signal based on strategy parameters"""
        try:
            if len(prices) < strategy_params["rsi_period"] + 5:
                return "HOLD", 0.5, "Insufficient data"
            
            # Check time-based filtering for adaptive strategy
            if self.should_avoid_time(timestamp, strategy_params):
                return "HOLD", 0.0, f"Avoiding hour {timestamp.hour}"
            
            # Calculate RSI
            price_series = pd.Series(prices)
            rsi_series = compute_rsi(price_series, strategy_params["rsi_period"])
            current_rsi = rsi_series.iloc[-1] if len(rsi_series) > 0 else 50
            
            # Calculate volatility (ATR) for confidence adjustment
            atr_series = compute_atr(price_series, 14)
            current_atr = atr_series.iloc[-1] if len(atr_series) > 0 else 0
            
            # Base confidence
            confidence = 0.5
            reason = ""
            
            # Generate signals based on RSI
            if current_rsi >= strategy_params["rsi_buy_threshold"]:
                signal = "SELL"  # Overbought, sell signal
                confidence = 0.6 + (current_rsi - strategy_params["rsi_buy_threshold"]) / 100
                reason = f"RSI overbought {current_rsi:.1f}"
                
            elif current_rsi <= strategy_params["rsi_sell_threshold"]:
                signal = "BUY"  # Oversold, buy signal
                confidence = 0.6 + (strategy_params["rsi_sell_threshold"] - current_rsi) / 100
                reason = f"RSI oversold {current_rsi:.1f}"
                
            else:
                signal = "HOLD"
                confidence = 0.5
                reason = f"RSI neutral {current_rsi:.1f}"
            
            # Apply minimum confidence threshold
            if confidence < strategy_params["min_confidence"]:
                signal = "HOLD"
                reason += f" (confidence {confidence:.2f} < {strategy_params['min_confidence']})"
            
            return signal, min(confidence, 1.0), reason
            
        except Exception as e:
            return "HOLD", 0.0, f"Error: {e}"
    
    def calculate_spread_cost(self, market: str, size: float) -> float:
        """Calculate spread cost for trade execution"""
        # Typical spreads based on our data analysis
        spread_pips = 1.4 if market == "DAX" else 1.0
        
        # Convert to monetary cost (assuming £1 per pip for simplicity)
        spread_cost = spread_pips * abs(size)
        return spread_cost
    
    def execute_trade(self, market: str, signal: str, entry_price: float, 
                     timestamp: datetime, strategy_params: Dict, 
                     current_rsi: float, reason: str) -> Optional[str]:
        """Execute a trade and return trade ID"""
        try:
            if signal == "HOLD":
                return None
            
            size = 1.0  # Standard position size
            direction = 1 if signal == "BUY" else -1
            
            # Calculate costs
            spread_cost = self.calculate_spread_cost(market, size)
            commission = self.commission_per_trade
            slippage = self.slippage_factor * direction  # Slippage against us
            
            # Adjust entry price for slippage
            actual_entry_price = entry_price + slippage
            
            # Calculate stop loss and take profit levels
            stop_distance = strategy_params["stop_loss_pips"]
            profit_distance = strategy_params["take_profit_pips"]
            
            if signal == "BUY":
                stop_loss = actual_entry_price - stop_distance
                take_profit = actual_entry_price + profit_distance
            else:  # SELL
                stop_loss = actual_entry_price + stop_distance
                take_profit = actual_entry_price - profit_distance
            
            # Create position tracking
            position_id = f"{market}_{strategy_params['strategy_name']}_{timestamp.strftime('%H%M%S%f')}"
            
            self.current_positions[position_id] = {
                "market": market,
                "strategy": strategy_params["strategy_name"],
                "signal": signal,
                "entry_price": actual_entry_price,
                "size": size * direction,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "entry_timestamp": timestamp,
                "entry_rsi": current_rsi,
                "spread_cost": spread_cost,
                "commission": commission,
                "reason": reason
            }
            
            return position_id
            
        except Exception as e:
            print(f"❌ Error executing trade: {e}")
            return None
    
    def check_position_exit(self, position_id: str, current_price: float, 
                          timestamp: datetime, current_rsi: float) -> Optional[BacktestTrade]:
        """Check if position should be closed and return trade result"""
        try:
            position = self.current_positions[position_id]
            
            # Check stop loss and take profit
            should_close = False
            exit_reason = ""
            
            if position["size"] > 0:  # Long position
                if current_price <= position["stop_loss"]:
                    should_close = True
                    exit_reason = "Stop Loss"
                elif current_price >= position["take_profit"]:
                    should_close = True
                    exit_reason = "Take Profit"
            else:  # Short position
                if current_price >= position["stop_loss"]:
                    should_close = True
                    exit_reason = "Stop Loss"
                elif current_price <= position["take_profit"]:
                    should_close = True
                    exit_reason = "Take Profit"
            
            if should_close:
                # Calculate P&L
                if position["size"] > 0:  # Long
                    raw_pnl = (current_price - position["entry_price"]) * abs(position["size"])
                else:  # Short
                    raw_pnl = (position["entry_price"] - current_price) * abs(position["size"])
                
                # Subtract costs
                net_pnl = raw_pnl - position["spread_cost"] - position["commission"]
                
                # Create trade record
                duration = (timestamp - position["entry_timestamp"]).total_seconds()
                
                trade = BacktestTrade(
                    timestamp=timestamp,
                    market=position["market"],
                    strategy=position["strategy"],
                    signal=position["signal"],
                    entry_price=position["entry_price"],
                    exit_price=current_price,
                    size=abs(position["size"]),
                    pnl=net_pnl,
                    cumulative_pnl=0,  # Will be calculated later
                    win=net_pnl > 0,
                    duration_seconds=int(duration),
                    reason=f"{exit_reason}: {position['reason']}",
                    entry_rsi=position["entry_rsi"],
                    exit_rsi=current_rsi,
                    spread_cost=position["spread_cost"] + position["commission"]
                )
                
                # Remove position
                del self.current_positions[position_id]
                
                return trade
            
            return None
            
        except Exception as e:
            print(f"❌ Error checking position exit: {e}")
            return None
    
    def run_backtest(self, market: str, strategy_params: Dict) -> List[BacktestTrade]:
        """Run complete backtest for a market and strategy"""
        print(f"\n🚀 Running backtest: {market} - {strategy_params['strategy_name']}")
        
        # Load tick data
        ticks = self.load_tick_data(market)
        if not ticks:
            print(f"❌ No tick data available for {market}")
            return []
        
        trades = []
        prices = []
        
        # Process each tick
        for i, tick in enumerate(ticks):
            timestamp = tick["timestamp"]
            bid_price = tick["bid"]
            offer_price = tick["offer"]
            mid_price = (bid_price + offer_price) / 2
            
            prices.append(mid_price)
            
            # Keep only recent prices for indicators (last 100 ticks)
            if len(prices) > 100:
                prices = prices[-100:]
            
            # Check existing positions for exits
            positions_to_check = list(self.current_positions.keys())
            for pos_id in positions_to_check:
                if self.current_positions[pos_id]["market"] == market and \
                   self.current_positions[pos_id]["strategy"] == strategy_params["strategy_name"]:
                    
                    # Calculate current RSI for exit
                    try:
                        if len(prices) >= 14:
                            price_series = pd.Series(prices)
                            rsi_series = compute_rsi(price_series, 14)
                            current_rsi = rsi_series.iloc[-1]
                        else:
                            current_rsi = 50
                    except:
                        current_rsi = 50
                    
                    trade = self.check_position_exit(pos_id, mid_price, timestamp, current_rsi)
                    if trade:
                        trades.append(trade)
            
            # Generate new signals (only if no position for this market/strategy)
            has_position = any(
                pos["market"] == market and pos["strategy"] == strategy_params["strategy_name"]
                for pos in self.current_positions.values()
            )
            
            if not has_position and len(prices) >= strategy_params["rsi_period"] + 5:
                signal, confidence, reason = self.generate_signal(prices, timestamp, strategy_params)
                
                if signal != "HOLD":
                    # Calculate current RSI for entry
                    try:
                        price_series = pd.Series(prices)
                        rsi_series = compute_rsi(price_series, strategy_params["rsi_period"])
                        current_rsi = rsi_series.iloc[-1]
                    except:
                        current_rsi = 50
                    
                    position_id = self.execute_trade(
                        market, signal, mid_price, timestamp, 
                        strategy_params, current_rsi, reason
                    )
            
            # Progress reporting
            if i % 10000 == 0 and i > 0:
                print(f"   Processed {i:,}/{len(ticks):,} ticks ({i/len(ticks)*100:.1f}%)")
        
        # Close any remaining positions at final price
        final_price = (ticks[-1]["bid"] + ticks[-1]["offer"]) / 2
        final_timestamp = ticks[-1]["timestamp"]
        
        remaining_positions = [
            pos_id for pos_id, pos in self.current_positions.items()
            if pos["market"] == market and pos["strategy"] == strategy_params["strategy_name"]
        ]
        
        for pos_id in remaining_positions:
            trade = self.check_position_exit(pos_id, final_price, final_timestamp, 50)
            if trade:
                trade.reason = f"End of backtest: {trade.reason}"
                trades.append(trade)
        
        # Calculate cumulative P&L
        cumulative = 0
        for trade in trades:
            cumulative += trade.pnl
            trade.cumulative_pnl = cumulative
        
        print(f"✅ Backtest complete: {len(trades)} trades generated")
        return trades
    
    def calculate_metrics(self, trades: List[BacktestTrade], strategy_name: str, market: str) -> BacktestMetrics:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return BacktestMetrics(
                strategy_name=strategy_name, market=market, total_trades=0,
                winning_trades=0, losing_trades=0, win_rate=0.0, total_pnl=0.0,
                gross_profit=0.0, gross_loss=0.0, profit_factor=0.0,
                average_win=0.0, average_loss=0.0, largest_win=0.0, largest_loss=0.0,
                max_drawdown=0.0, max_consecutive_wins=0, max_consecutive_losses=0,
                avg_trade_duration=0.0, total_spread_cost=0.0, sharpe_ratio=0.0, return_std=0.0
            )
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.win)
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades * 100
        
        # P&L metrics
        total_pnl = sum(t.pnl for t in trades)
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Trade size metrics
        wins = [t.pnl for t in trades if t.win]
        losses = [t.pnl for t in trades if not t.win]
        
        average_win = np.mean(wins) if wins else 0
        average_loss = np.mean(losses) if losses else 0
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0
        
        # Drawdown calculation
        cumulative_pnl = np.array([t.cumulative_pnl for t in trades])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdowns = cumulative_pnl - running_max
        max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0
        
        # Consecutive wins/losses
        consecutive_wins = consecutive_losses = 0
        max_consecutive_wins = max_consecutive_losses = 0
        current_wins = current_losses = 0
        
        for trade in trades:
            if trade.win:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
        
        # Duration and cost metrics
        avg_trade_duration = np.mean([t.duration_seconds for t in trades])
        total_spread_cost = sum(t.spread_cost for t in trades)
        
        # Risk metrics
        returns = [t.pnl for t in trades]
        return_std = np.std(returns) if len(returns) > 1 else 0
        sharpe_ratio = (np.mean(returns) / return_std) if return_std > 0 else 0
        
        return BacktestMetrics(
            strategy_name=strategy_name,
            market=market,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            average_win=average_win,
            average_loss=average_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            max_drawdown=max_drawdown,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            avg_trade_duration=avg_trade_duration,
            total_spread_cost=total_spread_cost,
            sharpe_ratio=sharpe_ratio,
            return_std=return_std
        )
    
    def export_trades_to_csv(self, trades: List[BacktestTrade], filename: str):
        """Export trades to CSV file"""
        try:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = [
                    'timestamp', 'market', 'strategy', 'signal', 'entry_price', 'exit_price',
                    'size', 'pnl', 'cumulative_pnl', 'win', 'duration_seconds', 'reason',
                    'entry_rsi', 'exit_rsi', 'spread_cost'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for trade in trades:
                    writer.writerow(asdict(trade))
            
            print(f"📊 Exported {len(trades)} trades to {filename}")
            
        except Exception as e:
            print(f"❌ Error exporting trades: {e}")

if __name__ == "__main__":
    # Test the backtesting engine
    print("🧪 Testing Backtesting Engine")
    print("=" * 50)
    
    engine = BacktestEngine()
    
    # Test with small sample
    test_market = "FTSE 100"
    original_params = engine.get_original_strategy_params(test_market)
    
    print(f"Testing {test_market} with original strategy...")
    trades = engine.run_backtest(test_market, original_params)
    
    if trades:
        metrics = engine.calculate_metrics(trades, "Original", test_market)
        print(f"\nTest Results:")
        print(f"Total Trades: {metrics.total_trades}")
        print(f"Win Rate: {metrics.win_rate:.1f}%")
        print(f"Total P&L: £{metrics.total_pnl:.2f}")
    
    print("\n✅ Backtesting engine test complete")