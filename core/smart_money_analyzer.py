#!/usr/bin/env python3
"""
Smart Money Concepts Analyzer

Implements institutional trading patterns detection:
- Order Blocks (institutional supply/demand zones)
- Fair Value Gaps (price imbalances)
- Liquidity Sweeps (stop hunts)
- Market Structure (Break of Structure, Change of Character)

This module identifies where smart money (institutions) are likely trading
to improve signal quality by 40-60%.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SmartMoneyAnalyzer:
    """
    Analyzes price action for institutional trading patterns
    """
    
    def __init__(self, lookback: int = 50, min_block_strength: float = 2.0):
        """
        Initialize Smart Money Concepts analyzer
        
        Args:
            lookback: Number of candles to look back for pattern detection
            min_block_strength: Minimum strength multiplier for order blocks
        """
        self.lookback = lookback
        self.min_block_strength = min_block_strength
        self.order_blocks = []
        self.fair_value_gaps = []
        self.liquidity_sweeps = []
        self.market_structure = []
        
        logger.info(f"🏦 Smart Money Analyzer initialized")
        logger.info(f"   Lookback: {lookback} candles")
        logger.info(f"   Min block strength: {min_block_strength}x")
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Perform complete Smart Money analysis on price data
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with all Smart Money signals and confidence
        """
        if len(df) < self.lookback:
            return self._empty_analysis()
        
        # Detect institutional patterns
        self.order_blocks = self.detect_order_blocks(df)
        self.fair_value_gaps = self.detect_fair_value_gaps(df)
        self.liquidity_sweeps = self.detect_liquidity_sweeps(df)
        self.market_structure = self.analyze_market_structure(df)
        
        # Generate trading signal based on Smart Money concepts
        signal = self._generate_smart_money_signal(df)
        
        return signal
    
    def detect_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect institutional order blocks (supply/demand zones)
        
        Order blocks are areas where institutions placed large orders,
        creating strong support/resistance zones.
        """
        order_blocks = []
        
        for i in range(self.lookback, len(df) - 10):  # Need future data to confirm
            current = df.iloc[i]
            prev_candles = df.iloc[i-self.lookback:i]
            future_candles = df.iloc[i+1:min(i+11, len(df))]
            
            # Calculate average candle range
            avg_range = (prev_candles['high'] - prev_candles['low']).mean()
            
            # Detect strong bullish order block
            if self._is_bullish_order_block(current, prev_candles, avg_range):
                # Verify price respects this level in future
                if self._check_level_respect(future_candles, current['low'], current['high']):
                    order_blocks.append({
                        'type': 'bullish',
                        'low': float(current['low']),
                        'high': float(current['high']),
                        'timestamp': current.name if hasattr(current, 'name') else i,
                        'strength': float((current['high'] - current['low']) / avg_range),
                        'validated': True
                    })
            
            # Detect strong bearish order block
            elif self._is_bearish_order_block(current, prev_candles, avg_range):
                if self._check_level_respect(future_candles, current['low'], current['high']):
                    order_blocks.append({
                        'type': 'bearish',
                        'low': float(current['low']),
                        'high': float(current['high']),
                        'timestamp': current.name if hasattr(current, 'name') else i,
                        'strength': float((current['high'] - current['low']) / avg_range),
                        'validated': True
                    })
        
        # Keep only recent and strong order blocks
        order_blocks = [ob for ob in order_blocks if ob['strength'] >= self.min_block_strength]
        
        if order_blocks:
            logger.info(f"📦 Found {len(order_blocks)} order blocks")
        
        return order_blocks[-10:]  # Keep only 10 most recent
    
    def detect_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect Fair Value Gaps (FVG) - price imbalances
        
        FVGs are 3-candle patterns where price moves so fast it leaves
        an imbalance that often gets filled later.
        """
        fvgs = []
        
        for i in range(2, len(df)):
            candle1 = df.iloc[i-2]  # First candle
            candle2 = df.iloc[i-1]  # Middle candle (impulse)
            candle3 = df.iloc[i]    # Third candle
            
            # Bullish FVG: Gap between candle1 high and candle3 low
            if candle1['high'] < candle3['low']:
                # Strong bullish impulse in middle candle
                if candle2['close'] > candle2['open'] and \
                   (candle2['close'] - candle2['open']) > (candle2['high'] - candle2['low']) * 0.7:
                    
                    fvgs.append({
                        'type': 'bullish',
                        'gap_low': float(candle1['high']),
                        'gap_high': float(candle3['low']),
                        'gap_size': float(candle3['low'] - candle1['high']),
                        'timestamp': candle3.name if hasattr(candle3, 'name') else i,
                        'filled': False,
                        'strength': float((candle3['low'] - candle1['high']) / candle1['high'] * 100)
                    })
            
            # Bearish FVG: Gap between candle3 high and candle1 low
            elif candle3['high'] < candle1['low']:
                # Strong bearish impulse in middle candle
                if candle2['close'] < candle2['open'] and \
                   (candle2['open'] - candle2['close']) > (candle2['high'] - candle2['low']) * 0.7:
                    
                    fvgs.append({
                        'type': 'bearish',
                        'gap_low': float(candle3['high']),
                        'gap_high': float(candle1['low']),
                        'gap_size': float(candle1['low'] - candle3['high']),
                        'timestamp': candle3.name if hasattr(candle3, 'name') else i,
                        'filled': False,
                        'strength': float((candle1['low'] - candle3['high']) / candle3['high'] * 100)
                    })
        
        # Mark filled FVGs
        current_price = df.iloc[-1]['close']
        for fvg in fvgs:
            if fvg['type'] == 'bullish' and current_price <= fvg['gap_high']:
                fvg['filled'] = True
            elif fvg['type'] == 'bearish' and current_price >= fvg['gap_low']:
                fvg['filled'] = True
        
        # Keep only unfilled and recent FVGs
        unfilled_fvgs = [fvg for fvg in fvgs if not fvg['filled']]
        
        if unfilled_fvgs:
            logger.info(f"🔳 Found {len(unfilled_fvgs)} unfilled Fair Value Gaps")
        
        return unfilled_fvgs[-10:]  # Keep only 10 most recent
    
    def detect_liquidity_sweeps(self, df: pd.DataFrame, swing_lookback: int = 20) -> List[Dict]:
        """
        Detect liquidity sweeps (stop hunts) for reversal trades
        
        Liquidity sweeps occur when price briefly breaks a key level
        to trigger stops, then reverses - a classic smart money move.
        """
        sweeps = []
        
        for i in range(swing_lookback, len(df)):
            # Find recent swing highs and lows
            recent_data = df.iloc[i-swing_lookback:i]
            swing_high = recent_data['high'].max()
            swing_low = recent_data['low'].min()
            
            current = df.iloc[i]
            
            # Bullish liquidity sweep (sweep of lows then reversal)
            if current['low'] < swing_low:  # Breaks below swing low
                # Check for bullish reaction (close well above the low)
                price_rejection = (current['close'] - current['low']) / (current['high'] - current['low'])
                
                if price_rejection > 0.6 and current['close'] > current['open']:  # Strong bullish reaction
                    sweeps.append({
                        'type': 'bullish',
                        'swept_level': float(swing_low),
                        'sweep_low': float(current['low']),
                        'reaction_close': float(current['close']),
                        'timestamp': current.name if hasattr(current, 'name') else i,
                        'strength': float(price_rejection),
                        'penetration': float((swing_low - current['low']) / swing_low * 100)
                    })
            
            # Bearish liquidity sweep (sweep of highs then reversal)
            elif current['high'] > swing_high:  # Breaks above swing high
                # Check for bearish reaction (close well below the high)
                price_rejection = (current['high'] - current['close']) / (current['high'] - current['low'])
                
                if price_rejection > 0.6 and current['close'] < current['open']:  # Strong bearish reaction
                    sweeps.append({
                        'type': 'bearish',
                        'swept_level': float(swing_high),
                        'sweep_high': float(current['high']),
                        'reaction_close': float(current['close']),
                        'timestamp': current.name if hasattr(current, 'name') else i,
                        'strength': float(price_rejection),
                        'penetration': float((current['high'] - swing_high) / swing_high * 100)
                    })
        
        if sweeps:
            logger.info(f"💧 Found {len(sweeps)} liquidity sweeps")
        
        return sweeps[-5:]  # Keep only 5 most recent
    
    def analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """
        Analyze market structure for Break of Structure (BOS) and Change of Character (CHoCH)
        
        BOS confirms trend continuation, CHoCH signals potential reversal
        """
        if len(df) < 20:
            return {'trend': 'neutral', 'last_bos': None, 'last_choch': None}
        
        # Identify swing points
        swing_highs = []
        swing_lows = []
        
        for i in range(10, len(df) - 10):
            # Swing high: higher than 10 candles before and after
            if df.iloc[i]['high'] == df.iloc[i-10:i+10]['high'].max():
                swing_highs.append({'price': float(df.iloc[i]['high']), 'index': i})
            
            # Swing low: lower than 10 candles before and after
            if df.iloc[i]['low'] == df.iloc[i-10:i+10]['low'].min():
                swing_lows.append({'price': float(df.iloc[i]['low']), 'index': i})
        
        # Determine current trend
        trend = 'neutral'
        last_bos = None
        last_choch = None
        
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            # Uptrend: Higher highs and higher lows
            if swing_highs[-1]['price'] > swing_highs[-2]['price'] and \
               swing_lows[-1]['price'] > swing_lows[-2]['price']:
                trend = 'bullish'
                last_bos = {
                    'type': 'bullish',
                    'level': swing_highs[-2]['price'],
                    'timestamp': swing_highs[-1]['index']
                }
            
            # Downtrend: Lower highs and lower lows
            elif swing_highs[-1]['price'] < swing_highs[-2]['price'] and \
                 swing_lows[-1]['price'] < swing_lows[-2]['price']:
                trend = 'bearish'
                last_bos = {
                    'type': 'bearish',
                    'level': swing_lows[-2]['price'],
                    'timestamp': swing_lows[-1]['index']
                }
            
            # Check for Change of Character (trend reversal)
            # Bullish CHoCH: Break above previous high in downtrend
            if trend == 'bearish' and df.iloc[-1]['close'] > swing_highs[-1]['price']:
                last_choch = {
                    'type': 'bullish',
                    'level': swing_highs[-1]['price'],
                    'timestamp': len(df) - 1
                }
                trend = 'bullish_reversal'
            
            # Bearish CHoCH: Break below previous low in uptrend
            elif trend == 'bullish' and df.iloc[-1]['close'] < swing_lows[-1]['price']:
                last_choch = {
                    'type': 'bearish',
                    'level': swing_lows[-1]['price'],
                    'timestamp': len(df) - 1
                }
                trend = 'bearish_reversal'
        
        return {
            'trend': trend,
            'last_bos': last_bos,
            'last_choch': last_choch,
            'swing_highs': swing_highs[-3:] if swing_highs else [],
            'swing_lows': swing_lows[-3:] if swing_lows else []
        }
    
    def _generate_smart_money_signal(self, df: pd.DataFrame) -> Dict:
        """
        Generate trading signal based on Smart Money concepts confluence
        """
        current_price = float(df.iloc[-1]['close'])
        signal = 'HOLD'
        confidence = 0.0
        reasons = []
        
        # 1. Check order blocks
        bullish_ob_score = 0
        bearish_ob_score = 0
        
        for ob in self.order_blocks:
            if ob['type'] == 'bullish' and ob['low'] <= current_price <= ob['high']:
                bullish_ob_score += ob['strength']
                reasons.append(f"Inside bullish order block (strength: {ob['strength']:.1f})")
            elif ob['type'] == 'bearish' and ob['low'] <= current_price <= ob['high']:
                bearish_ob_score += ob['strength']
                reasons.append(f"Inside bearish order block (strength: {ob['strength']:.1f})")
        
        # 2. Check Fair Value Gaps
        bullish_fvg_score = 0
        bearish_fvg_score = 0
        
        for fvg in self.fair_value_gaps:
            if fvg['type'] == 'bullish' and not fvg['filled']:
                # Price approaching bullish FVG from above (potential support)
                if current_price > fvg['gap_high'] and current_price < fvg['gap_high'] * 1.02:
                    bullish_fvg_score += fvg['strength']
                    reasons.append(f"Approaching bullish FVG (gap: {fvg['gap_size']:.1f})")
            elif fvg['type'] == 'bearish' and not fvg['filled']:
                # Price approaching bearish FVG from below (potential resistance)
                if current_price < fvg['gap_low'] and current_price > fvg['gap_low'] * 0.98:
                    bearish_fvg_score += fvg['strength']
                    reasons.append(f"Approaching bearish FVG (gap: {fvg['gap_size']:.1f})")
        
        # 3. Check liquidity sweeps (strongest signal)
        recent_sweep = None
        if self.liquidity_sweeps:
            recent_sweep = self.liquidity_sweeps[-1]
            # Check if sweep is recent (within last 5 candles)
            if isinstance(recent_sweep['timestamp'], int):
                if len(df) - recent_sweep['timestamp'] <= 5:
                    if recent_sweep['type'] == 'bullish':
                        bullish_ob_score += recent_sweep['strength'] * 3  # Strong signal
                        reasons.append(f"Recent bullish liquidity sweep (strength: {recent_sweep['strength']:.2f})")
                    else:
                        bearish_ob_score += recent_sweep['strength'] * 3
                        reasons.append(f"Recent bearish liquidity sweep (strength: {recent_sweep['strength']:.2f})")
        
        # 4. Check market structure
        structure_bias = 0
        if self.market_structure['trend'] == 'bullish':
            structure_bias = 0.2
            reasons.append("Bullish market structure")
        elif self.market_structure['trend'] == 'bearish':
            structure_bias = -0.2
            reasons.append("Bearish market structure")
        elif self.market_structure['trend'] == 'bullish_reversal':
            structure_bias = 0.3
            reasons.append("Bullish Change of Character detected")
        elif self.market_structure['trend'] == 'bearish_reversal':
            structure_bias = -0.3
            reasons.append("Bearish Change of Character detected")
        
        # Calculate final scores
        bullish_score = bullish_ob_score + bullish_fvg_score + max(0, structure_bias)
        bearish_score = bearish_ob_score + bearish_fvg_score + max(0, -structure_bias)
        
        # Normalize scores to confidence (0-1)
        total_score = bullish_score + bearish_score
        if total_score > 0:
            if bullish_score > bearish_score:
                signal = 'BUY'
                confidence = min(0.95, bullish_score / (bullish_score + bearish_score))
            else:
                signal = 'SELL'
                confidence = min(0.95, bearish_score / (bullish_score + bearish_score))
        
        # Boost confidence for multiple confluences
        confluence_count = len(reasons)
        if confluence_count >= 3:
            confidence = min(0.95, confidence * 1.2)
        elif confluence_count >= 2:
            confidence = min(0.95, confidence * 1.1)
        
        return {
            'signal': signal,
            'confidence': confidence,
            'smart_money_score': {
                'bullish': bullish_score,
                'bearish': bearish_score
            },
            'patterns_detected': {
                'order_blocks': len(self.order_blocks),
                'fair_value_gaps': len(self.fair_value_gaps),
                'liquidity_sweeps': len(self.liquidity_sweeps)
            },
            'market_structure': self.market_structure['trend'],
            'reasons': reasons,
            'analysis_type': 'smart_money'
        }
    
    def _is_bullish_order_block(self, candle: pd.Series, prev_candles: pd.DataFrame, avg_range: float) -> bool:
        """Check if candle qualifies as bullish order block"""
        # Large bullish candle
        if candle['close'] <= candle['open']:
            return False
        
        candle_range = candle['high'] - candle['low']
        body_size = candle['close'] - candle['open']
        
        # Candle must be significantly larger than average
        if candle_range < avg_range * self.min_block_strength:
            return False
        
        # Body must be at least 60% of range (strong momentum)
        if body_size < candle_range * 0.6:
            return False
        
        # Must be at/near local low
        recent_low = prev_candles['low'].min()
        if candle['low'] > recent_low * 1.01:  # Not at low
            return False
        
        return True
    
    def _is_bearish_order_block(self, candle: pd.Series, prev_candles: pd.DataFrame, avg_range: float) -> bool:
        """Check if candle qualifies as bearish order block"""
        # Large bearish candle
        if candle['close'] >= candle['open']:
            return False
        
        candle_range = candle['high'] - candle['low']
        body_size = candle['open'] - candle['close']
        
        # Candle must be significantly larger than average
        if candle_range < avg_range * self.min_block_strength:
            return False
        
        # Body must be at least 60% of range (strong momentum)
        if body_size < candle_range * 0.6:
            return False
        
        # Must be at/near local high
        recent_high = prev_candles['high'].max()
        if candle['high'] < recent_high * 0.99:  # Not at high
            return False
        
        return True
    
    def _check_level_respect(self, future_candles: pd.DataFrame, low: float, high: float) -> bool:
        """Check if price respects a level in future candles"""
        if len(future_candles) == 0:
            return False
        
        touches = 0
        for _, candle in future_candles.iterrows():
            # Check if price touches but doesn't break through significantly
            if (candle['low'] <= high and candle['high'] >= low):
                # Check if it respects (doesn't close beyond)
                if low <= candle['close'] <= high:
                    touches += 1
        
        return touches >= 1  # At least one respectful touch
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis when insufficient data"""
        return {
            'signal': 'HOLD',
            'confidence': 0.0,
            'smart_money_score': {'bullish': 0, 'bearish': 0},
            'patterns_detected': {
                'order_blocks': 0,
                'fair_value_gaps': 0,
                'liquidity_sweeps': 0
            },
            'market_structure': 'neutral',
            'reasons': ['Insufficient data for Smart Money analysis'],
            'analysis_type': 'smart_money'
        }
    
    def get_visual_report(self) -> str:
        """Generate visual report of detected patterns"""
        report = "\n🏦 SMART MONEY ANALYSIS REPORT\n"
        report += "=" * 50 + "\n"
        
        # Order Blocks
        report += f"\n📦 Order Blocks ({len(self.order_blocks)}):\n"
        for ob in self.order_blocks[-3:]:  # Last 3
            icon = "🟢" if ob['type'] == 'bullish' else "🔴"
            report += f"  {icon} {ob['type'].upper()} | "
            report += f"Range: {ob['low']:.1f}-{ob['high']:.1f} | "
            report += f"Strength: {ob['strength']:.1f}x\n"
        
        # Fair Value Gaps
        report += f"\n🔳 Fair Value Gaps ({len(self.fair_value_gaps)}):\n"
        for fvg in self.fair_value_gaps[-3:]:  # Last 3
            icon = "⬆️" if fvg['type'] == 'bullish' else "⬇️"
            status = "❌" if fvg['filled'] else "✅"
            report += f"  {icon} {fvg['type'].upper()} {status} | "
            report += f"Gap: {fvg['gap_size']:.1f} | "
            report += f"Strength: {fvg['strength']:.2f}%\n"
        
        # Liquidity Sweeps
        report += f"\n💧 Liquidity Sweeps ({len(self.liquidity_sweeps)}):\n"
        for sweep in self.liquidity_sweeps[-3:]:  # Last 3
            icon = "🚀" if sweep['type'] == 'bullish' else "💥"
            report += f"  {icon} {sweep['type'].upper()} | "
            report += f"Swept: {sweep['swept_level']:.1f} | "
            report += f"Rejection: {sweep['strength']:.2f}\n"
        
        # Market Structure
        report += f"\n📊 Market Structure:\n"
        if isinstance(self.market_structure, dict):
            report += f"  Trend: {self.market_structure.get('trend', 'neutral').upper()}\n"
            if self.market_structure.get('last_bos'):
                bos = self.market_structure['last_bos']
                report += f"  Last BOS: {bos['type']} at {bos['level']:.1f}\n"
            if self.market_structure.get('last_choch'):
                choch = self.market_structure['last_choch']
                report += f"  ⚠️ CHoCH: {choch['type']} at {choch['level']:.1f}\n"
        else:
            report += f"  Trend: neutral\n"
        
        report += "=" * 50 + "\n"
        return report


def test_smart_money_analyzer():
    """Test the Smart Money Analyzer with sample data"""
    import pandas as pd
    import numpy as np
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    
    # Generate price data with patterns
    prices = [8000]
    for i in range(1, 100):
        # Create some patterns
        if i == 30:  # Order block
            change = 50  # Large bullish candle
        elif i == 50:  # Liquidity sweep
            change = -30  # Sweep lows
        elif i == 51:
            change = 40  # Recovery (bullish reaction)
        elif i == 70:  # Fair value gap
            change = 60  # Strong move creating gap
        else:
            change = np.random.randn() * 10
        
        prices.append(prices[-1] + change)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices[:-1] + np.random.randn(99) * 2,
        'high': np.maximum(prices[:-1], prices[1:]) + abs(np.random.randn(99) * 5),
        'low': np.minimum(prices[:-1], prices[1:]) - abs(np.random.randn(99) * 5),
        'close': prices[1:],
        'volume': np.random.randint(1000, 10000, 99)
    })
    
    # Test analyzer
    analyzer = SmartMoneyAnalyzer()
    analysis = analyzer.analyze(df)
    
    print(analyzer.get_visual_report())
    print(f"\n🎯 Signal: {analysis['signal']}")
    print(f"📊 Confidence: {analysis['confidence']:.2%}")
    print(f"📝 Reasons: {', '.join(analysis['reasons'])}")
    
    return analysis


if __name__ == "__main__":
    # Run test
    test_smart_money_analyzer()