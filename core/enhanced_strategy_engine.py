# core/enhanced_strategy_engine.py

"""
🚀 Enhanced Strategy Engine

Combines multiple analysis methods for superior trading signals:
- Technical indicators (RSI, ATR, EMA)
- Multi-timeframe analysis 
- News sentiment analysis
- Market regime detection
- Advanced signal synthesis

Author: Next-Gen Algo Trading System
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yaml
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Import existing modules
from models.rsi import compute_rsi
from models.atr import compute_atr
from models.ema import compute_ema
from models.regime_model import detect_regime
from core.signal_classifier import generate_trade_signal

# Import new enhanced modules
from data.news_sentiment import get_market_sentiment_signal
from models.multi_timeframe import get_multi_timeframe_signal
from models.ml_predictor import get_ml_trading_signal
from data.db import db, sanitize_collection_name

# Load enhanced config
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

# Load sentiment config
try:
    with open("configs/sentiment_config.yaml", "r") as f:
        sentiment_config = yaml.safe_load(f)
except FileNotFoundError:
    sentiment_config = {"integration": {"enabled": False, "sentiment_weight": 0.0}}

class SignalSynthesizer:
    """Combines multiple signal types into a unified trading decision"""
    
    def __init__(self):
        self.weights = {
            "technical": 0.3,       # Technical indicators
            "multi_timeframe": 0.25, # Multi-timeframe analysis
            "ml_prediction": 0.25,  # Machine Learning predictions
            "sentiment": 0.15,      # News sentiment
            "regime": 0.05         # Market regime
        }
        
        # Load weights from config if available
        if sentiment_config.get("integration", {}).get("enabled", False):
            sentiment_weight = sentiment_config["integration"]["sentiment_weight"]
            self.weights["sentiment"] = sentiment_weight
            self.weights["technical"] = 0.7 - sentiment_weight
    
    def synthesize_signals(self, signals: Dict) -> Dict:
        """Combine multiple signals into final trading decision"""
        # Extract individual signals
        technical_signal = signals.get("technical", {})
        mtf_signal = signals.get("multi_timeframe", {})
        ml_signal = signals.get("ml_prediction", {})
        sentiment_signal = signals.get("sentiment", {})
        regime = signals.get("regime", "neutral")
        
        # Convert signals to numerical scores (-1 to 1)
        scores = {}
        
        # Technical score
        tech_sig = technical_signal.get("signal", "HOLD")
        if tech_sig == "BUY":
            scores["technical"] = 0.8
        elif tech_sig == "SELL":
            scores["technical"] = -0.8
        else:
            scores["technical"] = 0.0
        
        # Multi-timeframe score
        mtf_sig = mtf_signal.get("signal", "HOLD")
        mtf_strength = mtf_signal.get("strength", 0)
        if mtf_sig == "BUY":
            scores["multi_timeframe"] = mtf_strength
        elif mtf_sig == "SELL":
            scores["multi_timeframe"] = -mtf_strength
        else:
            scores["multi_timeframe"] = 0.0
        
        # ML prediction score
        ml_sig = ml_signal.get("ml_signal", "HOLD")
        ml_confidence = ml_signal.get("ml_confidence", 0)
        if ml_sig == "BUY":
            scores["ml_prediction"] = ml_confidence
        elif ml_sig == "SELL":
            scores["ml_prediction"] = -ml_confidence
        else:
            scores["ml_prediction"] = 0.0
        
        # Sentiment score
        sentiment_score = sentiment_signal.get("sentiment_score", 0)
        sentiment_confidence = sentiment_signal.get("confidence", 0)
        scores["sentiment"] = sentiment_score * sentiment_confidence
        
        # Regime score (influences risk)
        if regime == "trending":
            scores["regime"] = 0.2  # Slightly positive for trend following
        elif regime == "volatile":
            scores["regime"] = -0.3  # Negative for volatile markets
        else:
            scores["regime"] = 0.0
        
        # Calculate weighted composite score
        composite_score = sum(
            scores[signal_type] * self.weights[signal_type] 
            for signal_type in scores
        )
        
        # Generate final signal
        final_signal = "HOLD"
        signal_strength = abs(composite_score)
        
        if composite_score > 0.3:
            final_signal = "BUY"
        elif composite_score < -0.3:
            final_signal = "SELL"
        
        # Calculate confidence based on signal agreement
        signal_agreement = self._calculate_signal_agreement(signals)
        
        return {
            "final_signal": final_signal,
            "composite_score": round(composite_score, 3),
            "signal_strength": round(signal_strength, 3),
            "confidence": round(signal_agreement, 3),
            "individual_scores": scores,
            "signal_breakdown": {
                "technical": f"{tech_sig} ({scores['technical']:+.2f})",
                "multi_timeframe": f"{mtf_sig} ({scores['multi_timeframe']:+.2f})",
                "ml_prediction": f"{ml_sig} ({scores['ml_prediction']:+.2f})",
                "sentiment": f"{sentiment_signal.get('sentiment_signal', 'NEUTRAL')} ({scores['sentiment']:+.2f})",
                "regime": f"{regime} ({scores['regime']:+.2f})"
            }
        }
    
    def _calculate_signal_agreement(self, signals: Dict) -> float:
        """Calculate how much the different signals agree with each other"""
        signal_directions = []
        
        # Get signal directions
        tech_sig = signals.get("technical", {}).get("signal", "HOLD")
        if tech_sig != "HOLD":
            signal_directions.append(1 if tech_sig == "BUY" else -1)
        
        mtf_sig = signals.get("multi_timeframe", {}).get("signal", "HOLD") 
        if mtf_sig != "HOLD":
            signal_directions.append(1 if mtf_sig == "BUY" else -1)
        
        sentiment_sig = signals.get("sentiment", {}).get("sentiment_signal", "HOLD")
        if sentiment_sig != "HOLD":
            signal_directions.append(1 if sentiment_sig == "BUY" else -1)
        
        ml_sig = signals.get("ml_prediction", {}).get("ml_signal", "HOLD")
        if ml_sig != "HOLD":
            signal_directions.append(1 if ml_sig == "BUY" else -1)
        
        if not signal_directions:
            return 0.5  # Neutral confidence
        
        # Calculate agreement
        if len(set(signal_directions)) == 1:
            return 0.9  # All signals agree
        elif len(signal_directions) >= 3:
            # Majority agreement
            positive_count = sum(1 for x in signal_directions if x > 0)
            negative_count = sum(1 for x in signal_directions if x < 0)
            majority = max(positive_count, negative_count)
            return majority / len(signal_directions) * 0.8
        else:
            return 0.3  # Disagreement

class EnhancedStrategyEngine:
    """Enhanced strategy engine with multi-signal analysis"""
    
    def __init__(self):
        # Load configuration
        self.rsi_period = config["strategy"]["rsi_period"]
        self.buy_threshold = config["strategy"]["rsi_buy_threshold"]
        self.sell_threshold = config["strategy"]["rsi_sell_threshold"]
        self.dynamic_atr_sltp = config["strategy"]["dynamic_atr_sltp"]
        
        # Initialize synthesizer
        self.synthesizer = SignalSynthesizer()
        
        # Feature flags
        self.sentiment_enabled = sentiment_config.get("integration", {}).get("enabled", False)
        self.mtf_enabled = True  # Multi-timeframe always enabled
        
        print(f"🚀 Enhanced Strategy Engine initialized")
        print(f"   📰 Sentiment Analysis: {'✅ Enabled' if self.sentiment_enabled else '❌ Disabled'}")
        print(f"   📊 Multi-Timeframe: {'✅ Enabled' if self.mtf_enabled else '❌ Disabled'}")
    
    def analyze_market_conditions(self, prices: List[float], market_name: str = None) -> Dict:
        """
        Enhanced market analysis combining multiple signal sources
        
        Args:
            prices: List of recent prices (most recent last)
            market_name: Market identifier for external data sources
            
        Returns:
            Comprehensive analysis with synthesized signals
        """
        if len(prices) < self.rsi_period + 5:
            if market_name:
                print(f"❌ {market_name}: Insufficient price data ({len(prices)} prices)")
            return None
        
        print(f"🔍 Running enhanced analysis for {market_name}...")
        
        # === 1. TECHNICAL ANALYSIS ===
        technical_signals = self._analyze_technical_indicators(prices)
        
        # === 2. MULTI-TIMEFRAME ANALYSIS ===
        mtf_signals = {}
        if self.mtf_enabled and market_name:
            try:
                mtf_signals = get_multi_timeframe_signal(market_name)
                print(f"   📊 Multi-TF: {mtf_signals.get('signal', 'HOLD')} (confidence: {mtf_signals.get('confidence', 0):.2f})")
            except Exception as e:
                print(f"   ⚠️ Multi-TF analysis failed: {e}")
                mtf_signals = {"signal": "HOLD", "strength": 0, "confidence": 0}
        
        # === 3. SENTIMENT ANALYSIS ===
        sentiment_signals = {}
        if self.sentiment_enabled and market_name:
            try:
                sentiment_signals = get_market_sentiment_signal(market_name)
                print(f"   📰 Sentiment: {sentiment_signals.get('sentiment_signal', 'HOLD')} (score: {sentiment_signals.get('sentiment_score', 0):.2f})")
            except Exception as e:
                print(f"   ⚠️ Sentiment analysis failed: {e}")
                sentiment_signals = {"sentiment_signal": "HOLD", "sentiment_score": 0, "confidence": 0}
        
        # === 4. MACHINE LEARNING PREDICTION ===
        ml_signals = {}
        if market_name:
            try:
                ml_signals = get_ml_trading_signal(market_name, prices)
                if "error" not in ml_signals:
                    print(f"   🤖 ML: {ml_signals.get('ml_signal', 'HOLD')} (confidence: {ml_signals.get('ml_confidence', 0):.2f})")
                else:
                    print(f"   ⚠️ ML prediction failed: {ml_signals['error']}")
                    ml_signals = {"ml_signal": "HOLD", "ml_confidence": 0}
            except Exception as e:
                print(f"   ⚠️ ML prediction failed: {e}")
                ml_signals = {"ml_signal": "HOLD", "ml_confidence": 0}
        
        # === 5. SIGNAL SYNTHESIS ===
        all_signals = {
            "technical": technical_signals,
            "multi_timeframe": mtf_signals,
            "ml_prediction": ml_signals,
            "sentiment": sentiment_signals,
            "regime": technical_signals.get("regime", "neutral")
        }
        
        synthesized = self.synthesizer.synthesize_signals(all_signals)
        
        # === 6. COMPILE COMPREHENSIVE RESULT ===
        comprehensive_result = {
            # Core technical data
            "rsi": technical_signals.get("rsi"),
            "atr": technical_signals.get("atr"),
            "momentum": technical_signals.get("momentum"),
            "trend": technical_signals.get("trend"),
            "regime": technical_signals.get("regime"),
            "price": technical_signals.get("price"),
            
            # Enhanced signals
            "technical_signal": technical_signals.get("signal"),
            "multi_timeframe_signal": mtf_signals.get("signal", "HOLD") if mtf_signals else "HOLD",
            "ml_signal": ml_signals.get("ml_signal", "HOLD") if ml_signals else "HOLD",
            "sentiment_signal": sentiment_signals.get("sentiment_signal", "HOLD") if sentiment_signals else "HOLD",
            
            # Final synthesized decision
            "signal": synthesized["final_signal"],
            "composite_score": synthesized["composite_score"],
            "signal_strength": synthesized["signal_strength"],
            "confidence": synthesized["confidence"],
            
            # Detailed breakdown
            "signal_breakdown": synthesized["signal_breakdown"],
            "analysis_timestamp": datetime.now().isoformat(),
            
            # Additional context
            "mtf_confidence": mtf_signals.get("confidence", 0) if mtf_signals else 0,
            "ml_confidence": ml_signals.get("ml_confidence", 0) if ml_signals else 0,
            "sentiment_score": sentiment_signals.get("sentiment_score", 0) if sentiment_signals else 0
        }
        
        # Log the enhanced analysis
        print(f"   🎯 Final Signal: {synthesized['final_signal']} (strength: {synthesized['signal_strength']:.2f}, confidence: {synthesized['confidence']:.2f})")
        
        return comprehensive_result
    
    def _analyze_technical_indicators(self, prices: List[float]) -> Dict:
        """Analyze traditional technical indicators"""
        # Convert to pandas DataFrame
        df = pd.DataFrame({'price': prices})
        df.index = pd.date_range(end=datetime.utcnow(), periods=len(prices), freq='1min')
        
        # Compute indicators
        df["rsi"] = compute_rsi(df["price"], period=self.rsi_period)
        df["atr"] = compute_atr(df["price"]) if self.dynamic_atr_sltp else None
        df["ema"] = compute_ema(df["price"], span=50)
        df["momentum"] = df["price"].pct_change(periods=5) * 100
        
        # Get latest values
        latest = df.iloc[-1]
        latest_price = latest["price"]
        latest_ema = latest["ema"]
        
        # Determine trend
        if latest_price > latest_ema:
            trend = "uptrend"
        elif latest_price < latest_ema:
            trend = "downtrend"
        else:
            trend = "sideways"
        
        # Detect market regime
        regime = detect_regime(df["price"])
        
        # Generate traditional signal
        signal = generate_trade_signal(
            rsi=latest["rsi"],
            atr=latest["atr"] if self.dynamic_atr_sltp else None,
            regime=regime,
            thresholds=(self.buy_threshold, self.sell_threshold),
            trend=trend,
            momentum=latest["momentum"] if pd.notna(latest["momentum"]) else None
        )
        
        return {
            "rsi": float(latest["rsi"]) if pd.notna(latest["rsi"]) else None,
            "atr": float(latest["atr"]) if self.dynamic_atr_sltp and pd.notna(latest["atr"]) else None,
            "regime": regime,
            "trend": trend,
            "signal": signal,
            "price": float(latest_price),
            "momentum": float(latest["momentum"]) if pd.notna(latest["momentum"]) else None
        }

# Global enhanced strategy engine
_global_enhanced_engine = None

def get_enhanced_strategy_engine():
    """Get global enhanced strategy engine instance"""
    global _global_enhanced_engine
    if _global_enhanced_engine is None:
        _global_enhanced_engine = EnhancedStrategyEngine()
    return _global_enhanced_engine

if __name__ == "__main__":
    # Test enhanced strategy engine
    print("🧪 Testing Enhanced Strategy Engine")
    print("=" * 50)
    
    # Simulate some price data
    import numpy as np
    np.random.seed(42)
    base_price = 23500
    prices = [base_price]
    
    # Generate realistic price series (trending down)
    for i in range(100):
        change = np.random.normal(-0.5, 15)  # Slight downward bias with volatility
        new_price = prices[-1] + change
        prices.append(max(23000, min(24000, new_price)))  # Keep within bounds
    
    # Test with the enhanced engine
    engine = get_enhanced_strategy_engine()
    result = engine.analyze_market_conditions(prices, "DAX")
    
    if result:
        print(f"\n📊 Enhanced Analysis Results for DAX:")
        print(f"   Final Signal: {result['signal']}")
        print(f"   Composite Score: {result['composite_score']}")
        print(f"   Signal Strength: {result['signal_strength']}")
        print(f"   Confidence: {result['confidence']}")
        
        print(f"\n🔍 Signal Breakdown:")
        for signal_type, details in result['signal_breakdown'].items():
            print(f"   {signal_type.title()}: {details}")
        
        print(f"\n📈 Technical Indicators:")
        print(f"   RSI: {result['rsi']:.2f}" if result['rsi'] else "   RSI: N/A")
        print(f"   Trend: {result['trend']}")
        print(f"   Regime: {result['regime']}")
        print(f"   Momentum: {result['momentum']:.2f}%" if result['momentum'] else "   Momentum: N/A")