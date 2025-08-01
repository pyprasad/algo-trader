# core/ensemble_strategy.py

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
from typing import Dict, List, Tuple, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import all our technical indicators and strategies
from models.rsi import compute_rsi
from models.atr import compute_atr
from models.ema import compute_ema
from models.macd import compute_macd, generate_macd_signals
from models.bollinger_bands import compute_bollinger_bands, generate_bollinger_signals
from models.stochastic import compute_stochastic_from_price, generate_stochastic_signals
from models.momentum_strategies import (
    compute_momentum, generate_momentum_signals, 
    generate_multi_timeframe_momentum, compute_rate_of_change
)
from models.regime_model import detect_regime
from core.signal_classifier import generate_trade_signal

class EnsembleStrategy:
    """
    Advanced ensemble trading strategy that combines multiple algorithms
    with weighted voting and confidence scoring.
    """
    
    def __init__(self, strategy_weights: Optional[Dict[str, float]] = None):
        """
        Initialize ensemble strategy with optional custom weights.
        
        Parameters:
        - strategy_weights: Dictionary of strategy names and their weights
        """
        self.strategy_weights = strategy_weights or {
            "rsi_regime": 0.25,      # Original RSI + regime strategy
            "macd": 0.20,            # MACD crossover strategy
            "bollinger": 0.15,       # Bollinger bands strategy
            "stochastic": 0.15,      # Stochastic oscillator
            "momentum": 0.15,        # Multi-timeframe momentum
            "trend_following": 0.10   # Pure trend following
        }
        
        # Normalize weights to sum to 1.0
        total_weight = sum(self.strategy_weights.values())
        self.strategy_weights = {k: v/total_weight for k, v in self.strategy_weights.items()}
        
        self.strategy_results = {}  # Store individual strategy results
        
    def compute_all_indicators(self, df: pd.DataFrame) -> Dict:
        """
        Compute all technical indicators needed for the ensemble.
        
        Parameters:
        - df: DataFrame with columns ['midprice', 'bid', 'offer', 'timestamp']
        
        Returns:
        - Dictionary containing all computed indicators
        """
        
        price_series = df["midprice"]
        
        indicators = {
            # Basic indicators
            "rsi": compute_rsi(price_series, period=14),
            "atr": compute_atr(price_series),
            "ema_short": compute_ema(price_series, span=20),
            "ema_long": compute_ema(price_series, span=50),
            
            # Advanced indicators
            "macd": compute_macd(price_series),
            "bollinger": compute_bollinger_bands(price_series),
            "stochastic": compute_stochastic_from_price(price_series),
            "momentum": generate_multi_timeframe_momentum(price_series),
            "roc": compute_rate_of_change(price_series),
            
            # Market regime
            "regime": detect_regime(price_series)
        }
        
        return indicators
    
    def evaluate_rsi_regime_strategy(self, indicators: Dict, current_idx: int) -> Tuple[str, float]:
        """Original RSI + regime strategy."""
        
        rsi = indicators["rsi"].iloc[current_idx]
        regime = indicators["regime"]
        ema_short = indicators["ema_short"].iloc[current_idx]
        ema_long = indicators["ema_long"].iloc[current_idx]
        
        # Determine trend
        trend = "uptrend" if ema_short > ema_long else "downtrend" if ema_short < ema_long else "sideways"
        
        signal = generate_trade_signal(
            rsi=rsi,
            atr=indicators["atr"].iloc[current_idx],
            regime=regime,
            thresholds=(80, 20),
            trend=trend
        )
        
        # Calculate confidence based on signal strength
        confidence = 0.5  # Base confidence
        if signal == "BUY":
            confidence += min((20 - rsi) / 20, 0.4)  # Higher confidence for lower RSI
        elif signal == "SELL":
            confidence += min((rsi - 80) / 20, 0.4)  # Higher confidence for higher RSI
        
        return signal, confidence
    
    def evaluate_macd_strategy(self, indicators: Dict, current_idx: int) -> Tuple[str, float]:
        """MACD crossover strategy."""
        
        macd_data = indicators["macd"]
        price_series = pd.Series([0] * len(macd_data["macd"]), index=macd_data["macd"].index)
        signals = generate_macd_signals(macd_data, price_series)
        
        if current_idx >= len(signals):
            return "HOLD", 0.0
        
        signal_value = signals.iloc[current_idx]
        
        if signal_value == 1:
            signal = "BUY"
        elif signal_value == -1:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        # Confidence based on MACD histogram strength
        histogram = abs(macd_data["histogram"].iloc[current_idx])
        confidence = min(histogram / 0.1, 1.0)  # Normalize histogram strength
        
        return signal, confidence
    
    def evaluate_bollinger_strategy(self, indicators: Dict, current_idx: int) -> Tuple[str, float]:
        """Bollinger Bands strategy."""
        
        bb_data = indicators["bollinger"]
        price_series = pd.Series([0] * len(bb_data["upper"]), index=bb_data["upper"].index)
        signals = generate_bollinger_signals(bb_data, price_series)
        
        if current_idx >= len(signals):
            return "HOLD", 0.0
        
        signal_value = signals.iloc[current_idx]
        
        if signal_value == 1:
            signal = "BUY"
        elif signal_value == -1:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        # Confidence based on position within bands
        percent_b = bb_data["percent_b"].iloc[current_idx]
        if signal == "BUY":
            confidence = max(0, (0.2 - percent_b) / 0.2)  # Higher confidence when oversold
        elif signal == "SELL":
            confidence = max(0, (percent_b - 0.8) / 0.2)  # Higher confidence when overbought
        else:
            confidence = 0.3
        
        return signal, confidence
    
    def evaluate_stochastic_strategy(self, indicators: Dict, current_idx: int) -> Tuple[str, float]:
        """Stochastic oscillator strategy."""
        
        stoch_data = indicators["stochastic"]
        signals = generate_stochastic_signals(stoch_data)
        
        if current_idx >= len(signals):
            return "HOLD", 0.0
        
        signal_value = signals.iloc[current_idx]
        
        if signal_value == 1:
            signal = "BUY"
        elif signal_value == -1:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        # Confidence based on stochastic levels
        k_value = stoch_data["percent_k"].iloc[current_idx]
        if signal == "BUY":
            confidence = max(0, (30 - k_value) / 30)
        elif signal == "SELL":
            confidence = max(0, (k_value - 70) / 30)
        else:
            confidence = 0.3
        
        return signal, confidence
    
    def evaluate_momentum_strategy(self, indicators: Dict, current_idx: int) -> Tuple[str, float]:
        """Multi-timeframe momentum strategy."""
        
        momentum_data = indicators["momentum"]
        signals = momentum_data["signals"]
        
        if current_idx >= len(signals):
            return "HOLD", 0.0
        
        signal_value = signals.iloc[current_idx]
        
        if signal_value == 1:
            signal = "BUY"
        elif signal_value == -1:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        # Confidence based on momentum alignment
        short_mom = momentum_data["short_momentum"].iloc[current_idx]
        medium_mom = momentum_data["medium_momentum"].iloc[current_idx]
        long_mom = momentum_data["long_momentum"].iloc[current_idx]
        
        # Higher confidence when all timeframes align
        if signal == "BUY":
            alignment = sum([1 for m in [short_mom, medium_mom, long_mom] if m > 0]) / 3
        elif signal == "SELL":
            alignment = sum([1 for m in [short_mom, medium_mom, long_mom] if m < 0]) / 3
        else:
            alignment = 0.3
        
        confidence = alignment
        
        return signal, confidence
    
    def evaluate_trend_following_strategy(self, indicators: Dict, current_idx: int) -> Tuple[str, float]:
        """Simple trend following strategy using EMAs."""
        
        ema_short = indicators["ema_short"].iloc[current_idx]
        ema_long = indicators["ema_long"].iloc[current_idx]
        price = indicators["rsi"].index[current_idx]  # Use index as proxy for price context
        
        if ema_short > ema_long * 1.01:  # 1% threshold to avoid noise
            signal = "BUY"
            confidence = min((ema_short - ema_long) / ema_long * 100, 1.0)
        elif ema_short < ema_long * 0.99:
            signal = "SELL"
            confidence = min((ema_long - ema_short) / ema_long * 100, 1.0)
        else:
            signal = "HOLD"
            confidence = 0.2
        
        return signal, confidence
    
    def generate_ensemble_signal(self, df: pd.DataFrame) -> Tuple[str, Dict]:
        """
        Generate ensemble trading signal by combining all strategies.
        
        Parameters:
        - df: DataFrame with price data
        
        Returns:
        - Tuple of (signal, detailed_results)
        """
        
        if len(df) < 50:  # Need sufficient data for indicators
            return "HOLD", {"error": "Insufficient data for analysis"}
        
        # Compute all indicators
        indicators = self.compute_all_indicators(df)
        current_idx = -1  # Use latest data point
        
        # Evaluate each strategy
        strategies = {
            "rsi_regime": self.evaluate_rsi_regime_strategy,
            "macd": self.evaluate_macd_strategy,
            "bollinger": self.evaluate_bollinger_strategy,
            "stochastic": self.evaluate_stochastic_strategy,
            "momentum": self.evaluate_momentum_strategy,
            "trend_following": self.evaluate_trend_following_strategy
        }
        
        strategy_results = {}
        weighted_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        
        for strategy_name, strategy_func in strategies.items():
            try:
                signal, confidence = strategy_func(indicators, current_idx)
                weight = self.strategy_weights.get(strategy_name, 0.0)
                
                strategy_results[strategy_name] = {
                    "signal": signal,
                    "confidence": confidence,
                    "weight": weight,
                    "weighted_score": confidence * weight
                }
                
                # Add to weighted scores
                weighted_scores[signal] += confidence * weight
                
            except Exception as e:
                print(f"⚠️ Error in {strategy_name} strategy: {e}")
                strategy_results[strategy_name] = {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "weight": self.strategy_weights.get(strategy_name, 0.0),
                    "error": str(e)
                }
        
        # Determine final signal based on weighted voting
        final_signal = max(weighted_scores, key=weighted_scores.get)
        total_confidence = weighted_scores[final_signal]
        
        # Apply minimum confidence threshold
        if total_confidence < 0.3:
            final_signal = "HOLD"
        
        detailed_results = {
            "final_signal": final_signal,
            "total_confidence": total_confidence,
            "weighted_scores": weighted_scores,
            "strategy_results": strategy_results,
            "market_data": {
                "rsi": float(indicators["rsi"].iloc[current_idx]),
                "regime": indicators["regime"],
                "trend": "uptrend" if indicators["ema_short"].iloc[current_idx] > indicators["ema_long"].iloc[current_idx] else "downtrend"
            }
        }
        
        return final_signal, detailed_results

# Global ensemble instance
ensemble_strategy = EnsembleStrategy()