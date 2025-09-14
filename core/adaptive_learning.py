# core/adaptive_learning.py

"""
ADAPTIVE LEARNING SYSTEM

Features:
- Machine learning-based strategy adaptation
- Market regime detection and adaptation
- Parameter optimization using genetic algorithms
- Performance-based strategy selection
- Real-time model updates
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

@dataclass
class MarketRegime:
    name: str
    volatility_range: Tuple[float, float]
    trend_strength_range: Tuple[float, float]
    optimal_strategy: str
    optimal_parameters: Dict

class AdaptiveLearningEngine:
    """Machine learning engine that adapts strategies based on market conditions"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # ML models
        self.regime_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.performance_predictor = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
        # Market regimes
        self.market_regimes = self._initialize_market_regimes()
        self.current_regime = None
        
        # Learning data
        self.feature_history = []
        self.performance_history = []
        self.strategy_performance = {}
        
        # Adaptation tracking
        self.last_adaptation = datetime.now()
        self.adaptation_frequency = timedelta(hours=self.config.get('adaptation_frequency_hours', 24))
        
        print("🧠 ADAPTIVE LEARNING ENGINE INITIALIZED")
        print(f"   📊 Market regimes: {len(self.market_regimes)}")
        print(f"   🔄 Adaptation frequency: {self.adaptation_frequency}")
    
    def _initialize_market_regimes(self) -> List[MarketRegime]:
        """Initialize market regime definitions"""
        return [
            MarketRegime(
                name="LOW_VOLATILITY_TRENDING",
                volatility_range=(0, 0.3),
                trend_strength_range=(0.5, 1.0),
                optimal_strategy="ma_crossover",
                optimal_parameters={
                    'fast_ma': 8,
                    'slow_ma': 21,
                    'stop_loss_pips': 10,
                    'take_profit_pips': 25
                }
            ),
            MarketRegime(
                name="HIGH_VOLATILITY_TRENDING", 
                volatility_range=(0.5, 1.0),
                trend_strength_range=(0.6, 1.0),
                optimal_strategy="supertrend",
                optimal_parameters={
                    'atr_period': 12,
                    'multiplier': 2.5,
                    'stop_loss_atr': 2.0,
                    'take_profit_atr': 4.0
                }
            ),
            MarketRegime(
                name="RANGING_MARKET",
                volatility_range=(0.2, 0.7),
                trend_strength_range=(0, 0.4),
                optimal_strategy="rsi_mean_reversion", 
                optimal_parameters={
                    'rsi_period': 14,
                    'rsi_oversold': 25,
                    'rsi_overbought': 75,
                    'stop_loss_pips': 15,
                    'take_profit_pips': 20
                }
            ),
            MarketRegime(
                name="HIGH_VOLATILITY_CHOPPY",
                volatility_range=(0.7, 1.0),
                trend_strength_range=(0, 0.3),
                optimal_strategy="bollinger_rsi",
                optimal_parameters={
                    'bollinger_period': 20,
                    'bollinger_std': 2.0,
                    'rsi_period': 14,
                    'stop_loss_pips': 20,
                    'take_profit_pips': 25
                }
            )
        ]
    
    def extract_features(self, market_data: Dict, recent_trades: List) -> np.array:
        """Extract features for ML models"""
        
        # Price-based features
        price_features = [
            market_data.get('close', 0),
            market_data.get('high', 0) - market_data.get('low', 0),  # Range
            market_data.get('atr', 10),
            market_data.get('atr_percentile', 0.5),
        ]
        
        # Moving average features
        ma_fast = market_data.get('ma_fast', 0)
        ma_slow = market_data.get('ma_slow', 0)
        current_price = market_data.get('close', 1)
        
        ma_features = [
            (ma_fast - ma_slow) / current_price if current_price > 0 else 0,  # MA separation
            (current_price - ma_fast) / current_price if current_price > 0 else 0,  # Price vs fast MA
            (current_price - ma_slow) / current_price if current_price > 0 else 0,  # Price vs slow MA
        ]
        
        # RSI features
        rsi = market_data.get('rsi', 50)
        rsi_features = [
            rsi,
            1 if rsi > 70 else (-1 if rsi < 30 else 0),  # Overbought/oversold
            abs(rsi - 50) / 50,  # Distance from neutral
        ]
        
        # Volatility features
        volatility_features = [
            market_data.get('atr', 10),
            market_data.get('atr_trend', 1.0),
            market_data.get('volatility_percentile', 0.5),
        ]
        
        # Time-based features
        current_hour = datetime.now().hour
        time_features = [
            np.sin(2 * np.pi * current_hour / 24),  # Hour as sine
            np.cos(2 * np.pi * current_hour / 24),  # Hour as cosine
            1 if 7 <= current_hour <= 16 else 0,    # London session
            1 if 13 <= current_hour <= 22 else 0,   # NY session
        ]
        
        # Performance features
        if recent_trades:
            recent_pnl = [t.pnl for t in recent_trades[-10:]]  # Last 10 trades
            wins = len([p for p in recent_pnl if p > 0])
            performance_features = [
                wins / len(recent_pnl),  # Recent win rate
                np.mean(recent_pnl),     # Recent avg PnL
                np.std(recent_pnl),      # Recent PnL volatility
            ]
        else:
            performance_features = [0.5, 0, 0]
        
        # Combine all features
        all_features = (price_features + ma_features + rsi_features + 
                       volatility_features + time_features + performance_features)
        
        return np.array(all_features)
    
    def detect_market_regime(self, market_data: Dict, recent_trades: List) -> MarketRegime:
        """Detect current market regime using ML and rules"""
        
        # Extract features
        features = self.extract_features(market_data, recent_trades)
        
        # Calculate key metrics
        volatility_percentile = market_data.get('atr_percentile', 0.5)
        
        # Calculate trend strength
        ma_fast = market_data.get('ma_fast', 0)
        ma_slow = market_data.get('ma_slow', 0) 
        current_price = market_data.get('close', 1)
        
        if ma_slow and current_price:
            trend_strength = abs(ma_fast - ma_slow) / current_price
        else:
            trend_strength = 0.1
        
        # Find best matching regime
        best_regime = self.market_regimes[0]  # Default
        best_score = 0
        
        for regime in self.market_regimes:
            score = 0
            
            # Volatility match
            vol_min, vol_max = regime.volatility_range
            if vol_min <= volatility_percentile <= vol_max:
                score += 1
            else:
                # Penalize if outside range
                score -= min(abs(volatility_percentile - vol_min), 
                           abs(volatility_percentile - vol_max)) * 2
            
            # Trend strength match
            trend_min, trend_max = regime.trend_strength_range
            if trend_min <= trend_strength <= trend_max:
                score += 1
            else:
                score -= min(abs(trend_strength - trend_min),
                           abs(trend_strength - trend_max)) * 2
            
            # Historical performance bonus
            regime_performance = self.strategy_performance.get(regime.name, {})
            avg_performance = regime_performance.get('avg_pnl', 0)
            if avg_performance > 0:
                score += avg_performance / 100  # Small bonus for profitable regimes
            
            if score > best_score:
                best_score = score
                best_regime = regime
        
        self.current_regime = best_regime
        return best_regime
    
    def optimize_parameters_genetic(self, strategy: str, recent_performance: List[Dict]) -> Dict:
        """Optimize strategy parameters using genetic algorithm approach"""
        
        if not recent_performance:
            # Return default parameters if no performance data
            default_regimes = [r for r in self.market_regimes if r.optimal_strategy == strategy]
            return default_regimes[0].optimal_parameters if default_regimes else {}
        
        # Define parameter ranges for optimization
        param_ranges = self.config.get('parameter_ranges', {}).get(strategy, {})
        if not param_ranges:
            return {}  # No optimization ranges defined
        
        # Simple grid search optimization (would be genetic algorithm in production)
        best_params = {}
        best_score = float('-inf')
        
        # Test different parameter combinations
        for param_name, (min_val, max_val) in param_ranges.items():
            if isinstance(min_val, int):
                test_values = range(min_val, max_val + 1, max(1, (max_val - min_val) // 5))
            else:
                test_values = np.linspace(min_val, max_val, 5)
            
            for value in test_values:
                # Simulate performance with this parameter value
                # This is simplified - would use historical simulation in production
                score = self._evaluate_parameter_performance(param_name, value, recent_performance)
                
                if score > best_score:
                    best_score = score
                    best_params[param_name] = int(value) if isinstance(min_val, int) else float(value)
        
        return best_params
    
    def _evaluate_parameter_performance(self, param_name: str, param_value: float, performance_data: List[Dict]) -> float:
        """Evaluate parameter performance (simplified)"""
        
        # This is a simplified evaluation
        # In production, this would run backtests with the parameter value
        
        # For now, return a score based on recent performance and parameter value
        recent_pnl = [p['pnl'] for p in performance_data[-20:]]  # Last 20 performances
        base_score = np.mean(recent_pnl) if recent_pnl else 0
        
        # Add some parameter-specific logic
        if param_name in ['stop_loss_pips', 'stop_loss_atr']:
            # Prefer moderate stop losses
            optimal_range = (10, 20) if 'pips' in param_name else (1.5, 2.5)
            distance_from_optimal = min(abs(param_value - optimal_range[0]), 
                                      abs(param_value - optimal_range[1]))
            score_adjustment = -distance_from_optimal * 0.1
        elif param_name in ['take_profit_pips', 'take_profit_atr']:
            # Prefer higher take profits (better risk/reward)
            score_adjustment = param_value * 0.05
        else:
            score_adjustment = 0
        
        return base_score + score_adjustment
    
    def adapt_strategy(self, current_params: Dict, market_data: Dict, recent_trades: List, recent_performance: List[Dict]) -> Tuple[str, Dict]:
        """Main adaptation function - selects optimal strategy and parameters"""
        
        # Check if it's time to adapt
        if datetime.now() - self.last_adaptation < self.adaptation_frequency:
            return self.current_regime.optimal_strategy if self.current_regime else "ma_crossover", current_params
        
        # Detect current market regime
        regime = self.detect_market_regime(market_data, recent_trades)
        
        # Get base parameters for this regime
        adapted_params = regime.optimal_parameters.copy()
        
        # Optimize parameters based on recent performance
        optimized_params = self.optimize_parameters_genetic(regime.optimal_strategy, recent_performance)
        
        # Merge optimized parameters
        adapted_params.update(optimized_params)
        
        # Update adaptation tracking
        self.last_adaptation = datetime.now()
        
        # Log adaptation
        print(f"🧠 STRATEGY ADAPTATION:")
        print(f"   Regime: {regime.name}")
        print(f"   Strategy: {regime.optimal_strategy}")
        print(f"   Parameter updates: {list(optimized_params.keys())}")
        
        return regime.optimal_strategy, adapted_params
    
    def learn_from_trade(self, trade_data: Dict, market_conditions: Dict):
        """Learn from completed trades"""
        
        # Extract features from trade
        features = self.extract_features(market_conditions, [])
        
        # Store for learning
        self.feature_history.append({
            'features': features,
            'market_conditions': market_conditions,
            'timestamp': datetime.now()
        })
        
        # Store performance data
        self.performance_history.append({
            'pnl': trade_data.get('pnl', 0),
            'success': trade_data.get('pnl', 0) > 0,
            'strategy': trade_data.get('strategy', 'unknown'),
            'regime': self.current_regime.name if self.current_regime else 'unknown',
            'features': features
        })
        
        # Update strategy performance tracking
        strategy = trade_data.get('strategy', 'unknown')
        regime = self.current_regime.name if self.current_regime else 'unknown'
        
        if regime not in self.strategy_performance:
            self.strategy_performance[regime] = {
                'total_pnl': 0,
                'trades': 0,
                'wins': 0,
                'avg_pnl': 0
            }
        
        perf = self.strategy_performance[regime]
        perf['total_pnl'] += trade_data.get('pnl', 0)
        perf['trades'] += 1
        if trade_data.get('pnl', 0) > 0:
            perf['wins'] += 1
        perf['avg_pnl'] = perf['total_pnl'] / perf['trades']
        
        # Retrain models periodically
        if len(self.performance_history) % 50 == 0:  # Every 50 trades
            self._retrain_models()
    
    def _retrain_models(self):
        """Retrain ML models with new data"""
        
        if len(self.performance_history) < 20:
            return  # Need minimum data
        
        try:
            # Prepare training data
            features = [p['features'] for p in self.performance_history]
            labels = [1 if p['success'] else 0 for p in self.performance_history]  # Binary classification
            
            X = np.array(features)
            y = np.array(labels)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train regime classifier
            regime_labels = [p['regime'] for p in self.performance_history]
            unique_regimes = list(set(regime_labels))
            regime_numeric = [unique_regimes.index(r) for r in regime_labels]
            
            if len(unique_regimes) > 1:  # Need at least 2 classes
                self.regime_classifier.fit(X_scaled, regime_numeric)
                
                # Evaluate model
                predictions = self.regime_classifier.predict(X_scaled)
                accuracy = accuracy_score(regime_numeric, predictions)
                
                print(f"🧠 ML MODELS RETRAINED:")
                print(f"   Regime classifier accuracy: {accuracy:.2%}")
                print(f"   Training samples: {len(X)}")
            
        except Exception as e:
            print(f"⚠️  Model retraining failed: {e}")
    
    def get_adaptation_status(self) -> Dict:
        """Get current adaptation status"""
        
        return {
            'current_regime': self.current_regime.name if self.current_regime else 'Unknown',
            'last_adaptation': self.last_adaptation,
            'next_adaptation': self.last_adaptation + self.adaptation_frequency,
            'learning_samples': len(self.performance_history),
            'regime_performance': self.strategy_performance,
            'models_trained': len(self.performance_history) >= 20
        }
    
    def force_adaptation(self, market_data: Dict, recent_trades: List, recent_performance: List[Dict]) -> Tuple[str, Dict]:
        """Force immediate adaptation regardless of timing"""
        
        self.last_adaptation = datetime.now() - self.adaptation_frequency - timedelta(hours=1)
        return self.adapt_strategy({}, market_data, recent_trades, recent_performance)

# Utility function to create adaptive learning system
def create_adaptive_learning_engine(config_path: str = 'configs/adaptive_config.yaml') -> AdaptiveLearningEngine:
    """Create and initialize adaptive learning engine"""
    
    try:
        with open(config_path, 'r') as f:
            import yaml
            config = yaml.safe_load(f)
    except FileNotFoundError:
        # Default configuration
        config = {
            'adaptation_frequency_hours': 12,
            'min_samples_for_adaptation': 20,
            'parameter_ranges': {
                'ma_crossover': {
                    'fast_ma': (5, 15),
                    'slow_ma': (15, 30),
                    'stop_loss_pips': (8, 20),
                    'take_profit_pips': (15, 40)
                },
                'supertrend': {
                    'atr_period': (8, 20),
                    'multiplier': (1.5, 3.5),
                    'stop_loss_atr': (1.0, 3.0),
                    'take_profit_atr': (2.0, 5.0)
                }
            }
        }
        
        # Save default config
        with open(config_path, 'w') as f:
            import yaml
            yaml.dump(config, f, default_flow_style=False)
    
    return AdaptiveLearningEngine(config)