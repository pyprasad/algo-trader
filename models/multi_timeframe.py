# models/multi_timeframe.py

"""
📊 Multi-Timeframe Analysis Module

Analyzes market conditions across multiple timeframes (1m, 5m, 15m, 1h, 4h, 1d)
to provide comprehensive market context and improve signal quality.

Features:
- Higher timeframe trend confirmation
- Support/resistance level detection
- Multi-timeframe RSI divergence
- Trend strength analysis
- Confluence zone identification

Author: Enhanced Algo Trading System
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from data.db import db, sanitize_collection_name
from models.rsi import compute_rsi
from models.atr import compute_atr
from models.ema import compute_ema
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

class TimeframeResampler:
    """Resamples tick data to different timeframes"""
    
    @staticmethod
    def resample_ticks_to_ohlc(ticks: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Convert tick data to OHLC bars for specified timeframe"""
        if ticks.empty:
            return pd.DataFrame()
        
        # Ensure we have the right columns
        if 'bid' not in ticks.columns or 'offer' not in ticks.columns:
            return pd.DataFrame()
        
        # Create midprice
        ticks['midprice'] = (ticks['bid'] + ticks['offer']) / 2
        
        # Set timestamp as index if not already
        if 'timestamp' in ticks.columns:
            ticks = ticks.set_index('timestamp')
        
        # Ensure index is datetime
        if not isinstance(ticks.index, pd.DatetimeIndex):
            ticks.index = pd.to_datetime(ticks.index)
        
        # Resample to specified timeframe
        ohlc = ticks['midprice'].resample(timeframe).agg({
            'open': 'first',
            'high': 'max', 
            'low': 'min',
            'close': 'last',
            'volume': 'count'  # Use tick count as volume proxy
        }).dropna()
        
        return ohlc
    
    @staticmethod
    def get_timeframe_data(market: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """Get OHLC data for a specific timeframe"""
        # Get raw tick data
        collection_name = sanitize_collection_name(market)
        if collection_name not in db.list_collection_names():
            return pd.DataFrame()
        
        tick_collection = db[collection_name]
        
        # Calculate how far back we need to go based on timeframe
        timeframe_multipliers = {
            '1min': 1, '5min': 5, '15min': 15, '30min': 30,
            '1H': 60, '4H': 240, '1D': 1440
        }
        
        multiplier = timeframe_multipliers.get(timeframe, 1)
        lookback_minutes = limit * multiplier * 2  # Get extra data for resampling
        
        since = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        
        # Fetch tick data
        cursor = tick_collection.find(
            {"timestamp": {"$gte": since}}
        ).sort("timestamp", 1)
        
        ticks = list(cursor)
        if not ticks:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(ticks)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Resample to OHLC
        ohlc_data = TimeframeResampler.resample_ticks_to_ohlc(df, timeframe)
        
        # Return most recent bars
        return ohlc_data.tail(limit)

class MultiTimeframeIndicators:
    """Calculate indicators across multiple timeframes"""
    
    @staticmethod
    def calculate_multi_tf_rsi(market: str, timeframes: List[str], period: int = 14) -> Dict:
        """Calculate RSI across multiple timeframes"""
        rsi_data = {}
        
        for tf in timeframes:
            ohlc = TimeframeResampler.get_timeframe_data(market, tf, limit=50)
            if not ohlc.empty:
                rsi_series = compute_rsi(ohlc['close'], period=period)
                if not rsi_series.empty:
                    current_rsi = rsi_series.iloc[-1]
                    prev_rsi = rsi_series.iloc[-2] if len(rsi_series) > 1 else current_rsi
                    
                    # Determine RSI condition
                    if current_rsi > 70:
                        condition = "overbought"
                    elif current_rsi < 30:
                        condition = "oversold"
                    else:
                        condition = "neutral"
                    
                    rsi_data[tf] = {
                        "value": round(current_rsi, 2),
                        "previous": round(prev_rsi, 2),
                        "change": round(current_rsi - prev_rsi, 2),
                        "condition": condition
                    }
        
        return rsi_data
    
    @staticmethod
    def calculate_multi_tf_trend(market: str, timeframes: List[str], ema_period: int = 50) -> Dict:
        """Calculate trend direction across multiple timeframes"""
        trend_data = {}
        
        for tf in timeframes:
            ohlc = TimeframeResampler.get_timeframe_data(market, tf, limit=100)
            if not ohlc.empty:
                ema_series = compute_ema(ohlc['close'], span=ema_period)
                if not ema_series.empty:
                    current_price = ohlc['close'].iloc[-1]
                    current_ema = ema_series.iloc[-1]
                    prev_ema = ema_series.iloc[-2] if len(ema_series) > 1 else current_ema
                    
                    # Determine trend
                    if current_price > current_ema and current_ema > prev_ema:
                        trend = "strong_uptrend"
                    elif current_price > current_ema:
                        trend = "uptrend"
                    elif current_price < current_ema and current_ema < prev_ema:
                        trend = "strong_downtrend"
                    elif current_price < current_ema:
                        trend = "downtrend"
                    else:
                        trend = "sideways"
                    
                    trend_data[tf] = {
                        "trend": trend,
                        "price": round(current_price, 2),
                        "ema": round(current_ema, 2),
                        "distance_from_ema": round(((current_price - current_ema) / current_ema) * 100, 2)
                    }
        
        return trend_data

class SupportResistanceFinder:
    """Identifies support and resistance levels across timeframes"""
    
    @staticmethod
    def find_pivot_points(ohlc: pd.DataFrame, window: int = 5) -> Dict:
        """Find pivot high and low points"""
        if len(ohlc) < window * 2 + 1:
            return {"support_levels": [], "resistance_levels": []}
        
        highs = ohlc['high'].values
        lows = ohlc['low'].values
        
        resistance_levels = []
        support_levels = []
        
        # Find pivot highs (resistance)
        for i in range(window, len(highs) - window):
            if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
               all(highs[i] >= highs[i+j] for j in range(1, window+1)):
                resistance_levels.append(highs[i])
        
        # Find pivot lows (support)
        for i in range(window, len(lows) - window):
            if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
               all(lows[i] <= lows[i+j] for j in range(1, window+1)):
                support_levels.append(lows[i])
        
        return {
            "support_levels": sorted(support_levels, reverse=True)[:5],  # Top 5 support levels
            "resistance_levels": sorted(resistance_levels)[:5]  # Top 5 resistance levels
        }
    
    @staticmethod
    def get_multi_tf_support_resistance(market: str, timeframes: List[str]) -> Dict:
        """Get support/resistance levels across multiple timeframes"""
        levels_data = {}
        
        for tf in timeframes:
            ohlc = TimeframeResampler.get_timeframe_data(market, tf, limit=100)
            if not ohlc.empty:
                levels = SupportResistanceFinder.find_pivot_points(ohlc)
                levels_data[tf] = levels
        
        return levels_data

class MultiTimeframeAnalyzer:
    """Main class for multi-timeframe analysis"""
    
    def __init__(self):
        self.timeframes = ['1min', '5min', '15min', '1H', '4H']
        self.indicators = MultiTimeframeIndicators()
        self.sr_finder = SupportResistanceFinder()
    
    def analyze_market(self, market: str) -> Dict:
        """Comprehensive multi-timeframe analysis"""
        print(f"📊 Running multi-timeframe analysis for {market}...")
        
        # Get RSI across timeframes
        rsi_data = self.indicators.calculate_multi_tf_rsi(market, self.timeframes)
        
        # Get trend across timeframes
        trend_data = self.indicators.calculate_multi_tf_trend(market, self.timeframes)
        
        # Get support/resistance levels
        sr_data = self.sr_finder.get_multi_tf_support_resistance(market, self.timeframes)
        
        # Analyze confluence
        confluence = self._analyze_confluence(rsi_data, trend_data)
        
        # Generate multi-timeframe signal
        signal = self._generate_multi_tf_signal(rsi_data, trend_data, confluence)
        
        return {
            "market": market,
            "timestamp": datetime.now().isoformat(),
            "rsi_analysis": rsi_data,
            "trend_analysis": trend_data,
            "support_resistance": sr_data,
            "confluence": confluence,
            "multi_tf_signal": signal
        }
    
    def _analyze_confluence(self, rsi_data: Dict, trend_data: Dict) -> Dict:
        """Analyze confluence across timeframes"""
        confluence = {
            "bullish_confluence": 0,
            "bearish_confluence": 0,
            "total_timeframes": len(self.timeframes),
            "agreement_percentage": 0
        }
        
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0
        
        for tf in self.timeframes:
            if tf in rsi_data and tf in trend_data:
                rsi_info = rsi_data[tf]
                trend_info = trend_data[tf]
                
                # Count bullish signals
                if (rsi_info["condition"] == "oversold" and rsi_info["change"] > 0) or \
                   ("uptrend" in trend_info["trend"]):
                    bullish_signals += 1
                
                # Count bearish signals  
                if (rsi_info["condition"] == "overbought" and rsi_info["change"] < 0) or \
                   ("downtrend" in trend_info["trend"]):
                    bearish_signals += 1
                
                total_signals += 1
        
        if total_signals > 0:
            confluence["bullish_confluence"] = bullish_signals
            confluence["bearish_confluence"] = bearish_signals
            confluence["agreement_percentage"] = round(max(bullish_signals, bearish_signals) / total_signals * 100, 1)
        
        # Determine overall confluence
        if bullish_signals > bearish_signals * 1.5:
            confluence["overall"] = "bullish"
        elif bearish_signals > bullish_signals * 1.5:
            confluence["overall"] = "bearish"
        else:
            confluence["overall"] = "neutral"
        
        return confluence
    
    def _generate_multi_tf_signal(self, rsi_data: Dict, trend_data: Dict, confluence: Dict) -> Dict:
        """Generate trading signal based on multi-timeframe analysis"""
        # Higher timeframe trend (4H) has most weight
        higher_tf_trend = trend_data.get('4H', {}).get('trend', 'sideways')
        
        # Medium timeframe confirmation (1H)
        medium_tf_trend = trend_data.get('1H', {}).get('trend', 'sideways')
        
        # Short-term entry (15min, 5min)
        short_tf_rsi = rsi_data.get('15min', {}).get('condition', 'neutral')
        
        signal = "HOLD"
        strength = 0
        reasoning = []
        
        # Strong bullish scenario
        if (confluence["overall"] == "bullish" and 
            confluence["agreement_percentage"] > 60 and
            "uptrend" in higher_tf_trend):
            signal = "BUY"
            strength = min(1.0, confluence["agreement_percentage"] / 100 + 0.3)
            reasoning.append(f"Higher TF uptrend with {confluence['agreement_percentage']}% agreement")
        
        # Strong bearish scenario
        elif (confluence["overall"] == "bearish" and 
              confluence["agreement_percentage"] > 60 and
              "downtrend" in higher_tf_trend):
            signal = "SELL"
            strength = min(1.0, confluence["agreement_percentage"] / 100 + 0.3)
            reasoning.append(f"Higher TF downtrend with {confluence['agreement_percentage']}% agreement")
        
        # Counter-trend opportunity (buy oversold in uptrend)
        elif ("uptrend" in higher_tf_trend and 
              short_tf_rsi == "oversold"):
            signal = "BUY"
            strength = 0.6
            reasoning.append("Counter-trend buy: oversold in higher TF uptrend")
        
        # Counter-trend opportunity (sell overbought in downtrend)
        elif ("downtrend" in higher_tf_trend and 
              short_tf_rsi == "overbought"):
            signal = "SELL"
            strength = 0.6
            reasoning.append("Counter-trend sell: overbought in higher TF downtrend")
        
        return {
            "signal": signal,
            "strength": round(strength, 2),
            "confidence": confluence["agreement_percentage"] / 100,
            "reasoning": reasoning,
            "higher_tf_trend": higher_tf_trend,
            "confluence_score": confluence["agreement_percentage"]
        }

# Global multi-timeframe analyzer
_global_mtf_analyzer = None

def get_multi_timeframe_analyzer():
    """Get global multi-timeframe analyzer instance"""
    global _global_mtf_analyzer
    if _global_mtf_analyzer is None:
        _global_mtf_analyzer = MultiTimeframeAnalyzer()
    return _global_mtf_analyzer

def get_multi_timeframe_signal(market: str) -> Dict:
    """Quick function to get multi-timeframe signal for a market"""
    analyzer = get_multi_timeframe_analyzer()
    analysis = analyzer.analyze_market(market)
    return analysis.get("multi_tf_signal", {"signal": "HOLD", "strength": 0})

if __name__ == "__main__":
    # Test multi-timeframe analysis
    print("🧪 Testing Multi-Timeframe Analysis")
    print("=" * 50)
    
    analyzer = MultiTimeframeAnalyzer()
    
    # Test with DAX
    analysis = analyzer.analyze_market("DAX")
    
    print(f"\n📊 Multi-Timeframe Analysis for DAX:")
    print(f"   Signal: {analysis['multi_tf_signal']['signal']}")
    print(f"   Strength: {analysis['multi_tf_signal']['strength']}")
    print(f"   Confidence: {analysis['multi_tf_signal']['confidence']:.2f}")
    print(f"   Higher TF Trend: {analysis['multi_tf_signal']['higher_tf_trend']}")
    
    if analysis['multi_tf_signal']['reasoning']:
        print(f"   Reasoning: {', '.join(analysis['multi_tf_signal']['reasoning'])}")
    
    print(f"\n📈 Confluence Analysis:")
    confluence = analysis['confluence']
    print(f"   Overall: {confluence['overall']}")
    print(f"   Agreement: {confluence['agreement_percentage']}%")
    print(f"   Bullish TFs: {confluence['bullish_confluence']}")
    print(f"   Bearish TFs: {confluence['bearish_confluence']}")